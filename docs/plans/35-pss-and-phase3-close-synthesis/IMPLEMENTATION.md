# Implementation — 35 PSS at ≤ -j6 and plan 04 Phase 3 close synthesis

- Tool: the orchestrator is the Execute background worker. Phase 1 is an
  ops measurement run by Execute under the guard; it has no code unit.
  Phase 2 synthesis uses a Codex seat (if Codex is limited, Execute writes
  it and discloses that) and an independent clean-context review.
- DESIGN landed at `e2a2c71`. Disc in force: `4e6b0de7…`. Perth:
  `04be2f6e…`. Any sha mismatch stops the chain and is reported, never
  re-pinned.
- Scratch: `output/scratch-35/`. Protected inputs: `2ee3456a…`,
  `4ed9cd80…`, `013586b5…`, `4e6b0de7…`, R `8c2d2027…` and the spool, all
  hashed before and after by the plan-34 `snapshot` gate.
- No brief 3-90 execution and no "3-90" record. `-j` never exceeds 6. The
  ceiling of 9,726,501 kB stays as signed.

## Phase 1 — Ops and build gates measured on 4e6b0de7

Commands: `commands.md`. The chain `output/scratch-35/run_p1.sh` (log
`run_p1.log`) runs serially, each step under `run_heavy_python.py` and
`output/.heavy.lock`. The full `parser/tests` run is a separate guarded step
after plan 37 Phase 2 (`test_perf_inventory`) lands.
