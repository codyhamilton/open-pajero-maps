# Implementation — 04-c-core-orchestration

- Tool: Claude Code, orchestrator Sonnet 5.5
- Session: https://claude.ai/code/session_01KFbprktJzdCyubbCXezU5h
- Started: 2026-10-01T10:18Z
- Scope: Phase 1 (closed) then Phase 2 only. Workers Sonnet by default; Opus only as the one-tier retry after a Sonnet failure (user instruction). Phase 1 skipped refine (one unit); brief authored inline.

## Phase 1

### 1-01 policy-lock — dispatched (brief `briefs/1-01-policy-lock.md`)
Replaces "dispatched" above. Done with concerns (ccd2068, Sonnet 5.5).
**Built:** `docs/ARCHITECTURE.md` (rule section; libkiwiw boundary with D1/K1/census kernels/H5–H6 marked planned with phase numbers; module-map note that Phase 5 makes it true); a pointer block in plan 03 `DESIGN.md` (no contract text edited); `parser/perf_inventory.json` (92 modules + one `parser/tests/**` glob: orchestration 30, c-now 20 [1 phase 2, 19 phase 4], c-later 16, retired 26 [all phase 5]); `parser/tests/test_perf_inventory.py` (4 tests). The commit touches only the four owned paths.
**Evidence (worker's, then orchestrator re-ran):** test failed before the inventory (4 failed), passes after (4 passed); probe module `_probe.py` made it fail naming the path, removed → pass. Orchestrator re-ran the whole suite: 478 passed in 175 s (474 before + 4 new), diff of `ccd2068` is four paths, no `.py`/`.c` source changed so build sha, Perth and goldens are unchanged by construction (goldens test is in the passing suite).
**Deviations:** the test glob entry narrows "every module" to non-test modules by brief decision. `python` is not on PATH; `.venv-rp/bin/python` was used.
**Contradictions reported:** (1) `alldata_writer.py` is both build orchestration and the R-replicate load path; classified `retired` phase 5, which sits against Phase 5's "every remaining module is orchestration". (2) `retired` requires a phase in 2–5, so `spool_legacy.py` and `convert_spool.py` were put in `c-later` with a noted doubt.
**Low-confidence classes (worker):** retired: `roundtrip_idx*`, `roundtrip_misc`, `roundtrip_alldata_header` (no parcel decoder, listed by the brief's `roundtrip_*`), `dump_parcel`, `analyze_*`, `estimate_*`, `study_region_hierarchy`, `survey_road_reference_table` (they import `AllData`, which may survive); c-now: `harness/checks/{envelope,vocab}.py`, `harness/profile.py` (may be bounded by profile aggregates); c-later: route-planning, IDX modules, `link_id_registry`.
An unrelated commit `f4d0f2c` (docs WORKFLOW pointer, by the user) landed on master during the unit; not part of this phase.

### Phase 1 verification — closed
Outcome checked directly: ARCHITECTURE states the rule and D1/K1/H5–H6 (greps at lines 88–89); plan 03 DESIGN carries the pointer; inventory exists and the test fails for a missing module (probe) and passes now; every c-now/retired entry has a phase (test enforces); no source change, so sha 87a01b14…, Perth da13a775… and goldens hold (full suite 478 passed; I did not re-run the full-AU or Perth builds, as nothing they depend on changed).

**Carried** (ordered):
1. `alldata_writer.py` class: Phase 5 must split the build part from the retired R-replicate load path before the inventory can say orchestration; reclassify then. (Bears on Phase 5's wording.)
2. Re-check the low-confidence classes at the phase that moves them (Phase 2 for `quantisation_roundtrip`, Phase 4 for the harness checks/profile, Phase 5 for the retired scripts that import `AllData`); the inventory test only checks completeness, not correctness.
3. `spool_legacy.py`, `convert_spool.py` sit in `c-later` because no phase names them; decide at Phase 5 refine.
4. Tests are covered by one glob entry, not per module.

## Phase 2

Run header: Claude Code, orchestrator Sonnet 5.5, same session as above; Phase 2 execute started 2026-10-01 after refine (`d455dd2`, units 2-01..2-08, serial). Workers Sonnet; Opus only as one-tier retry after a Sonnet failure.

**Orchestrator decision (ledgered, refine asked for confirmation):** the parcel-tree walker is in C (2-02), per the standing intent "C for all perf-sensitive work" and the one-call-per-range rule. Refine's reading of "per-check D1 wall" (D1 full-disc decode wall plus Python per-check baselines) and the first-N=10 merged sample rule stand. Real-disc skips report `blocked`, not pass. Cody signs the Phase 4 budgets and the re-signed PSS ceiling from 2-08's numbers.

### 2-01 d1-frame-decoders — done with concerns (`621e624`, Sonnet 5.5; ~53 tool uses)
**Built:** `kw_d1_frames` (one call per leaf-frame range) filling 13 columnar tables (frame, mfde, dclass, addl, link, node, point, bgelem, bgunit, bgshape, bgcoord, nlist, nrec); raw fields as (offset,length) pairs; failing frames get `frame.status != 0`; grow-and-retry buffers; C-side stats. Surfaces: `parser/kiwiw/_d1.c`, `_d1.h` (layout declared once), `cbuild.py` (one `EXT_SOURCES` entry), `cenc.py` D1 section with load-time descriptor check, `parser/tests/test_d1_frames.py`.
**Evidence:** 11 tests fail before (AttributeError), pass after (129 s); mutation of node `oneway` and of the descriptor type each caught; 41 passed across goldens/cenc/e1/e2/inventory.
**Deviations/concerns:** ~1,050 lines changed (guide ~1,000); type-label strings rebuilt in `cenc.py` and the `UNHANDLED string_type` text is duplicated from `name.py` (drift risk until Phase 5 retires the Python decoder); default buffer capacity is virtual memory only. No brief contradictions.

### 2-02 d1-walker-equivalence — done with concerns (`1300a2b`, Sonnet 5.5; ~55 tool uses)
**Built:** `kw_d1_blocks` (`_d1.c`/`_d1.h`): one C call walks a block or row band, bit-exact bounds, divided-parent and L0 sparse-tile rules, checker `iy`/`ix` row filter, columnar output with grow-and-repeat, unparsable block becomes a marker row. `cenc.py` D1 section: `d1_blocks`, `d1_block_rows`, `D1_BLOCK_DTYPE`, shared grow loop, `retries` stat. `parser/tests/test_d1_equivalence.py`, `parser/tests/fixtures/d1_sample.json` (~6 KB, seed 20260930), `docs/provenance.md` entry.
**Evidence:** equivalence + 2-01 frame tests 17 passed (164 s), G and R cases run not skipped; goldens + inventory 13 passed; walker test fails with `parser/kiwiw` stashed to HEAD; whole-block leaves compared per level (G/R, L0 4096/4096 … L12 1/1) against the checker walk for count, order and every field; sample covers road, background and name in both discs; band calls counted (21 per disc); tile-height mutation caught.
**Deviations/concerns:** G has no `l0_sparse_tile` leaves (only R exercises that class); raw C calls exceed bands because buffer-growth retries occur (G 5, R 8), test asserts `calls - retries == planned`; one mutation (sparse-tile all-equal column) is an equivalent mutant on the discs; marker rows covered by synthetic bytes only; goldens hold frames only (2-01 covers them); unused leftovers in `_d1.c` (`BAND_NONE`, `walkr.rc`, a no-op store). No brief contradictions.

### 2-03 k1-point-kinds — done with concerns (`b762aca`, Sonnet 5.5; ~82 tool uses)
**Built:** `kw_k1_band` (`_k1.c`/`_k1.h`): decodes through D1 in C and checks `range` (incl. background vertices), `step`, `road_node`, `road_point`, `name_anchor` against the spool; five explained counters, exact counts, first-10 deterministic samples, C-side stats. `_k1_bg.c`/`_k1_cmp.c` are stubs for 2-04/2-05. `cbuild.py` `EXT_SOURCES` entries, `cenc.py` K1 section, `parser/tests/k1_fixtures.py`, `test_k1_points.py`.
**Evidence:** fails before (`K1Acc` missing), 57 passed in 63.6 s with R and G present; K1 counts, samples and worst error equal the Python tool on seven fixtures (clean, vertex_moved, piece_removed, name_node_moved, many_failures, dense, dense_moved); tolerance mutation 0.5→3.0 caught and reverted.
**Deviations/concerns:** D1 quirk — `link_first`/`nrec_first`/`bgshape_first` are set only when the section exists, so K1 guards loops on `has_road`/`has_name`/`has_bg` (D1 backlog); fixture `name_node_moved` changed to a 1-raw move so the mutation is detectable; explained counters `road_node_on_leaf_edge`, `road_point_*`, `name_anchor_halo` are 0 on every fixture (only `road_node_subcell_on_polyline` exercised), so they are proven only on the full disc in 2-08; `cbuild`'s content hash covers `.c` only, so a header-only edit does not rebuild (hazard, carried). No brief contradictions.

### 2-04 k1-background-kinds — done (`8c84efb`, Sonnet 5.5; ~79 tool uses)
**Built:** `k1_bg_kinds` in `_k1_bg.c` (~420 lines): typed vertex/segment outline distance, batched exact point-in-polygon, kinds `background`, `background_boundary`, `interior_cover` with first-10 samples. Plumbing in `_k1.h`, `_k1.c` (`kw_k1_band` gained 5 trailing args, `k1_ctx.shapes`), `cenc.py` K1 section (per-spool tall-set cache), `parser/tests/test_k1_background.py`, extended `k1_fixtures.py` (separate `BG_FIXTURES`, 15 fixtures).
**Evidence:** stub fails before; 103 passed after (61 in the new file); K1 equals the Python tool on all 15 fixtures (counts, samples, worst to 6 dp) and on the real G disc at levels 12, 10, 8, 6 (L6: background 366,528/0, boundary 4,921/4,004, interior_cover 1/1; K1 0.5 s vs Python 3.5 s); mutations of the near tolerance (0.5→0.65) and edge rule (`<`→`<=`) caught and reverted.
**Deviations/concerns:** Python's float-key `inside()` replaced by the exact comparison it approximates (ties within ~1e-8 could differ); keys assume shape types < 2048; dropping `+TOL` in the inside interval comparison is NOT caught by any fixture (inside-side tolerance uncovered; full-disc count equality in 2-08 is the backstop). **Contradiction:** brief's owned paths omitted `_k1.c`, which the kinds need; edited it, recorded as a dated Amendment in the brief.
