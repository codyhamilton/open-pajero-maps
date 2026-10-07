# Plan 57 implementation record

Run identity: Open Pajero Maps Execute (Grok Bot executor), host codyh-ubuntu, started 2026-10-08 ~00:31 AEST.
Design: `/workspace/maps-design-drafts/57-mass-control-spool-residency/DESIGN.md` → `docs/plans/57-mass-control-spool-residency/DESIGN.md`.
Seat: Soft-moved to **Codex** (`codex` 0.160.0) for review/close (CHM 2026-10-08); no new Flash sessions. No seat ask.
Heavy: `parser/tools/run_heavy_python.py` (wrapper takes flock — do not outer-flock). Encode ≤`-j4` N/A. Caps/guards plan-25. No R bump. No plan 04 P4–6; no 3-90.

## Phase 1 — Dominant residency named — DONE

See `PHASE1.md`. Plan 56 ledger cited. **Proof:** `_SPOOL_*` caches dominate mass *growth* (Unit 4c ~17.1 GiB vs Unit 4d ~2 GiB after clear-only). Disc-mmap contingency **not** triggered. Control share = hypothesis + stand-in; Phase 2 wires clear.

## Phase 2 — Cache bound cut — DONE

See `PHASE2.md`. Landed max-entries + control clear-every + refuse whole-level + drop tests. Harness cut below baseline. Resume-from verified. Decision identity baseline≡cut on smoke window.

## Phase 3 — Free-between + resume — DONE (docs)

See `RECIPE-FREE-BETWEEN.md`. Fresh wrapper scopes control→mass; resume semantics unchanged; plan 44 residuals **not** auto-discharged.

## Close

Pending Codex review after land commits.
