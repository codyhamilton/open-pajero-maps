# Plan 58 implementation record

Run identity: Open Pajero Maps Execute (Grok Bot), host codyh-ubuntu, started 2026-10-08 ~00:48 AEST.
Design: box `58-encode-level-residency-drop/DESIGN.md` → `docs/plans/58-…/DESIGN.md`.
Seat: **Codex** CLI 0.160.0 (CHM soft-move; no Flash). No seat ask.
Heavy: `run_heavy_python.py` (wrapper takes flock — no outer flock). Encode `-j4`. Caps plan-25. Live oracle `88bd7852`. No plan 04 P4–6; no 3-90. No Phase 3 product-close claim.

## Phase 1 — Encode residency classes named — DONE

See `PHASE1.md`. Plan 56 encode rows cited. Dominant: worker Pool j=4 co-resident (tree ≫ wrapper). Cut target: E1Spool not closed across levels (mode `"c"` COW → anon hypothesis). Tree peak alone = inventory.

## Phase 2 — Drop-between-levels — DONE

See `PHASE2.md`. `E1Spool.close` hardens mmap release; `_e1spool` closes prior level; post-level `pool.map(_release_worker_encode_caches)`; early `del e1_out`.

Perth `-j4` same-host harness:

| Arm | tree_mb | max_rss_kib | memory.peak | sha |
| --- | ---: | ---: | ---: | --- |
| baseline | 13848.7 | 3413788 | 2426187776 | `04be2f6e…` |
| cut | 13165.0 | 3234696 | 1379713024 | `04be2f6e…` |

## Phase 3 — AU confirm — DONE (no product-close claim)

AU `-j4` ×3 under wrapper+bench_build → `output/scratch-58/runs/au{1,2,3}/`:

- walls_s: [39.27, 37.53, 37.77] → **median 37.77 s of 3 at -j4 (spread 1.74 s)** vs baseline **37.38 s** (plan 41 Contract H median)
- tree peaks MB: [15308.6, 15179.3, 15364.6] (max 15364.6)
- sha all **`88bd7852…` PASS** (live oracle)
- Perth sha gate **`04be2f6e…` PASS** (Phase 2)

Incidental suite fix: `cell_local_2-01.py` refuse-uncapped before G sha; `G_SHA` pin → `88bd7852` (stale `4ed9cd80` after plan 48).

## Close gates (plan 41 trigger: `build_alldata.py`, `cenc.py`)

Close gate (a) full suite: 1486 passed, 9 skipped in 745.41s at 77b8598
Close gate (b) encode wall: median 37.77 s of 3 at -j4 (spread 1.74 s) vs baseline 37.38 s (plan 41 Contract H)
Close gate (c) sha gate: AU 88bd7852 PASS (3/3), Perth 04be2f6e PASS (-j4 baseline+cut)

## Codex review

Pending after this IMPLEMENTATION land.
