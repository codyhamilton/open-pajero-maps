# Plan 16 Phase 1 — strip removes `timing` and `wall_s`; fixture JSON proves j1/j12 equality

## Completed

- `parser/tools/quantisation_roundtrip.py`: added a thin exported normalisation
  next to the single source of truth `COMPARE_EXCLUDES = ["timing", "wall_s"]`:
  - `strip_compare_excludes(report)` returns a copy of a K1 report dict with
    every top-level key in `COMPARE_EXCLUDES` removed; every other top-level key
    and all nested content is unchanged (shallow copy of top-level keys only).
  - `normalise_k1_report_for_compare(report)` accepts a report dict **or** a
    path to a report JSON file, strips the excludes, and returns canonical
    (`indent=2, sort_keys=True`) JSON suitable for `cmp`. This is the shared
    path the 3-90 check-3 script and the tests can both use.
  - No second hard-coded exclude pair anywhere.
- `parser/tests/test_quantisation_roundtrip.py`: `_canon` now calls
  `normalise_k1_report_for_compare`, so the existing j1/j4 byte-equality test
  exercises the shared helper. Added four pure fixture-JSON tests (dicts and
  temp JSON files only — no disc, no spool, no encode, no `@needs_c`):
  1. reports differing only in `timing` and/or `wall_s` compare equal after
     strip (both the timing-only and both-keys cases);
  2. a non-excluded field diff (`failing`, `levels`) still compares unequal;
  3. a timing-only strip leaves a `wall_s` mismatch while the locked strip does
     not — plus the JSON-file path helper.
- `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` check 3:
  equality is now "after removing every key in
  `quantisation_roundtrip.COMPARE_EXCLUDES` — `timing` **and** `wall_s` (the
  Phase 2 contract), not `timing` alone", via `strip_compare_excludes`.

## Verification

- `pytest parser/tests/test_quantisation_roundtrip.py -q -k "strip or
  differing_only or non_excluded or not_timing_only"` → **4 passed,
  94 deselected**.
- Full file `pytest parser/tests/test_quantisation_roundtrip.py -q` →
  **96 passed, 2 failed in 16.20s**. The two failures
  (`test_finalize_dump_matches_baseline_bytes`,
  `test_finalize_dump_single_row`) reproduce on unmodified HEAD (verified by
  `git stash`): they are a `cenc.K1_DUMP_DTYPE`/baseline environment mismatch
  in the caller's interpreter, not caused by this phase. `@needs_c` tests skip
  when no C compiler is present.
- `py_compile` of both changed Python files: OK.
- `git diff --check`: clean.

## Deviations, unfinished work, and known problems

No scope deviations. This phase only lands the strip, its fixture tests, and the
brief amend.

- No 3-90 re-run, no disc, no encode, no completeness work.
- Plan 04 Phase 3 is **not** marked closed. PSS / classify / pins / oracle /
  completeness blockers are untouched.
- Design 170 / units 3-16 / 3-17 are not reseated.
- Historical 3-90 FAIL records that say "removes only timing" are left as
  accurate history of those blocked runs; only the live brief check 3 and the
  shared helper are amended.
- The 2 pre-existing finalize-dump failures and the absent C-gated coverage are
  environmental, disclosed not fixed (out of scope).
- Not pushed; nothing under `output/` committed; no `.venv-rp` tracked.
