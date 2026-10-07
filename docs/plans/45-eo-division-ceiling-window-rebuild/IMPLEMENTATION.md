# Plan 45 — IMPLEMENTATION

## Outcome

**R-G8-1-f discharged** (window determinism regenerated). **R-G5-4-c** reclassified
from blocks-phase3 to **maps-parity-carried**: all 80 rows named
`producer_home_outside_R_cap` under design 44 Gate-B at locked R=8 (0 proven-fixed).
No encoder/oracle change. Live tip AU `0c22b266…` / Perth `5b86d33e…` unchanged.
No Phase 3 product-close. No F6/kind-order/L8 expand.

## Phase 1 — 80 ceiling rows

| Item | Result |
|------|--------|
| Ref discs regenerated | `33006aa`→`013586b5` MATCH; `d35b565`→`4ed9cd80` MATCH |
| Window control (4 cells) | ALL_OK byte-equal to full-ref frames |
| Topology | 4→1, 4→1, 4→16, 4→1 |
| Source-tag | offline producer path (Assumption 1) |
| Producer | design 44 unique-byte\|unique-fragment, R=8 |
| Per-row | **80/80 `producer_home_outside_R_cap`** |
| Widen@16 | saturated (cands@8==cands@16); 0 recovers; stop_for_design=false |
| Window K1 bg | failing 0 on d35 windows (completeness noise only) |

Evidence: `triage/historical_bg/p4_ceiling/`.

## Phase 2 — determinism

| Item | Result |
|------|--------|
| d35b565 -j1 / -j4 | both `c4965442…` MATCH historical |
| tip -j1 / -j4 | equal (`c4965442…`) |
| -j12 | `unverifiable:cap` |

Evidence: `triage/independent_reviews/3-14/conditions/determinism/`.

## Gates

Encoder/build surfaces not modified this plan — close_gates trigger expected false.
Suite not re-run (no trigger). Report-only.

## Non-goals held

No plan 04 P4–6; no 3-90; no waivers; no encoder change; no plan 46.

## Scratch

`output/scratch-45/` (ref discs, windows, determinism, K1, probes — regenerable).

## close_gates.py

```
{"pass": true, "trigger": false, "missing": [], "base": "cf3cbfb"}
```

No encoder/build surface touched; gates (a)(b)(c) not required.
