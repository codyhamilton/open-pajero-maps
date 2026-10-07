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
