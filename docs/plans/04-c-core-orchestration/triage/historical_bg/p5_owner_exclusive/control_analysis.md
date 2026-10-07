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


## Stratified n=200 seed=44 expanding search ≤R_cap=8 — Gate A+B PASS

`CONTROL_OK` tip artifacts after `6b628f9` smoke + this run.

| Gate | Result |
| --- | --- |
| **Gate A** | resolved_unique=**191**, oe_pass=**191**, oe_fail=**0**, rate=**1.0** PASS (≥99%) |
| **Gate B** | ok=**198**, bad=**0** PASS — unique-byte=**73**, unique-fragment=**118**, producer_home_outside_R_cap=**7**, producer_ambiguous=**0** |

Skip=2 (unevaluable). Cover definition unchanged.

### Offset census (191 recovering unique-*)

| recovering Moore radius | count |
| ---: | ---: |
| 1 | 150 |
| 2 | 16 |
| 3 | 9 |
| 4 | 6 |
| 5 | 6 |
| 6 | 3 |
| 8 | 1 |

- max recovering radius = **8** (equals R_cap; 1 row)
- p50=1, p90=3, p95=4, p99=6
- Top offsets: `(0,0)`=84, `(-1,0)`=13, `(0,1)`=12, `(0,-1)`=9, `(1,0)`=9 (Moore-1 neighbourhood dominates)

Full census: `offset_census.json`.

### Proposed R for Phase 2 (Design confirm required)

**Propose R = 8** = max recovering radius among unique-* in this stratified sample (DESIGN Decision 5). Proof: 191/191 resolved rows recover at radius ≤8; the single max is radius 8. Setting R&lt;8 (e.g. p99=6) would leave that one sample row as an additional outside residual without census justification under the max rule.

### Phase 2 residuals (named)

7× `producer_home_outside_R_cap` → `phase2_residuals_outside_R_cap.tsv` (children of R-G5-4 or named Phase 2 residuals; never silent):

- `0/1610/657` code=288 shape=0 spool=1 clips=0 ib=78 uncovered=78
- `0/866/905` code=578 shape=3 spool=4 clips=1 ib=85 uncovered=85
- `0/1469/1728` code=289 shape=0 spool=1 clips=0 ib=96 uncovered=96
- `0/1674/718` code=578 shape=33 spool=32 clips=32 ib=34 uncovered=34
- `0/963/919` code=578 shape=1 spool=1 clips=0 ib=36 uncovered=36
- `0/1276/1754` code=289 shape=3 spool=2 clips=1 ib=64 uncovered=64
- `0/1749/1708` code=288 shape=1 spool=2 clips=1 ib=22 uncovered=22

### Phase 1 status

**CLOSED** on Gate A + Gate B. Do **not** start Phase 2 mass run until Design confirms proposed R=8.
Designs 45/46 remain blocked on that confirm.


## Right-censor widen R_widen=16 (Design confirm protocol)

One-shot probe on the 7 Phase 1 `producer_home_outside_R_cap` rows only (not full 95k).

| Metric | Value |
| --- | ---: |
| recovered unique-* | **5** |
| still outside at 16 | **2** |
| recover radius >8 | **5** |
| stop_for_design (≥20) | **False** |
| by_recover_r | {'16': 2, '15': 1, '9': 2} |

Recoveries (attribute at recovering radius; **do not bump mass-run R=8**):
- `0/1674/718` shape=33 code=578 → **unique-fragment** r=16 home=[1672, 734]
- `0/866/905` shape=3 code=578 → **unique-byte** r=15 home=[868, 920]
- `0/963/919` shape=1 code=578 → **unique-fragment** r=16 home=[979, 919]
- `0/1469/1728` shape=0 code=289 → **unique-byte** r=9 home=[1472, 1737]
- `0/1276/1754` shape=3 code=289 → **unique-fragment** r=9 home=[1285, 1755]

Still `producer_home_outside_R_cap` (max_radius=16):
- `0/1610/657` shape=0 code=288 spool=2 clips=0 ib=78 uncovered=78
- `0/1749/1708` shape=1 code=288 spool=2 clips=1 ib=22 uncovered=22

Mass-run default remains **R=8**. New outside_R_cap from mass run get the same widen-16 before final classification.
