# Plan 57 Phase 2 — Cache bound / chunk-stream cut

## Mechanism (after Phase 1: spool caches dominate growth)

Primary levers landed on tip:

1. **`--cache-clear-every N`** (mass default 50; control now wired, default 50) → `leaf_io.clear_spool_caches`.
2. **`--cache-max-cells N`** (default **4096**) → `set_spool_cell_cache_max`; `_maybe_bound_cell_cache` clears `_SPOOL_CELL_CACHE` when over max (keys kept — small).
3. **`set_refuse_whole_level(True)`** on mass/control startup — `spool_level_cells` raises (cell-keyed `_spool_cell` only).
4. **`spool_cache_stats()`** for tests/harness.

No OE/cover change. No R bump. No chunk-worker split required this phase (clear-every + max-entries suffice; resume already limits loss to unfinished leaves).

## KiB target (named leaf-window harness)

Window: `mass_decide --r 8 --smoke-leaves 20` (535 rows / 20 cells), same tip discs+spool.

| Arm | cache_clear_every | cache_max_cells | max_rss_kib | memory.peak | wall_s |
| --- | ---: | ---: | ---: | ---: | ---: |
| **pre-cut baseline** | 0 | 0 | **1296152** (~1.24 GiB) | **1350627328** | 70.0 |
| **cut** | 10 | 512 | **1066356** (~1.02 GiB) | **1084850176** | 113.0 |

Gate: cut **below** baseline on both RSS and `memory.peak` — **PASS** (Δrss −229796 KiB; Δpeak −265777152 bytes).

Logs: `output/scratch-57/runs/harness_{baseline,cut}.json` (gitignored scratch).

## Tests

`parser/tests/test_leaf_io_spool_cache_bound.py` — 4 passed:
- clear drops key+cell entry counts
- max-entries bounds cell cache
- without max, cache grows
- refuse whole-level

## Decision / resume honesty

- Baseline vs cut decision rows: **535/535 identical** (decision, producer_class, recover_r).
- `--resume-from` cut decisions on same smoke window: leaves 20→0, new rows **0** (`RESUME_OK`).

## Surfaces

- `leaf_io.py`, `mass_decide.py`, `control.py`
- test above; this note
