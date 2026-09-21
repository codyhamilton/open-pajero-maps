# Brief: 1-07 — Kick off a timed full-Australia extraction (dry run of extraction wall time)

Consumer: implementation worker; a fresh worker (1-09) reads the result. This unit only starts the run and hands off; it does not wait for it.
Owned paths: `output/extract_timing/` (new, git-ignored scratch; not committed). No source files. Touch nothing else.
Commits: Leave changes in the working tree. Nothing to commit.
Depends on: nothing.
Runs alongside: all Phase 1 units (it is CPU-heavy: warn the orchestrator that timing is only meaningful if nothing else heavy runs; report the load average at kickoff).
Budget: 3 files to read, no code, 15 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md`, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Assumption "Country-scale re-extraction is affordable"; Open Questions, third bullet.
2. `parser/osm_to_parcel_geometry.py` — `main()` argparse (~line 990): `--pbf`, `--levels`, `--spool`, `--dry-run`.
3. `docs/provenance.md` — the OSM extract entry (which `australia-*.osm.pbf` is present).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Measure country-scale extraction wall time without disturbing `output/spool` (which the current G was built from and Phase 3 reuses).

## Contract

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Extraction writes only to a scratch spool at `output/extract_timing/spool`, never to `output/spool`. Cited: "Extraction wall time at country scale (undocumented)... Phase 1 measures extraction wall time."

## Changes

- Start, detached in the background: `/usr/bin/time -v .venv-rp/bin/python parser/osm_to_parcel_geometry.py --pbf australia-260824.osm.pbf --spool output/extract_timing/spool > output/extract_timing/run.log 2>&1` (all default levels; adjust flags only if argparse differs, and say so). Record the start timestamp, PID, host core count and load average in `output/extract_timing/START.txt`.
- Confirm within a couple of minutes that it is running and not erroring, then stop. Do not poll to completion.
- Confirm `output/extract_timing/` is covered by `.gitignore` (`output/` rule); if not, do not edit `.gitignore`: report it.

### Keep untouched

`output/spool`, `output/ALLDATA.KWI`, `output/manifest.json`.

## Done evidence

- `ls output/extract_timing/` shows `START.txt` and a growing `run.log`; `ps -p <PID>` shows the process alive; `git status --short` shows no tracked change.
- Report back the exact command, PID, start time, and the path 1-09 must read (`run.log` final `Elapsed (wall clock)` line).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
