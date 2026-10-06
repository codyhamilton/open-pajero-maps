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

### Phase 2 closed — full parser/tests

The full suite ran as the guarded plan 35 step, collected at `0f3e530`, which
includes unit 2-01. Wrapper log: `output/scratch-35/runs/p1_pytest.json`
(exit 1, 700.3 s, memory.peak 10,110,922,752 B). Output:
`output/scratch-35/pytest.log`.

> `FAILED parser/tests/test_parcel_mask.py::test_fill_only_masked_and_absent_cells`
> `1 failed, 1365 passed, 7 skipped in 698.31s (0:11:38)`

- `test_perf_inventory.py` passes. It was 1 failed / 3 passed at `d2459b6`.
- The one failure is **not new in plan 37**. Bisected at 11:50 AEST in
  throwaway detached worktrees, running only this file: at `5182c83^` it gives
  4 passed; at `5182c83` (plan 34 unit 2-02, the outside-mask empty-shell
  omission) it gives 1 failed / 3 passed.
- Cause: the synthetic spooled cell (720, 30) carries only out-of-span names.
  Its frame is an exact empty shell (`is_empty_shell` True), and it lies outside
  the synthetic mask, so plan 34's rule omits it. The test predates that rule
  and still expects the frame.
- This is a plan 34 regression in the test suite, missed by plan 34's
  restricted suite and its review. It is carried to plan 35 G7 as a named
  residual, with plan 34 follow-up as owner. Plan 37 does not edit it: the test
  is outside plan 37's owned paths, and DESIGN forbids "changing the test" only
  for `test_perf_inventory`, but the fix belongs to the plan that changed the
  behaviour.
- Plan 37's own tests: `test_per_rule_f2_identity.py` (3) and
  `test_perf_inventory.py` (4) → 7 passed. `test_per_rule_f2_identity.py` was
  added after collection, so it was run separately.
