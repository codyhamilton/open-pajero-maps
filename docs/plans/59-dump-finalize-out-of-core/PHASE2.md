# Plan 59 Phase 2 — Out-of-core finalize

Tip parent: `22a4797`. Decision from Phase 1: **proceed**.

## Change

`parser/tools/quantisation_roundtrip.py`:

- `_sortable_dump_keys` — order-preserving packed uint8 keys (signed XOR sign bit; IEEE float total-order map; unsigned BE) matching `np.argsort(..., order=DUMP_ORDER)`.
- `_finalize_dump` — per-part stable sort → sorted `.sorted_*` + `.key_*` side files → stdlib `heapq` k-way merge on key bytes with buffered writes → delete temps. Single-part fast path rename. `gc.collect()` after each kind.

No whole-file extend revival; live extend stays `dump_join`.

## finalize-run (flock via wrapper only)

| Arm | median max_rss_kib | median wall_s |
| --- | ---: | ---: |
| baseline (plan-05 concat) | ~473268 | ~1.01 |
| tip candidate (pre-59, one kind array) | ~201200 (plan 56) | ~1× class |
| **plan 59 candidate** | **~88880** | **~1.42** (ratio **1.406** vs baseline) |

Gates (3 pairs, 1 000 013 rows, 8 parts): exit0, rss_delta (≥140626 KiB), output_sha_equal, counts_equal, parts_deleted, median_wall_le_2x — **all PASS**.

SHA (cand≡base): `background_boundary.bin` `96c7b512…`, `dump_manifest.json` `240b7628…`. Counts `{background_boundary: 1000013}`.

Artifacts: `output/scratch-59/runs/finalize_results2.json`, `finalize_run_wrapper2.json`.

## Outcome

Landed. Peak below tip candidate (~89 MiB vs ~201 MiB). ARCHITECTURE deferred section → landed (plan 59).
