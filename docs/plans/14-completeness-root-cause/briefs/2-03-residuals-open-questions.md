---
unit: 2-03
phase: 2
---

# Brief: 2-03 — Residuals and open questions ledger

Consumer: Maps Execute (lands on master). Assigned instance: OpenCode DeepSeek Flash.

## Outcome (Phase 2 slice)

Every Phase 1 row not closed in groups 2-01 or 2-02 is listed under **open questions** with discriminators tried and why none proved a single mechanism. Together with 2-01 and 2-02 membership, the 776 rows are exhaustive and disjoint. No fake group that only restates 3-15/3-16 labels. No rule registration. No encoder/checker edit.

## Owned paths

- `docs/plans/14-completeness-root-cause/triage/phase2_open_questions.md` (+ optional TSV)
- `docs/plans/14-completeness-root-cause/triage/phase2_membership.md` (or TSV) — authoritative union map: dump_row → `g-omits-cell-local-dvd-type` | `r-absent-complete-repair-zero` | `open-question:<id>`
- `docs/plans/14-completeness-root-cause/reports/2-03-residuals-open-questions.md`

## Non-goals

Same as 2-01/2-02: no C/rules edits; no Phase 3; no push; no PR; no reseat 170/3-16/3-17; no plan 04 Phase 3 close.

## Pre-edit checks

1. Units 2-01 and 2-02 have committed membership artefacts on HEAD (or this unit lands in the same push train after them).
2. Phase 1 TSV still 776 unique keys.
3. Quote Phase 2 outcome from `DESIGN.md`.

## Steps

1. Load 2-01 members, 2-02 members, and Phase 1 keys. Compute residual = 776 − members(2-01) − members(2-02). Must be ≥ 0; intersection of 2-01 and 2-02 must be empty.
2. For each residual row, record open-question id and discriminators tried, including at least:
   - **Q-source-335**: dump_row 335 — which source/requirement branch establishes K1 demand? (centre branch not enumerated in Phase 1.)
   - **Q-tile-alias**: 2-01 seeds that failed cell-local R (if any).
   - **Q-repair-emits**: 2-02 seeds where complete-repair emitted a representable piece (if any).
   - Any further failed discriminators (code 291/578/290/321 splits, branch `a` vs `b`, etc.).
3. Write `phase2_membership` mapping all 776 rows. Write `phase2_open_questions.md`. Write the report.
4. Verify: `|2-01| + |2-02| + |open questions| == 776` and pairwise disjoint.
5. Commit; no `Workflow-Phase:` trailer; do not push.

## Done evidence

- Exhaustive disjoint membership map committed.
- Every residual has tried discriminators + why unproven.
- No rule/encoder/checker edits.
