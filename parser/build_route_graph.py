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
  - Aggregated-intersection clustering (Road Reference Table, 10.13) is
    not implemented; written with count=0 (a spec-legal empty case).
  - Link-cost "Link ID Number" (10.10.2 items 1-2) is synthetic
    (sequential), since no main-map link writer exists in this repo yet
    to cross-reference a real one.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.route_planning_writer import RpGraph, RpNode, RpLink, RpLinkCost

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

    stats = {
        "n_osm_ways": len(ways),
        "n_osm_nodes_in_bbox": len(node_coord),
        "n_graph_nodes": len(graph.nodes),
        "n_graph_links": sum(len(n.links) for n in graph.nodes),
        "n_link_costs": len(graph.link_costs),
        "n_restrictions_seen": len(restriction_rels),
        "n_restrictions_applied": n_applied,
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
