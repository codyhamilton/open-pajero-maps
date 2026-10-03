---
design_id: 170
---

# G_new +60 byte non-payload

## Intent

User request, verbatim:

> Write the next design from the real backlog. 3-16 is already designed, so this is the one after it. One design. Start it as new work, not by continuing a session you already have open. Hold it and do not send it to Execute.

## Problem

Plan 04 unit 3-16 is already a signed design (window counterfactual on the 89 stitch-absent completeness keys, master `9b44b59`). The next real backlog item is not another completeness unit. It is the G_new +60 byte residual left by unit 3-11.

Unit 3-11 re-oracled full-AU. Frame payload grew by 164 bytes, which is 41 × 4 and matches the 37 L0 cells whose lengths changed. File `total_size` grew by 224 bytes. The residual 60 bytes sit outside the frame payload. A sector-rounding explanation does not fit: the file is not 2048-aligned, and rounding cell lengths to 512 or 2048 predicts a delta of 0, to 16 predicts 160. The residual is plausibly a container or index structure. It has been unattributed since the 3-11 review. It is required before plan 04 Phase 3 can close. It does not block 3-16, and it does not read 3-16's result.

## Solution Shape

After this design, the 60 bytes are either named or explicitly accepted. Naming means one non-payload structure, with a path, an offset, and disjoint before/after byte deltas on the existing 3-11 disc pair that sum to +60, are not part of the +164 payload, and are tied to the 37-cell growth or the assemble step. Accepting means the phase record states that those container regions were diffed and their deltas do not sum to +60, and then states "+164 payload attributed; +60 non-payload unattributed, accepted." No encoder change happens in this design.

### Domain: container accounting

- Owns: the bytes of `ALLDATA.KWI` that are not frame payload: header, sector map, index tables, trailing pad, any other container field already described in `docs/schema/`, and one not-yet-described container field only when its bytes are outside the frame payload and the deltas sum to +60.
- Contract: the only pair under test is the 3-11 old/new G discs. Payload delta is +164 and stays the figure already recorded for 3-11. `total_size` delta is +224. The residual is +60. A named cause cites a path, an offset, and disjoint before/after deltas that sum to +60, states the tie to the 37-cell growth or the assemble step, and is not part of the +164. "Sector rounding" is not a name. The 3-14 Perth sha change is orthogonal and is not this residual. A later 3-14 size move is not this residual.
- Non-goals: does not own frame payload, completeness, background stitch, or L8 TRIM.

### Domain: phase-close honesty

- Owns: the sentence this plan records for the residual.
- Contract: the line, stored in this plan, is either the named structure or the exact sentence "+164 payload attributed; +60 non-payload unattributed, accepted." The 3-11 exact 37-cell compare is a fact this phase does not re-measure. Plan 04 may quote the sentence when Phase 3 closes. This phase does not write plan 04's checklist and does not edit `docs/plans/04-c-core-orchestration/`.
- Non-goals: does not close plan 04 Phase 3. Completeness, the 9,064 re-baseline, and R01 exclusivity stay outside this plan.

## Architectural Implications

- `docs/ARCHITECTURE.md` "Output invariance" says `total_size` is identical across worker counts and performance changes for a given spool. It does not claim `total_size` is invariant across a content change. The +224 is a content change (37 cells grew). This design does not amend that contract.
- `docs/OVERVIEW.md` requires every accepted deviation to be recorded. An accept-with-honesty close is that record. A named field that `docs/schema/` does not yet describe is updated in the same change as the naming. No schema edit if the close is acceptance.
- This folder does not edit `docs/plans/04-c-core-orchestration/`. Plan 04's Phase 3 close may cite this plan's sentence later. Plans 03, 04 Phases 4–6, and the unsigned 06 draft stay untouched.
- `docs/design/` has no prior note of this residual. Nothing in the stable docs is stale in a way this design depends on.

## Decisions

1. This is the item after 3-16. The 9,064 re-baseline and the R01 exclusivity note wait behind it.
2. One phase. The outcome is attribute-or-accept. A code fix is a later amendment, not a second phase guessed now.
3. Held at the checkpoint. Not sent to Execute. Not a seat.

## Assumption Ledger

### Assumption 1

- Question: Does this live as a new plan folder, or as another unit inside plan 04?
- Answer chosen: a new folder, `docs/plans/07-g-new-nonpayload/`. Plan 06's number stays free for the unsigned CI-gate draft, which is not on master.
- Rationale: the request was to start new work, not to continue the plan 04 session. The folder is the work item.
- If wrong: rename the folder only. Do not move the record into plan 04. The outcome sentence stays in this plan.

### Assumption 2

- Question: May accept-with-honesty close this without a Cody ruling?
- Answer chosen: yes, only after header, sector map, index tables, trailing pad, and the other schema container fields are diffed on the existing 3-11 pair and those deltas do not sum to +60. A firmware or allowlist-policy ruling is out of scope.
- Rationale: the 164 byte payload is already explained. The residual is a honesty gap. The accept sentence is the record of a failed diff, not a skip.
- If wrong: stop with the diff and do not write the accept sentence.

### Assumption 3

- Question: Does the pass re-encode full-AU?
- Answer chosen: no. Diff the existing 3-11 pair only.
- Rationale: the residual was measured on that pair. A new encode mixes in later stitch changes and spends a full-AU run on a 60 byte question.
- If wrong: stop. A re-encode is a later design. This phase still diffs only the existing 3-11 pair and does not open a 3-14 disc.

## Open Questions

None that block sign-off.

## Phases

One phase. Refine is skipped: one worker can carry it.

### Phase 1 — Name the 60 bytes, or accept them

- Outcome: `docs/plans/07-g-new-nonpayload/PHASE.md` holds one of two records. (1) A non-payload structure with a path, an offset, and disjoint before/after deltas summing to +60, not called sector rounding, with the tie to the 37-cell growth or the assemble step, and a `docs/schema/` update in that same change only if the field is new. (2) The region diff showing header, sector map, index tables, trailing pad, and the other schema container fields do not sum to +60, plus the exact sentence "+164 payload attributed; +60 non-payload unattributed, accepted.", and no schema edit. The +164 figure stays the figure already recorded for 3-11. No encoder or checker file changes, and no disc or recorded build sha is added or edited.
- Surfaces: `docs/plans/07-g-new-nonpayload/PHASE.md`, and `docs/schema/` only in case (1).
- Approach: known
- Depends on: nothing in this design. It is the backlog item after signed 3-16. It does not read 3-16's result, and it is not a unit in plan 04's queue.

## Provenance Notes

- Rejected: folding this into 3-16. 3-16 tests whether 89 completeness keys reappear under a window counterfactual. The 60 bytes are a container residual from 3-11 and pre-date that stitch.
- Rejected: a build-fix phase. No structure is named yet, so a fix phase would invent the approach.
- Rejected: sector rounding. Already measured; it does not produce 60.
- Rejected: writing the honesty line into plan 04 from this phase. That would continue the plan 04 session. Plan 04 may cite this plan later.
- The checkpoint is held. This folder is not handed to Execute.
