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
6. `parser/kiwiw/alldata_writer.py` after unit 12, specifically `_build_alldata_kwi_multilevel`
   (the function whose docstring reserves the divided-parcel path, but which does **not** yet
   take a `divided` parameter — you are adding that parameter, not filling in one already
   there; see "Amendment" below).
7. Unit 12's outcome in `IMPLEMENTATION.md` (the "Unit 12" section) — it hit and documented
   the exact crash this unit exists to fix; read it before touching `synth.py`'s call sites.

**Amendment (post-12, orchestrator):** unit 12's done evidence hit a real, reproducible crash
this unit is the fix for: `parser/kiwiw/synth.py:851`, `build_map_frame_bytes()` —
`buf[0:2] = _u16(total_size // 2)` raises `ValueError: N does not fit in u16` whenever a
frame's `total_size` exceeds 131,070 bytes (a hard **format** ceiling — the header's size
field is a 16-bit word count, independent of anything the profile says about typical frame
sizes). This reproduced on the unmodified Perth spool in two ways worth knowing about before
you pick a threshold:

- An individual dense level-0 (CBD) parcel hit ~133,240 bytes — *inside* the profile's
  observed level-0 `mapframe_size.max` (136,096 bytes) but still over the 131,070-byte u16
  ceiling. This means **the threshold you divide against must be
  `min(profile mapframe_size.max for the level, 131070)`, not the profile max alone** — the
  format cannot represent an undivided frame anywhere near the profile's observed max at
  level 0, so some of `R`'s own level-0 parcels the profile measured are themselves already
  divided sub-frames, not whole-cell frames. Do not thin this out with unit 14's selection
  logic — this is `synth.py`'s frame-size threshold, not per-level census matching.
- Level 12's single global parcel (the fixture's entire unthinned content, since level 12 has
  exactly one cell) hit **39,555,559 bytes — roughly 300x the u16 ceiling**. Type-1 (2×2) or
  even type-2 (4×4) division only buys back a 4x–16x reduction; neither gets a 300x-oversize
  frame under budget alone. Report this rather than trying to force it: level 12 in particular
  is expected to need unit 14's per-level feature selection *in addition to* your division,
  and your own done evidence at level 12 may still show an overshoot after division — that is
  expected and not a bug in your work, so state the achievable numbers and don't block on it.

## Goal

A level-0 (or any level) cell whose Map Frame would exceed the per-level maximum this format
can represent is split into the divided sub-grid the LMR declares, so the generated disc never
emits a frame the header can't size.

## Contract

`DESIGN.md` section 6 rule (binding): the size threshold per level and the type order, capped
per the Amendment above at the format's 131,070-byte u16 ceiling. `divide.py`:
`plan_divisions(level, parcels: Iterator[(ix, iy, content)], threshold_bytes,
encode) -> Iterator[(ix, iy, parcel_type, sub_ix, sub_iy, map_frame_bytes)]` where the
content is re-tiled into the sub-grid using the extractor's existing per-parcel splitting
rules (import `TileGrid.split_polyline_by_parcel` semantics via a local sub-grid; do not
modify the extractor). Link ordinals are preserved from the spool (a chain split again
inside a divided parcel keeps its `(osm_way_id, ordinal)` and is emitted as one link per
sub-parcel; note this in the docstring for WP2). The writer emits subrecords in the Ch.6
form and `find_parcel` on the result descends to the right sub-parcel.

## Changes

- `divide.py` as above; deterministic.
- Writer `divided` path: add the `divided` parameter to `_build_alldata_kwi_multilevel`
  (there is no existing parameter to fill in — add it without changing the call shape for
  callers that omit it) — a management record with size 0 and subrecord table per Ch.6.
- Build CLI: apply `plan_divisions` per level with the threshold from the profile, capped at
  the u16 ceiling per the Amendment.
- Tests: an oversize synthetic parcel at level 0 is split into type-1 2×2; `find_parcel`
  on the built disc returns the sub-parcel containing a probe coordinate; a parcel under the
  threshold stays type 0; harness `decode` and `pointers` pass on the test disc; a synthetic
  parcel oversize even after 4×4 division (mirroring the level-12 case above) is left as the
  largest available division and does not crash the writer.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- Perth fixture rebuilt and `compare_disc.py --checks decode,pointers,shape,envelope` → PASS
  at every level **except possibly level 12** (per the Amendment, level 12 may still overshoot
  after maximal division since unit 14 hasn't landed yet) — report per-level parcel-divided
  counts and max frame size before/after, and if level 12 still overshoots after division,
  say so explicitly with the numbers rather than treating it as a failure to resolve here.

## Report back

A short summary with those numbers, anything you deviated from in this brief and why, and
any contradiction you found between this brief, `DESIGN.md` and Ch.6. **Do not resolve
contradictions silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
