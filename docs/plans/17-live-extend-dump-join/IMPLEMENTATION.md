# Implementation — 17 live extend → dump_join

- Tool: OpenCode DeepSeek Flash (assigned instance)
- Session: design landed; Phase 1 executing
- Started: 2026-10-06 ~00:07 Australia/Brisbane
- Base: detached HEAD `b211112` in worktree `open-pajero-maps-17`

## Phase 1 — Live extend is dump_join; plan-05 fixture SHA gates hold

Status: **done**.

- Wrapper path: gitignored `output/scratch-3-12/extend.py` is a thin wrapper that
  puts `parser/tools` on `sys.path`, imports `dump_join`, and
  `raise SystemExit(dump_join.main())` with no arguments — residual defaults
  (`DEFAULT_SRC` / `DEFAULT_SIDE` / `DEFAULT_ASSIGN` / `DEFAULT_DST` /
  `DEFAULT_COUNTS`), same pattern as plan 05's 3-07 wrapper. Durable CLI
  equivalent: `.venv-rp/bin/python parser/tools/dump_join.py` (mode `residual`,
  defaults). No change to `dump_join` or the vendored baseline.
- Gates (all pass):
  - `(cd parser/tests/fixtures/dump_join_baseline && sha256sum -c SHA256SUMS)` →
    `extend.py` / `study.py` / `witness.py` all OK; vendored `extend.py` stays
    `1b13b844…`.
  - `pytest parser/tests/test_dump_join_memory.py
    parser/tests/test_extend_s02_memory.py parser/tests/test_k1_triage.py
    parser/tests/test_perf_inventory.py -q` → **48 passed**.
  - AST parse of the wrapper + `dump_join.DEFAULT_SRC` / `DEFAULT_DST` →
    `output/scratch-3-11/dump_new_ext` / `output/scratch-3-12/dump_ext`.
- Docs: plan 05 opening summary / deviation / residual-risk / follow-up updated
  to record the switch; `docs/provenance.md` scratch-3-12 Dump extension now
  names the wrapper + tracked CLI and keeps the frozen fixture baseline for
  replay; this ledger and `reports/phase-1.md`.
- Deviation (Assumption 3): the `output/scratch-3-12/` tree was absent on this
  Execute host, so only the minimal gitignored path for the wrapper file was
  created. No dumps, side tables, or classify outputs were regenerated.
- Commit: `Workflow-Phase: 17-live-extend-dump-join:1`; full 40-hex SHA recorded
  in the gitignored `output/CHM-17-p1-EXIT_DONE` marker after landing.
