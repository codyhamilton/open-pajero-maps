# Plan 53 — IMPLEMENTATION

## Outcome

**R-G9-3-d discharged** by confined encoder fix. Phase 1 verdict: **encoder
defect** (not D1). Independent bit-level decode of tip `aeae426c` raw_bytes
places all five (1755,591) degenerates at `sx=8192` → `xc=4096`. Root cause:
`dv_assign` wrapped `lon > lon_hi` by −360° into the western sub-cell while
encode clamped x to the parent east edge. Fix: after `[0,360)` normalize, if
`delta > lon_span` return −1. Successor oracle **`0c22b266…`**. Remaining 128
outside-edge coincident links → **R-G9-3-d-rem**. No Phase 3 product-close.
No L8 selection expand / F6 / kind-order (Cody-held; plan 52 steering).

## Phase 1 — encode vs decode

| Item | Result |
|------|--------|
| Oracle | `aeae426c…` (live tip at start) |
| 5 witnesses | all vertices `xc=4096`, nip=0; D1 matches independent reader |
| Spool | exactly 5 nodes lon epsilon past east of (1755,591); assign leaves 0/4/8 |
| Verdict | **encoder defect** |

Evidence: `triage/trim_r_parity/l0_degen/discriminate.json`.

## Phase 2 — fix + census + successor

| Item | Result |
|------|--------|
| Fix | `parser/kiwiw/_e2.c` `dv_assign`; ctest `e2_div_assign` expects −1 |
| Goldens | `l0_divided_halo`, `l4_divided` refreshed |
| AU census before | outside-edge coincident **5969** (E-only 5871); parent 5 |
| AU census after | **128** (E 32 / N 39 / S 26 / W 29 + corners); parent **0** |
| Diff vs `aeae426c` | **565 changed / 0 added / 0 removed** (553 L0 + higher halo) |
| AU sha | `0c22b266e7b406bb0cabeee814c9f0cfeebebad6071e131252357f1d3e1aa25a` |
| Perth sha | `5b86d33ed5976e7bd4208fb46c4fdde14747c7f31d1d40d819e9e9b2bf5f00d9` (was `04be2f6e…`) |
| K1 AU | failing **0** (`output/scratch-53/k1_au.json`) |
| eo_census | guard_hits=0 declines_total=0 |
| Residuals | R-G9-3-d → discharged-plan-53; R-G9-3-d-rem named |

## Gates

- Close gate (a) full suite: 1490 passed, 9 skipped in 635.70s at afce673
- Close gate (b) encode wall: median 29.33 s of 3 at -j4 (spread 1.71 s) vs baseline 44.23 s (plan 50 single-run)
- Close gate (c) sha gate: AU 0c22b266 PASS, Perth 5b86d33e PASS

## Non-goals held

No plan 04 P4–6; no 3-90; no F6 catchall→288; no kind-order flip; no L8
selection expand; plan 45 not started.

## Scratch

`output/scratch-53/` (regenerable encodes, K1, oracle_diff, runs).

## close_gates.py

```
{"pass": true, "trigger": true, "missing": [], "base": "2563e47", "head": "afce673",
 "gates": {"a": {"present": true, "sha": "afce673"}, "b": {"present": true}, "c": {"present": true}}}
```

Run: `.venv-rp/bin/python -B parser/tools/close_gates.py --base 2563e47 --impl docs/plans/53-l0-degenerate-east-edge-roads/IMPLEMENTATION.md` → exit 0.
