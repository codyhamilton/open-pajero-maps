# Brief: 1-06 — Pointer targets must decode; whole-word spotcheck; Grenfell row

Consumer: implementation worker; result consumed by 1-09 and Phase 9.
Owned paths: `parser/harness/checks/decode.py`, `parser/harness/checks/spotcheck.py`, `parser/refdata/spot_checks.json`, `parser/tests/test_harness_spotcheck.py`, `parser/tests/test_harness_pointers.py` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing.
Runs alongside: 1-01, 1-02, 1-03, 1-04, 1-05, 1-07, 1-08.
Budget: 7 files to read, about 220 lines to change, 40 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F12 rows for `pointers` and `spotcheck`; grep "Grenfell" for the cell and lat/lon.
2. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Verification Contract: "`pointers` requires targets to decode as Map Frames; `spotcheck` uses whole-word equality and gains a Grenfell-in-northern-cell row".
3. `parser/harness/checks/decode.py` — `_run_pointers`, `_check_mfde_entry`.
4. `parser/harness/checks/spotcheck.py` — `_missing`.
5. `parser/refdata/spot_checks.json`, `parser/tests/test_harness_spotcheck.py`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

`pointers` no longer passes any in-file index >= 3; `spotcheck` no longer accepts substring hits ("Pulteney" must not match "Pulteney Pokies"), and a Grenfell row in the northern cell exists.

## Contract

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Cited: as in Required reading 2. A pointer target passes only if the bytes at the target decode as a Map Frame through the existing decoder (import path per the harness reading-paths-only constraint in `parser/harness/__init__.py`). Matching is whole-word, case-folded, on the normalised name (state the normalisation). Grenfell coordinates and expected road name come from FINDINGS; if FINDINGS lacks lat/lon, derive from R (find the cell in R by name) and cite how.

## Changes

- Adding the Grenfell row: do not tune it to pass. Expect FAIL on current G if the cell is absent.
- Keep decode's `_poison_run_found` and covered-range logic.

### Keep untouched

The `decode` check body, existing 14 spot rows (their expectations may not be loosened).

## Done evidence

Failing tests first (substring false positive; pointer into non-frame bytes).

- `.venv-rp/bin/python -m pytest parser/tests/test_harness_spotcheck.py parser/tests/test_harness_pointers.py -q` → passes.
- Run `pointers,spotcheck` on current G (`--no-manifest` if 1-01 has not landed) and on R vs R (R vs R must PASS spotcheck, apart from any row R itself cannot satisfy, which you report). Paste output; Grenfell FAIL and any newly surfaced pointer or substring failures are expected data for 1-09.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
