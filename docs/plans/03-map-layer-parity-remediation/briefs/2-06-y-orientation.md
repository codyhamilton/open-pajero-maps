# Brief: 2-06 — y orientation in `coordconv` and every copy of its formula

Consumer: implementation worker; result consumed by 2-08 and 2-04, and by Phase 3 (which owns the encoder rebuild).
Owned paths: `parser/kiwiw/coordconv.py`, `parser/kiwiw/_cenc.c` (the `to_xy` y line only), `parser/kiwiw/synth.py` (the `_bg_fast` y line only), `parser/tools/coord_scale_census.py` (`_raw` only), `parser/tools/road_density_census.py` (`parcel_metrics`'s raw recovery only), `parser/tests/test_parcel_geometry.py`, `parser/tests/test_road_encoder.py`, `parser/tests/test_harness_core.py`, `parser/tests/test_harness_profile.py`, `parser/tests/test_background_encoder.py`, `parser/osm_to_parcel_geometry.py` (its module docstring's coordinate description only). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-05 (it edits `road_density_census.py` and regenerates `density.json` before you do).
Runs alongside: 2-07.
Budget: 10 files to read, about 120 lines to change, 45 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-22 (user) — Phase 2 restart", item 2 (second half); "Architectural Implications", the *Rebuild cost* and *Determinism* bullets.
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the `2-03 overlay-test` record, "Done — Amendment 1 (orientation)" (the pooled y_up vs y_down table).
3. `parser/kiwiw/coordconv.py` — whole file (87 lines): module docstring, `xy_to_latlon`, `latlon_to_xy`.
4. The duplicated copies of the same formula, in this order: `parser/kiwiw/_cenc.c` `to_xy` (~line 113); `parser/kiwiw/synth.py` `_bg_fast` (~lines 240–243); `parser/tools/coord_scale_census.py` `_raw` (~line 40); `parser/tools/road_density_census.py` `parcel_metrics` (~line 80).
5. `parser/tests/test_parcel_geometry.py` (the SW-corner and round-trip tests, ~lines 231–295) and `parser/tests/test_road_encoder.py` (~lines 101–160).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make the parcel-local y axis mean what R's data says it means — y increases northward — everywhere the project converts between parcel pixels and lat/lon, so the decode side of the coordinate model is correct before the overlay is re-run, and so no two copies of the transform disagree.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-22 item 2: "the y orientation in `parser/kiwiw/coordconv.py` `xy_to_latlon` (y increases northward; the code is y-down and contradicts its own docstring). This authorises editing `coordconv.py`, which Phase 2's Surfaces listed read-only. Encoders keep byte-identical behaviour unless the fix requires otherwise; where it does, the impact is recorded for Phase 3."

Cited, 2-03's pooled evidence over 12 cells x 7 classes, y_up vs y_down matched fraction / p50 m (`IMPLEMENTATION.md`): "L0_urban 0.836/4.73 vs 0.094/50.33; L2 0.843/8.07 vs 0.190/210.78; L4 0.894/10.68 vs 0.138/1340.50; L6 0.875/25.43 vs 0.234/4412.48; L8 0.863/119.92 vs 0.145/58783.46; divided 0.773/3.62 vs 0.291/22.87; L0_sparse 0.717/26.51 vs 0.042/487.49." Settled: **y is up.** You are not re-testing this.

Cited, `parser/kiwiw/coordconv.py` module docstring: "We assume 'y increases toward the northern edge of the bbox' (screen-down convention flipped to geographic-up)" — while `xy_to_latlon` computes `lat = bounds.lat_hi - (yc / COORD_RANGE) * (lat_hi - lat_lo)`, which is y-down. The docstring is right and the code is wrong.

Cited, DESIGN "Architectural Implications", Determinism: "Every phase preserves byte-for-byte reproducibility for the same PBF and config."

`COORD_RANGE` stays `2**15` in this unit. Phase 3 owns replacing it with `range_for(level, parcel_class, division_state)`; do not start that here.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; G is `output/ALLDATA.KWI`. Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`.

## Changes

- `coordconv.xy_to_latlon`: y-up (`lat` increases with `yc` from `lat_lo`). `coordconv.latlon_to_xy`: the exact inverse, so the round-trip stays exact for integer pixels. Rewrite the module docstring's orientation paragraph to state the fact, cite 2-03's pooled evidence as its basis, and delete the "unconfirmed / this only affects north/south mirroring" hedge.
- Flip the three verbatim duplicates of the same formula in lockstep — `_cenc.c` `to_xy`, `synth.py` `_bg_fast`, and the two census tools' raw-recovery expressions. They are copies of `latlon_to_xy`, not independent code: leaving any of them y-down makes the C encoder and the Python oracle disagree (`parser/tests/test_cenc.py` compares them) or makes a census recover the complement of the coordinate it decoded. This lockstep edit is the minimum the fix requires; it is **not** licence to touch anything else in those files. If you find a fourth site, or the lockstep edit turns out to be more than a per-site y expression, stop and report `needs context` rather than widening the change yourself.
- `parser/tools/overlay_test.py` has its own `_raw`/`decode_uv` with an explicit `y_up` flag. It is 2-08's file: do not edit it.
- Update the tests that encode the old convention — the SW-corner assertion in `test_parcel_geometry.py` ("y=0 is north, so SW corner → full y") and any fixture comment saying the same — so they assert the new convention and would fail if it were reverted. Keep the round-trip tests as they are in substance.
- `parser/osm_to_parcel_geometry.py`'s module docstring describes the pixel grid; correct its orientation sentence if it states one. Change no code in that file.
- **Measure and report the encoder impact; do not hide it.** After the change, state: (i) whether `.venv-rp/bin/python -m pytest parser/tests -q` passes and which tests changed behaviour; (ii) for at least 20 parcels of a stated selection rule from the existing spool or from a small synthetic build, whether the encoded bytes change and how (expected: y values become `RANGE - y`); (iii) whether `parser/refdata/profile/{coord_scale,density}.json` regenerate byte-identically. Put this measurement in your report and in a short "Phase 3 impact" paragraph in your `IMPLEMENTATION.md` record, flagged as Phase 3's to absorb. A full rebuild of `output/ALLDATA.KWI` is **not** in scope and must not be run here.

### Keep untouched

Everything in `_cenc.c` and `synth.py` except the single y expression in each — Phase 3 owns those files and a broader edit here will collide with it. `COORD_RANGE`'s value. `parser/kiwiw/{road,background,name}.py` (they call `xy_to_latlon` and inherit the fix). `output/ALLDATA.KWI` and `output/manifest.json`. `parser/refdata/profile/coord_scale.json` and `density.json` as *content*: you regenerate them only to prove invariance, and if either changes, report it rather than committing a new version.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- A test that fails on HEAD and passes after: `xy_to_latlon(x, 0, b)` returns `b.lat_lo` and `xy_to_latlon(x, COORD_RANGE, b)` returns `b.lat_hi`, and `latlon_to_xy` inverts it exactly for a set of integer pixels.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report the pass/fail counts before and after and name every test whose expectation you changed.
- `.venv-rp/bin/python -m pytest parser/tests/test_cenc.py parser/tests/test_synth_vectorized.py -q` passes — the C encoder and the Python oracle still agree byte-for-byte (this is the check that proves the lockstep edit is complete). If `test_cenc` skips for lack of a C compiler, say so; that is a gap in the evidence, not a pass.
- Re-running `coord_scale_census.py` and `road_density_census.py` produces `coord_scale.json` and `density.json` byte-identical to the versions committed by 2-05. Report the two `sha256` values.
- The encoder-impact measurement above, with numbers.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. Lead with the encoder-impact measurement — Phase 3 depends on it being accurate.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
