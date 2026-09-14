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

## Resolution (implemented, 2026-09-14)

**What 306/308/509/528 turned out to mean.** `parser/kiwiw/roadtypes.py`'s own module
docstring already says `BACKGROUND_TYPE_CODES` (the 16-bit "Type Code" field) is shared
between background shapes (7.3.2.2.1) *and* name records' Attribute 2 field (7.4.1) — one
vocabulary, not two, contra this brief's framing of "two distinct problems" at levels 2-12.
Cross-referencing the four mystery codes against that table: 306 = 0x132 = "address level 2
(state)", 308 = 0x134 = "address level 4 (municipality)", 528 = 0x210 = "road type 0" — all
three are already-documented `BACKGROUND_TYPE_CODES` entries (and 306/528 already appear in
`bg_type.json`'s own levels-10/12 rules for admin boundaries and roads-as-background). Only
509 (0x1FD) remains unexplained — it doesn't match any `BACKGROUND_TYPE_CODES` entry,
including the neighbouring documented 0x1FE=510 ("information highway symbol"); left
unaddressed (no code ever emits it, which is allowed — the check is a subset bound, not
completeness).

**Root cause, more precisely than the brief's two-problem framing.** `_make_name_record`'s
`else` branch (level != 0) is not background-only: it is also the path for `kind="road"`
and `kind="place"` names at every level 2-12, since only `level == 0` has kind-specific
branches. Auditing all three:
- `kind="road"`: the call site never passes `type_code`, so the function's own default
  parameter (`0x134` = 308) is used — and 308 is in R's real per-level name census at
  *every* level 2-12. This path was already correct, by accident of the default parameter
  value, and needed no change.
- `kind="background"`: the call site passes `type_code=bg_type`, which — as the brief's
  findings table shows — is wholly disjoint from R's per-level name census at every level
  2-12. Confirmed wrong at every level, not just via one bad code the way level 0 is.
- `kind="place"` (`_handle_node`, suburb/city/town/village/locality points): **not audited
  by this brief's original findings section at all**, but it goes through the same `else`
  branch. `_handle_node` passes `type_code=0x134` (308) for `place=suburb`, `0x132` (306)
  for every other admitted value. 308 is always safe (see above). 306 is only in R's
  per-level name census at level 8 — and `parser/refdata/selection.json` (read-only per
  this brief's own owned-paths list, not modified) currently never admits a place node at
  level 8 (its own calibration note confirms: only `place=suburb`/308 is reachable there);
  every level `selection.json` *does* admit a non-suburb place at (2: city/town, 4: city,
  6: city) has a name census without 306. So this is a second, real leak of exactly the
  same shape as the background one, found while implementing rather than in the brief's own
  findings pass.

**Implementation.** No new `parser/refdata/vocab/name_type.json` table — the "open
questions" section's own alternative reading turned out to be right: for levels 2-12, no
table keyed by OSM tags (unit 08's shape) is evidenced, because the extractor's background
and place call sites have no reliable, evidenced way to choose *which* of the shared
vocabulary's values (306 vs. 308 vs. 528 vs. something unobserved) applies to a given
feature — R's real per-level name type_code appears to be driven by the feature's
real-world class (state boundary, municipality boundary, road), not by whatever background
shape or place tag happens to produce the name at that zoom, and this extractor's call
sites don't carry that classification. Rather than fabricate one, `_make_name_record` now
returns `None` (omit the name record; the underlying shape, if any, is unaffected) in
exactly three cases, each with an evidenced reason recorded in the function's own
docstring/inline comments:
1. `level == 0, kind == "background", type_code == 578` (the one bg-only code from the
   brief's own findings).
2. `kind == "background"` at any level other than 0 (the entire mechanism, per the findings
   table).
3. `kind == "place"` at any level other than 0 when `type_code == 0x132` (306) — the leak
   found during implementation, not in the brief's own findings.

Both call sites (`_handle_node`, `_handle_way`'s background branch) were updated to skip
spooling when `_make_name_record` returns `None`; the road-name call site was updated too
for symmetry/future-proofing even though `kind="road"` never actually returns `None` today.

**Deviation from the brief's owned-paths hint.** The brief's owned-paths paragraph names
"the `kind="background"`/`kind == level>0` branches" — read narrowly this could mean only
the background branches, but the `place` fix above is inside the same `level != 0` `else`
branch the brief already names, is required by the brief's own Contract ("every level" must
be a genuine subset, not just backgrounds), and does not touch `selection.json` or any
other file outside the brief's stated boundaries. Included as in-scope; flagged here rather
than silently expanded.

**Verification.** `.venv-rp/bin/pytest parser/tests/ -q` → 235 passed (up from 228 before
this brief: 7 new tests in `parser/tests/test_name_record_vocab.py`, plus
`test_extractor_scale.py`'s existing per-level name-count assertions updated for the new
omission behaviour). A full-Australia rebuild was not re-run here (the 2026-09-09 run this
brief cites took 1:27:24 wall time; out of proportion to re-verify a logic-level fix). In
its place: a small synthetic PBF exercising every changed path (a `place=suburb` node, a
`place=city` node, a `natural=water` background way with a name, a `railway=rail`
background way with a name — the exact case that produces bg_type 578 at level 0 — and a
`highway=residential` road with a name) was run through the real pipeline
(`osm_to_parcel_geometry.py` → `build_alldata.py` → `compare_disc.py --checks vocab`) at
levels 0/2/4/6/8/10/12 using the real `selection.json`/`bg_type.json` tables (unmodified) —
`vocab` check: **PASS** at every level, with the level-0 output profile showing 578 (the
railway background) correctly present on the background shape but absent from the name
records, and the level-2 output showing zero name records for the admitted `place=city`
node (previously would have leaked `type_code=306`). This is not a substitute for the
full-country done-evidence command, which whoever next runs a full-Australia build should
still execute to close this brief out with the originally-specified evidence; recorded here
as "representative multi-level build" per the brief's own Done-evidence alternative.

**Still open.** 509's real meaning is unknown (never emitted by this fix — allowed under
the subset contract, but a completeness gap). Whether R's real name-record type_code for
admin boundaries/roads at levels 2-12 is actually driven by real-world feature class (as
inferred here) rather than something else entirely is inferred from code-table matching,
not confirmed by decoding real per-record data — a genuine format-analysis question this
brief originally called for and this resolution does not fully close, though it does close
the concrete `vocab` check FAIL by construction (omission, not guessing).
