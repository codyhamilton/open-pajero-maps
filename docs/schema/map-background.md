# Map Frame background sub-frame (Ch.7.3)

The Background Data Frame is one of the three content sub-frames of a Map Frame (the
sub-frame directory and its index 1 slot are in `map-frame.md`; road records in
`map-road.md`; names in `map-name.md`). It holds non-road map features: water, parks,
railways, boundaries, ocean. Nesting:

```
Background Data Frame
  Distribution Header (SWS size, up to 32 Element Management entries)   <- one entry per display class
    Element Unit Background (one per non-empty display class)
      n (u16) + n Background Type Unit Headers (shape class + count)
      Minimum Graphics Data Records, grouped by type unit, in header order
```

All words are big-endian u16. `[D]` and `[SWS]` words are "stored halved": byte value is
word << 1, except `0xFFFF` = not present (`parser/kiwiw/bitutils.py` `sws`). Coordinates are
parcel-local integers (not degrees); polygon vertices are a start point plus signed i8
deltas (below). Drawing order is header order (spec ch.7.3.1, ch.7.3.2).

R was sampled read-only at eight metropolitan, regional and outback points per level
(2026-09, ~200 to 2,000 shapes per level; call it the "8-point sample"). The full-country
type-code and shape-class censuses are in `parser/refdata/profile/map.json`.

## Distribution header and element unit

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Frame +0, u16 SWS: header size | Bytes of the Distribution Header (2 + 4 x element count) | verified | Decoder loops `off < hlen`; a wrong value mis-parses and fails byte identity in `parser/tests/test_roundtrip_parcel_content.py`. R: 32 element entries in all 8 sampled parcels at every level (`spec ch.7.3.1`: max 32) | `parser/kiwiw/background.py` |
| Frame +2.., 4 bytes each: Element Management entry (`[D]` offset, `[SWS]` size) | Position and size of each display-class element unit; `0xFFFF` offset + 0 size = no data for that display class | verified | Same roundtrip test; `spec ch.7.3.1.1`. Entry index = display class = draw order | `parser/kiwiw/background.py`, `parser/kiwiw/parcel_writer.py` |
| Element index (0..31) as display class | Selects draw layer; each populated index holds one class of feature | observed | 8-point sample of R: idx 2 = type 321 polygons (L0-L8); idx 4 = 306 lines (L10/12); idx 5 = 1024 polygons (L0/L2 only); idx 7 = 289/290/291/288 polygons (all levels); idx 8 = 291 lines (L0/L2); idx 9 = 578 lines (L0/L2); idx 19 = 528 lines (L10/12). Indices 0,1,3,6,10-31 empty in the sample. 322 and 640 are censused but not seen in the sample, so their indices are unknown | `parser/kiwiw/background.py` |
| Element Unit +0, u16: n | Number of Background Type Units in this element | verified | `parser/tests/test_roundtrip_parcel_content.py`: Roundtrip test (unit count drives shape striding) | `parser/kiwiw/background.py` |
| Type Unit Header +0, u16 `[D]`: unit offset | Displacement of the unit's record list from the element start | observed | Decoder reads and ignores it, striding records sequentially; roundtrip replays the raw word. Not checked against the striding position | `parser/kiwiw/background.py` |
| Type Unit Header +2 bits 15:14: shape class | 0 = point, 1 = line, 2 = area, 3 = reserved | observed | R census `shape_class_hist` (`parser/refdata/profile/map.json`): only 1 and 2 occur (L0 3.73M/5.71M; L4-L8 polygons only; L10/12 19 lines, 6 polygons). No point (0) records exist on R. Spec ch.7.3.2.1 | `parser/kiwiw/background.py` |
| Type Unit Header +2 bit 13: height info flag | Records carry Height Information Records | observed | 0 in all sampled units (ch.7.3.2.1). Decoder does not parse height records | `parser/kiwiw/background.py` |
| Type Unit Header +2 bit 12 | Reserved | observed | 0 in all sampled units | `-` |
| Type Unit Header +2 bits 11:0: record count | Records in this unit | verified | `parser/tests/test_roundtrip_parcel_content.py`: Roundtrip test (count drives striding; wrong count leaves poison bytes) | `parser/kiwiw/background.py` |
| Type units per element | One unit per (shape class) or per type code | unknown | R sample shows one unit per element index at L0-L8 (e.g. idx 7: one polygon unit mixing 288-291); the writer groups by shape class only | `parser/kiwiw/synth.py` |
| Extended Data (header, element) | Expansion fields | spec-only | Spec ch.7.3 (1)/(2); never seen (frame sizes tile exactly) | `-` |

## Minimum Graphics Data Record (line and area)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| +0 bits 11:0: record size | Record length in halved bytes (bytes = value x 2) | verified | Sole stride between records; a wrong value breaks byte identity (`parser/tests/test_roundtrip_parcel_content.py`) | `parser/kiwiw/background.py` |
| +0 bits 15:12: delete, temporal, extended-data flags, reserved | Spec: delete flag, temporal-info flag, extended-data flag | observed | 0 in all 204+ to 2,020 records per level of the 8-point sample (hdr>>12 = 0) | `parser/kiwiw/background.py` |
| +2 bits 15:11: display scale flags 1-5 | Levels at which the shape is drawn; all 0 = never displayed | observed | R sample: 0x1C bits (flags 1-3 set) at L0 (all 204 records), 0x18 (flags 1-2) at L2-L10 and 0x10 (flag 1) in 17 of 760 L2 records and all 200 L12 records. Pattern by level plausible but the sample is small. The G writer writes 0 here (`synth.py`: flag word = ncoord only), which the spec defines as "no display" | `parser/kiwiw/synth.py` |
| +2 bits 10:0: N | Number of offset-coordinate records (vertices after the first) | observed | R: record length = 12 + 2N (+2 with name) for every sampled record; decoder trusts N for coordinates but not for striding. Max N censused 2,044 at L0 (`parser/refdata/profile/map.json` `max_n_coords`) | `parser/kiwiw/background.py` |
| +4 u16: type code | Feature type; vocabulary below | verified | Census `type_code_hist` per level (`parser/refdata/profile/map.json`); `parser/tests/test_vocab.py` fails if `bg_type.json` can emit a code outside R's per-level set; harness check `parser/harness/checks/vocab.py` compares G to it | `parser/kiwiw/background.py`, `parser/kiwiw/vocab.py` |
| +6 bits 15:14: additional info type | 00 frame A, 01 frame B, 10 building ID | observed | 0 in all sampled records | `-` |
| +6 bit 13: additional info flag | Additional info pointer present | observed | 0 in all sampled records | `-` |
| +6 bit 12: name flag | 2-byte Name Offset follows the coordinates | observed | Set on 139 of 204 sampled L0 records (each with +2 bytes tail, record length 12+2N+2); never set at L2-L12 in the sample. Decoder only strides it (via record size); name offset value is not decoded. Points into the name frame (`map-name.md`) per spec ch.7.3.2.2.1 (5) | `parser/kiwiw/background.py` |
| +6 bit 11: auxiliary data flag | 2-byte auxiliary data follows | observed | 0 in all sampled records | `-` |
| +6 bit 10: pen-up flag | Offset list contains (0,0) pen-up markers | observed | Decoded; 0 in all sampled records. Pen-up handling is not applied when building coordinates (deltas are accumulated as-is) | `parser/kiwiw/background.py` |
| +6 bit 9: underground | Feature is underground (subway) | observed | Decoded; 0 in all sampled records | `parser/kiwiw/background.py` |
| +6 bits 8:3 | Reserved | observed | 0 in all sampled records | `-` |
| +6 bits 2:0: multiplication constant n | Delta multiplier is 2^n (0 to 7) | observed | R census `mult_const_hist` (`parser/refdata/profile/map.json`): multipliers 1, 2, 4, 8, 16, 32, 64 seen at L0; 64 dominates at L4-L12 outside 1. 128 (n=7) never seen. Encoder keeps n as data (`parser/tests/test_synth_vectorized.py` fuzzes fast vs scalar encoder) | `parser/kiwiw/background.py`, `parser/kiwiw/synth.py` |
| +8 u16: start X | bits 12:0 value, bits 15:13 relative position (x 4096) in an integrated parcel | observed | Decoded value + region x 4096 (`parser/kiwiw/coordconv.py`). R sample: region bits are 0 for every record at L2-L12; at L0 region up to 3 on 38 of 192 sampled polygons (divided/integrated cells). Spec ch.7.3.2.2.1.1: max 4096 x 8 = 32768 | `parser/kiwiw/coordconv.py` |
| +10 u16: start Y | Same as X, latitude axis | observed | As above; Y axis direction (raw y increases southward, `lat = lat_hi - y/range`) is assumed, not confirmed (`parser/kiwiw/coordconv.py` docstring) | `parser/kiwiw/coordconv.py` |
| +12.., 2N bytes: offset coordinate pairs | Signed i8 (dx, dy) per vertex, each multiplied by 2^n and accumulated from the start point | observed | Decode plus re-encode reproduces coordinates (`parser/tests/test_background_encoder.py` covers only coords[0] and reuses raw delta bytes; `parser/tests/test_synth_vectorized.py` fuzzes G's encoder against itself). On R every sampled polygon closes exactly (192, 597, 513, 546, 2,020, 8, 48 polygons at L0-L12; sum of deltas = 0 as the spec requires) | `parser/kiwiw/background.py`, `parser/kiwiw/synth.py` |
| Coordinate range of the parcel-local space | Full-cell coordinate span used to place (x, y) in the parcel bounding box | unknown | Code uses 2^15 (`COORD_RANGE`; its docstring says not spec-confirmed). R sample: maximum decoded coordinate is 4096 at L2-L10, 3072 at L12 and 16384 at L0 (region-coded start points). `docs/design/map-layer-parity-remediation.md` F1 hypothesises 4096 as the true cell range (hypothesis, unconfirmed offline). Spec says 4096 per separate parcel, 32768 only for an integrated parcel. Undecided; needs the F1 census | `parser/kiwiw/coordconv.py` |
| Polygon vertex order | Counterclockwise, non-crossing, closed | spec-only | Spec ch.7.3.2.2.1.1.1. Closure verified by sample (above); winding and non-crossing not measured | `-` |
| Height Information Records | Altitude per element point | spec-only | Spec ch.7.3.2.2.1.2; type-unit height flag was 0 in every sampled unit | `-` |
| Temporal information (8 bytes) | Validity period | spec-only | Spec ch.7.3.2.2.1 (10); header temporal flag 0 in samples | `-` |
| Point record (shape class 0) | Symbol record without vertices | spec-only | Spec ch.7.3.2.2.2 (not read here); none exist on R (`shape_class_hist` has no class 0). Decoder skips coordinates; synth writes 12 bytes | `parser/kiwiw/background.py`, `parser/kiwiw/synth.py` |
| Frame round-trip | Decode then write reproduces the frame | verified | `parser/tests/test_roundtrip_parcel_content.py` (byte-identical, replicate mode: raw record bytes are replayed); encode-mode roundtrip in `parser/tests/test_background_encoder.py` patches only start X/Y | `parser/kiwiw/parcel_writer.py`, `parser/kiwiw/background_writer.py` |

## Background type-code vocabulary (per level)

Type codes are defined per country by META (spec ch.7.3.2.2.1 (2)); `spec/format_english/pdf/07A1122e.pdf` has no numeric table. Labels come from `parser/kiwiw/roadtypes.py` (transcribed from `tools/kiwiread`, medium-low confidence). The census counts below are shape counts from `parser/refdata/profile/map.json` (`levels.<L>.background.type_code_hist`), which is why the existence and per-level membership of each code is `verified` (`parser/tests/test_vocab.py` and `parser/harness/checks/vocab.py` assert against it). The meaning of each code is `observed`/`unknown`.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 288 (0x120) | Undocumented; polygon layer in element 7 alongside water | verified | `parser/refdata/profile/map.json` census: Present L0 2,203,680; L2 137,730; L4 8,344; L6 2,086; L8 2,086; absent L10/12 (census). Meaning unknown: no label in `roadtypes.py` | `parser/kiwiw/vocab.py` |
| 289 (0x121) | Water system: shore, ocean, bay, sea, creek. Ocean is this type | verified | `parser/refdata/profile/map.json` census: Present all levels: L0 2,826,074; L2 159,992; L4 36,639; L6 11,605; L8 8,010; L10 6; L12 6. Ocean polygons: type 289 named in design doc F7 (`docs/design/map-layer-parity-remediation.md`); on R sea cells are typically one 12-coordinate polygon (design doc, measured, not re-checked here). Sampled L4-L8 records are polygons in element 7 | `parser/kiwiw/vocab.py` |
| 290 (0x122) | Water system: lake, marsh, pond | verified | `parser/refdata/profile/map.json` census: L0 33,493; L2 2,190; L4 1,014; L6 689; L8 401; absent L10/12 | `parser/kiwiw/vocab.py` |
| 291 (0x123) | Water system: river | verified | `parser/refdata/profile/map.json` census: L0 3,729,504; L2 236,758; L4 2,968; L6 1,487; L8 830; absent L10/12. Lines in element 8 at L0/L2 and polygons in element 7 | `parser/kiwiw/vocab.py` |
| 306 (0x132) | Address level 2 (state boundary) | verified | `parser/refdata/profile/map.json` census: Only L10 (11 shapes) and L12 (11); absent L0-L8. Lines in element 4 | `parser/kiwiw/vocab.py` |
| 321 (0x141) | Green belt, park | verified | `parser/refdata/profile/map.json` census: L0 557,684; L2 41,001; L4 10,795; L6 3,833; L8 1,193; absent L10/12. Polygons in element 2 | `parser/kiwiw/vocab.py` |
| 322 (0x142) | Factory site | verified | `parser/refdata/profile/map.json` census: L0 951; L2 136; absent L4-L12 | `parser/kiwiw/vocab.py` |
| 528 (0x210) | "Road type 0" drawn as background line (roads-as-background) | verified | `parser/refdata/profile/map.json` census: Only L10 (8) and L12 (8); lines in element 19. The label is a guess; nature is a coarse road overview | `parser/kiwiw/vocab.py` |
| 578 (0x242) | Very high speed railway / JR line (railway) | verified | `parser/refdata/profile/map.json` census: L0 84,930; L2 6,048; absent L4-L12. Lines in element 9 | `parser/kiwiw/vocab.py` |
| 640 (0x280) | Other airport | verified | `parser/refdata/profile/map.json` census: L0 2,133; L2 205; absent L4-L12 | `parser/kiwiw/vocab.py` |
| 1024 (0x400) | Undocumented; 6,873 at L0 (0.07%), 258 at L2, polygons in element 5 | verified | `parser/refdata/profile/map.json` census: Census as stated; absent L4-L12. Meaning unknown | `parser/kiwiw/vocab.py` |
| Codes outside census | Any code in `BACKGROUND_TYPE_CODES` not listed above (0x131 country, 0x134 municipality, 0x408 cemetery, 0x464 university, 0x480 hospital, 0x6180 golf, ...) | observed | Zero occurrences on R at every level (`map.json`); previous OSM mapping that emitted them was removed (`parser/refdata/vocab/README.md`). Do not emit | `parser/kiwiw/roadtypes.py` |
| Display class (background) | Element index 0..31, see Distribution header above; distinct from the road `display_class` vocabulary | observed | `parser/refdata/vocab/display_class.json` covers roads only (`map-road.md`); no background display-class table exists in code | `-` |
| Type-per-element rule | Which display class each type code belongs in | observed | Inferred from the 8-point sample (element table above); no code encodes it (the writer puts everything in one element, `parser/kiwiw/synth.py`) | `parser/kiwiw/synth.py` |

### What R contains per level (censused)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| L0 | 9,445,322 shapes; codes {288, 289, 290, 291, 321, 322, 578, 640, 1024}; lines 3,734,845, polygons 5,710,477; max N 2,044 | verified | `parser/refdata/profile/map.json` `levels.0.background` | `parser/refdata/vocab/bg_type.json` |
| L2 | 584,318 shapes; codes as L0; lines 237,634, polygons 346,684 | verified | `levels.2.background` | `parser/refdata/vocab/bg_type.json` |
| L4, L6, L8 | 59,760 / 19,700 / 12,520 shapes; codes {288, 289, 290, 291, 321}; polygons only | verified | `levels.4/6/8.background` | `parser/refdata/vocab/bg_type.json` |
| L10, L12 | 25 shapes each; codes {289, 306, 528}; 19 lines, 6 polygons | verified | `levels.10/12.background` | `parser/refdata/vocab/bg_type.json` |

## Writer mapping tables (build-side, OSM to type code)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| `bg_type.json` L0 and L2-L8 rules | Ordered OSM tag to code: coastline/bay/sea/ocean 289; water/wetland/reservoir 290; river/stream/waterway 291; wood/scrub/heath/grass/meadow/farmland/forest/park 321; L0 only: industrial 322, rail 578, aerodrome 640; catch-all 288 | assumed | Chosen by census frequency, not by R semantics (`parser/refdata/vocab/README.md`). `parser/tests/test_vocab.py` only proves the emitted set is inside R's per-level census. `docs/design/map-layer-parity-remediation.md` F6 flags the 288 catch-all as the cause of building shapes (Melbourne CBD 474 vs 17 in R) and plans to replace it with an explicit mapping and drop default | `parser/kiwiw/vocab.py` |
| `bg_type.json` L10/L12 rules | Water tags 289; `boundary=administrative` + `admin_level=4` 306; no 528 | assumed | 306 is unreachable from way tags (no way carries `admin_level=4` in the Australian PBF; state borders are relations) per `parser/refdata/vocab/README.md`; 528 not generated | `parser/kiwiw/vocab.py` |
| `selection.json` background admission | L0 `background_all` (every non-road tagged way); L2 natural=water/coastline; L4 natural=wetland; L10/12 natural=bay; calibrated to shape-count envelopes | assumed | Calibrated to `count_ratio` envelope vs R counts, not to R content (`parser/refdata/selection.json` `_calibration_note`; `parser/tests/test_selection.py` guards that every predicate is mappable). Design doc F6/F7 records it as wrong for L0 and missing `place=sea` or `place=ocean` and ocean polygons | `parser/kiwiw/selection.py` |
| Ocean polygons | Complement of land polygons inside the populated rectangle, type 289 | assumed | Design doc F7 plan; OSM coastline is a line so the current pipeline builds none; not implemented | `-` |
| Frame builder | One element, units grouped by shape class, `boff_word` 0, flag word = N only, no name offset | assumed | `parser/kiwiw/synth.py` `build_background_frame_bytes`; decodes via the same decoder (`parser/tests/test_synth_map_frame.py`) but deviates from R's per-display-class elements and display scale flags above. Whether the head unit accepts it is unknown | `parser/kiwiw/synth.py` |
| G shape 4-byte alignment and clamp | Record padded even; coordinates clamped to 0..32767; deltas clamped to i8 | assumed | `parser/kiwiw/synth.py`; clamping follows `COORD_RANGE` (see the range row) | `parser/kiwiw/synth.py` |

## Open questions

1. True parcel-local coordinate range (4096, 16384 at L0, or 32768) and its dependence on parcel class; blocks correct quantisation (`docs/design/map-layer-parity-remediation.md` F1).
2. Meaning of type codes 288 and 1024 and which display-class element 322 and 640 occupy.
3. Display scale flag rule by level; the writer emits none (spec: all zero means not displayed).
4. Name offset (+6 bit 12) target and semantics, present on most L0 records in the sample.
5. Which element (display class) each type must be placed in on a build; whether the head unit requires R's element layout.
6. Type Unit offset word and pen-up/height/temporal/extended fields are never exercised.
7. Full-country census of element index versus type code (only an 8-point sample was taken).
