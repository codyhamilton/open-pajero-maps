# Review of 3-07 attempt 2 (Sonnet 5.5, independent)

Verdict: ACCEPT as evidence for the two rules (R01 checker, S02 spool) and as a blocked/partial table. No cause forced; 5,939,509 rows stay unattributed, as Sol reports. Nothing substantive to dispute.

## Checks
1. rules_bg.json: valid classify schema, ids R01/S02 unique, causes legal. Reran classify under flock with the two triage rules plus Sol's three OUT_ catch-alls (`output/scratch-3-07/review/rules_all_review.json`): exit 1 PARTITION FAIL as expected; background assigned 920,773 / unclassified 517,785; background_boundary 11,127,845 / 5,421,724. Per-level (R01 L0 918,297, L2 2,476; S02 11,127,845; unclassified 513,492 / 4,293 / 5,301,667 / 116,053 / 4,004) all match. `enumerate` output byte-identical to Sol's (R01 49,042 groups; S02 145,960).
2. Witness rerun on my own sample (`review/witness_rev.py`, Sol's script with seed 20261002, 50 groups, shared all-shape caches): R01 50/50 VALID (even-odd and winding agree, no disagreement, dump flag agrees; min same-type outline distance 1.08 raw). S02 50/50 INVALID (even-odd/winding outside same type; min same-type distance 64.02 raw; dump flag agrees). Outputs: `review/witness_R01.*`, `review/witness_S02.*`.
3. causes_bg.md arithmetic: per-kind sums 920,773+517,785 = 1,438,558 and 11,127,845+5,421,724 = 16,549,569; classified 12,048,618, remaining 5,939,509; level splits OK; top-30 table (30 rows) share/cumulative recomputed: 15,921,626 / 17,988,127 = 88.51186%, all rows OK; sentinel rows sum 15,913,571 = 88.46708% (the 94.5% correction is present and correct); sentinel table totals and sample sums (525/1000, 1,032, 2,032) match `sentinel_results.json`. Counterfactuals match cf_291/outcome.json (boundary 829 to 589, background 69 to 69, original piece gone, 9/9 G frames) and cf_short_ring (32 to 0, 255 to 0, interior_cover 1 to 0, 9/9 frames). onb 31,416/31,416 and H4 grid (3,969 points, 0 disagreements) match logs. H1-H7 table makes no claim beyond evidence.
4. No cause forced without a witness: R01 and S02 each have a witness; build rows 0.

## Observations (not edited, no cause changes)
- S02 labels all 11.1 M sentinel type-291 L0 rows `spool`. Support is the 200-group witness/producer match plus one counterfactual window that removed only 240 of 829 boundary failures (29%); the remainder is attributed by the sample producer match, not by counterfactual. Orchestrator should treat the pin step (Amendment 3 of attempt 3) as the real test.
- cf_short_ring after-state shows completeness failing 0 to 1, not mentioned in causes_bg.md (non-bg kind, likely window edge effect).
- Sampled S02 points are inside a different-type polygon (eo_any True) in the producer sample; consistent with spool but not discussed.

## Edits made
- causes_bg.md item 6 under Contradictions: "review outstanding" replaced with a pointer to this file. No other changes.

Seed/sample: 20261002; R01 50 groups (stride 980, offset 969), S02 50 groups (stride 2919, offset 2889). Heavy jobs ran serially under the lock; no processes left running.
