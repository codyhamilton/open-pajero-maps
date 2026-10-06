Verdict: PASS_WITH_FOLLOWUPS

Reviewer: Claude CLI, clean context (disclosed; Codex is weekly-limited). I authored none of the reviewed work.
Subject: plan 38 Phase 1 at `7848ac8` (detached, master direct). Only read-only checks were run. The witness was re-run at ~1.4 s and its output was byte-identical: `git diff` was empty, so no restore was needed. I also did one 66 B pread and one 22,080 B pread of the R disc, plus small Python checks. I ran no builds, K1, PBF scan or heavy lock, and changed no tracked file.

## Clause table

| Clause | Verdict | Evidence |
| --- | --- | --- |
| C1 R record decode | PASS | I decoded `record_bytes_hex` independently with the `background.py` layout. Header words `[33,57371,321,0,19908,17841]` give a 66 B record, 27 deltas, code 321 and mult 1, with nothing left over. The start point is region 2: 3524 → 11716 and 1457 → 9649. The ring is closed (first = last), and the frame_raw values equal the JSON. area2 = +621,301, which is 1.85% of the cell. bbox: x 3524–3972, y 919–1996. The nearest edge is 124 units away, so there are 0 contacts. An R-disc pread of 66 B at 360,774,274 equals the bytes. The leaf sha `7c3b4558…` is verified, and the record occurs exactly once in the leaf, at leaf offset 13,122. |
| C1 cell-raw vs frame_raw | PASS | All 28 vertices have the constant offset (−8192.000, −8192.000), which is 2 cells. The lat/lon bbox matches about 324 × 608 m. |
| C2 G control | PASS | Same slot, leaf [1730], sha `a0cd4d21…`. Records are `class2:code288` ×4 and `class2:code291` ×1, with 0 of type 321. The disc sha is taken from the `protected_before.json` snapshot and is not re-hashed (F6). |
| C3 spool demander clip under production `bg_shape` | PASS | `probe246.c` calls `kw__bg_shape` with closed=1 (class 2) and the spool's `b_mult`, `b_type` and `b_flags`. That matches `enc_bg` → `bg_shape(..., c==2, mult, tc, fl, bd, ...)` (`_cenc.c:1058`). b4 = {0,4096,0,4096} with already-lattice cell-raw input is an identity transform. rect = [0,0,4096,4096] and cr = 4096 equal the production default for a normal L0 cell: `encode_common`, where `kw__encode_rec` passes xrect=NULL (`_cenc.c:1286-1287`, `1352`). The result is 0 B / nrec 0. The Python mirror gives q 2 and area2 rint 0. The trigger vertex (4021.433, 2.392) equals `0246_requirement.json`. The absence of an OSM id is recorded, which answers Open question 1. |
| C4 predicate = DESIGN, fixed before measuring | PASS (weak) | Clause (i) matches, except that the edge term is looser than "the edge segment it touches" (F3). Clause (ii) turns "sign and magnitude" into the tolerance \|ΔA2\| ≤ 2·P_R, which is stated in the docstring and copied into the JSON. That is a reasonable first-order bound and here equals 5,596 against ΔA2 = 621,302. The sign term is not meaningful (F2). "Fixed before measuring" cannot be shown, because the predicate and the results land in the same commit (F3). The outcome holds under any reasonable predicate: 28/28 vertices are ≥ 917.9 u from the clip, and Hausdorff is 2,053.8. |
| C4 nearest alternative named | PARTIAL | The R side is covered: the other 10 polygons have no cell-local meet. On the spool side, only the 5×5 type-321 set is ranked. The 284 PBF candidates are not named; the doc only cites plan 30's 0-record result (F4). |
| C5 verdict H3, H1 rejected | PASS | H1 is rejected correctly: the R ring is interior, has no edge contact, and is far from the sliver. H3 over H2 is justified: no geometry is shared and there is no edge path. Plan 14's representability science is correctly left unchallenged, since the sliver is in the rint-annihilated class and R has no record for it. |
| "Source-data difference" proven | PASS with gap | A pinned-PBF node-in-box scan finds only McGlew Road. Any source for a 28-vertex interior ring would need nodes inside the +150 m box, so the class holds. However, two supporting statements in IMPLEMENTATION are false or unsupported (F1), and the absence is proven only against the 2026-08-24 extract (F5). |
| Outcome 4: no encoder change | PASS | The commit touches only the plan 38 folder. |

## Findings

1. **Medium: two evidence statements are false or unsupported.**
   - **Claims:** IMPLEMENTATION §3 says "Across any type, 4 features reach the cell (321, 291, 288 ×2). None contains R's ring centroid (3684, 1463)." §5 says "In that extract the area holds only McGlew Road."
   - **No artefact behind them:** the witness scans only `b_type == 321`, so neither claim has a committed artefact.
   - **G contradicts them:** I decoded G's slot. Two of the four 288 records are full-cell rectangles, [0,4096]×[0,4096] with 5 coords, and both contain R's centroid. 288 is the L0 catch-all for any non-road ring with unrecognised tags (`selection.py:55`). So at least two source rings with unmapped tags enclose R's location. Their source cells lie outside the 5×5 window: an any-type bbox check of that window finds 5 features, none of which encloses the cell.
   - **Effect on the verdict:** none. An enclosing ring can only clip to a full-cell record, never to R's 28-vertex interior ring. R's slot also has no 288 at all (11×321 and 10×291 class 1).
   - **Fix:**
     - Correct §3 and §5.
     - Add an any-type reach list to the witness, either by spool source cell and ordinal for the two full-cell 288s, or by reading the G records.
     - Name the enclosers' labels or tags where the spool has them, and state why they cannot be R's record (full-cell clip, and R has no 288 there).
     - Rephrase "holds only McGlew Road" as "no OSM object has a node in the box; ≥2 unmapped-tag areas enclose it".

2. **Low: the sign clause is not discriminating.**
   - **Why:** for closed rings, `bg_shape` reverses the source when its a2 < 0, so it always clips a positively oriented ring (`_cenc.c:919-929`). The Python mirror's −0.964 is taken before that orientation step. "Sign differs" is therefore an artefact of the mirror, not evidence.
   - **Fix:** orient the mirror ring as `bg_shape` does before comparing, or drop "sign differs" from §4 and rely on the vertex and magnitude clauses.

3. **Low: predicate fidelity and timing.**
   - **Looser edge term:** `dist_to_edge` uses the nearest of all four cell lines, but Contract 4 says "the cell edge segment it touches". The clip touches only y=0. Being looser can only add matches, so the conclusion is safe, but say so.
   - **Tolerance wording:** 2·P_R is first-order and omits the O(nδ²) term, so "the most a 1-unit band can move area2" is slightly overstated. Call it a first-order bound.
   - **Timing:** "Fixed before measuring" is asserted, not evidenced. The predicate's first commit is 7848ac8, alongside the results.
   - **Fix:** state these three points in IMPLEMENTATION §4. For future phases, commit the predicate before the measurement, or quote the DESIGN text verbatim and mark the interpretation.

4. **Low: Contract 4 alternative naming is incomplete.** The DESIGN asks for the nearest alternative among the 284 candidates to be named, and only plan 30's aggregate "0 in-cell records" is cited.
   - **Fix:** add one line saying that no candidate has in-cell geometry, so no nearest in-cell alternative exists. Cite the artefact path and sha of plan 30's r4 candidate evaluation.
   - **Gaps to record:** that account lists row-specific supply gaps for row 246 (r2316598, r7493850, r8043873, r8653540 at the native-C vertex limit, plus 29 relations missing member ways). Note that these cannot produce R's ring either: the PBF scan found no way with a node in the box, and the missing ways are extract-clipped, outside the AU polygon.

5. **Low: residual gap in "source-data difference".**
   - **What is proven:** absence only in the pinned 2026-08-24 extract, using node-in-box. Ways that cross the box with no node inside are not seen. They cannot form R's interior 28-vertex ring, but the stated limit should cover crossing as well as enclosing areas.
   - **What is not:** R's source vintage is unknown, so "R's source had a feature OSM lacks" is a class, not an identified object.
   - **Fix:** widen the limit text. Optionally, if external fetch is authorised under the plan 30 attic precedent, run an Overpass attic or history query for the bbox to name or exclude a deleted OSM feature. This is not required for Phase 2's `proven-cause:source-data` disposition.

6. **Info: G disc identity is not re-verified.** The witness records `expected_sha256` but does not hash the disc. The file mtime is 2026-10-06 09:35, and size is 1,692,079,168.
   - **Fix:** record size and mtime next to the snapshot reference, or note that the hash was verified by the snapshot's own run.

7. **Info: offset basis.** The record's "frame offset 622" is relative to the background frame, while its file offset 360,774,274 is the leaf offset plus 13,122 (leaf-relative). Adding 622 directly to the leaf offset gives the wrong address. I verified the bytes by pread.
   - **Fix:** state both bases in §1.

## Phase 2 guidance

Disposition `proven-cause:H3-other-feature / source-data`. Fold the F1 correction into the disposition evidence, so that the enclosing 288 areas are named rather than denied.
