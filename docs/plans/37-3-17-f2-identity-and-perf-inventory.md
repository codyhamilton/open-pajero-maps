# 3-17 F2 identity and perf inventory

Plan 37 discharged two small carried items:

- **Plan 28 F2:** the 3-15 → 3-17 delta of 34 rows was explained only as 31.
  The 34 rows are now named per row by the 3-14 forced-zero mechanism, and
  that mechanism reproduces the 3-17 aggregates exactly.
- **`test_perf_inventory`:** it failed on master because six modules had no
  entry. It now passes 4/4.

Both phases closed. The terminal review was PASS_WITH_FOLLOWUPS, and every
follow-up was fixed at close-out.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Small design for plan 28 F2 (3-17 34-vs-31 arithmetic) and `test_perf_inventory`. Void any item already resolved on master, with evidence. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`. Master direct. Do not reseat 170, 3-16 or 3-17. Do not draw plan 04 Phases 4–6 or plan 06. Do not claim Phase 3 closed. No 3-90 re-run.

## Why This Existed
- **F2.** Plan 28's Phase 1 control measured 3-15 → 3-17 as O05 −30, O04 −4,
  NO_RULE +34. The inherited explanation ("30 O05 and 1 O04 … zeroed",
  `completeness_3-15_cell_local.md` L34) accounts for only 31 of them. The
  3-17 per-row byte table has been deleted from every host.
- **Perf inventory.** `test_perf_inventory::test_inventory_covers_every_module`
  failed on `d2459b6`: six modules added on 2026-10-06 had no entry in
  `parser/perf_inventory.json`. Plan 29 R4 had carried this, and it blocked
  plan 35's full-pytest gate.

## What Was Built
Commits:

- `517781e`: DESIGN.
- `9c99dcb`: IMPLEMENTATION and briefs.
- `0f3e530`: unit 2-01.
- `66d9589`: unit 1-01, Phase 1 close.
- `5facd75`: Phase 2 close.
- The close-out commit: review fixes and this record.

### Phase 1 — F2 per-row identity (match)
Lasting files are in `docs/plans/04-c-core-orchestration/triage/`:

- `per_rule_phase1_f2_identity.py`: a light join of the committed tables plus
  one streamed read of the plan 31 changed-cell list;
- its outputs `per_rule_phase1_f2_identity.{tsv,json,md}`;
- `parser/tests/test_per_rule_f2_identity.py`, three synthetic tests.

Input pins:

| Input | sha256 | Rows |
| --- | --- | --- |
| assignment | `c73dc3fb…` | 776 |
| mechanism | `43cbc2c0…` | 776 |
| changed cells (`output/scratch-31/diff-3-14-au.cells.tsv`) | `77ff1d86…` | 246,123 |

The shared/added partition comes from the `in_historic_188` / `in_added_89`
columns.

Result:

- The forced-zero set is **34 = O05 30 (shared) + O04 4**. The O04 rows are
  shared 1 (dump_row 317) plus added 3 (dump_rows 138, 282, 563).
- Measured 3-15 is O01 363 / O04 7 / O05 132 / O06 0 / NO_RULE 274. The
  predicted 3-17, 363 / 3 / 102 / 0 / 308, equals the 3-17 yardstick.
  `match: true`.
- The `.md` carries a plan 28-scoped erratum. The 31 statement is incomplete:
  it accounts for the 31 shared forced-zero rows only.
- Plan 28 F2 points to the erratum.

### Phase 2 — perf inventory
- Six entries were added to `parser/perf_inventory.json` (+36 / −0 lines).
  Five are `orchestration`.
- `parser/tools/k1_representable.py` is `c-later` with `phase: null`. It is
  named as a plan 04 Phase 5 input: the `--engine python` count-oracle mirror.
- `test_perf_inventory.py` passes 4/4.
- Plan 29 R4 and the R4 carry in `docs/design/out-of-span-name-guard.md` are
  discharged by pointer.
- Full `parser/tests` was collected at `0f3e530` (plan 35 P1 guarded run,
  `output/scratch-35/runs/p1_pytest.json`): **1 failed, 1365 passed, 7 skipped
  in 698.31s**.
  - The one failure, `test_parcel_mask.py::test_fill_only_masked_and_absent_cells`,
    is not from plan 37. It was bisected to plan 34 unit 2-02 `5182c83`:
    `5182c83^` gives 4 passed, `5182c83` gives 1 failed / 3 passed.
  - It is owned by plan 34 and recorded in that plan's record.

## Deviations
- **Unit seat.** Codex (`gpt-6.1-sol`) hit its weekly usage cap at 11:23 AEST,
  so Execute did both units itself. The cap resets 2026-10-10 11:50 AEST (log
  `output/scratch-37/p1p2.codex.log`). This is disclosed in both unit reports.
- **Cell list.** The cell list is plan 31's `diff-3-14-au.cells.tsv`, as
  DESIGN prescribed. It stands in for the 3-15 text's `AU.differing_cells.tsv`,
  which is not in the repo. This is disclosed in the `.md` Limit (review F2).

## Review
- **Seat:** a Claude CLI clean-context reviewer, used because Codex was
  weekly-limited. It did not build this plan.
- **Scope:** reviewed `5facd75`, verdict **PASS_WITH_FOLLOWUPS**. It re-ran
  the identity script, and the TSV was byte-identical with JSON keys equal.
  The three input shas match. The join is a bijection (776/776). The six
  module classifications were checked against the code. 7 passed.
- **F1 (medium), fixed:** the plan 28 pointer said "proven per row". It now
  says "named per row … matched exactly to the 3-17 aggregates (per-row 3-17
  bytes deleted)".
- **F2 (medium), fixed:** the cell-list proxy is now disclosed in the `.md`
  Limit and in the script docstring. It closes fully only if
  `AU.differing_cells.tsv` is recovered.
- **F3 (low), fixed:** the erratum now says "incomplete" instead of "arithmetic
  undercount", and the row attribution is marked as derived.
- **F4 (info):** the full-suite collection predates
  `test_per_rule_f2_identity.py`, which passes separately (3/3).
- **F5 (low), fixed:** in the plan 29 R4 bullet, the "both carries" sentence is
  now its own bullet, and the pointer names this record.

## Residual Risks
- The 3-17 per-row bytes are gone, so the identity rests on per-row naming
  plus an exact aggregate match. It can never be confirmed row-for-row.
- The equality of the changed-cell set with `AU.differing_cells.tsv` is
  inferred rather than pinned.

## Follow-ups
- Plan 04 Phase 5 decides whether `parser/tools/k1_representable.py` is
  deleted or kept as the independent oracle for
  `test_k1_completeness_representable.py`. This is named in the inventory
  entry and not drawn here.
- If `AU.differing_cells.tsv` is ever recovered, hash it and compare it with
  `77ff1d86…` (review F2).

## Decisions Worth Keeping
- "Shared/added" means the mechanism table's `in_added_89` flag, not
  re-derived key sets. The added side cannot discriminate here: all 89 added
  keys lie on changed cells. The discriminating evidence is the shared side,
  where 31 of 136 rows are zeroed and 105 survive at exactly 3 / 102.
- Inventory class follows the code's scaling, not its importance. A
  full-AU-vertex loop reachable only from a non-default engine is still
  `c-later`.
