# C core, Python orchestration

## Intent

User request, verbatim:

> C for all perf-sensitive work; Python orchestration only. Close 3C as debt into plan 04/3D. Grow libkiwiw from existing C; C decoder+checker first; delete Python decoders once C matches goldens/R; checker-first keep SHA; freeze old Phase 4–10 briefs.

## Problem

Plan 03's Phase 3C moved the build hot path to C (full-AU build 100 s → 12.2 s, sha `87a01b14…` unchanged) and closed with one outcome unmet: `quantisation_roundtrip` runs in 991.6 s against 120 s, and reports failures that nobody has triaged (background 1,438,558; background_boundary 16,549,569; interior_cover 824; completeness 752; name_anchor 1) plus one confirmed disc defect (fill pieces 4–6 cells outside spool polygon 65623). The cause is structural, not a bug: verification still decodes the disc in Python (decode ≈ 70 % of CPU, ≥ 2,500 s serial), so no Python tuning reaches the budget. The same pattern holds for every other tool that decodes (`coord_scale` at 111 s of a 120 s budget, the census and overlay tools, the harness checks).

Plan 03's Contract B put verification and the decoders on the Python side, and Phases 4–10 of plan 03 are written against that shape. Continuing them as written would add more Python-side measurement of a disc that cannot yet be checked in budget, and would make the unresolved failures harder to attribute. The boundary rule has to change before the map-layer content work resumes.

## Solution Shape

One C library, `libkiwiw`, grown in place from `_cenc.c`/`_e1.c`/`_e2.c`, owns every per-vertex, per-shape, per-parcel and per-cell computation: encode (exists), decode (new), check (new), and the geometry/adjacency algorithms the census tools need. Python is orchestration only: CLI, range planning, process pool, paths and mmap handles, JSON/manifest/report glue, and bounded header reads. The Python decoders for the road, background, name and parcel layers are deleted once the C decoder reproduces them on the goldens and on R; no Python fallback remains. The 3C-04 debt is closed by a C checker that runs inside budget, then triaged until every failure has a cause, and the confirmed defect is fixed or enumerated. Plan 03's Phase 4–10 content work resumes afterwards under a successor design written C-first.

### Domain: libkiwiw (C core)

- Owns: all code that loops per vertex, shape, parcel, cell or frame over a full-AU spool or disc: E1/E2 (existing), the decoder (D1), the checker (K1), and geometry/adjacency kernels shared by them. Owns the C-side timers, call counters and the row layouts that cross its boundary. Single shared library built on demand by `cbuild`; gcc stays a stated requirement.
- Contract:
  - **Granularity (extends Contract B).** One C call per contiguous range of cells (build) or frames (decode/check). No per-parcel, per-shape or per-vertex call crosses the boundary. Calls take the mmap'd spool or disc region zero-copy and write fixed-width columnar rows into caller-provided buffers; no callbacks, no Python objects, no pickle.
  - **D1 decode.** Input: a byte region of `ALLDATA.KWI` (G or R) plus the block/frame descriptor for the range. Output: columnar rows carrying every field that `kiwiw.parcel.decode_parcel` and the road/background/name sub-decoders return today (header words, link and node fields, background shapes and vertices, name strings and anchors, flags), losslessly. A field the Python decoder returns and D1 omits is a defect.
  - **K1 check.** Input: D1 rows plus the spool via the same zero-copy reader. Output: for each check kind an exact `checked` count and an exact `failing` count, plus a bounded sample of failing items per kind (cell, type, shape id, vertex) so triage can start from them. Counts are exact; only samples are capped. Check kinds and tolerances are those of 3C-04's brief (`range`, `step`, `road_node`, `name_anchor` with its halo and subcell explained-categories, `background`, `background_boundary`, `completeness`, `interior_cover`); a tolerance or rule change is made only in Phase 3, with the reason and the count it moves recorded.
  - **Determinism.** D1 and K1 output is byte-identical for any worker count. The sample for each kind is the first N failing items in `(level, iy, ix)` order, then shape/vertex order; N is fixed in the header. Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal.
  - **Census kernels.** The geometry/adjacency work the census tools do (continuity, boundary mirroring, neighbour lookup, per-class coordinate scale, occupancy, density) is C under the same granularity rule: one call per range, fixed-width rows out. Its testable bound is the C-side call counter: calls ≤ number of ranges planned, reported per tool like the build's call counts.
  - **Off the build path.** D1, K1 and the census kernels are verification entry points; E1, E2 and the H4 copy stay the only C entry points on the build path, so plan 03's Contract B sentence "nothing else crosses from Python to C on the build path" still holds for the build and is superseded only for verification.
  - **Layout single-source.** Every row layout is declared once in a C header and mirrored in Python by a checked descriptor, as `COLS[]` is today; a mismatch fails at load.
  - **Evidence.** Every hot call reports C-side wall and call counts, so the Python/C/handoff split of Contract H is measurable for decode and check as it is for build.
- Non-goals: extraction (OSM → spool) stays Python and is not ported here; greenfield re-architecture of the library; replacing the process pool with C threads.

### Domain: Python orchestration

- Owns: the CLIs (`build_alldata.py`, `compare_disc.py`, the check/census entry points), range planning and weighting, the worker pool, locating/mmapping files, the single binding module to libkiwiw, manifest/report/JSON assembly, schema lint, extraction, and header-level reads whose trip count is bounded by file or level count (volume, misc, parcel-management).
- Contract:
  - **Perf-sensitive means:** any loop whose trip count scales with the vertices, shapes, parcels, frames or cells of a full-AU disc or spool. Such a loop is C. A Python loop is allowed when its count is bounded by ranges, levels, files, check kinds or report rows.
  - **One door.** Python reaches libkiwiw through a single binding module; no other module loads the library or declares layouts.
  - **No Python decoder or checker for the four parcel sub-layers after Phase 5**, and no Python copy of any C algorithm as an oracle after its equivalence phase (this amends Contract T: field-for-field equivalence between the Python decoders and D1, and count equivalence between the Python `quantisation_roundtrip` and K1, are permitted until Phase 5, and only for those two purposes).
  - **Inventory.** A committed inventory classifies every Python module under `parser/` as orchestration, C-now, C-later or retired; a test fails for any module absent from it.
- Non-goals: making Python faster; a plugin or scripting surface; moving CLI parsing or reporting into C.

### Domain: Gates and oracles

- Owns: the table of hard gates and who may change an oracle.
- Contract:
  - Full-AU build at `-j 12`: sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B, manifest equal to 3-11's. Perth `-j 1` == `-j 4` == `da13a775…`. Goldens (`parser/tests/fixtures/goldens`, plus the local trim golden) byte-exact. Declined list empty. These hold at every phase close.
  - Contract H budgets (plan 03) stay binding; the full build stays ≪ 60 s (3C close: 12.16 s) and the regression rule is unchanged: a rise above the run-to-run spread names its mechanism. Decode and check join as hot paths H5 and H6.
  - C checker: ≤ 120 s wall at `-j 12` on the 3-11 disc against its spool, median of three, peak memory measured as the sum of per-process PSS (not RSS) against a ceiling that is provisionally 22 GB (the old tool's limit) and re-signed at the Phase 2 close from the measured peak.
  - Oracle changes: the build sha moves only by a deliberate re-oracle recorded in a phase record with the exact cells that differ and the reason; until then 87a01b14… is the oracle. A check tolerance moves only in Phase 3, on a recorded cause. R is the reference disc; D1 must decode R and G identically to the Python decoders on the equivalence set (Phase 2) before they are deleted.
  - Agents: Flash may draft; every Flash draft gets a mandatory Sonnet 5.5 review before it counts; Claude/Grok sign phases off. No Opus on this plan.
- Non-goals: new content parity targets (those belong to the successor design).

## Architectural Implications

- `docs/ARCHITECTURE.md`: the Build boundary section becomes "libkiwiw boundary"; "Readers and writers" loses the Python decoders for the road/background/name/parcel layers; "Evaluation" and "Analysis" rows are re-stated against D1/K1. Phase 1 states the rule; Phase 5 makes the module map true.
- Plan 03 `DESIGN.md`: Contract B's "Python owns … all verification and analysis tools including the decoders", its "nothing else crosses" sentence (for verification only; see libkiwiw Contract), and Contract T's layer (a) "decode with the Python decoder" are superseded by Domain: Python orchestration above; boundary tests decode through D1 after Phase 5. Contract H gains H5/H6. Plan 03's other contracts (E1/E2, W) stand.
- Plan 03 stays open. Its remaining Phase 3 units (3-10, 3-13, 3-05, 3-06) and Phases 4–10 are frozen: no refine, brief or build against them until the successor design (Phase 6 here) replaces their Surfaces and verification. Plan 03 is not collapsed by plan 04.
- The 3C carried items 2–7 (raw-coordinates half of 3C-05, `test_bench_record` flake, stale docstrings and grep wording, 174 s default suite, Flash worktree) stay on plan 03's record. Item 2 is picked up in Phase 4 (it is a `coord_scale` matter); the rest are not plan 04 scope.
- Decoder deletion reaches the build module: `alldata_writer.py` (imported by `build_alldata.py`) calls `decode_parcel` and the parcel-layer writers on its R-replicate load path, and `disc.py` imports `decode_parcel`. Phase 5 re-points or retires those paths together with the R-replicate writers and the research scripts (Assumption 3); the build output must not change.

## Decisions

Locked by Cody before this design; not re-asked.

1. Approach B: C for all perf-sensitive work (encode, decode, check, geometry/adjacency); Python is orchestration only.
2. Phase 3C / plan 03 closed as debt into plan 04 at `0cf5d99`; the 3C-04 round-trip evidence is carried here.
3. Python decoders are deleted once the C decoder and checker match goldens and R.
4. Checker-first triage; the current sha oracle stays until an intentional re-oracle.
5. Plan 03 Phase 4–10 work is frozen until rewritten under the C-first rule.
6. libkiwiw is grown from the existing `_cenc`/`_e1`/`_e2` in this repo; a greenfield library is deferred.
7. Hard gates: full-AU sha 87a01b14…, Perth da13a775…, goldens, Contract H build ≪ 60 s; C checker ≤ 120 s target.
8. Agents: Flash may draft with mandatory Sonnet 5.5 review; Claude/Grok sign off phases; Sonnet only for this orchestrator and workers.
9. Extraction stays out of the C boundary ("not now", plan 03). It is a non-goal here; revisiting it is a later design.

## Assumption Ledger

Settled without Cody because they follow from the decisions above; challenge at the checkpoint.

### Assumption 1

- Question: Phase 3's outcome says "0 background failures", but a confirmed disc defect exists. Does fixing it break "keep SHA"?
- Answer chosen: Phase 3 classifies every failure first. Checker-side causes are fixed in the checker with the sha untouched. If a build-side cause is real, its fix lands in the C build and the sha changes only in the enumerated cells, recorded as a deliberate re-oracle in that phase's record, with goldens and Perth re-captured only where affected. Spool-caused items are enumerated as a pinned list. The outcome is "build- and checker-caused failures are 0 and spool-caused failures equal the pinned list, on the oracle disc in force at phase close".
- Rationale: The intent's "checker-first keep SHA" and "until intentional re-oracle" both allow this; forcing zero on a defective disc would require loosening the checker, which would hide the defect.
- If wrong: if Cody wants the sha frozen even for a build-side defect, that defect is pinned too and its fix moves into the successor design; if Cody wants literal zero, extraction fixes come into scope (Assumption 4).

### Assumption 2

- Question: What is the numeric budget for moving the harness and census hot checks to C?
- Answer chosen: `coord_scale` ≤ 20 s at `-j 12` (111 s today, same `per_class` results over 1,461,347 parcels / 73 classes); no individual harness check or census tool over 60 s on the 3-11 disc. Phase 4 measures each before and after and reports.
- Rationale: With D1 in C, decode dominates neither; the numbers are provisional placeholders, not measurements. Phase 2 measures per-check wall with D1 and reports it; the Phase 4 budgets are signed by Cody at the Phase 2 close, and 20 s / 60 s stand if he does not change them. The memory ceiling is likewise provisional (the existing tool's 23,068,672 kB limit, now measured as PSS) and is re-signed at the Phase 2 close from the measured peak.
- If wrong: the Phase 4 numeric outcome moves with the signed budgets; the mechanism (call counters bound C calls by ranges, no Python per-vertex loop) is unaffected.

### Assumption 3

- Question: What happens to the R-replicate parcel-layer writers and the research scripts that import the deleted decoders?
- Answer chosen: They are retired together with their tests, unless they are on the build or gate path, in which case they are re-pointed at D1. The build module's own R-replicate load path (`alldata_writer.py`, `disc.py`) is such a case unless Phase 5 shows it unused by any gate, in which case it is deleted; either way the full-AU, Perth and golden bytes are unchanged. `volume`/`misc`/`parcel_mgmt` decoders and writers stay (bounded headers).
- Rationale: They round-trip R through the Python decoder and are research/proof tools (Contract B already marks them verification-only); keeping them would keep a Python decoder alive.
- If wrong: a gate that turns out to need a retired writer forces it to be re-pointed at D1 inside Phase 5, and Phase 5 grows by that writer's port.

### Assumption 4

- Question: Do 3C-04 failures traced to extraction (spool) rather than the build get fixed in plan 04?
- Answer chosen: No. They are enumerated and carried to the successor design; extraction stays out of scope. Only a build-side (C) cause is fixed in Phase 3.
- Rationale: Decision 9 keeps extraction in Python and out of scope; Phase 3's job is attribution.
- If wrong: Cody pulls extraction fixes into Phase 3 and the phase count is unchanged but its surface grows.

### Assumption 5

- Question: Where do the unstarted Phase 3 units and plan 03's close-out go?
- Answer chosen: They wait. Phase 6 produces the successor design that re-states them (and Phases 4–10) C-first; plan 03 is collapsed when that design's content phases have absorbed or retired them.
- Rationale: The intent freezes them; plan 04's phases do not include building map-layer content.
- If wrong: plan 03 is closed early with the remaining phases carried as debt, as 3C was.

## Open Questions

None that block sign-off. Phase 3 may surface an extraction-side defect (Assumption 4) or a disc defect needing a re-oracle (Assumption 1); both are recorded at that phase, not decided now.

## Phases

The count and order are fixed at sign-off.

### Phase 1 — Policy and contracts lock

- Outcome: `docs/ARCHITECTURE.md` states the rule (C for every full-AU per-vertex/shape/parcel/frame/cell loop; Python orchestration only) and the libkiwiw boundary including D1, K1 and H5/H6; plan 03 `DESIGN.md` carries a pointer marking the superseded Contract B/T text and Phase 4–10 as frozen; the perf inventory exists and a test fails for any `parser/` Python module missing from it; every module classified C-now or retired names the phase that moves it. No code behaviour changes: full-AU build sha, Perth sha and goldens unchanged.
- Surfaces: `docs/ARCHITECTURE.md`, `docs/plans/03-map-layer-parity-remediation/DESIGN.md` (pointer only), the inventory file and its test under `parser/tests/`.
- Approach: known
- Depends on: nothing
- Refine: skipped. One worker carries it (92 non-test `parser/` modules to classify, one ARCHITECTURE edit, one pointer, one test); `execute` briefs it inline.

### Phase 2 — C decoder and C checker, within budget

- Outcome: The round-trip entry point, run at `-j 12` on the 3-11 disc and its spool, completes in ≤ 120 s median of three, with peak PSS (summed per-process PSS) recorded and under the ceiling in Gates, and reports exact `checked`/`failing` counts and failing samples for every 3C-04 check kind. K1's counts equal the 3C-04 record on that disc exactly: range 309,192,246 / 0, step 252,444,802 / 0, road_node 42,995,770 / 0, name_anchor 2,317,983 / 1, background 174,332,105 / 1,438,558, background_boundary 89,546,388 / 16,549,569, completeness 1,800,514 / 752, interior_cover 1,592,016 / 824, with the explained categories (name_anchor_halo 311,347, road_node_subcell_on_polyline 551,530) also equal. (Phase 2 reproduces the old answers fast; it does not fix them.) D1 gates K1: D1's equivalence is proven first. D1 reproduces every field of the Python decoders on all goldens and on a fixed sample of R parcels covering all four sub-layers (a field-for-field equality test, one of the two permitted Python-oracle uses), and decodes R and G identically to the Python decoders. Phase 2 also reports measured per-check wall for D1 on the harness checks so the Phase 4 budgets can be signed (Assumption 2). Build gates (sha, Perth, goldens, H budgets) unchanged.
- Surfaces: new `kiwiw/_d1.c`, `_k1.c` (names indicative) joined into the single library via `cbuild`, the binding module (`cenc.py` or its successor, the one door), `parser/kiwiw/ctest/`, `parser/tools/quantisation_roundtrip.py` (becomes a thin driver; its Python checking stays only as the count oracle until Phase 5), tests.
- Approach: known
- Depends on: Phase 1
- Units (briefs under `docs/plans/04-c-core-orchestration/briefs/`; heavy runs serialise on `output/.heavy.lock`):

  | Unit | Brief | Depends on | May run alongside |
  |---|---|---|---|
  | 2-01 D1 frame decoders (C) | `2-01-d1-frame-decoders.md` | Phase 1 | none (owns `_d1.c`, `_d1.h`, `cenc.py` D1 section) |
  | 2-02 D1 block walker and equivalence | `2-02-d1-block-walker-equivalence.md` | 2-01 | none |
  | 2-03 K1 point kinds (range, step, road_node, road_point, name_anchor) | `2-03-k1-core-point-kinds.md` | 2-02 | none |
  | 2-04 K1 background kinds | `2-04-k1-background-kinds.md` | 2-03 | none |
  | 2-05 K1 completeness | `2-05-k1-completeness.md` | 2-04 | none |
  | 2-06 round-trip thin driver | `2-06-roundtrip-thin-driver.md` | 2-05 | none |
  | 2-07 full-disc run kickoff | `2-07-full-disc-run-kickoff.md` | 2-06 | none |
  | 2-08 full-disc verify and record | `2-08-full-disc-verify-and-record.md` | 2-07 | none |

### Phase 3 — Triage the 3C-04 debt

- Outcome: every failing item behind the counts in Problem is assigned exactly one cause — checker rule wrong, build (disc) defect, or spool/extraction defect — with the count per cause recorded. On the oracle disc in force at phase close, the checker reports build-caused and checker-caused failures of 0 in every kind, and the failures that remain are exactly the enumerated spool-caused list (item identity, not only counts), carried to the successor design. `name_anchor`'s one failure (L0 cell (0,541), leaf 928) is such a carried spool item (the 3C record calls it an extractor defect), not an acceptance target; background, background_boundary, interior_cover and completeness reach 0 unless a pinned spool-caused item remains. The disc defect near spool polygon 65623 is classified in the cause table; if build-caused it is fixed in the C build. The run takes ≤ 120 s. Any sha change is a recorded re-oracle (Assumption 1); otherwise 87a01b14… stands.
- Surfaces: `_k1.c` rules and tolerances, `_e2.c`/`_cenc.c` only if a build defect is confirmed, `parser/tools/quantisation_roundtrip.py`, the cause table in the phase record.
- Approach: open
- Depends on: Phase 2
- Units (briefs under `docs/plans/04-c-core-orchestration/briefs/`; heavy runs serialise on `output/.heavy.lock`; the C library is touched by one unit at a time, so only 3-06 runs alongside anything):

  | Unit | Brief | Depends on | May run alongside |
  |---|---|---|---|
  | 3-01 cbuild header hash | `3-01-cbuild-header-hash.md` | Phase 2 | 3-06 |
  | 3-02 K1 failure dump | `3-02-k1-failure-dump.md` | 3-01 | 3-06 |
  | 3-03 dump diagnostic columns | `3-03-k1-dump-diagnostics.md` | 3-02 | 3-06 |
  | 3-04 inside-side tolerance fixture | `3-04-inside-tolerance-fixture.md` | 3-03 | 3-06 |
  | 3-05 triage tool | `3-05-k1-triage-tool.md` | 3-03 | 3-06 (not 3-04: both run K1 tests) |
  | 3-06 spool forensics dossier | `3-06-spool-forensics-dossier.md` | Phase 2 | 3-01 to 3-05 |
  | 3-07 cause table: background kinds | `3-07-cause-table-background.md` | 3-04, 3-05, 3-06 | none |
  | 3-08 cause table: remainder and consolidated | `3-08-cause-table-remainder.md` | 3-07 | none |
  | 3-10 to 3-89 fix units | authored inline by the orchestrator from `3-fix-template.md` after `triage/cause_table.md` lands | 3-08 | none |
  | 3-90 fresh verify and record | `3-90-fresh-verify.md` | 3-08 and all fix units | none |

  Fix units are not briefed now because `Approach: open`: their number and content depend on the cause table. 3-01 to 3-08 are the tooling that makes the cause table; the fix units follow it; 3-90 closes. If 3-07 or 3-08 report `blocked: unattributed`, bounce to Cody before any fix.

  Carried-item placement (from Phase 2): cbuild header-staleness hazard, absorbed in 3-01. Uncovered inside-side TOL mutation, absorbed in 3-04. D1 `*_first` quirk, float-key tie (hypothesis H2) and `container`/`shape` early-exit question: float-key tie absorbed in 3-07; the D1 quirk is checked only if the dossier (3-06) or cause table shows it causing a failure, otherwise goes to Phase 4; the early-exit question goes to Phase 4 (harness checks). Explained counters unexercised: goes to Phase 4/5 (counter gates there). rc=1 harness FAILs: goes to Phase 4 (harness), not scoped here.

### Phase 4 — Harness and census hot checks in C

- Outcome: before any change, a baseline output for each harness check and census tool on the 3-11 disc is captured from the Python code and recorded in `docs/provenance.md` (local, not committed). Afterwards `compare_disc --checks coord_scale --workers 12` produces the same PASS and `per_class` results as `output/scratch-3-11/cs_G.json` (0 of 1,461,347 parcels, 73 classes) within the `coord_scale` budget signed at the Phase 2 close (provisionally 20 s; 111 s today). Every other harness check (`decode`, `container`, `envelope`, `mfde`, `shape`, `vocab`, `spotcheck`) and census/overlay tool (`parser/tools/{coord_scale_census,continuity_census,boundary_mirror_census,header_word_census,road_density_census,parcel_occupancy,overlay_test}.py`, with `r_neighbours.py` as their shared lookup) produces output equal to its baseline and runs within its signed budget (provisionally 60 s). The C-side call counters show calls ≤ ranges planned for each. The raw-coordinates half of 3C-05 (carried item 2) is met; if it cannot be, the phase stops and asks Cody rather than restating it. Build gates unchanged.
- Surfaces: `parser/harness/checks/*`, `parser/harness/walk.py`, `parser/harness/bytediff.py`, the tools above, new census kernels in libkiwiw, ctest.
- Approach: known
- Depends on: Phase 3 (baselines and rules must not straddle a Phase 3 re-oracle)

### Phase 5 — Thin Python driver; Python decoders deleted

- Outcome: `kiwiw.{road,background,name,parcel}` decoders, the Python checking path in `quantisation_roundtrip.py`, the R-replicate load path in `alldata_writer.py`/`disc.py` and the writers and scripts retired under Assumption 3 are absent or re-pointed at D1, and no module imports them; every remaining Python module is classified orchestration in the inventory test; the only Python that loads libkiwiw is the binding module; boundary tests decode through D1; `parser/` pytest passes with no skips attributable to the removal; the build and check gates all hold (sha 87a01b14… or the Phase 3 oracle, Perth, goldens, H budgets, checker ≤ 120 s); `docs/ARCHITECTURE.md`'s module map matches the tree.
- Surfaces: `kiwiw/{road,background,name,parcel}.py` and matching `*_writer.py`, `kiwiw/alldata_writer.py` (its R-replicate load path), `kiwiw/disc.py`, `parser/roundtrip_*.py`, the `analyze_*`/`estimate_*`/`survey_*` importers, `parser/tests/boundary.py` and decoder tests, the binding module, `docs/ARCHITECTURE.md`; the Python checking in `quantisation_roundtrip.py` that K1 replaced.
- Approach: known
- Depends on: Phases 3, 4

### Phase 6 — Successor design for the frozen map-layer content

- Outcome: a signed-off successor design in `docs/plans/` re-states plan 03's remaining Phase 3 units (3-10, 3-13, 3-05, 3-06) and Phases 4–10 as phases whose Surfaces are libkiwiw sources and whose verification runs on the C checkers, with plan 03's old Surfaces and any reference to a deleted Python decoder removed. Plan 03's DESIGN carries a pointer to it and no frozen phase remains un-pointed. No map-layer content is built in plan 04.
- Surfaces: new design folder under `docs/plans/`, plan 03 `DESIGN.md` pointer.
- Approach: known
- Depends on: Phase 5

## Provenance Notes

- **Why the decoder comes before the checker's triage.** The 3C-04 failure counts cannot be attributed to causes until a run fits the iteration loop; 991 s per attempt is the reason the failures are untriaged. Phase 2 buys that loop; Phase 3 uses it.
- **Why deletion is last.** Python decoders are the equivalence oracle for D1 in Phase 2 and the only decoder the harness checks use until Phase 4. Deleting at Phase 5 keeps one working oracle at every close.
- **Rejected: a greenfield libkiwiw.** The existing C already has the descriptor, spool and build discipline; a rewrite spends a phase before the debt moves.
- **Rejected: speeding the Python checker.** 3C-04's measurement put decode at ≈ 70 % of CPU and ≥ 2,500 s serial; no restructuring of the Python reaches 120 s.
- **Rejected: a Phase 3 that loosens tolerances to reach 0.** It would hide the confirmed defect; tolerance changes need a recorded cause.
- Phase 6 is a design, not a build, because refine and briefs for the frozen content depend on surfaces that do not exist until Phase 5.
