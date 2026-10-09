#!/usr/bin/env python3
"""Plan 68 Phase 1: committed stratified sample of duplicate classes (written before any R read).

Input: census_au.tsv.gz (census.py on live 0c22b266). Strata use G-side facts only:
(level, type code, copies 2 | 3+, depth 1 | 2+ (divided), emitter form cover | ring | mixed). Framing equality vs R needs R's leaf
index (an R read), so it is a measured column of r_correspondence, not a stratum (Refine 4).
Per stratum the K classes with the lowest sha256("p68-sample:{level},{ix},{iy},{path},{sha}")
(K = 60; K = 240 for L0 type 288, which holds 99.8 % of classes); a stratum with fewer is taken
whole. Split: holdout iff sha256("p68-holdout:{level},{ix},{iy},{path},{sha}")[0] is odd.
Writes sample.json (definitions, strata counts, sample rows with emitters)."""
from __future__ import annotations

import argparse, csv, gzip, hashlib, json, sys
from collections import defaultdict
from pathlib import Path

K_DEFAULT, K_288 = 60, 240

CLASS_DEFS = {
    "R-one-byte": "an R leaf of the cell with the same leaf path and the same frame bounds as G's leaf holds exactly one record byte-equal to the duplicate record (same type, class>0)",
    "R-one-geom": "not R-one-byte; exactly one R same-type class>0 record in the cell whose decoded parent-raw vertex ring equals the piece's (same vertex count, cyclic start / either direction, every vertex within 1 parent-raw unit); flag framing_equal records whether R's leaf framing equals G's",
    "R-merged": "not the above; an R same-type class>0 record contains the piece (no piece sample point farther than 1 parent-raw unit outside it) and also covers more than 1 raw unit^2 of a different (non-duplicate) piece that one of the copies' emitters emits in the same G leaf",
    "R-absent": "no R same-type class>0 record within 1 parent-raw unit of the piece, and not R-noncomparable",
    "R-noncomparable": "(a) alias: an R leaf of the cell is an alias frame (its frame address is shared by more than one leaf slot); or (b) type-set: R holds no class>0 record of the piece's type anywhere in the cell while an R class>0 record of another type covers part of the piece (> 1 raw unit^2): the F6 type-mapping question. Counted and named, never a pass",
    "R-other": "none of the above (an R same-type record within 1 unit that is not equal, not merging): named per case, never a pass",
}
POSITION_DEF = ("R-one-byte / R-one-geom: align G's and R's class>0 record sequences of the leaf on unique "
                "byte-equal (same framing) or geometry-equal (same type) non-duplicate records; the R copy's "
                "anchor interval (previous / next matched record, mapped to G positions) is compared with each "
                "G copy's; exactly one G copy inside it -> first | last | middle (by plan-63 emitter order); "
                "none or several -> neither")


def key(r, tag):
    return hashlib.sha256(f"{tag}:{r['level']},{r['ix']},{r['iy']},{r['path']},{r['record_sha256']}".encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    strata = defaultdict(list)
    with gzip.open(a.census, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            depth = len(r["path"].split(","))
            kinds = {e[3] for e in json.loads(r["emitters"])}
            form = "cover" if kinds == {"cover"} else ("ring" if "cover" not in kinds else "mixed")
            st = f"L{r['level']}/{r['code']}/c{'2' if int(r['copies']) == 2 else '3+'}/d{'1' if depth == 1 else '2+'}/{form}"
            strata[st].append(r)
    rows = []; counts = {}
    for st, rs in sorted(strata.items()):
        k = K_288 if st.startswith("L0/288/") else K_DEFAULT
        pick = sorted(rs, key=lambda r: key(r, "p68-sample"))[:k]
        counts[st] = {"population": len(rs), "sampled": len(pick)}
        for r in pick:
            split = "holdout" if int(key(r, "p68-holdout")[:2], 16) & 1 else "derivation"
            rows.append({"stratum": st, "split": split, "level": int(r["level"]), "ix": int(r["ix"]),
                         "iy": int(r["iy"]), "path": [int(x) for x in r["path"].split(",")],
                         "code": int(r["code"]), "copies": int(r["copies"]), "record_sha256": r["record_sha256"],
                         "emitters": json.loads(r["emitters"])})
    rows.sort(key=lambda r: (r["level"], r["iy"], r["ix"], r["path"], r["record_sha256"]))
    out = {"census_sha256": hashlib.sha256(a.census.read_bytes()).hexdigest(),
           "strata_rule": "(level, code, copies 2|3+, depth 1|2+, emitter form cover|ring|mixed (sidecar kind)); K=60, K=240 for L0/288; lowest sha256('p68-sample:{level},{ix},{iy},{path},{sha}')",
           "split_rule": "holdout iff sha256('p68-holdout:{level},{ix},{iy},{path},{sha}')[0] odd",
           "classes": CLASS_DEFS, "position": POSITION_DEF, "tolerance_raw": 1.0,
           "strata": counts, "n": len(rows),
           "n_split": {s: sum(r["split"] == s for r in rows) for s in ("derivation", "holdout")},
           "rows": rows}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"n": out["n"], "n_split": out["n_split"], "strata": len(counts)}))


if __name__ == "__main__":
    main()
