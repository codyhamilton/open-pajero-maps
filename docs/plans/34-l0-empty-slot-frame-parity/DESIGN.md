---
design_id:
---

# L0 empty-slot frame parity (0,541) / (0,562) / (0,563)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Root-cause and fix (or prove a non-deviation for) the plan-29 carried structural residual: on successor `2ee3456a…`, G still has L0 frames at cells **(0,541)** (nameless after O03 drop), **(0,562)**, and **(0,563)** where R has **empty_slot** (no frames) in the same block. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Skip plan 29 close-out (Execute). Do not reseat the O03 name drop.

## Problem

Plan 29 cleared the O03 name_anchor failure (verdict A) and produced successor `2ee3456a…` with leaf-928 names empty. It explicitly carried:

- G still has a (now nameless) L0 **(0,541)** leaf frame where R has empty_slot.
- G has non-empty L0 frames at **(0,562)** and **(0,563)** in a block where R has **0** frames (`r_reader_control.json`: `block0_cells_with_frames` R=0 / G=3).

No K1 failure remains on these cells (562/563 carry 0 names; 541 names cleared). Under the standing rule, **frame occupancy vs R empty_slot** is still a verifiable DVD deviation without a closed root cause or fix.

| Cell | R (plan 29) | G successor |
| --- | --- | --- |
| (0,541) | empty_slot | leaf frame present, names `[]`, length 320 (padded after drop) |
| (0,562) | empty_slot (block census) | frame present, 0 names |
| (0,563) | empty_slot (block census) | frame present, 0 names |

**Ground (tip `5ff9eb0`):** plan 29 IMPLEMENTATION carried items; `witnesses/r_reader_control.json`, `g_successor.json`, `successor_diff.json` (541 hop only). Probe-and-pad kept frame extents after name drop — explained for 541's padding, not for why 562/563 exist at all.

## Solution shape

1. Byte-identify the three G frames vs R empty_slot.
2. Prove why G emits them (spool content, parcel mask, empty-frame emission policy).
3. Fix G to match R's empty_slot **or** prove a non-deviation (format requires a frame R also has under a different address — must be evidenced, not assumed).

### Domain: triple frame witness

- **Owns:** committed byte-level identity of the three G frames and R's empty_slot status for the same cells (and stated neighbours if needed).
- **Contract:**
  1. For each of (0,541), (0,562), (0,563) on successor `2ee3456a…`: frame offset, length, sha256, leaf path, name count, background/road counts if any, payload classification (empty / header-only / content).
  2. R pin `8c2d2027…`: slot status empty_slot (or decode of any unexpected frame).
  3. Historical `4ed9cd80…` control for the same three cells (pre-drop name on 541 only).
  4. Whole-block census: count G vs R frames in the 32×64 block containing ix=0 (extend plan-29 reader control as needed).
  5. Bounded preads via wrapper + lock; no whole-file loads.
- **Non-goals:** no fix yet; no O03 reseat; no other levels.

### Domain: root cause and fix or non-deviation

- **Owns:** named root cause for each cell's G-frame-vs-R-empty_slot deviation, and a closing verdict.
- **Contract:**
  1. Root-cause candidates to discriminate (not assume): spool has geometry/names forcing a frame; assembly emits empty frames for masked/unowned cells; probe-and-pad left a nameless shell (541 only); parcel_mask / occupancy mismatch vs R.
  2. Verdict ∈ {`fix-landed`, `proven-non-deviation`, `conflict-open`}.
  3. **`fix-landed`:** successor (or new path) no longer carries a frame where R has empty_slot for each named cell; diff confined to those frames/cells; protected discs untouched; live K1 exit 0 retained; Perth unchanged or explained.
  4. **`proven-non-deviation`:** byte proof that R's "empty_slot" is equivalent occupancy under the wire contract (e.g. shared sparse alias) — only with evidence; never by renaming.
  5. 541's nameless padded frame may share cause with 562/563 or split (pad-after-drop vs unjustified emit).
  6. No Phase 3 close; no 3-90; no P4–6.
- **Non-goals:** no full re-extract; no loosening K1; no inventing R frames.

## Decisions

1. Plan number **34**. Land on master directly. No feature branch. No PR.
2. Two phases. Phase 1 known. Phase 2 approach **open** (emit-suppression route vs mask/occupancy fix vs proven equivalence) against the fixed outcome. Refine skipped.
3. Independent of plan 33 (O04). Small enough to draft alongside.
4. Disc in force `2ee3456a…`. Heavy under wrapper + lock.
5. Hard constraints: no reseat 170/3-16/3-17; no P4–6/plan 06; no Phase 3 close; no 3-90; skip plan 29 close-out; do not undo O03 drop.

## Assumption ledger

### Assumption 1

- **Question:** Are only these three cells in scope?
- **Answer chosen:** Yes as the plan-29 carried set. Phase 1 block census may list extras; any extra G-frame-where-R-empty in that block is named and either folded in or residualled — not ignored.
- **Rationale:** Standing rule; don't silently absorb.
- **If wrong:** Scope expands to the full block list from the census.

### Assumption 2

- **Question:** Is a nameless padded frame at (0,541) acceptable as non-deviation because names match?
- **Answer chosen:** No by default — R has empty_slot (no frame). Names equality was plan 29's bar; frame occupancy remains open here.
- **Rationale:** Plan 29 carried it to Design explicitly.
- **If wrong:** Cody accepts nameless shells — then `proven-non-deviation` with that ruling recorded.

### Assumption 3

- **Question:** Does fixing empty-slot frames require a new successor oracle?
- **Answer chosen:** Yes if bytes change; record as successor of `2ee3456a…` with confined diff. Protected historical discs untouched.
- **Rationale:** Same discipline as plan 29.
- **If wrong:** In-place documented exception — still need hash proof.

## Open questions

1. Whether 562/563 frames contain any non-name payload (background/road) — Phase 1 answers.
2. Fix route (suppress empty emission vs occupancy mask) — Phase 2 open approach.

## Phases

### Phase 1: Three cells byte-witnessed; block census recorded

- **Outcome:**
  1. Committed witnesses for (0,541)/(0,562)/(0,563) on G successor + historical and R empty_slot proof.
  2. Block census G vs R frame counts; any extra cells listed.
  3. Payload class per G frame (empty shell / content).
  4. Not done: no fix; no Phase 3 close.
- **Surfaces:** `docs/plans/34-l0-empty-slot-frame-parity/`; read-only plan-29 witnesses/tools; discs via wrapper.
- **Approach:** known. **Refine:** skipped.

### Phase 2: Root cause proven; fix-landed or proven-non-deviation for each cell

- **Outcome:**
  1. Per-cell cause + verdict; `conflict-open` = 0 or named.
  2. If fix: new disc path, sha, diff confined to named cells, K1 exit 0, provenance/OVERVIEW note (no Phase 3 close).
  3. Plan-29 carried residual discharged or exact residual named.
- **Surfaces:** plan-34 folder; optional `build_alldata` / assembly emit policy; tests; `docs/provenance.md` / OVERVIEW as needed.
- **Approach:** open. **Refine:** skipped.

## Provenance

- Tip `5ff9eb0759c0dc2b38f9167682d99435cbd66fb7`. Plan 29 IMPLEMENTATION carried items; `r_reader_control.json`; `g_successor.json`.
- Rejected: absorbing into O03; claiming names-equal ⇒ frame-equal; Phase 3 close; 3-90; P4–6; reseating 170/3-16/3-17.
- Box draft only. Adversarial in-context: 541 pad ≠ proven non-deviation; 562/563 need own payload census before fix route.
