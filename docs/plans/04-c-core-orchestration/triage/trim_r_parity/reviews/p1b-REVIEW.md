Verdict: PASS_WITH_FOLLOWUPS

Plan 42 Phase 1 re-review. Seat: Claude CLI, clean context, disclosed (Codex is weekly-limited). Reviewed local HEAD `ca85ede`. I authored none of this work.

- **Rerun:** `trim_witness.py` ran in 10.8 s. `git diff --stat` was empty afterwards.
- **Independent checks:** I wrote throwaway scripts in `/tmp` that import the witness module and read the committed dumps, R and the G oracle.

The four revised verdicts follow from the evidence in substance:
- L0 roads: a real deviation by volume, but per-item presence is not decidable.
- L0 backgrounds: `R-lacks` by type census.
- L8 roads: not a priority difference.
- No trim-priority rule is evidenced by R.

The L8 result is more robust than the text shows. The findings below are follow-ups: one unexplained G anomaly, one unrecorded deviation, and some overclaims and wording. None of them reverses a verdict.

## F1–F8

| # | Resolved? | Basis |
|---|---|---|
| F1 L8 artefact | **Yes** | v1 is demoted, and the 144 is withdrawn. My checks: the max sampled distance from dropped to kept is **0.768 raw** (step 0.02). The 308 dropped pieces form 237 connected components; the largest is 5.5 raw. So no run of dropped stubs opens a gap of 1 R step or more. The evidence is stronger than stated (see N4). |
| F2 L0 control / bg | **Yes** | Control: 1,108 pieces, with leaf 6 correctly excluded (it has 0 links). q50 is 31.1, and 90% recall needs a tolerance of 500. "Not decidable" is the right conclusion. The bg census is reproduced: R has 0 of type 2:288. 288 is in R's vocabulary (R L8 has 2:288 ×1), so the census is a valid identity. The ring rule still has no positive control; this is a stated limit and acceptable because no verdict uses it. |
| F3 class identity | **Yes** | Any-class is primary. The text then reuses "dc 2 absent from R" as evidence (N3). |
| F4 priority claim | **Yes** | "Priority" is withdrawn and the hypotheses are listed. The label on (b) is misleading (N1). |
| F5 leaf rect | **Yes (latent caveat)** | The rects are data-checked: R road and bg, and G bg, are 0.0 outside. The grid inference is heuristic (N7). The G road 3,072 outlier is misexplained (N2). |
| F6 fields | **Yes, as a stated limit** | `dv_key` and bytes are not captured. This is acceptable because no verdict depends on priority keys. |
| F7 wording | **Yes** | |
| F8 shrink order | **Mostly** | The road → bg → name fallback is confirmed at `_e2.c:1011`. The claim that the fallback cut the 227 backgrounds is unverified (N6). |

## New findings

1. **MEDIUM: L8 G road under-selection against R is unrecorded, and hypothesis (b) is mislabelled.**
   - **Evidence** (`v2.road_volume.per_G_leaf`, L8):
     - In the G leaves with roads outside (3,0), G emits far less than R: leaf 2 has 225 against 4,786 raw; leaf 11 has 0 against 1,251; leaf 14 has 0 against 3,336.
     - R has 801 dc 10 links in the parent; G has no dc 10 at all (2,979 dc 12).
     - IMPLEMENTATION records only "G does not over-select by length". Under the standing rule, a large deviation in road volume has to be named.
     - It also bears on the trim. If G selected what R selects, (3,0) would hold more road bytes, not fewer. "The L8 count comes from fragmentation" is therefore only a partial account.
   - **Fix:**
     - Restate (b) as "G under-selects relative to R (whole parent, dc 10 missing)".
     - Record it as a named residual or follow-on, with the per-leaf numbers.

2. **MEDIUM: the G L0 road "3,072 raw outside the rect" is misexplained, and it is an unexplained G anomaly.**
   - **Evidence:**
     - The text says the pieces "are not clipped to the sub-cell". In fact exactly **5 links** cause it: one in leaf 0, three in leaf 4, one in leaf 8. They have 6–10 vertices, and **every vertex sits at the same point, x = 4096.0**, the parent's east edge (y = 619 / 1625 / 1766 / 1274 / 2193). They are degenerate zero-length links in western sub-cells.
     - All 1,103 other links lie inside their rects.
     - The dumped dropped pieces lie 0.0 outside (2,1).
     - So G pieces *are* clipped. These 5 are either a D1 decode artefact (range or overflow at the sub-cell frame) or an encoder defect in the oracle.
   - **Fix:**
     - Delete the "not clipped" sentence.
     - Determine whether the 5 links are a decode or an encode issue (raw frame bytes for those links). Record the cause, or open a residual.
     - The impact on the control is negligible (5 / 1,108).

3. **LOW–MEDIUM: "Most dropped pieces are G-only" overclaims, and the dc 2 argument repeats the F3 error.**
   - **Evidence:**
     - The text declares per-item presence undecidable, then asserts "most are G-only".
     - "79% dc 2, a class absent from R" uses class code as identity.
   - **Better evidence:** I computed a per-class control (median sampled distance to any R road, other sub-cells):

     | | dc 2 | dc 4 | dc 7 | dc 9 | dc 10 | dc 12 |
     |---|---|---|---|---|---|---|
     | kept q50 | 63.8 | 3.2 | 6.1 | 7.2 | 143.5 | 3.4 |
     | dropped q50 | 126.8 | — | — | — | — | — |

     Within 20 raw: 25% of kept dc 2, and 1% of dropped dc 2.
   - The geometry says G's dc 2 is largely off-R class-wide. That is an upstream L0 selection matter, not a trim matter.
   - **Fix:**
     - Replace "most are G-only" with the per-class distribution.
     - Phrase it as "dc 2 is geometrically distant from R parent-wide (kept and dropped alike)".

4. **LOW: the L8 redundancy argument is near-tautological as written, and "0 carry R-specific evidence" is vacuous.**
   - **Evidence:**
     - 294 of the 308 dropped pieces share an endpoint with a kept piece.
     - For a piece shorter than 1 raw, "every vertex within 1 R step of kept" is then automatic.
     - The R-specific test runs only on pieces that are neither sub-quantum nor redundant, and there are 0 of those.
     - What actually carries the verdict is not in the text:
       - the max sampled distance from dropped to kept, 0.768;
       - the component check (237 components, max 5.5 raw);
       - each dropped piece is its own record (`par` distinct; 0 shared with kept);
       - priority correlates with length (Spearman rank–length −0.80).
   - **Fix:**
     - Record these numbers in the JSON and the text.
     - Drop the "0 R-specific" sentence, or state that it was not exercised.
     - Note that G keeps **968** equally sub-quantum pieces, which supports "fragmentation".

5. **LOW: the L8 volume figures are not like for like.**
   - **Evidence:**
     - "G's is 5,373 decoded (4,738 exact, before the trim)" reads as decoded > pre-trim.
     - The same 2,109 kept pieces measure 4,644.5 from the exact dump against 5,373.3 decoded. That is about 16% inflation, presumably from decode quantisation of tiny pieces. R's 6,623 also comes from a decode.
   - **Fix:**
     - Compare decoded with decoded (5,373 vs 6,623), or exact with exact.
     - State the inflation. The conclusion "G is not above R" survives either way.

6. **LOW: the F8 mechanism wording is unverified.**
   - **Evidence:**
     - Every per-kind limit is `U16_MAPFRAME_BYTE_CEILING` (`build_alldata.py:73-81`).
     - The first `dv_shrink` loop (`_e2.c:992-1006`) therefore cuts backgrounds whenever the bg sub-frame alone exceeds 131,070. That may happen *before* the fallback.
     - "The fallback takes roads to 0 before cutting 227 backgrounds" is asserted, not shown. Roads → 0 in the fallback is right; the stage at which the 227 were cut is open.
   - **Fix:** say "roads are cut to 0 by the fallback; the 227 backgrounds are cut by the per-kind pass or the fallback", or show which from the dump or probe.

7. **LOW (latent): the grid inference in `leaf_rects` is a heuristic.**
   - **Evidence:**
     - `g = 2 if max(ks) < 4 else 4` mis-infers a 4 × 4 parent as 2 × 2 when every non-empty leaf is in row 0.
     - It is not triggered here, and the 0.0 bg rect check guards these two cases. It will silently mis-rect if Phase 2 reuses it on other parents.
   - **Fix:** take the division from the walk or descriptor, or assert it against the decoded data on every use.

8. **LOW: follow-ons are not named.**
   - DESIGN Contract 2.3 and the Phase 2 outcome require a named follow-on.
   - "The 288-template completeness item" has no residual ID.
   - The cause of the L8 fragmentation ("from short clipped or split stubs") is a hypothesis. The evidence shows separate short spool records that touch kept roads, not clipping.
   - **Fix:**
     - Cite the residual row for 288 over-emission.
     - Open or cite rows for L8 fragmentation and N1 / N2.
     - Phase 2 should then close as `proven-cause` (L0 roads, L8 roads) and `R-lacks` (L0 bg), with those follow-ons.

9. **NIT:** the JSON metric says "clamped at 600". Only out-of-reach (inf) values are clamped. Values above 600 that fall inside the expanded bbox pass through unclamped. Distances ≤ 600 are exact, so no number changes. `np.minimum(d, np.inf)` is a no-op.

## Verified numbers

- L0 control: q50 31.1; recall 0.036 at 1, 0.40 at 20, 0.76 at 100, 0.99 at 500. Dropped q50 100.6.
- L0 (2,1): R has 3,695.3 raw in the rect. G kept, from *all* leaves, has **19 raw** in the (2,1) rect. "Drawn with 0 roads" is effectively true, with neighbour spill-in of 19 raw.
- L0 (2,1): dropped in-rect = full = 37,039 raw, so the 10.0 ratio is valid.
- Dump bg: 6,628 type 288 (6,401 K + 227 D), plus 13 type 321 and 1 type 640. G parent: 2:288 ×8,777. R: no 288.
- L8: 308 dropped pieces, all 2-vertex; length q50 0.174; 295 sub-quantum + 13 redundant; dropped total 94.0 raw.
- L8 v1 any-class: 1,053 present / 815 absent / 241 ambiguous.
