# Brief: 15b — Full-Australia build: verify through the harness; record deviations and capacity

Consumer: implementation worker (verification and documentation; code changes only if a
check reveals a defect in a path this brief names, and then only as a separate commit
naming the unit whose ownership it falls under).
Owned paths: `docs/design/target-disc.md` (only: the file table's WP1 rows' "deviations"
cells and the capacity paragraph), `docs/plans/01-eval-harness-and-map-layer/PLAN.md`
(only: Acceptance Criteria checkmarks are **not** to be added — record the run's numbers
under a new "Build record (date)" heading at the end), `docs/provenance.md` (entries for
`output/spool/`, `output/ALLDATA.KWI`, `output/manifest.json`, `output/report.json`).
Commit to the current branch when done evidence passes; push.
Depends on: 15 (its background run must be underway or finished).
Runs alongside: nothing.

Fresh agent — do not resume unit 15's agent (see `EXECUTION-COST-ANALYSIS.md` in this plan
folder on why a resumed agent pays a 6-8x cache-reset tax on its next call regardless of the
wait length, which is exactly what this split avoids). Read unit 15's report-back for the
exact commands, log paths and PIDs it started; do not re-derive or re-launch them.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Acceptance Criteria" (both
   lists) verbatim; these are the pass/fail statements for this unit.
2. `docs/design/target-disc.md` — check table; file table; **Capacity accounting**;
   "Decisions that shape everything" 1 (generation from scratch; every departure recorded
   in the file table).
3. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` section 7 (the declared WP2 slots
   — these are expected, recorded deviations, not failures).
4. `parser/compare_disc.py --help`, `parser/refdata/harness.json`.
5. Unit 15's report-back — the commands, log paths and PIDs it started.

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

1. Wait for unit 15's background job to finish. Use one blocking wait per stage (e.g. `wait
   <pid>`, `tail --pid=<pid> -f /dev/null`, or a single shell invocation looping with a
   generous sleep — `while pgrep -f osm_to_parcel_geometry.py >/dev/null; do sleep 60; done`
   — as one tool call), not repeated liveness-check tool calls across many turns.
2. Read the `time -v` logs for wall time and peak RSS of both stages; read the build's
   `manifest.json` for output size and SHA-256.
3. Repeat the build step only (spool unchanged): re-run `.venv-rp/bin/python
   parser/build_alldata.py` and confirm the SHA-256 matches the first run's.
4. `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report output/report.json` (all checks).
5. Each user-facing acceptance bullet in `PLAN.md`: run its command as written; record exit
   status and the relevant output line.
6. Round-trip regression: `.venv-rp/bin/python -m pytest parser/tests -q`.
7. Write the build record into `PLAN.md` and the deviations into the design doc's file
   table; add the provenance entries.

## Done evidence

- `output/report.json` exists and every check is PASS or is a recorded deviation naming its file-table row.
- Two builds (unit 15's first run and this unit's repeat) produce the same SHA-256.
- All acceptance-list commands exit 0 with the described output, or the record says which do not and why.
- `git status` clean after commit; no file in `output/` staged.

## Report back

The build record (wall times, RSS, size, SHA), the per-check table, the deviations list,
any acceptance bullet that does not hold, and any contradiction you found between the plan's
acceptance criteria and what the harness or design doc actually requires. **Do not resolve
contradictions silently — report them.** If you find a non-trivial bug outside this unit's
own contract, report it (symptom, location, root cause if found) and leave it — do not fix
it here.
