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


# ---------------------------------------------------------------------------
# Brief 29: per-kind sub-frame budgets (escalation + final-tier trim)
# ---------------------------------------------------------------------------

from types import SimpleNamespace


def _measure_bg(level, ix, iy, bounds, content):
    fb = _encode(level, ix, iy, bounds, content)
    bgs = content.get("backgrounds") or []
    bg = synth.build_background_frame_bytes(bgs, bounds) if bgs else b""
    return fb, {"road": 0, "background": len(bg), "name": 0}


def test_kind_limit_triggers_escalation_when_total_fits():
    content = _quadrant_content(n_per_quadrant=20)
    whole, sizes = _measure_bg(LEVEL, 0, 0, _BOUNDS, content)
    threshold = len(whole) + 1000  # total fits comfortably
    plain = list(divide.plan_divisions(LEVEL, [(0, 0, content)], threshold, _encode))
    assert {r[2] for r in plain} == {0}
    limits = {"background": sizes["background"] - 1}
    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], threshold, _encode,
                                     kind_limits=limits, measure=_measure_bg))
    assert {r[2] for r in out} == {1}


def test_kind_limits_none_regression_and_requires_measure():
    content = _quadrant_content(n_per_quadrant=20)
    whole = _encode(LEVEL, 0, 0, _BOUNDS, content)
    a = list(divide.plan_divisions(LEVEL, [(0, 0, content)], len(whole) - 1, _encode))
    b = list(divide.plan_divisions(LEVEL, [(0, 0, content)], len(whole) - 1, _encode,
                                   kind_limits=None, measure=_measure_bg))
    assert a == b
    try:
        list(divide.plan_divisions(LEVEL, [(0, 0, content)], 10**6, _encode,
                                   kind_limits={"background": 1}))
    except ValueError:
        pass
    else:
        raise AssertionError("kind_limits without measure must raise")


def test_zero_or_absent_kind_not_budgeted():
    content = _quadrant_content(n_per_quadrant=5)
    whole = _encode(LEVEL, 0, 0, _BOUNDS, content)
    # road/name absent from limits -> only background checked; sizes for
    # absent kinds are 0 anyway.
    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], len(whole) + 10, _encode,
                                     kind_limits={"background": 10**6}, measure=_measure_bg))
    assert {r[2] for r in out} == {0}


def _name(text, st, i=0):
    return SimpleNamespace(text=text, string_type=st, lat=0.0, lon=0.0, idx=i)


def _fake_measure(per_item=10):
    def m(level, ix, iy, bounds, content):
        sizes = {"road": per_item * len(content.get("roads") or []),
                 "background": per_item * len(content.get("backgrounds") or []),
                 "name": per_item * len(content.get("names") or [])}
        return b"x" * sum(sizes.values()), sizes
    return m


def test_name_trim_priority_order_and_determinism():
    names = [_name("Dup", 1), _name("Dup", 1), _name("Shop", 6), _name("Queen Street", 5),
             _name("Town", 1), _name("Cafe", 6)]
    stats: dict = {}
    seen = []

    def m(level, ix, iy, bounds, content):
        seen.append(list(content.get("names") or []))
        return _fake_measure()(level, ix, iy, bounds, content)

    content = {"roads": [], "backgrounds": [], "names": names}
    fb, dropped = divide._trim_kinds(m, 0, 0, 0, _BOUNDS, content, {"name": 30}, stats)
    kept = [r for r in seen[-1]] if False else None
    order = divide._name_keep_order(names)
    assert [r.text for r in order] == ["Queen Street", "Dup", "Town", "Shop", "Cafe", "Dup"]
    assert dropped == 3 and len(fb) == 30
    assert stats["dropped"] == {"name": 3}
    # deterministic
    fb2, d2 = divide._trim_kinds(_fake_measure(), 0, 0, 0, _BOUNDS, content, {"name": 30}, {})
    assert (fb2, d2) == (fb, dropped)


def test_background_trim_keeps_large_features():
    def shp(size):
        return BackgroundShape(shape_class=2, type_code=0x100, type_label="", n_coords=3,
                               mult_const=1, underground=False, pen_up=False,
                               coords=[(0, 0), (size, 0), (0, size)])
    shapes = [shp(0.001), shp(0.5), shp(0.01)]
    order = divide._bg_keep_order(shapes)
    assert [s.coords[1][0] for s in order] == [0.5, 0.01, 0.001]


def test_road_trim_order_and_pinning():
    def rd(rt, n, way, ordn=0):
        return SimpleNamespace(road_type=rt, points=[(0, 0)] * n, osm_way_id=way, ordinal=ordn)
    roads = [rd(7, 5, 1), rd(12, 2, 2), rd(7, 5, 9), rd(4, 3, 3), rd(0, 1, 4)]
    ordered, pinned = divide._road_keep_order(2, roads)
    assert pinned == 2
    assert [r.osm_way_id for r in ordered] == [2, 4, 3, 1, 9]  # ties -> highest way id last
    _o, p0 = divide._road_keep_order(0, roads)
    assert p0 == 0
    # trim to zero budget still keeps the pinned links
    content = {"roads": roads, "backgrounds": [], "names": []}
    fb, dropped = divide._trim_kinds(_fake_measure(), 2, 0, 0, _BOUNDS, content,
                                     {"road": 0}, None)
    assert dropped == 3


# ---------------------------------------------------------------------------
# Brief 32: per-kind budgets in the hard-ceiling fallback; road-name halo
# ---------------------------------------------------------------------------

def _ceiling_measure(max_items=100, per_item=10):
    """Fake measure that raises ValueError (the format's hard ceiling) when
    the total item count exceeds `max_items`."""
    base = _fake_measure(per_item)

    def m(level, ix, iy, bounds, content):
        n = sum(len(content.get(k) or []) for k in ("roads", "backgrounds", "names"))
        if n > max_items:
            raise ValueError("over ceiling")
        return base(level, ix, iy, bounds, content)
    return m


def _rd(rt, n, way):
    return SimpleNamespace(road_type=rt, points=[(0, 0)] * n, osm_way_id=way, ordinal=0)


def test_shrink_priority_applies_kind_budgets_and_priority():
    roads = [_rd(7, 5, i) for i in range(60)] + [_rd(4, 3, 100)]
    bgs = [SimpleNamespace(coords=[(0, 0), (i + 1, 0), (0, i + 1)]) for i in range(80)]
    names = ([_name("Queen Street", 5)] + [_name(f"Shop{i}", 6) for i in range(30)]
             + [_name("Queen Street", 5)])
    content = {"roads": roads, "backgrounds": bgs, "names": names}
    limits = {"road": 200, "background": 300, "name": 250}  # 20 / 30 / 25 items
    stats: dict = {}
    fb, sizes = divide._shrink_priority(_ceiling_measure(), 0, 0, 0, _BOUNDS,
                                        content, limits, stats)
    assert sizes["road"] <= 200 and sizes["background"] <= 300 and sizes["name"] <= 250
    # 20+30+25 = 75 <= 100 ceiling: budgets alone suffice; nothing more dropped
    assert (sizes["road"], sizes["background"], sizes["name"]) == (200, 300, 250)
    assert stats["dropped"] == {"road": 41, "background": 50, "name": 7}
    # road names survive: the kept names are the first 25 in priority order
    kept = divide._name_keep_order(names)[:25]
    assert [r.text for r in kept][:2] == ["Queen Street", "Shop0"] or kept[0].text == "Queen Street"
    # deterministic
    fb2, s2 = divide._shrink_priority(_ceiling_measure(), 0, 0, 0, _BOUNDS,
                                      content, limits, None)
    assert (fb2, s2) == (fb, sizes)


def test_shrink_priority_ceiling_drops_roads_before_names():
    roads = [_rd(7, 5, i) for i in range(50)]
    bgs = [SimpleNamespace(coords=[(0, 0), (1, 0), (0, 1)]) for _ in range(40)]
    names = [_name(f"R{i} Street", 5) for i in range(30)]
    content = {"roads": roads, "backgrounds": bgs, "names": names}
    # budgets sum to 120 items > ceiling of 100
    limits = {"road": 500, "background": 400, "name": 300}
    _fb, sizes = divide._shrink_priority(_ceiling_measure(100), 0, 0, 0, _BOUNDS,
                                         content, limits, None)
    assert sizes["name"] == 300 and sizes["background"] == 400  # 30 + 40 kept
    assert sizes["road"] == 300  # roads absorbed the overshoot: 100 - 70 items


def test_hard_ceiling_path_uses_kind_budgets_in_plan_divisions(monkeypatch):
    content = _quadrant_content(n_per_quadrant=20)
    calls = []
    real = divide._shrink_priority

    def spy(*a, **k):
        calls.append(a[3:5])
        return real(*a, **k)
    monkeypatch.setattr(divide, "_shrink_priority", spy)

    def m(level, ix, iy, bounds, c):
        n = len(c.get("backgrounds") or [])
        if n > 10:  # hard ceiling: every tier holds 20 per sub-cell
            raise ValueError("ceiling")
        return b"y" * (10 * n), {"road": 0, "background": 10 * n, "name": 0}

    stats: dict = {}
    out = list(divide.plan_divisions(LEVEL, [(0, 0, content)], 10**6, _encode,
                                     kind_limits={"background": 50}, measure=m,
                                     trim_stats=stats))
    assert {r[2] for r in out} == {2} and len(out) == 4 and len(calls) == 4
    assert all(len(r[5]) == 50 for r in out)  # 5 items each: kind budget honoured
    assert stats["dropped"] == {"background": 60}


def test_name_halo_adds_neighbour_road_names_within_budget():
    b = BoundingBox(lat_lo=0.0, lat_hi=1.0, lon_lo=0.0, lon_hi=1.0)

    def nm(text, st, lat, lon):
        return SimpleNamespace(text=text, string_type=st, lat=lat, lon=lon)
    sub = [nm("Here Street", 5, 0.5, 0.5)]
    parent = sub + [nm("Hay Street", 5, 1.3, 0.5),        # within 1 sub-cell: halo
                    nm("Far Street", 5, 3.0, 0.5),        # too far
                    nm("Cafe", 6, 1.2, 0.5),              # not a road name
                    nm("Here Street", 5, 1.1, 0.5),       # text already present
                    nm("Hay Street", 5, 1.6, 0.5)]        # farther duplicate
    cands = divide._halo_candidates(parent, sub, b)
    assert [c.text for c in cands] == ["Hay Street"]
    assert cands[0].lat < 1.0 and (cands[0].lat, cands[0].lon) == (0.99, 0.5)
    content = {"roads": [], "backgrounds": [], "names": sub}
    m = _fake_measure()
    fb0 = m(0, 0, 0, b, content)[0]
    fb, n = divide._add_name_halo(m, 0, 0, 0, b, content, parent, {"name": 20}, 10**6, fb0)
    assert n == 1 and len(fb) == 20
    fb, n = divide._add_name_halo(m, 0, 0, 0, b, content, parent, {"name": 10}, 10**6, fb0)
    assert n == 0 and fb == fb0  # never exceeds the name budget
