# Report — 2-01 join and cause reconciliation

Status: **done with concerns**. All assigned Phase 2 work is complete and
uncommitted; concerns are the carried evidence/wording discrepancies below
and unrelated edits appearing in the shared working tree.

## What changed

- Added stdlib-only, argparse-based `triage/join_reconcile.py` and its three
  generated outputs: `phase2_join.tsv`, `phase2_crosstab.tsv`,
  `phase2_discriminators.tsv`. Full native keys join all 776 assignments to
  final plan-14 groups, with original causes, checker dispositions, proof
  references, 799 demander verdicts and both R polygon and cell-local presence.
- Added `phase2_reconciliation.md`: counts, prediction tests, all seven cause
  conflicts and counterfactuals, the spool successor list, 335's TOL-only
  centre-hit trigger, the separate 2-01 parity observation, and Phase 1
  Carried items 1–2 (also the skipped legacy control).
- Appended the F3 resolution to plan 14's Follow-ups, with all plan-28
  citations in one sentence, and changed only the allowed F3 pointer line.
- Narrowed OVERVIEW's completeness blockers and corrected both stale
  plan-14 status mentions to close-out `3fb5a35` and its record path.
  Other kinds' joins and plan 04 Phase 3 remain open.

## Check output

Join exited **0**:

```text
rows=776 unique_keys=776 membership_key_set_equal=true crosstab_sum=776
consistent=769 conflict-proven=7 conflict-open=0
every_2_01_row_rule_assigned=PASS NO_RULE_subset_2_02=PASS
O04 discriminator rows=7 O06 discriminator rows=0
```

Cross-tab: O01/2-01/consistent **340**; O01/2-02/consistent **23**;
O05/2-01/consistent **2**; O05/2-02/consistent **130**;
O04/2-02/conflict-proven **7**; NO_RULE/2-02/consistent **274**.

All O04 rows retain `spool`: **138, 284, 496** emit one representable piece
after penultimate deletion; **236, 282, 317, 563** emit none and cease to
demand the type. Every original ring and its original EO faces emit zero;
all seven have R count zero. No additional probe is needed.

Independent light self-checks passed: all original assignments/causes
preserved; exact cross-tab recomputation; 799 demander records; discriminator
key coverage; repaired-piece/no-piece split; both predictions; two negative
controls (absent probe and inconsistent demand/count give `conflict-open`).
The three outputs match a scratch re-run byte-for-byte. Twenty protected
tracked Phase 1/old-triage TSV/classifier artefacts match HEAD byte-for-byte.
Plan-14 diff deletes only the authorised one-line F3 pointer; all other changes
are additions. `git diff --check` passes. Self-check results:
`output/scratch-28/p2_light_checks.json`.

## Run command

Worker used the permitted light command
`python3 -B docs/plans/28-phase1-per-rule-classify-recovery/triage/join_reconcile.py`
and one comparison run with `--output-dir output/scratch-28/p2_join_repeat`.
Execute re-runs under the guard:

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py \
  --log output/scratch-28/runs/p2_join_reconcile.json -- \
  .venv-rp/bin/python -B docs/plans/28-phase1-per-rule-classify-recovery/triage/join_reconcile.py
```

## Deviations

None from the assigned implementation or heavy-run rule. No heavy job,
spool/disc open, K1, encode, forbidden script, commit or agent spawn was run.
Only the owned report/document/script/output paths and scratch-28 were written.

## Deferred work and known problems

No unit work or heavy discriminator is pending. Execute still owns the guarded
re-run, verification and commits. The seven named spool rows remain successor
items; the separate 2-01 source-data parity observation remains for Design.

The 3-17 inherited-byte table is deleted, so per-row identity comparison is
impossible; aggregate candidates do not identify its missing three rows.
The optional legacy-contract control remains skipped.

Unrelated changes appeared after the initially clean tracked-file status:
`parser/build_alldata.py`, `parser/kiwiw/cenc.py`, and untracked
`parser/tests/test_name_drop_guard.py`. This worker did not edit or revert them.
Pre-existing `.venv-rp` and `output` symlinks were left alone. Thus the shared
tree contains source edits beyond this unit, although this unit's authored
changes obey the owned-path boundary.

## Contradictions with DESIGN

- Carried: the measured 3-15 → 3-17 delta is **34** rows (O05 −30, O04 −4),
  while DESIGN explains only **31** forced-zero rows (30 + 1). Three remain
  unexplained by that sentence; no assignments were forced to fit it.
- Newly recorded wording discrepancy: DESIGN's carried 2-01 observation and
  the closed plan-14 record say type 288 in all 342 cells. The committed member
  TSV has **341 type-288 rows + one type-321 row**, dump_row **246** at
  `(0,834,886,321)`, assigned O05. The group proof and source-data parity
  observation remain carried unchanged; this unit records the precise typing.
- No contradiction with the Phase 2 join/verdict contract or outcome.
