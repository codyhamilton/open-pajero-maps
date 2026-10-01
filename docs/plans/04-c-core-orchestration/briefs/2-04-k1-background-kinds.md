# Brief: 2-04 — K1 background kinds (`background`, `background_boundary`, `interior_cover`)

Consumer: 2-05 (completeness reuses the shape index built here); 2-06 (driver).
Owned paths: `parser/kiwiw/_k1_bg.c` (replaces the 2-03 stub), `parser/kiwiw/_k1.h` (extend the shape-index interface only, additively), `parser/kiwiw/cenc.py` (K1 section only, if the binding needs an extra field), new `parser/tests/test_k1_background.py`, and `parser/tests/k1_fixtures.py` (append builders). Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 2-03.
Runs alongside: nothing (2-05 reuses this unit's shape index).
Tier: Sonnet.
Budget: 10 files to read, about 1,200 lines changed (about 850 C, 350 test), 90 tool turns. Past the budget: stop, commit what passes, report `over budget` with the handoff (this is the largest K1 unit; a clean split at "outline distance" versus "inside / interior cover" is the expected handoff line).

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — K1 check, Determinism, Evidence contract bullets; Phase 2 Outcome.
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` — Contract, and the Amendment (count table: background 174,332,105 / 1,438,558; background_boundary 89,546,388 / 16,549,569; interior_cover 1,592,016 / 824; findings 2 and 3).
3. `parser/tools/quantisation_roundtrip.py` — the spec and count oracle: `Shapes` (197-268), `_road_segments`, `_cells_to_shapes`, `_tall_mask` (269-340), `_seg_distance` (380-434), `Region` shape members: `outline_distance`, `inside`, the segment buckets and the scan-line crossing table (470-590), `_check_block` lines 928-1005 (the background half: `onb`, `near`, boundary rescue by `inside`, interior-cover detection and the cover-centre test), `_fail_rows`.
4. `parser/kiwiw/_k1.h`, `_k1.c` (the block context, accumulators and sample rule from 2-03), `_k1_bg.c` (stub).
5. `parser/tests/k1_fixtures.py`, `parser/tests/test_k1_points.py` (style and the Python-vs-K1 comparison harness).

Read ranges and grep; do not re-read a file already in context.

## Goal

K1 reproduces the Python tool's `background`, `background_boundary` and `interior_cover` verdicts exactly, from the same spool shapes (local plus tall), inside the K1 frame.

## Contract

Cited from `DESIGN.md`:

- "**K1 check.** Input: D1 rows plus the spool via the same zero-copy reader. Output: for each check kind an exact `checked` count and an exact `failing` count, plus a bounded sample of failing items per kind (cell, type, shape id, vertex) so triage can start from them. Counts are exact; only samples are capped. Check kinds and tolerances are those of 3C-04's brief (`range`, `step`, `road_node`, `name_anchor` with its halo and subcell explained-categories, `background`, `background_boundary`, `completeness`, `interior_cover`); a tolerance or rule change is made only in Phase 3, with the reason and the count it moves recorded."
- "**Determinism.** D1 and K1 output is byte-identical for any worker count. The sample for each kind is the first N failing items in `(level, iy, ix)` order, then shape/vertex order; N is fixed in the header. Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal."
- "Contract H budgets ... Decode and check join as hot paths H5 and H6." and "**Evidence.** Every hot call reports C-side wall and call counts."

3C-04's rules (the spec, from the plan 03 design, "Verification-tool decisions"): a decoded background vertex not on the frame boundary lies within half a raw unit per axis (Chebyshev) of an outline of a same-type spool shape at that level; a vertex on the frame boundary lies inside or on a same-type spool polygon (point in polygon, half-unit tolerance); every interior-cover piece's cell centre lies inside its source polygon; interior covers are rings whose every vertex is on the leaf boundary and whose area equals the leaf rectangle's (within 0.5).

Decisions this brief makes (do not reopen):

- The spatial index (vertex/segment buckets at `SEG_BUCKET`, scan-line crossing table, the local-plus-tall shape set per block) is built in C per block context from the zero-copy spool region; its structures and entry points are declared in `_k1.h` for 2-05 to reuse. The index never allocates per shape or per vertex across the boundary.
- Equality is exact on `checked` and `failing` for the three kinds, per level, and on `worst_error_raw` (to the 6 decimals the Python report rounds to). The explicit expected full-disc numbers above are for 2-07/2-08 to check, not for this unit's tests, which compare against the Python tool on fixtures, but this unit must read them to know what a wrong rule looks like (a rule that reproduces fixtures but is silently approximate for tall shapes, coarse `mult_const` rectangles or long edges is the failure mode to avoid).
- The point-in-polygon and half-unit tolerance arithmetic is performed with the same double operations as numpy does in `inside`/`outline_distance` (`-ffp-contract=off`; no reassociation). If exactness needs a different iteration order than Python's, stop and report `blocked` with a minimal reproducer; do not loosen the comparison.
- The samples follow 2-03's rule (first N in `(level, iy, ix)` then shape/vertex order).

## Changes

- `_k1_bg.c`: the shape index, `outline_distance`, `inside`, the boundary/non-boundary split, the interior-cover test, accumulators and samples wired through the 2-03 interface.
- Tests: `test_k1_background.py` compares K1 with the Python tool on fixtures from `k1_fixtures.py` plus new builders you append: a coarse `mult_const` polygon, a polygon spanning several cells (a vertex on the frame boundary needing point-in-polygon), an interior cover, a "tall" polygon whose bounding box leaves its home cell (exercises the tall pass), a polygon with a long near-closing edge like the 65623 pattern (finding 2), and injected faults (vertex outside every polygon; a displaced boundary vertex). Also assert byte-identical K1 output across band splits and band orders, and the call counter.
- A real-disc cross-check: on the 3-11 disc `output/scratch-3-11/G/ALLDATA.KWI` against `output/extract_timing/spool`, pick the single cheapest level that has background vertices (measure; levels are listed by `walk`/the manifest) and compare Python and K1 per-kind counts for that level. This one run is heavy only if the Python tool exceeds a few minutes on that level: if so run it under `flock output/.heavy.lock` as a background script (waiting rules below). If no level is cheap enough (more than 10 minutes of Python), skip it and say so; 2-07/2-08 carry the full-disc comparison.

### Keep untouched

Everything 2-03 delivered (point kinds, accumulators, sample rule), `quantisation_roundtrip.py`, D1, all build entry points and gates.

## Done evidence

Write the comparison tests first (stub returns zeros: fail); report before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_k1_background.py parser/tests/test_k1_points.py parser/tests/test_perf_inventory.py parser/tests/test_goldens.py -q --basetemp=output/scratch-2-04/pytest` → passes.
- Per-kind K1 vs Python table for each fixture and for the real-disc level (or the stated skip), all equal.
- A mutation of the half-unit tolerance, and one of the point-in-polygon edge rule, each make a test fail; revert.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha, check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently: write it into this brief as a dated `## Amendment` and report it. Over budget: stop, commit what passes, put the handoff (done, not done, what you learned) in the report.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Waiting rules (plan 03 Contract W, applied)

Chain every slow step in one background script (`run_in_background`) that appends `STEP <name> OK <s>` or `STEP <name> FAIL <rc> <s>` to a status file and ends with `ALLDONE`; a `trap ... EXIT` appends `ABORT` if it ends without `ALLDONE`. Block on it with ONE Monitor (or one Bash with a real timeout) whose match covers `ALLDONE|ABORT|FAIL|Traceback`; timeouts at least cover heavy-lock wait. Never end your turn to wait, never poll with no-op turns, never pipe a long command through `| tail`; read logs with Read or a bounded grep. A check needing many waits is a finding.

## Machine facts

- Python is `.venv-rp/bin/python` from the repo root (`python` is not on PATH). gcc is required; `kiwiw/cbuild.py` builds `_cenc.so` on demand from `EXT_SOURCES`, content-hashed. Build flags (`-O2 -ffp-contract=off -fPIC`) are not to change: floating-point results must be bit-reproducible against Python.
- Plan 04 `DESIGN.md` Decisions 1-9 and Assumptions 1-5 are settled; do not reopen them. Workers are Sonnet; no Opus.
- Commit and push to `master` when done evidence passes (project `CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, compiled `.so` or test binaries.
- Scratch for your own files: `output/scratch-<brief number>/` with `TMPDIR` exported there; pytest `--basetemp=output/scratch-<brief number>/pytest`.
- Reference discs: R `/run/media/codyh/464210-8480/ALLDATA.KWI` (tests using it skip when absent); G `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`); spool `output/extract_timing/spool` (build_alldata's default spool is not it).
- One heavy job at a time: any full-AU build or `-j 12` run takes `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`. Pytest and small builds do not.

## Amendment 2026-10-01 (2-04 worker)

The brief's owned paths omitted `parser/kiwiw/_k1.c`, but the background kinds need spool shapes
the 2-03 band did not collect and the level's tall shapes (`kw_k1_tall`) as band input. Done
(additively): `_k1.c` collects each cell's background shapes in `region_build`, merges the tall
set per band (`shp_add_tall`), exports `k1_frame_raw`, `k1_make_sample`, `k1_cheb_pt_seg`,
`k1_gx`, `k1_gy`; `kw_k1_band` gained 5 trailing arguments (tall rows, xy, offsets, bboxes,
count) and `cenc.py` caches a per-spool tall set (`_k1_tallset`). `_k1.h` gained `k1_shapes`,
`k1_tallset` and `k1_ctx.shapes`. Python's `inside()` float-key trick is replaced by the exact
comparison it approximates (ia <= a + TOL and running max ib >= a - TOL); no divergence on any
fixture or on G levels 12/10/8/6.
