---
unit: 1-01
phase: 1
---

# Brief: Per-row completeness evidence table

Consumer: Maps Execute, who lands on master. Design signed plan 14 with blank design_id (intentional — do not post to the workflow service).

## Outcome (from DESIGN.md Phase 1)

On the disc in force (`4ed9cd80…`, restored at `output/scratch-14/G_new/ALLDATA.KWI`), a committed evidence table lists every currently failing completeness identity exactly once. Each row has: full native key, classify assignment (O01/O04/O05/O06/`NO_RULE`/other), flags `in_historic_188` and `in_added_89` against the committed 3-17 identity list and 3-16 TSV, an R byte/decode witness, a G byte/decode witness, and a spool/K1 requirement witness (or an explicit `evidence gap` open question for that column). The table header states: failing total, attributed by rule, unattributed total, and the numeric drift vs 3-17 (776 failing, 308 unclassified) and 3-15 (274 unattributed). No cause is named. No rule file is edited. 3-16 / 3-17 / design-170 files are not rewritten.

## Owned paths

- `docs/plans/14-completeness-root-cause/` (evidence TSV + short note + this brief's report; triage under this folder)
- `docs/provenance.md` (scratch entry for new evidence / disc restore only)
- `docs/plans/14-completeness-root-cause/IMPLEMENTATION.md` (Phase 1 progress facts only if Execute has not already written encode facts)
- Rebuild artefacts under `output/scratch-14/` (git-ignored): dump, classify, witnesses

## Non-goals

- Do not name causes. Do not edit encoder rules, `rules_other.json`, `rules_bg.json`, or checker/encoder C.
- Do not rewrite 3-16 / 3-17 / 170 files. Do not reseat those units.
- Do not delete or overwrite `output/scratch-3-11/G_new/ALLDATA.KWI` (sha `013586b5…`). Do not delete spool or `.venv-rp`.
- Do not touch plan 15 paths. Do not claim plan 04 Phase 3 closed.
- Do not open a feature branch or pull request. Commit on master in this worktree.
- Do not push (Execute owns the push). Do not post to the workflow service.

## Pre-edit checks

1. Confirm disc sha256 of `output/scratch-14/G_new/ALLDATA.KWI` is `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` (already restored by Execute under flock; do not re-encode unless the file is missing).
2. Confirm R disc readable at `/run/media/codyh/464210-8480/ALLDATA.KWI`.
3. Confirm spool at `output/extract_timing/spool` and venv `.venv-rp`.
4. Quote Phase 1 outcome from `docs/plans/14-completeness-root-cause/DESIGN.md`.

## Steps

1. Under `flock output/.heavy.lock`, rebuild the live K1 completeness failure dump from the restored G disc (prefer completeness-only dump-kinds to avoid empty-kind classify aborts):
   ```
   flock output/.heavy.lock \
     .venv-rp/bin/python parser/tools/quantisation_roundtrip.py \
       --disc output/scratch-14/G_new/ALLDATA.KWI \
       --spool output/extract_timing/spool \
       --out output/scratch-14/k1_full.json \
       -j 6 --engine c \
       --dump-failures output/scratch-14/dump_raw \
       --dump-kinds completeness
   ```
   K1 workers ≤ `-j6`. If a fuller dump is required for witnesses, keep completeness primary.
2. Produce an extended dump suitable for `k1_triage.py classify` (needs `other_mechanism` for O01/O04/O05/O06). Side tables under `output/scratch-3-07` / `scratch-3-08` were cleaned; do **not** invent mechanism codes. Prefer, in order: (a) recover sides if still present elsewhere read-only; (b) recompute mechanism for completeness rows only with a committed/reproducible method and record it; (c) if neither is possible, extend with an explicit `evidence gap` for the classify-assignment column and still emit every failing native key. Never silently force-zero and pretend live O01/O04/O05 attribution.
3. Run read-only classify:
   ```
   .venv-rp/bin/python parser/tools/k1_triage.py classify \
     --dump output/scratch-14/dump_ext \
     --rules docs/plans/04-c-core-orchestration/triage/rules_other.json \
     --out output/scratch-14/classify_completeness
   ```
   (Adjust dump path to the extended dir you actually wrote.) Completeness-only is expected; record partition totals.
4. Build the committed evidence table under `docs/plans/14-completeness-root-cause/triage/` (TSV + short note). Native key = `(level, ix, iy, code, p0..p6, shape, vert)` per 3-17. Flags: `in_historic_188` from the preserved identities in `rebaseline_3-17_9064.md` (and/or any retained historic TSV); `in_added_89` from `completeness_3-16_outcomes.tsv` keys. R/G/spool witness columns: path or decode summary, or `evidence-gap`.
5. Header of the note must state failing / attributed-by-rule / unattributed totals and numeric drift vs 3-17 (776 / 308) and 3-15 (274).
6. Append a short `docs/provenance.md` scratch entry for `output/scratch-14/` (disc restore sha `4ed9cd80…`, dump/classify paths). Do not claim a new oracle — sha matched.
7. Write `docs/plans/14-completeness-root-cause/reports/1-01-evidence-table.md` (handoff: what was done, deviations, unfinished, known problems).
8. Commit on master with a plain summary title. Include evidence TSV, note, report, provenance entry. Do **not** add `Workflow-Phase:` (Execute closes the phase after verify).
9. Stop and report the commit SHA. Do not push.

## Done evidence

- Committed evidence TSV + note under plan-14 triage with every live failing completeness identity once.
- Header totals + drift vs 3-17 and 3-15 stated.
- No rule/encoder/checker edits; 3-16/3-17/170 untouched.
- Report path present in the same commit.
- Disc sha still `4ed9cd80…`; `scratch-3-11/G_new` untouched.
