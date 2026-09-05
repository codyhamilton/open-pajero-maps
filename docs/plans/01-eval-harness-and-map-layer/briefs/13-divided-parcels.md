# Brief: 13 — Divided parcels (types 1..3) for oversize Map Frames

Consumer: implementation worker.
Owned paths: `parser/kiwiw/divide.py` (new), `parser/tests/test_divide.py` (new), and in
`parser/kiwiw/alldata_writer.py` **only** the `divided` code path the unit-12 signature
reserved, plus in `parser/build_alldata.py` **only** the call that invokes `divide` before
handing parcels to the writer. Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 12.
Runs alongside: 14.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` — section 6 (divided/integrated
   parcels: sub-grids, `R`'s per-level occupancy, the rule WP1 applies).
2. `docs/design/target-disc.md` — **Capacity accounting**; file-table row on the map layer's
   parcel-management records.
3. `spec/format_english/pdf/0600122e.pdf` — Ch.6 parcel management: divided parcel
   subrecords (size==0 → subrecord recursion, as `parse_parcel_mgmt_record` implements).
4. `parser/kiwiw/volume.py` `parse_parcel_mgmt_record`, `parser/kiwiw/disc.py`
   `find_parcel` (how the reader descends into subrecords).
5. `parser/refdata/grid.json` (`n_parcels` per type: 2×2, 4×4, 1×1 at every level) and
   `parser/refdata/profile/map.json` (per-level Map Frame size histogram; parcel-type
   occupancy).
6. `parser/kiwiw/alldata_writer.py` after unit 12.

## Goal

A level-0 (or any level) cell whose Map Frame would exceed the per-level maximum observed on
`R` is split into the divided sub-grid the LMR declares, so the generated disc never emits
a frame larger than any the head unit has been observed to read.

## Contract

`DESIGN.md` section 6 rule (binding): the size threshold per level and the type order.
`divide.py`: `plan_divisions(level, parcels: Iterator[(ix, iy, content)], threshold_bytes,
encode) -> Iterator[(ix, iy, parcel_type, sub_ix, sub_iy, map_frame_bytes)]` where the
content is re-tiled into the sub-grid using the extractor's existing per-parcel splitting
rules (import `TileGrid.split_polyline_by_parcel` semantics via a local sub-grid; do not
modify the extractor). Link ordinals are preserved from the spool (a chain split again
inside a divided parcel keeps its `(osm_way_id, ordinal)` and is emitted as one link per
sub-parcel; note this in the docstring for WP2). The writer emits subrecords in the Ch.6
form and `find_parcel` on the result descends to the right sub-parcel.

## Changes

- `divide.py` as above; deterministic.
- Writer `divided` path: management record with size 0 and subrecord table per Ch.6.
- Build CLI: apply `plan_divisions` per level with the threshold from the profile.
- Tests: an oversize synthetic parcel at level 0 is split into type-1 2×2; `find_parcel`
  on the built disc returns the sub-parcel containing a probe coordinate; a parcel under the
  threshold stays type 0; harness `decode` and `pointers` pass on the test disc.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- Perth fixture rebuilt and `compare_disc.py --checks decode,pointers,shape,envelope` → PASS, with the report stating how many parcels were divided per level and the max frame size before/after.

## Report back

A short summary with those numbers, anything you deviated from in this brief and why, and
any contradiction you found between this brief, `DESIGN.md` and Ch.6. **Do not resolve
contradictions silently — report them.**
