background: checker 920,773 + build 0 + spool 0 + unattributed 517,785 = 1,438,558; background_boundary: checker 0 + build 0 + spool 11,127,845 + unattributed 5,421,724 = 16,549,569. Spool pinning: 145,960 groups (>10,000).

# 3-07 attempt 2 — blocked at the permitted spool-pinning stop

**S02 alone has 145,960 L0 groups. Cody must decide how to pin them (Assumption 1).** Amendment 1 says: “The only stops are: spool rule-level groups > 10,000, or a mechanism no witness explains after you have tried the steps”. This is the first stop condition. It is not `blocked: unattributed`: the remaining 5,939,509 rows have not been forced into a cause or exhaustively researched after the pinning stop. The full-partition goal is **not met**.

Two accepted, disjoint, column-only rules remain in `rules_bg.json`; neither lists target cells. No side-table predicates are used. The original dump, G, code, and protected scratch directories remain untouched. No agents, commits, pushes, cache drops, or fixes. Scratch contains scripts, full-level spool caches, copied counterfactual spools, and evidence. Every heavy run held `output/.heavy.lock`; compiles, builds and K1 counterfactuals were serial.

## Validity and first-step investigation

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
- Evidence: `witness_R01.txt`, `witness_R01.jsonl`, `enumerate_R01.tsv`; assignment is the final `classify_bg` run. No counterfactual is required for a checker rule. Settles H7's changed kind-validity mechanism.

## S02 — spool: a crossing closing edge produces outside perimeter pieces

- Predicate: `kind=background_boundary AND level==0 AND code==291 AND src_ix==-2147483648`.
- Mechanism: the spool ring's longest closing edge crosses its own outline, and the unchanged clipper emits outside pieces from that defective ring; removing the crossing removes the failing piece.
- Rows: **11,127,845**, all L0. **Enumerate groups: 145,960** (`enumerate_S02.tsv`), the number a pinned list would have. This exceeds 10,000 and triggers Amendment 1's stop.
- Independent witness: **200/200 INVALID**, same-type outline distance >64 raw in every sampled group, all-level parity/winding both outside. Final enumerate selection uses seed 20260930, stride 729, offset 425. Every final witness point is exactly the provenance-probed point (`accepted_evidence.json`).
- Independent producer attribution: all **200/200 disc piece records match original source-produced record bytes**, not just a nearest shape. All 200 producer rings are explicitly closed; their longest edge is the closing edge (`n-2`), with a proper crossing of another edge. E1 was run with the selected receiver existence bits, retaining all original source cells; the unchanged repository clipper was exposed by an owned scratch shim. Evidence: `producers_sentinel_background_boundary_L0_T291.json`, `producer_291_complete.log`.
- **Type-291 counterfactual:** original 3x3 window `[828,831)×[745,748)` reproduces **9/9 G frames exactly**, including padding. Source `(829,746,record81)`, n=35, has closing-edge crossings `[26,33]` and `[1,33]`. Delete only coordinate index 33, lat/lon `(-34.4360529,115.9231159)`, decrement `b_nstored` and `b_ncoords`, retain class/type/closure and all other content. The new n=34 ring has no proper crossings. The exact failing piece's original bytes **vanish**. K1 boundary failures in the window fall **829→589**; the 240 failures removed correspond to this producer's pieces; other defective sources remain. Background failures stay 69. Thus the prescribed outcome rule labels this mechanism `spool`. Evidence: `cf_291/{original/G_byte_gate.json,outcome.json}`, `cf_291_selection.json`, copied `spool_cf/drop_829_746_rec81_vertex33/change.json`.
- **Same-mechanism cross-kind control:** original 3x3 window `[1769,1772)×[202,205)` reproduces **9/9 G frames**. Source `(1765,216,record0)`, n=12, crosses at edges `[3,10]` and `[2,10]`. Delete coordinate 10, lat/lon `(-46.9384747,145.0316677)`; new n=11 has no proper crossings. K1 failures change `background 32→0`, `background_boundary 255→0`, `interior_cover 1→0`. Evidence: `cf_short_ring/{original/G_byte_gate.json,ring_geometry.json,outcome.json}`. This control establishes the same mechanism on type 288 but does not assign those other strata after the pinning stop.
- Settles H7's independently named crossing-closing-edge mechanism and explains the outside-piece symptoms considered by H5/H6 in these experiments. It does **not** establish H4's specific claim about polygon 65623.

## Hypotheses H1–H7

| Hypothesis | Tested / how | Outcome | Accepted rows |
|---|---|---|---:|
| H1 window omission | All-level independent parity and unbounded outline queries on 2,032 sentinel groups, plus final rule witnesses; inspected ring+tall selection. A relevant bbox either leaves the home ring and enters the tall set, or its home lies in the local ring. | No omitted valid source observed. Sentinels are genuinely distant outlines. Not a demonstrated cause. | 0 |
| H2 collinear scan-line tolerance / float-key tie | Read exact C interval handling and the 2-04 amendment; scanned full diagnostic near-distance columns; tested the corrected outline criterion independently. | No sampled boundary failure is within tolerance. The C float-key replacement is already present. No H2 checker attribution established. | 0 |
| H3 type handling | Native source code copied unchanged into records; 200 exact same-code producer matches; all-type witness distances and full `any_type` scan. | Another type containing/approaching a point does not prove remapping. No remapping established. | 0 |
| H4 bogus edge of polygon 65623 / winding-parity contradiction | Independently read `(1689,508,record0)`: n=1810, explicit closure, longest edge 1808, 1,908,357.169056 raw. Full proper-crossing sweep and 3,969-point interior bbox grid. | No proper crossing found; no parity/winding disagreement on that grid (winding only 0/1). Finite sampling cannot prove absence everywhere; H4's claimed contradiction is not demonstrated. Length alone is not a spool cause. | 0 under H4 as stated |
| H5 outside fills/covers with a well-formed source | Short-ring original/G gate; independently found the source's two crossings; remove crossing and recheck. | The selected outside cover disappears with the spool defect removed; it does not satisfy H5's well-formed-source premise. A residual build cause is not established before the pinning stop. | 0 build |
| H6 clip sliver/chord/off-outline vertices | Outside-fill candidate X03: 200/200 INVALID; exact record provenance for S02; both counterfactuals. | Outside vertices are real. In S02/control examples their defect disappears with crossing removal, so a generic build catch-all is unsupported. Other strata remain unclassified at the pinning stop. | 0 build; S02 explained by H7 |
| H7 other mechanisms | Interior-vs-outline kind validity (R01); self-crossing closing rings (S02); all-row leaf/frame `onb` audit. | R01 checker and S02 spool are supported. `onb` mismatch is diagnostic only and moves no failure count. | 920,773 checker + 11,127,845 spool |

## Final counts and partition

| Kind | Level | Checker | Build | Spool | Unclassified |
|---|---:|---:|---:|---:|---:|
| background | 0 | 918,297 | 0 | 0 | 513,492 |
| background | 2 | 2,476 | 0 | 0 | 4,293 |
| background_boundary | 0 | 0 | 0 | 11,127,845 | 5,301,667 |
| background_boundary | 2 | 0 | 0 | 0 | 116,053 |
| background_boundary | 6 | 0 | 0 | 0 | 4,004 |

Arithmetic: background `(918,297+2,476) + (513,492+4,293) = 920,773+517,785 = 1,438,558`; boundary `11,127,845 + (5,301,667+116,053+4,004) = 11,127,845+5,421,724 = 16,549,569`. Total classified **12,048,618**, remaining **5,939,509**.

Final command (because classify has no `--kinds`):

```sh
flock output/.heavy.lock .venv-rp/bin/python parser/tools/k1_triage.py classify   --dump output/scratch-3-03/dump   --rules output/scratch-3-07/rules_all.json   --out output/scratch-3-07/classify_bg
```

Result: exit **1**, **PARTITION FAIL**, `background` assigned 920,773/unclassified 517,785; `background_boundary` assigned 11,127,845/unclassified 5,421,724. The scratch rules file contains temporary plumbing catch-alls for the other three kinds; they make no attribution claim and are absent from `triage/rules_bg.json`.

The earlier **candidate** partition was OK only because X02/X03 guessed `build` for all invalid rows. Their witnesses each said 200/200 INVALID, but producer/counterfactual evidence showed invalidity alone cannot establish build. Those guesses were removed. A full `PARTITION OK` is not claimed. Original K1 failures are unchanged because the dump/G/code were not edited. Before this attempt there were no accepted triage rules; the fresh witness-backed attribution above is the after state.

## Contradictions, limits, and deviations

1. **Validity contract conflict:** 3C-04 / 2-04 as written and the current K1 implementation test outline for non-boundary `background`, interior-or-outline for `background_boundary`. Amendment 4 explicitly imposes interior for fills and outline for boundary items. This report applies Amendment 4, as requested; R01 is a checker cause under that amended criterion. It is not claimed that K1 violates the older outline requirement. Counterfactual count comparisons use unchanged K1, as step 4 requires; they do not establish that every new boundary vertex meets the separate amended outline criterion. No tolerance or code was changed.
2. **94.5% is arithmetically wrong:** independently verified sentinel counts give 88.46708%. Source concentration remains below 90%, so column investigation was used.
3. **Polygon 65623 is not a demonstrated spool defect:** its long edge is confirmed, but the stated winding/parity contradiction was not reproduced. Spool attribution here uses other rings with independently demonstrated proper crossings and byte-gated counterfactuals. Nearest-shape identity and a block-relative Region ordinal cannot establish a producer.
4. **Counterfactual criterion versus H4 wording:** the prescribed experiment classifies the crossing-removal mechanism as `spool`; it does not require a winding/parity disagreement at the sampled outside vertex. Here both tests say outside. No assertion is made that the source OSM way had the same topology: the spool stores no background OSM id, and the extractor closes non-road ways but the spool alone cannot establish whether a closing point was already present in OSM.
5. **Pinning stop:** stopped on S02's 145,960 rule-level groups as explicitly required by Amendment 1, not on budget, file reads, turn count, or ten low-yield rules. Further cause rules and a zero-unclassified partition await the pinning decision. The raw dump lacks producer topology fields; if a later mixed stratum needs them it may require the amendment's recorded side-table route. No unsupported side-table rule is accepted here.
6. **Review:** the mandatory Sonnet 5.5 review was done; see `review_3-07.md` (verdict: accept R01 and S02 as stated; arithmetic, classify counts and witnesses reproduced). Completed full attribution is still not claimed.
7. **Scratch recovery:** a provenance helper initially failed to serialize numpy integer indices; it was corrected. Its multi-piece length reader also needed big-endian decoding. The complete producer probe was rerun, and final S02 witness/provenance keys were cross-checked 200/200. A slow initial witness child continued after its tool session was interrupted, retaining the heavy lock until completion; subsequent jobs remained serialized. These were scratch-only corrections. `notes.md` records findings and recovery; attempt-1 claims were re-derived rather than adopted.
8. **Non-trivial diagnostic bug, not fixed:** `_k1_bg.c:k1_diag_fill` hard-codes 0/4096 for `onb` and misses internal leaf edges, producing all 31,416 misleading zero masks. This affects diagnostic-based triage predicates, not the kind chosen by K1. Counterfactual completeness counts are not a full-disc gate: receiver windows leave other cells in their checked blocks absent.
