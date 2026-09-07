"""Tests for the level-0 name-record encoders added by brief 11
(docs/plans/01-eval-harness-and-map-layer/briefs/11-name-types.md):
``kiwiw.synth.encode_name_record_type5_bytes``,
``encode_name_record_type6_bytes``, and ``build_name_frame_bytes``'s
per-level string-type selection.

Covers, per the brief's "Tests" requirement:
  1. Encode/decode round-trip for each supported type (5, 6) using
     synthetic records.
  2. A per-level emitted-type-subset test: at level 0, the set of
     string_type values ``build_name_frame_bytes`` can emit is a subset of
     the reference profile's level-0 ``string_type_hist`` keys, and
     string_type=1 is never emitted at level 0 (docs/design/target-disc.md,
     harness/checks/vocab.py's hard rule).
  3. A decoded R level-0 name record, re-encoded, is byte-identical -- three
     records sampled from the Brisbane parcel (spot_checks.json), requires
     the real disc mounted at /run/media/codyh/464210-8480/; skips if not
     present (same convention as test_name_encoder.py).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.model import BoundingBox, NameRecord
from kiwiw.name import decode_name_frame
from kiwiw.synth import (
    build_name_frame_bytes,
    encode_name_record_type5_bytes,
    encode_name_record_type6_bytes,
)

_BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)

_PROFILE_PATH = Path(__file__).resolve().parent.parent / "refdata" / "profile" / "map.json"

ROOT = "/run/media/codyh/464210-8480"
ALLDATA_PATH = os.path.join(ROOT, "ALLDATA.KWI")
BRISBANE = (-27.4698, 153.0251)


# ---------------------------------------------------------------------------
# 1. Encode/decode round-trip for each supported type, synthetic records.
# ---------------------------------------------------------------------------

def test_type5_round_trip():
    rec = NameRecord(
        string_type=5, type_code=0x210, type_label="", priority=32,
        vertical=False, display_scale_flag=24, text="ALICE STREET",
        lat=-31.9, lon=115.9, angle_deg=-41, angle_flags=11,
    )
    encoded = encode_name_record_type5_bytes(rec, _BOUNDS)
    assert encoded != b""

    frame_bytes = build_name_frame_bytes([rec], _BOUNDS, level=0)
    frame = decode_name_frame(frame_bytes, _BOUNDS)
    assert len(frame.records) == 1
    got = frame.records[0]
    assert got.string_type == 5
    assert got.type_code == 0x210
    assert got.text == "ALICE STREET"
    assert got.angle_deg == -41
    assert got.angle_flags == 11
    assert got.priority == 32
    assert got.vertical is False
    assert got.display_scale_flag == 24
    assert got.lat == pytest.approx(-31.9, abs=1e-3)
    assert got.lon == pytest.approx(115.9, abs=1e-3)


def test_type6_round_trip():
    rec = NameRecord(
        string_type=6, type_code=0x141, type_label="", priority=32,
        vertical=False, display_scale_flag=28, text="",
        lat=-31.85, lon=116.0,
    )
    encoded = encode_name_record_type6_bytes(rec, _BOUNDS)
    assert encoded != b""

    frame_bytes = build_name_frame_bytes([rec], _BOUNDS, level=0)
    frame = decode_name_frame(frame_bytes, _BOUNDS)
    assert len(frame.records) == 1
    got = frame.records[0]
    assert got.string_type == 6
    assert got.type_code == 0x141
    assert got.text == ""
    assert got.priority == 32
    assert got.display_scale_flag == 28
    assert got.lat == pytest.approx(-31.85, abs=1e-3)
    assert got.lon == pytest.approx(116.0, abs=1e-3)


def test_type6_round_trip_with_text():
    rec = NameRecord(
        string_type=6, type_code=0x120, type_label="", priority=5,
        vertical=False, display_scale_flag=0, text="CITY BOTANIC GARDENS",
        lat=-31.9, lon=115.85,
    )
    frame_bytes = build_name_frame_bytes([rec], _BOUNDS, level=0)
    frame = decode_name_frame(frame_bytes, _BOUNDS)
    assert len(frame.records) == 1
    assert frame.records[0].text == "CITY BOTANIC GARDENS"
    assert frame.records[0].string_type == 6


def test_wrong_string_type_returns_empty():
    """The type-5/6 encoders are no-ops for a record of a different
    string_type (the caller, build_name_frame_bytes, is responsible for
    routing records to the right encoder by string_type)."""
    rec1 = NameRecord(string_type=1, type_code=0, type_label="", priority=0,
                       vertical=False, display_scale_flag=0, text="x")
    assert encode_name_record_type5_bytes(rec1, _BOUNDS) == b""
    assert encode_name_record_type6_bytes(rec1, _BOUNDS) == b""


# ---------------------------------------------------------------------------
# 2. Per-level emitted-type subset test against the reference profile.
# ---------------------------------------------------------------------------

def test_level0_emitted_types_subset_of_profile():
    """build_name_frame_bytes(level=0) may only emit string types that the
    reference profile's level-0 census actually contains, and must never
    emit string_type=1 at level 0 (harness/checks/vocab.py's hard rule;
    docs/design/target-disc.md)."""
    profile = json.loads(_PROFILE_PATH.read_text())
    level0_types = {int(k) for k in profile["levels"]["0"]["name"]["string_type_hist"]}
    assert level0_types == {1, 4, 5, 6}   # sanity-check the fixture itself

    records = [
        NameRecord(string_type=1, type_code=0, type_label="", priority=0,
                   vertical=False, display_scale_flag=0, text="type1 rec",
                   lat=-31.9, lon=115.9),
        NameRecord(string_type=4, type_code=0, type_label="", priority=0,
                   vertical=False, display_scale_flag=0, text="type4 rec",
                   lat=-31.9, lon=115.9),
        NameRecord(string_type=5, type_code=0x210, type_label="", priority=0,
                   vertical=False, display_scale_flag=0, text="type5 rec",
                   lat=-31.9, lon=115.9, angle_deg=0),
        NameRecord(string_type=6, type_code=0x120, type_label="", priority=0,
                   vertical=False, display_scale_flag=0, text="type6 rec",
                   lat=-31.9, lon=115.9),
    ]
    frame_bytes = build_name_frame_bytes(records, _BOUNDS, level=0)
    frame = decode_name_frame(frame_bytes, _BOUNDS)
    emitted_types = {r.string_type for r in frame.records}

    assert emitted_types.issubset(level0_types), (
        f"emitted {emitted_types} not subset of profile level-0 {level0_types}")
    assert 1 not in emitted_types, "string_type=1 must never be emitted at level 0"
    # type 4 is deliberately not implemented (see synth.py's
    # build_name_frame_bytes docstring) -- it too must not appear.
    assert 4 not in emitted_types
    assert emitted_types == {5, 6}


# ---------------------------------------------------------------------------
# 3. A decoded R level-0 name record, re-encoded, is byte-identical.
# ---------------------------------------------------------------------------

def _open_disc():
    if not os.path.exists(ALLDATA_PATH):
        print(f"SKIP: {ALLDATA_PATH} not present (disc not mounted)")
        return None
    from kiwiw.disc import AllData
    return AllData(ALLDATA_PATH)


def test_brisbane_level0_records_byte_identical_round_trip():
    disc = _open_disc()
    if disc is None:
        pytest.skip(f"{ALLDATA_PATH} not present (disc not mounted)")

    with disc:
        parcel = disc.find_parcel(*BRISBANE, level=0)
        assert parcel is not None and parcel.name is not None
        bounds = parcel.location.bounds

        type5_recs = [r for r in parcel.name.records if r.string_type == 5 and r.text]
        type6_recs = [r for r in parcel.name.records if r.string_type == 6]
        assert len(type5_recs) >= 2, "expected at least 2 type-5 records in Brisbane parcel"
        assert len(type6_recs) >= 1, "expected at least 1 type-6 record in Brisbane parcel"

        picked = type5_recs[:2] + type6_recs[:1]
        assert len(picked) == 3

        for rec in picked:
            if rec.string_type == 5:
                encoded = encode_name_record_type5_bytes(rec, bounds)
            else:
                encoded = encode_name_record_type6_bytes(rec, bounds)
            assert encoded == rec.raw_bytes, (
                f"string_type={rec.string_type} text={rec.text!r}: "
                f"re-encoded {encoded.hex()} != original {rec.raw_bytes.hex()}")
