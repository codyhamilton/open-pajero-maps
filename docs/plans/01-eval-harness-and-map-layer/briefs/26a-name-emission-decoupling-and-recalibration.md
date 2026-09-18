# Brief: 26a — Decouple name emission from geometry admission; recalibrate per-level name_count

Consumer: implementation worker (code + tests; NO full rebuild, NO commit of a rebuild record).
Owned paths: `parser/kiwiw/selection.py`, `parser/refdata/selection.json`,
`parser/osm_to_parcel_geometry.py` (name-emission gates in `_handle_way`/`_handle_node` only),
`parser/tests/test_selection.py` (+ a new extractor name-gating test file). Do not touch
`parser/harness/`, `parser/build_alldata.py`, `parser/kiwiw/divide.py`, or PDMDH/assembler code
(another worker is editing those). Commit and push code+tests when `pytest parser/tests -q`
passes and the fixture build below is clean; do not clear `output/`.
Depends on: 25b, 26 design findings (this brief is the output of unit 26's design pass).
Runs alongside: 26c (parcel_count) -- disjoint files; 26 (kickoff) waits for both.

## Diagnosis this brief implements (25b `output/report.json`, envelope check)

name_count G/R: L0 1,759,290/19,081,105 (0.09x); L2 160,112/40,169 (3.99x); L4 79,089/4,042
(19.6x); L6 14,009/1,022 (13.7x); L8 13,937/209 (66.7x); L10/L12 0/8 (0x). link_count and
background_count are already in range at 2-8 (link 1.9x/2.0x/0.68x/1.35x). Cause: at levels 2-8
`_handle_way` (osm_to_parcel_geometry.py ~L851, `if name and any_link`) emits one NameRecord per
named admitted road way, so name_count == named-road count (L8: 14,004 motorway ways -> 13,937
names). R's levels 2-12 name census is place-type names only (type codes 306/308 family; see
`_make_name_record` docstring and briefs 11/23), i.e. R does not label roads at these levels.
Level 0 is the opposite: R has ~19M names (roads + POIs + place nodes), G only road/bg names.
Selection can therefore not fix this: dropping road classes breaks link_count. Names must be
gated independently of geometry, and the gate must go both directions.

## Changes

1. `selection.py`: extend the rule schema (backward compatible; absent key = current behaviour):
   - `road_names`: `true|false|[highway classes]` -- whether an admitted road way emits a
     NameRecord (and for which classes). Validate against the rule's own `highway` list.
   - `background_names`: `true|false|[{key,value}...]` analogous for background ways.
   - `name_nodes`: list of `{key,value}` (or `{key:"*"}`) named-node predicates admitted as
     name-only records, generalising `place` (keep `place` as an alias). Needed at level 0.
   - optional `name_cap_per_cell` (int): max names per parcel per record class, deterministic
     (keep highest priority, then lowest id) -- a safety valve only; not the primary lever.
   Expose `name_filter_way(level, tags, kind)` and extend the node gate; keep `level_filter`.
2. `osm_to_parcel_geometry.py`: call the new gates immediately before `_make_name_record` at the
   road (~L851), background (~L876) and node (~L794) sites. Geometry admission is unchanged.
   Do not touch `_make_name_record` vocab logic (briefs 11/22/23 own it).
3. Recalibrate `selection.json` from a tags-only dry run (extend `count_dry_run`; the existing
   `--dry-run` tooling, ~20-50s/pass, no rebuild) tallying candidate names per level:
   - L2-L8: `road_names: false`, `background_names: false`; names come from `place` nodes only.
     Target R: 40,169 / 4,042 / 1,022 / 209 (envelope x0.5..2). Tally `place` classes (and
     `natural` peaks/bays etc. if R's 306/308 census needs them -- check
     `parser/refdata/profile/map.json` levels[n].name.type_code_hist) and choose the smallest
     class set landing inside [0.5,2]x with margin; record the per-class tallies in each rule's
     `_calibration_note`. If L8 (R=209) has no class set inside the envelope, use
     `name_cap_per_cell`/a national top-N-by-priority cap; document as the chosen lever.
   - L0: R=19.08M. Currently 1.76M. Measure candidate tallies for: all named highways (already),
     named background ways (`background_names: true`), named place nodes (all `place=*`), named POI
     nodes (amenity/shop/tourism/historic/natural/leisure). Admit classes until within
     [9.54M, 38.2M]; keep within `_make_name_record`'s existing type-code vocab (brief 23) --
     omit rather than fabricate any class whose type_code is not in R's level-0 census.
   - L10/L12: R has 8 names, G 0: admit the place classes (e.g. `place=country|state|island|sea`
     as tallied) that yield 4..16 records; note this depends on the level-10/12 single-parcel
     cells (brief 19).
4. Tests: selection schema validation (bad `road_names` class, alias `place`, defaults preserve
   behaviour for the current table), extractor gating with a synthetic handler on a tiny tags
   set, and a regression asserting the *shipped* `selection.json` L8 rule yields zero road names.
5. Fast gate: `.venv-rp/bin/python -m pytest parser/tests -q`; `--fixture perth --levels 0 2 4 6 8`
   local build completes; report per-level fixture name/link counts vs ratios.

## Done evidence
pytest green; dry-run tally table (per level, per class, vs R and [0.5,2]x) in the report;
the committed `selection.json` note per rule; fixture build clean. Any level whose tally cannot
land in the envelope is named with its blocker (candidate deviation, see 26c/IMPLEMENTATION.md).

## Report back
Chosen lever per level and tallies; any level left outside the envelope and why; contradictions
found. Do not silently resolve contradictions with brief 20 (its "undershoot" amendment is wrong
for names: they overshoot at 2-8).

## Amendment (26a outcome)
Level 0 name_count is unreachable: the maximum OSM-derived total (all named roads, bg ways, place
and POI nodes) is ~1.98M vs a floor of 9.54M; all classes are admitted and the shortfall is a
declared deviation. The L10/L12 rule is satisfied by place=state|country|continent (8 records).
