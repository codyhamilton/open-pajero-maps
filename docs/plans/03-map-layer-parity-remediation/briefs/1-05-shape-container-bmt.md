# Brief: 1-05 — BMT comparison by key, DSA ordering, and table-presence in shape/container

Consumer: implementation worker; result consumed by 1-09 and Phases 3, 6, 10.
Owned paths: `parser/harness/checks/shape.py`, `parser/harness/checks/container.py`, `parser/tests/test_harness_container.py`, `parser/tests/test_harness_shape.py` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing.
Runs alongside: 1-01, 1-02, 1-03, 1-04, 1-06, 1-07, 1-08.
Budget: 6 files to read, about 250 lines to change, 40 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F12 rows 2-4 (shape/BMT presence, container PDMDH, DSA monotonicity).
2. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Verification Contract: "`shape` and `container` compare BMT tables by (level, blockset) key and check DSA ordering".
3. `parser/harness/checks/shape.py`, `parser/harness/checks/container.py`.
4. `docs/schema/parcel-management.md` — BMT / DSA layout rows.
5. `parser/tests/test_harness_container.py`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

The two checks stop passing when G's BMT differs from R's in presence, keying or ordering.

## Contract

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Cited: BMT tables are compared by (level, blockset) key, not position; G-only tables are FAIL unless in a declared edge set (there is none yet: list them in details, do not add an allowlist); shared tables are verified entry-for-entry; BMT DSAs must be monotonic within the layout order R uses (establish R's ordering rule from R first and state it in a code comment; whether the head unit requires it is unknown, so report it as FAIL with that caveat in the message). PDMDH length is not compared by length alone.

## Changes

- Failures name the key. Known expected FAILs on current G (do not suppress): 178 vs 165 BMT tables, non-monotonic DSAs.

### Keep untouched

`container_allowlist` semantics in `harness.json` (do not edit that file), the `mht29` check.

## Done evidence

Failing tests first (synthetic BMT tables: extra table, reordered table, non-monotonic DSA).

- `.venv-rp/bin/python -m pytest parser/tests/test_harness_container.py parser/tests/test_harness_shape.py -q` → passes.
- Run `shape` and `container` against R and current G (`--no-manifest` if 1-01 has not landed) → G-only tables listed (expect 13 extra), DSA-ordering violation reported. Paste counts. Also run R against R → PASS.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
