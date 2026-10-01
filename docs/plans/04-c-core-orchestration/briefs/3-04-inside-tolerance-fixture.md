# Brief: 3-04 — Cover the inside-side half-unit tolerance (Phase 2 carried)

Consumer: 3-07 and every checker-side fix unit that touches the point-in-polygon rule (they need this net).
Owned paths: `parser/tests/k1_fixtures.py` (append only), `parser/tests/test_k1_background.py` (append only). `parser/kiwiw/_k1_bg.c` is edited ONLY for the two mutations below and restored with `git checkout`; it must be byte-identical to HEAD at commit. Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 3-03 (shares the C library; no mutation may run while another unit builds).
Runs alongside: 3-06 only (3-06 does not load the C library).
Tier: Flash (mandatory Sonnet 5.5 review). RE-risky (moderate): needs a geometric construction with distances in (0, 0.5) raw.
Budget: 4 files to read, about 90 lines of test, 35 tool turns. Past the budget, stop, report `over budget`.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` — the "2-04" concerns paragraph (dropping `+TOL` in the inside interval comparison is not caught).
2. `parser/kiwiw/_k1_bg.c` lines 285-310 (the `ia <= a + K1_TOL` and `>= a - K1_TOL` comparisons).
3. `parser/tools/quantisation_roundtrip.py` `Region.inside` (about 534-600).
4. `parser/tests/k1_fixtures.py` — `BG_FIXTURES`, `bg_boundary_displaced`, `bg_shift_04`/`_06`; `parser/tests/test_k1_background.py` — how a fixture becomes a Python-vs-K1 comparison.

## Goal

A fixture pair that makes the inside-side tolerance observable: a frame-boundary disc vertex lying 0.3 raw OUTSIDE a same-type spool polygon along the scan line passes (inside by tolerance), and one 0.7 raw outside fails. Both engines agree, and removing `+ K1_TOL` or `- K1_TOL` in `_k1_bg.c` makes a test fail.

## Contract

Cited from the 3C-04 rules (in `2-04-k1-background-kinds.md`): "a vertex on the frame boundary lies inside or on a same-type spool polygon (point in polygon, half-unit tolerance)". Tolerance changes are made only in Phase 3, on a recorded cause; this unit changes none.

## Changes

- Append builders `bg_inside_out_03`, `bg_inside_out_07` (and, if the geometry needs it, one per scan orientation: horizontal and vertical) to the background fixtures and register them for the Python-vs-K1 equality test and a verdict assertion (03 passes with 0 `background_boundary` failures; 07 fails with exactly the expected vertex count).
- No change to any C or oracle code.

### Keep untouched

Existing fixtures and tests; `_k1_bg.c` at HEAD.

## Done evidence

- New tests fail on the mutation, pass at HEAD: for each of the two mutations (remove `+ K1_TOL` at line 301; remove `- K1_TOL` at line 302) apply it, run `.venv-rp/bin/python -m pytest parser/tests/test_k1_background.py -q --basetemp=output/scratch-3-04/pytest`, record which tests fail, then `git checkout parser/kiwiw/_k1_bg.c` and run again → pass. Both mutations must fail at least one new test; if a mutation is an equivalent mutant on every constructible fixture, report why (that finding matters to 3-07).
- `git diff --stat` at commit shows only the two test files.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
