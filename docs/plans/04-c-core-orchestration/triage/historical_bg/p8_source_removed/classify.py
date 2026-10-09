#!/usr/bin/env python3
"""Plan 64 classifier: the H1-H5 five-way test per empty-clip group (Phase 2/3 evidence).

Inputs: trace.json (Phase 1), stage.json (Phase 2 d35b565 stage trace), the discs (R, 4ed9cd80,
0c22b266; read-only) and the spool. Per group:
  H1 wrong producer      : sidecar emitter of the 013586b5 shape != recorded producer, or the producer's
                           33006aa clip does not reproduce the shape's bytes.
  H5 extract defect      : producer ring != its OSM way's coordinates (closure included) or its type !=
                           the documented bg_type mapping (first matching level-0 rule).
  coverage (R comparison): the producer's exact in-leaf region (ring polygon (even-odd) clipped to the
                           leaf clip rect) and the leaf rect itself, against every same-type R record of
                           the leaf's cell (parent-raw units): count of R same-type polygons meeting the
                           leaf rect, the in-leaf region's sample points covered by R same-type records,
                           min distance region->R same-type boundary; same for 4ed9cd80 / 0c22b266.
  stage                  : d35b565 producer call(s) in the committed frame (or the divided-leaf
                           assignment clip): EO path, faces, pieces dropped at round/clean.
  H3 correct removal     : H1, H5 false; the 33006aa record is a legacy artefact (its area exceeds the
                           exact in-leaf region by >= 100x); d35b565 drops every interior face at lattice
                           round/clean (pieces == pzero, rec == 0); and R has no same-type coverage of
                           the region (no R same-type polygon meets the leaf rect, or none covers a region sample point).
  H2 / H4 candidates     : R has same-type coverage of the region -> open (stage defect = H2 if the stage
                           trace names a defect, else H4 needs both source-absence proofs) -> stays open.
Writes classify.json."""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trace as TR  # noqa: E402
from trace import S, cell_b4  # noqa: E402

ARTEFACT_RATIO = 100.0


def seg_dist(P, Q):
    """min distance from points P (k,2) to closed polygon Q's edges."""
    if len(Q) < 2 or len(P) == 0:
        return float("inf")
    A = Q; B = np.roll(Q, -1, 0); AB = B - A; L = (AB ** 2).sum(1)
    best = np.inf
    for p in P:
        t = np.where(L > 0, ((p - A) * AB).sum(1) / np.where(L > 0, L, 1), 0).clip(0, 1)
        d = np.sqrt((((A + t[:, None] * AB) - p) ** 2).sum(1)).min()
        best = min(best, float(d))
    return best


def region_samples(ring, rect, n=200):
    """sample points of the exact even-odd region ring ∩ rect (grid over the clipped bbox); area = the larger
    of the Sutherland-Hodgman area and the sample estimate (conservative for the artefact ratio)."""
    ca, pts = TR.rect_clip_area(ring, rect)
    if not pts:
        return np.zeros((0, 2)), 0.0, None
    P = np.asarray(pts); lo, hi = P.min(0), P.max(0)
    xs = np.linspace(lo[0], hi[0], n + 1)[:-1] + (hi[0] - lo[0]) / (2 * n)
    ys = np.linspace(lo[1], hi[1], n + 1)[:-1] + (hi[1] - lo[1]) / (2 * n)
    gx, gy = np.meshgrid(xs, ys)
    R_ = np.asarray(ring, float)
    m = TR.pip(gx, gy, R_) & (gx >= rect[0]) & (gx <= rect[2]) & (gy >= rect[1]) & (gy <= rect[3])
    sa = float(m.sum()) / (n * n) * float((hi[0] - lo[0]) * (hi[1] - lo[1]))
    return np.column_stack([gx[m], gy[m]]), max(ca, sa), [*lo.tolist(), *hi.tolist()]


def main(argv=None):
    ap = argparse.ArgumentParser()
    for k in ("trace", "stage", "r_disc", "d35_disc", "live_disc", "spool", "out"):
        ap.add_argument("--" + k.replace("_", "-"), type=Path, required=True)
    a = ap.parse_args(argv)
    tr = json.loads(a.trace.read_text()); st = {g["gid"]: g for g in json.loads(a.stage.read_text())["groups"]}
    from kiwiw.spool import SpoolReader
    from quantisation_roundtrip import Lattice
    spool = SpoolReader(str(a.spool)); far = S.FarHomes(a.spool, 0); lat = Lattice(0)
    discs = {"R": a.r_disc, "4ed9cd80": a.d35_disc.parent, "0c22b266": a.live_disc.parent}
    dcache = {}; out = []
    for g in tr["groups"]:
        lv, ix, iy, path = g["leaf"]
        hx, hy, ri, tc = g["producer"]
        rect = g["clip_rect"]; cr = g["clip_range"]
        assert cr == 4096.0, "parent-raw == leaf-raw only when the clip range is 4096"
        b4, _cr, rect2 = S.leaf_clip_geometry(lv, ix, iy, tuple(path), g["parcel_type"], cell_b4)
        assert list(rect2) == rect
        ring = next(rg for cid, rg, _ll in S.fast_spool_candidates(spool, lv, ix, iy, rect2, b4, cr, 8, None,
                                                                    extra_homes=far.query(ix, iy))
                    if cid[:3] == (hx, hy, ri))
        samp, carea, cbbox = region_samples(ring, rect)
        cov = {}
        for dn, dp in discs.items():
            _st, _dv, recs = TR.disc_cell(str(dp), ix, iy, lat, dcache)
            same = [r for r in recs if r["type"] == tc and r["class"] == 2 and len(r["P"]) >= 3]
            meet = [r for r in same if not ((r["P"].max(0) < [rect[0], rect[1]]).any() or (r["P"].min(0) > [rect[2], rect[3]]).any())]
            covered = np.zeros(len(samp), bool)
            for r in meet:
                if len(samp):
                    covered |= TR.pip(samp[:, 0], samp[:, 1], r["P"])
            dmin = min([seg_dist(samp, r["P"]) for r in meet], default=float("inf")) if len(samp) else None
            cov[dn] = {"same_type_polygons_in_cell": len(same), "same_type_meeting_leaf_rect": len(meet),
                       "region_samples_covered": int(covered.sum()), "region_min_dist_raw": dmin}
        s = st[g["gid"]]
        calls = s["calls"] + s.get("dv_assign_calls", [])
        stage = {"n_calls": len(calls), "paths": sorted({c["path_name"] for c in calls}),
                 "eo_complex_reason": sorted({c["cx"] for c in calls}),
                 "faces": sum(c["faces"] for c in calls), "faces_pos_area": sum(c["fpos"] for c in calls),
                 "faces_interior": sum(c["fleft"] for c in calls), "pieces": sum(c["pieces"] for c in calls),
                 "pieces_dropped_round": sum(c["pzero"] for c in calls), "records": sum(c["rec"] for c in calls),
                 "dropped_lt3_points_cenc586": sum(c["pq3"] for c in calls),
                 "dropped_zero_area_cenc592": sum(c["pa0"] for c in calls),
                 "divided_assignment": bool(s.get("dv_assign_calls"))}
        h1 = not (g["sidecar_equals_producer"] and g["probe"]["33006aa"]["shape_bytes_in_pieces"]
                  and g["scan_unique_byte_hits_33006aa"] == [[hx, hy, ri]])
        e = g["extract"]
        h5 = not (e["ring_equal"] and e["bg_type"] == tc and e["bg_rule"] and e["bg_rule"]["value"] == tc)
        art = g["shape_geometry"]["area_raw2"] / max(carea, 1e-9)
        stage_drop = (stage["n_calls"] > 0 and stage["records"] == 0 and stage["pieces"] == stage["pieces_dropped_round"]
                      and g["probe"]["d35b565"]["size"] == 0)
        # R has no same-type polygon anywhere in the leaf rect, or (with region samples) none covers the region
        r_none = cov["R"]["same_type_meeting_leaf_rect"] == 0 or (len(samp) > 0 and cov["R"]["region_samples_covered"] == 0)
        if h1:
            verdict = "H1"
        elif h5:
            verdict = "H5"
        elif art >= ARTEFACT_RATIO and stage_drop and r_none:
            verdict = "H3"
        else:
            verdict = "open"
        out.append({"gid": g["gid"], "row": g["row"], "rows": g["rows"], "leaf": g["leaf"], "producer": g["producer"],
                    "H1": h1, "H5": h5, "osm_way": e["osm_way"], "osm_tags": e["tags"], "osm_way_closed": e["osm_way_closed"],
                    "bg_rule": e["bg_rule"], "shape_area_raw2": g["shape_geometry"]["area_raw2"],
                    "exact_region_area_raw2": round(carea, 4), "exact_region_bbox": cbbox,
                    "region_samples": len(samp), "artefact_ratio": round(art, 1), "stage": stage,
                    "coverage": cov, "verdict": verdict})
        print(json.dumps({"gid": g["gid"], "verdict": verdict, "art": round(art), "Rcov": cov["R"]["region_samples_covered"],
                          "Rmeet": cov["R"]["same_type_meeting_leaf_rect"], "samp": len(samp)}), flush=True)
    summ = {}
    for o in out:
        summ.setdefault(o["row"], {}).setdefault(o["verdict"], [0, 0])
        summ[o["row"]][o["verdict"]][0] += 1; summ[o["row"]][o["verdict"]][1] += o["rows"]
    res = {"groups": out, "summary_groups_rows": summ, "artefact_ratio_min": ARTEFACT_RATIO}
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True, default=str) + "\n")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
