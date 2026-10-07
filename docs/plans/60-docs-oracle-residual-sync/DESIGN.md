---
design_id:
---

# Sync OVERVIEW + residuals ownership after plans 50–59 (oracle aeae426c)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Docs-only honesty follow-on to plan **54**. Bring live residual-ownership wording and oracle prose in line with tip after plans **50–59**: live AU oracle is **`aeae426c…`** (plan 50 successor over `88bd7852…`); R-G9-2 discharged; R-G9-3-a emission proven-cause (plan 51) with volume still Cody/F6; plans 54–55 / 56–59 closed; Execute draining **52–53** then designed **45–46**. No false "plan 50 still owns R-G9-2" or "oracle still 88bd7852 only" framing.

Heavy work: none. Master direct. Never relabel. No plan 04 P4–6. No 3-90. No waivers. No F6 / kind-order product drafts (Cody open). Assigned Execute instance: OpenCode DeepSeek Flash (Design does not start workers).

## Problem

Plan **54** synced ownership through the 44–53 / 55 design map while oracle promotion and later closes were still in flight. Tip now (GitHub `origin/master` **`10a976a`**, 2026-10-08 ~03:10 AEST) has moved:

1. **Oracle chain.** Plan **48** accepted `88bd7852…`; plan **50** promoted successor **`aeae426c…`** (341/341 overlay; confined diff vs `88bd7852`). OVERVIEW / plan-35 post-close prose may still speak as if `88bd7852` were the sole live AU oracle, or omit `aeae426c`.
2. **Row state vs ownership tables.**
   - **R-G9-2** — `residuals.tsv` **discharged-plan-50**; ownership tables must not list plan 50 as a live Design owner.
   - **R-G9-3-a** — plan **51** closed emission proven-cause (land-local catch-all / F6); volume residual + F6 / kind-order questions are **Cody open** — name that honestly; do **not** draft F6 or kind-order flip packages here.
   - **R-G8-1-b-a** — plan **55** discharged (explained-dual-basis).
   - **R-G8-1-d-a** — plan **48** discharged; successor accepted.
   - Memory band **56–59** closed as ops residency — **not** residual-row owners (already stated; keep).
3. **Execute queue honesty.** Plans **52–53** in flight on Flash; next designed **blocks-phase3** drain is **45** then **46** (already drafted — do not re-open). Cody holds **R-G8-1-a / R-G9-4 / R-G5-5** unchanged — no waiver text.
4. **Non-goals of stale framing:** claiming plan 04 Phase 3 closed; inventing new residual owners; promoting F6/kind-order; reseating science.

## Solution shape

One bounded docs edit set: live ownership + oracle accounting only. Preserve historical plan-35 / plan-54 synthesis-time wording; add or refresh a dated **post-close** block.

### Domain: OVERVIEW live oracle + residual ownership

- **Owns:** OVERVIEW paragraphs that name the AU oracle in force and the residual ownership tables.
- **Contract:**
  1. State AU oracle in force = **`aeae426c…`** (plan 50); Perth stays `04be2f6e…`; `88bd7852…` / `4e6b0de7…` remain historical protected.
  2. Keep: plan 04 Phase 3 **not** closed; residual branch; no later phase released.
  3. Refresh **live `blocks-phase3` ownership:** **45** (R-G5-4-c, R-G8-1-f); **46** (R-G5-1/2, R-G8-4-c); plan **44** closed owner with residual parents still open (still-outside@16 / named children — plan **62**); Cody hold **R-G8-1-a**.
  4. Refresh **`maps-parity-carried`:** **52** (R-G9-3-b/c), **53** (R-G9-3-d) as Execute/Design owners until closed; **R-G9-3-a** volume → Cody (F6 / kind-order); **R-G5-5**, **R-G9-4** → Cody; **R-G9-2** discharged (not a live owner row).
  5. Name closed: 48, 49, 50, 51 (emission), 54, 55, 56–59 (ops).
- **Non-goals:** WP1 rewrite beyond honesty; claiming Phase 3 closed; listing box-only draft paths as landed science.

### Domain: residuals.tsv / plan-35 / synthesis post-close pointer

- **Owns:** consistency check that `residuals.tsv` blocking/owner columns match OVERVIEW; short post-close note on plan-35 / `phase3_synthesis/synthesis.md` if still naming discharged 50/51 as undifferentiated opens or wrong oracle.
- **Contract:**
  1. Do **not** flip historical gate PASS/RESIDUAL cells as if synthesis re-ran.
  2. If any prose still says oracle `4e6b0de7` or sole live `88bd7852` without `aeae426c`, fix with a dated pointer.
  3. Explicit: R-G9-3-a emission closed by 51; volume open on Cody — no Design waiver.
- **Non-goals:** editing closed IMPLEMENTATION science; changing oracle bytes.

## Decisions

1. Plan number **60**. Docs-only. Master direct. No feature branch. No PR. No build / encode / K1 / disc work.
2. Two phases: OVERVIEW + oracle first; residuals / synthesis consistency second. Refine skipped.
3. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not run 3-90.
4. Do **not** draft F6 catchall change or kind-order flip (Cody open from plan 51).
5. Do not draft waivers for R-G8-1-a / R-G9-4 / R-G5-5.
6. Assigned instance: OpenCode DeepSeek Flash.
7. Tip ground: `10a976a` (plan 51 close-out). Oracle ground: `aeae426c…`.

## Assumption ledger

### Assumption 1

- **Question:** May this plan re-label R-G9-3-a as discharged because emission RC is proven?
- **Answer chosen:** **No.** Emission is proven-cause; volume residual stays `maps-parity-carried` until Cody rules on F6 / kind-order.
- **Rationale:** Plan 51 close + Design ruling; residuals text.
- **If wrong:** Cody accepts volume under current policy as closed residual — still a Cody/Docs note, not this plan inventing product policy.

### Assumption 2

- **Question:** Must OVERVIEW claim 52–53 / 45–46 finished?
- **Answer chosen:** **No.** Name owners and in-flight vs designed accurately.
- **Rationale:** Tip has 51 closed; 52 starting; 45–46 still Design-on-tip until Execute lands.
- **If wrong:** none material.

### Assumption 3

- **Question:** Is plan 62 required before this docs sync can name still-outside@16?
- **Answer chosen:** OVERVIEW may say "plan 44 closed; residual parents / still-outside@16 owned by Design (plan **62**)" once 62's DESIGN exists as sibling — prefer naming **62**.
- **Rationale:** Same posture as plan 54 naming 55.
- **If wrong:** leave "Design (still-outside@16)" without a number.

## Open questions

1. Whether any non-OVERVIEW consumer still hard-codes `88bd7852` as live (Execute greps; fix only committed prose / pins that claim "oracle in force").
2. Cody F6 / kind-order — out of scope (do not answer here).

## Phases

### Phase 1: OVERVIEW oracle + ownership tables

- **Outcome:** OVERVIEW names `aeae426c…` as live AU oracle; ownership tables match tip discharges (50/51/55/48) and Cody holds; Phase 3 still not closed.
- **Surfaces:** `docs/OVERVIEW.md`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: residuals / synthesis consistency

- **Outcome:** `residuals.tsv` owners/blocking consistent with OVERVIEW; plan-35 / synthesis post-close pointer updated if stale; no gate-cell rewrite-as-re-synthesis.
- **Surfaces:** `residuals.tsv` (owner/status text only if needed); `docs/plans/35-…` / `phase3_synthesis/synthesis.md` post-close block.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Tip: GitHub `origin/master` **`10a976a68e3a85a3f856554fa97647c8b2026da5`** (plan 51 close-out).
- Oracle: plan 50 successor **`aeae426c…`**; prior `88bd7852…` (plan 48).
- Sources: tip `docs/OVERVIEW.md`; `residuals.tsv`; plan 50/51/54/55 close messages; box drafts 52–53, 60–62.
- Sibling: **61** (RSS unknowns), **62** (still-outside@16).
- Box draft only. No commit from Design.
