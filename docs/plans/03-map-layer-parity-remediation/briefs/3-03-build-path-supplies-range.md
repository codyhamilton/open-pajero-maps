# Brief: 3-03 — the build path supplies each parcel's real range; the legacy constant dies

Consumer: 3-05, which runs the determinism matrix on the disc this unit produces; 3-06, which verifies the phase outcome against it.
Owned paths: `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/divide.py`, `parser/build_alldata.py`, `parser/kiwiw/spool.py`, `parser/kiwiw/coordconv.py` (only the removal named below), `parser/tests/test_parcel_geometry.py`, `parser/tests/test_divide.py`, `parser/tests/test_build_alldata.py`, `parser/tests/test_spool_binary.py`, `parser/tests/test_mesh_divided_locate.py`. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-01, 3-02.
Runs alongside: 3-04 (disjoint paths).
Budget: 10 files to read, about 350 lines to change, 70 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "### Domain: Native encoding model", "#### Phase 3 — Outcome, as amended", and "#### New grounded rule: one global raw lattice per level".
2. 3-01's and 3-02's reports back (your orchestrator has them) — the landed signatures. Code against those, not against this brief's prose.
3. `parser/refdata/profile/coord_scale.json` — `ranges` and `class_rule`.
4. `parser/kiwiw/divide.py` — `_retile_content` and the surrounding division logic, including the comment stating that sub-chain nodes are rebuilt with `x=0, y=0` so the encoder "recomputes pixel coordinates from `lat`/`lon` against the new sub-cell bounds rather than reusing pixel coordinates computed against the parent cell".
5. `parser/build_alldata.py` — `_encode_one`, `_measure_one`, `_level_frames` (it yields `(ix, iy, parcel_type, sub_ix, sub_iy, frame_bytes)`), `cenc.make_encoder`, and the `-j/--workers` chunking.
6. `parser/osm_to_parcel_geometry.py` — `TileGrid`, `parcel_bounds`, `_make_road_link`, `_make_background_shape`, and their `COORD_RANGE`-derived limits.
7. `parser/kiwiw/spool.py` — the column list only (`n_x`, `n_y`, `n_lat`, `n_lon`, `p_lat`/`p_lon`, `c_lat`/`c_lon`, `s_lat`/`s_lon`).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Every parcel is now encoded at its own frame's range and against its own frame's bounds, so G's coordinates live on R's lattice instead of a uniform 2^15 one. This is the unit where output bytes change.

## Contract

Cited, DESIGN.md, "#### New grounded rule: one global raw lattice per level":

> At every level, R's raw coordinate resolution is 4096 raw units per top-level leaf slot. A coordinate frame covers an n x n block of slots and carries range `n x 4096`: n = 1 for a basic parcel (L0 urban, an L2–L8 leaf, a divided parent), n = 4 for an L0 sparse integrated-parcel tile, giving `4 x 4096 = 16384`.

Cited, DESIGN.md, "#### Phase 3 — Outcome, as amended":

> after assembly from the existing spool (encoders derive pixels from lat/lon; no re-extraction) … `range_for` feeds both encoders and no `COORD_RANGE` constant remains

Binding, and settled — do not re-derive:

- **No re-extraction.** The existing spool under `output/spool` (about 7 GB) is the input. It stores `lat`/`lon` for every vertex kind, and after 3-02 both encoders derive pixels from lat/lon, so nothing in the spool needs rewriting. If you find yourself wanting to re-run `osm_to_parcel_geometry.py` over the PBF, stop and report `needs context`. Changes to `osm_to_parcel_geometry.py` here are to its coordinate limits and its `COORD_RANGE` import, so that a *future* extraction agrees; they are not a licence to re-extract. (`output/manifest.json`'s `spool_dir` records a stale `.claude/worktrees/...` path — use the real `output/spool`, do not "fix" the manifest, and never edit anything under `.claude/worktrees/`.)
- **A divided sub-parcel is encoded in its parent's frame.** This is the behaviour change in `divide.py`. Today `_retile_content` zeroes `x`/`y` so the encoder renormalises each sub-parcel's vertices against the *sub-cell* bounds — which is exactly the uniform-scale assumption this phase removes. Under the settled model a sub-parcel's coordinates are expressed in the **parent's 4096 frame**, and `coord_scale.json` confirms it two-sidedly: `pardiv1_sub0` (the SW quadrant) peaks at **2048** — half of 4096, because that quadrant occupies the lower half of the parent frame — while `sub1`, `sub2` and `sub3` reach 4096. Encode every sub-parcel against the parent's bounds at range 4096 and the observed maxima fall out; they are *not* an input. If your sub-index-to-quadrant mapping produces a different pattern than sub0→2048 / sub1,2,3→4096, that is a `needs context` report, not something to force.
- **`range_for` is the only source of a range.** `build_alldata` derives `(level, parcel_class, division_state)` per parcel — the class from `coord_scale.json`'s `class_rule` (L0 `urban` when the leaf's aligned 4x4 tile is in `urban_tiles`, else `sparse`; every other level `full`), the division state from the parcel type it is already tracking in `_level_frames` — and passes `range_for(...)`'s answer to the encoder. No second copy of the tile arithmetic, no literal range anywhere.
- **`range_for` returns the frame divisor, never an observed maximum.** A divided sub-parcel's range is 4096, not `coord_scale.json`'s 2048 `max`. 3-01 already encoded this; do not work around it.
- **Delete the temporary legacy constant** that 3-01 left in `coordconv.py` (`_LEGACY_RANGE`, marked `# TEMPORARY -- deleted by unit 3-03`) and the defaults that referenced it, once no caller relies on them. After this unit the range is required everywhere. This is the only edit you make to `coordconv.py`.
- **Determinism is not negotiable.** Output must stay independent of `-j`. The range is a pure function of `(level, ix, iy, division_state)`, so it must be computed identically in every worker — derive it in the worker from the parcel's own identity, or pass it through the chunk, but never from anything a worker shares mutably or from anything order-dependent. Whatever memoisation `range_for` does must be fork-safe.
- **The disc will change, and that is the point.** The old sha `51c254ac…672743` is retired here. The new sha is this unit's output and 3-05's input.

Python is `.venv-rp/bin/python`. Assembly is about 263 s at `-j 12`.

## Changes

`build_alldata.py`: per-parcel class/division derivation and the `range_for` call threaded into `_encode_one` / `_measure_one` / the encoder factory. `divide.py`: sub-parcels encoded against the parent frame; the `x=0, y=0` renormalisation comment and mechanism corrected to match. `osm_to_parcel_geometry.py`: limits from `range_for` rather than a `COORD_RANGE` import. `spool.py`: only if a column or reader genuinely blocks the above — prefer leaving it alone, and say in your report whether you touched it. `coordconv.py`: the one deletion. Tests updated and extended.

### Keep untouched

The spool's contents and on-disk format (magic `KWSPIDX1`) — no re-extraction, no rewrite. The chunking and merge order that make output `-j`-independent. The division *policy* (when and how a parcel divides, the size thresholds): only the coordinate frame the sub-parcels are encoded in changes here. `parser/kiwiw/synth.py`, `road_writer.py`, `background_writer.py`, `cenc.py`, `_cenc.c` — 3-02's. `parser/harness/**` and `parser/tools/**` — 3-01's and 3-04's. `output/ALLDATA.KWI` and `output/manifest.json` — build to your scratch directory; 3-05 owns promoting a disc.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report counts before and after.
- A test asserting an L0 sparse parcel encodes at range 16384, an L0 urban parcel and an L6 leaf at 4096, and that the same vertex lat/lon yields different raw values in a sparse frame than in an urban one.
- A `divide.py` test asserting a divided parent's four sub-parcels are encoded in the parent's 4096 frame: sub0's raw coordinates all within `[0, 2048]`, sub1/2/3 reaching above 2048 and within `[0, 4096]`.
- A full assembly: `.venv-rp/bin/python parser/build_alldata.py --spool output/spool --out <scratch>/ALLDATA.KWI -j 12`. Report the new sha256, byte size, and the wall time. It must differ from `51c254ac…672743`.
- `.venv-rp/bin/python parser/build_alldata.py --fixture perth` at `-j 1` and `-j 4` produce identical bytes to each other. Report the sha (it will not be `e275879f…` any more).
- Run 3-04's `coord_scale` check against the new disc if 3-04 has landed; report PASS/FAIL and the message. If it has not landed, say so — 3-06 runs it either way.
- `git grep -rn "COORD_RANGE" -- parser/` returns only `COORD_RANGE_RL` in `parser/tools/header_word_census.py` (a route-planning-layer constant, out of scope). Report verbatim.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

State the new disc's sha256, size and the exact command that produced it — 3-05 reproduces it. State whether you touched `spool.py` and whether any re-extraction was needed (it must not have been). State the sub0/sub1-3 maxima you observed.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
