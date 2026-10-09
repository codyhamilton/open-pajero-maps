#!/usr/bin/env python3
"""Plan 64: output-neutral provenance re-extract (triage tool; does not touch the production extractor).

One streaming pass over the PBF with the production extractor's own functions
(parser/osm_to_parcel_geometry.py: ring closure, _osm_tags_to_bg_type, selection.level_filter,
_centroid, assign_to_parcel on TileGrid.from_reference(level)) and pyosmium's location index
(as the extractor's `apply`). Two outputs:
  homes : every background ring whose centroid cell is one of the --groups homes (in PBF order = spool order),
          with way id, tags, mapped type, coordinates -> compared ring-by-ring to the spool cell.
  query : every way (any tags, roads included) and every relation member-way whose node bbox meets
          each --groups query cell's frame bounds (+ margin), with tags, level-0 bg type mapping and
          level_filter result; relations listed with tags and member ids (H4 proof (i) input).
Deterministic JSON (sorted keys)."""
from __future__ import annotations

import argparse, hashlib, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser")]
import osm_to_parcel_geometry as X  # noqa: E402
from kiwiw import selection  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pbf", type=Path, required=True)
    ap.add_argument("--spool", type=Path, required=True)
    ap.add_argument("--level", type=int, default=0)
    ap.add_argument("--groups", type=Path, required=True,
                    help="JSON {homes: [[hx,hy],...], query_cells: [[ix,iy],...]}")
    ap.add_argument("--margin-deg", type=float, default=0.002)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    import osmium
    grid = X.TileGrid.from_reference(a.level)
    spec = json.loads(a.groups.read_text())
    homes = {tuple(h): [] for h in spec["homes"]}
    qcells = {}
    for c in spec["query_cells"]:
        qb = X.frame_bounds(c[0], c[1], grid)
        qcells[tuple(c)] = (qb.lat_lo - a.margin_deg, qb.lat_hi + a.margin_deg,
                            qb.lon_lo - a.margin_deg, qb.lon_hi + a.margin_deg)
    query = {c: [] for c in qcells}
    rels = []
    stats = {"ways": 0, "bg_rings_level": 0}

    class H(osmium.SimpleHandler):
        def way(self, w):
            stats["ways"] += 1
            try:
                coords = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
            except Exception:
                return
            if len(coords) < 2:
                return
            tags = dict(w.tags)
            lats = [c[0] for c in coords]; lons = [c[1] for c in coords]
            bb = (min(lats), max(lats), min(lons), max(lons))
            meets = [c for c, q in qcells.items()
                     if not (bb[1] < q[0] or bb[0] > q[1] or bb[3] < q[2] or bb[2] > q[3])]
            is_road = tags.get("highway") in X.ROADS
            bg = None if is_road else X._osm_tags_to_bg_type(tags, a.level)
            lf = bool(selection.level_filter(a.level, tags))
            for c in meets:
                query[c].append({"way": int(w.id), "tags": tags, "n": len(coords), "road": is_road,
                                 "bg_type_l": bg, "level_filter": lf, "bbox": list(bb)})
            if is_road or len(coords) < 3 or not lf or bg is None:
                return
            ring = list(coords)
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            stats["bg_rings_level"] += 1
            par = X.assign_to_parcel(*X._centroid(ring), grid)
            if par in homes:
                homes[par].append({"way": int(w.id), "tags": tags, "bg_type": bg, "ring": ring,
                                   "way_closed": bool(w.is_closed()), "n_nodes": len(w.nodes),
                                   "n_valid_coords": len(coords)})

        def relation(self, r):
            tags = dict(r.tags)
            if not tags:
                return
            mids = [int(m.ref) for m in r.members if m.type == "w"]
            rels.append((int(r.id), tags, mids))

    H().apply_file(str(a.pbf), locations=True, idx="flex_mem")
    from kiwiw.spool import SpoolReader
    sys.path.insert(0, str(ROOT / "parser/tools"))
    import bg_producer_scan as S
    sr = SpoolReader(str(a.spool))
    out_homes = {}
    for (hx, hy), home in sorted(homes.items()):
        c = S.direct_spool_cell(sr, a.level, hx, hy) or {}
        sp = c.get("backgrounds") or []
        cmp_rows = []
        for i in range(max(len(sp), len(home))):
            s_ = sp[i] if i < len(sp) else None
            h = home[i] if i < len(home) else None
            sc = [tuple(map(float, p)) for p in (s_.coords if s_ else [])]
            hc = [tuple(map(float, p)) for p in (h["ring"] if h else [])]
            cmp_rows.append({"ri": i, "spool_type": int(s_.type_code) if s_ else None,
                             "osm_way": h["way"] if h else None, "osm_type": h["bg_type"] if h else None,
                             "coords_equal": sc == hc, "n_spool": len(sc), "n_osm": len(hc)})
        out_homes[f"{hx},{hy}"] = {
            "rings": [{k: v for k, v in h.items() if k != "ring"} | {"n": len(h["ring"]),
                      "ring_sha256": hashlib.sha256(json.dumps(h["ring"]).encode()).hexdigest()} for h in home],
            "n_spool": len(sp), "n_osm": len(home),
            "all_equal": all(r["coords_equal"] and r["spool_type"] == r["osm_type"] for r in cmp_rows),
            "mismatch_rows": [r for r in cmp_rows if not (r["coords_equal"] and r["spool_type"] == r["osm_type"])]}
    out_q = {}
    for c, ws in sorted(query.items()):
        ids = {w["way"] for w in ws}
        out_q[f"{c[0]},{c[1]}"] = {"bbox": list(qcells[c]), "ways": sorted(ws, key=lambda w: w["way"]),
                                   "relations": [{"relation": rid, "tags": t, "member_ways_in_query": sorted(set(m) & ids),
                                                  "bg_type_l": X._osm_tags_to_bg_type(t, a.level)}
                                                 for rid, t, m in rels if set(m) & ids]}
    out = {"pbf": str(a.pbf), "level": a.level, "margin_deg": a.margin_deg, "stats": stats,
           "homes": out_homes, "query": out_q, "wall_s": round(time.time() - t0, 1)}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps({"homes": {k: [v["n_osm"], v["n_spool"], v["all_equal"]] for k, v in out_homes.items()},
                      "query": {k: [len(v["ways"]), len(v["relations"])] for k, v in out_q.items()},
                      "wall_s": out["wall_s"]}))


if __name__ == "__main__":
    main()
