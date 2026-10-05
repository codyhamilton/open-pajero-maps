---
design_id:
---

# Copy-through graphics cmp contracts (GRA256D/KGRA256…)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Copy-through graphics cmp contracts GRA256D/KGRA256… (ui) — byte-identical R↔G contracts for target-disc copy-through resources; missing files are missing verification, not successful copying. Offline-runnable preferred (fixtures/tests). Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

`docs/design/target-disc.md` lists ten content-independent files as **copy** (WP5): `LOADING.KWI`, `DICVCE56.KWI`, `GRA256D.KWI`, `KGRA256.KWI`, `PCT256D.KWI`, `KPCT256.KWI`, `PCT2DAT.KWI`, `KPCT2DT.KWI`, `KGRPDAT.KWI`, `VAR256D.KWI`. Schema and OVERVIEW agree they are firmware / voice / UI graphics carried unchanged from R. The Quality Assessor UI brief verifies that policy with:

```bash
cmp "$R/GRA256D.KWI" "$G/GRA256D.KWI"
cmp "$R/KGRA256.KWI" "$G/KGRA256.KWI"
```

and says to extend byte comparisons to the full copy-through list; **missing files are missing verification, not successful copying**.

Today nothing in the offline oracle enforces that:

| Surface | What it does today | Honesty gap |
| --- | --- | --- |
| `compare_disc.py` `_resolve_alldata_path` | Disc root → `…/ALLDATA.KWI` only; sibling roots discarded | Harness cannot see `GRA256D.KWI` next to ALLDATA |
| `parser/harness/checks/*` | Every registered check is `layer="map"` and ALLDATA-scoped | Zero copy-through sibling cmp rows |
| `mht29` | Byte-identical contract for the **in-ALLDATA** record-29 frame | Precedent for copy-through identity; does **not** cover root K/D/LOADING/DICVCE files |
| `parser/tests/test_roundtrip_misc.py` | Round-trips regenerated small files (PCT2MNG, COUNTRY, …) | Does not assert G siblings equal R for the copy list |
| WP5 (`docs/OVERVIEW.md`) | **Not started** | No copy writer yet — and no FAIL when G omits the files |
| Assessor UI recipe | External `cmp` | Not in harness report; easy to skip; silence looks like success |

Verified on `origin/master` at `893a846` from committed target-disc / schema / harness / OVERVIEW / Assessor UI wording — no disc mount or real GRA blobs required. Plans **01–05** and **07–21** occupy those numbers on master; draft **22** (harness map-only honesty) exists only under `/workspace/maps-design-drafts/` and is not on tip. **06** is not a work unit. This plan is **23**.

## Solution shape

One bounded verification package: register **byte-identical cmp contracts** for the ten target-disc copy files, preserve **disc roots** so sibling paths resolve, and lock PASS / FAIL / NA / missing semantics with **synthetic offline fixtures**. Do not implement WP5 copy writers, UDF burn, or image decode. Do not commit reference-disc binary payloads. Do not add the new layer to default `layers_present` (map-only remains map-only).

### Domain: disc-root awareness

- Owns: how the harness knows the directory that should contain copy-through siblings when CLI is given a disc root or an `ALLDATA.KWI` path.
- Contract: (1) Context (or equivalent) exposes `reference_root` and `generated_root` as the parent directory of the resolved ALLDATA path when the basename is `ALLDATA.KWI`, else NA-capable absence when a bare file path has no sibling meaning. (2) CLI still accepts disc root or ALLDATA path as today; resolving ALLDATA must not erase the root. (3) Unit tests construct tiny tmp disc trees (`R/ALLDATA.KWI` + stub siblings; `G/…`) without real DVD bytes.
- Non-goals: no change to manifest binding of ALLDATA sha256; no ISO/UDF walk; no inventing roots when only a lone ALLDATA path is supplied without a parent disc layout (Execute may treat parent-of-ALLDATA as root when basename matches — that is the intended disc-dir case).

### Domain: copy-through graphics cmp contracts

- Owns: discoverable harness check(s) that implement Assessor `cmp` for the target-disc **copy** row.
- Contract: (1) Stable greppable check id(s) (e.g. `copy_through_graphics` — Execute may refine) with `layer` **not** in today's `layers_present=["map"]` (suggested token: `meta` or `copy`, aligned with draft 22 / WP5 if that draft lands; Execute picks one string and docs/tests agree). (2) Canonical file list equals target-disc line 81 (ten names above); each basename compared as `reference_root/NAME` vs `generated_root/NAME`. (3) When the layer **is** present: every listed file must exist on both roots and be **byte-identical**; missing on G (or R when R root is required) → **FAIL** with the basename named; size or content mismatch → **FAIL** with basename + first differing offset or size pair; all ten identical → **PASS**. (4) When the layer is **absent** (default map-only config) → **NA** via existing `ctx.layer_present` gate (not PASS). (5) When reference is omitted and the check needs R → **NA** or FAIL per the same pattern as other R-requiring checks (Execute matches `container`/`mht29` precedent; must not PASS). (6) Unit tests lock: discover includes the check; under `layers_present=["map"]` status is NA; under layer present + identical stubs → PASS; missing G file → FAIL; one-byte mutate → FAIL; report details name failing basenames. (7) Docs (`parameters-metadata.md` copy-through section and/or OVERVIEW / target-disc Evaluation one-liner) state that missing copy-through files are FAIL when the layer is in scope, never silent success.
- Non-goals: no pixel/palette decode of GRA/PCT frames; no LOADING module disassembly; no writing/copying the ten files into G (WP5); no adding non-map entries to default `harness.json` `layers_present`; no `COVERAGE/AUC.BMP` (different target-disc rule); no HWMAP (regenerate / WP4); no claiming WP5 or Phase 3 started/closed.

## Decisions

1. Plan number is **23**. Standalone UI/verification contract plan for copy-through siblings. It does not absorb draft/plan 22 harness map-only honesty, plan 21 NAME content, or plan 20 PSS ops-cap.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — disc roots + sibling byte-cmp check + synthetic fixtures + docs).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Prefer offline synthetic disc trees and unit tests. No full-AU encode, no real GRA/LOADING blob commit, no disc mount as acceptance.
6. Reject treating absent G siblings as PASS. Reject putting these checks on `layer="map"` so map-only green silently implies graphics copy. Reject implementing the WP5 copy pipeline in this plan.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must acceptance `cmp` real mounted R/G `GRA256D.KWI` / `KGRA256.KWI` blobs?
- Answer chosen: **no**. Acceptance is unit tests over synthetic tiny stubs plus docs/harness contract. Optional live `cmp` when discs are mounted is confirmation, not a gate.
- Rationale: ticket prefers offline fixtures/tests; provenance forbids redistributing reference payloads; contract semantics (missing / mismatch / identical) do not need multi-megabyte fixtures.
- If wrong: Cody orders one optional smoke on an existing R/G pair; still no blob commit; still no Phase 3 close.

### Assumption 2

- Question: which filenames are in the contract — GRA/KGRA only, the eight image/key files, or the full target-disc copy row of ten?
- Answer chosen: **full ten** from target-disc.md line 81 (LOADING, DICVCE56, GRA256D, KGRA256, PCT256D, KPCT256, PCT2DAT, KPCT2DT, KGRPDAT, VAR256D).
- Rationale: Assessor says extend byte comparisons to the copy-through list in target-disc; missing any listed copy file is missing verification; one list avoids a second plan for firmware/voice siblings that share the same policy row.
- If wrong: Cody narrows to the eight image/key names; LOADING/DICVCE become a follow-up under the same layer — do not silently drop FAIL for the eight.

### Assumption 3

- Question: under default `layers_present=["map"]`, should missing G graphics FAIL the default discover run?
- Answer chosen: **no** — check layer is absent from map-only config → **NA**. FAIL missing/mismatch only when the layer is present (tests force that). Do not add the layer to default `harness.json` in this plan.
- Rationale: WP5 is Not started; map-only green must stay possible for map iteration (same honesty posture as draft 22). Visibility of NA (and unit-tested FAIL paths) is the contract; inventing a present layer without copy writers would be a false claim.
- If wrong: Cody promotes the layer into `layers_present` only together with a real copy step (WP5 or a thin copy helper) in a later plan.

### Assumption 4

- Question: implement copying the ten files from R into G here?
- Answer chosen: **no**. Contracts and harness/tests only. Copy writers stay WP5.
- Rationale: ticket is cmp **contracts** (ui verification), not disc authoring; OVERVIEW WP5 Not started.
- If wrong: a later WP5 design owns copy + promoting the layer; this plan's check bodies stay the acceptance oracle.

### Assumption 5

- Question: how does this plan relate to draft 22's WP5 N/A sentinel?
- Answer chosen: **independent**. If draft 22 lands a `wp5_meta` (or similar) NA-only sentinel first, Execute may replace or subsume that sentinel with this plan's real cmp check on the same layer token rather than leaving two WP5 rows. If 22 has not landed, this plan does not wait on it and does not re-draw map-only scope honesty.
- Rationale: different tickets (e2e scope honesty vs UI copy-through cmp); shared layer vocabulary is coordination, not a hard depends-on.
- If wrong: Cody orders an explicit merge note in Execute; still no Phase 3 close.

### Assumption 6

- Question: may this plan mark WP5, UI graphics, or Phase 3 complete because cmp contracts exist?
- Answer chosen: **no**. Contracts without copy writers and without layer present in default config do not prove G carries R graphics.
- Rationale: standing rule; OVERVIEW WP5 Not started remains true.
- If wrong: none — still must not claim WP5 / Phase 3 / full-disc done.

## Open questions

1. Exact layer token (`meta` vs `copy` vs draft-22 `meta`) and exact check id string — **Execute chooses**; tests and docs must agree; out of bounding altitude beyond "not `map`".
2. When WP5 first copies the ten files, is promoting the layer into `layers_present` + build manifest a same-commit requirement? **Out of scope** — owned by the WP5 design; this plan only requires today's NA under map-only and FAIL/PASS under forced layer in tests.

## Phases

### Phase 1 — Copy-through sibling cmp contracts exist and are fixture-proven

- Outcome: Harness discovers at least one new check covering the ten target-disc copy basenames. Default `layers_present=["map"]` yields **NA** for that check (not PASS). With the check's layer present in a test config and synthetic R/G disc roots: identical stubs → **PASS**; missing G basename → **FAIL** naming the file; content or size mismatch → **FAIL**. Disc-root resolution preserves sibling directories for those paths. Unit tests lock discover + NA + PASS + missing-FAIL + mismatch-FAIL. Docs state missing copy-through files are not successful copying when the layer is in scope. No real R graphics/LOADING blobs committed. No WP5 copy writer. Default `harness.json` `layers_present` stays `["map"]`. No Phase 3 close. No plan 04 P4–6 / plan 06. 170 / 3-16 / 3-17 not reseated. No disc mount required for acceptance. Plan folder `docs/plans/23-copy-through-graphics-cmp/` lands with this design when Execute commits.
- Surfaces: `parser/compare_disc.py` and/or `parser/harness/context.py` (disc-root fields); new `parser/harness/checks/` module (or extension) for copy-through cmp; `parser/tests/test_harness_*.py` (new or extended); short doc touch on `docs/schema/parameters-metadata.md` and/or `docs/OVERVIEW.md` / `docs/design/target-disc.md` Evaluation. Map check bodies, K1/PSS, triage, encode, IDX writers, and plans 14/20/21/22 science are **read-only** except optional layer-token alignment with draft 22 if it already landed.
- Approach: known
- Depends on: master tip with map-only harness, target-disc copy row, and mht29 byte-identical precedent (present at `893a846`). Does **not** depend on draft 22 landing.
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `893a84606aaa117935fd73729f6c5dd778007222` (“docs: add plan 21 R empty NAME vs G street.name design”).
- Candidate: Maps Quality Assessor NEW #5 — Copy-through graphics cmp contracts GRA256D/KGRA256… (ui); missing files ≠ successful copying; offline fixtures/tests preferred.
- Evidence cited (committed): `docs/design/target-disc.md` file table copy row (ten names, WP5); `docs/schema/disc-layout.md` copy-through vs regenerate policy; `docs/schema/parameters-metadata.md` LOADING / K/D copy-through rows (unknown internals, copied whole); `docs/OVERVIEW.md` WP5 **Not started**; `parser/compare_disc.py` resolves disc root → ALLDATA only; every current `Check(..., layer="map")`; `mht29` in-ALLDATA byte-identical precedent; Assessor UI brief: `cmp` GRA256D/KGRA256 and extend to target-disc copy-through list; missing = missing verification.
- Rejected for this design: committing real R GRA/LOADING blobs; implementing WP5 copy/UDF/burn; adding non-map layers to default `layers_present`; FAIL-on-absent under map-only default discover; decoding image/voice payloads; absorbing draft 22 map-only honesty; claiming WP5 / Phase 3 / full-disc complete; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06.
- Draft format followed: `/workspace/maps-design-drafts/22-harness-map-only-honesty/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–21; `/workspace/maps-design-drafts/` has through **22** (harness map-only honesty, not on tip) → this draft is **23**.
