# Implementation — 04-c-core-orchestration

- Tool: Claude Code, orchestrator Sonnet 5.5
- Session: https://claude.ai/code/session_01KFbprktJzdCyubbCXezU5h
- Started: 2026-10-01T10:18Z
- Scope: Phase 1 only. Workers Sonnet by default; Opus only as the one-tier retry after a Sonnet failure (user instruction). Phase 1 skipped refine (one unit); brief authored inline.

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
