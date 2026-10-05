---
design_id:
---

# Sync OVERVIEW for plans 14–16 + post-strip 3-90 status

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Sync `docs/OVERVIEW.md` so plans 14–16 appear and `wall_s` is no longer framed as a live 3-90 strip defect after plan 16. Other 3-90 blockers stay listed as open. Docs-only honesty. Offline-runnable. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

`docs/OVERVIEW.md` on tip is stale relative to closed and in-flight plans on master:

- The WP1 "Where things stand" row lists finished work through plan **13** only. It omits plan **14** (completeness root cause — Phase 1 closed, Phase 2 refine landed, Phases 2–3 still open), closed plan **15** (SADSR SRMX STFG vs R), and closed plan **16** (K1 determinism `wall_s` strip).
- The 3-90 status paragraph still names a "determinism comparison that retains varying `wall_s`" among live Phase 3 blockers. Plan **16** Phase 1 already aligned the strip with Phase 2 / `COMPARE_EXCLUDES` (`timing` + `wall_s`), amended brief check 3, and locked the behaviour with fixture-JSON tests. That strip defect is closed; framing it as live is dishonest.
- Historic completeness attribution is still open (plan **14**), and the other independent 3-90 blockers from the `5c5823e` record remain open: repeated PSS failure, native dumps missing classification joins, truncated historical pins, unresolved 3-11 versus 3-14 oracle evidence, and an incomplete independent-review chain. Those must stay listed. Plan 04 Phase 3 is not closed.

Verified on `origin/master` at `b211112` from committed OVERVIEW / plan 14–16 records only — no disc, encode, or completeness dump required. Plans **01–05** and **07–17** occupy those numbers on master (17 is the live-extend dump_join design folder); **18** is drafted (name_anchor L0 extractor); **06** is not a work unit. This plan is **19**.

## Solution shape

One bounded docs edit: bring OVERVIEW's WP1 accounting and 3-90 status paragraph in line with plans 14–16 as they stand on master, and stop calling the closed `wall_s` strip a live defect. Touch only related honesty surfaces if a grep after the OVERVIEW edit still frames that strip as live (expected: none — ARCHITECTURE does not name `wall_s`). Do not re-run 3-90. Do not close Phase 3. Do not edit plan 14 science or plan 15/16 closed records.

### Domain: OVERVIEW plan accounting

- Owns: the WP1 row (and, if needed for the same honesty, the "Where to read next" unfinished pointer) so readers see plans 14–16.
- Contract: WP1 states that plan **14** completeness root-cause is **open** (Phase 1 evidence landed; Phases 2–3 remain), and that plans **15** and **16** are **finished** with records under `docs/plans/`. Existing wording for plans 01–05 / 07–13 / plan 04 Phase 3 blocked at 3-90 / plan 03 frozen / no plan 06 is preserved in substance. Optional: the unfinished "Where to read next" row also names plan 14's open completeness work beside plan 04's blocked Phase 3 — without claiming Phase 3 closed.
- Non-goals: no rewrite of Goal / format / how-we-work sections; no inventing plan 14 Phase 2–3 outcomes; no listing draft plan 18 as landed; no claiming plan 17 closed unless master already has a collapsed record (it does not — folder in flight).

### Domain: post-strip 3-90 status honesty

- Owns: the OVERVIEW paragraph that summarises the latest 3-90 record and Phase 3 blockers.
- Contract: `wall_s` / timing-only strip mismatch is recorded as **closed by plan 16** (strip matches Phase 2 `COMPARE_EXCLUDES`), not as a live verification defect. The remaining blockers from the `5c5823e` record stay listed as open: PSS ceiling, native classify joins, truncated pins, 3-11 vs 3-14 oracle, incomplete independent-review chain. Completeness attribution stays open and is pointed at plan **14**. Explicit: these remaining items still block Phase 3 closure; no later phase is released; plan 04 Phase 3 is not marked closed.
- Non-goals: no amend of historical 3-90 FAIL provenance rows; no change to `3-90-fresh-verify.md` (already amended by plan 16); no PSS / join / pin / oracle / review / completeness code or triage science; no Phase 3 mega-close.

## Decisions

1. Plan number is **19**. Standalone docs-honesty plan. It does not absorb plan 14 Phases 2–3, does not reseat 15/16, and does not mega-close 3-90 / Phase 3.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — WP1 + 3-90 paragraph wording against committed plan records).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Docs-only. Offline-runnable. No disc, encode, K1 rerun, or completeness dump as a gate.
6. Primary surface is `docs/OVERVIEW.md`. Touch another path only if it still frames the plan-16 strip defect as live after the OVERVIEW edit (ARCHITECTURE currently does not).
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must ARCHITECTURE or other stable docs change in the same commit?
- Answer chosen: no, unless a post-edit grep still frames `wall_s` as a live 3-90 strip defect outside OVERVIEW. Tip shows that live framing only in OVERVIEW.
- Rationale: ticket scopes OVERVIEW and "only related honesty surfaces if required".
- If wrong: a second sentence in ARCHITECTURE's Phase 3 note naming plan 16 strip closed is allowed as a related honesty touch; do not widen into module-map redesign.

### Assumption 2

- Question: how should plan 14 be framed — finished, or open?
- Answer chosen: **open**. Phase 1 closed and Phase 2 refine briefs landed; Phases 2–3 outcomes are not done. Completeness attribution remains a Phase 3 blocker under plan 14.
- Rationale: tip IMPLEMENTATION and folder state; ticket forbids mega-closing completeness / 3-90.
- If wrong: none material for this docs sync — still must not claim plan 14 Phases 2–3 closed.

### Assumption 3

- Question: may this plan claim the full 3-90 fresh-verify gate is clear because the strip landed?
- Answer chosen: no. Only the strip defect is retired from the live-blocker list. PSS, joins, pins, oracle, review chain, and completeness attribution stay open; Phase 3 stays blocked.
- Rationale: plan 16 residual risks and ticket constraints say so explicitly.
- If wrong: Cody orders a fresh 3-90 attempt under a separate design — not this plan.

### Assumption 4

- Question: should OVERVIEW mention in-flight plan 17 or draft plan 18?
- Answer chosen: no requirement. Optional silence is fine; do not present 17/18 as finished records. This plan's job is 14–16 + post-strip 3-90 honesty.
- Rationale: 17 is an open design folder; 18 is draft-only off-master.
- If wrong: a single "plans 17+ in flight / drafted separately" clause is harmless if Execute finds it clarifies WP1; do not mark them finished.

### Assumption 5

- Question: edit historical 3-90 provenance / FAIL reports that described timing-only strips?
- Answer chosen: no. Leave as accurate history of those blocked runs (same posture as plan 16).
- Rationale: honesty sync is about live OVERVIEW framing, not rewriting evidence history.
- If wrong: Cody wants a one-line "superseded by plan 16" pointer on a specific provenance block — add only that pointer, do not rewrite FAIL bodies.

## Open questions

1. After this lands, when should a fresh 3-90 verify be re-attempted against the remaining blockers? **Out of scope** — owned by plan 04 Phase 3 once those blockers have designs; not this plan's acceptance.
2. Should the unfinished "Where to read next" row name plan 14 explicitly? **Default yes** if touched for the same honesty pass; skip if WP1 alone already makes 14 visible and Execute prefers minimal diff.

## Phases

### Phase 1 — OVERVIEW names 14–16; wall_s not a live strip defect

- Outcome: `docs/OVERVIEW.md` WP1 accounting includes plan **14** as open completeness root-cause work and plans **15** / **16** as finished records. The 3-90 status paragraph no longer lists varying `wall_s` / timing-only strip mismatch as a live Phase 3 blocker; it records that strip defect as closed by plan **16**. Remaining open blockers stay listed (PSS, native classify joins, truncated pins, 3-11 vs 3-14 oracle, incomplete independent-review chain, completeness attribution via plan 14). Plan 04 Phase 3 is not marked closed. No later phase released. No plan 04 P4–6 / plan 06 drawn. 170 / 3-16 / 3-17 not reseated. Grep on stable docs shows no remaining live "retains varying `wall_s`" (or equivalent) claim outside historical 3-90 / plan-16 records. Plan folder `docs/plans/19-overview-sync-14-16/` lands with this design when Execute commits. No code, encode, disc, or K1 rerun.
- Surfaces: `docs/OVERVIEW.md` (WP1 row; 3-90 status paragraph; optional unfinished "Where to read next" pointer). Related honesty path only if grep requires it (not expected). Plan 14/15/16 records, brief 3-90, triage science, encoder/checker, and ARCHITECTURE module map are **read-only** unless Assumption 1 forces a one-line related touch.
- Approach: known
- Depends on: master tip with closed `docs/plans/15-sadsr-srmx-stfg.md`, closed `docs/plans/16-k1-determinism-wall-s.md`, and open `docs/plans/14-completeness-root-cause/` (present at `b211112`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `b211112cd2f42034f2a7c1afbe20fc2d92208260` (“docs: plan 14 Phase 2 refine briefs and units list”).
- Candidate: Maps Quality Assessor NEW #1 — Sync OVERVIEW for plans 14–16 + post-strip 3-90 status (code-quality); tip omits 14–16 and still frames wall_s as live; plan 16 Phase 1 closed the strip; offline-runnable docs-only honesty.
- Evidence cited (committed): `docs/OVERVIEW.md` WP1 finished list through 13 and 3-90 paragraph naming varying `wall_s`; `docs/plans/16-k1-determinism-wall-s.md` (strip closed; Phase 3 not closed; other blockers remain); `docs/plans/15-sadsr-srmx-stfg.md` (closed); `docs/plans/14-completeness-root-cause/` DESIGN + IMPLEMENTATION (Phase 1 closed; Phase 2 refine landed; completeness still open); `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` check 3 already requires `COMPARE_EXCLUDES` (`timing` and `wall_s`); `docs/ARCHITECTURE.md` Phase 3 blocked note (no live `wall_s` strip claim); plan **17** folder on master; plan **18** draft under `/workspace/maps-design-drafts/18-name-anchor-l0-extractor/`.
- Rejected for this design: mega-close of 3-90 / Phase 3; claiming plan 14 Phases 2–3 done; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; rewriting historical 3-90 FAIL provenance; code or K1 rerun as acceptance; absorbing plan 17/18 scope.
- Draft format followed: `/workspace/maps-design-drafts/18-name-anchor-l0-extractor/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
