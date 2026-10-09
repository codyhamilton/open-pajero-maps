# Producer-ambiguous tie RC (R-G5-1-a / R-G5-2-a): emission provenance on 33006aa

## Intent
Plan 46 left 4,612 rows in 98 groups as `producer_ambiguous`: two same-type candidate rings each byte-hit the record. Plan 63 proves the producer of every copy with an output-neutral source-tag sidecar on the `33006aa` encoder. It derives and holdout-tests the selection rule, re-decides every row, publishes S′ as an opt-in, and records the duplicate-emission parity against R. It uses no nearest-ring choice and no waivers.

Design: box draft `63-producer-ambiguous-tie-rc/DESIGN.md` (re-copied fresh 2026-10-09), base `b889c2e`. Seat: Codex.

## Outcome
- **Commits:** P1 `627fabb`; P2 `1005eed`, `6b3c47b`; P3 `5174eab`, `c35a22e`; review fix `a4bb568`; close-out (this record).
- **R-G5-1-a (4,594) and R-G5-2-a (18): discharged-plan-63.** All 4,612 rows are `build:eo_bg_stitch`, and each copy has a sidecar-proven producer (`p7_producer_tie/verdicts_ambiguous.tsv.gz` `10d250a8…`).
- **Accepted rule: contiguous per-producer block emission** (`33006aa` `_cenc.c` `enc_bg` over `_e2.c` `kw_e2` / `e2_merge`; divided leaves via `dv_bg_cells` / `dv_probe`). 537/537 on derivation, 546/546 on holdout. Every other candidate rule was rejected.
- **Gates:** G1 2,085/2,085 frames are byte-equal to 013586b5. G2 398,324/398,324 unique-byte records agree, 581 of them in cover form.
- **S′ = S ∪ 6 scope-delta groups** (opt-in `gate_repro --s02-resolve`; plan 46's S is unchanged): 145,960 / 11,127,845; a(S′) = 15,080. The S04 identity is off by 2, and the record names why.
- **New R-G5-6 (Design):** G holds byte-identical same-type duplicate records in 336,329 leaves on 013586b5 and 336,135 on 0c22b266; R holds them in 0.
- **R-G5-4-a-1:** a note only, because applying the rule there is a 63 non-goal (plan-62 consumer).

## Review
Codex (read-only), first review: **FIX**.
1. G2 covered only the tie cells. Fixed: all 1,770 cells now pass, 398,324/398,324.
2. The receipt hash labels were stale. Fixed.

Codex re-review: **LAND**. Tests: `test_producer_tie`, `test_bg_producer_scan` and `test_perf_inventory` pass (19).

## Implementation log (collapsed from IMPLEMENTATION.md)

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

## Phase 3: apply, decide, residuals (in progress; checkpoint 2026-10-09 ~14:00 AEST)

- **Interruption ~13:42.** I checked the state afterwards: host up; both of my heavy scopes were alive (P2 reproduction holding the flock, P3 heavy queued); no duplicate job was started.
- **`dup_cases.tsv.gz` writer bug (found in P3).** `provenance.py` wrote each JSON case through `"\t".join(map(str, <string>))`, which put a tab between every character. No rule or provenance result was affected: `rules.json` and `provenance.tsv.gz` never read it back.
  - Fix: one-element row lists. The whole of Phase 2 was then reproduced from the committed patch and driver (`rerun_p2.sh`, under the wrapper; max RSS 3.71 GiB, memory.peak 1.26 GiB, 824 s).
  - `windows.json` was identical.
  - A == B for `provenance.tsv.gz`, `rules.json` and `dup_cases.tsv.gz`.
  - `provenance.tsv.gz` and `rules.json` are identical to the committed files (`e323cccf…`, `9b76437c…`).
  - The corrected `dup_cases.tsv.gz` is now `02378920…` (was `982269d0…`, malformed).
- **`apply_ties.py` → `verdicts_ambiguous.tsv.gz`** (`10d250a8…`; summary `.json` `730e4e6d…`). Run twice: byte-identical.
  - 4,612 rows / 98 groups (bg 18, bnd 4,594; T1 3,288, T2 1,324; scope delta 516).
  - Each row's producer is proven by the sidecar, and the accepted rule agrees on 4,612/4,612 rows (98/98 groups).
  - **Verdict: `build:eo_bg_stitch` 4,612/4,612** (the unchanged phase-23 limb for the proven producer, from `ties_all.json`).
- **Duplicate-emission census** (`dup_census.py`; distinct leaf frames; alias slots read once):

  | Disc | Leaves with byte-identical same-type class>0 duplicates | Classes | Extra copies |
  |---|---|---|---|
  | R `8c2d2027…` | **0** / 482,473 | 0 | 0 |
  | 013586b5 | 336,329 / 3,954,156 | 338,760 | 445,137 |
  | 0c22b266 (live) | 336,135 / 3,954,165 | 338,565 | 444,934 |

  G emits duplicates where R never does, so I opened new row **R-G5-6** (owner Design; `blocks-phase3`, Design may reclassify). The mechanism is the accepted rule: each routed same-type source emits its own piece, and identical pieces are not deduplicated. Plan 63 does not fix it.
- **S′ (opt-in; plan 46's S unchanged).**
  - `s02_resolution.tsv.gz` (`7b79ca5f…`): the 6 scope-delta groups. Their S02 bit is the plan-46 predicate on the sidecar-proven producer: all 6 = 1 (closed, closing edge longest, crossings ≥ 1).
  - New opt-in `gate_repro.py --s02-resolve` (default off; it touches the s02 side only, never the residual bit). One run with `--s02-scope full` → `p7_producer_tie/gate_result_s02_resolved.json`:
    - S02: 145,960 groups / 11,127,845 rows. S′ is the whole scope. Identity: 145,954 + 6 and 11,127,333 + 512 (75 + 75 + 119 + 119 + 62 + 62).
    - Res entries (fill+bnd): 305,225 (+3 cover = 305,228 = 451,185 − |S′| + 3). ✓
    - Res bnd groups: 204,121 = 219,201 − a(S′), with a(S′) = 15,080. ✓ (Design predicted 15,080.)
    - S04 status-1 groups: 203,954. The identity predicts 219,032 − 15,080 = 203,952. The difference of 2 is (1481,1288) shapes 0/2: their residual bit stays 0, because the resolution deliberately does not retro-edit `residual_crossing_verified` (Contract 3). Named, not absorbed.
    - Everything else is unchanged vs `gate_result_full.json` (R01 920,786; S03 517,648; S04 rows 5,413,971; rings 70,861; rem fill 137).
    - `rem_bnd` under S′ reads 8,227 (−512). It is informational only: the historical 137 / 8,739 stays the plan-46 gate.
- **Residuals:**
  - R-G5-1-a → discharged-plan-63 (4,594 build); R-G5-2-a → discharged-plan-63 (18 build).
  - Parents R-G5-1 / R-G5-2 updated.
  - R-G5-4-a-1 gets a note only: applying the rule there is a 63 non-goal, and the row is unchanged.
  - New R-G5-6.
  - Docs updated: `causes_residual.md` note, `synthesis.md`, and the OVERVIEW ownership map.

### scratch_receipt — Phase 3 (2026-10-09 ~14:15 AEST)
1. **`du -sb`:**
   - `output/scratch-63`: 5,633,431,511 B before; **gone** after. Deleted:
     - the P2 reproduction (386 windows, A/B outputs);
     - the `gatework` of the S′ gate run (dump_s02 / dump_ext / cls1 / cls2);
     - the census tsv intermediates (R / 0c22b266);
     - the apply_ties A/B copies (compared first);
     - wrapper logs (peaks copied to the ledger first).
   - Re-created throwaway worktree `open-pajero-maps-63-33006aa`: 10,164,202 B; **removed** after `PATCH_SAME`.
2. **Kept, all committed, all in `git ls-files`.** sha256 prefixes:
   - `verdicts_ambiguous.tsv.gz` `10d250a83a35ebe8`; `verdicts_ambiguous.json` `730e4e6d38927bd5`
   - `dup_cases.tsv.gz` `023789200fe88c03`
   - `s02_resolution.tsv.gz` `7b79ca5fafaa021c`
   - `gate_result_s02_resolved.json` `38a81418c1fd18de`
   - `dup_census_R.json` `2ca164f217df7d13`; `dup_census_0c22b266.json` `fc0ea943a2abcd49`
   - `residuals.tsv`: final hash in the review-fix receipt below.
   - Plus `apply_ties.py`, `s02_resolution.py`, `gate_repro.py --s02-resolve`, `causes_residual.md`, `synthesis.md`, `OVERVIEW.md` and the ledger rows.
   - No `keep/`.
3. **Worktrees:** no plan-63 worktree in `git worktree list`.
4. **Scopes and temp dirs:** 0 `maps-heavy*` units; `/tmp/p63_*`: 0.
5. **Disk:** `df -h /home`: 11 G free (97 %).
6. **Never-delete list respected.** `.heavy.lock`, `scratch-46` (dump, gate shards, `gatework_full_a`), the spool, R (read-only mount), 013586b5 / 4ed9cd80 / 0c22b266, and `.venv-rp` were read only, never touched.

## Review 1 (Codex, read-only): FIX → fixes

1. **G2 covered only the 46 tie cells** (the contract says every window cell). `provenance.py` now runs G2 over every record of every analysed window cell, tie and sample. I rebuilt the 386 windows from the committed patch (`windows.json` identical) and ran the analysis A + B (A == B on all three outputs). Max RSS 3.71 GiB, memory.peak 1.28 GiB, 859 s.
   - **G2 (all 1,770 cells):** 398,324 unique-byte records → 397,743 exact plus 581 cover-form (same source shape, E1 kind 1) = **100 %, 0 disagreements**.
     - Tie cells: 14,211 (3 cover-form).
     - Sample cells: 384,113 (578 cover-form).
   - Unchanged: G1, provenance, cases, the rule table, `provenance.tsv.gz` (`e323cccf…`) and `dup_cases.tsv.gz` (`02378920…`).
   - New `rules.json` `0ef611e2…` (G2 counts only).
   - `verdicts_ambiguous.tsv.gz` is unchanged (`10d250a8…`, A == B); its summary `.json` is now `569f3783…` because it records the new `rules.json` input sha.
   - The 14,211 figures above (Phase 2) are the tie-cell subset.
2. **Receipt hashes.** Phase 3's verdict tsv/json labels are corrected. Final kept hashes are in the receipt below.

### scratch_receipt — review fix 1 (2026-10-09 ~14:55 AEST)
1. **`du -sb`:**
   - `output/scratch-63/fix`: 52,170,794 B before; **gone** after (windows, A/B outputs, apply_ties A/B copies, wrapper logs; peaks are recorded above).
   - Throwaway worktree: 10,164,202 B; **removed** after `PATCH_SAME`.
   - `output/scratch-63/review` (13,859 B: prompt and Codex output) stays until the re-review, then is deleted at close-out.
2. **Kept, all committed, all in `git ls-files`.** sha256 prefixes:
   - `rules.json` `0ef611e2613bfb3c`
   - `verdicts_ambiguous.json` `569f3783332b4b7b`; `verdicts_ambiguous.tsv.gz` `10d250a83a35ebe8`
   - `provenance.tsv.gz` `e323cccf50e636c7`; `dup_cases.tsv.gz` `023789200fe88c03`
   - `residuals.tsv` `fb8cb4ba86afc888`
3. **Worktrees:** none for plan 63.
4. **Scopes and temp dirs:** 0 `maps-heavy*`; `/tmp/p63_*`: 0.
5. **Disk:** `df -h /home`: 11 G free.
