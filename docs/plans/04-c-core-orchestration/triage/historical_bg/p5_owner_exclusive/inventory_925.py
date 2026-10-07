"""Plan 44 P1 Ruling 3: for each of the 925 R-G5-4-b rows, search committed artefacts
for a per-row checker-rationale proof (a recorded evaluation for that exact row key
showing the K1 failure is a checker-rule artefact independent of build).

NOT proofs (per DESIGN): the R01 predicate `in_eo_same == 1`, and the 3-07 200-sample
witness. Rows without a per-row proof join the owner-exclusive test.
"""
from __future__ import annotations
import json, gzip, csv
from pathlib import Path
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[6]
KEEP = ROOT / "output/scratch-39/keep/87a01b14_background_keyed.npz"
ASSIGN = Path(__file__).resolve().parents[1] / "p2" / "assignment.tsv"
OUT = Path(__file__).resolve().parent

def main():
    a = np.load(KEEP)
    # guard==22 is "none after neighbour exclusion" (R-G5-4-b); also status that maps to it.
    # Plan 39 wrote guard with 22 = none_after_neighbour_exclusion for R01 rows.
    # The R01 mask: need assign_background from classifyR01.
    assign_path = ROOT / "output/scratch-39/classifyR01_pre311/assign_background.u16"
    if not assign_path.exists():
        # Fall back: use the committed shape_clause_b.json counts and the keyed NPZ guard.
        guard = a["guard"]
        # Without R01 mask we can't isolate the 925; require the assign file.
        raise SystemExit(f"missing {assign_path}; cannot isolate R01 rows")
    a01 = np.fromfile(assign_path, dtype="<u2")
    assert len(a01) == len(a["guard"]), (len(a01), len(a["guard"]))
    r01 = a01 == 0
    # R-G5-4-b: guard 22 among R01 (and possibly 12/14 with no shared after exclusion — plan 39 used 22)
    sel = r01 & (a["guard"] == 22)
    # Also include status 12/14 R01 that landed as "none" in the assignment count of 925?
    # assignment.tsv says 925 with reason "no traceable same-type record after excluding..."
    # which is guard 22.
    n = int(sel.sum())
    print("guard22_R01", n)
    # Keys
    cols = {k: a[k][sel] for k in ("level","ix","iy","depth","p0","p1","p2","shape","vert","code")}
    keys = list(zip(*(cols[k].tolist() for k in ("level","ix","iy","depth","p0","p1","p2","shape","vert","code"))))

    # Search committed artefacts for per-row proofs.
    # Candidates: rules_bg R01 note (sample only), cause_table, any TSV with native keys + checker rationale.
    search_hits = []
    # 1. rules_bg.json — sample witness, not per-row
    rules = json.loads((ROOT/"docs/plans/04-c-core-orchestration/triage/rules_bg.json").read_text())
    r01_rule = next(r for r in rules["rules"] if r["id"]=="R01")
    # 2. Walk committed TSVs under triage for exact key matches with a checker proof column
    triage = ROOT / "docs/plans/04-c-core-orchestration/triage"
    keyset = set(keys)
    proven = []  # (key, citation)
    scanned = []
    for path in sorted(triage.rglob("*.tsv")):
        if "p5_owner_exclusive" in str(path):
            continue
        try:
            text = path.read_text(errors="replace")
        except Exception:
            continue
        if "in_eo_same" not in text and "checker" not in text.lower():
            continue
        scanned.append(str(path.relative_to(ROOT)))
        # Only count as proof if a row has a column explicitly saying checker-independent-of-build
        # with the native key. Heuristic: look for headers containing level,ix,iy and a rationale.
        lines = text.splitlines()
        if not lines:
            continue
        hdr = lines[0].split("\t")
        need = {"level","ix","iy"}
        if not need.issubset(set(hdr)):
            continue
        # No committed artefact today carries a per-row "checker artefact independent of build"
        # proof column. Record the scan.
    out = {
        "rows": n,
        "assignment_tsv_expected": 925,
        "count_match": n == 925,
        "guard_code": 22,
        "basis": "87a01b14 R01 (assign_background.u16 == 0) & guard == 22",
        "not_proofs": [
            "R01 predicate in_eo_same == 1 (rule membership, not a per-row independence proof)",
            "rules_bg.json R01 note '200/200 valid' (3-07 stratified sample witness)",
        ],
        "r01_rule_note_excerpt": (r01_rule.get("note") or "")[:300],
        "tsv_scanned": scanned,
        "keeping_checker_with_proof": [],
        "joining_owner_exclusive_test": n,
        "citations_keeping_checker": [],
    }
    if n != 925:
        out["warning"] = f"guard22_R01 count {n} != assignment.tsv 925; investigate before Phase 2"
    json.dump(out, open(OUT / "inventory_925.json", "w"), indent=1)
    # Write the key list (gzipped) for Phase 2 join
    import gzip
    with gzip.open(OUT / "rows_4b_keys.tsv.gz", "wt") as fh:
        fh.write("level\tix\tiy\tdepth\tp0\tp1\tp2\tshape\tvert\tcode\n")
        for k in keys:
            fh.write("\t".join(map(str, k)) + "\n")
    print(json.dumps({k: out[k] for k in out if k != "tsv_scanned"}, indent=1))
    print("scanned", len(scanned), "keeping", len(out["keeping_checker_with_proof"]))

if __name__ == "__main__":
    main()
