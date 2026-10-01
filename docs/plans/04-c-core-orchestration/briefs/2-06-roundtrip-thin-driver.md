# Brief: 2-06 — `quantisation_roundtrip.py` as a thin driver over K1

Consumer: 2-07 (the full-disc run drives this entry point); Phase 3 (triage runs it).
Owned paths: `parser/tools/quantisation_roundtrip.py`, `parser/kiwiw/cenc.py` (a driver-facing wrapper only, if the 2-03..2-05 binding lacks one), `parser/tests/test_quantisation_roundtrip.py`, `parser/perf_inventory.json`, and `parser/tests/test_perf_inventory.py` only if the inventory schema needs it. Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 2-05 (and so 2-01..2-04).
Runs alongside: nothing.
Tier: Sonnet.
Budget: 8 files to read, about 500 lines changed, 70 tool turns. Past the budget: stop, commit what passes, report `over budget` with the handoff.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Phase 2 Outcome, Gates (checker row), libkiwiw Contract, Determinism, Assumption 2.
2. `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` — Carried section, item 2 (re-check low-confidence classes at the phase that moves them; this unit moves `quantisation_roundtrip`).
3. `parser/tools/quantisation_roundtrip.py` — `main`/argparse, the process-pool/band driver (`_check_block` call sites, `_merge`, report writer), the report schema.
4. `parser/kiwiw/cenc.py` K1 and D1 sections (what 2-01..2-05 left), `_k1.h` (the report/accumulator layout and `N`).
5. `parser/tests/test_quantisation_roundtrip.py`; `parser/perf_inventory.json` and `parser/tests/test_perf_inventory.py` (how a file is classified, and the `quantisation_roundtrip.py` entry).

Read ranges and grep.

## Goal

The round-trip entry point runs K1 by default, as a thin driver: split the level/band plan into ranges, call C once per range (through the binding), merge the per-range results deterministically, and write the same report schema as before. The Python checking path stays callable as `--engine python`, as the count oracle until Phase 5.

## Contract

Cited from `DESIGN.md`:

- "**K1 check.** Input: D1 rows plus the spool via the same zero-copy reader. Output: for each check kind an exact `checked` count and an exact `failing` count, plus a bounded sample of failing items per kind (cell, type, shape id, vertex) so triage can start from them. Counts are exact; only samples are capped. Check kinds and tolerances are those of 3C-04's brief (`range`, `step`, `road_node`, `name_anchor` with its halo and subcell explained-categories, `background`, `background_boundary`, `completeness`, `interior_cover`); a tolerance or rule change is made only in Phase 3, with the reason and the count it moves recorded."
- "**Determinism.** D1 and K1 output is byte-identical for any worker count. The sample for each kind is the first N failing items in `(level, iy, ix)` order, then shape/vertex order; N is fixed in the header. Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal."
- "Contract H budgets ... Decode and check join as hot paths H5 and H6." and "**Evidence.** Every hot call reports C-side wall and call counts."

Decisions this brief makes (do not reopen):

- `--engine c` is the default; `--engine python` runs the unchanged old path. The report records which engine produced it. The report schema (kinds, `checked`, `failing`, explained counters, samples) is unchanged so Phase 3 tooling and the 3C-04 record read both.
- The driver's work per band is one binding call. The merge is "first N of the union of each range's first N" and sums for counts. Output must be byte-identical between `-j 1` and `-j 4` (and `-j 12` for 2-07), with timings and PSS excluded from the compared bytes (they go in a separate `timing` section that the comparison drops, stated in the report header).
- The driver samples summed per-process PSS (`/proc/<pid>/smaps_rollup` `Pss:` for the driver and its pool children, sampled at least every 0.5 s) and reports the peak, the wall, and the C-side timers (H5/H6) in the `timing` section.
- `perf_inventory.json`: `quantisation_roundtrip.py` is reclassified to orchestration once the remaining Python per-vertex loops are only reachable behind `--engine python`; record exactly which functions remain Python-oracle-only and that Phase 5 deletes them. If the inventory test still counts those functions as hot-path, report the contradiction rather than weakening the test.

## Changes

- Driver rewrite, flag, report additions, PSS sampler, inventory update.
- Tests in `test_quantisation_roundtrip.py`: (a) on every small-input fixture, `--engine c` and `--engine python` reports have equal `checked`, `failing`, explained counters, and `worst_error_raw` on every kind, with samples equal under the first-N rule; (b) `-j 1` and `-j 4` C reports are byte-equal (timing section excluded); (c) the call counter equals the number of ranges planned and is far below the number of blocks/vertices; (d) the PSS sampler returns a positive peak.
- One real-disc-level count equality: on G (`output/scratch-3-11/G/ALLDATA.KWI`) and the spool (`output/extract_timing/spool`), pick the cheapest level that has all of road, background and name data (measure), run both engines, and compare all kinds. Run both under `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock` as one background script (waiting rules below). If no level fits in 10 minutes of Python wall, record the measured wall and the level chosen as the smallest available and say so; do not skip silently. A missing G or spool counts as `blocked`.

### Keep untouched

K1/D1 C code, build entry points, gates, `compare_disc` and the harness.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests/test_quantisation_roundtrip.py parser/tests/test_k1_points.py parser/tests/test_k1_background.py parser/tests/test_k1_completeness.py parser/tests/test_d1_frames.py parser/tests/test_perf_inventory.py parser/tests/test_goldens.py -q --basetemp=output/scratch-2-06/pytest` → passes.
- The per-kind table (C vs Python) for the real-disc level: every row equal. Report the level, both walls, the PSS peak.
- `-j 1` vs `-j 4` byte comparison (`cmp` output) on the real-disc level.
- `--engine python` on a fixture produces exactly the report it produced at HEAD before this unit (compare with `git stash`-free means: run the HEAD version from `git show HEAD:...` into scratch).
- The inventory test passes with `quantisation_roundtrip.py` reclassified; quote the new entry.

## Waiting rules (plan 03 Contract W, applied)

Chain every slow step in one background script (`run_in_background`) that appends `STEP <name> OK <s>` or `STEP <name> FAIL <rc> <s>` to a status file and ends with `ALLDONE`; a `trap ... EXIT` appends `ABORT` if it ends without `ALLDONE`. Block on it with ONE Monitor (or one Bash with a real timeout) whose match covers `ALLDONE|ABORT|FAIL|Traceback`; timeouts at least cover heavy-lock wait. Never end your turn to wait, never poll with no-op turns, never pipe a long command through `| tail`; read logs with Read or a bounded grep. A check needing many waits is a finding.


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

## Amendment (2026-10-01, 2-06 worker)

Contradictions and deviations, recorded rather than resolved silently:

1. **"Report records the engine" vs "`--engine python` produces exactly the HEAD report".**
   Both cannot hold byte-for-byte. The Python path adds one key, `"engine": "python"`; with
   that key (and `wall_s`) removed the report equals HEAD's on every fixture at `-j 1` and
   `-j 3` (checked against `git show HEAD:` loaded from scratch).
2. **Library default.** The CLI default is `--engine c`. The library function
   `roundtrip(..., engine="python")` keeps the Python default, because `test_k1_points.py`,
   `test_k1_completeness.py` (not owned here) call it as the oracle.
3. **Sample sets above N.** For `road_node`/`road_point`/`name_anchor`/`background`/
   `background_boundary` the Python tool keeps the first N by `(Y, X)` per band before its
   `_sample_key` sort, while K1 keeps the contract's first N in `(iy, ix, path, vx, vy)` order.
   Counts, worst error and explained counters are equal on every fixture and on the real
   levels; the sample SETS are identical when `failing <= N` and are both N-sized samples of
   the same failing set otherwise (G level 6 `background_boundary`: 4,004 failing). Phase 5
   deleting the Python path removes the difference; the K1 order is the contract's.
4. **Band plan independent of `-j`.** The planner is called with a fixed `PLAN_WORKERS = 12`
   so the byte-equality gate holds across `-j`; `-j` only sets the pool size. A Python
   `-j N` run plans with N, so compare engines at `-j 12` on a real disc.
5. **Extra flags.** `--levels` (needed to pick the real-disc level) and `-j` (alias).
6. **Real-disc finding (not fixed here).** G level 6 fails identically in both engines:
   `background_boundary` 4,004/4,921 and `interior_cover` 1/1 (a build-side or tolerance
   matter for Phase 3 triage); level 8 passes.
