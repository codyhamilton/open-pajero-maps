# Docs oracle + residual-ownership sync (OVERVIEW + plan 35 / phase3_synthesis)

Plan 60 is docs-only. It brings OVERVIEW and the plan-35 / `phase3_synthesis` ownership prose up to the live
tip after plans 45, 50–53 and 55. It does not claim Phase 3 closed and does not flip any historical gate cell.

## Intent
Cody standing rule. Docs-only: no heavy encode/K1, no plan 04 P4–6, no 3-90, no waivers for Cody-held rows,
no F6 / kind-order / L8-expand drafts.

## Why This Existed
The DESIGN draft was grounded at `10a976a` and was stale. It named `aeae426c…` (plan 50) as the oracle in force,
Perth `04be2f6e…`, plans 52–53 as in flight, plan 45 as designed and plan 62 as owning still-outside@16.
The live tip `b5c9ff9` had moved on: oracle `0c22b266…` (plan 53), Perth `5b86d33e…`, plans 45 / 50–59 closed,
plan 46 in progress, plans 61 / 62 box drafts only. OVERVIEW and the plan-54 block still named `88bd7852…` as live.

## What Was Built
**Changed** (land commit `6006486`):
- `docs/OVERVIEW.md`:
  - WP1 oracle cell: AU `0c22b266…` (53) over `aeae426c…` (50) over `88bd7852…` (48); Perth `5b86d33e…`;
    earlier oracles historical/protected.
  - Pin-contract line and the 2-01 "341 supply-path rows" wording (implemented by plan 50).
  - Phase-3 residual ownership section, rebuilt from live `residuals.tsv`.
- `docs/plans/35-pss-and-phase3-close-synthesis.md` and
  `docs/plans/04-c-core-orchestration/triage/phase3_synthesis/synthesis.md`: appended the dated block
  "Post-close residual ownership refresh (plan 60 — 2026-10-08)". The plan-35 verdict and the plan-54 block
  are preserved as history.

**Not changed:** `residuals.tsv`. Its owner/blocking columns already matched the live state, and rows
R-G5-1, R-G5-2 and R-G8-4-c are left for plan 46 to rewrite. No `gates.tsv` flip.

### Ownership map (live tip)
| Class | Owner | Rows |
| --- | --- | --- |
| discharged | **50** / **45** / **53** (new since 54); **55** / **48** | R-G9-2 / R-G8-1-f / R-G9-3-d; R-G8-1-b-a / R-G8-1-d-a |
| blocks-phase3 | plan **44** (closed) | R-G5-4-a/b (still open; still-outside@16 children to Design, plan 62 box draft) |
| blocks-phase3 | plan **46** (in progress, Execute; nothing landed) | R-G5-1/2, R-G8-4-c |
| blocks-phase3 | Cody via Design (no waiver) | R-G8-1-a |
| maps-parity-carried | **45** (still-outside@16 is plan 62's scope, box draft) | R-G5-4-c |
| maps-parity-carried | **51** (volume to Cody: F6 / kind-order) | R-G9-3-a |
| maps-parity-carried | **52** (piece count; volume to Cody: L8 selection expand) | R-G9-3-b, R-G9-3-c |
| maps-parity-carried | **53** (128 links) | R-G9-3-d-rem |
| maps-parity-carried | Cody via Design | R-G5-5, R-G9-4 |

**Carried is not closed for parity.** Carried rows are named deviations that still count against end-to-end
parity; they are only exempt from blocking the Phase 3 product close. Plans 56–59 are closed ops work, not
residual owners. Plans 61 and 62 are box drafts only.

## Review
Flash (`deepseek/deepseek-flash`): **PASS-WITH-CONCERNS**, recommendation **LAND**. Claims A–G verified
(oracle chain, ownership vs `residuals.tsv`, carried-not-closed wording, Cody-open naming, Phase 3 not closed,
TSV untouched, draft corrections recorded). Concerns:
1. The dated blocks said "tip `b5c9ff9`". Fixed in the close-out: it is the base (parent of the plan-60 commits).
2. The retained plan-54 block still heads "Live ownership" with `88bd7852`. Kept as history by design; the
   plan-60 block below it supersedes it.
3. `residuals.tsv` R-G5-4-a/b owner prose still reads "Design (needs a stronger identity test…)" although plan 44
   ran that test. Left untouched (no TSV edits in this plan); follow-up below.
4. IMPLEMENTATION checklist lagged the pushed commit. Moot after close-out.

## Residual Risks
- Soft: `residuals.tsv` owner prose for R-G5-4-a/b lags plan 44's closure. The blocking column is correct.
- Soft: the plan-62 box draft lists R-G5-4-c as a non-goal, while parent steering (2026-10-08 09:24) puts
  R-G5-4-c still-outside@16 in plan 62's scope. The docs follow the steering. Design should reconcile the draft
  before 62 is numbered.

## Follow-ups
- One-line `residuals.tsv` owner-prose refresh for R-G5-4-a/b. It can ride with plan 46's TSV edit or a later
  docs sync.
- Plan 46 updates OVERVIEW's plan-46 row when it lands or closes.

Scratch: `output/scratch-60/` (Flash review prompt/logs; regenerable).
