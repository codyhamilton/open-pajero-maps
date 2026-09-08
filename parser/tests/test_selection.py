"""Tests for `parser/kiwiw/selection.py` and `parser/refdata/selection.json`.

Reads the checked-in table (not literals) per brief 14: "the filter admits
motorways at 12 and residential only at 0/2 (or whatever the table says --
the test reads the table)". This project's calibrated table (see
`selection.json`'s `_calibration_note` fields and this unit's report)
admits *no* road classes at level 12 -- R's own census
(`parser/refdata/profile/map.json`, `levels."12".road.road_type_hist`) has
zero road links there -- so the tests below assert against the table's
actual content, not the brief's illustrative (and, for level 12,
superseded) example.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import selection  # noqa: E402

SELECTION_PATH = (
    Path(__file__).resolve().parent.parent / "refdata" / "selection.json"
)
PROFILE_PATH = (
    Path(__file__).resolve().parent.parent / "refdata" / "profile" / "map.json"
)

EVEN_LEVELS = (0, 2, 4, 6, 8, 10, 12)


def _raw_table() -> dict:
    with open(SELECTION_PATH) as f:
        return json.load(f)


def _table() -> selection.SelectionTable:
    return selection.SelectionTable.load(SELECTION_PATH)


def _rule_highway(raw: dict, level: int) -> set:
    for rule in raw["rules"]:
        if rule["levels"] == level:
            return set(rule.get("highway", []))
    return set()


def _rule_place(raw: dict, level: int) -> set:
    for rule in raw["rules"]:
        if rule["levels"] == level:
            return set(rule.get("place", []))
    return set()


# --- loading / validation ---------------------------------------------------


def test_checked_in_table_loads_without_error():
    _table()


def test_levels_cover_every_even_level_exactly_once():
    raw = _raw_table()
    covered: set = set()
    for lo, hi in raw["levels"]:
        for lv in EVEN_LEVELS:
            if lo <= lv <= hi:
                assert lv not in covered, f"level {lv} covered by more than one range"
                covered.add(lv)
    assert covered == set(EVEN_LEVELS)


def test_every_range_has_exactly_one_rule():
    raw = _raw_table()
    range_los = {lo for lo, _ in raw["levels"]}
    rule_los = [r["levels"] for r in raw["rules"]]
    assert set(rule_los) == range_los
    assert len(rule_los) == len(set(rule_los)), "duplicate rule for one range"


def test_overlapping_ranges_rejected():
    bad = {
        "levels": [[0, 4], [2, 8]],
        "rules": [{"levels": 0, "highway": []}, {"levels": 2, "highway": []}],
    }
    tmp = Path(__file__).resolve().parent / "_tmp_bad_selection.json"
    tmp.write_text(json.dumps(bad))
    try:
        with pytest.raises(selection.SelectionError):
            selection.SelectionTable.load(tmp)
    finally:
        tmp.unlink()


def test_incomplete_coverage_rejected():
    bad = {
        "levels": [[0, 0], [2, 8]],
        "rules": [{"levels": 0, "highway": []}, {"levels": 2, "highway": []}],
    }
    tmp = Path(__file__).resolve().parent / "_tmp_incomplete_selection.json"
    tmp.write_text(json.dumps(bad))
    try:
        with pytest.raises(selection.SelectionError):
            selection.SelectionTable.load(tmp)
    finally:
        tmp.unlink()


# --- level_filter behaviour, read from the table ----------------------------


@pytest.mark.parametrize("level", EVEN_LEVELS)
def test_highway_admission_matches_table(level):
    table = _table()
    raw = _raw_table()
    admitted = _rule_highway(raw, level)
    # Every admitted class passes.
    for hw in admitted:
        assert table.level_filter(level, {"highway": hw}) is True
    # A highway value that is never admitted at any level is rejected
    # everywhere (footway is excluded from every level's table by
    # construction: it is not in osm_to_parcel_geometry.ROADS in the first
    # place, and is not listed in any rule here either).
    assert table.level_filter(level, {"highway": "footway"}) is False


def test_level_12_admits_no_highway_class():
    """R's census has zero road links at level 12 (profile map.json,
    levels."12".road.road_type_hist == {}); the calibrated table matches
    that by admitting no highway class there -- this is the amendment's
    load-bearing case (an unthinned level 12 Map Frame measured
    39,555,559 bytes on the Perth fixture, ~300x the u16 ceiling)."""
    table = _table()
    raw = _raw_table()
    assert _rule_highway(raw, 12) == set()
    assert table.level_filter(12, {"highway": "motorway"}) is False
    assert table.level_filter(12, {"highway": "residential"}) is False


def test_level_0_admits_a_broad_highway_set():
    table = _table()
    raw = _raw_table()
    admitted = _rule_highway(raw, 0)
    assert "residential" in admitted
    assert table.level_filter(0, {"highway": "residential"}) is True


def test_background_admission_is_any_of_predicates():
    table = _table()
    raw = _raw_table()
    for rule in raw["rules"]:
        level = rule["levels"]
        preds = rule.get("background", [])
        for pred in preds:
            tags = {pred["key"]: pred["value"]}
            assert table.level_filter(level, tags) is True
        if rule.get("background_all"):
            # background_all short-circuits the predicate list entirely
            # (mirrors parser/refdata/vocab/bg_type.json's level-0 catch-
            # all `{"match": {}, "value": 288}` rule -- any non-road,
            # non-place tag set is admitted). Covered by
            # test_background_all_admits_any_non_road_tags below instead.
            continue
        # A tag combination matching none of the predicates (and not a
        # highway/place tag) is rejected.
        assert table.level_filter(level, {"amenity": "definitely_not_matched"}) is False


def test_background_all_admits_any_non_road_tags():
    """Level 0's rule sets background_all=true because
    parser/refdata/vocab/bg_type.json declares a catch-all level-0 rule
    (`{"match": {}, "value": 288}`) -- every non-road, non-place way is
    some background type there regardless of its tags, so this level's
    selection admits anything that reaches the background branch."""
    raw = _raw_table()
    table = _table()
    level0 = next(r for r in raw["rules"] if r["levels"] == 0)
    assert level0.get("background_all") is True
    assert table.level_filter(0, {"amenity": "anything_at_all"}) is True
    assert table.level_filter(0, {}) is True
    # Still gated correctly ahead of background_all: a highway tag not in
    # level 0's admitted set is rejected via the highway branch, not
    # swallowed by background_all.
    assert table.level_filter(0, {"highway": "footway"}) is False


def test_place_admission_matches_table():
    table = _table()
    raw = _raw_table()
    for level in EVEN_LEVELS:
        admitted = _rule_place(raw, level)
        for p in admitted:
            assert table.level_filter(level, {"place": p}) is True
        assert table.level_filter(level, {"place": "definitely_not_a_real_place_value"}) is False


def test_highway_tag_takes_precedence_over_background_and_place():
    """A tags dict with both `highway` and `place`/background-matching keys
    is classified as a road candidate (mirrors the extractor's own
    `_handle_way`, where `is_road = hw in ROADS` is decided before the
    background branch runs)."""
    table = _table()
    # motorway is admitted at level 0; natural=water is not a road tag, so
    # combining them should still resolve via the highway branch.
    assert table.level_filter(0, {"highway": "motorway", "natural": "water"}) is True


def test_out_of_range_level_admits_nothing():
    table = _table()
    assert table.level_filter(99, {"highway": "motorway"}) is False


# --- min_length_m: recorded, pure-function only (not wired into the
# extractor -- see selection.py's module docstring) -------------------------


def test_min_length_m_present_for_levels_4_and_up():
    raw = _raw_table()
    min_length = raw["min_length_m"]
    for level in (4, 6, 8, 10, 12):
        assert str(level) in min_length
        assert min_length[str(level)] > 0


def test_meets_length_threshold_pure_function():
    table = _table()
    assert table.meets_length_threshold(6, table.min_length_m(6)) is True
    assert table.meets_length_threshold(6, table.min_length_m(6) - 1) is False
    # Levels 0/2 have no threshold configured (0.0): everything passes.
    assert table.meets_length_threshold(0, 0.0) is True


def test_module_level_wrappers_match_default_table():
    table = _table()
    assert selection.level_filter(0, {"highway": "residential"}) == \
        table.level_filter(0, {"highway": "residential"})
    assert selection.meets_length_threshold(8, 1000.0) == \
        table.meets_length_threshold(8, 1000.0)


# --- coverage against the census: every admitted highway class corresponds
# to a road class R's own profile shows nonzero counts for at that level's
# range, where a mapping exists (best-effort cross-check, not exhaustive
# vocabulary coverage -- that is unit 08's test_vocab.py's job). -----------


def test_level_10_and_12_have_no_road_links_in_reference_profile():
    with open(PROFILE_PATH) as f:
        profile = json.load(f)
    for level in ("10", "12"):
        assert profile["levels"][level]["road"]["link_count"] == 0
        assert profile["levels"][level]["road"]["road_type_hist"] == {}
