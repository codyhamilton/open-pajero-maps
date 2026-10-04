# Implementation

- Tool: Open Pajero Maps Execute, orchestrator
- Run: design_id 170, plan 07-g-new-nonpayload, started 2026-10-03 22:45 Australia/Brisbane
- Worker: historical attribution landed as 90b05b69331e49e098367022bfa04f7ba9154a95

workflow-quality was not called for this brief. That is a gap to check against the ledger. Do not treat a missing id as a posted brief.

## Phase 1 — Name the 60 bytes, or accept them

Brief: `briefs/1-01-name-or-accept.md`. The attribution was completed in
`90b05b69331e49e098367022bfa04f7ba9154a95` and landed through
`ced98f8272fc1e4a34ba0d34b0dbbb1535c5f205`. The original "Not started" line
was stale. PHASE.md is the committed result, not a pending work item.

### Documentary verification

Codex status-continue read the design, brief, PHASE record, merge history,
`frame_table.py` allocation/placement, and the existing schema padding row.
The tracked 41-row table has 34 deltas of -4 and seven of +28, summing to +60;
every row's new minus old padding length equals its delta. Nonempty old spans
and nonempty new spans are disjoint. The named mechanism matches current
allocation/placement code and the already documented zero padding to 32 bytes.

This verifies the committed record's internal consistency. The original
disc comparison, zero-byte checks, full-file coverage and 37-cell membership
remain historical evidence from the landed attribution; no fresh disc check
or scratch replay occurred. No missing evidence is invented. No schema or
encoder change is needed. The historical execution had no service id, so its
documentary phase-closing commit uses exec none. Independent review precedes
close-out and the detailed accounting will be retained in docs/design.

**Carried:** None within this attribution. Plan 04 Phase 3 stays open.
