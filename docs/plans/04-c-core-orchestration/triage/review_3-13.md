# Unit 3-13 independent review

**Verdict: ACCEPT-WITH-CONDITIONS.** I found no high-severity defects. The build-vs-spool reclassification of S02–S05 is supported. Three claims in the report and rules overstate what the evidence shows (items 1, 2 and 3 below).

**Reviewer identity.** I am the model claude-sonnet-5-5, answering this prompt directly. This is not an availability probe, and nothing from the author's earlier timed-out `review/` attempts was used. The preexisting `review/mine/r1-r3.py` scripts were not used as evidence either.

**What I wrote.** Only my own scripts and logs, under `output/scratch-3-13/review/s55/` (t1–t12). I made no builds, dumps or heavy jobs, no commits, and no changes to code, rules or reports.

## What I verified independently

- **Exact arithmetic.** I wrote a separate all-pairs exact-Fraction slab reference. It matched `exact.area_compare` on 300/300 random self-crossing, multi-ring, rect-clipped integer cases. It checked source area, disc area and symmetric difference, so it also confirms per-ring even-odd with OR across rings.
- **Per-ring semantics.** The K1 header says "crossings paired per shape". The oracle's per-ring even-odd union is consistent with that.
- **Decomposition preserves the source region.**
  - `split.decompose` had zero symmetric difference against the original ring on 250 random integer rings (769 faces), with faces interior-disjoint.
  - The same held for 43 of the 52 real repaired rings (those with ≤60 vertices), on exact rationals of the original doubles. Face counts matched `changes.json`.
  - The closing chord is retained.
- **Original-outline tolerance, independent of the integer lattice.** I took 88 witness groups from my own seed (55055). Strata were all 22, with the smallest-area and random macro groups.
  - I recomputed the failing vertex against the original doubles and used my own source selection.
  - All 88 vertices are outside the original-double union.
  - My own L∞ distances matched the author's. The three cases with distance <3 raw were 0.534, 1.289 and 1.063.
  - Minimum distance over all 5905 groups is 0.5099, so the margin against 0.5 holds.
  - The invariance argument is sound: a ≤0.5-per-coordinate vertex move cannot cross a vertex that is >0.5 from the outline.
- **Geometry-preserving counterfactual.** I rescaled the sources by 1024 (rounding error ≤1/2048 raw) and re-ran `area_compare` on about 45 picks. Every group is still non-equal. Large areas agree with the integer-lattice result.
- **Cover class change.** I independently Monte-Carlo'd the three S05 cells on the original doubles. Covered area was 4.83M, 0 and 0.92M raw² against the author's 4.85M, 0 and 0.91M, so the full-frame covers are false. The window repairs clear 1→0 in each. The cover oracle uses area only, but the excesses are 11.9M–16.8M raw², far beyond rounding.
- **S02 class change.** There is own evidence from 300 groups sampled uniformly from the 25,772-group population. All 300 are beyond tolerance, with a minimum distance of 64.7 raw. The 34-ring L0/291 window clears the boundary rows (829→0).
- **CF windows and gates.**
  - All 9 original-build byte gates pass: 9/9, 1/1, 9/9, 1/1, 1/1, 1/1 and three 1/1.
  - `cf_summary.json` counts match the report table.
  - Sources changed: 41 + 11 = 52.
  - The L0/291 window's 7 remaining fill rows are all type 288 with `in_eo_same` = 1.
- **Classification arithmetic.**
  - 517,648 + 16,541,304 + 824 + 56 + 1 = 17,059,833.
  - Build 17,058,955 and spool 878.
  - Totals 921,281 + 17,058,955 + 878 + 9,064 = 17,990,178.
  - Unattributed 137 + 8,739 + 188 = 9,064.
  - Per-kind manifests reconcile.
- **Rules.** `rules_bg.json` differs from HEAD only in `cause` and `note` for S02–S05. IDs, predicates and order are unchanged, and R01 is untouched.
- **Matched pairs.** Table sums reconcile (155/182, 147/185 = 79.46%, 154/185). The predicate is correctly reported as failed.
- **Corrected evidence.** `exact.py` was last modified at 23:34 and the final oracle finished at 23:54. The pre-fix results differ in 232 area values and 1 vertex flag, and are archived and not used.

## Findings

### Medium

1. **The `witness` field is not tolerance-robust.**
   - In a random 127-group check, 19 witnesses (15%) disagree with original-double even-odd: source and disc both inside or both outside.
   - All 19 lie within 0.0–0.45 raw of an outline, including macro-error groups. They are first-differing-slab rounding slivers.
   - The report's statement that every group has "rational interior witness" evidence is therefore misleading.
   - The headline witness (`(123989/2,71680)`, key 6/15/17/288) does verify on the doubles.
   - **Condition:** drop or caveat the per-group witness claim. The robust evidence is the failing vertex plus original-outline distance.

2. **Counts and area claims are overstated.**
   - "5905 regions differ" is 5,905 vertex tests but only 5,399 distinct keys and 5,227 distinct (leaf, type) area comparisons. Sentinel True/False and multiple shapes in one leaf repeat the same result.
   - 1,129 groups (19%) have no macro-area error. For those, integer-lattice area is not a tolerance-robust witness: at 1/1024 resolution, small discrepancies move by up to about 4× (21→83, 471→1978, 735→1162 raw²).
   - They are still nonzero, and their vertex evidence stands, so the conclusion holds. For example, group 3417 has a vertex 72.9 raw from the outline but only about 83 raw² of region difference.
   - **Condition:** state that small-area groups rest on vertex and outline distance, not on area.

3. **R01 is not shown to be exclusive of the build defect.**
   - In the L0/291 window, the 31 type-291 `in_eo_same` = 1 fill rows (what R01 labels checker) vanish after repair.
   - The report discloses this and declines to credit it as build, but R01's note and the report headline still present R01 as checker for all 920,786 rows.
   - **Condition:** add an explicit caveat to R01 or the report that R01 may partly overlap the build defect, and that this was not tested beyond this window.

4. **The sample covers only flagged groups, and the repair evidence is thin.**
   - 5,899 of 5,905 sampled groups have `residual_crossing_verified` = 1, so the "independent of the crossing flag" sample effectively validates flagged groups. The 9,064 unattributed rows are correctly left alone.
   - The CF repair is 9 windows and 52 of about 71k rings. Four windows are a single frame with one ring repaired, chosen by minimum candidate count. Sentinel substrata are not separately repaired.
   - Extrapolating to 17.06M rows rests on oracle uniformity (about 100% wrong per stratum) plus one clean window per stratum.
   - **Condition:** word it as a stratified-sample basis, not an exhaustive repair.

5. **The near-tail verdict is partly argument by exclusion.**
   - The tail check re-measures distance and `mult_const` = 1 on 1,666 rows. It does no region test on tail vertices.
   - The C code reviewed supports the exclusion: `emit_piece` densifies in float and rounds once, so the plain rounding bound is ≤0.5.
   - I added independent support. All 54 oracle groups whose first failing vertex is ≤1.0 raw from the outline have symdiff ≥102k raw² and vertices outside the source.
   - **Condition:** call this group-level support, not a per-row proof for all 15,002 rows.

6. **Condition C and the mechanism text are hypothesis.**
   - The `bg_shape` account (global orientation, greedy successor, used-successor break) comes from reading the code and is untested.
   - The separator fails at 79%, and the 154/185 remeasure is on the same cohort. The train/heldout split is vacuous because nothing is fitted.
   - This is disclosed. Keep the wording as hypothesis in the report and rule notes.

### Low

7. **Report status is stale.** The report's status line and "Mandatory review outcome" section still say blocked/unavailable. They must be updated with this outcome and the above conditions.
8. **Concurrent edits.**
   - `cf.py` was modified (23:24:59) after `cf_summary.json` was written (23:08), probably for the cover and resume logic. I confirmed the outcome files are original build artifacts, not that the script is unchanged.
   - The working tree also has uncommitted edits to `parser/tools/quantisation_roundtrip.py` and `parser/tests/test_quantisation_roundtrip.py`. The diff I read is dump-finalize I/O only. These should be excluded from any commit for this unit.
9. **Source reuse in pairs.** The 734 pair rows use about 702 unique sources, so some sources repeat across leaves and the pairs are not fully independent.

## Incomplete evidence

I did not re-run CF builds, which the brief forbids, so CF counts rest on artifacts and the byte-gate files. I decomposition-checked only 43 of the 52 real repaired rings (the 9 larger ones are untested). The row-level extrapolation to 17.06M rows was not independently measured and cannot be without a full-disc dump.

## Decision

Accept, conditional on items 1–3 and 7 being corrected in the report and rule notes. Items 4–6 should be reflected as wording or limitations. The reclassification of S02–S05 to build, and the unchanged remainder of 9,064 unattributed rows with the expected PARTITION FAIL, are supported by my independent checks.
