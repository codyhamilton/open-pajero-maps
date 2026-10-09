#!/usr/bin/env python3
"""Plan 68 Phase 2: score the candidate dedup rules (defined in the draft before scoring) on the
committed sample's R correspondence (r_correspondence.tsv.gz), derivation and holdout separately.

Candidates and what each predicts R holds where G has k byte-identical copies:
  keep-first / keep-last / keep-own-cell-first: one copy, at the first / last / own-cell emitter's position
      -> correct only on R-one-byte / R-one-geom with that position label;
  merge-sources: one record from the union of the sources' pieces -> correct only on R-merged;
  drop-all: nothing -> correct only on R-absent.
Scoring sets: "design" = R-one-byte + R-one-geom (the draft's acceptance set: 100 % on derivation AND
holdout, non-empty); "comparable" = every class that is not R-noncomparable / error (R-other counts as a
miss for every rule: R holds same-type geometry there that no candidate predicts). National framing-equal
counts are reported alongside. A rule is accepted only with a non-empty 100 % / 100 % on the design set
and a code path; otherwise "no rule accepted" and the plan stops for Design (Phase 2 outcome)."""
from __future__ import annotations

import argparse, gzip, hashlib, json
from collections import Counter
from pathlib import Path

RULES = ("keep-first", "keep-last", "keep-own-cell-first", "merge-sources", "drop-all")


def correct(rule, r):
    c = r["class"]; pos = (r.get("position") or {}).get("label")
    if rule in ("keep-first", "keep-last", "keep-own-cell-first"):
        if c not in ("R-one-byte", "R-one-geom"):
            return False
        if rule == "keep-first":
            return pos == "first"
        if rule == "keep-last":
            return pos == "last"
        kinds = r.get("emitter_kinds_ordered") or []
        want = "first" if not kinds or kinds[0] == "own" else ("last" if kinds[-1] == "own" else None)
        return pos == want
    if rule == "merge-sources":
        return c == "R-merged"
    return c == "R-absent"


def load(p):
    with gzip.open(p, "rt") as f:
        next(f)
        return [json.loads(l) for l in f]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-corr", type=Path, required=True)
    ap.add_argument("--national-corr", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    rows = load(a.sample_corr)
    res = {}
    for rule in RULES:
        d = {}
        for setname, keep in (("design", lambda r: r["class"] in ("R-one-byte", "R-one-geom")),
                              ("comparable", lambda r: r["class"] not in ("R-noncomparable", "error"))):
            for split in ("derivation", "holdout"):
                rs = [r for r in rows if r["split"] == split and keep(r)]
                d[f"{setname}/{split}"] = [sum(correct(rule, r) for r in rs), len(rs)]
        full = all(d[f"design/{s}"][1] > 0 and d[f"design/{s}"][0] == d[f"design/{s}"][1] for s in ("derivation", "holdout"))
        res[rule] = {"scores": d, "pass_100_design": full, "accepted": False,
                     "why_not": "design set empty (0 R-one-byte / R-one-geom classes)" if not any(d[f"design/{s}"][1] for s in ("derivation", "holdout")) else ("below 100 %" if not full else None)}
    nat = load(a.national_corr)
    out = {"rules": res, "accepted": None, "outcome": "no rule accepted (stop for Design)",
           "sample_classes": dict(sorted(Counter(f"{r['split']}/{r['class']}" for r in rows).items())),
           "national_framing_equal_classes": dict(sorted(Counter(r["class"] for r in nat).items())),
           "inputs": {"sample_corr_sha256": hashlib.sha256(a.sample_corr.read_bytes()).hexdigest(),
                      "national_corr_sha256": hashlib.sha256(a.national_corr.read_bytes()).hexdigest()}}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["scores"] for k, v in res.items()}, indent=1))


if __name__ == "__main__":
    main()
