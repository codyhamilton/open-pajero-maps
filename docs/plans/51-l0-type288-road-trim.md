# L0 (1755,591)(2,1): type-288 over-emission driving road trim to zero (R-G9-3-a)

Plan 51 closed the **emission** half of **R-G9-3-a** as **proven-cause**: dominant
byte pressure is land-local L0 catch-all emission (`background_all` +
`match{}→288`), not marine spill. **No encoder/oracle change.** Road volume loss
(R 3695 raw vs G 0 in sub (2,1)) stays a **named residual** under current
kind-order policy; F6 selection successor and/or kind-order preference need
Cody/Design (no waiver, no silent flip). Live oracle **`aeae426c…`** unchanged.
No Phase 3 product-close. Plans 52–53 not started.

## Intent
Cody standing rule (2026-10-05). Re-measure on tip after plan 50. Prefer confined
fix if clear over-emission bug; else proven-cause with rule citation. No plan 04
P4–6; no 3-90; no Cody-hold waivers.

## Why This Existed
Plan 42 proved dv_shrink drops 207 roads + 227×288 under a frame filled with
type-288 R does not carry in this parent. Child R-G9-3-a owned the upstream
emission / kind-order question.

## What Was Built
**Phase 1 — census** (`triage/trim_r_parity/l0_288/`):
| Item | Result |
| --- | --- |
| Oracle | `aeae426c…` (`output/scratch-50/G_new`); plan 50 did not touch this parent |
| Parent type-288 | **8777** (plan 42 counts still valid) |
| Spool-local type-288 | **8629** (98.31%) |
| Overlap share-in | 148 (1.69%) |
| Dominant class | **land-local-catchall-emission** (≥95%) |
| Assumption 1 (marine spill) | **wrong** |
| Sub (2,1) | leaf 6; 6401 kept 288; 0 roads; frame 131072 B |
| Trim dump | drop 207 roads + 227×288; pre-shrink 6628×288 |
| R parent | 0×288, 19×1024, 1×321, 1×291; 179 roads |
| Kind-order pressure | 288 = 94.63% of (288 + dropped-road) verts in trim dump |

**Phase 2 — proven-cause (no fix landed):**
Rule citation:
1. `parser/refdata/selection.json` L0 `background_all: true`
2. `parser/refdata/vocab/bg_type.json` L0 `match:{} → 288`
3. `docs/design/osm-vocabulary-mapping.md` (288 catch-all is a decision)
4. Plan 03 F6 / `docs/schema/map-background.md` (excess buildings; replace catch-all)

Why not a confined fix now: removing catch-all/`background_all` is the F6
**national** product change (R carries 2,203,680×288 at L0). Kind-order
road→bg→name flip requires Cody (DESIGN open question 1).

## Review
Flash: **PASS-WITH-CONCERNS** → **LAND**.
- PASS: census re-measured on tip; dominant class ≥95%; rule cited; kind-order not
  silently flipped; residual updated; no oracle churn.
- Concerns (soft, kept): volume residual still open until F6 or kind-order product
  call; aggregate provenance (no per-shape OSM id on disc) — labels are uniformly
  `unknown type 0x120`, consistent with catch-all.

## Residual Risks
- Road length in (2,1) remains 0 vs R 3695 raw until selection or kind-order changes.
- Soft: overlap share-in 148 not itemised per neighbour (lower bound only).

## Follow-ups
- Cody/Design: F6 explicit bg mapping + unmapped→drop (successor plan), and/or
  kind-order preference when R has roads and 0×288.
- Do not start 52–53 from this unit.

Scratch: `output/scratch-51/` (regenerable census runs).
