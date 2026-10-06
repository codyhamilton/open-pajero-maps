"""Plan 43 P2 R-G8-4-a / R-G8-2-f: regenerate the 3-17 completeness-only classify on the retained 776-row dump.

1. Re-hash scratch-14/dump_raw/completeness.bin (must be 1a91b1c2...).
2. Side table = plan 28 per_rule_completeness_mechanism.tsv with other_mechanism forced to 0 on every row whose
   (level, ix, iy) is in plan 31's 3-14 AU changed-cell list (diff-3-14-au.cells.tsv, sha 77ff1d86..., 246,123 rows):
   the 3-14 dump extension's "conservatively zeroes it on changed cells" (rebaseline_3-17_9064.md).
3. dump_join --mode other_mechanism (unchanged tool) -> output/scratch-43/dump_forced (completeness-only, 152 B rows).
Classify runs are in run_p2.sh; compare.py reads their assign_completeness.u16."""
import csv, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[7]
T = ROOT / "docs/plans/04-c-core-orchestration/triage"
S = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-43")
RAW = ROOT / "output/scratch-14/dump_raw/completeness.bin"
CELLS = ROOT / "output/scratch-31/diff-3-14-au.cells.tsv"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
out = {"dump_raw_sha256": sha(RAW), "cells_sha256": sha(CELLS)}
assert out["dump_raw_sha256"].startswith("1a91b1c2"), out
assert out["cells_sha256"].startswith("77ff1d86"), out
cells = set()
with open(CELLS) as f:
    hdr = f.readline().rstrip("\n").split("\t"); il, ix, iy = hdr.index("level"), hdr.index("ix"), hdr.index("iy")
    for line in f:
        p = line.rstrip("\n").split("\t"); cells.add((int(p[il]), int(p[ix]), int(p[iy])))
out["cells_rows"] = len(cells); assert len(cells) == 246123
src = T / "per_rule_completeness_mechanism.tsv"; out["side_src_sha256"] = sha(src)
S.mkdir(parents=True, exist_ok=True); dst = S / "side_forced.tsv"
rows = list(csv.DictReader(open(src), delimiter="\t"))
forced = []
with open(dst, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t", lineterminator="\n"); w.writeheader()
    for r in rows:
        if (int(r["level"]), int(r["ix"]), int(r["iy"])) in cells and r["other_mechanism"] != "0":
            forced.append((int(r["dump_row"]), int(r["other_mechanism"]))); r = dict(r, other_mechanism="0")
        w.writerow(r)
out["rows"] = len(rows); out["forced_rows"] = len(forced)
out["forced_by_code"] = {str(c): sum(1 for _, k in forced if k == c) for c in sorted({k for _, k in forced})}
out["forced_dump_rows"] = sorted(r for r, _ in forced)
out["side_forced_sha256"] = sha(dst)
json.dump(out, open(Path(__file__).with_name("forced_zero.json"), "w"), indent=1)
print({k: v for k, v in out.items() if k != "forced_dump_rows"})
