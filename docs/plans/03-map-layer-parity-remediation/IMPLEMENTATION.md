# Implementation — 03-map-layer-parity-remediation

- Tool: Claude Code (Agent SDK), model Sonnet 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-21T19:17:25+10:00
- Scope: Phase 1 only

## Phase 1

Status: refine dispatched (no Units list in DESIGN.md).

### 1-05 shape-container-bmt — done (3b9e899, Sonnet)
Built: `bmt_key_diffs`/`bmt_keys`/`bmt_dsa_order_violations` in shape.py; `shape` compares G to grid.json key set; `container` adds `pdmdh.bmt_table` violations. Surfaces: harness/checks/{shape,container}.py, tests/test_harness_shape.py. Evidence: 12 tests pass; R vs R PASS; R vs G: shape FAIL 19 diffs (13 G-only tables, 6 cross-table DSA-order violations). Deviations: tests not written first; "entry-for-entry" = count + empty/non-empty pattern.
