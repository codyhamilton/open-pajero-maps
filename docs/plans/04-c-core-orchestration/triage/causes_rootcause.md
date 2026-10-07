# Unit 3-13 — crossing-ring root cause

**Status: ACCEPT-WITH-CONDITIONS (Sonnet 5.5, 2026-10-03 ~04:39–04:48 AEST).** See [review_3-13.md](review_3-13.md). S02–S05→build stands.

S02/S03/S04/S05 are **build**, superseding the historical spool attribution. A class-2 explicitly closed self-crossing ring has a defined even-odd interior. Retaining its closing chord and original region while expressing that region as simple faces makes the unchanged C encoder clear every target residual in nine complete-repair windows. Deleting an alleged extractor chord is unnecessary to obtain correct output. The extractor may still have generated an unintended chord, but these experiments cannot establish that intent and do not justify a spool pin. Other-kind rules O01–O06 and R01 are carried unchanged in IDs/predicates; **R01 exclusivity vs build is unproven** (L0/291 window: 31 type-291 `in_eo_same=1` fills vanish after repair and may overlap build; not tested beyond that window). This unit does not extend its conclusion to O02/O04 without their own discriminator.

**Must-fix (Sonnet findings 1–3).** (1) ~15% EO witness disagreement — robust evidence = failing vertex + outline distance; caveat “every group has rational interior witness”. (2) “5905 regions differ” = vertex tests (~5399 keys / ~5227 leaf,type); ~19% no macro-area error — use vertex+outline not area for those. (3) R01 exclusivity unproven — as above. **Limitations (findings 4–6 + D):** A stratified-sample not exhaustive; B group-level not per-row for all 15002; C `clip_right_inside` hypothesis only (~79%, no rule); D 9064 + PARTITION FAIL unchanged.

## Exact clip discriminator

Inputs: G_new `output/scratch-3-11/G_new/ALLDATA.KWI`, SHA256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`; original `output/scratch-3-12/dump_ext`, all-level original source caches from scratch-3-07. `select.py` chooses uniform failing residual **groups independently of residual_crossing_verified**, excluding already established R01/S02, seed **2026100313**. At least300 groups per populated (kind,level,type,sentinel) stratum, census below300: **5905 groups,22 strata**. `samples.jsonl` records native dump row and full key; `selection.json` records populations. No failing L6 fill stratum exists. A separate uniform S02 sample300, seed **2026100320**, is in `samples_s02.jsonl`/`s02_selection.json`; all three S05 rows are censused.

The brief says “even-odd over all shapes”; the actual contract is **OR of each same-type ring’s even-odd interior**, not XOR between separate rings (`quantisation_roundtrip.py:Region.inside`, `_k1_bg.c`). `common.py` walks actual management leaves and decodes frames with D1; leaf vertices are integer raw coordinates. `exact.py` independently rounds source vertices half-even to the integer raw lattice, intersects segments with Fraction arithmetic, splits vertical slabs, unions per-ring intervals and integrates exact area. Conservative outward-rounded float boxes prune candidates only; intersection, ordering and area decisions are exact. `oracle.py` compares the union of disc polygons with the source union clipped to the actual frame.

**5905/5905 tested failed vertices are outside lattice EO and farther than0.500001 raw Chebyshev from every original same-type outline** (unbounded original-double distance search, not a64-raw nearest-source search). Caveat (Sonnet finding 2): “5905 regions differ” counts **vertex tests** (~5399 distinct keys / ~5227 distinct leaf,type area comparisons); sentinel True/False and multi-shape leaves repeat results. Exact area inequality alone is not a cause predicate: lattice source rounding can legitimately create small symmetric differences. ~19% (1129 groups) have no macro-area error — for those, rest on **vertex + outline distance**, not area. The independent original-outline witnesses plus region-preserving original-double counterfactuals discriminate these failures from harmless quantisation. For these vertices, original outline distance>0.500001 also makes EO inclusion invariant under moving each source vertex by at most0.5 per coordinate: the segment homotopy cannot cross the queried vertex. Thus the snapped-region outside test is compatible with original-ring outside inclusion, rather than treating rounding as a new source contract. The conservative macro-area bound is descriptive and not used in rules. One boundary inset point enters the source region; this does not rescue its actual failed vertex.

| Kind | L | Type | Sentinel | Groups | Equal region | Vertex beyond region tolerance | Macro-area errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| background | 0 | 288 | False | 300 | 0 | 300 | 228 |
| background | 0 | 288 | True | 300 | 0 | 300 | 242 |
| background | 0 | 289 | False | 300 | 0 | 300 | 224 |
| background | 0 | 289 | True | 300 | 0 | 300 | 230 |
| background | 0 | 291 | False | 300 | 0 | 300 | 265 |
| background | 0 | 291 | True | 300 | 0 | 300 | 264 |
| background | 0 | 578 | False | 300 | 0 | 300 | 285 |
| background | 0 | 578 | True | 300 | 0 | 300 | 291 |
| background | 2 | 289 | False | 249 | 0 | 249 | 140 |
| background | 2 | 289 | True | 194 | 0 | 194 | 114 |
| background_boundary | 0 | 288 | False | 300 | 0 | 300 | 216 |
| background_boundary | 0 | 288 | True | 300 | 0 | 300 | 244 |
| background_boundary | 0 | 289 | False | 300 | 0 | 300 | 259 |
| background_boundary | 0 | 289 | True | 300 | 0 | 300 | 266 |
| background_boundary | 0 | 291 | False | 300 | 0 | 300 | 274 |
| background_boundary | 0 | 291 | True | 300 | 0 | 300 | 279 |
| background_boundary | 0 | 578 | False | 300 | 0 | 300 | 277 |
| background_boundary | 0 | 578 | True | 300 | 0 | 300 | 281 |
| background_boundary | 2 | 289 | False | 300 | 0 | 300 | 184 |
| background_boundary | 2 | 289 | True | 300 | 0 | 300 | 205 |
| background_boundary | 6 | 288 | False | 30 | 0 | 30 | 3 |
| background_boundary | 6 | 288 | True | 32 | 0 | 32 | 5 |

Every group’s rational source/disc/excess/missing/symmetric-difference area, recorded `witness` field, raw vertex, original outline distance, leaf rectangle and native dump key are in `oracle_groups.jsonl`; `leaf_geometry.jsonl` records all contributing source IDs and D1 polygons. Caveat (Sonnet finding 1): do **not** treat “every group has rational interior witness” as robust — ~15% of checked witnesses disagree with original-double EO (rounding slivers); robust evidence is the **failing vertex + original-outline distance**. The headline witness below does verify on the doubles. Representative independent seed-selected key: boundary `(6,15,17,288,p0=287,shape=0)`, native row16546637. Source area228569/2346 raw²; disc area2952781103/176; symmetric difference1711271009/102 (~16,777,166.75). Witness `(123989/2,71680)` is outside source and inside disc; actual failed vertex `(61440,69632)` is1566.48 raw from the nearest original same-type outline. This is almost a full-frame complement, not an outline rounding discrepancy.

S02: corrected `s02_oracle_groups.jsonl`/`s02_oracle_summary.json` show300/300 unequal,300/300 beyond region tolerance,261 macro errors. Its L0/type291 complete-repair window below clears all target failures, including historical S02 scope. S05: `cover_oracle.json` uses actual decoded leaf regions rather than placeholder dump vertices. Its three keys/cells1792,395;1801,395;1805,395 have exact excess areas about11,931,616.31;16,777,216;15,865,059.93 raw², missing area0. All three are false full-frame covers and independently cleared below.

## Mechanism and fix scope

`parser/kiwiw/_cenc.c:bg_shape` (around lines608–711) orients the **whole ring** by total signed area, obtains clipped chains, then chooses the next counterclockwise perimeter entry using `g_sin/g_sout`, without classifying each chain’s local even-odd filled side or cancelling coincident edges. Self-crossing lobes can have opposite local orientation although global area is positive. The greedy successor graph can also encounter an already-used successor; it breaks and `emit_piece` closes the accumulated path, potentially creating an interior chord. This explains complements/extra connector pieces and vertices far outside producer bboxes. The exact oracle establishes wrong output; local-side/graph details are the implementation diagnosis, with the incomplete separator disclosed below.

Fix proposal for follow-up only: replace the closed-ring chain stitching in `_cenc.c:bg_shape`/`chains` with even-odd-aware arrangement/clip traversal, handle repeated/coincident edges and filled-side classification, then pass correct faces through existing `emit_piece` rounding/densification. `_e2.c:_bg_sub_cells` division probes call `kw__bg_shape` (near637), so probes and final emit must share the correction. Keep integer wire rounding and checker tolerances. No Python build fix. Target S02/S03/S04/S05 rows →0: **17,058,955** =517,648 fill +16,541,304 boundary +3 cover; R01 and other-kind causes are separate. This is a future full-disc target, not a measured full-disc repaired result.

A legitimate frame-clip vertex can be far from original outlines and still be valid because K1/Python boundary validity accepts same-type interior OR outline within0.500001. The tested vertices are outside both. Current fill K1/Python demands outline proximity, whereas 3-07 Amendment4 accepts same-type interior: R01 remains labelled checker, **but exclusivity vs the build defect is unproven** (see L0/291 window caveat). Amendment4’s outline-only boundary wording differs from current K1/Python; all sampled failing boundary vertices are outside interiors, so that discrepancy changes none of these witnesses. See `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` and `parser/tools/quantisation_roundtrip.py` lines968–995. No checker rule or tolerance changed.

## Complete-repair counterfactuals (condition A)

`split.py` builds a rational arrangement of **original unrounded binary-double** ring coordinates, preserves original EO faces (including the original closing chord), and serializes simple faces. The change removes topological ambiguity for the encoder while preserving the source region up to sub-ulp serialization, not a source deletion or invented outline. `cf.py` repairs **ALL P rings** (explicit closure; longest closing edge properly crosses a nonadjacent edge) whose bbox meets the whole window, including non-failing rings. Every remote source is retained in private `spool_faces`; appended records update offsets, lengths and header totals. The historical windows are reused for288/291; other windows deterministically minimize candidate count then vertex count from the producer census. Small-window selection limits inference about incidence; it is not a full-Australia repair.

Original builds byte-match G_new in every window; C build uses j4, K1j1, serialized under the heavy lock. Repaired discs are tested against **ORIGINAL spool** as well as face spool, avoiding validity against a changed reference. Target fill and boundary residuals clear in all six strata. `cf_summary.json`, `cf_source_sets.json`, `cf291_remaining.json` and their per-case reports/dumps are evidence.

| L/type | Window inclusive source cells | P rings repaired | Raw fill before→after | Boundary before→after | Target fill/boundary remaining |
| --- | --- | --- | --- | --- | --- |
| 0/288 | [1769, 202, 1772, 205] | 1 | 32→0 | 255→0 | 0/0 |
| 0/291 | [828, 745, 831, 748] | 34 | 69→7 | 829→0 | 0/0 |
| 0/289 | [1401, 851, 1402, 852] | 1 | 32→0 | 90→0 | 0/0 |
| 0/578 | [1400, 1287, 1401, 1288] | 1 | 23→0 | 60→0 | 0/0 |
| 2/289 | [202, 229, 203, 230] | 1 | 17→0 | 108→0 | 0/0 |
| 6/288 | [15, 17, 16, 18] | 3 | 0→0 | 132→0 | 0/0 |

Plan **55** (2026-10-08): the Boundary-before integers above match a **half-open** leaf-cell window `[x0,x1)×[y0,y1)` on the `87a01b14` K1 `background_boundary` dump (type-filtered); `window_before.json` counts the same dump with an **inclusive** `[x0,x1]×[y0,y1]` — both correct (explained-dual-basis; see `triage/independent_reviews/3-14/conditions/window_before_basis.md`). R-G8-1-b after-0 is unchanged.

Type291 window has7 remaining raw fill rows, all unrelated type288 with in_eo_same1 (R01). Dedicated original-spool small before/after dumps census them: original type291 fill62=31 interior checker +31 outside; repaired type291 fill0 and boundary0; type288 interior7 remain. Thus the31 old R01 type291 rows disappearing are not credited as build attribution; Sonnet finding 3: this shows R01 may partly overlap build and was **not tested beyond this window**. Repairing all34 P sources explains the previous589 boundary remainder from repairing only one source. L6 fill before0 is explicitly vacuous, not a positive fill witness.

S05 complete windows add11 rings:

| L0/type291 window | P rings | Boundary before→after | S05 cover before→after |
| --- | --- | --- | --- |
| [1792, 395, 1793, 396] | 6 | 196→0 | 1→0 |
| [1801, 395, 1802, 396] | 3 | 132→0 | 1→0 |
| [1805, 395, 1806, 396] | 2 | 120→0 | 1→0 |

All three byte gates pass; fill remains0. `covers.py`, `cover_cf_summary.json`, `cover_source_sets.json`, `cf_cover/` hold builds/reports. The nine windows repair52 rings total; they do not claim an exhaustive repair of70,999 source rings. Caveat (Sonnet finding 4 / limitation A): extrapolation to S02–S05→build is a **stratified-sample** basis (oracle uniformity + one clean window per stratum), not an exhaustive repair.

## Why some P rings fail (condition C; failed hypothesis)

Crossing is a prerequisite for this scope, not a sufficient per-ring failure predicate. Rings wholly inside a frame avoid stitching; clipping can reach a locally reversed lobe, or only correctly oriented lobes. Coincident-edge cancellation, successor reuse, quantisation collapse and overlapping same-type source rescue further affect observed failure.

Tested predicate **clip_right_inside**: after global signed-area orientation, at least one frame-clipped source segment has original EO interior on RIGHT and exterior on LEFT. `predicate.py` uses exact rational side points, records wrong/correct/ambiguous edge counts and witnesses. `pairs.py` chooses P source pairs in the same actual leaf/level/type, vertex counts within25%, independent of the predicate; nonempty unchanged direct-C outputs required. Fail source is in exhaustive original failing-producer census and has an invalid own-ring emitted vertex; control matches no failing residual piece (including ambiguous candidates/historical S02) and its local vertices are all valid. A global failing ring may fail in another leaf; overlapping sources can rescue a local failure, so these labels are not row attribution.

Source-identity SHA split seed2026100315 is assigned **before pairing**, both sources same split. `pair_split_audit.json` verifies no source leakage. 367 matched pairs,182 training/185 heldout; integer-lattice predicate separates155/182 train and **147/185 heldout (79.46%)**: **FAILED as a complete separator** (Sonnet finding 6 / limitation C: `clip_right_inside` remains **hypothesis only** — ~79%, no rule predicates on it). Small strata are censuses of available matches, not300 independent pairs. Side columns/measurement story are `paired_predicates.tsv`; original observations/witnesses are `matched_pairs.jsonl`.

| L/type | Train separated/pairs | Heldout separated/pairs | Actual-C remeasurement heldout separated/pairs |
| --- | --- | --- | --- |
| 0/288 | 43/52 | 41/48 | 40/48 |
| 0/289 | 6/8 | 7/9 | 7/9 |
| 0/291 | 47/50 | 42/50 | 43/50 |
| 0/578 | 15/22 | 17/29 | 23/29 |
| 2/289 | 42/45 | 38/47 | 39/47 |
| 6/288 | 2/5 | 2/2 | 2/2 |

`refine_pairs.py` remeasures the SAME cohort using actual unrounded C parent-frame projection and sequential C float signed-area sign, with exact rational binary-double side tests. It gives161/182 training and154/185 heldout. This is **not fresh heldout validation**, and still fails completely separating the classes. Snapping thin rings can change their orientation sign, explaining some initial misses. No rule predicates on either tested separator. Next predicate: record the actual directed chain-successor graph, cancelled even-odd edges (same interior on both sides), used-successor early termination and implicit closing chords; compare resulting local EO region with correct face union, then validate on fresh source-disjoint rings. Condition C is a documented failed hypothesis with next predicate under the brief’s stopping clause, not claimed solved.

## Near-threshold verdict (condition B)

Original new-tail rows total **2184 fill +12818 boundary =15002** with d_src(0.5,1]. `tail_census.py` decodes actual D1 mult_const for **every15002** row: all1, ruling out coarse delta-floor quantisation. Independent seed2026100314 sample1666 (up to300 per kind/level/type, census smaller) reproduces distance to all original same-type outlines, agreeing with dump and exceeding0.500001. Nearest rounding of a point actually on an original segment at mc1 displaces each coordinate by at most0.5; it cannot by itself explain these failures. With the exact discriminator and region-preserving repairs, this tail belongs to bad clipping/connector geometry. Caveat (Sonnet finding 5 / limitation B): support is **group-level**, not a per-row region proof for all 15002 rows. No tolerance relaxation, no claimed measured tolerance gap. A pre-wire connector trace remains the strongest row-specific follow-up; it was not performed here.

| Kind | L | Type | Tail rows (all mult1) |
| --- | --- | --- | --- |
| background | 0 | 288 | 730 |
| background | 0 | 289 | 61 |
| background | 0 | 291 | 1204 |
| background | 0 | 578 | 180 |
| background | 2 | 289 | 9 |
| background_boundary | 0 | 288 | 2418 |
| background_boundary | 0 | 289 | 74 |
| background_boundary | 0 | 291 | 10184 |
| background_boundary | 0 | 578 | 89 |
| background_boundary | 2 | 289 | 45 |
| background_boundary | 6 | 288 | 8 |

## Classification and honest remainder

Only causes/notes of S02–S05 change. IDs, predicates, ordering, scopes and all other rules retain their original values. `classify.py` runs original `k1_triage.py` with scratch CHUNK250000 (default2M reduced for memory), reuses unaltered152-byte native dump. `partition_audit.json` verifies every assignment file SHA256 equals the 3-12 file, unclassified group TSV is byte-identical, and row totals match. `classify/partition.txt`: **PARTITION FAIL, expected exit1**, due9064 unattributed.

| Kind | Checker before→after | Build before→after | Spool before→after | Unattributed before→after |
| --- | --- | --- | --- | --- |
| background | 920786→920786 | 0→517648 | 517648→0 | 137→137 |
| background_boundary | 0→0 | 0→16541304 | 16541304→0 | 8739→8739 |
| interior_cover | 0→0 | 0→3 | 824→821 | 0→0 |
| completeness | 495→495 | 0→0 | 56→56 | 188→188 |
| name_anchor | 0→0 | 0→0 | 1→1 | 0→0 |
| **All** | **921281→921281** | **0→17058955** | **17059833→878** | **9064→9064** |

Total17990178 unchanged. Residual per kind/level/type:

| Kind | L | Type | Unattributed rows |
| --- | --- | --- | --- |
| background | 0 | 288 | 52 |
| background | 0 | 289 | 7 |
| background | 0 | 578 | 78 |
| background_boundary | 0 | 288 | 6855 |
| background_boundary | 0 | 289 | 252 |
| background_boundary | 0 | 291 | 516 |
| background_boundary | 0 | 578 | 900 |
| background_boundary | 2 | 289 | 216 |
| completeness | 0 | 288 | 182 |
| completeness | 0 | 291 | 6 |

The180 background-family groups retain prior98 ambiguous producer /45 non-longest crossing /37 touching-or-no-proper-crossing categories. Next: ordered E2 provenance to disambiguate producer identity; general crossing/cancellation and chain-successor topology for non-longest/touching cases. The188 completeness rows need cell-local representability/required-type analysis. No catch-all, no new spool pin.

## History, reproducibility and limitations

This explicitly rejects 3-12’s “faithfully clips” claim: invalidity/producer identity were correct but did not establish cause. That report and its prior spool tables remain preserved with a supersession notice. S02 and S05 were independently retested before changing their cause; untouched O02/O04 have separate historical evidence and are outside this brief’s owned rules. Remainder **9064** and PARTITION FAIL persist unchanged (Sonnet limitation D).

Final accepted markers: oracle_final.EXIT0 (corrected1082.3s), exact_recheck.EXIT0 (S02 and covers), cf.EXIT0, cf291_dump.EXIT0, covers.EXIT0, pairs.EXIT0, refine_pairs.EXIT0, tail.EXIT0, tail_census.EXIT0, classify.EXIT1 (expected), audit.EXIT0. Original library content hash remains `c76b511e073c1e76b9ab82ce87bd7ff3b16ca6b729379ad210c34a9536e06254`. No full-disc build or dump. All heavy jobs use flock output/.heavy.lock serially; buildj4/K1j1; config/temp output local.

An exact-oracle implementation bug removed both adjacent duplicate corners during simultaneous collinear cleanup, creating a shortcut. Diagnosed using native row769084/source5756259; fixed by deduplicating adjacent points first, then removing collinear forward-only points. Duplicate-square/bowtie/OR/vertical-jump regressions pass. The entire5905 oracle,300 S02 oracle and3 covers were rerun after the fix; previous results archived in `pre_duplicate_fix/` are not final evidence. Scratch pair decode initially used wrong uint16 endianness; corrected before accepted pair run. Reporting/resume script bugs were corrected and rerun.

Run-control deviation: interrupted shell descendants initially retained the lock. Recovery invalidated only this unit’s generated shared library, producing two diagnostic SIGBUS135 exits; subsequent own product rebuilt unchanged. No crash reports created outside repo were observed. Later wrappers bound actual child process groups with timeout and terminal markers; core dumps disabled, no pgrep loops or cache drops. Historical checkpoint statements identify intermediate results; this report supersedes them. Unrelated concurrent parser/performance/provenance edits were preserved.

Reproduce commands and side-table provenance are appended in `docs/provenance.md`. Mandatory requested reviewer/model: Sonnet5.5, concrete readonly prompt in `review_prompt.md`, isolated repo-local `run_review.py`; acceptance must be actual independent findings, never CLI availability. Review outcome appended below and in [review_3-13.md](review_3-13.md).

## Mandatory review outcome

**ACCEPT-WITH-CONDITIONS** (Sonnet 5.5 / `claude-sonnet-5-5`, 2026-10-03 ~04:39–04:48 AEST). Full independent write-up: [review_3-13.md](review_3-13.md). Reviewer scripts/logs under `output/scratch-3-13/review/s55/`; no builds/dumps/commits by the reviewer.

**Must-fix (findings 1–3).** (1) ~15% of checked `witness` points disagree with original-double EO — robust evidence is failing vertex + outline distance; do not claim every group has a rational interior witness. (2) “5905 regions differ” is vertex-test cardinality (~5399 keys / ~5227 leaf,type); ~19% lack macro-area error — use vertex+outline, not area, for those. (3) R01 exclusivity unproven — L0/291 window’s 31 type-291 `in_eo_same=1` fills may overlap build; not tested beyond that window.

**Limitations (findings 4–6 + D).** A stratified-sample not exhaustive; B group-level near-tail support, not per-row for all 15002; C `clip_right_inside` hypothesis only (~79%, no rule); D **9064** unattributed + expected PARTITION FAIL unchanged. S02–S05→build reclassification stands. Final checks in `final_checks.json`.
