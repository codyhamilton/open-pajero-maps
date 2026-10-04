---
design_id:
---

# Malformed rules JSON

## Intent

From the landed zero-row close-out, quoted:

> `_load_rules` can raise `JSONDecodeError` for syntactically invalid JSON, while `cmd_classify` catches only `BadRules` in that loading path. This pre-existing case exits with a traceback rather than the usual input-validation exit 2. Normalize that error reporting in a separately scoped change, with a regression that checks exit 2 and the absence of a stale success partition.

## Problem

Classify already returns exit 2 for a bad manifest or a rules file that fails the rules schema. A rules file that is not valid JSON skips that path: `json.loads` raises `JSONDecodeError`, nothing catches it, and the process prints a traceback. Partition cleanup already runs before rules loading, so this does not leave a stale success partition. It is still the wrong exit for bad input.

## Solution shape

One change on the classify input-error path. Invalid JSON is the same class of failure as the other rules-load failures: exit 2, no traceback, no success partition left behind.

### Domain: classify input errors

- Owns: how `cmd_classify` reports a rules file that `json.loads` cannot parse.
- Contract: a syntactically invalid rules file makes classify exit 2, with no uncaught `JSONDecodeError` and no `PARTITION OK` file left in the output directory. A valid rules file keeps today's partition. Empty-kind partitions from plan 08 stay as they are.
- Non-goals: no encoder change, no checker predicate change, no rule `cause` or `where` edit, no disc write, no completeness re-tally, no change to valid empty-kind classification.

## Decisions

1. One phase. This is only the invalid-JSON exit.
2. The 188 historic completeness rows stay where 3-17 left them. This plan does not name a cause for them.
3. Land on master. No feature branch. No pull request.

## Assumption ledger

### Assumption 1

- Question: should invalid JSON share exit 2 with the other rules-load failures, or stay a traceback?
- Answer chosen: exit 2, same as the other input-validation failures.
- Rationale: the close-out of plan 08 named that exit and a regression for it, and said the case is pre-existing and separate from empty-kind classification.
- If wrong: leave the traceback, and do not invent a new exit code.

## Open questions

None that block the phase.

## Phases

### Phase 1 — Invalid rules JSON exits 2

- Outcome: classify given a syntactically invalid rules file exits 2, does not raise `JSONDecodeError`, and leaves no success partition. A valid rules file still partitions as it does on `3a7fe37`. The disc sha is unchanged.
- Surfaces: the classify rules-load path in `parser/tools/k1_triage.py`, and the regression in `parser/tests/test_k1_triage.py`.
- Approach: known
- Depends on: plan 08 closed on master at `3a7fe37`. Do not reopen 3-17. Do not write 3-90. Do not reseat design 170 or 3-16.
- Refine: skipped. One phase, one worker.

## Provenance

- Plan 08 close-out recorded this as the only follow-up. The lasting note is in `docs/design/k1-triage.md`.
- Plan 04 phase 3 stays open. This plan does not close it.
