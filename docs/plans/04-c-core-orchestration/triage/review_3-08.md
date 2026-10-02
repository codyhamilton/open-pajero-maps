# Review of unit 3-08 draft (independent)

Verdict: ACCEPT as a partial, honestly blocked table. No forced causes, no loosened tolerance (NEAR = 0.500001, as 3-07). 191 rows stay unattributed.

## Checks
1. Native `classify` (rules_bg.json + rules_other.json, scratch dump_other): exit 1 (PARTITION FAIL by design); partition.txt byte-identical to Sol's.
2. Arithmetic: interior_cover 824 = 821 + 3; completeness 752 = 495 + 13 + 56 + 188; name_anchor 1 = 1. All-five: checker 921,268; build 13; spool 1,939,931; unattributed 15,128,492; total 17,989,704. All reproduced.
3. Reproducibility: rules_other.json does NOT run on the repo-reproducible dump (unknown column other_mechanism, exit 2). It needs scratch dump_other = 3-03 dump with byte 145 filled from side_*.npy + symlinks to scratch-3-07/dump_attempt3 (itself scratch-extended, byte 144). Neither is in docs/provenance.md: BOM entry needed before commit. Mechanism-code predicates are row lists (allowed by the side-table amendment, not falsifiable from dump columns).
4. Pins: 758 rings (O02), 6 rings (O04), 1 name (O03); 26,650 groups = 25,772 + 821 + 1 + 56. pinned_candidates.tsv (100 S02 rows + total line) is not a pinned list in the design's sense; the real lists are git-ignored enumerate_*.tsv / pins_*.tsv; S02 is partial at 10,001 rings.
5. Witnesses (seed 20261002, ~30/rule, own code): O01 30/30 consistent; O05 30/30 consistent (areas tiny; one ring nonzero at mult 8/64 but C clip emits 0 bytes); O02 30/30 (centre outside all same-type polygons, source ring has proper crossing); O04 30/30.
6. Build finding: raw bytes of G confirm cell (1795,647) declares 20, holds 4,116 = 4,096 + 20 records tiling the element; 9/9 wrapped cells hold exactly 4,096 hidden. `enc_bg` (_cenc.c:789) masks count to 12 bits with no overflow error (the name encoder errors, line 872). Agree with `build`.
7. name_anchor: Ile Saint-Paul lon 77.519 -> raw ix -399 -> clamped to 0 by assign_to_parcel -> to_xy clamp to 90.0. Plausible; encoder clamp is faithful (documented mirror of _clamp_coord); the extractor should have dropped it: spool.

## Disagreements / caveats
- The count-wrap counterfactual (4,116 -> 4,084) is a source-side edit; it shows count pressure and target restoration but does not by itself discriminate build from spool. Build rests on code reading + byte evidence.
- O05 validity partly leans on the C clip's own empty output; O01/O05 are judgement calls (degenerate/sub-pixel rings could be argued spool/build).
- Sister 12-bit masks at _cenc.c:222 and :459 are unmeasured. Element ceiling 131,070 bytes; worst case cell (1681,729) 128,130.
- Sol did not run a review itself; process deviations disclosed (one unlocked metadata scan).

## Edits made
Missing-space typos in cause_table.md and rules_other.json only (rules_other.json re-parsed valid). pinned_candidates.tsv untouched. No causes, predicates, numbers or code changed.

## Heavy runs
classify under flock, outputs in output/scratch-3-08/review/. None left running. No commit/push.
