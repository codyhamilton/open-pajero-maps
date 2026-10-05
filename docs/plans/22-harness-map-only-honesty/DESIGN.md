---
design_id:
---

# Harness map-only honesty + WP2–WP5 N/A negative controls

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Harness map-only honesty + WP2–WP5 N/A negative controls (e2e) — green CLI ≠ full-disc parity. Offline-runnable preferred (docs/tests/harness flags). Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

The offline oracle CLI (`parser/compare_disc.py` over `parser/harness/`) is the e2e surface Quality and workers read when they say "parity." Today it is **map-layer scoped** and that scope is easy to miss:

| Surface | What it does today | Honesty gap |
| --- | --- | --- |
| `parser/refdata/harness.json` | `"layers_present": ["map"]` | Correct but silent — no report banner that map-only ≠ full disc |
| `parser/build_alldata.py` `LAYERS_PRESENT` | Manifest writes `["map"]` only | Matches config; still no reader-facing claim bound |
| `parser/harness/checks/*.py` | Every registered `Check` has `layer="map"` | Default discover list has **zero** WP2–WP5 rows; absent layers never appear as NA |
| `compare_disc.py` exit | `0` iff no `FAIL` (PASS and NA both OK) | Green exit with only map checks looks like "disc parity done" |
| `docs/OVERVIEW.md` | WP2–WP5 rows say **Not started** | Program table is honest; the harness report is not joined to it |
| Assessor brief (Functional e2e) | Already warns: harness declares **map only**; green CLI is not full-disc parity | Verbal rule only — not enforced in CLI/report/tests |

`target-disc.md`'s Evaluation section already defines checks (cross-file consistency, capacity, round-trip, IDX/search/route) that WP2–WP5 must eventually pass. Those packages are **not started** (OVERVIEW). Leaving them off the discover list means a green map-only run has no negative control: nothing in the PASS/FAIL/NA table says "route / address / remaining IDX / metadata+image were not evaluated." That is an unexplained completeness claim by omission — the standing rule forbids it.

Verified on `origin/master` at `893a846` from committed harness CLI / config / OVERVIEW / target-disc / assessor brief wording — no disc mount or full-AU encode required. Plans **01–05** and **07–21** occupy those numbers on master (21 = R empty NAME vs G street.name design folder); **06** is not a work unit. This plan is **22**.

## Solution shape

One bounded honesty package: make every default harness run **declare map-only scope**, and register **WP2–WP5 N/A negative-control checks** so absent packages appear as NA (never PASS, never silent). Prefer docs + harness flags + unit tests. Do not implement real WP2–WP5 parity science. Do not change exit-0 meaning for map-layer PASS. Do not claim full-disc or Phase 3 done.

### Domain: map-only scope honesty

- Owns: how CLI, JSON report, and stable docs state that a green map-only run is not full-disc parity.
- Contract: (1) When `layers_present == ["map"]` (current default config and build manifest), the JSON report carries explicit scope fields — at minimum `layers_present` (echoed from config), a scope label equivalent to **map-only**, and a boolean or equivalent stating **full-disc parity is not claimed** (`full_disc_parity: false` or same meaning). (2) Human-readable output (table footer and/or stderr line after the PASS/FAIL/NA table) states that scope and that exit 0 under map-only is not full-disc parity. (3) `compare_disc.py` module docstring (and a short OVERVIEW and/or ARCHITECTURE / `target-disc.md` Evaluation touch if still silent) state the same rule in prose, matching the Assessor Functional-e2e warning. (4) Exit code stays **0** when every map check is PASS and WP NA controls are NA (no FAIL) — honesty is visibility, not turning map-only green into red.
- Non-goals: no change to PSS / K1 / 3-90 gates; no `--no-manifest` relaxation; no raising `layers_present` to invent non-map layers; no full-AU encode as acceptance.

### Domain: WP2–WP5 N/A negative controls

- Owns: discoverable harness rows that prove WP2–WP5 were considered and marked not applicable while those packages are not started.
- Contract: (1) Four registered checks (ids stable and greppable, e.g. `wp2_route`, `wp3_address`, `wp4_index`, `wp5_meta` — exact ids Execute may refine) with `layer` values **not** in today's `layers_present` (suggested layer tokens: `route`, `address`, `index`, `meta`, aligned with harness `__init__` / build comments about route-planning / index / metadata). (2) Under default `harness.json`, each appears in the default discover run as **NA** (via existing `ctx.layer_present` gate and/or an explicit NA run body whose message names the WP and "not started"). (3) Unit tests lock: all four are discovered; with `layers_present=["map"]` each status is NA not PASS/FAIL; report JSON includes them; a synthetic all-PASS map check set plus these four still exits 0 and still carries `full_disc_parity: false` (or equivalent). (4) When a future WP lands and adds its layer to `layers_present`, that control flips from auto-NA to runnable — this plan does **not** implement the real check body beyond the NA/not-started contract.
- Non-goals: no real route-planning / SADSR / POI / HWMAP / UDF-image decode or compare; no starting WP2–WP5 work packages; no reseating plan 15/21 address content; no claiming OVERVIEW WP rows "started."

## Decisions

1. Plan number is **22**. Standalone harness honesty / e2e visibility plan. It does not absorb draft or plan 21 NAME content work, plan 20 PSS ops-cap, or plan 14 completeness science.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — report scope fields + sentinel NA checks + docs/tests).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Prefer offline docs / harness flags / unit tests. No full-AU / disc mount as acceptance.
6. Reject changing exit 0 → non-zero solely because WP2–WP5 are NA (that would break honest map-layer CI). Reject leaving WP2–WP5 off the discover list while only documenting the warning in OVERVIEW.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must acceptance include a live full-disc `compare_disc.py` against mounted R/G?
- Answer chosen: **no**. Acceptance is unit tests + docs/CLI/report contract under default `layers_present=["map"]`. Optional live smoke is confirmation, not a gate.
- Rationale: ticket prefers offline docs/tests/harness flags; the defect is missing NA rows and missing scope claim, both provable without AU bytes.
- If wrong: Cody orders a one-shot smoke on an existing G with `--no-manifest` forbidden still; still no encode; still no Phase 3 close.

### Assumption 2

- Question: should exit code become non-zero while WP2–WP5 remain NA, so "green" cannot happen until full disc?
- Answer chosen: **no**. Keep exit 0 when no FAIL. Force visibility (report fields + NA rows + footer/docs) so green cannot be *read* as full-disc parity.
- Rationale: ticket text is "green CLI ≠ full-disc parity" (honesty of interpretation), not "forbid green until WP5." Map-layer iteration would otherwise be impossible under standing WORKFLOW.
- If wrong: Cody redefines exit policy in a follow-up; do not silently FAIL the NA controls.

### Assumption 3

- Question: what layer tokens and check ids name the four controls?
- Answer chosen: layers **`route` / `address` / `index` / `meta`** mapped to WP2–WP5; check ids prefixed `wp2_`…`wp5_` (Execute may pick exact strings if tests and docs agree). Messages must name the WP and that the package is not started / layer absent.
- Rationale: matches harness package comment (route-planning / index / metadata) and OVERVIEW WP table; keeps `map` as the only present layer.
- If wrong: Cody renames tokens in the same phase; do not invent extra layers in `layers_present`.

### Assumption 4

- Question: implement real cross-file / IDX / capacity checks for WP2–WP5 now?
- Answer chosen: **no**. Negative controls only. Real check bodies wait for those work packages' own designs.
- Rationale: OVERVIEW says WP2–WP5 not started; ticket asks N/A controls where not started, not to start them.
- If wrong: a later plan adds real checks and promotes the matching layer into `layers_present` + build manifest together.

### Assumption 5

- Question: may this plan mark WP1 map parity, Phase 3, or full-disc complete because the harness is now "honest"?
- Answer chosen: **no**. Honesty about scope is not map-layer PASS and not program completion. Envelope / completeness / 3-90 blockers stay as they are.
- Rationale: standing rule and ticket forbid mega-close; OVERVIEW WP1 unfinished and Phase 3 blocked remain true.
- If wrong: none — still must not claim Phase 3 or full-disc done.

## Open questions

1. When WP2 first lands, should the `wp2_route` sentinel be deleted, replaced by real checks, or kept as a parent row? **Out of scope** — owned by the future WP2 design; this plan only requires today's NA behaviour under map-only config.
2. Should `layers_present` eventually be validated against the build manifest's `layers_present` on every run (hard refuse on mismatch)? **Optional same-phase if cheap**; not required for acceptance if report already echoes config and tests lock the default. A hard refuse is a follow-up if Cody wants binding enforcement beyond today's manifest hash bind.

## Phases

### Phase 1 — Map-only scope declared; WP2–WP5 appear as NA

- Outcome: Default `compare_disc.py` discover includes four WP2–WP5 negative-control checks whose layers are absent from `layers_present=["map"]`. Under that config each reports **NA** (not PASS). JSON report records `layers_present`, map-only scope, and `full_disc_parity: false` (or equivalent). Printed output states that exit 0 under map-only is not full-disc parity. Unit tests lock discover + NA statuses + report honesty fields + exit 0 with NA controls present. Docstring / OVERVIEW (and ARCHITECTURE or `target-disc.md` Evaluation if still silent after OVERVIEW) state the same rule. `layers_present` stays `["map"]` in `harness.json` and build `LAYERS_PRESENT`. No real WP2–WP5 compare logic. No exit-policy flip to fail-on-NA. No Phase 3 close. No plan 04 P4–6 / plan 06. 170 / 3-16 / 3-17 not reseated. No full-AU / disc mount required for acceptance. Plan folder `docs/plans/22-harness-map-only-honesty/` lands with this design when Execute commits.
- Surfaces: `parser/compare_disc.py` (docstring + report/footer honesty); `parser/harness/report.py` (JSON scope fields); new `parser/harness/checks/` module for WP2–WP5 NA controls (or equivalent registry addition); `parser/tests/test_harness_*.py` (new or extended); `docs/OVERVIEW.md` (harness / WP honesty sentence); optional `docs/ARCHITECTURE.md` Evaluation one-liner and/or `docs/design/target-disc.md` Evaluation note; optional `parser/refdata/harness.json` comment or adjacent documented layer token list. Map check bodies, K1/PSS, triage, encode, IDX writers, and plan 14/20/21 science are **read-only**.
- Approach: known
- Depends on: master tip with harness `layers_present=["map"]`, map-only check registry, and OVERVIEW WP2–WP5 "Not started" (present at `893a846`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `893a84606aaa117935fd73729f6c5dd778007222` (“docs: add plan 21 R empty NAME vs G street.name design”).
- Candidate: Maps Quality Assessor NEW #4 — Harness map-only honesty + WP2–WP5 N/A negative controls (e2e); green CLI ≠ full-disc parity; offline docs/tests/harness flags preferred.
- Evidence cited (committed): `parser/refdata/harness.json` `"layers_present": ["map"]`; `parser/build_alldata.py` `LAYERS_PRESENT = ["map"]` + manifest echo; `parser/compare_disc.py` exit `0` iff no FAIL, docstring scoped to `ALLDATA.KWI`; `parser/harness/context.py` `layer_present` → NA path; every current `Check(..., layer="map")`; no WP2–WP5 check modules; `docs/OVERVIEW.md` WP2–WP5 **Not started**; `docs/design/target-disc.md` Evaluation (PASS/FAIL/N/A; applicability when package/plan + config say so) and file table owning route/IDX/meta under WP2–WP5; Assessor Functional e2e brief: harness declares map only — green CLI is not full-disc parity; missing checks stay unverified.
- Rejected for this design: failing the run solely because WP NA rows exist; implementing real WP2–WP5 parity checks; adding non-map entries to `layers_present` without generators; claiming Phase 3 / full-disc / WP1 map parity complete; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; absorbing plan 20 PSS or plan 21 NAME scope; full-AU as acceptance.
- Draft format followed: `/workspace/maps-design-drafts/20-reconcile-pss-ops-cap/DESIGN.md` and `/workspace/maps-design-drafts/21-r-empty-name-vs-g-street-name/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–21 (21 = empty-NAME design folder); `/workspace/maps-design-drafts/` has through 21 → this draft is **22**.
