background: checker 920,773 + build 0 + spool 0 + unattributed 517,785 = 1,438,558; background_boundary: checker 0 + build 0 + spool 1,939,053 + unattributed 14,610,516 = 16,549,569. S02 pins: 10,001 distinct source rings (>10,000), 25,772 verified groups; historical candidate stratum 145,960 groups.

# 3-07 attempt 3 — S02 carried as one rule (pin stop retired)

**Status: carried — the 10,000 pin stop is retired by the parent standing decision (no measurement story); S02 is carried as ONE `spool` rule with 1,939,053 rows evidenced (10,001 distinct identified source rings, 25,772 groups as evidence, not an exhaustive pinned list).** The ~9.19 M unvisited `background_boundary` rows and the ~14.6 M unattributed rows stay unattributed; no further Sol dispatch without new predicates.

Historical text follows. Attempt-3 Amendment 1 replaced the old group limit with the number of distinct source rings per rule; the audit stopped when this count exceeded 10,000. This is a partial source enumeration, not `blocked: unattributed`. The remaining ~5.9M rows were not investigated further after that stop. No build cause is guessed from invalidity alone. Full attribution and the Phase 3 outcome remain unmet.

R01 and the accepted attempt-2 S02 mechanism, independent witnesses and byte-gated counterfactuals remain the evidence base. Review item 6(a) additionally requires actual producer identity before retaining S02 attribution. The historical S02 predicate selects 11,127,845 rows; this attempt retains **1,939,053** rows whose original disc pieces have a uniquely identified defective source ring. The **9,188,792** other historical S02 rows are held unattributed (9,188,473 unvisited; 319 without an exact producer match). This narrows application of the accepted rule; it does not discard its mechanism or prior sample evidence, or assign the 589 counterfactual residual by analogy.

Only the owned triage files and `output/scratch-3-07/` changed. Original dump/G/code and protected scratch directories remain untouched. No agents, commits, pushes, cache drops or fixes. Every heavy run held `output/.heavy.lock`, serially; all build/checker counterfactual evidence uses one worker. The existing Sonnet review is preserved unedited; no new agent review was requested because this worker must not spawn agents.

## Validity and first-step investigation

The sentinel, source-concentration, leaf-frame and H4 investigations below are retained accepted attempt-2 evidence. Attempt 3 reruns producer enumeration, the S02 witness and the final partition, and audits the archived counterfactuals; it does not restart that accepted baseline.

Amendment 4 controls this attribution: `background` is valid only by even-odd interior of some same-type level polygon; `background_boundary` is valid only within **0.500001 raw Chebyshev** of a same-type outline (`K1_TOL=0.5`, `K1_EPS=1e-6`). The witness uses each selected dump row's lat/lon, converts to the level's global raw lattice, and rounds to the integer point K1 actually queried. It imports neither `quantisation_roundtrip` nor any K1 implementation. Its numpy polygon/ray and segment-distance code considers **all** original spool shapes, without a cell ring, tall filter, or radius cap. Later witnesses use exact bbox lower bounds to prune search, retaining every possible closer outline. Nearest-source diagnostics are not treated as producer identity.

Sentinel investigation preceded hypothesis/rule work. Evidence: `sentinel_results.json`, eleven `sentinel_*.jsonl`, and `onb_results.json` under `output/scratch-3-07/`. There are **15,913,571 sentinel rows / 17,988,127 = 88.46708%**, not the amendment's stated 94.5%. Its six listed counts themselves sum to 15,913,571.

| Kind | Level | Type | Sentinel rows | Groups | Sampled groups | Valid | Same-type distance >64 | Any-type distance >64 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| background | 0 | 288 | 469,112 | 22,853 | 200 | 177 | 200 | 185 |
| background | 0 | 289 | 23,673 | 1,113 | 200 | 97 | 200 | 158 |
| background | 0 | 291 | 434,419 | 21,113 | 200 | 95 | 200 | 180 |
| background | 0 | 578 | 14,377 | 624 | 200 | 69 | 200 | 149 |
| background_boundary | 0 | 288 | 2,956,051 | 51,695 | 200 | 0 | 200 | 184 |
| background_boundary | 0 | 289 | 394,514 | 5,945 | 200 | 0 | 200 | 126 |
| background_boundary | 0 | 291 | 11,127,845 | 145,960 | 200 | 0 | 200 | 179 |
| background_boundary | 0 | 578 | 376,132 | 4,708 | 200 | 0 | 200 | 127 |
| background | 2 | 289 | 4,359 | 236 | 200 | 87 | 200 | 199 |
| background_boundary | 2 | 289 | 109,364 | 1,334 | 200 | 0 | 200 | 197 |
| background_boundary | 6 | 288 | 3,725 | 32 | 32 | 0 | 32 | 32 |

Every one of the 2,032 sampled groups is genuinely farther than 64 raw from a same-type outline. Every sampled parity flag agrees with the dump. Thus the same-type radius is not hiding near-outline validity in these samples: the sentinel combines real interior fills (525/1,000 fill samples valid under the amended rule) and genuinely outside pieces. All 1,032 boundary samples are invalid. Any-type diagnostics have only a **2 raw** radius, so their NaNs cannot measure unbounded any-type distance. All-level distances are recorded independently above. The sentinel cannot be used as a producer identity or a blanket cause for fills.

**All 31,416 `background_boundary` rows with `onb=0` were verified against G's actual leaf metadata:** all are on the leaf boundary. All have parent frame range 4096, while their internal sub-cell edges occur at frame coordinate 1024, 2048 or 3072. `_k1_bg.c:k1_diag_fill` (around line 567) compares only with 0/4096; the actual kind selection (around line 634) compares global lattice coordinates with the leaf bounds. For example row 94050 is `(L0,1833,341,path[681,0])`, frame `(120,2048)`, global `(7508088,1398784)`, on its leaf's top boundary. `onb=0` is a diagnostic mismatch, not a real non-boundary point. No rule uses it as validity. Evidence: `onb_rows.jsonl`, `onb_boundary_frame_values.json`. Boundary-axis frequencies can count a corner twice.

Fresh full dump scan also finds zero `d_src <=0.500001` rows in either kind, zero rows where the dump's same-type parity/winding union flags differ, and class 2 for every row. Other-type proximity is not evidence of a type remapping. Evidence: `column_counts_attempt2.json`.

## Source concentration (original step 1)

The fresh locked `k1_triage.py summary` completed in 140s. Its four required background tables are byte-identical to 3-05, independently verified. The top 30 aggregate both kinds by `(type, level, src_ix, src_iy, src_rec, src_tall)`. Their **15,921,626 rows / 17,988,127 = 88.51186%**, below 90%, required column-led investigation. `by_src.tsv` is capped at 5,000 entries: an omitted entry is no larger than 33 rows; two omitted kind entries cannot displace the smallest top-30 aggregate (219). Sentinels are unknown source identities.

| Rank | Type | Level | Source (ix,iy,record,tall) | Rows | Share | Cumulative |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 291 | 0 | sentinel (unknown source) | 11,562,264 | 64.27720% | 64.27720% |
| 2 | 288 | 0 | sentinel (unknown source) | 3,425,163 | 19.04124% | 83.31844% |
| 3 | 289 | 0 | sentinel (unknown source) | 418,187 | 2.32479% | 85.64324% |
| 4 | 578 | 0 | sentinel (unknown source) | 390,509 | 2.17093% | 87.81416% |
| 5 | 289 | 2 | sentinel (unknown source) | 113,723 | 0.63221% | 88.44637% |
| 6 | 288 | 6 | sentinel (unknown source) | 3,725 | 0.02071% | 88.46708% |
| 7 | 288 | 0 | 1279,1294,0,1 | 756 | 0.00420% | 88.47128% |
| 8 | 288 | 0 | 2209,1058,0,1 | 696 | 0.00387% | 88.47515% |
| 9 | 288 | 0 | 1891,893,0,1 | 610 | 0.00339% | 88.47854% |
| 10 | 288 | 0 | 1621,322,0,1 | 440 | 0.00245% | 88.48099% |
| 11 | 288 | 0 | 1248,1536,0,1 | 422 | 0.00235% | 88.48334% |
| 12 | 288 | 0 | 1248,1513,0,1 | 371 | 0.00206% | 88.48540% |
| 13 | 288 | 0 | 1765,1729,0,1 | 366 | 0.00203% | 88.48743% |
| 14 | 288 | 0 | 1131,1684,0,1 | 364 | 0.00202% | 88.48946% |
| 15 | 288 | 0 | 2149,1371,0,1 | 302 | 0.00168% | 88.49114% |
| 16 | 288 | 0 | 1204,1272,0,1 | 292 | 0.00162% | 88.49276% |
| 17 | 288 | 0 | 1363,1438,0,1 | 282 | 0.00157% | 88.49433% |
| 18 | 288 | 0 | 1298,931,0,1 | 268 | 0.00149% | 88.49582% |
| 19 | 288 | 0 | 1189,659,0,1 | 267 | 0.00148% | 88.49730% |
| 20 | 291 | 0 | 1792,1458,0,1 | 262 | 0.00146% | 88.49876% |
| 21 | 288 | 0 | 1222,1398,0,1 | 255 | 0.00142% | 88.50018% |
| 22 | 291 | 0 | 1814,629,0,1 | 253 | 0.00141% | 88.50158% |
| 23 | 288 | 0 | 756,1549,0,1 | 246 | 0.00137% | 88.50295% |
| 24 | 288 | 0 | 1781,1613,0,1 | 241 | 0.00134% | 88.50429% |
| 25 | 288 | 0 | 1011,942,0,1 | 238 | 0.00132% | 88.50561% |
| 26 | 288 | 0 | 1612,1304,0,1 | 234 | 0.00130% | 88.50691% |
| 27 | 288 | 0 | 1573,860,0,1 | 225 | 0.00125% | 88.50816% |
| 28 | 288 | 0 | 1612,946,0,1 | 224 | 0.00125% | 88.50941% |
| 29 | 291 | 0 | 1644,1292,2,0 | 222 | 0.00123% | 88.51064% |
| 30 | 288 | 0 | 1248,1608,0,1 | 219 | 0.00122% | 88.51186% |


## R01 — checker: fill tested against an outline instead of an interior

- Predicate: `kind=background AND in_eo_same==1`.
- Mechanism: K1 demands same-type outline proximity for a non-boundary fill vertex that is valid by the interior rule explicitly imposed by Amendment 4.
- Rows: **920,773** (L0 918,297; L2 2,476). Enumerate groups: **49,042** (L0 48,816; L2 226).
- Independent witness: **200/200 VALID**, across all 7,546,320 L0 and 309,857 L2 spool shapes. Deterministic key sort, seed 20260930, stride 245, offset 142, first rule-assigned failing vertex of each selected group. No “near outline” rescue is used for fills.
- Evidence: `witness_R01.txt`, `witness_R01.jsonl`, `enumerate_R01.tsv`; assignment is the accepted attempt-2 `classify_bg` run; attempt-3 `classify_attempt3` reproduces exactly the same R01 rows. No counterfactual is required for a checker rule. Settles H7's changed kind-validity mechanism.

## S02 — spool: a crossing closing edge produces outside perimeter pieces (mechanism evidenced; application narrowed)

- Final predicate: `kind=background_boundary AND level==0 AND code==291 AND src_ix==-2147483648 AND s02_producer_verified==1`. The added field is a recorded producer side-table join; see the pin audit below.
- Mechanism: the spool ring's longest closing edge crosses its own outline, and the unchanged clipper emits outside pieces from that defective ring; removing the crossing removes the failing piece.
- Historical accepted candidate predicate: **11,127,845** L0 rows / **145,960** enumerate groups (`enumerate_S02.tsv`, preserved). Final producer-qualified application: **1,939,053** L0 rows / **25,772** groups (`enumerate_S02_attempt3.tsv`); **10,001 distinct pinned source rings** (`pins_S02.tsv`), reached the former pin stop (retired; no measurement story). The pins are evidence, not an exhaustive pinned list.
- Historical independent witness (preserved `witness_S02.*`): **200/200 INVALID**, same-type outline distance >64 raw in every sampled group, all-level parity/winding both outside. Historical enumerate selection uses seed 20260930, stride 729, offset 425. Every historical witness point is exactly the provenance-probed point (`accepted_evidence.json`).
- Independent producer attribution: all **200/200 disc piece records match original source-produced record bytes**, not just a nearest shape. All 200 producer rings are explicitly closed; their longest edge is the closing edge (`n-2`), with a proper crossing of another edge. E1 was run with the selected receiver existence bits, retaining all original source cells; the unchanged repository clipper was exposed by an owned scratch shim. Evidence: `producers_sentinel_background_boundary_L0_T291.json`, `producer_291_complete.log`.
- **Type-291 counterfactual:** original 3x3 window `[828,831)×[745,748)` reproduces **9/9 G frames exactly**, including padding. Source `(829,746,record81)`, n=35, has closing-edge crossings `[26,33]` and `[1,33]`. Delete only coordinate index 33, lat/lon `(-34.4360529,115.9231159)`, decrement `b_nstored` and `b_ncoords`, retain class/type/closure and all other content. The new n=34 ring has no proper crossings. The exact failing piece's original bytes **vanish**. K1 boundary failures in the window fall **829→589**; 240 failures were removed; the attempt-3 audit identifies 209 S02 rows in this producer's removed pieces; **the 589 residual is unexplained by this single-producer removal and is not assigned a cause from that count alone**. Background failures stay 69. Thus the prescribed outcome rule labels this mechanism `spool`. Evidence: `cf_291/{original/G_byte_gate.json,outcome.json}`, `cf_291_selection.json`, copied `spool_cf/drop_829_746_rec81_vertex33/change.json`.
- **Same-mechanism cross-kind control:** original 3x3 window `[1769,1772)×[202,205)` reproduces **9/9 G frames**. Source `(1765,216,record0)`, n=12, crosses at edges `[3,10]` and `[2,10]`. Delete coordinate 10, lat/lon `(-46.9384747,145.0316677)`; new n=11 has no proper crossings. K1 failures change `background 32→0`, `background_boundary 255→0`, `interior_cover 1→0`. Evidence: `cf_short_ring/{original/G_byte_gate.json,ring_geometry.json,outcome.json}`. This control establishes the same mechanism on type 288 but does not assign those other strata after the pinning stop.
- Evidences H7's independently named crossing-closing-edge mechanism (the `cf_291` counterfactual removed 240 of 829 window failures; the 589 residual is not counterfactually established, and the remaining S02 rows rest on the 200/200 witness and the producer match) and explains the outside-piece symptoms considered by H5/H6 in these experiments. It does **not** establish H4's specific claim about polygon 65623.

### Attempt-3 producer pin audit and side-table route

Fresh final-rule independent witness: **200/200 INVALID**, seed20260930, stride128, offset74, first assigned vertex in each selected key-sorted enumerate group. Unbounded nearest-outline and parity/winding queries use all **7,546,320 L0 shapes**, no cell window or tall pass, tolerance **0.500001 raw Chebyshev**. Evidence: `witness_S02_attempt3.txt`, `attempt3_witness/witness_S02.jsonl`. The original R01/S02 witnesses remain intact.

`pin_producers_attempt3.py` traversed actual G leaves and read each target background record byte string directly. It retained all original source cells, ran unchanged E1 with receiver-existence bits for the S02 cells, and considered both own and borrowed candidate records. The unchanged repository C encoder (exposed by the existing scratch shim, compiled with original flags) clipped every same-type candidate against the **actual leaf rectangle and frame range**. Exactly one byte-identical source-produced record is required. Nearest-source dump diagnostics play no part in producer identity. Synthetic interior-cover substitutions and ambiguous identities are not accepted.

For each unique exact match, fresh numpy computes explicit ring closure, the longest edge, proper nonadjacent crossings of the closing edge, and the original spool home/record identity. A pin requires the longest edge to be the closing edge and a proper crossing of that edge. `tall` is the original-spool geometric flag (bbox outside the home cell grown by one minus one raw unit), computed before clipping; it is not E1's edge/cover kind. Each pin is `(level, home_ix, home_iy, record, tall)`, with type, stored vertex count, crossing-edge indices, and attributed rows/groups.

| Rule | Distinct pinned source rings | Producer-qualified groups | Rows | Historical candidate groups | Pin stop |
|---|---:|---:|---:|---:|---|
| S02 | **10,001** | **25,772** | **1,939,053** | 145,960 | stop retired; carried as one rule |

The scan visited **25,775** groups before the immediate stop: 25,772 have the required unique producer; three groups / **319 rows** have no exact match; **120,185 groups / 9,188,473 rows** were not visited. `pins_S02.tsv` has one header and 10,001 data rows. Its rows/groups are the contributions discovered before the stop, **not complete totals for those shapes across G**; the full S02 shape count is not claimed. Evidence: `producer_matches_S02_attempt3.jsonl`, `pin_summary_attempt3.json`, and `side_background_boundary.npy`. The side table includes all historical S02 group keys, producer identity/topology when found, row counts and status (1 accepted; -1 no match; 0 unvisited). `side_background.npy` is empty: no fill producer attribution was attempted before the stop.

`extend_dump_attempt3.py` joins the side table on the complete group key `(level,ix,iy,code,p0..p6,shape)`, intersected with S02's original column predicate. It copies original fields unchanged into `dump_attempt3/` and appends `s02_producer_verified` (u8; 1 only for qualifying rows, otherwise 0). The original dump is untouched. Final `rules_bg.json` depends on this recorded extension for S02; a native classify against the original manifest alone cannot interpret the added field. Enumeration is through the native tool on the extended dump; no rule lists cells. Unvisited/no-match rows remain unclassified.

The accepted type291 counterfactual tests a pin that is actually in this list: `(L0,829,746,record81,tall0,type291,n35)`, closing edge33 crosses edges1/26. The side table identifies **two groups / 209 S02 rows** from that producer in its 3x3 window. `cf_291/pinned_rows_attempt3.json` checks both pinned original piece byte strings against the archived modified disc; **both pieces vanish** after deleting only vertex33. The original window's 9/9 G frame byte gate stands. K1 boundary count 829→589 removes 240 failures in total: 209 are rows in those pinned pieces; the remaining 31 removed failures are not credited to S02 here. The **589 residual is unexplained by this one-ring removal**. The original-G window separately has 761 producer-qualified S02 rows and 68 unattributed rows. Of those 761, 209 belong to the two disappearing pieces; **552 belong to persisting pieces with independently identified other producers and crossing topology**. Those other producers were not modified in this experiment; this is not a proof of their individual removal outcomes or a complete classification of the modified disc. Their original-G S02 attribution uses their own byte-exact producer evidence plus the witnessed mechanism/sample counterfactual, not the residual count or nearest-source analogy. Evidence: `cf_291/residual_audit_attempt3.json`, `audit_artifacts_attempt3.json`. This is the required sample test of identified producers; no blanket cause is assigned to the 589 residual.

**Review item 6(b), explained:** short-ring completeness changes **0→1** at source home `(1765,216)`, outside emitted receiver window `[1769,1772)×[202,205)`. That ring has no deep vertex in the home cell before or after. Independently recomputed home-centre parity changes **outside→inside** after vertex10 is removed. K1 completeness (`_k1_cmp.c`) includes original spool cells throughout the containing block/band, beyond rebuilt leaves; the newly required home cell has no emitted frame in this window. This is a window completeness effect, not a demonstrated new G defect. Exact crossing values and vertex-cell audit: `completeness_short_ring_attempt3.json`. No completeness cause is assigned or fixed.

## Hypotheses H1–H7

| Hypothesis | Tested / how | Outcome | Accepted rows |
|---|---|---|---:|
| H1 window omission | All-level independent parity and unbounded outline queries on 2,032 sentinel groups, plus final rule witnesses; inspected ring+tall selection. A relevant bbox either leaves the home ring and enters the tall set, or its home lies in the local ring. | No omitted valid source observed. Sentinels are genuinely distant outlines. Not a demonstrated cause. | 0 |
| H2 collinear scan-line tolerance / float-key tie | Read exact C interval handling and the 2-04 amendment; scanned full diagnostic near-distance columns; tested the corrected outline criterion independently. | No sampled boundary failure is within tolerance. The C float-key replacement is already present. No H2 checker attribution established. | 0 |
| H3 type handling | Native source code copied unchanged into records; 200 exact same-code producer matches; all-type witness distances and full `any_type` scan. | Another type containing/approaching a point does not prove remapping. No remapping established. | 0 |
| H4 bogus edge of polygon 65623 / winding-parity contradiction | Independently read `(1689,508,record0)`: n=1810, explicit closure, longest edge 1808, 1,908,357.169056 raw. Full proper-crossing sweep and 3,969-point interior bbox grid. | No proper crossing found; no parity/winding disagreement on that grid (winding only 0/1). Finite sampling cannot prove absence everywhere; H4's claimed contradiction is not demonstrated. Length alone is not a spool cause. | 0 under H4 as stated |
| H5 outside fills/covers with a well-formed source | Short-ring original/G gate; independently found the source's two crossings; remove crossing and recheck. | The selected outside cover disappears with the spool defect removed; it does not satisfy H5's well-formed-source premise. A residual build cause is not established before the amended source-pin stop. | 0 build |
| H6 clip sliver/chord/off-outline vertices | Outside-fill candidate X03: 200/200 INVALID; exact record provenance for S02; both counterfactuals. | Outside vertices are real. In S02/control examples their defect disappears with crossing removal, so a generic build catch-all is unsupported. Other strata remain unclassified at the amended source-pin stop. | 0 build; S02 explained by H7 |
| H7 other mechanisms | Interior-vs-outline kind validity (R01); self-crossing closing rings (S02); all-row leaf/frame `onb` audit. | R01 checker and S02 spool are supported. `onb` mismatch is diagnostic only and moves no failure count. | 920,773 checker + 1,939,053 producer-qualified spool |

## Final counts and partition

| Kind | Level | Checker | Build | Spool | Unclassified |
|---|---:|---:|---:|---:|---:|
| background | 0 | 918,297 | 0 | 0 | 513,492 |
| background | 2 | 2,476 | 0 | 0 | 4,293 |
| background_boundary | 0 | 0 | 0 | 1,939,053 | 14,490,459 |
| background_boundary | 2 | 0 | 0 | 0 | 116,053 |
| background_boundary | 6 | 0 | 0 | 0 | 4,004 |

Arithmetic: background `(918,297+2,476)+(513,492+4,293)=920,773+517,785=1,438,558`; boundary `1,939,053+(14,490,459+116,053+4,004)=1,939,053+14,610,516=16,549,569`. Total attributed **2,859,826**, unattributed **15,128,301**. Original ~5.9M remainder **5,939,509** plus held historical S02 rows **9,188,792** equals 15,128,301. Cause counts here are stricter than the accepted attempt-2 sample-level application because review item 6(a) requires enumerated producer identity.

Before: native attempt-2 classify assigned 920,773 fill and 11,127,845 boundary rows; unclassified 517,785/5,421,724, **PARTITION FAIL**. After: producer-qualified attempt-3 classify assigns 920,773 fill and 1,939,053 boundary rows; unclassified 517,785/14,610,516, **PARTITION FAIL**, expected exit1. Original K1 failures are unchanged: no dump, disc, checker or tolerance was changed.

| Unattributed kind | Level | Type | Rows |
|---|---:|---:|---:|
| background | 0 | 288 | 104,399 |
| background | 0 | 289 | 20,429 |
| background | 0 | 291 | 374,392 |
| background | 0 | 578 | 14,272 |
| background | 2 | 289 | 4,293 |
| background_boundary | 0 | 288 | 3,186,137 |
| background_boundary | 0 | 289 | 409,182 |
| background_boundary | 0 | 291 | 10,508,842 |
| background_boundary | 0 | 578 | 386,298 |
| background_boundary | 2 | 289 | 116,053 |
| background_boundary | 6 | 288 | 4,004 |

Source identity/counterfactual evidence for the original ~5.9M remainder is still missing; those rows stay unattributed (carried). The three no-match groups are L0/type291: `(1792,395,path352,shape6)` 70 rows; `(1801,395,path361,shape10)` 132 rows; `(1805,395,path365,shape517)` 117 rows. No producer cause is inferred for them. Audit details: `unclassified_strata_attempt3.tsv`, `audit_artifacts_attempt3.json`. Every original named field in both extended background dumps was compared to the original (NaNs equal) and matches; only the recorded producer flag is new.

Final command (native tool has no `--kinds`; only scratch contains the three unrelated-kind catch-alls):

```sh
flock output/.heavy.lock .venv-rp/bin/python parser/tools/k1_triage.py classify \
  --dump output/scratch-3-07/dump_attempt3 \
  --rules output/scratch-3-07/rules_all_attempt3.json \
  --out output/scratch-3-07/classify_attempt3
```

Evidence: `classify_attempt3/{partition.txt,cause_counts.tsv,unclassified_groups.tsv}`, `enumerate_S02_attempt3.tsv`, `final_checks_attempt3_status.txt`. A complete partition is not claimed. The earlier rejected X02/X03 candidate partition was OK only because it guessed build from INVALID witnesses alone; those guesses remain withdrawn.

## Contradictions, limits, and deviations

1. **Validity contract conflict:** 3C-04 / 2-04 as written and the current K1 implementation test outline for non-boundary `background`, interior-or-outline for `background_boundary`. Amendment 4 explicitly imposes interior for fills and outline for boundary items. This report applies Amendment 4, as requested; R01 is a checker cause under that amended criterion. It is not claimed that K1 violates the older outline requirement. Counterfactual count comparisons use unchanged K1, as step 4 requires; they do not establish that every new boundary vertex meets the separate amended outline criterion. No tolerance or code was changed.
2. **94.5% is arithmetically wrong:** independently verified sentinel counts give 88.46708%. Source concentration remains below 90%, so column investigation was used.
3. **Polygon 65623 is not a demonstrated spool defect:** its long edge is confirmed, but the stated winding/parity contradiction was not reproduced. Spool attribution here uses other rings with independently demonstrated proper crossings and byte-gated counterfactuals. Nearest-shape identity and a block-relative Region ordinal cannot establish a producer.
4. **Counterfactual criterion versus H4 wording:** the prescribed experiment classifies the crossing-removal mechanism as `spool`; it does not require a winding/parity disagreement at the sampled outside vertex. Here both tests say outside. No assertion is made that the source OSM way had the same topology: the spool stores no background OSM id, and the extractor closes non-road ways but the spool alone cannot establish whether a closing point was already present in OSM.
5. **Pin stop retired:** enumeration stopped at **10,001 distinct S02 source rings**, not 145,960 classify groups; the stop is now retired and S02 is carried as one rule. Remaining producer identities and the original ~5.9M remainder stay unattributed unless new predicates arrive. The permitted side-table extension is explicit and used for actual producer-qualified attribution; no build/spool guess fills the rest.
6. **Review:** the mandatory Sonnet 5.5 review was done; see `review_3-07.md` (verdict: accept attempt-2 R01 and S02 as a partial evidence table; arithmetic, classify counts and witnesses reproduced). Completed full attribution is still not claimed.
7. **Scratch recovery:** a provenance helper initially failed to serialize numpy integer indices; it was corrected. Its multi-piece length reader also needed big-endian decoding. The complete producer probe was rerun, and final S02 witness/provenance keys were cross-checked 200/200. A slow initial witness child continued after its tool session was interrupted, retaining the heavy lock until completion; subsequent jobs remained serialized. These were scratch-only corrections. `notes.md` records findings and recovery; attempt-1 claims were re-derived rather than adopted.
8. **Non-trivial diagnostic bug, not fixed:** `_k1_bg.c:k1_diag_fill` hard-codes 0/4096 for `onb` and misses internal leaf edges, producing all 31,416 misleading zero masks. This affects diagnostic-based triage predicates, not the kind chosen by K1. Counterfactual completeness counts are not a full-disc gate: receiver windows leave other cells in their checked blocks absent.

9. **Attempt-3 deviations and audit scope:** the stale plan-03 2-04 required-reading path was resolved to the plan-04 brief. The prescribed original-dump classify command is adapted to the explicitly permitted owned extended dump because the original schema has no producer identity/flag. New attribution is narrower than the historical S02 count, as required by attempt-3 review item6(a). New source-pin enumeration and remaining mechanism investigation stopped on the amended cap; only witness/partition/pin-counterfactual reporting evidence was completed after that stop. Existing accepted evidence and the Sonnet review were retained; no agents spawned. Initial extended join validation caught non-sentinel rows sharing pinned piece groups; the join was corrected to intersect the original S02 scope before any final classify.
