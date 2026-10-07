# Plan 57 Phase 1 — Dominant residency named (mass/control)

Tip at Phase 1 land: `0e5f986` (plan 56 closed). Live oracle `88bd7852`. No R bump. No residual discharge.

## Sources (plan 56 ledger)

| Row | Path | Peak | Role |
| --- | --- | --- | --- |
| mass_decide stand-in smoke20 | `docs/plans/56-cross-phase-rss-profile/ledger/mass_decide_smoke20.json` | max_rss **1232364 KiB** (~1.18 GiB); `memory.peak` 1257132032 | Fresh wrapper measure; too small to expose spool dominance (plan 56 SUMMARY note 2) |
| mass_decide cite_prior plan44 | `…/ledger/mass_decide_cite_prior_plan44.json` | **~17.1 GiB** @30k OOM (Unit 4c); **~2 GiB** chunk2 (Unit 4d) | Standing high-water + post-clear steady state |
| control stand-in n=200 | `…/ledger/control_n200.json` | max_rss **1585996 KiB** (~1.51 GiB) | Fresh; discs+spool frames walk; no clear-every wired |

Plan 56 SUMMARY handoff: **57** dominant evidence = cite_prior ~17 GiB + control 1.5 GiB stand-in. Explicit unknown retained: named structure size-accounting inside mass spool caches vs discs vs probes at peak (smoke20 did not decompose).

## Dominant co-resident class — mass_decide

### Proof (growing class)

**`_SPOOL_CELL_CACHE` / `_SPOOL_KEY_CACHE` in `leaf_io.py` dominate the *growing* co-resident set under mass_decide.**

Evidence chain (not hypothesis):

1. Plan 44 Unit 4c: mass `--r 8` without periodic clear reached RSS **~17.1 GiB** at ~30000/95059 leaves and was SIGTERM'd (MemAvailable ~3.2 GiB). Cited in plan 56 ledger as `host_rss_at_30k_oom_stop`.
2. Plan 44 Unit 4d: same path with `--cache-clear-every 50` (calls only `leaf_io.clear_spool_caches`, which clears those two dicts) finished the remaining ~65k leaves at peak RSS **~2 GiB**. Cited as `chunk2_peak_rss_approx`.
3. `clear_spool_caches` does **not** close disc frame maps, SpoolReader, or flex probes. The ~15 GiB drop when only spool caches are cleared attributes the growth to those caches, not to dual ALLDATA frame maps or probe `.so` residency.

Symbols: `leaf_io._SPOOL_KEY_CACHE`, `leaf_io._SPOOL_CELL_CACHE`, `leaf_io.clear_spool_caches`, `mass_decide --cache-clear-every` (default 50).

### Hypothesis (retained)

- Exact KiB split of residual ~2 GiB chunk2 peak among (disc frames + open files + probes + Python heap + uncleared neighbourhood rings) is **not** size-accounted. Labelled **hypothesis / unknown** per plan 56 explicit unknowns — does not overturn the growing-class proof above.
- Flex-probe / Python process growth as a *secondary* co-resident class: plausible, unmeasured at Unit 4c peak.

## Dominant co-resident class — control

### Proof (shared machinery)

Control imports the same `leaf_io.spool_candidates` → `_spool_cell` path and therefore fills the same `_SPOOL_*` caches. Plan 56 control stand-in peaked **~1.51 GiB** at n=200 / R_cap=8.

### Hypothesis

Under larger control walks (or same-process sequencing into mass without clear), spool caches are the same dominant *growing* class as mass. **Not proven at mass scale** — control has no `--cache-clear-every` today. Phase 2 wires the bound.

## Contingency check (Design Decision 6)

> If 56 shows disc mmap dominates over spool caches, retarget Phase 2 to frame-map lifecycle (still this band) — do NOT open encode (58).

**Contingency NOT triggered.** Disc/frame maps stay live across `clear_spool_caches`; the Unit 4c→4d drop proves spool caches, not mmap, drove the OOM-class growth. Phase 2 targets cache bound / chunk-stream on `leaf_io` / `mass_decide` / optionally `control` as designed.

## Labels summary

| Claim | Label |
| --- | --- |
| Spool cell/key caches dominate mass_decide *growth* to ~17 GiB | **Proof** (Unit 4c vs 4d; clear API scope) |
| Clear-every-50 sufficient for remaining ~65k at ~2 GiB | **Proof** for that chunk (Unit 4d); standing hygiene |
| Exact byte accounting of caches vs discs vs probes at peak | **Unknown** (plan 56) |
| Control shares dominant growing class | **Hypothesis** (shared code) + stand-in peak; Phase 2 hardens |
| Disc mmap dominates | **Rejected** for Phase 2 retarget (contingency closed) |
| R bump for memory relief | **Forbidden** (standing) |

## Phase 1 outcome

Go for Phase 2 spool cache bound (max-entries and/or clear-every hardening + control wire + drop test + harness peak gate). No encode (58). No R bump. No plan-44 residual discharge.
