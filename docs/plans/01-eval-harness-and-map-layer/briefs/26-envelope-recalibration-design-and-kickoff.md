# Brief: 26 — Envelope admission-rate recalibration: design, implement, kick off rebuild #3

Consumer: implementation worker. This unit deliberately bundles a design decision and a code
change with a rebuild kickoff — a justified deviation from the kickoff/wait-split shape units
15/25 and 03/03b use (see "Why this unit's shape is different" below). Do not treat this as a
gap to silently split further; the plan already considered and accepted the bundling. It does
**not** license skipping the kickoff/wait split at the *rebuild* boundary — the rebuild itself
still hands off to a fresh unit (26b), exactly like 25/25b.
Owned paths: `parser/refdata/selection.json`, `parser/kiwiw/divide.py` (whichever of these, or
both, your chosen calibration lever touches — see Changes). Do not touch
`parser/harness/checks/envelope.py` or any other harness file: the harness's tolerance is the
thing this recalibration is judged against, and loosening it from inside the unit it judges would
be self-certification, not a fix.
Do not commit. Leave the code change and this brief's report in the working tree for unit 26b to
verify and commit as one unit — the same wait-split commit convention units 03/03b and 15/15b use
(the design's correctness is only proven once 26b's rebuild passes the harness; committing before
that is proven would mean landing an unverified calibration change).
Depends on: 25b (must have produced `output/report.json` with fresh per-level
`parcel_count`/`name_count` data).
Runs alongside: nothing.

## Why this unit's shape is different (read before objecting to it)

`PLAN.md`'s "Deliberate deviation from the 15/25 kickoff shape" paragraph explains this
explicitly: unit 26 bundles a real design decision with its own rebuild kickoff, rather than
splitting the design into its own separate unit ahead of a pure kickoff. This is accepted because
(a) the design step is expected to be small and fast relative to the rebuild it triggers, and (b)
brief 20 already narrows the decision space to a short, enumerated set of options. **If you find
the design step is not in fact small** (e.g. it turns out to need new plumbing — decoupling
`divide.py`'s split threshold from raw content volume, or a way to admit a road/background
class's geometry without also emitting its name record) — **stop before implementing a large
change**, report exactly what you found and why it's larger than the plan expected, and recommend
splitting a design-only unit ahead of a fresh kickoff. That is the escape valve `PLAN.md` itself
names, not a plan violation.

## Required reading, in order

1. Unit 25b's report-back and `output/report.json` — the fresh per-level `parcel_count`/
   `name_count` generated/reference/ratio values. This is the binding input for your design; a
   `selection.json`/`divide.py` change based on the stale 2026-09-09 numbers instead is exactly
   what brief 20 called "a guess, not a calibration."
2. `docs/plans/01-eval-harness-and-map-layer/briefs/20-envelope-selection-calibration.md` — in
   full, especially "Open questions for the next worker to resolve" (the enumerated decision
   space this unit chooses from) and the "Amendment" section (the undershoot-vs-overshoot
   direction correction, and briefs 22/24's related fixes already landed).
3. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — the Acceptance Criteria bullet marked
   `(units 26/26b)`, the "Deliberate deviation..." paragraph, and the "Disk space, carried
   forward..." paragraph (this unit runs its own rebuild and must handle disk space explicitly,
   same as unit 25).
4. `parser/refdata/selection.json` — current per-level rules and `_calibration_note` fields,
   especially levels 0, 2, 4, 6, 8.
5. `parser/kiwiw/divide.py` — `divide_oversize_parcels`, `_retile_content`, and `_shrink_to_fit`
   (already amended by brief 22 to drop roads before names/backgrounds) — for how `parcel_count`
   is actually produced and where a threshold-logic lever would live if selection alone isn't
   enough.
6. `parser/harness/checks/envelope.py` — read only, to see exactly what is compared
   (`_COUNT_FIELDS`, the `[0.5, 2.0]x` ratio, the per-level union-of-levels iteration). Do not
   edit this file.

## Goal

From 25b's real per-level numbers, decide and implement the calibration change that brings
`parcel_count`/`name_count` at levels 0/2/4/6/8 into `[0.5, 2.0]x` of the reference — or narrows
the gap with the remainder explicitly named, per brief 20's own escape hatch — then check/free
disk space and kick off a third full-Australia rebuild for unit 26b to verify at scale.

## Contract

`PLAN.md`'s Acceptance Criteria bullet marked `(units 26/26b)`, verbatim: every level's
`parcel_count`/`name_count` ratio inside `[0.5, 2.0]x`, or the report names which level(s) remain
out of range and why — a residual gap is reported, not silently dropped. The harness's tolerance
(`envelope.py`'s `[0.5, 2.0]x` constant and its per-level union-of-levels iteration) is settled
and not open for you to change.

## Changes

1. From 25b's fresh numbers, determine per level (0, 2, 4, 6, 8) whether `parcel_count` and
   `name_count` are over or under `[0.5, 2.0]x`, and by how much. Brief 20's "Amendment" section
   already found the 2026-09-09 direction was undershoot (fewer parcels/names than R), not the
   overshoot brief 20's original hypothesis assumed — confirm whether that still holds with
   25b's fresh, post-fix numbers, since briefs 19/20/22/24's fixes may have shifted it.
2. Choose a lever per brief 20's enumerated options: (a) loosen/trim `selection.json` admission
   per level, (b) change `divide.py`'s split-threshold logic (if `parcel_count` is genuinely
   structural, not admission-driven), or (c) some combination. Do not choose "redefine the
   envelope check's tolerance" — that is the harness's contract, out of this unit's owned paths
   and explicitly forbidden above.
3. Implement the chosen change(s) in `selection.json` and/or `divide.py`.
4. Fast, in-repo verification before committing to a full rebuild: `.venv-rp/bin/python -m
   pytest parser/tests -q`, and a `--fixture perth --levels <affected levels>` local build to
   sanity-check the change doesn't break the byte-identical replicate path or crash outright
   (this is not a substitute for the full rebuild — it is a cheap gate before spending 30-40
   minutes on one).
5. **Before clearing `output/`:** the numbers you need from 25b's `output/report.json` are
   already in your report so far (step 1) — confirm you have quoted every number you'll want to
   compare against post-rebuild, since the next step deletes the file. If in doubt, copy
   `output/report.json` to a location outside the repo tree (e.g. `/tmp/wp1-unit26-prior-
   report.json`) before proceeding, so you (or unit 26b) can diff before/after.
6. Disk-space check, same as unit 25's step 1: `df -h /home`, `du -sh output/`, confirm
   post-`rm -rf output/` free space is comfortably above the ~6.9GB real spool footprint plus
   the ~814MB built `ALLDATA.KWI` plus a safety margin. Stop and report if not adequate — do not
   proceed blindly.
7. `rm -rf output/`.
8. Start the extraction + assembler pipeline in the background, following units 15/25's exact
   pattern:

```
mkdir -p /tmp/wp1-unit26-logs
nohup bash -c '
  /usr/bin/time -v .venv-rp/bin/python parser/osm_to_parcel_geometry.py \
    2> /tmp/wp1-unit26-logs/extract.time.log \
    > /tmp/wp1-unit26-logs/extract.out.log &&
  /usr/bin/time -v .venv-rp/bin/python parser/build_alldata.py \
    2> /tmp/wp1-unit26-logs/build.time.log \
    > /tmp/wp1-unit26-logs/build.out.log
' > /tmp/wp1-unit26-logs/kickoff.log 2>&1 &
disown
```

9. Confirm the process started (one liveness check). Do not wait on it, do not poll in a loop.
   End your turn once confirmed.

### Keep untouched

Everything in `selection.json`/`divide.py` not touched by your chosen lever — do not use this as
an opportunity to tidy unrelated calibration notes or thresholds.

## Done evidence

- `selection.json`/`divide.py` diff (uncommitted, in the working tree) shows the chosen
  calibration change, with its rationale tied to 25b's actual numbers (not the stale 2026-09-09
  ones).
- `pytest parser/tests -q` passes.
- The local fixture sanity build (step 4) completes without crashing.
- Disk-space numbers recorded, with an explicit go/no-go judgment.
- `pgrep -f osm_to_parcel_geometry.py` confirms the background process is running; logs exist at
  `/tmp/wp1-unit26-logs/`.
- 25b's `output/report.json` numbers are either already fully quoted in a report or preserved
  outside the repo tree before `output/` was cleared.

## Report back

Which lever(s) you chose and why, tied explicitly to 25b's numbers; whether the undershoot
direction still held; the disk-space numbers and judgment; the exact commands, log paths and
PIDs for unit 26b to pick up; whether the design step turned out small as the plan expected or
should have been split into its own unit (an explicit judgment call the plan defers to you); and
any contradiction you found between this brief, brief 20, and the contracts they cite. **Do not
resolve contradictions silently — report them.** If you find a non-trivial bug outside this
unit's own contract, report it (symptom, location, root cause if found) and leave it — do not fix
it here.
