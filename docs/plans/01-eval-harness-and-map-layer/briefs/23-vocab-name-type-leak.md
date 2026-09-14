# Brief: 23 — Background type codes leaking into name-record `type_code` (ad hoc)

Consumer: implementation worker. This brief was authored by the orchestrator (not `refine`)
to resolve the `vocab` check FAIL from WP1 unit 15b's 2026-09-09 full-Australia build
(`docs/design/target-disc.md`'s `ALLDATA.KWI` map layer row): "name_type_code values
288/289/290/306/321/578 appear at levels where R's per-level census does not have them —
likely background-type codes leaking into name records' type_code field beyond R's own
per-level name vocabulary, and `bg_type.json`'s `railway=rail → 578` rule at level 0 in
particular has no corresponding entry in R's level-0 name census". It is not part of the
original 01-15b dispatch list; dispatch it independently.

Owned paths: TBD by whoever picks this up — likely a new `parser/refdata/vocab/name_type.json`
(unit 08's pattern) plus the `kind="background"`/`kind == level>0` branches of
`_make_name_record` in `parser/osm_to_parcel_geometry.py`, and `parser/tests/test_vocab.py`
plus whichever name-record tests cover `_make_name_record`. Do not touch unit 08's
`road_type.json`/`display_class.json` or their call sites, unit 14's `selection.json`, or
any harness check other than `vocab.py` (read-only there; it's already correct — it censuses
R faithfully and correctly flagged this).

## Required reading, in order

1. `docs/design/target-disc.md` — the `ALLDATA.KWI` map layer row (search "vocab") for the
   FAIL text quoted above, and "Vocabulary is data, not code" (settled: mapping tables from
   OSM tags to KIWI road types, display classes, **background types and name string types**
   are checked-in data with a coverage test against R's censused vocabulary).
2. `docs/plans/01-eval-harness-and-map-layer/briefs/08-vocab-mapping.md` — the vocab-table
   contract. Note its owned-paths list built `road_type.json`, `display_class.json` and
   `bg_type.json` only; there is no `name_type.json` and never has been.
3. `docs/plans/01-eval-harness-and-map-layer/briefs/11-name-types.md` and
   `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`'s "Unit 11 — Name records:
   string types 4/5/6 at level 0" section. Unit 11's evidence base was **level 0 only**,
   from 7 sampled state-capital CBD parcels (`parser/refdata/spot_checks.json`): road names
   get `string_type=5`, fixed `type_code=0x210` (528) — confirmed against the full census.
   Background-attached names (its one example: "PRINCES PARK") get `string_type=6`,
   `type_code=` the feature's own background type code — confirmed for exactly one sample
   (park, code 321), then generalized in code to *every* `bg_type` value, at *every* level.
4. `parser/osm_to_parcel_geometry.py` — `_make_name_record` (~line 530) and its two
   background-way call sites: line ~776 (`_handle_way`, background branch) passes
   `type_code=bg_type` unconditionally for every level, not just level 0. Inside
   `_make_name_record`, the `level == 0 and kind == "background"` branch (evidenced, per unit
   11) and the catch-all `else` branch for `level != 0` (`string_type=1`,
   `chosen_type_code=type_code`, i.e. still `bg_type` — **never evidenced at all**, added
   incidentally by falling through the same parameter rather than by any unit's cited
   evidence).
5. `parser/harness/checks/vocab.py` — the check itself (already correct; do not change its
   logic). It compares generated `name.type_code_hist` keys per level against
   `ref_profile.levels[level].name.type_code_hist` keys, i.e. R's real name-record type-code
   census per level.
6. `parser/refdata/vocab/bg_type.json` and `parser/refdata/vocab/README.md`'s `bg_type.json`
   section, for the `railway=rail → 578` rule (level 0, added by unit 08 after unit 11 froze
   its evidence — unit 11 never had the chance to check 578 against real name records).
7. `parser/refdata/profile/map.json` — `levels[level].name.type_code_hist` and
   `levels[level].background.type_code_hist`, per level. This is the ground truth; see
   "Findings" below for what it actually shows.

## Findings (already done — do not re-derive, but do double check against a fresh profile.json if it has moved on)

Comparing R's per-level `name.type_code_hist` keys against `background.type_code_hist` keys
in the committed `parser/refdata/profile/map.json`:

| level | R's real name type_code set | R's background type_code set | overlap |
|---|---|---|---|
| 0 | {0,2,3,5,6,7,8,9,10,12,288,289,290,291,321,322,455,509,528,640,642,1024} | {288,289,290,291,321,322,**578**,640,1024} | {288,289,290,291,321,322,640,1024} — **578 is the one bg code that's genuinely absent from R's name census** |
| 2 | {308,509,528} | {288,289,290,291,321,322,578,640,1024} | **empty** |
| 4 | {308,509} | {288,289,290,291,321} | **empty** |
| 6 | {308,509} | {288,289,290,291,321} | **empty** |
| 8 | {306,308} | {288,289,290,291,321} | **empty** |
| 10 | {308} | {289,306,528} | **empty** |
| 12 | {308} | {289,306,528} | **empty** |

Two distinct problems, not one:

1. **Level 0**: bg-type-as-name-type-code is *mostly correct* (unit 11's generalization from
   one sample happens to hold for 288/289/290/291/321/322/640/1024), except the
   `railway=rail → 578` rule (added by unit 08, after unit 11's evidence pass) — R's level-0
   name census has no `type_code=578` record at all. `578` should never reach a name record
   at level 0, regardless of what it's legitimately used for on background shapes.
2. **Levels 2–12**: the entire mechanism is wrong, not just one code. R's real name records
   at these levels carry type codes {306, 308, 509, 528} — a completely disjoint set from
   every background type code the current tables emit at those levels. Background type and
   name type are evidently *unrelated* namespaces once you leave level 0: whatever governs a
   name record's type_code at levels 2–12 is not "the type of the background shape it's
   attached to". None of 306/308/509/528 are documented anywhere in this plan (`DESIGN.md`,
   `roadtypes.py`, `bg_type.json`'s README) — this needs fresh format analysis against
   Ch.7.A, the same way unit 08 derived `bg_type.json`'s values, to work out what a name
   record's type_code actually encodes at these levels (a road-name-class code, an
   overview-scale label-priority code, something else — unknown).

This is why it's an ad-hoc brief rather than a same-turn fix: it's not a bug in the sense of
"code doesn't do what was intended" — `_make_name_record`'s `else` branch faithfully does
what unit 11 wrote, it's just that unit 11's one-sample evidence never covered levels 2–12
or the (later-added) `578` rule, and closing the gap requires the same kind of
census-grounded format analysis unit 08 did for `bg_type.json`, not a one-line fix. It also
touches the unit 08/unit 11 shared boundary (whether background-type and name-type are one
vocabulary or two) and needs sign-off before implementation.

## Goal

Give name records at every level a `type_code` that is a genuine subset of R's per-level
`name.type_code_hist`, replacing the current "reuse whatever `bg_type` resolved to"
mechanism wherever it doesn't hold.

## Open questions to resolve before/while implementing

- Is a `name_type.json` vocab table (unit 08's JSON schema, `kiwiw/vocab.py`'s existing
  `load`/`lookup`/`emitted_values`) the right shape for this, keyed by OSM tag like the
  other three tables? Or, for levels 2–12 in particular, is the real driver not the feature's
  OSM tags at all but something structural (e.g. road class, or the background shape's role
  at that zoom) that the current per-way call site doesn't have access to?
- At level 0: should the fix be as narrow as "578 is bg-only, scope it out of the name-record
  call site" (keep the rest of unit 11's carry-through as is, since it matches census), or
  does the fact that one bg_type rule was already wrong for names argue for an explicit
  name-type allowlist/table at level 0 too, so the next new `bg_type.json` rule can't
  silently break this again?
- At levels 2–12: what do 306/308/509/528 mean? Requires Ch.7.A analysis
  (`spec/format_english/pdf/07A1122e.pdf`), the same method unit 08 used for `bg_type.json`
  (see its README's per-code table), applied to name records instead of background shapes.
  Until that's answered, there's no principled value to assign — the current code's
  `else` branch has no evidence for *any* value, so simply picking one bg_type-derived
  default would just replace one unevidenced guess with another.
- Should `_make_name_record`'s `type_code` default parameter (currently `0x134`, itself
  unvalidated per its own docstring's "place" branch discussion) be revisited at the same
  time, or left alone as an orthogonal open question?

## Contract

Whatever table/logic results must pass `vocab.py`'s existing check unchanged (it already
implements the correct comparison — R's per-level `name.type_code_hist` as the subset
bound) and must not weaken it. Prefer omitting a name record entirely (background shape
still emitted, no attached name) over emitting one with a type_code that isn't in R's
per-level census, consistent with unit 08's own precedent for `bg_type.json`'s `null`
default ("omit the feature ... rather than fabricate a plausible value").

## Done evidence

- `.venv-rp/bin/pytest parser/tests/ -q` → all pass.
- `.venv-rp/bin/python parser/compare_disc.py --checks vocab` (or the harness's standard
  invocation) on a full-Australia (or representative multi-level) build → `vocab` check
  PASS, specifically no `name_type_code` offenders at any level.

## Report back

A short summary, anything you deviated from in this brief and why, and any contradiction
found between this brief, `DESIGN.md`, and the code. In particular report what 306/308/509/528
turned out to mean, since nothing in this plan currently documents them.
