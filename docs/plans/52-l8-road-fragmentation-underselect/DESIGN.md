---
design_id:
---

# L8 (7,4): road fragmentation and under-selection vs R (R-G9-3-b, R-G9-3-c)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close R-G9-3-b and R-G9-3-c together: both are L8 parent (7,4) SE Queensland road selection / tiling defects left by plan 42.

Oracle `4e6b0de7…`. flock + wrapper, `-j4`. Master direct. Never relabel. No plan 04 P4–6. No 3-90. No waivers.

## Problem

Plan 42 on L8 (7,4):

| | G | R |
| --- | ---: | ---: |
| Topology | 4×4 (6 non-empty) | 2×2 |
| Road pieces / links in parent | 2,979 pieces | 929 links |
| Sub (3,0) before shrink | 2,417 pieces | 750 links in R's whole SE quadrant |
| Dropped by shrink | 308 (all dc 12; 295 sub-quantum; within 0.768 raw of kept roads; 2.0% of length) | — |
| Outside (3,0): leaves 2 / 11 / 14 raw | 225 / 0 / 0 | 4,786 / 1,251 / 3,336 |
| Display class | all dc 12 | 801 dc-10 links in parent; G has **no dc 10** |

- **R-G9-3-b:** the 308 drops lose no geometry at R's quantum; the count is G fragmentation (short spool records touching kept roads). Cause of the short records is not established.
- **R-G9-3-c:** outside (3,0), G under-selects against R by a large raw margin and never emits dc 10.

## Solution shape

### Domain: fragmentation root cause (R-G9-3-b)

- **Owns:** `triage/trim_r_parity/l8_frag/`.
- **Contract:**
  1. For the 308 dropped and a sample of kept sub-quantum pieces: spool parent way/relation, clip stage, and why the piece is 2 vertices / short.
  2. Named mechanism(s): over-split at cell/sub-cell boundaries; duplicate emission of one way; extract simplification; other.
  3. Proven-cause if the short records are an inevitable clip artefact at this topology **and** union coverage equals R at 1-raw quantum. Fix if they are duplicate or avoidable splits.
- **Non-goals:** changing the shrink tier's priority sort alone.

### Domain: under-selection and dc 10 (R-G9-3-c)

- **Owns:** the same folder's `underselect/` tables plus any extract/encoder mapping change.
- **Contract:**
  1. Map R's 801 dc-10 links to OSM / spool candidates (class mapping table).
  2. Show whether G's pipeline drops them at extract tags, at display-class assignment, or at E2 selection.
  3. For leaves 2/11/14: volume table G vs R before any trim.
  4. Fix confined to the named stage, with a successor oracle, **or** proven cause that G's class set is a deliberate subset (cited rule) and the volume gap is that rule's residual.
- **Non-goals:** forcing G's 4×4 topology to R's 2×2.

### Domain: joint gates

- After any fix: L8 (7,4) window/level build; trim dump shows dropped count and class mix; K1 road kinds; suite; close_gates; successor oracle if bytes change. Diff confined and explained.
- R-quantum coverage: union of G road pieces within 1 parent-raw of R's links covers ≥ stated % of R length in the parent (threshold committed before measuring).

## Decisions

1. Plan number 52. Master direct. Three phases: frag cause; underselect/dc10 cause; fix or proven-cause close for both children.
2. The 308 drops stay "no geometry lost at R quantum" unless Phase 1 refutes that.

## Assumption ledger

### Assumption 1

- **Question:** Are fragmentation and dc-10 absence independent?
- **Answer chosen:** Likely related (both are L8 road selection), but proven separately so a fix for one cannot silently claim the other.
- **If wrong:** one mechanism explains both; Phase 3 records the join.

## Open questions

1. Whether dc 10 in R corresponds to a tag class we intentionally collapse to 12. Needs the mapping table before any product call.

## Phases

### Phase 1: Fragmentation mechanism

- **Outcome:** named cause for the short records; R-G9-3-b ready for fix or proven-cause.
- **Surfaces:** `l8_frag/`, tests as needed.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Under-selection and dc 10

- **Outcome:** stage-of-loss named; mapping table committed; R-G9-3-c ready for fix or proven-cause.
- **Surfaces:** `l8_frag/underselect/`.
- **Approach:** known. **Depends on:** none (parallel with P1). **Refine:** skipped.

### Phase 3: Fix or proven cause for both

- **Outcome:** both children discharged; successor oracle if needed; residuals updated.
- **Surfaces:** encoder/extract as required; oracle_chain; residuals.
- **Approach:** known. **Depends on:** Phases 1–2. **Refine:** skipped.

## Provenance

- Master `607e5b6`. Plan 42; `trim_r_parity/{trim_witness.json,trim_l8_7_4.tsv.gz}`; residuals R-G9-3-b/c.
- Box draft only.
