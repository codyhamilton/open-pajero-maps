# Report: 1-01 — Copy-through sibling cmp contracts

## Done against brief

- Disc roots: `Context.reference_root` / `generated_root`; CLI
  `_resolve_disc_paths` preserves directory or parent-of-`ALLDATA.KWI`.
- Check `copy_through_graphics` on layer `meta` covers the ten target-disc
  copy basenames; PASS / FAIL / NA semantics as briefed.
- Subsumed plan-22 `wp5_meta` (removed from `wp_na.py`); WP2–WP4 sentinels kept.
- Unit tests: discover, map-only NA, PASS identical stubs, missing-G FAIL,
  content mismatch FAIL, size mismatch FAIL, NA without reference root,
  disc-root resolution.
- Docs: `parameters-metadata.md`, `target-disc.md` Evaluation, `OVERVIEW.md`,
  `compare_disc.py` docstring.
- Default `harness.json` `layers_present` remains `["map"]`.

## Verification

```
.venv-rp/bin/python -m pytest \
  parser/tests/test_harness_copy_through_graphics.py \
  parser/tests/test_harness_map_only_honesty.py -q
# 13 passed
```

`py_compile` clean on touched modules. No encode, K1, cell_local, disc mount,
or real GRA/LOADING blobs.

## Departures

None material. Execute implemented Phase 1 inline (Flash assigned; one
bounded unit; refine skipped per design).

## Deferred

- Promoting `meta` into default `layers_present` stays with a future WP5
  copy-writer design.
- Live `cmp` on mounted R/G remains optional confirmation, not a gate.

## Problems

None.
