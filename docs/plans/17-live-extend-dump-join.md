# Switch live scratch-3-12 extend to dump_join

Live `output/scratch-3-12/extend.py` is a thin wrapper over the tracked residual
`parser/tools/dump_join.py` adapter (same `DEFAULT_*` paths). Plan-05 fixture
SHA gates and sibling pytest suite passed. The plan 05 live whole-file follow-up
is closed. No full-AU encode, disc rebuild, or completeness dumps.

## Intent

From the signed design, verbatim:

> Switch live `output/scratch-3-12/extend.py` to the tracked `parser/tools/dump_join.py` residual adapter (thin wrapper, same pattern as plan 05's 3-07 scratch wrapper). Prove with plan-05 fixture SHA gates. Land on master. No feature branch. No pull request. No full-AU encode. Runnable without Cody disc rebuild or plan 14 completeness dumps.

## Why This Existed

Plan 05 landed tracked `dump_join.py` (windowed pread/pwrite, write-behind) and
proved byte identity against the vendored baseline, but deliberately left the
live scratch entry on the whole-file `copyfile` + whole-destination memmap
script until plan04 unit 3-13 accepted. 3-13 is on master
(ACCEPT-WITH-CONDITIONS; Conditions A–C closed). Plan 05 close-out still listed
the switch as the first follow-up; residual-risk text still warned that
re-running the live whole-file script dirties multi-GiB cache. The tracked
adapter was already the durable path; the live script was still the unsafe
operator entry.

## What Was Built

**Changed (tracked):** `docs/plans/05-heavy-job-memory.md` (follow-up / residual
risk closed), `docs/provenance.md` (scratch-3-12 Dump extension), this plan's
IMPLEMENTATION / phase-1 report (collapsed here). **On disk (gitignored):**
`output/scratch-3-12/extend.py` thin wrapper in the main checkout and the
plan-17 worktree. Design: `9af81fa`. Phase close: `a6ebed7`.

The wrapper puts `parser/tools` on `sys.path`, imports `dump_join`, and
`raise SystemExit(dump_join.main())` with no arguments so residual defaults
apply (`DEFAULT_SRC` `output/scratch-3-11/dump_new_ext`, side
`output/scratch-3-12`, assign `output/scratch-3-11/classify_new`, dst
`output/scratch-3-12/dump_ext`, counts `output/scratch-3-12/joined_counts.json`).
Durable CLI: `.venv-rp/bin/python parser/tools/dump_join.py` (mode `residual`,
defaults). Semantics unchanged (byte146 `residual_crossing_verified`; other
bytes unchanged; row size 152). Vendored
`parser/tests/fixtures/dump_join_baseline/extend.py` SHA `1b13b844…` untouched.

No change to `dump_join` join/sort/cast/window contracts, no reseat of 170 /
3-16 / 3-17, no plan 04 Phase 3 close, no full residual re-extend as a gate.

## Deviations

Assumption 3 held: `output/scratch-3-12/` was absent on the Execute host, so
only the minimal gitignored path for the wrapper file was created. No dumps,
side tables, or classify outputs were regenerated; fixture SHA / pytest remain
the semantic proof. Flash's first attempt was auto-rejected for writing the
main-checkout twin outside the worktree; the executor wrote both wrapper
copies, then Flash completed docs, gates, and the phase commit inside the
worktree. Assigned instance: OpenCode DeepSeek Flash. Refine skipped.

## Review

No independent `REVIEW.md`. Phase outcome is in the phase-1 report and this
record: wrapper, fixture SHA, pytest, and plan-05 follow-up close met the
signed outcome with no remaining in-scope issue.

## QA

- `(cd parser/tests/fixtures/dump_join_baseline && sha256sum -c SHA256SUMS)` →
  extend / study / witness OK.
- `pytest parser/tests/test_dump_join_memory.py
  parser/tests/test_extend_s02_memory.py parser/tests/test_k1_triage.py
  parser/tests/test_perf_inventory.py -q` → **48 passed**.
- Wrapper AST parse + `dump_join.DEFAULT_SRC` / `DEFAULT_DST` print OK.
- Re-verified after phase push. No disc / full-AU / completeness dump.

## Residual Risks

Whole-file OOM risk remains only if the vendored baseline under
`parser/tests/fixtures/dump_join_baseline/` is re-run live outside the isolated
replay harness. A full residual re-extend on Cody's host is out of scope
(evidence-only under heavy lock if ordered). Plan 04 Phase 3 stays open.

## Follow-ups

None within this entry-point harden. Optional evidence-only residual re-extend
under `output/.heavy.lock` if Cody orders it — not absorbed as algorithm work.
