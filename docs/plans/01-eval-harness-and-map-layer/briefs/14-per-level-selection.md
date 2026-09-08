# Brief: 14 — Per-level feature selection matched to the profile census

Consumer: implementation worker.
Owned paths: `parser/kiwiw/selection.py` (new), `parser/refdata/selection.json` (new),
`parser/tests/test_selection.py` (new), and in `parser/osm_to_parcel_geometry.py` **only**
the `level_filter` default (wire it to `selection.level_filter`). Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 08 (vocab tables), 10 and 11 (their extractor edits), 03b (profile, committed).
Runs alongside: 13.

## Required reading, in order

1. `docs/design/target-disc.md` — check-table rows **Profile envelope** and **Capacity**;
   **Capacity accounting** contract.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Execution Phases" row for unit 14 (the original phase text: "Per-level road selection and generalisation matched to the reference's per-level census (level 0 bound by size/capacity)")
   (all seven levels with per-level selection "matched to the census") and Open Question
   **Per-level selection tolerance** ("the tolerance is recorded in the harness config, not
   implied").
3. `parser/refdata/profile/map.json` — per-level counts (links, shapes, names, bg rings),
   road-type histograms, frame-size percentiles; `parser/refdata/harness.json`
   `envelopes.count_ratio` and `level0_count_exempt`.
4. `parser/refdata/vocab/` (unit 08), `parser/osm_to_parcel_geometry.py` `level_filter` seam
   (unit 07).
5. Unit 07's report numbers (spool stats per level with all features at all levels).

## Goal

Each level receives the subset of OSM features that puts the generated disc's per-level
content counts inside the harness's envelope around `R`, and keeps level 0 within capacity.

## Contract

Selection is data (`selection.json`): per level range, which `highway` classes (and which
background/place classes) are included, plus a minimum way length in metres for
generalisation at levels ≥4. `selection.level_filter(level, tags) -> bool`. The envelope is
the harness's `count_ratio` (default [0.5, 2.0]) at levels 2..12; level 0 is exempt from the
count envelope (`level0_count_exempt`) but bound by the capacity check. Do not change the
tolerance in `harness.json` to make a level pass; if a level cannot be brought inside the
envelope with class selection alone, report the achievable numbers and stop.

## Changes

- `selection.json` + loader with validation; `level_filter` wired as the extractor default.
- Tests: the filter admits motorways at 12 and residential only at 0/2 (or whatever the
  table says — the test reads the table); a unit test for the length threshold.
- Calibration run: tune the table using the spool stats via a dry-run mode that only counts
  (add it to `selection.py`, not the extractor) until the envelope passes at levels 2..12.
  Do not run a full-Australia extract+build to iterate — unit 07's own run took 1:27:24 for
  extraction alone; use the cheap counting path for every tuning pass.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- Dry-run counts (spool stats via `selection.py`'s counting mode) show `envelope` inside
  `count_ratio` at levels 2..12 and `capacity` within bound, or the report gives the
  level-0 overshoot and the trade-off unit 15 must record.
- **Do not run `build_alldata.py` (no args) or `compare_disc.py` against a full-Australia
  build in this unit** — that duplicates unit 15's own multi-hour build. The real
  envelope/capacity PASS confirmation against the full build happens in unit 15b, against
  the one full build unit 15 kicks off; this unit's job is to land `selection.json` in a
  state that build is expected to pass with, using only the cheap dry-run path.

## Report back

A short summary: the per-level table and the counts it achieved vs `R`, anything you
deviated from in this brief and why, and any contradiction you found between this brief and
the contracts it cites. **Do not resolve contradictions silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
