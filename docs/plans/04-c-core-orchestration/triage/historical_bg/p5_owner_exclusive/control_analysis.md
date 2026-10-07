# Plan 44 Phase 1 control analysis

## Prior stop (byte-equal-only) — `0551ed2`

- Smoke n=12 rate 0.25; home-with-bg n=60 rate 0.3167.
- All disagrees `prod_none` / `disagree_producer_none`.
- OE limb 100% whenever a unique `33006aa` producer existed.
- Root cause: identity-proven R01 shapes are often EO fragments / cover pieces — disc bytes ≠ full-leaf `33006aa` clip of the geometric source.
- Design revised producer to unique-byte | unique-fragment (`1b839e3`).

## Revised-contract re-run — tip `ef00c12` / `3073566`

- Stratified n=200 seed=44 (plan 39 identity-proven; codes 288/289/291/578 ×50).
- Result: agree=150 disagree=48 skip=2 rate=**0.757576** — **CONTROL_FAIL** (gate ≥0.99).
- Artifact: `control_result.json`, `control_result.txt`; run log `output/scratch-44/runs/control_n200.*`.
- Agree split: 91 unique-fragment + 59 unique-byte. Fragment recovery is real (rate 0.25→0.76).
- All 48 disagrees are still `disagree_producer_producer_none` (systematic class).
- Zero `producer-ambiguous`, zero `disagree_no_oe`, zero `disagree_source_removed`.

### Diagnosis of the 48 `producer_none` (diag_none)

Every row: no bbox-meeting spool candidate's `33006aa` clip into L contains all identity-bearing verts of the disc record (`no_cover`).

| bucket | n |
|--------|--:|
| zero spool candidates (nbhd=1) | 18 |
| few clips (1–5) but incomplete IB cover | 20 |
| many clips (≥6) but incomplete IB cover | 10 |

No empty-IB rows; no single-cover-without-exclusive rows in this sample.

Neighbourhood sweep (1/2/3/5) queued to test whether Assumption-1 search width recovers any; leaf_io notes `neighbourhood=1` is the 3×3 Assumption-1 window.

## Gate

Phase 1 **not closed**. Systematic `producer_none` remains. Phase 2 not started. Escalate to Design with this diagnosis (fragment limb helps but does not reach ≥99%; remaining misses are no-cover under nbhd=1).
