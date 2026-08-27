#!/usr/bin/env python3
"""Orchestrator / round-trip test for the Ch.9 + Ch.10 write path.

Builds a routing graph from OSM for one bounded test region (default:
the reference disc's own region_no=178, level=2 -- see below for why it
was picked), encodes it with ``kiwiw.route_planning_writer``, decodes the
result with the existing ``kiwiw.route_planning`` decoder (header/
subframe-table level) plus a set of record-level decoders defined in
*this* script (mirroring, not modifying, the writer's bit layouts) to
verify a structural round trip, and prints a sanity-check comparison
against the real disc's own decoded graph for the same region.

Test region selection (recorded here for reproducibility): of the 1,864
real regions on the reference disc, region_no=178 at level=2 (Western
Australia, south of Perth) has a moderate size -- 106 nodes / 282 links,
1 rank, road_class_mask covering classes 2 and 3 (Highway / Throughway),
rp_level=3 -- and is not the largest region on the disc.  Its exact bbox
(read directly off the disc's own Ch.9 Region Management Table) is:
  lon_left=115.49072916666667  lat_bottom=-31.718506944444446
  lon_right=116.03072916666666 lat_top=-31.31829861111111

IMPORTANT CAVEAT discovered while building this prototype (see the final
report): the real disc's level-2 region graph for this bbox has only 106
nodes. The raw OSM road network for the *same* bbox is vastly denser --
even restricted to primary/secondary/tertiary classes only (the classes
actually present in this region's road_class_mask), OSM's intersection
graph for this bbox has ~2,800 nodes / ~5,500 directed links, roughly 26x
more nodes than the real region. This is NOT a bug in this prototype's
OSM extraction -- it is direct, quantified evidence that the disc's
level-2 route-planning regions are a heavily contracted, sparse
long-distance layer (consistent with the CH/highway-hierarchy design the
spec describes), not "the local road network filtered to major classes."
Building a real multi-level contraction that reproduces this density
gap is out of scope for this prototype (see docs/phases/01-format-analysis.md's
scope-of-work note, which this finding reinforces rather than
contradicts) -- this script instead demonstrates the write/round-trip
machinery end-to-end on the OSM graph AS EXTRACTED, self-reporting the
size mismatch rather than hiding it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.bitutils import u8, u16, u24, u32, extract, geo_secs
from kiwiw.route_planning import parse_rp_frame, parse_node_table, parse_road_reference_table, BASIC_MGMT_FIELDS
from kiwiw.route_planning_writer import (
    RpGraph, RpNode, RpLink, RpLinkCost, RpAggregatedNode,
    write_node_record, write_link_record, write_regulation_record,
    write_between_links_cost_record, write_link_cost_header,
    write_link_cost_record, write_node_coord_header,
    write_reference_grid_record, write_node_coord_record,
    write_road_reference_table, write_ext_frame,
    d32_enc, sws_enc, _u16, _u32,
)
from kiwiw.misc import DISC_STAMP_12B

import build_route_graph as brg

REGION_178_BBOX = (
    115.49072916666667, -31.718506944444446,  # lon_left, lat_bottom
    116.03072916666666, -31.31829861111111,   # lon_right, lat_top
)
REGION_178_REAL = {"n_nodes": 106, "n_links": 282, "n_ranks": 1, "rp_level": 3}


# --------------------------------------------------------------------------
# Encoder: RpGraph -> full Route Planning Data Frame buffer
# --------------------------------------------------------------------------

def encode_rp_frame(graph: RpGraph) -> bytes:
    n_nodes = len(graph.nodes)
    n_links = sum(len(n.links) for n in graph.nodes)

    # -- node distribution header + rank info (single rank, matching the
    # real region 178's own single-rank structure) --
    road_class_mask = 0
    for n in graph.nodes:
        for l in n.links:
            road_class_mask |= 1 << (15 - l.road_class)
    rank_rec = _u16(n_nodes) + _u16(0) + _u16(n_links) + _u16(road_class_mask)
    rp_level = min((n.rank for n in graph.nodes), default=0)
    lvl_word = ((rp_level & 0x7) << 1)  # avg-travel-time flag left 0 (not modeled)
    rank_rec += _u16(lvl_word)
    node_header_fixed = _u16(sws_enc(8 + len(rank_rec))) + _u16(n_nodes) + _u16(n_links) + _u16(1)
    node_header = node_header_fixed + rank_rec

    # -- link table (per node: link records, then regulation records, then
    # between-links cost records), and node records referencing it --
    link_buf = bytearray()
    node_recs = bytearray()
    for node in graph.nodes:
        link_off = len(link_buf)
        n_link_recs = len(node.links)
        undecided = n_link_recs > 14
        for link in node.links:
            # Ch.10.7.1.1 item (8): the region_number field exists (8-byte
            # link record) for EVERY link of a boundary node, not just the
            # one(s) that actually cross into another region -- 0xFFFF ("no
            # region") is written for the ones that don't, per the spec's
            # literal wording. Non-boundary nodes keep the normal 6-byte
            # record (region_number=None -> omitted).
            region_number = None
            if node.is_boundary:
                region_number = link.region_number if link.region_number is not None else 0xFFFF
            link_buf += write_link_record(
                adjacent_node=link.adjacent_node,
                link_cost_index=link.link_cost_index,
                is_suburb=False,
                is_semi_urban_highway=False,
                is_reverse_direction=not link.forward_direction,
                following_same_road=link.following_same_road,
                angle_deg=link.angle_deg,
                region_number=region_number,
            )
        regs = []
        for link_i, link in enumerate(node.links):
            for exit_no, passage_code in link.regulations:
                regs.append(write_regulation_record(link_i, exit_no, False, passage_code))
        for r in regs:
            link_buf += r
        # no between-links cost records modeled in this prototype (no
        # per-turn cost data extracted from OSM) -- count is honestly 0,
        # not padded.
        node_recs += write_node_record(
            is_boundary=node.is_boundary,
            uppermost_identical_level=(node.uppermost_identical_level // 2) if node.uppermost_identical_level else 0,
            is_aggregated=node.is_aggregated,
            n_link_records=(14 if undecided else n_link_recs),
            is_parcel_boundary=False,
            has_traffic_light=False,
            is_rotary=False,
            link_record_offset=link_off,
            n_regulations=len(regs),
            n_between_links_cost=0,
        )
        if undecided:
            # spec: 1111(2) == undecided, and "the corresponding link
            # records are not created" -- but we already committed
            # link_buf above for round-trip purposes. Flag loudly: this
            # path is untested (no node in our extracted graph exceeds 14
            # links) rather than silently mis-encoding.
            raise NotImplementedError(
                f"node has {n_link_recs} links (>14); spec's 'undecided' "
                "case (link records omitted) is not implemented"
            )

    node_subframe = node_header + node_recs
    link_subframe = bytes(link_buf)

    # -- link cost table --
    n_with_time = sum(1 for c in graph.link_costs if c.has_avg_travel_time)
    n_without_time = len(graph.link_costs) - n_with_time
    lc_buf = write_link_cost_header(n_with_time, n_without_time)
    for c in graph.link_costs:
        lc_buf += write_link_cost_record(
            link_id_origin=c.link_id_origin,
            link_id_dest_delta=c.link_id_dest_delta,
            uppermost_identical_link_level=0,
            link_passage_status=0,
            is_toll=False,
            is_bypass=False,
            n_traffic_lights=0,
            forward_passable=c.forward_passable,
            reverse_passable=c.reverse_passable,
            has_center_line=False,
            crossable_oncoming_lane=False,
            same_cost_both_directions=(c.forward_passable == c.reverse_passable),
            has_statistics_cost=False,
            n_lanes_width_code=0,
            link_class_code=0,
            road_class_code=c.road_class,
            length_m=c.length_m,
            connected_node=c.connected_node,
            avg_travel_time_s=None,
        )
    link_cost_subframe = lc_buf

    # -- node coordinate table: one grid cell spanning the whole region
    # bbox (known simplification -- see module docstring) --
    lat_width = graph.lat_top - graph.lat_bottom
    lon_width = graph.lon_right - graph.lon_left
    ref_grid = write_reference_grid_record(graph.lat_bottom, graph.lon_left)
    node_coord_recs = bytearray()
    for node in graph.nodes:
        x = int(round((node.lon - graph.lon_left) / lon_width * 4095)) if lon_width else 0
        y = int(round((node.lat - graph.lat_bottom) / lat_width * 4095)) if lat_width else 0
        x = min(max(x, 0), 4095)
        y = min(max(y, 0), 4095)
        node_coord_recs += write_node_coord_record(0, x, y)
    nc_header = write_node_coord_header(
        lat_width_deg=lat_width, lon_width_deg=lon_width,
        n_lat_grids=1, n_lon_grids=1,
        ref_grid_table_offset=18, ref_grid_table_size=len(ref_grid),
        node_coord_table_offset=18 + len(ref_grid), node_coord_table_size=len(node_coord_recs),
    )
    node_coord_subframe = nc_header + ref_grid + bytes(node_coord_recs)

    aggregated_nodes = [graph.aggregated[i] for i in sorted(graph.aggregated)]
    road_ref_subframe = write_road_reference_table(aggregated_nodes)

    subframes = {
        "node": node_subframe,
        "link": link_subframe,
        "link_cost": link_cost_subframe,
        "upper_node": b"",
        "upper_link": b"",
        "passage_code": b"",
        "statistical_cost": b"",
        "node_coord": node_coord_subframe,
        "road_ref": road_ref_subframe,
    }

    ext0 = write_ext_frame(DISC_STAMP_12B, 0, b"")
    ext_frames = [ext0, b"", b"", b"", b"", b""]

    # -- assemble: distribution header (8B) + 9 basic mgmt entries (6B) +
    # 6 ext mgmt entries (6B) = 98 B, then basic payloads in
    # BASIC_MGMT_FIELDS order, then ext payloads --
    n_basic, n_ext = 9, 6
    header_len = 8 + n_basic * 6 + n_ext * 6
    off = header_len
    basic_entries = bytearray()
    basic_payload = bytearray()
    for name in BASIC_MGMT_FIELDS:
        data = subframes[name]
        if data:
            basic_entries += _u32(d32_enc(off)) + _u16(sws_enc(len(data)))
            basic_payload += data
            off += len(data)
        else:
            basic_entries += _u32(0xFFFFFFFF) + _u16(0)

    ext_entries = bytearray()
    ext_payload = bytearray()
    for data in ext_frames:
        if data:
            ext_entries += _u32(d32_enc(off)) + _u16(sws_enc(len(data)))
            ext_payload += data
            off += len(data)
        else:
            ext_entries += _u32(0xFFFFFFFF) + _u16(0)

    header = _u16(sws_enc(header_len)) + _u16(graph.region_no) + _u32(0)
    buf = bytes(header) + bytes(basic_entries) + bytes(ext_entries) + bytes(basic_payload) + bytes(ext_payload)
    return buf


# --------------------------------------------------------------------------
# Record-level decoders (inverse of the write_* functions above), used
# only by this script's own round-trip check -- NOT added to the shared
# kiwiw.route_planning decoder module, per the task's instruction not to
# touch shared parser files destructively. These intentionally mirror the
# bit layouts in route_planning_writer.py so a mismatch between "what we
# meant to write" and "what the bytes actually say" shows up as a
# decode failure/assertion, not a silent tautology.
# --------------------------------------------------------------------------

def decode_node_record(buf: bytes, off: int) -> dict:
    attr = u32(buf, off)
    w2 = u16(buf, off + 4)
    return {
        "uppermost_identical_level": extract(attr, 27, 29),
        "is_aggregated": bool(attr & (1 << 26)),
        "is_boundary": bool(attr & (1 << 25)),
        "n_link_records": extract(attr, 21, 24),
        "is_parcel_boundary": bool(attr & (1 << 20)),
        "has_traffic_light": bool(attr & (1 << 19)),
        "is_rotary": bool(attr & (1 << 18)),
        "link_record_offset": extract(attr, 0, 17),
        "n_regulations": extract(w2, 8, 15),
        "n_between_links_cost": extract(w2, 0, 7),
    }


def decode_link_record(buf: bytes, off: int, is_boundary: bool = False) -> dict:
    """Decode one Ch.10.7.1.1 Link Record. ``is_boundary`` must match the
    OWNING NODE's is_boundary flag (not a per-link property) -- per spec
    item (8), the record is 8 bytes (region_number present) for EVERY link
    of a boundary node, 6 bytes otherwise. Caller is responsible for
    stepping by link_record_size(is_boundary) between records."""
    adj = u16(buf, off) & 0x1FFF
    cost_idx = u16(buf, off + 2) & 0x7FFF
    fsr = u16(buf, off + 4)
    out = {
        "adjacent_node": adj,
        "link_cost_index": cost_idx,
        "is_suburb": bool(fsr & (1 << 15)),
        "is_semi_urban_highway": bool(fsr & (1 << 14)),
        "is_reverse_direction": bool(fsr & (1 << 13)),
        "following_same_road": extract(fsr, 9, 12),
        "angle_deg": extract(fsr, 0, 8),
        "region_number": None,
    }
    if is_boundary:
        out["region_number"] = u16(buf, off + 6)
    return out


def link_record_size(is_boundary: bool) -> int:
    return 8 if is_boundary else 6


def decode_regulation_record(buf: bytes, off: int) -> dict:
    b0, b1 = buf[off], buf[off + 1]
    return {
        "entry_link_no": None if (b0 >> 4) == 0xF else (b0 >> 4),
        "exit_link_no": None if (b0 & 0xF) == 0xF else (b0 & 0xF),
        "is_between_links": bool(b1 & 0x80),
        "passage_code": b1 & 0x7F,
    }


def decode_link_cost_record(buf: bytes, off: int) -> dict:
    link_id_origin = u32(buf, off)
    link_id_dest_delta = u16(buf, off + 4)
    w = u16(buf, off + 6)
    attr = u16(buf, off + 8)
    lw = u16(buf, off + 10)
    cn = u16(buf, off + 12)
    return {
        "link_id_origin": link_id_origin,
        "link_id_dest_delta": link_id_dest_delta,
        "uppermost_identical_link_level": extract(w, 13, 15),
        "link_passage_status": extract(w, 11, 12),
        "is_toll": bool(w & (1 << 10)),
        "is_bypass": bool(w & (1 << 9)),
        "n_traffic_lights": extract(w, 0, 8),
        "forward_passable": bool(attr & (1 << 15)),
        "reverse_passable": bool(attr & (1 << 14)),
        "road_class_code": attr & 0xF,
        "length_units": lw & 0xFFF,
        "length_mult": extract(lw, 12, 14),
        "connected_node": cn,
    }


def decode_node_coord_record(buf: bytes, off: int) -> dict:
    v = u32(buf, off)
    return {
        "grid_record_number": extract(v, 24, 31),
        "x": extract(v, 12, 23),
        "y": extract(v, 0, 11),
    }


def round_trip_check(graph: RpGraph, buf: bytes, n_basic: int = 9, n_ext: int = 6) -> dict:
    """Structural round trip: decode with the shared kiwiw.route_planning
    decoder (header/subframe-table level) + this script's own record
    decoders (node/link/regulation/link_cost/node_coord level), and
    verify everything is self-consistent with what we intended to
    encode."""
    rf = parse_rp_frame(buf, n_basic, n_ext)
    problems = []

    nh = rf.node_header
    n_nodes = len(graph.nodes)
    n_links = sum(len(n.links) for n in graph.nodes)
    if nh is None:
        problems.append("node_header failed to parse")
    else:
        if nh.n_nodes != n_nodes:
            problems.append(f"header n_nodes {nh.n_nodes} != graph {n_nodes}")
        if nh.n_links != n_links:
            problems.append(f"header n_links {nh.n_links} != graph {n_links}")
        if nh.n_ranks != 1:
            problems.append(f"expected 1 rank, header says {nh.n_ranks}")

    node_sub = rf.sub("node")
    link_sub = rf.sub("link")
    lc_sub = rf.sub("link_cost")
    ncoord_sub = rf.sub("node_coord")

    decoded_total_links = 0
    decoded_total_regs = 0
    node_rec_off = node_sub.offset + nh.header_size
    for i in range(n_nodes):
        rec = decode_node_record(buf, node_rec_off + i * 6)
        expect_links = min(len(graph.nodes[i].links), 14)
        if rec["n_link_records"] != expect_links:
            problems.append(f"node {i}: n_link_records {rec['n_link_records']} != {expect_links}")
        decoded_total_links += rec["n_link_records"]
        decoded_total_regs += rec["n_regulations"]
        link_off = link_sub.offset + rec["link_record_offset"]
        lrec_size = link_record_size(rec["is_boundary"])
        for j in range(rec["n_link_records"]):
            lrec = decode_link_record(buf, link_off + j * lrec_size, is_boundary=rec["is_boundary"])
            want = graph.nodes[i].links[j]
            if lrec["adjacent_node"] != want.adjacent_node:
                problems.append(f"node {i} link {j}: adjacent_node mismatch")
            if lrec["link_cost_index"] != want.link_cost_index:
                problems.append(f"node {i} link {j}: link_cost_index mismatch")
            if lrec["angle_deg"] != want.angle_deg:
                problems.append(f"node {i} link {j}: angle mismatch")
            if rec["is_boundary"]:
                want_region = want.region_number if want.region_number is not None else 0xFFFF
                if lrec["region_number"] != want_region:
                    problems.append(f"node {i} link {j}: region_number mismatch")
        reg_off = link_off + rec["n_link_records"] * lrec_size
        for k in range(rec["n_regulations"]):
            decode_regulation_record(buf, reg_off + k * 2)  # just verify it parses

    if decoded_total_links != n_links:
        problems.append(f"sum of node n_link_records {decoded_total_links} != graph n_links {n_links}")

    lc_header_size = 6
    for i, c in enumerate(graph.link_costs):
        rec = decode_link_cost_record(buf, lc_sub.offset + lc_header_size + i * 14)
        if rec["road_class_code"] != c.road_class:
            problems.append(f"link_cost {i}: road_class mismatch")
        if rec["connected_node"] != c.connected_node:
            problems.append(f"link_cost {i}: connected_node mismatch")
        recon_len = rec["length_units"] * (4 ** rec["length_mult"])
        if abs(recon_len - c.length_m) > max(4 ** rec["length_mult"], 1) * 1.0001:
            problems.append(f"link_cost {i}: length {recon_len} vs {c.length_m}")

    for i in range(n_nodes):
        rec = decode_node_coord_record(buf, ncoord_sub.offset + 18 + 6 + i * 4)
        if rec["grid_record_number"] != 0:
            problems.append(f"node_coord {i}: grid_record_number != 0")

    # -- road reference table (Ch.10.13 aggregated-intersection clustering)
    # -- decode with the SHARED kiwiw.route_planning decoder (not a local
    # mirror like the record decoders above), since that is the module
    # this project treats as the canonical Ch.10.13 reader.
    road_ref_sub = rf.sub("road_ref")
    node_records = None
    if node_sub is not None and nh is not None:
        try:
            node_records = parse_node_table(buf, node_sub, nh)
        except Exception as e:
            problems.append(f"road_ref: node table re-decode failed: {e}")
    decoded_aggregated = 0
    if road_ref_sub is not None:
        try:
            aggs = parse_road_reference_table(buf, road_ref_sub, node_records)
        except Exception as e:
            problems.append(f"road_ref: decode failed: {e}")
            aggs = []
        decoded_aggregated = len(aggs)
        if len(aggs) != len(graph.aggregated):
            problems.append(
                f"road_ref: decoded {len(aggs)} aggregated node records, "
                f"graph has {len(graph.aggregated)}"
            )
        want_node_numbers = sorted(graph.aggregated)
        got_node_numbers = [a.node_number for a in aggs]
        if got_node_numbers != want_node_numbers:
            problems.append(
                f"road_ref: node_number sequence {got_node_numbers} != "
                f"expected {want_node_numbers}"
            )
        for a in aggs:
            want = graph.aggregated.get(a.node_number)
            if want is None:
                continue
            if a.n_composition_links != len(want.composition_link_cost_numbers):
                problems.append(f"road_ref node {a.node_number}: n_composition_links mismatch")
            if a.n_subordinate_nodes != len(want.subordinate_node_offsets):
                problems.append(f"road_ref node {a.node_number}: n_subordinate_nodes mismatch")
            if a.composition_link_cost_numbers != want.composition_link_cost_numbers:
                problems.append(f"road_ref node {a.node_number}: composition_link_cost_numbers mismatch")
            if a.subordinate_node_offsets != want.subordinate_node_offsets:
                problems.append(f"road_ref node {a.node_number}: subordinate_node_offsets mismatch")
            if a.subordinate_node_order_by_link != want.subordinate_node_order_by_link:
                problems.append(f"road_ref node {a.node_number}: subordinate_node_order_by_link mismatch")

    return {
        "problems": problems,
        "header_n_nodes": nh.n_nodes if nh else None,
        "header_n_links": nh.n_links if nh else None,
        "decoded_total_links": decoded_total_links,
        "decoded_total_regs": decoded_total_regs,
        "decoded_aggregated": decoded_aggregated,
        "subframes": {s.name: (s.offset, s.size) for s in rf.basic},
        "buf_len": len(buf),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pbf", default=brg.DEFAULT_PBF)
    ap.add_argument("--road-classes", default="2,3",
                    help="comma list of Ch.32.2 road classes to include, matching region 178's own road_class_mask (2,3)")
    args = ap.parse_args()

    class_to_hw = {v: k for k, v in brg.ROAD_CLASS.items()}
    wanted_classes = {int(x) for x in args.road_classes.split(",")}
    brg.ROADS = {hw for hw, cls in brg.ROAD_CLASS.items() if cls in wanted_classes}
    print(f"Using OSM highway tags: {sorted(brg.ROADS)}")

    graph, stats = brg.build_graph(args.pbf, REGION_178_BBOX, region_no=178)
    print("OSM extraction stats:", stats)

    buf = encode_rp_frame(graph)
    print(f"Encoded RP frame: {len(buf)} bytes")

    result = round_trip_check(graph, buf)
    print("Round-trip check:")
    for k, v in result.items():
        if k != "problems":
            print(f"  {k}: {v}")
    if result["problems"]:
        print(f"  PROBLEMS ({len(result['problems'])}):")
        for p in result["problems"][:20]:
            print(f"    - {p}")
        if len(result["problems"]) > 20:
            print(f"    ... and {len(result['problems']) - 20} more")
    else:
        print("  No problems found: fully self-consistent round trip.")

    print()
    print("Sanity check vs real disc region_no=178, level=2:")
    print(f"  real:      n_nodes={REGION_178_REAL['n_nodes']}  n_links={REGION_178_REAL['n_links']}")
    print(f"  generated: n_nodes={len(graph.nodes)}  n_links={sum(len(n.links) for n in graph.nodes)}")
    ratio = len(graph.nodes) / REGION_178_REAL["n_nodes"]
    print(f"  ratio (generated/real nodes): {ratio:.1f}x")


if __name__ == "__main__":
    main()
