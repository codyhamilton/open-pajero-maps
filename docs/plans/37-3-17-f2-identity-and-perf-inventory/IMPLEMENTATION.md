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

### 2-01 landed (Execute; Codex usage-limited)

The Codex seat (11:23 AEST) hit the weekly Codex cap (reset 2026-10-10 11:50
AEST) before editing. Execute did the unit; see `reports/2-01-perf-inventory.md`.
Five modules are `orchestration`. `parser/tools/k1_representable.py` is
`c-later` and named as a plan 04 Phase 5 input. `test_perf_inventory.py`
passes 4/4. Plan 29 R4 and the contract carry now point here. The full
`parser/tests` run is the guarded plan 35 step, and its summary closes this
phase.

### 1-01 landed (Execute; Codex usage-limited) — Phase 1 closed

The Codex seat died at the weekly cap, so Execute did the unit; see
`reports/1-01-f2-identity.md`. The result is a **match**: the forced-zero set
is 34 rows (O05 30 shared; O04 1 shared + 3 added), and it reproduces 3-15 →
3-17 exactly (predicted O01 363 / O04 3 / O05 102 / NO_RULE 308). The erratum
is in `triage/per_rule_phase1_f2_identity.md`, and plan 28 F2 points there.
Tests: 7 passed (new synthetic test plus `test_perf_inventory`).
