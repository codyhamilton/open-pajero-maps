# Brief: 3-01 — `range_for` and the decode side taking its range from the frame

Consumer: 3-02 and 3-03, which make the encoders call `range_for` and the range-taking conversions; 3-04, which writes the `coord_scale` check and the quantisation round-trip tool against this API.
Owned paths: `parser/kiwiw/coordconv.py`, `parser/kiwiw/road.py`, `parser/kiwiw/background.py`, `parser/kiwiw/name.py`, `parser/kiwiw/model.py`, `parser/harness/walk.py`, `parser/tools/coord_scale_census.py`, `parser/tools/continuity_census.py`, `parser/tools/boundary_mirror_census.py`, `parser/tools/road_density_census.py`, `parser/tools/overlay_test.py`, `parser/tests/test_harness_walk.py`, `parser/tests/test_harness_core.py`, `parser/tests/test_coord_scale_census.py`, and a new `parser/tests/test_coordconv.py`. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing (Phase 2 is closed at `a9f5e03`).
Runs alongside: nothing.
Budget: 12 files to read, about 400 lines to change, 60 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "### Domain: Native encoding model" (the `range_for` contract), "#### Phase 3 — Outcome, as amended", and "#### New grounded rule: one global raw lattice per level" in the 2026-09-23 design-agent amendment. These three are the contract.
2. `parser/refdata/profile/coord_scale.json` — `ranges` (28 classes) and `class_rule` in full. This is the checked-in source of truth; do not re-derive it and do not regenerate it.
3. `parser/kiwiw/coordconv.py` — all 90 lines, including the docstring recording the settled y-up orientation (2-06).
4. `parser/harness/walk.py` — `L0_TILE`, `_tile_bounds`, `_is_sparse_tile`, `_leaf_frame`, `_frame_range`, `WalkedParcel.__post_init__`, and the decode call site around line 333 carrying the comment "the decoder's own 2**15 range vs frame_range is Phase 3's".
5. `parser/kiwiw/road.py`, `background.py`, `name.py` — the five `xy_to_latlon` call sites only (grep; do not read the files whole).
6. `parser/tools/road_density_census.py` lines 20–95, `parser/tools/coord_scale_census.py` `_work` and its raw recovery, `parser/tools/overlay_test.py` `DECODER_RANGE` / `control_32768` / `model_frame` / `class_range`, and the `ot.DECODER_RANGE` uses in `parser/tools/continuity_census.py` and `parser/tools/boundary_mirror_census.py`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Give the codebase one function that answers "what is this parcel's coordinate range", and make every decode-side reader take its range from that function instead of from a hard-coded 2^15. The encoders are 3-02's and 3-03's; this unit does not touch them.

## Contract

Cited, DESIGN.md, "### Domain: Native encoding model":

> `coordconv.range_for(level, parcel_class)` replaces `COORD_RANGE`; the C encoder receives it as a parameter, not its own constant

and, in the same domain's interface list:

> `range_for(level, parcel_class, division_state) -> int`

Cited, DESIGN.md, the 2026-09-23 design-agent amendment, "#### New grounded rule: one global raw lattice per level":

> At every level, R's raw coordinate resolution is 4096 raw units per top-level leaf slot. A coordinate frame covers an n x n block of slots and carries range `n x 4096`: n = 1 for a basic parcel (L0 urban, an L2–L8 leaf, a divided parent), n = 4 for an L0 sparse integrated-parcel tile, giving `4 x 4096 = 16384`. A parcel's global coordinate is `X = gx0 * 4096 + x_local`, `Y = gy0 * 4096 + y_local`, where `(gx0, gy0)` is the frame's south-west leaf slot on the level's global leaf grid.

Binding, and settled — do not re-derive any of it:

- **`range_for` returns the frame's divisor, not an observed maximum.** `coord_scale.json`'s `ranges[level][class][division]["max"]` is what R was *observed* to reach; for `pardiv1_sub0` that is **2048**, because a sub-parcel's coordinates live in the parent's 4096 frame and the SW quadrant only occupies its lower half. `range_for` for any divided sub-parcel returns **4096** (the parent's frame), never 2048. Dividing a coordinate by an observed maximum is the defect this unit exists to prevent. Say this in `range_for`'s docstring.
- The class is content-independent and comes from `coord_scale.json`'s `class_rule`: level 0 is `urban` when the leaf's aligned 4x4 tile is in `urban_tiles`, else `sparse`; every other level is `full`. Division state is `normal` or `pardiv<type>_sub<idx>`. Use `class_rule` as the rule; do not write a second copy of the tile arithmetic — reuse `walk`'s `L0_TILE` / `_is_sparse_tile` machinery, which 2-13 already reconciled against `class_rule`.
- **`range_for` reads `coord_scale.json`.** It is loaded once and memoised. If a `(level, class, division_state)` triple is absent from `ranges`, raise — do not fall back to a default.
- Range is a **required** argument of `xy_to_latlon`, `latlon_to_xy` and `encode_region_coord`. Every call site this unit owns passes it explicitly.
- `encode_region_coord`'s `(xc % 4096) | ((xc // 4096) << 13)` packing is unchanged. What changes is its validity bound: the admissible interval becomes `0 <= xc <= coord_range` **inclusive**, not `coord_range - 1`. R's own census shows `share_at_max = 1.0` and `observed_peak == max` in nearly every class, and criterion 4 requires boundary nodes to sit exactly on the frame edge. `encode_region_coord(4096, 4096)` is region 1, value 0, and is legal.
- y increases northward. That is 2-06's settled result, recorded in `coordconv.py`'s docstring with pooled 2-03 evidence; do not revisit it, and do not let a signature change quietly drop it.

**Staged migration, deliberate.** Removing `COORD_RANGE` outright would break `synth.py`, `road_writer.py`, `background_writer.py` and `osm_to_parcel_geometry.py`, which this unit does not own. So:

- Delete the public name `COORD_RANGE` and replace it with a single module-private `_LEGACY_RANGE = 32768` in `coordconv.py`, commented `# TEMPORARY -- deleted by unit 3-03; no caller may rely on it`.
- Give the three conversion functions a keyword-only `coord_range` parameter defaulting to `_LEGACY_RANGE`, so unmigrated encoder call sites keep their exact present behaviour and the build stays byte-identical after this unit.
- Every call site **you own** passes `coord_range` explicitly. None of them relies on the default.
- 3-03 deletes `_LEGACY_RANGE` and the defaults. Do not leave a second copy of the number anywhere else.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. Generated disc G is `output/ALLDATA.KWI`, sha256 `51c254ac87328f652e88f0b10880e83992622bcd1d2db2dbd519edc0a5672743`. Python is `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`.

## Changes

- `coordconv.py`: `range_for(level, parcel_class, division_state='normal') -> int`; range-taking `xy_to_latlon` / `latlon_to_xy` / `encode_region_coord`; inclusive `[0, coord_range]` bound; `_LEGACY_RANGE` as described.
- `road.py`, `background.py`, `name.py`: the decode sites take the range from the parcel's frame rather than assuming 2^15.
- `model.py`: `MeshLocation` (or whatever the decoders already receive) carries the frame's coordinate range alongside `bounds`, so a decoder is never asked to guess. Adding a field with a default keeps existing constructors valid; prefer that over changing every constructor.
- `harness/walk.py`: the decode call site at ~line 333 passes `frame_range`; delete the "Phase 3's" comment, because it is now done.
- The four `parser/tools/` census tools: their raw recovery must invert with the **same** range the decoder used, or every Phase 2 number moves. Replace `DECODER_RANGE` with the per-parcel frame range. `overlay_test.py`'s `control_32768` is a deliberately-named control and keeps its meaning — if reproducing it now requires something other than the literal 32768, say so in the report rather than redefining the control.

### Keep untouched

`parser/kiwiw/synth.py`, `road_writer.py`, `background_writer.py`, `cenc.py`, `_cenc.c`, `divide.py`, `spool.py`, `parser/osm_to_parcel_geometry.py`, `parser/build_alldata.py` — 3-02 and 3-03 own those. `parser/refdata/profile/*.json` — read-only here; regenerate nothing. `parser/tools/r_neighbours.py` (2-13's, its 32768 is prose). `GATE-2.md`, `EVIDENCE-2-*.json`, `DESIGN.md`, `IMPLEMENTATION.md`.

`1 << 15` in `parser/kiwiw/volume.py`, `volume_writer.py`, `route_planning.py` and `parser/osm_to_route_planning.py` are **bit flags, not coordinate ranges**, and `COORD_RANGE_RL = 4096` in `parser/tools/header_word_census.py` is a route-planning-layer constant. None of them is in scope. Do not touch them, and say so in your report so the phase's "no `COORD_RANGE` constant remains" source check is not later confused by them.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- New `parser/tests/test_coordconv.py` passes, covering: `range_for` returning 16384 for L0 sparse normal, 4096 for L0 urban normal, 4096 for every other level's `full` normal, and **4096 (not 2048) for `pardiv1_sub0`**; an absent triple raising; `encode_region_coord(4096, 4096)` == region 1 / value 0 and `encode_region_coord(-1, ...)` / `(4097, 4096)` raising; a lat/lon → xy → lat/lon round-trip at ranges 4096 and 16384 landing within half a pixel; and y increasing northward at both ranges.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes. The pre-existing count is 407; report before and after.
- `.venv-rp/bin/python parser/tools/coord_scale_census.py --reference /run/media/codyh/464210-8480 --out <scratch>/coord_scale.json --workers 10` — `ranges`, `class_rule` and `exceeds_max` (0 in all 28 classes) structurally identical to `parser/refdata/profile/coord_scale.json`. They must be: the raw values on R did not change, only the two sides of the conversion.
- Re-run the continuity and boundary-mirror censuses against R with the same arguments 2-14 used and compare to the sha256 values recorded in `EVIDENCE-2-14.json` (`da70cd59…` continuity, `23854cf5…` mirror). **State plainly whether each reproduces.** If either moves, stop and report `needs context` with the diff — a decode-side change that moves Phase 2's committed evidence is a finding, not something to accept.
- Report whether `overlay_test.py`'s figures move, and by how much. A change here is expected to be *geographic* (decoded positions are now correct rather than compressed into 1/8 of the frame) and is not automatically a defect — but it must be reported, never absorbed.
- `git grep -n COORD_RANGE -- parser/kiwiw parser/harness parser/tools` returns only `COORD_RANGE_RL` in `header_word_census.py`. Report the output verbatim.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

State the exact signatures you landed for `range_for`, `xy_to_latlon`, `latlon_to_xy` and `encode_region_coord`, and the name and location of the temporary legacy constant — 3-02 and 3-03 code against all five.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
