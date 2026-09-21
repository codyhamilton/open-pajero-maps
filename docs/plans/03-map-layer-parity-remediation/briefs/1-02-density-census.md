# Brief: 1-02 — Census of R vertices-per-link, vertices-per-km and road length

Consumer: implementation worker; result consumed by 1-03 (bands) and Phase 5 (density band).
Owned paths: `parser/tools/road_density_census.py` (new), `parser/refdata/profile/density.json` (new), `parser/tests/test_road_density_census.py` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing.
Runs alongside: 1-01, 1-05, 1-06, 1-07, 1-08.
Budget: 6 files to read, about 250 lines to change, 35 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Phase 1 "Also delivers"; Phase 5 Outcome; "Content generalisation" Contract (generalise.json band).
2. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F5.
3. `parser/harness/walk.py` — `iter_parcels`; `parser/harness/profile.py` — how existing censuses walk R.
4. `parser/refdata/README.md` — format of profile files (add nothing to it; note the new file in your report so 1-09 can).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Per-level statistics of R's road geometry so that Phase 5's density band and the Phase 1 bands have a measured basis: for each level, links, vertices (nodes plus intermediate points), vertices per link, total road length (km, from lat/lon-converted parcel coordinates; state the coordinate range used), vertices per km, each as mean and p50/p90.

## Contract

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Cited: "a vertices-per-km and road-length census of R (needed by Phase 5's density band)". The census reads R only through `parser/harness/` reading paths; it must not import writer modules (`parser/harness/__init__.py` constraint). Output is deterministic (sorted keys, no timestamps).

## Changes

- Length must use the coordinate scale that decodes R correctly for the parcel; the true model is not settled until Phase 2, so compute length from the level's cell extent (from `parser/refdata/grid.json`) divided by the parcel's coordinate maximum for the class (4096 at L2-L8, 16384 sparse L0 per DESIGN F1), and record which rule was used in the JSON as `length_basis`. Vertices-per-link needs no scale.
- Parallelise per block if the walk allows; wall time for a full R pass goes into the report.

### Keep untouched

`parser/refdata/profile/map.json` and `parser/harness/*` (read only).

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests/test_road_density_census.py -q` → passes (synthetic parcel fixtures, includes a determinism test).
- `.venv-rp/bin/python parser/tools/road_density_census.py --reference /run/media/codyh/464210-8480 --out parser/refdata/profile/density.json` → writes the file; run twice, `sha256sum` identical. File has an entry for every level R populates.
- Sanity: L8 total vertices in the file is within 1% of the 28.9k figure in DESIGN Phase 5 Outcome, or the deviation is reported.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
