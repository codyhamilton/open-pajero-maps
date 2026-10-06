---
design_id:
---

# Plan 28 F2 (3-17 34-vs-31 arithmetic) and test_perf_inventory

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Small design for plan 28 F2 (3-17 34-vs-31 arithmetic) and `test_perf_inventory`. Void any item already resolved on master, with evidence. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`. Master direct. Do not reseat 170, 3-16 or 3-17. Do not draw plan 04 Phases 4–6 or plan 06. Do not claim Phase 3 closed. No 3-90 re-run.

## Problem

**F2.** Plan 28's Phase 1 control (`triage/per_rule_phase1_controls.md`) measured 3-15 → 3-17 as O05 −30, O04 −4, NO_RULE +34. The sum is self-consistent: 308 − 274 = 34, and 132 − 102 + 7 − 3 = 34. The explanation it inherited names only "30 O05 and 1 O04 on `AU.differing_cells.tsv` cells were zeroed" (`completeness_3-15_cell_local.md` L34; also draft 28's Ground row). That is 31, leaving 3 rows unexplained.

The deleted 3-17 identity table (`output/scratch-3-17` is gone from every host worktree) means no per-row reference survives. Plan 28 record L59/L79 carries F2 as a medium follow-up owned by Design.

Candidate mechanism, to be proved rather than assumed: 3-15 O04 7 = shared 4 + added 3. The 89 added keys are EO-stitch side-effects on 3-14-changed cells (`completeness_3-15_cell_local.md` L20–26). The 3-14 extension zeroes `other_mechanism` on changed cells. So the 3 added O04 rows would also be forced to zero, giving 30 + 1 + 3 = 34.

**test_perf_inventory.** It fails on `d2459b6` (box pytest run 2026-10-06: 1 failed / 3 passed). `test_inventory_covers_every_module` lists 6 modules missing from `parser/perf_inventory.json`, each added on 2026-10-06 without an entry:

| Module | Added in |
| --- | --- |
| `parser/harness/checks/copy_through.py` | `e9afab8` plan 23 |
| `parser/harness/checks/wp_na.py` | `10aeb6e` harness WP2–WP5 NA |
| `parser/kiwiw/state_partitions.py` | `f4dc873` plan 26 |
| `parser/tools/k1_representable.py` | `a890662` plan 14 3-03 |
| `parser/tools/run_heavy_python.py` | `df1f071` plan 25 |
| `parser/tools/whole_file_guard.py` | `df1f071` plan 25 |

Plan 29 R4 carried this to "plan 04's performance-inventory owner". It blocks design 35's full-pytest gate.

Neither item is resolved on master: F2 is still listed in plan 28's follow-ups, and the test fails at tip.

## Solution shape

### Domain: F2 per-row identity

- **Owns:** `triage/per_rule_phase1_f2_identity.tsv` and `.md`, plus a small join script.
- **Contract:**
  1. Inputs (all pinned by sha):
     - plan 28 `per_rule_classify_assignment.tsv` (776 rows, native key plus rule);
     - the 3-15 shared-687 / added-89 key partition as committed for plan 28's controls;
     - the 3-14 AU changed-cell list `diff-3-14-au.cells.tsv` (sha `77ff1d86…`, 246,123 cells; plan 31).
  2. Predicted forced-zero set = rows whose rule is O04/O05 and whose cell is in the changed-cell list. Report it split shared/added × rule.
  3. **Match:** the set has exactly 34 rows (O05 30, O04 4) and the bucket deltas reproduce 3-15 → 3-17. The 31 statement is then recorded as an arithmetic error with the per-row identity, in a new erratum note. The 3-15 text and the generated controls file are not rewritten.
  4. **No match:** the exact surplus or missing rows are named as residual. No count is forced.
  5. Light work only: committed TSVs plus one bounded read of the cell list. No dump, classify or K1 run. 3-17 is not re-run or reseated.
- **Non-goals:** recomputing 3-15 science; restoring 3-17 bytes; changing rules.

### Domain: perf inventory coverage

- **Owns:** six new entries in `parser/perf_inventory.json`.
- **Contract:**
  1. Each module is classified under the inventory's own definition (perf-sensitive = a loop whose trip count scales with full-AU vertices / shapes / parcels / frames / cells). Each entry's reason comes from reading the module.
  2. `orchestration` or `c-later` (no phase) only. If a module meets the perf-sensitive definition and would need `c-now` with a phase, it is classified `c-later` and named in the record as a plan 04 Phase 4/5 input, without drawing those phases.
  3. `test_perf_inventory.py` passes 4/4. The full `parser/tests` summary shows no new failures.
- **Non-goals:** porting any module to C; changing the test.

## Decisions

1. Plan number 37. Master direct. Two independent phases; either may land first. Phase 2 should land before design 35 Phase 1's pytest step.
2. Both approaches known. Refine skipped.
3. No disc, encoder or checker surface is touched.

## Assumption ledger

### Assumption 1

- **Question:** Is the 3-15 shared/added key partition recoverable from committed files?
- **Answer chosen:** Yes. Plan 28's Phase 1 controls selected 188/188 historic and 89/89 added keys from committed artefacts.
- **Rationale:** `per_rule_phase1_controls.md` "Added control: 89/89 selected".
- **If wrong:** the partition is re-derived from the 776-row assignment plus the plan 28 historic/added control inputs. If that fails, F2 stays residual and the missing input is named.

### Assumption 2

- **Question:** Does "do not reseat 3-17" forbid an erratum?
- **Answer chosen:** No. The erratum is a new plan 28-scoped note that cites 3-15/3-17. Neither unit's record or outcome is edited.
- **Rationale:** The follow-up is owned by Design per the plan 28 record.
- **If wrong:** the identity table lands and the erratum text waits for Cody.

## Open questions

None blocking.

## Phases

### Phase 1: F2 34-row identity proven or residual named

- **Outcome:**
  1. `per_rule_phase1_f2_identity.tsv` lists every row in the predicted forced-zero set, with key, rule, shared/added and changed-cell membership.
  2. Counts: O05 30 / O04 4 = 34 (match), or the exact mismatch rows.
  3. Plan 28 F2 is marked discharged with a pointer, or carried with the named residual.
- **Surfaces:** `docs/plans/04-c-core-orchestration/triage/per_rule_phase1_f2_identity.{tsv,md}` and a join script; `docs/plans/28-phase1-per-rule-classify-recovery.md` (follow-up pointer only); `parser/perf_inventory.json` if the script lives under `parser/`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: test_perf_inventory passes

- **Outcome:**
  1. Six modules classified with reasons.
  2. `test_perf_inventory.py` 4 passed.
  3. Full `parser/tests` summary quoted, with no new failures.
  4. Plan 29 R4 discharged by pointer.
- **Surfaces:** `parser/perf_inventory.json`; `docs/plans/29-k1-name-anchor-failure.md` and `docs/design/out-of-span-name-guard.md` (follow-up pointer only).
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

## Provenance

- Master `d2459b6`. Sources:
  - `per_rule_phase1_controls.md` L9–25;
  - `completeness_3-15_cell_local.md` L10, L20–37;
  - `rebaseline_3-17_9064.md` L98–119;
  - plan 28 record L49, L59, L79;
  - plan 29 R4;
  - box pytest run of `parser/tests/test_perf_inventory.py` (temporary venv, 1 failed / 3 passed);
  - `git log --diff-filter=A` for the six modules;
  - host read-only check: no `output/scratch-3-17` and no `scratch-3-14/dump_ext` survive.
- Rejected:
  - asserting 31 + 3 without per-row proof;
  - editing the 3-15 or 3-17 records;
  - classifying modules without reading them.
- Box draft only.
