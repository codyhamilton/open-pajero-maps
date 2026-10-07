# Plan 60 — IMPLEMENTATION (docs oracle + residual ownership sync)

Status: in progress (checkpoint). Base: `origin/master` `b5c9ff9` (plan 45 close-out). Worktree
`/home/codyh/workspace/open-pajero-maps-60` (separate from plan 46's checkout). Docs-only; no heavy work.

## Ground truth vs DESIGN draft (draft grounded at `10a976a`, stale)

| Draft says | Live tip `b5c9ff9` | Source |
| --- | --- | --- |
| AU oracle in force `aeae426c…` (plan 50) | **`0c22b266…`** (plan 53 successor over `aeae426c…` over `88bd7852…`) | plan 53 record; `oracle_chain.json` / `pin_contract.json` `disc_in_force_sha256` |
| Perth `04be2f6e…` | **`5b86d33e…`** (plan 53; `04be2f6e…` historical) | plan 53 record |
| 52–53 in flight on Flash | **52 closed** (R-G9-3-b/c proven-cause; piece-count + L8 selection volume residuals), **53 closed** (dv_assign lon-wrap fix; R-G9-3-d discharged; R-G9-3-d-rem 128 carried) | records 52, 53 |
| 45 designed, next | **45 closed**: R-G8-1-f discharged; R-G5-4-c reclassified **maps-parity-carried** (80/80 `producer_home_outside_R_cap` at R=8; widen@16 saturated) | record 45; residuals.tsv |
| 46 designed | **46 in progress** (Execute; live `blocks-phase3` owner of R-G5-1/2, R-G8-4-c). No gate numbers stated as landed fact | parent |
| 62 owns still-outside@16 | 61 / 62 are **box drafts only, not landed**. Parent steering: R-G5-4-c 80/80 still-outside@16 is plan 62's scope | parent 09:24 |

Cody open (no waivers, no drafts): R-G8-1-a, R-G9-4, R-G5-5; F6 / kind-order (plan 51); L8 selection expand (plan 52).

## Decisions taken in Execute

1. `residuals.tsv` **not edited**. The owner/blocking columns already match the live state (R-G9-2 discharged-plan-50; R-G8-1-f discharged-plan-45; R-G5-4-c carried; R-G9-3-* per 51–53). The rows plan 46 will rewrite (R-G5-1, R-G5-2, R-G8-4-c) stay untouched so that 46 rebases cleanly. OVERVIEW names plan 46 as the live owner.
2. The historical plan-35 / plan-54 wording is preserved. A new dated block "plan 60 — 2026-10-08" is appended after the plan-54 block in plan 35 and synthesis.md.
3. "Carried is not closed for parity" is stated explicitly in OVERVIEW and in the post-close blocks.

## Consistency check vs residuals.tsv (owner/blocking columns, tip b5c9ff9)

R-G9-2 discharged-plan-50; R-G8-1-f discharged-plan-45; R-G9-3-d discharged-plan-53 (rem carried); R-G5-4-c maps-parity-carried (plan 45); R-G9-3-a/b/c maps-parity-carried (51/52, volume to Cody where stated); R-G9-3-d-rem carried; R-G5-5 / R-G9-4 carried (Cody); R-G5-1/2, R-G8-4-c, R-G5-4-a/b, R-G8-1-a blocks-phase3. OVERVIEW and both dated blocks match. No TSV edit needed.

## Progress
- [x] worktree + DESIGN copied
- [x] OVERVIEW: WP1 oracle cell (0c22b266 / Perth 5b86d33e; 88bd7852 and aeae426c now historical); ownership section (discharged 45/50/53 added; live blocks-phase3 = 44 closed, 46 in progress, Cody R-G8-1-a; carried table with the 'carried is not closed for parity' line; Cody-open list; 61/62 box-only); pin-contract line; stale '341 to implement' wording (plan 50)
- [x] plan 35 + synthesis.md: appended dated block 'plan 60 — 2026-10-08' (plan-54 block untouched)
- [ ] commit/push, Flash review, close-out
