---
design_id: 170
---

# G_new non-payload attribution

The existing 3-11 disc pair's +60-byte residual was named as Map Frame
allocation padding. The attribution landed in `ced98f8` from `90b05b6`.
This record replaces stale orchestration text that still said not started.

## Intent

User request, verbatim:

> Write the next design from the real backlog. 3-16 is already designed, so this is the one after it. One design. Start it as new work, not by continuing a session you already have open. Hold it and do not send it to Execute.

## Why This Existed

The recorded frame payload grew by +164 bytes across 37 L0 cells, while
ALLDATA total_size grew by +224. The extra +60 needed its own container
accounting; generic sector rounding was insufficient.

## What Was Built

The historical read-only comparison named zero-filled allocation padding:
21,570,746 → 21,570,806 bytes. The 41 changed spans sum to
34 × (-4) + 7 × (+28) = +60. Seven allocations grew by one 32-byte
logical sector; the other 34 absorbed four-byte frame growth.
The offsets, structure paths, full region accounting and all 41 rows are
retained in [the accounting record](../design/g-new-nonpayload-accounting.md).
The original +164 payload measurement was not repeated or changed.
The existing disc-layout schema already described this field.

## Deviations

The original design was held before the subsequent attribution execution
and landing. The historical brief was not posted to workflow-quality and
had no execution id; none was fabricated retrospectively. Reconciliation
recorded the already landed result and its missing phase-closing trailer.
The present user request authorized continuing and closing finished work.
No new attribution, encoder, checker or schema change was necessary.

## Review

Independent terminal review at `176383a` returned PASS. The signed named-field
outcome was met on the historical evidence. Fresh documentary review checked
all row deltas, their total, disjoint nonempty spans, allocation/placement code
and the existing schema contract. No blocker or high finding remained.

## QA

The landed record reports read-only container comparisons, zero padding,
complete file coverage and membership in the prior 37-cell list. The current
review established internal consistency of that record and source mechanism.
It did not perform a fresh disc comparison or rerun any blocked verification.

## Residual Risks

Original raw disc/scratch claims remain historical; those inputs were absent
in this worktree and were not accessed elsewhere. This record makes no new
full-disc or byte-hash claim. Plan 04 Phase 3 remains separately blocked.

## Follow-ups

None for the +60 attribution. Completeness, the historic ledger, R01 and
phase-close verification remain in plan 04; the +60 does not own those items.

## Decisions Worth Keeping

Compare container structures by path so relocation does not count as growth.
Allocation padding is separate from payload. The attribution applies to the
existing 3-11 pair; later 3-14 content changes are a separate oracle question.
