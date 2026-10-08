# Plan 65 — IMPLEMENTATION (docs-only owner wording sync)

Base `origin/master` `8498eec`. Worktree `/home/codyh/workspace/open-pajero-maps-60` (separate from plan 62's checkout). No heavy work.

## Verified ground
- The a/b split by the `src` column of `phase2_decisions_full.tsv.gz` was recomputed in plan 62's census join and matches:
  - a: 87,648 / 3,023 / 2,783 / 525 / 118 / 37;
  - b: 95 / 432 / 193 / 189 / 16.
- Shas at tip:
  - `phase2_decisions_full.tsv.gz` 3d221b6f…
  - `phase2_residuals_still_outside_r16.tsv` d11bcae8…
  - `inventory_925.json` 10166eb1…
  - `phase2_summary_full.json` 26d6fc92…

## Changes (exact contract text)
- `residuals.tsv`:
  - R-G5-4-a / R-G5-4-b: the `count_or_identity` and `evidence` cells get the plan-44 text appended, and the `owner` cell is replaced.
  - R-G5-4-c: the `owner` cell is replaced.
  - The `blocking` cells are byte-unchanged (asserted while editing).
  - `grep "or a waiver\|confirm checker\|optional further producer"` now returns nothing.
- `docs/OVERVIEW.md`: the Status/State/Owner cells at L85, L86 and L95.
  - 63 and 64 are not on Execute's queue yet, so L86 says "Design drafts **63** / **64**".

## Not changed
- No discharge state changes. No R-G5-1/2 rows.
- OVERVIEW L108 ("61 and 62 exist only as box drafts") is other prose and outside this contract. Plan 62's Phase 3 owns the OVERVIEW pointer and refreshes it.
- Plan 44's folder collapse (open question 1) is left to a close-out; it is named, not done here.

## Progress
- [x] residuals.tsv + OVERVIEW edits
- [ ] commit/push, Flash review, close-out
