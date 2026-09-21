# Brief: 2-05 — L0 sparse coordinate frame in `harness/walk.py`

Consumer: implementation worker; result consumed by 2-06, 2-08 and 2-04.
Owned paths: `parser/harness/walk.py`, `parser/tests/test_harness_profile.py` (add tests; do not weaken existing ones), a new `parser/tests/test_harness_walk.py` if you prefer a separate file, `parser/tools/road_density_census.py`, `parser/refdata/profile/density.json`. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing (2-01 and 2-02 are already done and committed).
Runs alongside: 2-07.
Budget: 8 files to read, about 150 lines to change, 40 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-22 (user) — Phase 2 restart", item 2 (first half).
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the `2-03 overlay-test` record (the "Bug found, not fixed" paragraph and the "L0 sparse frame is the 4x4 integrated parcel tile at 16384" finding), and the `2-01 coord-range-census` record.
3. `parser/harness/walk.py` — `_block_base_bounds`, `_narrow_bounds`, `WalkedParcel`, `_iter_tree_leaves`, `iter_parcels`.
4. `parser/tests/test_harness_profile.py` lines 296–345 — the recorded "aliased leaf slots" behaviour (several leaf slots legitimately share one on-disc Map Frame byte range) and why every other consumer needs per-leaf semantics.
5. `parser/tools/coord_scale_census.py` — `_raw`, `parcel_measure`, `l0_tile`, `L0_TILE`/`L0_GRID_W` (read only; it is **not** yours), and `parser/tools/road_density_census.py` — `parcel_metrics`, `_class_range` (yours).
6. `parser/refdata/profile/coord_scale.json` — `ranges` and `class_rule` (read only).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make `harness.walk` model the L0 sparse *coordinate frame* separately from the *leaf* it yields, so that every consumer can tell "the geographic cell this leaf owns" from "the bbox and range this Map Frame's stored coordinates are expressed in", and re-derive the one checked-in artefact whose numbers depend on that distinction.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-22 item 2: "Two known bugs are fixed before the overlay is re-run. `parser/harness/walk.py` L0 sparse frame bounds (all 16 slots are given the tile's bounds; the L0 sparse *frame* is the 4x4 tile at 16384)".

Cited, 2-03's recorded evidence (`IMPLEMENTATION.md`): "**L0 sparse frame is the 4x4 'integrated parcel' tile at 16384**, not the leaf: own_leaf_16384 0.004/1249 m; own_leaf_4096 0.306/34.5 m but coord_max 4.0 (out of range); tile4x4_16384 0.717/26.5 m, coord_max 1.0; tile4x4_4096 0.0/14414 m. 16384 = 4 x 4096 and the tile is the same one the 2-01 class rule keys urban/sparse on." And: "`harness/walk.py` assigns all 16 leaf slots of an L0 *sparse* tile the same Map-Frame bbox — `inside_cell_fraction` 0.038 for that class — i.e. leaf bounds for L0 sparse are the tile's, not the leaf's."

Settled by that evidence and not to be re-litigated: the L0 sparse frame is the 4x4 integrated-parcel tile and its coordinate range is 16384 (`coord_scale.json` `ranges` `0.sparse.normal.max`).

**Not settled, and you must establish it from R before changing code:** *why* walk currently yields the tile bbox as a leaf bbox — which of `_block_base_bounds`, `_narrow_bounds`, the mapinfo grid dimensions (`lmr.n_parcels_lat/lng`) or the tree depth is the actual cause — and what the correct per-leaf 1/16 bbox is. Do not assume a mechanism. Record the recon result (a short paragraph with numbers from R) in your report and in the code comment.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the generated disc G is `output/ALLDATA.KWI`. Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Harness reading paths must not import writer modules. Tool output is deterministic (sorted keys, no timestamps).

## Changes

- Recon first, on R, read-only: determine the real L0 leaf grid and how the 16 aliasing slots of one sparse tile are represented in the parcel-management tree. State the numbers (tile grid dimensions, leaf grid dimensions, how many distinct `(file_offset, length)` ranges a tile's slots resolve to). If the evidence contradicts "4x4 tile at 16384", stop and report `blocked` with the numbers — this is a gate phase and the model is not patched to fit.
- Make the leaf/frame distinction explicit in `WalkedParcel`. `WalkedParcel.bounds` must keep meaning **the geographic extent of the leaf slot itself** — that is what `decode`/`pointers`/`shape`/`vocab`/`mfde`/`spotcheck` need and what `test_harness_profile.py`'s aliasing note calls "correct per-leaf semantics". Add the frame as new, separately named state (bbox **and** range, or bbox plus enough to derive the range from `coord_scale.json`), defaulting to the leaf's own bbox and the class range for every class where frame == leaf. Do not repurpose `bounds`.
- `MeshLocation.bounds` is passed to `decode_parcel`, which converts stored pixels to lat/lon. Decide, and state in the code, which of leaf or frame bounds it must receive so decoded lat/lon are geographically correct, and make it so. This is the seam that produced `inside_cell_fraction` 0.038; getting it right is the point of the unit.
- Add a docstring on `WalkedParcel` naming the two bboxes and saying, in one sentence each, what a consumer should use each for.
- `parser/tools/road_density_census.py`: `parcel_metrics` derives kilometres from `wp.bounds` spans divided by a class coordinate max. Under the corrected model the span and the range must come from the *same* frame. Fix it and regenerate `parser/refdata/profile/density.json`. Report the before/after L0 vertices-per-km (HEAD is L0 41.05) and say whether any other level moved. This closes Phase 1 Carried item 4 ("L0 road-length census uses an unverified 16384 range heuristic; Phase 2 must validate and re-derive density.json if changed"); say so explicitly in your report.
- Check, by running it, whether `parser/tools/coord_scale_census.py` regenerates `parser/refdata/profile/coord_scale.json` byte-identically after your change (its `_raw` inverts the same transform it decoded with, so the maxima should be invariant). If it does not, **do not edit it** — report `needs context` with the diff: `coord_scale.json` is 2-01/2-02's artefact and a change there is a gate finding, not a fix.

### Keep untouched

`parser/harness/walk.py`'s streaming contract (one leaf decoded at a time, nothing retained across iterations) and its progress lines — `iter_parcels` runs over the whole disc and must not start buffering. The existing tests in `test_harness_profile.py`, including the aliased-leaf-slot dedupe test, must keep passing unmodified. `coord_scale.json`, `harness.json`, `parser/kiwiw/**` and `parser/harness/checks/**` are not yours.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- A new test that fails on HEAD and passes after: for an L0 sparse tile, the 16 leaf slots have 16 *distinct* leaf bboxes tiling the frame, the frame bbox is the same for all 16, and the frame is 4x the leaf in each axis. Use a synthetic fixture or a monkeypatched `iter_parcels` in the style of `test_mapframes_bytes_total_dedupes_aliased_leaf_slots`; if `alldata_writer` cannot build the shape you need, say so in the test comment as that test does.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts before and after).
- An R measurement, before and after, of the share of decoded L0 sparse road vertices that fall inside the leaf bbox they were yielded under, over at least 50 sparse tiles chosen by a stated position rule. HEAD's figure is 2-03's 0.038. State the rule and both numbers.
- `.venv-rp/bin/python parser/tools/road_density_census.py` (check its `--help` for the actual invocation) run twice with identical output; `density.json` before/after values reported.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. Include the recon paragraph (what the real cause was) and the density.json before/after.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
