# Plan 45 Phase 1 — eo_division_ceiling 80 R01 rows

## Window control
Single-cell L0 windows at `33006aa` / `d35b565` byte-equal full-ref cell frames
(`013586b5` / `4ed9cd80`). Topology: 4→1, 4→1, 4→16, 4→1. See `window_control.json`.

## Source identity
Source-tag sidecar not landed (Assumption 1 offline path). Producer via design 44
Gate-B (`unique-byte` | `unique-fragment`, Moore R=8 ∪ bbox-meet) against pinned
`_cenc` probes. Leaf-local full-frame rect `[0,cr]` (divided-leaf wire convention).

## Per-row outcome
All **80** → `producer_home_outside_R_cap`. No `build:eo_bg_stitch`.
Widen@16 candidate set equals R=8 (saturated); 0 recovers; `stop_for_design=false`.
Assumption 2 residual path. See `per_row_decisions.tsv`, `phase1_summary.json`,
`widen16.json`.

## Clause (c) note
Window K1 on d35b565 cells: background failing **0** (exit≠0 from completeness
only). Would satisfy (c) if producer resolved; does not alone prove-fixed.
