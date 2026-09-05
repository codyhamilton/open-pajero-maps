# Brief: 10 — Link identity `(osm_way_id, ordinal)`

Consumer: implementation worker.
Owned paths: `parser/link_id_registry.py`, `parser/kiwiw/model.py` (only: add an `ordinal`
field to `RoadLink`, default 0), `parser/tests/test_link_id_registry.py`, and in
`parser/osm_to_parcel_geometry.py` **only** the function that splits a way into per-parcel
chains (`split_polyline_by_parcel` and the `_make_road_link`-style constructor that
stamps `osm_way_id`) so each chain receives its ordinal. Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 08 (its extractor edits must land first; both touch that file).
Runs alongside: 09, 11 (11 touches the name path only — coordinate on `model.py`: 11 owns
`NameRecord`, this unit owns `RoadLink`).

## Required reading, in order

1. `docs/design/target-disc.md` — **Link identity** (settled: "A road link's identity is
   `(osm_way_id, ordinal)`, ordinal assigned at split time in the map-layer stage, and it is
   the same key in every layer that references a link. The registry keys on it; anything
   keyed on `osm_way_id` alone is a bug.").
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Why This Plan Exists" gap (8)
   (registry keyed `osm_way_id` first-in-wins).
3. `parser/link_id_registry.py`, `parser/tests/test_link_id_registry.py`.
4. `parser/osm_to_parcel_geometry.py` (after 07/08) — the split path.

## Goal

Every distinct chain a way produces after parcel splitting gets its own link ID, keyed on
the design doc's identity, so the RP layer (WP2) can address it.

## Contract

Design doc (settled, above). Ordinals are 0-based, assigned in chain order along the way's
node sequence at the moment `split_polyline_by_parcel` produces them, identical across
levels for the same way only when the split is identical (it is not; ordinals are per
level — record `(level, osm_way_id, ordinal)` if the registry is shared across levels, and
say so in the module docstring). The registry API: `assign(level, osm_way_id, ordinal) ->
link_id`, `lookup(...)`, and `items()` in deterministic order; two calls with the same key
return the same id; different ordinals for the same way return different ids.

## Changes

- `RoadLink.ordinal: int = 0` in `model.py`; nothing else in that file.
- Extractor split path stamps `ordinal` on each chain.
- Registry re-keyed; remove first-in-wins on `osm_way_id`.
- Tests: a way crossing two parcels yields two links with ordinals 0 and 1 and two ids; the
  same way re-registered gets the same ids; determinism across runs.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `grep -n "osm_way_id" parser/link_id_registry.py` shows no key that omits the ordinal.

## Report back

A short summary, anything you deviated from in this brief and why, and any contradiction
you found between this brief and the contracts it cites. **Do not resolve contradictions
silently — report them.**
