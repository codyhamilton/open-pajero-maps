# Name the R-G8-1-b-a window_before vs 3-13 boundary count basis

Plan 55 closed **R-G8-1-b-a** as **`explained-dual-basis`**: the 3-13 `Boundary before` integers and `window_before.json` dump census are both correct under named, different leaf-window predicates on the same `87a01b14` K1 dump. **R-G8-1-b** (after-0) stays discharged. No encoder change; live oracle `88bd7852` unchanged.

## Intent
Cody standing rule (2026-10-05). Prefer explained-dual-basis when both predicates cohere. No Phase 3 product-close; no Cody-hold waivers; no 3-90 / plan 04 P4–6.

## Why This Existed
Plan 43 review F1: e.g. **403 vs 255**, **1224 vs 829** between inclusive dump census and the CF table. Residual was a named unexplained deviation; after-0 supersession of R-G8-1-b does not depend on it, but honesty required a root cause.

## What Was Built
**Evidence:**
- `…/3-14/conditions/window_before_basis.md` — predicates + class
- `…/window_before_dual_basis_proof.json` — per-window inclusive vs half-open census
- `window_before.py` docstring pointer; `causes_rootcause.md` one sentence under the CF table
- `residuals.tsv` R-G8-1-b-a → discharged; OVERVIEW discharged list

**Reproduction:** regenerated `output/scratch-55/dump_pre311/` via wrapper on `G_pre311` (`87a01b14`); inclusive counts match committed `window_before.json`; half-open type-filtered counts match all 9 Boundary-before table cells.

### Predicates
| Figure | Predicate |
| --- | --- |
| Table Boundary-before | `background_boundary` dump, `code==type`, leaf in **half-open** `[x0,x1)×[y0,y1)` |
| `window_before.json` | Same dump filters, leaf in **inclusive** `[x0,x1]×[y0,y1]` (`window_before.py`) |

## Review
Flash: **PASS-WITH-CONCERNS** → **LAND** (provenance + committed proof JSON addressed at close).

## Residual Risks
- Soft: CF table header still says “Window inclusive source cells” (source-cell set); Boundary-before column is half-open — documented, not rewritten as silent history edit.

## Follow-ups
None for this residual. Plans 50–53 not started (parent).

Scratch: `output/scratch-55/` (regenerable).
