---
design_id:
---

# Zero-row classify

## Intent

From the landed 3-17 record, quoted, not a new measurement:

> This scoped re-baseline does not satisfy that phase-close outcome: the live completeness remainder is unattributed, and empty kinds lack a CLI partition.

This design is only the empty-kind partition. The completeness remainder stays where 3-17 left it.

## Problem

`k1_triage.py classify` rejects a zero-row dump. On the disc already in force, background and background_boundary failing counts are 0, their dumps are empty, and classify exits 1 with `dump_io.file_rows` raising `zero-row kinds are unsupported`. That abort is not a partition. It does not say whether the kind was read.

## Solution shape

One change in the classify path. A zero-row kind is a partition of zero rows, not an error. Predicates, causes, and the disc are untouched.

### Domain: classify

- Owns: reading a dump kind that has zero rows, and the partition line for that kind.
- Contract: a zero-row background dump and a zero-row background_boundary dump each classify to exit 0 and a partition of zero rows. A non-empty kind keeps the partition it produces today. An empty dump is not reported as `PARTITION OK` for a kind the run did not read.
- Non-goals: no encoder change, no checker predicate change, no rule `cause` or `where` edit, no disc write, no fresh full-AU encode, no completeness re-tally.

## Decisions

1. One phase. The empty-kind abort is the whole change. Completeness stays outside this plan.
2. The 188 historic completeness rows stay unattributed. This plan does not name a cause for them and does not edit that list.
3. Land on master. No feature branch. No pull request.

## Assumption ledger

### Assumption 1

- Question: is the zero-row rejection a defect, or a guard that must stay?
- Answer chosen: it is a defect for a kind whose failing count is already 0. Classify should report zero rows.
- Rationale: 3-17 could not emit a partition for empty background and background_boundary dumps, and the failing counts for those kinds are 0.
- If wrong: leave the rejection in place, record that empty kinds stay unsupported, and do not invent a partition result.

## Open questions

None that block the phase.

## Phases

### Phase 1 — Empty kinds partition as zero rows

- Outcome: classify of the existing zero-row background dump and the existing zero-row background_boundary dump exits 0, writes a partition of zero rows for that kind, and does not change the partition of a non-empty kind. The disc sha is unchanged. No file under the 3-17 record, plan 07, or the 3-16 packet is edited.
- Surfaces: `parser/tools/` classify entry and `dump_io.file_rows`, plus the test that covers a zero-row kind.
- Approach: known
- Depends on: 3-17 on master at `ac1a64d`. Do not reopen that unit. Do not write 3-90. Do not reseat design 170 or 3-16.
- Refine: skipped. One phase, one worker.

## Provenance

- 3-17 (`ac1a64d`) already recorded historic background 137 and background_boundary 8,739 as not in the failing set, and the classify abort on `background.bin`. This plan does not repeat that ledger.
- Plan 04 phase 3 stays open. This plan does not close it.
