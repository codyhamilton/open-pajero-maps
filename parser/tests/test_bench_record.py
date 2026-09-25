"""Tests for `--bench`, `--window` and `--frame-dump` (3C-01).

Uses the real Perth fixture spool (`output/extract_timing/spool`, machine
fact) rather than a synthetic one: `--fixture perth` restricts to the same
global cells the extractor populated, and these flags must be checked
against real overlap/division behaviour, not a hand-built fixture. Tests
are skipped if that spool is absent (docs/provenance.md: regenerable,
not committed). Level 0 only, to keep wall time reasonable; this is a
CLI/plumbing check, not the Contract H baseline (measured separately by
the background script).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata

_REPO = Path(__file__).resolve().parent.parent.parent
_SPOOL = _REPO / "output" / "extract_timing" / "spool"

pytestmark = pytest.mark.skipif(
    not _SPOOL.is_dir(), reason="output/extract_timing/spool not present locally")

# A small L0 rectangle well inside perth's fixture range (816..848, 839..887).
_WIN_IX0, _WIN_IY0, _WIN_IX1, _WIN_IY1 = 820, 850, 824, 854


def test_bench_output_byte_identical_to_unbenched(tmp_path):
    plain = tmp_path / "plain" / "ALLDATA.KWI"
    benched = tmp_path / "benched" / "ALLDATA.KWI"
    bench_path = tmp_path / "bench.json"

    rc1 = build_alldata.run(
        spool_dir=str(_SPOOL), out_path=str(plain), levels=[0],
        fixture="perth", disk_title="TEST", workers=4)
    assert rc1 == 0

    rc2 = build_alldata.run(
        spool_dir=str(_SPOOL), out_path=str(benched), levels=[0],
        fixture="perth", disk_title="TEST", workers=4, bench_path=str(bench_path))
    assert rc2 == 0

    assert plain.read_bytes() == benched.read_bytes()
    plain_manifest = json.loads((plain.parent / "manifest.json").read_text())
    benched_manifest = json.loads((benched.parent / "manifest.json").read_text())
    assert plain_manifest == benched_manifest

    record = json.loads(bench_path.read_text())
    assert set(record) >= {"wall_s", "outside_encode_s", "levels"}
    lvl = record["levels"]["0"]
    for key in ("wall_s", "prepass_s", "py_s", "c_s", "handoff_s", "ranges",
                "workers", "calls"):
        assert key in lvl, key
    for key in ("kw_encode_cell", "kw_measure_cell", "kw_bg_shape"):
        assert key in lvl["calls"], key
        assert lvl["calls"][key] > 0


def test_window_frame_dump_matches_full_digest_rows(tmp_path):
    full_out = tmp_path / "full" / "ALLDATA.KWI"
    full_digest = tmp_path / "full.digest"
    rc1 = build_alldata.run(
        spool_dir=str(_SPOOL), out_path=str(full_out), levels=[0],
        fixture="perth", disk_title="TEST", workers=4,
        frame_digest=str(full_digest))
    assert rc1 == 0

    full_rows = {}
    for line in full_digest.read_text().splitlines():
        level, ix, iy, pt, sx, sy, ln, sha = line.split()
        full_rows[(int(level), int(ix), int(iy), int(pt), int(sx), int(sy))] = \
            (int(ln), sha)

    win_out = tmp_path / "win" / "ALLDATA.KWI"
    dump_prefix = str(tmp_path / "dump")
    rc2 = build_alldata.run(
        spool_dir=str(_SPOOL), out_path=str(win_out), levels=[0],
        fixture=None, disk_title="TEST", workers=1,
        window=(0, _WIN_IX0, _WIN_IY0, _WIN_IX1, _WIN_IY1),
        frame_dump=dump_prefix)
    assert rc2 == 0

    tsv_rows = Path(dump_prefix + ".tsv").read_text().splitlines()
    assert tsv_rows, "windowed build over a populated Perth rectangle emitted no frames"

    dump_bytes = Path(dump_prefix + ".bin").read_bytes()
    seen_in_window = 0
    for line in tsv_rows:
        level, ix, iy, pt, sx, sy, off, ln, sha = line.split()
        level, ix, iy, pt, sx, sy, off, ln = (
            int(level), int(ix), int(iy), int(pt), int(sx), int(sy), int(off), int(ln))
        assert _WIN_IX0 <= ix < _WIN_IX1
        assert _WIN_IY0 <= iy < _WIN_IY1
        key = (level, ix, iy, pt, sx, sy)
        assert key in full_rows, f"{key} not found in full digest"
        exp_ln, exp_sha = full_rows[key]
        assert ln == exp_ln
        assert sha == exp_sha
        frame_bytes = dump_bytes[off:off + ln]
        assert hashlib.sha256(frame_bytes).hexdigest() == sha
        seen_in_window += 1
    assert seen_in_window == len(tsv_rows)
