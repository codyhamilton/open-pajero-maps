# Independent review: plan-16 / 3-90 check-3 strip

**Reviewer:** Open Pajero Maps Execute (plan 27 Phase 1) — fresh verification pass, not a copy of plan 16's Review section.
**Tip reviewed:** `a03c9bc2ec66399cd5634bdbb748e79a7f36a55f` (plan 27 DESIGN on `origin/master`; strip code ancestry includes plan 16 `d15a46f` / `2a9f3a7`).
**Method:** tip code + four fixture strip tests under pytest + live brief check 3 + light helper recompute. No disc mount, no 3-90 re-run, no full-AU encode, no heavy lock. Historical timing-only 3-90 FAIL rows are **not** treated as current strip defects.

## Stated outcome (plan 16 / brief check 3)

Reports that differ only in keys in `COMPARE_EXCLUDES` (`timing`, `wall_s`) compare equal after `strip_compare_excludes` / `normalise_k1_report_for_compare`; non-excluded diffs remain unequal; a timing-only strip leaves a `wall_s` mismatch; brief check 3 requires the shared helper, not timing alone.

## Evidence walked

| Surface | Tip cite |
| --- | --- |
| `COMPARE_EXCLUDES` | `parser/tools/quantisation_roundtrip.py:1250` = `["timing", "wall_s"]` |
| `strip_compare_excludes` | `parser/tools/quantisation_roundtrip.py:1253–1258` — shallow copy removing every top-level key in `COMPARE_EXCLUDES` |
| `normalise_k1_report_for_compare` | `parser/tools/quantisation_roundtrip.py:1261–1267` — canonical JSON of stripped report (dict or path) |
| Four fixture strip tests | `parser/tests/test_quantisation_roundtrip.py:451–518` |
| Live brief check 3 | `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md:31` — requires strip of `timing` **and** `wall_s` via `strip_compare_excludes` |
| Plan 16 self-Review | `docs/plans/16-k1-determinism-wall-s.md` Review: "This is not an independent review." — author/close-out only; does not discharge this ticket |

## Pytest (preferred gate)

Command (no `output/.heavy.lock`; used existing `.venv-rp` from main checkout, left untracked):

```text
.venv-rp/bin/python -m pytest parser/tests/test_quantisation_roundtrip.py -q \
  -k 'strip_compare_excludes_removes or reports_differing_only_in_excludes or non_excluded_field_difference or locked_strip_is_not_timing_only'
```

Result: **4 passed, 96 deselected in 4.21s**

| Test | Maps to clause |
| --- | --- |
| `test_strip_compare_excludes_removes_every_excluded_key` | Shared helper removes every `COMPARE_EXCLUDES` key; input untouched |
| `test_reports_differing_only_in_excludes_compare_equal` | Differ only in excludes → equal after `normalise_k1_report_for_compare` |
| `test_non_excluded_field_difference_still_unequal` | Non-excluded diffs remain unequal |
| `test_locked_strip_is_not_timing_only` | Timing-only strip leaves `wall_s` mismatch; locked strip equalises |

Light in-process recompute of the same four clauses against tip helpers also **PASS** (disclosure: corroborates pytest; not a substitute).

## PASS/FAIL per clause

| # | Clause | Verdict | Notes |
| --- | --- | --- | --- |
| 1 | Reports differing only in `COMPARE_EXCLUDES` (`timing`, `wall_s`) compare equal after strip helpers | **PASS** | pytest + light recompute; helpers strip both top-level keys |
| 2 | Non-excluded diffs remain unequal | **PASS** | `failing` / `levels` diffs stay unequal after normalise |
| 3 | Timing-only strip leaves a `wall_s` mismatch | **PASS** | `test_locked_strip_is_not_timing_only` asserts timing-only JSON unequal while locked strip equal |
| 4 | Brief check 3 requires the shared helper (`strip_compare_excludes`), not timing alone | **PASS** | Live brief L31 names `COMPARE_EXCLUDES` — `timing` **and** `wall_s` — and `strip_compare_excludes` |

**Overall strip-fix review: PASS** (all four clauses).

## Explicit non-claims

- Does **not** clear other 3-90 blockers (PSS contract, native classify joins, 3-11 vs 3-14 oracle cell identities, completeness / plan 14, OOM/CHM hold).
- Does **not** close plan 04 Phase 3; does **not** mega-close 3-90; does **not** claim WP3 / plan 06.
- Does **not** reseat 170 / 3-16 / 3-17.
- Historical timing-only 3-90 FAIL rows remain accurate history of a past defect; they are not current strip defects on tip.

## Residual

None within the plan-16 / check-3 strip contract. Truncated-pin ledger is Phase 2 of this plan (separate domain).
