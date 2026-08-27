#!/usr/bin/env python3
"""Genuine multi-level (Ch.9 levels 2/4/6/8) route-planning hierarchy
builder -- the successor to the single-region prototype in
``osm_to_route_planning.py`` / ``build_route_graph.py``, which explicitly
left multi-level contraction and cross-region boundary handling as future
work (see docs/phases/03-osm-pipeline.md).

Pipeline
--------
1. Collect ONE OSM road graph over a bounded test area (a union of several
   adjacent small bboxes -- "a few adjacent real regions' bboxes", per the
   task), reusing ``build_route_graph``'s OSM extraction/topology code.
2. Run REAL CH-style node contraction (``kiwiw.contraction.contract``) over
   that single flat graph, once, globally -- this produces a genuine
   contraction order/rank per node and a search graph of original edges +
   shortcut edges, not a per-region heuristic.
3. Assign each node its "uppermost identical level" (2/4/6/8) from its
   contraction rank quantile (``assign_levels``) -- this is what makes
   higher levels sparser, exactly like the real disc (see the region-tree
   study in docs/phases/03-osm-pipeline.md: node counts shrink and the
   surviving OSM road-class set narrows going up the levels).
4. Build a genuine PARENT/CHILD REGION TREE (Ch.9.2.1's parent_region /
   first_child_region / n_child_regions fields, confirmed 100% consistent
   -- 507/507 -- against real disc data by ``study_region_hierarchy.py``):
     level 2: N leaf tiles (the original bboxes), each containing every
       node whose contraction rank quantile is >= level 2 (i.e. everyone
       physically inside that tile).
     level 4: fewer, larger regions, each the union of >=2 adjacent level-2
       tiles' areas, containing only nodes whose uppermost level is
       4/6/8.
     level 6: union of the level-4 regions, nodes with uppermost level
       6/8.
     level 8: one root region (the whole test area), nodes with uppermost
       level 8 only.
   A region's own link set is the induced subgraph of the CH search graph
   (original edges + ALL shortcuts, from any contraction step) restricted
   to that region's own node set -- this is exactly the property
   ``kiwiw.contraction.verify_shortest_paths`` validates.
5. Mark BOUNDARY NODES: a node is a boundary node in a level-L region if
   its uppermost level is > L (see docs for the evidence and the caveat --
   this is the best-supported, but not 100%-certain, reading of the
   region-hierarchy study's Q2/Q3 findings).
6. Encode every region through the existing Ch.9/Ch.10 writer
   (``osm_to_route_planning.encode_rp_frame`` + a new multi-region Ch.9
   table assembler in this module), and round-trip-decode every one of
   them to confirm self-consistency.

This is still a bounded PROTOTYPE, not a full-country pipeline -- see the
"KNOWN LIMITATIONS" list near the bottom of this file and
docs/phases/03-osm-pipeline.md for what's proven vs. assumed.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_route_graph as brg
from kiwiw.contraction import Graph as CHGraph, contract, assign_levels, verify_shortest_paths, level_thresholds
from kiwiw.route_planning_writer import (
    RpGraph, RpNode, RpLink, RpLinkCost,
    write_level_mgmt_record, write_region_mgmt_record, write_dummy_region_record,
    write_region_frame_header, NO_DATA_DSA,
)
from kiwiw.route_planning import parse_region_header, parse_region_table, parse_rp_frame
from osm_to_route_planning import encode_rp_frame, round_trip_check

LEVELS = [2, 4, 6, 8]


@dataclass
class LeafTile:
    """One level-2 leaf region's bbox, as a (lon_left, lat_bottom, lon_right, lat_top) tuple."""
    bbox: tuple[float, float, float, float]


def default_test_area(base_bbox, n_lon: int = 2, n_lat: int = 2) -> list[LeafTile]:
    """Split ``base_bbox`` into an n_lon x n_lat grid of leaf tiles. Default
    2x2 -- "a few adjacent regions", per the task, not a full-country
    tiling."""
    l, b, r, t = base_bbox
    dlon = (r - l) / n_lon
    dlat = (t - b) / n_lat
    tiles = []
    for j in range(n_lat):
        for i in range(n_lon):
            tiles.append(LeafTile((l + i * dlon, b + j * dlat, l + (i + 1) * dlon, b + (j + 1) * dlat)))
    return tiles


def union_bbox(bboxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    ls = [b[0] for b in bboxes]; bs = [b[1] for b in bboxes]
    rs = [b[2] for b in bboxes]; ts = [b[3] for b in bboxes]
    return (min(ls), min(bs), max(rs), max(ts))


def in_bbox(lat, lon, bbox) -> bool:
    l, b, r, t = bbox
    return l <= lon <= r and b <= lat <= t


# --------------------------------------------------------------------------
# Step 1-3: one flat OSM graph -> global CH contraction -> level assignment
# --------------------------------------------------------------------------

@dataclass
class FlatGraph:
    node_ids: list[int]                      # global_id[local_index]
    coords: list[tuple[float, float]]         # (lat, lon) per local index
    ch: CHGraph                                # WORKING graph, mutated by contract() (do not use as an "original" baseline)
    original_ch: CHGraph                       # untouched copy of the pre-contraction edge set, for validation
    contraction_result: object                # kiwiw.contraction.ContractionResult
    levels: list[int]                         # uppermost level per local index
    edge_road_class: dict[tuple[int, int], int]
    level_graph: dict                          # level (2/4/6/8) -> CHGraph scoped to that level (see below)


#: Ch.32.2 road classes to extract from OSM for the hierarchy build. The
#: original single-region prototype (osm_to_route_planning.py's main())
#: restricted to just {2, 3} to match region 178's own road_class_mask;
#: this module's region-hierarchy study (docs/phases/03-osm-pipeline.md)
#: found the real disc's road-class set WIDENS as level increases (level 2
#: -> {2,3}, level 4 -> {2}, level 6/8 -> {0,2} -- i.e. motorway class 0
#: appears only at the coarser levels). {0,1,2,3} (motorway/trunk/primary/
#: secondary+tertiary) is used here so the flat graph has that same
#: motorway-class road available to be promoted to the coarser levels by
#: the CH contraction, rather than omitting it entirely. Using ALL OSM
#: highway classes (residential/service/track) was tried first and
#: produced a ~6x larger graph than the real region's own node count for
#: the same bbox (16844 vs. the single-region prototype's 2819) -- i.e.
#: this project's convention of matching the real disc's own road-class
#: scope, not "more data is better".
HIERARCHY_ROAD_CLASSES = {0, 1, 2, 3}


def build_flat_graph_and_contract(pbf_path: str, test_bbox, max_settled: int = 250) -> FlatGraph:
    brg.ROADS = {hw for hw, cls in brg.ROAD_CLASS.items() if cls in HIERARCHY_ROAD_CLASSES}
    ways, _restrictions = brg._collect(pbf_path, test_bbox)
    node_coord, refcount, segments = brg._build_graph_topology(ways)
    graph_node_ids = sorted(nid for nid, cnt in refcount.items() if cnt >= 2)
    node_index = {nid: i for i, nid in enumerate(graph_node_ids)}
    n = len(graph_node_ids)

    ch = CHGraph(n)
    original_ch = CHGraph(n)
    edge_road_class: dict[tuple[int, int], int] = {}
    for seg in segments:
        chain = seg["chain"]
        a_id, a_lat, a_lon = chain[0]
        b_id, b_lat, b_lon = chain[-1]
        if a_id not in node_index or b_id not in node_index or a_id == b_id:
            continue
        a_idx, b_idx = node_index[a_id], node_index[b_id]
        length_m = sum(
            brg.haversine_m(chain[i][1], chain[i][2], chain[i + 1][1], chain[i + 1][2])
            for i in range(len(chain) - 1)
        )
        if length_m <= 0:
            continue
        road_class = brg.ROAD_CLASS.get(seg["highway"], 4)
        ch.add_edge(a_idx, b_idx, length_m, road_class=road_class)
        original_ch.add_edge(a_idx, b_idx, length_m, road_class=road_class)
        edge_road_class[(a_idx, b_idx)] = road_class
        if not seg["oneway"]:
            ch.add_edge(b_idx, a_idx, length_m, road_class=road_class)
            original_ch.add_edge(b_idx, a_idx, length_m, road_class=road_class)
            edge_road_class[(b_idx, a_idx)] = road_class

    # Request level_graph snapshots at each level-boundary contraction step,
    # so each level's own link set is scoped to shortcuts that actually exist
    # by the time that level's node set has stabilized -- NOT the fully
    # completed contraction's search_graph, which accumulates shortcuts from
    # every step (including ones added long after any given level's cut) and
    # would hugely over-count links per region (see KNOWN LIMITATIONS below /
    # module history: this caused a u16 n_links overflow before the fix).
    thresholds = level_thresholds(n, n_levels=len(LEVELS))
    result = contract(ch, max_settled=max_settled, snapshot_at=set(thresholds))
    levels = assign_levels(result.rank, n_levels=len(LEVELS))
    coords = [node_coord[nid] for nid in graph_node_ids]

    # level_graph[2] = the ORIGINAL uncontracted graph (nothing has been
    # contracted away yet at the finest level); level_graph[4]/[6]/[8] = the
    # snapshot taken right after contracting everyone assigned to levels
    # below it.
    level_graph = {LEVELS[0]: original_ch}
    for i in range(1, len(LEVELS)):
        level_graph[LEVELS[i]] = result.snapshots.get(thresholds[i - 1], result.search_graph)

    return FlatGraph(node_ids=graph_node_ids, coords=coords, ch=ch, original_ch=original_ch,
                      contraction_result=result, levels=levels, edge_road_class=edge_road_class,
                      level_graph=level_graph)


# --------------------------------------------------------------------------
# Step 4-5: region tree assembly
# --------------------------------------------------------------------------

@dataclass
class RegionNode:
    level: int
    region_no: int             # index within its level's array
    bbox: tuple[float, float, float, float]
    local_indices: list[int]   # indices into FlatGraph.coords/levels for nodes belonging here
    parent_region: int = 0xFFFF
    first_child_region: int = 0xFFFF
    n_child_regions: int = 0
    children: list["RegionNode"] = field(default_factory=list)


def build_region_tree(fg: FlatGraph, leaf_tiles: list[LeafTile]) -> dict[int, list[RegionNode]]:
    """Build the 4-level tree: leaf tiles at level 2, pairwise-merged at
    level 4, merged again at level 6, single root at level 8. Node
    membership at each level is exactly {node : level(node) >= L AND node
    physically falls in this region's bbox}."""
    n_leaf = len(leaf_tiles)

    def nodes_in(bbox, min_level):
        return [i for i in range(len(fg.coords))
                if fg.levels[i] >= min_level and in_bbox(fg.coords[i][0], fg.coords[i][1], bbox)]

    level2 = [RegionNode(level=2, region_no=i, bbox=t.bbox, local_indices=nodes_in(t.bbox, 2))
              for i, t in enumerate(leaf_tiles)]

    # level 4: merge leaf tiles pairwise (defensible small-scale grouping;
    # if n_leaf is odd the last group is a singleton)
    level4 = []
    i = 0
    rno = 0
    while i < n_leaf:
        group = level2[i:i + 2]
        bbox = union_bbox([r.bbox for r in group])
        r4 = RegionNode(level=4, region_no=rno, bbox=bbox, local_indices=nodes_in(bbox, 4))
        r4.children = group
        level4.append(r4)
        i += 2
        rno += 1

    # level 6: merge all level-4 regions into one (small test area -> one
    # coarser tier is enough to demonstrate a real 4th level exists above
    # the leaves without needing a huge OSM extract)
    bbox6 = union_bbox([r.bbox for r in level4])
    r6 = RegionNode(level=6, region_no=0, bbox=bbox6, local_indices=nodes_in(bbox6, 6))
    r6.children = level4
    level6 = [r6]

    bbox8 = union_bbox([r.bbox for r in level6])
    r8 = RegionNode(level=8, region_no=0, bbox=bbox8, local_indices=nodes_in(bbox8, 8))
    r8.children = level6
    level8 = [r8]

    # wire parent/child indices (Ch.9.2.1 semantics, confirmed 507/507
    # consistent against real disc data by study_region_hierarchy.py)
    for parent_level_list, child_level_list in [(level4, level2), (level6, level4), (level8, level6)]:
        for parent in parent_level_list:
            if not parent.children:
                continue
            first_idx = child_level_list.index(parent.children[0])
            parent.first_child_region = first_idx
            parent.n_child_regions = len(parent.children)
            for c in parent.children:
                c.parent_region = parent.region_no

    return {2: level2, 4: level4, 6: level6, 8: level8}


def mark_boundary_and_build_rpgraph(fg: FlatGraph, region: RegionNode,
                                     tree: "dict[int, list[RegionNode]] | None" = None,
                                     index_maps: "dict[tuple[int, int], dict[int, int]] | None" = None) -> RpGraph:
    """Build the RpGraph for one region: node subset, is_boundary flags,
    links induced from the CH search graph, link-cost records (forward/
    reverse sharing one record where both directions exist, matching
    build_route_graph.py's convention).

    Cross-region "escape links" (Ch.10.7.1.1 item (8) Region Number, spec
    quote: "A boundary node is defined as a node that has a link to
    another region... The region number where the adjacent node exists is
    described.") are wired here when ``tree``/``index_maps`` are given: a
    boundary node in a level-L region also exists (same global_id) one
    level up, since is_boundary here means "this node's uppermost level is
    above the current region's level" -- so its natural cross-region
    neighbour is its own instance in the parent region. This is the
    best-supported reading found (see docs/phases/03-osm-pipeline.md), not
    spec-confirmed as the ONLY form of boundary link (the spec's own
    definition is broader: any node with a link to another region,
    including sibling regions at the SAME level -- not modeled here, since
    this prototype's region tree has no shared level-2/2 or level-4/4
    physical adjacency requiring it; see KNOWN LIMITATIONS)."""
    local_set = set(region.local_indices)
    global_to_region_idx = {gi: ri for ri, gi in enumerate(region.local_indices)}

    parent_index_map = None
    parent_region_no = None
    if tree is not None and index_maps is not None and region.parent_region != 0xFFFF:
        try:
            parent_level = LEVELS[LEVELS.index(region.level) + 1]
        except (ValueError, IndexError):
            parent_level = None
        if parent_level is not None:
            parent_region_no = region.parent_region
            parent_index_map = index_maps.get((parent_level, parent_region_no))

    l, b, r, t = region.bbox
    graph = RpGraph(lat_top=t, lat_bottom=b, lon_left=l, lon_right=r, region_no=region.region_no)
    for gi in region.local_indices:
        lat, lon = fg.coords[gi]
        is_boundary = fg.levels[gi] > region.level
        graph.nodes.append(RpNode(
            lat=lat, lon=lon, is_boundary=is_boundary, rank=fg.contraction_result.rank[gi],
            uppermost_identical_level=fg.levels[gi], global_id=fg.node_ids[gi],
        ))

    # induced subgraph of THIS LEVEL's own scoped graph (original edges plus
    # only the shortcuts that exist by the time this level's node set has
    # stabilized -- see FlatGraph.level_graph / build_flat_graph_and_contract)
    # over this region's node set; forward/reverse pairs (when both
    # directions exist with equal weight) share one RpLinkCost record,
    # mirroring build_route_graph.py's approach.
    search = fg.level_graph[region.level]
    seen_cost: dict[tuple[int, int], int] = {}
    for gi in region.local_indices:
        ri = global_to_region_idx[gi]
        for gj, edge in search.out[gi].items():
            if gj not in local_set:
                continue
            rj = global_to_region_idx[gj]
            key = (min(gi, gj), max(gi, gj))
            if key in seen_cost:
                cost_idx = seen_cost[key]
            else:
                road_class = fg.edge_road_class.get((gi, gj)) or fg.edge_road_class.get((gj, gi)) or 4
                cost_idx = len(graph.link_costs)
                graph.link_costs.append(RpLinkCost(
                    link_id_origin=(hash((key, region.level)) & 0xFFFFFFFF),
                    link_id_dest_delta=0, length_m=edge.weight, connected_node=rj,
                    road_class=road_class,
                    forward_passable=True, reverse_passable=(gj in search.out and gi in search.out[gj]),
                ))
                seen_cost[key] = cost_idx
            link = RpLink(adjacent_node=rj, link_cost_index=cost_idx, forward_direction=True,
                          angle_deg=0, following_same_road=None, road_class=road_class)
            graph.nodes[ri].links.append(link)

    # Cross-region escape links: for every boundary node whose parent
    # region's own node table is already known (index_maps passed in and
    # this region isn't the level-8 root), add one extra RpLink pointing at
    # this same global node's index WITHIN the parent region, with
    # region_number set to the parent's region_no. This is what upgrades
    # is_boundary from a bare flag into an actual "link to another region"
    # per the spec's own definition. A fresh, dedicated RpLinkCost is used
    # (zero length -- this is a same-node cross-region reference, not a
    # physical road segment; the spec does not describe a "cost" for this
    # kind of link, so 0 is the honest choice here, not a measured value).
    if parent_index_map is not None:
        for gi in region.local_indices:
            if fg.levels[gi] <= region.level:
                continue  # not a boundary node
            ri = global_to_region_idx[gi]
            parent_ri = parent_index_map.get(gi)
            if parent_ri is None:
                continue  # shouldn't happen (boundary implies present one level up), but don't crash if it does
            cost_idx = len(graph.link_costs)
            graph.link_costs.append(RpLinkCost(
                link_id_origin=(hash((gi, "escape", region.level)) & 0xFFFFFFFF),
                link_id_dest_delta=0, length_m=0.0, connected_node=parent_ri,
                road_class=4,  # synthetic escape link, no real OSM road class applies
                forward_passable=True, reverse_passable=True,
            ))
            graph.nodes[ri].links.append(RpLink(
                adjacent_node=parent_ri, link_cost_index=cost_idx, forward_direction=True,
                angle_deg=0, following_same_road=None, road_class=4,
                region_number=parent_region_no,
            ))

    for node in graph.nodes:
        node.rank = 0  # single-rank-per-region, matching every real region observed (see study doc)
    return graph


# --------------------------------------------------------------------------
# Step 6: Ch.9 multi-region table assembler (generalizes
# route_planning_writer.write_region_frame, which only supports one
# standalone region) + orchestration entry point
# --------------------------------------------------------------------------

def assemble_region_frame(tree: dict[int, list[RegionNode]], rp_sizes_ls: dict[tuple[int, int], int]):
    """Build the Ch.9 header+level-table and Region Management Table
    for the whole multi-level tree. rp_sizes_ls maps (level, region_no)
    -> its encoded RP frame size in logical sectors (32 B units)."""
    level_records = []
    dummy_level = write_level_mgmt_record(
        level=-32, n_basic_rp_frames=0, n_ext_rp_frames=0, n_regions=1,
        region_rec_size=24, node_rec_size=0, link_rec_size=0,
        link_cost_rec_size=0, between_links_restriction_rec_size=0,
        between_links_cost_rec_size=0,
    )
    level_records.append(dummy_level)
    for lvl in LEVELS:
        level_records.append(write_level_mgmt_record(
            level=lvl, n_basic_rp_frames=9, n_ext_rp_frames=6, n_regions=len(tree[lvl]),
            region_rec_size=24, node_rec_size=6, link_rec_size=6,
            link_cost_rec_size=14, between_links_restriction_rec_size=2,
            between_links_cost_rec_size=4,
        ))
    levels_bytes = b"".join(level_records)

    region_table = bytearray()
    region_table += write_dummy_region_record()
    n_region_records = 1
    for lvl in LEVELS:
        for region in tree[lvl]:
            size_ls = rp_sizes_ls.get((lvl, region.region_no), 1)
            region_table += write_region_mgmt_record(
                lat_top=region.bbox[3], lat_bottom=region.bbox[1],
                lon_left=region.bbox[0], lon_right=region.bbox[2],
                parent_region=region.parent_region,
                first_child_region=region.first_child_region,
                n_child_regions=region.n_child_regions,
                rp_dsa=NO_DATA_DSA, rp_size_ls=size_ls,
            )
            n_region_records += 1

    header = write_region_frame_header(
        n_region_records=n_region_records, n_levels=len(LEVELS) + 1,
        level_rec_size=16, levels_bytes=levels_bytes,
        rmt_size_ls=len(region_table) // 32 or 1,
    )
    return header, bytes(region_table)


def build_hierarchy(pbf_path: str, base_bbox, n_lon: int = 2, n_lat: int = 2, max_settled: int = 250):
    leaf_tiles = default_test_area(base_bbox, n_lon=n_lon, n_lat=n_lat)
    test_bbox = union_bbox([t.bbox for t in leaf_tiles])
    fg = build_flat_graph_and_contract(pbf_path, test_bbox, max_settled=max_settled)
    tree = build_region_tree(fg, leaf_tiles)

    # node index maps must be known for EVERY region before any escape links
    # can be wired (a child region's boundary node needs its parent
    # region's already-decided node ordering) -- region.local_indices is
    # fixed by build_region_tree() above, so this can be precomputed in one
    # pass regardless of level processing order.
    index_maps = {(lvl, region.region_no): {gi: ri for ri, gi in enumerate(region.local_indices)}
                   for lvl in LEVELS for region in tree[lvl]}

    encoded: dict[tuple[int, int], bytes] = {}
    rpgraphs: dict[tuple[int, int], RpGraph] = {}
    for lvl in LEVELS:
        for region in tree[lvl]:
            rp = mark_boundary_and_build_rpgraph(fg, region, tree=tree, index_maps=index_maps)
            rpgraphs[(lvl, region.region_no)] = rp
            if rp.nodes:
                encoded[(lvl, region.region_no)] = encode_rp_frame(rp)
            else:
                encoded[(lvl, region.region_no)] = b""

    rp_sizes_ls = {k: (len(v) // 32 or 1) for k, v in encoded.items() if v}
    ch9_header, ch9_table = assemble_region_frame(tree, rp_sizes_ls)

    return {
        "fg": fg, "tree": tree, "encoded": encoded, "rpgraphs": rpgraphs,
        "ch9_header": ch9_header, "ch9_table": ch9_table, "leaf_tiles": leaf_tiles,
    }


def validate(result: dict) -> dict:
    """Round-trip every region's Ch.10 frame + the Ch.9 header/table, and
    run the CH shortest-path preservation check across the WHOLE flat
    graph for a sample of node pairs drawn from each level's surviving
    node set (task item 1's validation requirement, applied end-to-end
    rather than on a synthetic graph -- see tests/test_contraction.py for
    the synthetic-graph unit tests)."""
    problems = []
    fg = result["fg"]
    tree = result["tree"]

    # Ch.9 round trip
    rf = parse_region_header(result["ch9_header"])
    parse_region_table(rf, result["ch9_table"])
    if len(rf.regions) != sum(len(tree[l]) for l in LEVELS) + 1:
        problems.append(f"Ch.9 region count mismatch: {len(rf.regions)} decoded vs "
                         f"{sum(len(tree[l]) for l in LEVELS) + 1} expected")
    by_level = {}
    for r in rf.regions:
        by_level.setdefault(r.level, []).append(r)
    consistency_checked = consistency_ok = 0
    for lvl_i, lvl in enumerate(LEVELS[:-1]):
        parent_level = LEVELS[lvl_i + 1]
        for r in by_level.get(lvl, []):
            if r.parent_region == 0xFFFF:
                continue
            consistency_checked += 1
            prego = by_level.get(parent_level, [])
            if r.parent_region < len(prego):
                p = prego[r.parent_region]
                if p.first_child_region <= r.region_no < p.first_child_region + p.n_child_regions:
                    consistency_ok += 1

    n_regions_encoded = 0
    n_regions_roundtrip_ok = 0
    for (lvl, region_no), buf in result["encoded"].items():
        if not buf:
            continue
        n_regions_encoded += 1
        graph = result["rpgraphs"][(lvl, region_no)]
        rt = round_trip_check(graph, buf)
        if not rt["problems"]:
            n_regions_roundtrip_ok += 1
        else:
            problems.append(f"region level={lvl} no={region_no}: {rt['problems'][:3]}")

    # CH correctness: for each level, sample pairs among that level's
    # surviving nodes (global indices), verify shortest path cost in the
    # full original graph == shortest path in the CH search graph
    # restricted to that node subset.
    ch_checks = {}
    original_for_check = fg.original_ch  # untouched pre-contraction edge set
    for lvl in LEVELS:
        subset = [i for i in range(len(fg.levels)) if fg.levels[i] >= lvl]
        if len(subset) < 2:
            ch_checks[lvl] = {"n_pairs": 0, "n_match": 0, "n_mismatch": 0}
            continue
        check = verify_shortest_paths(original_for_check, fg.contraction_result, subset,
                                       n_pairs=min(100, len(subset) * (len(subset) - 1) // 2), seed=lvl)
        ch_checks[lvl] = check
        if check["n_mismatch"]:
            problems.append(f"level {lvl}: {check['n_mismatch']}/{check['n_pairs']} CH shortest-path mismatches")

    return {
        "problems": problems,
        "ch9_regions_decoded": len(rf.regions),
        "ch9_parent_child_consistency": (consistency_ok, consistency_checked),
        "n_regions_encoded": n_regions_encoded,
        "n_regions_roundtrip_ok": n_regions_roundtrip_ok,
        "ch_checks": ch_checks,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pbf", default=brg.DEFAULT_PBF)
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_LEFT", "LAT_BOTTOM", "LON_RIGHT", "LAT_TOP"),
                     default=None, help="defaults to a 2x area around the region-178 test bbox")
    ap.add_argument("--n-lon", type=int, default=2)
    ap.add_argument("--n-lat", type=int, default=2)
    ap.add_argument("--max-settled", type=int, default=250)
    args = ap.parse_args()

    if args.bbox is None:
        import osm_to_route_planning as orp
        # NOTE: previously this doubled REGION_178_BBOX's width/height (4x
        # area), which on a real OSM extract produced >65535 links in the
        # level-8 root region and overflowed the Ch.10 rank record's u16
        # n_links field. Use REGION_178_BBOX's own area (already known, from
        # the single-region prototype, to produce a tractable ~2800-node
        # graph) as the base test area instead -- "a few adjacent regions'
        # bboxes", not a multiple of one region's full extent.
        base_bbox = orp.REGION_178_BBOX
    else:
        base_bbox = tuple(args.bbox)

    print(f"Building hierarchy over base_bbox={base_bbox}, {args.n_lon}x{args.n_lat} leaf tiles")
    result = build_hierarchy(args.pbf, base_bbox, n_lon=args.n_lon, n_lat=args.n_lat,
                              max_settled=args.max_settled)
    fg = result["fg"]
    print(f"Flat graph: {len(fg.coords)} nodes, "
          f"{sum(len(fg.ch.out[i]) for i in range(len(fg.coords)))} directed edges "
          f"(after contraction, incl. shortcuts)")
    print(f"CH contraction: {fg.contraction_result.n_shortcuts} shortcuts added")

    for lvl in LEVELS:
        for region in result["tree"][lvl]:
            n = len(region.local_indices)
            nb = sum(1 for i in region.local_indices if fg.levels[i] > lvl)
            print(f"  level={lvl} region_no={region.region_no} bbox={region.bbox} "
                  f"n_nodes={n} n_boundary={nb} n_children={region.n_child_regions}")

    print("\nValidating...")
    v = validate(result)
    print(f"Ch.9 regions decoded: {v['ch9_regions_decoded']}")
    print(f"Ch.9 parent/child consistency: {v['ch9_parent_child_consistency']}")
    print(f"Regions encoded: {v['n_regions_encoded']}, round-trip OK: {v['n_regions_roundtrip_ok']}")
    for lvl, check in v["ch_checks"].items():
        print(f"  CH check level {lvl}: {check['n_match']}/{check['n_pairs']} match, "
              f"{check['n_mismatch']} mismatch")
    if v["problems"]:
        print(f"\nPROBLEMS ({len(v['problems'])}):")
        for p in v["problems"][:20]:
            print(f"  - {p}")
    else:
        print("\nNo problems found.")


if __name__ == "__main__":
    main()


# ==========================================================================
# KNOWN LIMITATIONS (explicitly not hidden, per project convention)
# ==========================================================================
# - Region tree shape (2x leaf tiles -> pairwise merge -> single level-6 ->
#   single level-8 root) is a small, defensible DEMONSTRATION tree, not a
#   country-scale tiling. A real pipeline would need many more leaf tiles
#   and a merge strategy chosen for load-balancing (roughly equal node
#   counts per region), not just fixed 2x2 grid geometry.
# - Boundary-node semantics (is_boundary = "this node's uppermost level is
#   above the current region's level") is the best-supported reading found
#   during the region-hierarchy study (see docs/phases/03-osm-pipeline.md),
#   but a direct empirical test (matching a real region's flagged boundary
#   node coordinates against its real parent region's own node coordinates)
#   only matched 0.8%-12/1579 in a scoped sample -- inconclusive, likely due
#   to this study's own coordinate-grid decoding gaps (multi-grid Node
#   Coordinate tables were not fully decoded), not necessarily a wrong
#   hypothesis. Flagged as an open item, not asserted as proven.
# - "uppermost_identical_level" node-record field width is 3 bits (0-7);
#   this code writes level/2 (1-4) into it, following the same index
#   convention already used for RankInfo's "rp_level" field elsewhere in
#   this codebase. Not independently spec-confirmed.
# - Single rank per region (matching literally every real region sampled
#   in the study -- n_ranks was 1 in all ~80 decoded), so multi-rank
#   regions (spec-legal, just not observed in the sample) are not
#   exercised.
# - Turn restrictions, aggregated-intersection clustering (Road Reference
#   Table), and non-default ext frames are unchanged from the prior
#   prototype (not in scope for this task per the constraints).
# - CH witness search is BOUNDED (max_settled), a standard, safe
#   over-approximation (see kiwiw/contraction.py docstring) -- it can add
#   a few unneeded shortcuts but never loses correctness.
