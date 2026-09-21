# Brief: 1-01 — Bind compare report to the evaluated ALLDATA.KWI

Consumer: implementation worker (Python, harness).
Owned paths: `parser/compare_disc.py`, `parser/harness/report.py`, `parser/tests/test_harness_core.py`. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing.
Runs alongside: 1-02, 1-05, 1-06, 1-07, 1-08.
Budget: 5 files to read, about 120 lines to change, 25 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Domain: Verification and deviation ledger", first Contract bullet; Phase 1 Outcome.
2. `parser/compare_disc.py` — `main()`; `parser/harness/report.py` — `write_report`.
3. `parser/tests/test_harness_core.py` — existing style.
4. `output/manifest.json` — keys `sha256`, `total_size` (top level; ignore `levels`).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

A compare report can no longer be mistaken for a different build: it records the sha256 and mtime of the `ALLDATA.KWI` it evaluated, and the tool refuses to compare when that file is not the build `output/manifest.json` describes. Consumer of the result: every later phase's verification and unit 1-09.

## Contract

Cited: "`compare_disc.py` report carries the sha256 and mtime of the `ALLDATA.KWI` it evaluated and refuses to compare when they differ from `output/manifest.json`."

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`.

## Changes

- Compute sha256 (streamed, chunked) and mtime of the generated `ALLDATA.KWI`; add `generated_sha256`, `generated_mtime` (ISO 8601 UTC) and the manifest path used to the report JSON.
- Manifest location: `<parent dir of the generated ALLDATA.KWI>/manifest.json`, overridable with a new `--manifest` option. Compare its `sha256` with the computed one. On mismatch: print which two hashes differ and why (stale report / different build), write no report, exit code 2, run no check. Missing manifest is also a refusal unless `--no-manifest` is passed; when passed, the report records `"manifest_bound": false`.
- `--profile` mode is unaffected.
- Stale-report guard is only for the generated side; do not hash R.

### Keep untouched

Check discovery/selection, the results table, the exit-code rule for check FAIL (1), and the `--profile` path.

## Done evidence

Identify or write the failing tests first (in `test_harness_core.py`, using tiny synthetic files, no real disc). Report output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_harness_core.py -q` → passes, with tests for: match writes report containing both fields; mismatch exits 2 and writes no report; missing manifest refused; `--no-manifest` records `manifest_bound: false`.
- Observable: `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --checks decode --report /tmp/x.json` either writes a report whose `generated_sha256` equals `output/manifest.json`'s `sha256`, or refuses naming both hashes. Report which, and both hashes (the manifest may point at a stale build; that outcome is data for 1-09, do not repair it).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
