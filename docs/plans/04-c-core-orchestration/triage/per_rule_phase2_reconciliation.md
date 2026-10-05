# Phase 2 — per-row join and cause reconciliation

The saved Phase 1 assignments join to all **776** plan-14 native keys, uniquely
and exhaustively: **342 2-01 + 434 amended 2-02**. Every row has a verdict:
**769 consistent, 7 conflict-proven, 0 conflict-open**. No cause is relabelled.
This is a fresh current-contract measurement, not restoration of deleted
3-08 mechanism bytes. Plan 14's historical Phase 1 outputs remain unchanged.

## Reproduction and evidence

From the repository root, Execute re-runs the light join under the guard:

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py \
  --log output/scratch-28/runs/p2_join_reconcile.json -- \
  .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/per_rule_join_reconcile.py
```

The worker ran `python3 -B` on that join script, exit **0**; Execute re-ran it under the guard (exit 0, outputs byte-identical). It reads only
committed TSVs and the small rules JSON; no proof bytes, spool, disc, K1 or
encode are opened or run. No additional heavy discriminator is needed.
`--output-dir output/scratch-28/<name>` permits a comparison run without
overwriting the published outputs. The script has an argparse entry point.

Outputs under `triage/`:

- `per_rule_phase2_join.tsv`: full key `(level, ix, iy, code, p0..p6, shape, vert)`,
  original rule/cause, final plan-14 group/disposition, 3-01 demander verdicts,
  proof references, R polygon presence, cell-local R verdict and reconciliation verdict.
- `per_rule_phase2_crosstab.tsv`: rule × final group × verdict counts.
- `per_rule_phase2_discriminators.tsv`: all seven O04 rows, including the saved per-demander
  counterfactual, current-contract pin, original and repaired C counts, R presence,
  verdict, explanation and successor flag. There are **0 O06** assignments.

Assignment, mechanism, membership, evidence and member-table joins use the full
native key. Tables lacking it (3-01 and 3-02) attach through the validated
`dump_row` and independently checked cell/type key. The 432 original 2-02 seeds
use their EO-repair proofs; 765 uses its proven 3-02 contribution and the Design
ruling; 335 uses its distinct 3-01 trigger and the F2 ruling. All 799 original
demanders are proven unrepresentable; the 3-03 checker disposition applies to
that original geometry. `R_polygon_count` is kept separate from cell-local
presence: row 765 has one R polygon, which contributes zero records in the cell.

## Counts and prediction tests

| Rule | Cause | Final group | Verdict | Rows |
| --- | --- | --- | --- | ---: |
| O01 | checker | 2-01 | consistent | 340 |
| O01 | checker | amended 2-02 | consistent | 23 |
| O05 | checker | 2-01 | consistent | 2 |
| O05 | checker | amended 2-02 | consistent | 130 |
| O04 | spool | amended 2-02 | conflict-proven | 7 |
| NO_RULE | unclassified; cause supplied by group proof | amended 2-02 | consistent | 274 |
| **Total** | | | | **776** |

O06/build count is zero. `NO_RULE` remains the measured assignment, with its
cause established by the joined group proof; no new rule is registered.

- **PASS:** every 2-01 row is rule-assigned: 342/342 (O01 340, O05 2).
- **PASS:** `NO_RULE` is a subset of amended 2-02: 274/274; 0 in 2-01.
- **PASS:** 776 join rows, 776 unique full keys, key set equals `phase3_membership.tsv`.
- **PASS:** cross-tab sum 776; every row has one of the three defined verdicts.
- **PASS:** discriminator keys equal all O04/O06 assignment keys (7/7 O04; 0 O06).

## Every cause conflict and the spool successor list

All seven rows below retain **O04 / spool**, final group **amended 2-02**,
3-03 **checker** disposition and verdict **conflict-proven**. Their original
crossing-closing rings emit zero records, and all EO faces of the original rings
emit zero records. The bounded discriminator instead deletes **only the
penultimate stored coordinate**, removing every crossing and leaving a simple
ring. These are different repair operations: EO decomposition preserves the
original filled region; coordinate deletion changes the source geometry.

| dump_row | Native cell/type (level, ix, iy, code) | Demander | Deleted coordinate | Repaired C records / bytes | Representable? | Repaired demand? | Added 89? |
| ---: | --- | --- | ---: | --- | --- | --- | --- |
| 138 | (0, 1695, 699, 288) | tall=11620:L0:home(1695,699):ordinal=0 | 8 | 1 / 144 | yes | yes | yes |
| 236 | (0, 913, 876, 578) | L0:home(913,875):ordinal=7 | 3 | 0 / 0 | no | no | no |
| 282 | (0, 1915, 1030, 288) | L0:home(1914,1031):ordinal=1 | 7 | 0 / 0 | no | no | yes |
| 284 | (0, 1411, 1044, 288) | tall=33995:L0:home(1413,1043):ordinal=2 | 9 | 1 / 18 | yes | yes | no |
| 317 | (0, 1945, 1110, 578) | L0:home(1946,1110):ordinal=0 | 3 | 0 / 0 | no | no | no |
| 496 | (0, 1248, 1253, 288) | tall=45377:L0:home(1248,1255):ordinal=0 | 15 | 1 / 148 | yes | yes | no |
| 563 | (0, 1505, 1315, 288) | tall=48332:L0:home(1509,1315):ordinal=0 | 8 | 0 / 0 | no | no | yes |

Every key has `p0..p6 = 0`, `shape = vert = -1`; the TSVs store these full keys.
For **each** row, R polygon count is **0**, R cell-local presence is **false**,
original C count is **0**, EO-repaired C count is **0**, and the saved
penultimate-repair `missing_mismatch` is **false**. Thus:

- **138, 284, 496:** the edited source becomes representable and C emits one
  piece. The original checker demand was unrepresentable; the source defect
  still has a positive repair counterfactual even though R lacks the type.
- **236, 282, 317, 563:** the edited source has no representable target-cell piece
  and ceases to demand the type. Repair removes the mismatch by removing the
  demand, rather than producing a piece.

The exact inputs are the seven `penultimate_repair_probe` records in
`triage/per_rule_completeness_mechanism.tsv`; original-ring EO counts and proof paths
are in plan 04's `2-02_r-absent-complete-repair-zero_members.tsv`; R-zero
contribution is proven in `r_contribution_3-02.tsv`. These settle why the spool
cause and checker disposition coexist. **All seven named rows are carried to
plan 04's successor spool list**, including the four where repair removes
demand. This evidence does not authorise a spool edit or an R-parity claim.

## Row 335 and amended membership

dump_row **335**, full key `(0, 1379, 1138, 288, 0, 0, 0, 0, 0, 0, 0, -1, -1)`,
is **O05 / checker**, **amended 2-02**, **consistent**, with no R polygon and
zero original C records. Its demander is
`tall=39083:L0:home(1379,1143):ordinal=0`, a type-288 triangular sliver. The
3-01 branch is **c**, `c_tol_only=True`: it misses the centre by **0.348 raw**,
within the old checker's **0.5-raw TOL**. This distinct TOL-only centre-hit
trigger is retained; the join uses final `phase3_group`, not the historical
`phase2_group=open-question:Q-source-335`. The F2 Design ruling in
`phase3_groups.md` already folds it into 2-02; this unit makes no new ruling.

## Carried observations and known limits

1. **Phase 1 Carried item 1 — 3-17 arithmetic contradiction:** the measured
   3-15 → 3-17 aggregate delta is O05 −30, O04 −4, `NO_RULE` +34. The DESIGN
   sentence explains only 30 O05 + 1 O04 = 31 forced-zero rows, leaving three
   unexplained by that sentence. Counts and assignments are not adjusted.
2. **Phase 1 Carried item 2 — deleted per-row identity control:** the 3-17
   inherited-byte table is deleted, so a per-row comparison is impossible.
   Phase 1 lists aggregate bucket members as candidates, not proven mismatches.
   The three rows in item 1 cannot be identified from aggregate counts alone.
3. The optional legacy-contract control was skipped in Phase 1; this join adds
   no legacy-contract claim. Phase 1 Carried item 4 is settled by the seven
   saved current-contract discriminators above; no new heavy probe is pending.
4. **2-01 source-data parity remains carried to Design:** R has cell-local
   geometry while the spool has no representable source of the demanded type,
   so G cannot match R without inventing geometry. This is a proven source-data
   deviation, not a non-deviation. Its rule rows are **O01 340 + O05 2** (the
   O05 rows are 246 and 567); no O04 or `NO_RULE` row is absorbed into it.
   The historical observation says “288 in the 342 cells”; the member TSV
   actually has **341 type-288 rows and one type-321 row (246, cell (834,886))**.
   That wording discrepancy is recorded here without rewriting the closed
   record or re-deriving the group science.

F3's assignment gap is resolved by the new artefacts. Other kinds' native
classify joins stay open. Plan 04 Phase 3 stays open; no 3-90 re-run, plan 04
Phases 4–6, plan 06 or reseating of 170 / 3-16 / 3-17 is performed or claimed.
