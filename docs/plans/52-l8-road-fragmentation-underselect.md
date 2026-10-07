# L8 (7,4): road fragmentation and under-selection vs R (R-G9-3-b, R-G9-3-c)

Plan 52 closed **R-G9-3-b** and **R-G9-3-c** as **proven-cause** (separate
mechanisms, joint close). No encoder/oracle change; live **`aeae426c…`**
unchanged. No Phase 3 product-close. Plan 53 not started. Steering hard: no F6
catchall/kind-order work.

## Intent
Cody standing rule (2026-10-05). Re-measure tip after plans 50–51. Prove b and c
separately. R-quantum coverage threshold **0.95** committed before measure.

## Why This Existed
Plan 42 named children for L8 (7,4): 308 shrink drops from fragmentation, and
under-selection / missing dc 10 outside sub (3,0).

## What Was Built
**Re-measure** (`l8_frag/remeasure.json`): plan 42 counts still valid on
`aeae426c` — G 2979 all dc12; R 929 (801 dc10 + 128 dc12); drop 308 all 2-vert.

**Phase 1 — R-G9-3-b**
| Item | Result |
| --- | --- |
| Mechanism | `extract-short-motorway-ways` |
| Spool | 3281 roads, 1 piece/way_id; 1089× npts==2 (interior; p50≈46 m) |
| Coverage threshold | 0.95 pre-committed |
| All-R coverage | 17.0% (fails; dc10 omitted) |
| R dc12 coverage | **100%** at 1 parent-raw |
| Disposition | proven-cause; piece-count residual named |

**Phase 2 — R-G9-3-c**
| Item | Result |
| --- | --- |
| Drop stage | `selection.json` L8 `highway=[motorway]` |
| Mapping | motorway→dc12; secondary…track→dc10 (never admitted) |
| Leaves 2/11/14 | G raw 225/0/0 vs R-in-leaf 4443/846/3205 |
| Disposition | proven-cause (deliberate subset); volume residual → Cody |

**Phase 3:** both proven-cause; no successor oracle; residuals updated.

## Review
Flash: **PASS-WITH-CONCERNS** → **LAND**.
- PASS: tip re-measure; separate b/c proofs; threshold pre-committed; dc12
  coverage 100%; selection rule cited; no silent topology force; no F6/kind-order.
- Soft concerns: all-R coverage fails by design of motorway-only selection;
  piece-count residual (2979 vs 128 dc12) not fixed; L8 selection expand is product.

## Residual Risks
- Volume under-select until L8 selection admits dc10-mapped classes (Cody).
- Soft: G motorway over-segmentation vs R’s 128 dc12 links.

## Follow-ups
Cody/Design: expand L8 `selection.json` beyond motorway? Optional generalisation
successor for short-way piece count. Do not start 53 from this unit.

Scratch: `output/scratch-52/` (regenerable).
