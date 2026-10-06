# Implementation — 37 3-17 F2 identity and perf inventory

- Tool: the orchestrator is the Execute background worker. Unit workers are
  Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`. Execute commits.
  If Codex is usage-limited, Execute does the unit and says so here.
- DESIGN landed at `517781e`. Both phases are light. There is no disc,
  encoder or checker surface, and no heavy run.
- Scratch: `output/scratch-37/`.
- Phase 2 must land before plan 35 Phase 1's full-pytest gate.

## Phase 1 — F2 34-row identity proven or residual named

Refine skipped. Unit: `briefs/1-01-f2-identity.md`.

## Phase 2 — test_perf_inventory passes

Refine skipped. Unit: `briefs/2-01-perf-inventory.md`.
