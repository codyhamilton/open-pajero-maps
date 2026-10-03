---
design_id: 170
---

# Brief: 07 phase 1 — Name the +60 non-payload bytes, or accept them

Consumer: the orchestrator, who lands this folder. Design already signed design_id 170. This is not design id 2.
Owned paths: `docs/plans/07-g-new-nonpayload/PHASE.md`, and `docs/schema/` only if you name a field that `docs/schema/` does not yet describe. Evidence notes may live under `output/scratch-07/` (git-ignored). Never overwrite `output/scratch-3-11/`, `output/scratch-3-14/`, `output/scratch-3-15/`, or `output/scratch-3-16/`.
Commits: PHASE.md, and a schema file only in the naming case. No encoder, checker, disc, or recorded build-sha edits.
Depends on: the existing 3-11 disc pair only. Read `docs/plans/04-c-core-orchestration/triage/review_3-11.md` for the recorded figures. Do not edit anything under `docs/plans/04-c-core-orchestration/`.
Runs alongside: nothing that writes those discs. Diff only. No full-AU encode. Do not read a 3-16 result.
Tier: Codex or DeepSeek. No Claude. No Sonnet.
Budget: ≤ 40 tool turns.

## Cited contract (do not re-measure the 37-cell compare)

From design 170 and the 3-11 review:

- The only pair under test is the 3-11 old/new G discs under `output/scratch-3-11/` (`G` and `Gnew`). Frame payload grew by 164 bytes (1,597,341,290 → 1,597,341,454), which is 41 × 4 and matches the 37 L0 cells whose lengths changed. `total_size` grew by 224 bytes. The residual is 60 bytes outside the frame payload.
- The file is not 2048-aligned. Rounding cell lengths to 512 or 2048 predicts a delta of 0. Rounding to 16 predicts 160. Sector rounding is not a name for this residual.
- The 3-14 Perth sha change is orthogonal and is not this residual. A later 3-14 size move is not this residual.
- The +164 figure stays the figure already recorded for 3-11. Do not recompute the 37-cell compare.

## Goal

On that existing pair, either name the 60 bytes or accept them.

Naming means one non-payload structure, with a path, an offset, and disjoint before/after byte deltas that sum to +60, are not part of the +164 payload, and are tied to the 37-cell growth or the assemble step.

Accepting is allowed only after header, sector map, index tables, trailing pad, and the other container fields already described in `docs/schema/` are diffed and those deltas do not sum to +60. Then PHASE.md states the exact sentence "+164 payload attributed; +60 non-payload unattributed, accepted." No schema edit in the accept case.

## Non-goals

- No encoder or checker edits. No disc or recorded build-sha added or edited.
- No re-encode, including no full-AU and no 3-14 disc.
- Do not edit `docs/plans/04-c-core-orchestration/`.
- Do not read 3-16's result. Do not close plan 04 Phase 3.
- Completeness, the 9,064 re-baseline, and R01 exclusivity stay outside this plan.
- Do not amend `docs/ARCHITECTURE.md`.

## Pre-edit checks (any fail → blocked)

C1. `docs/plans/07-g-new-nonpayload/DESIGN.md` frontmatter is `design_id: 170`. If the body is design id 2, stop.
C2. The 3-11 pair is the existing `output/scratch-3-11/` G and Gnew discs. If either file is missing, blocked. Do not build a replacement.
C3. Quote the recorded payload delta +164 and `total_size` delta +224. Do not re-derive them from a new encode.

## Steps

1. Diff only the non-payload container regions on the existing pair: header, sector map, index tables, trailing pad, and the other container fields already described in `docs/schema/`.
2. If one structure's disjoint before/after deltas sum to +60, are outside the +164 payload, and tie to the 37-cell growth or the assemble step, write that path, offset, and deltas in PHASE.md. Update `docs/schema/` in the same change only if that field is new.
3. Otherwise write the region diff and the exact sentence "+164 payload attributed; +60 non-payload unattributed, accepted." Do not edit schema.
4. Record the outcome in `IMPLEMENTATION.md` under Phase 1: C1–C3, which record you wrote, deviations.

## Done evidence

- `PHASE.md` exists and is exactly one of the two records in the design's Phase 1 outcome.
- `git diff` shows no encoder, checker, disc, or build-sha change, and no edit under `docs/plans/04-c-core-orchestration/`.
- Schema changes appear only in the naming case, and only for a field the schema did not already describe.

## Report back

Under 400 tokens: status (`done` | `blocked`); named structure or the accept sentence; paths touched; deviations. Do not start another unit.
