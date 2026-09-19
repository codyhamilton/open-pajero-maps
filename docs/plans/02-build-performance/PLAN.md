# Build Performance: Byte-Identical Assembly Speed-up

## Intent

User request, verbatim:

> The build time runs far too long in this repo. Lets investigate what can be done - profile the runtime. We would want to see something like an OOM improvement in the runtime or more. Lets profile where the time is being spent, and if there is a ceiling on performance due to using python for what is very computational and memory intensive work
>
> Ok plan the first four suggestions (leave our C hot path until after other stages)

(The four suggestions, from the profiling report: numpy-vectorize the coordinate transform/delta encoding; multiprocessing over cells; replace the pickle spool with a flat memory-mapped binary format; stream frames to the output file instead of holding the whole container in RAM.)

## Why This Plan Exists

`parser/build_alldata.py` (spool -> `ALLDATA.KWI`) takes 11-17 minutes and ~6.85 GB peak RSS for the full-Australia build, and every WP1 fix ends in a rebuild-and-verify cycle (rebuilds #4-#6 each cost a wait of 11-17 min). A cProfile of the Perth fixture (artifact: `/home/codyh/.claude/jobs/107c3d34/tmp/perth.prof`, ephemeral) showed where the time goes:

- ~47%: reading the pickle spool (1.27M `pickle.load` calls on the level-0 file, `spool.py` `iter_level`).
- ~35%: `encode_background_shape_bytes` (`synth.py`), ~10%: road link encoding; both are per-vertex pure-Python arithmetic (82M `_clamp_coord` genexpr calls, 119M `min`/`max`).
- The build is single-threaded (12 cores idle) and holds every encoded frame, then the whole 1.4 GB container as `bytes`, in RAM before writing.

Reducing wall time and peak memory without changing a single output byte makes every later rebuild cheap and keeps the byte-diff oracle (`docs/design/target-disc.md` "Determinism") valid.

## Scope

Four changes to the assembly stage, sequenced streaming -> binary spool -> vectorized encoders -> multiprocessing, each gated on a byte-identical `ALLDATA.KWI` against a fixed baseline. Covers `build_alldata.py`, `kiwiw/alldata_writer.py` (multilevel path), `kiwiw/spool.py` (+ its extractor writer call sites and a one-time pickle-to-binary converter), and the encoders in `kiwiw/synth.py`. Non-goals: the C/Rust hot path (deferred to after this plan), extractor (`osm_to_parcel_geometry.py`) speed, `compare_disc.py` runtime, and any change to output bytes.

## Architectural Implications

- `docs/design/target-disc.md` "Determinism" (byte-for-byte reproducible) is the governing contract; this plan adds "and independent of worker count and of streaming/spill strategy".
- The spool is "intermediate pipeline state" (`docs/provenance.md` `output/spool/`); its on-disk format changes. Its consumers must migrate: `build_alldata.py`, `parser/harness/checks/envelope.py`, `parser/tools/parcel_occupancy.py`, and tests that read spools (`test_build_alldata.py`, `test_parcel_mask.py`, `test_extractor_scale.py`, `test_selection.py`).
- `build_alldata_kwi()` currently returns the whole container as `bytes` (tests and roundtrip scripts rely on that); a streaming path must coexist with it for small fixtures.
- New dependency: numpy in `.venv-rp`. `docs/provenance.md` must record it (project rule: non-committed materials get a BOM entry), and the `output/spool/` entry must document the new format and converter.
- Per-cell work is independent (`divide.plan_divisions` and `_add_name_halo` use only the parent cell's own content), which is what makes parallelism safe; `trim_stats`/`halo_names` are the only cross-cell state and are additive counters.
- Contracts that need reifying for cross-implementor work live in `DESIGN.md` (spool format, spill/assembly contract, partition/merge contract).

## Intent Validation

- numpy as a hard dependency: asked; answer: yes (see PROVENANCE.md Turn 1).
- Existing spool migration: asked; answer: one-time converter, no re-extraction (Turn 2).
- The user's four items keep their names, but their order is changed (streaming and the spool come before vectorization and parallelism) because of the dependencies noted in Agent Decisions.

## Assumption Ledger

None — interactive session; see PROVENANCE.md.

## Open Questions

- Default worker count and flag name (e.g. `-j`, default `os.cpu_count()` or a cap): deferred to `refine`; it does not change the contract as long as output is worker-count-independent.
- Whether the per-frame golden digest manifest (Phase 0) is committed or regenerated: a large file would be a BOM entry, not committed; decided in Phase 0 by its size.

## Execution Phases

1. **Phase 0 — Baseline and bench harness.** Confirm determinism at HEAD (two Perth builds under different `PYTHONHASHSEED`, identical sha). Record baseline shas (full: `51c254ac...2743` from `output/manifest.json`; Perth: measured here). Add a small bench script recording wall and peak RSS (parent + children) per stage. Emit a per-frame digest listing so a later mismatch is localized to a `(level, ix, iy, sub)` cell. Install numpy in `.venv-rp`; record in `docs/provenance.md`.
2. **Phase 1 — Streaming assembly (suggestion 4).** Spill encoded frames to a temp file with an in-memory offset index; write the container sequentially in block order; patch the PDMDH region last (its contents depend on final offsets, its size does not); compute sha256 by a chunked re-read. Keep the `bytes`-returning API for small builds.
3. **Phase 2 — Binary columnar spool (suggestion 3).** Define the format (`DESIGN.md`), implement writer and mmap reader behind the existing `SpoolReader`/`SpoolWriter` interface, migrate the extractor's writer and the other consumers, and add the one-time pickle-to-binary converter.
4. **Phase 3 — Vectorized encoders (suggestion 1).** Batch the lat/lon-to-pixel transform and clamp per cell in numpy on the columnar content; delta recurrence gets a no-saturation fast path with an exact scalar fallback; road frames pack via `struct`/numpy. The current scalar encoders stay in the tree as the test oracle.
5. **Phase 4 — Parallel cell encoding (suggestion 2).** Workers take contiguous ranges of the ordered cell list, read their own spool ranges, encode and divide, write spill segments; the parent merges indexes and counters in canonical order. Output must be identical for any worker count.
6. **Phase 5 — Full verify and record.** Full-Australia build on the final code: sha equals baseline, wall/RSS floors met, timings recorded in the plan's record at close-out; update `docs/provenance.md` and the stage-timing figures quoted elsewhere.

## Acceptance Criteria

User-facing (entry point -> action -> observable result):

- `.venv-rp/bin/python parser/build_alldata.py` (full spool at `output/spool`, run under `/usr/bin/time -v`) -> build completes -> exit 0, `output/manifest.json` `sha256` equals `51c254ac87328f652e88f0b10880e83992622bcd1d2db2dbd519edc0a5672743` and `total_size` equals 1,397,923,200; wall time is at most 6 min and peak RSS (parent + children) at most 3 GB (baseline 11-17 min, 6.85 GB; floors to be re-set from Phase 0's measured baseline if that differs materially).
- `build_alldata.py --fixture perth` -> build completes -> sha equals the Phase 0 Perth baseline.
- `build_alldata.py` with worker count 1, then with worker count 12 -> both complete -> identical sha256.
- The spool converter run on the existing pickle spool -> `SpoolReader.stats(level)` totals for all seven levels equal the pickle spool's `manifest.json` `spool_stats`, and a full build from the converted spool matches the baseline sha.
- `osm_to_parcel_geometry.py --fixture perth` -> extraction completes -> its (new-format) spool builds to the Perth baseline sha.

Non-user-facing (observable statements):

- `pytest parser/tests -q` passes, including new tests: vectorized vs scalar encoder byte equality on Perth cells plus fuzz (out-of-bounds coordinates, `mult_const` > 1, delta saturation, single-coordinate shapes, point shapes); converted-spool vs pickle-spool decode equivalence per cell; streaming vs `bytes` path equality on a small multilevel fixture.
- Peak RSS does not grow with output size beyond the frame index: building levels 12-2 only and the full build differ by no more than the level-0 index and worker buffers (checked from the bench harness).
- Two builds under different `PYTHONHASHSEED` values produce identical sha256.
- `docs/provenance.md` records numpy and the new spool format/converter; no large or regenerable binary is staged in git.

## Provenance Notes

See `PROVENANCE.md` in this plan folder for the plan conversation record.

- The byte-identity gate makes `compare_disc.py` (~22 min) unnecessary for this plan: an identical sha256 means every existing check result is unchanged.
- Vectorization is the riskiest item and lower-yield than first estimated: the background delta encoder is a clamped recurrence, and small per-shape numpy calls can cost more than the Python they replace, hence per-cell batching on columnar content and a scalar oracle. If Phase 3 measures under ~1.3x on encode time, it is dropped and the plan closes without it rather than keeping complexity that does not pay.
- The spool converter exists so the byte-identity comparison uses the same content the baseline was built from; a re-extraction would confound the comparison.
- Challenge pass (run inline, not via subagent, because subagents are reserved for explicit user requests in this session): checked that (a) phase order respects dependencies (parallel needs spill + mmap spool), (b) acceptance floors are measurable, (c) the plan does not quietly widen into extractor or harness speed, (d) the two non-obvious risks are named: Python `round()` (half-to-even) must match `numpy.rint`, and float operation order in `latlon_to_xy` must be preserved bit-for-bit (`(lon - lo) / (hi - lo) * RANGE`, not a refactored form).
