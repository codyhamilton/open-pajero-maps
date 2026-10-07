# R-G8-1-b-a — window_before vs 3-13 Boundary-before basis (plan 55)

**End state: `explained-dual-basis`.** R-G8-1-b (after-0 on `4ed9cd80`) stays discharged.

## Predicates (both reproduced on tip)

Inputs: HEAD K1 `--dump-failures` on `output/scratch-36/G_pre311/ALLDATA.KWI` (`87a01b14…`), kinds `background` + `background_boundary`. Regenerated under `run_heavy_python` as `output/scratch-55/dump_pre311/` (byte census matches committed `window_before.json`).

| Figure | Predicate | Reproduction |
| --- | --- | --- |
| `table_boundary_before` in `causes_rootcause.md` L60–77 | `background_boundary` dump rows with `level==L`, `code==window_type`, leaf cell in **half-open** rectangle `[x0,x1)×[y0,y1)` (`x0≤ix<x1`, `y0≤iy<y1`) | All 9 windows: half-open type count **equals** the table (e.g. 255, 829) |
| `background_boundary_*` in `window_before.json` | Same kind/level/type filters, leaf cell in **inclusive** rectangle `[x0,x1]×[y0,y1]` as coded in `window_before.py` | Exact match to committed JSON (e.g. 403, 1224) |

Fill-before usually matches the **inclusive** dump census (`all_types` or, for 0/289, `type`).

## Root cause

Not a HEAD-checker bug. The 3-13 table’s Boundary-before integers are a **half-open leaf-cell window** count; `window_before.py` counts the same dump with an **inclusive** window (and the prose label “Window inclusive source cells” describes the CF source-cell set, not the Boundary-before dump predicate). Both integers are correct under their named predicates.

## Evidence

- `output/scratch-55/runs/dual_basis_proof.json`
- `output/scratch-55/runs/predicate_census.json`
- Regenerated dump: `output/scratch-55/dump_pre311/` (regenerable; not required in git)

## Non-goals kept

No encoder change; R-G8-1-b not reopened; no Phase 3 product-close.
