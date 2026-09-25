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

## Module map (`parser/`)

| Area | Modules | Role |
|---|---|---|
| Format model | `kiwiw/model.py`, `bitutils.py`, `coordconv.py`, `grid.py`, `mesh.py`, `roadtypes.py`, `vocab.py` | Shared types, bit packing, coordinate and mesh maths, type vocabularies |
| Readers and writers, per layer | `kiwiw/{volume,parcel,parcel_mgmt,road,background,name,misc,route_planning,index_data}.py` and the matching `*_writer.py` | Decode R; encode G. Replicate-mode writers round-trip R byte-identical |
| Map synthesis | `kiwiw/{synth,selection,divide,frame_table,spill,spool,alldata_writer}.py`, `kiwiw/_cenc.c` + `cenc.py` | Turn cell content into Map Frames, fit and divide parcels, place blocks, write `ALLDATA.KWI` |
| Extraction | `osm_to_parcel_geometry.py`, `osm_to_route_planning.py`, `osm_to_address_index.py`, `build_route_graph.py` | OSM to spool and route graph |
| Evaluation | `compare_disc.py`, `harness/` (`checks/`, `profile.py`, `bytediff.py`, `report.py`) | Parity checks against R |
| Analysis | `roundtrip_*.py`, `analyze_*.py`, `study_*.py`, `estimate_*.py`, `survey_*.py`, `dump_parcel.py` | Research and round-trip proofs; not on the build path |
| Tools | `tools/lint_schema.py`, `bench_build.py`, `convert_spool.py`, `parcel_occupancy.py` | Schema lint, benchmarking, spool conversion |
| Tests | `tests/` | Round-trip, synthesis, encoding and harness tests |

## Stage contracts

**Spool.** Per level, a `.data` file of per-cell records and a `.idx` file, little-endian,
fixed-width, mmap-able, no pickle. Cells ascend `(iy, ix)`. The spool carries lat/lon for every
vertex, and encoders derive pixels at assembly from each frame's range, so a coordinate-range
change needs only re-assembly, not re-extraction.

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

**Partition and merge.** A level's cells are split into contiguous ranges by cell count, not
content size. Each range returns its frame table plus additive counters; the merge sums
counters and orders by canonical key, with no order-dependent float reduction. A worker
failure aborts the build, names the failing `(level, cell range)` and deletes partial output.

**C kernel.** `_cenc.c` encodes a whole cell from the raw spool record. It answers only the
"fits, no kind breach" case; anything else returns -1 and `divide.plan_divisions` handles the
cell in Python. The Python path is the byte-identity oracle. Floating point parity is held by
`-ffp-contract=off`, `rint` and identical operation order. `KIWIW_NO_C=1` or no compiler falls
back to Python.

**Spill and indexed assembly.** Encode workers `pwrite` frames to per-process spill files and
return a numpy `FrameTable`. `IndexedLayout` places every frame and block with one `lexsort`;
simple blocks are written vectorised and frames copied by threads in C; divided blocks are
built in Python. The object path (`FrameSpill`/`FrameRef`) remains as the identity oracle.

Measured: full build 263 s → 32.5 s at `-j 12`, peak RSS ~0.75 GB, with output SHA unchanged.

**Evaluation.** The harness reports PASS, FAIL or N/A per check (decodes clean, pointers
resolve, same vocabulary, profile envelope, container byte-diff, cross-file consistency,
round-trip regression, capacity). Definitions are in `docs/design/target-disc.md`.

## Schema as a build contract

`docs/schema/` rows carry a status, evidence and the module that reads or writes them.
`python parser/tools/lint_schema.py` (via `.venv-rp/bin/python`) validates the row format and
regenerates `docs/schema/UNKNOWNS.md`. A stage that learns a format fact updates the row it
touches in the same change.

## Open questions

`docs/schema/UNKNOWNS.md` indexes every row that is not `verified`. Open items are grouped by
work package there and in `docs/design/target-disc.md`; none may be decided by guess.
