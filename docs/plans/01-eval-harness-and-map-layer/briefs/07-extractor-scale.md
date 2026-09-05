# Brief: 07 — Extractor at country scale (one PBF pass, all levels, streaming, bounded memory)

Consumer: implementation worker.
Owned paths: `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/spool.py` (new),
`parser/tests/test_parcel_geometry.py`, `parser/tests/test_extractor_scale.py` (new). Do not
touch anything else — in particular not `build_alldata.py`, `synth.py`, `alldata_writer.py`
or `link_id_registry.py`.
Commit to the current branch when done evidence passes; push.
Depends on: 01 (`kiwiw.grid.ReferenceGrid` replaces the mounted-disc grid).
Runs alongside: 02, 03, 04, 05, 06.

## Required reading, in order

1. `docs/design/target-disc.md` — **Grid contract** (all levels from checked-in data, global
   cell indices, wrap at ±180°) and **Determinism**; "Decisions that shape everything" 2
   (regional subsets are fixtures behind explicit flags, never defaults).
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Execution Phases" row for unit 07
   verbatim; "Why This Plan Exists" gaps (4), (5), (6); Open Question **Anti-meridian
   coverage**; user-facing acceptance bullet 3 (no bbox or level flags, no reference mounted,
   per-level progress lines).
3. `parser/osm_to_parcel_geometry.py` — whole file. Note `_GeomHandler` collects every way
   in memory and `extract_parcel_geometry` is called once per level by the current build.
4. `parser/kiwiw/grid.py` (unit 01).
5. `parser/tests/test_parcel_geometry.py` — keep every existing assertion passing (they may
   be re-pointed at the new grid source).

## Goal

One pass over the Australia PBF produces per-parcel content for all seven levels, spooled
to disk so that memory stays bounded and the assembler can read parcels level by level. The
Perth bbox becomes an explicit fixture flag.

## Contract

Settled by the plan (original phase-3 text, carried here verbatim): "One PBF pass feeding all levels, streaming per-parcel
output, progress output unbuffered, bounded memory, longitude-wrap-safe tiling; a documented
run on the full Australia extract that completes on this machine with a recorded wall time
and output size."

Settled here (refine's calls):

- The grid at every level comes from `ReferenceGrid`; `build_tile_grid_from_lmr` and the
  mounted-disc default path are removed from this module. `TileGrid` keeps its interface
  (`nx`, `ny`, `cell_lat`, `cell_lon`, `assign_to_parcel`, `parcel_bounds`,
  `split_polyline_by_parcel`, `target_cells`) and gains a constructor
  `TileGrid.from_reference(level, target=None)` where `target=None` means the full
  coverage box.
- Per-level *selection* (which ways appear at which level) is unit 14's; here every level
  receives the same feature set, so unit 14 only adds a filter. Do not invent a selection
  rule; a `level_filter` hook (callable `(level, tags) -> bool`, default all-true) is the
  seam unit 14 fills.
- Spool format (`parser/kiwiw/spool.py`): a directory of per-level append-only files with
  one pickled `(ix, iy, content_dict)` record per parcel, plus an index file per level
  listing offsets, written by a single writer process; reader API
  `iter_level(level) -> Iterator[(ix, iy, content)]` in ascending `(iy, ix)` order and
  `stats()` per level. Records for the same parcel must be merged at write time or on read
  so a parcel appears once. Deterministic ordering is part of the contract.
- CLI defaults: `--pbf` stays (default `australia-260824.osm.pbf` in the repo root),
  `--levels` default `12 10 8 6 4 2 0`, no `--bbox` default (omitted = full coverage),
  `--fixture perth` sets the old Perth bbox, `--spool <dir>` default `output/spool/`.
- Progress lines every N ways (N = 1,000,000) and per level at tiling time, `flush=True`
  or `sys.stdout.reconfigure(line_buffering=True)`.

## Changes

### `parser/osm_to_parcel_geometry.py`

Restructure `_GeomHandler` so a way is tiled into every requested level as it is read
(not stored), accumulating per-parcel buckets that are flushed to the spool when a bucket
count threshold is exceeded, and finally at end of file. Nodes with `place=*` names are
handled the same way. Background rings and name centroids use the existing assignment
rules. Keep `HIGHWAY_TO_ROAD_TYPE`, `HIGHWAY_TO_DISPLAY_CLASS`, `_osm_tags_to_bg_type` and
`_make_*` exactly as they are (unit 08 replaces them with data tables; unit 11 changes name
records) — but route every call through them so the later swap is one-line. Use
`osmium.SimpleHandler` with `locations=True, idx="flex_mem"` as today, or switch to
`sparse_file_array` with a documented reason if resident memory exceeds 8 GB on the full
file. Remove `pickle` output of the whole dict; `extract_parcel_geometry(pbf, grids,
spool, level_filter=None)` returns the spool.

Longitude wrap: `_lon_delta`, `assign_to_parcel`, `parcel_bounds` already normalise; add a
test that a way crossing 180° E is assigned to cells on both sides with correct bounds.

### Tests

Existing `test_parcel_geometry.py` classes keep passing with `TileGrid.from_reference`.
`test_extractor_scale.py`: write a tiny synthetic PBF in-test with `osmium.SimpleWriter`
(three ways, one crossing 180° E, one named `place=suburb` node), run the extractor for
levels `[0, 2, 12]` into a temp spool, assert: each level has the expected parcels; a way
split across parcels yields the expected chains; `iter_level` order is deterministic across
two runs (byte-compare the spool files).

### Full-file run

Run `parser/osm_to_parcel_geometry.py --pbf australia-260824.osm.pbf --spool output/spool`
for all seven levels. Record wall time, peak RSS (`/usr/bin/time -v`), spool size on disk,
and per-level parcel/link/shape/name counts in your report.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `grep -n "DEFAULT_BBOX\|DEFAULT_ALLDATA\|build_tile_grid_from_lmr" parser/osm_to_parcel_geometry.py` → no default Perth bbox used as a default, no mounted-disc path.
- The full-file run completes with exit 0 and per-level progress lines; wall time and peak RSS recorded in the report. If it does not complete within 4 hours or exceeds available RAM, stop and report the numbers instead of narrowing scope.

## Report back

A short summary: the numbers above, the spool layout you settled, anything you deviated
from in this brief and why, and any contradiction you found between this brief and the
contracts it cites. **Do not resolve contradictions silently — report them.**
