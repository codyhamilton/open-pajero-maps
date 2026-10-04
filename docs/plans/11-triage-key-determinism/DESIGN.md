# Triage key determinism

## Intent

User request, verbatim:

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history, including whatever the previous seat just pushed. Draw up designs only for remaining work that is actually still open in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp. One worker only. Stop when the remaining in-repo work you can finish is committed and pushed to master, or when you are genuinely blocked, and leave the result SHAs in the unit log.

## Problem

Plan 09 QA and commit `07c3918` explicitly record three summary-determinism
test failures reproduced on the preceding baseline. They were outside that
plan's malformed-JSON contract and remain in `parser/tests/test_k1_triage.py`.
This is existing repo debt, not a new map-content unit.

`k1_triage` aggregates internal structured keys by their bytes. Its keys use
aligned dtypes with padding. Zeroing their initial allocation does not control
padding in copies made by NumPy unique and advanced indexing. Different
padding can split equal logical keys across windows and prevent the source
group count lookup from finding its row key. This violates the tool's stated
byte-identical output and plan 05's window-invariance contract.

Ground: current `origin/master` is `7c4b78f`, including the previous seat's
eight commits. Plans 05 and 07–10 are completed records. Plan 04 Phase 3 is
blocked at 3-90; its dependent phases and plan 03's frozen content remain
unreleased. No plan 06 exists. Overview, Architecture, Workflow and the
stable K1 triage contract were read. No other independent signed build work
was found: optional measurements, the unreproduced bench flake and deferred
out-of-core finalization do not create implementation units.

## Solution Shape

Internal grouping identity consists only of declared field values, with no
allocator-dependent padding. NumPy still performs bounded window reductions;
Python retains independent copies only for report groups. The existing
summary, classify and enumerate entry points use the same key builders.

### Domain: internal aggregation

- Owns: the internal group, level/type, source and composite keys in
  `parser/tools/k1_triage.py`.
- Contract: equal declared values have equal byte keys through uniqueness,
  indexed copies and retained ownership. Distinct declared keys stay distinct.
  NaN source sentinels keep the existing canonicalization. Report counts,
  min/max, group membership, source associations, formatting and sorting are
  independent of repeated runs and window sizes.
- Non-goals: changing the aligned on-disk dump dtype, C row layout, rule
  predicates/order/causes, assignment format or CLI validation contracts.

### Domain: verification and records

- Owns: bounded synthetic regressions in `parser/tests/test_k1_triage.py`,
  the lasting contract in `docs/design/k1-triage.md` and Architecture, and
  the resolution pointer in plan 09 and Overview.
- Contract: independently computed field-value groups and source counts must
  match the CLI tables. Existing repeat/window/high-cardinality tests and
  classify/enumerate checks pass without needing a real disc or dump.
- Non-goals: rerunning blocked 3-90, signing a re-oracle, reconstructing native
  classification joins, resolving completeness or changing plan 04's gates.

## Decisions

One phase, one worker, direct implementation in the supplied worktree and
fast-forward push to `origin/master`, as requested. No PR. The installed
workflow skills were found at version 2.9.0 after the advertised 2.8.0 paths
proved absent. The user's one-worker instruction overrides skill delegation
and independent-agent review; a separate self-review is recorded honestly.

## Assumption Ledger

### Assumption 1

- Question: are the explicitly recorded baseline summary failures remaining
  work within the request, despite plan 09 itself being complete?
- Answer chosen: yes; resolve only their internal grouping cause here.
- Rationale: the committed QA names the unresolved failures, existing tests
  specify the expected behavior, and these report keys have no dependency on
  blocked map verification.
- If wrong: stop this scoped repair; do not treat it as Phase 3 closure.

### Assumption 2

- Question: can an internal key layout change while dump rows stay aligned?
- Answer chosen: yes; grouping keys never cross the file/C ABI boundary.
- Rationale: key constructors are local to triage and their consumers use
  named fields, dtype sizes and bytes rather than fixed offsets.
- If wrong: canonicalize padding at each copy boundary instead, retaining
  the same field-value identity and bounded memory contract.

## Phases

### Phase 1 — Triage tables agree across windows and runs

- Outcome: given the existing synthetic dump fixtures, `summary` produces
  identical TSV bytes across repeated runs and windows 1/17/64/997/65536,
  with correct logical group and source counts, including high cardinality
  and NaN sentinels. `classify` and `enumerate` retain correct rule row totals
  and group identities. The focused triage and shared-I/O tests pass.
- Surfaces: `parser/tools/k1_triage.py`, `parser/tests/test_k1_triage.py`,
  `docs/design/k1-triage.md`, `docs/ARCHITECTURE.md`,
  `docs/plans/09-malformed-rules-json.md`, `docs/OVERVIEW.md`.
- Approach: known.
- Depends on: the recorded baseline failures, independently of plan 04's gate.
- Refine: skipped; one bounded unit, brief `1-01-existing-key-determinism`.

## Verification Boundary

Run the existing failing unit tests to establish the baseline, then targeted
synthetic regression and shared-I/O/inventory tests after the fix. This design
does not prescribe a rerun of any recorded blocked verification. Tests use
temporary generated inputs; no protected paths are changed or deleted.
There is no new full-disc, memory-budget or build-byte claim.

## Design Challenge

Self-review under the one-worker constraint: fixing only source-key lookup
would leave group/classify/enumerate keys vulnerable to the same copy padding.
All four internal key builders belong to this one defect. The on-disk dtype
must remain aligned. An adversarial allocator-padding regression plus a
field-value reference will distinguish a real fix from a lucky test run.
This is not an independent review.
