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
