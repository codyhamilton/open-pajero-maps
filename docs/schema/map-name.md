# Map Frame: Name sub-frame

The Name Data Frame (spec ch.7.4) is sub-frame slot 2 of a Map Frame (`map-frame.md`
holds the header, region list and mfde directory that locate it). One parcel has at most
one name sub-frame. It holds every label for the parcel: road labels, place names, park
and water names, route shields, and search tags (`A=`, `1=`).

All multi-byte values are big-endian u16. "SWS/D" means the stored-halved encoding: the
field holds bytes/2, and `0xFFFF` means "absent" (`parser/kiwiw/bitutils.py` `sws()`).
Coordinates are 13-bit normalized within the parcel (`decode_region_coord`, with the top
3 bits reserved for the integrated-parcel relative position); lat/lon conversion lives in
`parser/kiwiw/coordconv.py` and is outside this layer.

Structure:

```
Name Data Frame
  u16   header size (SWS)                      -> 2 + 4*n_lists bytes
  n_lists x { u16 offset (SWS/D), u16 count }   Name Data Management Information
  ...   Name Data Lists (one per populated management entry), each a run of
        Name Data Records laid end to end; record length comes from the record's own `na`
```

The frame is length-bounded by the mfde entry, not by the header (`map-frame.md`).
Record boundaries come from `na` (byte length = `na[11:0] * 2`), never from the string
type. This is the rule that fixed an earlier decode misalignment in the Linear-B parser.

## Name Distribution Header (spec ch.7.4.1)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @0 u16 header size (SWS) | Header byte length; management entries fill `[2, hlen)` | verified | R: `33` (=66 bytes = 2 + 16x4) on every sampled parcel L0-L12 (35 parcels); byte-identical frame round-trip `parser/tests/test_roundtrip_parcel_content.py` | `parser/kiwiw/name.py`, `parser/kiwiw/parcel_writer.py` |
| @2 + 4i: u16 offset (SWS/D) | Start of list i from frame start; `0xFFFF` = empty list | verified | Same round-trip test (raw words carried verbatim in `NameList`); R shows `0xFFFF` for all but 1-3 lists per parcel | `parser/kiwiw/name.py`, `parser/kiwiw/parcel_writer.py` |
| @4 + 4i: u16 count | Records in list i | verified | Same round-trip test `parser/tests/test_roundtrip_parcel_content.py` | `parser/kiwiw/name.py`, `parser/kiwiw/parcel_writer.py` |
| Number of lists | Always 16 entries on R, one per "display class" grouping | observed | R: 35/35 sampled parcels have 16 (header=33). Spec (7.4.1(1)) says the number and order are unconstrained | `parser/kiwiw/name.py` |
| Meaning of list index | Records of a kind sit in a fixed list slot on R | observed | R sample (5 parcels x 4 levels, records mapped to lists by offset order): L0 slot 7 = type 6; slot 11 = plain type 4 incl. sea names; slot 13 = types 4 (`A=`/`1=`) and 5; L2 slot 1 = type 1, slot 13 = type 5; L4 slots 1 and 10 = type 1; L8 slots 0/1 = type 1. The spec says "grouped by display class" but the class-to-slot mapping was never derived | - |
| Extended data after lists (spec 7.4 No.3) | Expansion area after the lists | unknown | Spec only ("Individual Expansion"); never seen or checked | - |
| G synthetic layout | Generated frames emit a single list (hlen = 6 bytes, one entry) | assumed | Legal per spec 7.4.1(1); differs from R's 16-entry header. No reader test confirms the head unit accepts it | `parser/kiwiw/synth.py` |

## Name Data Record header (spec ch.7.4.2.1.1)

Every record starts with a 6-byte Name Attribute Header. `na` is the length word.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @0 bits 11:0 `na` length (SWS) | Record byte length = value x 2 (includes the 6-byte header) | verified | Record walking by `na` reproduces every record boundary; byte-identical round-trip `parser/tests/test_roundtrip_parcel_content.py`; historical fix recorded in `docs/phases/02-roundtrip.md` correction 3 | `parser/kiwiw/name.py` |
| @0 bit 15 deletion flag | In-memory flag, normally 0 | observed | R: bits 15:12 of `na` are 0 on 1237/1237 sampled records | - |
| @0 bit 14 temporal-info flag | Record carries 8-byte temporal info | observed | 0 on 1237/1237 sampled records; spec 7.4.2.1 No.5 | - |
| @0 bit 13 extended-data flag | Record has extended data | observed | 0 on 1237/1237 sampled records | - |
| @0 bit 12 | Reserved | observed | 0 on 1237/1237 sampled records | - |
| @2 bits 15:11 display scale flags 1-5 | One bit per display scale; all of 1-4 zero means "not drawn by itself" | verified | Decoded as `display_scale_flag`; re-encode of type 4/5/6 byte-identical against R (`parser/tests/test_name_encoder.py`, `parser/tests/test_name_encode.py`). R values: type 4 = 0; type 5/6 at L0 = 24 or 28; L2 types 1/5 = 16 or 24 | `parser/kiwiw/name.py`, `parser/kiwiw/name_writer.py`, `parser/kiwiw/synth.py` |
| @2 bits 10:8 string type | Selects the String Data Record layout, see the string-type table | verified | Round-trip tests above; census `parser/refdata/profile/map.json` `string_type_hist` | `parser/kiwiw/name.py` |
| @2 bit 7 height-info flag | Record has altitude information | observed | 0 on 1237/1237 sampled records; `name_writer` preserves it verbatim, synth writes 0 | `parser/kiwiw/name_writer.py` |
| @2 bit 6 string orientation | 0 horizontal, 1 vertical | observed | 0 on all sampled R records; decoded as `vertical`; ignored for types A and B per spec | `parser/kiwiw/name.py` |
| @2 bits 5:0 priority | 6-bit signed priority, -32 = priority invalid | observed | R census `priority_hist`: L0 `{0: 8,877,667 (all type 4), 32: 10,203,438 (types 1/5/6)}`; every other level 100% `32`. Decoded unsigned, so 32 is spec's -32 (invalid). Census exists but no check compares priority | `parser/kiwiw/name.py` |
| @4 attribute 2 = type code | Feature type code (same vocabulary as background type codes, `map-background.md`) | verified | `type_code_hist` per level in `parser/refdata/profile/map.json`, enforced by `parser/harness/checks/vocab.py` (generated codes must be a subset per level) | `parser/kiwiw/name.py`, `parser/kiwiw/roadtypes.py` |

## String types (Attribute 1 bits 10:8)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 | Reserved | spec-only | spec ch.7.4.2.1.1; never seen on R (census keys are {1,4,5,6} only) | - |
| 1 Barycentric string | Text anchored at a point (place names). Layout: 6-byte coords, then character info list | verified | Census: 1,042,019 at L0, all type code 509; all of L2 25,465, L4 4,042, L6 1,022, L8 209, L10/L12 8 (`parser/refdata/profile/map.json`). Round-trips via raw bytes (`parser/tests/test_roundtrip_parcel_content.py`). Synthetic encoder is `parser/kiwiw/synth.py` `encode_name_record_bytes`, checked by decode only | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| 2 Point-indicating | Indicated point + offset to string point | spec-only | spec ch.7.4.2.1.3; absent from R census; not decoded (`name.py` records raw bytes, no text) | - |
| 3 Linear-placed type A | Indicated point + per-character offset records | spec-only | spec ch.7.4.2.1.4; absent from R census; not decoded | - |
| 4 Linear-placed type B | String attached to a road link or background shape; placement points + character info list | verified | Census: 8,877,667 at L0, none at L2+. Layout below. Type 4 re-encode patches attr1/attr2 and is byte-identical on R parcels (`parser/tests/test_name_encoder.py`). No from-scratch type 4 encoder exists | `parser/kiwiw/name.py`, `parser/kiwiw/name_writer.py` |
| 5 Linear-placed type C | Text at a point with a display angle (road labels) | verified | Census 7,603,420 at L0, 14,704 at L2; all type code 528 at L0. `parser/tests/test_name_encode.py` re-encodes R Brisbane records byte-identical (skipped if R is not mounted) | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| 6 Symbol + string | Symbol with an attached string (POIs, parks) | verified | Census 1,557,999 at L0 only. `parser/tests/test_name_encode.py` byte-identical re-encode against R. 20% of R type 6 records have an empty string (design doc F8 stride sample) | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| 7 | Spec names type D (ch.7.4.2.1.8) yet the type table marks `111` "undefined" | unknown | Spec is internally inconsistent: ch.7.4.2.1.1 table vs section 7.4.2.1.8. Absent from R | - |

Which string types occur at which level (R census, `parser/refdata/profile/map.json`):

| Level | Types present | Notes |
|---|---|---|
| 0 | 1, 4, 5, 6 | 19,081,105 records; max text 88 |
| 2 | 1, 5 | 40,169 records |
| 4, 6, 8 | 1 | 4,042 / 1,022 / 209 records |
| 10, 12 | 1 | 8 records each |

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Type 1 at level 0 | Census shows 1,042,019 type 1 records at L0 (5.5%); synth and harness forbid it at L0 | observed | Sources disagree. Census `parser/refdata/profile/map.json` (winner: it is a direct count on R) vs. the design/spot-check rule that L0 has none (`parser/harness/checks/vocab.py`, `parser/kiwiw/synth.py` comment). A 35-parcel R sample of city parcels found none at L0, so the records are somewhere in remote/other parcels. Not resolved: the harness still fails a G with type 1 at L0 | `parser/harness/checks/vocab.py` |
| Type 4 at levels >= 2 | None on R at L2-L12 | verified | Census (zero counts) `parser/refdata/profile/map.json` | `parser/harness/checks/vocab.py` |
| Type 5/6 at levels >= 4 | None on R | verified | Census `string_type_hist` per level | `parser/harness/checks/vocab.py` |

## Type 1 body (Barycentric, spec ch.7.4.2.1.2)

Offsets are relative to record start.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @6 u16 additional-background type/flags | Type (15:14), has-additional-info (13), aux-data flag (11) | observed | 0 on the R type 1 records sampled (202); synth writes 0 | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| @8 u16 X | Normalized longitude, 13-bit + 3-bit relative-position field | observed | Decoded lat/lon land in the correct parcel for R records; whole-frame raw round-trip passes but does not test this field alone | `parser/kiwiw/name.py`, `parser/kiwiw/coordconv.py` |
| @10 u16 Y | Normalized latitude, same format | observed | Same | `parser/kiwiw/name.py`, `parser/kiwiw/coordconv.py` |
| @12 u16 string size (words) | Character byte count / 2 | observed | Round-trip byte-identical | `parser/kiwiw/name.py` |
| @14 string bytes | Text, NUL-padded to a word | observed | Same; R text ASCII only (see encoding) | `parser/kiwiw/name.py` |
| Altitude word after string | Optional, only if height flag (attr1 bit 7) set | spec-only | spec ch.7.4.2.1.2; flag never set on R | - |
| Multi-language pointer table | Present when more than one language is stored | spec-only | spec ch.7.4.2.1.2.2; `name.py` reads single-language layout only; R records decode sanely as single-language | `parser/kiwiw/name.py` |

## Type 4 body (Linear-placed type B, spec ch.7.4.2.1.5)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @6 u16 string placement information | Bits 15:14 additional-bg type, 13 additional-bg flag, 11 aux-data flag, 10:8 placement type (1 point, 2 line, 3 area), 7:6 target kind (00 road, 01 background), 5 height flag, 3:0 number of placement points (1-15) | observed | R values: `0x0201` (line, road target, 1 point) on all `A=`/`1=` records; `0x0b41` (area, background target, aux-data flag set, 1 point) on plain names. Only bits 3:0 are read by `name.py` (`extract(w,0,3)`) | `parser/kiwiw/name.py` |
| @8 u16 offset to drawn data | Displacement of the target road/background record | observed | Spec (7.4.2.1.5(1)) defines it as an offset into the road or background frame. R: `0xFFFF` on 1493/1493 sampled type 4 records, so the R disc does not use it. Spec and R disagree; R wins for our purposes | - |
| @10 + 2k placement point records | Per point: bits 15:14 side (0 on link, 1 left, 2 right, 3 either), 13:0 normalized distance | observed | R value `0x0000` on the sampled records; `name.py` skips them (2 bytes each) without decoding | `parser/kiwiw/name.py` |
| string size + string | u16 words, then text | verified | Round-trip byte-identical `parser/tests/test_roundtrip_parcel_content.py` | `parser/kiwiw/name.py` |
| Trailing 2 bytes when placement bit 11 = 1 | 2 bytes of "Auxiliary Data" (spec: 3-D symbol code) after the string | observed | Records with `0x0b41`: `na` length = 6+2+2+2+2+padded string + 2 exactly (checked by hand on 3 records, and the gap is `0x0000`); not decoded, carried in raw bytes | - |
| No decoded coordinate | Position is implied by the target link or shape | assumed | `name.py` gives type 4 no lat/lon. How a viewer resolves a name to its road or background target when the offset is `0xFFFF` is not known | `parser/kiwiw/name.py` |

## Type 5 body (Linear-placed type C, spec ch.7.4.2.1.6)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @6..@11 barycentric coords | As type 1 (word0 flags, X, Y) | verified | Byte-identical re-encode against R (`parser/tests/test_name_encode.py`) | `parser/kiwiw/synth.py` |
| @12 u16 display angle info | Bit 12 rotation-angle mode, 11:10 character orientation, 9 string rotation, 8:0 angle | verified | Re-encode byte-identical. R: bits 15:9 = `0x16` (relative angle, vertical-to-angle, per-string rotation) on 221/221 sampled | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| angle formula | Code stores `angle_deg = field[8:0] - 90` | assumed | Spec says 0-359 clockwise from north. The `-90` offset is a decode convention picked so re-encoding is exact, and was not derived from the spec (`synth.py` docstring). Byte round-trip holds either way | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| @14 string size + string | u16 words + text | verified | Byte-identical re-encode `parser/tests/test_name_encode.py` | `parser/kiwiw/synth.py` |

## Type 6 body (Symbol + string, spec ch.7.4.2.1.7)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @6..@11 barycentric coords | Center of the symbol | verified | Byte-identical re-encode against R `parser/tests/test_name_encode.py` | `parser/kiwiw/synth.py` |
| @12 u16 string placement | 15:14 alignment (2 = center), 13:12 position (0 = above) | observed | R `0x8000` on 41/41 sampled type 6 records; synth writes `0x8000` (the "not verified" caveat in `synth.py` predates this sample). Re-encode of 1 R record byte-identical | `parser/kiwiw/synth.py` |
| @14 string size + string | u16 words + text, empty string allowed | verified | `parser/tests/test_name_encode.py`; R has empty strings | `parser/kiwiw/synth.py` |

## Character encoding and string content

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Byte encoding | One byte per character, decoded as latin-1, NUL-terminated within the length | observed | R sample: 1237 records, 0 bytes above 0x7F. Head-unit code page is not stated in the spec (`CC` = "code" type) | `parser/kiwiw/name.py` |
| Uppercase text | R text is ~99% uppercase, no accents | observed | R sample: 0 lowercase letters in 1237 records (design doc F8 figure: ~99%). The ~1% is unexamined | `parser/kiwiw/name.py` |
| Non-ASCII on R | None seen | observed | 0 in 1237 sampled records; design doc F8 reports "no accents" | - |
| Odd-length pad | A trailing 0x00 byte pads odd-length text to a word; no other NUL terminator | verified | Re-encode of R type 5/6 is byte-identical only with this rule (`parser/tests/test_name_encode.py`; `parser/kiwiw/synth.py` `_encode_char_info_list` docstring). The type 1 synth encoder still always appends a NUL, so it disagrees | `parser/kiwiw/synth.py` |
| ASCII-uppercase fold in R | Whether the head unit can render lowercase or accented glyphs | unknown | Design doc F8 chooses to fold accents to ASCII and uppercase because the head unit's encoding and glyph set are unknown. Not tested; no fold function exists in code yet | - |
| Max text length | 88 bytes at L0; 39 at L2; 10-18 at L4-L12 | verified | Census `max_text_length` in `parser/refdata/profile/map.json`; harness envelope check `parser/harness/checks/envelope.py` compares against it | `parser/harness/checks/envelope.py` |

## Name tags and attribution

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Plain type 4 (`<NAME>`) | Named parks, buildings, water, sea, reserves | observed | 16.6% of the design doc's 2.73M-record stride sample. R L0 slot 11. Type codes seen: 0x141 (321), 0x121, 0x120, 0x400 (1024), 0x2-0x9 (many) | `parser/kiwiw/name.py` |
| `1=<ROAD>` tag | Type 4, placement `0x0201`, text `1=` + uppercase road name; type code 0x5-0x9 (road class) | observed | 1236 sampled records; 22.9% of the design doc's stride sample. Suspected purpose: a searchable road name tied to a road link; whether the head unit needs it is not known | - |
| `A=<LOCALITY>, <SUBURB>,<REGION>` tag | Type 4, placement `0x0201`, e.g. `A=BRISBANE CBD, BRISBANE,QUEENSLAND`; type code follows road class (0x6-0x8) | observed | 130 sampled records; 7.0% of the design doc's stride sample. Same open purpose as `1=` | - |
| Tag purpose | Whether `A=` / `1=` are required for the address search chain | unknown | `docs/ARCHITECTURE.md` and the design doc F8 list it as open | - |
| Type 5 road label | One per link, type code 528 (0x210), priority 32, display flags 24/28 (L0), 16/24 (L2) | verified | Census `parser/refdata/profile/map.json`: 7,603,420 all with type code 528; 100% priority 32 | `parser/kiwiw/synth.py` |
| Type 6 POI/park | Symbol + text at a point; type codes 321 (park), 455, 0x1c7 etc. | observed | Sampled 41; census type_code_hist includes 321, 455, 640, 642, 1024 | - |
| Type 1 route shield | Type code 509 (0x1FD), one text string (route number), priority 32 | observed | Census 1,042,019 type 1 all code 509 at L0; the code is not in `BACKGROUND_TYPE_CODES` (`parser/kiwiw/roadtypes.py`) and has no known meaning | - |
| Place name at L2-L12 | Type 1, code 308 (0x134 municipality) at all levels 2-12; 509 and 306 also appear | verified | Census `type_code_hist` per level, enforced by `parser/harness/checks/vocab.py` | `parser/osm_to_parcel_geometry.py` |
| Attribution to a road link | A type 5 record is positioned near its link; a type 4 record refers to a link by offset | unknown | Spec: road records hold a "street name data offset" (7.4.2.1.5, 8.x). No such field is decoded in `road.py`; R type 4 offsets are all `0xFFFF`. How link and name pair up is not established | - |
| Attribution to a background shape | Background record has an optional trailing "name" 2-byte field | unknown | `parser/kiwiw/model.py` notes the field is strided past unread. Same open question | `parser/kiwiw/background.py` |
| Attribution to a point | Type 1 and type 6 carry their own coordinates, so no back-reference is needed | observed | Byte-identical re-encode of X/Y; decoded positions fall inside the parcel | `parser/kiwiw/name.py` |
| Duplicated strings | 44% of sampled records repeat a string already in the same cell (per-link, per-road-type copies) | observed | Design doc F8 stride sample (450k parcels, 2.73M records); not re-measured here | - |

## Sea names

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Ocean/sea name per cell | Cells over water carry one or more type 4 records naming the sea, e.g. `TASMAN SEA`, `CORAL SEA`, `SOUTHERN OCEAN`, `SOUTH PACIFIC OCEAN` | observed | R L0 parcels at (-40.5,150), (-15,150), (-36,138), (-45,140), (-30,156): a single type 4 record each, type code 0x120 (288) or 0x121 (289), priority 0, display flags 0, list slot 11 | `parser/kiwiw/name.py` |
| Coverage | ~85% of L0 cells carry a region or ocean name on R | observed | Design doc F8 measured ~3.15M cells; G has ~5% | - |
| Sea name type code | 288/289 (ocean/lake background codes) reused as the name type code | observed | Census `type_code_hist` L0 has 288: 2,203,664 and 289: 546,663 | - |
| Higher-level sea/ocean names | Not seen at L2+ | unknown | L2-L12 census lists only 306/308/509/528 | - |

## Writer behavior (what G builds)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Replicate mode | Re-emit every record from `raw_bytes` unchanged | verified | Byte-identical parcel round-trip `parser/tests/test_roundtrip_parcel_content.py`; negative control flips a raw byte and breaks it | `parser/kiwiw/parcel_writer.py` |
| Encode mode | Type 4: patch attr1/attr2 from decoded fields; other types return raw bytes | verified | `parser/tests/test_name_encoder.py` | `parser/kiwiw/name_writer.py` |
| From-scratch types | Types 1, 5, 6 have encoders; type 4 has none | verified | `parser/tests/test_name_encode.py` (type 5/6 synthetic round-trip), `parser/tests/test_synth_map_frame.py` | `parser/kiwiw/synth.py` |
| Level filter on emit | L0 emits 5 and 6 only; other levels 1 and 5 | assumed | `parser/tests/test_name_encode.py` pins it, but it is a policy chosen against the type-1-at-L0 census (see above) | `parser/kiwiw/synth.py` |
| G background-name codes | Levels 2-12 background-attached names omitted; L0 578 omitted | assumed | `parser/tests/test_name_record_vocab.py`; a policy to stay inside the census vocabulary | `parser/osm_to_parcel_geometry.py` |
| Vocabulary tables | Name type codes are data, checked against the census | verified | `parser/harness/checks/vocab.py` | `parser/kiwiw/vocab.py` |

## Open questions

1. How road links and background shapes refer to name records (and whether they do), given type 4 offsets are `0xFFFF` on R. The road and background name-offset fields are not decoded.
2. Whether the head unit needs `A=` and `1=` records for address search, or displays them.
3. Head-unit character set: whether lowercase or non-ASCII glyphs render, so whether the fold in the design doc is needed or only conservative.
4. Meaning of the 16 list slots (display-class mapping) and whether a single-list frame is accepted.
5. Type code 509 (route shields) and the type-1-at-L0 conflict between the census and the harness rule.
6. Spec string types 2, 3, 7 (never seen on R); multi-language name lists.
7. The `-90` display-angle convention for type 5 versus the spec's clockwise-from-north.
8. The ~1% of R text that is not uppercase.
