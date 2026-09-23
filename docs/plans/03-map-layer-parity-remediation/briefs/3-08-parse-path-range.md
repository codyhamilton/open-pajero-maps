# Brief: 3-08 — the parse path takes each frame's real range (`PARSE_RANGE` dies)

Consumer: 3-07 (starts from the tree this unit leaves); 3-06, which runs the phase's source check.
Owned paths: `parser/kiwiw/parcel.py`, `parser/kiwiw/alldata_writer.py`, `parser/kiwiw/mesh.py`, `parser/kiwiw/disc.py`, `parser/harness/**` (only as needed to share frame-range logic), `parser/roundtrip_parcel_content.py`, `parser/roundtrip_alldata_full.py`, and the tests that reference `PARSE_RANGE` or break with this change — `parser/tests/test_name_encode.py`, `test_road_encoder.py`, `test_name_encoder.py`, `test_background_encoder.py`, `test_alldata_writer.py`, `test_parcel_mask.py`, `test_harness_*.py`, `test_roundtrip_*.py`, `test_mesh_*.py` — plus `parser/tests/test_harness_coord_scale.py` for the fix below. Touch nothing else; if another file must change, report `needs context`.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-03.
Runs alongside: nothing.
Budget: 10 files to read, about 250 lines to change, 50 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "#### Phase 3 — Outcome, as amended" and "#### New grounded rule: one global raw lattice per level".
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-01 and 3-03 records.
3. `parser/kiwiw/parcel.py` (`PARSE_RANGE`, the parse path around line 155), `parser/kiwiw/alldata_writer.py` (its two `PARSE_RANGE` uses), `parser/kiwiw/mesh.py` `locate_parcel`, `parser/harness/walk.py` `leaf_frame_range` / `_leaf_frame` / `with_range`.

Read ranges and grep; do not read whole files.

## Goal

3-03 left `kiwiw/parcel.py` decoding every parcel at a named `PARSE_RANGE = 32768` because the `mesh.locate_parcel` parse path knows only the leaf box, not the frame's shape. That is the retired legacy range under a new name, and the Phase 3 outcome's "`range_for` … no `COORD_RANGE` constant remains" is a statement that no hard-coded coordinate range survives. Make the parse path take each parcel's real frame range from the same single source the harness walk uses (`walk.leaf_frame_range` → `coordconv.range_for`), and delete `PARSE_RANGE`.

## Contract

- One source of a range: `coordconv.range_for`, reached through the frame logic `walk` already has (L0 frame class by structure — a frame shared by a 4x4 tile of slots is sparse/16384, otherwise 4096; divided sub-parcels decode against the parent slot at 4096). Move or share that logic rather than copying the class arithmetic; if the parse path genuinely cannot know the frame shape, derive it the way `walk` does from the same Map-Frame sharing, and say how.
- `alldata_writer` re-encodes with the same range it decoded with, so parse → re-encode stays byte-preserving.
- Fix `parser/tests/test_harness_coord_scale.py::test_unranged_class_fails`: `pardiv2` is now ranged (4096, per the 3-03 amendment); make the test exercise a genuinely unranged frame (e.g. an unknown level or malformed division state) so the check's unranged-FAIL path stays covered.
- Reference disc R at `/run/media/codyh/464210-8480`; spool `output/extract_timing/spool`; Python `.venv-rp/bin/python`; scratch under `output/scratch-3-08/` with `TMPDIR` there. Never edit `.claude/worktrees/`.

## Done evidence

- `git grep -nE "PARSE_RANGE|32768" -- parser/kiwiw parser/harness` — report verbatim; every remaining `32768` must be prose or a bit flag, not a coordinate range.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes with 0 failures (report before/after: before is 462 pass / 1 fail).
- The full-ALLDATA round-trip (`parser/roundtrip_alldata_full.py` or its test, whichever is the existing entry point) still reproduces bytes; report.
- Decode a sample of R parcels through the parse path and through `walk.iter_parcels` and show the lat/lon agree (L0 urban, L0 sparse, a divided sub-parcel, an L6 leaf).

## Report back

Under 1,000 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, check output before and after, deviations, contradictions. Never resolve a contradiction silently. Do not spawn agents beyond read-only research helpers.
