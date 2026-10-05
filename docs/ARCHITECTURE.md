# Architecture

How the code is organised and the contracts between stages. What the format *is* lives in
`docs/schema/`; what we are building and how it is judged lives in
`docs/design/target-disc.md`. Open questions are not listed here: see
`docs/schema/UNKNOWNS.md`, which is generated from the schema rows.

## Pipeline

```
OSM PBF (Australia)
  → extract     osm_to_parcel_geometry.py   per-cell spool (per level, columnar binary)
  → assemble    build_alldata.py            ALLDATA.KWI + manifest.json
  → (WP2–WP4)   route-planning and IDX writers
  → (WP5)       UDF-bridge image → burn

Evaluation, offline: compare_disc.py + harness/  →  G vs R report
```

Stages communicate through files, not in-process state, so each can be rerun alone.

Fixture extraction applies a conservative way-bounds precheck per level before
splitting roads. Its admission extent covers whole target cells, including their
margin beyond the requested bbox. Crossing ways, floating-point boundaries,
longitude wrapping and existing edge-column clamping are retained. The check
changes neither the splitting/centroid rules nor chain identities and skips
only ways that cannot produce output in those cells. Full-grid extraction keeps
its existing path; place nodes retain their existing admission.

## Rule: C for perf-sensitive work, Python orchestration only

Any loop whose trip count scales with the vertices, shapes, parcels, frames or cells of a
full-AU disc or spool is C, in the one library `libkiwiw`. Python owns the CLIs, range
planning, the worker pool, paths and mmap handles, manifest/report glue, schema lint,
extraction, and header reads bounded by file or level count. A Python loop is allowed only
when its count is bounded by ranges, levels, files, check kinds or report rows. Python reaches
libkiwiw through one binding module (one door). The contracts, gates and phases are in
`docs/plans/04-c-core-orchestration/DESIGN.md`; this file does not restate them.
`parser/perf_inventory.json` classifies every non-test `parser/` Python module as
orchestration, c-now, c-later or retired, and `parser/tests/test_perf_inventory.py` fails for
any module missing from it. Extraction stays Python (plan 04 Decision 9).

## Module map (`parser/`)

| Area | Modules | Role |
|---|---|---|
| Format model | `kiwiw/model.py`, `bitutils.py`, `coordconv.py`, `grid.py`, `mesh.py`, `roadtypes.py`, `vocab.py` | Shared types, bit packing, coordinate and mesh maths, type vocabularies. `mesh.py` also owns the frame-range rule (`frame_range`, `leaf_frame_range`) and the frame-class table the descriptor reads |
| Readers and writers, per layer | `kiwiw/{volume,parcel,parcel_mgmt,road,background,name,misc,route_planning,index_data}.py` and the matching `*_writer.py` | Decode R; encode G. Replicate-mode writers round-trip R byte-identical |
| libkiwiw (C), build side | `kiwiw/_e1.c` (E1), `kiwiw/_e2.c` (E2), `kiwiw/_cenc.c` (shared encoders and the assembly copy helpers), `kiwiw/cenc.py` (ctypes bindings), `kiwiw/cbuild.py` (compile on demand; the C unit-test binary), `kiwiw/ctest/*.c` | Everything per shape or per cell: overlap scan and merge, clip, densify, round, record and Map Frame encoding, measurement, division, retile, trim, name halo. See "libkiwiw boundary" |
| Level descriptor | `kiwiw/descriptor.py` | Python builds it once per level; it carries grid, frame ranges, window, mask, limits and spool column layout as data, never a rule |
| Assembly | `kiwiw/{spool,frame_table,alldata_writer}.py`, `build_alldata.py` | `SpoolReader`; `FrameTable`, `ChunkSpill` and the vectorised `IndexedLayout`; the `ALLDATA.KWI` file layout; the CLI, worker pool, manifest and bench record |
| Selection | `kiwiw/selection.py` | Per-level feature selection thresholds, read by extraction, not by the build |
| Extraction | `osm_to_parcel_geometry.py`, `osm_to_route_planning.py`, `osm_to_address_index.py`, `build_route_graph.py` | OSM to spool and route graph |
| Evaluation | `compare_disc.py`, `harness/` (`checks/`, `profile.py`, `bytediff.py`, `report.py`) | Parity checks against R |
| Analysis | `roundtrip_*.py`, `analyze_*.py`, `study_*.py`, `estimate_*.py`, `survey_*.py`, `dump_parcel.py` | Research and round-trip proofs; not on the build path |
| Tools | `tools/lint_schema.py`, `bench_build.py`, `convert_spool.py`, `parcel_occupancy.py` | Schema lint, benchmarking, spool conversion (`convert_spool` requires `--i-trust-this-pickle`; legacy pickle quarantined in `kiwiw/spool_legacy.py`, plan 24) |
| Tests | `tests/` | Boundary tests (decode what E2 wrote), the C unit-test binary, committed goldens, round-trip and harness tests. No Python encoder exists to compare C against |

Plan 04 Phase 2 landed the C decoder (**D1**) and checker (**K1**). Phase 3
remains blocked at 3-90 after the recorded 3-14–3-17 work; census kernels
(Phase 4) and Python decoder retirement (Phase 5) depend on its close. The
Python parcel decoders still exist as migration oracles and harness readers.

## Stage contracts

**Spool.** Per level, a `.data` file of per-cell records and a `.idx` file, little-endian,
fixed-width, mmap-able, no pickle. Cells ascend `(iy, ix)`. The spool carries lat/lon for every
vertex, and encoders derive pixels at assembly from each frame's range, so a coordinate-range
change needs only re-assembly, not re-extraction. Production build/extract/harness use
`kiwiw.spool` only. Legacy pickle (`kiwiw.spool_legacy`) is quarantined (plan 24): every
`pickle.load` needs `enable_legacy_pickle_trust` / convert `--i-trust-this-pickle`; an offline
allowlist oracle fails new `pickle.load` outside that module.

**Assembly.** `ALLDATA.KWI` layout is a pure function of the spool and the parcel mask.
Frames are keyed `(level, ix, iy, parcel_type, sub_ix, sub_iy)`. Blocks are written in
`sorted((level, bsidx, blidx))` order; within a block, frames ascend by local slot, then
divided sub-frames per parent by `(sub_iy, sub_ix)`; each block's management record follows
its frames. Every frame is zero-padded to `logical_sz` (32). The PDMDH region is written
last, once block offsets are final.

**Output invariance.** For any spool, `ALLDATA.KWI` bytes, the manifest `sha256`,
`total_size`, per-level counts, `trimmed_items` and `halo_names` are identical before and
after any performance change and for any worker count. The manifest carries no run-varying
fields; timings go to a separate bench record.

**Partition and merge.** A level's rows are split into contiguous `[lo, hi)` row spans by
`build_alldata._plan_chunks`, balanced by weight (record size, with big records weighted
superlinearly, plus a per-empty-cell term inside the mask rectangle), at most `jobs * 64`
spans. Windowed and fixture builds still partition the whole level; the window travels in the
descriptor. E1 and E2 run over the same spans. Each E2 span returns its frame index plus
additive counters; the merge sums counters and orders by canonical key, with no order-dependent
float reduction. Any partition gives identical output; the partition only balances work. A
worker failure aborts the build, names the failing `(level, row span)` and deletes partial
output.

**libkiwiw boundary.** The C side has two kinds of entry point. Contracts are in plan 04
`DESIGN.md` (Domain: libkiwiw; Gates), with plan 03 "Contract B" (placement) and "Contract H"
(hot paths and budgets) still binding for the build.

- Build path, exists today: E1, E2 and the H4 copy helpers (`kw_copy_frames`, `kw_write_rows`).
  These are the only C entry points on the build path.
- Verification, off the build path: **D1** (decoder: `ALLDATA.KWI`
  byte region to lossless columnar rows) and **K1** (checker: D1 rows plus
  the spool to exact `checked`/`failing` counts and capped samples per check kind)
  exist from plan 04 Phase 2. K1 attribution remains open in Phase 3. The
  **census kernels** (continuity, boundary mirror, neighbour lookup, coordinate
  scale, occupancy, density) are planned for dependent Phase 4. Each uses one call per
  range of cells or frames, zero-copy in, fixed-width rows out, byte-identical for any worker count.
- Hot paths H5 (decode) and H6 (check) join Contract H's table, with C-side wall and call
  counters, from Phase 2.

The sections below describe the build path as it stands.

**Build boundary.** `build_alldata.py` crosses into C only through E1, E2 and the H4 assembly
copy helpers (`kw_copy_frames`, `kw_write_rows`). The contract is `DESIGN.md` of Plan 03,
"Contract B" (placement) and "Contract H" (hot paths and budgets); this file does not restate it.
In outline, per level:

1. Python builds the level descriptor once (`descriptor.build_for_spool`).
2. E1 runs once per row span over the level's mmap'd spool and returns 32-byte routing rows
   (target cell, source cell offset, edge or interior cover) and the additive overlap counters.
   Python only concatenates the rows, sorts them by target and splits them at the span edges.
3. E2 runs once per row span with the descriptor, the spool and that span's routing rows.
   It orders borrowed shapes canonically, encodes every cell (including masked-in empty cells),
   and divides, retiles, trims and adds the name halo itself. It writes finished frame bytes
   to a caller-supplied spill file descriptor and returns a 36-byte-per-frame index and the
   manifest counters.
4. E2's declined list is empty on any valid build; a non-empty list is a build error. There is
   no E3, no merged-content output and no Python fallback.

E1 calls equal E2 calls at every level, and the build tests assert it from the bench record.
Floating-point parity is held by `-ffp-contract=off`, `rint` and identical operation order,
checked against the committed goldens and the Python decoders, never against a Python encoder
(Contract T). The `KIWIW_NO_C` switch and the no-compiler fallback are gone.

**Build requirement.** `gcc` (or `cc`) must be on `PATH`. `cbuild.build_ext()` compiles
`_cenc.c`, `_e1.c` and `_e2.c` into `kiwiw/_cenc.so` on first use (`-O2 -ffp-contract=off
-fPIC -lm`), keyed by a content hash of the sources and flags. A missing or failing compiler
raises `BuildError`; a build without a compiler fails. The same module builds the C unit-test
binary from `kiwiw/ctest/*.c`.

The assembly helper binding `cenc.lib()` also raises `BuildError` when its
shared library cannot be opened or a required assembly symbol is missing,
with the path and original exception preserved. It caches only a completely
configured library; failure permits retry after repair.

**Spill and indexed assembly.** Each encode worker owns one spill file (`ChunkSpill`). E2 writes
frame bytes into it from C at a caller-given offset and returns the frame index; Python keeps
a numpy `FrameTable` of index rows and no per-frame object, and nothing but the table crosses
the process boundary. `IndexedLayout` places every frame and block with one `lexsort`. Simple
and divided blocks, their management and sub-records are all built with numpy over the frame
table (`divided_block_rows`, no per-frame Python), and frames are copied to their final offsets
by threads in a GIL-free C loop. There is no object path and no `spill` module.

Measured (3C close, median of three): full build 12.2 s at `-j 12` (L0 5.2 s including a 1.4 s
pre-pass; outside-encode 6.7 s), output SHA unchanged. L0 worker time is almost all C, with
Python and handoff under 1 % of it (budget table in the 3C-13 report; Contract H). Earlier
points: 263 s (object path), 32.5 s (indexed assembly), about 100 s (3-11, Python overlap and
divide).

**Evaluation.** The harness reports PASS, FAIL or N/A per check (decodes clean, pointers
resolve, same vocabulary, profile envelope, container byte-diff, cross-file consistency,
round-trip regression, capacity). Definitions are in `docs/design/target-disc.md`.

## Schema as a build contract

`docs/schema/` rows carry a status, evidence and the module that reads or writes them.
`python parser/tools/lint_schema.py` (via `.venv-rp/bin/python`) validates the row format and
regenerates `docs/schema/UNKNOWNS.md`. A stage that learns a format fact updates the row it
touches in the same change.


## Bounded dump I/O and heavy-job memory

Offline dump transforms and triage readers that once whole-file `memmap`'d or
`copyfile`'d multi-GiB kinds now share a storage boundary. This is an analysis /
scratch-path change; the full-Australia deliverable, schema facts, build oracle,
C-first kernel boundary, and plan04 PSS gates are unchanged.

### Shared window boundary

`parser/kiwiw/dump_io.py` owns window lifetimes only (no C layout declarations,
no per-row Python kernels):

- Default window **65,536** rows. Changing the window leaves bytes and aggregates
  identical.
- At most one bounded source, destination, and assignment window at a time.
  Release every derived view before closing or reusing a window. Slicing a
  whole-file mapping is **not** a window; flushing an entire mapping is **not**
  a residency bound.
- Write-behind: on each completed destination window start writeback
  (`sync_file_range`) and drop windows already written back from the page cache
  (`posix_fadvise(DONTNEED)`), and drop consumed source windows the same way.
  Output bytes and final durability (fsync / close) are unchanged; dirty and
  cached output stay near a few windows instead of the whole file.
- Validate row size, field offsets, complete-row file length (and assignment
  length where applicable) before writing. Shared mapped readers/writers reject
  zero-length kinds; classify alone accepts manifest-validated zero-row files
  and emits their zero partitions (see `docs/design/k1-triage.md`).

Transformation-specific adapters keep their own join / padding / aggregation
policy: residual byte146 and 3-07 144→152 rebuild in `parser/tools/dump_join.py`;
`summary` / `classify` / `enumerate` in `parser/tools/k1_triage.py`. Side indexes
scale with side-table rows; triage retained aggregation keys must own independent
storage (no structured scalar into a unique-array buffer). Report group / source /
pair cardinalities separately — triage RSS is **not** cardinality-independent.
Triage's internal structured keys are packed, so NumPy unique/indexed copies
cannot introduce allocator-dependent padding into byte-key identity. The
aligned on-disk dump layout stays separate and unchanged; grouping contracts
are in `docs/design/k1-triage.md`.

### Why RSS alone was the wrong story (oomd)

Host kills observed in this work were **systemd-oomd** pressure kills on
`user@*.service` (PSI above threshold with reclaim activity), not always the
kernel OOM killer selecting the heaviest RSS process. A heavy job hurts the
session two ways: its own resident set, and file pages it dirties or keeps hot
even when they are not mapped. Sibling scopes (terminals, browsers) can die
first.

Whole-file patterns that drove that pressure:

- `shutil.copyfile` of a ~2.34 GiB dump leaves dirty page cache **outside**
  process RSS.
- A whole-file read-write `np.memmap` that touches every row keeps touched pages
  in the process page tables across the scan (RSS grows with the file) and keeps
  the destination hot.
- Holding multiple full arrays (K1 `_finalize_dump` concatenating parts, then
  `tobytes()` of the sorted rows) creates a multi-GiB anonymous spike after the
  plan04 PSS sampler has already stopped.

Measurement therefore gates **both** max RSS (KiB) and the worker's cgroup v2
`memory.peak`, records `memory.stat` (`anon`, `file`, `file_dirty`,
`file_writeback`) and pressure totals, and runs each worker in a fresh
`systemd-run --user --scope -p MemoryAccounting=yes` process. Operational lock,
commands, and metric guidance: `docs/WORKFLOW.md` (Heavy jobs).

### Deferred: out-of-core dump finalizer

Phase 2 removed the redundant full-array copies from
`parser/tools/quantisation_roundtrip.py` `_finalize_dump` (preallocate +
`readinto`, release parts as consumed, stable `argsort(order=DUMP_ORDER)`,
chunked write by permutation — no `tobytes()` of the full sorted array). Bytes,
canonical order, manifest, counts, and part deletion are unchanged.

An **external-sort / out-of-core** rewrite of `_finalize_dump` remains a **known
limitation**, not live plan work. Peak anonymous memory for finalization still
scales with one full in-memory kind array. Do not treat Phase 2 as a bound on
arbitrarily large kinds without further design.

## Open questions

`docs/schema/UNKNOWNS.md` indexes every row that is not `verified`. Open items are grouped by
work package there and in `docs/design/target-disc.md`; none may be decided by guess.
