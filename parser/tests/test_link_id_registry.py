"""Tests for LinkIdRegistry: the (level, osm_way_id, ordinal) -> link_id
join registry shared between the main map layer and the route-planning
layer (docs/design/target-disc.md, "Link identity").

All tests are self-contained (synthetic data only -- no real disc or OSM
PBF).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.link_id_registry import LinkIdRegistry
from kiwiw.model import BoundingBox
from osm_to_parcel_geometry import TileGrid, split_polyline_by_parcel


def _make_grid(
    lat_lo: float = -35.0,
    lon_lo: float = 113.0,
    lat_span: float = 10.0,
    lon_span: float = 20.0,
    nx: int = 100,
    ny: int = 50,
    level: int = 8,
) -> TileGrid:
    """Synthetic TileGrid (same shape as test_parcel_geometry.py's helper)."""
    target = BoundingBox(
        lat_lo=lat_lo, lat_hi=lat_lo + lat_span,
        lon_lo=lon_lo, lon_hi=lon_lo + lon_span,
    )
    return TileGrid(
        level=level,
        disc_lat_lo=lat_lo,
        disc_lon_lo=lon_lo,
        disc_lat_span=lat_span,
        disc_lon_span=lon_span,
        nx=nx,
        ny=ny,
        target=target,
    )


# ---------------------------------------------------------------------------
# test 1 -- a way crossing two parcels yields two links / two ordinals / two ids
# ---------------------------------------------------------------------------

def test_way_crossing_two_parcels_gets_two_ordinals_and_ids():
    """A way whose polyline crosses a parcel boundary splits into two
    chains; each chain's ordinal is 0-based in node-sequence order, and
    registering both yields two distinct link ids.
    """
    grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                       nx=100, ny=50)
    # Crosses the iy=5/iy=6 boundary at lat=-33.0 within a single ix column
    # (same setup as test_parcel_geometry.py's test_cross_boundary_splits).
    p1 = (-34.05, 114.05)
    p2 = (-33.85, 114.05)

    per_parcel = split_polyline_by_parcel([p1, p2], grid)
    assert len(per_parcel) == 2, "test setup: way must cross exactly one boundary"

    chains = [chain for chains in per_parcel.values() for chain in chains]
    assert len(chains) == 2
    ordinals = sorted(chain.ordinal for chain in chains)
    assert ordinals == [0, 1]

    level = 0
    way_id = 42
    registry = LinkIdRegistry()
    ids = [registry.assign(level, way_id, chain.ordinal) for chain in chains]
    assert len(set(ids)) == 2, "two ordinals of the same way must get two distinct ids"
    assert len(registry) == 2

    print("PASS: test_way_crossing_two_parcels_gets_two_ordinals_and_ids")


# ---------------------------------------------------------------------------
# test 2 -- re-registering the same key returns the same id (idempotent)
# ---------------------------------------------------------------------------

def test_reassign_same_key_returns_same_id():
    registry = LinkIdRegistry()
    level, way_id, ordinal = 0, 101, 0

    first = registry.assign(level, way_id, ordinal)
    second = registry.assign(level, way_id, ordinal)
    assert first == second
    assert len(registry) == 1

    # A different ordinal for the same way is a different key -> different id.
    other = registry.assign(level, way_id, ordinal + 1)
    assert other != first
    assert len(registry) == 2

    # A different level for the same (way_id, ordinal) is also a different key.
    other_level = registry.assign(level + 1, way_id, ordinal)
    assert other_level != first
    assert len(registry) == 3

    assert registry.lookup(level, way_id, ordinal) == first
    assert registry.lookup(level, way_id, ordinal + 1) == other
    assert registry.lookup(level + 1, way_id, ordinal) == other_level
    assert registry.lookup(level, way_id, 999) is None
    assert (level, way_id, ordinal) in registry
    assert (level, way_id, 999) not in registry

    print("PASS: test_reassign_same_key_returns_same_id")


# ---------------------------------------------------------------------------
# test 3 -- determinism across runs
# ---------------------------------------------------------------------------

def test_determinism_across_runs():
    """Two independently-built registries, fed the same assign() calls in
    the same order, produce identical id assignments and identical
    ``items()`` output.
    """
    keys = [
        (0, 101, 0),
        (0, 101, 1),
        (0, 102, 0),
        (2, 101, 0),
        (0, 101, 1),  # repeat -- must not mint a new id
    ]

    def build():
        r = LinkIdRegistry()
        ids = [r.assign(*k) for k in keys]
        return r, ids

    registry_a, ids_a = build()
    registry_b, ids_b = build()

    assert ids_a == ids_b
    assert list(registry_a.items()) == list(registry_b.items())
    # items() is sorted by key regardless of assignment order.
    assert list(registry_a.items()) == sorted(registry_a.items())
    assert len(registry_a) == 4  # one repeat among the 5 assign() calls

    print("PASS: test_determinism_across_runs")


if __name__ == "__main__":
    test_way_crossing_two_parcels_gets_two_ordinals_and_ids()
    test_reassign_same_key_returns_same_id()
    test_determinism_across_runs()
    print("All link_id_registry tests passed.")
