# Brief: existing triage key determinism

Consumer: K1 triage users and the plan 09 baseline-failure record.
Owned paths: `parser/tools/k1_triage.py`, `parser/tests/test_k1_triage.py`,
`docs/design/k1-triage.md`, `docs/ARCHITECTURE.md`,
`docs/plans/09-malformed-rules-json.md`, `docs/OVERVIEW.md`, this plan's
execution records and report.
Depends on: current master `7c4b78f`; no blocked verification dependency.
Runs alongside: nothing. One worker only, direct implementation.

## Goal and contract

Resolve the three baseline summary determinism failures recorded by plan 09
and commit `07c3918`. Cite DESIGN's internal aggregation contract: grouping
identity includes only declared fields, stays invariant through NumPy copies
and window changes, and retains independently owned storage.

## Work

Read the internal key builders and every consumer. Establish the baseline
with the three existing repeat/window/high-cardinality tests. Add a bounded
regression that makes copy padding adversarial while checking logical groups
and per-source row/group counts against a field-value reference. Change only
internal grouping representation; preserve aligned dump rows, key field order,
NaN handling, sorting, assignments, rule behavior and bounded windows.
Record the resolved limitation in the stable contract and plan 09.

## Verification

Use an existing Python environment read-only. Run the bounded tests:

```
python -m pytest parser/tests/test_k1_triage.py -q
python -m pytest parser/tests/test_dump_join_memory.py parser/tests/test_extend_s02_memory.py parser/tests/test_perf_inventory.py -q
git diff --check
```

No full-disc build, real dump scan, memory benchmark or 3-90 rerun. No
scratch/disc/spool/.venv-rp deletion or change. Report what the tests prove
without extending the claim to Phase 3 closure or memory budgets.

## Handoff

Write `reports/1-01-existing-key-determinism.md` before committing; include
observed failures and passing results, deviations, limitations and remaining
blocked repo work. Record the outcome and result commit in IMPLEMENTATION.
Perform an explicit self-review; do not invent an independent reviewer or
service identity. Commit and push to master without a PR; leave result SHAs
in the external unit log.
