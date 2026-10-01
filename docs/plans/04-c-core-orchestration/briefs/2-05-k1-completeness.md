# Brief: 2-05 — K1 `completeness`

Consumer: 2-06 (driver); the Phase 2 close.
Owned paths: `parser/kiwiw/_k1_cmp.c` (replaces the 2-03 stub), `parser/kiwiw/_k1.h` (additive only), `parser/kiwiw/cenc.py` (K1 section, only if needed), new `parser/tests/test_k1_completeness.py`, `parser/tests/k1_fixtures.py` (append builders). Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 2-04.
Runs alongside: nothing.
Tier: Sonnet.
Budget: 8 files to read, about 700 lines changed (about 450 C, 250 test), 70 tool turns. Past the budget: stop, commit what passes, report `over budget` with the handoff.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — K1 check, Determinism, Evidence; Phase 2 Outcome.
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` — Contract and the Amendment table (completeness 1,800,514 / 752).
3. `parser/tools/quantisation_roundtrip.py` — `_required_cells` (1030-1097), `key_cells`, `_check_block` lines 1006-1027 (the `present` set and the missing-cell computation), `Region` members it uses (`spool_cells`, the shape index), `_fail_rows`/sample shape for completeness.
4. `parser/kiwiw/_k1.h`, `_k1.c`, `_k1_bg.c` (the shape index 2-04 built), `_k1_cmp.c` (stub).
5. `parser/tests/k1_fixtures.py`, `test_k1_background.py` (comparison harness).

Read ranges and grep.

## Goal

K1 reproduces the Python tool's `completeness` verdict: for each `(cell, type)` a spool polygon's interior demonstrably meets, at least one decoded polygon piece (three or more vertices) of that type exists in that cell.

## Contract

Cited from `DESIGN.md`:

- "**K1 check.** Input: D1 rows plus the spool via the same zero-copy reader. Output: for each check kind an exact `checked` count and an exact `failing` count, plus a bounded sample of failing items per kind (cell, type, shape id, vertex) so triage can start from them. Counts are exact; only samples are capped. Check kinds and tolerances are those of 3C-04's brief (`range`, `step`, `road_node`, `name_anchor` with its halo and subcell explained-categories, `background`, `background_boundary`, `completeness`, `interior_cover`); a tolerance or rule change is made only in Phase 3, with the reason and the count it moves recorded."
- "**Determinism.** D1 and K1 output is byte-identical for any worker count. The sample for each kind is the first N failing items in `(level, iy, ix)` order, then shape/vertex order; N is fixed in the header. Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal."
- "Contract H budgets ... Decode and check join as hot paths H5 and H6." and "**Evidence.** Every hot call reports C-side wall and call counts."

Decisions this brief makes: semantics are `_required_cells` and the `present` computation exactly (including which cells count, the "demonstrably meets" test and its tolerances); equality is exact on `checked` and `failing` per level; `completeness` samples are `(cell, type)` in `(level, iy, ix)` then type order, first N; the shape index is 2-04's (no second index).

## Changes

- `_k1_cmp.c`, tests: `test_k1_completeness.py` compares K1 with the Python tool on the fixtures (including a removed piece, a polygon whose interior meets a cell without a vertex in it, a cell entirely covered by one big polygon, a tall polygon) and asserts band-split byte-identity and the call counter.
- Whole-tool check: with 2-03, 2-04 and this unit in place, K1 vs Python `roundtrip` on all fixture discs equal on EVERY kind and every explained counter (add this as one test, `test_k1_all_kinds_match_python`).

### Keep untouched

2-03/2-04 behaviour and files, `quantisation_roundtrip.py`, D1, build gates.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests/test_k1_completeness.py parser/tests/test_k1_background.py parser/tests/test_k1_points.py parser/tests/test_perf_inventory.py parser/tests/test_goldens.py -q --basetemp=output/scratch-2-05/pytest` → passes; the comparison test fails before (stub) and passes after (report both).
- The all-kinds equality test passes on every fixture; print the per-kind table.
- A mutation of the required-cell test makes a test fail; revert.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha, check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently: write it into this brief as a dated `## Amendment` and report it. Over budget: stop, commit what passes, put the handoff (done, not done, what you learned) in the report.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Machine facts

- Python is `.venv-rp/bin/python` from the repo root (`python` is not on PATH). gcc is required; `kiwiw/cbuild.py` builds `_cenc.so` on demand from `EXT_SOURCES`, content-hashed. Build flags (`-O2 -ffp-contract=off -fPIC`) are not to change: floating-point results must be bit-reproducible against Python.
- Plan 04 `DESIGN.md` Decisions 1-9 and Assumptions 1-5 are settled; do not reopen them. Workers are Sonnet; no Opus.
- Commit and push to `master` when done evidence passes (project `CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, compiled `.so` or test binaries.
- Scratch for your own files: `output/scratch-<brief number>/` with `TMPDIR` exported there; pytest `--basetemp=output/scratch-<brief number>/pytest`.
- Reference discs: R `/run/media/codyh/464210-8480/ALLDATA.KWI` (tests using it skip when absent); G `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`); spool `output/extract_timing/spool` (build_alldata's default spool is not it).
- One heavy job at a time: any full-AU build or `-j 12` run takes `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`. Pytest and small builds do not.
