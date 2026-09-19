# Design: Build Performance Contracts

> Contracts introduced by plan 02 (build performance): binary spool format, spill/assembly, and partition/merge. Governs any future change to the assembly stage.

Only the contracts that more than one worker must agree on. Implementation detail is left to `refine`/`execute`.

## 1. Output invariance

For any input spool, `ALLDATA.KWI` bytes, `manifest.json` `sha256`/`total_size`/per-level counts, `trimmed_items` and `halo_names` are identical before and after every phase, and identical for any worker count. `manifest.json` gains no fields that vary run to run (timings go to a separate bench record, not the manifest).

## 2. Spill and assembly contract (Phase 1, used by Phase 4)

- Frames are keyed `(level, ix, iy, parcel_type, sub_ix, sub_iy)`; type-0 frames use `sub = 0`.
- Encoding may produce frames in any order and from many processes. Encoders append raw frame bytes to a spill file and report `(key, spill_offset, length)`.
- Final layout is exactly what `_build_alldata_kwi_multilevel` produces today: blocks in `sorted((level, bsidx, blidx))` order; within a block, frames in ascending local slot index, then divided sub-frames per parent in ascending `(sub_iy, sub_ix)`; each block's management record follows its frames. Every frame is zero-padded to `logical_sz` (32) exactly as today.
- The PDMDH region (offset 6144, size known from the grid before any frame is encoded) is written last, after block offsets are final.
- Assembly needs only the key/offset/length index in memory, never frame bytes for more than one block at a time.
- `sha256` is computed over the finished file by a chunked read; the `bytes`-returning call keeps working for small (test) builds.

## 3. Binary columnar spool contract (Phase 2)

- Per level: a `.data` file of per-cell records and a `.idx` file, both little-endian and fixed-width, mmap-able, no pickle.
- A cell record stores each content kind as columns: road links (scalar header fields, node x/y int columns, `points` and any other fields `synth`/`divide`/`selection` read), background shapes (scalar fields plus float64 `lat`/`lon` coordinate columns with per-shape offsets), names (scalar fields, UTF-8 text, optional `lat`/`lon`/`angle`).
- Losslessness bar: every field read by `synth.py`, `divide.py` (including `_retile_content` and `_add_name_halo`), `selection.py` and `envelope.py` round-trips exactly (floats bit-exact). Fields never read on that path (round-trip-only `raw_bytes`/`raw_offset`) are not stored; the plan-time grep list is confirmed in Phase 2.
- `.idx` lists cells in ascending `(iy, ix)` with `(offset, length)` per cell so a worker can take any contiguous cell range without scanning; per-level `totals` (parcels/roads/backgrounds/names) are stored so `stats()` never re-reads data.
- Reader interface stays `iter_level(level)` yielding `(ix, iy, content)` plus range access `iter_cells(level, start, stop)`; the columnar arrays are exposed for the vectorized encoders.
- Converter: reads a pickle spool and writes the new format; the equivalence test decodes both per cell and compares.

## 4. Partition and merge contract (Phase 4)

- The ordered cell list for a level is the `(iy, ix)`-ascending stream after `_fill_masked` applies the parcel mask; it is partitioned into contiguous ranges by cell count, not by content size, so the partition is a pure function of the spool and mask (worker-count changes only regroup ranges).
- Each range is self-contained: it needs the level's `TileGrid`, thresholds/kind budgets (already pure data) and its own cell content.
- A range returns its frame index plus additive counters: `trim_stats` totals, `dropped`, per-kind `cells`, `halo_names`. The parent sums counters and orders the index by canonical key; no float or order-dependent reduction is allowed in the merge.
- A worker failure aborts the build with the failing range's `(level, cell range)` in the error; partial output is deleted.

## 5. C cell kernel (follow-on)

- `parser/kiwiw/_cenc.c` encodes a whole cell's Map Frame straight from the raw spool record (`kw_encode_cell`). It answers only the "fits and no kind breach" case; anything else (oversize, kind breach, any bail) returns -1 and Python runs `divide.plan_divisions` on that one cell, so the Python path stays the byte-identity oracle.
- `kw_bg_shape` also replaces the numpy background encoder on the divided-cell retile path, which dominated the L0 time.
- Float parity: `-ffp-contract=off`, `rint` for half-even rounding, identical operation order. Built on demand by `kiwiw/cenc.py` into an ignored `_cenc.so`; `KIWIW_NO_C=1` or no compiler falls back to Python.
- Full build, `-j 12`: 263 s -> ~90 s (encode ~58 s, serial assembly ~31 s), SHA-256 `51c254ac…` unchanged, peak RSS ~3.2 GB. Perth fixture SHA unchanged at `-j 1`/`-j 4`, with and without C.

## 6. Spill files, indexed assembly, C probe (plan 02 close-out)

- **Spill**: encode workers pwrite frames to a per-process spill file (`ChunkSpill`) and return only a numpy `FrameTable` (ix, iy, type, sub, fid, len, off). Chunks are weighted `len + len²/65536`, submitted heaviest-first, consumed in row order (deterministic).
- **Indexed assembly** (`frame_table.IndexedLayout`): one `lexsort` places every frame and block; fixed-size simple blocks are written vectorised (`kw_write_rows`), frames are copied by threads in C (`kw_copy_frames`); divided blocks are built in Python. The object path (`FrameSpill`/`FrameRef`) stays as the byte-identity oracle and the `KIWIW_NO_C=1` fallback.
- **Divided cells**: `divide.plan_divisions` is unchanged (still the oracle for retile, trim, shrink, halo). Its probe (`build_alldata._measure_one`) now tries `cenc.measure_content` -> `kw_measure_cell` (sub-cell content serialised to a spool record, encoded in C with explicit bounds, sizes returned) and falls back to the Python encoders when the kernel declines (ceiling, unmodelled input). A full C port of retile/halo was rejected: the probes were ~80% of the cost, and keeping the object logic in Python keeps identity risk low.
- **Result** (`-j 12`): 263 s -> ~90 s -> 46 s -> **32.5 s**, SHA-256 `51c254ac…` unchanged, peak RSS ~0.75 GB. Perth SHA `e275879f…` unchanged at `-j 1`/`-j 4` and `KIWIW_NO_C=1`. Remaining time is split between the Python retile and probe serialisation on ~533 divided parents.
- No new untracked files (spill files are temporary and deleted), so `docs/provenance.md` is unchanged.
