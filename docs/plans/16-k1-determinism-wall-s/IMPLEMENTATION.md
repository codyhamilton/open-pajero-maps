# Implementation — 16 K1 determinism wall_s strip

- Tool: OpenCode DeepSeek Flash (assigned instance for this unit)
- Session: design landed; Phase 1 executed on detached worktree open-pajero-maps-16
- Started: 2026-10-05 ~23:12 Australia/Brisbane
- Phase 1 closed: 2026-10-05 ~23:30 Australia/Brisbane
- Worker commit: d15a46f4c6c7dbd5d380a012fadc80cdbadecb48
- Closing commit carries `Workflow-Phase: 16-k1-determinism-wall-s:1`

## Phase 1

**Done** (closed).

- `parser/tools/quantisation_roundtrip.py`: added `strip_compare_excludes(report)`
  next to `COMPARE_EXCLUDES = ["timing", "wall_s"]` — returns a copy with every
  excluded top-level key removed, other content intact — and
  `normalise_k1_report_for_compare(report)` which accepts a report dict or a
  report JSON path and returns canonical (`indent=2, sort_keys=True`) JSON for
  `cmp`. One shared exclude list; no second hard-coded pair.
- `parser/tests/test_quantisation_roundtrip.py`: `_canon` now calls the shared
  helper; added four pure fixture-JSON tests (no disc / spool / encode / `@needs_c`):
  (1) reports differing only in `timing` and/or `wall_s` compare equal after
  strip; (2) non-excluded field diffs still unequal; (3) a timing-only strip
  leaves a `wall_s` mismatch while the locked strip does not; plus the
  JSON-file path helper.
- `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` check 3:
  equality is now after removing every `COMPARE_EXCLUDES` key (`timing` **and**
  `wall_s`, the Phase 2 contract), not `timing` alone.
- Tests: `pytest parser/tests/test_quantisation_roundtrip.py -q -k "strip or
  differing_only or non_excluded or not_timing_only"` → **4 passed**. Full file:
  **96 passed, 2 failed** — both failures
  (`test_finalize_dump_matches_baseline_bytes`, `test_finalize_dump_single_row`)
  reproduce on unmodified HEAD and are a `K1_DUMP_DTYPE`/baseline environment
  mismatch, not this phase. C-gated tests (`@needs_c`) skip when no C compiler.

No disc / encode. Plan 04 Phase 3 not marked closed. PSS / classify / pins /
oracle / completeness untouched. 170 / 3-16 / 3-17 not reseated. Not pushed.

See `reports/phase-1.md`.
