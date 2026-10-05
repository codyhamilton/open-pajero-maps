# 3-03 — Checker representable demand

Status: **over budget**. Implementation is unfinished; this is a research handoff only.

## Done

- Read the brief, required design sections, demand attribution, C completeness implementation, Python demand/completeness sections, wire emission contract, Phase 2 mirror, existing completeness tests and fixture helpers, compile-on-demand mechanism, and heavy-runner usage.
- Investigated shape multiplier carriage in `_k1.h` and `_k1.c`.
- Verified protected discs before any edit:
  - `output/scratch-3-11/G_new/ALLDATA.KWI`: `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`.
  - `output/scratch-14/G_new/ALLDATA.KWI`: `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
- No checker, encoder, test, expectation, or protected-output changes.

## Not done

No failing regression was written or run. No representability implementation, live K1 rerun, identity diff, or fresh re-encode was performed. The brief supplies baseline completeness `checked=1,800,514`, `failing=776`; after totals and other-kind equality are unverified. The current protected-disc SHA is not fresh re-encode evidence.

Existing suites: **259 passed in 22.39s** (all four named suites), through `run_heavy_python.py`; log `output/scratch-14/runs/k1_p3_baseline_tests.json`, child exit 0, memory peak 198,352,896 bytes. This is baseline validation only; there is no implementation after-state. No existing-test expectation edits.

## What was learned / continuation

- Attribution predicts **776** removed keys and **zero** surviving exceptions; its branch counts are b=797, c=1, a=1 distinct demanders. Row 335 is a TOL-only centre hit; row 656 is the branch-a densification control.
- `k1_shapes` has no multiplier. `_k1.c:shp_begin`, local `region_build`, tall-shape compaction, and selected-tall insertion need carriage. The tall rows currently carry only type, class, vertex count, home cell, and record ordinal. Adding a tall-row field would require examining the Python ABI binding, which is outside owned paths; consider recovering the multiplier from the spool by the existing home/ordinal identity instead. This is an implementation constraint, not a proved blocker.
- Python `Shapes` also lacks the multiplier. Carry spool `b_mult` through construction, `take`, `concat`, and pass-one serialization. Preserve demanded-key count; retain demanding shape indices separately and filter only missing decoded pairs.
- The Phase 2 mirror supplies exact Fraction crossing detection and EO arrangement decomposition, followed by floating face coordinates, clipping, densification, rint, adjacent deduplication, spike removal, and area testing. The new checker must independently implement this contract in C and Python; no encoder calls are permitted.
- cbuild hashes C sources and headers, so a changed checker rebuilds the shared library; fresh re-encode SHA evidence remains required despite encoder source being unchanged.

## Budget, deviations, contracts

Stopped under the brief's explicit budget fallback after reading 15 repository files including the brief (14 excluding it). The required reading plus `_k1.h` / `_k1.c` multiplier investigation consumed this budget before implementation. No further implementation research was performed. The fallback expressly authorizes a handoff in `IMPLEMENTATION.md`.

The referenced repository rubric `tools/quality/checks/execution-report.json` does not exist in this worktree. A similarly named plugin copy was located, but not read because the file-read budget was exhausted. This report follows the brief's report-back fields without claiming rubric validation.

No contradiction between the geometry contracts was identified. No non-trivial out-of-scope bug was established. No agents spawned; no push.
