# Implementation — 03-map-layer-parity-remediation

- Tool: Claude Code (Agent SDK), model Sonnet 5
- Session: https://claude.ai/code/session_01RexnjYaodJxiRvFV9nsAaE
- Started: 2026-09-21T19:17:25+10:00
- Scope: Phase 1 only

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
2. Strict `pointers` FAILs R itself on ~2% (65/4000) of out-of-buffer idx>=3 targets; needs allowance or premise correction before it can be used as R-parity.
3. Envelope L10/L12 frame-size FAILs: cause inferred (F3/F5); Phase 4 envelope rewrite (2x-R advisory) must confirm.
4. L0 road-length census uses an unverified 16384 range heuristic; Phase 2 must validate and re-derive density.json if changed.
5. Extraction timing 26:03 is an upper bound (concurrent load); re-time cleanly before Phase 8 planning if it matters.
6. Grenfell spot row passes on G (design predicted FAIL); coordinates were derived from R.
7. Git stash@{0} holds stale sibling WIP from concurrent workers; drop after confirming nothing is lost.
