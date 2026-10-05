# Sync OVERVIEW for plans 14–16 + post-strip 3-90 status

Docs-only honesty pass landed on master. `docs/OVERVIEW.md` now accounts for plans 14–16 and stops framing the plan-16 `wall_s` strip as a live 3-90 defect. Other 3-90 blockers and plan 04 Phase 3 stay open.

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Sync `docs/OVERVIEW.md` so plans 14–16 appear and `wall_s` is no longer framed as a live 3-90 strip defect after plan 16. Other 3-90 blockers stay listed as open. Docs-only honesty. Offline-runnable. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Why This Existed

OVERVIEW's WP1 row stopped at plan 13 and the 3-90 paragraph still listed varying `wall_s` among live Phase 3 blockers after plan 16 had already closed that strip defect.

## What Was Built

**Changed:** `docs/OVERVIEW.md` only.

- WP1 finished list includes plans **15** and **16**; plan **14** named as **open** (Phase 1 evidence landed; Phases 2–3 remain).
- 3-90 status paragraph records the `wall_s` / timing-only strip as closed by plan **16** (`COMPARE_EXCLUDES`: `timing` + `wall_s`) and keeps PSS ceiling, native classify joins, truncated pins, 3-11 vs 3-14 oracle, incomplete independent-review chain, and completeness attribution (via plan 14) as open blockers. Explicit: Phase 3 not closed.
- Unfinished "Where to read next" row names plan 14 beside blocked plan 04 Phase 3.

## Deviations

None.

## Review

Terminal docs-only review deferred as pipeline-style on master push (Maps lands straight to master). Outcome verified by diff + grep against Phase 1 contract.

## QA

Not applicable (docs-only; no deploy).

## Residual Risks

Readers who only skim historical 3-90 FAIL provenance may still see timing-only strip language; those rows were left as accurate history of blocked runs.

## Follow-ups

- Fresh 3-90 verify remains owned by plan 04 Phase 3 once remaining blockers have designs — not this plan.
- Plan 14 Phases 2–3 still open for completeness attribution.
