"""Scale-path tests for parser/osm_to_parcel_geometry.py + kiwiw/spool.py.

Builds a tiny synthetic PBF in-test (osmium.SimpleWriter) covering:
  - a place=suburb name node,
  - a road way entirely inside one parcel at every level,
  - a road way crossing the 180deg E antimeridian,
  - a road way whose points cross level-0 parcel boundaries but stay inside
    one parcel at the coarser levels,
  - a natural=water background way with a name.

and runs `extract_parcel_geometry` for levels [0, 2, 12] into a temp spool,
checking the whole pipeline (PBF -> osmium -> tiling -> spool) against the
pure-Python tiling functions (`split_polyline_by_parcel`, `assign_to_parcel`)
as the oracle -- those are exercised directly (and more thoroughly) by
test_parcel_geometry.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.spool import SpoolReader, SpoolWriter
from osm_to_parcel_geometry import (
    TileGrid,
    assign_to_parcel,
    extract_parcel_geometry,
    split_polyline_by_parcel,
)

LEVELS = [0, 2, 12]

# --- Synthetic feature coordinates (lat, lon) -------------------------------

SUBURB_NODE = (-27.0, 153.0)
WAY_SIMPLE = [(-27.0001, 153.0001), (-27.0002, 153.0002)]           # 101
WAY_CROSS_180 = [(-27.0, 179.99), (-27.0, -179.99)]                  # 102
WAY_SPLIT = [(-27.00, 150.00), (-27.03, 150.00), (-27.06, 150.00)]   # 103
WAY_BG_RING = [(-30.00, 140.00), (-30.00, 140.01),
                (-30.01, 140.01), (-30.01, 140.00)]                  # 104


def _build_pbf(path: str) -> None:
    import osmium
    from osmium.osm.mutable import Node, Way

    writer = osmium.SimpleWriter(path)
    try:
        # Node ids 1..12; way node ids reference these.
        writer.add_node(Node(
            id=1, location=(SUBURB_NODE[1], SUBURB_NODE[0]),
            tags={"place": "suburb", "name": "Test Suburb"},
        ))
        node_id = 2
        way_node_ids: dict[str, list[int]] = {}
        for key, coords in (
            ("simple", WAY_SIMPLE),
            ("cross180", WAY_CROSS_180),
            ("split", WAY_SPLIT),
            ("bg", WAY_BG_RING),
        ):
            ids = []
            for lat, lon in coords:
                writer.add_node(Node(id=node_id, location=(lon, lat), tags={}))
                ids.append(node_id)
                node_id += 1
            way_node_ids[key] = ids

        writer.add_way(Way(
            id=101, nodes=way_node_ids["simple"],
            tags={"highway": "residential", "name": "Straight Street"},
        ))
        writer.add_way(Way(
            id=102, nodes=way_node_ids["cross180"],
            tags={"highway": "residential", "name": "Cross Meridian Road"},
        ))
        writer.add_way(Way(
            id=103, nodes=way_node_ids["split"],
            tags={"highway": "residential", "name": "Split Road"},
        ))
        writer.add_way(Way(
            id=104, nodes=way_node_ids["bg"],
            tags={"natural": "water", "name": "Lake Test"},
        ))
    finally:
        writer.close()


def _grids() -> dict[int, TileGrid]:
    return {level: TileGrid.from_reference(level) for level in LEVELS}


def _expected_road_chain_count(grid: TileGrid) -> int:
    total = 0
    for coords in (WAY_SIMPLE, WAY_CROSS_180, WAY_SPLIT):
        per_parcel = split_polyline_by_parcel(coords, grid)
        for chains in per_parcel.values():
            total += len(chains)
    return total


def _expected_road_parcels(grid: TileGrid) -> set:
    parcels = set()
    for coords in (WAY_SIMPLE, WAY_CROSS_180, WAY_SPLIT):
        parcels |= set(split_polyline_by_parcel(coords, grid).keys())
    return parcels


@pytest.fixture(scope="module")
def pbf_path(tmp_path_factory):
    d = tmp_path_factory.mktemp("extractor_scale")
    p = d / "synthetic.osm.pbf"
    _build_pbf(str(p))
    return str(p)


class TestExtractorScale:
    def test_per_level_parcels_and_counts(self, pbf_path, tmp_path):
        grids = _grids()
        spool_dir = tmp_path / "spool"
        writer = SpoolWriter(spool_dir, flush_threshold=1)  # flush aggressively
        extract_parcel_geometry(pbf_path, grids, writer, verbose=False)

        reader = SpoolReader(spool_dir)
        assert sorted(reader.levels()) == sorted(LEVELS)

        for level in LEVELS:
            grid = grids[level]
            # Levels 10/12 have zero road_type/display_class values in R's
            # census (parser/refdata/vocab/README.md, "Levels 10/12"), so
            # kiwiw.vocab's road_type/display_class tables both return None
            # for every highway= tag there and `_make_road_link` omits the
            # feature -- no road links (and, since a road name is only
            # emitted "if name and any_link", no road-derived names either)
            # are produced at level 12, unlike levels 0/2.
            roads_expected_at_level = level not in (10, 12)
            expected_road_parcels = (
                _expected_road_parcels(grid) if roads_expected_at_level else set()
            )
            expected_road_chains = (
                _expected_road_chain_count(grid) if roads_expected_at_level else 0
            )

            seen_parcels = {}
            for ix, iy, content in reader.iter_level(level):
                seen_parcels[(ix, iy)] = content

            # Road-bearing parcels match the pure-function oracle exactly.
            road_parcels = {k for k, v in seen_parcels.items() if v["roads"]}
            assert road_parcels == expected_road_parcels, level

            total_roads = sum(len(v["roads"]) for v in seen_parcels.values())
            assert total_roads == expected_road_chains, level

            # Background: exactly one shape, at the ring's centroid parcel.
            total_bgs = sum(len(v["backgrounds"]) for v in seen_parcels.values())
            assert total_bgs == 1, level

            # Names: suburb (1) + one per road way that produced a link (3,
            # only when roads are expected at this level) + background name
            # (1).
            total_names = sum(len(v["names"]) for v in seen_parcels.values())
            expected_names = 5 if roads_expected_at_level else 2
            assert total_names == expected_names, level

            stats = reader.stats(level)
            assert stats["parcels"] == len(seen_parcels)
            assert stats["roads"] == total_roads
            assert stats["backgrounds"] == total_bgs
            assert stats["names"] == total_names

    def test_split_way_yields_expected_chains(self, pbf_path, tmp_path):
        """WAY_SPLIT crosses level-0 parcel boundaries (checked directly
        against split_polyline_by_parcel) but stays within a single parcel
        at level 12 (its span is far smaller than a level-12 cell). At
        level 12 itself, R's census has zero road links (parser/refdata/
        vocab/README.md, "Levels 10/12") and kiwiw.vocab's road_type/
        display_class tables return None there for every highway= tag, so
        WAY_SPLIT (highway=residential) yields zero links at level 12 even
        though it geometrically fits in one parcel."""
        grids = _grids()
        grid0 = grids[0]
        grid12 = grids[12]

        expected0 = split_polyline_by_parcel(WAY_SPLIT, grid0)
        assert len(expected0) > 1, "test setup: WAY_SPLIT should cross a level-0 boundary"

        expected12 = split_polyline_by_parcel(WAY_SPLIT, grid12)
        assert len(expected12) == 1, "test setup: WAY_SPLIT should stay in one level-12 parcel"

        spool_dir = tmp_path / "spool"
        writer = SpoolWriter(spool_dir, flush_threshold=1)
        extract_parcel_geometry(pbf_path, grids, writer, verbose=False)
        reader = SpoolReader(spool_dir)

        def links_for_way(level):
            found = []
            for ix, iy, content in reader.iter_level(level):
                for link in content["roads"]:
                    if getattr(link, "osm_way_id", None) == 103:
                        found.append((ix, iy, link))
            return found

        links0 = links_for_way(0)
        links12 = links_for_way(12)
        assert len({(ix, iy) for ix, iy, _ in links0}) == len(expected0)
        assert len({(ix, iy) for ix, iy, _ in links12}) == 0

    def test_iter_level_order_deterministic_byte_identical(self, pbf_path, tmp_path):
        grids = _grids()

        spool_a = tmp_path / "spool_a"
        writer_a = SpoolWriter(spool_a, flush_threshold=1)
        extract_parcel_geometry(pbf_path, grids, writer_a, verbose=False)

        spool_b = tmp_path / "spool_b"
        writer_b = SpoolWriter(spool_b, flush_threshold=1)
        extract_parcel_geometry(pbf_path, grids, writer_b, verbose=False)

        for level in LEVELS:
            data_a = (spool_a / f"level_{level}.data").read_bytes()
            data_b = (spool_b / f"level_{level}.data").read_bytes()
            assert data_a == data_b, f"level {level} .data differs across runs"

            idx_a = (spool_a / f"level_{level}.idx").read_bytes()
            idx_b = (spool_b / f"level_{level}.idx").read_bytes()
            assert idx_a == idx_b, f"level {level} .idx differs across runs"

        # And iteration order is ascending (iy, ix).
        reader = SpoolReader(spool_a)
        for level in LEVELS:
            keys = [(ix, iy) for ix, iy, _ in reader.iter_level(level)]
            assert keys == sorted(keys, key=lambda k: (k[1], k[0]))
