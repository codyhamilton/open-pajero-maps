#!/usr/bin/env python3
"""Plan 62 Phase 1: still-outside@16 census join (light, streaming; no clipping).

Joins every R-G5-4 row to the plan-46 tracked producer scan of the 013586b5 background dump
(Moore R=8 U far bbox-meet homes, per-piece byte match, same-type producer, divided-leaf clip
rect: plan 46 RC2-RC6):
  - R-G5-4-a/b: plan 44 decisions (95,059; p5_owner_exclusive/phase2_decisions_full.tsv.gz)
    with leaf paths from rows_weak/rows_none;
  - R-G5-4-c: plan 45 per-row decisions (80; p4_ceiling/).
Output: one TSV.gz row per residual row (gzip mtime=0) + cross-tab JSON.
The background dump rows differ between 87a01b14 (plan 44 basis) and 013586b5 only in cell
0/1769/587 (p1/basis_311.json); rows there are flagged basis_cell_311.
"""
import csv, gzip, io, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HB = ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg"
P5, P4 = HB / "p5_owner_exclusive", HB / "p4_ceiling"
BASIS_CELL = ("0", "1769", "587")
SCAN_COLS = ("row_index", "vx", "vy", "producer_class", "producer_raw", "producer_hx", "producer_hy",
             "producer_ri", "mechanism")


def rd(p):
    op = gzip.open if str(p).endswith(".gz") else open
    with op(p, "rt") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main(scan_dir, out):
    scan_dir, out = Path(scan_dir), Path(out)
    paths = {}
    for r in rd(P5 / "rows_weak.tsv.gz") + rd(P5 / "rows_none.tsv.gz"):
        paths[(r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"])] = (r["p0"], r["p1"], r["p2"])
    rows = []
    for d in rd(P5 / "phase2_decisions_full.tsv.gz"):
        k6 = (d["level"], d["ix"], d["iy"], d["shape"], d["vert"], d["code"])
        p = paths[k6]
        rows.append({"parent": "R-G5-4-a" if d["src"] == "weak" else "R-G5-4-b", "level": d["level"], "ix": d["ix"],
                     "iy": d["iy"], "depth": d["depth"], "p0": p[0], "p1": p[1], "p2": p[2], "shape": d["shape"],
                     "vert": d["vert"], "code": d["code"], "p44_decision": d["decision"],
                     "p44_producer_class": d["producer_class"], "p44_recover_r": d["recover_r"],
                     "p44_extra": d["extra"]})
    keys80 = {(r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"]): r for r in rd(P4 / "rows_80_keys.tsv")}
    for d in rd(P4 / "per_row_decisions.tsv"):
        k6 = (d["level"], d["ix"], d["iy"], d["shape"], d["vert"], d["code"])
        kr = keys80[k6]
        rows.append({"parent": "R-G5-4-c", "level": d["level"], "ix": d["ix"], "iy": d["iy"], "depth": d["depth"],
                     "p0": kr["p0"], "p1": kr["p1"], "p2": kr["p2"], "shape": d["shape"], "vert": d["vert"],
                     "code": d["code"], "p44_decision": d["decision"] + "@16(p45)",
                     "p44_producer_class": d["producer_class"], "p44_recover_r": "16", "p44_extra": d["extra"]})
    want = {}
    for i, r in enumerate(rows):
        k = (r["level"], r["ix"], r["iy"], r["depth"], r["p0"], r["p1"], r["p2"], r["shape"], r["vert"], r["code"])
        assert k not in want, k
        want[k] = i
    hit = 0
    for part in sorted(scan_dir.glob("bg.s*/scan.tsv.gz")):
        with gzip.open(part, "rt") as f:
            for s in csv.DictReader(f, delimiter="\t"):
                k = (s["level"], s["ix"], s["iy"], s["depth"], s["p0"], s["p1"], s["p2"], s["shape"], s["vert"], s["code"])
                i = want.get(k)
                if i is not None:
                    for c in SCAN_COLS:
                        rows[i]["s46_" + c] = s[c]
                    hit += 1
    for r in rows:
        r["basis_cell_311"] = int((r["level"], r["ix"], r["iy"]) == BASIS_CELL)
        for c in SCAN_COLS:
            r.setdefault("s46_" + c, "")
    fields = list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, delimiter="\t", lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    with open(out, "wb") as fo, gzip.GzipFile(filename="", mode="wb", fileobj=fo, mtime=0) as gz:
        gz.write(buf.getvalue().encode())
    xt = Counter((r["parent"], r["p44_decision"], r["s46_producer_class"] or "UNJOINED") for r in rows)
    summ = {"rows": len(rows), "joined": hit, "unjoined": len(rows) - hit,
            "basis_cell_311_rows": sum(r["basis_cell_311"] for r in rows),
            "crosstab": {"|".join(k): v for k, v in sorted(xt.items())}}
    out.with_suffix(".json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
