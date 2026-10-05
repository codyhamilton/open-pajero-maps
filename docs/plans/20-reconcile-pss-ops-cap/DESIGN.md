---
design_id:
---

# Reconcile signed PSS ceiling with ≤6-worker ops cap

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Reconcile signed PSS ceiling 9,726,501 with ≤6-worker ops cap (performance) — measured PSS ~10.0M at 3-90. Offline-runnable if possible (docs/contract/test without full-AU). If it requires a full 3-90 K1 re-run as gate, say so in Assumptions and still design a bounded fix path. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

Two standing contracts disagree, and 3-90 keeps failing the memory bar because of that disagreement:

- **Signed PSS ceiling** (plan 04 Phase 2 close, Cody via Bot Team Manager): **9,726,501 kB**. That number is the measured peak of three dump-off K1 runs at **`-j 12`** on G (peaks 8,736,916 / 8,982,284 / 9,726,501). DESIGN named no margin; none was invented. The ceiling equals the historical `-j 12` peak.
- **Ops worker cap** (`docs/WORKFLOW.md` Heavy jobs; plan 05; Phase 3 briefs): cbuild/make ≤ `-j4`, **K1/harness ≤ `-j6`**, one heavy job under `flock output/.heavy.lock`. This cap is the live operational contract for host memory pressure.
- **3-90 brief** still requires check 2 timing/PSS at **`-j 12`** against 9,726,501 kB, and check 4 dump at `-j 12`. Repeated fresh-verify runs at that worker count exceed the no-margin ceiling: max **10,008,455** then **10,020,516** kB (~10.0M) while wall still passes (median ~74 s ≤ 120 s). Earlier ledger runs at `-j 12` sometimes stayed under (e.s. max 9,690,973).
- Summed per-process PSS scales with pool size. Phase 2 `-j 1` peak was **6,646,774 kB**. A `-j 6` dump-off wall (~82 s) is already on record and still under the 120 s bar; no committed full-disc `-j 6` PSS peak sits next to the signed ceiling. Running the gate above the ops cap against a peak-equals-ceiling signature is why check 2 flaps.

Raising the ceiling to cover ~10.02M would invent margin and leave the ops-cap conflict in place. Leaving 3-90 at `-j 12` while WORKFLOW forbids it is dishonest. The bounded fix is to **split and align**: keep the signed absolute ceiling; measure the live Phase 3 / ops gate at ≤6 workers so the gate and the cap agree.

Verified on `origin/master` at `00cabd8` from committed OVERVIEW / WORKFLOW / plan 04 IMPLEMENTATION + 3-90 brief / quantisation_roundtrip / plan 05 records — no disc or K1 rerun required for the design. Plans **01–05** and **07–18** occupy those numbers on master; plan **19** OVERVIEW sync is closed on master; **06** is not a work unit. This plan is **20**.

## Solution shape

One bounded reconciliation: keep Cody's signed **9,726,501 kB** ceiling unchanged; move the live K1 timing/PSS (and related heavy 3-90 K1 invocations) to the ops-cap worker count **`-j 6`**; document the Phase 2 signature as a historical `-j 12` measurement that remains the absolute ceiling, not a license to run above ops. Prefer docs/brief/contract + named constants + unit tests. Do **not** re-sign or invent margin. Do **not** claim 3-90 PSS PASS or Phase 3 closed in this plan.

### Domain: live gate vs signed ceiling

- Owns: the Phase 3 / 3-90 memory bar as operators run it, and how it relates to the Phase 2 signature.
- Contract: (1) Absolute ceiling stays **9,726,501 kB** (signed; no margin). (2) Live timing/PSS gate (3-90 check 2) runs dump-off K1 at **`-j 6`** (ops cap), median wall ≤ 120 s, max summed PSS ≤ 9,726,501 kB. (3) Determinism check compares `-j 1` to a `-j 6` report after `COMPARE_EXCLUDES` (`timing` + `wall_s`). (4) Dump/classify heavy K1 in check 4 also uses **`-j 6`** (bytes are worker-count-independent; ops cap applies). (5) Phase 2 IMPLEMENTATION / DESIGN historical wording that measured the signature at `-j 12` stays accurate history — not rewritten as if Phase 2 ran at `-j 6`.
- Non-goals: no raise of the ceiling; no full-AU encode; no Phase 3 close trailer; no change to PLAN_WORKERS band planning (stays 12 — plans bands independent of pool size); no PSS sampler algorithm change; no reseat of other 3-90 blockers (joins, pins, oracle, review, completeness).

### Domain: ops docs and tool defaults

- Owns: WORKFLOW / OVERVIEW honesty that the signed ceiling is enforced under the ≤6-worker ops cap, and optional CLI default alignment.
- Contract: WORKFLOW Heavy-jobs section states explicitly that plan04's signed PSS ceiling **9,726,501 kB** applies to K1 runs at the ops cap (**≤ `-j 6`**), and that running above the cap can exceed a no-margin peak. OVERVIEW's live 3-90 blocker list keeps PSS as open but frames the defect as **contract mismatch (ceiling signed at `-j 12` peak; ops/gate must use ≤6)** rather than an unexplained memory blow-up — without claiming the bar is cleared. Optional same-phase: `quantisation_roundtrip` CLI default `--workers` / `-j` moves **12 → 6**; named module constants for ceiling and ops max workers; fixture/unit tests lock those constants and that default ≤ ops max. `PLAN_WORKERS` remains 12.
- Non-goals: no machine-wide cgroup memory cap; no change to plan 05 RSS/`memory.peak` gates; no ARCHITECTURE module-map redesign; no absorbing draft plan 19's OVERVIEW 14–16 sync beyond the PSS sentence if touched.

## Decisions

1. Plan number is **20**. Standalone contract-honesty plan. It amends the 3-90 brief and related ops surfaces; it is not a mega Phase-3-close and does not absorb draft 19.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — split contract + enforce ops `-j 6`; raise-ceiling rejected).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Prefer offline docs/brief/constants/unit over full-AU. Clearing the live 3-90 PSS FAIL is a **later** re-run under the amended brief (Assumption 1) — not this plan's acceptance gate.
6. Reject raising the ceiling to ~10.02M without Cody re-sign and without fixing the ops mismatch.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must this plan's acceptance include a full-AU / 3-90 K1 trio that proves max PSS at `-j 6` ≤ 9,726,501?
- Answer chosen: **no**. This plan lands the reconciliation (brief + docs + constants/tests). Proving check 2 PASS on the live disc is a **future 3-90 re-run** under the amended brief (and still blocked by the other independent 3-90 failures until those have their own designs).
- Rationale: ticket prefers offline docs/contract/test; wall at `-j 6` already met historically (~82 s); PSS at `-j 1` was 6.65M and summed PSS falls with fewer workers — enough to design the contract without inventing a new peak. Ticket asks to say so if a full re-run is needed to clear the gate.
- If wrong: Cody orders an evidence-only `-j 6` K1 trio under heavy lock as this plan's gate — still not a Phase 3 mega-close; still no ceiling raise.

### Assumption 2

- Question: raise the signed ceiling to cover measured ~10.0M at `-j 12`, or keep 9,726,501 and move the gate to `-j 6`?
- Answer chosen: **keep 9,726,501**; enforce ops `-j 6` on the live gate. Split: Phase 2 signature remains the absolute ceiling (historical `-j 12` peak); ops/3-90 measure under the cap.
- Rationale: no-margin signature was deliberate; ops cap is standing WORKFLOW law; raising alone leaves `-j 12` vs ≤6 dishonest.
- If wrong: Cody re-signs a new ceiling (with stated worker count and margin policy) under a separate design — do not invent margin here.

### Assumption 3

- Question: change the CLI default `-j` from 12 to 6 in the same phase?
- Answer chosen: **yes, preferred** — default should match ops so accidental `-j 12` dumps are not the easy path. Band plan `PLAN_WORKERS = 12` stays. Tests that pass explicit `-j` are unaffected.
- Rationale: default 12 is how 3-90 and muscle memory keep violating the cap.
- If wrong: Execute may leave CLI default 12 and only amend brief/docs if a fixture regresses; must still document that ops max is 6.

### Assumption 4

- Question: rewrite plan 04 DESIGN Gates / Phase 2 outcome lines that say `-j 12` for the C checker?
- Answer chosen: **no historical rewrite**. Add a short Phase 3 / gates note (or 3-90 brief + WORKFLOW only) that the **live** memory bar is enforced at ops ≤ `-j 6` against the signed 9,726,501 kB ceiling. Phase 2 close text stays as the measurement provenance.
- Rationale: Phase 2 outcome was true at `-j 12`; lying about history is worse than a split contract.
- If wrong: a one-line Gates amendment naming the split is allowed; do not renumber Phase 2 figures.

### Assumption 5

- Question: does aligning the gate clear other 3-90 blockers (native classify joins, truncated pins, 3-11 vs 3-14 oracle, review chain, completeness / plan 14)?
- Answer chosen: **no**. Only the PSS/worker-cap contradiction is in scope. Those blockers stay open; Phase 3 stays blocked.
- Rationale: ticket and plan 16 residual risks list them as independent.
- If wrong: none — still must not mega-close Phase 3 in this plan.

## Open questions

1. After this lands, when should a fresh 3-90 verify be re-attempted at `-j 6` against the remaining blockers? **Out of scope** — owned by plan 04 Phase 3 once other blockers have designs; not this plan's acceptance.
2. If a future `-j 6` trio somehow still exceeds 9,726,501 kB, is the next step a Cody re-sign with margin, or a real memory cut? **Out of scope** until measured; do not pre-raise.

## Phases

### Phase 1 — Gate and ops agree: ceiling held, live K1 ≤ `-j 6`

- Outcome: `briefs/3-90-fresh-verify.md` check 2 requires three dump-off K1 runs at **`-j 6`**, median wall ≤ 120 s, max PSS ≤ **9,726,501 kB**; check 3 determinism compares `-j 1` to a `-j 6` report after `COMPARE_EXCLUDES`; check 4 dump/classify K1 uses **`-j 6`**. Signed ceiling value is unchanged. WORKFLOW (and OVERVIEW's live PSS framing if touched) state that the signed ceiling is enforced under the ops K1 cap (≤ `-j 6`), and that `-j 12` exceedances against a no-margin `-j 12` peak are expected under the old mismatched gate — not an unexplained blow-up and not a cleared bar. Optional same commit: CLI default workers 12→6; named constants for ceiling and ops max; unit tests lock them. Phase 2 historical signature text is not rewritten. No ceiling raise. No Phase 3 close. No plan 04 P4–6 / plan 06. 170 / 3-16 / 3-17 not reseated. No full-AU / disc / K1 trio required for this plan's acceptance. Plan folder `docs/plans/20-reconcile-pss-ops-cap/` lands with this design when Execute commits.
- Surfaces: `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` (checks 2–4 worker counts); `docs/WORKFLOW.md` (Heavy jobs / PSS ceiling vs ops cap); optional `docs/OVERVIEW.md` (PSS blocker sentence only); optional one-line note on plan 04 DESIGN Gates domain without rewriting Phase 2 numbers; `parser/tools/quantisation_roundtrip.py` (CLI default / named constants if Assumption 3 holds); `parser/tests/test_quantisation_roundtrip.py` (constant + default contract). PSS sampler, band `PLAN_WORKERS`, dump layout, triage, encode, and other 3-90 blocker surfaces are **read-only**.
- Approach: known
- Depends on: master tip with signed ceiling recorded in plan 04 IMPLEMENTATION, ops cap in WORKFLOW, and 3-90 brief still at `-j 12` (present at `00cabd8`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `00cabd82f14878146b40129f8cda59333fdbfc73` (“docs: add plan 18 name_anchor L0 extractor design”).
- Candidate: Maps Quality Assessor NEW #2 — Reconcile signed PSS ceiling 9,726,501 with ≤6-worker ops cap (performance); measured PSS ~10.0M at 3-90; prefer offline docs/contract/test.
- Evidence cited (committed): plan 04 IMPLEMENTATION Phase 2 close — signed ceiling **9,726,501 kB** from `-j 12` peaks 8,736,916 / 8,982,284 / 9,726,501; `-j 1` PSS 6,646,774; 3-90 FAIL rows max **10,008,455** / **10,020,516** at `-j 12` with wall still ≤120 s; `briefs/3-90-fresh-verify.md` check 2 still at `-j 12`; `docs/WORKFLOW.md` K1/harness ≤ `-j6`; Phase 3 briefs (e.g. 3-11, 3-13, 3-14, 3-16, 3-17) same cap; `quantisation_roundtrip.py` CLI default `-j 12`, `PLAN_WORKERS = 12`, PSS sampler via `smaps_rollup`; plan 05 / ARCHITECTURE note that plan04 PSS gates are a separate contract; plan 16 residual: PSS ceiling still an independent Phase 3 blocker.
- Rejected for this design: raising ceiling to ~10.02M without Cody re-sign; keeping 3-90 at `-j 12` while ops forbid it; claiming PSS PASS / Phase 3 closed without a later re-run; rewriting Phase 2 history as `-j 6`; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; absorbing draft 19 overview sync; full-AU as this plan's acceptance.
- Draft format followed: `/workspace/maps-design-drafts/19-overview-sync-14-16/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–18; `/workspace/maps-design-drafts/` has 17–19 → this draft is **20**.
