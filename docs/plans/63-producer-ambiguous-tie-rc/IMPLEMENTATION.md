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

## Phase 2: emission provenance (in progress)

### Refine: sidecar hook point and sampler (fixed before any rule is scored)

- **Sidecar** (`p7_producer_tie/sidecar/sidecar_33006aa.patch` vs `33006aa`). It is applied in a throwaway worktree `open-pajero-maps-63-33006aa` and is gated by `KW_SIDECAR_DIR`, writing one file per pid/tid.
  - `_e2.c` `kw_e2`: `I` lines for each routed item (target cell, item j, source cell, k, cover flag) and a `C` line for each receiving cell (own background count). Together these map merged ordinal → source: own first, then items in E1 row order.
  - `_cenc.c` `enc_bg`: records (input background ordinal, class, records emitted) in emission order.
  - `_e2.c`: logs those entries after each whole-cell `kw__encode_rec` (`W`) and after each divided-tier `dv_probe` (`P`, sub-record j mapped to parent ordinal), plus `F` for each committed sub-frame. Every line carries an FNV-1a hash of the frame, so committed frames are tied to their probe.
  - Output-neutral by construction (logging only). Gate 1 checks this.
- **Trial** (24-cell window 0 1760 580 1768 583, which includes divided cells): 72/72 frames byte-equal to 013586b5, 3.7 s, max RSS 1.0 GiB. Single-cell windows are cheap, so the plan uses them directly.
- **Windows** (`p7_producer_tie/windows.py`):
  - 46 single-cell windows, one per affected cell.
  - Plus a sampler: 40 6×6 L0 windows anchored at the spool L0 cells with the lowest `sha256("p63-sample:{ix},{iy}")`.
  - Builds are serial, `-j4`, under the heavy wrapper.
- **Analysis** (`p7_producer_tie/provenance.py`): G1 (frames vs 013586b5 leaves) → sidecar → per-record emitter (count and unit class checked) → G2 (scan unique-byte vs sidecar, tie cells) → per-copy provenance → duplicate cases → rule table.
- **Holdout (fixed now, before scoring):**
  - Derivation = all tie-window cells, plus sample cells whose `sha256("p63-holdout:{level},{ix},{iy}")[0]` is even.
  - Holdout = sample cells where that byte is odd.
  - Scored cases are byte-identical same-type class>0 duplicate records in one leaf whose scan hits equal their distinct non-cover sidecar emitters. Other cases are counted by reason.
  - Strata (split/depth/type) are reported.
- **Rules scored:**
  - candidate key order; nearest home; spool order in home; global spool order;
  - block order (L0: block 32×64 cells, blockset 8×4 blocks);
  - contiguous per-producer block emission (enc_bg class-major, then merged ordinal = own first, then routed by source (iy,ix), k), the one with a code path;
  - disc record order of the distinguishing piece; first emitter; divided-leaf keep order (depth 2 only).

### Phase 2 results (2026-10-09 ~13:45 AEST)

**Runs, in order:**
- **Window builds:** v1 = 86 windows (46 tie cells plus 40 6×6 samples), 79 s. v2 = 300 stratified single-cell windows, 278 s. 386 windows in total (`p7_producer_tie/windows.json`).
- **Duplicate census of 013586b5** (`dup_census.py`, 104 s): 3,954,156 leaves. 336,329 leaves hold byte-identical same-type class>0 duplicates (L0 336,325; L2 4), with 338,760 classes and 445,137 extra copies. By type: L0/288 = 338,220; 291 = 373; 321 = 110; the rest ≤ 17. Output: `dup_census_013586b5.{json,tsv.gz}`. Phase 3 reuses this for the parity fact.
- **`provenance.py`**, run twice (B and B2); outputs byte-identical:
  - `provenance.tsv.gz` `e323cccf…`
  - `rules.json` `9b76437c…`
  - `dup_cases.tsv.gz` `982269d0…`

**Gates:**
- **G1, output neutrality:** 2,085/2,085 window frames over 1,770 analysed cells are byte-equal to a 013586b5 leaf of the same cell. Every disc leaf of those cells is matched: 0 mismatches, 0 unmatched leaves. Sidecar parse: 2,085/2,085 frames; the hash, record count and unit class all agree; 0 failures.
- **G2, sidecar control (46 tie cells):** 14,211 class>0 records have a unique scan producer.
  - 14,208 match the sidecar emitter exactly.
  - 3 match the same source shape emitted in its **interior-cover form** (E1 kind 1): (1541,801)[1061] shape 1 ← (1541,800,0), and (1753,1158)[217] / (1754,1158)[218] shape 0 ← (1732,1144,0).
  - 0 disagreements. 116 records have 2 hits (the ties).
- **Per-copy provenance:** all 98 groups (T1 54, T2 44) have both copies named by the sidecar. In every group:
  - both emitters are among the group's 2 candidates;
  - the emitters are distinct: one candidate emits one copy (Assumption 3 confirmed);
  - emitters are 30 own, 166 routed, 0 cover.
  - Example: (1481,1288)[265] copy 0 ← (1485,1280,0), copy 2 ← (1486,1280,0). (1753,1158)/(1754,1158): the lower copy ← (1755,1157,1), the higher copy ← (1755,1157,2).
- **Rules** (scored cases = byte-identical same-type duplicate classes whose scan hits equal their distinct sidecar emitters; 1,083/1,083 cases qualify):

  | Rule | Derivation | Holdout | Accepted? |
  |---|---|---|---|
  | **contiguous per-producer block emission** | **537/537** | **546/546** | **accepted (code path cited)** |
  | divided-leaf keep order (same key, depth 2 only) | 183/183 | 265/265 | accepted (code path cited) |
  | global spool order | 528/537 | 543/546 | rejected |
  | block order | 476/537 | 495/546 | rejected |
  | nearest home | 384/537 | 395/546 | rejected |
  | candidate key order | 366/537 | 370/546 | rejected |
  | spool order in home | 341/537 | 322/546 | rejected |
  | disc record order of the distinguishing piece | 35/537, abstains 502 | 15/546, abstains 531 | rejected |
  | first emitter | 0/537 | 0/546 | rejected |

  - **Accepted rule:** copies, in leaf order, go to the candidates sorted by (source class, own cell first, then source (iy, ix), then ri). This is the order of `33006aa` `_cenc.c` `enc_bg` (class-major, then merged background ordinal, with each background's `bg_shape` pieces contiguous) over `_e2.c` `kw_e2` / `e2_merge` (own backgrounds first, then E1-routed items ordered by target, source (iy, ix), shape). For divided leaves it also follows `dv_bg_cells` / `dv_probe` (ascending parent ordinal).
  - Holdout ≥ derivation (546 ≥ 537). Strata (split/depth/type/cover-vs-ring) in `rules.json`. Both splits cover d1 and d2, types 288/289/290/291/321/322/578/640, and ring and cover forms.

**Deviations (named):**
1. **Cover-form emitters.** The first analysis run (v1 windows) treated an E1 kind-1 cover item as a separate emitter. That produced 3 G2 "disagreements" (the 3 rows above) and excluded 292 cover cases. A cover item is the routed row of its source shape (E1 kind 1, same (sx, sy, k)), so emitter identity was corrected to the source shape. The 3 rows are listed in `rules.json` `gate2_cover_form`. No rule key changed.
2. **Holdout size.** v1 sampling gave holdout 2 against derivation 60, under the design's size bar. Sampler v2 was added: strata (type, depth) from the 013586b5 duplicate census, 60 cells per stratum with the lowest `sha256("p63-sample2:…")`, single-cell windows. The holdout definition (`HOLDOUT()`, fixed in `1005eed` before any scoring) and the rule list are unchanged.

### scratch_receipt — Phase 2 (2026-10-09 ~13:50 AEST)
1. **`du -sb`:**
   - `output/scratch-63`: 53,789,549 B before; **gone** after.
   - Deleted: 386 window dirs (frame dumps and sidecar logs), the A/B analysis outputs, the 013586b5 census copy, and the wrapper logs. Peaks were copied to the ledger first, and B==B2 was compared first.
   - Throwaway worktree `open-pajero-maps-63-33006aa`: 10,164,202 B before; **removed** (`git worktree remove --force`, then prune). It held only the sidecar diff and the build `.so`; the diff was byte-compared to the committed patch first (`PATCH_SAME`).
2. **Kept, all committed, all in `git ls-files`.** sha256 prefixes:
   - `provenance.tsv.gz` `e323cccf50e636c7`
   - `rules.json` `9b76437ce21d10ab`
   - `dup_cases.tsv.gz` `982269d0a7471595`
   - `dup_census_013586b5.json` `54ab9fb6280d5b96`
   - `dup_census_013586b5.tsv.gz` `5e8cdf7dc218fb40`
   - `windows.json` `9bd5856ad90b080e`
   - `sidecar/sidecar_33006aa.patch` `3d0494d0fb7e2369`
   - Plus `windows.py`, `provenance.py`, `dup_census.py`, the ledger row, and the `docs/provenance.md` entry.
   - No `keep/`. 63 holds no scratch for 64.
3. **Worktrees:** `git worktree list` has no plan-63 worktree.
4. **Scopes and temp dirs:** 0 `maps-heavy*` units; `/tmp/p63_*` and `$TMPDIR/p63_*`: 0. The trial script `/tmp/p63_cmp.py` was removed.
5. **Disk:** `df -h /home`: 11 G free (97 %).
