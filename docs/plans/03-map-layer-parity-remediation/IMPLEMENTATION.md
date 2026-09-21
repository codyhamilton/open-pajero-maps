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
