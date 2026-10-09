#!/usr/bin/env python3
"""Plan 67 Phase 1: committed census of L0 road links in divided leaves whose vertices sit on the
parent edge (R-G9-3-d-rem), reconstructing plan 53's scratch-only predicate (P53) side by side with
the encoder-pinned predicate (PE).

Reads a disc through plan 48's reader (`overlay_test.RReader`: whole leaf entries, `decode_parcel`).
Per divided L0 leaf (leaf path length >= 2): every road link's vertices in two frames:
  frame-raw  : (lon, lat) -> raw at the leaf frame's own coord_range (overlay_test._raw; what D1 stored)
  parent-raw : relative to the parent slot bounds, scaled to 4096 (y-up)
Predicate variants (all evaluated; the reproduction gate picks P53):
  shape  : 'coincident' (all vertices identical) | 'all_on_edge' (every vertex on a parent edge)
  coords : 'frame' | 'parent'
  nx     : 'ptype' (1 -> 2x2, 2 -> 4x4) | 'two'
For a variant, each qualifying link is classed: on parent edge (every vertex x in {0,R} or y in {0,R})
-> inside / outside the closed leaf rect [sx*R/nx, (sx+1)*R/nx] x [sy*R/nx, (sy+1)*R/nx] with
c = lpath[-1] = sy*nx + sx; else coincident_not_on_parent_edge (shape 'coincident' only).
PE: rect from `bg_producer_scan.leaf_clip_geometry` (the committed E2 clip convention) on frame-raw.
Output <out>.json (counts per variant, by edge, per parent) and <out>.tsv.gz (every PE / P53-candidate
record with full vertex lists)."""
from __future__ import annotations

import argparse, gzip, io, json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
from overlay_test import RReader, _raw  # noqa: E402
from kiwiw.model import MeshLocation  # noqa: E402
from kiwiw.parcel import decode_parcel  # noqa: E402

EDGE_TOL = 0.0  # exact: P53 sample points are integral (e.g. [4096, 1698])


def parent_raw(la, lo, pb):
    return (round((lo - pb.lon_lo) / (pb.lon_hi - pb.lon_lo) * 4096.0, 6),
            round((la - pb.lat_lo) / (pb.lat_hi - pb.lat_lo) * 4096.0, 6))


def edges_of(V, R):
    """set of parent edges every vertex lies on, or None if some vertex is on no edge."""
    out = set()
    for x, y in V:
        e = {k for k, ok in (("E", x == R), ("W", x == 0), ("N", y == R), ("S", y == 0)) if ok}
        if not e:
            return None
        out |= e
    return out


def in_rect(V, rect):
    x0, y0, x1, y1 = rect
    return all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in V)


def edge_key(es):
    order = "EWNS"
    return str(tuple(sorted(es, key=order.index)))


def iter_divided_links(disc):
    rr = RReader(str(disc))
    lmr, blks = rr.blocks(0)
    gn_lng = 1 + lmr.n_parcels_lng[0]; gn_lat = 1 + lmr.n_parcels_lat[0]
    nbl = 1 + lmr.n_blocks_lng; nbs = 1 + lmr.n_blocksets_lng; nbl_lat = 1 + lmr.n_blocks_lat
    for blk in blks:
        _o, bs_index, ei, _e, _bb = blk
        bsy, bsx = divmod(bs_index, nbs); bly, blx = divmod(ei, nbl)
        for leaf in rr.leaves(lmr, blk):
            lpath, le, lb, ptype, parent, (fb, fc) = leaf
            if len(lpath) < 2:
                continue
            ly, lx = divmod(lpath[0], gn_lng)
            gx = (bsx * nbl + blx) * gn_lng + lx; gy = (bsy * nbl_lat + bly) * gn_lat + ly
            fbr = rr.walk.with_range(fb, rr.walk.leaf_frame_range(0, ptype, lpath, fc))
            rr.fh.seek(rr.volume.getsector(le.dsa, rr.ss, rr.ls)); buf = rr.fh.read(le.size * rr.ls)
            loc = MeshLocation(level=0, parcel_type=ptype, blockset_index=bs_index, block_index=ei,
                               parcel_index=lpath[-1], bounds=fbr, sector_addr=le.dsa, size_logical_sectors=le.size)
            p = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
            links = p.road.links if p.road else []
            yield gx, gy, tuple(lpath), ptype, fbr, parent, links


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=Path, required=True, help="dir holding ALLDATA.KWI")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    from bg_producer_scan import leaf_clip_geometry
    VARS = [(s, c, n) for s in ("coincident", "all_on_edge") for c in ("frame", "parent") for n in ("ptype", "two")]
    cnt = {v: Counter() for v in VARS}; pe = Counter(); rows = []
    parents = set(); nlinks = 0; frame_ranges = Counter()
    for gx, gy, lpath, ptype, fbr, pb, links in iter_divided_links(a.disc):
        parents.add((gx, gy)); c = int(lpath[-1])
        R_f = float(fbr.coord_range); frame_ranges[int(R_f)] += 1
        _b4, crs, pe_rect = leaf_clip_geometry(0, gx, gy, lpath, ptype, lambda lv, x, y: (None, R_f))
        for li, lk in enumerate(links):
            nlinks += 1
            pts = lk.points or []
            V = {"frame": [_raw(la, lo, fbr) for la, lo in pts], "parent": [parent_raw(la, lo, pb) for la, lo in pts]}
            rec = None
            for v in VARS:
                s, cs, nn = v
                W = V[cs]
                if not W:
                    continue
                if s == "coincident" and len(set(W)) != 1:
                    continue
                R = R_f if cs == "frame" else 4096.0
                es = edges_of(W, R)
                if es is None:
                    if s == "coincident":
                        cnt[v]["coincident_not_on_parent_edge"] += 1
                    continue
                nx = (2 if ptype == 1 else 4) if nn == "ptype" else 2
                sx, sy = c % nx, c // nx
                rect = (sx * R / nx, sy * R / nx, (sx + 1) * R / nx, (sy + 1) * R / nx)
                if in_rect(W, rect):
                    cnt[v]["on_edge_inside_leaf_rect"] += 1
                else:
                    cnt[v]["on_edge_outside_leaf_rect"] += 1
                    cnt[v]["by_edge/" + edge_key(es)] += 1
                    cnt[v]["parent/%d,%d" % (gx, gy)] += 1
                    rec = rec or {}
                    rec.setdefault("variants", []).append("/".join(v))
            Wf = V["frame"]
            es = edges_of(Wf, R_f) if Wf else None
            pe_out = bool(Wf) and es is not None and not in_rect(Wf, pe_rect)
            if pe_out:
                pe["on_edge_outside_leaf_rect"] += 1; pe["by_edge/" + edge_key(es)] += 1
                rec = rec or {}
            elif Wf and es is not None:
                pe["on_edge_inside_leaf_rect"] += 1
            if rec is not None:
                rows.append({"ix": gx, "iy": gy, "lpath": list(lpath), "ptype": ptype, "link": li,
                             "dc": lk.display_class, "osm_way_id": getattr(lk, "osm_way_id", None),
                             "frame_range": R_f, "pe_rect": list(pe_rect), "pe_outside": pe_out,
                             "edges": sorted(es) if es else None, "variants": rec.get("variants", []),
                             "v_frame": Wf, "v_parent": V["parent"]})
    rows.sort(key=lambda r: (r["ix"], r["iy"], r["lpath"], r["link"]))
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(b"row_json\n")
        for r in rows:
            g.write((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    summ = {"schema": "plan67-l0-edge-census-v1", "disc": str(a.disc), "n_divided_parents": len(parents),
            "n_road_links_in_divided_leaves": nlinks, "frame_ranges": dict(sorted(frame_ranges.items())),
            "variants": {"/".join(v): dict(sorted((k, n) for k, n in cnt[v].items() if not k.startswith("parent/")))
                         for v in VARS},
            "variant_parents": {"/".join(v): len([k for k in cnt[v] if k.startswith("parent/")]) for v in VARS},
            "PE": dict(sorted(pe.items())), "wall_s": round(time.time() - t0, 1)}
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: summ[k] for k in ("n_divided_parents", "n_road_links_in_divided_leaves")}))


if __name__ == "__main__":
    main()
