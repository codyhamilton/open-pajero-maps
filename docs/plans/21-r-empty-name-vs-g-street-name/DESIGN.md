---
design_id:
---

# R empty NAME vs G street.name (SADSR SRMX)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Plan-15 follow-up: R empty NAME vs G street.name (ux/e2e) — SADSR201 0/38120 non-empty NAME on R. Plan 15 made G emit STFG 0x7f00 + NAME (street.name). R evidence may show empty NAME on the dominant population. Reconcile honestly without inventing disc bytes. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not mega-close 3-90 or claim Phase 3 closed. Prefer offline evidence from committed schema/plan 15 records; remounted IDX optional, not a gate.

## Problem

Plan **15** closed the STFG **presence** defect: G now emits SRMX `STFG = 0x7f00` (bit 6 = NAME present) instead of the false `0x3f00`. It left NAME **content** on Assumption 2 (`NAME = KYCH = street.name`). That content rule is already contradicted by committed residual evidence and by the Assessor census claim:

| Surface | What it says | Status |
| --- | --- | --- |
| `docs/plans/15-sadsr-srmx-stfg.md` Residual / Follow-ups | NAME bit set but NAME value empty on sampled SADSR street records; G still writes `street.name`; Open Q1 may adjust value only | **committed** on tip |
| Plan 15 Phase 2 unit report (git `56a5462`, collapsed at close) | Mounted-R probe: **0 / 38,120** non-empty NAME on SADSR201; STFG `7f00` on 38,119 and `ff0f` on the known 1 exception; first records of SADSR202–207 also `NAME == ""` | **historical worker record** (not a tip schema row); matches ticket |
| `parser/osm_to_address_index.py` `street_to_srmx_dict` | `"NAME": street.name` with docstring still citing Assumption 2 | **live G≠R content** |
| `parser/tests/test_address_extractor.py` | Asserts `NAME == street.name` and round-trips that non-empty string | locks the wrong content |
| `docs/schema/flags.md` STFG row | Still describes G NAME as KYCH = `street.name` | schema honesty lag |

Presence bit and content are different contracts. Leaving non-empty NAME while R carries empty VRBL CH is an unexplained deviation on the search/UX path (KYCH remains the search key; NAME is the next gated field). Plan 15 intentionally deferred the value rule; this plan owns that deferred Open Q1.

Verified on `origin/master` at `f82e2a5` from committed plan 15 / flags / encoder / tests only — no live IDX mount in the design environment. Plans **01–05** and **07–20** occupy those numbers on master (20 is the PSS/ops-cap design folder); **06** is not a work unit. This plan is **21**.

## Solution shape

One bounded reconciliation: keep STFG `0x7f00` (NAME **present**); change G's NAME **value** to the empty string so content matches the R-dominant pattern; keep KYCH = `street.name`. Update tests and schema wording so presence and content are not conflated. Do not invent new disc byte dumps. Do not reopen WP3 or other IDX families.

### Domain: NAME content vs presence

- Owns: the honesty package that separates STFG bit 6 (field present) from VRBL CH payload (may be empty), citing plan 15 residual and the historical 0/38120 probe without minting new R hex as if freshly measured in this design.
- Contract: schema / plan surfaces state: (1) R dominant SRMX pattern remains STFG `0x7f00` with bit 6 set; (2) NAME **content** on the dominant SADSR201 population is empty (`""`), with Evidence pointing at plan 15 residual plus the historical Phase 2 probe cited in that record's Follow-ups / ticket; (3) KYCH remains the non-empty street search string; (4) G's former Assumption 2 (NAME = KYCH) is retired for SRMX streets. No encoder edit in this domain alone if Execute prefers a single commit — the contract must land with the emission fix.
- Non-goals: no new full-disc IDX census as a gate; no classification of the single `ff0f` STFG exception; no POISR/ITSSR/SRHA NAME rules; no completeness / ALLDATA work.

### Domain: G SRMX NAME emission

- Owns: `street_to_srmx_dict` NAME value and the tests that lock it.
- Contract: every SRMX dict for a street has `STFG == [0x7f, 0x00]`, `"KYCH": street.name`, and `"NAME": ""` (empty string, key still present). Synthetic unit tests assert that shape and fail if NAME equals a non-empty street string under `7f00`. Round-trip smoke still proves bit 6 set and empty NAME survives write/parse. Docstring no longer claims NAME = KYCH.
- Non-goals: no STFG mask change; no KYCH change; no regeneration of all 99 IDX files as a program milestone; no claim that WP3 or Phase 3 closed.

## Decisions

1. Plan number is **21**. Standalone plan-15 Open Q1 follow-up. It does not reseat plan 15's STFG presence close and does not absorb draft/plan 20 PSS work.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — empty NAME value under retained `0x7f00`).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Prefer offline evidence already on master / in plan 15 history. Remounted IDX census is optional confirmation, not acceptance.
6. Reject clearing bit 6 again (that would recreate the plan 15 defect). Reject leaving `NAME = street.name` while documenting R as empty.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: must this plan remount R / IDX and re-prove 0/38120 before changing G?
- Answer chosen: **no**. Acceptance uses committed plan 15 residual (empty NAME with bit set on sampled SADSR streets) plus the historical Phase 2 probe already cited there / in the Assessor ticket (0/38120). Optional remount may reconfirm and strengthen schema Evidence; it is not a gate.
- Rationale: ticket prefers offline schema/plan 15 evidence; inventing fresh disc bytes in the design environment is forbidden; the worker probe already answered Open Q1 once.
- If wrong: Cody restores an IDX mount; Execute may add a non-blocking confirm script or Evidence line that sampled/full NAME values are empty — still no completeness dumps, still no invented hex.

### Assumption 2

- Question: what string does G write into SRMX NAME under bit 6?
- Answer chosen: **empty string** `""` (key present). KYCH stays `street.name`.
- Rationale: R-dominant content is empty while presence bit stays set; plan 15 Open Q1 said a follow-up adjusts value only; clearing the bit would undo plan 15.
- If wrong: Cody supplies a distinct display form (folded key, suburb-qualified, etc.); adjust NAME value only, STFG stays `0x7f00`.

### Assumption 3

- Question: does the full 0/38120 census need a tip schema row before emission may change?
- Answer chosen: **no requirement for a separate census artifact**. Promote the content rule into `flags.md` (and a one-line `index-idx.md` clarity touch if needed) citing plan 15 residual + historical probe / ticket. Do not invent a new binary dump file.
- Rationale: honesty is presence-vs-content wording + G alignment; a remount census is bonus Evidence, not a second phase.
- If wrong: Execute may commit a tiny text evidence note under this plan folder quoting the remount counts — still no ALLDATA / completeness disc.

### Assumption 4

- Question: does fixing SRMX street NAME imply changing SRHA / POISR NAME emission?
- Answer chosen: **no**. Bound to SADSR SRMX street records only.
- Rationale: ticket and plan 15 residual are SRMX-street scoped; SRHA/POISR NAME populations are not evidenced as empty here.
- If wrong: Cody widens with separate R evidence; do not silently empty other families.

### Assumption 5

- Question: may this plan claim address-search UX / e2e parity complete?
- Answer chosen: **no**. It removes one known G≠R NAME-content deviation on SRMX streets. Broader WP3 / IDX / Phase 3 gates stay open.
- Rationale: standing rule and ticket forbid mega-close; KYCH/search behaviour is unchanged.
- If wrong: none — still must not mark Phase 3 or WP3 finished.

## Open questions

1. After remount, are SADSR202–207 likewise 100% empty NAME (Phase 2 report sampled first records only beyond 201)? **Not a Phase gate.** If a state shows non-empty NAME, a follow-up adjusts that state's rule only.
2. Does the head unit ever display SRMX NAME when empty, or always fall back to KYCH? **Out of scope** — behaviour on R with empty NAME is the parity target; no firmware reverse-engineering in this plan.
3. The single SADSR201 non-`7f00` SRMX row (`ff0f`) — still **out of scope** (plan 15 Open Q2 residual).

## Phases

### Phase 1 — G NAME empty under retained `0x7f00`; schema splits presence vs content

- Outcome: `street_to_srmx_dict` returns STFG bytes `0x7f00`, `"KYCH": street.name`, and `"NAME": ""`. Docstring retires Assumption 2 (NAME = KYCH) and states R-dominant empty NAME with bit 6 set, citing plan 15 residual / this plan. `test_stfg_bits_correct_for_srmx`, `test_srmx_dict_has_required_keys`, and `test_srmx_record_roundtrip_bit6_name` (and any sibling asserting non-empty NAME) expect empty NAME, still require the NAME key and bit 6 set, and keep KYCH = street name. `docs/schema/flags.md` SADSR SRMX STFG row (and a one-line `index-idx.md` clarity touch if needed) records: presence = `0x7f00` verified; content = empty NAME on dominant SADSR201 population; G emits empty NAME. Optional: short evidence note under the plan folder restating plan 15 residual + historical 0/38120 probe without new disc bytes. No STFG mask regression to `0x3f00`. No ALLDATA encode. No Phase 3 close. No plan 04 P4–6 / plan 06. 170 / 3-16 / 3-17 not reseated. Remounted IDX not required for acceptance. Plan folder `docs/plans/21-r-empty-name-vs-g-street-name/` lands with this design when Execute commits.
- Surfaces: `parser/osm_to_address_index.py` (`street_to_srmx_dict`); `parser/tests/test_address_extractor.py` (NAME assertions + round-trip); `docs/schema/flags.md` (STFG/NAME content honesty); optional `docs/schema/index-idx.md` one-liner; optional plan-folder evidence note. SRHA/POISR/ITSSR encoders, plan 15 collapsed record body (historical), triage, and completeness surfaces are **read-only**.
- Approach: known
- Depends on: master tip with plan 15 closed (`docs/plans/15-sadsr-srmx-stfg.md`) and G already on `0x7f00` + NAME key (present at `f82e2a5`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `f82e2a508b6d328426c4cc86cfcc50ede98a9bfe` (“docs: add plan 20 reconcile PSS ops cap design”).
- Candidate: Maps Quality Assessor NEW #3 — Plan-15 follow-up: R empty NAME vs G street.name (ux/e2e); SADSR201 0/38120 non-empty NAME on R; reconcile without inventing disc bytes.
- Evidence cited (committed / historical): `docs/plans/15-sadsr-srmx-stfg.md` Residual Risks + Follow-ups (NAME empty with bit set; Assumption 2 retained); plan 15 Phase 2 report at git `56a5462` (0/38120 non-empty NAME on SADSR201; 202–207 first records empty); `docs/schema/flags.md` STFG row still naming NAME = KYCH; `parser/osm_to_address_index.py` `"NAME": street.name`; `parser/tests/test_address_extractor.py` NAME == street.name assertions; `docs/schema/index-idx.md` SRMX field list + STFG `7f00` census; VRBL CH empty string is a valid length-prefixed payload (synthetic FieldDefs already use VRBL CH for NAME).
- Rejected for this design: clearing STFG bit 6 (reopens plan 15); keeping `NAME = street.name` while only documenting the conflict; inventing fresh R hex dumps in design; remount as acceptance gate; widening to SRHA/POISR/WP3; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; mega-closing Phase 3 / claiming full address UX done; absorbing plan 20 PSS scope.
- Draft format followed: `/workspace/maps-design-drafts/19-overview-sync-14-16/DESIGN.md` and `/workspace/maps-design-drafts/20-reconcile-pss-ops-cap/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
- NN verification: `origin/master` occupies 01–05, 07–20 (20 = PSS/ops-cap design folder); `/workspace/maps-design-drafts/` has 19–20 → this draft is **21**.
