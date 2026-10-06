"""Plan 39 P3 screen: failing rows on 87a01b14 (HEAD K1 dumps) that COULD be produced by source (L0,1689,508,rec0,type288).
Necessary conditions for production: level 0, record type 288, vertex inside the source ring's lat/lon bbox (+eps for quantisation)."""
import json, numpy as np, sys
exec(open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + '/../p1/basis_311.py').read().split('out = {')[0])
B = dict(lat0=-44.2609896, lat1=-34.3905473, lon0=134.2256316, lon1=149.0274827); eps = 0.01
out = {"source": "(L0,1689,508,rec0,type288,n1810)", "bbox": B, "eps_deg": eps}
for kind in ("background", "background_boundary", "interior_cover"):
    R, n = load("output/scratch-39/dump_pre311", kind)
    lv, code = np.asarray(R["level"]), np.asarray(R["code"])
    lat, lon = np.asarray(R["lat"]), np.asarray(R["lon"])
    m0 = (lv == 0) & (code == 288)
    mb = m0 & (lat >= B["lat0"] - eps) & (lat <= B["lat1"] + eps) & (lon >= B["lon0"] - eps) & (lon <= B["lon1"] + eps)
    srcm = mb & (np.asarray(R["src_ix"]) == 1689) & (np.asarray(R["src_iy"]) == 508) & (np.asarray(R["src_rec"]) == 0)
    cells = np.unique((np.asarray(R["ix"])[mb].astype(np.int64) << 20) | np.asarray(R["iy"])[mb])
    out[kind] = {"rows": int(n), "L0_type288": int(m0.sum()), "candidates_in_bbox": int(mb.sum()), "candidate_cells": int(len(cells)),
                 "candidates_nearest_src_is_65623": int(srcm.sum())}
    print(kind, out[kind], flush=True)
json.dump(out, open("output/scratch-39/p65623_screen.json", "w"), indent=1)
