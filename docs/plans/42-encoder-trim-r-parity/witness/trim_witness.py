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
ROOT = next(p for p in HERE.parents if (p / "parser").is_dir() and (p / "docs").is_dir())
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


# ---------------------------------------------------------------------------
# Phase 1 rework (review p1 F1-F5): validated analysis, "v2". The v1 rule above
# is kept as recorded but is not validated (review F1-F3) and drives no verdict.
G_DISC = ROOT / "output/scratch-34/G_new"   # oracle 4e6b0de7 (protected; read only)
TOLS = [1, 2, 5, 10, 20, 50, 100, 200, 500]


def leaf_rects(leaves):
    """Review F5: a divided leaf's rect is its quadrant, not the parent.
    Grid from the leaf index (2x2 when every index < 4, else 4x4); checked
    against the decoded data (rect_check)."""
    ks = [lf["leaf_path"][-1] for lf in leaves]
    divided = len(leaves[0]["leaf_path"]) > 1 if leaves else False
    g = (2 if max(ks) < 4 else 4) if divided else 1
    w = RAW / g
    worst = {"road": 0.0, "background": 0.0}
    for lf, k in zip(leaves, ks):
        qx, qy = (k % g, k // g) if divided else (0, 0)
        r = [qx * w, qy * w, (qx + 1) * w, (qy + 1) * w]
        lf["rect_leaf_raw"] = r
        for kind, pts in (("road", [p for _, ps in lf["_links"] for p in ps]),
                          ("background", [p for _, _, ps in lf["_bgs"] for p in ps])):
            if pts:
                P = np.asarray(pts)
                out = np.maximum.reduce([r[0] - P[:, 0], P[:, 0] - r[2], r[1] - P[:, 1], P[:, 1] - r[3], np.zeros(len(P))])
                worst[kind] = max(worst[kind], round(float(out.max()), 3))
    return g, worst


def plen(P):
    return float(np.sqrt((np.diff(P, axis=0) ** 2).sum(1)).sum()) if len(P) > 1 else 0.0


def sample(P, step, cap=400):
    if len(P) < 2:
        return np.asarray(P, float)
    L = plen(P)
    k = int(min(cap, max(2, np.ceil(L / step) + 1)))
    seg = np.sqrt((np.diff(P, axis=0) ** 2).sum(1)); cum = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, cum[-1], k)
    return np.column_stack([np.interp(t, cum, P[:, 0]), np.interp(t, cum, P[:, 1])])


def local_dist(Pts, S, reach):
    """distance from points to segments, considering only segments whose bbox is
    within `reach` of the points' bbox (exact for distances <= reach; inf/large beyond)."""
    if len(S) == 0 or len(Pts) == 0:
        return np.full(len(Pts), np.inf)
    lo = Pts.min(0) - reach; hi = Pts.max(0) + reach
    sx0 = np.minimum(S[:, 0], S[:, 2]); sx1 = np.maximum(S[:, 0], S[:, 2])
    sy0 = np.minimum(S[:, 1], S[:, 3]); sy1 = np.maximum(S[:, 1], S[:, 3])
    m = (sx1 >= lo[0]) & (sx0 <= hi[0]) & (sy1 >= lo[1]) & (sy0 <= hi[1])
    d = seg_dist(Pts, S[m]) if m.any() else np.full(len(Pts), np.inf)
    return np.minimum(d, np.inf)


def qs(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    return {k: round(float(np.quantile(a, q)), 3) for k, q in (("q10", .1), ("q50", .5), ("q90", .9), ("max", 1.0))}


def in_rect_len(P, r, step=0.5):
    """polyline length inside rect r (sampled)."""
    if len(P) < 2:
        return 0.0
    tot = 0.0
    for a, b in zip(P[:-1], P[1:]):
        L = float(np.hypot(*(b - a)))
        if L == 0:
            continue
        k = max(2, int(np.ceil(L / step)))
        t = (np.arange(k) + 0.5) / k
        x = a[0] + t * (b[0] - a[0]); y = a[1] + t * (b[1] - a[1])
        tot += L * float(((x >= r[0]) & (x <= r[2]) & (y >= r[1]) & (y <= r[3])).mean())
    return tot


def rows_geom(rows, lat, ix, iy):
    out = []
    for r in rows:
        kind = int(r[5]); head, body = r[11].split("|", 1)
        pts = [tuple(map(float, c.split(","))) for c in body.split(";") if c]
        P = np.array([(float(lat.gx(lo)) - ix * RAW, float(lat.gy(la)) - iy * RAW) for la, lo in pts])
        out.append({"sub": (int(r[3]), int(r[4])), "kind": kind, "KD": r[6], "code": int(head[3:]), "P": P,
                    "item": int(r[8]), "par": int(r[9])})
    return out


def v2_analysis(level, ix, iy, rows, rleaves):
    lat = Lattice(level)
    gr = RReader(str(G_DISC))
    _, gdiv, gleaves = r_parent(gr, LeafIndex(gr, level), level, ix, iy, lat)
    rg, rworst = leaf_rects(rleaves)
    gg, gworst = leaf_rects(gleaves)
    items = rows_geom(rows, lat, ix, iy)
    roadsD = [i for i in items if i["kind"] == 0 and i["KD"] == "D"]
    roadsK = [i for i in items if i["kind"] == 0 and i["KD"] == "K"]
    subs = sorted({i["sub"] for i in items})
    assert len(subs) == 1
    sx, sy = subs[0]
    sub_rect = [sx * RAW / gg, sy * RAW / gg, (sx + 1) * RAW / gg, (sy + 1) * RAW / gg]
    R_roads = [(dc, np.asarray(p)) for lf in rleaves for dc, p in lf["_links"]]
    RS = np.vstack([segs(p, False) for _, p in R_roads if len(p) > 1])
    out = {"R_rect_grid": rg, "R_rect_check_max_outside_raw": rworst,
           "G_oracle_disc": str(G_DISC / "ALLDATA.KWI"), "G_divided": gdiv, "G_rect_grid": gg,
           "G_rect_check_max_outside_raw": gworst,
           "G_leaves": [{k: v for k, v in lf.items() if not k.startswith("_")} for lf in gleaves],
           "trimmed_sub": [sx, sy], "trimmed_sub_rect_raw": sub_rect,
           "R_quantum_parent_raw": 1.0,
           "R_quantum_note": "every R leaf here has frame range 4096 over the whole parent (divided_parent or leaf), so one R coordinate step is one parent raw unit"}
    # per-sub-cell volume: G kept (oracle decode) vs R road length inside each G sub-cell rect
    vol = []
    for lf in gleaves:
        r = lf["rect_leaf_raw"]
        glen = sum(in_rect_len(np.asarray(p), r) for _, p in lf["_links"])   # length inside the leaf's own rect
        rlen = sum(in_rect_len(p, r) for _, p in R_roads)
        vol.append({"leaf_path": lf["leaf_path"], "rect": r, "G_kept_links": len(lf["_links"]),
                    "G_kept_len_in_rect_raw": round(glen, 1), "R_len_in_rect_raw": round(rlen, 1),
                    "G_over_R": round(glen / rlen, 3) if rlen else None})
    dlen = sum(plen(i["P"]) for i in roadsD); klen = sum(plen(i["P"]) for i in roadsK)
    out["road_volume"] = {"per_G_leaf": vol,
                          "trimmed_sub": {"G_pre_trim_pieces": len(roadsD) + len(roadsK), "G_kept_pieces": len(roadsK),
                                          "G_dropped_pieces": len(roadsD), "G_pre_trim_len_raw": round(dlen + klen, 1),
                                          "G_dropped_len_raw": round(dlen, 1),
                                          "R_len_in_rect_raw": round(sum(in_rect_len(p, sub_rect) for _, p in R_roads), 1)},
                          "R_links_whole_parent": len(R_roads),
                          "G_kept_links_whole_parent": sum(len(lf["_links"]) for lf in gleaves),
                          "R_classes": dict(Counter(dc for dc, _ in R_roads)),
                          "G_classes_kept_whole_parent": dict(Counter(dc for lf in gleaves for dc, _ in lf["_links"])),
                          "G_classes_dropped": dict(Counter(i["code"] for i in roadsD))}
    # piece lengths / vertex counts (review F1 evidence)
    out["piece_shape"] = {"dropped_len_raw": qs([plen(i["P"]) for i in roadsD]),
                          "dropped_n_pts": dict(Counter(len(i["P"]) for i in roadsD)) if len(roadsD) < 2000 else None,
                          "kept_len_raw": qs([plen(i["P"]) for i in roadsK]) if roadsK else None}
    # control distribution: per-piece median sample distance to R roads (any class)
    def med_dist(P, step):
        Q = sample(P, step)
        d = local_dist(Q, RS, 600.0)
        d = np.where(np.isfinite(d), d, 600.0)   # beyond reach: clamp (reported as >=600)
        return float(np.median(d))
    if roadsK:
        ctrl = [med_dist(i["P"], 0.25) for i in roadsK]; ctrl_src = "kept pieces of the trimmed sub-cell (exact dump geometry)"
    else:
        ctrl = [med_dist(np.asarray(p), 2.0) for lf in gleaves if lf["leaf_path"][-1] != sy * gg + sx
                for _, p in lf["_links"] if len(p) > 1]
        ctrl_src = "G oracle-decoded kept roads of the parent's other sub-cells (no kept road in the trimmed sub-cell)"
    drop = [med_dist(i["P"], 0.25 if level else 2.0) for i in roadsD]
    rec = {t: round(float(np.mean(np.asarray(ctrl) <= t)), 4) for t in TOLS}
    rec_d = {t: round(float(np.mean(np.asarray(drop) <= t)), 4) for t in TOLS}
    tstar = next((t for t in TOLS if rec[t] >= 0.9), None)
    out["road_control"] = {"source": ctrl_src, "n": len(ctrl),
                           "metric": "per-piece median of sampled distance to the nearest R road of any class, parent raw units (clamped at 600)",
                           "control_quantiles": qs(ctrl), "dropped_quantiles": qs(drop),
                           "control_recall_at_tol": rec, "dropped_within_tol": rec_d,
                           "calibrated_tol_recall90": tstar,
                           "dropped_present_at_calibrated_tol": int(sum(d <= tstar for d in drop)) if tstar else None,
                           "dropped_absent_at_calibrated_tol": int(sum(d > tstar for d in drop)) if tstar else None}
    # L8-style redundancy: are dropped pieces within one R quantum of kept G pieces?
    if roadsK:
        KS = np.vstack([segs(i["P"], False) for i in roadsK if len(i["P"]) > 1])
        cats = Counter()
        for i in roadsD:
            L = plen(i["P"]); Q = sample(i["P"], 0.05)
            dK = local_dist(Q, KS, 2.0); dR = local_dist(Q, RS, 2.0)
            nonred = dK > 1.0
            if L < 1.0:
                c = "sub-quantum (<1 R step)"
            elif not nonred.any():
                c = "redundant (every sample within 1 R step of a kept G piece)"
            else:
                f = float((dR[nonred] <= 1.0).mean())
                c = "R-has-specific" if f >= 0.5 else "R-lacks" if f == 0 else "ambiguous"
            i["v2"] = c; cats[c] += 1
        out["dropped_categories"] = dict(cats)
        out["dropped_within_1_of_kept_all_vertices"] = int(sum(
            bool((local_dist(i["P"], KS, 2.0) <= 1.0).all()) for i in roadsD))
        # kept control, any class primary (review F3)
        kc = Counter()
        for i in roadsK:
            d = local_dist(i["P"], RS, 2.0)
            kc["present" if (d <= 1).all() else "absent" if not (d <= 1).any() else "ambiguous"] += 1
        out["kept_any_class_v1_rule"] = dict(kc)
    # background census (review F2): types in G (oracle, whole parent) vs R
    gt = Counter((cl, tc) for lf in gleaves for tc, cl, _ in lf["_bgs"])
    rt = Counter((cl, tc) for lf in rleaves for tc, cl, _ in lf["_bgs"])
    out["background_census"] = {"G_class_type": {f"{c}:{t}": n for (c, t), n in sorted(gt.items())},
                                "R_class_type": {f"{c}:{t}": n for (c, t), n in sorted(rt.items())},
                                "dropped_types": dict(Counter(i["code"] for i in items if i["kind"] == 1 and i["KD"] == "D"))}
    return out


def main():
    rr = RReader(R_DISC)
    res = {"rule_v1_not_validated": __doc__.split("Match rule")[1].split("Writes")[0].strip(), "cases": []}
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
        leaf_rects(leaves)   # review F5: quadrant rect for divided leaves
        r_bg = []
        for lf in leaves:
            for tc, cl, pts in lf["_bgs"]:
                if cl == 2 and len(pts) >= 3:
                    P = np.asarray(pts)
                    r_bg.append((tc, P, lf["rect_leaf_raw"], P.min(0), P.max(0)))
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
        case["v2"] = v2_analysis(level, ix, iy, rows, leaves)
        res["cases"].append(case)
        print(level, ix, iy, status, divided, len(leaves), [(lf["leaf_path"], lf["length"], lf["n_road_links"], lf["n_bg"]) for lf in leaves])
        print(" ", case["summary"])
    (HERE / "trim_witness.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
