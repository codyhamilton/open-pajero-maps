# OSM tag → KIWI vocabulary tables

Checked-in data (`docs/design/target-disc.md`, "Vocabulary is data, not
code"). Loaded by `parser/kiwiw/vocab.py`; format documented in that
module's docstring. Coverage against the reference census
(`parser/refdata/profile/map.json`) is enforced by
`parser/tests/test_vocab.py`.

## Format-analysis limitation (read this first)

`spec/format_english/pdf/07A1122e.pdf` (Ch. 7.A), the source this brief
cites for "what each numeric value means on the disc", **has no numeric
road-type or display-class code table**. Section 7.A.1 is titled "Road
Type" but the extracted text jumps straight from that heading to 7.A.2
("Divided/Integrated Parcels (added in future)") with no body content —
either the table was an embedded image `pdftotext`/this tool's PDF reader
cannot extract, or this revision of the archived spec genuinely ships
that section empty (unlike 7.A.2/7.A.3, 7.A.1 carries no "added in
future" marker, so the empty content looks like a spec artefact, not a
placeholder). `parser/kiwiw/roadtypes.py`'s module docstring already
recorded this exact finding from an earlier pass. No later section of the
27-page PDF (7.A.2 through 7.A.11, `Input for ISO Physical Storage
Format`) defines these codes either — the rest of the chapter is entirely
about multilink connectivity rules, link IDs and route-planning
correspondence, not per-value semantics.

Given that, every value assignment below is derived from two other
sources, in order of trust:

1. `parser/kiwiw/roadtypes.py`'s existing labels, themselves sourced from
   `kiwiread.c`'s render-color comments (informal notes, not spec text;
   that module's own docstring already flags them "confidence:
   low/guessed"). Only road_type 0 ("highway (expressway)") is used here
   with any confidence, because it is the only code the profile's rarity
   ranking also supports as this project's own best current guess for
   "motorway".
2. **Profile frequency**, cross-referenced against `road_type_hist` and
   `display_class_hist` in `parser/refdata/profile/map.json`. This is the
   brief's fallback method ("prefer the value whose profile frequency ...
   is closest to that OSM class's share"), used here as the *primary*
   method because (1) barely covers half the observed codes and (2) no
   OSM-side highway-tag frequency table exists yet — unit 07's own report
   (`docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, "Unit
   07") records way/node counts and per-level parcel counts, not a
   highway-tag histogram of the Australia PBF. **This is a second,
   separate contradiction with the brief**, reported alongside the
   spec-content one above: the brief asks to compare "that OSM class's
   share of the extractor's spool statistics (unit 07's report)" against
   the profile, but that report contains no such per-highway-tag
   breakdown to compare against. Absent it, assignment here uses only the
   reference-side frequency ranking (assume rarity ⇔ road-class
   importance, which is directionally reasonable but not independently
   confirmed against actual OSM tag counts for this PBF).

**Net effect: every value below is best-effort format analysis with
stated but unverified confidence, not a spec citation.** Treat mismatches
as expected until either an image-OCR pass on `07A1122e.pdf` page 1 turns
up hidden table content, or in-vehicle testing (or a later unit) falsifies
a specific value.

## `road_type.json` / `display_class.json`

Level 0's reference census (`profile/map.json`, `levels."0".road.road_type_hist`)
has exactly 10 distinct road_type codes: `{0, 2, 3, 5, 6, 7, 8, 9, 10, 12}`.
That is a near-exact match for the 9 real-world OSM highway classes named
in this brief (motorway/trunk/primary/secondary/tertiary/unclassified/
residential/service/track) plus one spare. Assignment: sort the 9 classes
by real-world importance (motorway most important/rarest ... service/track
least important/most common) and match them against the 9 non-trivial
codes sorted by ascending census count, anchoring code 0 = motorway on
`roadtypes.py`'s existing (low-confidence) label. Code `12` (39 occurrences
at level 0, the single rarest code, well below even code `0`'s 18,241) is
left **unassigned** — its count is too small relative to any real highway
class's expected share to be a plausible class anchor, and no rule in
either table maps to it; this is flagged, not resolved.

| road_type | level-0 count | OSM class(es) |
|---|---|---|
| 0 | 18,241 | motorway, motorway_link (roadtypes.py: "highway (expressway)") |
| 10 | 1,772 | trunk, trunk_link |
| 7 | 38,493 | primary, primary_link |
| 8 | 71,032 | secondary, secondary_link |
| 3 | 370,408 | tertiary, tertiary_link |
| 5 | 374,388 | unclassified, road |
| 6 | 3,046,886 | residential, living_street |
| 9 | 5,127,756 | service, busway |
| 2 | 848,884 | track |
| 12 | 38 | *(unassigned)* |

**display_class is derived, not guessed.** Level 0's
`display_class_hist` sums line up *exactly* against the road_type
assignment above once two DC codes are read as grouping two road types
each: `DC 7 = 3,421,274 = road_type 6 (3,046,886) + road_type 5
(374,388)`; `DC 2 = 5,127,794 = road_type 9 (5,127,756) + road_type 12
(38)`. Every other DC code equals exactly one road_type's count
(`DC 12 = road_type 0 = 18,241`; `DC 0 = road_type 10 = 1,772`; `DC 3 =
road_type 8 = 71,032`; `DC 4 = road_type 7 = 38,493`; `DC 9 = road_type 3
= 370,408`; `DC 10 = road_type 2 = 848,884`). This is real evidence (exact
integer sums over ~10M records, not a coincidence) that R's display_class
is a deterministic function of road_type at level 0, grouping
{tertiary, residential} → one DC and {service, the unassigned code 12} →
another. It is used directly rather than re-derived from OSM class
importance. Note the resulting DC ordering is **not** monotonic with
real-world road importance (motorway → the *highest* DC value 12; trunk →
the *lowest*, 0) — this contradicts the previous code's assumption
(`HIGHWAY_TO_DISPLAY_CLASS`'s comment "0 = most prominent, higher =
less"). Flagged as a genuine finding: whatever `display_class` encodes on
this disc, it is not a simple prominence rank in the direction the old
code assumed.

**Levels 2–8** (one range in the table, `[2, 8]`): the census road_type
set narrows to `{0, 2, 3, 7, 10, 12}` at level 2 and `{0, 2, 7, 10}` at
levels 4/6/8; display_class narrows to `{0, 4, 9, 10, 12}` / `{0, 4, 10,
12}`. Because one table row must be safe for every level in `[2, 8]`, the
rules use the **intersection** across 2/4/6/8: road_type `{0, 2, 7, 10}`,
display_class `{0, 4, 10, 12}`. `motorway→0`, `trunk→10`, `primary→7`
keep their level-0 meaning (plausible: an overview/route-network tier
naturally keeps the top of the class hierarchy); every other class
(secondary through track) collapses into code `2` (display_class `10`) —
a lossy many-to-one generalisation with no direct evidence beyond "it's
in the allowed set and the census gives no finer signal at this scale".
**This directly contradicts `PLAN.md`'s "Refinement findings
(2026-09-05)"** ("levels 2–8 use road types {0, 2, 3} and display classes
{9, 10, 12}") — the actual committed profile (required reading #3, which
postdates that refinement pass and is the authoritative census per unit
03b) shows different sets at every level in that range (see the "Report
back" section of this unit for the exact numbers). This unit follows the
profile, not the stale `PLAN.md` prose, per the brief's own instruction to
build "a coverage test against `R`'s censused vocabulary" — but the
mismatch is reported here, not silently corrected in `PLAN.md`.

**Levels 10/12**: the census has zero road links at these levels
(`link_count: 0`, empty histograms) — no plausible code exists, so both
tables declare the `[10, 12]` range (required for the loader's "cover
0..12 even" validation) with no rules and rely on the table's `default`
(`null`) to omit road features entirely at these levels.

**Schema limitation found while implementing**: the brief's format has
one `"default"` field per file, but the correctly required per-range
default differs — `null` at `[10, 12]` (nothing plausible) vs. "non-null
wherever plausible" at `[0, 0]`/`[2, 8]`. A single global default cannot
satisfy both without either (a) fabricating a plausible value at levels
10/12 that seeds a nonzero `emitted_values(10)`/`emitted_values(12)`,
breaking the coverage test against R's empty per-level histograms, or (b)
losing the non-null fallback at levels 0/2-8. Resolved here by making the
`[0, 0]`/`[2, 8]` rule lists *exhaustive* over the extractor's `ROADS` set
(so the global default, `null`, is never actually reached for a road
feature) rather than leaning on `"default"` for those ranges. `bg_type`
uses the same exhaustive-rules approach but via an explicit catch-all
rule (`"match": {}`, which matches unconditionally) at the end of each
of its `[0, 0]`/`[2, 8]` rule lists, because unlike the two road tables
its rule set is not naturally exhaustive over every OSM tag combination.
Reported as a brief/schema contradiction, not resolved by changing the
schema.

## `bg_type.json`

Level 0's `background.type_code_hist` set is `{288, 289, 290, 291, 321,
322, 578, 640, 1024}` — a **different code space** from the values the
previous `_osm_tags_to_bg_type` emitted (`0x131`/`0x132`/`0x134` for
admin boundaries, `0x464`/`0x480`/`0x408`/`0x6180` for
university/hospital/cemetery/golf): none of those six codes occur in R's
level-0 background census at all. Only `0x280`=640 (airport) was already
correct.

| code (dec) | code (hex) | roadtypes.py label | OSM source used here |
|---|---|---|---|
| 289 | 0x121 | water system (shore/ocean/bay/sea/creek) | `natural=coastline/bay/sea/ocean` |
| 290 | 0x122 | water system (lake/marsh/pond) | `natural=water/wetland`, `landuse=reservoir` |
| 291 | 0x123 | water system (river) | `natural=river/stream`, `waterway=river/stream/canal` |
| 321 | 0x141 | green belt, park | `natural=wood/scrub/heath`, `landuse=grass/meadow/farmland/forest`, `leisure=park` |
| 322 | 0x142 | factory, factory site | `landuse=industrial` |
| 578 | 0x242 | very high speed railway / JR line | `railway=rail` (not previously mapped at all) |
| 640 | 0x280 | other airport | `aeroway=aerodrome` (unchanged from before) |
| 288 | 0x120 | *(undocumented in roadtypes.py; between "unknown 10x" and "water 0x121")* | catch-all default: `building=*`, admin boundaries, university/hospital/cemetery/golf/leisure, and anything else not matched above |
| 1024 | 0x400 | *(undocumented; 6,873 occurrences, 0.07% of level-0 shapes)* | left unmapped — too rare to anchor a guess, and no OSM class was an obvious fit |

`0x120`/288 is the single largest non-water bucket at level 0 (2,203,680
occurrences) and the natural home for the classes this brief explicitly
calls out (`building`) that the previous code never handled at all, plus
the several POI/boundary classes (admin boundary, university, hospital,
cemetery, golf course) for which R's level-0 background vocabulary has no
observed code whatsoever — using it as the exhaustive catch-all is a
choice, not a spec-derived fact; flagged here for the same reason as the
road tables' unassigned code.

**Levels 2–8**: the water/vegetation codes (`289/290/291/321`) plus `288`
are present at all four levels (2/4/6/8); `322`/`578`/`640`/`1024` are
present at level 2 only, so the shared `[2, 8]` rule table intentionally
omits the industrial/railway/airport/unmapped rules (they would violate
coverage at 4/6/8) and lets those OSM classes fall through to the `288`
catch-all instead.

**Levels 10/12**: the census background set shrinks to `{289, 306, 528}`
— a *different* code space again. `306` = `0x132` ("address level 2
(state)" per `roadtypes.py`) reappears here even though it was absent at
level 0 — consistent with an overview level drawing state boundaries as
background shapes instead of the fine-grained natural/vegetation set.
`528` = `0x210` ("road type 0" per `roadtypes.py`, i.e. roads rendered
*as background shapes* at the most zoomed-out levels) is **not**
implemented here: populating it would mean generating background shapes
from road geometry, which is a different data flow than
`_osm_tags_to_bg_type`'s tag-driven lookup and is out of this unit's
scope (the brief's owned-paths list is `_osm_tags_to_bg_type` and its two
tag-based call sites, not a new road→background bridge). Flagged as a gap
for whichever later unit builds level 10/12 backgrounds in full: at
present this table only supplies `289` (water, generalised — all of
coastline/bay/sea/ocean/water/wetland/river/stream collapse to the one
code available at this zoom) and `306` (`boundary=administrative` +
`admin_level=4`); everything else is omitted (`default: null`) at these
levels.

## Extractor call-site changes

`parser/osm_to_parcel_geometry.py`'s `_osm_tags_to_bg_type` computation
(the only call site that resolves a real value, not just a not-None
check) previously ran **once per way**, before the per-level loop in
`_handle_way` — i.e. the same `bg_type` value was reused for every
requested level. Because the vocab contract is level-scoped
(`Vocab.lookup(level, tags)`), and R's own background vocabulary
genuinely differs by level range (see above), that call had to move
inside the per-level loop; a way that would have produced one background
shape reused across levels can now produce a different `type_code` (or
none at all, at levels where nothing matches) per level. This is judged
in-scope as "the call site that uses" `_osm_tags_to_bg_type`, not a
structural change to the file, but is called out explicitly since it
touches more of `_handle_way`'s body than a one-line replacement.

Similarly, `_make_road_link` previously took only the `highway` tag
value (a string), with no `level` parameter — `road_type`/`display_class`
were looked up once per link regardless of level. Per-level lookup
requires `level` (and the full tag dict, per `Vocab.lookup(level, tags)`)
at that call site, so `_make_road_link`'s signature grew a `level`
parameter and its single call site (inside `_handle_way`'s per-level
loop, where `level` is already in scope) was updated to pass it. This is
a larger edit than "replace two `.get()` calls" and is flagged as a
deviation from the brief's literal "no other edits to that file" — it is
judged necessary to satisfy the per-level contract the same brief
requires, and is exactly the kind of contradiction the brief asks to be
reported rather than silently resolved by, e.g., hardcoding level 0
everywhere (which would have produced wrong `road_type`/`display_class`
values at every other level while still passing this unit's own
level-0-only done evidence).
