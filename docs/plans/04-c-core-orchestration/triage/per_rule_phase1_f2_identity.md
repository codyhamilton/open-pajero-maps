# Plan 28 F2 — 3-15 → 3-17 per-row identity (plan 37 Phase 1)

Result: **match.** The forced-zero set has exactly **34 rows: O05 30 + O04 4**
(O05 shared 30; O04 shared 1 + added 3). Applying it to the measured 3-15
buckets reproduces the 3-17 inherited-byte buckets exactly.

## Mechanism

The 3-14 dump extension reuses `other_mechanism` only in byte-unchanged cells
and zeroes it on changed cells (`rebaseline_3-17_9064.md`, "conservatively
zeroes it on changed cells"). 3-17 ran the classifier on those raw bytes, so
every O04/O05 row whose cell changed in 3-14 reads as NO_RULE there. O01 is not
affected because no O01 row lies on a changed cell. The predicted set is
therefore *O04/O05 rows whose (level, ix, iy) is in the 3-14 AU changed-cell
list*.

## Inputs (sha256)

| Input | Path | sha256 | Rows |
|---|---|---|---|
| Rule per row (plan 28 classify) | `per_rule_classify_assignment.tsv` | `c73dc3fb0c07363546ef84da98dd73e741857a2dd5bc1ad47e5ecd14eeb5f9ef` | 776 |
| 3-15 shared/added partition (`in_historic_188`, `in_added_89`; the columns plan 28's controls select from) | `per_rule_completeness_mechanism.tsv` | `43cbc2c00d2df7ccb9cfc16c7e6fc8ce5c502c66efea2a4d19de13f772e2a85d` | 776 = 687 shared + 89 added (188 historic) |
| 3-14 AU changed cells, 013586b5 → 4ed9cd80 (plan 31) | `output/scratch-31/diff-3-14-au.cells.tsv` (one streamed read) | `77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f` | 246,123 (all `changed`) |

Rows are joined on the full 13-field native key plus `dump_row`. The script
fails on any unmatched row, a cell-list sha mismatch, or a row count other than
246,123.

## Counts

| Rule | 3-15 measured | Forced zero (shared / added) | Predicted 3-17 | 3-17 yardstick |
|---|---:|---:|---:|---:|
| O01 | 363 | 0 | 363 | 363 |
| O04 | 7 | 4 (1 / 3) | 3 | 3 |
| O05 | 132 | 30 (30 / 0) | 102 | 102 |
| O06 | 0 | 0 | 0 | 0 |
| NO_RULE | 274 | — | 308 | 308 |

The other 99 rows on changed cells are already NO_RULE in 3-15. No forced row
is in the historic 188. The per-row list is in `per_rule_phase1_f2_identity.tsv`
(34 rows: key, 3-15 rule, shared/added, historic flag, changed-cell status,
predicted 3-17 rule). The summary is `per_rule_phase1_f2_identity.json`.

**Limit:** the 3-17 per-row byte table is deleted from every host. This proves
that the mechanism predicts exactly the measured 3-17 aggregates, and it names
the 34 rows that mechanism forces. It cannot compare row-for-row against bytes
that no longer exist. 3-17 was not re-run or reseated.

## Erratum (plan 28-scoped)

`completeness_3-15_cell_local.md` says the 3-14 dump's forced-zero bytes are
"30 O05 and 1 O04 on `AU.differing_cells.tsv` cells". The statement is an
arithmetic undercount. It names the shared rows (30 O05 + O04 dump_row 317)
and omits the 3 **added** O04 rows, dump_rows 138, 282 and 563. Those rows lie
on changed cells as well, which is expected: the 89 added keys are EO-stitch
side-effects on 3-14-changed cells. The forced-zero total is 30 + 1 + 3 = 34,
matching O05 −30 / O04 −4 / NO_RULE +34. The 3-15 text, the 3-17 rebaseline
note and the generated `per_rule_phase1_controls.md` are not rewritten.

Reproduce: `.venv-rp/bin/python -B
docs/plans/04-c-core-orchestration/triage/per_rule_phase1_f2_identity.py`
(exit 0 on match, 1 otherwise). Tests:
`parser/tests/test_per_rule_f2_identity.py`.
