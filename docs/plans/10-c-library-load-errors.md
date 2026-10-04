---
design_id: 214
---

# C library load errors

Plan 03 Phase 3C carried item 4 was resolved in `68aa329`: assembly library
load and missing-symbol failures now raise BuildError, retain their causes,
and allow retry. The obsolete Python-fallback descriptions were removed.

## Intent

User request, verbatim (relevant portion):

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history. Draw up designs only for remaining work that is actually in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp.

## Why This Existed

The already landed build requires C, but its assembly binding leaked
AttributeError for a missing symbol and hid library-open OSError behind None.
The compiler module still described a deleted Python fallback. Both were
explicit debt in plan 03, separate from blocked plan 04 verification.

## What Was Built

**Changed:** `parser/kiwiw/cenc.py`, `parser/kiwiw/cbuild.py`, focused tests
in `parser/tests/test_cenc.py`, and the carried-item resolution in plan 03.
Compiler BuildError propagates unchanged. Library-open OSError and missing
assembly-symbol AttributeError become BuildError with the library path and
original exception chained. Cache publication follows complete signature
setup. A failed load leaves retry possible; valid signatures and successful
object caching remain unchanged. No C algorithm or compiled ABI changed.

The mandatory-C and assembly binding contracts are in
[Architecture](../ARCHITECTURE.md#build-requirement).

## Deviations

Refine was skipped for one small implementation. Design and brief received
an independent design pass; its docstring/scope clarifications were applied.
The orchestrator implemented directly with no worker running, as permitted
by the execute skill. Workflow service identities were design 214, brief 216,
execution 17. Initial brief rating findings were addressed before execution.
Final design rating 0.873 vs repo mean 0.872, brief 0.735 vs repo 0.632;
neither flagged a criterion outside the repo norm.

The user authorized direct fast-forward push to master from the supplied
branch and prohibited a PR. Separate documentary bookkeeping reconciled
landed plans 07/09 and plan 03's already accepted grep wording; it added no
functional unit to this design or plan 04.

## Review

Independent terminal review at `176383a` returned PASS. A low stale statement
in `cbuild.build_ext()` was corrected mechanically during review (`be52fe7`).
The failure/retry/cache contract and design assumption held. No briefed finding
or non-blocking functional follow-up remained. The plan was sufficient to
bound the existing debt and its verification.

## QA

Before implementation, the seven new cases gave **5 failed, 2 passed**.
Afterward, loader, real column-table, tiny build wiring and indexed assembly
checks gave **13 passed in 4.36 s**, no skips. `git diff --check` passed.
No already blocked check, full-Australia build, disc check, or memory benchmark
was repeated. Review inspected the recorded results and tests without replay.

## Residual Risks

Other loader families, broad ABI checking and concurrency are outside this
binding contract. There is no new full-disc or performance claim. Original
inputs, scratch, symlink targets, .venv-rp and other checkouts were preserved.
Plan 04 Phase 3 and dependent phases remain blocked by their existing record.

## Follow-ups

None within carried item 4. Plan 03's remaining content work stays frozen
pending plan 04's successor design; its other historical or optional debt
was not converted into ungrounded implementation units.
