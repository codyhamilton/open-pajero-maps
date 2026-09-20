# OSM tag → KIWI vocabulary mapping

Decisions behind `parser/refdata/vocab/{road_type,display_class,bg_type}.json`, loaded by
`parser/kiwiw/vocab.py` (format in that module's docstring). Coverage against R's census
(`parser/refdata/profile/map.json`) is enforced by `parser/tests/test_vocab.py`. What the
codes mean on the disc is in `docs/schema/map-road.md` and `docs/schema/map-background.md`.

## Basis

The spec has no numeric road-type or display-class table (ch. 7.A.1 is empty in the archived
copy). Every assignment is therefore derived from R's census, ranked by frequency, with rarity
taken as a proxy for road importance. That is a best guess, not a spec citation. Code 0 =
motorway is the only assignment with an independent label (`kiwiw/roadtypes.py`). Plan 03
Phase 7 revisits these tables against the native coordinate and selection work.

Tables are ranged by level (`[0,0]`, `[2,8]`, `[10,12]`), and each range must be safe for
every level in it, so `[2,8]` uses the intersection of what R carries at levels 2, 4, 6 and 8.
Road tables have exhaustive rule lists over the extractor's road set; `bg_type` ends each of
`[0,0]` and `[2,8]` with a catch-all rule. Lookup is per level, so the extractor resolves
`bg_type`, `road_type` and `display_class` inside its per-level loop.

## Roads

| road_type | L0 count on R | OSM classes |
|---|---|---|
| 0 | 18,241 | motorway, motorway_link |
| 10 | 1,772 | trunk, trunk_link |
| 7 | 38,493 | primary, primary_link |
| 8 | 71,032 | secondary, secondary_link |
| 3 | 370,408 | tertiary, tertiary_link |
| 5 | 374,388 | unclassified, road |
| 6 | 3,046,886 | residential, living_street |
| 9 | 5,127,756 | service, busway |
| 2 | 848,884 | track |
| 12 | 38 | unassigned (too rare to anchor) |

`display_class` is a deterministic function of road_type on R at L0. The census sums match
exactly once DC 7 = types 6 + 5 and DC 2 = types 9 + 12, and every other DC equals one
type's count. The resulting order is not monotonic in importance (motorway is DC 12, trunk
is DC 0), so it is not a prominence rank.

Levels 2–8: types `{0, 2, 7, 10}` and display classes `{0, 4, 10, 12}`. Motorway, trunk and
primary keep their L0 codes; every other class collapses to type 2 (DC 10), a lossy
generalisation with no finer signal in the census. R has no road links at levels 10 and 12,
so both tables carry no rules there and the default `null` omits roads.

## Backgrounds

R's L0 background codes are `{288, 289, 290, 291, 321, 322, 578, 640, 1024}`.

| code | OSM source |
|---|---|
| 289 | `natural=coastline/bay/sea/ocean`; at L10/12 also all water tags |
| 290 | `natural=water/wetland`, `landuse=reservoir` |
| 291 | `natural=river/stream`, `waterway=river/stream/canal` |
| 321 | `natural=wood/scrub/heath`, `landuse=grass/meadow/farmland/forest`, `leisure=park` |
| 322 | `landuse=industrial` (L2 only) |
| 578 | `railway=rail` (L2 only) |
| 640 | `aeroway=aerodrome` (L2 only) |
| 288 | catch-all at L0 and L2–8: buildings, admin boundaries, campus/hospital/cemetery/golf, anything unmatched |
| 1024 | unmapped: 0.07% of L0 shapes, no clear OSM analogue |

Choosing 288 as the catch-all is a decision, not a spec fact. It is R's largest non-water
bucket (2,203,680 at L0). Codes 322, 578, 640 and 1024 appear at L2 only, so the shared
`[2,8]` table omits them and lets those classes fall to 288.

Levels 10 and 12 use a different code space, `{289, 306, 528}`, and the `[10,12]` range has
no catch-all because R has no catch-all-shaped code there.

- **289** is selected from `natural=bay` only. It is the single water tag whose national way
  count (26) fits R's 25 shapes; the rest overshoot by two to three orders of magnitude.
- **306** (state boundary) is unreachable. Australian state boundaries are relations tagged
  `admin_level=4`, and their member ways carry no such tag, so the `boundary=administrative` +
  `admin_level=4` rule never fires. Closing it needs relation-tag propagation or another
  geometry source.
- **528** (roads drawn as background shapes, 8 of R's 25 shapes at these levels) is not
  implemented. It needs a road-geometry-to-background path.

Selection at a level must be consistent with this table. Admitting a tag the table cannot map
drops it silently, and zero content at a level means no block is placed for its blocksets and
the PDMDH blob comes out short by R's BMT size there.
