"""K1 failure dump (plan 04, Phase 3, brief 3-02).

`quantisation_roundtrip.py --dump-failures DIR` writes EVERY failing item of the
five failing kinds to `DIR/<kind>.bin` as fixed-width rows (`K1_F_DUMP` in
`_k1.h`, mirrored by `cenc.K1_DUMP_DTYPE`) plus `DIR/dump_manifest.json`. On a
fixture: the dump's row count per kind equals the report's `failing` for that
kind, every bounded sample in the report appears in the dump, and the bytes do
not depend on the worker count or the band split.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import k1_fixtures as fx  # noqa: E402
from kiwiw import cenc  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")

DUMP_KINDS = qr.DUMP_KINDS
_REASON = {"name_anchor": 1, "background": 4, "background_boundary": 5,
           "interior_cover": 6, "completeness": 7}


def _run(disc, spool, dump_dir, report, workers=1, kinds=None, monkey=None):
    args = ["--disc", str(disc), "--spool", str(spool), "--workers", str(workers),
            "--engine", "c", "--dump-failures", str(dump_dir)]
    if kinds is not None:
        args += ["--dump-kinds", ",".join(kinds)]
    if report is not None:
        args += ["--out", str(report)]
    if monkey is not None:
        monkey()
    return qr.main(args)


def _rows(dump_dir, kind):
    p = Path(dump_dir) / f"{kind}.bin"
    if not p.exists():
        return np.zeros(0, cenc.K1_DUMP_DTYPE)
    return np.fromfile(p, dtype=cenc.K1_DUMP_DTYPE)


def _fixture_names():
    names = list(fx.BG_FIXTURES) + list(fx.CMP_FIXTURES)
    names += [n for n in ("vertex_moved", "piece_removed", "name_node_moved",
                          "many_failures", "dense_moved")
              if n in fx.FIXTURES]
    return names


@pytest.mark.parametrize("name", _fixture_names())
def test_dump_counts_and_samples_match_report(tmp_path, name):
    disc, spool = fx.build_fixture(tmp_path, name)
    report = tmp_path / "report.json"
    dump_dir = tmp_path / "dump"
    rc = _run(disc, spool, dump_dir, report, workers=1)
    assert rc in (0, 1)
    res = json.loads(report.read_text())
    assert res["dump"] == {k: int(res["totals"][k]["failing"]) for k in DUMP_KINDS}
    manifest = json.loads((dump_dir / "dump_manifest.json").read_text())
    for kind in DUMP_KINDS:
        rows = _rows(dump_dir, kind)
        failing = int(res["totals"][kind]["failing"])
        assert len(rows) == failing == manifest["kinds"][kind]["rows"], (name, kind)
        if failing == 0:
            continue
        assert manifest["kinds"][kind]["row_size"] == cenc.K1_DUMP_DTYPE.itemsize
        if kind == "completeness":
            keys = {(int(r["ix"]), int(r["iy"]), int(r["reason"]), int(r["code"]))
                    for r in rows}
            for f in res["levels"]["0"]["failures"]:
                if f["kind"] != kind:
                    continue
                assert (f["cell"][0], f["cell"][1], 7, f["type"]) in keys, (name, f)
        elif kind == "interior_cover":
            keys = {(int(r["ix"]), int(r["iy"]), int(r["reason"])) for r in rows}
            for f in res["levels"]["0"]["failures"]:
                if f["kind"] != kind:
                    continue
                assert (f["cell"][0], f["cell"][1], 6) in keys, (name, f)
        else:
            keys = {(int(r["ix"]), int(r["iy"]), int(r["vx"]), int(r["vy"]),
                     int(r["reason"])) for r in rows}
            for f in res["levels"]["0"]["failures"]:
                if f["kind"] != kind:
                    continue
                raw = f["vertex"]["raw"]
                assert (f["cell"][0], f["cell"][1], raw[0], raw[1],
                        _REASON[kind]) in keys, (name, f)


def test_every_requested_kind_has_a_file(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_boundary_displaced")
    dump_dir = tmp_path / "dump"
    _run(disc, spool, dump_dir, None, workers=1, kinds=["background", "name_anchor"])
    assert (dump_dir / "background.bin").exists()
    assert (dump_dir / "name_anchor.bin").exists()
    manifest = json.loads((dump_dir / "dump_manifest.json").read_text())
    assert set(manifest["kinds"]) == {"background", "name_anchor"}
    assert not (dump_dir / "background_boundary.bin").exists()


@pytest.mark.parametrize("name", ["bg_boundary_displaced", "bg_tall"])
def test_dump_bytes_do_not_depend_on_workers_or_split(tmp_path, name, monkeypatch):
    disc, spool = fx.build_fixture(tmp_path, name)
    outs = []
    for tag, workers, plan in (("j1", 1, 12), ("j4", 4, 12), ("split3", 1, 3)):
        d = tmp_path / f"dump_{tag}"
        monkeypatch.setattr(qr, "PLAN_WORKERS", plan)
        _run(disc, spool, d, None, workers=workers)
        blob = {k: (d / f"{k}.bin").read_bytes() for k in DUMP_KINDS}
        outs.append(blob)
    for blob in outs[1:]:
        assert blob == outs[0], name


def test_dump_is_off_by_default(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_boundary_displaced")
    report = tmp_path / "report.json"
    qr.main(["--disc", str(disc), "--spool", str(spool), "--workers", "1",
             "--engine", "c", "--out", str(report)])
    res = json.loads(report.read_text())
    assert "dump" not in res
    assert not (tmp_path / "dump").exists()


# ---------------------------------------------------------------- 3-03 diagnostics
# The diagnostic columns are computed only for the three background-family kinds and
# only with the dump on; every other row keeps the stated sentinel. `onb` is the
# frame-boundary mask of the row's frame-raw `vx`/`vy`.

_SENT = np.iinfo(np.int32).min


def _raw_at(ix, iy, rx, ry):
    clat, clon = fx._centre(ix, iy)
    return clat + ry * fx.CELL_LAT / 4096, clon + rx * fx.CELL_LON / 4096


def _build_bowtie(parent):
    """A self-overlapping pentagram spool (a figure-eight ring) with a tiny disc ring
    at its centre: the centre has winding 2 but is even-odd outside, so `in_wn_same`
    and `in_eo_same` differ there."""
    import math
    r = 1600
    th = [math.radians(90 + 144 * k) for k in range(5)]
    star = [_raw_at(512, 0, r * math.cos(t), r * math.sin(t)) for t in th]
    star.append(star[0])
    spool_cells = fx._poly_cells(star, (512, 0), [512], [0], 2)
    tri = [_raw_at(512, 0, 0, 0), _raw_at(512, 0, 100, 0), _raw_at(512, 0, 0, 100),
           _raw_at(512, 0, 0, 0)]
    disc_cells = fx._poly_cells(tri, (512, 0), [512], [0], 2)
    disc, _ = fx._build(parent, "bg_bowtie_d", disc_cells)
    _, spool = fx._build(parent, "bg_bowtie_s", spool_cells)
    return disc, spool


def _dump(disc, spool, tmp_path):
    d = tmp_path / "dump"
    r = tmp_path / "report.json"
    assert _run(disc, spool, d, r, workers=1) in (0, 1)
    return {k: _rows(d, k) for k in DUMP_KINDS}


def _eo_wn(xs, ys, px, py):
    """Even-odd (checker pairing, no tolerance) and non-zero winding at (px, py) for one
    closed ring, horizontal ray, half-open edge rule -- the numpy double of `diag_inside`."""
    xs, ys = list(xs), list(ys)
    n = len(xs)
    pairs, wn = [], 0
    for i in range(n):
        j = (i + 1) % n
        x1, y1, x2, y2 = xs[i], ys[i], xs[j], ys[j]
        vlo, vhi = (y1, y2) if y1 < y2 else (y2, y1)
        if not (vlo <= py < vhi):
            continue
        pairs.append(x1 + (py - y1) * (x2 - x1) / (y2 - y1))
        cross = (x2 - x1) * (py - y1) - (px - x1) * (y2 - y1)
        if y1 <= py:
            wn += 1 if cross > 0 else 0
        else:
            wn -= 1 if cross < 0 else 0
    pairs.sort()
    eo = any(pairs[k] <= px <= pairs[k + 1] for k in range(0, len(pairs) - 1, 2))
    return int(eo), int(wn != 0)


def _sentinels(r):
    return (np.isnan(r["d_any"]) and r["any_type"] == -1 and r["in_eo_same"] == 0
            and r["in_wn_same"] == 0 and r["in_eo_any"] == 0 and r["src_ix"] == _SENT
            and r["src_iy"] == _SENT and r["src_rec"] == -1 and r["src_tall"] == 0
            and r["src_nv"] == -1 and np.isnan(r["src_maxseg"]) and np.isnan(r["d_src"])
            and r["dcls"] == -1 and r["dnv"] == -1)


@pytest.mark.parametrize("name", ["bg_boundary_displaced", "bg_wrong_type", "many_failures"])
def test_onb_is_the_frame_raw_boundary_mask(tmp_path, name):
    disc, spool = fx.build_fixture(tmp_path, name)
    rows = _dump(disc, spool, tmp_path)
    seen = 0
    for arr in rows.values():
        for r in arr:
            vx, vy = int(r["vx"]), int(r["vy"])
            want = (int(vx == 0) | (int(vx == 4096) << 1) | (int(vy == 0) << 2)
                    | (int(vy == 4096) << 3))
            assert int(r["onb"]) == want, (name, r)
            seen += 1
    assert seen


def test_diag_sentinels_for_kinds_without_diagnostics(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "name_node_moved")
    na = _dump(disc, spool, tmp_path)["name_anchor"]
    assert len(na)
    assert all(_sentinels(r) for r in na)
    disc, spool = fx.build_fixture(tmp_path, "cmp_tall_removed")
    comp = _dump(disc, spool, tmp_path)["completeness"]
    assert len(comp)
    assert all(_sentinels(r) for r in comp)


def test_bg_wrong_type_any_columns_and_src_sentinel(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_wrong_type")
    bg = _dump(disc, spool, tmp_path)["background"]
    assert len(bg)
    assert np.all(bg["code"] == 1)
    assert np.all(bg["any_type"] == 2)                  # the spool's type
    assert np.all(bg["d_any"] < 1.0)                    # coincident square, quantisation noise
    assert np.all(bg["in_eo_same"] == 0)                # no type-1 spool shape
    assert np.any(bg["in_eo_any"] == 1)                 # inside the type-2 square
    assert np.all(bg["src_ix"] == _SENT)                # no type-1 source within 64 raw
    assert np.all(bg["dcls"] == 2) and np.all(bg["dnv"] == 25)


def test_bg_boundary_displaced_source_and_maxseg(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_boundary_displaced")
    bb = _dump(disc, spool, tmp_path)["background_boundary"]
    assert len(bb)
    assert np.all(bb["onb"] != 0)                       # every row is a boundary vertex
    assert np.allclose(bb["d_src"], 8.0)                # the spool is 8 raw east
    assert np.all(bb["src_ix"] == 514) and np.all(bb["src_iy"] == 3)
    assert np.all(bb["src_rec"] == 0) and np.all(bb["src_tall"] == 0)
    assert np.all(bb["src_nv"] == 5)                    # a closed square
    side = 2.5 * 4096                                   # 2.5 cells of raw, computed here
    assert np.allclose(bb["src_maxseg"], side)
    assert np.all(bb["dcls"] == 2)


def test_bg_tall_displaced_source_is_tall(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_tall_displaced")
    rows = _dump(disc, spool, tmp_path)
    for kind in ("background", "background_boundary"):
        arr = rows[kind]
        assert len(arr)
        assert np.all(arr["src_tall"] == 1)
        assert np.allclose(arr["src_maxseg"], 4.5 * 4096)
        assert np.all(arr["src_ix"] == 514) and np.all(arr["src_iy"] == 3)


def test_bg_outside_inside_flags_and_source(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_outside")
    bg = _dump(disc, spool, tmp_path)["background"]
    assert len(bg)
    assert np.all(bg["in_eo_same"] == 0)
    # the moved vertex is 30 raw outside the source square: within K1_DIAG_SAME (64),
    # so the source IS found (the brief's "src_* sentinel" here is contradicted).
    assert np.all(np.isfinite(bg["d_src"]))
    assert np.all(bg["d_src"] <= 64.0)
    assert np.all(bg["src_ix"] == 512) and np.all(bg["src_iy"] == 0) and np.all(bg["src_rec"] == 0)


def test_bg_bowtie_winding_differs_from_parity(tmp_path):
    disc, spool = _build_bowtie(tmp_path)
    bg = _dump(disc, spool, tmp_path)["background"]
    assert len(bg)
    import math
    r = 1600
    th = [math.radians(90 + 144 * k) for k in range(5)]
    star = [_raw_at(512, 0, r * math.cos(t), r * math.sin(t)) for t in th]
    star.append(star[0])
    lat = qr.Lattice(0)
    sx = [int(np.rint(lat.gx(lo))) for _la, lo in star]
    sy = [int(np.rint(lat.gy(la))) for la, _lo in star]
    diff = 0
    for row in bg:
        px = int(np.rint(lat.gx(float(row["lon"]))))
        py = int(np.rint(lat.gy(float(row["lat"]))))
        eo, wn = _eo_wn(sx, sy, px, py)
        assert int(row["in_eo_same"]) == eo, row
        assert int(row["in_wn_same"]) == wn, row
        diff += int(eo != wn)
    assert diff

