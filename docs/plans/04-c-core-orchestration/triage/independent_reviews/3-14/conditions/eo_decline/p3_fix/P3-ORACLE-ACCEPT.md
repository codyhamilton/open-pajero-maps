# Plan 48 P3 — R-DVD accept (Design 2026-10-07 ~22:29 AEST)

## Gate (prior HOLD)
Hold land on successor oracle `88bd7852` until R-DVD per-cell compare on L0 `(1768,573)` and `(1817,726)` shows each cell **no worse** vs R than live oracle `4e6b0de7` (or equal), with per-cell exact witness. Perth MATCH alone does not waive.

## Measure (Execute, tip `094b11f`)
- `all_cells_accept_no_worse_R_coverage = true` (plan 42 R-coverage-by-G: R verts → nearest G).
- L0 `(1768,573)`: all R-coverage metrics **equal**; payload same len 108466 (47 B differ); witness: one type-288 sc=2 hexagon **rotated** (same vertices/bbox).
- L0 `(1817,726)`: all R-coverage metrics **equal**; payload 3266→3278 (+12); witness: one 7-pt type-288 → **two** 4-pt rings sharing split vertex `(3039,154)`.
- Evidence (uncommitted): `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-14/conditions/eo_decline/p3_fix/` — `R_DVD_COMPARE.md`, `CHANGED_CELLS.md`, `r_coverage.json`.

## Ruling: ACCEPT
Lift HOLD. Execute may Flash-review when free, then land P3 + promote successor oracle `88bd7852` + close plan 48.

Soft residual (not a land gate): exact OSM/spool **input** ring IDs into `eo_split_on_vertices` not instrumented. Output arrangement witnesses above satisfy the accept gate; do not block on input ring-ID instrumentation.

Master direct; flock + wrapper; `-j4`; no plan 04 P4–6; no 3-90; OpenCode DeepSeek Flash.
