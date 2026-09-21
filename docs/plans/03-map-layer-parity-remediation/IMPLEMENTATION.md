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

---

# Phase 2 run (restart, 2026-09-22)

- Tool: Claude Code (Agent SDK), orchestrator model Opus 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-22
- Scope: Phase 2 only (gate), under `DESIGN.md` Decisions "Amendment 2026-09-22 (user) — Phase 2 restart".
- Carry-in: units 2-01 and 2-02 are recorded done above and are **not** re-run. The restart covers the two authorised bug fixes, the word-7 adoption, a re-run of 2-03 against the redefined gate, and 2-04.
- Status: refine dispatched (phase re-briefed against the amendment and the code as it now stands).

### refine (Phase 2 restart) — proceed (36457a5, Opus)
Verdict: dispatchable in 5 units. 2-01/2-02 stay done and are not re-run; 2-03 is superseded by 2-08. New/rewritten briefs: `2-05-l0-sparse-frame.md`, `2-06-y-orientation.md`, `2-07-word7-adoption.md`, `2-08-overlay-rerun.md`, and `2-04-schema-rows-and-gate.md` rewritten against the redefined gate. DESIGN.md Phase 2 Units table updated with the restart sequencing. Parallel groups: A = 2-05 ‖ 2-07, B = 2-06, C = 2-08, D = 2-04.
Points raised to the orchestrator:
1. **2-06 scope.** `latlon_to_xy`'s y expression is copied verbatim into `kiwiw/_cenc.c` `to_xy`, `synth.py` `_bg_fast` and the `_raw` recovery in both census tools. Flipping only `coordconv.py` would make the C encoder and the Python oracle disagree (`test_cenc.py` compares them byte-for-byte) and make the censuses recover the complement of the coordinate they decoded — a regression, not a deferral. The brief owns the single y expression at each of those four sites and nothing else. Accepted by the orchestrator as within the user's "unless the fix requires otherwise".
2. **2-08 margins were chosen with the first run's numbers visible** — unavoidable, since the first run exists, so the brief discloses it rather than hiding it: `MARGIN_MATCH 1.5`, `MARGIN_DIST 2.0`, with `divided_pardiv1` (1.51 on the first run) flagged as the expected tight class. The worker may not change a threshold; a `divided_pardiv1` failure is a real gate failure.
3. `tol_extent` is resolved up front (tolerance scales the **frame** extent, per `harness.json`'s own basis text), with leaf-basis numbers reported as a diagnostic.
4. Carried item 4 (`rg_size`, word 16) is a **DESIGN gap**, not a unit's to fix: the header-word exemption list omits it although R writes it nonzero on L0 rg parcels. 2-04 adds the schema row and names the gap; the orchestrator must resolve it before Phase 4.
5. Carried item 5 (pointer non-frame targets) is Phase 9's; no Phase 2 obligation.
6. If 2-05's fix changes `coord_scale.json`'s regenerated content (it should be invariant), the worker reports `needs context` rather than editing 2-01/2-02's artefact.
Orchestrator deviation from refine's advice: refine recommended Opus for 2-05/2-06/2-08; the user's model guidance for this run is Sonnet at medium effort for build workers, so they are dispatched on Sonnet, with Opus held as the one-tier retry.

### 2-06 y-orientation — done with concerns (39c9c2f, Sonnet)
Built: the y expression is now `(lat - lat_lo)/span` at all five sites that carried the y-down copy — `kiwiw/coordconv.py` (`xy_to_latlon` uses `lat_lo + …`), `kiwiw/_cenc.c` `to_xy`, `kiwiw/synth.py` `_bg_fast`, `tools/coord_scale_census.py` and `tools/road_density_census.py`. The `coordconv` module docstring now states the orientation as settled and cites 2-03's pooled table (the docstring and the code no longer contradict each other). New test `test_y_axis_increases_northward` in `tests/test_parcel_geometry.py`; the SW-corner test now asserts `yc == 0`. No fourth copy turned up — `mesh.py`'s `local_lat_frac` was already lat-lo-based and was left alone; `osm_to_parcel_geometry.py` states no orientation.
Evidence: before, 363 passed with the new test deselected and the new test failed on HEAD; after, 364 pass — including `test_cenc.py` and `test_synth_vectorized.py` running **with** the C library (not skipped), which is what confirms the lockstep edit is complete. Both census tools reran against R: `density.json` `1982b1ec…4754` byte-identical to the committed file; `coord_scale.json`'s `ranges` and `class_rule` identical to the committed file (the census's own output `b2d21b66…2485` lacks the `header` section, which `header_word_census.py` writes). Neither profile file was recommitted.
**Encoder impact, for Phase 3 to inherit.** Measured on 24 synthetic parcels (seed 7, one random bbox each, one 2–12 point type-5 line background shape each) through the real `encode_background_shape_bytes` path, C and scalar: encoded bytes changed for 24 of 24. Pixel **x is unchanged**; pixel **y becomes exactly `32768 - y_old`** for every point in every parcel, with no rounding exceptions — i.e. `RANGE - y` at `RANGE = 2**15`, since the encoder rounds identically. The C encoder and the scalar oracle agree byte-for-byte on all 24 before and after. Roads, background and name records all inherit the same y mirror. Not measured: road or name bytes separately, and no full rebuild was run. This is the "unless the fix requires otherwise" case the user's decision 2 anticipated: byte-identity could not be preserved, and the deviation is an exact, total y mirror rather than a diffuse change.
Deviations: (1) `tests/test_coord_scale_census.py` is not on the owned list, but its `_pt` fixture was y-down and failed the suite; one line changed to `B.lat_lo + y/32768`. (2) The Phase 3 impact paragraph was reported rather than written into `IMPLEMENTATION.md`, since the orchestrator holds that file. No contradictions, no unfixed bugs; `overlay_test.py` untouched as directed.

### 2-07 word7-adoption — done with concerns (e71174e, Sonnet)
Built: `w7_census` (a geometry-keyed pass over R, same shape as `divided_adjacency_census`) and `w7_road_presence_rule` in `tools/header_word_census.py`, wired through `build_header_section(agg, stride, w7=None)`; 5 new tests (23 pass, the 5 fail against the HEAD tool first); `header.words.7` in `profile/coord_scale.json` regenerated **from the tool**, so the profile stays generated rather than hand-edited; adoption section appended to `WORD7-ANALYSIS.md`.
The rule is now scored by the tool's existing `>= 0.99` threshold with no special-casing, and passes — `status` moves from `blocked` to `ok`. Accuracy: L0 3,704,843/3,704,871 (28 exceptions, all single-link road parcels stored `0xFF00`); L2 231,564/231,564; L4–L12 15,538/15,538 always `0xFF00`; held-out all levels 988,860/988,865 = 0.999995. The 28 L0 misses are recorded as `residual_tolerance` (explicitly "not an exemption"). `phase4_scope.l2_post_pass: true` and `area_18_meaning: documented-unknown` are recorded in the profile. The rejected `subframe_presence_rule` and `constant_per_key_rule` are kept as evidence.
Evidence: two runs against R both hash `eef25d90…0a33` (deterministic); every other `header` key and words 0, 6, 9, 10, 11 byte-identical to HEAD — only `header.words.7` differs.
Deviations: the L2 population is 231,564 not the analysis's 231,548, because the 16 divided L2 parcels are now scored by leaf-bounds containment and all agree — that caveat of `WORD7-ANALYSIS.md` is closed. The analysis's 22 "zero-height L0" parcels do not appear under leaf bounds (count 0); carried in the JSON as `caveats.zero_height_l0_parcels`. `--load-agg` falls back to the old blocked behaviour for word 7, since the L2 pass needs a fresh disc walk.
### 2-05 l0-sparse-frame — done with concerns (2f874e3, Sonnet)
Built: `parser/harness/walk.py` now separates **leaf** from **frame**. `WalkedParcel.bounds` stays the leaf slot's extent; new `frame_bounds`, `frame_range` (from `coord_scale.json` `ranges`) and `frame_class` (`"leaf"` | `"l0_sparse_tile"`) carry the coordinate frame. L0 sparse tiles are detected **structurally** (`_is_sparse_tile`: all 16 slots share one `(dsa, size)`), and their frame is the 4x4 tile bbox at range 16384. `MeshLocation.bounds` now receives the frame bbox, so decoded lat/lon are anchored on the frame. `tools/road_density_census.py` takes span and range from `frame_bounds`/`frame_range`; `profile/density.json` regenerated. 3 new tests in `tests/test_harness_walk.py` (fail on HEAD, pass now; they drive `_leaf_frame` with a synthetic record because `alldata_writer` cannot build aliased slots).
Recon on R: L0 mapinfo `n_parcels_lat/lng` = 63/31, so each block is a 64x32 leaf grid (2048 slots). Of 231,552 L0 4x4 tiles, 231,300 resolve to one distinct `(dsa, size)` across their 16 slots; the other 252 resolve to 16 — matching 2-01's urban tile table exactly. The 4x4 tile at 16384 is confirmed.
Evidence: `pytest parser/tests -q -x` 363 passed. Sparse-vertex measurement over 60 sparse tiles / 819,088 road vertices (every 97th sparse tile in on-disc order, kept if its frame has roads): under the corrected placement 0.9977 of vertices fall inside the tile frame and 0.062 inside the slot's own leaf (≈ the 1/16 expected for a tile-wide frame); median displacement of HEAD's placement from the corrected one is **4.6 km**. `density.json` byte-identical over two runs. `coord_scale.json` regenerates identically (`ranges`, `class_rule` untouched), so refine's point 6 escalation did not fire.
**Closes Phase 1 Carried item 4**, and the correction is large: L0 vertices/km 41.05 -> 13.36 (mean 45.35 -> 12.82, p50 46.14 -> 12.14, p90 63.60 -> 18.49) because `length_km` 355,012 -> 1,091,110. The old figure used the leaf span and undercounted sparse road length about 4x. Phase 5's density band is derived from this number and must be re-read against the corrected `density.json`.
Contradictions in the brief, reported not resolved silently: (1) the brief says walk gave all 16 slots the same bbox — it did not; `_narrow_bounds` already produced 16 distinct leaf bboxes, and the missing piece was the *frame*, so the first attempt's diagnosis was half right. (2) The brief's "share of vertices inside the leaf bbox they were yielded under" is 1.0 by construction under any consistent decode and cannot demonstrate the fix; the worker reported geographically corrected figures instead. (3) The decoder still has a fixed 2^15 range while the frame range is 16384/4096; only frame bbox and extent were set, since fixing the range scale is Phase 3's and `kiwiw/` is not this unit's.
Bug found, not fixed (fixer dispatched after 2-06): `tools/coord_scale_census.py` `parcel_measure` (`_raw`) inverts using the leaf `wp.bounds`, but decode now uses the frame bbox. It stayed invariant only because the maxima come from road nodes' direct raw x/y; intermediate `points` would be mis-inverted for sparse tiles. Fix is to read `wp.frame_bounds`. Only the two census tools read `wp.bounds`.
Note: a full-disc walk runs ~1,300 leaves/s, and sparse tiles are decoded 16 times (once per aliased slot); no cache was added, to keep the no-retention contract.

### fixer (2-05's deferred bug) — done (075fc99, Sonnet)
`tools/coord_scale_census.py` `parcel_measure` now inverts lat/lon with `wp.frame_bounds` instead of the leaf `wp.bounds`, matching the bbox decode uses after 2-05 — a one-line consistency fix. `tests/test_coord_scale_census.py`'s `_wp` helper takes an optional `leaf` bbox and always sets `frame_bounds`; new `test_raw_inverts_against_frame_not_leaf` uses a leaf that is a quarter-width slice of the frame (1 failed / 5 passed with the fix reverted; 6 pass with it). Full suite after: 365 passed.
Gate-relevant check: `coord_scale.json` regenerated with the fixed tool against R (452,199 parcels walked, L0 rule accuracy 1.0 on 222,192) has `ranges` and `class_rule` **identical** to the committed file, so nothing gate-relevant moved and the committed file was left alone. `road_density_census.py` already used `frame_bounds`.
Carried: `road_density_census.py`'s `LENGTH_BASIS` string still reads "leaf bounds extent" although the basis is now the frame — stale wording, not changed by the fixer.

### 2-08 overlay-rerun — done, **gate FAILS** (e296f78, Sonnet)
Built: `tools/overlay_test.py` rewritten against the redefined gate and `tests/test_overlay_test.py` extended to 10 tests; `EVIDENCE-2-08.json` written (`EVIDENCE-2-03.json` kept as the first run's record). Frames come from `walk._leaf_frame`, so L0 sparse uses the 4x4 tile at 16384; the raw-coordinate inversion is y-up to match `coordconv` after 2-06. The docstring states every fixed threshold, the (a)/(b) rules, the frame-extent tolerance decision and the diagnostics **before** the run. **No threshold or margin was changed after seeing a result.**

**Criterion (a) — relative discrimination: 4 of 7 classes pass, 3 fail.**
- L0_sparse **fail**: match ratio against the best alternative (`own_leaf_4096`) 1.164, below the 1.5 margin; distance ratio 1.015.
- L0_urban **fail**: match ratio 5.34 (passes) but distance ratio against `range_half` 0.584, above the required 0.5.
- divided_pardiv1 **fail**: match ratio against `own_bounds` 1.376, below 1.5; distance ratio 0.404 (passes on its own).
- L2, L4, L6, L8 **pass**: match ratios 3.44, 20.75, 7.60, 10.22.

**Criterion (b) — R-only measures: coordinate maximum passes everywhere; axis coverage and clip-exact each fail somewhere.**

| Class | Coordinate max (median/max) | Axis coverage median | Clip-exact share (clipped links) |
|---|---|---|---|
| L0_sparse | 1.0 / 1.0 | 1.0 | 0.983 (114) |
| L0_urban | 1.0 / 1.0 | 1.0 | 0.927 (329) |
| L2 | 1.0 / 1.0 | 1.0 | 1.0 (80) |
| L4 | 1.0 / 1.0 | 1.0 | 0.908 (76) |
| L6 | 1.0 / 1.0 | 1.0 | **0.617 (180) fail** |
| L8 | 1.0 / 1.0 | 1.0 | **0.482 (112) fail** |
| divided_pardiv1 | 1.0 / 1.0 | **0.5625 fail** | **0.870 (506) fail** |

**Named cells** (a fail only counts at >= 50 links):

| Cell | Class | Links | Verdict | Criterion (a) | Match ratio | Distance ratio |
|---|---|---|---|---|---|---|
| Brisbane CBD | L2 | 1229 | fail | fail | 0.92 | 0.326 |
| Sydney | L2 | 220 | fail | fail | 0.836 | 0.306 |
| Longreach | L6 | 22 | low_n | pass | 4.999 | 0.038 |
| Birdsville | L8 | 43 | low_n | pass | no best alternative | no best alternative |

At Brisbane CBD and Sydney the match ratio is below 1.0 — the 32768 control beats the assumed range on matched fraction in those two cells, even though L2 passes pooled. Clip-exact is `insufficient_data` at Sydney, Longreach and Birdsville.

**Diagnostics (no threshold applies).** Pooled matched fraction vs the recorded source-disagreement baseline (the share of like-for-like OSM ways with no R link within tolerance): L0_sparse 0.717/0.523, L0_urban 0.836/0.485, L2 0.843/0.757, L4 0.895/0.393, L6 0.875/0.323, L8 0.863/0.466, divided_pardiv1 0.767/0.795. The match rate clears its baseline in six of seven classes; divided is the exception (0.767 vs 0.795).

Worker's own reading, offered as a hypothesis and **not** acted on: criterion (b)'s axis-coverage threshold is measured on the parent frame, where a correctly decoded sub-quadrant can only reach about half of each axis, so the divided axis-coverage failure may be a mismatch between the threshold and the geometry rather than a decoding fault. It was not tested beyond noting it, and the threshold was left as stated.
Deviations: the 4 new tests were written after the code, so there is no failing-before output for them; two new-test assertions were adjusted before passing because the synthetic fixture is too sparse for the strict `axis_coverage` and clipped-link thresholds — a fixture adjustment, not a threshold change.

Concern (carried): the committed `header.pointer_nonframe_targets.examples` list does **not** regenerate — it differs between HEAD's committed JSON and a fresh run, reproduced with the pristine HEAD tool, so it predates this unit. Counts match; only the examples list drifts. The worker restored HEAD's list to honour keep-untouched, so the committed JSON is not exactly a fresh run. This contradicts 2-02's claim that these keys regenerate byte-identically. Root cause not chased (likely example ordering).

## Phase 2 gate verdict (restart): NOT CLOSED (unsuccessful) - design bounced for re-analysis

No `Workflow-Phase` trailer. Unit 2-04 (schema rows and gate verdict). Gate criteria are the redefined ones of the DESIGN.md amendment 2026-09-22; thresholds are those stated in `tools/overlay_test.py` before the run (margin_match 1.5, margin_dist 2.0, axis_coverage_min 0.75, clip_exact_min 0.9, min_clipped_links 50, min_links_strict 50), unchanged and not re-tuned here. Source of every number below: `EVIDENCE-2-08.json` (`gate`, `pooled_classes`, `named_cells`, `criteria_rules`) unless another file is named.

**Criterion (a) relative discrimination: FAIL (4 of 7 classes pass).**
- L0_sparse FAIL: match ratio vs best alternative (`own_leaf_4096`) 1.164 (needs 1.5); distance ratio 1.015 (needs <= 0.5). Versus the 32768 control: match 31.03, distance 0.481 (pass).
- L0_urban FAIL: match ratio 5.34 (pass); distance ratio vs `range_half` 0.584 (needs <= 0.5). Control: match 10.269, distance 0.472.
- divided_pardiv1 FAIL: match ratio vs `own_bounds` 1.376 (needs 1.5); distance ratio 0.404 (pass). Control: match 2.733, distance 0.404.
- L2 pass (match ratio 3.44, control distance 0.312); L4 pass (20.75; control 154.224/0.067); L6 pass (7.60); L8 pass (10.22).

**Criterion (b) R-only measures: FAIL.**
| Class | Coord max / range (median, max) | Axis coverage median (>= 0.75) | Clip-exact share (>= 0.9, clipped links) |
|---|---|---|---|
| L0_sparse | 1.0 / 1.0 pass | 1.0 pass | 0.9825 (114) pass |
| L0_urban | 1.0 / 1.0 pass | 1.0 pass | 0.9271 (329) pass |
| L2 | 1.0 / 1.0 pass | 1.0 pass | 1.0 (80) pass |
| L4 | 1.0 / 1.0 pass | 1.0 pass | 0.9079 (76) pass |
| L6 | 1.0 / 1.0 pass | 1.0 pass | 0.6167 (180) FAIL |
| L8 | 1.0 / 1.0 pass | 1.0 pass | 0.4821 (112) FAIL |
| divided_pardiv1 | 1.0 / 1.0 pass | 0.5625 FAIL | 0.8696 (506) FAIL |
Coordinate maximum passes in all seven classes. Axis coverage fails for divided_pardiv1; clip-exact fails for L6, L8, divided_pardiv1. No class reported `insufficient_data` in the pooled table; per-cell clip-exact is `insufficient_data` at Sydney, Longreach and Birdsville.
2-08's worker offered, as an untested hypothesis, that the divided axis-coverage threshold is measured on the parent frame where a decoded sub-quadrant can reach only about half of each axis. That is a re-analysis question for the user; the threshold was not changed and the class is recorded as failing.

**Named cells (a fail counts only at >= 50 links):** Brisbane CBD (L2, 1229 links) FAIL, match ratio 0.92, distance ratio 0.326; Sydney (L2, 220 links) FAIL, match ratio 0.836, distance ratio 0.306 (the 32768 control beats the range on matched fraction in both cells although pooled L2 passes); Longreach (L6, 22 links) low_n, (a) pass, match ratio 4.999; Birdsville (L8, 43 links) low_n, no best alternative. Two named cells fail, two are low_n.

**Diagnostics only (not pass/fail; the amendment makes match rate a diagnostic).** Pooled matched fraction vs recorded source-disagreement baseline: L0_sparse 0.717/0.523, L0_urban 0.836/0.485, L2 0.843/0.757, L4 0.895/0.393, L6 0.875/0.323, L8 0.863/0.466, divided 0.767/0.795. The rate clears its baseline in six of seven classes (divided does not). Neither number decides the verdict above.

**Header words (2-02, `coord_scale.json` `header.words`, held-out 988,865):** word 0 1.0 (988,865/988,865); word 6 1.0; word 9 1.0; word 10 0.999977; word 11 0.999988. The 42 word-0 "exceptions" are L6 nregion=1 leaves with n_entries 21/22/23 (19+15+8); the formula `36 + 4*nregion + 6*n_entries` has 0 disagreements; the cause (extra adjacency entries at parcels bordering a divided parcel) is proven by `divided_adjacency_census`. Word 7 (2-07, `WORD7-ANALYSIS.md` Adoption): status ok, held-out 988,860/988,865 (0.999995); L0 3,704,843/3,704,871, L2 231,564/231,564, L4-L12 15,538/15,538; the 28 single-link L0 parcels stored 0xFF00 are a recorded residual tolerance (count 28), not an exemption. Area 18's meaning stays documented-unknown (schema row, status unknown).

**Verdict.** Criterion (a) fails for 3 classes, criterion (b) fails for axis coverage (1 class) and clip-exact share (3 classes), and 2 named cells fail. The gate is not closed. The Phase 2 outcome is not met and the design is bounced for re-analysis (DESIGN Decisions, coordinate-range gate: nothing downstream proceeds on the current constant). The schema rows in `docs/schema/map-frame.md` record what R shows at `observed` status; they are not a gate pass. Run status: `unsuccessful`.

**Carried list, updated (the earlier Carried items 1-6):**
1. Word 7 rule: CLOSED (adopted, 2-07).
2. y orientation in coordconv: CLOSED for the decoder and every copy of the formula (39c9c2f); the encoder impact is Phase 3's (below).
3. walk.py L0-sparse frame: CLOSED (2f874e3; `EVIDENCE-2-08.json` `l0_sparse_frame_check` 12 of 12).
4. `rg_size` (word 16) nonzero on real L0 rg parcels, absent from the DESIGN header-word exemption list: OPEN. The orchestrator must resolve it before Phase 4: either word 16 joins the exemption list or Phase 4 must model it. DESIGN.md not edited here.
5. Pointer non-frame targets (`header.pointer_nonframe_targets`: 19,771 of 31,564,067; L8 5.4%, L6 0.72%): OPEN, Phase 9 owns the `pointers` allowance; no schema row obligation here.
6. Phase 1 Carried items 1, 3, 5, 6, 7: remain with their original owners.
New: the coordinate gate itself (above) is open and is the reason the phase does not close; `road_density_census.py` `LENGTH_BASIS` wording is stale; the committed `pointer_nonframe_targets.examples` list does not regenerate (counts do).

**Phase 4 scope recorded:** the L2 post-pass for word 7 (L2 headers read their L0 children); the `rg_size` exemption-list gap (item 4).
**Phase 3 scope recorded (2-06's measured impact):** the y flip changes generated bytes: on 24 synthetic parcels, 24 of 24 changed; pixel x unchanged, pixel y becomes `32768 - y_old` for every point; roads, background and name records all inherit the mirror; no full rebuild measured. Phase 3 also cannot proceed until the gate is resolved.
