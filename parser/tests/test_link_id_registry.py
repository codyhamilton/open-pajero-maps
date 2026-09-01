"""Tests for LinkIdRegistry: joint Link ID assignment between the main map
layer (RoadFrame/RoadLink) and the route-planning layer (Ch.10 RP links).

All tests are self-contained (synthetic data only -- no real disc or OSM PBF).
"""
from __future__ import annotations

import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.link_id_registry import LinkIdRegistry
from kiwiw.model import BoundingBox, RoadFrame, RoadLink, RoadNode
from kiwiw.route_planning_writer import (
    RpGraph,
    RpLink,
    RpLinkCost,
    RpNode,
)


# ---------------------------------------------------------------------------
# Minimal RoadLink factory (no raw_bytes -- IR-only synthetic links)
# ---------------------------------------------------------------------------

def _make_link(osm_way_id=None, link_id=0) -> RoadLink:
    node = RoadNode(x=100, y=200, lat=-32.0, lon=115.9, oneway=0,
                    planned=0, tunnel=False, bridge=False)
    return RoadLink(
        display_class=2,
        road_type=5,
        altitude_flag=False,
        route_type_guidance_flag=False,
        pseudo3d_updown=0,
        route_planning_tag=False,
        link_id_flag=False,
        selected_link_flag=False,
        toll_flag=False,
        route_number_flag=False,
        infra_link_flag=False,
        link_id_number_flag=False,
        n_nodes=1,
        nodes=[node],
        osm_way_id=osm_way_id,
        link_id=link_id,
    )


# ---------------------------------------------------------------------------
# test 1 -- basic registry construction and lookup
# ---------------------------------------------------------------------------

def test_registry_basic():
    """Construct a synthetic LinkIdRegistry with 5 entries, look up 3, assert
    correct (parcel_key, index) returned; assert missing key returns fallback.
    """
    registry = LinkIdRegistry()
    entries = [
        (1001, "parcel_A", 0),
        (1002, "parcel_A", 1),
        (1003, "parcel_A", 2),
        (2001, "parcel_B", 0),
        (2002, "parcel_B", 1),
    ]
    for way_id, parcel_key, idx in entries:
        registry.register(way_id, parcel_key, idx)

    assert len(registry) == 5

    # Correct lookups
    assert registry.lookup(1001) == ("parcel_A", 0)
    assert registry.lookup(2001) == ("parcel_B", 0)
    assert registry.lookup(2002) == ("parcel_B", 1)

    # Missing key returns (None, fallback)
    assert registry.lookup(9999) == (None, 0)
    assert registry.lookup(9999, fallback_index=42) == (None, 42)

    # index_for convenience method
    assert registry.index_for(1003) == 2
    assert registry.index_for(9999, fallback_index=7) == 7

    # First-in-wins: registering a duplicate should not overwrite
    registry.register(1001, "parcel_X", 99)
    assert registry.lookup(1001) == ("parcel_A", 0)

    # __contains__
    assert 1001 in registry
    assert 9999 not in registry

    print("PASS: test_registry_basic")


# ---------------------------------------------------------------------------
# test 2 -- RpLink uses registry values in encoded link cost records
# ---------------------------------------------------------------------------

def _u32(buf, off):
    return struct.unpack_from(">I", buf, off)[0]


def _u16(buf, off):
    return struct.unpack_from(">H", buf, off)[0]


def test_rp_link_uses_registry():
    """Build a minimal RpGraph whose RpLinkCost.link_id_origin values come
    from a LinkIdRegistry lookup, encode via encode_rp_frame (from
    osm_to_route_planning), decode the link_cost subframe bytes manually,
    and assert the decoded link_id_origin fields match the registry values.
    """
    # Import encode_rp_frame here (not at top) to keep the import inside
    # the test's own sys.path setup.
    import osm_to_route_planning as ortp

    # Registry: three OSM ways with known positions in their (synthetic) parcel
    registry = LinkIdRegistry()
    registry.register(101, "p1", 0)   # way 101 -> index 0
    registry.register(102, "p1", 1)   # way 102 -> index 1
    registry.register(103, "p1", 4)   # way 103 -> index 4

    osm_way_ids = [101, 102, 103]
    expected_origins = [registry.index_for(w) for w in osm_way_ids]  # [0, 1, 4]

    # Build a minimal 2-node, 3-link graph (nodes A and B, three directed
    # edges A->B to give us three distinct link cost records).
    node_a = RpNode(lat=-32.0, lon=115.9, is_boundary=False, rank=2)
    node_b = RpNode(lat=-32.1, lon=116.0, is_boundary=False, rank=2)

    for i, way_id in enumerate(osm_way_ids):
        cost_idx = i
        origin = registry.index_for(way_id)
        graph_lc = RpLinkCost(
            link_id_origin=origin,
            link_id_dest_delta=0,
            length_m=100.0 * (i + 1),
            connected_node=1,   # node B's index
            road_class=5,
        )
        node_a.links.append(RpLink(
            adjacent_node=1,
            link_cost_index=cost_idx,
            forward_direction=True,
            angle_deg=90,
            following_same_road=None,
            road_class=5,
        ))
        if i == 0:
            graph = RpGraph(
                lat_top=-31.9, lat_bottom=-32.2,
                lon_left=115.8, lon_right=116.1,
                nodes=[node_a, node_b],
                link_costs=[],
            )
        graph.link_costs.append(graph_lc)

    buf = ortp.encode_rp_frame(graph)

    # Decode just the link_cost subframe: use parse_rp_frame to get offsets
    from kiwiw.route_planning import parse_rp_frame
    rf = parse_rp_frame(buf, n_basic=9, n_ext=6)
    lc_sub = rf.sub("link_cost")

    # Link cost header: 6 bytes (sws(6), n_with_time, n_without_time)
    lc_header_size = _u16(buf, lc_sub.offset) * 2  # SWS decode: *2
    # (the header value stored as sws_enc(6) so sws_dec = *2 = 6 + 0 padding? no)
    # Actually sws_enc(6) = 6//2 = 3 => stored as 3; sws decode = *2 = 6.
    # But we can just use the constant 6 (link_cost_header = fixed 6 bytes
    # as written by write_link_cost_header).
    LC_HEADER = 6
    LC_REC_SIZE = 14  # no avg_travel_time in this graph

    for i, expected_origin in enumerate(expected_origins):
        rec_off = lc_sub.offset + LC_HEADER + i * LC_REC_SIZE
        decoded_origin = _u32(buf, rec_off)
        assert decoded_origin == expected_origin, (
            f"link_cost {i}: expected link_id_origin={expected_origin}, "
            f"got {decoded_origin}"
        )

    print("PASS: test_rp_link_uses_registry")


# ---------------------------------------------------------------------------
# test 3 -- from_parcels builds the expected mapping from a synthetic parcel
# ---------------------------------------------------------------------------

def test_map_layer_join():
    """Build a synthetic parcel with 3 RoadLinks having known osm_way_ids,
    derive positional indices, assert LinkIdRegistry.from_parcels produces
    the expected mapping.  Also test assign_link_ids stamps link_id correctly.
    """
    links = [
        _make_link(osm_way_id=201),
        _make_link(osm_way_id=202),
        _make_link(osm_way_id=None),  # no way id -- should be skipped
        _make_link(osm_way_id=203),
    ]

    parcel_dict = {
        "parcel_X": links,
    }

    registry = LinkIdRegistry.from_parcels(parcel_dict)

    # Only the 3 non-None entries are indexed
    assert len(registry) == 3
    assert registry.lookup(201) == ("parcel_X", 0)
    assert registry.lookup(202) == ("parcel_X", 1)
    assert registry.lookup(203) == ("parcel_X", 3)  # index 2 was the None-id link
    assert registry.lookup(999) == (None, 0)

    # Also test the sub-dict form ({"roads": [...], ...})
    parcel_dict2 = {
        "parcel_Y": {"roads": [
            _make_link(osm_way_id=301),
            _make_link(osm_way_id=302),
        ], "backgrounds": [], "names": []},
    }
    registry2 = LinkIdRegistry.from_parcels(parcel_dict2)
    assert len(registry2) == 2
    assert registry2.lookup(301) == ("parcel_Y", 0)
    assert registry2.lookup(302) == ("parcel_Y", 1)

    # assign_link_ids stamps link_id = positional index
    LinkIdRegistry.assign_link_ids(parcel_dict)
    for expected_idx, link in enumerate(links):
        assert link.link_id == expected_idx, (
            f"link at position {expected_idx} has link_id={link.link_id}"
        )

    print("PASS: test_map_layer_join")


if __name__ == "__main__":
    test_registry_basic()
    test_rp_link_uses_registry()
    test_map_layer_join()
    print("All link_id_registry tests passed.")
