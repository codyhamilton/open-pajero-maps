# Report 1-01 — F2 per-row identity

Seat: **Execute (Grok Bot), not Codex.** The Codex seat launched at 11:23 AEST
died at the weekly Codex usage limit before editing anything (reset 2026-10-10
11:50 AEST; `output/scratch-37/p1p2.codex.log`). Execute did the unit from the
brief.

- Script: `docs/plans/04-c-core-orchestration/triage/per_rule_phase1_f2_identity.py`.
  It joins committed tables and makes one streamed read of the plan 31 cell
  list. There was no dump, classify or K1 run.
- Outputs: `per_rule_phase1_f2_identity.{tsv,json,md}` in the same triage directory.
- Counts: forced zero **34 = O05 30 (shared 30) + O04 4 (shared 1, added 3)**.
  3-15 measured O01 363 / O04 7 / O05 132 / O06 0 / NO_RULE 274 → predicted
  3-17 363 / 3 / 102 / 0 / 308, which equals the 3-17 yardstick. `match: true`.
- The 31 statement omitted the 3 added O04 rows (dump_rows 138, 282, 563). The
  erratum is in the `.md`.
- Tests (11:52 AEST): `parser/tests/test_per_rule_f2_identity.py` (3 synthetic)
  plus `test_perf_inventory.py` → 7 passed.
- Proposed plan 28 pointer, applied by Execute: "**Discharged by plan 37 Phase
  1:** the 34 rows are O05 30 + O04 4 (shared 31, added 3), proven by
  `triage/per_rule_phase1_f2_identity.md`. The 31 statement omitted the 3
  added O04 rows."
