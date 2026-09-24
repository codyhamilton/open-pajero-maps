# Brief: 3-11 — mult_const selection for exact-rectangle background shapes

Consumer: 3-12, which re-measures overlap duplication cost against this unit's rebuilt disc; 3-05 and 3-06, which build the determinism matrix and phase evidence from the tree this unit (and 3-12) leave.
Owned paths: `parser/kiwiw/synth.py` (`_bg_mult`, `_bg_piece_record`, `encode_background_shape_records_scalar`), `parser/kiwiw/_cenc.c` (the matching background encode path), `parser/kiwiw/clip.py` (only if `shape_pieces`'s signature must change to accept a per-shape mult decision — do not change its clip/densify geometry otherwise), `parser/kiwiw/overlap.py` (`cover_ring` only, if the interior-cell substitute ring needs to carry a hint), and their tests under `parser/tests/` (`test_cenc.py`, `test_synth_*.py`, new test file if needed). Touch nothing else; if another file must change, report `needs context`.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-09.
Runs alongside: nothing.
Budget: 10 files to read, about 250 lines to change, 70 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-09 entry (its "Concerns" item 1: disc size 2.14 GB vs R's ~1.53 GB) and the research write-up this brief is drawn from (ask the orchestrator if not present as a file; the key numbers are quoted below).
2. `parser/kiwiw/synth.py` around `_bg_mult`, `_bg_piece_record`, `encode_background_shape_records_scalar` (~lines 235-335) — read the docstring on `_bg_piece_record` closely: it states the *current* exactness invariant depends on `mult == 1`.
3. `parser/kiwiw/background.py` around the decode loop (`mult_const = 1 << extract(addl, 0, 2)`, `xc += xo * mult_const`) — this is the decoder your encoder change must stay exact against.
4. `parser/kiwiw/clip.py` module docstring and `_densify`/`shape_pieces` (~lines 250-345) — `lim = 127.0 * mult - 1.0` is the only place `mult` currently affects output; densify picks `k = ceil(mx / lim)` roughly-equal interpolated steps.
5. `parser/osm_to_parcel_geometry.py:520-538` (`_make_background_shape`) — `mult_const=1` is hardcoded here at extraction time; leave it hardcoded (out of this unit's owned paths) and instead choose the real mult later, at encode time, in `synth.py`.
6. `parser/kiwiw/overlap.py` — module docstring lines 1-30 and `cover_ring` (~line 164) — the interior-cell substitute ring is always the clip rectangle's four corners grown a quarter-cell out, i.e. structurally the same "whole-cell rectangle" shape R was found to encode cheaply.

Read ranges and grep; do not read a whole file to find one section, and truncate long tool output.

## Goal

R encodes a shape that covers an entire frame (or sub-frame) as a handful of vertices — 12 for an L0-sparse tile, 4 for an L2 frame, ~10 average at L4 — by choosing a coarse `mult_const` (the addl word's 3-bit exponent, values 1–128) so each rectangle edge is written in 3–4 big steps instead of many small ones. G currently hardcodes `mult_const=1` for every background shape regardless of size or shape, so the same rectangle needs ~33 steps per edge (`127*1 - 1 = 126` raw units per step) — about ~130 vertices, a ~10x overdensification that a research probe traced as the dominant cause of G's full-Australia disc growing from 1,414,851,520 B (post-3-07) to 2,137,628,064 B (post-3-09), against R's ~1.53 GB. Give background encoding a coarser `mult_const` wherever it is provably safe to do so, and nowhere else.

## Contract

- **Exactness is non-negotiable and is not a per-shape "does it happen to work" search over already-rounded points.** The decoder reconstructs each vertex by `xc += dx * mult_const` (`background.py`). A vertex is reproduced exactly only if every consecutive rounded delta on that piece is an exact integer multiple of the chosen `mult_const`. Do not pick a `mult_const` and then hope the existing densify/round pipeline happens to satisfy this for an arbitrary shape — for a shape whose rounded vertices are not already multiples of the candidate `mult_const`, raising `mult_const` **silently corrupts the shape** (the round-trip and `coord_scale`/quantisation checks may not catch a drift that stays within tolerance at low levels, so do not rely on them alone — reason about exactness by construction).
- **The provably safe case, and the one to build:** a shape whose clip to its cell/sub-cell rectangle *is* that rectangle (all 4 corners, nothing else — R's own "whole-cell fill" case, and `overlap.py`'s `cover_ring` interior-cell substitute ring, which is always exactly this shape). For such a rectangle, edge length equals the frame's `coord_range` (or a divided sub-parcel's sub-range, from `frame_range`/`leaf_frame_range`). Choose the largest `mult_const` in `{128, 64, 32, 16, 8, 4, 2, 1}` such that `coord_range % mult_const == 0`, then split each edge into `k = ceil(coord_range / (127 * mult_const))` steps that are each an exact multiple of `mult_const` (R's own examples show uneven steps are fine — e.g. 5440, 5440, 5504 for a 16384 edge at mult 64 — as long as every individual step is a multiple of `mult_const` and the steps sum exactly to `coord_range`; the simplest correct construction: `k-1` steps of `mult_const * floor(coord_range / (k * mult_const))`, the last step absorbing the remainder, which is itself a multiple of `mult_const` because `coord_range` is).
- **Detect the rectangle case structurally, not by re-deriving it from densified output.** The cleanest point to detect it is before clipping: a shape is a whole-cell fill if, after `clip.shape_pieces`'s own clip (before densify), a piece has exactly 4 vertices equal (in some rotation) to the clip rectangle's corners. If detecting this cleanly needs `shape_pieces` to expose the pre-densify piece or accept a mult-selection callback, that is an allowed, minimal signature change — keep the clip/round/spike-drop geometry itself untouched (owned by 3-07/3-09).
- **Everything else stays at `mult_const=1`.** Do not attempt adaptive mult selection for edge-crossing shapes, genuine coastline detail, or any shape whose clipped piece is not exactly the rectangle case above. That is out of scope here — R's own edge-cell vertex counts (from the research probe) are not all simple rectangles, and getting that right without corrupting geometry is a separate, harder problem than this unit's budget covers. If you find a second safe, low-risk generalisation while you're in there, name it in your report as future scope; do not build it speculatively.
- **Both encoders.** `synth.py` (`encode_background_shape_records_scalar`, the Python oracle) and `_cenc.c` (`kw_bg_shape` / the matching fast path) must make the same mult decision and stay byte-identical, exactly as 3-02/3-07/3-09 kept them in step.
- **`addl`'s mult field is 3 bits (values 1–128), not the 2-bit/1–8 range a stale comment near `synth.py`'s `_bg_mult` might suggest** — confirm against `background.py`'s `extract(addl, 0, 2)` (an inclusive 3-bit range) before relying on any comment.
- Reference disc R is at `/run/media/codyh/464210-8480`. The spool is `output/extract_timing/spool`. Python is `.venv-rp/bin/python`. Put scratch under `output/scratch-3-11/` with `TMPDIR` set there. Never edit `.claude/worktrees/`.

### Keep untouched

`osm_to_parcel_geometry.py` (extraction still emits `mult_const=1`; this unit reassigns it at encode time only), `clip.py`'s clip/densify/round-clean algorithm and its C twin's geometry (only a signature/plumbing change is allowed if strictly needed), `overlap.py`'s cell-assignment logic (only `cover_ring`'s shape may gain a hint that it's the rectangle case), roads, names, `parser/harness/**`, `parser/refdata/**`, all plan documents.

## Done evidence

Identify or write the failing check before changing code (e.g. a synthetic whole-cell-rectangle fixture at `coord_range=16384`: before, the record has ~130 vertices at `mult_const=1`; after, it has R's ballpark of ~12 at `mult_const=64`, and decoding it round-trips exactly to the same rounded vertices). Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report the counts before and after.
- A full assembly from `output/extract_timing/spool` at `-j 12` into scratch. Report its sha256, size, wall time. Compare size directly to 3-09's 2,137,628,064 B and to R's ~1.53 GB. The Perth fixture must be identical at `-j 1` and `-j 4`; report its sha.
- `compare_disc.py --generated <new ALLDATA.KWI> --checks coord_scale --no-manifest --report <scratch>/cs_G.json` PASS; report the summary line.
- `quantisation_roundtrip.py --spool output/extract_timing/spool --out <scratch>/roundtrip.json`: report the per-kind written totals and failing counts before and after — **any new background failure here is a correctness regression, not an acceptable trade-off; if the count rises, the mult selection is unsafe and must be narrowed or reverted before committing.**
- Re-run `output/research-3-bg/bg_edge_probe.py` (or 3-09's equivalent probe) for crossing/corner mirror at a few sampled levels; report it beside 3-09's numbers to confirm no regression (this unit should not touch which cells receive which shapes, only how cheaply each shape is written).
- Report the disc's total background vertex count before and after (from the manifest or a quick tally), and how many shapes/pieces took the coarse-mult path vs stayed at `mult_const=1`, per level.

## Report back

Keep it under 1,500 tokens. Status is one of `done`, `done with concerns`, `blocked`, `needs context` or `over budget`. Then give what changed, the check output before and after, the disc and Perth shas, any deviation and why, and any contradiction with the contracts or R evidence. Never resolve a contradiction silently. For a non-trivial bug outside your done evidence, report its symptom, location and root cause if found, and do not fix it here. Do not spawn agents beyond read-only research helpers.
