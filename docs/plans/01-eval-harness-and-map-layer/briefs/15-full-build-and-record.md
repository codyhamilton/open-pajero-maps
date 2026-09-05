# Brief: 15 — Full-Australia build through the harness; record deviations and capacity

Consumer: implementation worker (verification and documentation; code changes only if a
check reveals a defect in a path this brief names, and then only as a separate commit
naming the unit whose ownership it falls under).
Owned paths: `docs/design/target-disc.md` (only: the file table's WP1 rows' "deviations"
cells and the capacity paragraph), `docs/plans/01-eval-harness-and-map-layer/PLAN.md`
(only: Acceptance Criteria checkmarks are **not** to be added — record the run's numbers
under a new "Build record (date)" heading at the end), `docs/provenance.md` (entries for
`output/spool/`, `output/ALLDATA.KWI`, `output/manifest.json`, `output/report.json`).
Commit to the current branch when done evidence passes; push.
Depends on: all of 01–14.
Runs alongside: nothing.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Acceptance Criteria" (both
   lists) verbatim; these are the pass/fail statements for this unit.
2. `docs/design/target-disc.md` — check table; file table; **Capacity accounting**;
   "Decisions that shape everything" 1 (generation from scratch; every departure recorded
   in the file table).
3. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` section 7 (the declared WP2 slots
   — these are expected, recorded deviations, not failures).
4. `parser/compare_disc.py --help`, `parser/refdata/harness.json`.

## Goal

Produce the WP1 deliverable: a full-coverage `ALLDATA.KWI` built from scratch by the
default commands, judged by the harness, with every remaining difference from `R` written
down where the design doc says it lives.

## Contract

Plan Acceptance Criteria (binding, verbatim from `PLAN.md`). A deviation is acceptable
only if it is (a) a `DESIGN.md` section-7 WP2 slot, or (b) recorded in the design doc's
file table with the check that reports it. Nothing else may be waived, and the harness
config may not be loosened by this unit.

## Changes

1. From a clean tree: `rm -rf output/ && .venv-rp/bin/python parser/osm_to_parcel_geometry.py && .venv-rp/bin/python parser/build_alldata.py` (both without flags), each under `/usr/bin/time -v`; capture wall time, peak RSS, output size, SHA-256.
2. Repeat the build step (spool unchanged) and confirm the SHA-256 matches.
3. `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report output/report.json` (all checks).
4. Each user-facing acceptance bullet in `PLAN.md`: run its command as written; record exit
   status and the relevant output line.
5. Round-trip regression: `.venv-rp/bin/python -m pytest parser/tests -q`.
6. Write the build record into `PLAN.md` and the deviations into the design doc's file
   table; add the provenance entries.

## Done evidence

- `output/report.json` exists and every check is PASS or is a recorded deviation naming its file-table row.
- Two builds produce the same SHA-256.
- All acceptance-list commands exit 0 with the described output, or the record says which do not and why.
- `git status` clean after commit; no file in `output/` staged.

## Report back

The build record (wall times, RSS, size, SHA), the per-check table, the deviations list,
any acceptance bullet that does not hold, and any contradiction you found between the plan's
acceptance criteria and what the harness or design doc actually requires. **Do not resolve
contradictions silently — report them.**
