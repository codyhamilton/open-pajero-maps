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


## DESIGN revision 2 (after `8ee2559`) — Gates A+B

Root cause of second stop: Assump-1 candidate window understates true producer homes (`diag_nbhd`: 16/25/37 of 48 recover at Moore 2/3/5, including unique-byte). Full-set ≥99% agreement-rate conflated search-window understatement with OE failure — **retired**.

Contract (box draft → `92cd35f`):
- Candidates = bbox-meet ∪ Moore(R); R not preset to 1.
- Phase 1 control: **expanding search** radius 1→R_cap=8 per row until unique-byte|unique-fragment (or residual); log recovering radius.
- **Gate A:** among rows that resolve unique-*, ≥99% OE/new-disc pass.
- **Gate B:** 100% class coverage with RC — unique-byte | unique-fragment | `producer_home_outside_R_cap` | `producer_ambiguous`. Bare `producer_none` does not close.
- Cover definition unchanged. Offset census → `offset_census.json` / this file before locking Phase 2 default R.

`diag_nbhd` table (48 prior `producer_none` under nb=1):

| Moore radius | recovered of 48 |
| ---: | ---: |
| 1 (3×3) | 0 |
| 2 (5×5) | 16 |
| 3 (7×7) | 25 |
| 5 (11×11) | 37 |

Expanding-search control + census in flight (`2e936e4`).


## Expanding-search smoke (`--smoke --r-cap 8`, after `27f6e5b` fix)

CONTROL_OK both gates:
- Gate A: resolved_unique=11, oe_pass=11, oe_fail=0, rate=1.0 PASS
- Gate B: ok=12, bad=0 PASS — classes unique-fragment=6, unique-byte=5, producer_home_outside_R_cap=1
- Stratified n=200 seed=44 queued next.
