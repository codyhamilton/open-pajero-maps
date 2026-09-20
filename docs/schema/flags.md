# Flags, node bits and flag-like enums

One table of every flag, bit field and flag-like enum in the nine layer files, so that no
flag is undocumented (design `docs/plans/03-map-layer-parity-remediation/DESIGN.md` Phase 9;
ledger class `documented-unknown`). This file **aggregates**: it derives nothing. Each row
points at its source row in a layer file, and its Status equals that row's status (never
stronger). Where layer files or code disagree about a flag, the row is `unknown` and both
statements are recorded; nothing here resolves a conflict.

Reading the Meaning column: `[layer file]` + **R** (census or sample figure on the
reference disc) + **OSM** (the OSM tag the writer could derive it from, or `none`) +
**G** (the value the generator writes today, from the code). R figures are copied from the
source row; "sample" means a small parcel sample, not a disc-wide census.

Pending tests (referenced by name in Evidence for every row that is not `verified`):

- **P-census**: disc-wide R census of the field (all levels), added to
  `parser/refdata/profile/map.json` or a sibling census file, with a harness check that
  compares G against it.
- **P-name**: name-matched spot check of R samples against known real features
  (bridge, one-way street, toll road) before the field is renamed or populated.
- **P-struct**: offline byte/structural comparison of a G parcel against the R parcel for
  the same cell (the oracle; no in-vehicle loop).
- **P-spec**: a spec-conformance test on the encoder for a spec-only field, once a writer
  emits it.

## Road: multilink attribute word (offset 14)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| road bits 15:12 road_type | `map-road.md`. R: codes 0,2,3,5,6,7,8,9,10,12 seen (L0 counts in source). OSM: highway=* via `road_type.json` (mapping under revision, design F4). G: from OSM mapping, motorway 0, trunk 10, primary 7, ... | verified | `docs/schema/map-road.md` (attribute word, bits 15:12) | `parser/kiwiw/road_writer.py`, `parser/kiwiw/vocab.py` |
| road bit 11 link_id_number_flag | `map-road.md`. R: 9,897,898 of 9,897,898 set. OSM: none. G: False (no link ids emitted) | verified | `docs/schema/map-road.md` (bit 11) | `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/road_writer.py` |
| road bit 10 infra_link_flag | `map-road.md`. R: 0 of 9,897,898 set. Spec polarity inverted (0 = infra-link present); code name suggests the opposite. OSM: none. G: False | verified | `docs/schema/map-road.md` (bit 10; polarity noted there, meaning of "infra-link" on this disc unknown) | `parser/kiwiw/road_writer.py` |
| road bit 9 route_number_flag | `map-road.md`. R: 0 of 9,897,898. OSM: none (ref=* not used). G: False | verified | `docs/schema/map-road.md` (bit 9) | `parser/kiwiw/road_writer.py` |
| road bit 8 toll_flag | `map-road.md`. R: 1,147 at L0, 474 L2, 346 L4, 244 L6, 111 L8. OSM: toll=yes (assumed rule, design F9, not measured). G: False always | verified | `docs/schema/map-road.md` (bit 8; the OSM rule itself is assumed, pending P-name) | `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/road_writer.py` |
| road bit 7 selected_link_flag | `map-road.md`. R: 4,696,111 (47%) at L0, 100% L2, 0% L4-L8. OSM: none known (what determines it is open). G: False always | verified | `docs/schema/map-road.md` (bit 7; determinant open question 4) | `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/road_writer.py` |
| road bit 6 link_id_flag | `map-road.md`. Spec meaning: link-id differentials omitted (all differentials 1); code and design F9 treat it as opaque. R: 4,483,861 (45%) at L0; set exactly where n_nodes > 2 on a 12-link sample. OSM: none. G: False always | verified | `docs/schema/map-road.md` (bit 6; spec wins there, code name disagrees) | `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/road_writer.py` |
| road bit 5 reserved | `map-road.md`. R: 0 on 748/748 sampled. OSM: none. G: 0 | observed | `docs/schema/map-road.md` (bit 5). Pending: P-census | `parser/kiwiw/road_writer.py` |
| road bit 4 route_planning_tag | `map-road.md`. R: 1,238,931 (12.5%) at L0, 100% at L2-L8. OSM: none (derived from route-planning inclusion). G: False always | verified | `docs/schema/map-road.md` (bit 4) | `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/road_writer.py` |
| road bits 3:2 pseudo3d_updown | `map-road.md`. R: 0 on 100%. OSM: none. G: 0 | verified | `docs/schema/map-road.md` (bits 3:2) | `parser/kiwiw/road_writer.py` |
| road bit 1 route_type_guidance_flag | `map-road.md`. R: 0 on 100%. OSM: none. G: False | verified | `docs/schema/map-road.md` (bit 1) | `parser/kiwiw/road_writer.py` |
| road bit 0 altitude_flag | `map-road.md`. R: 0 on 100% (9,897,898). OSM: none. G: False | verified | `docs/schema/map-road.md` (bit 0) | `parser/kiwiw/road_writer.py` |

## Road: multilink header and display-class flags

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| hdr u32 bit 31 delete flag | `map-road.md`. R: 0 on 748/748 sampled. OSM: none. G: 0 (bit not written) | observed | `docs/schema/map-road.md` (multilink header bit 31). Pending: P-census | `parser/kiwiw/road_writer.py` |
| hdr u32 bit 30 temporal information present | `map-road.md`. R: 0 on 748/748 sampled. OSM: none. G: 0 | observed | `docs/schema/map-road.md` (bit 30). Pending: P-census | `parser/kiwiw/road_writer.py` |
| hdr u32 bits 29:28 expansion-data flags | `map-road.md`. R: 0 on 748/748 sampled. OSM: none. G: 0 | observed | `docs/schema/map-road.md` (bits 29:28). Pending: P-census | `parser/kiwiw/road_writer.py` |
| hdr u32 bit 15 street address header present | `map-road.md`. R: set on 748/748 sampled. OSM: none (addr:* not attached to links). G: 0, header size 8 | observed | `docs/schema/map-road.md` (bit 15). Pending: P-census, P-struct | `parser/kiwiw/synth.py` |
| display-class section word: bits 15:11 display-scale flags 1-5, bits 3:0 delete flags for the four optional sections | `map-road.md`. R: value distribution not censused. OSM: none. G: zero unless set by `build_road_frame_bytes` | unknown | `docs/schema/map-road.md` (display-class section, offset 0). Pending: P-census | `parser/kiwiw/synth.py` |
| node connection record: node type, on-boundary flag, median-strip flag, neighbour direction, additional-node change flags | `map-road.md`. R: section present (8 B x n_nodes) on 748/748 sampled; bit layout spec-only, never decoded. OSM: none. G: section omitted | observed | `docs/schema/map-road.md` (records not written by the generator). Pending: P-struct, P-spec | `parser/kiwiw/road.py` |
| additional-data record j (u16 offset, u16 size), count m | `map-road.md`. R: m = 6 on the sampled parcel, content unknown. OSM: none. G: m = 0 | observed | `docs/schema/map-road.md` (frame header, offset 8+4n). Pending: P-census | `parser/kiwiw/parcel_writer.py` |

## Road: node (shape point) attribute bits, offset +0

Conflict, not resolved here: code names (`oneway`, `planned`, `tunnel`, `bridge`,
undecoded) differ from the spec bit table (validity of one-way, one-way code, planned,
tunnel, bridge), and `map-road.md` records that the R sample matches the spec. All five
rows are `unknown`. G writes `oneway=0, planned=0, tunnel=False, bridge=False` for every
node (`parser/osm_to_parcel_geometry.py`), so bit 10 and bits 15:11 are 0 on G.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| node bit 15 (code `oneway`; spec: one-way validity, 0 = validated) | `map-road.md`. R: 0 on all 29,866,457 nodes (census). Code/design F9 read it as "one-way", spec reads it as validity. OSM: oneway=* would apply only if bits 14:13 are not the one-way code. G: 0 | unknown | `docs/schema/map-road.md` (node bit 15; its census fact is verified, its meaning conflicts). Pending: P-census, P-name | `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| node bits 14:13 (code `planned`; spec: one-way code 00/01/10/11) | `map-road.md`. R sample (Melbourne L0, 2,147 nodes): 0 on 1,235, 1 on 263, 2 on 649, 3 never; fits one-way streets. OSM: oneway=yes/-1 (do not populate until decided). G: 0 | unknown | `docs/schema/map-road.md` (node bits 14:13). Pending: P-census, P-name | `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| node bit 12 (code `tunnel`; spec: additional type 1, building-planned road) | `map-road.md`. R sample: 0 on all 2,147. OSM: tunnel=yes only if code name is right (undecided). G: False | unknown | `docs/schema/map-road.md` (node bit 12). Pending: P-census, P-name | `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| node bit 11 (code `bridge`; spec: additional type 2, tunnel) | `map-road.md`. R sample: 0 on all 2,147. OSM: bridge=yes only if code name is right (undecided). G: False | unknown | `docs/schema/map-road.md` (node bit 11). Pending: P-census, P-name | `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| node bit 10 (code: undecoded; spec: additional type 3, bridge) | `map-road.md`. R sample: set on 45 of 2,147 nodes, fits bridges in central Melbourne. OSM: bridge=yes if spec reading holds. G: 0 (copy-and-patch preserves it; synth never sets it) | unknown | `docs/schema/map-road.md` (node bit 10). Pending: P-census, P-name | `parser/kiwiw/road_writer.py` |

## Map Frame header: dipid, dsflag, divided-neighbour info

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| dipid bits 15:14 = 11 (undivided) | `map-frame.md`. R: 0xE000 at L2-L10, 0xC000 at L12. OSM: none. G: writes dipid 0x0000 (bytes 12-13) on every parcel, not the R value | observed | `docs/schema/map-frame.md` (dipid bits). Pending: P-census, P-struct | `parser/kiwiw/synth.py` |
| dipid bits 15:14 = 01 (divided, type 1 2x2) | `map-frame.md`. R: 0x6100 + low byte 0x00/0x01/0x10/0x11 at L2-L8. OSM: none. G: dipid not written on divided leaves | observed | `docs/schema/map-frame.md` (dipid bits, "G divided leaves"). Pending: P-census, P-struct | `parser/kiwiw/divide.py`, `parser/kiwiw/synth.py` |
| dipid bits 15:14 = 10 (integrated) | `map-frame.md`. R: 0xA033 (4x4 basic parcels) on about 99.9% of an L0 stride sample; 49 of 37,500 are 0xE000. OSM: none. G: 0x0000 | observed | `docs/schema/map-frame.md` (dipid bits). Pending: P-census, P-struct | `parser/kiwiw/synth.py` |
| dipid bit 13 | `map-frame.md`. R: 1 whenever slots 12-19 hold adjacency, 0 at L12; spec polarity is the opposite (0 = information contained). OSM: none. G: 0 | unknown | `docs/schema/map-frame.md` (dipid bit 13; R and spec disagree, polarity unresolved). Pending: P-census | `parser/kiwiw/synth.py` |
| dsflag (u16 at 18) | `map-frame.md`. R: 0x0064 in 100% of sample. OSM: none. G: 0x0064 (`_HEADER_DSFLAG`) | observed | `docs/schema/map-frame.md` (header offset 18). Pending: P-census | `parser/kiwiw/synth.py` |
| rlx bit 15 | `map-frame.md`. R: 0 at L0-L8, 1 at L10, L12. OSM: none. G: level-dependent as written by synth | observed | `docs/schema/map-frame.md` (header offset 20). Pending: P-census | `parser/kiwiw/synth.py` |
| divided-neighbour entry info word: bits 15:12 Y divisions - 1, 11:8 X divisions - 1, 3:0 adjacent count - 1 | `map-frame.md`. R: 100% of 15,537 R leaves at L4-L10 (ad hoc scripts, not checked in). OSM: none. G: not written (12-19 emitted by parcel code as adjacency slots only) | observed | `docs/schema/map-frame.md` (divided-neighbour entry). Pending: P-census, P-struct | `parser/kiwiw/parcel.py` |

## Background record and type-unit flags

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| type-unit +2 bits 15:14 shape class (0 point, 1 line, 2 area, 3 reserved) | `map-background.md`. R: only 1 and 2 occur; no point records. OSM: derived from way geometry (closed ring = area). G: one unit per shape class | observed | `docs/schema/map-background.md` (type unit header +2). Pending: P-census | `parser/kiwiw/background.py`, `parser/kiwiw/synth.py` |
| type-unit +2 bit 13 height info flag | `map-background.md`. R: 0 in all sampled units. OSM: none. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `parser/kiwiw/background.py` |
| type-unit +2 bit 12 reserved | `map-background.md`. R: 0 in all sampled. OSM: none. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `-` |
| record +0 bits 15:12 delete, temporal, extended-data flags, reserved | `map-background.md`. R: 0 in all sampled (204 to 2,020 records per level). OSM: none. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `parser/kiwiw/background.py` |
| record +2 bits 15:11 display scale flags 1-5 | `map-background.md`. R sample: 0x1C at L0, 0x18 at L2-L10 (0x10 on 17 of 760 L2 records), 0x10 on all L12 records. OSM: none. G: 0 (spec: never displayed) | observed | `docs/schema/map-background.md`. Pending: P-census, P-struct | `parser/kiwiw/synth.py` |
| record +6 bits 15:14 additional info type (00 frame A, 01 frame B, 10 building id) | `map-background.md`. R: 0 in all sampled. OSM: building=* could map to 10 but is not attempted. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `-` |
| record +6 bit 13 additional info flag | `map-background.md`. R: 0 in all sampled. OSM: none. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `-` |
| record +6 bit 12 name flag | `map-background.md`. R: set on 139 of 204 sampled L0 records, never at L2-L12 in the sample. OSM: name=* possible but no name offset is written. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census, P-struct | `parser/kiwiw/background.py` |
| record +6 bit 11 auxiliary data flag | `map-background.md`. R: 0 in all sampled. OSM: none. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `-` |
| record +6 bit 10 pen-up flag | `map-background.md`. R: 0 in all sampled. OSM: none (multipolygon holes not encoded). G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `parser/kiwiw/background.py` |
| record +6 bit 9 underground | `map-background.md`. R: 0 in all sampled. OSM: tunnel/layer=-1 not mapped. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `parser/kiwiw/background.py` |
| record +6 bits 8:3 reserved | `map-background.md`. R: 0 in all sampled. OSM: none. G: 0 | observed | `docs/schema/map-background.md`. Pending: P-census | `-` |
| record +6 bits 2:0 multiplication constant n (delta x 2^n) | `map-background.md`. R census `mult_const_hist`: multipliers 1-64 seen at L0, 64 dominates L4-L12, 128 never. OSM: none. G: chosen by encoder as data | observed | `docs/schema/map-background.md` (`parser/refdata/profile/map.json` `mult_const_hist`; no check compares G). Pending: P-census | `parser/kiwiw/synth.py` |
| type code (u16 at +4) | `map-background.md`. R: per-level set from `type_code_hist` (e.g. 288, 289, 290, 291, 321, 322, 578, 640, 1024). OSM: tag rules in `bg_type.json` (natural=water 290, wood/park 321, catch-all 288, ...). G: from those rules | verified | `docs/schema/map-background.md` (type code row; membership checked by `parser/tests/test_vocab.py`) | `parser/kiwiw/vocab.py`, `parser/kiwiw/synth.py` |

## Name record flags and enums

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| @0 bit 15 deletion flag | `map-name.md`. R: 0 on 1237/1237 sampled. OSM: none. G: 0 | observed | `docs/schema/map-name.md`. Pending: P-census | `-` |
| @0 bit 14 temporal-info flag | `map-name.md`. R: 0 on 1237/1237. OSM: none. G: 0 | observed | `docs/schema/map-name.md`. Pending: P-census | `-` |
| @0 bit 13 extended-data flag | `map-name.md`. R: 0 on 1237/1237. OSM: none. G: 0 | observed | `docs/schema/map-name.md`. Pending: P-census | `-` |
| @0 bit 12 reserved | `map-name.md`. R: 0 on 1237/1237. OSM: none. G: 0 | observed | `docs/schema/map-name.md`. Pending: P-census | `-` |
| @2 bits 15:11 display scale flags 1-5 | `map-name.md`. R: type 4 = 0; types 5/6 at L0 = 24 or 28; L2 types 1/5 = 16 or 24. OSM: none. G: `display_scale_flag=0` (`osm_to_parcel_geometry.py`), which R never writes for types 5/6. `map-background.md` labels the same field family `observed` | verified | `docs/schema/map-name.md` (@2 bits 15:11; byte-identical re-encode of R types 4/5/6) | `parser/kiwiw/name_writer.py`, `parser/kiwiw/synth.py` |
| @2 bits 10:8 string type (1 barycentric, 4, 5 linear type C, 6, ...) | `map-name.md`. R: `string_type_hist` census (type 1 1,042,019 at L0; type 5 7,603,420). OSM: none (chosen by feature kind). G: types written by `synth.py` | verified | `docs/schema/map-name.md` (@2 bits 10:8; string-type table) | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| @2 bit 7 height-info flag | `map-name.md`. R: 0 on 1237/1237. OSM: none. G: 0 | observed | `docs/schema/map-name.md`. Pending: P-census | `parser/kiwiw/name_writer.py` |
| @2 bit 6 string orientation (0 horizontal, 1 vertical) | `map-name.md`. R: 0 on all sampled. OSM: none. G: `vertical=False` | observed | `docs/schema/map-name.md`. Pending: P-census | `parser/kiwiw/name.py` |
| @2 bits 5:0 priority (6-bit signed, -32 invalid) | `map-name.md`. R: L0 {0: 8,877,667 (type 4), 32: 10,203,438 (types 1/5/6)}; 32 on 100% at other levels. OSM: none. G: priority 5 (`osm_to_parcel_geometry.py`) | observed | `docs/schema/map-name.md`. Pending: P-census, P-struct | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| type 5 display angle info: bit 12 rotation mode, 11:10 character orientation, 9 string rotation, 8:0 angle | `map-name.md`. R: bits 15:9 = 0x16 on 221/221 sampled. OSM: none (angle from geometry). G: `angle_flags` default 0 for synthetic records | verified | `docs/schema/map-name.md` (@12 display angle info; byte-identical re-encode) | `parser/kiwiw/name_writer.py`, `parser/kiwiw/synth.py` |
| type 1 @6 additional-background type/flags (15:14, bit 13, bit 11) | `map-name.md`. R: 0 on 202 sampled type 1 records. OSM: none. G: 0 | observed | `docs/schema/map-name.md`. Pending: P-census | `parser/kiwiw/name.py`, `parser/kiwiw/synth.py` |
| type 4 @6 placement word: bits 10:8 placement type, 7:6 target kind, 5 height flag, 3:0 point count, bit 11 aux-data | `map-name.md`. R: 0x0201 on all `A=`/`1=` records; 0x0b41 on plain names. OSM: none. G: not written for `A=`/`1=` tags | observed | `docs/schema/map-name.md`. Pending: P-census, P-struct | `parser/kiwiw/name.py` |
| placement point record: bits 15:14 side (0 on link, 1 left, 2 right, 3 either) | `map-name.md`. R: 0x0000 on sampled records. OSM: none. G: none | observed | `docs/schema/map-name.md`. Pending: P-census | `parser/kiwiw/name.py` |
| name type code (attribute 2) | `map-name.md`. Same vocabulary as background type codes. R: per-level `type_code_hist`; type 1 all 509 at L0, type 5 all 528. OSM: none. G: from vocab | verified | `docs/schema/map-name.md` (@4 type code; `parser/harness/checks/vocab.py`) | `parser/kiwiw/vocab.py` |
| `1=` and `A=` search tags (a tagged-name enum) | `map-name.md`. R: `1=` 22.9%, `A=` 7.0% of a stride sample. OSM: name/addr tags could source them. G: not written. Whether needed for address search is open | unknown | `docs/schema/map-name.md` (tag purpose). Pending: P-struct, P-name | `-` |

## Route planning flags

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| rank avg_travel_time flag | `route-planning.md`. R: False in all sampled ranks (120 regions). OSM: none. G: as written by the RP writer (no travel-time table) | observed | `docs/schema/route-planning.md` (node frame header). Pending: P-census | `parser/kiwiw/route_planning.py` |
| RP region type code | `route-planning.md`. R: all 1883 region records are type 0. OSM: none. G: 0 | observed | `docs/schema/route-planning.md` (region record). Pending: P-census | `parser/kiwiw/route_planning_writer.py` |
| node bit 31 delete flag | `route-planning.md`. R: 0 in all samples. OSM: none. G: 0 | observed | `docs/schema/route-planning.md` (node record). Pending: P-census | `parser/kiwiw/route_planning_writer.py` |
| node bit 30 upper-level correspondence table exists | `route-planning.md`. R: set in the 33 regions failing offset contiguity. OSM: none. G: never set (writer has no bit 30) | unknown | `docs/schema/route-planning.md` (node bit 30). Pending: P-census, P-struct | `-` |
| node bits 29:27 uppermost_identical_level | `route-planning.md`. R: relative, 0..3 at L2, 0..2 at L4, 0..1 at L6, 0 at L8 (171,293 nodes). OSM: none. G: writes `level//2` absolute encoding when non-zero, which conflicts with R and spec | observed | `docs/schema/route-planning.md`. Pending: P-census, P-struct | `parser/kiwiw/route_planning_writer.py`, `parser/osm_to_route_planning.py` |
| node bit 26 is_aggregated | `route-planning.md`. R: 14,650 of 171,293. OSM: none (aggregated intersections not derived). G: from `node.is_aggregated` (default False) | observed | `docs/schema/route-planning.md`. Pending: P-census, P-struct | `parser/kiwiw/route_planning_writer.py` |
| node bit 25 is_boundary | `route-planning.md`. R: 781 of 171,293. OSM: none (region boundary). G: from `node.is_boundary` | observed | `docs/schema/route-planning.md`. Pending: P-census, P-struct | `parser/kiwiw/route_planning_writer.py` |
| node bits 20/19/18 parcel_boundary, traffic_light, rotary | `route-planning.md`. R: 0 of 171,293 each. OSM: highway=traffic_signals, junction=roundabout (not used). G: always False | observed | `docs/schema/route-planning.md`. Pending: P-census | `parser/kiwiw/route_planning_writer.py` |
| node is_suburb, is_semi_urban flags | `route-planning.md`. R: not separately recorded. OSM: none. G: writer has no node-level suburb bits at all (the same names exist only on link records) | unknown | `docs/schema/route-planning.md` (node record). Pending: P-census | `parser/kiwiw/route_planning_writer.py` |
| link adj word bit 15 delete, bit 14 infra-link | `route-planning.md`. R: 0 in 428,951 links. OSM: none. G: not written (adjacent-node word is 13-bit only) | observed | `docs/schema/route-planning.md` (link record). Pending: P-census | `-` |
| link flags word bit 15 suburb, bit 14 semi-urban highway | `route-planning.md`. R: 0 in 428,951 links. OSM: none. G: is_suburb=False, is_semi_urban_highway=False (`osm_to_route_planning.py`) | observed | `docs/schema/route-planning.md`. Pending: P-census | `parser/kiwiw/route_planning_writer.py`, `parser/osm_to_route_planning.py` |
| link flags word bit 13 reverse | `route-planning.md`. R: 214,379 of 428,951 (50%). OSM: derived from way direction (`not link.forward_direction`). G: same derivation | observed | `docs/schema/route-planning.md`. Pending: P-census, P-struct | `parser/kiwiw/route_planning.py`, `parser/osm_to_route_planning.py` |
| regulation record between-links bit | `route-planning.md`. R: 232,083 of 236,327 records set. OSM: type=restriction relations (1 of 57,372 resolved in region 178). G: `is_between_links` False, no between-links cost | observed | `docs/schema/route-planning.md`. Pending: P-census, P-struct | `parser/kiwiw/route_planning_writer.py`, `parser/build_route_graph.py` |
| regulation passage_code enum | `route-planning.md`. R: 127 (231,996), 1 (4,186), 2 (88); spec table ch.10.11 not decoded. OSM: restriction=* (mapping unknown). G: passed through by writer | unknown | `docs/schema/route-planning.md` (passage code values). Pending: P-census, P-spec | `parser/kiwiw/route_planning_writer.py` |
| between-links cost aggregated-intersection flag | `route-planning.md`. R: set on all 32,726 records. OSM: none. G: no between-links cost records | observed | `docs/schema/route-planning.md`. Pending: P-census, P-struct | `parser/kiwiw/route_planning_writer.py` |

## Index (IDX) flags

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| STFG presence bitmap (general rule) | `index-idx.md`. Bit i (LSB first, byte 0 first) = presence of the i-th gated field. R: rule holds on every decoded family. OSM: none (derived from which fields the record carries). G: `_stfg_bytes` | verified | `docs/schema/index-idx.md` (STFG row; `parser/tests/test_roundtrip_idx.py`) | `parser/kiwiw/search_frame.py`, `parser/osm_to_address_index.py` |
| SADSR SRMX street STFG value | `index-idx.md`. R: 0x7f00 on 38,119 of 38,120 (201) and all 2,827 (202): bits 0-6 present incl. NAME. G: 0x3f00 (bits 0-5; NAME absent) and its code comment says this matches the real disc, which the layer file contradicts | unknown | `docs/schema/index-idx.md` (STFG row and SRMX row) versus `parser/osm_to_address_index.py` lines 468-476. Conflict recorded, not resolved. Pending: P-struct | `parser/osm_to_address_index.py` |
| SADSR SRT1 address-range STFG = 0x07 | `index-idx.md`. R: bits 0-2 set (ZIPN, PRFX, STAD). G: same three bits | verified | `docs/schema/index-idx.md` (STFG row; SRT1 row; `parser/tests/test_roundtrip_idx_full.py`) | `parser/osm_to_address_index.py`, `parser/kiwiw/search_frame.py` |
| SADSR SRHA suburb STFG | `index-idx.md`. R: SRHA records decode byte-identical in 201 (STFG value not tabulated). G: bits 1-5 and 7 (STID absent) | verified | `docs/schema/index-idx.md` (SRHA row; `parser/tests/test_roundtrip_idx_full.py`) | `parser/osm_to_address_index.py` |
| POISR SRMX STFG (2 bytes) | `index-idx.md`. R: POISR202 varies (fd07, fd06, fc07, ...) over 10,969 records. G: not generated | observed | `docs/schema/index-idx.md` (POISR SRMX row). Pending: P-struct | `parser/kiwiw/search_frame.py` |
| ITSSR SRBT/SRAL STFG | `index-idx.md`. R: 0 on 2,803 SRBT in ITSSR202. G: not generated | observed | `docs/schema/index-idx.md` (ITSSR row). Pending: P-struct | `-` |
| POIDT001-007 / 012 / 013 STFG | `index-idx.md`. R: field present in the DCTF definitions, values not tabulated (013 has a 2-byte STFG). G: not generated | observed | `docs/schema/index-idx.md` (POIDT body rows, DCTF dump). Pending: P-struct | `-` |
| SPFX, SSFX, STYP, GDXY presence bits | `index-idx.md`. R: never present (STFG bits 0). G: absent | unknown | `docs/schema/index-idx.md` (SPFX SSFX STYP GDXY row). Pending: P-census | `-` |
| DSIR/definition FGFZ, FGSA fields (flag-named words) | `index-idx.md`. Named in field lists (SRMX, SRHA, SRT1, POISR, ITSSR) with no meaning given. R: present; values not tabulated. G: written per `osm_to_address_index.py` `fgfz` | unknown | `docs/schema/index-idx.md` (record family rows list FGFZ/FGSA without semantics). Pending: P-census | `parser/osm_to_address_index.py` |
| ARCD area code | `index-idx.md`. R: always starts 0x1e; three tiers. OSM: none. G: written by the index builder | unknown | `docs/schema/index-idx.md` (ARCD row: semantics unknown). Pending: P-census | `parser/kiwiw/search_frame.py` |
| CTGY category code | `index-idx.md`. R: multiples of 128, about 38% vendor codes absent from the spec (QLD sample). OSM: amenity/shop tags (WP4). G: not generated | observed | `docs/schema/index-idx.md` (CTGY row). Pending: P-census | `-` |

## Disc layout, parcel management and parameters flags

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| DSA side/layer flag bits (bit 7, 6 of low byte) | `disc-layout.md`. R: clear on all 13 populated MHT entries. OSM: none. G: 0 (code masks with 0x3F) | observed | `docs/schema/disc-layout.md`. Pending: P-census | `parser/kiwiw/volume.py` |
| Module Identification category bits (7 diagnostic, 6 test, 1:0 initial/program/library/data) | `disc-layout.md`. R: 0x01 (program). OSM: none. G: copied | observed | `docs/schema/disc-layout.md` (offset 20). Pending: P-census | `-` |
| header 416 Data contents word 0: bit 15 main map, 14 route planning, 13 index data | `disc-layout.md`. R: 0xE000, words 1-3 = 0. OSM: none. G: copied from R | verified | `docs/schema/disc-layout.md` (offset 416; `parser/tests/test_roundtrip_alldata_header.py`); whether the head unit gates on it is open | `parser/kiwiw/volume.py` |
| header 476 Background default: bit 15 in-map parcels (0 land, 1 sea), bit 14 out-of-map | `disc-layout.md`. R: 0x4000. OSM: none. G: copied | verified | `docs/schema/disc-layout.md` (offset 476; `parser/tests/test_roundtrip_alldata_header.py`) | `parser/kiwiw/volume.py` |
| PDMDH file name designation (bit 0, bytes 4..5) | `parcel-management.md`. R: 0 (inline BMT). OSM: none. G: 0 | observed | `docs/schema/parcel-management.md` (PDMDH 4..5). Pending: P-census | `parser/kiwiw/volume.py` |
| LMR bits 9:8 reserved | `parcel-management.md`. R: 0 by round trip. OSM: none. G: 0 | assumed | `docs/schema/parcel-management.md`. Pending: P-census | `parser/kiwiw/volume_writer.py` |
| LMR 4..23 five display scale flags (u32 scale denominators, FFFFFFFF unused) | `parcel-management.md`. R: per level, e.g. L0 5000/10000/20000, L12 40960000/81920000. OSM: none. G: copied from `grid.json` | observed | `docs/schema/parcel-management.md` (LMR 4..23). Pending: P-struct | `parser/kiwiw/volume.py` |
| LMR bits 7:4 upper_level, 3:0 lower_level (enums) | `parcel-management.md`. R: upper 0 at L12, 2 elsewhere; lower 2 at L12-L2, 0 at L0. OSM: none. G: copied | observed | `docs/schema/parcel-management.md` (LMR 0..1). Pending: P-census | `parser/kiwiw/volume.py` |
| BSMR bits 15:10 and 9:8 reserved | `parcel-management.md`. R: 0 by round trip. OSM: none. G: 0 | assumed | `docs/schema/parcel-management.md` (BSMR 0..1). Pending: P-census | `parser/kiwiw/volume_writer.py` |
| LMR 40..41 bits 15:14 reserved | `parcel-management.md`. R: 0 by round trip. OSM: none. G: 0 | assumed | `docs/schema/parcel-management.md`. Pending: P-census | `parser/kiwiw/volume_writer.py` |
| parcel mgmt record bits 15:10 reserved | `parcel-management.md`. R: 0. OSM: none. G: 0 | assumed | `docs/schema/parcel-management.md` (parcel mgmt record 0..1). Pending: P-census | `parser/kiwiw/parcel_mgmt.py` |
| parcel mgmt record bits 9:8 parcel_type (0 root, 1..3 divided) | `parcel-management.md`. R: 2,113 root type 0, 42 subrecords type 1. OSM: none. G: as built by mesh code | verified | `docs/schema/parcel-management.md` (`parser/tests/test_mesh_divided_locate.py`, `parser/tests/test_divide.py`) | `parser/kiwiw/parcel_mgmt.py`, `parser/kiwiw/mesh.py` |
| parcel mgmt record bits 7:0 list_type (0 = 6-byte slots) | `parcel-management.md`. R: 0 in every record. OSM: none. G: 0 | verified | `docs/schema/parcel-management.md` (parser rejects non-zero on all R records) | `parser/kiwiw/parcel_mgmt.py`, `parser/kiwiw/mesh.py` |
| BMR file name (present only with file-designation flag) | `parcel-management.md`. R: absent. OSM: none. G: absent | spec-only | `docs/schema/parcel-management.md` (BMR 6..17). Pending: P-spec | `-` |
| drawing parameter mgmt record flag byte: bit 7 line-style palette, bit 6 map-element drawing params | `parameters-metadata.md`. R: not measured. OSM: none. G: files copied through | spec-only | `docs/schema/parameters-metadata.md` (drawing parameter mgmt record). Pending: P-spec | `-` |
