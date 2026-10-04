# Malformed rules JSON

Classify's malformed rules JSON handling was completed at
`07c3918ace0f37b3c1a47c8e069c6e0e1a9cd783`. Invalid input now exits 2
without an uncaught traceback or a stale success partition. This is a
record of the already landed fix, not a second implementation.

## Intent

From the landed zero-row close-out, quoted:

> `_load_rules` can raise `JSONDecodeError` for syntactically invalid JSON, while `cmd_classify` catches only `BadRules` in that loading path. This pre-existing case exits with a traceback rather than the usual input-validation exit 2. Normalize that error reporting in a separately scoped change, with a regression that checks exit 2 and the absence of a stale success partition.

## Why This Existed

Schema-invalid rules already used exit 2, but syntactically invalid JSON
escaped as JSONDecodeError. The input errors needed the same CLI contract.

## What Was Built

**Changed:** `parser/tools/k1_triage.py` catches JSONDecodeError beside
BadRules, and `parser/tests/test_k1_triage.py` covers fresh output and a
stale successful output directory. Cleanup precedes rules loading. Valid
rules and zero-row partitions keep their prior behavior.

The lasting contract is in [K1 classify partitions](../design/k1-triage.md).
The stale follow-up wording there was corrected during status reconciliation.

## Deviations

The original execution's user prohibited service calls and extra workflow
records/close-out. Its design had no service id and its commit used exec none.
Both phase and done trailers already exist at the implementation commit;
this documentary close-out does not invent or repeat a phase execution.
The present user authorized finishing the remaining repo bookkeeping.

## Review

Independent documentary review at `176383a` returned PASS. The input-error
outcome, bounded diff and regression intent match the design. No blocker or
high finding remained. No test or blocked verification was rerun for closure.

## QA

The implementation commit records both new cases failing before the fix
and passing afterward, all 15 classify tests passing, and valid nonempty,
all-empty and mixed partitions byte-identical to `3a7fe37`. Synthetic input
hashes were unchanged. These are historical results, not new measurements.
The full triage file then had 19 passes and three summary-determinism failures;
all three were reproduced on the baseline and predate this change.

## Residual Risks

The disc was absent at implementation time and not freshly rehashed; no disc
was accessed or modified. Current documentary review makes no new disc hash
or completeness attribution claim. Plan 04 Phase 3 remains independently
blocked. The recorded baseline summary failures are outside this contract.
Their internal-key padding cause was subsequently resolved by
[plan 11](11-triage-key-determinism.md); the historical QA above is retained.

## Follow-ups

None for malformed JSON handling. Plan 04 owns its existing completeness,
classification and phase-close blockers; this fix does not reopen those units.
