# Brief: 1-03 — Numeric bands in harness.json, with recorded review

Consumer: implementation worker; bands are consumed by 1-04 and every later "within band" outcome (Phases 2-10).
Owned paths: `parser/refdata/harness.json`, `parser/refdata/profile/bands_derivation.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 1-02 (density census).
Runs alongside: 1-05, 1-06, 1-07, 1-08 (1-01 also, no shared paths).
Budget: 6 files to read, about 150 lines to change, 25 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Contract "Numeric bands ... are fixed before any tuning"; Phase 1 "Also delivers".
2. `parser/refdata/harness.json` — current shape (`envelopes`, allowlist).
3. `parser/refdata/profile/map.json` and `parser/refdata/profile/density.json` — the R statistics available.
4. `parser/harness/checks/envelope.py` — how `envelopes` is consumed (do not edit it).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

A `bands` section in `harness.json` giving, for each measurable quantity later phases gate on, an explicit tolerance around R's per-level statistic, with a stated derivation rule, fixed now before any run on G.

## Contract

Cited: "Phase 1 delivers a bands section in `harness.json` with a stated derivation rule (a tolerance around R's per-level statistic, stated as a fraction) and a recorded review. Bands are never adjusted after seeing G."

Quantities (one entry each, keyed by level where R's statistic is per level): vertices per link, vertices per km, road-type class distribution share, display-class distribution share, background type/count distribution, link-flag and node-bit prevalence, name-type mix, name-record distance tolerance for the Phase 2 overlay, and the vocabulary **coverage** share (fraction of R's values, weighted by R frequency, that G must use) consumed by 1-04.

## Changes

- Each entry: `statistic` (name, R source file and key), `rule` (e.g. `abs(G-R)/R <= tol`), `tol` (fraction), `basis` (one sentence why that fraction). Choose tolerances a priori from R's own internal variability where it can be measured (e.g. spread across R's blocks at the same level), not from G. Do NOT run any check or census on G in this unit.
- `bands_derivation.json`: the R numbers used, so the bands can be re-derived.
- Existing keys are untouched; the `envelopes` ratio [0.5, 2.0] stays.
- Review: after writing, spawn one read-only research helper (allowed for this unit) with only the derivation rule and R numbers, asking it to challenge each tolerance; record its objections and your resolution under `bands.review` (`reviewer`, `objections`, `resolution`). The orchestrator confirms the review at phase close; do not mark it accepted.

### Keep untouched

`container_allowlist`, `layers_present`, `spot_checks`, `level0_count_exempt`.

## Done evidence

- `.venv-rp/bin/python -c "import json;b=json.load(open('parser/refdata/harness.json'))['bands'];print(sorted(b))"` → lists every quantity named in the Contract.
- `.venv-rp/bin/python -m pytest parser/tests/test_harness_core.py parser/tests/test_harness_profile.py -q` → still passes (config loads).
- `git diff --stat` shows only the two owned paths; no G-derived number appears in either file (state in the report how you know).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
