# Brief: 2-01 — per-row join, cause reconciliation and F3 resolution

Consumer: Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`.
Owned paths:
- `docs/plans/28-phase1-per-rule-classify-recovery/triage/` (new join script and generated outputs only; Phase 1 outputs stay byte-unchanged);
- `docs/plans/28-phase1-per-rule-classify-recovery/phase2_reconciliation.md` (new);
- `docs/plans/14-completeness-root-cause.md` (**append-only**: an F3 resolution under Review/Follow-ups; no existing sentence rewritten except the single F3 follow-up bullet's pointer);
- `docs/OVERVIEW.md` (the completeness blocker wording only; see Changes);
- scratch writes only under `output/scratch-28/`.

Touch nothing else.
Commits: leave changes in the working tree. Execute commits.
Report: write `docs/plans/28-phase1-per-rule-classify-recovery/reports/2-01-join-reconcile.md` (rubric `/home/codyh/workspace/workflow-plugin/tools/quality/checks/execution-report.json`).
Depends on: Phase 1 (closed at `c8e08f4`).
Runs alongside: nothing.
Budget: about 20 files to read, about 500 lines to add, 100 tool turns.

## Required reading, in order

1. `docs/plans/28-phase1-per-rule-classify-recovery/DESIGN.md`: Domain "join and cause reconciliation", Assumptions 5–6, Phase 2. **Binding.**
2. `docs/plans/28-phase1-per-rule-classify-recovery/IMPLEMENTATION.md`: Phase 1 record and its **Carried** list.
3. Phase 1 outputs: `triage/classify_assignment.tsv`, `triage/completeness_mechanism.tsv` (predicate inputs, including `penultimate_repair_probe` for O04 rows), `triage/phase1_controls.md` (head only).
4. `docs/plans/04-c-core-orchestration/triage/phase3_membership.tsv`, `completeness_evidence.tsv` (R witness columns), `demand_attribution_3-01.tsv`, the 2-01/2-02 member TSVs and `2-02_..._note.md`, `r_contribution_3-02.tsv`, `phase3_groups.md`.
5. `docs/plans/14-completeness-root-cause.md` (Review, Follow-ups) and `docs/design/k1-completeness.md` (3-03 checker disposition).
6. `docs/OVERVIEW.md`: the WP1 row (about L42), the blocker paragraph (about L55–66), and the "What remains unfinished?" row (about L79).

## Goal

Join every one of the 776 per-rule assignments to its proven plan-14 group with a per-row verdict. Discriminate each rule/cause conflict, without relabelling. Then record the F3 resolution.

## Contract

The DESIGN's join domain is settled:
- **Join key:** the full native key.
- **Each row carries:** rule id and cause; plan-14 group and disposition; proof references; R presence; and a verdict of `consistent`, `conflict-proven` or `conflict-open`, with the stated definitions.
- **O04 (spool) and O06 (build) rows:** each gets a bounded discriminator record: the repair counterfactual under the current contract (does the repaired ring yield a representable piece?), R presence, and the verdict.
- **Spool-caused rows:** named for plan 04's successor spool list, never absorbed into checker.
- **Row 335:** amended 2-02, with its TOL-only centre-hit trigger recorded.
- **Cross-tab predictions:** test them (every 2-01 row rule-assigned; `NO_RULE` ⊆ 2-02) and report a failure plainly.
- **The 2-01 source-data parity observation** stays carried.

Phase 1 Carried items 1–2 go into `phase2_reconciliation.md`.

## Changes

- `triage/join_reconcile.py` writes:
  - `triage/phase2_join.tsv` (776 rows);
  - `triage/phase2_crosstab.tsv` (rule × group × verdict counts);
  - `triage/phase2_discriminators.tsv` (one row per O04/O06 row).

  Use the saved Phase 1 predicate inputs first. They already hold the current-contract C probe of the penultimate-deleted ring, so a separate heavy probe is needed only if they cannot settle a row. If one is needed, give a windowed command for Execute; do not run it.
- **`phase2_reconciliation.md`:** counts, prediction tests, every conflict row with its discriminator, the spool successor list, the 335 note, and the carried 2-01 parity observation and Phase 1 carried items.
- **Plan 14 record:** append an "F3 resolution (plan 28)" paragraph citing `docs/plans/28-phase1-per-rule-classify-recovery/` artefacts by path. Close-out will later repoint these to `docs/plans/28-phase1-per-rule-classify-recovery.md`, so keep the citations to a single sentence that is easy to rewrite.
- **OVERVIEW:**
  - narrow "historic completeness attribution (open under plan **14**)" and the completeness part of "native classify joins" per Assumption 6, naming any `conflict-open` rows;
  - correct the stale plan-14 status mentions in the WP1 row and the "What remains unfinished?" row: plan 14 closed out at `3fb5a35` with record `docs/plans/14-completeness-root-cause.md`.

  Other kinds' joins stay open, and plan 04 Phase 3 stays open.

### Keep untouched

- Phase 1 outputs, `k1_triage.py`, `rules_*.json`, all encoder/checker/K1 sources, plan-04/14 TSVs.
- The protected discs and the spool.
- Do not run `build_evidence.py`, `verify_evidence.py` or any script you have not verified uses argparse.

## Heavy-run rule (binding)

You may run:
- your join script, which reads only committed TSVs and small JSON and opens no spool or disc;
- light self-checks.

Do not open the spool, a disc, or run K1 or an encode. Any needed probe goes to Execute as an exact `run_heavy_python.py` command.

## Done evidence

- `phase2_join.tsv` has 776 rows and 776 unique keys, with the key set equal to `phase3_membership.tsv`. Every row has a verdict.
- The cross-tab counts sum to 776. The prediction tests are stated pass/fail.
- Every O04/O06 row appears in `phase2_discriminators.tsv`.
- `git diff docs/plans/14-completeness-root-cause.md` shows additions only, apart from the one-line F3 pointer.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then:
- what changed;
- the check output;
- the run command (Execute re-runs it under the guard);
- deviations;
- contradictions with DESIGN.

Do not spawn agents beyond read-only research helpers.
