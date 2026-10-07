# Plan 59 — Implementation

Seat: **Codex** CLI 0.160.0. Host: codyh-ubuntu checkout `open-pajero-maps-14-completeness`. Parent tip `22a4797`. Live oracle `88bd7852` unchanged.

## Phases

| Phase | Status | Note |
| --- | --- | --- |
| P1 join vs finalize attribution | **proceed** | Cite plan 56 `ledger/dump_finalize.json` (~0.45 GiB); finalize kind-array dominates |
| P2 out-of-core `_finalize_dump` | **landed** | packed-key k-way merge; finalize-run all gates PASS |
| P3 multi-kind free + pointers | **landed** | RECIPE-FREE-BETWEEN; ARCHITECTURE/WORKFLOW updated |

## Peaks (plan-05 finalize fixture)

| | max_rss_kib (median) | wall_s (median) |
| --- | ---: | ---: |
| baseline | ~473268 | ~1.01 |
| tip (pre-59 candidate) | ~201200 | ~1× |
| plan 59 | **~88880** | **~1.42** (ratio 1.406) |

## Gates

sha/counts/parts/rss_delta/wall_le_2x: **PASS** (`output/scratch-59/runs/finalize_results2.json`).

## Non-goals kept

No whole-file extend revival; no Phase 3 product-close; no R bump; ARCHITECTURE deferred → landed (honest wall residual ~1.4×).
