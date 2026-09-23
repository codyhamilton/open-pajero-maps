# Brief: 3-02 — both encoders take the coordinate range as a parameter

Consumer: 3-03, which supplies the real per-parcel range at every call site and deletes the legacy constant; 3-06, which runs the phase's source check.
Owned paths: `parser/kiwiw/synth.py`, `parser/kiwiw/road_writer.py`, `parser/kiwiw/background_writer.py`, `parser/kiwiw/cenc.py`, `parser/kiwiw/_cenc.c`, `parser/tests/test_cenc.py`, `parser/tests/test_synth_map_frame.py`, `parser/tests/test_synth_vectorized.py`, `parser/tests/test_road_encoder.py`, `parser/tests/test_background_encoder.py`, `parser/tests/test_name_encoder.py`. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-01.
Runs alongside: 3-04 (disjoint paths).
Budget: 10 files to read, about 450 lines to change, 70 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "### Domain: Native encoding model" and "#### Phase 3 — Outcome, as amended".
2. 3-01's report back (your orchestrator has it) — the landed signatures of `range_for`, `xy_to_latlon`, `latlon_to_xy`, `encode_region_coord`, and the name of the temporary legacy constant.
3. `parser/kiwiw/coordconv.py` — all of it, as 3-01 left it.
4. `parser/kiwiw/_cenc.c` — `COORD_RANGE` / `COORD_MAX` defines, `to_xy`, `region_coord`, `clampc`, and the four entry points `kw_encode_cell`, `kw_bg_shape`, `kw_measure_cell`, `kw_bounds`.
5. `parser/kiwiw/cenc.py` — all 174 lines: the ctypes argtypes and `CellEncoder` / `bg_shape_bytes` / `measure_content`.
6. `parser/kiwiw/synth.py` — grep for `COORD_RANGE`, `_COORD_MAX`, `_clamp_coord`, `latlon_to_xy`, `encode_region_coord`, `_bg_fast`. Read those regions only; the file is 988 lines.
7. `parser/kiwiw/road_writer.py`, `background_writer.py` — their `latlon_to_xy` / `xy_to_latlon` call sites only.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make the coordinate range an argument that flows into both encoders instead of a constant each one owns, and make both encoders derive pixels from lat/lon rather than trusting pixel columns computed at some other range — **without changing a single output byte yet**. Supplying the real ranges is 3-03's.

## Contract

Cited, DESIGN.md, "### Domain: Native encoding model":

> `coordconv.range_for(level, parcel_class)` replaces `COORD_RANGE`; **the C encoder receives it as a parameter, not its own constant**

Cited, DESIGN.md, "#### Phase 3 — Outcome, as amended":

> `range_for` feeds both encoders and no `COORD_RANGE` constant remains (a source check, not a judgement) … two builds are byte-identical at worker counts 1, 4 and 12

Binding, and settled — do not re-derive:

- **The two encoders stay byte-identical to each other.** The Python oracle (`synth.py`, including the numpy `_bg_fast` path) and the C hot path (`_cenc.c`) must produce the same bytes for the same input. `_cenc.c` is compiled with `-ffp-contract=off` and uses `rint` precisely so its rounding matches Python's half-even. Any new arithmetic you add must preserve that: the range enters as a `double` on the C side and as the same numeric value on the Python side, and the multiply/divide order must be identical in both. Do not "simplify" one side's expression.
- **`#define COORD_RANGE 32768.0` and `#define COORD_MAX 32767` are deleted.** The range arrives as a parameter of `kw_encode_cell`, `kw_bg_shape`, `kw_measure_cell` and `kw_bounds` (whichever of those convert coordinates), threaded through `cenc.py`'s ctypes argtypes and `CellEncoder`. `synth.py`'s `_COORD_MAX` and `_clamp_coord` become range-relative in the same way.
- **Clamping becomes inclusive.** The admissible interval is `[0, coord_range]`, not `[0, coord_range - 1]`. R's census shows `share_at_max = 1.0` in nearly every class and `observed_peak == max`; a boundary node must be able to land exactly on the frame edge, which is what Phase 2's criterion 4 measures. `encode_region_coord(coord_range, coord_range)` is legal.
- **Stop preferring stored pixel columns.** Both encoders currently do the same thing: `synth.encode_road_link_bytes` uses `node.x`/`node.y` when either is non-zero and only falls back to `latlon_to_xy`; `_cenc.c`'s road loop mirrors it with `if (x != 0 || y != 0) { x = clampc(x); ... } else if (to_xy(...))`. The spool's `n_x`/`n_y` columns were written at the 32768 scale, so trusting them would silently defeat this phase. The spool also stores `n_lat`/`n_lon` (and `p_`, `c_`, `s_` lat/lon) for every vertex kind, which is why the existing spool is reusable and no re-extraction is needed — **confirmed in the code, not assumed**. Both encoders must therefore always derive pixels from lat/lon at the supplied range. Remove the stored-pixel preference from both, in the same change, symmetrically.
- **This unit does not change output bytes.** Every caller you do not own keeps passing (or defaulting to) the legacy 32768 range, so `ALLDATA.KWI` must come out with the identical sha256. That is what makes this unit checkable on its own. Two things could break it and both are your responsibility to catch: the inclusive clamp (a value of exactly 32768 that previously clamped to 32767) and dropping the stored-pixel preference (a stored `n_x` that disagreed with `latlon_to_xy(n_lat, n_lon)`). If bytes move, do not accept it — report the count and kind of vertices that differ and why, as `needs context`. A disagreement between stored pixels and lat/lon is itself a finding worth naming.

Python is `.venv-rp/bin/python`. The spool is at `output/spool` (note: `output/manifest.json`'s `spool_dir` records a stale `.claude/worktrees/...` path — use the real directory, do not "fix" the manifest, and do not edit anything under `.claude/worktrees/`). Rebuild the C extension the way the repo already does; do not invent a new build step.

## Changes

`_cenc.c`: delete the two defines, add the range parameter to the converting entry points, make `to_xy` and `clampc` take it, drop the stored-pixel branch. `cenc.py`: matching argtypes and `CellEncoder` plumbing. `synth.py`: range-relative `_clamp_coord`, explicit range at every `latlon_to_xy` / `encode_region_coord` call, range threaded into `_bg_fast`'s numpy expression, drop the stored-pixel branch. `road_writer.py` / `background_writer.py`: explicit range at their conversion sites. Tests updated for the new signatures, plus new cases for the inclusive bound and the lat/lon-always path.

### Keep untouched

The byte layout of every record, the rounding mode, the `-ffp-contract=off` build flag, the region-word packing `(v % 4096) | ((v / 4096) << 13)` (it is defined against the 4096 raw unit and is **not** a function of the frame range), the kind limits / threshold logic, and the chunking that makes output independent of the worker count. `parser/kiwiw/coordconv.py` is 3-01's and 3-03's — do not edit it. `divide.py`, `spool.py`, `build_alldata.py`, `osm_to_parcel_geometry.py` are 3-03's.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report counts before and after (407 before 3-01; 3-01 added cases).
- A Python-vs-C equivalence test in `test_cenc.py` that exercises **both** the legacy 32768 range and at least ranges 4096 and 16384, on road links, background shapes and names, asserting identical bytes from `synth` and `cenc`. Report it passing at all three ranges.
- A test asserting a vertex whose stored `n_x`/`n_y` disagrees with its `n_lat`/`n_lon` encodes from the lat/lon, in both encoders.
- A test asserting a coordinate of exactly `coord_range` survives the clamp and encodes to the next region's value 0.
- A fixture build reproduces the recorded Perth sha256 `e275879f…` (`build_alldata.py --fixture perth`), at `-j 1` and `-j 4`. Report both.
- **The full disc is byte-identical.** `.venv-rp/bin/python parser/build_alldata.py --spool output/spool --out <scratch>/ALLDATA.KWI -j 12` then `sha256sum` equals `51c254ac87328f652e88f0b10880e83992622bcd1d2db2dbd519edc0a5672743` and the size is 1,397,923,200 bytes. Assembly is about 263 s at `-j 12`; write to your scratch directory, not over `output/ALLDATA.KWI`. If the sha differs, report `needs context` with the first differing offset from `parser/harness/bytediff.py` and the vertex class responsible — do not adjust the expectation.
- `git grep -n "COORD_RANGE\|COORD_MAX" -- parser/kiwiw` returns nothing from `_cenc.c` or `synth.py`. Report verbatim.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

State the exact signatures of the C entry points and their ctypes argtypes, and of every `synth`/writer function that gained a range parameter — 3-03 calls all of them. State plainly whether the full-disc sha reproduced, and whether any vertex had stored pixels disagreeing with its lat/lon.

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

For this unit: `synth.py` must stop importing `COORD_RANGE` (shim 1's `synth.py` side) and `_cenc.c`'s `#define COORD_RANGE` must go (shim 2). The `coordconv` alias itself is 3-03's to delete.

## Amendment after 3-02's first report (orchestrator, 2026-09-24)

The "output bytes unchanged" done evidence rested on a false premise. The spool's stored road-node `n_x`/`n_y` were written y-down (spool extracted 21 Sep, before 2-06's y-up switch at 39c9c2f); x agrees with lat/lon everywhere, y agrees only with y-down. Removing the stored-pixel preference, which this brief requires and the design mandates ("encoders derive pixels from lat/lon"), therefore moves every road node's y onto the settled y-up orientation. That is a latent-defect fix, accepted. The expected shas `51c254ac…` / `e275879f…` also predate 2-06 and do not reproduce at HEAD.

Replacement byte evidence: (a) new code with **only** the stored-pixel branch restored reproduces HEAD byte-for-byte (full disc `1518dc62…`, Perth `1d29e76e…`) — proving the range threading and inclusive clamp move no bytes; (b) the new build's Perth `-j 1` == `-j 4`. New baseline: full disc `9407122122b9…`, Perth `99d72f0b1cf14b8b…`. The spool of record is `output/extract_timing/spool` (binary `KWSPIDX1`); `output/spool` is a legacy pickle spool that `SpoolReader` rejects.
