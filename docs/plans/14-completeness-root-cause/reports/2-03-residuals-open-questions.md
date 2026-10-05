# Report 2-03 — residuals and open questions ledger

Phase 2, unit **2-03** of plan 14. Status: **closed on master**.
No rule registration. No `_k1_cmp.c` / `_cenc.c` / rules edit. No Phase 3.

## Phase 2 outcome (quoted from `DESIGN.md`)

> every Phase 1 unattributed row is either (a) member of exactly one named group whose
> committed reproducer isolates a single mechanism and states the expected completeness
> count movement (or expected R/G byte equality), or (b) listed under `open questions`
> with the discriminators tried and why none proved.

## Pre-edit checks

- 2-01 (`b775e9b`) and 2-02 (`bcb266b`) membership artefacts are on HEAD.
- The Phase 1 TSV has 776 unique native keys (asserted).

## Union map (`triage/phase2_membership.tsv`)

| phase2_group | rows |
| --- | ---: |
| `g-omits-cell-local-dvd-type` (2-01) | 342 |
| `r-absent-complete-repair-zero` (2-02) | 432 |
| `open-question:Q-source-335` | 1 |
| `open-question:Q-tile-alias` | 1 |
| **total** | **776** |

The script asserts that `|2-01| + |2-02| + |open| = 342 + 432 + 2 = 776`, that
2-01 ∩ 2-02 = ∅, and that every key is in the Phase 1 set.

## Open questions

Details are in `triage/phase2_open_questions.md`.

- **Q-source-335.**
  - Tried: a centre-branch / (a) / (b) search over ±32 L0 spool cells (4,225
    cells, 433 code-288 rings). Nothing met.
  - The single bbox-meeting sliver has 0 records in both the mirror and C.
  - Unproven: no source reproduces the demand.
- **Q-tile-alias (765).**
  - Tried: 2-01 cell-local test (no meet). Complete repair plus C: 0 records.
  - The evidence matches the 2-02 mechanism, but the row is kept open because
    DESIGN's 2-02 membership rule is `R_polygon_count == 0`. A Design ruling is
    proposed.
- **Q-repair-emits.** None (656 resolved by densify; production C agrees).
- **Q-2-01-densify (verification).** Production C gives 0 records on 342/342
  2-01 sources, so the 2-01 mechanism is confirmed under the production encoder.

## Reproducer and runs

- `triage/residuals_2-03.py` (read-only), via `parser/tools/run_heavy_python.py`.
  - `runs/residuals_2-03_w8.json`: exit 0, peak 79.8 MB.
  - `runs/residuals_2-03_w32.json`: exit 0, peak 79.8 MB.
- Scratch: `output/scratch-14/residuals/`.

## Phase 2 movement summary (for Phase 3; nothing applied)

| Group | Rows | Predicted movement |
| --- | ---: | --- |
| 2-01 `g-omits-cell-local-dvd-type` | 342 | build synthesises the piece, or checker excludes zero-rounded-area branch-`b` sources → −342 (Phase 3 chooses) |
| 2-02 `r-absent-complete-repair-zero` | 432 | proven non-deviation (R=G=absent under clip/densify/round) or checker stops the demand → −432 |
| open questions | 2 | none until resolved |
