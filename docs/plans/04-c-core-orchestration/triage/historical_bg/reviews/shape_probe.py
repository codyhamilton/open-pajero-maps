"""Reviewer probe (light): for a sample of R01 leaves, is the failing vertex's *record* (same type) still present
in the same leaf on 4ed9cd80, and how far is the failing raw vertex from the nearest same-type vertex there?"""
import random, json
src = open("docs/plans/04-c-core-orchestration/triage/historical_bg/p2/r01_clause_b.py").read()
src = src.replace('__file__', '"docs/plans/04-c-core-orchestration/triage/historical_bg/p2/r01_clause_b.py"')
head = src.split("old = frames(")[0]
exec(head.split("cells = set(zip(")[0])
random.seed(7)
allc = sorted(set(zip(rows["level"].tolist(), rows["ix"].tolist(), rows["iy"].tolist())))
cells = set(random.sample(allc, 60))
exec("def frames" + head.split("def frames")[1].split("def records")[0])
exec("def records" + head.split("def records")[1])
old = frames("output/scratch-36/G_pre311/ALLDATA.KWI"); new = frames("output/scratch-14/G_new/ALLDATA.KWI")
from collections import Counter
st = Counter(); dists = []; rs = Counter(); onb = Counter(); recsame = Counter()
for r in rows:
    c = (int(r["level"]), int(r["ix"]), int(r["iy"]))
    if c not in cells or fe.get(c, ("", "0"))[1] != "1": continue
    k = c + (leafkey(r),)
    if k not in new: st["leaf_missing"] += 1; continue
    bgn = sec.split(new[k])["background"]; bgo = sec.split(old[k])["background"]
    ro = records(bgo); rn = records(bgn)
    code = int(r["code"])
    pts = []
    for p, cd, cls in rn:
        if cls and cd == code:
            xs, ys = verts(bgn, p); pts += list(zip(xs.tolist(), ys.tolist()))
    st["type_present_in_leaf" if pts else "type_absent_in_leaf"] += 1
    # same record bytes present on new?
    s = int(r["shape"]); p0 = ro[s][0]; L = (sec.u16(bgo, p0) & 0xFFF) * 2
    rb = bytes(bgo[p0:p0 + L]); recsame["record_bytes_unchanged" if rb in bytes(bgn) else "record_bytes_changed"] += 1
    if pts:
        a = np.array(pts); d = np.hypot(a[:, 0] - int(r["vx"]), a[:, 1] - int(r["vy"])).min(); dists.append(float(d))
    rs[int(r["reason"])] += 1; onb[int(r["onb"])] += 1
d = np.array(dists)
print(json.dumps({"cells": len(cells), **st, **recsame, "reason": dict(rs), "onb": dict(onb),
  "nearest_same_type_vertex_raw": {"n": len(d), "eq0": int((d == 0).sum()), "le1": int((d <= 1).sum()), "le16": int((d <= 16).sum()),
  "le256": int((d <= 256).sum()), "median": float(np.median(d)) if len(d) else None, "max": float(d.max()) if len(d) else None}}, indent=1))
