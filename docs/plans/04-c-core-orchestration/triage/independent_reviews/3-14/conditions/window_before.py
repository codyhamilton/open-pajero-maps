"""Plan 43 P1 R-G8-1-b context: pre-3-14 failing rows per committed 3-13 CF window (causes_rootcause.md L60-77), counted
from plan 39's keyed per-row arrays (output/scratch-39/keep/, 87a01b14 basis; identical to 013586b5 outside the 37 3-11
cells, which are flagged). Window = inclusive cell range at the level, type = the window's target type code. Context only:
the after-0 claim is carried by the whole-disc K1 on 4ed9cd80."""
import json, numpy as np
W = [(0, 288, (1769, 202, 1772, 205), 32, 255), (0, 291, (828, 745, 831, 748), 69, 829), (0, 289, (1401, 851, 1402, 852), 32, 90),
     (0, 578, (1400, 1287, 1401, 1288), 23, 60), (2, 289, (202, 229, 203, 230), 17, 108), (6, 288, (15, 17, 16, 18), 0, 132),
     (0, 291, (1792, 395, 1793, 396), None, 196), (0, 291, (1801, 395, 1802, 396), None, 132), (0, 291, (1805, 395, 1806, 396), None, 120)]
K = "output/scratch-39/keep/87a01b14_%s_keyed.npz"
cells37 = {tuple(map(int, l.split("\t")[:3])) for l in open("output/scratch-36/diff-3-11-au.cells.tsv").read().splitlines()[1:]}
A = {k: np.load(K % k) for k in ("background", "background_boundary")}
out = []
for L, t, (x0, y0, x1, y1), fill_t, bnd_t in W:
    r = {"level": L, "type": t, "window": [x0, y0, x1, y1], "table_fill_before": fill_t, "table_boundary_before": bnd_t}
    for k, a in A.items():
        m = (a["level"] == L) & (a["ix"] >= x0) & (a["ix"] <= x1) & (a["iy"] >= y0) & (a["iy"] <= y1)
        r[k + "_all_types"] = int(m.sum()); r[k + "_type"] = int((m & (a["code"] == t)).sum())
    r["overlaps_37_cells"] = any(c[0] == L and x0 <= c[1] <= x1 and y0 <= c[2] <= y1 for c in cells37)
    out.append(r); print(r)
json.dump(out, open("docs/plans/04-c-core-orchestration/triage/independent_reviews/3-14/conditions/window_before.json", "w"), indent=1)
