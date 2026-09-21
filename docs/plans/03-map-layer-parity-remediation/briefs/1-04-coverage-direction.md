# Brief: 1-04 — Coverage direction for mfde and vocab checks

Consumer: implementation worker; result consumed by 1-09 (expectation run) and Phases 6-9.
Owned paths: `parser/harness/checks/mfde.py`, `parser/harness/checks/vocab.py`, `parser/tests/test_harness_mfde.py`, `parser/tests/test_vocab_coverage.py` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 1-03 (reads `bands.coverage` from `harness.json`).
Runs alongside: 1-05, 1-06, 1-07, 1-08.
Budget: 6 files to read, about 200 lines to change, 35 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Verification Contract, "`mfde`/`vocab` gain a coverage direction (G must use a stated share of R's values by R frequency)".
2. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F12 first row.
3. `parser/harness/checks/mfde.py`, `parser/harness/checks/vocab.py` — current subset logic.
4. `parser/refdata/harness.json` — `bands.coverage` (do not edit).
5. `parser/tests/test_harness_mfde.py`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

The two checks fail when G is poorer than R, not only when G uses values R lacks.

## Contract

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Cited coverage rule: per level and per index/vocabulary, the R-frequency-weighted share of R's values that G also uses must be >= `bands.coverage` (from `harness.json`). Keep the existing subset direction. A vocabulary where R has fewer than a minimum number of observations (state the constant, put it in the check, report it) is reported as advisory, not FAIL. The details dict lists, per level, the top missing R values by frequency.

## Changes

- Compute weights from the R profile already loaded by `ctx.profile`; add whatever counts to the profile only if absent, in which case stop and report `needs context` (profile regeneration is not owned here).
- Coverage FAIL must not mask the existing subset messages.

### Keep untouched

Existing check ids, subset semantics, `nregion`/WP2 slot handling in mfde.

## Done evidence

Write the failing unit tests first (synthetic profiles: G subset-but-poor must FAIL; G covering must PASS; low-count vocab is advisory).

- `.venv-rp/bin/python -m pytest parser/tests/test_harness_mfde.py parser/tests/test_vocab_coverage.py -q` → passes.
- `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --checks mfde,vocab --no-manifest --report /tmp/cov.json` (if 1-01 has landed; otherwise call the checks through a small script) → prints the result; paste the coverage numbers per level into the report. FAIL here is expected and is data for 1-09; do not tune to make it pass.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
