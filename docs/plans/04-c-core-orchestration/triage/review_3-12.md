VERDICT: ACCEPT-WITH-CONDITIONS

Reviewer: independent (did not author 3-12). Read-only review; no repo edits other than this file. Scripts and picks were kept in the session scratchpad.

## Disposition by rule

| Rule | Rows | Disposition |
| --- | --- | --- |
| S03 (background, residual_crossing_verified==1) | 517,648 | STANDS as spool, provisional (condition A) |
| S04 (background_boundary, same predicate) | 14,602,251 | STANDS as spool for the L0 type 288 and L0 type 291 strata. DEMOTE to unattributed the strata with no counterfactual (condition A): L0 289/578, L2 289, L6 288, unless a counterfactual is supplied |
| S05 (completeness cover) | 3 | STANDS (trivial) |
| Remainder 9,064 (137 bg, 8,739 boundary, 188 completeness) | 9,064 | STAYS unattributed; PARTITION stays FAIL (honest) |

The per-stratum row split of the demotable strata must be produced by Sol from the dump (group by level, code); I did not compute exact row totals per stratum, only group-level samples. Until the counterfactual lands, report those rows as "spool-probable, unconfirmed", not as spool.

## Findings

1. [medium] Counts reproduce exactly. An independent hash join on the full key (level, ix, iy, code, p0..p6, shape) against the side table gives 517,648 rows / 30,547 groups (S03), 14,602,251 / 216,319 (S04), 3 / 3 (S05), identical to the flag column. Status-1 rows taken first by R01/S02 (343,217 fill, 1,746,206 boundary) are correctly ordered; no failures are hidden. Among the new rows in_eo_same = 0, in_wn_same = 0, d_src <= 0.500001 = 0.

2. [high] The mechanism is named and partly evidenced, but the counterfactual coverage is far too thin for a 15.1M-row claim. Only 2 source rings of 70,999 were repaired (about 315 of 15.1M rows, about 0.002%). Type 288: window failures go to 0. Type 291: only 29 new rows removed; 589 window failures remain and are not explained. No counterfactual at all exists for L0 289/578, L2 289, L6 288. A one-coordinate repair does not generalise (median 3 crossings per ring, up to 39). Cody's rule requires witness AND counterfactual per attribution; the counterfactual half is met only for L0 288. No complete-repair window run (repair every status-1 source in a window, expect S03/S04 rows to go to 0) was done.

3. [medium] Predicate-independence (item 2): my own implementation (slab Chebyshev test at 0.500001 and 64 raw, even-odd test, distance to claimed producer ring), fresh seed 424242, one random vertex per group, 1,029 vertices (497 fill, 532 boundary): 0 valid in every stratum, 0 even-odd mismatches vs the dump. This confirms invalidity independently of the predicate. It does not discriminate cause, since all sampled vertices were already known failing; the discriminating evidence is the counterfactual (finding 2).

4. [high] Specificity of the predicate (item 5): not a forced catch-all. Ring property P (explicit closure, closing edge longest, proper nonadjacent crossing) holds for 53% of L0 type 291 rings, yet about 99.94% of failing groups have P producers while non-P rings (47% of type 291) yield about 180 failing groups. So P is strongly necessary. It is NOT sufficient: P rings fail at 4% to 73% depending on ring size, and why only some fail is unexplained. Attribution is group-level (the producer), not row-level (the vertex).

5. [high] Root cause is ambiguous between spool defect and build defect. The closing edge is the longest in 99.96% of L0 type 291 rings, consistent with an open polyline closed by a chord (an extractor/spool defect). But the failing vertices are clip connectors on leaf edges (example: cell 1589,1170 path 597, shapes 8 and 15, whose rows trace a frame at 0/4096 along the leaf edges). Many failing vertices lie outside the claimed producer's bbox: inside bbox +/-1 only 52/84 and 60/173 (L0 288/291 sentinel boundary), 21/48 (578), 9/34 (L2 289), 0/27 (L6 288), at 2,000-4,000 raw from the producer ring. So the effective locus is the encoder's clip semantics applied to a self-crossing ring. Whether that is "faithful build of a defective shape" (spool, per brief) or a build robustness gap is a design call that must be stated in causes_residual.md; the follow-up fix unit scoping depends on it (condition C).

6. [medium] Item 6 reconciliation: no contradiction with the earlier "sentinel groups are ~90% farther than 64 raw from any outline" finding. The new rows are leaf-edge connector vertices, far from outlines and outside same-type interiors, which is exactly that population. Record this in the report.

7. [medium] Near-threshold tail untested: 2,184 fill and 12,818 boundary new rows have d_src in (0.5, 1.0) raw. These could be a tolerance/quantisation mechanism swept into a group-level spool attribution. Test or demote (condition B).

8. [medium] Honesty of the remainder (item 4): 180 background-family groups break into 98 ambiguous producer, 45 non-longest crossing, 37 no crossing. The reported 9,064 and the PARTITION FAIL are honest. Next predicates are reasonable (disambiguate 98 producers by geometry; examine the 45 non-longest cases), but should not be forced into spool.

9. [low] Amendment 4 vs K1: K1/Python also accept boundary points inside a same-type polygon, while Amendment 4 does not. Sol disclosed it; confirm the counts are by K1 semantics (my check agrees with the dump flags), and note it in the report.

10. [medium] Provenance (item 7): docs/provenance.md documents inputs, side tables, extend.py (byte 146), witnesses and reproduce commands, and large evidence is gitignored. The result depends on uncommitted side tables and dump_ext under output/scratch-3-12/; they must be reproducible from the listed commands. I did not rerun them (no heavy jobs).

11. [low] Process: Sol's own mandatory Sonnet review never ran (timeouts), so this is the first independent review. provenance.md says the review is outstanding; update it to reference this file.

## Conditions

A. Per-stratum complete-repair window counterfactuals (repair all status-1 sources in a window, expect S03/S04 rows to go to 0), covering L0 288, L0 291 (and explaining the 589 residual window failures), L0 289/578, L2 289, L6 288. Strata without one are demoted to unattributed.
B. Test or demote the near-threshold rows (d_src 0.5-1.0; 2,184 fill, 12,818 boundary).
C. State and justify the root cause (extractor chord closure vs encoder clip with self-crossing input), and explain why only some P rings fail, so the fix unit is scoped correctly.
D. Keep the 9,064 remainder unattributed and PARTITION FAIL; do not pin it as spool.
