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

### 2-04 schema-rows-and-gate — done with concerns (2b640f0, Sonnet)
Built: `docs/schema/map-frame.md` rewritten for the settled model — word 0's formula row (correcting plan 01's buffer-size claim, with the 42 L6 exceptions explained), the pmcode row **replaced** by the adopted word-7 rule (Area 18 iff road data at L0 or below, else 255; word 8 = 0; 28-parcel residual tolerance; Phase 4 L2 post-pass), rows for words 6/9/10/11 citing `coord_scale.json`, new rows for `rg_size` and the WP2-exempt words with R's census values, an unknown row for the meaning of Area Number 18, and a rewritten Coordinates section (class rule, per-level/per-class ranges, L0 sparse frame at 16384, divided sub-parcels absolute at 4096, y-up) that states the gate is **not** closed. `docs/schema/UNKNOWNS.md` regenerated by the lint tool. The gate verdict section below is this unit's.
Check: `lint_schema.py` 505 unverified / 0 errors before, 509 / 0 after. No code changed, so the worker did not run the suite.
Deviations: the brief's done evidence assumes the coordinate rows carry `observed` status and could be read as a gate pass — the worker kept `observed` and added an explicit row saying the gate did not pass, rather than downgrading the rows. It also wrote the gate section into `IMPLEMENTATION.md` per its brief, although the orchestrator's dispatch reserved that file; content accepted as briefed. The old word-0 row's "100% of sample, no exceptions" versus DESIGN's "42 exceptions" is explained in the row (both hold) rather than silently reconciled. It did not grep-check the `l0_sparse_frame_check` "12 of 12" figure; the orchestrator did (below). 2-08's untested divided-axis-coverage hypothesis is recorded as a re-analysis question, not acted on.

## Phase 2 verification (orchestrator)
The Phase 2 outcome — "decoding R at its per-class range ... puts matched roads within a recorded distance tolerance with no clustering ... clipped links terminating at the cell edge" — was exercised end to end, not read from reports: `tools/overlay_test.py` against R at `/run/media/codyh/464210-8480` and the OSM extract, two runs byte-identical (`sha256 97bc1564c14a56c97609b8d01fa7ec7cb867b3f64dad4c1f7ec172e5f60020a3`), evidence at `EVIDENCE-2-08.json`. The orchestrator read the `gate` object directly rather than trusting the worker's prose: `a_relative_discrimination` **fail** (L0_sparse, L0_urban, divided_pardiv1), `b_axis_coverage` **fail** (divided_pardiv1), `b_clip_exact_share` **fail** (L6, L8, divided_pardiv1), `b_coord_max_over_range` pass (7/7), `named_cells_failing` `["Brisbane CBD", "Sydney"]` (Longreach and Birdsville `low_n`) — matching the section below exactly. Suite after all units: `.venv-rp/bin/python -m pytest parser/tests -q` → **369 passed** in 139s.
**The outcome does not hold.** Verification confirms the failure is real and reproducible, not a reporting artefact. Per the 2026-09-22 amendment the phase does **not** close: no `Workflow-Phase: 03-map-layer-parity-remediation:2` trailer is applied and Phase 3 is not started.

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

---

# Phase 2 run (grounded-gate re-run, 2026-09-23)

- Tool: Claude Code (Agent SDK), orchestrator model Sonnet 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-23
- Scope: Phase 2 only (gate), under `DESIGN.md` Decisions "Amendment 2026-09-23 (user) — grounded phase gates", Phase 2 Outcome as amended (criteria 1-5), plus the three conditions the design agent attached before the gate verdict can count (committing the continuity and mirror checks under `parser/tools/`, block/blockset-crossing neighbour lookup for the mirror check, absolute-raw-unit tolerance for the divided_pardiv1 continuity re-measurement).
- Carry-in: criteria 1 and 5 are carried by committed, tested tools (`coord_scale_census.py`, `header_word_census.py`) — no new unit unless evidence proves stale.
- Model tier this run: Opus at medium reasoning effort for `refine`/design-reasoning dispatch; Sonnet at medium reasoning effort for build/worker/research dispatch.
- Status: refine dispatched (no Units list in DESIGN.md matches the new grounded criteria).

### refine (Phase 2 grounded gate) — proceed (7d3303f, Opus)
Verdict: dispatchable in 4 units, 3 sequential groups: A = 2-09 alone; B = 2-10 ‖ 2-11 (both consume 2-09's module, disjoint owned paths); C = 2-12 alone. New briefs: `2-09-neighbour-lookup.md` (block/blockset-crossing R leaf-neighbour lookup — a precondition the amendment names for criterion 4 being load-bearing), `2-10-continuity-and-quadrant.md` (criteria 2 and 3, folded into one unit since they share the raw-coordinate decode path, divided-parcel enumeration and frame model; `EDGE_TOL_RAW=4`/`PAIR_TOL_RAW=16` fixed in absolute raw units, pre-stated, selection/pairing run once and re-scored under every alternative to remove the circularity the amendment flagged in the provisional 122 m median), `2-11-boundary-mirror.md` (criterion 4, exact integer equality, reports matches by same-block/cross-block/cross-blockset), `2-12-grounded-gate-verdict.md` (re-runs all five criteria for real, writes schema rows and `GATE-2.md`, supplies Assumption Ledger replacement text for the orchestrator to apply on CLOSED only, never edits DESIGN.md itself). DESIGN.md Phase 2 Units table updated with the four new units.
Verified rather than assumed: criteria 1/5 evidence (`coord_scale.json` `ranges`/`class_rule`/`header.words`) is current — invariant under the 2-05/2-06/075fc99 changes since decode and inversion use the same bbox and word 7's census depends only on link counts and leaf-bbox centres. No new unit for criteria 1/5; 2-12 re-runs both tools to confirm.
Findings surfaced: (1) nothing under `parser/` implements criteria 2/3/4 today — confirmed by repo search, the amendment's inventory is accurate; the only adjacency code is `header_word_census.divided_adjacency_census`, an L6 same-level bbox-touch cross-tab, not neighbour lookup. (2) `coord_scale_census._work` builds `WalkedParcel` without `frame_bounds`, so the 075fc99 fixer never takes effect in that tool's own worker path (harmless for criterion 1's numbers; its test passes only on a synthetic parcel) — recorded as a carried item for 2-12 to confirm, not fixed here. (3) `exceptions` != `exceeds_max` in `coord_scale.json`'s `ranges`; criterion 1's quantity is `exceeds_max`; 2-12 must cite the right one. (4) `header.pointer_nonframe_targets.examples` still does not regenerate (2-08's carried concern) — 2-12 compares structurally, not by whole-file sha.
Assumption Ledger: DESIGN.md line 252 requires the ledger entry updated in the same change that closes Phase 2; refine's brief keeps `DESIGN.md` out of every unit's owned paths and has 2-12 write ready-to-paste replacement text into `GATE-2.md` (only on a CLOSED verdict) for the orchestrator to apply.
Attribution deviation: refine ran on Opus 5, so the commit trailer reads `Claude Opus 5` rather than the dispatch's literal `Claude Sonnet 5` text, to keep the trailer accurate to the model that ran; `Claude-Session` unchanged.
Model tier for downstream dispatch, per refine's report: Sonnet at medium reasoning effort for 2-09 through 2-12; no brief contains a model directive (briefs are worker-agnostic, matching 2-04's convention).

### 2-09 neighbour-lookup — done (8649d09, Sonnet)
Built: `parser/tools/r_neighbours.py` (`global_leaf_xy`, `grid_dims`, `LeafIndex` with `.get`/`.neighbour`, `Neighbour` dataclass — `status` in `resolved`/`outside_coverage`/`empty_slot`, `crossing` in `same_block`/`cross_block`/`cross_blockset`, `divided`, `handles`), `parser/tests/test_r_neighbours.py` (7 tests, stub `rdr` fixture since a real R block requires full PDMDH/LMR assembly, same avoidance `test_overlay_test.py` makes), `EVIDENCE-2-09.json`. API left exactly as the brief fixed it; no name/shape deviations.
Evidence: `test_r_neighbours.py` 7/7 pass; full suite 369 -> 376 passed (139.65s); disc run twice, sha256 `4abc3f96...` both times identical; edge-sharing assertions 0 failures at every level (L0 323,232, L2 152,184, L4 57,404, L6 3,550, L8 220 checks, all pass).
**Finding for 2-11 and 2-12 to account for**: `cross_blockset` is nonzero at every sampled level (L0 1,472; L2 2,344; L4 1,776; L6 217; L8 57). `cross_block` (different block, same blockset) is nonzero only at L0 (6,112) and L2 (2,376) — structurally absent at L4/L6/L8, which have exactly one block per blockset there, so any block-crossing at those levels is automatically blockset-crossing too. At L6/L8 specifically, 2-11's "block- and blockset-crossing" load-bearing claim is exercised only via `cross_blockset`, never via an intra-blockset `cross_block` boundary — `cross_block=0` at those levels is a structural fact about the grid, not a lookup gap.
Deviations: none from the fixed API.

### 2-11 boundary-mirror — done with concerns (3f8e7e1, Sonnet)
Built: `parser/tools/boundary_mirror_census.py` (exact-integer mirror check, `EXACT_ONLY=True`, `MIRROR_TOL_RAW=0`, `MIN_NODES_PER_CLASS=300`, pre-stated and unchanged), `parser/tests/test_boundary_mirror_census.py` (10 tests), `EVIDENCE-2-11.json` against R. `parser/tests -q`: 392 passed after (no regressions). Tool run twice against R, sha256 `c859bdd6...` identical both times.
Per class (denominator/matched/violations/outside_coverage/empty_slot/scale_mismatch): L0_urban 408/408/0/0/0/114; **L0_sparse 11536/2884/8652/0/0/0**; L2 4067/4061/6/0/0/111; L4 825/825/0/0/0/45; L6 746/746/0/0/0/104; L8 66/66/0/0/0/23.
Crossing breakdown of matched (same_block/cross_block/cross_blockset): L0_urban 408/0/0; L0_sparse 2648/228/8; L2 4006/37/18; L4 818/0/7; L6 742/0/4; L8 64/0/2. Both `cross_block` and `cross_blockset` carried matches in aggregate (cross_block 265 total from L0_sparse+L2; cross_blockset 39 total, present in every class) — consistent with 2-09's structural finding that `cross_block` is structurally absent at L0_urban/L4/L6/L8 (one block per blockset there), so those levels' load-bearing claim rests on `cross_blockset` alone.
Verdict per class: pass (L0_urban, L4, L6, L8); pass_with_residual (L2, 6 violations enumerated); **L0_sparse is a real criterion-4 failure** — 8652 of 11536 denominator, majority same-block (violation examples show the neighbour resolving to a leaf far from where the mirrored coordinate should land, e.g. expected [6642,0], nearest actual [10854,0]). Worker flags this `needs context`: not a code defect fixable within this unit's fixed-constant scope; may mean L0_sparse leaves don't tile edge-to-edge the way other classes do, or need a different mirror rule for the tile frame. Not fixed here; carried to 2-12/gate verdict.
Deviations: none from the brief; no pre-stated constant changed after a run (confirmed).

### 2-10 continuity-and-quadrant — done with concerns (68ec29e, Sonnet)
Built: `parser/tools/continuity_census.py` (criterion 2, cross-parcel edge-node continuity, built once under `overlay_test.model_frame` and re-scored unchanged under `half`/`double`/`decoder_range`/`own_leaf_bbox_own_range`; criterion 3, per-point divided-quadrant containment under both `parent_local` and `sub_local` readings) and `parser/tests/test_continuity_census.py` (6 tests). Thresholds pre-stated in the docstring: `EDGE_TOL_RAW=4`, `PAIR_TOL_RAW=16`, `PASS_RAW_UNITS=1.0`, `MIN_PAIRS_PER_CLASS=300` (per brief `2-10-continuity-and-quadrant.md`).
Evidence: `pytest parser/tests/test_continuity_census.py -q` 6/6 pass; full suite 386 -> 392 passed, 0 regressions; tool run twice against R, sha256 `8041db0f6647144db0c0eef61fa1875cedd1f5250881a335fe6c2f9c49c1a15a` both times identical.
Per-class continuity (n_pairs/median_m/max_m/over_threshold/unpaired, `double`(range*2) median alongside):
| class | n_pairs | median_m | max_m | over_threshold | unpaired | double_median_m |
|---|---|---|---|---|---|---|
| L0_urban | 405 | 0.0 | 6899.1 | 26 | 78 | 1181.9 |
| L0_sparse | 3068 | 0.0 | 11884.3 | 328 | 7956 | 4607.3 |
| L2 | 550 | 0.0 | 32.8 | 5 | 3 | 4607.3 |
| L4 | 416 | 0.0 | 0.0 | 0 | 0 | 18429.0 |
| L6 | 383 | 0.0 | 421.1 | 9 | 10 | 73716.0 |
| L8 | 34 | 0.0 | 1702.0 | 1 | 9 | 294864.0 |
| divided_pardiv1 | 984 | 0.0 | 9.2 | **38** | 81 | own_leaf_bbox_own_range=1151.8 (double n/a, 0.0) |

Quadrant containment: `n_subparcels`=168, `n_points`=1,037,716, `violations`=0 under `parent_local` (0 violations => pass); `sub_local` reading gives 798,575 violations, reported per the brief's instruction as a non-chosen alternative, not a competing claim (matches the settled contract in `docs/schema/map-frame.md`/`overlay_test.model_frame`/`test_overlay_test.py` that divided sub-parcel coordinates are absolute in the parent leaf frame).
**Verdict: criterion 2 = fail** (`over_threshold_total`=407 across all classes, not fully enumerated so not `pass_with_residual` per the brief's rule); **criterion 3 = pass** (0 violations under `parent_local`).
Deviations: none in method; `SAMPLE_BLOCKS=60` and `RESIDUAL_ENUM_CAP=200` are the worker's own sampling/reporting choices, explicitly documented in the module docstring as *not* among the four pre-stated constants. No pre-stated constant changed after a run (confirmed). No contradiction found between the brief and cited contracts. One internal bug (`_cell_dict` `NoneType` subscript) was caught and fixed during development, before any real-disc evidence run — not a carried defect.

### 2-12 grounded-gate-verdict — done, gate NOT CLOSED (8c95bfb, Sonnet)
Built: rewrote the Coordinates section of `docs/schema/map-frame.md` with all five criteria (numbers, denominators, verdicts) and explicit dispositions for the retired occupied-fraction clause, `axis_coverage` 0.75 (divided), and `clip_exact_share`; `docs/schema/UNKNOWNS.md` regenerated via `lint_schema.py --write` (509 -> 513 unverified, 0 errors both times); `docs/plans/03-map-layer-parity-remediation/GATE-2.md` (new, full criterion-by-criterion record); `EVIDENCE-2-12.json` (new, every re-run command/result/sha).
Re-ran every criterion for real in this repo state (not read from committed evidence alone):
- **Criterion 1 PASS**: `exceeds_max`=0 in every one of 28 (level, class, division) classes, denominator 452,199 content-bearing parcels; re-run `ranges`/`class_rule` structurally identical to the committed profile.
- **Criterion 2 FAIL**: `over_threshold_total`=407 (L0_urban 26, L0_sparse 328, L2 5, L4 0, L6 9, L8 1, divided_pardiv1 38); L0_sparse's 328 exceed the 200-example enumeration cap, so the residual is not record-by-record explained. Re-run byte-identical to `EVIDENCE-2-10.json` (sha `8041db0f...`).
- **Criterion 3 PASS**: 0 violations over 1,037,716 shape points, 168 sub-parcels (52 content-bearing), 42 divided parents, under `parent_local`. Same byte-identical re-run.
- **Criterion 4 FAIL (L0_sparse)**: L0_urban 408/408/0 pass; L2 4061/4067 (6 violations) pass-with-residual; L4/L6/L8 0 violations pass; **L0_sparse 8652/11536 (75%) violations** — a majority, not an explainable residual. The tool's own `verdict` field calls this `pass_with_residual` (its enumeration-cap logic only checks that examples were printed, not what share they cover); 2-12 overrode that label in `GATE-2.md` per the criterion's actual wording. Re-run byte-identical to `EVIDENCE-2-11.json` (sha `c859bdd6...`).
- **Criterion 5 PASS WITH RESIDUAL**: words 0/6/9 exact; word 7 0.999995 with a named, disc-wide-exhaustive 28-record residual; words 10/11 miss only on unseen table keys (12/988,865 each), never a wrong value. Re-run `header.words` structurally identical to the committed profile; `header.pointer_nonframe_targets.examples` drift confirmed but is 2-08's pre-existing, unrelated carried concern.
Evidence: `lint_schema.py` passes before and after (509/0 -> 513/0); `pytest parser/tests -q` 392 passed both before and after (no code changed — regression guard only).
**Assumption Ledger: not touched.** Verdict is NOT CLOSED, so per DESIGN.md line 252 the entry "Coordinate range 4096/16384 is the true full-cell range" stays exactly as it is; `GATE-2.md` states this and quotes the unchanged entry.
New Carried items confirmed by this unit: (5) `coord_scale_census._work` builds `WalkedParcel` without `frame_bounds`, so the 075fc99 fixer never takes effect in that tool's own worker path — harmless for criterion 1, confirmed not fixed here; (6) criterion 2's L0_sparse under-enumerated 328-pair residual and divided_pardiv1's fully-enumerated 38-pair residual, both genuine and open (not a provisional-tolerance artefact — tolerance is already absolute-raw-units); (7) criterion 4's L0_sparse failure — the decisive reason, with criterion 2, this gate does not close.
Deviations: none from the brief. Commit not pushed by the worker (orchestrator to push).

## Phase 2 verification (orchestrator, grounded-gate re-run)
Read `GATE-2.md` and `EVIDENCE-2-12.json` directly rather than trusting the worker's prose. The five criterion verdicts, numbers and denominators in `GATE-2.md` match 2-09/2-10/2-11's own committed evidence files exactly (criterion 2 and 4's headline numbers are byte-identical re-runs of `EVIDENCE-2-10.json`/`EVIDENCE-2-11.json`, confirmed by matching sha256). The failures are real and reproducible, not a reporting artefact: criterion 2 (`over_threshold_total`=407, L0_sparse's 328 exceeding the 200-example enumeration cap) and criterion 4 (L0_sparse 8652/11536 = 75% violations, a majority) both fail on their own stated wording ("zero violations... or an enumerated residual explained record by record"), independent of either tool's own looser `verdict` field.

## Phase 2 gate verdict (grounded re-run): NOT CLOSED (unsuccessful)
No `Workflow-Phase` trailer applied. All three conditions attached to this re-run before the gate verdict could count were met: (a) the continuity and boundary-mirror checks are committed, tested tools under `parser/tools/` (`continuity_census.py`, `boundary_mirror_census.py`); (b) the mirror check has block- and blockset-crossing neighbour lookup (via `r_neighbours.py`, 2-09); (c) the divided_pardiv1 continuity re-measurement used a tolerance fixed in absolute raw units (`EDGE_TOL_RAW=4`, `PAIR_TOL_RAW=16`), not a fraction of the range under test — the circularity flagged in the provisional 122 m median is resolved (divided_pardiv1 now shows a 0.0 m median with a genuine, fully-enumerated 38-pair residual, not a tolerance artefact).
Criteria 1, 3 pass; criterion 5 passes with a named, fully-enumerated residual. **Criteria 2 and 4 fail**, each on real, reproducible numbers, not a reporting artefact: criterion 2's `over_threshold_total`=407 (L0_sparse 328 of these exceed the enumeration cap, unexplained record-by-record); criterion 4's L0_sparse 8652/11536 (75%) boundary-node mirror violations, a majority. Per the design's own binding rule ("if the criteria genuinely still fail once run for real... report unsuccessful — do not force a close"), the gate does not close. The Assumption Ledger entry "Coordinate range 4096/16384 is the true full-cell range" is left untouched, per DESIGN.md line 252, since Phase 2 does not close here.

## Carried (Phase 2 grounded re-run, updated)
1. Word 7 rule: CLOSED (adopted, 2-07). 2. y orientation: CLOSED. 3. walk.py L0-sparse frame: CLOSED.
4. `rg_size` (word 16) — OPEN, a DESIGN gap; the orchestrator must resolve before Phase 4.
5. Pointer non-frame targets — OPEN, Phase 9's.
6. Stale `LENGTH_BASIS` wording in `road_density_census.py` — OPEN, cosmetic.
7. `header.pointer_nonframe_targets.examples` does not regenerate identically — OPEN, pre-existing, unrelated to this gate.
8. `coord_scale_census._work` builds `WalkedParcel` without `frame_bounds` (075fc99 fixer inert in that tool's own worker path) — OPEN, harmless for criterion 1, confirmed by 2-12; a future frame-sensitive reuse of that worker must fix it first.
9. **Criterion 2 (cross-parcel continuity) fails — OPEN, decisive.** `over_threshold_total`=407; L0_sparse's 328-pair residual exceeds the enumeration cap and is not record-by-record explained. Needs either a larger enumeration/explanation pass or a structural finding about why these pairs don't land together.
10. **Criterion 4 (boundary-node mirror) fails at L0_sparse — OPEN, decisive.** 8652/11536 (75%) violations, majority same-block, not fixable within a fixed-constant unit's scope. 2-11's worker hypothesized L0_sparse leaves may not tile edge-to-edge the way other classes do, or need a different mirror rule for the tile frame — untested, a re-analysis question for the user/next design pass.
11. Prior Phase 1 Carried items 1, 3, 5, 6, 7 remain with their original owners.

---

# Phase 2 run (frame-adjacency remediation, 2026-09-23)

- Tool: Claude Code (Agent SDK), orchestrator model Sonnet 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-23
- Scope: Phase 2 only (gate), under `DESIGN.md` Decisions "Amendment 2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot". Root cause: `r_neighbours.py` stepped one leaf slot instead of one coordinate frame, inflating `L0_sparse`'s denominator 16x and self-comparing 12/16 aliased slots. Units 2-13, 2-14, 2-15, strictly sequential, briefs already authored (no `refine` dispatch needed).
- Model tier this run: Opus at medium reasoning effort for `refine`/design-reasoning dispatch (not needed here); Sonnet at medium reasoning effort for build/worker dispatch.
- Status: units in progress.

### 2-13 frame-adjacency — done (1e92b8b, Sonnet)
Built: frame-level adjacency in `parser/tools/r_neighbours.py` alongside the unchanged leaf-slot API — `RAW_PER_SLOT=4096` (pre-stated), `FrameId`, `FrameNeighbour`, `frame_of`, `frame_neighbour`, `corner_frames`, `to_global`, `to_frame_local`, `frame_extent_slots`, `_load_coord_scale`; output note `l0_is_per_leaf_slot` text rewritten (key kept) to point callers at the frame API. Fixed `coord_scale_census.py`'s `_work` `WalkedParcel` construction to thread real `frame_bounds`/`frame_range`/`frame_class` from `walk._leaf_frame`/`walk._frame_range` (075fc99's fixer now takes effect in that worker). 6 new synthetic-fixture tests in `test_r_neighbours.py` (no disc).
Evidence: `test_r_neighbours.py` 7 -> 13, all pass; full suite 392 -> 398, all pass (net +6, no regressions). Against R: L0 (40-block sample) `frame_status_counts` resolved 20,856 / outside_coverage 80 / empty_slot 8, crossings same_block 19,106 / cross_block 1,527 / cross_blockset 313, both classes present (n=1 slots 192, n=4 slots 80,704), `frame_tile_disagreements=0`. L2 resolved 152,184 / outside_coverage 168 / empty_slot 224, crossings same_block 147,632 / cross_block 2,376 / cross_blockset 2,176. L6 (whole 6-block population) resolved 3,550 / outside_coverage 27 / empty_slot 95, crossings same_block 3,360 / cross_blockset 190, **cross_block 0 at L6** (reported as-is, not forced — matches 2-09's structural finding that L6 has one block per blockset). `coord_scale_census.py` re-run (452,199 parcels): `ranges`/`class_rule` structurally identical to committed `coord_scale.json`, `exceeds_max` still 0 in all 28 classes — criterion 1 unmoved. `lint_schema.py` 513/0 before and after.
Deviation, reported not hidden: also changed the adjacent `MeshLocation(bounds=...)` argument from `lb` to `frame_bounds` in the same `_work` block (brief named only the `WalkedParcel` construction) — needed because forward decode (`MeshLocation.bounds`) and reverse `_raw` (`WalkedParcel.frame_bounds`) must use the same bbox to round-trip; verified criterion 1's maxima did not move. No contradictions found; no pre-stated constant changed after a result.
Frame-adjacency API landed for 2-14 (signatures in the worker's report): `frame_of(idx, handle, class_rule, ranges) -> (FrameId, bool)`; `frame_neighbour(idx, frame, edge, class_rule, ranges) -> FrameNeighbour`; `corner_frames(idx, frame, corner, class_rule, ranges) -> FrameNeighbour`; `to_global(frame, x_local, y_local) -> (X, Y)`; `to_frame_local(frame, gx_raw, gy_raw) -> (x, y)`; `frame_extent_slots(ranges, level, cls) -> int`; `_load_coord_scale() -> (ranges, class_rule)`.

### 2-14 continuity-and-mirror-rerun — done with concerns (a51e734, Sonnet)
Found substantial pre-existing uncommitted WIP on `parser/tools/continuity_census.py` and `parser/tools/boundary_mirror_census.py` that already correctly implemented the brief's contract (frame-level adjacency via `r_neighbours`' `FrameId`/`frame_of`/`frame_neighbour`/`corner_frames`, exact-only selection/pairing, `EDGE_TOL_RAW`/`PAIR_TOL_RAW`/`FRAME_EXTENT_TOL_REL` retired, corrected verdict logic, `scale_mismatch` redefinition, corner-node any-sharing-frame rule). Built on it rather than rewriting — zero tool-code changes needed. Both test files rewritten against the frame-level API: `test_boundary_mirror_census.py` fixed two genuine fixture bugs (ENDS3 not aliasing all 16 sparse-tile slots per R's own documented invariant; wrong `corner_nodes` expectation) plus two new fixtures; `test_continuity_census.py` fully rewritten (stale since 2-10, 5x AttributeError on HEAD), 12 tests.
Evidence: combined census tests 25/25 pass; full suite 407 passed (no regressions); `lint_schema.py` 0 errors before and after; both tools run twice against R, identical sha256 both times (continuity `da70cd59...`, mirror `23854cf5...`).
Criterion 2 (continuity), denominator/matched/violations/verdict: L0_urban 473/470/3/pass_with_residual, L0_sparse 686/686/0/pass, L2 547/547/0/pass, L4 416/416/0/pass, L6 379/379/0/pass, L8 33/33/0/pass, divided_pardiv1 979/983/4/pass_with_residual (52 parents, exact midline, no tolerance). Total violations 7, cap 400, not exceeded, every residual enumerated record-by-record. Criterion 3 unchanged: 0/1,037,716, pass.
Criterion 4 (mirror), denominator/matched/violations/verdict: L0_urban 522/521/1/pass_with_residual (`cross_class_split` L0_urban<->L0_sparse: 113 matched/1 violation), L0_sparse 721/721/0/pass (matches the design-agent amendment's cited expected figure exactly), L2 4065/4061/4/pass_with_residual (2 corner nodes, both matched), L4 825/825/0/pass, L6 746/746/0/pass, L8 66/66/0/pass. `cross_block` and `cross_blockset` each carried at least one match (e.g. L0_sparse cross_block 57, cross_blockset 2, both matched).
Divided `pardiv1`'s provisional marking (DESIGN.md 2026-09-23 user amendment) is lifted: 979 matched / 4 violations / 983 denominator at exact midline, zero tolerance.
Deviations/findings (not corrected, reported as such): actual figures are far smaller than the design-agent amendment's "expected, comparison-only" numbers (e.g. L0_urban mirror denominator 522 here vs 100,958 cited; pardiv1 983 nodes vs 3,300 cited) because both tools sample (`SAMPLE_BLOCKS=60` continuity, 40 mirror) rather than scanning the whole disc, matching the sampling convention 2-09/2-10/2-11 already used — a scope note, not a regression. Unresolved contradiction, documented verbatim in both tools' JSON output rather than resolved silently: `RESIDUAL_ENUM_CAP=400` (brief) vs `200` (DESIGN.md design-agent amendment) — moot for this run since every residual (7 + 5 = 12) is far under both caps. No pre-stated constant changed after seeing a result.

### 2-15 grounded-gate-verdict — done (4deca2d, Sonnet)
Re-ran all five grounded criteria for real against R post 2-13/2-14, rewrote `GATE-2.md` in place (supersedes 2-12), wrote `EVIDENCE-2-15.json`.
- **Criterion 1 PASS**: `exceeds_max`=0/28 classes, 452,199 parcels; `ranges`/`class_rule` structurally identical to committed profile; confirmed 2-13's `frame_bounds` fix is threaded through `coord_scale_census.py`'s worker and the numbers did not move. sha `b2d21b66...` matches `EVIDENCE-2-12.json`.
- **Criterion 2 PASS WITH RESIDUAL**: 7 violations / 3,517 matched (per class: L0_urban 473/470/3, L0_sparse 686/686/0, L2 547/547/0, L4 416/416/0, L6 379/379/0, L8 33/33/0, divided_pardiv1 983/979/4); every residual individually traced (2 duplicate-node collisions, 1 genuine 126-raw-unit offset, 4 dead-end-at-midline sibling lookups). sha `da70cd59...` matches `EVIDENCE-2-14.json`.
- **Criterion 3 PASS**: 0/1,037,716 shape points, same run as criterion 2.
- **Criterion 4 PASS WITH RESIDUAL**: 5 violations / 7,346 matched (per class: L0_urban 522/521/1, L0_sparse 721/721/0, L2 4065/4061/4, L4 825/825/0, L6 746/746/0, L8 66/66/0). **L0_sparse now 721/721/0** — the decisive reproduction of the design-agent amendment's re-measurement, reversing 2-12's 8,652/11,536 (75%) failure. `L0_urban<->L0_sparse` cross_class_split (113 matched/1 violation) is the committed two-sided evidence for 16384=4x4096, named as the brief required. L2's 4 residuals are 0-2 raw-unit rounding; L0_urban's 1 is a 51-raw-unit offset, reported as a measurement without further trace. sha `23854cf5...` matches `EVIDENCE-2-14.json`.
- **Criterion 5 PASS WITH RESIDUAL**: unchanged mechanism/disposition from 2-12 (word 7 0.999995 named 28-record residual; words 10/11 miss only on unseen table keys). sha `eef25d90...` matches `EVIDENCE-2-12.json`.
- **Overall verdict: CLOSED.** No criterion fails; every residual fully enumerated and individually traced to a named mechanism, none over `RESIDUAL_ENUM_CAP` under either cited value (400 or 200).
- **Assumption Ledger updated** (only entry touched in DESIGN.md, per its own rule): "Coordinate range 4096/16384 is the true full-cell range" now states Phase 2 tested it and what it rests on (global raw lattice, n x n frame model, `L0_urban<->L0_sparse` two-sided evidence).
- `docs/schema/map-frame.md`/`UNKNOWNS.md` updated: criteria 1-4 moved to verified with restated wording; `lint_schema.py --write` 513 -> 508 unverified rows, 0 errors before/after. `pytest parser/tests -q`: 407 passed before and after (no code changed).
- Carried: closed items 5 (2-13, `frame_bounds`), 6 and 7 (2-13/2-14, L0_sparse continuity and mirror fixes) named explicitly; new open items — (8) `RESIDUAL_ENUM_CAP` 400-vs-200 contradiction, still unresolved, moot at 12 total residuals against either value; (9) `continuity_census.py`'s greedy exact-match double-counts up to 1-2 L0_urban residuals from duplicate source nodes at one boundary point (correctly counted/enumerated, not a correctness bug, future cleanup); prior Phase 1 items 1/3/5/6/7 carried unchanged.
Deviations: none from the brief. No contradiction between the brief and its cited contracts beyond the already-carried `RESIDUAL_ENUM_CAP` discrepancy.

## Phase 2 verification (orchestrator, this run)
Independently re-ran `pytest parser/tests -q` (407 passed) and `lint_schema.py` (508 unverified rows, 0 errors) against the post-2-15 tree — matches 2-15's own reported figures exactly. Cross-checked `EVIDENCE-2-15.json`'s `rerun_out_sha256_run1`/`run2` and `matches_evidence_2_14_sha` fields against `EVIDENCE-2-14.json`'s `reproducibility.continuity_census_sha256`/`boundary_mirror_census_sha256`: `da70cd597ed800763c4b9368664948842fc65205faecdd0df560d754e4b6d377` (continuity) and `23854cf540b3c6519f0945f7fb787890859787f1e3ef214a3f1fb646ad6733e4` (mirror) match byte-for-byte across both units' independent runs — this is a real, reproducible re-run against R, not a copied or fabricated report. Read `GATE-2.md` in full: every quoted criterion wording matches DESIGN.md's amendment text, all five per-criterion numbers/denominators/verdicts are internally consistent with `EVIDENCE-2-15.json`, and the binding rule ("if any criterion fails, the verdict is NOT CLOSED... do not close on four of five") was correctly applied — no criterion fails on this run. Reviewed the `DESIGN.md` diff in `4deca2d` directly: only the single Assumption Ledger entry for the coordinate range was touched, exactly as the brief requires; no other DESIGN.md content, no new amendment section.

## Phase 2 gate verdict (grounded re-run, frame-adjacency remediation): CLOSED
Commit `4deca2d` did not itself carry the `Workflow-Phase` trailer (units never apply it — the orchestrator does). Closing trailer applied in a following commit on this branch. All conditions the coordinator attached to this run were met before closing: (a) `continuity_census.py`/`boundary_mirror_census.py` promoted to committed, tested tools under `parser/tools/` (2-10/2-11, re-verified 2-14); (b) block- and blockset-crossing neighbour lookup added to the mirror check via `r_neighbours.py`'s frame API (2-13); (c) the divided-parcel continuity result re-measured at exact lattice equality (no tolerance at all, stronger than an absolute-unit tolerance) — 979/983, 4 violations, individually traced, no longer provisional.
Criteria 1 and 3 pass at zero violations. Criteria 2, 4 and 5 pass with residuals, every one fully enumerated (source identifiers, raw coordinates, counterpart frame) and individually traced to a named mechanism — none asserted on a plausible story, none over the enumeration cap under either cited value. The decisive figure — `L0_sparse`'s boundary mirror — reverses from 2-12's 75% failure to 721/721/0 under frame adjacency, and the `L0_urban<->L0_sparse` cross-class crossing (113/114) stands as the two-sided evidence for 16384=4x4096.

## Carried (Phase 2, final)
1. `rg_size` (word 16) — still OPEN, a DESIGN gap; the orchestrator must resolve before Phase 4.
2. Pointer non-frame targets — still OPEN, Phase 9's.
3. Stale `LENGTH_BASIS` wording in `road_density_census.py` — still OPEN, cosmetic.
4. `header.pointer_nonframe_targets.examples` does not regenerate identically — still OPEN, pre-existing, unrelated to this gate.
5. CLOSED by 2-13: `coord_scale_census._work` now threads `frame_bounds`/`frame_range`/`frame_class`.
6. CLOSED by 2-13/2-14: criterion 2's L0_sparse under-enumerated 328-pair residual (2-12) is gone under frame adjacency (686/686/0); divided_pardiv1's residual persists in a smaller, fully-traced form (4/983).
7. CLOSED by 2-13/2-14: criterion 4's L0_sparse failure (8,652/11,536, 2-12) reverses to 721/721/0 under frame adjacency.
8. **OPEN — `RESIDUAL_ENUM_CAP` value contradiction.** `parser/tools/continuity_census.py` and `boundary_mirror_census.py` both set 400; DESIGN.md's design-agent amendment states 200 for the same cap. First reported 2-14, restated 2-15, never resolved across three units in scope to report it but not fix it (`parser/**`/`DESIGN.md` criteria text both out of scope for those units). Does not affect this phase's outcome (residuals never approach either value) — a future unit or the next design pass should reconcile the two sources.
9. **OPEN, minor, not a correctness bug.** `continuity_census.py`'s greedy exact-match can double-count residuals when two source nodes decode to the same global boundary point (up to 1-2 of L0_urban's 3 criterion-2 residuals). Correctly counted and enumerated either way; a future unit touching `continuity_census.py` may want to dedupe source nodes the way target nodes already are.
10. Prior Phase 1 Carried items 1, 3, 5, 6, 7 remain with their original owners, unchanged.
Does not declare Phase 2 closed (2-15's job).

---

# Phase 3 run (native coordinates, 2026-09-23)

- Tool: Claude Code (Agent SDK), orchestrator model Sonnet 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-23
- Scope: Phase 3 only ("Native coordinates"), under `DESIGN.md`'s Phase 3 Outcome as amended 2026-09-23 ("grounded phase gates"): `range_for` feeds both encoders and no `COORD_RANGE` constant remains; the `coord_scale` check PASSES; two builds are byte-identical at worker counts 1, 4 and 12; `pytest parser/tests` passes; zero parcels exceeding their class range; a per-vertex quantisation round-trip (lat/lon -> pixel -> lat/lon) agrees within half a pixel for every vertex written.
- Model tier this run: Opus at medium reasoning effort for `refine`/design-reasoning dispatch; Sonnet at medium reasoning effort for build/worker/research dispatch.
- Status: no Units list in DESIGN.md for Phase 3 and the surfaces span multiple files/encoders — `refine` dispatched.

## Phase 3 run, resumed (2026-09-24)

- Tool: Claude Code (CLI, remote-control), orchestrator model Opus 5.5
- Session: https://claude.ai/code/session_01GLBUseFWng4Gw3XZHwPQYv
- Started: 2026-09-24T00:18:53+10:00
- Model tier this run (user-directed): Opus 5.5 at medium reasoning effort for every dispatched worker, verifier and helper (agent `opus-medium`).
- Resume state: no Phase 3 unit had a recorded outcome. The working tree held uncommitted, unreported edits in 3-01's owned paths (`coordconv.py`, `road.py`, `background.py`, `name.py`, `model.py`, `harness/walk.py`, three censuses, new `tests/test_coordconv.py`) from the prior run's stalled 3-01 worker. Not resumed by message: a fresh 3-01 worker is dispatched with those edits as its handoff, to verify against the brief and keep or discard.

### 3-01 decode-side-range — done with concerns (e029952, Opus 5.5)
Built: `coordconv.range_for` (reads `coord_scale.json`, memoised, raises on absent triple, 4096 for divided sub-parcels); `xy_to_latlon`/`latlon_to_xy`/`encode_region_coord` take keyword `coord_range` (default `_LEGACY_RANGE = 32768`, temporary), inclusive bound; `BoundingBox.coord_range`; decoders in road/background/name take the frame's range; `walk.leaf_frame_range`/`with_range`, one class-arithmetic home; censuses invert at the frame range. Surfaces: the brief's owned paths plus `parser/tools/continuity_census.py`. Kept the stalled worker's `range_for`/signatures/model/decoder/road_density edits and `test_coordconv.py`; rewrote walk and coord_scale_census; reverted its `overlay_test.class_range` change.
Evidence: `test_coordconv.py` 24 pass (collection error before); pytest 407 → 431 pass; `coord_scale_census` on R identical `ranges`/`class_rule`, `exceeds_max` 0 ×28; continuity `da70cd59…` and mirror `23854cf5…` **reproduce** 2-14; `overlay_test` output byte-identical before/after (`97bc1564…`). G not rebuilt (encoders unchanged, default 32768).
Deviations: `walk.iter_parcels` decodes divided sub-parcels against the parent slot (`frame_class="divided_parent"`) — R's criterion-3 evidence shows sub-parcel coords are absolute in the parent frame; changes `road_density_census` lengths for sub1–3 only.
Contradictions (brief amended — 3-02, 3-03, 3-04 carry an "Amendment after 3-01"): public `COORD_RANGE` kept as alias (importers not owned); grep check cannot pass yet (`_cenc.c`, `synth.py`, alias); `overlay_test.DECODER_RANGE` kept as alias (test not owned); `road_density_census` frameless fallback (test not owned). 3-03's owned paths extended to remove all shims.
Agent: 47 tool uses, ~122k tokens.

### 3-02 encoders-take-range — done with concerns (1ec910a, Opus 5.5)
Built: `_cenc.c` loses `COORD_RANGE`/`COORD_MAX`; `Bounds` carries `range`/`cmax`; `kw_encode_cell`/`kw_bg_shape`/`kw_measure_cell` take trailing `double coord_range`; `cenc.py` plumbing; `synth.py` drops the `COORD_RANGE` import, adds `frame_range(bounds, coord_range=None)`, range-relative clamp, every conversion passes `coord_range=`; writers explicit; stored-pixel (`n_x`/`n_y`) preference removed in both encoders. Surfaces: brief's owned paths.
Evidence: pytest 447 → 465 pass; new `test_cenc.py` cases 16 fail → pass, C-vs-Python equivalence at 32768/16384/4096; `git grep COORD_RANGE\|COORD_MAX -- parser/kiwiw` → only the `coordconv` alias (3-03's). Isolation probe: new code with only the stored-pixel branch restored == HEAD (disc `1518dc62…`, Perth `1d29e76e…`). New baseline disc `9407122122b9…`, Perth `99d72f0b1cf14b8b…` (`-j 1` == `-j 4`).
Deviations: bytes moved — spool's stored road y is y-down (extracted pre-2-06); x agrees everywhere, y agrees with y-down on all but midpoint nodes at every level. Accepted by the orchestrator as a design-mandated latent-defect fix (brief amended, a513745). Used `output/extract_timing/spool` (`output/spool` is a legacy pickle spool `SpoolReader` rejects); scratch in `output/scratch-3-02/` (`/tmp` quota).
Contradictions: brief's expected shas `51c254ac…`/`e275879f…` predate 2-06 and don't reproduce at HEAD; `encode_region_coord(32768, 32768)` = 65536 overflows the region field — encoders cap at `min(range, 32767)` transitionally; 3-03's brief now owns removing the cap and making overflow raise.
Agent: 78 tool uses, ~93k tokens (two turns: report, then commit on decision).

### 3-04 coord-scale-check-and-roundtrip — done with concerns (9db5b2f, Opus 5.5)
Built: `harness/checks/coord_scale.py` (`id=coord_scale`, range via `walk.leaf_frame_range`, inclusive `[0, range]`, Map Frames shared by slots judged once, unranged parcels FAIL); `tools/quantisation_roundtrip.py` (every spool vertex lat/lon → round → clamp → lat/lon, per level/class/kind JSON, exit 0 only on pass); 16 tests. Surfaces: the four owned new files only.
Evidence: pytest 431 → 447. Check on R: PASS, 0/452,199 parcels exceed (28 classes; observed maxima as `coord_scale.json`). Check on pre-3-02 G: FAIL 448,824/452,540 (still 32768), 632 unranged (`pardiv2`). Round-trip on `output/extract_timing/spool` (17 s): road nodes/points 42,195,850 each, 0 fail; name anchors 1 fail of 2,006,629; **background vertices 10,652,030 fail of 126,425,744** (all clamped; worst overshoot 3.5M raw at L0 sparse).
Commands: `compare_disc.py --generated <disc> --checks coord_scale --no-manifest --report <out>` (~10 min G, ~16 min R); `tools/quantisation_roundtrip.py --spool output/extract_timing/spool --out <out>`.
Deviations: check does its own `iter_parcels` walk (Context caches only counts; `context.py` not owned); over line budget (~690 vs ~400).
Concerns: (1) spool background polygons are not clipped to their cell (8.4% of vertices outside the frame, encoders clamp) — the per-vertex round-trip cannot pass on encoder migration alone; **escalated to the user**. (2) check classes L0 by frame structure, so encoding G's per-slot L0 frames at 16384 would fail — resolved by amending 3-03 (8e0f237): G's range follows its written frame shape (4096), per DESIGN's L0-sparse Open Question. (3) G's `pardiv2` has no `coord_scale.json` triple — resolved in the same amendment: any `pardiv<t>_sub<i>` → parent's 4096 (spec 7.2.2.1.1.2, type-independent). (4) spool `p_` points duplicate node coordinates (minor, carried).
Agent: 58 tool uses, ~133k tokens.

### Research: R's background geometry at the frame edge — done (Opus 5.5, read-only)
Asked by the user ("I'd be relying on matching R behaviour … align your test appropriately") after 3-04's concern 1. Finding: **R clips** background polygons and lines to the frame — 0 vertices outside `[0, range]` in every sampled class (L0 urban/sparse, L2–L8); corner vertices mirror exactly into the neighbour frame ≥ 98%; crossing vertices mirror 75–87% exact, > 90% within 4 raw (clamping would give ≈ 0); many edge-running segments, few spikes; whole-cell fills are frame rectangles; no pen-up; almost no bridges (re-entering polygons are separate pieces). No spec rule for backgrounds (roads: 7.A ②); conclusion is empirical. Outputs in `output/research-3-bg/` (gitignored). ~18 tool uses, ~98k tokens.
Decision: new unit **3-07** (`briefs/3-07-clip-to-frame.md`) — clip, never clamp, in the global raw lattice before rounding, proper piece splitting, C == Python; round-trip redefined over written (post-clip) vertices. Units table in DESIGN.md updated: 3-05 and 3-06 now also depend on 3-07; their briefs amended.

### 3-03 build-path-supplies-range — done with concerns (b94c23a, Opus 5.5)
Built: `osm_to_parcel_geometry.g_frame_class`/`g_frame_range`/`frame_bounds` (one class helper; every G L0 frame and leaf 4096 per the 3-04 amendment); `build_alldata` passes the range to the C encoder; `divide.py` encodes sub-parcels against the parent's bounds at 4096 (Map Frame header records the parent's SW corner); `range_for` returns 4096 for any `pardiv<t>_sub<i>`, raises on malformed/unknown; `_LEGACY_RANGE`, the `COORD_RANGE` alias, encoders' 32767 cap, `CellEncoder.encode` default, decoder fallbacks (`BoundingBox.require_range()` raises), `DECODER_RANGE` and the road-density frameless fallback all removed; `encode_region_coord` rejects region > 7.
Evidence: pytest 465 → 462 pass + 1 fail (3-04's `test_unranged_class_fails` asserts `pardiv2` unranged — contradicted by the amendment). Full disc `e1ca51eca9a4…` (1,397,923,200 B, 33.9 s, `output/scratch-3-03/`); Perth `d0bb3240b8cc…` `-j 1` == `-j 4`. `coord_scale` on the new disc: **PASS, 0 of 453,171 parcels exceed** (90 classes). Continuity `da70cd59…` / mirror `23854cf5…` reproduce. `git grep COORD_RANGE -- parser/kiwiw parser/harness parser/tools` → only `COORD_RANGE_RL`.
Deviations: edited outside owned paths to keep the suite green once a missing range raises — `kiwiw/parcel.py` now decodes at a named `PARSE_RANGE = 32768` (the `mesh.locate_parcel` parse path knows only the leaf box), `kiwiw/alldata_writer.py` re-encodes at it, ~11 test files one-line range fixes. `_cenc.c` still has a `PACK_MAX` 32767 clamp (no effect ≤ 16384). Tests written alongside, not first. ~95 tool uses, ~84k tokens (slightly over turn budget).
Findings: (a) `PARSE_RANGE` is the legacy 32768 under a new name, against the outcome's "no `COORD_RANGE` constant remains" intent → fixer unit **3-08** (`briefs/3-08-parse-path-range.md`). (b) On the real disc every sub index, sub0 included, reaches 4096 (R: sub0 2048): G does not clip sub-parcel content to its quadrant. Not a range violation. Background side placed in 3-07's clip rectangle; road side carried to Phase 5 (division).

### 3-08 parse-path-range — done with concerns (3fc686f, Opus 5.5)
Built: frame rule has one home in `kiwiw/mesh.py` (`leaf_frame`, `leaf_frame_range`, `leaf_frame_shape`, `is_sparse_tile`, `tile_bounds`, `narrow_bounds`, `sparse_memo`); `walk` re-exports its old names from there; new `mesh.locate_frame` (location + frame box + range; tests the 4x4 tile from the loaded block's mapinfo slots); `disc.find_parcel` and `roundtrip_parcel_content.py` use it; `parcel.py`'s `PARSE_RANGE` and fallback deleted; `alldata_writer.load_region` decodes each leaf against `mesh.leaf_frame`; 3-04's `test_unranged_class_fails` now exercises an unknown level and L10 divided, plus new `test_pardiv2_is_ranged_at_parent_4096`.
Evidence: `git grep -nE "PARSE_RANGE|32768" -- parser/kiwiw parser/harness` → one `_cenc.c` comment only. pytest 462+1 fail → 464 pass, 0 fail. `roundtrip_alldata_full.py` default: 87/87 in-place byte-identical, 84/84 de novo, PASS; L0 blockset 22: 65,571/65,571 and 65,568/65,568, PASS. Parse path vs `walk.iter_parcels` on R: identical lat/lon (max diff 0) for L0 urban (4096), L0 sparse (16384), L8 divided sub-parcel (4096), L6 leaf (4096).
Deviations: `locate_frame` added beside `locate_parcel` (which keeps the leaf box); `disc.find_parcel(...).location.bounds` is now the decode frame (tile/parent slot for sparse/divided leaves); `walk._is_sparse_tile` takes entries. ~40 tool uses, ~103k tokens.

### 3-07 clip-to-frame — done with concerns (ab7681b, Opus 5.5)
Built: `kiwiw/clip.py` (frame-local raw floats before rounding; Liang–Barsky segment cut with fixed endpoint order; Weiler–Atherton ring assembly with corner insertion; even-odd whole-frame cover; re-entering polygons → separate CCW pieces; lines → one record per inside run; post-round removal of repeats/spikes/zero-area); identical algorithm in `_cenc.c` (`kw_bg_shape` takes the clip rect; `bg_shape_records` wrapper), `PACK_MAX` gone; `synth.py` background clamps and `_bg_fast` removed, written vertices asserted inside the rect; long steps split to fit one signed byte; every ring written CCW; `quantisation_roundtrip.py` measures written (post-clip) vertices by origin and asserts in-rect / crossing-on-edge / no step overflow.
Evidence: pytest 464 → 504. Round-trip: background 134,877,414 written, **0 failing**, worst 0.49999995 raw (original 100.7M, crossing 2.6M, corner 343k, step-split 31.2M; 0 outside, 0 off-edge crossings, 0 overflow; 18,216 shapes wholly outside dropped); n/p 42,195,850 each, 0 fail; **s (name anchors) 1 failing of 2,006,629 → tool exits 1**. Full disc `aa4907193f2e…` (1,414,851,520 B, 36.7 s, `output/scratch-3-07/G/`); Perth `afaa0c10336c…` `-j 1` == `-j 4`; `coord_scale` PASS, 0 of 452,619. Probe vs R: 0 vertices out of range at every level (R 0); corner mirror G 105/417 L0 vs R 1463/1464; **crossing mirror G ≈ 2% exact vs R 75–87%**; a few bridges/spikes in G.
Deviations: edited `divide.py` (outside owned paths) so a sub-parcel passes its quadrant clip rect; over line budget (~1,430 added vs ~600) for the byte-identical C port; round-trip tool checks divided shapes against the full cell rect.
Concerns: (1) **content loss at cell edges** — the extractor (`osm_to_parcel_geometry.py:950`) and `divide.py` assign each whole background shape to one cell by centroid; clipping now drops the overhang (≈ 8.4% of vertices) and the neighbouring cell never received the shape, hence the ≈ 2% mirror. R's mirror shows R assigns a shape to every cell it overlaps. (2) One name anchor (lat −38.7273, lon 77.519, St Paul/Amsterdam Is. region) assigned to L0 cell (0, 541) whose frame starts at lon 90 — extractor cell-assignment bug, pre-existing (also in 3-04's run). (3) Residual bridges/spikes in G, uninvestigated. ~103 tool uses, ~67k tokens.

### Orchestrator decision after 3-07 (2026-09-24)
The user asked that G match R. R's frame-edge mirror shows that R gives a background shape to every cell it overlaps, so G's centroid-only assignment is a defect exposed by clipping, not a new scope. Two fixers were added. **3-09** (`briefs/3-09-shape-to-every-overlapped-cell.md`) makes every existing cell and divided sub-parcel receive each shape it overlaps, at assembly time from the spool (no re-extraction), independent of `-j`. **3-10** (`briefs/3-10-name-cell-clamp.md`) fixes the root cause in `assign_to_parcel`, which clamps an out-of-span longitude into an edge cell, and drops name records outside their cell at assembly, with counts. 3-05 and 3-06 now also depend on 3-09 and 3-10, and their briefs are amended. 3-07's concern (3), the residual bridges and spikes, is re-measured by 3-09's probe.

### 3-09 shape-to-every-overlapped-cell — done with concerns (3738613, Opus 5.5)
**Built:**
- New `kiwiw/overlap.py`, a deterministic per-level pre-pass that runs in parallel over spool chunks.
  - A shape that reaches outside its own cell is recorded against the cells its outline passes through, plus, for polygons, the cells wholly inside it.
  - Only existing cells receive shapes: spool cells plus the level mask fill. The rest are counted as skipped.
  - A wholly covered interior cell gets a small ring just outside the cell, which clips to the same frame rectangle.
  - Order within a cell: own shapes in spool order, then borrowed shapes by source `(iy, ix)` and spool index.
- `build_alldata.py` merges borrowed shapes after mask fill, on both the C and Python paths, and records the counts in the manifest under `"overlap"`.
- `divide.py` sub-parcels receive every shape whose clip to their sub-rectangle is non-empty.
- `quantisation_roundtrip.py` measures borrowed shapes too.
- New `test_overlap.py`, 7 tests.

**Evidence:**
- pytest: 504 → 511.
- Full disc `860e78018c73…` at 2,137,628,064 B, up from 1,414,851,520. Wall time 98.7 s (was 36.7), peak RSS unchanged at about 828 MB.
- Perth `0eecee390fc2…`, identical at `-j 1` and `-j 4`.
- `coord_scale` PASS: 0 of 1,461,362 parcels exceed.
- Round-trip: background 273,418,176 written, 0 failing, worst 0.49999999. The name-anchor failure is still 1 (3-10's).
- Overlap at L0: 708,857 shapes shared, 1.91M outline cells, 1.58M interior cells, 821,967 skipped (cell absent).
- Divided parents at L0: 544 → 564. L0 background trim: 168 → 227.
- Crossing mirror, exact / ≤ 4 raw:

  | Level | G | R |
  |---|---|---|
  | L8 | 81 / 100 | 88 / 96 |
  | L6 | 91 / 98 | 90 / 95 |
  | L4 | 92 / 99 | 100 |
  | L2 | 95 / 99 | n/a |
  | L0 | 99 / 99.5 (6,000 frames) | 76 / 98 |

**Deviations:**
- At 400 frames every sampled L0 frame is now a covered interior rectangle, so the L0 probe was re-run at 6,000 frames.
- Over the line budget: about 640 lines including tests.

**Concerns:**
1. The disc is 2.14 GB against R's 1.53 GB. 3-07's one-byte step split densifies each whole-cover frame rectangle to about 130 points, and the densified vertices went from 31M to 141M. The large type-288 polygons span up to about 1.2M L0 cells. Whether R densifies whole-cover rectangles the same way is unverified.
2. Build time is 2.7× longer.
3. L0 edge spikes: 607 per 6,000 frames in G, against R's 9 per 400.

### Research: does R densify whole-cover background rectangles the same way? (2026-09-25, read-only)
Asked by the user to validate 3-09's concern 1 before continuing the phase. Finding, from a read-only probe against R and against G's decode path (`background.py`'s `mult_const = 1 << extract(addl, 0, 2)`, `xc += xo * mult_const`): R never densifies a whole-cover rectangle at `mult_const=1` the way G does — it chooses a coarse `mult_const` (observed up to 128) so each edge is written in 3–4 big steps (e.g. an L0-sparse tile in exactly 12 vertices, an L2 frame in 4, L4 in ~10 average), against G's ~130 vertices for the same shape at `mult_const=1` hardcoded since extraction (`osm_to_parcel_geometry.py:534`). This ~10x per-shape overdensification is then multiplied by 3-09's overlap-propagation mechanism (708,857 shared shapes → 3.49M cell-copies), which is itself correct and stays. Two leads, user-approved to integrate without further review ("these don't really need pushing back for human review... objectively improve R fit and are no-loss"):
1. Pick the coarsest `mult_const` at encode time that keeps every vertex exactly representable — provably safe only for the whole-cell-rectangle case (the decoder's accumulator only reproduces a vertex exactly when every delta on that piece is an exact multiple of `mult_const`, so this cannot be a general adaptive search over arbitrary shapes' already-rounded output).
2. Re-measure whether `overlap.py`'s interior-cell duplication is still the dominant cost once (1) lands, since `cover_ring`'s substitute ring is structurally the same rectangle (1) makes cheap.
Decision: two new fixer units, sequenced and dependency-linked, same pattern as 3-07 → 3-09/3-10. **3-11** (`briefs/3-11-mult-const-selection.md`) builds lead 1. **3-12** (`briefs/3-12-overlap-duplication-remeasure.md`) depends on 3-11 and builds lead 2, re-measuring against 3-11's rebuilt disc first — "no code change" is an acceptable, complete outcome if the gap is closed. DESIGN.md's Phase 3 units table updated; 3-05/3-06 amended to depend on both. Outputs left read-only at `output/research-3-density/` (gitignored).

### Orchestrator decision: build-performance is now a standing goal (2026-09-25)
The user set a second, equally binding goal alongside disc-size parity: full-Australia build wall time must stay under about a minute (the baseline before this phase's work was ~35 s; 3-09 alone already pushed it to 98.7 s). Any regression needs its specific mechanism identified, not just accepted as a size/correctness trade-off. 3-12's brief amended to make wall time an explicit measurement alongside size, with its own "if wall time alone is over budget, that's grounds to trim" clause. Applies retroactively as a standing concern to every full-assembly done-evidence report from here on, starting with 3-09's own 98.7 s figure above.

### 3-11 mult-const-selection — done with concerns (25d0fcc, Sonnet 5)
**Built:** `clip.py` gained `_rect_mult` (detects a pre-densify piece equal to the clip rectangle's 4 corners in some rotation; returns the largest `mult_const` in `{128,...,1}` dividing both rectangle edges, else `None`), `_edge_steps` (splits an edge into the fewest exact-multiple-of-`mult` steps, each `<= 127*mult`, distributed evenly to avoid overflow — not "last step absorbs the remainder," which can exceed the signed-8-bit cap for some edge/mult combinations), `_rect_ring` (the exact corner+step vertex sequence at a given mult), `_raw_pieces` (pre-densify clip output factored out), and `shape_pieces(..., auto_rect_mult=True)` returning `(piece, piece_mult)` pairs; every other piece is untouched and stays at `mult_const=1`. `synth.py`'s `_bg_piece_record`/`encode_background_shape_records_scalar` consume the per-piece mult. `_cenc.c` gained the matching `rect_mult_for`/`emit_rect_piece` path (a `write_record` helper factored out of `emit_piece` to share code), kept byte-identical to the Python oracle. Existing `shape_pieces` callers (`divide.py`, `quantisation_roundtrip.py`) default to `auto_rect_mult=False` and are unaffected. `overlap.py` needed no change — `cover_ring`'s substitute ring is always exactly 4 corners, so detection (structural, post-clip) fires on it without a hint.
**Process note:** the first dispatched worker stalled overnight mid-verification (killed with `TaskStop`, no report, no commit) but had left this same implementation, uncommitted, matching the brief's contract; a second worker reviewed it in full against the brief rather than trusting it, then finished verification and committed.
**Evidence:**
- Synthetic fixture: a 4096-edge whole-cell rectangle drops from 133 vertices (mult=1) to 5 at `mult_const=128`; decoded round-trip reproduces the exact same corners.
- pytest: 511 → 516 pass.
- Full disc (`-j 12`, `output/extract_timing/spool`): `87a01b14b612…`, 1,731,021,568 B, down from 3-09's 2,137,628,064 B (−19.0%) — now ~5.4% over R's ~1.53 GB target, was ~39% over. Byte-identical at `-j 1`/`-j 4`/`-j 12`. Wall time 105–123 s, up from 3-09's 98.7 s (small regression, attributed to rect-detection overhead, not re-verified independently — see Concerns).
- Perth `da13a775064…`, identical at `-j 1` and `-j 4`.
- `coord_scale` PASS: 0 of 1,461,347 parcels exceed (73 classes; small count delta from 3-09's 1,461,362 expected from the disc content change, not investigated further).
- Round-trip: background 273,418,176 written, 0 failing, worst 0.49999999 — identical to 3-09's numbers (see Concerns: the tool's own `shape_pieces` call does not pass `auto_rect_mult=True`, so it does not exercise the new path at all).
- Crossing/corner mirror probe, L0 and L4, ~100 frames each: L0 poly exact-crossing 244/244; L4 103/116 exact, 113/116 within ≤4 raw — consistent with 3-09's L0 99/99.5, L4 92/99, no regression (expected: this unit changes vertex density, not cell assignment).
**Concerns:**
1. `quantisation_roundtrip.py` has a coverage gap: it calls `shape_pieces` without `auto_rect_mult=True` (outside this unit's owned paths), so its round-trip numbers do not exercise the new coarse-mult path at all — the "0 failing, unchanged" result is not evidence the new path round-trips correctly by that tool's own measurement, only by the separate synthetic fixture and the mirror probe. Worth a small follow-up unit.
2. Per-level vertex-count tally (before/after, coarse-path vs `mult_const=1`) is incomplete: instrumented at L2/L4/L6/L8/L10 (0 rectangles found — `overlap.py`'s interior-cell rectangles, the dominant source, only occur at L2 (15 cells) and L0 (1,575,723 cells)); a direct tally at L0 was infeasible within budget (forcing the Python path with `KIWIW_NO_C=1` to instrument the C fast path timed out even at L2 within 100 s). The 19.0% disc-size drop and the fact that `cover_ring` always emits exactly 4 corners (always taking the coarse path deterministically) are offered as evidence in its place; 3-12 is tasked with the precise before/after breakdown.
3. Wall time rose again (98.7 s → 105–123 s) despite the size drop, worsening the standing build-performance concern above. Attributed to rect-detection overhead by the worker but not independently isolated. 3-12's brief already treats wall time as a binding goal for this reason.
Agent: two dispatches (first stalled, stopped; second reviewed and finished), 120 + prior tool uses, ~145k tokens on the finishing agent.

### 3-12 overlap-duplication-remeasure — stopped, no outcome (2026-09-25)
The worker was stopped at the user's request after 84 tool calls in ~14 min, with no commit and a clean tree. It had its measurements (full disc `-j 12` 1:48 wall, byte-for-byte the 3-11 content; L0 96.3 s of which overlap pre-pass 26.9 s; round-trip 0 background failing, unchanged; mirror probe run) but spent 21 no-op calls and 8 expired monitors waiting on checks. `compare_disc --checks coord_scale` was run in the foreground piped through `tail`, timed out into the background with an empty output file, and the worker could not tell whether it was alive. Timed afterwards by the orchestrator: `coord_scale` PASS, **783 s single-process** (some contention with a concurrent profiling run); round-trip ~5 min. The original 3-11 worker died the same way: it ended its turn to "wait for the build", which ends a subagent. Remedy for every dispatch from here: chain slow checks in one background script with a status line per step, block on it with one monitor matching every terminal state, never end the turn or spend no-op turns to wait, and treat a check slow enough to need many waits as something to investigate.

### Orchestrator decision: the build hot path moves to C at a cell-range boundary (2026-09-25, user)
Build time tripled from 36.7 s (3-07) to 108 s (3-11) because new per-shape/per-cell work (3-09's overlap pre-pass, 3-11's rect detection) and its tests landed in Python first, with C mirrors added afterwards and a per-shape Python→C handoff on the path. The user's decision: the compute-heavy pipeline goes to C with an absolutely clear boundary, so new build work and its tests land on the C side directly instead of in Python first and then being refactored. The boundary is **one C call per cell range**: C takes the spool bytes for a cell range and returns finished frame bytes (overlap, clip/densify/round, mult selection, record encoding, division). Python keeps orchestration, CLI, worker pool, manifest, and verification/analysis tools. Hot paths and a per-level time budget become design contracts, with a Python/C/handoff profile split required in done evidence. A read-only profiling pass (running) splits L0's time by stage and scopes the port. It feeds a `design` amendment adding the C-pipeline phase and the boundary contract. 3-12 and 3-10 are held until that amendment lands, since tuning the Python path now would be rework.

### Research: where the build time goes, and the C porting scope (2026-09-25, read-only)
Profiled L0 at `-j 12` on HEAD, 3-07 (`ab7681b`) and 3-09 (`3738613`), with per-stage timers summed over workers and scaled to wall. Full build 108.3 s, L0 96.3 s. The L0 split:
- overlap pre-pass `_scan`, Python/numpy: 27.1 s measured (per-shape numpy overhead in `_shape_cell_keys`)
- overlap `merge_raw`, Python: ~30 s (re-serialises every record; 11.25 GB handed to C from a 4.45 GB spool)
- divide fallback for 563 parents, Python with C measuring: ~27 s
- per-cell glue, Python: ~6.5 s
- C encode `kw_encode_cell`: ~5 s (one ctypes call per cell, 3.70M calls, 2.27M of them empty cells)

Attribution: 3-07 → 3-09 is +62 s (pre-pass +28, merge +31, retile +6.5). 3-09 → 3-11 left L0 unchanged (98.3 vs 98.0 s), so **the 3-11 record's "rect-detection overhead" attribution is wrong**. Its 105–123 s spread is outside L0 or noise (not profiled).

Verification tools:
- `quantisation_roundtrip.py` (280 s) runs the overlap scan serially because it calls `build_level` without a pool.
- `coord_scale` (10–15 min) is single-process, uses a full Python `decode_parcel`, and makes a lat/lon round-trip of every vertex inside `parcel_extent`.

The researcher recommended porting the scan and the chunk driver/merge to C behind one call per row range (~50 s est.), with divide kept in Python for now. That is narrower than the user's cell-range boundary decision above, which puts divide on the C side too. The design amendment settles it. Scratch is at `output/research-hotpath/` (gitignored).

# Phase 3C run (build pipeline in C at the cell-range boundary, 2026-09-25)

- Tool: Claude Code (Agent SDK), phase orchestrator model Opus 5.5
- Started: 2026-09-25 (phase orchestrator, dispatched by the user's session)
- Scope: Phase 3C only, per `DESIGN.md` as amended at b62de24 and settled at 6301d91. Phase 3's remaining units (3-10, 3-13, 3-05, 3-06) are not started.
- Model tier this run (user-directed): Sonnet workers (`general-purpose`, `model: sonnet`) for bounded units; `opus-medium` for the hard ports (E2 range encoder, divide in C) and for `refine`. A failed unit gets one retry on the next tier, then stops.
- Status: no Units list for Phase 3C and the work spans several stages — `refine` dispatched.

### refine (Phase 3C) — proceed (87f36cc, opus-medium)
13 units, `briefs/3C-01`…`3C-13`, Units table and refine notes in `DESIGN.md` (Phase 3C). Settled at refine and binding on the briefs: cell range = today's `_plan_chunks` row span (ARCHITECTURE's "by cell count" wording corrected at close); E1 row layout (32 B) and E1's additive overlap counters (an addition to Contract B's E1 output); E2 frame-index row (36 B) written against a caller-provided spill fd; heavy-job lock (`flock output/.heavy.lock`) serialising every full build and `-j 12` run so units may run alongside; Contract W markers `STEP … OK|FAIL`, `ALLDONE`, `ABORT`.
Refine's flagged items, carried for the user: (1) E3 is two call sites while division is Python — `kw_measure_cell` and the per-shape `kw_bg_shape` behind `bg_shape_records` — where Contract B names only the measure call; both die in 3C-09. The orchestrator proceeds on it as transitional (Contract B itself says E3 exists "as today's divide does") and flags it for sign-off. (2) E1 returns the additive overlap counters (not in Contract B's E1 output; E2 cannot compute them additively). (3) Deletions of the no-C `_encode_level` path and `KIWIW_NO_C` move to 3C-08 because that path imports `overlap.py`. (4) Contract W's `DONE` is realised as `ALLDONE`/`ABORT`. (5) 3C-09 carries a committed stop point (C divides parents needing no trim/halo, declines the rest).
Agent: 71 tool uses, ~126k tokens, 23 min.
