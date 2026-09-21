# Brief: 2-03 — Overlay of decoded R against OSM at four named cells

Consumer: implementation worker; result consumed by 2-04 and by the phase gate verdict.
Owned paths: `parser/tools/overlay_test.py` (new), `parser/tests/test_overlay_test.py` (new), `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-03.json` (new, small result file). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-01 (`coord_scale.json` `ranges`).
Runs alongside: 2-02.
Budget: 7 files to read, about 300 lines to change, 45 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Phase 2 Outcome; Assumption Ledger first item.
2. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F1.
3. `parser/refdata/harness.json` — `bands` (the distance-tolerance entry `name_record_distance_tolerance`: rule `distance_m <= tol * cell_extent_m`, and the derivation rule); `parser/refdata/spot_checks.json` (coordinates for Brisbane and Sydney).
4. `parser/kiwiw/coordconv.py` — `xy_to_latlon`, `latlon_to_xy`; `parser/harness/walk.py`; `parser/kiwiw/parcel.py` — decode paths (read only).
5. `parser/refdata/profile/coord_scale.json` (2-01) and `parser/refdata/grid.json`.
6. How existing tools read the OSM extract (grep `australia-260824.osm.pbf` in `parser/`; reuse the reader, do not write a new PBF parser).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Test that R decoded at the per-class range from `coord_scale.json` lands on real roads: at four named cells, matched roads fall within the recorded distance tolerance, do not cluster into a sub-region of the cell, and clipped links end at the cell edge. Also run the same overlay decoding R at the current constant (32767) as the negative control, so the result shows the model discriminates.

## Contract

Cited: "decoding R at its per-class range and overlaying it against OSM at four named cells (Brisbane CBD, Sydney, rural QLD, outback) puts matched roads within a recorded distance tolerance with no clustering into a sub-region of the cell, clipped links terminating at the cell edge; ... the tolerance is the Phase 1 band and 'no clustering' is measured as the occupied fraction of the cell extent and coordinate maximum relative to the cell" (DESIGN, Phase 2 Outcome). Tolerance: `harness.json` `bands` (`distance_m <= tol * cell_extent_m`); read the number there, do not choose one. Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Census tools read R only through `parser/harness/` reading paths and must not import writer modules. Output is deterministic (sorted keys, no timestamps).

## Changes

- Name the four cells before the run, in the result file: Brisbane CBD and Sydney from `spot_checks.json`; a rural QLD cell and an outback cell chosen by a stated rule (e.g. the L2-L4 parcel nearest a named locality, present in R with >= 20 links) that you record with lat/lon and level/parcel ids. Choose them without looking at match quality.
- For each cell: decode R road links to lat/lon at the per-class range; match each to the OSM way it best follows (name-agnostic geometric match: median point-to-polyline distance, with a stated matching rule); report matched fraction and distance distribution vs tolerance.
- Clustering measure: occupied fraction of the cell extent (share of a fixed grid of the cell, e.g. 16x16, containing R road vertices, compared with the OSM roads' occupied fraction over the same cell) and coordinate maximum relative to cell (observed max / class range). A cell clustered into a sub-region (occupied fraction below half of the OSM figure) fails.
- Clipped links: those touching the parcel boundary end at 0 or the class range exactly; report the share.
- Result file: cell names, ids, tolerance value used and its source, per-cell numbers for the model and for the 32767 control, and a verdict per cell. No result file for a cell you could not run: report `blocked`.

### Keep untouched

Everything under `parser/kiwiw/`, `parser/harness/`, `parser/refdata/`.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests/test_overlay_test.py -q` passes (synthetic fixtures: a correct-range case passes; a wrongly scaled case fails the clustering measure).
- `.venv-rp/bin/python parser/tools/overlay_test.py --reference /run/media/codyh/464210-8480 --pbf australia-260824.osm.pbf --out docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-03.json` runs twice with identical output; all four cells pass the tolerance, clustering and edge-termination criteria under the model and the 32767 control fails at least the clustering measure at the L2-L8 cells.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. If the evidence contradicts the coordinate-range hypothesis, report `blocked` with the numbers: this phase is a gate and the design is bounced, not patched.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.


## Amendment after first attempt (blocked, uncommitted work in tree)

First attempt left uncommitted `parser/tools/overlay_test.py`, `parser/tests/test_overlay_test.py`, `EVIDENCE-2-03.json` (start from these). Findings: Sydney passed; Brisbane CBD near-pass (79.8% matched, 84.5% clipped-at-edge); rural/outback cells had only 5-6 links so the occupancy and matched criteria were noise; the 32768 control fails clustering everywhere. Two real issues must be resolved, not waived:
1. `coordconv` y orientation: y-up (flipped) fits far better than the documented y-down. Establish the orientation canonically (evidence across several cells) and report it; do not edit coordconv (Phase 3 owns it).
2. Divided sub-parcels: a divided sub-leaf at range 4096 (and 2048 for sub 0) matched 13% at 304 m. Determine how sub-parcel bounds relate to the coordinate range (e.g. sub-parcel covers a quadrant of the leaf and its range is 4096 over the quadrant, sub 0 being 2048 over a different span) by testing hypotheses against OSM; report the canonical rule or that none fits.
Method fixes: pick cells (rural, outback) with >=20 links even if at a coarser level or a larger set of cells, up to 3 per class; measure occupancy by comparing R's occupied fraction with OSM roads that R links also match (like-for-like: use OSM roads within tolerance of R-decoded links plus unmatched OSM roads of the same class set), or use pooled statistics over >=10 cells per class instead of single cells. State thresholds before running. The gate passes only if the coordinate model (range 4096/16384 per class, with orientation and divided-cell rule established) is supported; report `blocked` with numbers if it truly is not. Do not weaken criteria to pass.
