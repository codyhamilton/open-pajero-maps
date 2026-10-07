---
design_id:
---

# L0 (1755,591)(2,1): type-288 over-emission driving road trim to zero (R-G9-3-a)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close R-G9-3-a. Plan 42 proved the 207 roads and 227 backgrounds are dropped by `dv_shrink` under a frame filled with type-288 content that R does not carry. The trim itself is explained; the upstream cause (why G emits 6,628 type-288 in the sub-cell / 8,777 in the parent while R has 0) and the fixed kind-order policy (road → background → name) are not.

Oracle `4e6b0de7…`. Heavy work only under flock + wrapper, `-j4`. Master direct. Never relabel. No plan 04 Phases 4–6. No 3-90 brief. No waivers.

## Problem

| Fact (plan 42 witness) | Value |
| --- | --- |
| Parent | L0 (1755,591), Melbourne / Tullamarine |
| R topology | undivided, 1 leaf, 179 road links, **0 type-288** backgrounds |
| G topology | 4×4, sub (2,1) frame 131,064 B |
| G type-288 in sub / parent | 6,628 / 8,777 |
| After shrink | roads 0 (all 207 dropped); backgrounds −227 (all type 288) |
| R road length in (2,1) | 3,695 raw (~2.3 km) — real volume loss |
| Per-item R presence | not decidable (OSM↔vendor offset; control q50 31 raw) |

Two candidate root causes, both named by plan 42, neither R-evidenced:

1. **Upstream emission:** G over-emits type-288 (marine / protected-area fill class used on land here) relative to R.
2. **Kind-order policy:** when the per-kind binary search still overflows, the fallback always cuts road before background.

## Solution shape

### Domain: type-288 census and provenance

- **Owns:** `triage/trim_r_parity/l0_288/` — per-record provenance for every type-288 item in parent (1755,591): spool source cell, relation/way id if known, whether it is an overlap share-in, bbox vs land.
- **Contract:**
  1. Classify each of the 8,777 parent items into: land-local / marine-share-in / encoder-synthesised / unknown.
  2. Compare the land-local set to R's background type census in the same parent (R has 21 backgrounds, 0×288).
  3. Name the dominant mechanism that accounts for ≥95% of the byte pressure in sub (2,1).
- **Non-goals:** changing emission in this domain.

### Domain: confined fix or proven cause

- **Owns:** either a confined encoder/extract change, or a proven-cause close with no code change.
- **Contract — fix path (preferred if the census shows a clear over-emission bug):**
  1. Change confined to the mechanism (for example: stop sharing marine 288 into this land parent; or correct a wrong code mapping).
  2. Successor oracle if bytes change. Diff confined to cells whose 288 set changes; every changed cell explained.
  3. After the fix, sub (2,1) must keep enough road that G road length in the rect is within a stated band of R's 3,695 raw **or** the remaining gap has a named residual. Band and method committed before measuring.
  4. K1 0 on affected kinds; suite; `close_gates.py`; AU/Perth sha recorded.
- **Contract — proven-cause path (if emission matches a deliberate, R-divergent product rule):**
  1. Document the rule and show R's 0×288 and G's 8,777 under it.
  2. Kind-order policy: either leave it (with the road loss as a named accepted residual under that rule) or propose a policy change as a **separate** child with Cody's explicit product call. Design does not silently flip road↔background priority.
  3. R-G9-3-a becomes proven-cause with the rule citation; volume loss stays a named residual if policy is unchanged.
- **Non-goals:** waiving the standing rule; claiming per-item R identity at L0.

## Decisions

1. Plan number 51. Master direct. Two phases (census; fix or proven cause).
2. Kind-order change needs Cody if the census does not yield an emission bug.
3. May promote R-G9-3-a to `blocks-phase3` once a fix lands that changes the oracle; until then it stays maps-parity-carried.

## Assumption ledger

### Assumption 1

- **Question:** Is type 288 in this parent mostly spill from marine relations?
- **Answer chosen:** Likely, given plan 30's 288-template marine parks and the overlap pass. The census must prove it.
- **If wrong:** the mechanism is a land mapping or encoder fill rule; the fix target moves.

## Open questions

1. Cody: if the only remaining lever is kind-order (road before background), do you want roads preferred when R has roads and 0×288?

## Phases

### Phase 1: Type-288 provenance census

- **Outcome:** committed classification of the 8,777 items; dominant mechanism named; kind-order pressure quantified (bytes freed if 288 were absent).
- **Surfaces:** `triage/trim_r_parity/l0_288/`, trim_witness extension.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Confined fix or proven cause

- **Outcome:** R-G9-3-a discharged as fixed (successor oracle) or proven-cause (rule cited); residuals updated; any policy question escalated to Cody without a waiver.
- **Surfaces:** encoder/extract as needed; oracle_chain; residuals.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `607e5b6`. Plan 42 record; `trim_r_parity/{trim_witness.json,trim_l0_1755_591.tsv.gz,instr_e2.patch}`; `residuals.tsv` R-G9-3-a.
- Box draft only.
