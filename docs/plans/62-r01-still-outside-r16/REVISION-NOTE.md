# Plan 62 revision note (Design, 2026-10-08 ~11:00 AEST)

Earlier draft: box 2026-10-08 03:13 AEST, ground tip `10a976a`, oracle `aeae426c`. Copy kept at `maps-design-drafts/62-r01-still-outside-r16.bak/DESIGN.md`. Intent unchanged; reconciliation appended under it.

## What changed and why

| # | Change | Why (evidence at tip `8498eec`) |
| --- | --- | --- |
| 1 | **R-G5-4-c moved from non-goals into scope.** It gets gates G-c1–G-c6 and an RC path. | Design steering 09:24. Execute started 62 with it in scope. `residuals.tsv` row 17 is `maps-parity-carried`, and carried is not closed. |
| 2 | Old Phase 2 "mass finish / stitch" **dropped**, replaced by **re-decide under the plan-46 producer**. | Plan 44 decided 95,059 / 95,059 (`phase2_decisions_full.tsv.gz` `3d221b6f…`). The 30k / 451 figures were partial. |
| 3 | All plan-44 / plan-45 residual classes are re-decided before naming children. The 87,743 proven rows get a same-type audit. | `mass_decide.py` / `widen_outside.py` / `ceiling_decide.py` use `leaf_rect_raw` or the full-frame rect (RC4), `find_producer(piecewise=False)` (RC2), no `FarHomes` (RC3) and no same-type filter (RC5). A class from a known-defective matcher is not a root cause. |
| 4 | `producer_home_outside_R_cap` is barred as an RC for R-G5-4-c. | `p4_ceiling/widen16.json`: cands@8 == cands@16 (saturated). `rows_80_keys.tsv`: 57 / 80 rows have a historical source at Chebyshev ≤ 1. |
| 5 | Rows needing plan 63 (ambiguous) or plan 64 (source-removed) become named children owned by those plans. | 2,972 R01 `producer_ambiguous`; 469 `disagree_source_removed`. |
| 6 | Owner wording for R-G5-4-a/b is fixed first by plan 65 (docs). | `residuals.tsv` R-G5-4-a/b owner columns lag plan 44 (still say "or a waiver" / "confirm checker"). |
| 7 | Oracle / tip updated: `0c22b266` (plan 53), Perth `5b86d33e`; tip `8498eec`. | OVERVIEW L42. |

## Execute reconciliation

Execute started from the earlier draft. Reuse any census output that meets the new Phase 1 contract. Items 2–4 are a scope addition to Phase 2. If Execute already ran a plan-44-matcher census, keep it as the "old class" column.
