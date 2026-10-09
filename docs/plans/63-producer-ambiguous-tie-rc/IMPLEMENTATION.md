# Plan 63 — IMPLEMENTATION (checkpoint)

The draft was re-copied fresh from the box on 2026-10-09 12:55 AEST.
- Base: `origin/master` `b889c2e` (plan 62 close-out).
- Checkout: `open-pajero-maps-14-completeness` (existing; holds `.venv-rp`).
- Seat: Codex.
- Out of scope: no oracle change, no nearest-ring choice, no waivers.

## Phase 1: tie census (done)

`historical_bg/p7_producer_tie/tie_census.py` builds the census; its helpers are in `parser/tools/producer_tie.py`, tested by `parser/tests/test_producer_tie.py`.
- **Inputs:** all `producer_ambiguous` rows of `p6_producer/verdicts.tsv.gz` (`ca4a555a…`).
- **Producer side:** the plan-46 candidate set (Moore 8 ∪ FarHomes, `leaf_clip_geometry`, same type, piecewise hit), clipped with `cenc_33006aa` on `ref_33006aa` (013586b5).
- **Decide side:** per candidate, the unchanged phase-23 limb (`cenc_d35b565` clip, byte or owner-exclusive vertex on `ref_d35b565` = 4ed9cd80).

Output `p7_producer_tie/ties_all.json` (sha256 `8ce2237e…`):
- Run twice under the wrapper: byte-identical (TIES_IDENTICAL).
- Peak: max RSS 3.72 GiB, memory.peak 0.63 GiB, 19 s per run. Recorded in `56/ledger/producer_tie_plan63.json` plus a SUMMARY row.

**Result:**
- **Coverage:** 98 groups, 4,612 rows, 47 leaves.
  - By kind: background 18, background_boundary 4,594.
  - Scope delta: 6 groups, 516 rows.
  - Everything reconciles.
- **Hits:** every group has exactly **2** same-type hits.
- **Duplicates:** every ambiguous shape belongs to a full-record duplicate class of size 2 on 013586b5. The pairs are byte-identical records, which confirms Problem item 3 on full bytes.
- **T1: 54 groups / 3,288 rows.** Identical clip blobs and identical decide verdict.
  - Plan 46's (1753,1158) T1 is reproduced, with lowest key (1755,1157,1).
- **T2: 44 groups / 1,324 rows.** The clip blobs differ.
  - This includes (1481,1288) shapes 0/2 and (1754,1158) shapes 1/3. Their piece maps match `ties.json`.
- **T0: 0.**
- **Decide verdict: `build:eo_bg_stitch` for all 196 (group, candidate) pairs.** For every T2 group, the decide outcome does not depend on which candidate is the producer. Even so, the design requires a proven producer per copy for T2, which Phase 2 provides.

### scratch_receipt — Phase 1 (2026-10-09 ~13:05 AEST)
1. `du -sb output/scratch-63`: 244,280 B before; **gone** after.
   - Deleted: `runs/` = `p1.sh`, `p1.log`, the wrapper json/time, and `ties_all_b.json`. The cmp was recorded first, and the peak was copied to the ledger.
2. **Kept, all committed:** `p7_producer_tie/ties_all.json` (`8ce2237e…`), `tie_census.py`, `producer_tie.py` and its test, the ledger row. No `keep/`.
3. **Worktrees:** none added.
4. **Temp dirs and scopes:** the `/tmp/p63_tie_*` probe dirs were removed by atexit (0 remain). 0 `maps-heavy` scopes.
5. **Disk:** `df -h /home`: 11 G free (97 %).
