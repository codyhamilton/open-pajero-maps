"""Tests for the `build_alldata.py` CLI (unit 12): running it against a tiny
spool (built in-test via `kiwiw.spool.SpoolWriter`, unit 07) writes the
output file and `manifest.json`; a missing spool directory exits non-zero.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata
from kiwiw.model import NameRecord
from kiwiw.spool import SpoolWriter


def _make_name(text: str, lat: float, lon: float) -> NameRecord:
    return NameRecord(
        string_type=6,
        type_code=0,
        type_label="",
        priority=0,
        vertical=False,
        display_scale_flag=0,
        text=text,
        lat=lat,
        lon=lon,
    )


def _make_spool(spool_dir: Path) -> None:
    with SpoolWriter(str(spool_dir)) as w:
        # A handful of level-0 cells near Perth, well inside the reference
        # coverage box.
        w.add(0, 512, 0, names=[_make_name("Cell A", -1.0, 1.0)])
        w.add(0, 513, 0, names=[_make_name("Cell B", -1.0, 1.0)])
        w.add(0, 520, 10, names=[_make_name("Cell C", -1.0, 1.0)])


def test_pipeline_writes_output_and_manifest(tmp_path):
    spool_dir = tmp_path / "spool"
    _make_spool(spool_dir)

    out_path = tmp_path / "out" / "ALLDATA.KWI"
    rc = build_alldata.run(
        spool_dir=str(spool_dir), out_path=str(out_path), levels=[0],
        fixture=None, disk_title="TEST",
    )
    assert rc == 0
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    manifest_path = out_path.parent / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["total_size"] == out_path.stat().st_size
    assert "sha256" in manifest
    assert manifest["levels"]["0"]["parcels"] == 3
    assert manifest["layers_present"] == ["map"]


def test_background_mfde_slot_always_in_buffer(tmp_path):
    """DESIGN.md section 4 / mfde index 1: `R` never emits `absent` for the
    background sub-frame, even when a parcel has zero background shapes --
    `_encode_one()` must call `build_background_frame_bytes()`
    unconditionally (a real bug: it used to skip the call, and thus emit
    the absent sentinel, whenever a parcel's `backgrounds` list was empty --
    the 2026-09-09 full-Australia build's mfde entry-index-1 discrepancy).
    This fixture's spool has names only, no backgrounds, at every cell."""
    from harness.profile import generated_profile

    spool_dir = tmp_path / "spool"
    _make_spool(spool_dir)

    out_path = tmp_path / "out" / "ALLDATA.KWI"
    rc = build_alldata.run(
        spool_dir=str(spool_dir), out_path=str(out_path), levels=[0],
        fixture=None, disk_title="TEST",
    )
    assert rc == 0

    profile = generated_profile(str(out_path))
    idx1_classes = profile["levels"]["0"]["mfde"]["per_entry_index_class_hist"]["1"]
    assert idx1_classes.get("absent", 0) == 0, (
        "mfde index 1 (background) must never be absent, even with zero "
        f"background shapes -- got {idx1_classes}")
    assert idx1_classes.get("in_buffer", 0) == 3


def test_missing_spool_exits_nonzero(tmp_path):
    missing = tmp_path / "does-not-exist"
    out_path = tmp_path / "out" / "ALLDATA.KWI"
    rc = build_alldata.run(
        spool_dir=str(missing), out_path=str(out_path), levels=[0],
        fixture=None, disk_title="TEST",
    )
    assert rc != 0
    assert not out_path.exists()
