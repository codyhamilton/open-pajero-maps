"""The build's E1/E2 wiring (plan 03, 3C-08; DESIGN.md Contract B).

Boundary checks on a tiny synthetic spool (fast; no Perth, no full disc):
  * per level, E1 and E2 are each called once per planned row range
    (`--bench` call counts), and the bench carries the E1/E2 C timers;
  * the manifest's `overlap` block is E1's own counters (summed over the
    ranges equals one whole-level E1 call);
  * the Python overlap pre-pass, the legacy per-cell encoder binding and
    the extractor imports are gone from the build.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata
from kiwiw import cenc, descriptor
from test_build_alldata import _make_multirow_spool

_PARSER = Path(__file__).resolve().parent.parent


def _build(tmp_path, workers, **kw):
    spool_dir = tmp_path / "spool"
    if not spool_dir.exists():
        _make_multirow_spool(spool_dir)
    out = tmp_path / f"j{workers}" / "ALLDATA.KWI"
    bench = tmp_path / f"bench{workers}.json"
    rc = build_alldata.run(spool_dir=str(spool_dir), out_path=str(out), levels=[6],
                           fixture=None, disk_title="TEST", fill_mask=True,
                           workers=workers, bench_path=str(bench), **kw)
    assert rc == 0
    return (json.loads(bench.read_text()), json.loads((out.parent / "manifest.json").read_text()),
            spool_dir)


def test_e1_e2_once_per_range(tmp_path):
    for workers in (1, 3):
        rec, _m, _s = _build(tmp_path, workers)
        lvl = rec["levels"]["6"]
        assert lvl["ranges"] >= (2 if workers > 1 else 1)
        assert lvl["calls"]["e1"] == lvl["calls"]["e2"] == lvl["ranges"], lvl
        assert "e3" in lvl["calls"]
        for k in ("e1_c_s", "e2_c_s", "prepass_s", "py_s", "c_s", "handoff_s"):
            assert lvl[k] >= 0.0, k


def test_manifest_overlap_is_e1_counters(tmp_path):
    _rec, m, spool_dir = _build(tmp_path, 3)
    mask = build_alldata.load_parcel_mask()
    desc = descriptor.build_for_spool(spool_dir, 6, mask_rect=mask.get(6))
    sp = cenc.E1Spool(spool_dir, 6)
    _rows, whole = cenc.e1(desc, sp, None, None)
    sp.close()
    assert m["overlap"]["6"] == whole


def test_python_prepass_and_legacy_encoder_gone():
    assert not (_PARSER / "kiwiw" / "overlap.py").exists()
    src = (_PARSER / "build_alldata.py").read_text()
    assert "import osm_to_parcel_geometry" not in src and "from osm_to_parcel_geometry" not in src
    assert "import overlap" not in src and "KIWIW_NO_C" not in src
    for name in ("make_encoder", "CellEncoder"):
        assert not hasattr(cenc, name), name
