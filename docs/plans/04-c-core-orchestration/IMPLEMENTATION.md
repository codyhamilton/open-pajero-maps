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

### 2-05 k1-completeness — done (`363283c`, Sonnet 5.5; ~22 tool uses)
**Built:** K1 `completeness` in `_k1_cmp.c` with the arithmetic of the Python `_required_cells`/`present` (rules a, b, c; cells from decoded leaves plus spool cells in the block rectangle, rows clipped to the band); samples `(iy, ix, type)` order, reason 7. `parser/tests/test_k1_completeness.py` (verdict and sample equality, non-vacuousness, band-split/merge byte-identity, one-call-per-band counter, `test_k1_all_kinds_match_python`) and five new fixtures (`cmp_*`).
**Surfaces beyond owned list (additive, Amendment in brief):** `_k1.c` (region records spool cells; band passes c0,c1,r0,r1; releases shape index), `_k1_bg.c` (shape index built once per band, shared via `k1_ctx.bgx`, `k1_bg_inside` wrapper), `cenc.py` (reason-7 label).
**Evidence:** stub run 41 failed / 79 passed with the new tests in place; after: completeness, background, points, inventory and goldens 223 passed; K1 equals Python on all 9 kinds and every explained counter on 20 fixtures; mutations of rule (a) area test (15 fail) and rule (c) (28 fail) caught and reverted. No G/R run and no full-AU timing (fixtures only, per brief).
**Deviations:** owned list omitted `_k1.c`, `_k1_bg.c`. No contradictions with the cited contracts.

### 2-06 thin-driver — done with concerns (`12a893c`, Sonnet 5.5; ~36 tool uses)
**Built:** `parser/tools/quantisation_roundtrip.py` defaults to `--engine c` (one `cenc.k1_check_band` call per range, `K1Acc.merge`, same report schema plus `timing` section and `compare_excludes`); `PssSampler` sums `Pss:` from `/proc/<pid>/smaps_rollup` for driver and pool children every 0.25 s (started after the pool forks); `--engine python` kept as the count oracle; `--levels`, `-j` alias. `parser/perf_inventory.json`: driver reclassified `orchestration`, 27 oracle-only functions listed for Phase 5 deletion (Carried item 2 placed). `cenc.py` untouched.
**Evidence:** seven-file pytest 323 passed (C vs Python on 22 fixtures, `-j 1` == `-j 4` bytes, call counter, PSS peak); Python path at HEAD vs now identical on fixtures at `-j 1`/`-j 3` once `engine` and `wall_s` dropped. Real disc G + spool, levels 8 and 6 at `-j 12`, Python vs C: all nine kinds' checked/failing, worst error and explained counters equal (L8 3.2 s py / 3.0 s C, 115 MiB PSS; L6 3.4 s / 3.1 s, 101 MiB); canonical bytes identical across `-j 1`, `-j 4`, `-j 12`. Levels 12 and 10 have no road data.
**Deviations (dated Amendment in brief):** Python path adds an `"engine"` key; `roundtrip()` keeps `engine="python"` library default (unowned tests use it as the oracle), CLI default is `c`; when more than N items fail, Python and K1 keep different N-sized samples (K1 follows the contract's `(iy, ix, …)` order; counts, worst and explained equal; samples identical when failing ≤ N); the band plan uses fixed 12 workers so `-j` cannot change bytes, so engines compare at `-j 12`.
**Finding for Phase 3 (not fixed):** G level 6 fails identically in both engines: 4,004 `background_boundary`, 1 `interior_cover`.

### 2-07 full-disc-kickoff — done, ALLDONE (no repo changes; Sonnet 5.5; ~22 tool uses)
**Ran:** `output/scratch-2-07/run.sh` once under `output/.heavy.lock` (start 23:09:22, lock immediate); `status.txt` ends `ALLDONE`, every step OK. Outputs (uncommitted, in `output/scratch-2-07/`): `k1_{a,b,c,j1}.json/.log`, `determinism.txt`, `d1_decode.json`, `py_checks.tsv` + `py_<check>.json/.log`, `gates.txt`, `goldens.log`, `hbudget.log`. Counts were NOT judged against the 3C-04 table; 2-08 does that.
**K1 at `-j 12` on G:** wall 71.2 / 68.4 / 66.0 s (median 68.4); summed-PSS peak 8.74 / 8.98 / 9.73 GB; `-j 1` 426 s, 6.65 GB. All reports `pass` false (known failures remain). Determinism: a vs j1, a vs b, a vs c IDENTICAL excluding `timing`/`wall_s`.
**D1 decode:** 4.79 s at `-j 12` (7.96 s with planning); 2,165 ranges, 3,954,156 frames, 460,018,916 rows, 0 failed; 150 buffer retries.
**Python per-check wall (`--workers 12`):** decode 464.3, container 1.3, envelope 618.7, mfde 636.5, shape 1.3, vocab 612.7, spotcheck 1.7, coord_scale 112.9 s. rc 1 rows are reference-vs-itself FAILs, recorded not triaged; `container`/`shape` ~1.3 s look like early exits (2-08 to confirm).
**Gates:** full-AU sha `87a01b14…2797862` matches; Perth `-j 1` == `-j 4` == `da13a775…` matches; goldens 9 passed; H budget 3 passed.
**Deviations:** H-budget tests chosen by worker (`test_build_alldata.py::test_budgets_and_thresholds_are_u16_ceiling_everywhere`, `test_bench_record.py`); `run.sh` deletes the rebuilt full-AU `ALLDATA.KWI` after recording its sha; K1 driver exits 1 on a failing report so rc 0|1 with a report counts OK; ranges planned via the driver's `_block_tasks`. **Contradictions:** brief pointed at 1-01 for gate commands (taken from 3C-01); "one Monitor" cannot cover a multi-hour run (30-minute cap), so a single until-loop on `status.txt` was used.

### Phase 2 verification — closed
Source: `output/scratch-2-07/` read only (no K1, `compare_disc`, or build re-run). Judged against DESIGN.md Phase 2, Gates and Assumption 2. Closed after Cody signatures (below).

**K1 counts vs 3C-04** (`k1_a/b/c.json` `totals`; identical across the three runs and `k1_j1.json`). All cells exact, no deviations:

| kind | K1 checked | K1 failing | 3C-04 checked | 3C-04 failing | verdict |
|---|---|---|---|---|---|
| range | 309,192,246 | 0 | 309,192,246 | 0 | equal |
| step | 252,444,802 | 0 | 252,444,802 | 0 | equal |
| road_node | 42,995,770 | 0 | 42,995,770 | 0 | equal |
| name_anchor | 2,317,983 | 1 | 2,317,983 | 1 | equal |
| background | 174,332,105 | 1,438,558 | 174,332,105 | 1,438,558 | equal |
| background_boundary | 89,546,388 | 16,549,569 | 89,546,388 | 16,549,569 | equal |
| completeness | 1,800,514 | 752 | 1,800,514 | 752 | equal |
| interior_cover | 1,592,016 | 824 | 1,592,016 | 824 | equal |

Explained counters equal: `name_anchor_halo` 311,347 (L0 only); `road_node_subcell_on_polyline` 551,530 = 547,622 (L0) + 840 (L2) + 2,882 (L4) + 175 (L6) + 11 (L8), summed across levels from `k1_*.json`. `road_point` is a K1 kind absent from the 3C-04 table (0/0); no other differences. Report `pass` false on all runs (the old failures are reproduced, not fixed).

**Wall vs 120 s bar** (`timing.wall_s`, `-j 12`): 71.183 / 68.408 / 66.006 s; **median 68.408 s ≤ 120 s → met** (the 120 s is on the 3-11 disc against its spool).
**Peak PSS** (`timing.pss_peak_kb`): 8,736,916 / 8,982,284 / 9,726,501 kB; **peak 9,726,501 kB ≈ 9.28 GiB (9.73 GB decimal)** vs the provisional 22 GB ceiling → **met** (well under). DESIGN names no margin ("re-signed at the Phase 2 close from the measured peak"; Assumption 2). Proposed re-signed ceiling: the measured peak **9,726,501 kB**, for **Cody to sign** — no margin invented.

**Determinism** (`determinism.txt`): `k1_a` vs `k1_j1`, vs `k1_b`, vs `k1_c` all `IDENTICAL (timing and wall_s excluded)`, rc=0 → **met** (the `-j 1` run took 426.189 s; `-j 12` 71.183).

**D1 equivalence:** met, per 2-02 (`1300a2b`): frame+equivalence 17 passed on G and R (not skipped); goldens+inventory 13 passed; `parser/tests/fixtures/d1_sample.json` (seed 20260930) forces road-link, background-polygon and name-record coverage in both discs and compares whole blocks field-for-field. Full-disc D1 decode of G (`d1_decode.json`): `decode_wall_s` **4.787 s**, 7.962 s with planning; 2,165 ranges, 2,315 C calls, 150 retries, 3,954,156 frames, 460,018,916 rows, 0 failed.

**Per-check wall for the Phase 4 budgets** (`py_checks.tsv`, Python baseline, `--workers 12`; D1 full-disc decode wall from `d1_decode.json`):
| check | Python wall_s | rc | note |
|---|---|---|---|
| decode | 464.3 | 0 | PASS (3,954,156 leaves, 0 errors) |
| container | 1.3 | 1 | FAIL 6 unallowlisted byte differences |
| envelope | 618.7 | 1 | FAIL 2 envelope failures |
| mfde | 636.5 | 1 | FAIL 0 subset failures, 50 coverage failures |
| shape | 1.3 | 1 | FAIL 19 shape differences |
| vocab | 612.7 | 1 | FAIL coverage below 0.95 at 5 levels |
| spotcheck | 1.7 | 0 | PASS (15 checks) |
| coord_scale | 112.9 | 0 | PASS |
| **D1 full-disc decode** | **4.787** | 0 | new C path |

Provisional Phase 4 budgets to sign: `coord_scale` ≤ 20 s; each other harness check ≤ 60 s (Assumption 2). `container`/`shape` return genuine FAILs (6 byte diffs; 19 shape diffs) in ~1.3 s; whether they scan the whole disc or exit early at the first failures is unconfirmed (logs do not say), so their 1.3 s is a lower bound for budgeting, not a proven full-scan cost. All rc=1 rows ran with reference = generated = G (`py_checks.tsv` note), are pre-existing, and are not triaged here.

**Gates** (`gates.txt` verbatim):
```
fullAU rc=0 wall=18s sha256=87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862
expect fullAU 87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862
perth_j1 rc=0 wall=3s sha256=da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc
perth_j4 rc=0 wall=1s sha256=da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc
expect perth da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc
goldens pytest rc=0: 9 passed in 2.89s
hbudget pytest rc=0: 3 passed in 3.82s
```
Verdict: sha `87a01b14…2797862` matches; Perth `-j 1` == `-j 4` == `da13a775…`; goldens pass; H budget passes → build gates unchanged, **met**.

**Outcome clause verdicts:** ≤120 s median of three — met (68.408 s). Peak PSS recorded and under ceiling — met (9,726,501 kB < 22 GB). Exact `checked`/`failing` and bounded failing samples for every 3C-04 kind — met. K1 counts equal 3C-04 exactly (8 kinds) — met. Explained categories (311,347 / 551,530) equal — met. Reproduces old answers, does not fix — met. D1 gates K1 (D1 equivalence first) — met. D1 field equality on goldens and the R/G sample, and G/R decode — met (per 2-02). Per-check D1 wall for Phase 4 budgets — met (above). Build gates (sha, Perth, goldens, H) unchanged — met.

**Carried for Phase 3:**
1. Triage inputs: `output/scratch-2-07/k1_a.json` (identical to `k1_b/c/j1` modulo `timing`/`wall_s`); each level's `failures[]` holds the first-N bounded samples per kind. Failing kinds and counts: `background` 1,438,558; `background_boundary` 16,549,569; `interior_cover` 824; `completeness` 752; `name_anchor` 1.
2. `name_anchor` single failure is L0 cell (0,541), leaf 928 (`reason: no spool record within half a raw unit`) — the known spool/extractor item.
3. The rc=1 harness checks (`container`, `envelope`, `mfde`, `shape`, `vocab`) are pre-existing Python reference-comparison FAILs, recorded not triaged; Phase 4 must baseline them before changing them.
4. `output/scratch-2-07/` is uncommitted; a provenance entry was added in this commit. Phase 3 depends on it — do not delete.
5. H-budget tests were chosen by 2-07 by name (`test_budgets_and_thresholds_are_u16_ceiling_everywhere`, `test_bench_record.py`); not re-run in 2-08.

**Signed (Cody via Bot Team Manager, 2026-10-02):** re-signed PSS ceiling = measured peak **9,726,501 kB** (no margin). Phase 4 budgets: `coord_scale` ≤ **20 s**; each other harness check ≤ **60 s**. Phase 2 close authorized.

**Review (Sonnet 5.5, draft → reviewed):** every figure re-read from `output/scratch-2-07/` and matched: the eight K1 `totals` (checked/failing) equal the 3C-04 table to the integer in `k1_a`, `k1_b`, `k1_c` and `k1_j1`; total failing 17,989,704 = 1,438,558 + 16,549,569 + 824 + 752 + 1; explained `name_anchor_halo` 311,347 and `road_node_subcell_on_polyline` 551,530 (547,622 + 840 + 2,882 + 175 + 11) in all four reports, other explained counters 0; walls 71.183 / 68.408 / 66.006 s (median 68.408), `-j 1` 426.189 s; PSS peaks 8,736,916 / 8,982,284 / 9,726,501 kB (9.276 GiB), `-j 1` 6,646,774 kB; determinism three IDENTICAL lines; D1 decode 4.787 s / 7.962 s, 2,165 ranges, 2,315 calls, 150 retries, 3,954,156 frames, 460,018,916 rows, 0 failed; gates verbatim; `py_checks.tsv` walls. Fixes: removed the unsupported "not an early exit" claim for `container`/`shape`; filled the failure messages for `envelope`, `mfde`, `vocab`. DESIGN names no PSS margin (lines 49, 91: re-signed from the measured peak); none was invented. At review time Phase 2 was still open for Cody's PSS/budget signatures; those are now recorded above and closed in this commit with the Workflow-Phase trailer.


### Phase 2 close — Grok (Build Orchestrator)
Outcome verified against DESIGN Phase 2 and the Sonnet-reviewed 2-08 record (`6a00f2e`): K1 median wall 68.408 s ≤ 120 s; PSS peak 9,726,501 kB under the signed ceiling (equals the ceiling); all eight 3C-04 kinds and explained counters exact; determinism and build gates met; D1 equivalence per 2-02; Phase 4 budget table recorded. Flash draft `c1b0424` → Sonnet review `6a00f2e` → Cody signatures → this trailer.

**Carried** (into Phase 3; ordered):
1. Triage inputs in `output/scratch-2-07/` (esp. `k1_a.json` failures[] samples): background 1,438,558; background_boundary 16,549,569; interior_cover 824; completeness 752; name_anchor 1.
2. `name_anchor` L0 (0,541) leaf 928 is the known spool/extractor item (Assumption 4 carry).
3. Harness rc=1 rows (`container`, `envelope`, `mfde`, `shape`, `vocab`) pre-existing; Phase 4 baselines before change.
4. Do not delete `output/scratch-2-07/` (provenance entry stands).
5. Signed PSS ceiling 9,726,501 kB and Phase 4 budgets (20 s / 60 s) apply from here.

## Phase 3

Run header: Claude Code, orchestrator Sonnet 5.5, same session as above; Phase 3 execute started 2026-10-02 after refine (`ac758cd`, briefs 3-01..3-08, 3-fix-template, 3-90). Credit-burn standing (Cody via parent): execution units run on OpenCode Flash (`deepseek/deepseek-flash`); every Flash unit gets a mandatory Sonnet 5.5 review before it is committed/pushed and recorded as done; Sol/Claude only at the 3-07/3-08 cause-table decision moments (checker vs build vs spool). The phase is not auto-closed after Flash. Bounce to parent/BTM if 3-07/3-08 report `blocked: unattributed` or spool groups exceed 10,000. `output/scratch-2-07/` stays untouched; heavy runs under `flock output/.heavy.lock`. Flash units leave changes uncommitted; the orchestrator commits after review.

### 3-01 cbuild header hash (Flash → Sonnet 5.5 review)
Built: `parser/kiwiw/cbuild.py` — `_ext_headers()` (sorted `parser/kiwiw/*.h`, evaluated per call) and a `headers=None` parameter on `build_ext` / `build_test_bin`; headers are hashed with sources and flags but never passed to gcc. New `parser/tests/test_cbuild_headers.py` (3 tests: ext rebuild on header edit, test-bin rebuild on header edit, real tree includes `_k1.h`/`_d1.h`). Flash evidence: pre-change 3 failed / 42 passed; post-change 45 passed (`output/scratch-3-01/{pre,post}.log`). Review: diff read against the brief; the new tests plus the C unit tests re-run under the heavy lock, 4 passed. Deviation: the brief contradicts itself (constant vs function); Flash chose the function — accepted, the function picks up new headers without a list edit. The rebuilt product is unchanged for current sources, so no sha impact.

### 3-06 forensics dossier (Flash → Sonnet 5.5 review)
Built: `output/scratch-3-06/dossier.md` (git-ignored; scripts `common.py`, `build_tall.py`, `d1_d3.py`, `d456.py`, `d7.py`, `d8.py` beside it). D1–D8 answered, no classification (reserved for 3-07/3-08). Key facts: "polygon 65623" is shape index 65623 of one block's Region (type 288, class 2, 1810 vertices, tall origin, home cell (1689,508)), the first tall shape in that Region, so it is order-dependent, not a global id; its longest edge (1,908,357 raw, i=1808→1809) ends on the first/last vertex; whether the source OSM ring was already closed is unestablished (the spool stores no id or closed flag). The `name_anchor` item: the disc name is at lon 90.0, the only spool name in cell (0,541) is at lon 77.519 (~1.64M raw away). All 10 sampled completeness cells have 0 pieces of the required type on disc. Review: spot-checked the identity line, D7 and process notes. Deviation: the brief forbids spawning agents; the worker spawned general subagents as hands and said so in the dossier. Accepted for this read-only unit; no repo writes beyond `output/scratch-3-06/`.

### 3-02 K1 failure dump (Flash ×2 → Sonnet 5.5 review)
Built: opt-in `--dump-failures DIR` / `--dump-kinds` on `quantisation_roundtrip.py`; `K1_F_DUMP` X-macro in `_k1.h` (sample fields + `kind`, `level`, `shape`, `vert`; 80-byte rows) mirrored by a checked descriptor in `cenc.py`; per-failing-item emit sites in `_k1.c` (name_anchor), `_k1_bg.c` (background, background_boundary, interior_cover) and `_k1_cmp.c` (completeness); grow-and-retry via `kw_k1_band` return 1; `parser/tests/test_k1_dump.py`; provenance entry for `output/scratch-3-02/dump/`.
Evidence: full-disc dump rows 1,438,558 / 16,549,569 / 824 / 752 / 1 equal the 3C-04 table; report totals equal `k1_a.json`; level 6 `-j 1` vs `-j 12` byte-equal; mutation (skip boundary emit) fails 2 fixture tests; my re-run of dump + points/background/completeness/goldens: 245 passed.
Deviations / amendments (brief amended): (1) four new fields, not three; (2) the driver sorts each kind canonically instead of task-order concatenation, and the struct padding is zeroed, so bytes are independent of `-j` and band split; (3) run 1 kept `shape`/`vert` side arrays in `qs_t` unconditionally, adding per-item work with the dump off (wall 84–91 s); review caught it; run 2 made them dump-only. A/B dump-off full-disc `-j 12` under the heavy lock, loaded machine (load 14–18): HEAD 73.910 / 73.945 s, fixed tree 72.985 / 73.252 / 73.247 s; summed C time indistinguishable. The 72 s done-evidence figure was a quiet-machine reference (k1_a 66–71 s); the contract bar is 120 s, met. Dump-on wall 115.7 s. `cmp_j.py` reports DIFFERENT only because it does not strip the new `dump` key.
