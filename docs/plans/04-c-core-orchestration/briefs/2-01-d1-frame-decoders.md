# Brief: 2-01 — D1 frame decoders (road, background, name, map-frame header)

Consumer: 2-02 (adds the block walker and calls these decoders per leaf); then K1 (2-03 onward) reads their rows.
Owned paths: new `parser/kiwiw/_d1.c`, new `parser/kiwiw/_d1.h`, `parser/kiwiw/cbuild.py` (one `EXT_SOURCES` entry), `parser/kiwiw/cenc.py` (D1 binding section only), `parser/kiwiw/ctest/test_d1_frames.c` (optional), new `parser/tests/test_d1_frames.py`. Touch nothing else. Add no other non-test `.py` module (the perf-inventory test would fail; the binding lives in `cenc.py`, the one door).
Commits: Commit to `master` and push when done evidence passes.
Depends on: nothing (Phase 1 is closed).
Runs alongside: nothing (the K1 chain waits on D1).
Tier: Sonnet.
Budget: 12 files to read, about 1,000 lines changed (about 700 C, 300 test), 90 tool turns. Past the budget, stop: report `over budget` with the handoff (done, not done, what you learned) in your report; the orchestrator records it.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Domain: libkiwiw, Contract bullets "Granularity", "D1 decode", "Determinism", "Layout single-source", "Evidence"; Phase 2 Outcome.
2. `parser/kiwiw/parcel.py` (159 lines, whole), `road.py`, `background.py`, `name.py` (about 350 lines together, whole) — these are the spec: what D1 must reproduce.
3. `parser/kiwiw/model.py` — `RoadNode`, `RoadLink`, `RoadFrame`, `BackgroundShape`, `BackgroundElement`, `BackgroundFrame`, `NameRecord`, `NameList`, `NameFrame`, `MapFrameHeader`, `MapFrame`: the field list D1 must carry.
4. `parser/kiwiw/bitutils.py`, `coordconv.py` (`decode_region_coord`, `xy_to_latlon`, `range_for`), `roadtypes.py` — the integer/float conversion rules.
5. `parser/kiwiw/cenc.py` (binding style, per-range stats dicts `_e1_stats`/`_e2_stats`), `cbuild.py`, `descriptor.py` header docstring and how the `COLS[]` mismatch is detected at load (`-7: "descriptor column table differs from _cenc.c COLS[]"`), `_e1.c` top 80 lines (C style, error codes, timers, counters).
6. `parser/tests/test_goldens.py` and `parser/tests/fixtures/goldens/*/` (`frames.bin`, `frames.tsv`: `level ix iy pt sx sy fid len?` rows then frame sha) — the committed frames that are the equivalence set; `parser/tests/test_cenc.py` for test style.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

A C decoder that turns a set of leaf Map Frames (frame bytes plus the leaf's coordinate frame) into fixed-width columnar rows carrying every field the Python decoders return, equal to them on the goldens' frames.

## Contract

Cited from `DESIGN.md`, binding:

- "**D1 decode.** Input: a byte region of `ALLDATA.KWI` (G or R) plus the block/frame descriptor for the range. Output: columnar rows carrying every field that `kiwiw.parcel.decode_parcel` and the road/background/name sub-decoders return today (header words, link and node fields, background shapes and vertices, name strings and anchors, flags), losslessly. A field the Python decoder returns and D1 omits is a defect."
- "**Granularity (extends Contract B).** One C call per contiguous range of cells (build) or frames (decode/check). No per-parcel, per-shape or per-vertex call crosses the boundary. Calls take the mmap'd spool or disc region zero-copy and write fixed-width columnar rows into caller-provided buffers; no callbacks, no Python objects, no pickle."
- "**Layout single-source.** Every row layout is declared once in a C header and mirrored in Python by a checked descriptor, as `COLS[]` is today; a mismatch fails at load."
- "**Evidence.** Every hot call reports C-side wall and call counts" (H5 measures the Python/C/handoff split of Contract H; mirror `_e1_stats`).
- "**Determinism.** D1 and K1 output is byte-identical for any worker count": rows are in on-disc frame order within a range, with no thread-dependent or address-dependent bytes.

Decisions this brief makes (the contract leaves them open; do not reopen):

- This unit's input is a **leaf-frame table** (one fixed-width row per frame: byte offset and length into the mapped region, `n_basic_map`, `n_ext_map`, the frame's bounds as four doubles, `coord_range`) plus the mapped disc region, and its entry is one ctypes call per frame range. Walking the parcel-management tree to produce that table is 2-02. Declare the leaf-frame row layout in `_d1.h` so 2-02 emits it.
- `raw_bytes`/`raw_offset` fields (links, shapes, name records, header, `region_list_raw`, `tail_raw`, `ext_frame_raw`, `display_class_flags`, `additional_data_raw`) are carried as `(offset, length)` pairs into the mapped region, never copied; the equivalence test slices the region to compare. Name text is carried as `(offset, length)` too (the Python `_cstr` decode rule is the spec; if text needs a decode step, emit a char blob).
- `type_label` fields are a pure function of `type_code` (`roadtypes`); D1 emits codes, and the binding derives labels per distinct code through the existing `roadtypes` functions (a loop bounded by vocabulary size, not by shapes). The test asserts `type_label` equality through that path. If you find a label that is not a pure function of the code, stop and report `blocked`.
- A frame that Python decode raises on gets a per-frame status code in D1 (the checker counts "leaf did not decode" as a failure, `quantisation_roundtrip._iter_leaves`); the test asserts D1 fails on exactly the frames Python raises on, using the golden frames plus synthetic truncated copies of them.
- lat/lon are doubles computed with the same operation order as `coordconv.xy_to_latlon`; compared **bit-exactly** (compare the `float64` bit patterns). If bit-exact is impossible with `-ffp-contract=off`, stop and report `blocked` with the two values and the operation sequences. No tolerance is introduced here.

## Changes

- `_d1.c`/`_d1.h`: the four decoders as one entry `kw_d1_frames(...)` over a leaf-frame table, writing into caller buffers that grow on a "needs more space" return (the `e1` pattern), C timer and counters in a stats slot array. Row layouts for: frame header (one per frame, including mfde entries and the counts of rows it contributed), road links, road nodes, road shape points, display-class table and additional-data table rows, background shapes, background coordinates, background elements and their unit-table pairs, name records, name lists.
- `cenc.py`: a D1 section: load, layout check at load (mismatch raises), one wrapper `d1_frames(region, table) -> columns`, `d1_stats()` (ranges, calls, rows, py/c/handoff seconds) in the style of `e1_stats`.
- `cbuild.py`: add `_d1.c` to `EXT_SOURCES`; nothing else.
- `test_d1_frames.py`: for every committed golden's frames (and the `local.json` goldens if present), decode every frame with Python `decode_parcel` and with D1; assert every field equal, field for field, via a flattening helper that walks the model dataclasses (so a field added later to the model without D1 support fails). Include the truncated-frame error case, and an assertion that D1 makes one call per range (stats).

### Keep untouched

`_e1.c`, `_e2.c`, `_cenc.c`, the E1/E2/H4 bindings and counters, the build output (the full-AU sha, Perth sha and goldens must not move: run `parser/tests/test_goldens.py` and `test_cenc.py`, `test_e1.py`, `test_e2.py` unchanged), and every Python decoder (they are the oracle until Phase 5).

## Done evidence

Write the failing equivalence test first (no D1 yet); report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_d1_frames.py -q --basetemp=output/scratch-2-01/pytest` → fails before, passes after, covering every committed golden.
- A deliberate mutation (change one decoded field in C, e.g. a node `oneway`) makes the test fail naming that field; revert and pass. Report both.
- `.venv-rp/bin/python -m pytest parser/tests/test_goldens.py parser/tests/test_cenc.py parser/tests/test_e1.py parser/tests/test_e2.py parser/tests/test_perf_inventory.py -q` → pass (build unchanged; no new non-test module).
- Load-time layout check: corrupt one field width in the Python descriptor in a throwaway edit and show `import`/first call raises; revert.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha, check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently: write it into this brief as a dated `## Amendment` and report it.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Machine facts

- Python is `.venv-rp/bin/python` from the repo root (`python` is not on PATH). gcc is required; `kiwiw/cbuild.py` builds `_cenc.so` on demand from `EXT_SOURCES`, content-hashed. Build flags (`-O2 -ffp-contract=off -fPIC`) are not to change: floating-point results must be bit-reproducible against Python.
- Plan 04 `DESIGN.md` Decisions 1-9 and Assumptions 1-5 are settled; do not reopen them. Workers are Sonnet; no Opus.
- Commit and push to `master` when done evidence passes (project `CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, compiled `.so` or test binaries.
- Scratch for your own files: `output/scratch-<brief number>/` with `TMPDIR` exported there; pytest `--basetemp=output/scratch-<brief number>/pytest`.
- Reference discs: R `/run/media/codyh/464210-8480/ALLDATA.KWI` (tests using it skip when absent); G `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`); spool `output/extract_timing/spool` (build_alldata's default spool is not it).
- One heavy job at a time: any full-AU build or `-j 12` run takes `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`. Pytest and small builds do not.
