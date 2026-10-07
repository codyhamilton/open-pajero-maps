# Plan 58 Phase 2 — Drop-between-levels lands (sha-identical)

## Cut

1. `E1Spool.close()` closes underlying numpy memmap `_mmap` handles before nulling views.
2. `_e1spool` closes the previous level's spool when the cache key changes.
3. After each level in `run()`, `pool.map(_release_worker_encode_caches)` (or serial) + `gc.collect()`.
4. Parent drops `e1_out` row arrays before E2 stage.

No algorithm/EO/clip change. `-j4` max. Spill FDs remain until assemble.

## Perth harness (same host recipe)

| Arm | peak_rss_tree_mb | max_rss_kib | memory.peak | sha256 prefix | wall_s |
| --- | ---: | ---: | ---: | --- | ---: |
| baseline (tip f616059, pre-cut) | **13848.7** | **3413788** | **2426187776** | `04be2f6e…` | 4.29 |
| cut | **13165.0** | **3234696** | **1379713024** | `04be2f6e…` | 3.22 |

Gates: sha-identical **PASS**; RSS improved **PASS**; memory.peak improved **PASS**; tree improved (−683.7 MB).

Logs: `output/scratch-58/runs/{baseline_perth,cut_perth}/` + `*_wrapper.json`.

## Tests

`parser/tests/test_e1spool_level_release.py` — close nulls views; cache closes previous level.
