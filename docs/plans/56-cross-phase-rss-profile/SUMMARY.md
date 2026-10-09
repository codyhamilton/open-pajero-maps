# Plan 56 — cross-phase RSS / residency summary

Published for Design handoff to plans **57–59**. Measurement-only; no optim landings here. Tip at publish: see git log (post-`d99040b` ledger commit).

## Caps observed

- Serial `flock` + `run_heavy_python.py`; encode `-j4`; representability workers=1 (≤ `-j6`).
- No run hit RSS clean-stop ≳17.5 GiB or MemAvailable ≲3 GiB.
- Every wrapper run recorded `memory.peak` (fail-closed **guard present** in `run_heavy_python.py`; not exercised — no missing-peak run).
- Inter-phase free-then-reenter samples: mass→control; control→representability; representability→dump; dump→encode (`clear_spool_caches+gc` + meminfo).

## Peak table (evidence-backed)

| Phase | Label | max RSS | memory.peak | tree peak | Dominant co-resident (evidence) | Optim candidate |
| --- | --- | --- | --- | --- | --- | --- |
| mass_decide | stand-in smoke20 | 1.18 GiB (1232364 KiB) | 1.17 GiB | — | process + cgroup peak; anon/file post-exit snap (wrapper) | **57** |
| mass_decide | cite_prior plan44 | ~17.1 GiB @30k OOM; ~2 GiB chunk2 | unknown | — | host RSS at Unit 4c stop; spool caches co-resident until `cache-clear-every` (IMPLEMENTATION) | **57** |
| control | stand-in n=200 | 1.51 GiB | 1.51 GiB | — | process + cgroup; discs+spool frames walk | **57** |
| representability | stand-in historic_188 | 0.68 GiB | 0.72 GiB | — | SpoolReader + tall L0 (61157 shapes / 14.4M coords) + Region+_required_cells | unknown→**57** if shared spool |
| encode | stand-in Perth `-j4` | wrapper 3.25 GiB; **tree 13.96 GiB** | 1.27 GiB (scope) | **13962.9 MB** | worker Pool j=4 + parent (bench_build tree sampler); Perth sha `04be2f6e…` | **58** |
| encode | cite_prior plan48 | — | — | AU 15240.1 / Perth 13809.5 MB | tree peak only (no phase tags) | **58** |
| dump/extend | finalize-run fixture | 0.45 GiB (baseline max 473352 KiB) | 0.33 GiB | — | finalize kind array (1 000 013 rows × parts); gates all pass | **59** |
| triage (plan 46) | bg producer scan v5, 4 shards | wrapper 4.39 GiB; **max shard RssAnon 928.6 MiB** (cap 3072) | 4.36 GiB (incl. file pages) | — | LRU 4096 numpy ring cache + tiled leaf order; spool/disc memmap file pages; follow-on gate_repro 6.10 GiB max RSS / 5.36 GiB peak | — (post-56 addendum, `ledger/bg_producer_scan_plan46.json`) |
| triage (plan 62) | R01 residual re-decide + RC ablation + audit, run A+B | wrapper max RSS 3.88 GiB (VmHWM A 3.84 / B 3.88 GiB) | 4.52 GiB (incl. file pages) | — | FarHomes(L0) + LRU 4096 ring cache; per-leaf caches; companion phase23 decide 3.84 GiB max RSS / 6.10 GiB peak incl. file pages | — (post-56 addendum, `ledger/r01_residual_plan62.json`) |
| triage (plan 63) | producer-tie census P1, run A+B | wrapper max RSS 3.72 GiB | 0.63 GiB | — | FarHomes(L0) + 47 leaves | — (post-56 addendum, `ledger/producer_tie_plan63.json`) |
| triage (plan 63) | P2 sidecar window builds (386) + provenance/rules A+B + 013586b5 dup census | wrapper max RSS 3.71 GiB (provenance) / 1.07 GiB (builds) / 0.41 GiB (census) | 1.94 GiB (census, incl. file pages) | — | FarHomes(L0); builds serial -j4 | — (post-56 addendum, `ledger/producer_tie_plan63.json`) |
| triage (plan 63) | P3 P2-reproduction + dup census R/0c22b266 + gate_repro (S′ opt-in) | wrapper max RSS 6.94 GiB (gate_repro) / 3.71 GiB (reproduction) | 6.34 GiB | — | dump_join/K1 classify; serial | — (post-56 addendum, `ledger/producer_tie_plan63.json`) |
| triage (plan 64) | P1 PBF provenance re-extract (17 homes / 23 cells) + 23 sidecar windows at 33006aa + trace | wrapper max RSS 4.08 GiB (re-extract) / 3.71 GiB (trace) | 4.35 GiB (incl. file pages) | — | pyosmium flex_mem node index; FarHomes(L0); builds serial -j4 | — (post-56 addendum, `ledger/source_removed_plan64.json`) |
| triage (plan 64) | P2 d35b565 stage windows (23) + stage trace + H1–H5 classifier | wrapper max RSS 3.72 GiB (classify, FarHomes) / 1.06 GiB (windows) | 0.35 GiB | — | FarHomes(L0); builds serial -j4 | — (post-56 addendum, `ledger/source_removed_plan64.json`) |
| triage (plan 68) | P1a sidecar AU+Perth encodes (-j4) + national duplicate census | wrapper max RSS 3.41 GiB | 7.93 GiB (incl. file pages) | — | sidecar encode -j4 + census over all leaves | — (post-56 addendum, `ledger/bg_dedup_plan68.json`) |
| triage (plan 68) | P1b–c R census + R correspondence (sample A+B, national) + R-G5-4-a-1 windows | wrapper max RSS 3.57 GiB (p1c) / 2.24 GiB (rcorr A) / 0.07 GiB (R census) | 4.41 GiB (incl. file pages) | — | R whole-frame reads; FarHomes(L0); windows serial -j4 | — (post-56 addendum, `ledger/bg_dedup_plan68.json`) |
| triage (plan 68) | P1d D-class census Perth / R / AU (-j4) | wrapper max RSS 1.51 GiB (R+AU) / 0.47 GiB (Perth) | 4.27 GiB (incl. file pages) | — | Pool -j4 over blocks; vertex criterion + 24×24 overlap grid | — (post-56 addendum, `ledger/bg_dedup_plan68.json`) |
| triage (plan 68) | reader re-audit (R p64 cells + 3 G discs whole vs cut) | wrapper max RSS 0.30 GiB | 3.76 GiB (incl. file pages) | — | sequential frame reads | — (post-56 addendum, `ledger/bg_dedup_plan68.json`) |
| triage (plan 68) | review-1 rerun: sidecar encodes + census B + r_corr A/B + D-class A/B (R/Perth/AU) | wrapper max RSS 3.57 GiB | **10.42 GiB** (incl. file pages; cap 12G) | — | serial; Pool -j4 D-class; encodes -j4 | — (post-56 addendum, `ledger/bg_dedup_plan68.json`) |

Ledger JSON: `docs/plans/56-cross-phase-rss-profile/ledger/`. Wrapper logs: `output/scratch-56/runs/` (gitignored).

## Concurrent residency notes (no assumed frees)

1. **Encode tree ≫ wrapper RSS:** Perth fresh tree peak **13962.9 MB** aligns with plan-48 Perth cite (13809.5). Worker children dominate; level-resident structures stay live across the encode (plan **58** target: drop between levels / mmap).
2. **mass_decide cite_prior ~17 GiB** is the standing high-water for spool/disc co-residency under full worklist; smoke20 (~1.2 GiB) is too small to expose spool-cache dominance — use cite_prior + plan-44 Unit 4c for **57** sizing.
3. **Dump finalize** fixture keeps a full kind array in memory (plan-05 / ARCHITECTURE deferred) — **59** out-of-core target. Candidate path already lower RSS than baseline (gates pass).
4. **Representability** stand-in matched 3-15 historic 188 exactly (885/189/205/0). Full-AU K1 completeness not seated — labelled unknown for full-pass peak.
5. **Inter-phase boundaries:** MemAvailable stayed ~20–21 GiB after each free+gc; separate wrapper scopes, so leftovers are host-level (page cache / other agents), not proven in-process spill from phase A into B.

## Explicit unknowns

- Full-AU encode tree peak under this plan’s wrapper (cite_prior AU 15240.1 MB only).
- Full mass_decide 95059 under this plan’s wrapper (cite_prior Unit 4c/4d only).
- Full-AU K1 / representability completeness pass RSS.
- Named structure size-accounting inside mass spool caches vs discs vs probes (smoke20 did not decompose).
- Post-exit `memory.stat` anon/file in wrapper logs are **not** peak co-residency (scope torn down); use `max_rss_kib` / `memory.peak` / tree sampler for peaks.

## Handoff

- **57** mass/control spool residency — dominant evidence: cite_prior ~17 GiB + control 1.5 GiB stand-in.
- **58** encode level residency drop — dominant evidence: Perth tree 13.96 GiB / AU cite 15.24 GiB.
- **59** dump finalize out-of-core — dominant evidence: finalize-run kind-array fixture peaks ~0.45 GiB baseline.

This summary does **not** claim 57–59 acceptance proven — only that Phase-1 design acceptance has a coherent cross-phase ledger.

## Flash close

PASS-WITH-CONCERNS (2026-10-08 ~00:30 AEST). Provenance + fail-closed wording addressed in close-out commit. Plan 56 closed.

