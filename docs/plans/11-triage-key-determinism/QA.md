# Bounded synthetic verification

Interpreter: existing prior-seat `.venv-rp/bin/python`, read-only, Python
3.14 environment. No disc or spool is needed by these tests.

- Baseline repeat/window/high-cardinality selection: 3 assertion failures
  reproduced, after moving generated test inputs off quota-limited `/tmp`.
- Added adversarial copy-padding regression before fix: 3 failures.
- Entire triage test file after fix: 25 passed in 4.51 s, no skips.
- Dump-join, S02-extension and performance-inventory files: 23 passed in
  6.89 s, no skips.
- Strengthened shared-source/classify/enumerate regression: 3 passed in
  0.42 s. No other test or source changed after the full focused runs.
- `git diff --check`: pass.

Commands used the repository-relative test paths in the brief and unique
`--basetemp=/dev/shm/maps-key-*-20261005` directories. The fixtures are small
temporary synthetic data. Original project paths were not altered or deleted.
No blocked verification, full-disc build or memory benchmark was rerun.
