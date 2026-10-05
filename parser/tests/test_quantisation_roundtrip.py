"""Quantisation round-trip tool (plan 03, units 3-04, 3-07, 3C-04).

The tool decodes a built `ALLDATA.KWI` and checks it against the spool, so
these tests build tiny real discs (`build_alldata.run`, level 0 only) from
synthetic spools (`kiwiw.spool.SpoolWriter`) and then check them against the
same spool or a deliberately mismatched one."""
from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata  # noqa: E402
from kiwiw.model import BackgroundShape, NameRecord, RoadLink, RoadNode  # noqa: E402
from kiwiw.spool import SpoolWriter  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402
from kiwiw import cenc  # noqa: E402

ENGINES = pytest.mark.parametrize("engine", ["python", pytest.param(
    "c", marks=pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler"))])

# Level-0 cell (512, 0) is lat -50..-49.97917, lon 106..106.03125.
CELL_LAT, CELL_LON = 1 / 48, 1 / 32
LAT0, LON0 = -49.99, 106.01
D = 0.002
RAW_LON = CELL_LON / 4096     # one raw unit of longitude at level 0


def _node(lat, lon):
    return RoadNode(x=0, y=0, lat=lat, lon=lon, oneway=0, planned=0, tunnel=False, bridge=False)


def _link(pts):
    nodes = [_node(*pts[0]), _node(*pts[-1])]
    return RoadLink(display_class=1, road_type=1, altitude_flag=False,
                    route_type_guidance_flag=False, pseudo3d_updown=0,
                    route_planning_tag=False, link_id_flag=False, selected_link_flag=False,
                    toll_flag=False, route_number_flag=False, infra_link_flag=False,
                    link_id_number_flag=False, n_nodes=2, nodes=nodes, points=list(pts))


def _square(lat0, lon0, d=D, dlon=None):
    e = d if dlon is None else dlon
    return [(lat0 - d, lon0 - e), (lat0 + d, lon0 - e), (lat0 + d, lon0 + e),
            (lat0 - d, lon0 + e), (lat0 - d, lon0 - e)]


def _bg(coords, type_code=1):
    return BackgroundShape(shape_class=2, type_code=type_code, type_label="x",
                           n_coords=len(coords), mult_const=1, underground=False,
                           pen_up=False, coords=coords)


def _name(lat, lon):
    # string_type 6 / type_code 0: other codes are dropped by the name encoder
    return NameRecord(string_type=6, type_code=0, type_label="", priority=0, vertical=False,
                      display_scale_flag=0, text="n", lat=lat, lon=lon)


def _centre(ix, iy):
    return -50 + (iy + 0.5) * CELL_LAT, 90 + (ix + 0.5) * CELL_LON


def _write_spool(path: Path, cells: dict) -> Path:
    with SpoolWriter(str(path)) as w:
        for (ix, iy), content in sorted(cells.items()):
            w.add(0, ix, iy, **content)
    return path


def _base_cells(bg=True, bg_shift_lon=0.0):
    a, m, b = (LAT0, LON0), (LAT0 + 0.0003, LON0 + 0.0001), (LAT0 + 0.0005, LON0 + 0.0005)
    bgs = [_bg(_square(LAT0, LON0 + bg_shift_lon))] if bg else []
    return {(512, 0): {"roads": [_link([a, m, b])], "backgrounds": bgs, "names": [_name(*a)]}}


def _big_cells(shift_lon=0.0):
    """A polygon 2.5 cells square homed in cell (514, 3), so it crosses cell
    edges (boundary vertices) and covers the centre cell (interior cover);
    every cell it touches is emitted through a name of its own."""
    clat, clon = _centre(514, 3)
    cells = {}
    for ix in range(513, 516):
        for iy in range(2, 5):
            cells[(ix, iy)] = {"roads": [], "backgrounds": [], "names": [_name(*_centre(ix, iy))]}
    cells[(514, 3)]["backgrounds"] = [_bg(_square(clat, clon + shift_lon, 1.25 * CELL_LAT,
                                                  1.25 * CELL_LON), type_code=2)]
    return cells


def _build(tmp_path: Path, name: str, cells: dict):
    spool = _write_spool(tmp_path / f"spool_{name}", cells)
    disc = tmp_path / name / "ALLDATA.KWI"
    rc = build_alldata.run(spool_dir=str(spool), out_path=str(disc), levels=[0],
                           fixture=None, disk_title="TEST")
    assert rc == 0
    return disc, spool


def _failing(res):
    return {k: v["failing"] for k, v in res["totals"].items() if v["failing"]}


# ------------------------------------------------------------------ geometry units

def test_point_set_is_chebyshev_within_half_unit():
    ps = qr.PointSet(np.array([10.4, 20.0]), np.array([5.2, 7.6]))
    d = ps.nearest(np.array([10, 20, 30]), np.array([5, 8, 0]))
    assert d[0] == pytest.approx(0.4) and d[1] == pytest.approx(0.4) and np.isinf(d[2])


def test_cheb_seg_distance():
    d = qr._cheb_seg(np.array([5.0, 0.0]), np.array([3.0, 0.0]),
                     np.array([0.0, 10.0]), np.array([0.0, 10.0]),
                     np.array([10.0, 20.0]), np.array([0.0, 10.0]))
    assert d[0] == pytest.approx(3.0)
    # diagonal segment (10,10)-(20,10)... distance from origin is 10
    assert d[1] == pytest.approx(10.0)


# ------------------------------------------------------------------ end to end

@ENGINES
def test_passes_against_its_own_spool(tmp_path, engine):
    cells = {**_base_cells(), **_big_cells()}
    disc, spool = _build(tmp_path, "full", cells)
    res = qr.roundtrip(str(disc), str(spool), workers=1, engine=engine)
    assert res["pass"] is True, (_failing(res), res["levels"]["0"]["failures"])
    t = res["totals"]
    for kind in ("road_node", "name_anchor", "background", "background_boundary",
                 "completeness", "interior_cover", "range", "step"):
        assert t[kind]["checked"] > 0, kind
    text = json.dumps(res, sort_keys=True)
    assert str(tmp_path) not in text
    res2 = qr.roundtrip(str(disc), str(spool), workers=1, engine=engine)
    for r in (res, res2):
        r.pop("wall_s")
        r.pop("timing", None)
    assert res2 == res
    assert res["engine"] == engine


@ENGINES
def test_cli_exit_code_and_report(tmp_path, engine):
    disc, spool = _build(tmp_path, "full", _base_cells())
    out = tmp_path / "rt.json"
    assert qr.main(["--disc", str(disc), "--spool", str(spool), "--out", str(out),
                    "--workers", "1", "--engine", engine]) == 0
    assert json.loads(out.read_text())["pass"] is True
    _, other = _build(tmp_path, "nobg", _base_cells(bg=False))
    assert qr.main(["--disc", str(disc), "--spool", str(other), "--out", str(out),
                    "--workers", "1", "--engine", engine]) == 1


@ENGINES
def test_vertex_outside_every_source_polygon_is_caught(tmp_path, engine):
    """Check a disc against a spool whose same-type polygon sits 8 raw units
    east: every decoded vertex is then outside every source polygon's
    half-unit neighbourhood."""
    disc, _ = _build(tmp_path, "full", _base_cells())
    _, moved = _build(tmp_path, "moved", _base_cells(bg_shift_lon=8 * RAW_LON))
    res = qr.roundtrip(str(disc), str(moved), workers=1, engine=engine)
    assert res["pass"] is False
    assert _failing(res) == {"background": res["totals"]["background"]["failing"]}
    fails = [f for f in res["levels"]["0"]["failures"] if f["kind"] == "background"]
    assert fails and all(f["error_raw"] is None or f["error_raw"] > 0.5 for f in fails)
    assert all(f["cell"] == [512, 0] for f in fails)


@ENGINES
def test_boundary_vertex_outside_every_source_polygon_is_caught(tmp_path, engine):
    """The large polygon moved 8 raw units east: boundary vertices on its
    west side then lie outside it, and interior vertices off its outline."""
    disc, _ = _build(tmp_path, "full", _big_cells())
    _, moved = _build(tmp_path, "moved", _big_cells(shift_lon=8 * RAW_LON))
    res = qr.roundtrip(str(disc), str(moved), workers=1, engine=engine)
    assert res["pass"] is False
    assert res["totals"]["background_boundary"]["failing"] > 0


@ENGINES
def test_removed_piece_is_caught(tmp_path, engine):
    """A disc built without the polygon, checked against the spool that has
    it: the (cell, type) has no decoded piece."""
    disc, _ = _build(tmp_path, "nobg", _base_cells(bg=False))
    _, spool = _build(tmp_path, "full", _base_cells())
    res = qr.roundtrip(str(disc), str(spool), workers=1, engine=engine)
    assert res["pass"] is False
    assert _failing(res) == {"completeness": 1}
    (f,) = [f for f in res["levels"]["0"]["failures"] if f["kind"] == "completeness"]
    assert f["cell"] == [512, 0] and f["type"] == 1


@ENGINES
def test_removed_cover_piece_is_caught(tmp_path, engine):
    """Removing the large polygon loses its pieces in all nine cells."""
    cells = _big_cells()
    disc, _ = _build(tmp_path, "full", cells)
    stripped = {k: {**v, "backgrounds": []} for k, v in cells.items()}
    disc2, _ = _build(tmp_path, "stripped", stripped)
    _, spool = _build(tmp_path, "spool", cells)
    res = qr.roundtrip(str(disc2), str(spool), workers=1, engine=engine)
    assert _failing(res) == {"completeness": 9}


@ENGINES
def test_moved_road_node_and_name_are_caught(tmp_path, engine):
    disc, _ = _build(tmp_path, "full", _base_cells(bg=False))
    a, b = (LAT0, LON0 + 3 * RAW_LON), (LAT0 + 0.0005, LON0 + 0.0005)
    moved = {(512, 0): {"roads": [_link([a, b])], "backgrounds": [], "names": [_name(*a)]}}
    _, spool = _build(tmp_path, "moved", moved)
    res = qr.roundtrip(str(disc), str(spool), workers=1, engine=engine)
    assert _failing(res) == {"road_node": 1, "name_anchor": 1}


# ------------------------------------------------------------------ Plan 04 2-06: the K1 driver

sys.path.insert(0, str(Path(__file__).resolve().parent))
import k1_fixtures as fx  # noqa: E402

needs_c = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")
ALL = {**fx.FIXTURES, **fx.BG_FIXTURES, **fx.CMP_FIXTURES}


@pytest.fixture(scope="module", params=list(ALL))
def fixture(request, tmp_path_factory):
    disc, spool = fx.build_fixture(tmp_path_factory.mktemp(request.param), request.param)
    return request.param, disc, spool


def _canon(res):
    """The compared bytes: everything but `COMPARE_EXCLUDES` (`timing`, `wall_s`)."""
    return qr.normalise_k1_report_for_compare(res).encode()


@needs_c
def test_c_equals_python_on_every_fixture(fixture):
    name, disc, spool = fixture
    py = qr.roundtrip(str(disc), str(spool), workers=1, engine="python")
    c = qr.roundtrip(str(disc), str(spool), workers=1, engine="c")
    assert (py["engine"], c["engine"]) == ("python", "c")
    assert (c["pass"], c["failing"]) == (py["pass"], py["failing"]), name
    for lv, a in py["levels"].items():
        b = c["levels"][lv]
        assert (b["blocks"], b["leaves"], b["tall_shapes"]) == (a["blocks"], a["leaves"], a["tall_shapes"])
        assert b["explained"] == a["explained"], name
        for kind, ak in a["kinds"].items():
            bk = b["kinds"][kind]
            assert (bk["checked"], bk["failing"]) == (ak["checked"], ak["failing"]), (name, kind)
            assert bk["worst_error_raw"] == pytest.approx(ak["worst_error_raw"], abs=2e-6), (name, kind)
            pf = [f for f in a["failures"] if f["kind"] == kind]
            cf = [f for f in b["failures"] if f["kind"] == kind]
            assert len(cf) == min(ak["failing"], qr.SAMPLE) == min(len(pf), qr.SAMPLE), (name, kind)
            if ak["failing"] <= qr.SAMPLE:
                # the whole failing set is sampled: identical sets
                dump = lambda rows: sorted(json.dumps(r, sort_keys=True) for r in rows)
                assert dump(cf) == dump(pf), (name, kind)
            # else: the Python tool keeps a (Y, X)-ordered first N per band for the point
            # and background kinds, K1 the contract's (iy, ix, path, vx, vy) first N
            # (DESIGN.md Determinism): both N-sized samples of the same failing set


@needs_c
def test_j1_and_j4_are_byte_equal(fixture, tmp_path):
    name, disc, spool = fixture
    outs = []
    for j in (1, 4):
        out = tmp_path / f"j{j}.json"
        qr.main(["--disc", str(disc), "--spool", str(spool), "--out", str(out),
                 "--workers", str(j), "--engine", "c"])
        res = json.loads(out.read_text())
        assert res["timing"]["workers"] == j and res["compare_excludes"] == ["timing", "wall_s"]
        outs.append(_canon(res))
    assert outs[0] == outs[1], name


@needs_c
def test_one_binding_call_per_range(fixture):
    name, disc, spool = fixture
    res = qr.roundtrip(str(disc), str(spool), workers=1, engine="c")
    container = qr.walk.read_container(str(disc))
    keys = qr._block_keys(str(disc))
    lats = {lv: qr.Lattice(lv) for lv in {k[0] for k in keys}}
    planned = len(qr._block_tasks(qr.SpoolReader(str(spool)), container, keys, lats,
                                  qr.PLAN_WORKERS))
    tm = res["timing"]
    assert tm["ranges"] == planned == tm["c_stats"]["calls"], name
    if name == "dense":
        assert tm["c_stats"]["calls"] * 10 < res["totals"]["range"]["checked"]
    assert tm["c_ns"] > 0 and tm["pss_peak_kb"] > 0


def test_pss_sampler_returns_a_positive_peak():
    import time
    s = qr.PssSampler(interval=0.05).start()
    time.sleep(0.2)
    peak = s.stop()
    assert peak > 0 and s.samples >= 3


# Phase 2: direct finalizer checks; no sampler or K1 worker is launched.
FINALIZE_KIND = "background_boundary"
_FINALIZE_BASELINE = (Path(__file__).resolve().parent / "fixtures" /
                      "finalize_dump_baseline" / "finalize_dump_baseline.py")


def _load_finalize_baseline():
    spec = importlib.util.spec_from_file_location(
        "finalize_dump_baseline", _FINALIZE_BASELINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.finalize_dump_baseline


# Struct padding byte (not a named field); used so equal DUMP_ORDER keys stay
# distinguishable under stable vs unstable argsort. NumPy still uses omitted
# named fields as tie-breakers, so unique dcls alone does NOT prove stability.
_FINALIZE_PAD = 65


def _finalize_rows(n):
    arr = np.zeros(n, dtype=cenc.K1_DUMP_DTYPE)
    raw = arr.view(np.uint8).reshape(n, cenc.K1_DUMP_DTYPE.itemsize)
    raw[:, _FINALIZE_PAD] = (np.arange(n) % 251) + 1
    return arr


def _finalize_pad_seq(arr):
    return arr.view(np.uint8).reshape(len(arr), cenc.K1_DUMP_DTYPE.itemsize)[:, _FINALIZE_PAD].copy()


def _write_finalize_parts(d, chunks, indices=None):
    Path(d).mkdir(parents=True, exist_ok=True)
    for i, chunk in enumerate(chunks):
        if indices is not None and i not in indices:
            continue
        chunk.tofile(Path(d) / f"part_{i:05d}_{FINALIZE_KIND}.bin")


def test_finalize_dump_matches_baseline_bytes(tmp_path):
    n, parts = 5000, 8
    rows = _finalize_rows(n)
    # Prove padding markers make unstable sort diverge while DUMP_ORDER keys tie.
    assert not np.array_equal(
        np.argsort(rows, order=qr.DUMP_ORDER, kind="stable"),
        np.argsort(rows, order=qr.DUMP_ORDER, kind="quicksort"))
    chunks = np.array_split(rows, parts)
    base, cand = tmp_path / "base", tmp_path / "cand"
    _write_finalize_parts(base, chunks)
    _write_finalize_parts(cand, chunks)
    baseline = _load_finalize_baseline()
    bc = baseline(base, [FINALIZE_KIND], parts, lambda s: None)
    cc = qr._finalize_dump(cand, [FINALIZE_KIND], parts, lambda s: None)
    assert bc == cc
    base_sha = hashlib.sha256((base / f"{FINALIZE_KIND}.bin").read_bytes()).digest()
    cand_sha = hashlib.sha256((cand / f"{FINALIZE_KIND}.bin").read_bytes()).digest()
    expected = rows[np.argsort(rows, order=qr.DUMP_ORDER, kind="stable")]
    assert base_sha == cand_sha == hashlib.sha256(expected.tobytes()).digest()
    assert (base / "dump_manifest.json").read_bytes() == (cand / "dump_manifest.json").read_bytes()
    out = np.fromfile(cand / f"{FINALIZE_KIND}.bin", dtype=cenc.K1_DUMP_DTYPE)
    # Equal DUMP_ORDER keys: stable sort preserves input (pad) order.
    assert np.array_equal(_finalize_pad_seq(out), _finalize_pad_seq(rows))
    assert not list(base.glob("part_*.bin"))
    assert not list(cand.glob("part_*.bin"))


def test_finalize_dump_empty_kinds(tmp_path):
    base, cand = tmp_path / "base", tmp_path / "cand"
    _write_finalize_parts(base, [])
    _write_finalize_parts(cand, [])
    baseline = _load_finalize_baseline()
    bc = baseline(base, [FINALIZE_KIND], 4, lambda s: None)
    cc = qr._finalize_dump(cand, [FINALIZE_KIND], 4, lambda s: None)
    assert bc == cc == {FINALIZE_KIND: 0}
    assert (base / f"{FINALIZE_KIND}.bin").read_bytes() == b""
    assert (cand / f"{FINALIZE_KIND}.bin").read_bytes() == b""
    assert (base / "dump_manifest.json").read_bytes() == (cand / "dump_manifest.json").read_bytes()
    assert not list(base.glob("part_*.bin"))
    assert not list(cand.glob("part_*.bin"))


def test_finalize_dump_single_row(tmp_path):
    rows = _finalize_rows(1)
    base, cand = tmp_path / "base", tmp_path / "cand"
    _write_finalize_parts(base, [rows])
    _write_finalize_parts(cand, [rows])
    baseline = _load_finalize_baseline()
    bc = baseline(base, [FINALIZE_KIND], 1, lambda s: None)
    cc = qr._finalize_dump(cand, [FINALIZE_KIND], 1, lambda s: None)
    assert bc == cc == {FINALIZE_KIND: 1}
    base_sha = hashlib.sha256((base / f"{FINALIZE_KIND}.bin").read_bytes()).digest()
    cand_sha = hashlib.sha256((cand / f"{FINALIZE_KIND}.bin").read_bytes()).digest()
    assert base_sha == cand_sha
    assert (base / "dump_manifest.json").read_bytes() == (cand / "dump_manifest.json").read_bytes()
    assert not list(base.glob("part_*.bin"))
    assert not list(cand.glob("part_*.bin"))


def test_finalize_dump_missing_middle_parts(tmp_path):
    n, parts = 1001, 10
    chunks = np.array_split(_finalize_rows(n), parts)
    base, cand = tmp_path / "base", tmp_path / "cand"
    _write_finalize_parts(base, chunks, indices={0, 3, 9})
    _write_finalize_parts(cand, chunks, indices={0, 3, 9})
    baseline = _load_finalize_baseline()
    bc = baseline(base, [FINALIZE_KIND], parts, lambda s: None)
    cc = qr._finalize_dump(cand, [FINALIZE_KIND], parts, lambda s: None)
    assert bc == cc
    base_sha = hashlib.sha256((base / f"{FINALIZE_KIND}.bin").read_bytes()).digest()
    cand_sha = hashlib.sha256((cand / f"{FINALIZE_KIND}.bin").read_bytes()).digest()
    assert base_sha == cand_sha
    assert (base / "dump_manifest.json").read_bytes() == (cand / "dump_manifest.json").read_bytes()
    assert not list(base.glob("part_*.bin"))
    assert not list(cand.glob("part_*.bin"))


def test_finalize_dump_source_has_no_full_copy():
    src = inspect.getsource(qr._finalize_dump)
    assert ".tobytes()" not in src
    assert "write_bytes" not in src
    assert "tofile" in src
    assert 'kind="stable"' in src or "kind='stable'" in src
    assert "argsort" in src


# ------------------------------------------- Plan 16 Phase 1: determinism strip
# Pure fixture JSON / dicts: no disc, no spool, no encode, no C. These lock the
# contract that the determinism strip removes every key in COMPARE_EXCLUDES
# (`timing` and `wall_s`), not `timing` alone.

def _k1_report(**over):
    r = {
        "tool": "quantisation_roundtrip",
        "disc": "ALLDATA.KWI",
        "spool": "spool",
        "tolerance_raw": 0.5,
        "pass": True,
        "failing": 0,
        "totals": {"range": {"checked": 10, "failing": 0, "worst_error_raw": 0.0}},
        "levels": {"0": {"blocks": 1, "leaves": 2, "failures": []}},
        "wall_s": 447.0,
        "compare_excludes": list(qr.COMPARE_EXCLUDES),
        "timing": {"wall_s": 446.912, "workers": 1, "ranges": 3, "pss_peak_kb": 1000},
    }
    r.update(over)
    return r


def test_strip_compare_excludes_removes_every_excluded_key():
    report = _k1_report()
    stripped = qr.strip_compare_excludes(report)
    assert set(report) - set(stripped) == set(qr.COMPARE_EXCLUDES)
    assert "timing" not in stripped and "wall_s" not in stripped
    assert stripped["compare_excludes"] == list(qr.COMPARE_EXCLUDES)
    assert stripped["totals"] == report["totals"] and stripped["levels"] == report["levels"]
    # the input dict is untouched
    assert report["wall_s"] == 447.0 and report["timing"]["wall_s"] == 446.912


def test_reports_differing_only_in_excludes_compare_equal():
    timing_only = _k1_report(wall_s=447.0, timing={"wall_s": 1.0, "workers": 1})
    timing_only_12 = _k1_report(wall_s=74.4, timing={"wall_s": 1.0, "workers": 1})
    assert qr.normalise_k1_report_for_compare(timing_only) == \
        qr.normalise_k1_report_for_compare(timing_only_12)
    both = _k1_report(wall_s=447.0, timing={"wall_s": 446.912, "workers": 1, "ranges": 3})
    both_12 = _k1_report(wall_s=74.4, timing={"wall_s": 74.101, "workers": 12, "ranges": 3})
    assert qr.normalise_k1_report_for_compare(both) == \
        qr.normalise_k1_report_for_compare(both_12)


def test_non_excluded_field_difference_still_unequal():
    base = _k1_report()
    assert qr.normalise_k1_report_for_compare(base) != \
        qr.normalise_k1_report_for_compare(_k1_report(failing=1))
    assert qr.normalise_k1_report_for_compare(base) != \
        qr.normalise_k1_report_for_compare(_k1_report(levels={"0": {"blocks": 2}}))


def test_locked_strip_is_not_timing_only(tmp_path):
    j1 = _k1_report(wall_s=447.0, timing={"wall_s": 446.912, "workers": 1})
    j12 = _k1_report(wall_s=74.4, timing={"wall_s": 74.101, "workers": 12})

    def timing_only(r):
        return json.dumps({k: v for k, v in r.items() if k != "timing"},
                          indent=2, sort_keys=True)

    assert timing_only(j1) != timing_only(j12)
    assert qr.strip_compare_excludes(j1) == qr.strip_compare_excludes(j12)

    a, b = tmp_path / "k1_j1.json", tmp_path / "k1_j12.json"
    a.write_text(json.dumps(j1))
    b.write_text(json.dumps(j12))
    assert qr.normalise_k1_report_for_compare(a) == qr.normalise_k1_report_for_compare(b)
