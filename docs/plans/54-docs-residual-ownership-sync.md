# Docs residual-ownership sync (OVERVIEW + plan 35 / phase3_synthesis)

Plan 54 is docs-only honesty: bring OVERVIEW and plan-35 / `phase3_synthesis` residual-ownership prose in line with live tip `residuals.tsv` after plans 36–53 / 44 / 48–49, without claiming Phase 3 closed or flipping historical gate cells.

## Intent
Cody standing rule (2026-10-05). Docs-only; no heavy encode/K1; no plan 04 P4–6; no 3-90; no waivers for Cody-held rows.

## Why This Existed
DESIGN draft at `094b11f` still spoke as if oracle `4e6b0de7` were live and plan 44/48 were in flight. Stable OVERVIEW listed opened children including discharged R-G8-2-f-a / R-G8-1-d-a without current owners.

## What Was Built
**Changed:**
- `docs/OVERVIEW.md` — WP1 live oracle `88bd7852…` (plan 48); residual ownership tables from live `residuals.tsv`.
- `docs/plans/35-pss-and-phase3-close-synthesis.md` — dated post-close ownership block; historical RESIDUAL verdict preserved.
- `docs/plans/04-c-core-orchestration/triage/phase3_synthesis/synthesis.md` — same post-close block.

### Ownership map (live tip)
| Class | Owner | Rows |
| --- | --- | --- |
| blocks-phase3 | plan **44** (closed) | R-G5-4-a/b (still open) |
| blocks-phase3 | plan **45** (Design) | R-G5-4-c, R-G8-1-f |
| blocks-phase3 | plan **46** (Design) | R-G5-1/2, R-G8-4-c |
| blocks-phase3 | Design (window-before; **55** when numbered) | R-G8-1-b-a |
| blocks-phase3 | Cody via Design | R-G8-1-a |
| maps-parity-carried | **50** / **51** / **52** / **53** | R-G9-2 / 3-a / 3-b,c / 3-d |
| maps-parity-carried | Cody via Design | R-G5-5, R-G9-4 |
| discharged | **48** / **49** (+ earlier) | R-G8-1-d-a / R-G8-2-f-a; G1/G4; … |

Oracle live: `88bd7852…`. Perth: `04be2f6e…`. Memory plans 56–59 closed ops only — not residual-row owners.

## Review
Flash (`deepseek/deepseek-flash`): **PASS-WITH-CONCERNS** → **LAND** after R-G8-1-b-a wording aligned to `residuals.tsv` (no plan-55 folder on master yet).

## Residual Risks
- Soft: `residuals.tsv` owner column still says Design for several rows that OVERVIEW names by designed plan folder — intentional docs sync, not a TSV rewrite.
- Soft: plan 55 numbering pending; R-G8-1-b-a held as Design until then.

## Follow-ups
Plan **55** (window-before count basis) when parent asks — ready; not auto-started.

Scratch: `output/scratch-54/` (Flash review logs; regenerable).
