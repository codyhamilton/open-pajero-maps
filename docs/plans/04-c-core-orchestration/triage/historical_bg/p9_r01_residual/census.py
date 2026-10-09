#!/usr/bin/env python3
"""Plan 62 Phase 1: residual census of R-G5-4-a/b (the plan-44 residual of 7,316 non-stitch rows)
and R-G5-4-c (plan 45's 80 rows), from census_join.tsv.gz (all 95,139 rows joined to the plan-46 scan).

Columns: parent, keys, old_class (plan-44/45 matcher class), cell depth, historical source
(plan 44: decision extra; plan 45: K1 dump src_ix/src_iy/src_rec/src_nv/reason, brief 3-03),
plan-46 scan producer (s46_*). Deterministic gzip (mtime 0)."""
from __future__ import annotations

import csv, gzip, json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser/tools"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p6_producer")]
from phase23 import det_gz_text, close_det, sha, relp, content_sha  # noqa: E402
import r01_redecide as rd  # noqa: E402

H = ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg"


def main():
    join = H / "p9_r01_residual/census_join.tsv.gz"  # = output/scratch-62/census_join.tsv.gz (census_join.py)
    src80 = H / "p4_ceiling/rows_80_keys.tsv"
    p44 = H / "p5_owner_exclusive/phase2_decisions_full.tsv.gz"
    out = H / "p9_r01_residual/census.tsv.gz"
    src = {}
    with open(src80) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            src[(r["level"], r["ix"], r["iy"], r["p0"], r["shape"], r["vert"])] = r
    rows = []
    with gzip.open(join, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            oc = rd.old_class(r["p44_decision"])
            if oc == "build" and r["parent"] != "R-G5-4-c":
                continue
            hist = r["p44_extra"]
            if r["parent"] == "R-G5-4-c":
                s = src[(r["level"], r["ix"], r["iy"], r["p0"], r["shape"], r["vert"])]
                hist = json.dumps({k: s[k] for k in ("src_ix", "src_iy", "src_rec", "src_nv", "reason")},
                                  separators=(",", ":"))
            rows.append({"parent": r["parent"], "level": r["level"], "ix": r["ix"], "iy": r["iy"],
                         "depth": r["depth"], "p0": r["p0"], "p1": r["p1"], "p2": r["p2"],
                         "shape": r["shape"], "vert": r["vert"], "code": r["code"],
                         "old_decision": r["p44_decision"], "old_class": oc,
                         "old_producer_class": r["p44_producer_class"], "old_recover_r": r["p44_recover_r"],
                         "historical_source": hist,
                         "s46_row_index": r["s46_row_index"], "vx": r["s46_vx"], "vy": r["s46_vy"],
                         "s46_producer_raw": r["s46_producer_raw"],
                         "s46_producer": f'{r["s46_producer_hx"]},{r["s46_producer_hy"]},{r["s46_producer_ri"]}',
                         "s46_mechanism": r["s46_mechanism"]})
    f = det_gz_text(out)
    w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
    w.writeheader(); w.writerows(rows); close_det(f)
    cnt = Counter((r["parent"], r["old_class"], r["s46_producer_raw"]) for r in rows)
    summ = {"rows": len(rows),
            "by_parent": dict(sorted(Counter(r["parent"] for r in rows).items())),
            "by_parent_oldclass": {"|".join(k): n for k, n in
                                   sorted(Counter((r["parent"], r["old_class"]) for r in rows).items())},
            "by_parent_oldclass_s46": {"|".join(k): n for k, n in sorted(cnt.items())},
            "by_depth": dict(sorted(Counter(f'{r["parent"]}|d{r["depth"]}' for r in rows).items())),
            "c_by_cell": dict(sorted(Counter(f'{r["ix"]},{r["iy"]}' for r in rows
                                             if r["parent"] == "R-G5-4-c").items())),
            "cells": len({(r["level"], r["ix"], r["iy"]) for r in rows}),
            "inputs": {"census_join": [relp(join), sha(join)], "rows_80_keys": [relp(src80), sha(src80)],
                       "plan44_decisions": [relp(p44), sha(p44)]},
            "file": relp(out), "sha256": sha(out), "content_sha256": content_sha(out)}
    (out.parent / "census.json").write_text(json.dumps(summ, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
