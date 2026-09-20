"""Coverage for `_make_name_record`'s per-level name `type_code` vocabulary
(docs/plans/01-eval-harness-and-map-layer.md).

The `vocab` harness check (`parser/harness/checks/vocab.py`) requires every
generated `name.type_code` at a given level to be a subset of R's real
per-level `name.type_code_hist` census (`parser/refdata/profile/map.json`).
Brief 23 found the old "reuse whatever bg_type resolved to" mechanism in
`_make_name_record` violated this at level 0 for exactly one bg_type value
(578, "very high speed railway / JR line") and, more broadly, at every
level 2-12 (background type codes there are a wholly disjoint vocabulary
from R's real name-record type codes). These tests pin the fix: level 0
omits the one bad code; levels 2-12 omit background-attached names
entirely rather than emit an uncensused value.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from osm_to_parcel_geometry import (  # noqa: E402
    TileGrid,
    _make_name_record,
    extract_parcel_geometry,
)
from kiwiw.spool import SpoolReader, SpoolWriter  # noqa: E402

PROFILE_PATH = (
    Path(__file__).resolve().parent.parent / "refdata" / "profile" / "map.json"
)


def _profile_name_type_codes(level: int) -> set[int]:
    with open(PROFILE_PATH) as f:
        profile = json.load(f)
    node = profile["levels"][str(level)]["name"]["type_code_hist"]
    return {int(k) for k in node.keys()}


def test_level_0_background_reuses_bg_type_code():
    rec = _make_name_record("PRINCES PARK", -27.0, 153.0, type_code=321,
                             level=0, kind="background")
    assert rec is not None
    assert rec.string_type == 6
    assert rec.type_code == 321


def test_level_0_background_railway_code_578_is_omitted():
    """578 (0x242) is present in R's level-0 background census but absent
    from its level-0 name census -- see brief 23's findings table."""
    rec = _make_name_record("SOME RAILWAY", -27.0, 153.0, type_code=578,
                             level=0, kind="background")
    assert rec is None


def test_level_0_background_578_absent_from_reference_name_census():
    assert 578 not in _profile_name_type_codes(0)


def test_levels_2_to_12_background_names_are_omitted():
    """No evidenced mapping exists from a background feature's bg_type to
    a level 2-12 name type_code (R's real per-level name census at these
    levels is disjoint from every bg_type.json value) -- omit rather than
    fabricate, per this unit's contract (unit 08's own null-default
    precedent)."""
    for level in (2, 4, 6, 8, 10, 12):
        for bg_type in (288, 289, 290, 291, 321, 322, 578, 640, 1024, 306):
            rec = _make_name_record("SOME FEATURE", -27.0, 153.0,
                                     type_code=bg_type, level=level,
                                     kind="background")
            assert rec is None, (level, bg_type)


def test_levels_2_to_12_nonsuburb_place_names_are_omitted():
    """`_make_name_record` still rejects an 0x132 (306, "address level 2
    (state)") place-kind type_code at every level 2-12 as a defensive
    no-op -- 306 is absent from R's real name census at every level
    selection.json currently admits a place node at (2/4/6: only 3
    occurrences at level 8, where selection.json admits no place nodes at
    all). As of brief 22
    (docs/plans/01-eval-harness-and-map-layer.md, brief 22-spotcheck-missing-names in git history), `_handle_node` itself no longer ever
    passes 0x132 -- it was found to be the root cause of the Perth
    level-2 `spotcheck` FAIL (place=city nodes silently dropped here) and
    was changed to always pass 0x134 (308) instead, see
    `test_handle_node_assigns_308_to_nonsuburb_place` below. This test
    exercises `_make_name_record`'s own guard directly, independent of
    what any caller currently passes."""
    for level in (2, 4, 6, 10, 12):
        rec = _make_name_record("PERTH", -27.0, 153.0, type_code=0x132,
                                 level=level, kind="place")
        assert rec is None, level


def test_levels_2_to_12_suburb_place_names_kept():
    for level in (2, 4, 6, 8, 10, 12):
        rec = _make_name_record("SOME SUBURB", -27.0, 153.0, type_code=0x134,
                                 level=level, kind="place")
        assert rec is not None
        assert rec.type_code == 308
        assert 308 in _profile_name_type_codes(level)


def test_levels_2_to_12_road_names_unaffected():
    """Road name records at levels >0 fall through the same branch as
    background names used to, but their default type_code (0x134=308) is
    already in R's census at every level 2-12 -- this unit does not touch
    that path."""
    for level in (2, 4, 6, 8, 10, 12):
        rec = _make_name_record("SOME ROAD", -27.0, 153.0, level=level,
                                 kind="road", geometry=[(-27.0, 153.0), (-27.01, 153.01)])
        assert rec is not None
        assert rec.type_code == 0x134 == 308
        assert 308 in _profile_name_type_codes(level)


def test_handle_node_assigns_308_to_nonsuburb_place(tmp_path):
    """End-to-end regression for brief 22
    (docs/plans/01-eval-harness-and-map-layer.md, brief 22-spotcheck-missing-names in git history): a real `place=city` OSM node (like
    Perth's) run through the actual extractor (`_handle_node`, via
    `extract_parcel_geometry` with the real `selection.json`-backed
    level_filter, not the test-only `_default_level_filter`) must produce
    a `NameRecord` with type_code=308 at level 2 -- not be silently
    dropped the way 0x132 (306) was before this fix."""
    import osmium
    from osmium.osm.mutable import Node

    pbf_path = tmp_path / "city_node.osm.pbf"
    writer = osmium.SimpleWriter(str(pbf_path))
    try:
        writer.add_node(Node(
            id=1, location=(115.8605784, -31.9558967),
            tags={"place": "city", "name": "Test City"},
        ))
    finally:
        writer.close()

    grids = {2: TileGrid.from_reference(2)}
    spool_dir = tmp_path / "spool"
    spool_writer = SpoolWriter(spool_dir, flush_threshold=1)
    extract_parcel_geometry(str(pbf_path), grids, spool_writer, verbose=False)

    reader = SpoolReader(spool_dir)
    names = [n for _ix, _iy, content in reader.iter_level(2) for n in content["names"]]
    matches = [n for n in names if n.text == "Test City"]
    assert len(matches) == 1, names
    assert matches[0].type_code == 308
    assert 308 in _profile_name_type_codes(2)
