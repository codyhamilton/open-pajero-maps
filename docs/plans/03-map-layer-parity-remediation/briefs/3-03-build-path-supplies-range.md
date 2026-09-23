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

## Amendment after 3-01 (landed `e029952`, 2026-09-24)

3-01 landed the API with these exact signatures, all in `parser/kiwiw/coordconv.py`:
`range_for(level: int, parcel_class: str, division_state: str = "normal") -> int` (`parcel_class` is a `coord_scale.json` key: `urban`/`sparse`/`full`/`divided`; raises `KeyError` on an absent triple; 4096 for any divided sub-parcel via `_SLOT_RANGE = 4096`);
`xy_to_latlon(xc, yc, bounds, *, coord_range: int = _LEGACY_RANGE)`; `latlon_to_xy(lat, lon, bounds, *, coord_range: int = _LEGACY_RANGE)`; `encode_region_coord(xc, *, coord_range: int = _LEGACY_RANGE)` (inclusive `0 <= xc <= coord_range`). Temporary constant `coordconv._LEGACY_RANGE = 32768`.
`BoundingBox` (`parser/kiwiw/model.py`) carries `coord_range: Optional[int] = None`; `harness/walk.py` exposes `leaf_frame_range(level, ptype, leaf_path, frame_class)` and `with_range(bounds, range)`. `walk.iter_parcels` decodes a divided sub-parcel against its **parent slot** (`frame_class="divided_parent"`), not its quadrant.

Transitional shims 3-01 could not remove (its owned paths excluded the importers) — these are what "no `COORD_RANGE` constant remains" now depends on:
1. `coordconv.COORD_RANGE = float(_LEGACY_RANGE)` — a public alias kept because `synth.py` and `parser/osm_to_parcel_geometry.py` import it.
2. `_cenc.c`'s own `#define COORD_RANGE 32768.0`.
3. `parser/tools/overlay_test.py`: `DECODER_RANGE` kept as an alias of `CONTROL_RANGE_32768` because `parser/tests/test_overlay_test.py` imports it.
4. `parser/tools/road_density_census.py` falls back to `coordconv._LEGACY_RANGE` for a parcel with no frame, because `parser/tests/test_road_density_census.py` builds frameless fixtures at 32768.
5. The decoders in `road.py`, `background.py`, `name.py` fall back to the legacy value when handed a `BoundingBox` whose `coord_range` is `None`.

For this unit — **owned paths extended** to cover the shims: `parser/kiwiw/road.py`, `parser/kiwiw/background.py`, `parser/kiwiw/name.py`, `parser/kiwiw/model.py`, `parser/tools/overlay_test.py`, `parser/tools/road_density_census.py`, `parser/tests/test_overlay_test.py`, `parser/tests/test_road_density_census.py`. When `_LEGACY_RANGE` and the defaults go: delete the `COORD_RANGE` alias (1); drop `DECODER_RANGE` and move its test to `CONTROL_RANGE_32768` (3) — `control_32768` keeps its literal meaning; give the road-density fixtures an explicit range and delete the frameless fallback (4); make a `None` `coord_range` in the decoders raise rather than fall back (5). The continuity and mirror census sha256s (`da70cd59…`, `23854cf5…`, EVIDENCE-2-14) must still reproduce afterwards — add that to this unit's done evidence. The `git grep -n COORD_RANGE -- parser/kiwiw parser/harness parser/tools` check must then return only `COORD_RANGE_RL`.

## Amendment after 3-02 (orchestrator, 2026-09-24)

- **Spool path.** Use `output/extract_timing/spool` (binary `KWSPIDX1`, stats match the manifest's `spool_stats`) wherever this brief says `output/spool`; `output/spool` is a legacy pickle spool that `SpoolReader` rejects.
- **Baseline.** 3-02 removed the encoders' stored-pixel preference; road nodes' y moved from the spool's stale y-down pixels onto the settled y-up orientation. The pre-3-03 baseline is full disc `9407122122b9…` / Perth `99d72f0b1cf14b8b…`; `51c254ac…` / `e275879f…` are retired (they predate 2-06).
- **Scratch.** `/tmp` hits its disk quota on full builds; put scratch under `output/scratch-<unit>/` (gitignored) and set `TMPDIR` there.
- **Region packing.** `coordconv.encode_region_coord(32768, coord_range=32768)` returns 65536 (overflows the 3-bit region / u16 word), and both encoders clamp to `min(coord_range, 32767)` as a transitional guard. When `_LEGACY_RANGE` dies, make `encode_region_coord` reject a result that does not fit (region > 7) and drop the `32767` cap from the encoders' clamp so the edge is simply inclusive `[0, coord_range]` (every real range is ≤ 16384). `synth.frame_range`'s fallback to `_LEGACY_RANGE` goes with it: a `None` range raises.
- **3-02's signatures.** C entry points `kw_encode_cell`, `kw_bg_shape`, `kw_measure_cell` take a trailing `double coord_range`; `CellEncoder.encode(raw, ix, iy, *, coord_range=_LEGACY_RANGE)`, `measure_content(..., *, coord_range=None)`; every `synth.py` encode/build function and `road_writer.encode_road_link` / `background_writer.encode_background_shape` take keyword `coord_range=None`, resolved by `synth.frame_range(bounds, coord_range)`. `parser/kiwiw/synth.py`, `parser/kiwiw/cenc.py` and `parser/tests/test_cenc.py` are added to this unit's owned paths for removing those legacy defaults only.

## Amendment after 3-04 (orchestrator, 2026-09-24) — overrides the L0 sparse bullets above

- **The range follows the frame G actually writes, not `class_rule` alone.** DESIGN.md's Open Question "The L0 sparse frame is a shape difference between R and G, and no phase owns it" settles this: G writes each L0 leaf slot as its own frame (it does not alias sixteen slots into one integrated-parcel tile), so under the one-global-lattice rule (`range = n x 4096`, n = slots the frame covers) every G L0 frame is n = 1, range **4096** — `range_for(0, "urban")`. Encoding one slot's bounds at 16384 would break the global lattice (4096 raw units per slot) and the `coord_scale` check (which classes a frame by its structure, via `walk._leaf_frame`) would fail every such parcel. Do **not** build the 4x4 integrated tile — that is the unowned shape difference, carried. Replace the test asserting "L0 sparse encodes at 16384 / different raw values than urban" with one asserting every G L0 parcel encodes at 4096 on the global lattice, and derive the class through one shared helper so a future integrated-tile build changes one place.
- **Every division type lives in the parent's 4096 frame.** G's divider emits `pardiv2` sub-parcels (632 parcels, e.g. `8/divided/pardiv2_sub0`); R uses only `pardiv1`, so `coord_scale.json` has no `pardiv2` entries and `range_for` raises. Spec 7.2.2.1.1.2(2)/(3) — "the normalized coordinate in the original basic parcel is used" — is division-type independent. `parser/kiwiw/coordconv.py` is extended in scope for this: `range_for` returns `_SLOT_RANGE` for any `pardiv<t>_sub<i>` whose `(level, "divided")` exists, without requiring the exact triple; it still raises for an unknown level/class or a malformed state. Add a test for `pardiv2`. Division policy itself (whether G should emit `pardiv2`) is Phase 5's; do not change it.
- Add to done evidence: `compare_disc.py --generated <your new ALLDATA.KWI> --checks coord_scale --no-manifest --report <scratch>/cs_G.json` (3-04's check; ~10 min) and report its summary line. Do not run the quantisation round-trip as a gate here — background-polygon clamping is a known, separately-decided issue.
