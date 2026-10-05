# Phase 1 report — live extend is dump_join

Implemented against detached HEAD `b211112` in worktree
`open-pajero-maps-17`. No disc, full-AU encode, or plan 14 completeness dumps
were used. Tool: OpenCode DeepSeek Flash. Work stayed inside this worktree.

## Outcome

The live, gitignored residual entry `output/scratch-3-12/extend.py` is now a
thin wrapper over the tracked `parser/tools/dump_join.py` adapter. It puts
`parser/tools` on `sys.path`, imports `dump_join`, and calls
`dump_join.main()` with no arguments, so it runs the residual defaults
(`DEFAULT_SRC` `output/scratch-3-11/dump_new_ext`, side dir
`output/scratch-3-12`, assign dir `output/scratch-3-11/classify_new`,
`DEFAULT_DST` `output/scratch-3-12/dump_ext`, counts
`output/scratch-3-12/joined_counts.json`). This mirrors plan 05's 3-07
thin-wrapper precedent. The durable CLI equivalent is
`.venv-rp/bin/python parser/tools/dump_join.py` (mode `residual`, defaults).

Semantics are unchanged: the windowed adapter populates
`residual_crossing_verified` (u8) at byte146 (previously padding), checks every
other byte against the input, keeps row size 152, exact full-key join of
status1 default0. The vendored whole-file oracle
`parser/tests/fixtures/dump_join_baseline/extend.py` stays frozen (SHA
`1b13b844…`) and was not touched.

## Gates (all pass)

- `(cd parser/tests/fixtures/dump_join_baseline && sha256sum -c SHA256SUMS)` →
  `extend.py: OK`, `study.py: OK`, `witness.py: OK`.
- `.venv-rp/bin/python -B -m pytest parser/tests/test_dump_join_memory.py
  parser/tests/test_extend_s02_memory.py parser/tests/test_k1_triage.py
  parser/tests/test_perf_inventory.py -q` → **48 passed** in 14.19s.
- AST parse of the wrapper succeeded; `dump_join.DEFAULT_SRC` /
  `dump_join.DEFAULT_DST` printed
  `output/scratch-3-11/dump_new_ext output/scratch-3-12/dump_ext`.

No full-AU encode, no disc rebuild, no completeness dumps.

## Docs

- `docs/plans/05-heavy-job-memory.md`: opening summary records the plan-17
  switch; the scratch-3-12 deviation is marked as landed in plan 17; the
  residual-risk bullet now scopes the whole-file risk to re-running the frozen
  fixture baseline outside the isolated harness; the follow-up bullet is closed.
- `docs/provenance.md`: the scratch-3-12 **Dump extension** bullet now names the
  live thin wrapper and the durable `dump_join.py` CLI, states semantics are
  unchanged (byte146 / other bytes / row 152), and notes the vendored whole-file
  baseline is kept in fixtures for replay.
- `docs/WORKFLOW.md` was checked; it does not name the live whole-file extend as
  an open risk, so no one-liner was needed.

## Deviation

Assumption 3 held: `output/scratch-3-12/` was absent on this Execute host, so
only the minimal gitignored path needed for the wrapper file was created. No
dumps, side tables, or classify outputs were regenerated; the fixture SHA and
pytest gates are the semantic proof.

Plan 04 Phase 3 was not closed; 170 / 3-16 / 3-17 were not reseated. Nothing
was pushed and no PR was opened. The phase commit carries
`Workflow-Phase: 17-live-extend-dump-join:1`; its full 40-hex SHA is recorded in
the gitignored `output/CHM-17-p1-EXIT_DONE` marker.
