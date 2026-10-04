---
brief_id:
design_id:
---

# Unit 1-01 — Empty-kind partition

Consumer: the single implementation worker for phase 1. Work only in
`/home/codyh/workspace/open-pajero-maps-08-zero-row-classify`, on `master`.
Read the committed design and `CLAUDE.md`. Starting design base: `ac1a64d`.
Execution id: `none`; workflow-service calls are forbidden by the user.

## Contract

From the design, verbatim:

> a zero-row background dump and a zero-row background_boundary dump each classify to exit 0 and a partition of zero rows. A non-empty kind keeps the partition it produces today. An empty dump is not reported as `PARTITION OK` for a kind the run did not read.

## Scope and ownership

Own `parser/tools/k1_triage.py`, `parser/kiwiw/dump_io.py`, and
`parser/tests/test_k1_triage.py`. Use a narrow change in classify; preserve default
zero-row rejection for other I/O consumers unless strictly required here.
Stat/open the named dump before accepting zero rows. A manifest claiming zero
for a non-empty, malformed, missing, or unreadable file must not pass. Emit an
empty assignment file for an accepted empty kind, replacing stale assignments.
Keep predicates, causes, rules, encoders, checker, and disc unchanged.

Do not edit plan 04, plan 07, 3-17 records, or the 3-16 packet. Do not write 3-90,
reseat design 170, encode, tally completeness, create a branch, push, open a PR,
call a workflow service, or commit. The orchestrator records and commits results.

## Implementation context

Required reading, in order: the design contract and phase outcome, `CLAUDE.md`,
then the classify loop, `file_rows`, and existing triage test helpers. Read only
relevant ranges. Depends on no other unit; runs alongside no implementation
agent. Budget: six relevant files, approximately 150 changed lines, 15 tool
turns. If exceeded, stop and report a handoff; do not expand scope.

`cmd_classify` validates with `file_rows` then constructs a `WindowedReader` and
`AssignWriter`, both rejecting zero. The non-empty loop and output ordering must
stay intact. Tests use synthetic aligned rows with all required columns.

## Done evidence

Demonstrate a failing regression before changing code and report before/after
results.

- Regression tests exercise each empty background kind through `main(classify)`
  with manifest count zero; exact zero partition line, exit 0, empty assignment,
  and header-only tables. Include a mixed empty/non-empty run to protect ordinary
  assignments and failure reporting.
- Guard tests reject zero manifest with non-empty/malformed/missing input and
  ensure no success partition is emitted for a kind that was not inspected.
- Run `PYTHONDONTWRITEBYTECODE=1
  /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python -B -m pytest
  parser/tests/test_k1_triage.py parser/tests/test_perf_inventory.py -q`.

## Reporting

Report touched files, implementation decisions, runnable test results, remaining
gaps and deviations. The orchestrator independently verifies existing real dump
views and disc identity under the shared heavy lock, then records the phase.
No further unit depends on this work.
