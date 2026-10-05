# Reconcile signed PSS ceiling with ≤6-worker ops cap

Signed PSS ceiling **9,726,501 kB** stays absolute (no margin). Live 3-90 /
ops K1 timing, PSS, determinism, and dump gates use **≤ `-j 6`** so the gate
matches WORKFLOW. CLI default workers moved 12→6. Plan 04 Phase 3 was not
closed; the PSS bar is not claimed cleared.

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end
generation matches the original DVD in every aspect that can be verified,
every claim, assumption, and implementation aspect is verified and proven, and
there are no unexplained deviations — each has a root cause.

Reconcile signed PSS ceiling 9,726,501 with ≤6-worker ops cap (performance) —
prefer offline docs/contract/test without full-AU. Land on master. No feature
branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04
P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Why This Existed

Two standing contracts disagreed: the signed ceiling equals the historical
`-j 12` dump-off peak, while WORKFLOW caps K1/harness at ≤ `-j 6`. The 3-90
brief still gated check 2/4 at `-j 12`, so fresh-verify runs exceeded the
no-margin ceiling (~10.0M) while wall still passed. Raising the ceiling would
invent margin and leave the ops mismatch; keeping 3-90 at `-j 12` while ops
forbid it is dishonest. Bounded fix: keep the absolute ceiling; measure the
live gate at ops ≤6.

## What Was Built

**Changed:** `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md`
(checks 2–4 → `-j 6`), `docs/WORKFLOW.md` (Signed PSS ceiling vs ops K1 cap),
`docs/OVERVIEW.md` (PSS framed as contract mismatch; bar not cleared),
`docs/plans/04-c-core-orchestration/DESIGN.md` (Gates one-liner only),
`parser/tools/quantisation_roundtrip.py` (`PSS_CEILING_KB`, `OPS_MAX_WORKERS`,
CLI default), `parser/tests/test_quantisation_roundtrip.py` (constant + default
locks). Design: `f82e2a5`. Phase close: `7d615d7`.

Named constants: `PSS_CEILING_KB = 9_726_501`, `OPS_MAX_WORKERS = 6`,
`PLAN_WORKERS = 12` (unchanged). Phase 2 historical `-j 12` signature text was
not rewritten.

## Deviations

None in scope. Refine skipped. Execute implemented Phase 1 directly (docs +
small Python) rather than spawning a Flash subprocess. Assigned instance was
OpenCode DeepSeek Flash. No full-AU / 3-90 K1 trio (Assumption 1).

## Review

No `REVIEW.md`. Phase outcome recorded in the phase-1 report and
IMPLEMENTATION ledger. This is not an independent review.

## QA

Focused fixture/unit tests: **5 passed** (signed constants, CLI default ≤ ops
max, strip_compare_excludes, reports differing only in excludes, locked strip
vs timing-only). `py_compile` OK; `git diff --check` clean. No disc, encode, or
3-90 re-run as a gate.

## Residual Risks

- Live 3-90 PSS PASS still needs a future re-run at `-j 6` under the amended
  brief; other independent blockers (native classify joins, truncated pins,
  3-11 vs 3-14 oracle, review chain, plan 14 completeness) still block Phase 3.
- If a future `-j 6` trio somehow exceeds 9,726,501 kB, next step is Cody
  re-sign with margin policy or a real memory cut — not invented here.
- Function API defaults for `roundtrip*` remain `workers=12` (CLI default only
  moved to 6); callers that omit `-j` via CLI get 6.

## Follow-ups

Owned elsewhere: plan 04 Phase 3 / 3-90 re-attempt once other blockers have
designs; do not raise the ceiling in this plan's wake without Cody re-sign.
