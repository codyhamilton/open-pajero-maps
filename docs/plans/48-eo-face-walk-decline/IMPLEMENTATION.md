# Plan 48 — IMPLEMENTATION

## Run identity
- Tool: Grok Bot (maps executor)
- Start: 2026-10-07 ~14:08 AEST
- Worktree: open-pajero-maps-14-completeness (master-direct)
- Parallel with plan 44 expanding-search control (Gates A+B) and plan 49 regen.

## Phase 1 — Decline root cause (in progress)
- Seeded decline cases from stress_20k (seed 4314, N=20000): r359, r8475, r11892, r14503, r19650.
- Rings regenerated and committed under `triage/independent_reviews/3-14/conditions/eo_decline/decline_rings.json`.
- Next: `EO_DIAG` compile-time hook in `_cenc.c` (absent from production), `eo_walk_diag.py` dumping arrangement + Fraction exact checks (H1–H4), named mechanism per ring, xfails.

## Phase 2 / 3
- Not started. Census + robust walk after P1 mechanisms named.

## Carried
- Heavy lock shared with SC/garcia; EO_DIAG compile/tests queue behind plan 44 smoke + 47 representability + 49 regen.

## Phase 1 progress (2026-10-07 ~14:21 AEST)
- `EO_DIAG` hook landed in `_cenc.c` (compile-time `-DEO_DIAG`; production omit).
- Dumps for all 5 declines under `eo_decline/dumps/`.
- `eo_walk_diag.py` named mechanisms:
  - r359, r8475, r19650 → **H2_equal_angle_ties**
  - r11892, r14503 → **H1_rounding_non_planarity**
- All declines: site `used=1` (already-used half-edge), not `np≥ne`.
- Next: commit dumps + mechanisms; add xfails; successor_non_injective always co-present (verify); Phase 2 census.

## Phase 1 CLOSE-READY (2026-10-07 ~14:57 AEST)
- All 5 rings named with witnesses (`mechanisms.json`).
- EO_DIAG dumps committed; production builds omit `-DEO_DIAG`.
- Regression xfails: 3 passed + 5 strict xfails invoking real probe declines.
- Awaiting Flash review before marking Phase 1 discharged; Phase 2 census next.


## Flash review (Phase 1) — 2026-10-07 ~15:00 AEST
- Seat: OpenCode DeepSeek Flash.
- Verdict: **APPROVE Phase 1 discharge** (PASS-WITH-CONCERNS equivalent).
- Mechanisms independently recomputed; causal ties to decline site confirmed for all 5.
- Conditions to carry: (1) make dumps reproducible via real `-DEO_DIAG` invoke in `eo_walk_diag.py`; (2) fix `:885`→actual EO_DIAG site in README; (3) note H2 ties are equal atan2 doubles not exact-collinear for Phase 3.
- Transcript: `output/scratch-48/flash.stdout`.

## Phase 2 — census (in progress)
- `eo_stats` thread-local counters in `_cenc.c` + `kw__eo_stats_get/reset` (default visibility).
- `parser/tools/eo_guard_census.py` + `test_eo_guard_census.py` (r359 walk_used≥1; clean square 0).
- Next: wire cbuild sidecar; AU/Perth builds at -j4 proving guard hits=0, sha unchanged.
