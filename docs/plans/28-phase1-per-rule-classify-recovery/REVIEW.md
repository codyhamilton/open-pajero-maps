# Independent comprehensive review — plan 28

## Verdict

**PASS_WITH_FOLLOWUPS** — post-fix state. No blocker/high findings and no
briefed findings remain. F2 is a non-blocking historical control limitation;
the current 776-row assignment and cause join are supported by the evidence.

Reviewed SHA: `cc965701d0ea0670ff3e550ecaf5fcdd1b070c31`.
Review date: 2026-10-06, Australia/Brisbane.
The mechanical fixes and this review are uncommitted for the orchestrator.

Independent reviewer: did not build either phase. Applied
`/home/codyh/workspace/workflow-plugin/skills/comprehensive-review/SKILL.md`.
Reviewed `git show` for `fe18160`, `ea9a107`, `2564de7`, `c8e08f4`,
`3314881`, `e21d29a`, and `cc96570`, and the scoped
`git diff 3fb5a35 cc96570`. Interleaved plan-29 commits and concurrent
plan-29/checker/assembly work are excluded. Historical input hashes were
checked against git blobs at `2564de7`, rather than concurrent working-tree
edits to the shared rules file.

## Phase outcome assessment

### Phase 1 — reproducible per-rule assignments

| Outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Explain non-recovery and correct regeneration claims | Met | `phase1_note.md` explains deleted scratch-only producers, fallback (c), the unscheduled recovery and both classifier schema gates. The provenance diff explicitly withdraws the old recipes. |
| 2. Tracked producer and 776 witnessed full-key side rows | Met | `triage/completeness_mechanism.py` and `.tsv`; 776 unique native keys, 799 demanders, all paths `light`, no multi-match. Independent checks recompute all-demander/first-match decisions from the recorded predicate inputs. Fourteen saved-proof rows were independently reproduced, including all seven O04 rows, O01, O05, NO_RULE, multi-demander rows, 335 and 765. |
| 3. Pinned source and original-byte-preserving extension | Met | Review producer runs verify the actual baseline pin `1a91b1c2…`. The execution record reports full 776-row byte verification. Synthetic fixtures independently cover every original byte, nonzero padding/NaN payloads, byte 144 zero, byte 145, native `vert`, and noncontiguous windows. F1 strengthens input preservation. |
| 4. Unchanged real classifier, literal projection and published assignments | Met | 776 assignment rows: O01 363, O05 132, O04 7, O06 0, NO_RULE 274. No evidence gap. Projection objects and hashes match the historical source byte slices. Packing the committed assignments as classifier indices reproduces `classify_run.json`'s assignment-array SHA256. The recorded classifier exit 1 is valid. Full classify was not replayed in this review. |
| 5. Historic/added and historical-count controls, with exact mismatching rows | Partial | Historic 188 all NO_RULE and added 89 = O04 3 + NO_RULE 86 pass independently; 3-15 totals match. 3-17 comparison correctly reports aggregate FAIL and candidate rows with inputs. Exact identity mismatches cannot be established from the deleted byte table; the 34-versus-31 explanation remains incomplete (F2). Optional legacy control is explicitly skipped. |
| 6. Guarded heavy execution with logs | Met on recorded execution evidence | `IMPLEMENTATION.md` and `docs/provenance.md` record guarded full runs, wrapper argv, logs and the 81 MB producer peak. Review runs were permitted light checks only; original wrapper logs/heavy runs were not independently replayed. |
| 7. No rule/checker/encoder/K1 changes or protected reseating | Met | The seven plan-28 commits change only the authorized surfaces. Classifier/rule objects are preserved; no K1 rerun/full encode or reseating of 170, 3-16 or 3-17 is introduced. Concurrent plan-29 edits are excluded. |

### Phase 2 — join and cause reconciliation

| Outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Exhaustive full-key join with cause, proofs, R and verdict | Met | `triage/phase2_join.tsv`: 776 unique keys equal final membership, 342 2-01 + 434 amended 2-02; 769 consistent, 7 conflict-proven, 0 conflict-open. Independent rerun is byte-identical. Polygon count and cell-local R presence remain separate, including row 765. |
| 2. Cross-tab and predictions | Met | `triage/phase2_crosstab.tsv` sums to 776; all 342 2-01 rows rule-assigned and all 274 NO_RULE rows in amended 2-02. Independently checked against assignment/member tables. |
| 3. Every spool/build conflict discriminated without relabel | Met | Seven O04 keys exactly cover `phase2_discriminators.tsv`; no O06 assignments. All seven current-contract repair probes reproduced byte-identically. Rows 138/284/496 emit one repaired record; 236/282/317/563 emit none and cease demand. All retain O04/spool and successor flags, with R absent. Missing/inconsistent probes independently produce `conflict-open`. |
| 4. Row 335's amended group and distinct trigger | Met | Full-key join retains O05/checker, amended 2-02 and branch-c `c_tol_only=True`; `phase2_reconciliation.md` states the F2 ruling and TOL-only sliver trigger. |
| 5. Plan-14 F3 resolution, preserving history | Met | Scoped diff adds the resolution and changes only the permitted F3 follow-up pointer. Original Phase 1 partial history remains. |
| 6. OVERVIEW narrows only completeness blockers | Met | Other kinds' joins stay open; seven spool successors and source-data parity remain carried; plan 04 Phase 3 explicitly stays open. Stale plan-14 status references are corrected. |
| 7. Source-data parity stays separate | Met | `phase2_reconciliation.md` retains the 2-01 observation and identifies its O01 340 + O05 2 rule rows. It records the precise 341 type-288 + one type-321 composition without rewriting historical group science. |
| 8. No Phase 3 close/later-phase release/reseating | Met | No such claim or action appears in the scoped commits or review fixes. No 3-90 rerun. |

## Findings by severity

### Medium

**F1 — resolved in review: hard-linked destinations overwrite protected inputs.**
Location: `parser/tools/dump_join.py:375` (`extend_other_mechanism`).
`resolve()` catches path/symlink aliases but not distinct names for the same
inode. A synthetic destination hard-linked to the source passed preflight,
overwrote the original bytes, then raised `VerifyError` at row 2; the source
was already corrupted. This violates the explicit read-only input contract.
Fixed mechanically with `samefile()` checks for both output files against
the source binary, manifest and side TSV before any writes. Three regression
cases verify rejection and byte preservation for hard-linked binary,
manifest and side-table inputs. All permitted tests pass. Closed; no brief.

**F2 — follow-up, non-blocking: historical 3-17 control cannot identify all mismatches.**
Locations: `triage/completeness_mechanism.py:424`,
`triage/phase1_controls.md`, and `phase2_reconciliation.md:117`.
The measured O05 −30 / O04 −4 delta is 34 rows; the recorded forced-zero
explanation names 31. The inherited per-row table is deleted, so candidate
bucket members are not proven identity differences. This pre-existing design
limitation is honestly carried; it does not invalidate fresh per-row predicates
or the plan-14 cause join. Preserve the partial historical-control assessment
at close-out. Any later explanation must distinguish inherited shared rows
from added keys using surviving provenance; if a pinned identity reference
is recovered, compare full native keys and record the exact mismatching rows
and inputs. Do not infer identities from aggregate counts, force codes, or
reseat 3-17. No structural brief is needed for the current assignment recovery.

### Low

**F3 — resolved in review: fixture depends on ignored saved scratch.**
Location: `parser/tests/test_dump_join_other_mechanism.py:34`.
Ten original adapter cases obtained their field schema from
`output/scratch-14/dump_raw/dump_manifest.json`, so an ordinary checkout
without historical scratch cannot run these otherwise synthetic fixtures.
Replaced that read with the explicit original 144-byte fixture contract.
Verified fixture creation and extension with saved-scratch reads deliberately
refused; existing byte-preservation and regression tests pass. Closed; no brief.

**F4 — resolved in review: report's guarded rerun command lacks an interpreter.**
Location: `reports/2-01-join-reconcile.md:61`.
The report passed the non-executable join script directly to the wrapper.
Added `.venv-rp/bin/python -B`, matching the already-correct command in
`phase2_reconciliation.md` and the recorded Execute correction.
Verified the script's interpreter invocation through the permitted light
join replay. No heavy wrapper rerun was necessary. Closed; no brief.

## Intent and assumption ledger assessment

The implementation matches recovery by fresh current-contract measurement,
unchanged rules/classifier and a full-key proof join. It does not claim DVD
parity or close plan 04 Phase 3. NO_RULE remains an honest assignment.

| Ledger entry | Assessment |
| --- | --- |
| 1. Deleted historical side tables | Holds on recorded Ground. Review did not repeat a host-wide search. The historical identity limitation is explicit (F2). |
| 2. Current build contract | Holds. Reproduction validates the `_cenc.c` SHA pin; its per-class units split at 4095, supporting the O06 negative contract proof. No claim of a new disc measurement is made. |
| 3. No catch-all/new rule | Holds. Literal O01/O04/O05/O06 projection; 274 NO_RULE rows retained. |
| 4. 3-01 demander set | Implemented as chosen: 799 checked demanders across 776 keys, predicates require all demanders. Non-demanding meeting sources are not newly enumerated; equivalence relies on the signed design assumption. |
| 5. Preserve closed plan-14 history | Holds, with the specifically authorized F3 pointer exception from brief 2-01; additions supply the new evidence. |
| 6. Narrow completeness blockers only | Holds. Other joins, parity/spool successors and plan 04 Phase 3 remain open. |

## Plan-sufficiency judgment

**Sufficient to determine intent, place findings and derive QA**, with one
overstated historical control obligation. The domains, native key, rule order,
NO_RULE behavior, cause-conflict counterfactual and protected boundaries are
precise. The design's 31-row explanation and exact-identity mismatch obligation
cannot be fully proved from the surviving historical artifacts (F2).
This warrants a retained limitation, not invented evidence or a measurement
change. The optional legacy control was correctly treated as optional.

## Verification and residual risks

- Permitted pytest files: **27 passed before fixes; 30 passed after fixes**.
  The existing memory replay helper was relocated at runtime using a scratch
  pytest plugin; no helper/source changes outside the authorized surfaces.
- Independent committed-file audit: native-key/dump-row equality, 799 demander
  coverage, all-demander predicates/first-match/multi-match, source-input pins,
  literal projection objects/hashes, packed assignment-array hash and historic/
  added controls pass. `output/scratch-28/review/audit_committed.json`.
- Producer reproduction: 12 rows in `review/mechanism/` plus O01 and
  multi-demander rows 2/3 in `review/mechanism-extra/`; all 14 complete TSV rows
  equal the committed witnesses. All seven O04 original and repair probes
  are included, as are 335, 765 and the two 2-01 O05 rows 246/567.
- Join replay: `review/join/phase2_{join,crosstab,discriminators}.tsv` are
  byte-identical to committed outputs. Four altered counterfactual controls
  (absent probe, wrong demand, nonzero original count, remaining crossing)
  each stay `conflict-open`.
- Review outputs are only under `output/scratch-28/review/`.
  Scoped `git diff --check` passes. No spool/disc opened, K1/encode run,
  `build_evidence.py`/`verify_evidence.py` invoked, or heavy job launched.
  No required check needs a forbidden run; no new orchestrator heavy command
  is pending for these mechanical fixes.

Residual risks: F2's historical control remains partial; saved proof bytes
are required for regeneration; the optional legacy control is unrun; the
plan-14 group science and disc/re-encode provenance are prior evidence rather
than independently re-derived in this review. The seven spool successor items
and separate 2-01 source-data parity observation remain downstream work.
