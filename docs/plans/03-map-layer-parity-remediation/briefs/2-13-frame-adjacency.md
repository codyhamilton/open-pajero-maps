# Brief: 2-13 — frame adjacency and the global raw lattice in `r_neighbours.py`

Consumer: 2-14, which rebuilds the continuity and mirror censuses on top of this; and any later unit that needs to ask "what is on the other side of this parcel's edge".
Owned paths: `parser/tools/r_neighbours.py`, `parser/tests/test_r_neighbours.py`, `parser/tools/coord_scale_census.py` (the one `WalkedParcel` construction named below, nothing else in that file). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing.
Runs alongside: nothing.
Budget: 8 files to read, about 250 lines to change, 45 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot", in full. It is the contract for this unit: the root cause, the global-lattice rule, and the two tool defects.
2. `parser/tools/r_neighbours.py` — all of it. `EDGE_DELTA`, `LeafIndex`, `_block_key`, `_addr`, `leaves`, `slot_bounds`, `get`, `neighbour`, `global_leaf_xy`, and the output notes block containing `"l0_is_per_leaf_slot"`.
3. `parser/harness/walk.py` — `L0_TILE`, `_tile_bounds`, `_is_sparse_tile`, `_leaf_frame` (returns `(frame_bounds, frame_class)`), `_frame_range`, and `WalkedParcel.__post_init__`.
4. `parser/refdata/profile/coord_scale.json` — `ranges` (L0 `sparse.normal` max 16384, L0 `urban.normal` max 4096, all other levels `full.normal` 4096) and `class_rule` (`l0_tile`, `l0_grid_width`, `urban_tiles`, `urban_tiles_key`).
5. `parser/tools/overlay_test.py` — `model_frame`, `class_range`, `tile_frame`, `_class_key`, `spread`, `RReader`. Do not modify it.
6. `parser/tools/coord_scale_census.py` — the `_work` function, around lines 176–178, where `walk.WalkedParcel(...)` is constructed.
7. `parser/tests/test_r_neighbours.py` — 2-09's existing fixture and assertion patterns.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make `r_neighbours` answer adjacency questions in units of **coordinate frames**, so that a caller asking for the neighbour across an L0 sparse tile's east edge gets the adjacent *tile* rather than an aliased slot of the tile it started in. Expose the level's global raw lattice so a caller can compare two nodes in different frames without reasoning about either frame's range.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23 (design agent), "New grounded rule: one global raw lattice per level":

> At every level, R's raw coordinate resolution is 4096 raw units per top-level leaf slot. A coordinate frame covers an n x n block of slots and carries range `n x 4096`: n = 1 for a basic parcel (L0 urban, an L2–L8 leaf, a divided parent), n = 4 for an L0 sparse integrated-parcel tile, giving `4 x 4096 = 16384`. A parcel's global coordinate is `X = gx0 * 4096 + x_local`, `Y = gy0 * 4096 + y_local`, where `(gx0, gy0)` is the frame's south-west leaf slot on the level's global leaf grid.

Cited, the same amendment, root cause: `LeafIndex.neighbour` steps one top-level leaf slot; for `L0_sparse` the frame is the 4x4 tile, so 12 of 16 aliased slots step *inside the same frame* and the "neighbour" is the source parcel itself. 100 % of criterion 4's 8,652 `L0_sparse` violations were `same_block` for this reason, with `11536 = 16 x 721`, `2884 = 4 x 721`.

Cited, spec 7.2.2.1.1.2, via the same amendment: "a basic parcel is 4096 x 4096 and an integrated parcel up to 4096 x 8 = 32768" — the integrated parcel's range is a whole multiple of the basic parcel's because the raw unit is the same size at both.

**Pre-stated, not tuned.** Put these in the module docstring with the words "pre-stated, not tuned", and do not change one after seeing a result. A constant that turns out to be wrong is a `needs context` report, not an edit.

- `RAW_PER_SLOT = 4096` — raw units per top-level leaf slot, at every level.
- Frame extent in slots is `n = range // RAW_PER_SLOT`, taken from `coord_scale.json` via `overlay_test.class_range`, never inferred from observed data.
- Lattice comparison is **exact integer equality**. No tolerance, no epsilon.

Binding, on the API:

- The existing leaf-slot API (`get`, `neighbour`, `global_leaf_xy`, `Neighbour`, `crossing`) keeps its current behaviour and signature. 2-09's semantics are correct for what they say; the gap was callers using them as frame adjacency. Do not silently redefine `neighbour`.
- Add frame-level adjacency alongside it. A frame is identified by its south-west leaf slot on the global grid plus its extent in slots. A frame-neighbour query takes a source frame and an edge and returns the frame(s) on the other side, with the same `status` vocabulary (`resolved`, `outside_coverage`, `empty_slot`) and the same `crossing` vocabulary (`same_block`, `cross_block`, `cross_blockset`) that 2-09 established. Never return the source frame as its own neighbour — a frame-step is `n` slots, not one.
- Add the corner query. Spec 7.2.2.1.1.3 says identical node information is held in neighbouring **parcels**, plural, so a point at a frame corner is shared by up to three other frames. A caller must be able to ask for **all** frames sharing a given lattice point, not one nominated edge neighbour.
- Add global-lattice conversion: frame-local raw `(x, y)` plus the frame's SW slot to global `(X, Y)`, and the inverse. These are the only place the `gx0 * 4096` arithmetic lives; no caller re-derives it.
- Frame identity for an L0 sparse tile must come from `walk`'s existing tile machinery (`L0_TILE`, `_is_sparse_tile`, `_tile_bounds`) and `coord_scale.json`'s `class_rule.urban_tiles`, not a new independent tile derivation. If the two disagree on any tile, that is a `needs context` report.
- Replace the output-notes string `"l0_is_per_leaf_slot"` with an accurate note saying what the leaf-slot figures are and that frame adjacency is now available and is what mirror/continuity callers must use. Do not delete the warning; a caller reading only the JSON must still be told which unit it is looking at.

Also in scope, because the amendment makes it load-bearing: **fix `coord_scale_census._work`'s `WalkedParcel` construction**, which omits `frame_bounds` / `frame_range` / `frame_class` so `__post_init__` defaults `frame_bounds` to the leaf bbox and 075fc99's fixer never takes effect in that worker. Pass the real frame from `walk._leaf_frame` / `_frame_range`. This was harmless for criterion 1 because raw values round-trip through whichever bbox both directions use, so **criterion 1's `ranges` and `exceeds_max` must not move**. If they move, stop and report `needs context`: that is a finding about the census, not a licence to accept new numbers.

Settled and not to be re-derived: the frame of record is `overlay_test.model_frame` with `class_range` (2-05, commit 2f874e3); y increases northward (2-06); edges are W/E on longitude and S/N on latitude; the L0 sparse frame is the 4x4 tile at 16384 (2-05).

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. R only; **no OSM input at all**. Python: `.venv-rp/bin/python`. Reads R through `parser/harness/` reading paths and `overlay_test.RReader`; imports no writer module. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

`parser/tools/r_neighbours.py`: frame adjacency, the corner query, global-lattice conversion, the corrected output note. `parser/tools/coord_scale_census.py`: the one `WalkedParcel` construction.

### Keep untouched

`parser/tools/overlay_test.py`, `parser/tools/continuity_census.py` and `parser/tools/boundary_mirror_census.py` (2-14 owns both), `parser/harness/**`, `parser/kiwiw/**`, `parser/refdata/**`, `docs/schema/**`, `docs/plans/**/DESIGN.md`, `GATE-2.md`. Do not update the Assumption Ledger; 2-15 handles the ledger. Do not re-run the Phase 2 gate.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_r_neighbours.py -q` passes, with synthetic-fixture tests (no disc) for: a frame-step at n = 4 landing 4 slots away, not 1; **every one of the 16 aliased slots of one sparse tile producing the same frame identity and the same east neighbour** (this is the regression that caused the gate failure — assert it directly); a frame-step off the grid returning `outside_coverage`; a corner query returning the three other frames sharing the point, and fewer when one is off-grid; global-lattice conversion round-tripping for n = 1 and n = 4; and an n = 1 frame adjacent to an n = 4 frame resolving in both directions.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts before and after; the pre-existing count is 392).
- Against R, report the frame-adjacency figures for a stated deterministic sample at L0 (both classes), L2 and L6, with `status` and `crossing` breakdowns, and say plainly whether `cross_block` and `cross_blockset` each carried at least one resolved frame neighbour.
- `.venv-rp/bin/python parser/tools/coord_scale_census.py --reference /run/media/codyh/464210-8480 --out <scratch>/coord_scale.json --workers 10` run after the `frame_bounds` fix: report whether `ranges` and `class_rule` are still structurally identical to `parser/refdata/profile/coord_scale.json` and whether `exceeds_max` is still 0 in all 28 classes. They must be.
- `.venv-rp/bin/python parser/tools/lint_schema.py` — report before and after; no new errors.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. State explicitly whether any pre-stated constant was changed after a run — the answer must be no. State the frame-adjacency API you landed, with signatures, because 2-14 codes against it.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
