---
design_id:
---

# Quarantine pickle legacy + sketch sanitizer/CI gate

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Quarantine pickle legacy + sketch sanitizer/CI gate (security). Offline-runnable preferred (fixtures/tests). Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Problem

Quality Assessor Security already names the gap: production spool is documented pickle-free, but **legacy pickle conversion needs trusted input**, and **no dedicated security scanner or sanitizer CI** exists in the tracked repo. On tip that is still true:

| Surface | What it does today | Honesty / security gap |
| --- | --- | --- |
| `parser/kiwiw/spool_legacy.py` | Four `pickle.load` call sites on `.data` / `.idx` streams | Reachable unsafe deserialization if any caller opens an untrusted path; module is only "LEGACY" by docstring |
| `parser/tools/convert_spool.py` | Imports `spool_legacy` and converts pickle → binary | No trusted-input gate; any argv path is deserialized |
| `parser/tests/test_spool_binary.py` | Builds pickle fixtures via `spool_legacy` then converts | Correct for lossless proof; also keeps pickle.load on the default pytest path without a quarantine contract |
| `parser/kiwiw/spool.py` | Binary `KWSPIDX1`; rejects non-magic idx with "legacy pickle? run convert_spool" | Production build (`build_alldata`, extractors, harness tools) correctly uses this — but nothing **proves** no new `pickle.load` lands outside legacy |
| `parser/osm_to_address_index.py` | `pickle.dump` of `OsmAddressIndex` to `address_index.pkl` | Write-only today (no in-repo `pickle.load` of that artifact); still emits pickle as the default handoff format for WP3-adjacent address work |
| `.github/` | **Absent** | Assessor ticket: no security scanner / sanitizer CI; draft **06** (full pytest+C gate) is explicitly not a work unit and must not be drawn here |
| Assessor Security brief | Recipes for D1/pointers/dump-join; flags spool_legacy/convert_spool | Verbal review only — no greppable allowlist, no gate that fails CI/local when a new `pickle.load` appears |

Verified on `origin/master` at `022a8af` from committed spool / convert_spool / address extractor / ARCHITECTURE / provenance / Assessor Security wording — no disc mount or full-AU encode required. Plans **01–05** and **07–22** occupy those numbers on master; `/workspace/maps-design-drafts/` has **23** (copy-through graphics cmp) and **25** (OOM RCA; text already soft-reserves **24** for this pickle draft); **06** is not a work unit. This plan is **24**.

## Solution shape

One bounded security package: **quarantine** every remaining pickle deserialize path behind an explicit trusted-input contract, lock an **offline allowlist oracle** so new `pickle.load`/`loads` outside quarantine fail tests, and land a **sketch** security CI workflow that runs only that oracle (plus a documented sanitizer posture). Do not implement draft/plan **06** full pytest+C PR gate. Do not productize AddressSanitizer as the default `cbuild` path. Do not delete lossless binary↔legacy conversion proofs. Do not claim Phase 3 or full-disc complete.

### Domain: pickle quarantine

- Owns: which modules may call `pickle.load` / `pickle.loads`, and under what trusted-input gate conversion or fixture code may run them.
- Contract: (1) Allowlist of files permitted to contain `pickle.load` / `pickle.loads` is exactly the quarantine set — initially `parser/kiwiw/spool_legacy.py` only (Execute may add at most one thin wrapper module under `parser/kiwiw/` or `parser/tools/` if loads move behind a single gate function; the allowlist and tests must name the same paths). (2) Every load path requires an explicit trusted-input enablement before deserialize (module-level or function-level API such as `enable_legacy_pickle_trust(reason: str)` / CLI `--i-trust-this-pickle` / env — Execute picks one mechanism); without enablement, load raises a clear error and does not call `pickle.load`. (3) `convert_spool.py` refuses to convert unless that trusted-input gate is set; help text states inputs must be operator-trusted local spools, never untrusted uploads. (4) `test_spool_binary.py` (and any other test that needs legacy) enables trust inside the test only. (5) Production build/extract/harness paths (`build_alldata`, `osm_to_parcel_geometry`, `quantisation_roundtrip`, harness checks, binary `SpoolReader`) remain import-free of `spool_legacy` and of `pickle` deserialize. (6) `osm_to_address_index.py` either keeps dump-only pickle with a module/CLI warning that the `.pkl` is lab-trusted handoff only and **must not** grow a `pickle.load` reader in-tree without a new design, **or** changes default `--out` to a non-pickle format in the same phase if Execute finds a cheap JSON/structured alternative that existing address tests already cover — do not add a load API. (7) Docs (`ARCHITECTURE` spool row / Tools row, `provenance` spool format note, short `WORKFLOW` security note) state: production spool is pickle-free; legacy pickle is quarantined; conversion needs trusted input.
- Non-goals: no rewriting binary spool format; no deleting `spool_legacy` or `convert_spool` in this plan; no migrating historical multi-GB `output/spool` trees as acceptance; no WP3 address IDX writer; no reseating plan 15/21 address science.

### Domain: sketch sanitizer / security CI gate

- Owns: the smallest offline-provable security gate and its optional Actions sketch — not the general master pytest+C gate (forbidden plan **06**).
- Contract: (1) An offline unit test (or tiny `parser/tools/` checker invoked by that test) fails if any tracked `*.py` under `parser/` contains `pickle.load` / `pickle.loads` outside the quarantine allowlist; passes on tip after quarantine. (2) Optional second assertion: production entry modules listed in a short freeze set do not import `kiwiw.spool_legacy` (or `spool_legacy`). (3) A sketch workflow under `.github/workflows/` (name indicative, e.g. `security-sketch.yml`) triggers on `push`/`pull_request` to `master` and runs **only** that allowlist/oracle test with stock setup-python — no reference disc, no full `pytest parser/tests`, no mandatory C extension build, no Perth/sha smoke. (4) `docs/WORKFLOW.md` states what this sketch gate enforces vs what stays local/heavy vs what a future full CI (not drawn here; not plan 06) would add. (5) Sanitizer posture (written in the same WORKFLOW / plan note): default `cbuild` `CFLAGS` stay `-O2 -ffp-contract=off -fPIC`; AddressSanitizer/UBSan are **not** default; this plan records them as a named follow-up sketch only (no requirement to land `-fsanitize=` product code unless Execute finds a ≤one-file opt-in that skips cleanly without clang — still not the default gate). (6) Green sketch workflow URL or local `pytest` path for the allowlist test is enough evidence; no disc mount.
- Non-goals: draft/plan **06** pytest+C+optional Perth smoke; Cursor CloudAgent as CI; storing DVD/PBF in Actions; making ASan mandatory on every commit; security fuzzing of R; claiming the Assessor Security surface (D1/pointers/dump-join) is replaced by this gate.

## Decisions

1. Plan number is **24**. Standalone security quarantine + sketch gate. It does not absorb draft 23 copy-through cmp, draft 25 OOM RCA, or draft/plan 06 CI gate.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — trust gate + allowlist test + sketch workflow + docs).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Prefer offline allowlist tests and synthetic legacy fixtures already used by `test_spool_binary`. No full-AU / disc mount as acceptance.
6. Reject deleting legacy conversion without a replacement lossless proof. Reject silent `pickle.load` on arbitrary paths. Reject implementing the full master pytest CI under this plan number or as plan 06.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must acceptance run AddressSanitizer builds of `_cenc` / `ctest` on every commit?
- Answer chosen: **no**. Acceptance is quarantine + allowlist oracle (+ sketch Actions that run the oracle). ASan/UBSan stay a documented follow-up sketch, not default `cbuild`.
- Rationale: ticket says **sketch** sanitizer/CI gate; Assessor flags missing scanner/CI and trusted pickle input — both closed by allowlist + trust gate offline; ASan needs toolchain matrix and is easy to conflate with forbidden plan 06 scope.
- If wrong: Cody orders a later plan for opt-in `-fsanitize=address` on `ctest` only; still no plan 06; still no Phase 3 close.

### Assumption 2

- Question: delete `spool_legacy.py` / `convert_spool.py` now that binary spool is production?
- Answer chosen: **no**. Quarantine and trust-gate them; keep `test_spool_binary` lossless proof.
- Rationale: plan 02 and provenance still name one-time conversion; Assessor asks trusted input, not deletion; removing the oracle loses the binary↔legacy equality proof.
- If wrong: a later plan can retire legacy after Cody confirms no remaining pickle spools and relocates the lossless test.

### Assumption 3

- Question: must `osm_to_address_index.py` stop writing `.pkl` in this plan?
- Answer chosen: **prefer warn + no-load contract**; format migration only if Execute finds a cheap drop-in already covered by `test_address_extractor` without WP3 scope creep.
- Rationale: tip has dump only (no `pickle.load` of address pkl); deserialize risk is latent; ticket centers spool_legacy/convert_spool and missing security CI.
- If wrong: Cody orders JSON (or similar) default `--out` in the same phase; still no pickle.load reader; still no WP3 claim.

### Assumption 4

- Question: is the sketch Actions workflow the same as draft 06 CI gate?
- Answer chosen: **no**. Sketch runs only the pickle-allowlist/security oracle. Full `pytest parser/tests` + C build + optional Perth smoke stays undrawn (plan 06 forbidden).
- Rationale: user constraint and standing "06 is not a work unit"; first `.github/` file is allowed if its contract is security-sketch-only and WORKFLOW says so.
- If wrong: Cody defers Actions entirely and accepts local allowlist pytest alone as Phase 1 evidence; do not expand the workflow into plan 06.

### Assumption 5

- Question: may this plan claim Assessor Security complete, Phase 3 closed, or full-disc done because pickle is quarantined?
- Answer chosen: **no**. Quarantine closes the unsafe-deserialize / missing-sketch-CI ticket slice only. D1/pointers/dump-join recipes and map parity blockers unchanged.
- Rationale: standing rule; OVERVIEW / plan 04 Phase 3 state unchanged.
- If wrong: none — still must not mega-close.

### Assumption 6

- Question: trust-gate mechanism — env var, CLI flag, or Python API?
- Answer chosen: **Execute picks one**; must be explicit, off by default, named in help/docstring, and required by both `convert_spool` and any test that loads pickle.
- Rationale: bounding altitude; all three satisfy "trusted input"; brief cites the chosen name.
- If wrong: rename in the same phase; do not leave an ungated load path.

## Open questions

1. Exact trust API name and whether loads stay inside `spool_legacy.py` or move to one wrapper — **Execute chooses**; allowlist + tests must agree.
2. Whether a future full master CI (pytest+C) should be a new NN after Cody lifts the plan-06 ban — **out of scope**; this plan must not draw it.
3. Opt-in ASan for `ctest` as its own later design vs a tiny same-phase skip-gated sketch — default **later**; same-phase only if ≤one-file and non-default.

## Phases

### Phase 1 — Pickle quarantine + allowlist oracle + security-sketch CI

- Outcome: (1) No `pickle.load` / `pickle.loads` remains callable on the convert/test path without an explicit trusted-input enablement; without enablement, attempts fail with a clear error. (2) An offline unit test fails if any `parser/**/*.py` outside the quarantine allowlist contains `pickle.load` / `pickle.loads`, and passes on the quarantined tree. (3) Production build/extract/harness modules still do not import `spool_legacy`. (4) `convert_spool` help/docs and ARCHITECTURE/provenance/WORKFLOW state trusted-input + pickle-free production spool. (5) A sketch `.github/workflows/` job runs only that allowlist/oracle test on push/PR to `master` (or, if Actions is deferred per Assumption 4 correction, local pytest of the oracle alone is the recorded gate — WORKFLOW must match). (6) Default `cbuild` flags unchanged; ASan not mandatory. (7) `test_spool_binary` still proves binary↔legacy lossless under trust enablement. No real DVD/PBF in CI. No plan 06 full pytest+C. No Phase 3 close. No plan 04 P4–6. 170 / 3-16 / 3-17 not reseated. Plan folder `docs/plans/24-quarantine-pickle-sanitizer-ci/` lands with this design when Execute commits.
- Surfaces: `parser/kiwiw/spool_legacy.py`; `parser/tools/convert_spool.py`; optional thin quarantine helper; `parser/tests/test_spool_binary.py` and new `parser/tests/test_pickle_quarantine.py` (indicative); optional `parser/osm_to_address_index.py` warn/default-out touch; `.github/workflows/security-sketch.yml` (indicative); short docs on `docs/ARCHITECTURE.md`, `docs/provenance.md`, `docs/WORKFLOW.md`. Map encode/K1/PSS/triage/harness map checks and plans 14/20–23/25 science are **read-only**.
- Approach: known
- Depends on: master tip with binary spool production path and legacy module present (present at `022a8af`). Does **not** depend on drafts 23 or 25 landing.
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `022a8af63c7a79c40e642214d663c32221a0ca0d` (“Close out plan 20: collapse PSS ops-cap reconcile record”).
- Candidate: Maps Quality Assessor NEW #6 — Quarantine pickle legacy + sketch sanitizer/CI gate (security); offline fixtures/tests preferred.
- Evidence cited (committed): `parser/kiwiw/spool_legacy.py` four `pickle.load` sites; `parser/tools/convert_spool.py` ungated legacy read; `parser/kiwiw/spool.py` binary magic + legacy hint; `parser/osm_to_address_index.py` `pickle.dump` default `--out`; production imports use `kiwiw.spool` only; `docs/ARCHITECTURE.md` spool “no pickle”; `docs/provenance.md` plan-02 pickle→binary conversion note; Assessor Security skill: trusted input for legacy conversion; no security scanner/sanitizer CI; no `.github/` on tip; draft `06-ci-gate` exists only under `/workspace/maps-design-drafts/` and must not be drawn.
- Rejected for this design: deleting legacy spool without replacement proof; ungated pickle.load; full plan 06 pytest+C(+Perth) gate; mandatory ASan default cbuild; disc/PBF in Actions; claiming Assessor Security / Phase 3 / full-disc complete; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; absorbing drafts 23/25.
- Draft format followed: `/workspace/maps-design-drafts/23-copy-through-graphics-cmp/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–22; `/workspace/maps-design-drafts/` has **23** (copy-through) and **25** (OOM RCA; soft-reserves 24 for pickle) → this draft is **24**.
