# Brief: 3-07 — clip background geometry to the frame, as R does

Consumer: 3-05, which builds the determinism matrix from the tree this unit leaves; 3-06, which runs the per-vertex quantisation round-trip against the definition this unit lands.
Owned paths: new `parser/kiwiw/clip.py`, `parser/kiwiw/synth.py`, `parser/kiwiw/_cenc.c`, `parser/kiwiw/cenc.py`, `parser/kiwiw/background_writer.py`, `parser/tools/quantisation_roundtrip.py`, new `parser/tests/test_clip.py`, `parser/tests/test_cenc.py`, `parser/tests/test_background_encoder.py`, `parser/tests/test_synth_vectorized.py`, `parser/tests/test_quantisation_roundtrip.py`. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-03 (it removes the legacy range and the encoders' transitional `32767` cap; this unit builds on the tree it leaves).
Runs alongside: nothing.
Budget: 12 files to read, about 600 lines to change, 90 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "#### Phase 3 — Outcome, as amended" and "#### New grounded rule: one global raw lattice per level". These are the contract.
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-02, 3-03 and 3-04 records (signatures, commands, the background-clamping concern).
3. `output/research-3-bg/bg_edge_probe_v2.json` and `bg_edge_probe.py` (gitignored, on disk) — the R evidence summarised below, and the probe you will re-run against G.
4. `parser/kiwiw/synth.py` — `_clamp_coord`, `_bg_fast`, `encode_background_shape_bytes{,_scalar}`, `build_background_frame_bytes`; `parser/kiwiw/_cenc.c` — `kw_bg_shape`, `enc_bg`, and the cell kernel's background call; `parser/kiwiw/cenc.py` — the matching wrappers.
5. `parser/tools/quantisation_roundtrip.py` (3-04's) and its test.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make G write background geometry the way R does at a frame edge — clipped, not clamped — and make the Phase 3 per-vertex round-trip measure the vertices G actually writes.

## Contract

The R evidence (research, 2026-09-24; orchestrator-accepted): R **clips** background polygons and lines to the coordinate frame. Across L0 urban/sparse, L2, L4, L6 and L8 samples, **0** background vertices lie outside `[0, range]`; frame-corner vertices mirror exactly into the neighbouring frame (≥ 98% at every class); edge-crossing vertices mirror exactly 75–87% and > 90% within 4 raw (clamping would give ≈ 0%); long runs of segments lie along the frame edge (clip artifacts), single on-edge spikes are rare; whole-cell fills are frame-corner rectangles; pen-up is never used; almost no zero-width "bridges" (0 at L0 urban, 4/4,130 at L6, 12/9,652 at L8), i.e. a polygon that leaves and re-enters the frame is emitted as **separate pieces**. Spec: roads 7.A ② ("cut them on the parcel boundary, then set the nodes on the boundary"); backgrounds 7.3.2.2.1.1 (coordinates limited to the parcel) and 7.3.2.2.1.1.1 (area data closed, counter-clockwise, non-self-crossing). The spool's background polygons are *not* pre-clipped (8.4% of background vertices lie outside their frame); roads already are, and are out of scope.

Binding:

- **Clip, never clamp.** After this unit no background vertex is written by clamping. `_clamp_coord` / `np.clip` on background coordinates go; a vertex outside `[0, range]` after clipping is a bug (assert, don't clamp).
- **Clip in the level's global raw lattice, before rounding.** Convert each vertex to global raw floats (`X = gx0*4096 + x_local` etc., per the grounded rule), clip against the frame's rectangle in that space, then subtract the frame origin and round. A crossing point is then computed from the same global geometry on both sides of the boundary, so the two frames agree exactly — do better than R's 75–87%.
- **Polygon clip against an axis-aligned rectangle with proper piece splitting** (no Sutherland–Hodgman bridges): a polygon that leaves and re-enters becomes several closed pieces, each its own shape record of the same type; insert the frame corners each piece covers; keep rings closed and counter-clockwise; drop degenerate results (zero area after rounding, repeated consecutive vertices, spikes). **Lines** (open background shapes) are clipped into one record per inside run, each ending exactly on the edge. A shape entirely outside its frame writes nothing; a shape covering the whole frame writes the frame-corner rectangle.
- **No new dependency** (no shapely/GEOS): write the rectangle clip in `parser/kiwiw/clip.py`, and the same algorithm in `_cenc.c`. Python and C must produce byte-identical output — extend `test_cenc.py`'s C-vs-Python equivalence to clipped shapes (leave/re-enter, corner-covering, fully inside, fully outside, whole-frame, lines).
- **Determinism.** Output must stay independent of `-j` and of piece-emission order; emit pieces in a defined order.
- **No pen-up**, no change to roads, names, the offset/step encoding, or the range model.
- **Round-trip definition** (the Phase 3 outcome's "every vertex written"): every vertex the encoder writes after clipping — original in-frame vertices and inserted crossing and corner points — compared against the clipped geometry's exact (pre-rounding) position, within half a pixel. `quantisation_roundtrip.py` must use `clip.py` for this, report written vertices per kind, and additionally assert (a) no written vertex outside `[0, range]`, (b) every inserted crossing vertex lies exactly at 0 or `range` on its crossed axis. Remove the "clamped" pass path; keep the per-level/class/kind JSON shape otherwise.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. The spool of record is `output/extract_timing/spool`. Python is `.venv-rp/bin/python`. `/tmp` hits its quota on full builds: scratch under `output/scratch-3-07/` with `TMPDIR` set there. Never edit worktree copies under `.claude/worktrees/`.

### Keep untouched

Roads (`road.py`, `road_writer.py`, the C road path), `coordconv.py`, `divide.py`, `build_alldata.py`, `spool.py`, `osm_to_parcel_geometry.py`, `parser/harness/**`, `parser/refdata/**`, all plan documents. Do not re-extract.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- New `test_clip.py` and the extended equivalence tests pass; `.venv-rp/bin/python -m pytest parser/tests -q` passes (report before/after counts).
- `quantisation_roundtrip.py --spool output/extract_timing/spool --out <scratch>/roundtrip.json` exits 0: 0 failing written vertices of every kind; report written-vertex totals per kind and the worst error in raw units.
- A full assembly from `output/extract_timing/spool` at `-j 12` into scratch; report sha256 and size. Perth fixture at `-j 1` and `-j 4` identical; report the sha.
- `compare_disc.py --generated <new ALLDATA.KWI> --checks coord_scale --no-manifest --report <scratch>/cs_G.json` PASS; report its summary line.
- Re-run the research probe (`output/research-3-bg/bg_edge_probe.py`, same sampling) against the new G and report its table beside R's: vertices outside range (must be 0), corner-vertex mirror, crossing-vertex mirror exact / ≤ 2 / ≤ 4 raw (expect ≈ 100% exact), bridge counts, spikes.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, the new disc and Perth shas, any deviation from this brief and why, and any contradiction between this brief and the contracts or R evidence it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
