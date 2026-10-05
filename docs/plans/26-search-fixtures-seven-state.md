# WA-only search fixtures → seven-state search fixtures

Canonical seven-row state↔suffix table (`parser/refdata/state_partitions.json`),
offline synthetic search fixtures for suffixes 201–207, and parameterized unit
tests. Demo `--state`/`--suffix` with default-WA honesty. Offline fixtures ≠
WP3 complete ≠ Australia-wide MMCS proof. Phase 3 not closed.

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end
generation matches the original DVD in every aspect that can be verified, every
claim, assumption, and implementation aspect is verified and proven, and there
are no unexplained deviations — each has a root cause.

WA-only search fixtures → seven-state search fixtures (ux/e2e). Offline-runnable
preferred (synthetic/small fixtures). Land on master. No feature branch. No pull
request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06.
Do not mega-close 3-90 or claim Phase 3 closed.

## Delivered (Phase 1)

- `parser/refdata/state_partitions.json` — seven-row table (201 WA … 207 TAS)
- `parser/kiwiw/state_partitions.py` — loader + `resolve_suffix`
- `parser/tests/test_search_fixtures_seven_state.py` — table oracle + per-suffix
  synthetic `build_index` + SRMX round-trip + SADSR/POISR basename stubs
- `parser/tests/test_address_extractor.py` — WA bbox scoped to this module’s
  WA-only synthetics; non-WA fixtures owned by the seven-state module
- `parser/demo_address_search.py` — `--state` / `--suffix` (default 201 WA
  honesty note)
- Docs: `docs/schema/index-idx.md`, `docs/OVERVIEW.md` WP3 row (still Not
  started), `parser/refdata/README.md`

## Explicit non-claims

Offline seven-state fixtures ≠ WP3 complete ≠ Australia-wide MMCS proof.
No disc mount, no full-AU encode, no heavy.lock, no WP3 writers, no POISR
decoder bugfix, no Phase 3 / plan 04 P4–6 / plan 06, no 170 / 3-16 / 3-17
reseat.

## Design (archived)

# WA-only search fixtures → seven-state search fixtures

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

WA-only search fixtures → seven-state search fixtures (ux/e2e) — search-index/search tests currently only cover Western Australia (WA) fixtures; extend fixture coverage to all seven states/territories the product ships, so search behaviour is proven per state. Offline-runnable preferred (synthetic/small fixtures). Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

The product ships **seven** address/POI search partitions (`IDX/SADSR201..207`, `IDX/POISR201..207`: WA, NT, SA, QLD, NSW, VIC, TAS). Assessor UX already warns that the demo and related evidence are **WA-only** and do not establish all-state generated search. On tip that gap is still concrete:

| Surface | What it does today | Honesty / coverage gap |
| --- | --- | --- |
| `parser/demo_address_search.py` | Hardcodes `IDX/SADSR201.IDX` and `IDX/POISR201.IDX` | Successful WA demo is easy to misread as Australia-wide UX proof |
| `parser/tests/test_roundtrip_idx.py` | Round-trips structure against real-disc **SADSR201** / **POISR201** only; skips if disc unmounted | No offline proof; zero coverage of 202–207 |
| `parser/tests/test_roundtrip_idx_full.py` | Whole-file assemble/replicate of **SADSR201** only; disc-mounted | Same — WA-only, not offline |
| `parser/tests/test_address_extractor.py` | Offline synthetic `AddressPoint` list — Perth/Fremantle only; asserts WA bbox | Offline but **WA-shaped**; no per-state suffix / partition contract |
| `parser/osm_to_address_index.py` | Builds one `OsmAddressIndex`; docs/examples name `SADSR201.IDX` | No greppable seven-state suffix table; no write-per-state fixture path in tests |
| `docs/schema/index-idx.md` / `docs/design/target-disc.md` | Canonical 201–207 state partition; WP3 generate ×7; state by OSM `admin_level=4` (not bbox) | Spec is seven-way; tests are not |
| Assessor UX brief | Demo = WA; require seven state partitions + seven-city spot-check | Verbal — no offline oracle that fails when a state suffix is missing from fixtures/tests |
| Host OOM hold (`/workspace/maps-oom-2026-10-06.md`) | Heavy Maps encode/K1 on hold | Any design that needs full-AU / disc `4ed9cd80` / multi-GB IDX is blocked and out of scope |

Verified on `origin/master` at `df1f071` from committed demo / roundtrip tests / address extractor / index-idx / target-disc / OVERVIEW WP3 **Not started** / Assessor UX wording — no disc mount or full-AU encode required. Ticket is **not** already satisfied: no `SADSR202`–`207` (or POISR equivalents) appear under `parser/tests/`. Plans **01–05** and **07–23** and **25** occupy those numbers on master; `/workspace/maps-design-drafts/` has **24** (pickle quarantine, not on tip). **06** is not a work unit. This plan is **26**.

## Solution shape

One bounded offline verification package: land a **canonical seven-state partition table**, **tiny synthetic search fixtures** for every suffix **201–207**, and **parameterized unit tests** that prove the search-index path is exercised per state. Prefer synthetic bytes and in-memory/tmp trees. Do not implement WP3 OSM→IDX writers for all states. Do not mount the reference disc or load disc `4ed9cd80`. Do not claim WP3 or Phase 3 complete. Do not run heavy encode/K1 (OOM hold active).

### Domain: seven-state partition contract

- Owns: the greppable mapping from product state/territory → IDX suffix (and inverse), shared by fixtures, tests, and (optionally) the demo CLI.
- Contract: (1) A single committed table (module constant and/or tiny JSON under `parser/refdata/` — Execute picks one home) enumerates exactly seven rows: `201 WA`, `202 NT`, `203 SA`, `204 QLD`, `205 NSW`, `206 VIC`, `207 TAS`, matching `docs/schema/index-idx.md` / `target-disc.md`. (2) Unit test fails if the table length ≠ 7, if any suffix outside `201..207` appears, if any of the seven codes is missing, or if codes/abbreviations disagree with the schema row. (3) Docs (`index-idx.md` Files and state partition and/or a one-liner in OVERVIEW WP3 / `demo_address_search` docstring) point at that table as the offline source of truth for fixture naming. (4) No bbox-as-state rule is introduced as product law — target-disc already requires OSM `admin_level=4` containment for real generation; fixtures may tag each synthetic point with an explicit state code without implementing polygon containment in this plan.
- Non-goals: no OSM admin boundary loader; no ZONEZSRC/ZSEL decode; no claiming state assignment from live PBF is proven.

### Domain: offline seven-state search fixtures + parameterized tests

- Owns: synthetic/small search fixtures covering all seven suffixes, and tests that use them so search behaviour cannot silently stay WA-only.
- Contract: (1) For each of `201..207`, an offline fixture exists that is enough to exercise the search-index read/write path under test — indicative shapes: a tiny synthetic SADSR-shaped buffer (DFSR header + minimal DSIR/DCTF/matching records via existing `index_writer` helpers), and/or a per-state synthetic `AddressPoint` set that `build_index` accepts; Execute may also add empty/minimal POISR filename stubs if that keeps demo/path tests honest without fixing POISR decoder bugs. Fixtures are **small** (KiB-class or generated in tmp by the test), never multi-MB R extracts, never committed real-disc IDX. (2) At least one parameterized pytest (or equivalent) iterates **all seven** suffixes and asserts a greppable per-state outcome: e.g. fixture path/basename contains the suffix; round-trip of a written matching record (or DFSR header) succeeds; coordinates/names for that state's synthetic street resolve via the same decoder API the WA path uses; missing suffix in the fixture set fails the suite. (3) WA remains covered (201) — extending coverage must not delete the WA case. (4) `test_address_extractor`'s WA-only bbox assertion is either generalized to per-state expected bounds for synthetic points **or** replaced by an explicit state-code tag check so non-WA fixtures are not falsely forced into the WA box. (5) Optional same-phase: `demo_address_search.py` accepts a state suffix / code (default may stay 201 for back-compat) and documents that default WA ≠ all-state proof — not a disc-mount gate. (6) Docs note: offline seven-state fixtures prove **partition coverage of the search test surface**, not WP3 generation completeness and not MMCS navigation.
- Non-goals: no full-AU PBF extract; no real SADSR201..207 byte-identical replicate; no POISR decoder bugfix; no WP3 "started/complete"; no disc `4ed9cd80` dependency; no heavy memory jobs; no harness layer promotion that claims address parity under map-only.

## Decisions

1. Plan number is **26**. Standalone ux/e2e search-fixture coverage plan. It does not absorb draft 24 pickle quarantine, plan 23 copy-through cmp, plan 25 OOM RCA, or plan 15/21 SADSR NAME science.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — partition table + synthetic per-suffix fixtures + parameterized tests + light docs/demo touch).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Prefer offline synthetic/small fixtures only. No full-AU encode, no disc mount, no disc `4ed9cd80`, no multi-GB IDX as acceptance. Respect the active host OOM hold on heavy Maps jobs.
6. Reject treating a green WA-only demo or WA-only roundtrip as seven-state proof. Reject bbox-as-state as the product assignment rule. Reject implementing WP3 writers or POISR bugfixes under this plan.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must acceptance mount R and round-trip real `SADSR202`–`207` / `POISR202`–`207` bytes?
- Answer chosen: **no**. Acceptance is offline synthetic fixtures + parameterized unit tests for all seven suffixes. Optional live remount of non-WA IDX is confirmation, not a gate.
- Rationale: ticket prefers offline fixtures; OOM hold and provenance forbid heavy/disc-as-gate; partition semantics (suffix ↔ state) do not need multi-MB real files.
- If wrong: Cody orders one optional smoke when a disc is mounted; still no blob commit; still no WP3 / Phase 3 close.

### Assumption 2

- Question: do fixtures need both SADSR and POISR for every state in this plan?
- Answer chosen: **SADSR (or address-index path) required for all seven**; POISR per-state path coverage is **best-effort** (filename/partition stubs or one shared decoder smoke with seven basenames) without fixing known POISR decoder bugs.
- Rationale: Assessor demo names both families; schema marks POISR assembly/decoder as unfinished; ticket centers search fixtures and state partitions, not POISR science.
- If wrong: Cody orders minimal POISR synthetic records per state in the same phase — still no decoder bugfix claim.

### Assumption 3

- Question: must this plan implement OSM `admin_level=4` containment for state assignment?
- Answer chosen: **no**. Fixtures carry an explicit state code/suffix. Real generation's admin-boundary rule stays target-disc / WP3.
- Rationale: light offline scope; polygon containment is WP3 product work, not a fixture-coverage gate.
- If wrong: a later WP3 design owns containment + writers; this plan's per-suffix tests remain the offline oracle for partition coverage.

### Assumption 4

- Question: is extending `demo_address_search.py` required in Phase 1?
- Answer chosen: **optional but preferred** (CLI state/suffix argument + docstring honesty). Parameterized unit tests are the acceptance gate; demo change alone is insufficient.
- Rationale: Assessor recipe uses the demo; making default-WA explicit reduces false UX claims; tests carry the proof.
- If wrong: Execute ships tests+fixtures only and leaves demo hardcoded 201 with a docstring warning — still must not claim seven-state demo coverage.

### Assumption 5

- Question: may this plan mark WP3, search UX, or Phase 3 complete because seven fixtures exist?
- Answer chosen: **no**. Fixtures prove offline test coverage of the seven partitions. OVERVIEW WP3 stays **Not started** until real generation exists.
- Rationale: standing rule; OVERVIEW honesty.
- If wrong: none — still must not mega-close.

### Assumption 6

- Question: may fixtures or tests load large real IDX or run under the heavy lock as acceptance?
- Answer chosen: **no**. Keep fixtures synthetic/small; no heavy-lock encode/K1; no disc `4ed9cd80`.
- Rationale: active OOM hold; ticket is light/offline.
- If wrong: still must not clear the hold from this plan.

## Open questions

1. Exact home of the partition table (`parser/refdata/state_partitions.json` vs `kiwiw` constant) and exact pytest module name — **Execute chooses**; tests and docs must agree.
2. Whether POISR stubs are filename-only or carry a minimal synthetic record — **Execute chooses** under Assumption 2; out of bounding altitude beyond "no POISR bugfix claim".
3. When WP3 first writes all seven real IDX files, whether promoting harness `address` layer checks is a same-commit requirement — **out of scope** (owned by a WP3 design).

## Phases

### Phase 1 — Seven-state offline search fixtures exist and are test-proven

- Outcome: (1) A committed seven-row state↔suffix table matching index-idx / target-disc (201 WA … 207 TAS) is greppable and unit-tested for completeness. (2) Offline synthetic/small search fixtures exist for **every** suffix `201`–`207` (WA retained). (3) A parameterized unit test iterates all seven suffixes and proves a search-index behaviour per state (write/read or `build_index`+record round-trip / basename+decoder path — Execute picks one stack already present on tip). (4) WA-only bbox (or equivalent) assertions no longer block non-WA synthetic fixtures. (5) Docs state that offline seven-state fixtures ≠ WP3 complete and ≠ Australia-wide MMCS proof; demo default-WA honesty is documented (and CLI state/suffix is updated if Execute takes Assumption 4's preferred branch). (6) No real-disc IDX blobs committed; no full-AU encode; no disc `4ed9cd80`; no heavy-lock acceptance; no WP3 writer; no Phase 3 close; no plan 04 P4–6 / plan 06; 170 / 3-16 / 3-17 not reseated. Plan folder `docs/plans/26-search-fixtures-seven-state/` lands with this design when Execute commits.
- Surfaces: new or extended `parser/refdata/` or `parser/kiwiw/` partition table; `parser/tests/test_address_extractor.py` and/or new `parser/tests/test_search_fixtures_seven_state.py` (indicative); optional tiny fixture helpers under `parser/tests/fixtures/`; optional `parser/demo_address_search.py` state/suffix argument; short doc touches on `docs/schema/index-idx.md` and/or `docs/OVERVIEW.md` WP3 row / demo docstring. Map encode/K1/PSS/triage, plans 14/15/21/23–25 science, and POISR decoder internals are **read-only** except shared writer/decoder helpers already used by WA tests.
- Approach: known
- Depends on: master tip with `index_writer` / `search_frame` / `osm_to_address_index.build_index` and WA synthetic extractor tests (present at `df1f071`). Does **not** depend on draft 24 landing or OOM hold clearance.
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `df1f0714c7fb69bce2962aa662c14bfb0d2b304d` (“Close plan 25: OOM memory RCA + Flash peak wrapper + cell_local bounds”).
- Candidate: Maps Quality Assessor offline ticket (Quality tip `f01ed41` wave, one of eight offline tickets) — **WA-only search fixtures → seven-state search fixtures** (ux/e2e); synthetic/small fixtures preferred. Exact Assessor agent transcript text was **not** recoverable here (agent `3fca5301-…` / Design `c8207a82-…` `transcript_entries` empty; no ReadTranscript MCP in this executor). Ticket title and constraints taken from the Design-lane task brief; substance aligned with committed Assessor UX brief (`.cursor/skills/assessor-briefs/SKILL.md`): WA-only `SADSR201`/`POISR201` demo; require coverage of the seven state partitions; do not treat WA success as Australia-wide UX proof. Tip-wave siblings already drafted as NEW #1–#6 (plans/drafts 19–24).
- Evidence cited (committed): `docs/schema/index-idx.md` suffix 201–207 state partition; `docs/design/target-disc.md` SADSR/POISR generate ×7 + state by `admin_level=4`; `docs/OVERVIEW.md` WP3 **Not started**; `parser/demo_address_search.py` hardcoded 201; `parser/tests/test_roundtrip_idx.py` / `test_roundtrip_idx_full.py` SADSR201(+POISR201) disc-mounted only; `parser/tests/test_address_extractor.py` Perth/Fremantle synthetic + WA bbox; seven-city `parser/refdata/spot_checks.json`; Assessor UX brief WA warning; host OOM hold note `/workspace/maps-oom-2026-10-06.md`.
- Rejected for this design: real-disc multi-state IDX commit; full-AU / disc `4ed9cd80` acceptance; WP3 writers; POISR decoder bugfix; bbox-as-state product rule; claiming WP3 / Phase 3 / full-disc complete; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; heavy encode/K1 under OOM hold; absorbing draft 24.
- Draft format followed: `/workspace/maps-design-drafts/23-copy-through-graphics-cmp/DESIGN.md` and `/workspace/maps-design-drafts/24-quarantine-pickle-sanitizer-ci/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction. Box draft only — no commit/push.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–23, 25; `/workspace/maps-design-drafts/` has **24** (pickle) → this draft is **26**.
