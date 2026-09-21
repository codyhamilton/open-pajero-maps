# Brief: 1-09 — Run the strengthened harness on current G; record expectation list and extraction time

Consumer: verification worker (fresh); its output is the Phase 1 outcome record read by `execute` and Phase 2+ workers.
Owned paths: `docs/plans/03-map-layer-parity-remediation/EXPECTATIONS.md` (new), `docs/provenance.md` (only the compare-report entry and an entry for `output/extract_timing/`). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 1-01, 1-03, 1-04, 1-05, 1-06, 1-07 (the extraction must have finished), 1-08.
Runs alongside: nothing.
Budget: 6 files to read, about 150 lines to change, 25 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md`, commit, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Phase 1 Outcome (both sentences) and "Phase 1 succeeds when every FAIL ... is on the recorded expectation list".
2. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F12 and the sections F-items each check maps to.
3. `output/extract_timing/START.txt`, and the tail of `output/extract_timing/run.log`.
4. `docs/provenance.md` — compare-report entry (~line 190).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Run the full strengthened harness on the current G, and record which FAILs and advisories appear, each mapped to the F-finding that predicts it, plus the measured extraction time.

## Contract

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. The expectation list is written from the DESIGN's predicted differences: G-only BMT tables, non-monotonic BMT DSAs, poorer-than-R vocabulary coverage, Grenfell row. Every FAIL not predicted is reported as **unexpected** and, per the design, the phase does not close on it: report it, do not add it to the expectation list to make it pass. Do not modify any check or config.

## Changes

- Command: `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report output/compare_report.json`. If it refuses because `output/manifest.json` does not match `output/ALLDATA.KWI`, that is a finding: record both hashes, rebuild is out of scope, rerun with `--no-manifest` for the check output and say the report is unbound.
- `EXPECTATIONS.md`: table of (check, status, message, predicting finding or "unexpected"), the report's `generated_sha256`, bands review status (from `harness.json` `bands.review`), and the extraction wall time (Elapsed line, core count, load at kickoff, caveat if other units ran concurrently). Wall time is also the answer to DESIGN Open Question 3; state it there in your report for the orchestrator to move.
- Provenance: add the extraction-timing scratch directory and note the updated report binding.

### Keep untouched

`DESIGN.md` (the orchestrator owns it).

## Done evidence

- `output/compare_report.json` exists and its `generated_sha256` matches `sha256sum output/ALLDATA.KWI`.
- `EXPECTATIONS.md` has a row for every check the run produced; `grep -c unexpected` count reported.
- Refusal case demonstrated: `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated <a different ALLDATA.KWI or a temp copy with one byte changed> --checks decode` exits 2 and names the hash mismatch.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
