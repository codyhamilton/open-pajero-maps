# Brief: 09 — Map Frame shape per `DESIGN.md` (mfde table, region list, slot values)

Consumer: implementation worker.
Owned paths: `parser/kiwiw/synth.py` (functions `build_map_frame_bytes` and any new
helpers it needs; do not change `build_road_frame_bytes`, `build_background_frame_bytes`,
`build_name_frame_bytes`), `parser/tests/test_synth_map_frame.py` (new). Do not touch
anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 06 (`DESIGN.md` is the spec for this unit), 03b (`checks/mfde.py` judges it against the committed profile).
Runs alongside: 08, 10.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` — sections 2, 3, 4, 7 in full;
   every emission decision there is binding.
2. `docs/design/target-disc.md` — **Unknown bytes policy**, **Determinism**.
3. `parser/kiwiw/synth.py` `build_map_frame_bytes` and `parser/kiwiw/parcel.py`
   `decode_parcel` (the decoder derives the mfde table length from the lowest in-buffer
   sub-frame offset — the encoder's layout must keep that derivation valid).
4. `parser/kiwiw/parcel_writer.py` `write_map_frame` (round-trip mode; must stay untouched
   and must still pass its tests).
5. `parser/harness/checks/mfde.py` (unit 03).

## Goal

The synthetic Map Frame has the reference's shape at every level: the right mfde table
length, the header fields and region list `DESIGN.md` specifies, and the absent-slot value
in every entry WP1 does not generate.

## Contract

`DESIGN.md` section 4 per-index table (binding). Signature change (settled here):
`build_map_frame_bytes(level, llpid, llcode, road_bytes, bg_bytes, name_bytes, *,
region_list=None, ext_frames=None)` where `ext_frames` is `{index: bytes}` for in-buffer
Extended Data Frames (unit 12 passes none; WP2 fills it) and `region_list` is the encoded
bytes from `DESIGN.md` section 3 (`None` → what `DESIGN.md` says WP1 emits at that level).
Output must decode with `decode_parcel` to a `Parcel` whose `mfde_n`, `nregion`, and
per-entry `(offset, size)` match the profile's presence classes for that level, and whose
road/bg/name sub-frames round-trip byte-identically to the inputs. Deterministic: same
inputs → same bytes.

## Changes

- Rewrite the mfde layout code to size the table from `DESIGN.md`'s per-level length and
  fill each index from the decision table (basic frames 0..2; ext frames from `ext_frames`
  with in-buffer offsets; everything else absent value).
- Emit header fields and region list per `DESIGN.md` sections 2–3.
- Tests: for each level in `12 10 8 6 4 2 0`, build a frame from fixture sub-frames, decode
  it, assert table length / nregion / per-index presence match `DESIGN.md`; assert
  `ext_frames={4: b"..."}` produces an in-buffer entry 4 that decodes into `ext_frame_raw`;
  determinism (two builds byte-equal); existing round-trip tests untouched and passing.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `.venv-rp/bin/python parser/compare_disc.py --generated output/ALLDATA.KWI --checks mfde` on a fresh single-level build (existing `build_alldata.py --levels 0` path, unmodified) → `mfde` PASS at level 0. (Other levels come with unit 12.)

## Report back

A short summary: what you changed, anything you deviated from in this brief and why, and
any contradiction you found between this brief, `DESIGN.md` and the decoder. **Do not
resolve contradictions silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
