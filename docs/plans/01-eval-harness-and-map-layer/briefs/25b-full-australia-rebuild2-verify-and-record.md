# Brief: 25b — Full-Australia rebuild #2: verify group 1's fix at scale; record a fresh report.json for unit 26

Consumer: implementation worker (fresh agent — do not resume unit 25's agent, same reasoning as
units 03b and 15b: a resumed agent pays a 6-8x cache-reset tax on its next call regardless of the
wait length). Verification and documentation only; code changes only if a check reveals a defect
in a path this brief names, and then only as a separate commit naming the unit whose ownership it
falls under (this unit owns no source code).
Owned paths: `docs/plans/01-eval-harness-and-map-layer/PLAN.md` (only: append a new "Build record
(date)" heading at the end — do **not** add Acceptance Criteria checkmarks), `docs/design/
target-disc.md` (only: the file table's WP1 `ALLDATA.KWI` map-layer row's "deviations" cell),
`docs/provenance.md` (only if a genuinely new non-committed artifact class appears that the
existing `output/spool/`/`output/ALLDATA.KWI`/`output/manifest.json`/`output/report.json`
entries don't already cover — check before adding a duplicate entry).
Commit to the current branch when done evidence passes; push.
Depends on: 25 (its background run must be underway or finished).
Runs alongside: nothing.

## Required reading, in order

1. Unit 25's report-back — the exact commands, log paths, PIDs, and disk-space judgment it
   recorded. Do not re-derive or re-launch anything it already started.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — the Acceptance Criteria bullets marked
   `(units 25/25b)` and `(units 25b/26)`, verbatim; these are this unit's pass/fail statements.
3. `docs/plans/01-eval-harness-and-map-layer/briefs/19-container-pdmdh-blob-tail.md` — "Amendment
   (post-implementation...)" section, for exactly what the `container` check FAIL looked like
   before (PDMDH-blob-length diff, R=21,088 G=18,624 bytes) and what "gone or a new, different
   cause" means in practice.
4. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Build record (2026-09-09)" section, for
   the stale baseline this run must diverge from (sha256
   `5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66`) and the per-check table
   format to follow when recording this run's results.

## Goal

Confirm unit 25's rebuild reflects briefs 19-24's fixes (not the stale pre-fix build), confirm
group 1's dune→bay fix actually closes the `container` check's PDMDH-blob-length FAIL at full
scale, and produce a fresh `output/report.json` with real per-level `parcel_count`/`name_count`
data for unit 26 to design against.

## Contract

`PLAN.md`'s Acceptance Criteria bullets `(units 25/25b)` and `(units 25b/26)`, verbatim:

- A full-Australia rebuild produced after briefs 19-24 land (sha256 differing from
  `5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66`) is checked with
  `compare_disc.py --checks container` against the mounted reference disc; the PDMDH-blob-length
  violation is gone or the report states a new, different cause.
- The same rebuild's fresh `output/report.json` records per-level `parcel_count`/`name_count`
  generated/reference/ratio values.

The harness config may not be loosened by this unit.

## Changes

1. Wait for unit 25's background job to finish. Use one blocking wait per stage (e.g. `wait
   <pid>`, `tail --pid=<pid> -f /dev/null`, or a single shell invocation looping with a generous
   sleep as one tool call), not repeated liveness-check tool calls across many turns.
2. Confirm `output/ALLDATA.KWI`'s sha256 differs from `5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66`
   (the stale pre-fix build). This is a required, explicit check per the acceptance bullet — not
   optional.
3. Read the `time -v` logs for wall time and peak RSS of both stages; read `output/manifest.json`
   for output size and its own recorded SHA-256 (cross-check against step 2's).
4. Run the full harness once (this satisfies both this unit's `container` need and unit 26's
   data need — do not run it twice):
   `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report output/report.json`
5. Read `output/report.json`'s `container` check result specifically: is the PDMDH-blob-length
   diff gone, or does a different, named cause remain? Record which.
6. Read `output/report.json`'s `envelope` check per-level `parcel_count`/`name_count`
   generated/reference/ratio values for levels 0/2/4/6/8 (the levels the 2026-09-09 build
   recorded as FAILing) — this is the data unit 26 needs; quote the actual numbers in your
   report-back, do not just say "still failing."
7. Round-trip regression: `.venv-rp/bin/python -m pytest parser/tests -q`.
8. Write the build record into `PLAN.md` (wall times, RSS, size, both SHA-256 values and the
   confirmation they differ from the stale baseline, the per-check table, particularly
   `container` and `envelope`'s per-level parcel_count/name_count breakdown) and any genuine new
   deviation into `docs/design/target-disc.md`'s file table.

## Done evidence

- `output/report.json` exists; its sha256-of-`ALLDATA.KWI` differs from
  `5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66`.
- `container` check result recorded: PASS, or FAIL with a named cause different from the
  2026-09-09 PDMDH-blob-length diff.
- `envelope` check's per-level `parcel_count`/`name_count` generated/reference/ratio values for
  every level recorded (quoted, not summarized away) — this is unit 26's required input.
- `pytest parser/tests -q` passes with no regression in replicate-mode byte-identical tests.
- `git status` clean after commit; no file in `output/` staged.

## Report back

The build record (wall times, RSS, size, both SHA-256 values), the full per-check table
(especially `container`'s exact status/cause and `envelope`'s per-level `parcel_count`/
`name_count` numbers for every level, quoted), whether group 1's fix is confirmed closing the
`container` FAIL at scale, and any contradiction you found between the plan's acceptance
criteria and what the harness actually reports. **Do not resolve contradictions silently — report
them.** If you find a non-trivial bug outside this unit's own contract, report it (symptom,
location, root cause if found) and leave it — do not fix it here.
