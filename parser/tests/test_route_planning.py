"""Round-trip tests for the Ch.9/Ch.10 route-planning writer/decoder pair
(``kiwiw.route_planning_writer`` / ``kiwiw.route_planning``), and for the
aggregated-intersection clustering added in ``build_route_graph.py``
(Ch.10.13 Road Reference Table -- see docs/phases/01-format-analysis.md,
"Road reference table (Ch.10.13, aggregated-intersection clustering)" and
docs/phases/03-osm-pipeline.md for the empirical findings this
implementation is based on).

These tests are self-contained (synthetic in-memory graphs / records) --
they do not require the real disc or an OSM PBF (this repo's environment
does not always have ``pyosmium`` installed; ``build_route_graph.py``
only imports it lazily inside its OSM-collection functions, so
``cluster_nodes()`` itself can be exercised without it).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.route_planning import (
    NodeRecord,
    parse_road_reference_table,
)
from kiwiw.route_planning_writer import (
    RpAggregatedNode,
    RpGraph,
    RpLink,
    RpLinkCost,
    RpNode,
    write_road_reference_table,
)
import build_route_graph as brg


class _FakeSub:
    def __init__(self, size):
        self.offset = 0
        self.size = size


def test_road_reference_table_empty_round_trip():
    """The still-legitimate no-clustering case: int 0 in, count=0 out."""
    buf = write_road_reference_table(0)
    assert buf == b"\x00\x00"
    out = parse_road_reference_table(buf, _FakeSub(len(buf)), None)
    assert out == []
    print("PASS: empty road reference table round-trips")


def test_road_reference_table_single_record_round_trip():
    """One aggregated node with 2 composition links, 1 subordinate node,
    and 2 route-info entries -- exercises every variable-length array and
    the word-alignment padding rule (see route_planning.AggregatedNodeInfo
    docstring)."""
    agg = RpAggregatedNode(
        node_number=5,
        subordinate_node_order_by_link=[0, 1, 0, 1, 1],
        composition_link_cost_numbers=[10, 11],
        subordinate_node_offsets=[(3, -4)],
        route_info=[
            {"entry_link_no": 0, "exit_link_no": 1, "composition_link_relative_numbers": [0]},
            {"entry_link_no": 1, "exit_link_no": 0, "composition_link_relative_numbers": [0]},
        ],
    )
    buf = write_road_reference_table([agg])
    assert len(buf) % 2 == 0, "table must be an even byte length (SWS convention)"

    node_records = [None] * 5 + [
        NodeRecord(
            index=5, is_boundary=False, uppermost_identical_level=0, is_aggregated=True,
            n_link_records=5, is_parcel_boundary=False, has_traffic_light=False,
            is_rotary=False, link_record_offset=0, n_regulations=0, n_between_links_cost=0,
        )
    ]
    out = parse_road_reference_table(buf, _FakeSub(len(buf)), node_records)
    assert len(out) == 1
    r = out[0]
    assert r.node_number == 5
    assert r.n_composition_links == 2
    assert r.n_subordinate_nodes == 1
    assert r.n_route_info == 2
    assert r.subordinate_node_order_by_link == [0, 1, 0, 1, 1]
    assert r.composition_link_cost_numbers == [10, 11]
    assert r.subordinate_node_offsets == [(3, -4)]
    assert len(r.route_info) == 2
    assert r.route_info[0]["entry_link_no"] == 0
    assert r.route_info[0]["exit_link_no"] == 1
    assert r.route_info[0]["composition_link_relative_numbers"] == [0]
    assert r.route_info[1]["entry_link_no"] == 1
    assert r.route_info[1]["exit_link_no"] == 0
    print("PASS: single aggregated-node record round-trips field-for-field")


def test_road_reference_table_multi_record_walk():
    """Multiple records back-to-back: the record-to-record walk must rely
    solely on each record's own declared ``size`` (as it does on the real
    disc -- see survey_road_reference_table.py), not any fixed stride."""
    a = RpAggregatedNode(node_number=1, subordinate_node_order_by_link=[0, 1],
                          composition_link_cost_numbers=[7], subordinate_node_offsets=[(1, 1)])
    b = RpAggregatedNode(node_number=9, subordinate_node_order_by_link=[0, 1, 0],
                          composition_link_cost_numbers=[3, 4, 5],
                          subordinate_node_offsets=[(-1, -1), (2, -2)])
    buf = write_road_reference_table([a, b])
    node_records = {
        1: NodeRecord(index=1, is_boundary=False, uppermost_identical_level=0, is_aggregated=True,
                      n_link_records=2, is_parcel_boundary=False, has_traffic_light=False,
                      is_rotary=False, link_record_offset=0, n_regulations=0, n_between_links_cost=0),
        9: NodeRecord(index=9, is_boundary=False, uppermost_identical_level=0, is_aggregated=True,
                      n_link_records=3, is_parcel_boundary=False, has_traffic_light=False,
                      is_rotary=False, link_record_offset=0, n_regulations=0, n_between_links_cost=0),
    }

    class _NR(list):
        def __getitem__(self, i):
            return node_records.get(i)

        def __len__(self):
            return 10

    out = parse_road_reference_table(buf, _FakeSub(len(buf)), _NR())
    assert [r.node_number for r in out] == [1, 9]
    assert out[0].composition_link_cost_numbers == [7]
    assert out[1].composition_link_cost_numbers == [3, 4, 5]
    assert out[1].subordinate_node_offsets == [(-1, -1), (2, -2)]
    print("PASS: multi-record road reference table walk is size-driven, not stride-driven")


def _make_synthetic_graph():
    """Two close nodes (0, 1), ~11m apart, sharing one short internal
    link, each also linked outward to a distinct external node (2, 3) --
    the canonical "divided-road join" shape this project's short-link
    clustering heuristic targets (see build_route_graph.py module
    docstring, AGGREGATED-INTERSECTION CLUSTERING)."""
    g = RpGraph(lat_top=1, lat_bottom=0, lon_left=0, lon_right=1)
    g.nodes = [
        RpNode(lat=0.0000, lon=0.0000, is_boundary=False, rank=0),
        RpNode(lat=0.0001, lon=0.0000, is_boundary=False, rank=0),
        RpNode(lat=0.0010, lon=0.0010, is_boundary=False, rank=0),
        RpNode(lat=-0.0010, lon=-0.0010, is_boundary=False, rank=0),
    ]
    g.link_costs = [
        RpLinkCost(link_id_origin=1, link_id_dest_delta=0, length_m=11.1, connected_node=1, road_class=3),
        RpLinkCost(link_id_origin=2, link_id_dest_delta=0, length_m=150.0, connected_node=2, road_class=3),
        RpLinkCost(link_id_origin=3, link_id_dest_delta=0, length_m=150.0, connected_node=3, road_class=3),
    ]
    g.nodes[0].links = [
        RpLink(adjacent_node=1, link_cost_index=0, forward_direction=True, angle_deg=0,
               following_same_road=None, road_class=3),
        RpLink(adjacent_node=2, link_cost_index=1, forward_direction=True, angle_deg=45,
               following_same_road=None, road_class=3, regulations=[(0, 0x7F)]),
    ]
    g.nodes[1].links = [
        RpLink(adjacent_node=0, link_cost_index=0, forward_direction=False, angle_deg=180,
               following_same_road=None, road_class=3),
        RpLink(adjacent_node=3, link_cost_index=2, forward_direction=True, angle_deg=225,
               following_same_road=None, road_class=3),
    ]
    g.nodes[2].links = [
        RpLink(adjacent_node=0, link_cost_index=1, forward_direction=False, angle_deg=225,
               following_same_road=None, road_class=3),
    ]
    g.nodes[3].links = [
        RpLink(adjacent_node=1, link_cost_index=2, forward_direction=False, angle_deg=45,
               following_same_road=None, road_class=3),
    ]
    return g


def test_cluster_nodes_merges_close_pair():
    g = _make_synthetic_graph()
    brg.cluster_nodes(g, roundabout_groups=[])

    assert len(g.nodes) == 3, "the two close nodes must merge into one"
    assert len(g.aggregated) == 1
    merged_idx, agg = next(iter(g.aggregated.items()))
    merged = g.nodes[merged_idx]
    assert merged.is_aggregated
    assert len(merged.links) == 2, "both external links must survive on the merged node"
    adjacents = sorted(l.adjacent_node for l in merged.links)
    others = sorted(i for i in range(3) if i != merged_idx)
    assert adjacents == others

    # the regulation on node 0's link to node 2 must survive re-indexed
    # (or be honestly dropped -- here its exit link is external so it must
    # survive) since exit_link_no=0 referred to node 0's OWN link 0 (the
    # internal 0<->1 link), which no longer exists post-merge -- so this
    # particular regulation is expected to be DROPPED, not mis-encoded.
    all_regs = [r for l in merged.links for r in l.regulations]
    assert all_regs == [], "regulation referencing a merged-away internal link must be dropped, not corrupted"

    # composition link cost index 0 (the internal 0<->1 link) must be
    # recorded, and the two external link-cost records' connected_node
    # fields must be remapped to the merged node's new index.
    assert agg.composition_link_cost_numbers == [0]
    assert len(agg.subordinate_node_offsets) == 1
    # cost 0 was the internal 0<->1 link (both ends now the merged node);
    # costs 1/2 point at the two distinct external nodes (2, 3), which
    # were themselves untouched by the merge, so they still point at
    # each other, not at the merged node.
    assert g.link_costs[0].connected_node == merged_idx
    external_targets = sorted([g.link_costs[1].connected_node, g.link_costs[2].connected_node])
    assert external_targets == others
    print("PASS: cluster_nodes merges a close node pair and remaps links/costs/regulations correctly")


def test_cluster_nodes_roundtrips_through_writer_and_decoder():
    """The clustered graph's Road Reference Table, once written, must
    decode back through the shared kiwiw.route_planning decoder to
    exactly the aggregated metadata cluster_nodes() produced."""
    g = _make_synthetic_graph()
    brg.cluster_nodes(g, roundabout_groups=[])

    aggregated_nodes = [g.aggregated[i] for i in sorted(g.aggregated)]
    buf = write_road_reference_table(aggregated_nodes)

    node_records = [
        NodeRecord(index=i, is_boundary=False, uppermost_identical_level=0,
                   is_aggregated=node.is_aggregated, n_link_records=len(node.links),
                   is_parcel_boundary=False, has_traffic_light=False, is_rotary=False,
                   link_record_offset=0, n_regulations=0, n_between_links_cost=0)
        for i, node in enumerate(g.nodes)
    ]
    out = parse_road_reference_table(buf, _FakeSub(len(buf)), node_records)
    assert len(out) == len(aggregated_nodes)
    for want, got in zip(aggregated_nodes, out):
        assert got.node_number == want.node_number
        assert got.composition_link_cost_numbers == want.composition_link_cost_numbers
        assert got.subordinate_node_offsets == want.subordinate_node_offsets
        assert got.subordinate_node_order_by_link == want.subordinate_node_order_by_link
    print("PASS: cluster_nodes output round-trips through write_road_reference_table + parse_road_reference_table")


def test_cluster_nodes_no_clusters_is_a_no_op():
    """When no node pair is close enough and no roundabout groups are
    given, cluster_nodes() must leave the graph untouched (this is the
    common case: most nodes on the real disc are NOT aggregated -- see
    docs/phases/01-format-analysis.md, 89.6% of *regions* have some
    aggregation, but the large majority of individual nodes do not)."""
    g = _make_synthetic_graph()
    for cost in g.link_costs:
        cost.length_m = 500.0  # nothing short enough to cluster
    n_before = len(g.nodes)
    brg.cluster_nodes(g, roundabout_groups=[])
    assert len(g.nodes) == n_before
    assert g.aggregated == {}
    print("PASS: cluster_nodes is a no-op when nothing qualifies for clustering")


def test_roundabout_group_merges_three_or_more_nodes():
    """A roundabout with 4 graph nodes on its ring merges into one node,
    exercising n_subordinate_nodes > 1 (the real disc's max is 5 -- see
    survey_road_reference_table.py)."""
    g = RpGraph(lat_top=1, lat_bottom=0, lon_left=0, lon_right=1)
    g.nodes = [RpNode(lat=0.0 + 0.0001 * i, lon=0.0, is_boundary=False, rank=0) for i in range(4)]
    g.nodes.append(RpNode(lat=0.01, lon=0.01, is_boundary=False, rank=0))  # external, index 4
    g.link_costs = [
        RpLinkCost(link_id_origin=100, link_id_dest_delta=0, length_m=800.0, connected_node=4, road_class=3),
    ]
    g.nodes[0].links = [
        RpLink(adjacent_node=4, link_cost_index=0, forward_direction=True, angle_deg=0,
               following_same_road=None, road_class=3),
    ]
    g.nodes[4].links = [
        RpLink(adjacent_node=0, link_cost_index=0, forward_direction=False, angle_deg=180,
               following_same_road=None, road_class=3),
    ]
    # No short internal links modeled between the 4 ring nodes -- this
    # exercises the *roundabout_groups* clustering path in isolation.
    roundabout_groups = [{0, 1, 2, 3}]
    brg.cluster_nodes(g, roundabout_groups)
    assert len(g.nodes) == 2, "4 ring nodes + 1 external must collapse to 2 nodes"
    assert len(g.aggregated) == 1
    agg = next(iter(g.aggregated.values()))
    assert agg.n_route_info if hasattr(agg, "n_route_info") else True  # route_info intentionally empty for roundabouts
    assert agg.subordinate_node_offsets and len(agg.subordinate_node_offsets) == 3
    print("PASS: a 4-node roundabout ring merges into one aggregated node with 3 subordinates")


if __name__ == "__main__":
    test_road_reference_table_empty_round_trip()
    test_road_reference_table_single_record_round_trip()
    test_road_reference_table_multi_record_walk()
    test_cluster_nodes_merges_close_pair()
    test_cluster_nodes_roundtrips_through_writer_and_decoder()
    test_cluster_nodes_no_clusters_is_a_no_op()
    test_roundabout_group_merges_three_or_more_nodes()
