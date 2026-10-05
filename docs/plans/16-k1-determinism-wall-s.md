# K1 determinism strip: align with Phase 2 `wall_s`

The 3-90 K1 determinism strip was aligned with Phase 2 and the driver's
`COMPARE_EXCLUDES` so content-identical `-j 1` / `-j 12` reports compare
equal after removing both `timing` and top-level `wall_s`. Fixture-JSON
unit tests lock the strip. Brief check 3 was amended. Plan 04 Phase 3 was
not closed.

## Intent

User request, verbatim:

> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Align the 3-90 K1 determinism strip with Phase 2's `timing` + `wall_s` exclusion so content-identical `-j 1` / `-j 12` reports compare equal. Prove it with fixture-JSON unit tests. Land on master. No feature branch. No pull request. Runnable without a full-AU encode, disc `4ed9cd80…`, or completeness dumps.

## Why This Existed

Phase 2 had already closed K1 determinism as byte-identical reports with
`timing` and `wall_s` excluded. The driver encodes that as
`COMPARE_EXCLUDES = ["timing", "wall_s"]` in `quantisation_roundtrip.py`,
and fixture tests already canonised via those excludes. Brief
`3-90-fresh-verify.md` check 3 and the scratch `strip_timing.py` helpers
used by every 3-90 rerun still removed only `timing`, so content-identical
reports FAIL solely because walls differ (j12 ≈ 74–77 s vs j1 ≈ 447–449 s).
This was a verification-strip defect, not K1 content nondeterminism.
OVERVIEW named it among Phase 3 blockers. The work was drawable without a
disc, encode, or completeness dumps.

## What Was Built

**Changed:** `parser/tools/quantisation_roundtrip.py`,
`parser/tests/test_quantisation_roundtrip.py`, and check 3 in
`docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md`.
Design: `742d8ad`. Implementation: `d15a46f`. Phase close: `2a9f3a7`.

`strip_compare_excludes(report)` returns a shallow copy with every top-level
key in `COMPARE_EXCLUDES` removed. `normalise_k1_report_for_compare(report)`
accepts a dict or JSON path and returns canonical (`indent=2`,
`sort_keys=True`) JSON for `cmp`. One shared exclude list; no second
hard-coded pair. `_canon` now calls the shared helper. Four pure fixture-JSON
tests (no disc, spool, encode, or `@needs_c`) prove: reports differing only
in `timing` and/or `wall_s` compare equal after strip; non-excluded field
diffs remain unequal; a timing-only strip leaves a `wall_s` mismatch while
the locked strip does not; plus the JSON-file path helper. Brief check 3 now
requires equality after removing every `COMPARE_EXCLUDES` key (`timing` and
`wall_s`), via `strip_compare_excludes`.

No report-schema change, no moving `wall_s` under `timing`, no PSS / classify /
pins / oracle / completeness work, no full-disc K1 rerun, no Phase 3 close,
and no reseat of 170 / 3-16 / 3-17.

## Deviations

None in scope. Refine was skipped (approach known). Historical 3-90 FAIL
records that say "removes only timing" were left as accurate history of those
blocked runs; only the live brief check 3 and the shared helper were amended.
Two pre-existing finalize-dump failures
(`test_finalize_dump_matches_baseline_bytes`,
`test_finalize_dump_single_row`) reproduced on unmodified HEAD as a
`K1_DUMP_DTYPE`/baseline environment mismatch and were disclosed, not fixed.
Assigned instance was OpenCode DeepSeek Flash.

## Review

No `REVIEW.md` was written. Phase outcome was recorded in the phase-1 report
and IMPLEMENTATION ledger: strip, fixture tests, and brief amend met the
signed outcome with no remaining in-scope issue. This is not an independent
review.

## QA

Focused fixture strip tests: **4 passed** (94 deselected). Full
`test_quantisation_roundtrip.py`: **96 passed, 2 failed** — the two failures
are the pre-existing finalize-dump environment mismatch above, not caused by
this work. `py_compile` of both changed Python files OK; `git diff --check`
clean. No disc, encode, or 3-90 re-run was performed as a gate.

## Residual Risks

The strip is proven on synthetic fixture JSON only. A future 3-90 fresh-verify
must still clear the other independent blockers (PSS ceiling, native classify
joins, truncated pins, oracle, review chain, completeness attribution). Plan 04
Phase 3 remains open. Historical provenance rows that describe timing-only
scratch scripts remain as history of those blocked runs.

## Follow-ups

None within this strip defect. Re-attempting 3-90 after other blockers have
designs remains owned by plan 04 Phase 3. Do not silently widen
`COMPARE_EXCLUDES` if a future report field is nondeterministic — that needs
a new design.
