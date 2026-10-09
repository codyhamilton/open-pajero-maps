background: checker 920,786 + build 0 + spool 517,648 + unattributed 137 = 1,438,571; background_boundary: checker 0 + build 0 + spool 16,541,304 + unattributed 8,739 = 16,550,043.

# Unit 3-12 — residual attribution on the new disc

**Status: ACCEPT-WITH-CONDITIONS (review_3-12) — science follow-up closed in 3-13.** Independent review of 3-12 is recorded in [review_3-12.md](review_3-12.md) (verdict ACCEPT-WITH-CONDITIONS A–D). Counts and invalidity witnesses from 3-12 stand as historical measurement. Unit **3-13** (`causes_rootcause.md`, [review_3-13.md](review_3-13.md)) accepted S02–S05→**build** (spool-pin superseded); honesty + `rules_bg.json` flip landed (`aa7e840` / `a9432c1`). Condition D remains: keep the **9,064** remainder unattributed; PARTITION FAIL stays honest. Live residual / root-cause SoT is **3-13** + current `rules_bg.json`, not this 3-12 body alone.

The measured disc is `output/scratch-3-11/G_new/ALLDATA.KWI`, SHA256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`. Inputs are `dump_new_ext` and `classify_new`. Historical 3-07/3-08 counts concern the old disc: new-disc R01 is **920,786**, not 920,773; boundary residual is **14,610,990**, not 14,610,516. The +13 fill and +474 boundary rows were decoded by 3-11. S02 is preserved at 1,939,053 rows with its existing predicate and priority. Established sentinel, onb, R01/S02 and counterfactual facts are cited from [causes_bg.md](causes_bg.md) and [review_3-07.md](review_3-07.md), not re-derived as new discoveries. The 3-08 completeness repair evidence is carried by an exact full-key join.

## Partition and new rules

| Kind | Checker before → after | Build before → after | Spool before → after | Unattributed before → after | Total |
| --- | --- | --- | --- | --- | --- |
| background | 920,786 → 920,786 | 0 → 0 | 0 → 517,648 | 517,785 → 137 | 1,438,571 |
| background_boundary | 0 → 0 | 0 → 0 | 1,939,053 → 16,541,304 | 14,610,990 → 8,739 | 16,550,043 |
| interior_cover | 0 → 0 | 0 → 0 | 821 → 824 | 3 → 0 | 824 |
| completeness | 495 → 495 | 0 → 0 | 56 → 56 | 188 → 188 | 739 |
| name_anchor | 0 → 0 | 0 → 0 | 1 → 1 | 0 → 0 | 1 |


All five kinds: checker **921,281 → 921,281**, build **0 → 0**, spool **1,939,931 → 17,059,833**, unattributed **15,128,966 → 9,064**; sum **17,990,178**. `classify/partition.txt` reports **PARTITION FAIL** (expected exit 1). No catch-all rules. O06 has zero rows on the new disc, following 3-11; it remains in the unchanged other-kind rules.

| Rule | Cause | Kind | Rows | Groups | Distinct recorded source rings |
| --- | --- | --- | --- | --- | --- |
| S03 | spool | background | 517,648 | 30,547 | 24,731 |
| S04 | spool | background_boundary | 14,602,251 | 216,319 | 70,911 |
| S05 | spool | interior_cover | 3 | 3 | 3 |


**Mechanism for all three new rules:** the unchanged build faithfully clips an explicitly closed spool ring whose longest closing edge properly crosses a nonadjacent edge; the crossing-removal controls eliminate outside pieces. Each rule predicates on `residual_crossing_verified == 1`, a u8 recorded join on the complete `(level,ix,iy,code,p0..p6,shape)` key. Status 1 requires a **unique byte-exact original producer**, no E1 cover substitution, explicit closure, closing = longest edge, and at least one proper closing-edge crossing. No rule uses a list of cells, a tuned distance/size threshold, nearest-source identity, or the diagnostic sentinel as producer identity. R01/S02 run first, and the assignment audit verifies every inherited assignment unchanged and no new rule stealing an existing row.

Source identity comes from all own records plus unchanged E1 routing with **all original source cells retained** and receiver existence bits for the complete residual receiver set. The unchanged repository C ring encoder is exposed by a scratch shim compiled with `-O2 -ffp-contract=off -fPIC`; it clips against the actual integer leaf rectangle using the build's exact `kw_bounds` arithmetic. Actual G_new record bytes, rather than a nearest polygon, are compared. Full scan: **425,416 group/stratum entries**, **30,558 distinct fill groups**, **216,488 distinct boundary groups**, and **3 cover groups**. Mixed sentinel/non-sentinel or mixed-kind pieces can occur twice in that entry count. **70,999 distinct qualifying source rings** are evidenced across these groups; per-rule source counts overlap and must not be summed as a distinct total. `side_<kind>.npy`, `build_producers.jsonl` and `pins_residual.tsv` record the identities/topology and native assigned contributions. The former pin cap is not used.

## Independent witness and counterfactuals

Fresh seed **2026100213**, uniform sampling without replacement from unique full group keys **after** the producer predicate; 200 groups per `(kind,level,type,sentinel status)`, census when fewer. The validity code has no K1 or `quantisation_roundtrip` import and uses every original spool shape of the level, with exact bbox lower bounds only to prune an unbounded distance search. Fill validity is even-odd interior of a same-type polygon; boundary validity is **0.500001 raw Chebyshev**. Source geometry and invalidity are separate tests. Results: **S03 1,994/1,994 INVALID; S04 2,062/2,062 INVALID; S05 3/3 INVALID** at actual leaf centres. Files: `qualified_samples.jsonl`, `qualified_witness.jsonl`, `qualified_witness_summary.json`, `witness_S05.jsonl/.txt`. An initial independent broad sample (seed 2026100212, 4,056 vertices) also had zero valid points or EO diagnostic mismatches. The 298 exception group/stratum first vertices likewise are all INVALID; this is not a build/spool attribution.

**Validity-contract discrepancy retained:** 3-07 Amendment 4 says boundary validity is outline-only, whereas current `_k1_bg.c:k1_bg_kinds` and the Python oracle also accept a boundary point inside a same-type polygon. This unit follows the explicit amended witness criterion. Every sampled residual boundary point is outside same-type interiors as well, so this difference does not rescue or change the attributed sample. R01 likewise follows the amended fill-interior criterion, while current K1/Python still demand a fill outline. No rule/tolerance was silently changed in either checker.

| Kind | Level | Type | Sentinel | Sampled groups | Valid | Same distance >64 | Any distance >64 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| background | 0 | 288 | False | 200 | 0 | 0 | 0 |
| background | 0 | 288 | True | 200 | 0 | 200 | 184 |
| background | 0 | 289 | False | 200 | 0 | 0 | 0 |
| background | 0 | 289 | True | 200 | 0 | 200 | 149 |
| background | 0 | 291 | False | 200 | 0 | 0 | 0 |
| background | 0 | 291 | True | 200 | 0 | 200 | 172 |
| background | 0 | 578 | False | 200 | 0 | 0 | 0 |
| background | 0 | 578 | True | 200 | 0 | 200 | 141 |
| background | 2 | 289 | False | 200 | 0 | 0 | 0 |
| background | 2 | 289 | True | 194 | 0 | 194 | 192 |
| background_boundary | 0 | 288 | False | 200 | 0 | 0 | 0 |
| background_boundary | 0 | 288 | True | 200 | 0 | 200 | 183 |
| background_boundary | 0 | 289 | False | 200 | 0 | 0 | 0 |
| background_boundary | 0 | 289 | True | 200 | 0 | 200 | 167 |
| background_boundary | 0 | 291 | False | 200 | 0 | 0 | 0 |
| background_boundary | 0 | 291 | True | 200 | 0 | 200 | 189 |
| background_boundary | 0 | 578 | False | 200 | 0 | 0 | 0 |
| background_boundary | 0 | 578 | True | 200 | 0 | 200 | 148 |
| background_boundary | 2 | 289 | False | 200 | 0 | 0 | 0 |
| background_boundary | 2 | 289 | True | 200 | 0 | 200 | 197 |
| background_boundary | 6 | 288 | False | 30 | 0 | 0 | 0 |
| background_boundary | 6 | 288 | True | 32 | 0 | 32 | 32 |


The already established crossing-removal mechanism was **re-run**, without changing code or rewriting the original/recorded modified spools, against G_new. `cf_current/type291`: original window `[828,831) × [745,748)` matches **9/9 G_new frames**, including padding; source `(L0,829,746,record81)` coordinate33 removed in the recorded modified spool. Modified serial and four-worker builds have identical SHA; K1 j1 boundary **829→589**, fill **69→69**. `cf_current/type288`: original `[1769,1772) × [202,205)` matches **9/9 G_new frames**; source `(1765,216,record0)` coordinate10 removed. Modified j1/j4 match; K1 fill **32→0**, boundary **255→0**, cover **1→0**. All claimed original producer pieces are removed in the archived exact piece tests and fresh record differences; counts alone are not used to credit other sources. The remaining 589 type291-window boundary failures are not assigned from that aggregate residual. All original CF selection/topology/piece-disappearance evidence is in scratch-3-07; fresh outcomes, G gates and j1/j4 manifests are under scratch-3-12/cf_current.

The type288 counterfactual completeness **0→1** is the established source-home effect: removal flips home-centre parity at `(1765,216)`, outside the emitted receiver window. Type291 completeness **1,747→1,747** includes required absent out-of-window cells in this small-disc run. Neither is attributed from a window aggregate. These are window controls, not new full-AU K1 timing measurements. Small K1 walls actually run were 3.7/4.8s (type291 before/after), 4.3/4.4s (type288); no Flash or full-disc K1 wall is claimed.

`cf_piece_audit.json` additionally checks the actual **new-rule** pieces against the fresh modified disc in the same cells: type291 removes both producer-identified S04 pieces (**29 newly assigned rows**, beyond the carried 209 S02 rows); type288 removes the source-identified S03 fill piece (**31 new rows**) and all three S04 boundary pieces (**255 new rows**) in the control window. The full 32-fill reduction also includes one previously checker-classed R01 vertex, which is not credited to S03. Aggregate reductions are not substituted for these exact row/piece identities.

## Column-first measurement and producer correction

`column_study.json` has exact row-weighted histograms/quantiles for each residual kind/level/type/sentinel stratum: `onb`, frame coordinates/1024 multiples, `dnv`, nearest-source `src_nv/src_maxseg`, censored `d_src/d_any`, parity flags, nearest any-type code, depth. `geometry_distributions.json` joins every residual fill/boundary row to the actual leaf rectangle and gives side/corner/interior counts and exact frame-edge coordinates; source n, bbox width/height, max edge and ownership distributions are group/stratum weighted, explicitly not row-weighted. Source size for a sentinel is obtained from a demonstrated producer, not invented from the sentinel columns.

There are **13,028,968 residual sentinel boundary rows**. Only **1,126** residual boundary rows have `dnv=4`; many clipped/densified pieces have 100+ vertices, so rectangle vertex count cannot establish synthetic origin. The 64-raw same-type and 2-raw any-type diagnostic windows are censoring limits: NaN is not an unbounded distance. Full witness distances are recorded separately. No distance population gap justifies loosening the 0.500001 criterion; finite same-type residual distances approach that limit continuously. Every strict rule uses topological predicates and an exact record match, not a numerical size cut.

| Boundary sentinel level/type | Rows | dnv p10/p50/p90 | Actual leaf-edge rows | Interior rows | Leaf-corner rows | onb=0 leaf-edge rows |
| --- | --- | --- | --- | --- | --- | --- |
| L0 T288 | 2956345 | 91 / 132 / 179 | 2956345 | 0 | 91051 | 996 |
| L0 T289 | 394514 | 104 / 146 / 236 | 394514 | 0 | 12135 | 525 |
| L0 T291 | 9188792 | 125 / 145 / 193 | 9188792 | 0 | 282859 | 6416 |
| L0 T578 | 376228 | 90 / 137 / 179 | 376228 | 0 | 12239 | 9946 |
| L2 T289 | 109364 | 135 / 183 / 421 | 109364 | 0 | 3365 | 0 |
| L6 T288 | 3725 | 135 / 143 / 158 | 3725 | 0 | 122 | 80 |


**Do not silently reconcile the producer contradiction:** the first full probe used walker-derived floating bounds, yielding eight no-match items (five boundary groups and three covers). H12 tested the hypothesis that the probe's arithmetic differed from the build: copying `kw_bounds`' exact operation order resolved **8/8** to original crossing-closing producers, and the **entire** scan was repeated with that arithmetic. Definitive evidence is `build_producers.jsonl` (141.5s forensic time), not the retained old `full_producers.jsonl` (135.3s). The covers now identified are `(1792,395,path352,shape6) ← (1792,396,record4)`, `(1801,395,path361,shape10) ← (1801,396,record0)`, `(1805,395,path365,shape517) ← (1805,396,record171)`, all L0/type291. This repairs a forensic query, **not a checker cause or a tolerance change**; the historical no-match statements are superseded by tested exact provenance. The first scratch study also briefly mistook assignment0 for unassigned; corrected to the native65535 sentinel and all accepted outputs were rerun.

A separate diagnostic issue surfaced in the full leaf join: dump path fields beyond `depth` can retain prior child components. Example fill row 8679 has depth 1 but `(p0,p1)=(529,3)`; its actual G_new leaf is path `[529]`. `_d1.c` copies all seven walker path slots into the leaf row and decrements `path_n` without clearing a popped slot; `_k1.c:k1_make_sample` copies all slots onward. Leaf geometry queries now explicitly truncate at depth; producer probes already did so. Complete native group keys, side-table keys and original bytes remain unchanged. Geometry census confirms **all 14,610,990 residual boundary rows are on actual leaf edges**, including all 24,964 current residual rows with diagnostic `onb=0`; all 517,785 residual fill rows are interior to their leaves. This path diagnostic issue moves no failure count and was not fixed.

## H8–H12 — tests, outcomes, credited rows

| Hypothesis | Test / outcome | New attributed rows |
| --- | --- | --- |
| H8 synthetic complements/covers | All-source E1 + own-record byte probes on every residual piece; no cover substitutions and no unmatched records after build-arithmetic correction. All 4,056 broad sampled fill/boundary points invalid. Complement/cover hypothesis fails; unsupported checker/build attribution. | 0 |
| H9 leaf clipping / tolerance window | Full actual-leaf edge census; all-level first-vertex distance/interior witnesses (broad sample + independent qualified sample +298 exception census). No tolerance/window validity rescue; frame1024/2048/3072 onb mismatch is the established diagnostic issue. | 0 |
| H10 type remap / merge | Every exact original producer has the disc type code; producer C writes tc&0xffff, E2 copies source type, D1 decodes it directly. All-type proximity/containment occurs without a producer-code mismatch. No remapping observed. | 0 |
| H11 source outside K1 window | All level shapes in independent witness, no home ring/tall/radius exclusions; all 4,056 + 4,056 sampled vertices and all 298 exception vertices invalid. Omitted valid source not observed. | 0 |
| H12 crossing-closing provenance | Exhaustive exact producer identity + original topology, fresh independent rule-stratum witnesses +G_new-gated source-only counterfactuals. Supported S03/S04/S05. Generalised all-residual strict hypothesis fails on 180 groups with other topology or ambiguous identity. | 15,119,902 spool |
| H12 forensic frame arithmetic | All eight missing byte matches resolved by build kw_bounds arithmetic; entire source probe repeated. Includes three cover rows and boundary rows credited only through actual qualifying sources. | Included above; no separate checker/build rows |


No new checker or build mechanism is established. Therefore there is no new build-code fix proposal. If later work finds a checker window/tolerance/type cause, `_k1_bg.c:k1_bg_kinds` and Python `quantisation_roundtrip.py:_check_block`/`Region` must change in lockstep with an independently VALID witness. Under the explicit amended contract, the carried R01 fix remains the non-boundary interior rule at those locations; it does not explain these residual outside points.

## Every remaining group: failed test and next predicate

| Kind | Level | Type | Remaining rows |
| --- | --- | --- | --- |
| background | 0 | 288 | 52 |
| background | 0 | 289 | 7 |
| background | 0 | 578 | 78 |
| background_boundary | 0 | 288 | 6,855 |
| background_boundary | 0 | 289 | 252 |
| background_boundary | 0 | 291 | 516 |
| background_boundary | 0 | 578 | 900 |
| background_boundary | 2 | 289 | 216 |
| completeness | 0 | 288 | 182 |
| completeness | 0 | 291 | 6 |


`remaining_groups.tsv` enumerates every full key and native row count: **180 fill/boundary groups and 188 completeness groups**, 368 total (groups from different kinds remain separate). `exception_tests.jsonl` records exact producer candidates, fresh proper-crossing sweep, direct original/penultimate-repair probe outcomes, failed strict hypothesis and next untested predicate for each of the 180; `exception_witness.jsonl` separately witnesses all 298 sentinel/non-sentinel first-vertex strata. `small_hypotheses.jsonl` maps all 188 completeness keys to their accepted failed repair probes. No remaining group lacks a tested hypothesis.

| Remaining bg hypothesis failure | Distinct kind/group keys | Next untested predicate |
| --- | --- | --- |
| Unique exact producer is not established:2+ candidate rings match the same record | 98 | Ordered E2 class-2 record-sequence provenance, including divided-leaf keep-order; do not choose a nearest ring. |
| Closing edge properly crosses but is not the longest; strict mechanism predicate fails | 45 | G-gated window removal of this non-longest closing crossing, with independent resulting validity; do not remove the longest condition by analogy. |
| No proper closing-edge crossing; fresh full proper-crossing sweep also finds none | 37 | Nonadjacent touches/collinear overlaps and independent clip/densify/round comparison on the actual leaf. |


The 188 completeness rows are 182 L0/type288 +6 L0/type291. The accepted source-only one-coordinate repair leaves an independently deep-vertex requirement and still no C piece for 187 crossing/quantisation interactions; one cell `(1712,1274,type288)` has mixed crossing/simple-collapse sources. Hence neither defective source topology alone nor an empty C clip proves the required attribution. Next: independently measure cell-local representability after a **complete** topology repair, over every meeting source. Exact original evidence: scratch-3-08/completeness_repair.jsonl and causes in [cause_table.md](cause_table.md); no new counterfactual is claimed for these rows.

**3-15 update (complete topology repair):** the 188 were each decomposed into their even-odd simple faces (3-13 `split.decompose`) and re-tested under the builder clip/densify/round contract: 885 faces / 189 meets, 205 clip into the target cell, **0 representable** (0 quantised area, 0 C records). All 188 are **`checker:repaired-not-representable`** (sub-unit-width slivers). The 3-14 disc moved the completeness key set by 89 added / 52 cleared (net +37): the 89 added were satisfied by the pre-3-14 encoder and dropped by the EO stitch, the 52 cleared are now satisfied (contract comparison, `scratch-3-08/probe_bg.so` vs the 3-14 stitch probe). Recount 776 = O01 363 + O05 132 + O04 7 + unattributed 274. Full note [completeness_3-15_cell_local.md](completeness_3-15_cell_local.md).

This is stop(b), not an assertion of complete attribution. No nontrivial valid outside-source clipping defect is guessed as build. The separately carried source 65623 question is not assigned by similarity to these rings; its established no-proper-crossing result stands. No Phase 4 work or fixes.

## Provenance, reproduction and review limitations

The dump side-table extension is recorded in [docs/provenance.md](../../../provenance.md). `extend.py` copies the current 152-byte dump and populates previously padding byte 146; every other byte is compared against the original. `dump_ext/dump_manifest.json` records the new column and original extension. Committed rules require these uncommitted recorded side tables/dump; original manifest-only classify cannot use S02/new fields. Scratch scripts and evidence are gitignored. `rules_all.json` combines updated bg rules with unchanged other rules, with no catch-alls.

All heavy jobs ran serially under `flock output/.heavy.lock`; cbuild was serial, window builds used 1/4 workers, K1 controls used 1 (never beyond 6); no cache drops, pgrep waits, code fixes, commits, Phase 4 or writes outside the repository. Protected scratch-2-07, scratch-3-06 and old scratch-3-11/G stayed read-only. About 2.3GiB free remains, so no second full-disc dump/build was made. Existing modified spool copies were read-only reused for the controls. The mandatory Sonnet 5.5 review has **not** been completed; provide this result and ask the reviewer to choose an independent sample and rerun the witness, under the same lock. Native partition remains FAIL and Phase 3 sign-off is not justified.

**Plan 46 note (2026-10-08).** The 180 groups / 8,876 rows above now have committed row identities from the tracked producer scan (`historical_bg/p6_producer/identity_remainder.tsv.gz`, R-G8-4-c discharged). Per-row verdicts are in `historical_bg/p6_producer/verdicts.tsv.gz`:
- build:eo_bg_stitch: 4,214 rows / 81 groups (119 background, 4,095 boundary);
- producer_ambiguous: 4,612 rows / 98 groups (R-G5-2-a 18, R-G5-1-a 4,594). This is the same 98-group "2+ candidate rings" class as the table above;
- source-removed: 50 rows / 1 group (R-G5-1-b).

The historical tables in this file are unchanged as history. See `residuals.tsv` and `docs/plans/46-bg-producer-scan-rebuild.md`.

**Plan 62 note (2026-10-09).** Plan 62 re-decided the R01 residual of plans 44/45 (R-G5-4-a/b 7,316 rows, R-G5-4-c 80) under the plan-46 producer (`historical_bg/p9_r01_residual/`). It ablated each fix singly over every residual group.
- **6,597 rows are build:eo_bg_stitch.** The fix that moved them:

  | Fix | Rows |
  | --- | ---: |
  | RC2 | 3,405 |
  | RC3 | 2,525 |
  | RC2 and RC3 (each necessary) | 32 |
  | RC4 | 605 (525 skip + 80 R-G5-4-c) |
  | RC5 | 25 |
  | Plan-44 Unit 4f defect | 5 |

  The Unit 4f defect: it took the first ring of the producer home instead of the producer ring.
- **No `producer_home_outside_R_cap` row remains.**
- **Same-type audit:** all 87,743 proven rows have a same-type producer.
- **Children:**
  - R-G5-4-a-1: 222 producer_ambiguous (plan 63);
  - R-G5-4-a-2 and R-G5-4-b-1: 32 + 545 source-removed, clip empty on d35b565 (plan 64).

**Plan 63 note (2026-10-09).** The 98-group "2+ candidate rings match the same record" class (table above; R-G5-1-a 4,594 + R-G5-2-a 18 rows) is resolved by the predicate this file named: ordered E2 class-2 record-sequence provenance, including divided-leaf keep order, with no nearest-ring choice.
- **Proof.** An output-neutral source-tag sidecar on the `33006aa` encoder (`historical_bg/p7_producer_tie/sidecar/sidecar_33006aa.patch`).
  - 2,085/2,085 window frames are byte-equal to 013586b5.
  - The sidecar matches the plan-46 scan on 398,324/398,324 unique-byte records in all 1,770 window cells (14,211 in the 46 tie cells); 581 of these are the same source in E1 interior-cover form.
- **Result.** Every ambiguous record is one of two byte-identical copies, and each copy is emitted by a distinct candidate.
- **Rule.** The copies follow `enc_bg` class-major order over the merged ordinal: own backgrounds first, then E1-routed items by source (iy, ix), k.
  - Accepted: 537/537 derivation and 546/546 holdout, with the code path cited.
  - Rejected: key order, nearest home, spool / global / block order, distinguishing-piece order and first emitter.
- **Verdicts.** All 4,612 rows are build:eo_bg_stitch under the unchanged phase-23 limb (`verdicts_ambiguous.tsv.gz`).
- **Scope delta.** S′ = S ∪ 6 groups (145,960 / 11,127,845; a(S′) = 15,080) comes from one opt-in `gate_repro --s02-scope full --s02-resolve` run.
  - Measured: res entries 305,225 (+3 cover), res bnd groups 204,121.
  - S04 status-1 groups stay at 203,954, against the identity's 203,952. The 2 are the (1481,1288) all-sentinel groups: the resolution does not set `residual_crossing_verified`, by design.
  - The historical remainder 137 / 8,739 stays the plan-46 gate.
- **New finding, R-G5-6.** G holds byte-identical same-type duplicate records in 336,329 leaves (013586b5) and 336,135 leaves (0c22b266); R holds them in 0 leaves.

