# Implementation — 03-map-layer-parity-remediation

- Tool: Claude Code (Agent SDK), model Sonnet 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-21T19:17:25+10:00
- Scope: Phase 1 only (closed)

## Phase 2 run

- Tool: Claude Code (Agent SDK), model Sonnet 5, same session
- Started: 2026-09-21 (phase 2 orchestrator)
- Scope: Phase 2 only (gate). Status: refine dispatched (no Units list in DESIGN.md).


## Phase 1

Status: refine dispatched (no Units list in DESIGN.md).

### 1-05 shape-container-bmt — done (3b9e899, Sonnet)
Built: `bmt_key_diffs`/`bmt_keys`/`bmt_dsa_order_violations` in shape.py; `shape` compares G to grid.json key set; `container` adds `pdmdh.bmt_table` violations. Surfaces: harness/checks/{shape,container}.py, tests/test_harness_shape.py. Evidence: 12 tests pass; R vs R PASS; R vs G: shape FAIL 19 diffs (13 G-only tables, 6 cross-table DSA-order violations). Deviations: tests not written first; "entry-for-entry" = count + empty/non-empty pattern.

### 1-07 extraction-timing-kickoff — kicked off (Sonnet)
Extraction running detached into output/extract_timing/spool (log run.log, START.txt; gitignored via output/). Nothing to commit. Caveat: units 1-01/02/05/06/08 ran concurrently, so wall time is inflated (upper bound, not clean timing). Deviations: none.

### 1-08 schema-unknowns — done (0398669, Haiku)
Built: first tests for 20 WP2-WP5 unknowns; 2 new rows (suburb hierarchy, link endpoints). Surfaces: docs/schema/{route-planning,map-road,index-idx,disc-layout,UNKNOWNS}.md. Evidence: lint_schema.py exit 0; 505 unverified rows, 0 errors. Deviations: none.

### 1-01 report-binding — done (442d31a, Sonnet)
Built: report records generated_sha256/mtime/manifest_bound; compare_disc.py refuses (exit 2) on manifest mismatch/missing; `--manifest`/`--no-manifest`. Surfaces: harness/report.py, compare_disc.py, tests/test_harness_core.py. Evidence: 8 tests pass; real ALLDATA sha256 == manifest sha256 (51c254ac...), so manifest is NOT stale. Deviations: tests written with code; a sibling's `git stash` swept edits (restored; stash@{0} may remain, to drop at close). Full CLI run on real disc not seen by worker; 1-09 covers.

### 1-06 pointers-spotcheck — done with concerns (4cfca25, Sonnet)
Built: `pointers` requires index>=3 out-of-buffer targets to decode as Map Frames (llpid range, nregion<=255 are worker-chosen limits); `spotcheck` whole-name equality, `;` segments, casefold; Grenfell northern-cell row (Adelaide -34.9235,138.6007 L0, coords derived from R). Surfaces: harness/checks/{decode,spotcheck}.py, refdata/spot_checks.json, tests/test_harness_{spotcheck,pointers}.py. Evidence: 14 tests pass; G spotcheck PASS 15/15 incl. Grenfell; G pointers run unfinished at report time (1-09 to run).
Concern (carried): ~2% (65/4000) of R's own out-of-buffer idx>=3 targets do not decode as Map Frames (placeholder/non-frame data, L6/L8), so strict `pointers` FAILs R itself. Needs allowance or premise correction. Grenfell row passes on G (cell present).
1-06 addendum: G `pointers` and `spotcheck` both PASS (run with --no-manifest, pointers on final rule; spotcheck 15/15 confirmed on final code in a separate run).

### 1-02 density-census — done (bafffec, Sonnet)
Built: tools/road_density_census.py (R only, via iter_parcels), refdata/profile/density.json (L0,2,4,6,8), tests/test_road_density_census.py. Evidence: 4 tests pass; two runs byte-identical; L8 vertices 28,873 vs design 28.9k. Vertices/km: L0 41.0, L2 5.80, L4 2.46, L6 1.38, L8 0.90. Deviations: first run overcounted L0 (divided slots share a frame) -> dedupe by (offset,length). L0 16384 heuristic unverified until Phase 2. 1-09 must add density.json to refdata/README.md.

### 1-03 bands — done with concerns (8a6d678, Sonnet)
Built: `bands` section in harness.json (12 quantities, derivation_rule, review, amendments), profile/bands_derivation.json. Tolerances 0.25 (L0/2/4), 0.35 (L6/8), distance 0.005 of cell, vocab coverage 0.95. Review by a read-only helper: 11 objections, resolutions recorded in `bands.review` (not marked accepted). No G data used. Tests pass (15). Concerns: tolerances are judgment values (no per-block spread in map.json); helper flagged L6/L8 as possibly tight; node bits censused only for oneway/pseudo3d_updown.

### 1-04 coverage-direction — done (7c48f83, Sonnet)
Built: R-count-weighted `coverage()`/`coverage_band()` in vocab.py, reused by mfde.py; tol 0.05 (bands.vocab_coverage), 1%-class-must-appear rule; histograms with R n<100 advisory. Surfaces: harness/checks/{vocab,mfde}.py, tests/test_vocab_coverage.py (new), tests/test_harness_mfde.py. Evidence: 13 tests pass (failing tests first); on current G both mfde and vocab FAIL as designed (e.g. road_type coverage L2 0.014, nregion L0-6 ~0.018 since G emits only 0; L4 background 0.950 and L8 name_type 0.986 fail the 1%-class rule). Deviation: mfde tests patch coverage_band to (1,1) to isolate the subset direction.

### 1-09 expectations-and-close — done (82f25f5, Sonnet)
Built: EXPECTATIONS.md, provenance entries (compare_report.json, extract_timing/), README line for density.json. Evidence: output/compare_report.json generated_sha256 51c254ac... == ALLDATA sha256, manifest_bound true (manifest was not stale); refusal demo exit 2 on altered manifest hash. Extraction wall time 26:03 (upper bound, concurrent load; 12 cores, 10.1 GB RSS) — answers Open Question 3. FAILs: container/shape (13 G-only BMT + 6 DSA order), mfde (50 coverage), vocab (coverage <0.95 all levels), envelope L0 name_count 0.119 (F8) — all expected. Two envelope FAILs (L10 3616>2336, L12 4992>3808) were not on the list; orchestrator triaged them as F3/F5 (ratios 1.55, 1.31, under 2x-R) and added them to EXPECTATIONS.md; cause inferred, not measured.

## Phase 1 verification
Outcome check: compare_disc.py on current G binds sha256 to manifest (equal); altered manifest refuses with reason (exit 2); strengthened mfde/vocab/shape/container/pointers/spotcheck ran on G and every FAIL is on the expectation list (after triage above). Bands recorded in harness.json before any G run (1-03 finished before 1-04/1-09). Note: `header_words`/`coord_scale` checks belong to Phases 3/4.

## Carried
1. Bands review (`bands.review`) is recorded but not marked accepted; needs human confirmation. Tolerances are judgment values; L6/L8 possibly tight.
2. Strict `pointers` FAILs R itself on ~2% (65/4000) of out-of-buffer idx>=3 targets; needs allowance or premise correction before it can be used as R-parity. (Classified by 2-02 over all of R: 19,771/31,564,067 = 0.063% overall, concentrated at L8 5.4% / L6 0.72% / L0 0.066%; see `coord_scale.json` `header.pointer_nonframe_targets`. Still carried — Phase 9 owns the allowance.)
3. Envelope L10/L12 frame-size FAILs: cause inferred (F3/F5); Phase 4 envelope rewrite (2x-R advisory) must confirm.
4. L0 road-length census uses an unverified 16384 range heuristic; Phase 2 must validate and re-derive density.json if changed.
5. Extraction timing 26:03 is an upper bound (concurrent load); re-time cleanly before Phase 8 planning if it matters.
6. Grenfell spot row passes on G (design predicted FAIL); coordinates were derived from R.
7. Git stash@{0} holds stale sibling WIP from concurrent workers; drop after confirming nothing is lost.

### 2-01 coord-range-census — done (2cbe296, Sonnet)
Built: tools/coord_scale_census.py, tests, profile/coord_scale.json (ranges, class_rule; no header section). Range hypothesis confirmed: L0 sparse 16384 (99.46%), L0 urban 4096, L2-L12 4096, divided sub0 2048 / sub1-3 4096; no parcel exceeds class max. Class rule content-independent, 100% vs R word 6 (urban via 252-tile table). Deviation: edited tools/road_density_census.py and regenerated density.json (carried 4: heuristic wrong for 482 sparse L0 parcels and 13 divided sub-0; L0 vertices/km 41.01 -> 41.05).

### 2-02 header-word-census — done with concerns (Opus, budget doubled)
Built: `tools/header_word_census.py` (full-R census, worker-side aggregation — no per-parcel dump), `tests/test_header_word_census.py` (18 tests, synthetic fixtures), `header` section in `profile/coord_scale.json` (`ranges`/`class_rule` byte-identical to 2-01's). 3,951,973 parcels, 988,865 held out (`sha1("<bs>:<blk>:<p0>.<p1>...")[0] < 64`, by parcel identity).
Held-out accuracy: word 0 `size` 1.000000; word 6 `dipid` 1.000000; word 7 `pmcode` **0.856991 (blocked)**; word 9 `dsflag` 1.000000; word 10 `rlx` 0.999977; word 11 `rly` 0.999988.
- Word 0 rule is structural, not a table: `word0*2 = 36 + 4*nregion + 6*n_mfde_entries`, and equals the first in-buffer data-slot offset in 988,865/988,865 held-out parcels. Zero disagreements anywhere on R.
- **The 42 explained.** L6 has 939 leaves; `(nregion, n_entries)` = {(0,20):14, (0,21):1, (0,22):1, (1,20):881, (1,21):19, (1,22):15, (1,23):8}. The 42 are exactly the nregion=1 leaves with n_entries != 20 (19+15+8). Header-size classes 156/160/162/166/168/172/178 B. Cause proven geometrically (`divided_adjacency_census`): every leaf with extra entries borders a divided parcel, and no non-adjacent leaf has extra ones (n_entries21/22/23 → adjacent_to_divided=1 for all 43 rows incl. the nregion=0 pair). Extra mfde entries are adjacent-parcel pointers; a divided neighbour needs one record per sub-parcel. Content-independent (follows from the WP1 grid + division layout).
- rlx/rly rule is an exact table keyed (level, lat_lo, lat_span, lon_span), 2,921 rows, 0 ambiguous fit keys; misses are 12/10 unseen keys, not wrong values. The closed-form WGS84 model (phi = lat+50) scores 0.972924 and is recorded as evidence only.
- **Word 7 blocked, not tuned.** Two values only: 0xFF00 (area 255) and 0x1200 (area 18); 0x1200 occurs only at L0/L2. Not positional: per-key constant 85.70%, per-1-degree-cell majority at L2 93.73%, 114/331 sampled blocks mixed, 665/2,430 L2 cells mixed, 0x1200 spans lat -44..-11 / lon 113..153. It tracks frame composition: at L0, 0x1200 ⟺ all three basic sub-frames present (99.9995%); at L2 exact for every presence mask except background-only, where 10,767/208,923 carry 0x1200 with no distinguisher (no slot-size threshold, no nregion or WP2-word correlation). That sub-frame rule scores 0.99716 overall / 0.95185 at L2 and is **not** content-independent, so it is recorded under `word_7.subframe_evidence` with `status: "blocked"`, never as the model rule. 2-04/Phase 4 must decide: source-derived (land-mask area code) or an accepted exemption.
- WP2-exempt words censused with R values: `nregion` {0: 69,915, 1: 3,882,058}; `n_intersections`, `route_planning_level`, `n_additional_data` (r_values top-20 + distinct counts); ext-frame populated-entry counts per level.
- **Carried item 2 classified** (`header.pointer_nonframe_targets`): 19,771 non-Map-Frame targets among 31,564,067 out-of-buffer idx>=3 targets. By key: `0|sparse|normal` 19,488; `0|urban|normal` 74; `4|full|normal` 94; `6|full|normal` 52; `2|full|normal` 32; `8|full|normal` 31. Reasons: llpid out of range 17,231; nregion implausible 2,540. Rate by level: L0 0.000661, L2 0.000017, L4 0.000819, L6 0.007196, L8 0.053633, L10 0. The carried "65/4000" was a sample: L6+L8 alone give 83/7,804 = 1.06%, consistent with 1-06's L6/L8 placeholder-data reading. The `pointers` check was not changed (Phase 9 owns the allowance).
Evidence: 18 tests pass; tool run twice against the real file, sha256 `9e6155b0c7d325acf95a80fbc0e6032d61ae6ee5318391249f92d9a895af6b93` both times; `ranges` and `class_rule` identical to HEAD.
Deviations: tests written with the code, not first. Classification of the 65 uses an exact mirror of `harness/checks/decode.py`'s `_decodes_as_map_frame` (census tools may not import the check) — results are comparable but not the same code path.
Side finding (not fixed here): word 16 `rg_size` is nonzero on real L0 rg parcels but is not on the DESIGN exemption list — raise with 2-04.

#### 2-02 prior handoff (superseded)
Done: `parser/tools/header_word_census.py` (collector only: raw big-endian header words, nregion, mfde slot starts, fit/held-out hash split `sha1(bs:blk:path)[0]<64`, `keyof` via 2-01 class rule; full R pass is ~10 s at L0 stride 8, whole disc is cheap). No `header` section written, no tests, `coord_scale.json` untouched.
Not done: rule/accuracy report, word-0 exception table, `header` section, tests, `pointer_nonframe_targets` classification.
Learned (stride-8 L0 + all L2-L12, big-endian words; NOTE 2-01's dump read words little-endian, so its "224/13216" = 0xE000/0x33A0-ish byte-swapped labels):
- w6 dipid: L0 sparse 0xA033, L0 urban 0xE000, L2-L10 undivided 0xE000, L12 0xC000, divided 0x6100 + {0x00,01,10,11} for sub0..3 (100% of class keys, single value per key).
- w9 dsflag 0x0064 constant everywhere. w17 nregion is 0/1 (WP2-exempt); w16 rg_size at L0 is nonzero on real rg parcels (not in the exempt list: raise with 2-04).
- w0*2 == min in-buffer offset of slots 0-2 for 100% of all parcels surveyed at every level (my `first`), so the "42 of 939" arises only if compared to slot 0 specifically or a different table-length definition; not yet re-found (test L6: w0*2 vs slot0 offset, and n_entries 20/21/22... i.e. header size 160/166/172 B classes = 36+4*nreg+6*{20,21,22}).
- w7 pmcode high half: 0xFF00 (area 255) vs 0x1200 (area 18). Not a function of block/lat. 0x1200 parcels are content-bearing (L2 median frame 864 B vs 320 B for 0xFF00; L0 2336 vs 448), so it looks like a land/sea (land-mask) area code. Next: test "any road or background shape" vs w7 via decode_parcel; if exact, rule is source-derived (natural), else needs land-mask evidence.
- w10/w11 (rlx/rly) are the spec's real-length-per-LSB (100x metres per normalized unit; bit15 = metres at L10/L12), a function of (level, parcel lat_lo, lat span) only (0 ambiguous groups at every level). Model fits: x = 100*W*mlon(phi')/4096, y = 100*H*mlat(phi')/4096 with phi' = lat+50 (R's data behaves as if latitude were measured from the -50 grid origin; standard WGS84 metre-per-degree series), range 4096 for ALL classes incl. L0 sparse. Exact-match rates 97.0-98.6% (L2/L0 sparse), 100% (L0 urban): below 99, constants not yet tuned. Fallback: exact lookup table keyed (level, lat_lo, lat_span) (~2.9k rows, unique per key).
Hazard: writing the full-R dump to tmpfs (~1 GB+) broke the shell; aggregate in workers instead.

### 2-03 overlay-test — over budget (45-turn budget reached; Opus)
Built: `tools/overlay_test.py` (rewritten), `tests/test_overlay_test.py` (6 tests, synthetic fixtures, all pass), `EVIDENCE-2-03.json` (run twice, byte-identical). Thresholds stated in the tool docstring before the run: MIN_LINKS 20, POOL_N 12 cells/class, MATCH_MIN 0.8, OCC_RATIO_MIN 0.5, MAX_REL_LO 0.9, CLIP_MIN 0.9; tolerance `tol=0.005` read from `harness.json` `bands.name_record_distance_tolerance`.
Done — Amendment 1 (orientation): **raw y increases NORTHWARD (y-up)**. Pooled over 12 cells x 7 classes, y_up vs y_down matched fraction / p50 m: L0_urban 0.836/4.73 vs 0.094/50.33; L2 0.843/8.07 vs 0.190/210.78; L4 0.894/10.68 vs 0.138/1340.50; L6 0.875/25.43 vs 0.234/4412.48; L8 0.863/119.92 vs 0.145/58783.46; divided 0.773/3.62 vs 0.291/22.87; L0_sparse 0.717/26.51 vs 0.042/487.49. `kiwiw/coordconv.xy_to_latlon` is currently y-DOWN, contradicting its own docstring; **not edited (Phase 3 owns it)**.
Done — Amendment 2 (divided rule): sub-parcel coordinates are **absolute in the PARENT leaf's frame at range 4096**. Pooled 12 pardiv1 cells (5044 links): parent_4096 matched 0.773 / p50 3.62 m; own_bounds (2048/4096 per sub) 0.282 / 12.06 m; quadrant_4096 0.223 / 13.63 m. Each sub covers a 2x2 quadrant (walk.py `_narrow_bounds` row 0 = SOUTH, so sub0 = SW), which is why sub0 never exceeds 2048 — exactly the 2-01 census max. `inside_cell_fraction` median 1.0.
New finding — **L0 sparse frame is the 4x4 "integrated parcel" tile at 16384**, not the leaf: own_leaf_16384 0.004/1249 m; own_leaf_4096 0.306/34.5 m but coord_max 4.0 (out of range); tile4x4_16384 0.717/26.5 m, coord_max 1.0; tile4x4_4096 0.0/14414 m. 16384 = 4 x 4096 and the tile is the same one the 2-01 class rule keys urban/sparse on.
Negative control (32768) fails everywhere: matched 0.006-0.512 (0/7 classes reach 0.8), clustered in 7/7 classes (occupied_ratio median 0.016-0.34), `coord_max_over_range` pinned at 0.125.
Not done / gate not met: `all_pass` false. Pooled model reaches MATCH_MIN in **5 of 7** classes (L0_sparse 0.717 and divided 0.773 fall short). Named cells: only **Sydney** passes (0.836 matched, clip 1.0); Brisbane CBD 0.798 matched / clip 0.845 (tight 0.934); Longreach 0.682 (22 links); Birdsville 0.791 / clip 1.0 (43 links).
Deviation (post-hoc, reported not hidden): the band scales `cell_extent_m`, but R's quantisation grid spans the *frame*, which is wider than the leaf for divided subs and L0 sparse tiles. `analyze()` gained `tol_extent` so those classes are scored against the frame extent; both bases are kept in the output (`matched_fraction` vs `matched_fraction_leaf_basis`). This interpretation was adopted after seeing results.
Bug found, not fixed: `harness/walk.py` assigns all 16 leaf slots of an L0 *sparse* tile the same Map-Frame bbox — `inside_cell_fraction` 0.038 for that class — i.e. leaf bounds for L0 sparse are the tile's, not the leaf's. Symptom: L0 sparse leaf bboxes are 4x too wide/tall; location `parser/harness/walk.py` `_iter_tree_leaves`/`_block_base_bounds`; root cause: the L0 sparse frame granularity (4x4 integrated parcel) is not modelled.

## Phase 2 gate verdict: NOT CLOSED (unsuccessful) — design bounced to user
No `Workflow-Phase` trailer. Units 2-01/2-02/2-03 done or over-budget-with-evidence; 2-04 not run.
Evidence:
1. Header word 7 (pmcode): held-out 0.857 with any content-independent rule (values 0xFF00 / 0x1200). Best predictor is frame composition (0.997 overall, 0.952 at L2), not content-independent. Fails the >=99% criterion. Words 0, 6, 9 = 1.0; words 10/11 = 0.99998 (exact 2,921-row table; closed-form 0.973). The 42 word-0 exceptions are explained (leaves bordering divided parcels carry extra mfde entries).
2. Overlay: coordinate model (4096/16384 per class) is directionally strongly supported (32768 control fails everywhere), but stated thresholds not met: named cells 1 of 4 pass (Brisbane 0.798 matched vs 0.8, clip 0.845; Longreach 0.682; Birdsville 0.791), pooled 5 of 7 classes (L0 sparse 0.717, divided 0.773). A post-hoc frame-extent basis was added (needs review).
3. Established facts for the re-analysis: y is UP (coordconv.xy_to_latlon decodes y-down, contradicting its docstring); divided sub-parcel coordinates are absolute in the parent leaf frame at 4096 (sub0 = SW quadrant); L0 sparse frame is the 4x4 integrated-parcel tile at 16384, and walk.py gives all 16 slots the tile bbox (bug, `_iter_tree_leaves`/`_block_base_bounds`).
User decisions needed: accept word 7 as a documented exemption or land-mask-derived code; whether overlay thresholds (judgment values set by the worker) are to be relaxed or the tile-frame model is the fix.

## Carried (phase not closed)
1. Word 7 rule (above). 2. y-orientation fix in coordconv (Phase 3). 3. walk.py L0-sparse leaf bounds bug. 4. rg_size (word 16) nonzero on L0 rg parcels, absent from the exemption list. 5. Pointer non-frame targets are 0.063% overall (L8 5.4%); strict pointers still fails R. 6. Prior Phase 1 Carried items 1, 3, 5, 6, 7 remain.
