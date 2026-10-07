# Window rebuild for 80 R01 rows in eo_division_ceiling cells + determinism (R-G5-4-c, R-G8-1-f)

Plan 45 closed **R-G8-1-f** (determinism regenerated) and reclassified **R-G5-4-c**
from blocks-phase3 to **maps-parity-carried**: all 80 rows named
`producer_home_outside_R_cap` under design 44 Gate-B at locked R=8 (0 proven-fixed).
No encoder/oracle change. Live AU **`0c22b266…`** / Perth **`5b86d33e…`** unchanged.
No Phase 3 product-close. No F6/kind-order/L8 expand. Plan 46 not started.

## Intent
Cody rulings 4–5 (2026-10-06). Window rebuild at `d35b565` for ceiling R01 rows;
regenerate `-j1 == -j4` determinism or name unverifiable.

## Why This Existed
Plan 39 left 80 R01 rows in 4 `eo_division_ceiling` cells untestable by leaf
identity (footprints changed). R-G8-1-f: lost `determinism.json`; `-j12` never run.

## What Was Built

**Phase 1 — ceiling rows**
| Item | Result |
| --- | --- |
| Ref discs | `33006aa`→`013586b5` MATCH; `d35b565`→`4ed9cd80` MATCH |
| Window control | ALL_OK (4 cells byte-equal to full-ref frames) |
| Topology | 4→1, 4→1, 4→16, 4→1 |
| Producer | design 44 unique-byte\|fragment, R=8; source-tag offline |
| Per-row | **80/80 `producer_home_outside_R_cap`**; 0 `build:eo_bg_stitch` |
| Widen@16 | saturated (cands@8==cands@16); 0 recovers |

**Phase 2 — determinism**
| Item | Result |
| --- | --- |
| d35b565 -j1/-j4 | both `c4965442…` MATCH historical |
| tip -j1/-j4 | equal (`c4965442…`) |
| -j12 | `unverifiable:cap` |

Evidence: `triage/historical_bg/p4_ceiling/`;
`triage/independent_reviews/3-14/conditions/determinism/`.

## Review
Flash (`deepseek/deepseek-flash`): **LAND**.
- PASS A–G: window control; topology; 80 Gate-B residual; R-G5-4-c reclass;
  determinism; R-G8-1-f discharge; no encoder/plan-46.
- Soft: window comparator not separately committed (result JSON is); producer_class
  column aligned to decision on close; residuals forward-ref collapsed record
  (resolved by this close-out).

## Residual Risks
- R-G5-4-c: 80 rows remain without unique producer under R=8; optional Design
  revision for divided-leaf ceiling producer.
- Soft: window K1 bg failing 0 does not alone prove-fixed without producer.

## Follow-ups
Design: optional divided-leaf producer revision. Do not start 46 from this unit.

Scratch: `output/scratch-45/` (regenerable).
