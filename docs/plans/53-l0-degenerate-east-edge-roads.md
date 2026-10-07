# Five degenerate G L0 road links on the parent east edge (R-G9-3-d)

Plan 53 closed **R-G9-3-d** by confined encoder fix. Phase 1 verdict:
**encoder defect** (not D1). Successor oracle **`0c22b266…`** (was
`aeae426c…`). Perth tip **`5b86d33e…`** (was `04be2f6e…`). Remaining 128
outside-edge coincident links → **R-G9-3-d-rem**. No Phase 3 product-close.
Steering held: no F6 / kind-order / L8 selection expand. Plan 45 not started.

## Intent
Cody standing rule (2026-10-05). Discriminate encode vs D1 for the five
(1755,591) east-edge degenerates; fix or proven-cause; AU census; successor
oracle only if encode changes.

## Why This Existed
Plan 42 found 5 G L0 road links in parent (1755,591) leaves 0/4/4/4/8 with all
vertices at x=4096 (parent east), outside sub-cell rect. Encode vs D1 was open.

## What Was Built

**Phase 1 — encode vs decode**
| Item | Result |
| --- | --- |
| Oracle | `aeae426c…` |
| Independent decode | all 5: `sx=8192` → `xc=4096`, nip=0; D1 matches |
| Spool | 5 nodes lon epsilon past east; assign leaves 0/4/8 |
| Verdict | **encoder defect** |

**Phase 2 — fix + census + successor**
| Item | Result |
| --- | --- |
| Root cause | `dv_assign` wrapped `lon > lon_hi` by −360° into western sub-cell; encode clamped x=4096 |
| Fix | after `[0,360)` normalize, `delta > lon_span` → −1 (`parser/kiwiw/_e2.c`) |
| Tests/goldens | `e2_div_assign`; `l0_divided_halo`, `l4_divided` refreshed |
| AU outside-edge coincident | **5969 → 128** (E-only 5871 → 32); (1755,591) **5 → 0** |
| Diff vs `aeae426c` | **565 changed / 0 added / 0 removed** (553 L0 + halo) |
| AU sha | `0c22b266e7b406bb0cabeee814c9f0cfeebebad6071e131252357f1d3e1aa25a` |
| Perth sha | `5b86d33ed5976e7bd4208fb46c4fdde14747c7f31d1d40d819e9e9b2bf5f00d9` |
| K1 / eo | failing 0; guard_hits=0 declines_total=0 |

Evidence: `triage/trim_r_parity/l0_degen/` (discriminate, census, census_after,
successor_oracle_0c22b266, cells TSV, README).

## Review
Flash (`deepseek/deepseek-flash`): **LAND**.
- PASS A–G: encoder-defect verdict; lon-wrap root cause; confined fix; census
  5969→128; successor AU/Perth; R-G9-3-d discharged + rem named; close_gates
  pass at afce673 / ddd0d54.
- Soft (non-blocking): census generators live in scratch (JSON committed);
  residuals forward-ref collapsed record path (resolved by this close-out).

## QA
- Close gate (a) full suite: 1490 passed, 9 skipped in 635.70s at afce673
- Close gate (b) encode wall: median 29.33 s of 3 at -j4 (spread 1.71 s) vs baseline 44.23 s (plan 50 single-run)
- Close gate (c) sha gate: AU 0c22b266 PASS, Perth 5b86d33e PASS
- `close_gates.py --base 2563e47` PASS (trigger true; missing [])

## Residual Risks
- **R-G9-3-d-rem**: 128 remaining N/S/W/E edge-coincident outside-leaf links
  (not lon-wrap); mechanism TBD; maps-parity-carried.

## Follow-ups
- Design: optional residual class for R-G9-3-d-rem.
- Parent starts plan 45 after this close (not from this unit).

Scratch: `output/scratch-53/` (regenerable).
