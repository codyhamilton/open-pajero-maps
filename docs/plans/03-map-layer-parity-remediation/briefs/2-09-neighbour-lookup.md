# Brief: 2-09 — R leaf-neighbour lookup (block- and blockset-crossing)

Consumer: implementation worker; the module is consumed by 2-10 (cross-parcel continuity) and 2-11 (boundary-node mirror), and its coverage counts are cited by the gate verdict (2-12).
Owned paths: `parser/tools/r_neighbours.py` (new), `parser/tests/test_r_neighbours.py` (new), `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-09.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing.
Runs alongside: nothing (2-10 and 2-11 both consume this module and start after it).
Budget: 8 files to read, about 200 lines to change, 40 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (user) — grounded phase gates": the classification rule, and "#### Phase 2 — Outcome, as amended" criteria 2 and 4 plus the "Carried into the re-run" paragraph. Criterion 4's sentence "The mirror invariant was tested only on same-block neighbours, so block- and blockset-crossing neighbour lookup must exist before it is load-bearing" is why this unit exists.
2. `parser/harness/walk.py` — `_block_base_bounds` (lines 99–113), `_narrow_bounds`, `_tile_bounds`, `_is_sparse_tile`, `_leaf_frame`, `_frame_range`, `WalkedParcel`'s docstring (the leaf/frame distinction), `_iter_tree_leaves`.
3. `parser/tools/overlay_test.py` — `RReader` (lines 499–568: `blocks`, `leaves`, `decode`), `_urban`, `_class_key`, `tile_frame`, `spread`, `class_range`. `RReader` is the R reading engine you reuse; do not modify it.
4. `parser/tools/header_word_census.py` — `divided_adjacency_census` (lines 807–848), the one existing precedent for a cross-block geometric adjacency test on R, including its `touches` bbox predicate and why it runs per level.
5. `parser/refdata/profile/coord_scale.json` — `class_rule` (`l0_grid_width`, `l0_tile`, `urban_tiles`) and `ranges` (read only).
6. `parser/tests/test_overlay_test.py` lines 1–20 — how a test imports a tool from `parser/tools` (`sys.path` insert, then plain `import`).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Give the two grounded cross-parcel checks one tested way to ask "which leaf holds the cell on the other side of this edge?", answered correctly when the answer lies in another block or another blockset, with the cases where there is no answer separated from the cases where the answer is a leaf with no data.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23, Phase 2 criterion 4: "A link end-node whose raw coordinate is exactly 0 or exactly the class range is a genuine boundary crossing: the adjacent parcel holds an end-node at the mirrored coordinate, crossed axis = range - value, other axis unchanged. Per-node violation count; denominator all exact-coordinate nodes with a resolvable neighbour, with nodes at the extract's outer edge excluded from the denominator rather than failed."

Cited, the same amendment, "Carried into the re-run": "The mirror invariant was tested only on same-block neighbours, so block- and blockset-crossing neighbour lookup must exist before it is load-bearing."

Cited, `parser/harness/walk.py` `_block_base_bounds`: a block's bbox is derived from the disc coverage box and the level's global grid —

```
base_ix = (bsx * nbl_lng + blx) * npc_lng
base_iy = (bsy * nbl_lat + bly) * npc_lat
```

so leaf slots at one level lie on a single **global** leaf grid whose integer coordinates are `(base_ix + leaf_x, base_iy + leaf_y)`. Adjacency is therefore integer arithmetic on that grid, not float bbox comparison; the bbox check is your verification, not your lookup.

Settled and not to be re-derived: `WalkedParcel.bounds` is the leaf slot's extent and `frame_bounds` is the bbox the stored coordinates are expressed in, which differs from the leaf only for an L0 sparse tile (2-05, commit 2f874e3). A leaf index within a block decomposes as `x = idx % gn_lng`, `y = idx // gn_lng` with `gn_lng = 1 + lmr.n_parcels_lng[parcel_type]` (`_iter_tree_leaves`).

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. This unit reads R only; **no OSM input at all**. Python: `.venv-rp/bin/python`. Reads R only through `parser/harness/` reading paths and `overlay_test.RReader`; imports no writer module. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

**The API below is fixed at refine time, because 2-10 and 2-11 are written against it. Keep the names and the return shapes; add to them if you must, remove nothing.**

- `global_leaf_xy(lmr, bsx, bsy, blx, bly, leaf_index) -> (gx, gy)` — the leaf's coordinates on the level's global leaf grid, using `_block_base_bounds`'s own formula. `grid_dims(lmr) -> (nx, ny)` gives the grid's extent so a lookup can tell "off the grid" from "grid cell with no block".
- `class LeafIndex(rdr, level)` — built once per level over `rdr.blocks(level)`; indexes every populated **top-level** leaf slot (`len(leaf_path) == 1`) by `(gx, gy)`. Block leaf lists are read on demand and cached with a bounded cache (state the bound; L0 has thousands of blocks and the index must not hold them all decoded). It stores handles, never decoded parcels.
- `LeafIndex.get(gx, gy) -> Neighbour | None` and `LeafIndex.neighbour(handle, edge) -> Neighbour`, with `edge` one of `"W"`, `"E"`, `"S"`, `"N"` (W/E on longitude, S/N on latitude, y increasing northward per 2-06).
- `Neighbour` carries: `status`, `handles`, `divided`, `crossing`, and the target's `(gx, gy)`.
  - `status` is exactly one of:
    - `"resolved"` — a populated leaf slot exists there.
    - `"outside_coverage"` — the target `(gx, gy)` is off the level's global grid, or its block is not on the disc at all. **This is the extract's outer edge: the consumer excludes these from its denominator, it does not fail them.**
    - `"empty_slot"` — the block is on the disc but that leaf slot is `NO_DATA`. Also excluded, but counted separately, because it is a different fact about R.
  - `handles` is the list of `(lmr, blk, leaf)` triples that `rdr.decode(lmr, blk, leaf)` accepts: one for a normal leaf, and for a divided parent **all of its sub-leaves**, with `divided=True`. Do not decide here what a consumer should do with a divided neighbour; 2-11 excludes them and counts them.
  - `crossing` is `"same_block"`, `"cross_block"` or `"cross_blockset"` — which boundary the lookup crossed. 2-11 must be able to report that the cross-block and cross-blockset paths actually carried matches, which is the amendment's condition for the mirror check being load-bearing.
- Verification, inside the module and exercised by the evidence run: for every `resolved` neighbour, assert the two leaf bboxes share the edge — for `"E"`, `neighbour.lon_lo == leaf.lon_hi` and the latitude bounds are equal, within a relative tolerance you state (the bboxes are float arithmetic over the coverage box; `divided_adjacency_census` uses `eps = 1e-9` on degrees, and a relative tolerance against the leaf span is better). A failed assertion is a **finding**, not something to loosen: report it with the ids and the numbers.
- `main()`: `--reference`, `--out`, `--levels` (default `0,2,4,6,8`), writing `EVIDENCE-2-09.json`. Per level it reports, over a **stated deterministic sample** (full population at L6, L8 and L10/L12 if present; for L0, L2 and L4 use `overlay_test.spread` over the block list with a stated block count, and every leaf of each chosen block): the counts of each `status`, the counts of each `crossing`, how many resolved neighbours are divided parents, how many edge-sharing assertions passed and failed, and the sample rule itself in words. State in the JSON that the L0 figures are per leaf slot, not per sparse tile frame.

### Keep untouched

`parser/tools/overlay_test.py`, `parser/harness/**`, `parser/kiwiw/**`, `parser/refdata/**`, `docs/schema/**`, and the existing `EVIDENCE-2-03.json` / `EVIDENCE-2-08.json`. This module reads; it changes nothing about how R is decoded.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_r_neighbours.py -q` passes, with synthetic-fixture tests (no disc) for: `global_leaf_xy` against a hand-computed case with `bsx`/`blx` both non-zero; `neighbour` on the W edge of leaf index 0 of a block returning a `(gx-1, gy)` target in the **previous block**, and on the W edge of the grid's first column returning `outside_coverage`; `crossing` reported as `cross_blockset` when the target's blockset differs; a divided parent returning `divided=True` with four handles. Build the fixtures the way `test_overlay_test.py` builds its synthetic R links, or with a stub `rdr`; say in a test comment if a real block cannot be synthesised.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts before and after).
- `.venv-rp/bin/python parser/tools/r_neighbours.py --reference /run/media/codyh/464210-8480 --out docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-09.json --levels 0,2,4,6,8` run **twice** with identical output (report the `sha256` both times).
- From that run, report in your handback: at L6 and L8, the number of resolved neighbours and how many were `cross_block` and `cross_blockset`; and the edge-sharing assertion pass/fail counts at every level. If `cross_blockset` is zero at every level, say so plainly — 2-11's load-bearing claim then rests on `cross_block` alone and the orchestrator needs to know.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. Lead with the API as you left it (signatures and `status`/`crossing` values), because 2-10 and 2-11 are written against it: if you had to change a name or a return shape, say so in the first line.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
