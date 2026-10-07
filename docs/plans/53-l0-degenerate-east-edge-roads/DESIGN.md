---
design_id:
---

# Five degenerate G L0 road links on the parent east edge (R-G9-3-d)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close R-G9-3-d: plan 42 found 5 G L0 road links in parent (1755,591) leaves 0/4/4/4/8 with 6–10 vertices all at x=4096 (parent east edge), outside their sub-cell rect by up to 3,072 raw. Whether this is a D1 decode artefact or an encoder defect in oracle `aeae426c` (live tip; DESIGN draft cited historical `4e6b0de7`) was not determined.

flock + wrapper, `-j4`. Master direct. Never relabel. No plan 04 P4–6. No 3-90. No waivers.

## Problem

- Only data outside a leaf rect in the plan 42 L0 control (5 of 1,108 pieces).
- Display classes 12/2/7/7/7; all vertices coincident on the east edge.
- D1 decode of R was not implicated; the question is G encode vs D1 of G.

## Solution shape

### Domain: encode vs decode discrimination

- **Owns:** `triage/trim_r_parity/l0_degen/`.
- **Contract:**
  1. Re-extract the 5 items' encoded bytes from live tip oracle `aeae426c` (draft cited `4e6b0de7`) (frame pread) and decode with the production D1 and with an independent bit-level reader.
  2. Compare to the E2 input geometry (trim dump / spool) for the same `(level, kind, row)` keys.
  3. Verdicts:
     - **D1 artefact:** encoded bytes are a normal in-rect chain; only D1 places them at x=4096. Fix or quarantine D1; oracle unchanged if encode is clean.
     - **Encoder defect:** encoded deltas produce the edge collapse. Root-cause the write path (clip, delta, attribute). Confined fix + successor oracle, or proven cause if it is an accepted edge-clip singularity with no R counterpart needed.
  4. Search AU for other all-vertices-on-parent-edge links (bounded scan). Count and sample committed; each class follows the same verdict rule.
- **Non-goals:** redesigning division.

## Decisions

1. Plan number 53. Master direct. Two phases (discriminate; fix or proven cause + census).
2. Light unless the census finds a large class.

## Assumption ledger

### Assumption 1

- **Question:** Are the 5 an isolated clip singularity?
- **Answer chosen:** Possible. The AU census must say.
- **If wrong:** promote to a broader encoder bug with its own residual children.

## Open questions

None blocking.

## Phases

### Phase 1: Encode vs decode

- **Outcome:** one named verdict for the 5, with byte witnesses.
- **Surfaces:** `l0_degen/`, small tests.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Fix or proven cause + AU census

- **Outcome:** R-G9-3-d discharged; census counts committed; successor oracle only if encode changes.
- **Surfaces:** `_e2.c` / D1 as required; residuals; oracle_chain if needed.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master tip at plan-53 start `f3b1aa9` (DESIGN draft cited `607e5b6`). Plan 42 L160–170 region; `trim_witness.json`; residuals R-G9-3-d.
- Box draft only.
