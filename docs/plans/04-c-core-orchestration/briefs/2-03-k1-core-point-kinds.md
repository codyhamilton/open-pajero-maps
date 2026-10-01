# Brief: 2-03 — K1 core and the point kinds (`range`, `step`, `road_node`, `road_point`, `name_anchor`)

Consumer: 2-04 and 2-05 (add the shape-based kinds into the K1 frame this unit builds); 2-06 (the driver calls this entry).
Owned paths: new `parser/kiwiw/_k1.c`, `parser/kiwiw/_k1.h`, stub `parser/kiwiw/_k1_bg.c` and `parser/kiwiw/_k1_cmp.c` (each returns zero counts and is replaced by 2-04 and 2-05), `parser/kiwiw/cbuild.py` (`EXT_SOURCES` entries for all three), `parser/kiwiw/cenc.py` (K1 section only), new `parser/tests/k1_fixtures.py`, new `parser/tests/test_k1_points.py`. Touch nothing else, and add no other non-test `.py` module.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 2-02 (D1 gates K1: do not start until D1's equivalence is green on master).
Runs alongside: nothing.
Tier: Sonnet.
Budget: 12 files to read, about 1,200 lines changed (about 850 C, 350 test), 90 tool turns. Past the budget: stop, commit what passes, report `over budget` with the handoff.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Domain: libkiwiw contract bullets "K1 check", "Determinism", "Layout single-source", "Evidence"; Gates "C checker"; Phase 2 Outcome.
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` — Contract, Changes, and the Amendment's count table and numbered findings (the semantics and the expected counts).
3. `parser/tools/quantisation_roundtrip.py` — the Python checker is the spec and the count oracle. Read lines 1-95 (constants: `RAW`, `TOL`, `EPS`, `INT_EPS`, `SEARCH`, `SEG_BUCKET`, `SAMPLE`, `KINDS`, `EXPLAINED`), `Lattice` (96-119), `PointSet` (144-181), `_read_cells`, `_pass1`, `_cells_to_shapes` (the spool shapes + "tall" pass: 197-380), `Region.__init__` and its point-set members (435-520), `Decoded` (591-673), `Acc` (674-705), `_check_points`, `_road_rescue`, `_halo_name_rescue`, `_range_check` (715-830), `_check_block` lines 897-927 only (the point half), and `roundtrip` (1165-1223).
4. `parser/kiwiw/_d1.h`, `_d1.c` entry points; `parser/kiwiw/_e1.c` top 120 lines (the zero-copy spool reader and `spool._COLUMNS` layout this unit reuses; do not write a second spool parser).
5. `parser/kiwiw/spool.py` lines 1-60 and `SpoolReader.cell_weights/iter_cell_columns` (index layout), `parser/kiwiw/mesh.py` `CellGrid`.
6. `parser/tests/test_quantisation_roundtrip.py` lines 60-140 (fixture builders to copy into `k1_fixtures.py`).

Read ranges and grep; do not re-read a file already in context.

## Goal

The K1 frame: one C call per block row band that decodes (through D1, in C, no Python round trip) and checks the point kinds against the spool, with exact counts, the explained categories, the bounded deterministic samples and the C-side counters; shape-based kinds are stubs the next units fill.

## Contract

Cited from `DESIGN.md`:

- "**K1 check.** Input: D1 rows plus the spool via the same zero-copy reader. Output: for each check kind an exact `checked` count and an exact `failing` count, plus a bounded sample of failing items per kind (cell, type, shape id, vertex) so triage can start from them. Counts are exact; only samples are capped. Check kinds and tolerances are those of 3C-04's brief (`range`, `step`, `road_node`, `name_anchor` with its halo and subcell explained-categories, `background`, `background_boundary`, `completeness`, `interior_cover`); a tolerance or rule change is made only in Phase 3, with the reason and the count it moves recorded."
- "**Determinism.** D1 and K1 output is byte-identical for any worker count. The sample for each kind is the first N failing items in `(level, iy, ix)` order, then shape/vertex order; N is fixed in the header. Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal."
- "Contract H budgets ... Decode and check join as hot paths H5 and H6." and "**Evidence.** Every hot call reports C-side wall and call counts."

Decisions this brief makes (do not reopen):

- Semantics are the Python checker's, exactly, for the kinds in this unit: same lattice (`X = (lon - disc_lon_lo)/cell_lon * 4096`, rounding with `rint`), `TOL`, `EPS`, `INT_EPS`, the `range` rule (decoded raw must be integral within `INT_EPS` and within `[0, range]`), the `step` rule (a multiple of `mult_const`, at most `127 * mult_const`; the step arithmetic needs background vertices from D1, so `step` is implemented here over D1 rows even though background geometry checks come later), nearest-spool-point Chebyshev distance for `road_node`, `road_point`, `name_anchor`, the two road rescues and the halo-name rescue as `explained` counters (`road_node_subcell_on_polyline`, `road_node_on_leaf_edge`, `road_point_subcell_on_polyline`, `road_point_on_leaf_edge`, `name_anchor_halo`), and "leaf did not decode" counted as a `range` failure. Float operations mirror numpy's (no fused ops; same order); `rint` is round-half-even.
- `checked`/`failing`/`worst_error_raw` per (level, kind) are exact integers/doubles. Samples: the first N failing items per (level, kind) in `(level, iy, ix)` order then shape/vertex order, with N a constant in the header of the result (use 10); each sample row carries cell, kind, type (when it has one), leaf path, shape id and vertex index (when it has them), decoded lat/lon and frame-raw, reason code. The merge across ranges is "first N of the union of each range's first N", which makes any worker split identical; test it (below).
- The one-call-per-range granularity: the entry is called once per (block, row band). Block bands are formed by Python exactly as `_block_tasks` forms them today (bounded by blocks); the spool "tall shapes" pass is one C call per level per spool row range, output shared read-only across worker processes by fork (no pickling per task); both are in the binding and counted.
- Layouts (accumulators, samples, tall-shape arrays) are declared in `_k1.h` and mirrored by a checked Python descriptor, as in 2-01.
- `_k1_bg.c` and `_k1_cmp.c` are registered stubs behind a stable internal interface declared in `_k1.h` (a function per kind group taking the block context and the accumulator) so 2-04 and 2-05 change only their own file and tests.

## Changes

- `_k1.c`/`_k1.h`: block context (lattice, spool region index for the block's rectangle grown by one cell, point sets, the tall-shape pass), accumulators with exact counts and the first-N sample rule, the `range`/`step`/point-kind checks, the explained rescues, stats (C wall, calls, items checked).
- `cenc.py`: `k1_tall(...)`, `k1_check_band(...)`, `k1_stats()`; reuse the D1 binding.
- `k1_fixtures.py`: copy `_base_cells`, `_big_cells`, `_build`-style helpers from `test_quantisation_roundtrip.py` (do not edit that file; it belongs to 2-06), plus injected-fault builders: a vertex moved outside every polygon, a removed piece, a name moved, a road node moved. Make them importable by 2-04/2-05 tests.
- `test_k1_points.py`: for each fixture disc (clean, and each injected fault), run the Python `quantisation_roundtrip.roundtrip(..., workers=1)` and K1 over the same disc and spool, and assert equal `checked`/`failing` for `range`, `step`, `road_node`, `road_point`, `name_anchor` and equal `explained` counters; assert K1 results are byte-identical when the same disc is checked as one band versus split into several bands/ranges in different orders; assert the call counter equals the bands planned; assert a sample is the first N in the stated order on a fixture with more than N failures.

### Keep untouched

`quantisation_roundtrip.py` and `test_quantisation_roundtrip.py` (read-only here), all D1 behaviour, all build entry points and gates.

## Done evidence

Write the equality test first (K1 not present: fails); report before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_k1_points.py parser/tests/test_d1_equivalence.py parser/tests/test_quantisation_roundtrip.py parser/tests/test_perf_inventory.py parser/tests/test_goldens.py -q --basetemp=output/scratch-2-03/pytest` → passes.
- A mutation of one tolerance in C makes `test_k1_points` fail on the injected-fault fixtures; revert.
- K1 point-kind counts equal the Python tool's on every fixture, including the explained counters (print the table in the report).

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
