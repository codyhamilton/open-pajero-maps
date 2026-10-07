# Plan 59 Phase 3 — Multi-kind free recipe

Standing: no Phase 3 product-close claim; no plan 04 P4–6 / 3-90; wrapper takes `output/.heavy.lock` (no outer `flock`).

## In-process (default)

`_finalize_dump(dump_dir, kinds, ntasks, log)` walks `kinds` **one at a time**:

1. Sort each part for that kind alone; write `.sorted_*` / `.key_*`; `del part, keys`.
2. K-way merge into `<kind>.bin`; unlink temps.
3. `gc.collect()` before the next kind.

Peak working set ≈ **largest part of the current kind** (+ key rows ~72 B/row + merge buffers). Prior kind arrays are not retained — only the small `counts` dict and the on-disk `<kind>.bin`.

`DUMP_KINDS` order is the product order (`name_anchor`, `background`, `background_boundary`, …). Callers that pass a subset still finalize sequentially.

## Fresh wrapper scopes (optional inter-phase)

When dump finalize follows another heavy band (encode / mass / control), prefer a **new** `run_heavy_python.py` scope so cgroup `memory.peak` resets:

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py \
  --log output/scratch-59/runs/finalize_run_wrapper.json -- \
  .venv-rp/bin/python -B parser/tools/bench_dump_memory.py finalize-run \
  --out output/scratch-59/runs/finalize_results.json
```

## Honesty bars

- Bytes / counts / `DUMP_ORDER` / part deletion match tip finalize candidate (finalize-run sha gates).
- Do not resurrect whole-file scratch extend; live path remains windowed `dump_join`.
