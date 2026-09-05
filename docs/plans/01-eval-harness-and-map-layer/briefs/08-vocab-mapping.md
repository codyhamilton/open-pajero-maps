# Brief: 08 — Data-driven OSM → KIWI vocabulary tables, per level

Consumer: implementation worker.
Owned paths: `parser/kiwiw/vocab.py` (new), `parser/refdata/vocab/` (new: `road_type.json`,
`display_class.json`, `bg_type.json`, `README.md`), `parser/tests/test_vocab.py` (new), and in
`parser/osm_to_parcel_geometry.py` **only** the bodies of `HIGHWAY_TO_ROAD_TYPE`,
`HIGHWAY_TO_DISPLAY_CLASS`, `_osm_tags_to_bg_type` and the two call sites that use them
(replace with `vocab` lookups; no other edits to that file). Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 03 (the per-level vocabulary census), 07 (the extractor's call-site seam).
Runs alongside: 06, 09.

## Required reading, in order

1. `docs/design/target-disc.md` — **Vocabulary is data, not code** (settled: "The mapping
   tables from OSM tags to KIWI road types, display classes, background types and name
   string types are checked-in data with a coverage test against `R`'s censused vocabulary,
   not literals in a converter."); check-table row **Same vocabulary**.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Open Questions → Refinement
   findings (2026-09-05)": `R`'s level-0 road types include 8 and display classes reach 12;
   levels 2–8 use road types {0,2,3} and DCs {9,10,12}; the current synth tables (types
   0..7, DCs 0..3) are off.
3. `parser/refdata/profile/map.json` — `road_type`, `display_class`, `bg_type` histograms per
   level.
4. `spec/format_english/pdf/07A1122e.pdf` — Ch.7.A road type / display class definitions
   (what each numeric value means on the disc).
5. `parser/osm_to_parcel_geometry.py` — the three mapping sites (after unit 07).

## Goal

Replace the hard-coded tag→code literals with checked-in tables whose emitted vocabulary
per level is a subset of the reference's, with a test that proves it.

## Contract

Design doc (settled, above). Refine's calls: tables are keyed by level range so one file
covers all seven levels: `{"levels": [[0,0],[2,8],[10,12]], "rules": [{"levels": 0,
"match": {"highway": ["motorway","trunk"]}, "value": 3}, ...], "default": <value or null>}`
— first matching rule wins, `null` default means "omit the feature at this level" (this is
the *type* mapping only; unit 14 decides selection, so keep the default non-null wherever
`R` has a plausible code). `kiwiw/vocab.py` exposes `load(name) -> Vocab` and
`Vocab.lookup(level, tags) -> int | None`, plus `Vocab.emitted_values(level) -> set[int]`.
The coverage test asserts `emitted_values(level) ⊆ profile.vocab[level]` for every level and
every table, reading the profile JSON directly.

The value assignments themselves are format analysis: use Ch.7.A's definitions to map each
OSM `highway` class to the type/DC that `R` uses for the corresponding real-world road
class (motorway/trunk/primary/secondary/tertiary/residential/service/track/unclassified,
plus `oneway`/`junction=roundabout` if the type table distinguishes them), and `landuse`/
`natural`/`water`/`building` to `R`'s background types. Where Ch.7.A is unclear, prefer the
value whose profile frequency at that level is closest to that OSM class's share of the
extractor's spool statistics (unit 07's report). Record each non-obvious choice in the
`README.md` with the spec citation.

## Changes

- `parser/refdata/vocab/*.json` + `README.md` (table format, per-value rationale).
- `parser/kiwiw/vocab.py` loader with validation (levels cover 0..12 even, values ints).
- Call-site swap in the extractor; delete the three literal tables.
- `parser/tests/test_vocab.py`: coverage-vs-profile test per table and level; a lookup test
  for one rule per level range; a test that the loader rejects an overlapping level range.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass, including the coverage test.
- `grep -n "HIGHWAY_TO_ROAD_TYPE\|HIGHWAY_TO_DISPLAY_CLASS" parser/` → no hits outside `refdata/vocab/README.md`.
- Running the extractor on the Perth fixture (`--fixture perth --levels 0 2`) and `compare_disc.py --checks vocab` on the resulting single-level build (use the existing `build_alldata.py --levels 0` path as it stands; do not modify it) → `vocab` PASS at level 0.

## Report back

A short summary: the tables' rationale for the non-obvious values, the coverage numbers,
anything you deviated from in this brief and why, and any contradiction you found between
this brief and the contracts it cites. **Do not resolve contradictions silently — report them.**
