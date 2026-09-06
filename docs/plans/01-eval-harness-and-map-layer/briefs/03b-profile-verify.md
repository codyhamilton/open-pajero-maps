# Brief: 03b — Reference profile: verify the real-disc runs, check in the profile, commit

Consumer: implementation worker (fresh — do not resume unit 03's agent; per
`EXECUTION-COST-ANALYSIS.md` a resumed agent pays a 6-8x cache-reset tax on its next call
regardless of how long the wait was, and this unit's whole reason to exist is to avoid that).
Owned paths: `parser/refdata/profile/map.json` (new — write it, this unit's one code-adjacent
deliverable), plus committing unit 03's already-implemented code. Do not edit unit 03's code
unless one of the checks below fails; if it does, report the failure — do not silently patch
around a wrong number.
Commit to the current branch when done evidence passes; push.
Depends on: 03 (must have started the background runs described in its Kickoff section).
Runs alongside: 04, 05, 06, 07, 08 (touches no file any of them own).

## Required reading, in order

1. This plan folder's `EXECUTION-COST-ANALYSIS.md` — why this unit exists as a separate,
   fresh agent rather than a resume of unit 03.
2. Unit 03's report-back (the two commands it started, their log paths, and any PID) —
   read it from wherever the orchestrator routed it; do not re-derive the commands yourself.
3. `briefs/03-reference-profile.md` — Contract and Changes sections, for what the profile and
   checks must show.
4. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — Open Questions (mfde entries 3..19;
   name string types; per-level road selection tolerance) and the acceptance bullets on
   vocabulary subsets, count envelopes and mfde entry count.

## Goal

Confirm the two real-disc runs unit 03 started have finished cleanly, confirm the profile is
reproducible, and land the checked-in profile plus unit 03's code as one committed unit.

## Contract

Same as unit 03's Contract section (cited there from `docs/design/target-disc.md` and
`PLAN.md`) — this unit does not re-litigate it, only verifies the real disc satisfies it.

## Changes

Wait for unit 03's background job to finish. Use one blocking wait (e.g. `wait <pid>` if the
shell is still attached, or `tail --pid=<pid> -f /dev/null`, or a single generously-timed
poll loop written as one shell invocation — `while pgrep -f compare_disc.py >/dev/null; do
sleep 30; done`), not repeated tool calls each checking liveness once. One tool call should
do the whole wait.

Once both commands in the log have exited:

1. Read the profile log; confirm `parser/refdata/profile/map.json` was written and inspect it
   for the level-0 string types, mfde entry counts and absent-slot value, and `nregion` values
   the Contract section describes as hypotheses to confirm or correct.
2. Re-run `.venv-rp/bin/python parser/compare_disc.py --profile --reference
   /run/media/codyh/464210-8480` once more (a second real invocation, foreground is fine here
   since this unit's whole job is to wait) and diff against the first run's output —
   `git status --porcelain parser/refdata/profile` must show no change once the file is
   staged from the first run.
3. Read the self-check log; confirm `vocab`, `envelope`, `mfde` all report PASS.
4. `.venv-rp/bin/python -m pytest parser/tests -q` → all pass (re-run; unit 03's own pass
   doesn't cover this unit's checked-in profile file).

## Done evidence

- `parser/refdata/profile/map.json` exists, is byte-identical across the two `--profile` runs,
  and its level-0/level-12 numbers match (or the report explains a deviation from) the
  hypotheses in unit 03's Contract section.
- `.venv-rp/bin/python parser/compare_disc.py --reference <root> --generated <root>/ALLDATA.KWI --checks vocab,envelope,mfde` → all PASS (read from the log unit 03 produced, or re-run if the log is missing/stale).
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `git log` shows one commit landing unit 03's code together with `parser/refdata/profile/map.json`.

## Report back

A short summary: the per-level tables for string types, road types, display classes, mfde
presence by index, and `nregion`; the capacity numbers (map bytes and non-map bytes); both
runs' wall times; anything that deviated from unit 03's hypotheses; and any contradiction
you found between unit 03's brief, this brief, and the contracts they cite. **Do not resolve
contradictions silently — report them.** If a check fails or a number doesn't match, report
it rather than editing unit 03's code to make it pass. If you find a non-trivial bug outside
this unit's own contract, report it (symptom, location, root cause if found) and leave it —
do not fix it here.
