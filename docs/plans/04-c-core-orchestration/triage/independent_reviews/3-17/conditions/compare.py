"""Plan 43 P2: per-row assignment of the forced-zero completeness classify (both CLIs), compared with plan 28's assignment
(3-15 basis) and plan 37's 34-row forced-zero identity. Writes completeness_forced_assignment.tsv and compare.json."""
import csv, json, sys
from collections import Counter
from pathlib import Path
import numpy as np
C = Path(__file__).resolve().parent; T = C.parents[2]
S = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-43")
NO_RULE = 65535
rules = json.load(open(S / "rules/rules_completeness_cur.json"))["rules"]
man = json.load(open(S / "p2/dump_forced/dump_manifest.json"))
res = {}
assign = {}
for tag, d in (("cur", S / "p2/cls_completeness_cur"), ("at317", S / "p2/cls_completeness_at317"),
               ("view_cur", S / "p2/x_view_completeness_cur"), ("view_at317", S / "p2/x_view_completeness_at317")):
    a = np.fromfile(d / "assign_completeness.u16", dtype="<u2")
    assign[tag] = [("NO_RULE" if v == NO_RULE else rules[v]["id"]) for v in a.tolist()]
    res[tag] = {"rows": len(a), "rule_counts": dict(sorted(Counter(assign[tag]).items())),
                "partition": (d / "partition.txt").read_text().splitlines(),
                "cause_counts": (d / "cause_counts.tsv").read_text().splitlines(),
                "exit": int((S / f"p2/{d.name}.rc").read_text().split()[-1])}
assert assign["cur"] == assign["at317"] == assign["view_cur"] == assign["view_at317"]
p28 = list(csv.DictReader(open(T / "per_rule_classify_assignment.tsv"), delimiter="\t"))
f2 = {int(r["dump_row"]): r for r in csv.DictReader(open(T / "per_rule_phase1_f2_identity.tsv"), delimiter="\t")}
ext = man.get("extension_other_mechanism", {})
src_rows = ext.get("dump_rows") or ext.get("source_dump_rows") or list(range(len(p28)))
assert len(src_rows) == len(p28) == res["cur"]["rows"]
KEY = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")
delta = []
with open(C / "completeness_forced_assignment.tsv", "w", newline="") as fh:
    w = csv.writer(fh, delimiter="\t", lineterminator="\n")
    w.writerow(KEY + ("dump_row", "rule_315_plan28", "rule_forced_zero", "forced_zero_changed_cell"))
    for i, r in enumerate(p28):
        assert int(r["dump_row"]) == int(src_rows[i])
        new = assign["cur"][i]
        if new != r["rule_id"]: delta.append(int(r["dump_row"]))
        w.writerow([r[k] for k in KEY] + [r["dump_row"], r["rule_id"], new, int(int(r["dump_row"]) in f2)])
res["changed_rows_vs_plan28"] = len(delta)
res["delta_equals_plan37_34"] = sorted(delta) == sorted(f2)
res["delta_rule_matches_plan37_prediction"] = all(assign["cur"][[int(r["dump_row"]) for r in p28].index(k)] == f2[k]["rule_317_predicted"] for k in f2)
res["yardstick_317"] = {"O01": 363, "O04": 3, "O05": 102, "NO_RULE": 308}
res["match_317"] = res["cur"]["rule_counts"] == res["yardstick_317"]
json.dump(res, open(C / "compare.json", "w"), indent=1); print(json.dumps(res, indent=1))
