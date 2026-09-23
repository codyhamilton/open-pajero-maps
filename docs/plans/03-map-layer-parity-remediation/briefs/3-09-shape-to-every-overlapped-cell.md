# Brief: 3-09 — every cell a background shape overlaps receives it, as R does

Consumer: 3-10 (starts from the tree this unit leaves); 3-05, which builds the determinism matrix from it; 3-06, which runs the phase evidence against it.
Owned paths: `parser/build_alldata.py`, `parser/kiwiw/spool.py` (read side only — no format change), `parser/kiwiw/divide.py`, new `parser/kiwiw/overlap.py` (or similar, one new module), `parser/tools/quantisation_roundtrip.py` (only if it must see the same per-cell content the build sees), and their tests under `parser/tests/` (`test_build_alldata*.py`, `test_divide*.py`, `test_spool*.py`, new `test_overlap.py`, `test_quantisation_roundtrip.py`). Touch nothing else; if another file must change, report `needs context`.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-07.
Runs alongside: nothing.
Budget: 12 files to read, about 500 lines to change, 90 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "#### Phase 3 — Outcome, as amended" and "#### New grounded rule: one global raw lattice per level".
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the research ("R clips background geometry") and 3-07 records, especially 3-07's concern (1).
3. `briefs/3-07-clip-to-frame.md` — the R evidence and the clip contract this unit completes.
4. `parser/osm_to_parcel_geometry.py` around line 945 (read only: how a background way is assigned to one cell by centroid; shapes are stored in lat/lon), `parser/kiwiw/divide.py` (module docstring, `_retile_content`, `_sub_frame`), `parser/build_alldata.py` (`_level_frames`, `_level_frames_c`, `_plan_chunks`, `_encode_chunk`, `_encode_level_indexed`), `parser/kiwiw/spool.py` (`iter_cell_raw`, `iter_cells`, the index).

Read ranges and grep; do not read whole files, and truncate long tool output.

## Goal

3-07 made G clip background geometry to the frame as R does. But the extractor puts each background shape in the one cell that holds its centroid (and `divide.py` does the same for sub-cells), so the part of a shape that crosses into a neighbouring cell is now clipped away. The neighbour never received the shape, so that ground is simply missing. On R, edge-crossing vertices mirror into the neighbouring frame 75–87% of the time. On G they mirror about 2% of the time. Make every cell (and every divided sub-parcel) whose rectangle a background shape overlaps receive that shape. Each cell then clips it to its own rectangle (3-07's clip), so the two sides of a boundary meet.

## Contract

- **At assembly time, from the spool of record. Do not re-extract** and do not change the spool format. Shapes are lat/lon, so a shape can be tested against any cell's rectangle in the level's global raw lattice (the same lattice 3-07 clips in).
- **Every overlapped cell, not just neighbours.** A shape's bounding box can span many cells (large lakes, forests, sea polygons). Receiving is by true overlap of the clipped result: a cell whose clip produces nothing writes nothing (3-07 already drops wholly-outside shapes). A bbox-overlap prefilter is fine.
- **Only cells that exist.** Add shapes to cells the build already emits at that level; do not create new parcels. Report how many overlapped cells were skipped because they don't exist, per level. The disc's cell set, and whether R has parcels there, is not this unit's question.
- **Divided parcels.** A sub-parcel receives every shape that overlaps its sub-rectangle, not only shapes whose centroid falls in it. Update `divide.py`'s docstring. Roads stay out of scope.
- **Determinism and `-j` independence.** A cell's content must not depend on chunking or worker count. Build the cross-cell sharing in a deterministic pre-pass per level, or any equivalent, and keep it memory-bounded on the full spool (report peak RSS). Within a cell, shapes go in a defined order: the cell's own shapes first in spool order, then shapes borrowed from other cells, ordered by source `(iy, ix)` and then spool index. Both the Python and C (`iter_cell_raw` / `_cenc`) assembly paths must see the same per-cell shape list and produce byte-identical output.
- **Budgets.** More shapes per cell can trip byte budgets, which triggers division or trimming. Keep the existing keep-order and shrink rules unchanged. Report the before/after counts of divided parcels and trimmed shapes per level, so the orchestrator can see the effect.
- Names and roads are unchanged. Offset/step encoding, the range model and pen-up are unchanged.
- Reference disc R is at `/run/media/codyh/464210-8480`. The spool is `output/extract_timing/spool`. Python is `.venv-rp/bin/python`. Put scratch under `output/scratch-3-09/` with `TMPDIR` set there. Never edit `.claude/worktrees/`.

### Keep untouched

`osm_to_parcel_geometry.py`, `coordconv.py`, `kiwiw/clip.py`, `_cenc.c` clip/encode logic (the per-cell input list is the change, not the encoder), roads, names, `parser/harness/**`, `parser/refdata/**`, all plan documents.

## Done evidence

Identify or write the failing check before changing code (e.g. a two-cell fixture where one shape straddles the boundary: before, only one side writes it; after, both do and the crossing vertices are identical in global raw). Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report the counts before and after.
- A full assembly from `output/extract_timing/spool` at `-j 12` into scratch. Report its sha256, size, wall time and peak RSS. The Perth fixture must be identical at `-j 1` and `-j 4`; report its sha.
- `compare_disc.py --generated <new ALLDATA.KWI> --checks coord_scale --no-manifest --report <scratch>/cs_G.json` PASS; report the summary line.
- `quantisation_roundtrip.py --spool output/extract_timing/spool --out <scratch>/roundtrip.json`: background kinds 0 failing. Report the per-kind written totals and the worst error. The one known name-anchor failure is 3-10's; report it only if the count changes.
- Re-run `output/research-3-bg/bg_edge_probe.py` (same sampling) against the new G. Report corner mirror and crossing mirror (exact / ≤ 2 / ≤ 4 raw) beside R's and beside 3-07's G. Expect crossing mirror to rise from about 2% to at least R's 75–87%, near 100% exact. Also report bridges and spikes.
- Before/after counts of divided parcels and trimmed shapes per level.

## Report back

Keep it under 1,500 tokens. Status is one of `done`, `done with concerns`, `blocked`, `needs context` or `over budget`. Then give what changed, the check output before and after, the disc and Perth shas, any deviation and why, and any contradiction with the contracts or R evidence. Never resolve a contradiction silently. For a non-trivial bug outside your done evidence, report its symptom, location and root cause if found, and do not fix it here. Do not spawn agents beyond read-only research helpers.
