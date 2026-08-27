"""Round-trip tests for boundary-node cross-region Link Records
(Ch.10.7.1.1 item (8), "Region Number") -- the wiring added in
build_route_hierarchy.py to turn a bare is_boundary flag into an actual
"link to another region" per the spec's own definition (found via
pdftotext of spec/format_english/pdf/1000122e.pdf): "A boundary node is
defined as a node that has a link to another region... The region number
where the adjacent node exists is described."

These are synthetic, in-memory RpGraph tests -- no OSM data or the
mounted disc required. See build_route_hierarchy.py's
mark_boundary_and_build_rpgraph() for the real (OSM-driven) version of
this same wiring, exercised end-to-end by that script's own --max-settled
run (not part of the automated test suite, since it needs a real OSM PBF).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.route_planning_writer import RpGraph, RpNode, RpLink, RpLinkCost
from osm_to_route_planning import encode_rp_frame, round_trip_check, decode_link_record, link_record_size


def _two_node_graph_with_boundary() -> RpGraph:
    """Node 0 is an ordinary node with one local link to node 1. Node 1 is
    a boundary node: it has the same local link back to node 0 (region
    _number = None -> encoded as 0xFFFF, "no region"), PLUS an escape link
    to node index 3 in region_no=7 (region_number=7) -- simulating a
    boundary node's link to its own instance one level up."""
    g = RpGraph(lat_top=1.0, lat_bottom=0.0, lon_left=0.0, lon_right=1.0, region_no=0)
    g.nodes.append(RpNode(lat=0.1, lon=0.1, is_boundary=False, rank=0))
    g.nodes.append(RpNode(lat=0.2, lon=0.2, is_boundary=True, rank=0))
    g.link_costs.append(RpLinkCost(link_id_origin=1, link_id_dest_delta=0, length_m=100.0,
                                    connected_node=1, road_class=2))
    g.link_costs.append(RpLinkCost(link_id_origin=2, link_id_dest_delta=0, length_m=0.0,
                                    connected_node=3, road_class=4))
    g.nodes[0].links.append(RpLink(adjacent_node=1, link_cost_index=0, forward_direction=True,
                                    angle_deg=90, following_same_road=None, road_class=2))
    # node 1's local link back to node 0 -- region_number left as None, so
    # encode_rp_frame must fill in 0xFFFF ("no region") since the OWNING
    # node (1) is a boundary node and every one of its links gets the
    # 8-byte record.
    g.nodes[1].links.append(RpLink(adjacent_node=0, link_cost_index=0, forward_direction=False,
                                    angle_deg=270, following_same_road=None, road_class=2))
    # node 1's escape link to region 7, node-table index 3
    g.nodes[1].links.append(RpLink(adjacent_node=3, link_cost_index=1, forward_direction=True,
                                    angle_deg=0, following_same_road=None, road_class=4,
                                    region_number=7))
    return g


def test_boundary_node_links_round_trip_with_region_number():
    g = _two_node_graph_with_boundary()
    buf = encode_rp_frame(g)
    result = round_trip_check(g, buf)
    assert result["problems"] == [], result["problems"]


def test_non_boundary_node_link_record_is_6_bytes_boundary_is_8():
    assert link_record_size(is_boundary=False) == 6
    assert link_record_size(is_boundary=True) == 8


def test_boundary_node_local_link_encodes_no_region_sentinel():
    """A boundary node's link that does NOT cross regions must still get
    the 8-byte record (spec: ALL of a boundary node's links do), with
    region_number == 0xFFFF ("no region"), not omitted."""
    g = _two_node_graph_with_boundary()
    buf = encode_rp_frame(g)
    from kiwiw.route_planning import parse_rp_frame
    rf = parse_rp_frame(buf, 9, 6)
    node_sub = rf.sub("node")
    link_sub = rf.sub("link")
    from osm_to_route_planning import decode_node_record
    rec1 = decode_node_record(buf, node_sub.offset + rf.node_header.header_size + 1 * 6)
    assert rec1["is_boundary"] is True
    link_off = link_sub.offset + rec1["link_record_offset"]
    lrec0 = decode_link_record(buf, link_off, is_boundary=True)
    assert lrec0["region_number"] == 0xFFFF  # the local (non-crossing) link
    lrec1 = decode_link_record(buf, link_off + 8, is_boundary=True)
    assert lrec1["region_number"] == 7       # the escape link
    assert lrec1["adjacent_node"] == 3
