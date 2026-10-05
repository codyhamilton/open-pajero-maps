# Phase-1 per-rule classify recovery (plan 28)

Plan 28 recovered the plan-14 Phase 1 per-rule classify assignments that plan 14 never produced (its review F3). All 776 baseline completeness rows now have a reproducible current-contract assignment, and every assignment joins its proven plan-14 cause. Commits: DESIGN `fe18160`, Phase 1 `c8e08f4`, Phase 2 `cc96570`, terminal review `904f416`.

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Recover plan-14 Phase 1 per-rule classify assignments so every one of the 776 rows has a recorded per-rule assignment that joins to its proven 2-01/2-02 cause. Find why they were never recovered (classify exit 2 / other_mechanism missing were noted earlier) and design the recovery. Heavy runs are allowed only under `flock output/.heavy.lock` plus the plan-25 `run_heavy_python.py` memory wrapper with bounded/streamed triage loads; prefer a light path if one exists. Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4-6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Never relabel.

## Why This Existed

Plan 14 closed with all 776 rows marked `evidence-gap:other_mechanism`. Unchanged `rules_other.json` classify exited 2 on the missing byte-145 `other_mechanism` column. Its producer and side tables had lived only in plan 04's scratch (3-07/3-08) and were gone. The baseline manifest also declared only `completeness`, so other-kind rules O02/O03 would fail next. Recovery had been rejected as a plan-14 gate and never scheduled.

## What Was Built

- **Producer** `docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.py`. It recomputes each row's mechanism code from the documented 3-07/3-08 predicates, using committed plan-14 TSVs and saved `scratch-14` proofs. All 776 rows took the light path, with no evidence gap.
  - Codes: 4:363, 5:132, 7:7, 0:274.
  - Side table `per_rule_completeness_mechanism.tsv`.
  - This is a fresh measurement, not a restoration of 3-08 bytes.
- **Byte-145 join** `parser/tools/dump_join.py --mode other_mechanism`. It is read-only on its inputs and refuses path, symlink and hard-link aliases. Tests: `parser/tests/test_dump_join_other_mechanism.py`.
- **Completeness projection** of `rules_other.json` (O01/O04/O05/O06, raw objects byte-preserved): `per_rule_rules_completeness_projection.json` + `per_rule_projection_hashes.json`.
- **Classify** on the extended dump: `PARTITION FAIL` exit 1, a valid NO_RULE partition. O01 363 / O05 132 / O04 7 / O06 0 / NO_RULE 274. Output `per_rule_classify_assignment.tsv`, run `per_rule_classify_run.json`, controls `per_rule_phase1_controls.md`, note `per_rule_phase1_note.md`.
- **Join** `per_rule_join_reconcile.py`: 776 rows join the 342 (2-01) + 434 (amended 2-02) proven causes as **769 consistent, 7 conflict-proven, 0 conflict-open** (`per_rule_phase2_join.tsv`, `_crosstab.tsv`, `_discriminators.tsv`, `per_rule_phase2_reconciliation.md`).
  - The 7 conflict-proven rows are the O04 spool rows 138, 236, 282, 284, 317, 496, 563. R presence is false for all of them. After penultimate repair, 138/284/496 give a representable piece and the other four do not. They are listed for plan 04's successor spool list.
- **F3 resolved** in `docs/plans/14-completeness-root-cause.md`. The OVERVIEW was narrowed, and its stale "plan 14 open" text was corrected.
- **Lasting contract** promoted to `docs/design/k1-completeness.md` § Per-rule assignment of completeness rows.

### Phase 1 — Every baseline row has a reproducible per-rule classify assignment

Met. Input checks:
- `scratch-14/dump_raw` sha `1a91b1c2…`, re-hashed before and after.
- The `dump_ext` bin is byte-identical to it. Its manifest `28fa57f1…` has no committed pin.
- `classify_invocation.json` (`09b64658…`, exit 2 as recorded) was not used as input.

Controls:
- 188/188 historic rows are NO_RULE: PASS.
- 89 added rows split O04 3 / NO_RULE 86: PASS.
- 3-15 totals: exact PASS.
- 3-17 aggregate: FAIL, as expected and reported (see Deviations).
- O06 is excluded by a contract proof against `_cenc.c` (`5c43e00d…`).

### Phase 2 — Every assignment joins to its proven plan-14 cause, with conflicts discriminated

Met. Both predictions PASS. Every conflict is discriminated by byte-level evidence, and none is open.

## Deviations

- **3-17 arithmetic:** DESIGN's control explanation is internally inconsistent. The measured O05 −30 / O04 −4 delta is 34 rows; the forced-zero explanation names 31. The legacy per-row 3-17 control was skipped because its identity table is deleted. The aggregate FAIL is recorded, not forced.
- Heavy commands in briefs and reports first lacked the interpreter in the `run_heavy_python.py` argv; they were fixed before running (review F4).
- The terminal reviewer edited a worker report (F4 argv fix) as well as making code fixes in review.
- Codex reached its usage limit (about 05:11 AEST, reset 06:18 AEST), so close-out was done directly by the orchestrator.
- At close-out, the evidence moved with a `per_rule_` prefix into plan 04's triage folder and was regenerated under the guards (see Verification). The chain ran twice by mistake; it is deterministic, and the second run is the one recorded.

## Review

Independent terminal review (Codex), **PASS_WITH_FOLLOWUPS**, reviewed `cc96570`, landed `904f416`.
- **F1 (medium), resolved:** hard-linked destinations could overwrite protected inputs in `extend_other_mechanism`. Fixed with `samefile()` checks, plus three regression cases.
- **F2 (medium), follow-up:** the historical 3-17 control cannot identify all mismatches (34 vs 31).
- **F3 (low), resolved:** the fixture depended on ignored saved scratch; it now uses an explicit 144-byte fixture contract.
- **F4 (low), resolved:** a report's guarded rerun command lacked an interpreter.

## Verification

- Phase 1 (`c8e08f4`), guarded: exits 0, 0, 0, 1, 0. Produce took 57 s with an 81 MB peak. `dump_raw` (`1a91b1c2…`) was re-hashed unchanged.
- Phase 2 (`cc96570`): join exit 0, both predictions PASS, membership key set equal, crosstab sum 776.
- Close-out regeneration at the new paths (`output/scratch-28/run_closeout.{sh,log}`, 2026-10-06 ~05:32 AEST, guarded): produce, projection, dump_join, classify (exit 1, valid NO_RULE), publish, join, and the dump_join tests. Every output is byte-identical to the `904f416` blobs or equal modulo the renamed paths.
  - One real difference: `per_rule_projection_hashes.json` / `per_rule_mechanism_run.json` record `rules_other.json` sha `c9154451…`, not `a67da962…`. Plan 29's O03 note changed (`ecfae1c`); the projected O01/O04/O05/O06 objects are byte-identical.
  - The chain ran twice in sequence under the lock, from a relaunch slip. Both runs gave the same result.
- Tests: `test_dump_join_other_mechanism.py` + `test_dump_join_memory.py` gave 27 passed (Phase 1) and 30 passed (review and close-out).

## Residual Risks

- Proof inputs (`output/scratch-14/`, `output/scratch-28/`) are ignored scratch, not git objects. Reproduction needs the retained `dump_raw` (`1a91b1c2…`).
- The mechanism codes are recomputed from documented predicates, so they can only match the deleted 3-08 bytes as far as those predicates were documented.

## Follow-ups

- **3-17 per-row identity control** (review F2) and the 34-vs-31 explanation. Owner: Design; there is no plan yet. Carried in `docs/plans/04-c-core-orchestration/triage/per_rule_phase1_controls.md` and here.
- **Seven O04 spool rows** for plan 04's successor spool list (`docs/plans/04-c-core-orchestration/triage/per_rule_phase2_reconciliation.md`). *(2026-10-06, appended: plan 33 closes all seven as proven-non-deviation on per-row G/R byte/decode witnesses; no spool edit.)*
- **2-01 source-data parity** stays a carried observation for Design (plan 14 record).
- Plan 04 Phase 3 is not closed by this plan.

## Decisions Worth Keeping

- Recompute, not recover: the side tables and producer were physically gone, so tracked code over documented predicates is the only reproducible path.
- NO_RULE is a valid recorded assignment; its cause is the joined plan-14 proof. No new rule was registered.
- Predictions are yardsticks. A mismatch is reported per row with its discriminator, never forced.
