# Zero-row classify

This change made existing empty background and background_boundary dumps valid
zero-row classify partitions. Both selected kind views exited 0 and produced
their own zero partition lines. The non-empty name_anchor output stayed byte
identical to the retained reference, and the disc SHA stayed unchanged.

## Intent

From the supplied design, verbatim:

> This scoped re-baseline does not satisfy that phase-close outcome: the live completeness remainder is unattributed, and empty kinds lack a CLI partition.

This design is only the empty-kind partition. The completeness remainder stays where 3-17 left it.

## Why This Existed

The landed 3-17 record at `ac1a64d` had zero-byte background and boundary dumps,
but classify aborted at the shared `dump_io.file_rows` zero-row guard. An abort
did not establish a partition or prove the empty kind had been inspected.

## What Was Built

**Changed:** `parser/tools/k1_triage.py`, `parser/kiwiw/dump_io.py`, and
`parser/tests/test_k1_triage.py`. New scratch evidence was documented in
`docs/provenance.md`.

Classify opted into empty file row counting, checked file/manifest agreement,
and opened and read an empty input before reporting success. It emitted an empty
assignment file, a zero partition line, and header-only tables when appropriate.
The shared reader/writer guards continued to reject zero rows for other callers.

Invalid input checks rejected missing, unreadable, malformed, and non-empty
files declared empty. A mixed empty/non-empty run continued to fail when ordinary
rows remained unclassified. Partition cleanup moved ahead of manifest and rule
validation to prevent old success output from surviving rejected invocations.

The lasting contract is in [K1 classify partitions](../design/k1-triage.md).

## Deviations

Refine was skipped for the single implementation unit. Workflow-service calls
and posts were omitted under the explicit user instruction; execution ids were
`none`. Work landed directly on `master` without a feature branch, push, or PR.
The supplied untracked design was included in preparation commit `77211c1`.

The legacy skill checker reported missing Claude skill entries; the available
Codex workflow plugin skills were used without installing anything externally.
No behavioral scope deviation was required.

## Review

Independent comprehensive review assessed the phase outcome and design
assumption as met. It resolved one medium stale-output finding mechanically,
with focused regressions. The final verdict was `PASS_WITH_FOLLOWUPS` for the
pre-existing malformed-rules-JSON error path described below. The design was
sufficient to determine scope, ownership, and verification.

## QA

The implementation worker demonstrated five failing regressions before the fix.
The final relevant suite passed **43 tests** across triage, performance
inventory, dump join, and extension tests.

The retained 3-17 kind-view CLI replay produced:

| Kind | Exit | Manifest / assigned / unclassified / cause sum |
| --- | ---: | --- |
| background | 0 | 0 / 0 / 0 / 0 |
| background_boundary | 0 | 0 / 0 / 0 / 0 |
| name_anchor | 0 | 1 / 1 / 0 / 1 |

Each view emitted `PARTITION OK` for that kind. Every name_anchor output byte
matched the prior reference. Both empty assignments were zero bytes. Replay
input hashes matched after execution, and before/after disc SHA256 was
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.

A separate cheap-tier verifier reran the CLI replay and checked disc identity
and protected paths. The replay used the shared heavy lock and new local
`output/scratch-08-zero-row-classify/` evidence; reproduction is recorded in
`docs/provenance.md`. `git diff --check` passed.

## Residual Risks

The real replay covered the selected kind views; it did not establish all-kind
partition success. The historic completeness remainder stayed unattributed.
No encoder, checker, rule cause/predicate, disc, 3-17 record, plan 07 file, or
3-16 packet was edited. Plan 04 phase 3 stayed open.

## Follow-ups

The separately scoped malformed-rules JSON follow-up was resolved by
[plan 09](09-malformed-rules-json.md) at `07c3918`. The historic finding above
is retained; no follow-up remains within the zero-row contract.
