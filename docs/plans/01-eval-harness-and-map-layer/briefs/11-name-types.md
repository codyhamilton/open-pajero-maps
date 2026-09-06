# Brief: 11 — Name records: string types 4/5/6 at level 0, per-level type from the profile

Consumer: implementation worker.
Owned paths: `parser/kiwiw/synth.py` (`build_name_frame_bytes` and new name-record
encoders only), `parser/kiwiw/name.py` (decoder: complete the type-4 placement-record
decode if needed for round-trip tests), `parser/kiwiw/model.py` (`NameRecord` only),
`parser/tests/test_name_encode.py` (new), and in `parser/osm_to_parcel_geometry.py` **only**
`_make_name_record`. Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 09 (synth.py edits must land first), 10 (model.py `RoadLink` edit first).
Runs alongside: 12.

## Required reading, in order

1. `docs/design/target-disc.md` — **Name records** (settled: types 4/5/6 as `R` does; "no
   type 1"), and **Unknown bytes policy**.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Open Questions → Refinement
   findings (2026-09-05)": string type 1 *is* what `R` uses at levels ≥2 (L2: {1, 5};
   L4–L12: {1}); level 0 is {4, 5, 6}. This narrows the design doc's "no type 1" to level 0;
   report it as a contradiction resolved by the profile, and cite the profile in the encoder
   docstring. Also the Open Question **Name string types 5 and 6**: "If the spec's placement
   semantics cannot be pinned down from Ch.7.4 and the reference, the format-analysis
   question goes to the user."
3. `spec/format_english/pdf/0704122e.pdf` — Ch.7.4 name data frame: string types 1, 4, 5, 6
   record layouts.
4. `parser/kiwiw/name.py` (current decoder for 1/4/5/6; type-4 placement records are counted
   but not decoded), `parser/refdata/profile/map.json` (`string_type` per level, name record
   size histograms).
5. `parser/kiwiw/synth.py` `build_name_frame_bytes`.

## Goal

Generated name frames use the reference's string types per level, with the type-4/5/6
record bodies encoded from a decoded model, not zero-filled.

## Contract

Per level, the set of emitted string types ⊆ the profile's set for that level (this is what
`checks/vocab.py` judges). Type choice per feature is data in the encoder's own small table
(road name → which type at level 0; place name → which type) justified from Ch.7.4 and from
sampling `R`'s level-0 records (which types carry which kinds of names). Placement fields
(type-4 placement records; type-5/6 position fields) are generated from the feature's
geometry using Ch.7.4's definitions. Round-trip: encode → `name.py` decode → same text,
type and placement values.

If, after reading Ch.7.4 and sampling `R`, a field's semantics cannot be pinned down, stop:
write what you have, list the field with the observed byte patterns, and report it as the
open format question the plan names. Do not zero-fill it and do not fall back to type 1 at
level 0.

## Changes

- `NameRecord` gains the fields needed to carry placement (type-4 placement list; type-5/6
  position) — additive, defaults preserve current decoding.
- `name.py`: decode type-4 placement records fully (if required for the round-trip test).
- `synth.py`: encoders for types 4, 5, 6; `build_name_frame_bytes(level, records)` selects
  type per record and level.
- `_make_name_record` passes geometry so placement can be derived.
- Tests: encode/decode round-trip for each type; per-level emitted-type subset test against
  the profile; a decoded `R` level-0 name record re-encoded is byte-identical (pick three
  records from the Brisbane parcel).

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `.venv-rp/bin/python parser/compare_disc.py --generated output/ALLDATA.KWI --checks vocab` on a level-0 build → string-type part of `vocab` PASS (or the report names the blocked field).

## Report back

A short summary: the type-selection table and its evidence, any placement field you could
not pin down (with bytes), anything you deviated from in this brief and why, and any
contradiction you found between this brief and the contracts it cites — including the
"no type 1" narrowing. **Do not resolve contradictions silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
