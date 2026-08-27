#!/usr/bin/env python3
"""Build an in-memory routing graph (kiwiw.route_planning_writer.RpGraph)
from OSM data for a single bounded test region, as the first stage of the
Ch.9/Ch.10 write-path prototype (see docs/phases/01-format-analysis.md,
"Route planning / region data" section, for the read-path this inverts).

This is a PROTOTYPE for ONE bounded test region -- not a full-country
pipeline. It is deliberately a first-pass heuristic in the areas the task
explicitly allows (hierarchy-level selection, turn-regulation coverage);
see the module-level "KNOWN SIMPLIFICATIONS" list below and the mirrored
list in route_planning_writer.py's docstring.

Pipeline:
  1. Stream the OSM PBF once (pyosmium, locations=True) collecting every
     way tagged with a routable ``highway=*`` value whose bounding box
     intersects the requested region bbox, plus the referenced nodes'
     coordinates.
  2. Split ways at shared nodes (any node referenced by >1 way, or a
     way's own endpoints) to get graph edges between "intersection or
     endpoint" nodes -- the spec's Node/Link model (10.6/10.7).
  3. Assign each node a single "rank" (10.6.1 Rank Management Information)
     using OSM highway class as a first-pass hierarchy-level heuristic
     (task item 1's explicitly-sanctioned simplification): rank 0 = the
     highest class present, ranks group by Ch.32.2 road-class code.
  4. Compute each link's real-world length (haversine over the original
     way's node chain between the two graph nodes) and OSM->KIWI road
     class (Ch.32.2).
  5. Parse OSM turn-restriction relations (``type=restriction``) that
     reference ways/nodes inside the graph into regulation records
     (10.7.1.2), where resolvable to two links physically meeting at one
     graph node -- otherwise dropped (see KNOWN SIMPLIFICATIONS).

KNOWN SIMPLIFICATIONS (task item 1/3 -- explicitly flagged, not silently
assumed away):
  - Hierarchy is single-level relative to OSM highway class, not a real
    multi-region level-2/4/6/8 contraction hierarchy: this prototype
    builds ONE region/one RP frame, so there is no "between-region"
    coarsening to validate at all. The "Corresponding Route Planning
    Data Level" per rank is set from the highway-class rank, following
    the *shape* of 10.6.1 but not exercising multi-level linkage.
  - Every OSM node with degree 1 or >=3 becomes a graph node (a proper
    intersection/endpoint set); a chain of degree-2 nodes along one way is
    collapsed into a single link, matching the spec's Node/Link
    abstraction. Roundabouts are not specially detected as "rotary" nodes
    (the node record's `is_rotary` flag is always False) -- OSM
    `junction=roundabout` is not consulted; a documented simplification,
    not a spec ambiguity.
  - Turn restrictions: only ``restriction=no_*``/``only_*`` relations
    with exactly one ``from`` way, one ``to`` way, and zero or one ``via``
    node (not ``via`` way chains) are translated, and only when both ways
    are present as links meeting at the same graph node in our graph.
    Complex (via-way) restrictions are skipped, and are the overwhelming
    minority in OSM data generally.
  - No boundary-node / cross-region bookkeeping: the whole bbox is one
    self-contained region, so no node is marked a boundary node, no link
    carries a region number, and there is no upper-level node/link table
    (matching the real disc's own near-zero population of upper_link /
    statistical_cost, per the phase-1 byte-population breakdown).
  - Link-cost "Link ID Number" (10.10.2 items 1-2) is synthetic
    (sequential), since no main-map link writer exists in this repo yet
    to cross-reference a real one.

AGGREGATED-INTERSECTION CLUSTERING (Road Reference Table, 10.13):
implemented as of 2026-08-27, following a real-disc survey
(``survey_road_reference_table.py``) that found the table populated on
89.6% of real regions (see docs/phases/01-format-analysis.md and
docs/phases/03-osm-pipeline.md for the full measurement). Two candidate
groups of OSM nodes are merged into one routing node each:
  1. **Roundabouts**: every graph node lying on an OSM
     ``junction=roundabout``/``circular`` way is merged into one node.
  2. **Short internal links**: any two non-boundary graph nodes joined by
     a link shorter than ``SHORT_LINK_THRESHOLD_M`` are merged (connected
     components across the whole graph) -- intended to catch dual-
     carriageway splits/joins and other tightly-coupled simple
     intersections, which the real disc's own median of 2 composition
     links / 1 subordinate node per aggregated record suggests is the
     dominant real-world case.
This is a best-effort, OSM-side heuristic -- there is no way to check it
node-for-node against real disc "ground truth" (the real disc's own
node/link contraction is independent of any specific OSM extract). It is
only structurally validated: the written Road Reference Table round-trips
through ``route_planning.parse_road_reference_table`` and produces
records shaped like the real disc's own (envelope fields, composition-
link/subordinate-node arrays; see that function's docstring for the
byte-layout confidence breakdown). Cluster size is capped at 1
representative + 5 subordinates (matching the real disc's observed max of
5 subordinate nodes); larger candidate groups (e.g. big roundabouts) keep
only the highest-degree node plus its 5 nearest members and leave the
rest as ordinary standalone nodes -- a deliberate simplification, not a
discovered structural limit.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.route_planning_writer import RpGraph, RpNode, RpLink, RpLinkCost, RpAggregatedNode

# Links shorter than this (metres) are treated as candidates for
# aggregated-intersection clustering -- see module docstring
# "AGGREGATED-INTERSECTION CLUSTERING" above.
SHORT_LINK_THRESHOLD_M = 20.0

# Cap on total members (representative + subordinates) per cluster --
# matches the real disc's observed max of 5 subordinate nodes (see
# survey_road_reference_table.py).
MAX_CLUSTER_MEMBERS = 6

DEFAULT_PBF = str(
    Path.home() / "workspace" / "open-pajero-maps" / "australia-260824.osm.pbf"
)

# OSM highway=* values considered routable, mirroring
# estimate_route_planning_scaling.py's ROADS set (deliberately excludes
# footway/cycleway/path/steps/pedestrian -- those map to Ch.32.2 class 8
# "Walkway" in a fuller pipeline, out of scope for this vehicle-routing
# prototype).
MAJOR = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
ROADS = MAJOR | {"unclassified", "residential", "living_street", "service", "track", "road", "busway"}

# OSM highway=* -> Ch.32.2 Road Class Code. Chosen from the spec's own
# speed-band descriptions (0/1 Freeway, 2 Highway >91kph/National road,
# 3 Throughway 51-90kph/Main district road, 4 Local road 31-50kph/
# Prefectural road, 5 Frontage road, 6 very-low-speed <30kph, 7 Private
# road). This is a first-pass mapping, not a validated one -- no
# empirical calibration against the reference disc's own road-class
# distribution was done in this prototype (out of scope: this repo has
# no main-map road writer yet to compare against).
ROAD_CLASS = {
    "motorway": 0, "motorway_link": 0,
    "trunk": 1, "trunk_link": 1,
    "primary": 2, "primary_link": 2,
    "secondary": 3, "secondary_link": 3,
    "tertiary": 3, "tertiary_link": 3,
    "unclassified": 4, "road": 4,
    "residential": 5,
    "living_street": 6,
    "service": 7,
    "track": 7,
    "busway": 12,
}


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def bearing_deg(lat1, lon1, lat2, lon2) -> int:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    deg = (math.degrees(math.atan2(x, y)) + 360.0) % 360.0
    return int(deg) % 360


class _WayCollector:
    """First pyosmium pass: collect routable ways whose bbox intersects
    the region, and every node id they reference."""

    def __init__(self, bbox):
        import osmium
        self.bbox = bbox  # (lon_left, lat_bottom, lon_right, lat_top)
        self.ways: list[dict] = []
        self.node_ids: set[int] = set()
        self.restriction_rels: list[dict] = []
        self._osmium = osmium

    def way(self, w):
        hw = w.tags.get("highway")
        if hw not in ROADS:
            return
        try:
            coords = [(nd.ref, nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        except Exception:
            return
        if len(coords) < 2:
            return
        lons = [c[2] for c in coords]
        lats = [c[1] for c in coords]
        l, r, b, t = self.bbox[0], self.bbox[2], self.bbox[1], self.bbox[3]
        if max(lons) < l or min(lons) > r or max(lats) < b or min(lats) > t:
            return
        oneway = w.tags.get("oneway") in ("yes", "true", "1") or hw in (
            "motorway", "motorway_link",
        )
        self.ways.append({
            "id": w.id,
            "coords": coords,
            "highway": hw,
            "oneway": oneway,
            "junction": w.tags.get("junction"),
        })
        for nid, _, _ in coords:
            self.node_ids.add(nid)

    def relation(self, rel):
        if rel.tags.get("type") != "restriction":
            return
        restr = rel.tags.get("restriction")
        if not restr:
            return
        frm = to = via_node = None
        for m in rel.members:
            if m.role == "from" and m.type == "w":
                frm = m.ref
            elif m.role == "to" and m.type == "w":
                to = m.ref
            elif m.role == "via" and m.type == "n":
                via_node = m.ref
        if frm is not None and to is not None:
            self.restriction_rels.append({
                "restriction": restr, "from": frm, "to": to, "via": via_node,
            })


def _collect(pbf_path: str, bbox):
    import osmium

    class Handler(osmium.SimpleHandler, _WayCollector):
        def __init__(self, bbox):
            osmium.SimpleHandler.__init__(self)
            _WayCollector.__init__(self, bbox)

    h = Handler(bbox)
    h.apply_file(pbf_path, locations=True, idx="flex_mem")
    return h.ways, h.restriction_rels


def _build_graph_topology(ways: list[dict]):
    """Split ways at shared/endpoint nodes. Returns:
      node_coord: {osm_node_id: (lat, lon)}
      node_degree: {osm_node_id: int}  (how many way-endpoints/splits touch it)
      segments: list of dicts {way_id, highway, oneway, chain: [osm_node_id,...]}
    where a segment's chain runs between two "graph nodes" (endpoints or
    shared nodes), possibly through intermediate degree-2 nodes kept only
    for length computation.
    """
    from collections import defaultdict

    node_coord: dict[int, tuple[float, float]] = {}
    refcount: dict[int, int] = defaultdict(int)
    for w in ways:
        for nid, lat, lon in w["coords"]:
            node_coord[nid] = (lat, lon)
        refcount[w["coords"][0][0]] += 2   # endpoints always count as graph nodes
        refcount[w["coords"][-1][0]] += 2
        for nid, _, _ in w["coords"][1:-1]:
            refcount[nid] += 1

    def is_graph_node(nid):
        return refcount[nid] >= 2

    segments = []
    for w in ways:
        coords = w["coords"]
        chain = [coords[0]]
        for nid, lat, lon in coords[1:]:
            chain.append((nid, lat, lon))
            if is_graph_node(nid):
                if len(chain) >= 2:
                    segments.append({
                        "way_id": w["id"], "highway": w["highway"], "oneway": w["oneway"],
                        "chain": chain,
                    })
                chain = [(nid, lat, lon)]
    return node_coord, refcount, segments


def _roundabout_node_groups(ways: list[dict], node_index: dict[int, int]) -> list[set[int]]:
    """Graph-node-index groups for each OSM ``junction=roundabout``/
    ``circular`` way -- see module docstring."""
    groups = []
    for w in ways:
        if w.get("junction") not in ("roundabout", "circular"):
            continue
        idxs = {node_index[nid] for nid, _, _ in w["coords"] if nid in node_index}
        if len(idxs) >= 2:
            groups.append(idxs)
    return groups


def cluster_nodes(graph: RpGraph, roundabout_groups: list[set[int]]) -> None:
    """Merge groups of graph nodes representing one physical intersection
    into single nodes (Ch.10.13 aggregated-intersection clustering -- see
    module docstring). Mutates ``graph`` in place: ``graph.nodes`` shrinks
    to one entry per cluster/unclustered node, all ``RpLink.adjacent_node``
    and ``RpLinkCost.connected_node`` references are remapped, and
    ``graph.aggregated`` is populated with one ``RpAggregatedNode`` per
    cluster, keyed by the surviving (representative) node's new index.
    """
    n = len(graph.nodes)
    if n == 0:
        return
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for group in roundabout_groups:
        idxs = [i for i in group if i < n]
        for k in idxs[1:]:
            union(idxs[0], k)

    for i, node in enumerate(graph.nodes):
        if node.is_boundary:
            continue
        for link in node.links:
            j = link.adjacent_node
            if j == i or graph.nodes[j].is_boundary:
                continue
            cost = graph.link_costs[link.link_cost_index]
            if cost.length_m <= SHORT_LINK_THRESHOLD_M:
                union(i, j)

    from collections import defaultdict
    raw_groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        raw_groups[find(i)].append(i)
    clusters = [sorted(g) for g in raw_groups.values() if len(g) >= 2]
    if not clusters:
        return

    old_to_new: dict[int, int] = {}
    new_nodes: list[RpNode] = []
    new_aggregated: dict[int, RpAggregatedNode] = {}
    clustered_members: dict[int, list[int]] = {}  # new index -> old member indices (rep first)

    clustered_old_ids = {i for c in clusters for i in c}
    for old_i, node in enumerate(graph.nodes):
        if old_i in clustered_old_ids:
            continue
        old_to_new[old_i] = len(new_nodes)
        new_nodes.append(node)

    for cluster in clusters:
        members = sorted(cluster, key=lambda i: -len(graph.nodes[i].links))
        kept = members[:MAX_CLUSTER_MEMBERS]
        overflow = members[MAX_CLUSTER_MEMBERS:]
        rep_old = kept[0]
        new_idx = len(new_nodes)
        rep_node = graph.nodes[rep_old]
        merged = RpNode(
            lat=rep_node.lat, lon=rep_node.lon, is_boundary=False,
            rank=rep_node.rank, links=[], is_aggregated=len(kept) >= 2,
        )
        new_nodes.append(merged)
        for i in kept:
            old_to_new[i] = new_idx
        clustered_members[new_idx] = kept
        # Overflow members (beyond the cluster-size cap) become ordinary
        # standalone nodes, unmodified.
        for i in overflow:
            old_to_new[i] = len(new_nodes)
            new_nodes.append(graph.nodes[i])

    # Second pass: remap every link's adjacent_node and every link-cost's
    # connected_node, and (for cluster representatives) collect external
    # links + internal composition links.
    for new_idx, kept in clustered_members.items():
        member_set = set(kept)
        merged = new_nodes[new_idx]
        seen_cost: set[int] = set()
        composition_cost_idxs: list[int] = []
        # external: (origin order within `kept`, old_i, old_local_idx, link)
        external: list[tuple[int, int, int, RpLink]] = []
        for order, old_i in enumerate(kept):
            for old_local_idx, link in enumerate(graph.nodes[old_i].links):
                if link.adjacent_node in member_set:
                    if link.link_cost_index not in seen_cost:
                        seen_cost.add(link.link_cost_index)
                        composition_cost_idxs.append(link.link_cost_index)
                    continue
                external.append((order, old_i, old_local_idx, link))
        composition_cost_idxs = composition_cost_idxs[:15]

        subs_old = kept[1:]
        rep_lat, rep_lon = graph.nodes[kept[0]].lat, graph.nodes[kept[0]].lon
        offsets = []
        for i in subs_old:
            dlat_m = (graph.nodes[i].lat - rep_lat) * 111320.0
            dlon_m = (graph.nodes[i].lon - rep_lon) * 111320.0 * math.cos(math.radians(rep_lat))
            dy = int(max(-127, min(127, round(dlat_m))))
            dx = int(max(-127, min(127, round(dlon_m))))
            offsets.append((dx, dy))

        # old (old_i, old_local_idx) -> new local index in merged.links,
        # needed to remap between-links regulations (which reference the
        # *same node's* own local link numbering) after the merge changes
        # that numbering.
        old_local_to_new_local: dict[tuple[int, int], int] = {
            (old_i, old_local_idx): new_local
            for new_local, (_, old_i, old_local_idx, _) in enumerate(external)
        }

        order_by_link = []
        for order, old_i, _old_local_idx, link in external:
            remapped_regs = []
            for exit_no, passage_code in link.regulations:
                if exit_no is None:
                    remapped_regs.append((None, passage_code))
                    continue
                new_exit = old_local_to_new_local.get((old_i, exit_no))
                if new_exit is not None:
                    remapped_regs.append((new_exit, passage_code))
                # else: the exit link was merged away as an internal
                # composition link -- this regulation can no longer be
                # expressed post-merge, so it is dropped (documented
                # simplification; regulations are already a rare/simple-
                # case-only feature in this prototype).
            new_link = RpLink(
                adjacent_node=old_to_new[link.adjacent_node],
                link_cost_index=link.link_cost_index,
                forward_direction=link.forward_direction,
                angle_deg=link.angle_deg,
                following_same_road=None,
                road_class=link.road_class,
                regulations=remapped_regs,
            )
            merged.links.append(new_link)
            order_by_link.append(order)

        if len(kept) >= 2:
            new_aggregated[new_idx] = RpAggregatedNode(
                node_number=new_idx,
                subordinate_node_order_by_link=order_by_link,
                composition_link_cost_numbers=composition_cost_idxs,
                subordinate_node_offsets=offsets,
                route_info=[],
            )

    # Remap links on every *unclustered* node (clustered nodes' own links
    # were already rebuilt above).
    for new_idx, node in enumerate(new_nodes):
        if new_idx in clustered_members:
            continue
        for link in node.links:
            link.adjacent_node = old_to_new[link.adjacent_node]

    for cost in graph.link_costs:
        cost.connected_node = old_to_new[cost.connected_node]

    graph.nodes = new_nodes
    graph.aggregated = new_aggregated


def build_graph(pbf_path: str, bbox, region_no: int = 0) -> tuple[RpGraph, dict]:
    """bbox = (lon_left, lat_bottom, lon_right, lat_top). Returns
    (RpGraph, stats) where stats carries counts useful for the sanity
    check / report (n_osm_ways, n_osm_nodes_in_bbox, n_restrictions_seen,
    n_restrictions_applied)."""
    ways, restriction_rels = _collect(pbf_path, bbox)
    node_coord, refcount, segments = _build_graph_topology(ways)

    graph_node_ids = sorted(nid for nid, cnt in refcount.items() if cnt >= 2)
    node_index = {nid: i for i, nid in enumerate(graph_node_ids)}

    graph = RpGraph(
        lat_top=bbox[3], lat_bottom=bbox[1], lon_left=bbox[0], lon_right=bbox[2],
        region_no=region_no,
    )
    for nid in graph_node_ids:
        lat, lon = node_coord[nid]
        graph.nodes.append(RpNode(lat=lat, lon=lon, is_boundary=False, rank=0, links=[]))

    # way_id -> osm node id -> local link-record-number, for restriction resolution
    node_way_links: dict[tuple[int, int], list[int]] = {}  # (node_idx, way_id) -> [local link nos]

    for seg in segments:
        chain = seg["chain"]
        a_id, a_lat, a_lon = chain[0]
        b_id, b_lat, b_lon = chain[-1]
        if a_id not in node_index or b_id not in node_index or a_id == b_id:
            continue
        a_idx, b_idx = node_index[a_id], node_index[b_id]
        length_m = sum(
            haversine_m(chain[i][1], chain[i][2], chain[i + 1][1], chain[i + 1][2])
            for i in range(len(chain) - 1)
        )
        if length_m <= 0:
            continue
        road_class = ROAD_CLASS.get(seg["highway"], 4)

        cost_idx = len(graph.link_costs)
        graph.link_costs.append(RpLinkCost(
            link_id_origin=seg["way_id"] & 0xFFFFFFFF,
            link_id_dest_delta=0,
            length_m=length_m,
            connected_node=b_idx,
            road_class=road_class,
            forward_passable=True,
            reverse_passable=not seg["oneway"],
        ))

        fwd_angle = bearing_deg(a_lat, a_lon, chain[1][1], chain[1][2])
        rev_angle = bearing_deg(b_lat, b_lon, chain[-2][1], chain[-2][2])

        link_a = RpLink(
            adjacent_node=b_idx, link_cost_index=cost_idx, forward_direction=True,
            angle_deg=fwd_angle, following_same_road=None, road_class=road_class,
        )
        graph.nodes[a_idx].links.append(link_a)
        node_way_links.setdefault((a_idx, seg["way_id"]), []).append(len(graph.nodes[a_idx].links) - 1)

        if not seg["oneway"]:
            link_b = RpLink(
                adjacent_node=a_idx, link_cost_index=cost_idx, forward_direction=False,
                angle_deg=rev_angle, following_same_road=None, road_class=road_class,
            )
            graph.nodes[b_idx].links.append(link_b)
            node_way_links.setdefault((b_idx, seg["way_id"]), []).append(len(graph.nodes[b_idx].links) - 1)

    # First-pass hierarchy: rank by best (lowest) road class among a
    # node's incident links (task item 1's sanctioned heuristic).
    for node in graph.nodes:
        if node.links:
            node.rank = min(l.road_class for l in node.links)
        else:
            node.rank = 15

    n_applied = 0
    for r in restriction_rels:
        via = r["via"]
        if via is None or via not in node_index:
            continue
        node_idx = node_index[via]
        from_links = node_way_links.get((node_idx, r["from"]))
        to_links = node_way_links.get((node_idx, r["to"]))
        if not from_links or not to_links:
            continue
        entry_link = from_links[0]
        exit_link = to_links[0]
        passage_code = 0x7F if r["restriction"].startswith("no_") else 0x00
        graph.nodes[node_idx].links[entry_link].regulations.append((exit_link, passage_code))
        n_applied += 1

    n_nodes_before_clustering = len(graph.nodes)
    roundabout_groups = _roundabout_node_groups(ways, node_index)
    cluster_nodes(graph, roundabout_groups)

    stats = {
        "n_osm_ways": len(ways),
        "n_osm_nodes_in_bbox": len(node_coord),
        "n_graph_nodes_before_clustering": n_nodes_before_clustering,
        "n_graph_nodes": len(graph.nodes),
        "n_graph_links": sum(len(n.links) for n in graph.nodes),
        "n_link_costs": len(graph.link_costs),
        "n_restrictions_seen": len(restriction_rels),
        "n_restrictions_applied": n_applied,
        "n_aggregated_nodes": len(graph.aggregated),
    }
    return graph, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pbf", default=DEFAULT_PBF)
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LON_LEFT", "LAT_BOTTOM", "LON_RIGHT", "LAT_TOP"),
                    required=True)
    ap.add_argument("--region-no", type=int, default=0)
    args = ap.parse_args()

    graph, stats = build_graph(args.pbf, tuple(args.bbox), region_no=args.region_no)
    print(stats)


if __name__ == "__main__":
    main()
