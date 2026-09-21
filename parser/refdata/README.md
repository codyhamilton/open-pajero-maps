# parser/refdata/

Checked-in measurements derived once from the reference disc, plus one
manufacturer configuration frame carried byte-identical from it. Nothing
here is map content, and the map-layer build reads only these files, never
the mounted disc (see `docs/design/target-disc.md`, "Grid contract").

- `grid.json` — the reference disc's Parcel Data Management Distribution
  Header (PDMDH) coverage box, header fields (`lmr_size`, `bsmr_size`,
  `n_lmr`, `n_bsmr`, ...), the on-disc Level Management Record for every
  zoom level (12, 10, 8, 6, 4, 2, 0), and the Block Set Management Record
  list. Produced by `parser/extract_reference_data.py` from the mounted
  reference disc's `ALLDATA.KWI`
  (`/run/media/codyh/464210-8480/ALLDATA.KWI`, the user's imaged Mitsubishi
  Pajero MMCS "WhereIS" 2007 nav disc — see `docs/provenance.md`). Loaded
  by `parser/kiwiw/grid.py` (`ReferenceGrid`).
- `mht29_frame.bin` — the exact 2048 bytes addressed by management header
  record 29 (0-based; spec record 30, RESERVED), a manufacturer-defined
  language/country code list. Produced by the same script, from the same
  disc. Carried byte-identical into every generated disc (copy-through,
  per `docs/design/target-disc.md`), never regenerated.
- `profile/map.json` — full per-level census of the reference disc's map layer, judged
  against by `harness/checks/{vocab,envelope,mfde}.py`. Produced by
  `compare_disc.py --profile`.
- `parcel_mask.json` — per-level cell index bounds of the reference coverage.
- `harness.json` — count-ratio envelopes, the level-0 exemption, the container byte-diff
  allowlist and the path of the spot-check table. Loaded by `harness/`.
- `selection.json` — per-level OSM feature selection, calibrated to `profile/map.json` so
  build counts land inside the `harness.json` envelopes. Loaded by `kiwiw/selection.py`.
- `spot_checks.json` — city coordinates with expected street and place names, checked by
  `harness/checks/spotcheck.py`.
- `vocab/*.json` — OSM tag to code tables; see `docs/design/osm-vocabulary-mapping.md`.

Regenerate `grid.json` / `mht29_frame.bin` with:

```
.venv-rp/bin/python parser/extract_reference_data.py
```

A re-run against the same reference disc is byte-identical (sorted JSON
keys, fixed indent, trailing newline).
