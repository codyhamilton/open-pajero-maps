"""Export keyed row sets for plan 44: identity-proven (guard 20), weak (21), none (22), all R01."""
import json, gzip
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
KEEP = ROOT / "output/scratch-39/keep/87a01b14_background_keyed.npz"
a = np.load(KEEP)
a01 = np.fromfile(ROOT / "output/scratch-39/classifyR01_pre311/assign_background.u16", dtype="<u2")
r01 = a01 == 0
KEYS = ("level","ix","iy","depth","p0","p1","p2","shape","vert","code")
summary = {}
for name, code in (("identity_proven", 20), ("weak", 21), ("none", 22)):
    sel = r01 & (a["guard"] == code)
    summary[name] = int(sel.sum())
    with gzip.open(OUT / f"rows_{name}.tsv.gz", "wt") as fh:
        fh.write("\t".join(KEYS) + "\n")
        cols = [a[k][sel] for k in KEYS]
        for row in zip(*[c.tolist() for c in cols]):
            fh.write("\t".join(map(str, row)) + "\n")
json.dump(summary, open(OUT / "row_counts.json", "w"), indent=1)
print(summary)
