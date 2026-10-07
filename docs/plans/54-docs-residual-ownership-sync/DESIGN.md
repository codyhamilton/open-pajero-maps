---
design_id:
---

# Sync OVERVIEW + plan 35 / phase3_synthesis residual-ownership prose after plans 36–53

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Docs-only honesty. Bring live residual-ownership wording in OVERVIEW and the plan-35 / phase3_synthesis prose in line with `residuals.tsv` after plans **36–53**, so closed rows (43 / 47 / 49 and the earlier 36–42 discharges) and in-flight owners (44–46 / 48 / 50–53) plus Cody-held rows are named accurately. No false "G1 / G4 / G5 / G8 / G9 still open" framing where the gate's rows are discharged or already owned.

Oracle in force remains `4e6b0de7…` until Design accepts a successor (plan 48 may promote `88bd7852` only after R-DVD evidence — do **not** treat that sha as live in this docs sync). Heavy work: none. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief. Design grants no waivers. Assigned Execute instance: OpenCode DeepSeek Flash (Design does not start workers).

## Problem

Plan 35's synthesis correctly ended on the residual branch. Later plans discharged many rows and opened children; designs **44–53** (and **55** for R-G8-1-b-a) now own the live remainder. Stable docs still speak as if gate bands G1/G4/G5/G8/G9 were undifferentiated open sets:

**Ground (GitHub `origin/master` `094b11f`, 2026-10-07 ~18:33 AEST; host `codyh-ubuntu` offline — box shallow fetch only):**

1. **`residuals.tsv` live blocking classes**
   - **Discharged (examples already on tip):** all G1; both G4; R-G5-3 / R-G5-4 (parent) / R-G9-1 / R-G9-3 (parent) / R-G8-5 / R-G10-1; plan **43** light set; plan **47** completeness evidence set; plan **49** R-G8-2-f-a.
   - **`blocks-phase3` still open:** R-G5-1, R-G5-2, R-G5-4-a/b/c, R-G8-1-a, R-G8-1-b-a, R-G8-1-d-a, R-G8-1-f, R-G8-4-c.
   - **`maps-parity-carried`:** R-G5-5, R-G9-2, R-G9-3-a/b/c/d, R-G9-4.
2. **Ownership already designed (do not re-open):**
   | Owner | Rows |
   | --- | --- |
   | **44** (in flight on tip) | R-G5-4-a, R-G5-4-b |
   | **45** | R-G5-4-c, R-G8-1-f |
   | **46** | R-G5-1, R-G5-2, R-G8-4-c |
   | **48** (P2 landed; P3 hold for R-DVD / `88bd7852`) | R-G8-1-d-a |
   | **50–53** (DESIGNs on tip) | R-G9-2; R-G9-3-a; R-G9-3-b/c; R-G9-3-d |
   | **55** (this round's sibling draft) | R-G8-1-b-a |
   | **Cody via Design (no waiver design)** | R-G8-1-a, R-G9-4, R-G5-5 |
3. **Stale surfaces**
   - `docs/OVERVIEW.md` Phase-3 blocker paragraph still lists children R-G8-1-b-a / R-G8-1-d-a / **R-G8-2-f-a** as opened without saying **49 discharged 2-f-a**, and does not name 44–46 / 48 / 50–53 / 55 ownership.
   - `docs/plans/35-pss-and-phase3-close-synthesis.md` and `triage/phase3_synthesis/synthesis.md` still summarise G1/G4/G5/G8/G9 as undifferentiated RESIDUAL with the original open-item lists. `gates.tsv` already carries some post-close discharge notes; the prose summaries do not.
4. **Non-goals of the false framing:** claiming plan 04 Phase 3 closed; promoting `88bd7852`; drafting waivers; re-running synthesis science.

## Solution shape

One bounded docs edit set: live ownership accounting only. Historical plan-35 gate PASS/RESIDUAL *at synthesis time* stays accurate history; add explicit **post-close ownership** wording so readers do not treat discharged bands as live undifferentiated opens.

### Domain: OVERVIEW live residual ownership

- **Owns:** the OVERVIEW paragraph that points at `residuals.tsv` / plan 35's residual branch.
- **Contract:**
  1. Keep: plan 04 Phase 3 is **not closed**; residual branch; no later phase released.
  2. State that **G1 and G4 rows are discharged** (plans 36 / 39) — do not list them as live blockers.
  3. Name **live `blocks-phase3` ownership** exactly: 44 (R-G5-4-a/b), 45 (R-G5-4-c, R-G8-1-f), 46 (R-G5-1/2, R-G8-4-c), 48 (R-G8-1-d-a; P3 successor `88bd7852` not live until Design accepts after R-DVD), 55 (R-G8-1-b-a), Cody holds R-G8-1-a (budget basis, with R-G9-4).
  4. Name **closed review-condition work:** 43 light set; 47 completeness evidence; **49 discharged R-G8-2-f-a** (no longer an open child).
  5. Name **maps-parity-carried** ownership: 50–53 for R-G9-2 / R-G9-3-a..d; Cody holds R-G5-5 and R-G9-4.
  6. Oracle in force stays `4e6b0de7…` / Perth `04be2f6e…`.
- **Non-goals:** WP1 rewrite beyond residual honesty; claiming Phase 3 closed; listing draft-only box paths as landed science.

### Domain: plan 35 + phase3_synthesis post-close ownership

- **Owns:** a short **Post-close residual ownership** section (or equivalent banner) on:
  - `docs/plans/35-pss-and-phase3-close-synthesis.md`
  - `docs/plans/04-c-core-orchestration/triage/phase3_synthesis/synthesis.md`
  - and, only if still falsely listing discharged rows as live undifferentiated opens after the above, a one-line pointer on `gates.tsv` / `commands.md` (prefer prose files; do not rewrite historical PASS/RESIDUAL cells as if synthesis re-ran).
- **Contract:**
  1. Preserve the original synthesis verdict text as history.
  2. Add a dated post-close block that points to live `residuals.tsv` and the ownership table in Domain 1 (plans 36–53 / 55 / Cody holds). Explicit: **do not** say "G1/G4/G5/G8/G9 still open" without naming which child rows remain and who owns them.
  3. Note R-G8-2-f-a discharged by plan 49; R-G8-1-d-a's encoder work is plan 48 (oracle promotion separate).
- **Non-goals:** re-running gates; changing oracle sha; editing closed plan 36–53 IMPLEMENTATION science.

## Decisions

1. Plan number **54**. Docs-only. Master direct. No feature branch. No PR. No build, encode, K1, or disc work.
2. Two phases (OVERVIEW first; plan-35 / synthesis second). Refine skipped — approach known from committed `residuals.tsv` + plan records.
3. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not run 3-90.
4. Do not promote `88bd7852`. Mention only as "pending Design accept after R-DVD" if OVERVIEW names plan 48's open P3.
5. Do not draft or imply waivers for R-G8-1-a / R-G9-4 / R-G5-5.
6. Assigned instance for Execute: OpenCode DeepSeek Flash.

## Assumption ledger

### Assumption 1

- **Question:** May historical plan-35 gate RESIDUAL cells be flipped to PASS in `gates.tsv` by this plan?
- **Answer chosen:** No. Leave synthesis-time states; add post-close ownership prose. A future Phase-3 close synthesis re-evaluates gate state.
- **Rationale:** Same posture as existing `[Post-close: …]` notes on G1/G4 in `gates.tsv`; this plan extends that honesty to OVERVIEW + synthesis prose.
- **If wrong:** Cody orders a full re-synthesis under a separate design — not this plan.

### Assumption 2

- **Question:** Must OVERVIEW claim plans 44–53 / 55 are "finished"?
- **Answer chosen:** No. Name them as **owners** of the live rows (in flight or designed). Only mark discharged where `residuals.tsv` already says discharged (43 / 47 / 49 and earlier).
- **Rationale:** Tip has DESIGN folders for 50–53 and in-flight 44/48 work; claiming finished would be false.
- **If wrong:** none material — still must not claim Phase 3 closed.

### Assumption 3

- **Question:** Is R-G8-1-b-a ownership plan 55 for this sync?
- **Answer chosen:** Yes. Sibling draft `55-window-before-count-basis` owns it; OVERVIEW may say "plan 55 (Design)" once 55's DESIGN is the accepted owner, or "Design (window-before count basis)" if Execute lands 54 before 55 is numbered on master. Prefer naming **55** if both land together.
- **Rationale:** User order this round: draft 55 for the uncovered child.
- **If wrong:** leave owner as Design with the row id; do not invent a different plan number.

## Open questions

1. When should a fresh Phase-3 close synthesis re-evaluate gate PASS/RESIDUAL after 44–55 land? **Out of scope** — owned by plan 04 Phase 3 / a later synthesis design.
2. Plan 48 successor `88bd7852`: accept only after R-DVD per Design ruling in the plan-48 P3 note. **Not this plan.**

## Phases

### Phase 1 — OVERVIEW names live residual ownership

- **Outcome:** `docs/OVERVIEW.md` residual / Phase-3 blocker paragraph matches the Domain 1 contract. No claim that G1/G4 rows are live blockers. R-G8-2-f-a not listed as open. Owners 44–46 / 48 / 50–53 / 55 and Cody holds named. Phase 3 still not closed. Oracle remains `4e6b0de7…`. Grep: no live "G1… still open" / undifferentiated "G5/G8/G9 still open" claim in OVERVIEW that contradicts `residuals.tsv`.
- **Surfaces:** `docs/OVERVIEW.md`. Plan folder `docs/plans/54-docs-residual-ownership-sync/` lands with this design when Execute commits.
- **Approach:** known. **Depends on:** master tip with current `residuals.tsv` (present at `094b11f`). **Refine:** skipped.

### Phase 2 — plan 35 / synthesis post-close ownership block

- **Outcome:** `docs/plans/35-pss-and-phase3-close-synthesis.md` and `triage/phase3_synthesis/synthesis.md` carry a dated post-close residual-ownership section pointing at live `residuals.tsv` and the same owner map. Historical synthesis verdict preserved. Optional one-line related touch only if grep still frames discharged bands as live undifferentiated opens elsewhere in stable docs.
- **Surfaces:** plan 35 record; `phase3_synthesis/synthesis.md`; optionally a pointer sentence near existing post-close notes. `gates.tsv` science columns read-only unless Assumption 1 forces a pointer-only edit.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master tip used: GitHub `origin/master` **`094b11f`** (`094b11f0b0b719e4e7c7270d48f758a088be8dee`), fetched 2026-10-07 ~18:33 AEST on the box (`git fetch --depth=50 origin master`). Host `codyh-ubuntu` offline — not read.
- Sources: `triage/phase3_synthesis/{residuals,gates,synthesis}.tsv/md`; `docs/OVERVIEW.md`; plan 35 record; plan 43/47/49 close records; DESIGNs 44–53 on tip; box note `P3-ORACLE-RULING.md` for `88bd7852` hold (not promoted).
- Box draft only. No commit from Design.
