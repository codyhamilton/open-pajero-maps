# R empty NAME vs G street.name (SADSR SRMX)

Plan-15 Open Q1 follow-up closed: G keeps SRMX STFG `0x7f00` (NAME **present**) and emits empty NAME content to match the R-dominant pattern. KYCH stays `street.name`. Plan 15 Assumption 2 (NAME = KYCH) is retired. No new disc bytes.

## Intent

User request, verbatim:

> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Plan-15 follow-up: R empty NAME vs G street.name (ux/e2e) — SADSR201 0/38120 non-empty NAME on R. Plan 15 made G emit STFG 0x7f00 + NAME (street.name). R evidence may show empty NAME on the dominant population. Reconcile honestly without inventing disc bytes. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed.

## Why This Existed

Plan 15 closed the STFG **presence** defect (`0x7f00` + NAME key) but left NAME **content** on Assumption 2 (`NAME = KYCH = street.name`). Committed residual and the historical Phase 2 probe (0/38,120 non-empty NAME on SADSR201) already contradicted that content rule. Leaving non-empty NAME while R carries empty VRBL CH was an unexplained G≠R deviation on the search/UX path.

## What Was Built

**Changed:** `parser/osm_to_address_index.py` (`street_to_srmx_dict`), `parser/tests/test_address_extractor.py`, `docs/schema/flags.md`, `docs/schema/index-idx.md` (one-liner). Design: `893a846`. Phase 1: `0694b9e`.

### Phase 1 — empty NAME under retained `0x7f00`

- Emission: `STFG == [0x7f, 0x00]`, `"KYCH": street.name`, `"NAME": ""`. Docstring retires Assumption 2; cites plan 15 residual / this plan.
- Tests: `test_srmx_dict_has_required_keys`, `test_stfg_bits_correct_for_srmx`, `test_srmx_record_roundtrip_bit6_name` expect empty NAME, key present, bit 6 set, KYCH = street name; fail if NAME equals a non-empty street under `7f00`.
- Schema: `flags.md` splits presence (`0x7f00`) vs content (empty NAME on dominant SADSR201; G emits empty). `index-idx.md` STFG row notes bit 6 = present (value may be empty).
- Offline evidence note (collapsed into this record): plan 15 residual + historical 0/38,120 probe; no remount; no invented hex.
- Gate: `PYTHONPATH=parser` pytest `parser/tests/test_address_extractor.py` → **33 passed**.

No STFG regression to `0x3f00`. No ALLDATA encode. No Phase 3 / WP3 close. 170 / 3-16 / 3-17 not reseated. SRHA/POISR/ITSSR untouched.

## Deviations

None material. Executor implemented Phase 1 directly (bounded edit) rather than spawning OpenCode DeepSeek Flash. Worktree stayed detached on advancing `origin/master` (master branch held by another worktree); DESIGN was already on tip before Phase 1. No `.venv-rp` created in this worktree (used shared main-checkout venv). `output/scratch-3-11/G_new` not present here / not touched.

## Review

Terminal review deferred as pipeline-style on master push (Maps lands straight to master). Outcome verified by unit tests + schema wording against Phase 1 contract.

## QA

Not applicable (no disc remount / deploy). Unit tests only.

## Residual Risks

1. SADSR202–207 full NAME emptiness beyond first-record samples remains Open Q1 from the design (not a gate).
2. Single SADSR201 non-`7f00` row (`ff0f`) still out of scope (plan 15 Open Q2).
3. Broader address-search UX / WP3 / Phase 3 parity still open — this plan only removes one known NAME-content deviation.

## Follow-ups

- Optional remount confirmation of NAME emptiness across SADSR202–207 (non-blocking).
- Do not claim Phase 3 or WP3 finished from this close.
