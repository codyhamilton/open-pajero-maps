# Brief: 1-01 — Copy-through sibling cmp contracts

## Outcome (from DESIGN Phase 1)

Harness discovers a check covering the ten target-disc copy basenames.
Default `layers_present=["map"]` → NA (not PASS). With layer present +
synthetic R/G disc roots: identical stubs → PASS; missing G basename →
FAIL naming the file; content/size mismatch → FAIL. Disc-root resolution
preserves sibling directories. Unit tests lock discover + NA + PASS +
missing-FAIL + mismatch-FAIL. Docs state missing copy-through files are
not successful copying when the layer is in scope.

## Choices (Execute)

- **Layer token:** `meta` (aligns with plan 22 `wp5_meta`; not `map`).
- **Check id:** `copy_through_graphics`.
- **Subsume:** replace the plan-22 `wp5_meta` NA-only sentinel with this
  real cmp check on the same layer (one WP5 row, not two). Keep
  `wp2_route` / `wp3_address` / `wp4_index` sentinels.
- **Roots:** Context exposes `reference_root` / `generated_root`. CLI
  preserves disc root when given a directory or an `ALLDATA.KWI` path
  (parent of ALLDATA). Bare non-ALLDATA file → root None → check NA.
- **No reference / missing roots:** NA (container precedent); never PASS.
- **Default `harness.json` `layers_present`:** stays `["map"]`.

## Surfaces

- `parser/harness/context.py` — `reference_root`, `generated_root`
- `parser/compare_disc.py` — disc-root resolution
- `parser/harness/checks/copy_through.py` — new check
- `parser/harness/checks/wp_na.py` — drop `wp5_meta`
- `parser/tests/test_harness_copy_through_graphics.py` — new
- `parser/tests/test_harness_map_only_honesty.py` — meta id update
- `docs/schema/parameters-metadata.md` — FAIL-when-in-scope note
- `docs/design/target-disc.md` and/or `docs/OVERVIEW.md` — one-liner

## Done evidence

- `registry.discover()` includes `copy_through_graphics` with `layer="meta"`.
- Under `layers_present=["map"]` the check is NA (CLI gate).
- Synthetic tmp R/G trees: identical → PASS; missing G file → FAIL with
  basename; one-byte mismatch → FAIL with basename + offset or size.
- `wp5_meta` no longer discovered; honesty tests still green for WP2–4.
- Default harness.json unchanged (`["map"]` only).
- No encode, K1, cell_local, real GRA blobs, WP5 writer, Phase 3 claim.

## Non-goals

No WP5 copy writer; no non-map default layers; no reseat 170 / 3-16 /
3-17; no plan 04 P4–6 / plan 06; no disc mount as acceptance.
