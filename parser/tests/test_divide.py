"""Tests for `kiwiw.divide` (WP1 unit 13: divided parcels, types 1..3):

- an oversize synthetic level-0 parcel splits into type-1 (2x2);
- `AllData.find_parcel()` on a disc built with the `divided` output
  returns the sub-parcel containing a probe coordinate;
- a parcel under `threshold_bytes` stays type 0;
- harness `decode`/`pointers` pass on the resulting disc;
- a synthetic parcel still oversize after 4x4 (type-2) division is left as
  the largest available division and does not crash the writer/harness
  (mirrors the fixture's real level-12 case -- see this unit's report).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import alldata_writer as aw
from kiwiw import divide
from kiwiw import synth
from kiwiw.disc import AllData
from kiwiw.grid import ReferenceGrid
from kiwiw.model import BackgroundShape, BoundingBox
from osm_to_parcel_geometry import TileGrid, parcel_bounds

from harness.checks import decode as decode_checks
from harness.context import Context

LEVEL = 0
_IX, _IY = 0, 0
# `plan_divisions()` derives a parcel's bounds itself from (level, ix, iy)
# via the checked-in reference grid (not passed by the caller) -- so test
# content must be built against the *real* bounds for (LEVEL, _IX, _IY),
# not an arbitrary hand-picked box, or content ends up geographically
# outside the cell `plan_divisions()` actually re-tiles against.
_BOUNDS = parcel_bounds(_IX, _IY, TileGrid.from_reference(LEVEL))


def _encode(level: int, ix: int, iy: int, bounds: BoundingBox, content: dict) -> bytes:
    """Minimal stand-in for `build_alldata.py`'s `_encode_one()`: only
    backgrounds are exercised here (roads/names are exercised by the wider
    round-trip suite; this module's own content re-tiling is what's under
    test)."""
    bgs = content.get("backgrounds") or []
    bg_bytes = synth.build_background_frame_bytes(bgs, bounds) if bgs else None
    llpid = (bounds.lat_lo, bounds.lon_lo)
    llcode = (ix % 256, iy % 256)
    return synth.build_map_frame_bytes(level, llpid, llcode, None, bg_bytes, None)


def _point_shape(lat: float, lon: float, type_code: int) -> BackgroundShape:
    return BackgroundShape(
        shape_class=0, type_code=type_code, type_label="", n_coords=0,
        mult_const=1, underground=False, pen_up=False, coords=[(lat, lon)],
    )


def _quadrant_content(n_per_quadrant: int) -> dict:
    """One content dict for `_BOUNDS` with `n_per_quadrant` distinct point
    shapes placed in each of the four quadrants (so a 2x2 sub-grid split
    puts a roughly even share of content in each sub-cell)."""
    lat_mid = (_BOUNDS.lat_lo + _BOUNDS.lat_hi) / 2
    lon_mid = (_BOUNDS.lon_lo + _BOUNDS.lon_hi) / 2
    offsets = [
        (_BOUNDS.lat_lo + (lat_mid - _BOUNDS.lat_lo) * 0.5,
         _BOUNDS.lon_lo + (lon_mid - _BOUNDS.lon_lo) * 0.5),
        (_BOUNDS.lat_lo + (lat_mid - _BOUNDS.lat_lo) * 0.5,
         lon_mid + (_BOUNDS.lon_hi - lon_mid) * 0.5),
        (lat_mid + (_BOUNDS.lat_hi - lat_mid) * 0.5,
         _BOUNDS.lon_lo + (lon_mid - _BOUNDS.lon_lo) * 0.5),
        (lat_mid + (_BOUNDS.lat_hi - lat_mid) * 0.5,
         lon_mid + (_BOUNDS.lon_hi - lon_mid) * 0.5),
    ]
    shapes = []
    type_code = 0x100
    for lat, lon in offsets:
        for _ in range(n_per_quadrant):
            shapes.append(_point_shape(lat, lon, type_code))
            type_code += 1
    return {"roads": [], "backgrounds": shapes, "names": []}


# ---------------------------------------------------------------------------
# 1. Oversize parcel splits into type-1 (2x2)
# ---------------------------------------------------------------------------

def test_oversize_parcel_splits_type1():
    content = _quadrant_content(n_per_quadrant=20)
    whole_bytes = _encode(LEVEL, 0, 0, _BOUNDS, content)
    threshold = len(whole_bytes) - 1  # guarantees the whole frame is oversize

    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], threshold, _encode))

    assert out, "plan_divisions() yielded nothing"
    types = {row[2] for row in out}
    assert types == {1}, f"expected only type-1 sub-frames, got types {types}"
    sub_positions = {(row[3], row[4]) for row in out}
    assert sub_positions <= {(0, 0), (1, 0), (0, 1), (1, 1)}
    assert len(sub_positions) > 1, "content should have landed in more than one quadrant"
    for *_rest, frame_bytes in out:
        assert len(frame_bytes) <= threshold, (
            "a type-1 sub-frame is still oversize after splitting a mild "
            "overshoot -- threshold/content chosen too aggressively for this test")


# ---------------------------------------------------------------------------
# 2. find_parcel() on the built disc resolves to the right sub-parcel
# ---------------------------------------------------------------------------

def test_find_parcel_resolves_divided_subparcel(tmp_path):
    content = _quadrant_content(n_per_quadrant=20)
    whole_bytes = _encode(LEVEL, 0, 0, _BOUNDS, content)
    threshold = len(whole_bytes) - 1

    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], threshold, _encode))
    assert {row[2] for row in out} == {1}

    grid = ReferenceGrid.load()
    levels = {LEVEL: aw.LevelBuild(level=LEVEL, parcels=[])}
    out_path = tmp_path / "test.kwi"
    aw.build_alldata_kwi(levels, grid, disk_title="TEST", out_path=str(out_path),
                          divided={LEVEL: out})

    # Probe deep inside the top-right quadrant (sub_ix=1, sub_iy=1): a point
    # clearly inside that sub-cell, not near any boundary.
    lat_mid = (_BOUNDS.lat_lo + _BOUNDS.lat_hi) / 2
    lon_mid = (_BOUNDS.lon_lo + _BOUNDS.lon_hi) / 2
    probe_lat = lat_mid + (_BOUNDS.lat_hi - lat_mid) * 0.5
    probe_lon = lon_mid + (_BOUNDS.lon_hi - lon_mid) * 0.5

    with AllData(str(out_path)) as ad:
        parcel = ad.find_parcel(probe_lat, probe_lon, level=LEVEL)
        assert parcel is not None
        assert parcel.background is not None
        # Every shape placed in this parcel's content came from the
        # top-right quadrant's type_code range [0x100+60, 0x100+80) (4
        # quadrants x 20 shapes/quadrant, this one is quadrant index 3).
        got_codes = {s.type_code for s in parcel.background.shapes}
        assert got_codes, "resolved sub-parcel has no background shapes"
        assert got_codes <= set(range(0x100 + 60, 0x100 + 80)), (
            f"find_parcel() returned the wrong sub-parcel: got type_codes "
            f"{sorted(got_codes)}, expected the top-right quadrant's range")


# ---------------------------------------------------------------------------
# 3. Under-threshold parcel stays type 0
# ---------------------------------------------------------------------------

def test_under_threshold_stays_type0():
    content = _quadrant_content(n_per_quadrant=1)
    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], 10_000_000, _encode))
    assert len(out) == 1
    ix, iy, ptype, sub_ix, sub_iy, frame_bytes = out[0]
    assert (ix, iy, ptype, sub_ix, sub_iy) == (0, 0, 0, 0, 0)
    assert frame_bytes == _encode(LEVEL, 0, 0, _BOUNDS, content)


# ---------------------------------------------------------------------------
# 4. harness decode/pointers pass on the divided-parcel disc
# ---------------------------------------------------------------------------

def test_harness_decode_pointers_pass_on_divided_disc(tmp_path):
    content = _quadrant_content(n_per_quadrant=20)
    whole_bytes = _encode(LEVEL, 0, 0, _BOUNDS, content)
    threshold = len(whole_bytes) - 1
    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], threshold, _encode))

    grid = ReferenceGrid.load()
    levels = {LEVEL: aw.LevelBuild(level=LEVEL, parcels=[])}
    out_path = tmp_path / "test.kwi"
    aw.build_alldata_kwi(levels, grid, disk_title="TEST", out_path=str(out_path),
                          divided={LEVEL: out})

    ctx = Context(reference=None, generated=str(out_path), config={"layers_present": ["map"]})
    decode_result = decode_checks._run_decode(ctx)
    assert decode_result.status == "PASS", decode_result.message
    pointers_result = decode_checks._run_pointers(ctx)
    assert pointers_result.status == "PASS", pointers_result.message


# ---------------------------------------------------------------------------
# 5. Still oversize after 4x4 (type-2): left as the largest division, no crash
# ---------------------------------------------------------------------------

def test_oversize_after_type2_does_not_crash():
    content = _quadrant_content(n_per_quadrant=1)
    # Impossible threshold: even a single point-shape Map Frame is well
    # over 1 byte, so this forces escalation all the way to type 2 and
    # still leaves every sub-frame oversize -- mirrors the fixture's real
    # level-12 case (Amendment: "left as the largest available division
    # and does not crash the writer").
    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], 1, _encode))

    assert out, "plan_divisions() yielded nothing"
    types = {row[2] for row in out}
    assert types == {2}, f"expected escalation to type-2, got types {types}"
    assert any(len(row[-1]) > 1 for row in out), (
        "expected at least one still-oversize sub-frame (that's the point "
        "of this test) -- got everything under the impossible 1-byte threshold")

    # Also must not crash the writer: build a disc from this output.
    grid = ReferenceGrid.load()
    levels = {LEVEL: aw.LevelBuild(level=LEVEL, parcels=[])}
    data = aw.build_alldata_kwi(levels, grid, disk_title="TEST", divided={LEVEL: out})
    assert isinstance(data, (bytes, bytearray))


# ---------------------------------------------------------------------------
# 6. `_shrink_to_fit()` drop order: names/backgrounds preserved over roads
# ---------------------------------------------------------------------------

def _size_capped_encode(max_items: int):
    """A fake `encode()` whose only notion of "size" is the combined
    road+background+name item count in `content` -- returns a byte string
    whose length equals that count if <= `max_items`, else raises
    `ValueError` (mirrors `synth.build_map_frame_bytes()`'s hard-ceiling
    `ValueError` on oversize content, without needing real synth-encodable
    road/background/name objects -- `_shrink_to_fit()` only ever slices the
    content lists, it never inspects the items themselves)."""
    def _encode_capped(level, ix, iy, bounds, content):
        n = (len(content.get("roads") or [])
             + len(content.get("backgrounds") or [])
             + len(content.get("names") or []))
        if n > max_items:
            raise ValueError(f"{n} items exceeds cap {max_items}")
        return b"x" * max(n, 1)
    return _encode_capped


def test_shrink_to_fit_preserves_names_and_backgrounds_over_roads():
    # 30 roads (the dominant class, as in the real Sydney/Melbourne
    # road-chain-dominated cells brief 22 traced this to), plus a handful of
    # backgrounds and names -- budget only large enough for the
    # non-road content plus a few roads.
    content = {
        "roads": [f"road{i}" for i in range(30)],
        "backgrounds": [f"bg{i}" for i in range(3)],
        "names": [f"name{i}" for i in range(2)],
    }
    encode = _size_capped_encode(max_items=10)

    frame_bytes, dropped = divide._shrink_to_fit(
        encode, LEVEL, _IX, _IY, _BOUNDS, content)

    assert dropped == 30 + 3 + 2 - 10
    # Re-derive what was kept the same way `_shrink_to_fit()` does, to
    # confirm names and backgrounds both survived in full and only roads
    # were truncated -- this is the brief-22 fix: previously roads were
    # preserved first and names were the first thing dropped to zero.
    assert len(frame_bytes) == 10
    # With keep=10: all 2 names + all 3 backgrounds + 5 of 30 roads.
    # Directly exercise _attempt-equivalent slicing via a second capped
    # encode that only succeeds when names/backgrounds are intact.
    def _assert_names_bgs_intact(level, ix, iy, bounds, c):
        assert len(c.get("names") or []) == 2, "a name was dropped before roads"
        assert len(c.get("backgrounds") or []) == 3, "a background was dropped before all roads"
        n = len(c.get("roads") or []) + len(c.get("backgrounds") or []) + len(c.get("names") or [])
        if n > 10:
            raise ValueError("still oversize")
        return b"x" * n
    frame_bytes2, dropped2 = divide._shrink_to_fit(
        _assert_names_bgs_intact, LEVEL, _IX, _IY, _BOUNDS, content)
    assert dropped2 == 25  # only roads dropped (30 -> 5)
