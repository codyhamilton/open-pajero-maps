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
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.spool import SpoolReader, SpoolWriter
from kiwiw.model import BoundingBox
import osm_to_parcel_geometry as geometry
from osm_to_parcel_geometry import (
    TileGrid,
    _default_level_filter,
    assign_to_parcel,
    extract_parcel_geometry,
    split_polyline_by_parcel,
)

LEVELS = [0, 2, 12]


def _fixture_grid(target=None, level=0, lon_lo=110.0):
    return TileGrid(level, -35.0, lon_lo, 10.0, 20.0, 20, 10,
                    target or BoundingBox(-32.8, -32.2, lon_lo + 5.2, lon_lo + 5.8))


def _way(coords):
    return NS(id=900, tags={"highway": "residential", "name": "Fixture Road"},
              nodes=[NS(lat=lat, lon=lon, location=NS(valid=lambda: True))
                     for lat, lon in coords])


def test_disjoint_fixture_way_avoids_split(monkeypatch):
    grid = _fixture_grid()
    handler = geometry._GeomHandler({0: grid}, NS(add=lambda *a, **kw: None),
                                    _default_level_filter)
    def unexpected(*args):
        pytest.fail("disjoint fixture way reached full-grid splitting")
    monkeypatch.setattr(geometry, "split_polyline_by_parcel", unexpected)
    handler._handle_way(_way([(-30.5, 115.5), (-30.4, 115.6)]))
    handler._handle_way(_way([(-32.5, 120.5), (-32.4, 120.6)]))


@pytest.mark.parametrize("coords", [
    [(-32.5, 115.05), (-32.4, 115.1)],  # cell margin outside exact fixture
    [(-32.5, 114.5), (-32.5, 116.5)],  # both endpoints outside; crosses
    [(-33.0, 115.0), (-33.0, 116.0)],  # cell boundary
])
def test_fixture_retains_admitted_roads(monkeypatch, coords):
    grid = _fixture_grid()
    handler = geometry._GeomHandler({0: grid}, NS(add=lambda *a, **kw: None),
                                    _default_level_filter)
    calls = []
    def split(points, actual_grid):
        calls.append((points, actual_grid))
        return {}
    monkeypatch.setattr(geometry, "split_polyline_by_parcel", split)
    handler._handle_way(_way(coords))
    assert calls == [(coords, grid)]


@pytest.mark.parametrize("target", [
    BoundingBox(-27.02, -26.98, 152.98, 153.02),
    BoundingBox(-27.1, -26.9, 179.9, 180.1),
    BoundingBox(-30.02, -29.98, 139.98, 140.02),
])
def test_fixture_precheck_preserves_spool_bytes(pbf_path, tmp_path, monkeypatch, target):
    grids = {level: TileGrid.from_reference(level, target) for level in LEVELS}
    enabled = tmp_path / "enabled"
    baseline = tmp_path / "baseline"
    extract_parcel_geometry(pbf_path, grids, SpoolWriter(enabled, flush_threshold=1),
                            verbose=False, level_filter=_default_level_filter)
    monkeypatch.setattr(geometry._GeomHandler, "_way_intersects_target",
                        lambda *a: True)
    extract_parcel_geometry(pbf_path, grids, SpoolWriter(baseline, flush_threshold=1),
                            verbose=False, level_filter=_default_level_filter)
    actual = {p.name: p.read_bytes() for p in enabled.iterdir() if p.is_file()}
    expected = {p.name: p.read_bytes() for p in baseline.iterdir() if p.is_file()}
    assert actual and actual == expected


def test_precheck_matches_existing_road_admission():
    # Existing tiling is the permitted extraction oracle. Include wrapped
    # longitudes and edge columns, where assign_to_parcel clamps positions.
    targets = [BoundingBox(-32.8, -32.2, 115.2, 115.8),
               BoundingBox(-32.8, -32.2, 110.0, 110.8),
               BoundingBox(-32.8, -32.2, 129.2, 130.0),
               BoundingBox(-32.8, -32.2, 179.2, 179.8)]
    for target in targets:
        grid = _fixture_grid(target, lon_lo=174.0 if target.lon_lo > 170 else 110.0)
        handler = geometry._GeomHandler({0: grid}, NS(), _default_level_filter)
        for lat in (-36.0, -33.0, -32.5, -32.0, -24.0):
            for lon in (-179.5, -170.0, 90.0, 110.0, 115.5, 120.5, 130.0, 179.5):
                coords = [(lat, lon), (lat + 0.2, lon + 0.2)]
                admitted = set(split_polyline_by_parcel(coords, grid)) & handler.target_cells[0]
                if admitted:
                    assert handler._way_intersects_target(0, (lat, lat + 0.2, lon, lon + 0.2))


def test_fixture_admission_is_per_level(monkeypatch):
    near = _fixture_grid()
    far = _fixture_grid(BoundingBox(-30.8, -30.2, 115.2, 115.8), level=2)
    handler = geometry._GeomHandler({0: near, 2: far}, NS(), _default_level_filter)
    calls = []
    monkeypatch.setattr(geometry, "split_polyline_by_parcel",
                        lambda coords, grid: calls.append(grid.level) or {})
    handler._handle_way(_way([(-32.5, 115.5), (-32.4, 115.6)]))
    assert calls == [0]


def test_empty_fixture_and_boundary_guard():
    near = _fixture_grid()
    empty = _fixture_grid(BoundingBox(-50.0, -49.0, 115.2, 115.8), level=2)
    handler = geometry._GeomHandler({0: near, 2: empty}, NS(), _default_level_filter)
    assert not handler._way_intersects_target(2, (-32.5, -32.4, 115.5, 115.6))
    assert handler._way_intersects_target(0, (-33.0 - 1e-10, -33.0 - 1e-10,
                                              115.0 - 1e-10, 115.0 - 1e-10))

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
        extract_parcel_geometry(pbf_path, grids, writer, verbose=False, level_filter=_default_level_filter)

        reader = SpoolReader(spool_dir)
        assert sorted(reader.levels()) == sorted(LEVELS)

        for level in LEVELS:
            grid = grids[level]
            # Levels 10/12 have zero road_type/display_class values in R's
            # census (docs/design/osm-vocabulary-mapping.md, "Backgrounds"), so
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

            # Names: suburb (1, every level) + one per road way that
            # produced a link (3, only when roads are expected at this
            # level) + background name (1, level 0 only -- brief 23:
            # background-attached name records are omitted at levels other
            # than 0, since R's real per-level name type_code census there
            # is disjoint from every value bg_type.json can emit).
            total_names = sum(len(v["names"]) for v in seen_parcels.values())
            expected_names = 1
            if roads_expected_at_level:
                expected_names += 3
            if level == 0:
                expected_names += 1
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
        docs/design/osm-vocabulary-mapping.md, "Backgrounds") and kiwiw.vocab's road_type/
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
        extract_parcel_geometry(pbf_path, grids, writer, verbose=False, level_filter=_default_level_filter)
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
        extract_parcel_geometry(pbf_path, grids, writer_a, verbose=False, level_filter=_default_level_filter)

        spool_b = tmp_path / "spool_b"
        writer_b = SpoolWriter(spool_b, flush_threshold=1)
        extract_parcel_geometry(pbf_path, grids, writer_b, verbose=False, level_filter=_default_level_filter)

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
