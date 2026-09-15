# Brief: 25 — Full-Australia rebuild #2: kickoff

Consumer: implementation worker (kickoff only; no code changes — if you notice a real defect,
report it, do not fix it here).
Owned paths: none to edit. This unit only runs commands and reports; it writes no tracked file in
the repo (its background-run logs live outside the repo tree, per Changes below; `output/` is
gitignored).
Do not commit anything. Leave the working tree exactly as it is on entry.
Depends on: 15b, ad-hoc briefs 19-24 (all landed on master — group 1 dune→bay fix, group 2
divide.py drop-order + Perth place type_code, group 3 mfde investigation, group 4 name-record
vocab fix).
Runs alongside: nothing.

This unit is split from the rebuild's verification exactly the way unit 15/15b and unit 03/03b
were: the full done evidence depends on a country-scale extraction + assembler pass (unit 15's
own run: 33:23 extraction + 6:44 assembly), and `EXECUTION-COST-ANALYSIS.md` in this plan folder
found that sitting inside one agent's turn polling a background subprocess was the single largest
source of wasted cost in the units-01/02/07 run. This unit does only the kickoff; unit 25b (a
fresh agent — never a resume of this one) waits for the result, runs the harness, and records it.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Re-refinement findings (2026-09-15)"
   (why this rebuild exists and what it must prove), the "Disk space, carried forward..."
   paragraph (the required disk-space handling for this unit specifically), and the Acceptance
   Criteria bullet marked `(units 25/25b)`.
2. `docs/plans/01-eval-harness-and-map-layer/briefs/15-full-build-and-record.md` — the kickoff
   command shape this unit reuses (same two-stage extractor → assembler pipeline, same
   nohup/disown pattern).
3. `docs/plans/01-eval-harness-and-map-layer/briefs/19-container-pdmdh-blob-tail.md` — "Amendment
   (post-implementation...)" section, for why this rebuild is needed at all (group 1's fix was
   only confirmed by mechanism on a Perth fixture, never at full-Australia byte-level scale).

## Goal

Start a from-scratch, full-Australia extraction and build over the current master (post
briefs 19-24), running unattended, from a demonstrably-cleared `output/` and with disk space
explicitly checked beforehand — then hand off enough information that a fresh agent (unit 25b)
can find and judge the result without re-deriving anything.

## Contract

None new — this unit produces inputs for unit 25b's contract (`PLAN.md`'s Acceptance Criteria
bullets marked `(units 25/25b)` and `(units 25b/26)`, binding there).

## Changes

1. **Disk-space check, explicit, before touching anything.** Run `df -h /home` and record the
   free space. Then run `du -sh output/` (the current worktree's `output/` is the stale
   2026-09-09 pre-fix build — confirmed by `PLAN.md` to be sha256
   `5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66` — plus its ~6.9GB
   `spool/`) so you know how much this step will reclaim. Compute and report: free space now,
   free space expected after `rm -rf output/`, and whether that is comfortably above unit 14's
   observed real spool footprint (~6.9GB, not the ~21GB unfiltered figure — see `PLAN.md`'s
   "Disk space" paragraph) plus the ~814MB built `ALLDATA.KWI` plus a safety margin. If the
   post-clear free space is not comfortably above that (use your judgment, but treat "less than
   2x the ~6.9GB spool footprint" as the line), **stop and report** — this is its own failure
   mode per unit 15's original note, not a process crash to debug blindly. Do not proceed to
   step 2 if you stop here.
2. `rm -rf output/` — clear the stale build. Confirm afterward (`ls output/` should fail or be
   empty/absent) and re-run `df -h /home` to confirm the reclaimed space matches your step-1
   estimate.
3. Start the extraction + assembler pipeline in the background, following unit 15's exact
   pattern:

```
mkdir -p /tmp/wp1-unit25-logs
nohup bash -c '
  /usr/bin/time -v .venv-rp/bin/python parser/osm_to_parcel_geometry.py \
    2> /tmp/wp1-unit25-logs/extract.time.log \
    > /tmp/wp1-unit25-logs/extract.out.log &&
  /usr/bin/time -v .venv-rp/bin/python parser/build_alldata.py \
    2> /tmp/wp1-unit25-logs/build.time.log \
    > /tmp/wp1-unit25-logs/build.out.log
' > /tmp/wp1-unit25-logs/kickoff.log 2>&1 &
disown
```

4. Confirm the process actually started (one liveness check, e.g. `pgrep -f
   osm_to_parcel_geometry.py`) and that `output/` is being written to. Do not wait on it, do not
   sleep-and-recheck in a loop, and do not use `Monitor` to sit on it. End your turn once you've
   confirmed it started.

Treat unit 15's own timings (33:23 extraction, 6:44 assembly, first run at ~9.7GB/8.19GB peak
RSS extraction / ~3.36GB assembly) as the floor for this run's expected duration, not a
guarantee — the post-19-24-fixes content mix differs (group 1 re-selects `natural=bay` instead of
`natural=dune` at levels 10/12; group 2 changes `divide.py`'s drop order) and has not itself been
timed at country scale. Say this in your report-back so unit 25b sizes its wait accordingly.

## Done evidence

- Disk-space numbers (before and after `rm -rf output/`) recorded in your report-back, with an
  explicit statement of whether they were judged adequate to proceed.
- `pgrep -f osm_to_parcel_geometry.py` (or equivalent) confirms the process is running.
- `/tmp/wp1-unit25-logs/kickoff.log` and the per-stage logs exist and are being appended to.
- `output/` did not exist (or was empty) immediately before the background run started.

## Report back

The disk-space numbers and your go/no-go judgment on them; the exact commands you ran; every log
path; the PID(s); unit 15's benchmark numbers above as context for expected duration; and an
explicit note that this rebuild's output is needed for **two** downstream purposes it does not
itself satisfy — unit 25b's `container` check (confirming group 1's fix at scale) and unit 26's
recalibration design input (a fresh `output/report.json`) — so unit 25b must produce a full
`compare_disc.py` report, not just a `--checks container` run. **Do not resolve any contradiction
you notice silently — report it.** If you find a non-trivial bug outside this unit's own
contract, report it (symptom, location, root cause if found) and leave it — do not fix it here.
