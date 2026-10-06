"""Plan 39 P2 partial: R01 rows (87a01b14 replay basis) against build-fixed clauses (a) and (c). Light: memmap of background.bin + assign file."""
import json, gzip, sys, numpy as np
from collections import Counter
S = "output/scratch-39"
man = json.load(open(f"{S}/dump_pre311/dump_manifest.json"))["kinds"]["background"]
dt = np.dtype([(f["name"], {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}[f["type"]]) for f in man["fields"]])
pad = man["row_size"] - dt.itemsize
if pad: dt = np.dtype({"names": list(dt.names), "formats": [dt.fields[n][0] for n in dt.names], "offsets": [dt.fields[n][1] for n in dt.names], "itemsize": man["row_size"]})
rows = np.memmap(f"{S}/dump_pre311/background.bin", dtype=dt, mode="r")
assign = np.fromfile(f"{S}/classifyR01_pre311/assign_background.u16", dtype="<u2")
assert len(assign) == len(rows) == man["rows"]
r01 = assign == 0   # rule index 0 = R01; 65535 = unclassified
causes = {}
with gzip.open("docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/cells_causes-au.tsv.gz", "rt") as f:
    next(f)
    for line in f:
        a = line.split("\t"); causes[(int(a[0]), int(a[1]), int(a[2]))] = a[3]
def cellcls(m):
    lv, ix, iy = rows["level"][m].astype(int), rows["ix"][m].astype(int), rows["iy"][m].astype(int)
    return dict(Counter(causes.get((l, x, y), "NOT-CHANGED") for l, x, y in zip(lv, ix, iy)))
cls = cellcls(r01); cls_un = cellcls(assign == 65535)
k314 = json.load(open(f"{S}/k1_314.json"))["totals"]["background"]
out = {"r01_rows_pre311": int(r01.sum()), "assign_values": {str(int(v)): int((assign == v).sum()) for v in np.unique(assign)},
       "clause_a_absent_on_4ed9cd80": {"holds_for_all": k314["failing"] == 0, "basis": "K1 background failing on 4ed9cd80 = %d (dump_314 empty)" % k314["failing"]},
       "clause_c_cell_class": cls, "non_R01_background_cell_class": cls_un,
       "clause_b_item_still_checked": "NOT TESTED: K1 dumps failing items only; no per-item checked identity on 4ed9cd80. Whole-kind background checked 175,171,302 (013586b5) -> 176,386,506 (4ed9cd80)"}
json.dump(out, open(f"{S}/r01_join.json", "w"), indent=1); print(json.dumps(out, indent=1))
