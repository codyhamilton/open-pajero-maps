"""Plan 38 P1: every OSM object (any tags) with a node inside R's row-246
record bbox (+~150 m margin) in the pinned PBF. Streamed three-pass scan
(nodes -> ways -> relations), no location index; run under the heavy wrapper.

Limit (stated): an area whose ring has no node inside the box (a large
enclosing polygon) is not found by this scan.

Writes witness/row246_pbf_scan.json.
"""
import json
import sys
from pathlib import Path

import osmium

HERE = Path(__file__).resolve().parent
PBF = Path("/home/codyh/workspace/open-pajero-maps/australia-260824.osm.pbf")
w = json.loads((HERE / "row246_witness.json").read_text())
r = [p for p in w["R"]["type321"] if "a" in p["meet_branches"]][0]
LAT0, LAT1, LON0, LON1 = r["latlon_bbox"]
M_LAT, M_LON = 150 / 111320.0, 150 / 95000.0
BOX = (LAT0 - M_LAT, LAT1 + M_LAT, LON0 - M_LON, LON1 + M_LON)


class Nodes(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.ids = {}; self.tagged = []

    def node(self, n):
        if n.location.valid():
            la, lo = n.location.lat, n.location.lon
            if BOX[0] <= la <= BOX[1] and BOX[2] <= lo <= BOX[3]:
                self.ids[n.id] = (la, lo)
                if len(n.tags):
                    self.tagged.append({"id": n.id, "lat": la, "lon": lo, "tags": dict(n.tags)})


class Ways(osmium.SimpleHandler):
    def __init__(self, ids):
        super().__init__(); self.ids = ids; self.ways = []

    def way(self, wy):
        refs = [nd.ref for nd in wy.nodes]
        hit = [x for x in refs if x in self.ids]
        if hit:
            self.ways.append({"id": wy.id, "n_nodes": len(refs), "n_in_box": len(hit),
                              "closed": refs[0] == refs[-1], "tags": dict(wy.tags)})


class Rels(osmium.SimpleHandler):
    def __init__(self, wids):
        super().__init__(); self.wids = wids; self.rels = []

    def relation(self, rl):
        m = [(x.ref, x.role) for x in rl.members if x.type == "w" and x.ref in self.wids]
        if m:
            self.rels.append({"id": rl.id, "tags": dict(rl.tags), "members_in_box": m})


def main():
    n = Nodes(); n.apply_file(str(PBF))
    wh = Ways(n.ids); wh.apply_file(str(PBF))
    rh = Rels({x["id"] for x in wh.ways}); rh.apply_file(str(PBF))
    out = {"pbf": str(PBF), "box_lat_lat_lon_lon": BOX, "r_record_sha256": r["record_sha256"],
           "nodes_in_box": len(n.ids), "tagged_nodes": n.tagged, "ways": wh.ways, "relations": rh.rels,
           "limit": "areas with no node inside the box are not found"}
    (HERE / "row246_pbf_scan.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"nodes": len(n.ids), "ways": len(wh.ways), "rels": len(rh.rels)}))


if __name__ == "__main__":
    sys.exit(main())
