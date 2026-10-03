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

### 3-03 Diagnostic columns on dump rows (Flash → Sonnet 5.5 review)
Built: 15 diagnostic columns appended to `K1_F_DUMP` (row 80 → 144 B): nearest any-type and same-type outline distance and source identity (home cell, record ordinal, tall flag), source max segment, even-odd and winding inside flags for any and same type, on-boundary mask; search radii `K1_DIAG_SAME` 64, `K1_DIAG_ANY` 2 cells. Lazy edge-bucket index and per-shape max-edge cache in `_k1_bg.c`; home cell and record carried in the shape builder and tall pass. 9 new tests (35 in `test_k1_dump.py`) including a pentagram self-overlap fixture.
Evidence: my re-run of dump/points/background/completeness/goldens/perf_inventory: 258 passed. Flash: full-disc dump (wall 221.8 s, PSS 7944 MiB) with exact row counts and totals equal `k1_a.json`; first 5 rows per level and kind equal the 3-02 dump on all 21 shared columns; level 6 `-j 1` vs `-j 12` byte-equal; dump-off A/B vs `8d96e3a` in the same window: HEAD 67.4 s, tree 62.8 s, reports identical to `k1_a.json` outside timing.
First-look facts (for 3-05/3-07, not a classification): `in_wn_same ≠ in_eo_same` is 0 on the real disc (simple rings); of background L0 failures 1,244,617 of 1,431,789 are inside an any-type polygon by even-odd; no `d_any` within 2 cells for most rows.
Deviations: brief amended (4 items, see brief): `src_*` sentinel only beyond 64 raw; `src_maxseg` fixtures; pentagram for bowtie; lattice search point. Size ~505 changed lines vs ~350 estimate. Caution for 3-07: these diagnostics are new geometry in C; the cause-table decision should spot-check a sample of rows against the 3-06 dossier (D4/D6/D8 hand measurements) before leaning on them.

### 3-04 Inside-side tolerance fixtures (Flash → Sonnet 5.5 review)
Built (tests only, append): `bg_inside_out_03` / `bg_inside_out_07` fixtures, `INSIDE_FIXTURES`, `build_inside_fixture` in `k1_fixtures.py`; `test_inside_out_verdicts_equal_the_python_tool` and `test_inside_out_exact_counts` in `test_k1_background.py`. `_k1_bg.c` byte-identical to HEAD.
Evidence: removing `+ K1_TOL` (`_k1_bg.c:309`) or `- K1_TOL` (`:310`) each fails `test_inside_out_verdicts_equal_the_python_tool[bg_inside_out_03]` (K1 `interior_cover (2,1)` vs Python `(2,0)`); the 61 pre-existing background tests passed under both mutations (the gap this unit closes). Restored with `git checkout`; my re-run of background/points/completeness/dump tests passed.
Finding for 3-07: `background_boundary` cannot observe the inside tolerance. A boundary vertex reaches `inside_batch` only when `d > NEAR = K1_TOL + K1_EPS`, so within-tolerance cases pass the near gate first and both `K1_TOL` terms are equivalent mutants there. The tolerance is observable only through `interior_cover` centres. Any tolerance change meant to move `background_boundary` counts must therefore be made on the near gate (`NEAR`/`SEARCH`), not the inside intervals.
Deviations: brief's mutation line numbers 301/302 are actually 309/310; the brief's premise (frame-boundary disc vertex observes the tolerance) is not constructible and the brief's `interior_cover` fallback was used; fixtures kept out of `BG_FIXTURES` (vacuity check); `07` pins 35 boundary failures (frame vertices shared into edge cells) plus 1 cover.

### 3-05 Triage tool (Flash → Sonnet 5.5 review)
Built: `parser/tools/k1_triage.py` (`summary`, `classify`, `enumerate`; numpy memmap in 2,000,000-row chunks over the dump manifest, no C library), `parser/tests/test_k1_triage.py` (synthetic 3,000-row dump), one `orchestration` entry in `parser/perf_inventory.json`, provenance entry for `output/scratch-3-05/`.
Evidence: my re-run of triage + perf_inventory tests passed (12). Flash on the real 3-03 dump: `summary` totals equal 1,438,558 / 16,549,569 / 824 / 752 / 1, peak RSS 3.38 GB (≤ 4 GB), wall 139 s; a one-catch-all-per-kind `classify` gives `PARTITION OK` with 0 unclassified, 40 s; `enumerate` for the name_anchor catch-all returns the single L0 cell (0,541) leaf 928. A dropped rule exits 1 and lists exactly its groups; unknown column or cause exits 2; first-rule-wins; two runs byte-identical.
Deviations: `classify` also writes `OUT/rules.json` (needed by `enumerate`); NaN sentinels canonicalised for grouping and key arrays zero-initialised (a `np.empty` padding bug made group counts vary run to run, now locked by a test); `by_src.tsv` cap 5,000 rows + a `# cut` line; `--kinds` not implemented.
Contradictions to carry into 3-07/3-08: `unclassified_groups.tsv` has no `kind` column although groups are per kind (rows from different kinds can look identical); `type` is read as the dump `code` column and first/last vert as min/max `vert`.

### 3-07 Cause table, background family (Sol, attempt 1: over budget, blocked: unattributed)
No rows attributed; no rules, witnesses, counterfactuals or classify run. Sol stopped at the brief's literal 12-file read budget (~63k tokens used) and left a handoff at `output/scratch-3-07/handoff.md` (placeholder `rules_bg.json`/`causes_bg.md` moved to `output/scratch-3-07/draft_triage/`, not committed). Treated as a budget stop, not a finding: the budget was sized for Flash.
Facts recovered (verified by a fresh locked `summary` run, tables byte-identical to 3-05; Sonnet 5.5 read the handoff tables, not yet independently re-derived): 17,988,127 background-family rows; top-30 (type, level, source) combinations cover only 88.51 %, but that is because 17.0 M rows (94.5 %) have a SENTINEL source (no same-type outline within `K1_DIAG_SAME` = 64 raw): type 291 L0 11,562,264; type 288 L0 3,425,163; 289 L0 418,187; 578 L0 390,509; 289 L2 113,723; 288 L6 3,725. `background_boundary` rows have `in_eo_same` = 0 everywhere while `in_eo_any` = 1 for 8.99 M of the 12.45 M type-291 L0 rows; `background` rows have `in_eo_same` = 1 on 920,773 rows. 31,416 boundary rows carry `onb` = 0 (diagnostic or boundary-interpretation question, untested). Hypotheses H1–H7: all untested (0 rows).
Deviations: brief's witness criterion ("inside OR within 0.5 of an outline") conflicts with the cited non-boundary outline requirement for `background`; the dossier's outside-by-both results do not establish H4's parity/winding contradiction; budget handoff placed in scratch since `IMPLEMENTATION.md` is not an owned path of the unit.
Bounce: parent/BTM, per `blocked: unattributed`. Recommended: re-dispatch Sol on 3-07 with the read/turn budget lifted (amend the brief), the witness criterion fixed, and the rule schema (3-05) inlined.

### 3-07 attempts 2 and 3 (Sol; Sonnet 5.5 review ACCEPT both, `triage/review_3-07.md`)
Attempt 2 (brief amended: budget lifted, witness criterion fixed, sentinel/onb first): R01 checker 920,773 (`background` fills even-odd inside under Amendment 4's interior criterion); S02 spool 11.1 M (stopped at 145,960 groups > 10,000). Decision (parent, BTM notified, Cody can override): pin spool at shape/source-ring level. Attempt 3 narrowed S02 to identified producers: pin stop at 10,001 rings (25,772 groups, 1,939,053 rows). State: `background`: checker 920,773, unattributed 517,785; `background_boundary`: spool 1,939,053, unattributed 14,610,516. No `build` rows; partition does NOT close. 9,188,792 formerly claimed S02 rows are unvisited (producer scan stopped early), not disproved. Corrections: sentinel share is 88.46708 % (not 94.5 %); polygon 65623's winding/parity contradiction not reproduced; H1-H3, H5-H6 not demonstrated.
Carried: rules_bg.json S02 depends on side-table column (see provenance); cf_291 residual 589 (552 other identified producers + 37); pin-cap decision for the remaining ~9.19 M boundary rows; 14.6 M boundary rows unexplained by any witness. 3-07 stays open.

### 3-08 Cause table, remainder (Sol; Sonnet 5.5 review ACCEPT, `triage/review_3-08.md`)
`interior_cover` 824: spool 821 (unique byte-exact crossing-ring producers), unattributed 3. `completeness` 752: checker 495 (363 zero-width rings, 132 simple rings clipping to zero area), build 13, spool 56, unattributed 188. `name_anchor` 1: spool (extractor places lon 77.519 in west-edge cell 0; faithful encoder clamp gives 90.0; counterfactual 1 to 0). All five kinds: checker 921,268, build 13, spool 1,939,931, unattributed 15,128,492 (sum 17,989,704). Partition does NOT close.
Build finding (the only one): `parser/kiwiw/_cenc.c` `enc_bg` masks the class record count to 12 bits (line ~789) while writing all records; 9 cells wrap (each holds exactly 4,096 hidden records); cell (1795,647) declares 20, holds 4,116. Review confirms from disc bytes; the counterfactual alone does not separate build from spool (it edits the source side), the code and byte evidence carry it. Not fixed: scope of the re-oracle needs Cody (Assumption 1).
Carried: `pinned_candidates.tsv` is a 100-row view + total (26,650 groups), not the pinned list; real lists are git-ignored `enumerate_*.tsv`/`pins_*.tsv`; S02 pin cap decision (10,001 rings, ~9.19 M boundary rows unvisited); 14.6 M boundary + 517,785 `background` + 191 small-kind rows unattributed; sister 12-bit masks at `_cenc.c` ~222 and ~459 unmeasured; polygon 65623 unestablished; O01/O05 judgement calls; rules files need side-table columns (provenance). Phase 3 stays open; no trailer.

### 3-10 Count-wrap recon (Sonnet 5.5; `triage/count_wrap_recon.md`; independent Sonnet 5.5 review ACCEPT, `triage/review_3-10.md`)
Scope of rule O06 is 37 cells / 41 frames (not 9): `enc_bg` 12-bit class count wraps silently, each wrap is physical − declared = 4096, max 6,415 records, single class-2 unit; sister masks (`_cenc.c` ~222, ~241, ~459, ~460) never reached (tightest: vertex count, max 1,997 of 2,047). Host readers (D1, `background.py`, `dumpbkgd`; K1 via D1) sum same-class units. Original disc: 57,693 of 4,157,312 elements have 2-4 same-class units with disjoint type codes; max class unit 517 records; none reaches 4,095; offset word is true offset (G writes 0). A split by type code is impossible here (one type alone has up to 6,401 records). Split into same-class units needs 1 extra unit per element (+4 B; bg sub-frame headroom after: 970 B; whole-frame headroom measured only for golden cell (1755,591): 6 B to the 131,070 ceiling). Re-oracle would move full-AU and Perth shas and golden `l0_divided_trim_halo`; K1 completeness counts move declared to physical.
Open (Cody): same-class split with unrelated type codes and a >4,095-record unit has no original-disc precedent and no firmware evidence: format risk before 3-11 is authored. Unmeasured: whole-frame headroom of the other 36 cells; Perth-window overlap with the 37 cells. 3-11 NOT authored. Phase 3 open.
Review (ACCEPT, no blocker/high): mechanism, 41 elements/37 cells, reader sums and all original-disc statistics reproduced from saved data. Review adds: offset-word G-vs-R difference bears on the split (kept at 0 in 3-11, carried to Cody); bit 12 as a 13th count bit is a further unevidenced option (not used); G density (6,415) is ~11x R's maximum (585), so other firmware limits are also unobserved; Perth no-overlap computable now (bbox ix 816-848 vs cells ix ≥ 872); whole-frame headroom for 36 cells and golden-window list become 3-11 pre-edit checks C1-C3.
Decision (Cody/BTM, locked): O06 path = same-class split, the 37 cells are NOT carried as a known defect; format risk accepted, verified last-mile in vehicle. Unit authored: `briefs/3-11-count-wrap-split.md` (serial, recorded re-oracle, Assumption 1). Phase 3 open; no trailer.

### 3-11 O06 count-wrap split (Flash attempt 2; RE-risky re-oracle; Sonnet 5.5 review ACCEPT, `triage/review_3-11.md`)
Change: `parser/kiwiw/_cenc.c` `enc_bg` emits `ceil(class_n/4095)` consecutive same-class units (all but the last 4095, last the remainder) instead of one 12-bit-masked count; records keep order; table resized to `new_rec0 = unit_off+2+n_units*4`, squeeze generalized, bit 12 stays 0, `esz`/`out[2..5]` from `p`. Byte-identical for any element with no class >4095.
Pre-edit checks (all PASS): C1 whole-frame headroom of all 37 cells from G.leaf.tsv — worst leaf (1755,591) 131,060 -> 131,064, min slack 6 B, 0 over the 131,070 ceiling (`output/scratch-3-11/c1_result.json`); C2 Perth L0 bbox ix 816-848 / iy 839-887 vs 37 cells ix>=872, intersection empty; C3 only `l0_divided_trim_halo` (window 1755 591 1756 592) holds a wrap cell, the 7 committed fixtures hold none; C4 old oracle `output/scratch-3-11/G/ALLDATA.KWI` size 1,731,021,568 sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, inventory `G.cells.tsv` (3,951,970 cells) sha `b5e8fe3327e803cc848afc377378e969c05135832bfa53ed530b97ab913cd2ac`, Perth `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc`; old disc kept.
Build A: full-AU `G_new/ALLDATA.KWI` at -j6 sha256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` size 1,731,021,792 (+224 B: manifest frame payload +164 B = 41 x 4; the other +60 B is non-payload and UNATTRIBUTED, "sector rounding" does not fit the data, review finding 3); encode 11.4 s, assemble 9.0 s, wall 20.7 s. Fixed Perth `perth_fix/ALLDATA.KWI` sha `da13a775…` unchanged.
Compare B: `G.cells.tsv` vs `Gnew.cells.tsv` (both 3,951,970, no add/remove) -> exactly 37 differing cells, all level 0, 37/37 predicted, 0 extras (`output/scratch-3-11/Gnew.diff_cells.txt`, sha `9f2b0e554465d030637fa7d19b4ceaf88b6283b1d4d86810de5ccd4dece50e5e`); `scan.py` new `big=41`, `mism=0`, `multi_unit_elems=41`, `nunits_hist {1:1,420,958, 2:41}` (each of the 41 elements +1 unit).
K1 D: dump-off wall 82.1 s at -j6 — **exceeds the 72 s budget**; the brief caps harness at -j6 and the historic -j12 wall was 67-71 s, so the budget is only met above the mandated cap (deviation for the orchestrator). Full dump 189.5 s; extend 39.2 s. Classify OLD->NEW: O06 13->0; R01 920,773->920,786 (+13); S02 1,939,053->1,939,053 (0); O01 363, O02 821, O03 1, O04 56, O05 132 all 0. Kind failing totals: background 1,438,558->1,438,571; background_boundary 16,549,569->16,550,043 (+474, all unclassified); completeness 752->739; interior_cover 824; name_anchor 1. Causes: the 13 O06 rows now decode; the same 13 surface as R01 failures (unclassified background unchanged at 517,785, so additive not reassignment); the +474 boundary rows (14 new unclassified groups in 9 of the 37 cells, on previously hidden records) are newly decoded and join the unattributed `background_boundary` ledger (not S02, no cause forced); S02's 25,772 groups / 1,939,053 rows byte-unchanged. No unexplained delta.
Tests E: `parser/tests/test_bg_count_split.py` 4 passed (fixture `bg_split/under_4096_100.bin`, 1968 B, sha `4aa4f0546494d91900f48ad7eeaf2e2e2a93cfacdb4d5e64dae1cf4ff9fb750d`, generated from HEAD; the test needed a `sys.path` insert for `kiwiw`); full suite 839 passed in 581.9 s, 0 failed/skipped; committed goldens byte-identical (shas unchanged); `-j1` == `-j12` windowed build equal (sha `5162a0c5cc0306b271a9c58f18228df8d9962bb618b8d5fcca8b756b21bed2c9`).
Goldens F: recaptured only `output/goldens-3C/l0_divided_trim_halo`: frame_bytes 310,002->310,006, affected frame 131,060->131,064 (+4), total_sha `6cbe2f6f9dd8844e5fe5b4eb8fe332ecc488ca8314424245f61ea52e7244085e` -> `5162a0c5…`; the other 15 frames unchanged. (`manifest.overlap` drift is stale 3C-03 metadata, frames unaffected.)
Carried to Cody: G offset word stays 0 (do not fix here); same-class split has no original-disc/firmware precedent (format risk accepted, verified last-mile in vehicle); the -j6 72 s dump-off tension. Re-oracle is Cody-signed at phase close. Phase 3 open; no trailer.
Review (ACCEPT, no blocker/high): diff, 37-cell list, Perth and K1 per-rule table independently reproduced. Medium findings carried: (a) +60 B non-payload growth unattributed; (b) 82.1 s dump-off at -j6 vs 72 s: no pre-fix -j6 run exists, evidence favours the cap (445 CPU-s / 6 + ~7 s serial; K1 work identical), 120 s bar met, brief contradicts itself (-j6 cap vs budget set at -j12): ruling needed from Cody; (c) 474 new unattributed boundary rows; (d) new tests exercise class 2 only (full-AU byte compare covers multi-class). 3-12 fresh verify of the re-oracle and Cody's sign-off remain; Phase 3 open, no trailer.

### 3-12 Residual attribution (Sol; Sonnet 5.5 review ACCEPT-WITH-CONDITIONS, `triage/review_3-12.md`)
Sol: S03 (`background`, 517,648 rows / 30,547 groups), S04 (`background_boundary`, 14,602,251 / 216,319) and S05 (interior_cover, 3 rows) attributed spool through exact producers and a crossing-closing-edge mechanism; 9,064 rows remain unattributed (137 background, 8,739 boundary, 188 completeness); native classify `PARTITION FAIL`. Review: rule counts reproduce independently; fresh witness (1,029 vertices, seed 424242) all invalid; rule order hides nothing; remainder honest. PROVISIONAL, not accepted as a closed spool attribution: (A) the counterfactual repaired only 2 of 70,999 source rings (L0 type 288 window to 0; type 291 589 failures unexplained; L0 289/578, L2 289, L6 288 have none); (B) 2,184 fill + 12,818 boundary new rows lie 0.5-1.0 raw from an outline, untested as tolerance/quantisation; (C) root cause ambiguous: closing edge is the longest edge in 99.96% of L0 291 rings (open chain closed by a chord?), failing vertices are encoder clip connectors on leaf edges, many 2,000-4,000 raw outside the producer bbox, and why only some crossing rings fail (4-73% by ring size) is unexplained: spool extractor vs build clipping robustness decides the fix scope. Strata without a complete counterfactual are demoted to unattributed until 3-13. Phase 3 open; PARTITION not closed; 3-90 not run.

### 3-14 EO-aware background stitch (Maps Execute land-gates; Design TRIM ruling; landed `414c5fe`)
Run identity: branch `feat/3-14-bg-shape-eo-stitch` rebased onto `origin/master` `120bc78` (Plan 05 Phase 4 docs; clean rebase from `f3def00`+`67e48d9` → `e276eab`); Maps Execute finish_gates + pytest 2026-10-03; tip `a10585a` (finish_gates + golden recapture + d1 `cap_hint`). Adversarial review (DeepSeek → `output/CHM-3-14-adversarial.md`) initially **BOUNCE** on stale tip `67e48d9`; Design overruled completeness/stale-goldens vs tip `a10585a`. Design TRIM ruling 2026-10-03 (below).
Built: `parser/kiwiw/_cenc.c` (+300/-4) — new even-odd arrangement `eo_clip()` called from `bg_shape` for complex closed rings (per-chain filled-side classification via `eo_left`, coincident-edge cancel, DCEL face traversal with horizontal bridges, no interior chord); ordinary rings retain the legacy byte path. New `parser/tests/test_bg_eo_stitch.py` (32 tests) + `parser/tests/fixtures/bg_eo/{probe.c,simple_sha256.json}`. `docs/provenance.md` §`output/scratch-3-14/`.
Evidence (prior Flash continuation, retained): synthetic suite 32 passed and the 4-file gate 41 passed; `review_stress.py` 1,000 rings / 99,717 off-outline queries pass. Nine 3-13 CF windows clear target background/boundary/cover residuals to 0 on the original spool. Re-oracle: AU `013586b5…` → `4ed9cd80…` and Perth `da13a775…` → `04be2f6e…`; differing cells AU 246,123 (L0 244,060 / L2 1,944 / L6 118 / L8 1) and Perth 795 (L0 784 / L2 11), added 0 / removed 0. Explanation census (`explanations.json`): AU 246,116 background-payload-only + 4 division-topology + 3 frame-ceiling, Perth 792 + 3, **0 unexplained**; the 7 AU / 3 Perth non-payload-only cells are labelled inference, not byte-proven.
Classify / kind before→after (disclose; do not absorb R01 into build credit):
- S02–S05 build-target rows: **17,058,955 → 0** (S03 fill 517,648 + S02/S04 boundary 16,541,304 + S05 cover 3).
- R01 checker background: **920,786 → 0** (pre-edit L0 918,310 + L2 2,476 from `classify_before/cause_counts.tsv`; post-fix residual dumps for background empty — R01 cause stays checker with the 3-13 caveat; not reclassified here).
- K1 kind failing (new disc `k1_full.json`): background 0, background_boundary 0, interior_cover 0, road_node 0, range/step 0; **name_anchor 1** (pre-existing `lon 90.0` vs spool `77.519`, cell `(0,541)` — residual +1); **completeness 739 → 776 (+37, all L0)** — carry, not a land-blocker unless review attributes to EO stitch; not root-caused in Execute.
- Classify CLI still aborts on empty residual dump (`k1_triage._memmap`); S02–S05 = 0 rests on empty dumps + `k1_full`; tooling unchanged. 9,064 unattributed / PARTITION FAIL from 3-12 stays open.
Land gates (Execute, under `flock output/.heavy.lock`, cbuild ≤ `-j4`):
- `finish_gates.py`: determinism **`-j1` == `-j4`** on window `(0,828,745,831,748)` sha `c4965442effea2ea9a7cb1aca7b8f5abe4db050e968ff05572626ac9c2d21da5` (`determinism.json`); golden recapture for crossing-risk fixtures with sha change: `l2`, `l0_dense`, `l0_divided_halo` (committed under `parser/tests/fixtures/goldens/`) and `l0_divided_trim_halo` (scratch `local_goldens/` only — output/ goldens not overwritten upstream). Unchanged fixtures left alone. `goldens_changes.json` recorded.
- pytest: bg/cenc suite **45 passed** (`test_bg_eo_stitch`, `test_bg_clip_boundary`, `test_bg_count_split`, `test_c_units`, `test_cenc`, `test_cbuild_headers`). Full `parser/tests`: **894 passed + 4 failed** on first run; after installing recaptured `output/goldens-3C/l0_divided_trim_halo` and fixing `test_d1_one_call_per_range` (EO `l0_dense` needs ~1.47 M `bgcoord` rows — pass explicit `cap_hint=1<<21` so the one-call/range contract holds), remaining failure is **only** `test_dump_join_memory.py::test_replay_root_refusal` — worktree artifact: `output/scratch-3-12` symlinks into the main repo path, so `check_isolated` does not see the target as under worktree `output/` (same test **passes** on main-repo `33006aa`). Not an EO-stitch defect. Re-checked failing subset after fixes: d1 + local trim_halo goldens/e2 **pass**.
TRIM / finish_gates (Design ruling 2026-10-03 — measurement story):
- Encoder rule (`parser/build_alldata.py` ~533–539): `pct = 100 * dropped / total_kind` for the **level as built**; prints `** >1% BLOCKER **` when `pct > 1.0`. Denominator is window-local under `--window` / golden windows, not full-AU.
- Window L0 (finish_gates golden `l0_divided_trim_halo`): road **207/1,083 (19.114%)**, bg **227/8,824 (2.573%)** in 1 sub-cell — **overruled as land-blocker**. Same absolutes on full-AU: road **207/3,015,057 (0.007%)**, bg **227/11,029,580 (0.002%)**. Window % is a tiny-denominator artifact, not AU content loss.
- L8 full road (binding >1% signal, level-scoped): **308/14,012 (2.198%)** in 1 sub-cell (hard-ceiling fallback sub-cell `(3,0)` 308/2417). **Old-oracle vs new-disc (same full-AU encode recipe):** pre-3-14 `output/scratch-3-11/G_new_build.log` / `G_build.log` and `output/scratch-3-12/G_build.log` print identical `308/14,012 (2.198%)`; post-3-14 `output/scratch-3-14/full_build.log` identical. **No L8 bg TRIM line** on either. L8 road TRIM **unchanged** → accept as **known budget** (Design ticket for any expand-to-zero follow-up; not 3-14 scope).

Deviations / carry (not land-blockers): completeness **+37** / name_anchor **+1** (Design carry); dump_join isolation false-negative in this worktree only; 7 AU / 3 Perth cells inference-only; classify mmap caveat; CHM adversarial MED items (inference labels, AU∩Perth cell overlap, EO edge residuals) disclosed, not blockers. No tolerance loosened, no spool pin, no live `extend.py` semantics change. Report: `output/CHM-3-14-report.md` (git-ignored). **Landed** `414c5fe` (merge PR #2) after Design TRIM ruling + L8 baseline unchanged.

### 3-15 Completeness remainder: cell-local representability (Science; no land-blocker)

Brief [briefs/3-15-completeness-cell-local.md](briefs/3-15-completeness-cell-local.md), base `adfbdbd` (3-14 `414c5fe`). Scratch `output/scratch-3-15/`; full note [triage/completeness_3-15_cell_local.md](triage/completeness_3-15_cell_local.md). No S02–S05 predicate edited, no tolerance loosened, no L8 expansion, no rule registered.

C1–C4: C1 tip contains 3-14; AU `4ed9cd80…` / Perth `04be2f6e…`. C2 188-key list + both dumps located; **776 and net +37 confirmed, but the key set-diff is 687 shared + 89 added + 52 cleared (739 − 52 + 89 = 776), not a 37-key superset** — corrects the §3-14 carry wording. C3 O01/O04/O05 load; empty-residual-dump mmap caveat unchanged. C4 baseline completeness **776**, name_anchor **1**, S02–S05 **0** (`k1_full`). 9,064 unattributed not re-claimed.

Complete topology repair (3-13 `split.decompose` even-odd faces) over the historic 188: 885 faces / 189 meets, 205 clip into cell, **0 representable** (0 non-zero quantised area2, 0 C records); sub-unit-width slivers. Disposition **`checker:repaired-not-representable` ×188** (supersedes the 3-08 one-coordinate-repair stop).

+37 disposition (contract comparison legacy vs 3-14 stitch): **89 added = all legacy-records>0 → stitch-records==0 = EO-stitch side-effect (build regression)**; **52 cleared = stitch-records>0 = EO-stitch side-effect (now satisfied)**; historic 188 unchanged (checker). Not byte-pinned per cell (no window CF); contract-level.

Recount on the 3-14 disc (stitch contract): **776 = O01 363 + O05 132 + O04 7 + unattributed 274**, remainder 0 (shared 687 `{363,132,4,188}` + added 89 `{O04 3, unattributed 86}`). Legacy-contract recomputation reproduces pre 739 `{O01 363, O05 132, O04 56, unattributed 188}`. The 3-14 dump's `other_mechanism` bytes are inherited/forced-zero artifacts (30 O05 + 1 O04 zeroed on changed cells); the recomputed tally is used. No absorption into O01/O04/O05.

Build-fix gate: **not passed** — no original-spool byte-gate/window CF and no Design amendment, so only the honesty packet is delivered. Candidate rule O07 recorded in the triage note, not registered. Deviations: actual 89/52 churn vs documented +37 superset; dump mechanism bytes untrustworthy; no full-AU rebuild (13G disk). Status `done with concerns`. **Landed** `6b8a68a` (merge PR #3). No follow-on unit until Design names one.


### 3-16 Completeness 89-key window counterfactual — done (Science)

Run identity: local Codex Sol, branch `feat/3-16-completeness-89-window-cf`,
base `9b44b595787656ba0311dd5c1641aa1d588d5310`, started 2026-10-03.
Only brief `briefs/3-16-completeness-89-window-cf.md`; unit worker, not phase closure.
C1 PASS: `6b8a68a` is an ancestor. C2 PASS: `7a12618`'s packet points to the
recoverable `open-pajero-maps-3-15/output/scratch-3-15/contract_comparison.json`
`added_89` rows; keys and meeting-source identities copied to private
`output/scratch-3-16/keys89.json`. C3 PASS: the cited arithmetic is quoted once in the
[3-16 science packet](triage/completeness_3-16_window_cf.md), without a fresh census.
Workflow-quality execution service is not exposed in this local harness;
no execution id is available. No phase trailer will be added by this unit.
Built: [science packet](triage/completeness_3-16_window_cf.md),
[full-key outcome table](triage/completeness_3-16_outcomes.tsv), this unit record,
and `docs/provenance.md` for private scratch. No encoder, checker, or rule changes.
Tally: **0 pass / 89 fail / 0 untested**. All 89 original-spool one-cell windows
match the stored 3-14 frame bytes; 34 source rings → 156 exact EO faces bypass
complex-ring stitching in a private spool; every counterfactual frame remains
byte-identical and every original completeness key persists under original-spool
K1. Run wall 1,213.8 s. Cold audit PASS: exact full-key coverage/dumps, decoded
geometry, byte gates/equality, EO interior witnesses, serialization error at most
1.8617682673836184e-9 raw, original home-record/index hashes unchanged. Legacy
original-spool-degree probe remains positive 89/89; no counterfactual piece appears.
Disposition: accept-with-honesty for these 89 only. No gate (b) pass or evidence
for a later C amendment; Design gate (c) unchanged. Untested list: none.
Deviation/limit: 3-15 names an EO-stitch contract side-effect but no localized C
bug; the tested correction is a topology-preserving face bypass, not a C patch.
No other scope deviation. No full-AU encode, no cache drops, builds/K1 one worker,
serial compilation, all heavy stages under the main checkout's shared lock.
No protected oracle overwritten, no O07, no historic cause or 9,064-row ledger
reopened. Tool-turn budget ≤60; harness cost/token telemetry unavailable.
Unit stops here; Phase 3 remains open, Execute owns landing.
