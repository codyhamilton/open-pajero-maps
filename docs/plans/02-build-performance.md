# Build Performance: Byte-Identical Assembly Speed-up

The assembly stage (`parser/build_alldata.py`, spool to `ALLDATA.KWI`) went from 11–17 min and 6.85 GB peak RSS to 263 s and about 3.0 GB (tree-summed RSS) on a 12-core machine, with the output byte-identical to the baseline (sha256 `51c254ac…672743`, 1,397,923,200 bytes). Both acceptance targets (≤ 6 min, ≤ 3 GB) were met, the RSS one narrowly.

## Intent

User request, verbatim:

> The build time runs far too long in this repo. Lets investigate what can be done - profile the runtime. We would want to see something like an OOM improvement in the runtime or more. Lets profile where the time is being spent, and if there is a ceiling on performance due to using python for what is very computational and memory intensive work
>
> Ok plan the first four suggestions (leave our C hot path until after other stages)

## Why This Existed

Every WP1 fix ended in a 11–17 min rebuild-and-verify cycle. Profiling showed about 47% of time in unpickling the spool, about 45% in pure-Python per-vertex background/road encoding, one core in use, and the whole container held in RAM. Speed-ups had to leave every output byte unchanged so the byte-diff oracle stayed valid.

## What Was Built

- **Streaming assembly:** frames are appended to a spill file (`kiwiw/spill.py`, `FrameRef` index) and the container is streamed to disk by `alldata_writer.build_alldata_kwi(..., return_bytes=False)`; the bytes-returning path remains for small fixtures.
- **Binary columnar spool:** `kiwiw/spool.py` writes little-endian fixed-width per-cell records (`.data` + `.idx`, magic `KWSPIDX1`); the reader uses `os.pread` per cell. The old pickle format lives in `kiwiw/spool_legacy.py`, and `parser/tools/convert_spool.py` converts existing spools (per-level stats verified equal). The contract is promoted to `docs/ARCHITECTURE.md` (stage contracts).
- **Vectorized encoder:** `synth._bg_fast` (numpy pixel conversion plus an inlined integer loop for multiplier > 1 / saturating deltas), guarded by the retained scalar oracle and a 4000-shape fuzz test. About 1.5x on level 2.
- **Parallel encoding:** `-j/--workers` in `build_alldata.py`. Whole-row chunks (weight-balanced, independent of the worker count) are encoded by forked workers with their own readers and merged in canonical order through a bounded window; `trim_stats` merge additively.
- Tooling: `parser/tools/bench_build.py` (wall + tree RSS), `--frame-digest` per-frame sha256 listing, numpy as a hard dependency, `docs/provenance.md` updated.

**Changed:** `parser/build_alldata.py`, `parser/kiwiw/{spool,spool_legacy,spill,alldata_writer,synth}.py`, `parser/tools/{convert_spool,bench_build,parcel_occupancy}.py`, tests (`test_spool_binary`, `test_synth_vectorized`, `test_build_alldata`, `test_alldata_writer`), `docs/provenance.md`.

### Phase results (full build, converted spool)
Phase 1 streaming: 805 s, 1,820 MB. Phase 2 binary spool: 771 s, 1,854 MB (an mmap reader was rejected: mapped pages count toward RSS at 6.67 GB). Phase 3 numpy: kept (≥ 1.3x). Phase 4 `-j 12`: 263 s, 2,995 MB, identical sha.

## Deviations

- One commit ("Record phase 1") also swept in Phase 2 source files.
- The pool is a `multiprocessing` fork `Pool` created up front rather than a lazily-forking executor, which had inflated summed RSS to 3,043 MB.
- The Perth baseline digest was committed during the run and removed here.
- Full `-j 1` was not re-run after Phase 4, and the extractor's `--fixture perth` was not run end-to-end (Perth was built from the converted full spool).

## Review

In-run terminal review: PASS_WITH_FOLLOWUPS, no blocker/high findings. Perth sha `e275879f…` verified at `-j 1`/`-j 4` and under two PYTHONHASHSEED values; 288 tests passed.

## QA

Byte identity and the frame-digest listing compared at worker counts 1/2/4/5/12; full suite green.

## Residual Risks

RSS margin is thin (2,995 MB vs the 3,000 MB limit; the metric double-counts shared copy-on-write pages, so it is conservative). Lower `-j` or the pending window if it regresses.

## Follow-ups

None filed. Possible later work: empty-cell frame caching, faster road/column decode, the deferred C hot path.

## Decisions Worth Keeping

- Streaming and the binary spool come before vectorization and parallelism: parallelism needs both.
- Rejected mmap for the reader; `pread` keeps RSS honest.
- Chunk boundaries never depend on worker count; only chunk count does, and any partition yields identical bytes.
