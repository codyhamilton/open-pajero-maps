---
name: assessor-briefs
description: >-
  How-to-test briefs for this repo's assessors (code quality, security,
  performance, functional e2e, UI, UX). Use when this bot runs daily
  analysis or is prodded because the designs pipeline is empty.
---

# Assessor how-to-test briefs — open-pajero-maps

## Ownership map

**Quality Assessor is the only assessor named for this repo.** It owns code quality, security, performance, and the verification bar below. **Functional e2e, UI, and UX are explicitly folded under Quality Assessor ownership.** There is no separate Experience or E2E assessor seat, and no harness seat.

**Project-complete definition:**

- E2E generation matches the original DVD in every verifiable aspect.
- Every claim / assumption / implementation is verified.
- Every deviation has a root cause.

Apply `docs/design/target-disc.md`: full Australia, levels **0, 2, 4, 6, 8, 10, 12**, map/routing/POI/address content, every map-dependent file regenerated, then UDF-bridge DVD and final MMCS acceptance. Replicated original content must round-trip byte-identically; OSM-derived content needs structural/behavioral parity with verified source-data differences. Processing defects remain defects. A locally accepted but unattributed deviation does **not** meet this completion definition.

**Assessment procedure:** ticket **Design only**, with domain, reviewed commit, input/output hashes, command, expected/actual behavior, affected keys/offsets, evidence, and acceptance check. Do not build, merge, push, alter product code/config/oracles, or create build/harness/Experience/E2E seats. If verification requires compilation or generation, request the resulting evidence through Design; assess existing artifacts. In particular, full pytest and golden tests include compilation and temporary generation. Recipes below describe reproducible verification, not authorization to build a deliverable.

**Command context:** run from `/home/codyh/workspace/open-pajero-maps`. Set `PY=.venv-rp/bin/python`, `R=/run/media/codyh/464210-8480`, `G` to the **reviewed generated disc directory**, and `E` to a fresh private evidence directory under `output/` (create it before writing reports). The reference mount and `original-disc/pajero-whereis-2007.iso` exist here. Never assume `output/ALLDATA.KWI` is the latest oracle. Heavy checks/replays hold `flock output/.heavy.lock` for their entire process tree, one at a time; current operational caps are build/compiler ≤4 and K1/harness ≤6 workers (`docs/WORKFLOW.md`).

Grounding: repository inspection at `ced98f8272fc1e4a34ba0d34b0dbbb1535c5f205`; commands were inspected, not executed. `docs/OVERVIEW.md` supplies the README-style overview; no tracked GitHub Actions CI was found. Spec evidence is local in `spec/INDEX.md` and `spec/format_english/`. Mark conjectures **[guess]**; guesses cannot discharge verification.

## Code quality

**Owner: Quality Assessor.**

**What to check:** enforce stage contracts in `docs/ARCHITECTURE.md`: extraction → binary per-level spool → assembly → evaluation; deterministic bytes/manifests; canonical frame ordering; worker failure cleanup; one C binding boundary; full-disc hot loops in C, with extraction's documented exception. Check source/header cache invalidation in `parser/kiwiw/cbuild.py`, schema evidence links, and whether documentation describes implemented behavior rather than future phases.

**How to check:** inspect `parser/kiwiw/{descriptor,spool,frame_table,alldata_writer,cenc,cbuild}.py`, C sources/headers, and `parser/perf_inventory.json`. Use:

```bash
"$PY" parser/tools/lint_schema.py
"$PY" -m pytest parser/tests/test_perf_inventory.py -q
```

The lint command without `--write` checks schema and generated `UNKNOWNS.md` freshness without rewriting either. Require Design's full-suite evidence from `"$PY" -m pytest parser/tests -q -rs -s`, including `test_c_units.py`, `test_cbuild_headers.py`, `test_build_wiring.py`, boundary tests, D1 equivalence, and committed/local goldens. `test_goldens.py` actually generates windowed output; assess its evidence rather than launching a build. Inventory coverage does not prove each classification is correct. Inspect logs: older real-disc tests print `SKIP` and return, potentially appearing passed in pytest; local goldens also skip when missing.

**When to ticket:** incorrect boundaries, stale verified claims, missing negative controls, altered oracles without justified byte deltas, nondeterminism, silent fallbacks, or absent evidence. State whether a finding blocks a phase or project completion.

**What not to do:** ticket Design only; no build, merge, harness seat, opportunistic refactor, schema rewriting, or golden recapture.

## Security

**Owner: Quality Assessor.**

**What to check:** binary input boundaries and resource exhaustion across disc offsets, frame lengths/counts, recursive divided parcels, spool columns, ctypes layouts, and dump joins. Audit C integer arithmetic and buffer capacities before reads/writes. Check subprocess argument handling, compiler selection/cache behavior, scratch-path isolation, and protection of the manufacturer's reference data. The reference DVD is an offline oracle and is not redistributed (`docs/provenance.md`).

**How to check:** inspect `parser/kiwiw/{_d1.c,_k1.c,_k1_bg.c,_k1_cmp.c,_cenc.c,cenc.py,spool.py,dump_io.py}` and `parser/harness/checks/decode.py`. Verification recipes:

```bash
"$PY" -m pytest parser/tests/test_d1_frames.py parser/tests/test_harness_pointers.py parser/tests/test_dump_join_memory.py -q -rs
flock output/.heavy.lock "$PY" parser/compare_disc.py --reference "$R" --generated "$G" --checks decode,pointers --workers 1 --report "$E/security.json"
```

D1 tests include truncated and byte-corrupted golden frames; pointer tests reject non-frame targets, near-EOF reads, and `0xA5` poison. Dump-join tests cover replay-root refusal. Check complete-row length/field-layout validation before dump writes, and ensure scratch symlinks cannot defeat isolation. Review `spool_legacy.py`/`tools/convert_spool.py`: the production binary spool is documented as pickle-free; legacy pickle conversion needs trusted input. Require evidence through Design if a test needs compilation. No dedicated security scanner or sanitizer CI was found in the tracked repo.

**When to ticket:** crash, out-of-bounds access, overflow, unbounded malformed-input work, unsafe deserialization on a reachable path, overwrite of protected evidence, or undisclosed distribution of reference content. Include the smallest reproducer and exact byte offset/field.

**What not to do:** ticket Design only; no build, merge, harness seat, destructive fuzzing of originals, firmware changes, or uploading DVD binaries.

## Performance

**Owner: Quality Assessor.**

**What to check:** wall time, summed process PSS, RSS plus cgroup `memory.peak`, bounded dump windows, and invariance of bytes/counts/manifests across workers. Separate encoding, decoding/checking, and dump-finalization costs; a faster wrong result fails.

**How to check:** read `docs/WORKFLOW.md`, closed plan `05-heavy-job-memory.md`, and plan 04 `IMPLEMENTATION.md` Phase 2 signatures. K1's historical ≤120 s median-of-three gate was measured at `-j12`; signed summed-PSS ceiling is **9,726,501 kB**. Current ≤6-worker operational cap takes precedence: label that configuration difference and ticket conflicting budgets. Phase 4 signed targets are coord-scale ≤20 s, other checks ≤60 s; do not present them as already achieved.

For existing reviewed output:

```bash
flock output/.heavy.lock "$PY" parser/tools/quantisation_roundtrip.py --disc "$G/ALLDATA.KWI" --spool output/extract_timing/spool --engine c -j 6 --out "$E/k1-perf.json"
```

Read `timing`, PSS, counts, and `pass`, including exit 1. Request Design's bounded replay evidence via `flock output/.heavy.lock "$PY" parser/tools/bench_dump_memory.py triage-run --out output/scratch-5-03/triage_results.json` using fresh supported scratch destinations. Other documented modes are `finalize-run` and `s07-run`. Gates cover SHA equality, RSS/peak reduction, growth, and wall bounds. Build timing evidence comes from `parser/tools/bench_build.py` and bench-record tests; its summed RSS is not PSS. Historical ~12.2 s full-map assembly is not whole-disc generation time.

**When to ticket:** exceeded applicable gates, regressions beyond measured spread, changed outputs, per-row Python hot loops, unbounded residency, or missing attributable measurements. Finalizer memory still scales with a full kind array.

**What not to do:** ticket Design only; no build, merge, harness seat, overlapping heavy jobs, cache dropping, or metric substitution to obtain a pass.

## Functional e2e

**Owner: Quality Assessor — folded e2e verification.**

**Project-complete definition:** E2E generation matches the original DVD in every verifiable aspect; every claim / assumption / implementation is verified; every deviation has a root cause.

**What to check:** trace dated Australia PBF → spool → seven map levels → routing/search joins → all regenerated map-dependent files → metadata/coverage → UDF-bridge image ≤**4,700,000,000 bytes** → final MMCS acceptance. Account for every target-disc file, including all `IDX/` families, `HWMAP.KWI`, and `INDEXDAT.KWI`; fixtures cannot establish country-wide completion.

**How to check:** bind the reviewed disc to its manifest and source/config hashes:

```bash
flock output/.heavy.lock "$PY" parser/compare_disc.py --reference "$R" --generated "$G" --workers 1 --report "$E/parity.json"
flock output/.heavy.lock "$PY" parser/tools/quantisation_roundtrip.py --disc "$G/ALLDATA.KWI" --spool output/extract_timing/spool --engine c -j 6 --dump-failures "$E/k1-dump" --out "$E/k1.json"
```

Do not use `--no-manifest`. Review every result, all seven level populations, pointers, vocabulary, container allowlist, profile bounds, and `spot_checks.json`. `harness.json` currently declares **map only**: a green CLI is not full-disc parity. Require Design's round-trip evidence (`test_roundtrip_{alldata_full,idx_full,misc}.py`) and independent cross-file/link/state/coverage checks for the remaining packages; missing checks stay unverified.

Map every schema claim and assumption to reproducible evidence using `docs/schema/UNKNOWNS.md`, `spec/`, refdata, and provenance. For failures, run `parser/tools/k1_triage.py summary --dump "$E/k1-dump" --out "$E/summary"` under the heavy lock. Require complete-key counts, exact producer/offset witnesses, independently checked geometry, byte-gated counterfactuals, and a demonstrated source/checker/build cause. Historical classification rules need their documented side-field extensions; empty-dump handling has a recorded limitation. Consult plan 04 triage and the 3-16 outcome TSV; its 89 failed counterfactuals do not prove every possible repair impossible. Plan 07's possible “+60 non-payload unattributed, accepted” outcome still fails this stricter completion bar.

**When to ticket:** any missing evidence/file/level, unexplained delta, absent real-disc test, or unverified accepted deviation.

**What not to do:** ticket Design only; no build, merge, harness seat, tolerance/allowlist relaxation, oracle recapture, or partial-disc completion claim.

## UI

**Owner: Quality Assessor — folded UI verification; no Experience seat.**

**What to check:** generated map geometry and labels remain visually consistent with verified coordinates, frame ranges, zoom levels, vocabulary, and coverage. Check missing/misplaced names, seams at divided/integrated parcels, polygon fill errors, clipping, and content loss. The UI is the vehicle's MMCS; no tracked web frontend was found. UI graphics are among the target design's content-independent copy-through resources.

**How to check:** review `parser/refdata/{spot_checks.json,profile/coord_scale.json}`, `docs/schema/{map-frame,map-name,map-background,parameters-metadata}.md`, and evidence from:

```bash
flock output/.heavy.lock "$PY" parser/compare_disc.py --reference "$R" --generated "$G" --checks spotcheck,coord_scale,vocab --workers 1 --report "$E/ui.json"
cmp "$R/GRA256D.KWI" "$G/GRA256D.KWI"
cmp "$R/KGRA256.KWI" "$G/KGRA256.KWI"
```

Extend byte comparisons to the copy-through graphics listed in `target-disc.md`. Missing files are missing verification, not successful copying. `tools/kiwiread/out.svg` is an existing study rendering; the third-party reader has hard-coded reference paths and does not establish generated-disc rendering. `parser/tools/overlay_test.py --reference "$R/ALLDATA.KWI" --pbf australia-260824.osm.pbf --out "$E/overlay.json"` provides coordinate discrimination diagnostics under the heavy lock, not a screenshot or generated-UI proof.

[guess] A matched R/G MMCS screenshot sequence at the same locations and zoom settings would help assess visual parity; exact screen controls and capture procedures require device evidence. Request that evidence only at the documented final vehicle-acceptance stage.

**When to ticket:** visually reproducible defects backed by coordinates/frame keys, corrupted copy-through assets, unexplained clipping/trim, or unverified rendering claims. Separate old/new source content differences from processing defects.

**What not to do:** ticket Design only; no build, merge, harness seat, UI redesign, firmware editing, burn, or claiming a study SVG proves MMCS parity.

## UX

**Owner: Quality Assessor — folded UX verification; no Experience or E2E seat.**

**What to check:** useful end-to-end navigation: street/address/POI lookup resolves to the right coordinates and map links, state selection matches administrative boundaries, routing references resolve, and coverage/name selection supports the expected locations. Assess CLI usability as well: explicit input/output paths, useful failure messages, reliable exit status, and clear PASS/FAIL/N/A semantics.

**How to check:** read `docs/design/target-disc.md`, `docs/schema/{index-idx,route-planning,flags}.md`, `parser/kiwiw/link_id_registry.py`, and `parser/demo_address_search.py`. On available complete disc roots:

```bash
flock output/.heavy.lock "$PY" parser/demo_address_search.py "$R" --street 'HAY STREET' --no-full-scan
flock output/.heavy.lock "$PY" parser/demo_address_search.py "$G" --street 'HAY STREET' --no-full-scan
```

The demo exercises **WA** `SADSR201.IDX` and `POISR201.IDX`; compare returned street/range/POI coordinates and documented bounds, not just process success. It does not establish all-state generated search or routing. Require Design's `parser/tests/test_link_id_registry.py`, `test_route_planning.py`, and `test_roundtrip_idx_full.py` evidence; confirm integration joins, beyond isolated writer/round-trip tests. Review the seven-city spot-check table and require coverage of the seven state partitions defined in the target design. No complete route/search MMCS automation was found.

[guess] Final acceptance scenarios should include destination selection, route guidance, zoom transitions, unavailable destinations, and restarting with the disc inserted; derive exact expectations from original-DVD device behavior rather than inventing them. In-vehicle work remains last-mile after offline verification.

**When to ticket:** wrong destination, broken link joins/state assignment, misleading success after a skip/N/A, unclear failures, unusable documented commands, or unsupported “navigation works” claims. Missing generated search/routing evidence blocks project completion even if map checks pass.

**What not to do:** ticket Design only; no build, merge, harness seat, burn, repeated vehicle debugging, or treating a successful WA reference demo as generated Australia-wide UX proof.
