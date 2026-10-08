---
design_id:
---

# Sync R-G5-4-a/b (and R-G5-4-c) owner wording in residuals.tsv to plan 44's record

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Design brief (plan 60 follow-up from Execute, 2026-10-08): "R-G5-4-a/b owner wording in residuals.tsv lags plan 44." Write the exact corrected wording against plan 44's record, as a small docs item.

Docs-only. Master direct. No build, encode, K1, disc or scan work. Never relabel. Append "UPDATED by plan 44" text and do not rewrite history. No discharge here: plan 44 states R-G5-4-a/b are "not discharged", and plan 62 owns discharge. No waivers. Assigned Execute instance: OpenCode DeepSeek Flash.

## Problem

**Ground (GitHub `origin/master` `8498eec`):**

`docs/plans/04-c-core-orchestration/triage/phase3_synthesis/residuals.tsv` (columns: gate, item_id, count_or_identity, evidence, owner, blocking):

| Row | Current owner | Current evidence | Lag vs plan 44 |
| --- | --- | --- | --- |
| R-G5-4-a (line 15) | `Design (needs a stronger identity test, e.g. per-source counterfactual, or a waiver)` | plan 39 record; `p2/assignment.tsv`, `p2/allrows/shape_clause_b.json` | Plan 44 *is* the stronger identity test (owner-exclusive, Gates A+B, R=8, widen@16) and decided all 94,134 rows. "or a waiver" contradicts Cody's no-waiver bar. Plan 44 is not cited. |
| R-G5-4-b (line 16) | `Design (confirm checker; may reclassify)` | plan 39 record; same p2 files | Plan 44 Unit 2 (`inventory_925.json`) found **0 of 925** rows keep the checker with per-row proof, and all 925 joined the owner-exclusive test. "confirm checker" is superseded. Plan 44 is not cited. |
| R-G5-4-c (line 17) | `Design (optional further producer revision for divided-leaf ceiling)` | plan 45 record, `p4_ceiling/` | "optional" contradicts "carried is not closed". Plan 62 now owns it (reconciled 2026-10-08). |

Plan 44 facts (`docs/plans/44-r01-owner-exclusive-identity/IMPLEMENTATION.md`, Unit 4d–4f and "Phase 2 CLOSED"; `p5_owner_exclusive/phase2_decisions_full.tsv.gz` sha256 `3d221b6f…`, split by its `src` column, weak = a and none = b):
- **a:** 94,134 → 87,648 build:eo_bg_stitch; residual 6,486 = outside@16 3,023 + ambiguous 2,783 + skip_divided_leaf 525 + disagree_no_oe 118 + disagree_source_removed 37.
- **b:** 925 → 95 build:eo_bg_stitch; residual 830 = disagree_source_removed 432 + outside@16 193 + ambiguous 189 + skip_divided_leaf 16.
- Total 95,059. Plan 44: "Not discharged: R-G5-4-a/b remain open as residual parents."

OVERVIEW L85 and L95 still call plan 62 "a box draft only, not landed". The plan-46 children row (L86) names no plan for R-G5-1-a/b, R-G5-2-a.

Plan 44's folder `docs/plans/44-r01-owner-exclusive-identity/` was never collapsed into a record (no `44-….md` at tip). Other uncollapsed folders at tip: 47, 49, 56, 57. Close-out hygiene; named here and not fixed by Design.

## Solution shape

### Domain: residuals.tsv owner / evidence text for R-G5-4-a, -b, -c

- **Owns:** the `count_or_identity` (append only), `evidence` (append only) and `owner` cells of these three rows. `blocking` is **unchanged** on all three.
- **Contract (exact text):**

  **R-G5-4-a**
  - `count_or_identity`: append ` — UPDATED by plan 44 (owner-exclusive identity; Phase 2 Design option (c): R=8, standing widen@16; closed 2026-10-08): all 94,134 rows decided — 87,648 build:eo_bg_stitch (proven-fixed by the design-44 OE limb; not discharged by plan 44); residual 6,486 = producer_home_outside_R_cap max=16 3,023, producer_ambiguous 2,783, skip_divided_leaf 525, disagree_no_oe 118, disagree_source_removed 37`
  - `evidence`: append `; docs/plans/44-r01-owner-exclusive-identity/IMPLEMENTATION.md (Phase 2 CLOSED); docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive/phase2_decisions_full.tsv.gz (sha256 3d221b6f…), phase2_summary_full.json, phase2_residuals_still_outside_r16.tsv (sha256 d11bcae8…)`
  - `owner`: replace with `plan 44 (closed owner; 87,648 proven-fixed, not discharged) → Design: plan 62 (residual 6,486 rows; re-decide and named children)`

  **R-G5-4-b**
  - `count_or_identity`: append ` — UPDATED by plan 44 (Unit 2 checker-rationale inventory: 0 of 925 rows keep the checker with per-row proof, all 925 joined the owner-exclusive test; Phase 2 option (c)): 95 build:eo_bg_stitch (not discharged by plan 44); residual 830 = disagree_source_removed 432, producer_home_outside_R_cap max=16 193, producer_ambiguous 189, skip_divided_leaf 16`
  - `evidence`: append `; docs/plans/44-r01-owner-exclusive-identity/IMPLEMENTATION.md (Unit 2; Phase 2 CLOSED); docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive/inventory_925.json, phase2_decisions_full.tsv.gz (sha256 3d221b6f…)`
  - `owner`: replace with `plan 44 (closed owner; 0/925 keep-checker; 95 proven-fixed, not discharged) → Design: plan 62 (residual 830 rows; re-decide and named children)`

  **R-G5-4-c**
  - `owner`: replace with `plan 45 (closed) → Design: plan 62 (re-decide under the plan-46 producer; carried is not closed)`

  **All three:** `blocking` unchanged (a, b: `blocks-phase3 (Design may reclassify)`; c: its current `maps-parity-carried …` text). No count is relabelled as discharged.
- **Non-goals:** discharging any row; editing plan 39 / 44 / 45 science; touching R-G5-1/2 rows.

### Domain: OVERVIEW ownership lines

- **Owns:** `docs/OVERVIEW.md` L85, L86, L95 (Status / State cells only).
- **Contract (exact text):**
  - L85 Status: `Closed owner; 87,743 rows proven-fixed but not discharged; residual parents still \`blocks-phase3\` (7,316 rows) → Design: plan **62** (in Execute)`
  - L86 Owner cell: `Design (plan **46** children) → plans **63** (R-G5-1-a, R-G5-2-a) / **64** (R-G5-1-b)`. Status unchanged.
  - L95 State: `80/80 R01 rows \`producer_home_outside_R_cap\` at R=8 (widen@16 saturated); in plan **62**'s scope (re-decide under the plan-46 producer); carried is not closed`
- **Non-goals:** any other OVERVIEW prose; claiming 62 / 63 / 64 landed. If 63 / 64 are not yet on Execute's queue when this lands, write "Design drafts **63** / **64**".

## Decisions

1. Plan number **65** (not folded into 63 Phase 0). These rows are owned by plan 62, which is in flight ahead of 63. A 63 Phase 0 would edit them after 62 Phase 3 had rewritten them. 65 is docs-only, takes no heavy lock, and can land now in parallel with 62. It must land **before 62 Phase 3**. If 62 Phase 3 lands first, 65 becomes a verify-only check that 62's text covers the contract above.
2. One phase, one worker. Refine skipped.
3. Append-only on history cells; owner cells replaced.
4. Tip `8498eec`.

## Assumption ledger

### Assumption 1

- **Question:** May this docs item mark the 87,743 proven rows discharged?
- **Answer chosen:** **No.** Plan 44 says "not discharged". Plan 62 also adds a same-type audit (RC5) before any discharge.
- **Rationale:** plan 44 IMPLEMENTATION; plan 62 reconciled draft Problem item 5.
- **If wrong:** 62 Phase 3 discharges them anyway; no loss.

### Assumption 2

- **Question:** Is the `src` column a faithful a/b split?
- **Answer chosen:** Yes. `src=weak` totals 94,134 and `src=none` totals 925, matching the two parents exactly (and `rows_weak.tsv.gz` / `rows_none.tsv.gz` line counts 94,135 / 926 with headers).
- **Rationale:** Design Ground computation at tip.
- **If wrong:** Execute recomputes the split from `rows_weak` / `rows_none` keys and uses those numbers.

## Open questions

1. Whether plan 44's folder should get its close-out collapse (record `docs/plans/44-r01-owner-exclusive-identity.md`) in the same commit. Execute/close-out decides; this plan only names it.

## Phases

### Phase 1 — Owner wording synced to plan 44

- **Outcome:**
  - `residuals.tsv` R-G5-4-a / -b / -c `owner` cells read exactly as in the contract. R-G5-4-a/b `count_or_identity` and `evidence` cells carry the appended plan-44 text, and `blocking` is byte-unchanged.
  - OVERVIEW L85 / L86 / L95 read as in the contract.
  - `grep -n "or a waiver\|confirm checker\|optional further producer" residuals.tsv` returns nothing.
  - No row changes discharge state.
- **Surfaces:** `docs/plans/04-c-core-orchestration/triage/phase3_synthesis/residuals.tsv`; `docs/OVERVIEW.md`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

## Provenance

- Tip GitHub `origin/master` **`8498eec`**. Sources: `residuals.tsv` lines 15–17; OVERVIEW L81–95; plan 44 IMPLEMENTATION (Units 2, 4d–4f, Phase 2 CLOSED); `p5_owner_exclusive/phase2_decisions_full.tsv.gz` (`3d221b6f…`), `phase2_summary_full.json` (`26d6fc92…`), `inventory_925.json` (`10166eb1…`), `phase2_residuals_still_outside_r16.tsv` (`d11bcae8…`).
- Siblings: **60** (closed docs sync; this is its named follow-up), **62** (owner of the rows).
- Box draft only. No commit from Design.
