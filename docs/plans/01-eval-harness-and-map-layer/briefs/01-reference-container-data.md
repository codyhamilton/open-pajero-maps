# Brief: 01 — Reference container data (grid parameters + record-29 frame)

Consumer: implementation worker.
Owned paths: `parser/kiwiw/grid.py` (new), `parser/extract_reference_data.py` (new),
`parser/refdata/grid.json` (new), `parser/refdata/mht29_frame.bin` (new),
`parser/refdata/README.md` (new), `parser/tests/test_grid_data.py` (new),
`docs/provenance.md` (one new entry only). Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: nothing — may start immediately.
Runs alongside: nothing (units 02 and 07 start when this lands; it is small).

## Required reading, in order

1. `docs/design/target-disc.md` — "Pipeline shape and stage contracts": the **Grid contract**,
   **Copy-through management data**, and **Determinism** bullets are binding.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Architectural Implications", third
   bullet (reference LMR grid parameters become checked-in data; the build never reads the
   mounted disc), and "Why This Plan Exists" item "Resolved during planning" (record 29).
3. `parser/kiwiw/volume.py` — `parse_pdmdh_full`, `LevelMgmtRecord` fields (incl. the
   extended `n_road_frames`/`road_frame_table` etc. populated when `lmr_size >= 42`),
   `parse_management_header_table`, `getsector`.
4. `parser/osm_to_parcel_geometry.py` — `build_tile_grid_from_lmr` (what the build currently
   reads from the mounted disc; you are producing its checked-in replacement).
5. `parser/build_alldata.py` — `_make_synth_grid` and the `os.path.exists(alldata_path)`
   fallback in `run()` (the non-determinism this unit removes the need for; do not edit it
   here — unit 12 rewires the build).

## Goal

Make every reference-disc parameter the map-layer build needs available from checked-in
data, so a build on a machine without the reference disc is byte-identical to one with it.

## Contract

Design doc, Grid contract (settled): "Parcel cells at every level 12..0 are the reference
disc's own LMR grid (block set × block × parcel counts, cell sizes, coverage box E90..W142
crossing ±180°). Those parameters are checked-in data derived once from `R`; a build never
reads the mounted reference."

Design doc, Copy-through management data (settled): the frame pointed at by management
header record 29 (0-based) "is carried byte-identical from `R`."

Reference facts measured during refinement (2026-09-05, mounted disc at
`/run/media/codyh/464210-8480/ALLDATA.KWI`); your extractor must reproduce them:

| level | blocksets (lat×lng) | blocks | parcels type0 (lat×lng) | parcel types 1..3 | grid nx×ny |
|---|---|---|---|---|---|
| 12 | 1×1 | 1×1 | 1×1 | 2×2, 4×4, 1×1 | 1×1 |
| 10 | 2×4 | 1×1 | 2×1 | same | 4×4 |
| 8 | 2×4 | 1×1 | 8×4 | same | 16×16 |
| 6 | 2×4 | 1×1 | 32×16 | same | 64×64 |
| 4 | 8×8 | 1×1 | 32×32 | same | 256×256 |
| 2 | 16×16 | 2×2 | 32×32 | same | 1024×1024 |
| 0 | 16×16 | 4×8 | 64×32 | same | 4096×4096 |

Coverage lat −50.0..35.3333, lon 90.0..−142.0 (wraps). `lmr_size` 170, 7 LMRs, 601 BSMRs,
`n_basic_map`=3, `n_ext_map`=9 at every level, `n_basic_route`=2 at levels 0 and 2 only,
`node_record_size`=8, frame tables 16/32/16 at every level. MHT entry 29: dsa 512, size 64
(→ byte 4096, 2048 bytes). PDMDH blob at byte 6144, total_size 21088.

## Changes

### `parser/extract_reference_data.py` (new script)

Reads a reference `ALLDATA.KWI` (argument `--alldata`, default the mount path above) and
writes two files under `parser/refdata/`:

- `grid.json`: `{"source": {"disk_title", "data_version", "format_version"}, "sector_size",
  "logical_sector_size", "coverage": {lat_lo, lat_hi, lon_lo, lon_hi}, "coverage_exponents"
  (from `VolumeHeaderExtras`), "pdmdh": {"lmr_size", "bsmr_size", "bmr_size", "n_lmr",
  "n_bsmr", "header_gap_hex", "record_size", "total_size"}, "levels": [one object per LMR
  in on-disc order with every `LevelMgmtRecord` field except `grid_nx`/`grid_ny`, which are
  derived], "blocksets": [{"level", "blockset_index", "has_bmt": bool} …] in on-disc order}`.
  Sort keys, indent 2, trailing newline, so a re-run is byte-identical.
- `mht29_frame.bin`: the exact bytes addressed by MHT entry 29 (`getsector(dsa)` for
  `size * logical_sector_size` bytes). Refuse to write if the entry is the 0xFFFFFFFF sentinel.

The script is run once; its output is committed. It is the only code in this unit that
reads the mounted disc.

### `parser/kiwiw/grid.py` (new module)

`ReferenceGrid.load(path=None)` → dataclass holding the parsed `grid.json` (default path:
`parser/refdata/grid.json` resolved relative to the package, never the CWD). Provide
`level(n) -> LevelGrid` with `nx`, `ny`, `cell_lat`, `cell_lon` (derived from coverage and
counts exactly as `mesh.locate_parcel` derives `mx`/`my`), the raw LMR fields, and
`lon_span` computed with the same wrap rule as `mesh._lon_span`. Provide
`mht29_frame_bytes()` returning the 2048-byte blob. Provide `to_level_mgmt_record(n) ->
LevelMgmtRecord` so unit 12 can emit the LMR without re-deriving field order. This module
imports only `kiwiw.model` and stdlib.

### `parser/refdata/README.md`

One paragraph per file: what it is, which script produced it, the reference disc it came
from, and that the profile subdirectory (`profile/`) is written by unit 03. State that the
directory holds derived measurements and a manufacturer configuration frame, not map content.

### `docs/provenance.md`

Add nothing to `.gitignore`. Add one entry saying `parser/refdata/` is committed, derived
from the reference ISO by `parser/extract_reference_data.py`, and how to regenerate it.

### Keep untouched

`build_tile_grid_from_lmr` and `_make_synth_grid` stay as they are; unit 12 removes them.

## Done evidence

- `.venv-rp/bin/python parser/extract_reference_data.py && git status --porcelain parser/refdata` → after the second run, no modified files (byte-identical re-run).
- `parser/tests/test_grid_data.py` (no disc needed) asserts: 7 levels in order 12,10,8,6,4,2,0; level 0 `nx == ny == 4096`; level 12 `nx == ny == 1`; coverage lon_lo 90.0 and lon_hi −142.0 with `lon_span == 128.0`; `mht29_frame_bytes()` is 2048 bytes and starts with the language-code list (assert the ASCII substring `au` is present); `to_level_mgmt_record(0).n_basic_route == 2` and `to_level_mgmt_record(4).n_basic_route == 0`.
- With the disc mounted: a test (skip when unmounted) that `ReferenceGrid.level(n)` matches `build_tile_grid_from_lmr(...)` for every level on `nx`, `ny`, `cell_lat`, `cell_lon`, and that `mht29_frame_bytes()` equals the bytes read from the disc.
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass (baseline 132 + new).

## Report back

A short summary: what you changed, anything you deviated from in this brief and why, and any
contradiction you found between this brief and the contracts it cites (in particular, if the
measured table above does not match what you extract). **Do not resolve contradictions
silently — report them.**
