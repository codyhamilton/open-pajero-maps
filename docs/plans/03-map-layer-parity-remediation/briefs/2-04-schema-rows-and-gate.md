# Brief: 2-04 — Schema rows for the model and the gate verdict

Consumer: implementation worker, then the phase orchestrator (gate verdict); rows consumed by Phases 3, 4 and 10.
Owned paths: `docs/schema/map-frame.md`, `docs/schema/UNKNOWNS.md` (rows for the model only), `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` (append the Phase 2 gate record). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-01, 2-02, 2-03 (all finished).
Runs alongside: nothing.
Budget: 6 files to read, about 120 lines to change, 25 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Phase 2 Outcome; Architectural Implications (stable docs); Decisions (coordinate-range gate).
2. `docs/schema/README.md` — row format and status vocabulary (verified / observed / spec-only / assumed / unknown); `parser/tools/lint_schema.py` (usage).
3. `docs/schema/map-frame.md` and `docs/schema/UNKNOWNS.md` — existing header and coordinate rows.
4. `parser/refdata/profile/coord_scale.json` (2-01, 2-02).
5. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-03.json`.
6. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 2-01..2-03 records.

## Goal

Record the coordinate model and header-word rules as schema rows carrying their evidence, and state the gate verdict from the three units' numbers.

## Contract

Cited: "`docs/schema/` rows for the model" (DESIGN, Phase 2 Surfaces); "Coordinate-range gate (user): hard stop. If the offline test does not confirm R's range model, the design is bounced for re-analysis" (Decisions). A row's status must match its evidence: measured on R and consistent on held-out data is `observed`; `verified` only where the spec independently states it. Do not raise a status above the evidence.

## Changes

- Add or update rows: per-(level, class, division) coordinate maximum and the class rule; header word 0 (header size; correct the plan-01 "matches buffer size" claim in the row); words 6, 7, 9, 10, 11; WP2-exempt words with R census values. Each row cites `coord_scale.json` and the overlay evidence file.
- Append a "Phase 2 gate" record to `IMPLEMENTATION.md`: pass or fail per criterion (2-03 tolerance, clustering, edge termination; 2-02 held-out >= 99% and exceptions explained; 2-01 rule >= 99%), with the numbers. If any criterion fails, the record says the gate is not closed and the design must be bounced; do not soften it.

### Keep untouched

Code, `coord_scale.json`, `harness.json`, `DESIGN.md`.

## Done evidence

- `.venv-rp/bin/python parser/tools/lint_schema.py` exits 0.
- Every value in the new rows appears in `coord_scale.json` or the evidence file (spot-check five by grep and say which).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. If the evidence contradicts the coordinate-range hypothesis, report `blocked` with the numbers: this phase is a gate and the design is bounced, not patched.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

