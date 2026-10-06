#!/usr/bin/env python3
"""Plan 37 Phase 1: per-row identity for plan 28 F2 (3-15 -> 3-17 O05 -30, O04 -4).

Light join of committed tables plus one streamed read of the 3-14 AU
changed-cell list. The 3-14 dump extension keeps `other_mechanism` only on
byte-unchanged cells and zeroes it on changed cells (`rebaseline_3-17_9064.md`),
so the predicted forced-zero set is every O04/O05 row whose (level, ix, iy) is
a 3-14 changed cell. The script reports that set split shared/added x rule and
checks it against the measured 3-15 and 3-17 bucket counts. It forces no count:
a mismatch is written as residual rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

ASSIGNMENT = HERE / "per_rule_classify_assignment.tsv"
MECHANISM = HERE / "per_rule_completeness_mechanism.tsv"
CELLS = ROOT / "output/scratch-31/diff-3-14-au.cells.tsv"

PINS = {
    "assignment": "per_rule_classify_assignment.tsv",
    "mechanism": "per_rule_completeness_mechanism.tsv",
}
CELLS_SHA = "77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f"
CELLS_ROWS = 246123
# Measured yardsticks (per_rule_phase1_controls.md table; rebaseline_3-17_9064.md).
Y315 = {"O01": 363, "O04": 7, "O05": 132, "O06": 0, "NO_RULE": 274}
Y317 = {"O01": 363, "O04": 3, "O05": 102, "O06": 0, "NO_RULE": 308}
NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")
FORCED = ("O04", "O05")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_tsv(path: Path) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def native(row: dict) -> tuple:
    return tuple(int(row[k]) for k in NATIVE)


def changed_cells(path: Path, wanted: set) -> tuple[dict, int, Counter]:
    """Stream the cell list; return status for wanted (level, ix, iy) only."""
    hit, n, status = {}, 0, Counter()
    with open(path, newline="") as f:
        r = csv.reader(f, delimiter="\t")
        head = next(r)
        il, ix, iy, ist = (head.index(k) for k in ("level", "ix", "iy", "status"))
        for row in r:
            n += 1
            status[row[ist]] += 1
            k = (int(row[il]), int(row[ix]), int(row[iy]))
            if k in wanted:
                hit[k] = row[ist]
    return hit, n, status


def run(assignment: Path, mechanism: Path, cells: Path, *, check_cells_pin: bool = True) -> dict:
    asg, mech = read_tsv(assignment), read_tsv(mechanism)
    if len(asg) != len(mech):
        raise ValueError(f"row count mismatch {len(asg)} vs {len(mech)}")
    part = {}
    for m in mech:
        k = native(m)
        h, a = int(m["in_historic_188"]), int(m["in_added_89"])
        part[k] = {"dump_row": int(m["dump_row"]), "historic": h, "added": a}
    rows = []
    for r in asg:
        k = native(r)
        if k not in part or part[k]["dump_row"] != int(r["dump_row"]):
            raise ValueError(f"assignment row {r['dump_row']} has no matching mechanism row")
        rows.append({"key": k, "dump_row": int(r["dump_row"]), "rule": r["rule_id"],
                     "set": "added" if part[k]["added"] else "shared",
                     "historic_188": part[k]["historic"]})
    cells_sha = sha256(cells)
    if check_cells_pin and cells_sha != CELLS_SHA:
        raise ValueError(f"cell list sha {cells_sha} != pin {CELLS_SHA}")
    wanted = {r["key"][:3] for r in rows}
    hit, ncells, status = changed_cells(cells, wanted)
    if check_cells_pin and ncells != CELLS_ROWS:
        raise ValueError(f"cell list rows {ncells} != {CELLS_ROWS}")
    for r in rows:
        r["changed_cell"] = int(r["key"][:3] in hit)
        r["cell_status"] = hit.get(r["key"][:3], "")
    forced = [r for r in rows if r["rule"] in FORCED and r["changed_cell"]]
    by = Counter((r["rule"], r["set"]) for r in forced)
    measured = Counter(r["rule"] for r in rows)
    predicted317 = Counter(measured)
    for r in forced:
        predicted317[r["rule"]] -= 1
        predicted317["NO_RULE"] += 1
    pred = {k: predicted317.get(k, 0) for k in Y317}
    meas = {k: measured.get(k, 0) for k in Y315}
    counts = {"O05": sum(v for (k, _), v in by.items() if k == "O05"),
              "O04": sum(v for (k, _), v in by.items() if k == "O04")}
    match = (counts == {"O05": 30, "O04": 4} and meas == Y315 and pred == Y317)
    other_changed = Counter(r["rule"] for r in rows if r["changed_cell"] and r["rule"] not in FORCED)
    return {
        "inputs": {"assignment": {"path": str(assignment.relative_to(ROOT)) if assignment.is_relative_to(ROOT) else str(assignment), "sha256": sha256(assignment), "rows": len(asg)},
                   "mechanism_partition": {"path": str(mechanism.relative_to(ROOT)) if mechanism.is_relative_to(ROOT) else str(mechanism), "sha256": sha256(mechanism),
                                           "shared": sum(r["set"] == "shared" for r in rows),
                                           "added": sum(r["set"] == "added" for r in rows),
                                           "historic_188": sum(r["historic_188"] for r in rows)},
                   "changed_cells": {"path": "output/scratch-31/diff-3-14-au.cells.tsv", "sha256": cells_sha,
                                     "rows": ncells, "status_counts": dict(sorted(status.items()))}},
        "measured_315": meas, "yardstick_315": Y315,
        "predicted_317": pred, "yardstick_317": Y317,
        "forced_zero": {"total": len(forced), "by_rule": counts,
                        "by_rule_set": {f"{k}/{s}": v for (k, s), v in sorted(by.items())}},
        "non_forced_rules_on_changed_cells": dict(sorted(other_changed.items())),
        "match": match,
        "rows": rows, "forced_rows": forced,
    }


def write(res: dict, out: Path) -> None:
    fields = ["dump_row", *NATIVE, "rule_315", "set", "historic_188", "changed_cell", "cell_status", "rule_317_predicted"]
    with open(out.with_suffix(".tsv"), "w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(fields)
        for r in sorted(res["forced_rows"], key=lambda r: r["dump_row"]):
            w.writerow([r["dump_row"], *r["key"], r["rule"], r["set"], r["historic_188"],
                        r["changed_cell"], r["cell_status"], "NO_RULE"])
    summ = {k: v for k, v in res.items() if k not in ("rows", "forced_rows")}
    out.with_suffix(".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assignment", type=Path, default=ASSIGNMENT)
    ap.add_argument("--mechanism", type=Path, default=MECHANISM)
    ap.add_argument("--cells", type=Path, default=CELLS)
    ap.add_argument("--out", type=Path, default=HERE / "per_rule_phase1_f2_identity")
    a = ap.parse_args(argv)
    res = run(a.assignment, a.mechanism, a.cells)
    write(res, a.out)
    print(json.dumps({k: res[k] for k in ("forced_zero", "measured_315", "predicted_317", "match",
                                           "non_forced_rules_on_changed_cells")}, sort_keys=True))
    return 0 if res["match"] else 1


if __name__ == "__main__":
    sys.exit(main())
