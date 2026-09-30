"""Name records through E2 (plan 03, 3C-10; Contract T layer (a)).

These replace `test_name_encode.py`, whose cases tested the Python name
encoders in the old Python synthesizer. Here a fixture spool holds name records,
E1 then E2 (the C build kernel, via `fixtures/harness/e2_fixture.py`) emit the
Map Frame, and `kiwiw.name.decode_name_frame` (through `boundary.decode_frame`)
reads them back. The oracle is the Python decoder, the reference profile's
level-0 census and, where the reference disc is mounted, R's own bytes -- never
a Python encoder.

Coverage, per supported type, matches the cases it replaces:
  1. Round trip for string types 5 (with angle) and 6 (with and without text).
  2. A record of a type E2 does not emit (1, 4) is dropped, never mangled.
  3. The set of types emitted at level 0 is a subset of the reference
     profile's level-0 `string_type_hist`, never 1 or 4.
  4. Three records sampled from R's Brisbane parcel, run through E2, come back
     with R's exact record bytes (needs the disc at /run/media/...; skips if
     absent, as `test_name_encoder.py` does).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "harness"))

import boundary
import e2_fixture
from kiwiw import mesh
from kiwiw.model import NameRecord

_PROFILE_PATH = Path(__file__).resolve().parent.parent / "refdata" / "profile" / "map.json"

ROOT = "/run/media/codyh/464210-8480"
ALLDATA_PATH = os.path.join(ROOT, "ALLDATA.KWI")
BRISBANE = (-27.4698, 153.0251)

LEVEL = 0
IX, IY = 1780, 814                      # a Perth level-0 cell
_BOUNDS = e2_fixture.cell_bounds(LEVEL, IX, IY)


def _at(fx: float, fy: float) -> tuple[float, float]:
    """(lat, lon) at fraction (fy, fx) of the cell."""
    return (_BOUNDS.lat_lo + fy * (_BOUNDS.lat_hi - _BOUNDS.lat_lo),
            _BOUNDS.lon_lo + fx * (_BOUNDS.lon_hi - _BOUNDS.lon_lo))


def _rec(string_type: int, text: str, at=(0.5, 0.5), **kw) -> NameRecord:
    lat, lon = _at(*at)
    base = dict(type_code=0, type_label="", priority=0, vertical=False,
                display_scale_flag=0)
    base.update(kw)
    return NameRecord(string_type=string_type, text=text, lat=lat, lon=lon, **base)


def _names_through_e2(records, bounds=None, ix=IX, iy=IY):
    """Decode the name records of the one cell E2 emits for `records`."""
    with tempfile.TemporaryDirectory() as d:
        frames = e2_fixture.e2_frames(d, LEVEL, {(ix, iy): {"names": list(records)}})
    b = bounds or e2_fixture.cell_bounds(LEVEL, ix, iy)
    return boundary.decode_frame(frames[(ix, iy)], b).name.records


# ---------------------------------------------------------------------------
# 1. Round trip for each supported type.
# ---------------------------------------------------------------------------

def test_type5_round_trip():
    lat, lon = _at(0.25, 0.75)
    rec = NameRecord(
        string_type=5, type_code=0x210, type_label="", priority=32,
        vertical=False, display_scale_flag=24, text="ALICE STREET",
        lat=lat, lon=lon, angle_deg=-41, angle_flags=11)
    records = _names_through_e2([rec])
    assert len(records) == 1
    got = records[0]
    assert got.string_type == 5
    assert got.type_code == 0x210
    assert got.text == "ALICE STREET"
    assert got.angle_deg == -41
    assert got.angle_flags == 11
    assert got.priority == 32
    assert got.vertical is False
    assert got.display_scale_flag == 24
    assert got.lat == pytest.approx(lat, abs=1e-3)
    assert got.lon == pytest.approx(lon, abs=1e-3)


def test_type6_round_trip():
    lat, lon = _at(0.75, 0.25)
    rec = NameRecord(
        string_type=6, type_code=0x141, type_label="", priority=32,
        vertical=False, display_scale_flag=28, text="", lat=lat, lon=lon)
    records = _names_through_e2([rec])
    assert len(records) == 1
    got = records[0]
    assert got.string_type == 6
    assert got.type_code == 0x141
    assert got.text == ""
    assert got.priority == 32
    assert got.display_scale_flag == 28
    assert got.lat == pytest.approx(lat, abs=1e-3)
    assert got.lon == pytest.approx(lon, abs=1e-3)


def test_type6_round_trip_with_text():
    rec = _rec(6, "CITY BOTANIC GARDENS", type_code=0x120, priority=5)
    records = _names_through_e2([rec])
    assert len(records) == 1
    assert records[0].text == "CITY BOTANIC GARDENS"
    assert records[0].string_type == 6


# ---------------------------------------------------------------------------
# 2. A type E2 does not emit is dropped.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("string_type", (1, 4))
def test_unsupported_string_type_is_dropped(string_type):
    """Replaces `test_wrong_string_type_returns_empty`: with the type-5/6
    encoders internal to E2, the observable contract is that a record of any
    other type puts nothing in the frame."""
    assert _names_through_e2([_rec(string_type, "x")]) == []


# ---------------------------------------------------------------------------
# 3. Per-level emitted-type subset against the reference profile.
# ---------------------------------------------------------------------------

def test_level0_emitted_types_subset_of_profile():
    """E2 at level 0 may only emit string types that the reference profile's
    level-0 census actually contains, and never string_type=1
    (`harness/checks/vocab.py`'s hard rule; `docs/design/target-disc.md`).
    Type 4 is deliberately not implemented either."""
    profile = json.loads(_PROFILE_PATH.read_text())
    level0_types = {int(k) for k in profile["levels"]["0"]["name"]["string_type_hist"]}
    assert level0_types == {1, 4, 5, 6}   # sanity-check the fixture itself

    records = [
        _rec(1, "type1 rec", (0.2, 0.2)),
        _rec(4, "type4 rec", (0.4, 0.4)),
        _rec(5, "type5 rec", (0.6, 0.6), type_code=0x210, angle_deg=0),
        _rec(6, "type6 rec", (0.8, 0.8), type_code=0x120),
    ]
    emitted_types = {r.string_type for r in _names_through_e2(records)}

    assert emitted_types.issubset(level0_types), (
        f"emitted {emitted_types} not subset of profile level-0 {level0_types}")
    assert 1 not in emitted_types, "string_type=1 must never be emitted at level 0"
    assert 4 not in emitted_types
    assert emitted_types == {5, 6}


# ---------------------------------------------------------------------------
# 4. R's level-0 name records, through E2, keep R's bytes.
# ---------------------------------------------------------------------------

def test_brisbane_level0_records_byte_identical_through_e2():
    if not os.path.exists(ALLDATA_PATH):
        pytest.skip(f"{ALLDATA_PATH} not present (disc not mounted)")
    from kiwiw.disc import AllData

    with AllData(ALLDATA_PATH) as disc:
        parcel = disc.find_parcel(*BRISBANE, level=0)
        assert parcel is not None and parcel.name is not None
        r_bounds = parcel.location.bounds  # ranged decode frame (disc.find_parcel)

        type5_recs = [r for r in parcel.name.records if r.string_type == 5 and r.text]
        type6_recs = [r for r in parcel.name.records if r.string_type == 6]
        assert len(type5_recs) >= 2, "expected at least 2 type-5 records in Brisbane parcel"
        assert len(type6_recs) >= 1, "expected at least 1 type-6 record in Brisbane parcel"
        picked = type5_recs[:2] + type6_recs[:1]

    # The spool cell is the level-0 grid cell holding R's parcel; E2 encodes
    # against the same grid, so its bounds must be R's.
    grid = mesh.CellGrid.from_reference(0)
    ix, iy = mesh.assign_to_parcel(*BRISBANE, grid)
    cell = e2_fixture.cell_bounds(0, ix, iy)
    assert (cell.lat_lo, cell.lat_hi) == pytest.approx((r_bounds.lat_lo, r_bounds.lat_hi))
    assert (cell.lon_lo, cell.lon_hi) == pytest.approx((r_bounds.lon_lo, r_bounds.lon_hi))

    got = _names_through_e2(picked, bounds=r_bounds, ix=ix, iy=iy)
    by_key = {(g.string_type, g.type_code, g.text): g for g in got}
    for rec in picked:
        g = by_key[(rec.string_type, rec.type_code, rec.text)]
        assert g.raw_bytes == rec.raw_bytes, (
            f"string_type={rec.string_type} text={rec.text!r}: "
            f"E2 emitted {g.raw_bytes.hex()} != R's {rec.raw_bytes.hex()}")
