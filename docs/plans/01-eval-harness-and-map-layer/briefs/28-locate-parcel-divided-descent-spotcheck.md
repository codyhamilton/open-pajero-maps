# Brief: 28 -- Fix `mesh.locate_parcel` divided-parcel descent (spotcheck Brisbane/Sydney/Melbourne L0)

Consumer: implementation worker (code + tests; NO rebuild, do NOT touch `output/`).
Owned paths: `parser/kiwiw/mesh.py` (only `locate_parcel`), `parser/tests/test_mesh.py`
(+ a new `parser/tests/test_mesh_divided_locate.py` if cleaner). Do not touch `parser/harness/`,
`parser/refdata/spot_checks.json`, `parser/kiwiw/divide.py`, `synth.py`, `build_alldata.py`.
Commit and push code+tests when `pytest parser/tests -q` passes.
Depends on: 26b record. Runs alongside: 29, 30 (disjoint files). Needs no rebuild: it is verified
against the existing `output/ALLDATA.KWI` (read-only).

## Diagnosis (evidence, 2026-09-19, live `output/ALLDATA.KWI`)

The 26b "L0 missing road names" spotcheck FAIL is NOT a data/admission/name-gate problem. G contains the
names; the *reader* returns the wrong sub-frame for divided parcels.
- The three failing spot cells are divided (Brisbane cell (2016,1081), Sydney (1958,774), Melbourne (1758,584); fixed-locate
  results are type-2 sub-frames; 2/4/2 distinct populated sub-frames per cell). Perth/Adelaide/Hobart/Darwin
  spot cells are undivided (type 0) and pass.
- `AllData.find_parcel(-33.8688,151.2093,level=0)` returns `location.bounds` = lat
  [-33.87280,-33.87272] lon [151.19409,151.19434] (a ~9 m box, cell/128 wide) that does NOT contain
  the query point; its 190 road nodes sit inside that wrong box, `parcel_index` clamps to the last
  index (15/12/3). Same pattern for Melbourne and Brisbane.
- Cause: `mesh.py::locate_parcel` depth==1 subparcel descent (the `Subparcel: descend` block,
  ~L221-230). For a type-0 top-level record whose entry has `size == 0`, `bounds` is already the
  (ix,iy) cell, but the code narrows it again with `lpx=px, lpy=py` and `gn_lng/gn_lat` of the
  *type-0* record (`npc_*`), shifting/shrinking the box; `local_lat_frac/lon_frac` then
  fall far outside [0,1] and clamp. At depth>1 the narrowing is correct.
- Proof of fix (monkeypatched copy, `/tmp/diag28/spot5.py`): when depth==1 sets `new_bounds = bounds`
  (no narrowing), find_parcel returns bounds that contain the spot and every expected name is present
  (Brisbane: Queen Street, Adelaide Street; Sydney: York/Kent/Elizabeth Street; Melbourne: Queen/
  Swanston/Collins Street), all with `parcel_type` 2 sub-frames of 447/761/1076 names.
- Corroboration: the wrong-sub-frame frames' data are valid; per-cell union of quadrants contains
  Queen Street (Brisbane). No extractor/selection change is needed.

## Changes
1. In `locate_parcel`, at `depth == 1` set `new_bounds = bounds` (the cell derived from ix/iy already
   is this record's cell) instead of re-narrowing; keep the depth>1 narrowing. Update the stale
   comment block. Do not change the leaf-branch narrowing (`if depth > 1 or pt != 0`).
2. Tests: synthetic divided-parcel fixture (type-0 root entry size==0 -> pardiv type 1 (2x2) and type 2
   (4x4)) asserting for a point in each quadrant that `location.bounds` contains the point and
   `parcel_index` = `lpy*gn_lng+lpx` of that quadrant; a depth-3 (subparcel-of-subparcel) case; and
   that undivided results are unchanged. Reuse `divide.py`/`synth` builders, not hand-built bytes,
   if the existing test_mesh.py helpers allow.
3. Regression on R (read-only, `/run/media/codyh/464210-8480/ALLDATA.KWI`, mount may be absent -> skip):
   for R's 52 L0 type-1 leaves (use `harness.walk.iter_parcels`, break after level 0's divided ones
   are seen, or sample a few), `find_parcel` at each leaf's bounds centre must now return the frame
   with that leaf's `file_offset`. Report how many of R's divided leaves resolved wrongly before the
   fix (informational).
4. Verify end-to-end without a rebuild: `python parser/compare_disc.py --reference
   /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --checks spotcheck --report
   /tmp/spotcheck-28.json` -> expect PASS (all 14 rows). Do not write to `output/`.

## Done evidence
pytest green; before/after `find_parcel` bounds for the three cities; spotcheck-only run PASS.

## Report back
Whether R divided-leaf resolution changed; any other caller of `locate_parcel`
(`roundtrip_parcel_content.py:185`, `kiwiw/disc.py`) whose tests moved.
