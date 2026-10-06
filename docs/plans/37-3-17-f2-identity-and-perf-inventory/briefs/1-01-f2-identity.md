# Brief: 1-01 — F2 per-row identity (3-15 → 3-17: O05 −30, O04 −4, NO_RULE +34)

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.

Owned paths:
- `docs/plans/04-c-core-orchestration/triage/per_rule_phase1_f2_identity.py`, `.tsv` and `.md` (new);
- `parser/tests/test_per_rule_f2_identity.py` (new, synthetic);
- `docs/plans/37-3-17-f2-identity-and-perf-inventory/reports/1-01-f2-identity.md` (new).

Commits: none.

## Outcome (DESIGN Phase 1)

1. **Pin every input by sha256:**
   - `docs/plans/04-c-core-orchestration/triage/per_rule_classify_assignment.tsv`
     (776 rows, native key plus rule);
   - the committed 3-15 shared-687 / added-89 key partition used by plan
     28's controls. Find the exact committed source from
     `per_rule_phase1_controls.md` and plan 28's tools, and cite it;
   - the 3-14 AU changed-cell list `output/scratch-31/diff-3-14-au.cells.tsv`
     (sha `77ff1d86…`, 246,123 cells). Read it once, streamed.
2. **Predicted forced-zero set:** rows whose rule is O04 or O05 and whose
   cell is in the changed-cell list. Split it shared/added × rule.
3. **Match:** exactly 34 rows (O05 30, O04 4), and the bucket deltas
   reproduce 3-15 → 3-17. Write the identity TSV (key, rule, shared/added,
   changed-cell membership) and an erratum note in the `.md`: the inherited
   "30 O05 + 1 O04" statement is an arithmetic error, with per-row
   identity. Do not rewrite the 3-15 text, the 3-17 rebaseline or the
   generated controls file.
4. **No match:** name the exact surplus or missing rows as residual, and
   force no count.
5. **Proposed pointer text** for the plan 28 record's F2 follow-up
   (discharged or carried). Execute applies it.

## Rules

- Light work only: committed TSVs plus one streamed read of the cell list.
  No dump, classify or K1 run. Do not re-run or reseat 3-17.
- Run only your new test and
  `parser/tests/test_perf_inventory.py`, with
  `--basetemp output/scratch-37/tests`.
- Your script lives under `docs/`, so `parser/perf_inventory.json` is not
  affected.
