# Brief: 3-04 — the `coord_scale` check and the per-vertex quantisation round-trip

Consumer: 3-06, which runs both against the rebuilt disc to decide the phase outcome; 3-03, which may run the check against its own build.
Owned paths: new `parser/harness/checks/coord_scale.py`, new `parser/tools/quantisation_roundtrip.py`, new `parser/tests/test_harness_coord_scale.py`, new `parser/tests/test_quantisation_roundtrip.py`. Create only these four; touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-01.
Runs alongside: 3-02, 3-03 (disjoint paths).
Budget: 8 files to read, about 400 lines to write, 50 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "#### Phase 3 — Outcome, as amended" in full. It is this unit's entire reason for existing.
2. `parser/refdata/profile/coord_scale.json` — `ranges` and `class_rule`.
3. `parser/kiwiw/coordconv.py` — `range_for` and the conversions as 3-01 left them, plus 3-01's report back for the signatures.
4. `parser/harness/checks/envelope.py` — the module shape: `_run_envelope(ctx) -> CheckResult` and the module-level `CHECKS = [Check(id=..., layer=..., description=..., run=...)]` list. The registry auto-discovers `checks/*.py`, so no registry edit is needed.
5. `parser/harness/context.py` — `Context`, `CheckResult`, `WalkSummary` (the memoised walk, so your check does not re-walk the disc on its own).
6. `parser/harness/walk.py` — `iter_parcels`, `WalkedParcel` and its `frame_bounds` / `frame_range` / `frame_class` fields.
7. `parser/kiwiw/spool.py` — the reader API and the column names (`n_x`, `n_y`, `n_lat`, `n_lon`, `p_lat`/`p_lon`, `c_lat`/`c_lon`, `s_lat`/`s_lon`).
8. `parser/tests/test_harness_profile.py` or `test_harness_core.py` — how harness checks are tested without a disc.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Build the two measurements the phase outcome names, so the phase can be judged rather than asserted. This unit writes no encoder or decoder code and changes no existing file.

## Contract

Cited, DESIGN.md, "#### Phase 3 — Outcome, as amended", verbatim:

> Grounded: `range_for` feeds both encoders and no `COORD_RANGE` constant remains (a source check, not a judgement); the `coord_scale` check PASSES; two builds are byte-identical at worker counts 1, 4 and 12; `pytest parser/tests` passes. The first clause is tightened: "coordinate maxima equal `coord_scale.json`" is content-dependent — a sparse cell legitimately never reaches its maximum — and is replaced by **zero parcels exceeding their class range**, the same invariant Phase 2 uses, plus a **per-vertex quantisation round-trip**: lat/lon to pixel to lat/lon agrees within half a pixel for every vertex written.

Binding, and settled — do not re-derive:

- **The check's criterion is "zero parcels exceeding their class range".** Not "maxima equal `coord_scale.json`". A sparse cell that never reaches 16384 is correct, not a failure. Do not add an "expected maximum" assertion, a minimum-occupancy rule, or a tolerance band; the criterion is an inequality with zero as its threshold. The check reports the observed per-class maxima as **details**, because they are informative, and passes or fails only on the exceedance count.
- The check is **`id="coord_scale"`, `layer="map"`**, in `parser/harness/checks/coord_scale.py`, discovered automatically. It walks the disc under test via `Context`'s memoised walk, derives each parcel's range with `coordconv.range_for` (never a literal, never `coord_scale.json`'s `max` used as a divisor), and counts parcels holding any vertex outside `[0, range]` — **inclusive**; a value of exactly `range` is legal and is what R's `share_at_max = 1.0` records.
- The check must **FAIL on the current generated disc and PASS on R**. That asymmetry is the proof it measures anything. Run it against both and report both, before any of 3-02/3-03's work lands. A check that passes on today's G is wrong.
- **The round-trip's frame does not depend on division.** A divided sub-parcel is encoded in its parent's 4096 frame, so the frame a vertex lands in is a function of `(level, ix, iy)` and the class rule alone. The tool therefore needs no knowledge of the division policy. If you conclude otherwise, stop and report `needs context` — do not model division.
- **The round-trip's real content is detecting clamping.** `round()` alone cannot err by more than half a raw unit, so a vertex only fails the half-pixel criterion when it falls outside its frame and is clamped. Say this in the tool's docstring, and make the tool report the clamped vertices — their level, class, count, and the worst overshoot in raw units — not just a boolean. "Half a pixel" is half of one raw unit, i.e. the frame's lon/lat extent divided by `2 * range`; state the definition in the output.
- The tool covers **every vertex in the spool**, over every vertex kind the spool carries (`n_`, `p_`, `c_`, `s_`), and states its coverage as counts in its output. If any vertex kind cannot be covered, name it and say why rather than quietly omitting it. Vectorise over spool columns; a per-vertex Python loop over a 7 GB spool will not finish.
- Output is deterministic: sorted keys, no timestamps, no absolute paths outside the arguments.

R is mounted read-only at `/run/media/codyh/464210-8480`; G is `output/ALLDATA.KWI`; the spool is `output/spool` (`output/manifest.json`'s `spool_dir` records a stale `.claude/worktrees/...` path — ignore it, do not "fix" it, never edit worktree copies). Python is `.venv-rp/bin/python`. The checks run through `parser/compare_disc.py`.

## Changes

Two new modules and their two new test modules. Nothing else.

### Keep untouched

Every existing file. In particular: do not edit `parser/harness/registry.py` (auto-discovery), `parser/refdata/harness.json` (the check needs no config row; if you believe it does, report `needs context` rather than adding one), `parser/refdata/profile/coord_scale.json` (read-only, never regenerated here), `docs/plans/**` including `EXPECTATIONS.md` (the orchestrator records the new check's expected state), and anything owned by 3-01, 3-02 or 3-03.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_harness_coord_scale.py parser/tests/test_quantisation_roundtrip.py -q` passes, on synthetic fixtures with no disc: a parcel one raw unit over its range failing; a parcel at exactly its range passing; an L0 sparse parcel judged at 16384 and an L0 urban one at 4096; a divided sub-parcel judged at 4096, not 2048.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report counts before and after.
- The check **against R**: PASS, zero exceedances across all 28 classes. Report the message and the per-class observed maxima.
- The check **against the current `output/ALLDATA.KWI`**: FAIL, with the exceedance count. Report the message. State plainly that it fails before the encoder work and is expected to pass after.
- `.venv-rp/bin/python parser/tools/quantisation_roundtrip.py --spool output/spool --out <scratch>/roundtrip.json` — report the wall time, the vertex counts per kind, the number of vertices failing the half-pixel criterion, and the worst overshoot. Against the spool as it stands (encoders not yet migrated) this measures the source geometry against the native frames; report the number, whatever it is, and do not tune the tool to make it small.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

State the exact command lines for the check and the tool, and the shape of the tool's JSON output — 3-06 runs both and reads the output. State the check's verdict on R and on today's G, both.

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

For this unit: take each parcel's range from `walk.leaf_frame_range` / `range_for`, never from a local copy of the class arithmetic; a divided sub-parcel's frame is its parent slot.
