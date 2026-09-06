# Brief: 15 — Full-Australia build: kickoff

Consumer: implementation worker (verification only; no code changes — if a check fails
because of a real defect, report it, do not fix it here).
Owned paths: none to edit. This unit only runs commands and reports; it writes no file in
the repo (its background-run logs live outside the repo tree, per Changes below).
Do not commit anything. Leave the working tree exactly as it is on entry.
Depends on: all of 01–14.
Runs alongside: nothing.

This unit is split from the original single "full build and record" unit because its full
done evidence depends on the same country-scale extraction unit 07 already ran once
(1:27:24 wall time) plus a full assembler pass over it — a multi-hour wait. Per
`EXECUTION-COST-ANALYSIS.md` in this plan folder, sitting inside one agent's turn polling a
background subprocess like this was the single largest source of wasted cost in the
units-01/02/07 run (58% of unit 07's own calls came after its last write, most of them
liveness polls). This unit does only the kickoff; unit 15b (a fresh agent — never a resume
of this one, to avoid the cache-reset tax `EXECUTION-COST-ANALYSIS.md` documents) waits for
the result, verifies it, and writes the build record.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Acceptance Criteria" (both lists),
   so you know what unit 15b will need output for.
2. `parser/osm_to_parcel_geometry.py --help`, `parser/build_alldata.py --help`.

## Goal

Start the from-scratch, full-Australia extraction and build, running unattended, and hand
off enough information that a fresh agent can find and judge the result without re-deriving
anything.

## Contract

None new — this unit produces inputs for unit 15b's contract (`PLAN.md`'s Acceptance
Criteria, verbatim, binding there).

## Changes

From a clean tree:

```
rm -rf output/
mkdir -p /tmp/wp1-unit15-logs
nohup bash -c '
  /usr/bin/time -v .venv-rp/bin/python parser/osm_to_parcel_geometry.py \
    2> /tmp/wp1-unit15-logs/extract.time.log \
    > /tmp/wp1-unit15-logs/extract.out.log &&
  /usr/bin/time -v .venv-rp/bin/python parser/build_alldata.py \
    2> /tmp/wp1-unit15-logs/build.time.log \
    > /tmp/wp1-unit15-logs/build.out.log
' > /tmp/wp1-unit15-logs/kickoff.log 2>&1 &
disown
```

Confirm the process actually started (one liveness check, e.g. `pgrep -f
osm_to_parcel_geometry.py`) and that `output/` is being written to. Do not wait on it, do
not sleep-and-recheck in a loop, and do not use `Monitor` to sit on it. End your turn once
you've confirmed it started.

Unit 07's own full run took 1:27:24 for extraction alone at ~9.7 GB peak RSS; treat that as
the floor, not a guarantee — `build_alldata.py`'s wall time over the full spool has no prior
benchmark (unit 12's own full-spool step is optional/best-effort and may not have run to
completion). Say this in your report-back so unit 15b sizes its wait accordingly.

## Done evidence

- `pgrep -f osm_to_parcel_geometry.py` (or equivalent) confirms the process is running.
- `/tmp/wp1-unit15-logs/kickoff.log` and the per-stage logs exist and are being appended to.

## Report back

The exact commands you ran, every log path, the PID(s), and unit 07's benchmark numbers
above as context for expected duration. **Do not resolve any contradiction you notice
silently — report it.** If you find a non-trivial bug outside this unit's own contract,
report it (symptom, location, root cause if found) and leave it — do not fix it here.
