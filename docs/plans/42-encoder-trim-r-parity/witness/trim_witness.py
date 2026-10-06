"""Plan 42 Phase 1: trimmed items vs R (light; bounded R leaf preads only).

Inputs (committed beside this file):
  trim_l0_1755_591.tsv.gz, trim_l8_7_4.tsv.gz -- the instrumented encoder's dump
  (instr_e2.patch, throwaway worktree; frames byte-identical to the plain build).
  Columns: level ix iy sub_x sub_y kind(0 road,1 bg,2 name) K|D rank item par tier geom
  (roads: "dc=<display class>|lat,lon;..." of the chain piece; background:
  "tc=<type>|lat,lon;..." of the parent-record ring, which includes shapes shared
  in from neighbouring cells by the overlap pass).

Match rule (DESIGN Contract 2, fixed before measuring), parent-cell raw units of
the item's level (RAW = 4096 per parent cell):
  road: every vertex of the G chain piece lies within 1 raw unit of the union of
        R road polylines of the same display class in the parent's R leaves ->
        present; no vertex within 1 unit -> absent; otherwise ambiguous.
  bg:   an R class-2 record of the same type whose every vertex lies within 1 raw
        unit of the G source ring or of its own R leaf frame edge, with at least
        one vertex within 1 unit of the ring and more than 1 unit from the frame
        edge -> present; none -> absent; an R record of the same type meeting the
        ring at some but not all vertices -> ambiguous.
G control: the kept (K) items of the same trimmed sub-cell go through the same rule.

Writes trim_witness.json.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from harness import walk  # noqa: E402
from kiwiw.model import MeshLocation  # noqa: E402
from kiwiw.parcel import decode_parcel  # noqa: E402
from overlay_test import RReader  # noqa: E402
from r_neighbours import LeafIndex  # noqa: E402
from quantisation_roundtrip import Lattice, RAW  # noqa: E402

R_DISC = "/run/media/codyh/464210-8480"
CASES = [("trim_l0_1755_591.tsv.gz", 0, 1755, 591), ("trim_l8_7_4.tsv.gz", 8, 7, 4)]
TOL = 1.0


def seg_dist(P, S):
    """min distance from each point P (k,2) to segments S (m,4)."""
    if len(S) == 0:
        return np.full(len(P), np.inf)
    out = np.empty(len(P))
    a = S[:, :2]; b = S[:, 2:]; ab = b - a; L = (ab ** 2).sum(1)
    for s in range(0, len(P), 256):
        p = P[s:s + 256, None, :]
        t = np.where(L > 0, ((p - a) * ab).sum(2) / np.where(L > 0, L, 1), 0).clip(0, 1)
        q = a + t[..., None] * ab
        out[s:s + 256] = np.sqrt(((p - q) ** 2).sum(2)).min(1)
    return out


def segs(pts, closed):
    P = np.asarray(pts, float)
    if len(P) < 2:
        return np.zeros((0, 4))
    Q = np.vstack([P[1:], P[:1]]) if closed else P[1:]
    A = P if closed else P[:-1]
    return np.hstack([A, Q])


def r_parent(rr, idx, level, ix, iy, lat):
    nb = idx.get(ix, iy)
    leaves = []
    for (lmr, blk, leaf_row) in nb.handles:
        lpath, le, lb, ptype, _, (fb, fc) = leaf_row
        frng = walk.leaf_frame_range(level, ptype, lpath, fc)
        fbr = walk.with_range(fb, frng)
        off = rr.volume.getsector(le.dsa, rr.ss, rr.ls)
        length = le.size * rr.ls
        rr.fh.seek(off)
        buf = rr.fh.read(length)
        loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=blk[1], block_index=blk[2],
                           parcel_index=lpath[-1], bounds=fbr, sector_addr=le.dsa, size_logical_sectors=le.size)
        p = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
        cv = lambda la, lo: (float(lat.gx(lo)) - ix * RAW, float(lat.gy(la)) - iy * RAW)
        links = [(l.display_class, [cv(a, o) for a, o in l.points]) for l in (p.road.links if p.road else [])]
        bgs = [(s.type_code, s.shape_class, [cv(a, o) for a, o in s.coords])
               for s in (p.background.shapes if p.background else [])]
        b = fbr
        rect = None
        try:
            x0, y0 = cv(b.lat_lo, b.lon_lo); x1, y1 = cv(b.lat_hi, b.lon_hi)
            rect = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
        except AttributeError:
            pass
        leaves.append({"leaf_path": list(lpath), "file_offset": off, "length": length,
                       "sha256": hashlib.sha256(buf).hexdigest(), "rect_parent_raw": rect,
                       "n_road_links": len(links), "n_bg": len(bgs),
                       "road_frame_size": p.road.frame_size if p.road else 0,
                       "bg_frame_size": p.background.frame_size if p.background else 0,
                       "_links": links, "_bgs": bgs})
    return nb.status, nb.divided, leaves


def rect_segs(r):
    x0, y0, x1, y1 = r
    return segs([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True)


def main():
    rr = RReader(R_DISC)
    res = {"rule": __doc__.split("Match rule")[1].split("Writes")[0].strip(), "cases": []}
    for fname, level, ix, iy in CASES:
        lat = Lattice(level)
        idx = LeafIndex(rr, level)
        status, divided, leaves = r_parent(rr, idx, level, ix, iy, lat)
        rows = [l.rstrip("\n").split("\t") for l in gzip.open(HERE / fname, "rt")]
        # R geometry pools
        road_by_class = {}
        all_road = []
        for lf in leaves:
            for dc, pts in lf["_links"]:
                S = segs(pts, False)
                road_by_class.setdefault(dc, []).append(S); all_road.append(S)
        road_by_class = {k: np.vstack(v) for k, v in road_by_class.items()}
        all_road = np.vstack(all_road) if all_road else np.zeros((0, 4))
        r_bg = []
        for lf in leaves:
            for tc, cl, pts in lf["_bgs"]:
                if cl == 2 and len(pts) >= 3:
                    P = np.asarray(pts)
                    r_bg.append((tc, P, lf["rect_parent_raw"], P.min(0), P.max(0)))
        items = []
        for r in rows:
            lv, cx, cy, sx, sy, kind, kd, rank, it, par, tier = r[:11]
            kind = int(kind); par = int(par)
            rec = {"sub": [int(sx), int(sy)], "kind": ["road", "background", "name"][kind], "KD": kd,
                   "rank": int(rank), "item": int(it), "parent_record_index": par, "tier": tier}
            if kind == 0:
                head, body = r[11].split("|", 1)
                dc = int(head[3:])
                pts = [tuple(map(float, c.split(","))) for c in body.split(";") if c]
                P = np.array([(float(lat.gx(lo)) - ix * RAW, float(lat.gy(la)) - iy * RAW) for la, lo in pts])
                rec["display_class"] = dc; rec["n_pts"] = len(P)
                d = seg_dist(P, road_by_class.get(dc, np.zeros((0, 4))))
                dany = seg_dist(P, all_road)
                w = int((d <= TOL).sum())
                rec["status"] = "present" if w == len(P) else "absent" if w == 0 else "ambiguous"
                rec["within_1u_same_class"] = w
                rec["status_any_class"] = ("present" if (dany <= TOL).all() else "absent" if not (dany <= TOL).any()
                                           else "ambiguous")
                rec["bbox_parent_raw"] = [round(float(P[:, 0].min()), 1), round(float(P[:, 0].max()), 1),
                                          round(float(P[:, 1].min()), 1), round(float(P[:, 1].max()), 1)]
            elif kind == 1:
                head, body = r[11].split("|", 1)
                tc = int(head[3:])
                pts = [tuple(map(float, c.split(","))) for c in body.split(";") if c]
                G = np.array([(float(lat.gx(lo)) - ix * RAW, float(lat.gy(la)) - iy * RAW) for la, lo in pts])
                rec["type"] = tc; rec["n_pts"] = len(G)
                GS = segs(G, True)
                g0, g1 = G.min(0) - 2, G.max(0) + 2
                best = "absent"
                for rtc, P, rect, p0, p1 in r_bg:
                    if rtc != tc or (p1 < g0).any() or (p0 > g1).any():
                        continue
                    dr = seg_dist(P, GS)
                    de = seg_dist(P, rect_segs(rect)) if rect else np.full(len(P), np.inf)
                    ok = (np.minimum(dr, de) <= TOL)
                    core = (dr <= TOL) & (de > TOL)
                    if ok.all() and core.any():
                        best = "present"; break
                    if (dr <= TOL).any():
                        best = "ambiguous"
                rec["status"] = best
            items.append(rec)
        summ = Counter((i["kind"], i["KD"], i["status"]) for i in items if "status" in i)
        case = {"level": level, "parent": [ix, iy], "dump": fname,
                "dump_sha256": hashlib.sha256((HERE / fname).read_bytes()).hexdigest(),
                "R": {"slot_status": status, "divided": divided, "n_leaves": len(leaves),
                      "leaves": [{k: v for k, v in lf.items() if not k.startswith("_")} for lf in leaves]},
                "summary": {"|".join(k): v for k, v in sorted(summ.items())},
                "items": items}
        res["cases"].append(case)
        print(level, ix, iy, status, divided, len(leaves), [(lf["leaf_path"], lf["length"], lf["n_road_links"], lf["n_bg"]) for lf in leaves])
        print(" ", case["summary"])
    (HERE / "trim_witness.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
