# Plan 58 implementation record

Run identity: Open Pajero Maps Execute (Grok Bot), host codyh-ubuntu, started 2026-10-08 ~00:48 AEST.
Design: box `58-encode-level-residency-drop/DESIGN.md`. Seat: **Codex** 0.160.0 (no Flash). No seat ask.
Heavy: `run_heavy_python.py` (wrapper takes flock). Encode `-j4`. Live oracle `88bd7852`. No plan 04 P4–6; no 3-90. **No Phase 3 product-close claim.**

## Phase 1 — DONE

See `PHASE1.md`. Plan 56 encode rows: worker Pool j=4 dominates tree peak (inventory). Cut target: E1Spool not closed across levels.

## Phase 2 — DONE (+ Codex HOLD fix)

See `PHASE2.md`. Close prior E1Spool; harden `E1Spool.close`; early `del e1_out`.
**HOLD fix:** recycle fork Pool after each level (guaranteed worker E1Spool drop; spill files retained on disk).

Perth `-j4` (MB = `bench_build.py` units):

| Arm | tree_mb | max_rss_kib | memory.peak | sha |
| --- | ---: | ---: | ---: | --- |
| baseline | 13848.7 | 3413788 | 2426187776 | `04be2f6e…` |
| cut (map release) | 13165.0 | 3234696 | 1379713024 | `04be2f6e…` |
| cut (pool recycle) | **13113.3** | **3200832** | **1681948672** | `04be2f6e…` |

## Phase 3 — AU confirm DONE (no product-close)

AU `-j4` ×3 after pool-recycle (`output/scratch-58/runs/au_recycle{1,2,3}/`):

- walls_s: [37.69, 37.38, 36.26] → **median 37.38 s of 3 at -j4 (spread 1.43 s)** vs baseline **37.38 s** (plan 41)
- tree peaks MB: [15274.2, 15476.1, 15389.1] (≈14.1–14.4 GiB; report MB as measured)
- sha all **`88bd7852…` PASS**

Incidental: `cell_local_2-01.py` refuse-uncapped before G sha; `G_SHA` → `88bd7852`.

## Close gates (trigger: build_alldata.py, cenc.py)

Close gate (a) full suite: 1486 passed, 9 skipped in 740.67s at d2de71a
Close gate (b) encode wall: median 37.38 s of 3 at -j4 (spread 1.43 s) vs baseline 37.38 s (plan 41 Contract H)
Close gate (c) sha gate: AU 88bd7852 PASS (3/3), Perth 04be2f6e PASS (-j4 baseline+cut+recycle)

## Codex review

1. First review at 65ce85c: **PASS-WITH-CONCERNS / HOLD** — Pool.map release not per-worker guaranteed; GiB/MB wording.
2. Addressed: pool recycle + MB wording; Perth/AU re-measured; suite at d2de71a.
3. Re-review: pending this close-out tip.
