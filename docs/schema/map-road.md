# Map Frame: Road sub-frame

The Road Data Frame (spec ch.7.2) is one of the three content sub-frames of a Map Frame
(the others are background and name; see `map-frame.md` for the header and sub-frame
directory, `map-background.md`, `map-name.md`). It holds every road of one parcel, grouped
by display class. A road is a **multilink**: a polyline of one or more links that share
attributes. Code calls a multilink a `RoadLink`; the spec calls its shape points "nodes"
in the code and "link shape data" in the spec (the code's `RoadNode` is a spec Link Shape
Data entry: a vertex plus the attributes of the link leading to the next vertex).

Nesting: Road frame -> 8-byte header -> display-class table (4 bytes x n) -> additional-data
table (4 bytes x m) -> per display class: 2-byte display-scale word + multilinks -> per
multilink: header, shape data, node/link connection records, additional-node info,
altitude, passage regulation, street address.

Endianness and units: all multi-byte fields are big-endian. `SWS`/`D` fields are stored
halved (value x 2 = bytes) except the sentinel `0xFFFF` = absent. Coordinates are
parcel-local pixels; see "Shape coordinates". The decoder reads only header, shape data
and attributes; the connection, additional-node, altitude, passage-regulation and street
address sections are carried verbatim (`raw_bytes`) on the read side and are **absent** on
the synthetic (generated) side, which writes header + shape only.

Display class is stored implicitly (position in the display-class table), not per record.
Road type is stored per multilink in the attribute word.

## Road frame header (spec 7.2.1)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u16 header size | Spec: SWS header size. Code stores it raw (`header_size_raw`) and never uses it; G writes 0. | unknown | Spec ch.7.2.1 says SWS; R value not censused. Code ignores it. | `parser/kiwiw/road.py` |
| 2 u16 n_intersections | Total intersection nodes (3+ roads), 0xFFFF = invalid. R carries 0xFFFF on the sampled parcel; G writes 0. | observed | Sampled Melbourne L0 parcel (748 links): 65535. Spec says 0xFFFF = invalid, consistent. Not censused across the disc. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 4 u8 n_display_classes (n) | Number of display-class management records; spec allows up to 16. | verified | Read by every road decode; `parser/tests/test_roundtrip_parcel_content.py` byte-identical frame rewrite; `parser/refdata/profile/map.json` display_class_hist. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 5 u8 n_additional_data (m) | Count of additional-data management records (passage-code frame, composite-node frame, extension). Sampled parcel: 6. | observed | Sampled parcel: 6. Spec 7.2.1 item 4. Content is not decoded. | `parser/kiwiw/road.py` |
| 6 u16 level word: bits 15:10 route-planning level | Level of route-planning data matching this parcel, signed -31..+31, -32 = null. Bits 9:0 reserved. Sampled raw word 0x0800 (level +2). | observed | Sampled parcel `lvl_field_raw` = 2048. G writes 0 where R writes real values. Sign handling in code: `extract(v,10,15)` is unsigned. | `parser/kiwiw/road.py` |
| 8 + 4i: display-class record i, u16 offset | Offset to display class i's section (D, stored halved), 0xFFFF if empty. | verified | `parser/tests/test_roundtrip_parcel_content.py`; empty-slot sentinel written by `build_road_frame_bytes` and read back. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 8 + 4i + 2: display-class record i, u16 count | Bits 11:0 = number of multilinks (1..4095; 0 when empty); bits 15:12 reserved. | verified | `parser/tests/test_roundtrip_parcel_content.py` (same as above); spec 7.2.1.1. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 8 + 4n + 4j: additional-data record j (u16 offset, u16 size) | Offset (D) and size (SWS) of j-th additional block. Content captured raw and rewritten at its offset. | observed | Captured as `additional_data_raw`; round-trip is byte-identical; G writes m = 0. Content meaning unknown. | `parser/kiwiw/road.py`, `parser/kiwiw/parcel_writer.py` |

Display-class sections are ordered ascending by class (spec 7.2.1.1: "data is sorted in the
order in which records are displayed"). Synthetic frames must emit table slots for every
class 0..max, using the 0xFFFF sentinel for empty ones, because the decoder assigns class
from the table index (`build_road_frame_bytes`).

## Display-class section (spec 7.2.2.1)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u16 display scale flag | Bits 15:11 = display-scale flags 1-5; bits 3:0 = delete flags for node/link connection, additional-node header, altitude header, passage regulation header; other bits reserved. Held raw (`display_class_flags`). | unknown | Stored and round-tripped; bit meaning is spec-only and the R value distribution is not censused. G writes what `build_road_frame_bytes` emits (zero flags word unless set). | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 2.. multilink records | Consecutive multilinks, count from the display-class record. | verified | Byte-identical round-trip of whole road frames on R: `parser/tests/test_roundtrip_parcel_content.py`; `parser/roundtrip_parcel_content.py`. | `parser/kiwiw/road.py` |

## Multilink header (spec 7.2.2.1.1.1)

Sampled on R (Melbourne L0 parcel, 748 links, all satisfied): record length = header size +
shape size + 8 x n_nodes (connection info) + additional-node + altitude + passage-regulation
+ street-address sizes. This is a measurement made for this document, not an existing test.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u32 bits 7:0 | Header size, units of 2 bytes. R = 12 (24 bytes) on every sampled link (16 fixed + 4 link id + 2 id diff + 2 street address header). G writes 8 (16 bytes). Read as SWS. | verified | Node offset derives from this in `road.py`; whole-frame byte-identical round trip; 748/748 sampled links consistent. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 0 u32 bits 27:16 | Multilink size, units of 2 bytes (spec allows 1..4095, so max 8190 bytes). Used to advance to the next link. | verified | Read in `road.py`; whole-frame round trip; 748/748 sampled links equal `len(raw_bytes)`. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 0 u32 bit 31 | Multilink delete flag. 0 on all sampled links. | observed | Sampled: 748/748 zero. Undecoded by code (preserved via raw bytes). | `parser/kiwiw/road_writer.py` |
| 0 u32 bit 30 | Temporal information present. 0 on all sampled links. | observed | Sampled: 748/748 zero. | `parser/kiwiw/road_writer.py` |
| 0 u32 bits 29:28 | Expansion-data flags (record, header). 0 on all sampled links. | observed | Sampled: 748/748 zero. | `parser/kiwiw/road_writer.py` |
| 0 u32 bit 15 | Street address management header present. 1 on all sampled R links (the header word then sits at record offset 22); G writes 0. | observed | Sampled: 748/748 set. Spec 7.2.2.1.1.1 item 1. | `parser/kiwiw/road_writer.py` |
| 4 u16 bits 10:0 | Number of nodes (shape vertices with a node record). Spec allows 1..511. | verified | Read in `road.py`; round-trip; test_road_encoder asserts `n_nodes` equality. `parser/tests/test_road_encoder.py`. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 6 u16 bits 11:0 | Shape information size, units of 2 bytes. R: equals the byte length of the node records plus their intermediate points on 748/748 sampled links. G writes 0 here. | observed | Measured on the sampled parcel. Decoder reads it into `sws(extract(...))` but does not use it to walk shapes (walks by node count and nip). G writes 0, which a strict reader could reject (not tested on hardware). | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| 8 u16 bits 11:0 | Additional node information size, units of 2 bytes. Non-zero on R (values 4..26 seen); 0 on G. | observed | Sampled parcel, sizes reconcile with record length (see above). | `parser/kiwiw/road_writer.py` |
| 10 u16 bits 11:0 | Altitude information size. 0 on all sampled links, and `altitude_flag` is False on every R link. | observed | Sampled parcel; `parser/refdata/profile/map.json` altitude_flag False 9,897,898 of 9,897,898. | `parser/kiwiw/road_writer.py` |
| 12 u16 bits 11:0 | Passage regulation information size. Mostly 0, some non-zero. | observed | Sampled parcel. | `parser/kiwiw/road_writer.py` |
| 14 u16 multilink attribute | See "Multilink attribute word". | verified | See `parser/refdata/profile/map.json` and the attribute table below. | `parser/kiwiw/road.py`, `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| 16 u32 origin absolute link ID | Present when `link_id_number_flag` = 1: 2-bit direction + 30-bit line number. R values are 20-24-bit numbers ascending within a display class. G omits (flag 0 and header size 16). | observed | Sampled parcel: e.g. 0x000ee0a3, 0x00094c685 ascending. Spec 7.2.2.1.1.1 (8-2). `link_id_number_flag` is True on 9,897,898 of 9,897,898 R links (`parser/refdata/profile/map.json`). | `parser/kiwiw/road.py` |
| 20 u16 end-point link ID differential | End id minus origin id (>= 0). R value = n_nodes - 2 on all shown samples (n_nodes = 2 gives 0). | observed | Sampled parcel first 12 links. | `parser/kiwiw/road.py` |
| 22 u16 street address size | Spec (10): bits 11:0 = size of street address info, units of 2 bytes. Present when header bit 15 = 1. | observed | Sampled: 748/748 headers of 24 bytes; sections reconcile to record length with this word as the address size. | `parser/kiwiw/road_writer.py` |
| Route number fields (alpha u16, numeric u16) | Present when `route_number_flag` = 1. | spec-only | Spec (8-4), (8-5). `route_number_flag` is False on all R links (map.json), so the field is never exercised. | `-` |
| Route-type guidance offset (u16, D) | Present when `route_type_guidance_flag` = 1. | spec-only | Spec (8-6). Flag False on all R links (map.json). | `-` |

## Multilink attribute word (record offset 14, spec 8-1)

R census: `parser/refdata/profile/map.json` `levels.<n>.road.link_flag_hists`. Population values
below are level 0 (9,897,898 links) unless stated.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| bits 15:12 road_type | Road type code (spec: road class code, ch.32.2). See vocabulary tables. | verified | R census `road_type_hist` present at L0/L2/L4/L6/L8, coverage test `parser/tests/test_vocab.py::test_coverage_against_reference_census`; spec 8-1-1 says "see chapter 32". | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py`, `parser/kiwiw/road_writer.py` |
| bit 11 link_id_number_flag | Link ID number specified (link IDs present in header). 1 on 100% of R links; G writes False. | verified | Census 9,897,898/9,897,898; `test_road_encoder.py` asserts flag equality after re-encode. Spec 8-1 agrees on position. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| bit 10 infra_link_flag | Spec: 0 = infra-link present, 1 = not infra-link (inverted sense). R: False (0) on 100% of links. Code stores the raw bit under a name that suggests the opposite polarity. | verified | Census `infra_link_flag` 0 set of 9,897,898 in `parser/refdata/profile/map.json`; spec 7.2.2.1.1.1 (8-1) says bit10 0 = infra-link. Position agrees; meaning (what "infra-link" means for this disc) unknown. | `parser/kiwiw/road.py` |
| bit 9 route_number_flag | Route number specified. 0 on 100% of R links. | verified | Census `route_number_flag` 0 set of 9,897,898 in `parser/refdata/profile/map.json`; spec 8-1. | `parser/kiwiw/road.py` |
| bit 8 toll_flag | Toll (charged) multilink. R: 1,147 of L0, 474 at L2, 346 at L4, 244 at L6, 111 at L8. | verified | Census counts in `map.json`; spec 8-1. OSM source rule (`toll=yes`) is assumed, not measured. | `parser/kiwiw/road.py` |
| bit 7 selected_link_flag | Spec: link used for a selected (navigable) route; requires `link_id_number_flag`. R: 47% at L0 (4,696,111), 100% at L2, 0% at L4-L8. | verified | Census in `map.json`. Correlation with road class or name not established (F9 design item). Spec name "Navigable multilink flag" in 8-1-3 heading. | `parser/kiwiw/road.py` |
| bit 6 link_id_flag | Spec: "Link ID Differential Information Delete Flag": 1 = differential IDs omitted because every link differential is 1. R: 45% at L0 (4,483,861). On the sampled parcel the flag is set exactly where n_nodes > 2, consistent with the spec meaning (sample: 12 links). | verified | Census in `map.json`. Meaning reading rests on the spec plus the 12-link sample; the code treats it as an opaque flag ("link_id_flag"). Spec wins. | `parser/kiwiw/road.py` |
| bit 5 | Reserved. 0 on all sampled links; preserved verbatim by the copy-and-patch encoder, written 0 by the synthetic encoder. | observed | Sampled: 748/748 zero. Spec: RESERVED. | `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| bit 4 route_planning_tag | Multilink is contained in a link of the corresponding route-planning data. R: 12.5% at L0 (1,238,931), 100% at L2/L4/L6/L8. | verified | Census in `map.json`. Spec 8-1-8. | `parser/kiwiw/road.py` |
| bits 3:2 pseudo3d_updown | 0 none, 1 up (start to end), 2 down, 3 reserved. R: 0 on 100% of links. | verified | Census 0 for all (`pseudo3d_updown` hist). Spec 8-1-5. | `parser/kiwiw/road.py` |
| bit 1 route_type_guidance_flag | Guidance data offset present. 0 on 100% of R links. | verified | Census `route_type_guidance_flag` False 9,897,898. | `parser/kiwiw/road.py` |
| bit 0 altitude_flag | Altitude information specified. 0 on 100% of R links. | verified | Census `altitude_flag` False 9,897,898. | `parser/kiwiw/road.py` |

Note on "verified": the bit positions are checked by the R census and `test_road_encoder.py`
round-trip; because decode and encode share one layout the round-trip alone cannot expose a
wrong position, so agreement with the spec bit table (all positions match) is the second
leg. Meaning for `link_id_flag` and `selected_link_flag` on R (what determines them) is a
different question, tracked in Open questions.

## Shape data: nodes and intermediate points (spec 7.2.2.1.1.2)

A multilink has `n_nodes` shape records starting at the header size offset. Each is a
6-byte node followed by `nip` 2-byte offset pairs.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| node +0 u16 bits 9:0 nip | Number of intermediate points between this node and the next (0..1023). R sampled: nip 0 in 2,011 of 2,147 nodes, 1-5+ in the rest. | observed | Sampled parcel; shape size equals node bytes plus 2 x nip on 748/748 links. Round-trip preserves nip (`raw_bytes`); `road_writer.encode_road_link` reads it but never changes it. | `parser/kiwiw/road.py`, `parser/kiwiw/road_writer.py` |
| node +0 u16 bit 15 | Code name `oneway`. Spec: "Validated one-way" (0 = validated, 1 = not validated), a validity bit for the one-way code, not the direction. R: 0 on all 29,866,457 nodes. | verified | Census `oneway` all 0 (`map.json`), spec 7.2.2.1.1.2 (1). Conflict in naming: code and the F9 design note treat it as "one-way = 0 so one-way is not in the map layer"; the spec reads bits 14:13 as the one-way code (see next row). Spec position wins; the census fact stands. | `parser/kiwiw/road.py`, `parser/kiwiw/road_writer.py`, `parser/kiwiw/synth.py` |
| node +0 u16 bits 14:13 | Code name `planned` (0..3). Spec: one-way code (00 none, 01 one-way forward, 10 one-way backward, 11 two-way prohibited). R sampled: value 0 on 1,235 nodes, 1 on 263, 2 on 649, never 3 (2,147 nodes, Melbourne L0). Populations are inconsistent with a "building-planned" flag and fit one-way streets. | unknown | Sampled parcel (this document). Code name and the writer's treatment (one-way is not in the map layer; oneway is 0 on all nodes) conflict with the spec reading. No test distinguishes. Winner: undecided; do not populate from OSM until decided. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| node +0 u16 bit 12 | Code name `tunnel`. Spec: bit 12 = additional type 1 (building-planned road). R sampled: 0 on all 2,147 nodes. | unknown | Sampled parcel only; code and spec name different meanings for this bit. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| node +0 u16 bit 11 | Code name `bridge`. Spec: bit 11 = additional type 2 (tunnel). R sampled: 0 on all 2,147 nodes. | unknown | Sampled parcel only; code and spec conflict. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |
| node +0 u16 bit 10 | Undecoded by code (preserved). Spec: additional type 3 (bridge). R sampled: set on 45 of 2,147 nodes, which fits bridges/overpasses in central Melbourne. | unknown | Sampled parcel (this document). Code documents it as "undecoded". Spec reading is plausible but unchecked against known bridge geometry. | `parser/kiwiw/road_writer.py` |
| node +2 u16 x | Bits 12:0 coordinate; bits 15:13 relative position in integrated parcel. Decoded `value + region * 4096`. | verified | `parser/tests/test_road_encoder.py::test_encode_region_coord_roundtrip_synthetic` and real-node round trip; spec 7.2.2.1.1.2 (2). | `parser/kiwiw/coordconv.py` |
| node +4 u16 y | Same encoding for y. y grows toward the south in `xy_to_latlon` (lat = lat_hi - y/range x span). | verified | Encoding round-trip as above. Orientation is unverified against a known point. Encoding `verified`, orientation `assumed`. | `parser/kiwiw/coordconv.py` |
| node +6.. nip x (i8 dx, i8 dy) | Offset from the previous shape point (node or intermediate point), each -128..127, in the same pixel unit as coordinates. Nip points follow their node before the next node. | observed | Decoded by walking `xc += i8(...)`; preserved verbatim by the copy-and-patch encoder. Synthetic encoder never emits them (nip = 0). Delta semantics from spec (4-1), (4-2); no independent geometry oracle beyond decoded points landing inside the parcel bbox. | `parser/kiwiw/road.py`, `parser/kiwiw/synth.py` |

### Shape coordinates

Spec: a basic parcel is 4096 x 4096; an integrated parcel encodes up to 8 basic parcels
along an axis by using bits 15:13 as the parcel index, giving 4096 x 8 = 32768. The code's
`COORD_RANGE = 1 << 15` follows that and is labelled "not spec-confirmed" in its own
docstring. R measurement (design doc F1, not repeated here): node maxima observed 0..4096
at L2-L8 and up to 16384 at rural L0, so the per-parcel effective range is smaller than the
encodable range. This schema does not settle it; the coordinate range per (level, parcel
class) is owned by `map-frame.md`.

Synthetic encoder: nodes only, no intermediate points, `encode_region_coord` uses
`region = x // 4096`, `value = x % 4096` (value bit 12 always 0). The R encoding may use
value bit 12; both decode to the same pixel.

## Records not written by the generator

These sections exist on R (sizes measured above) and are carried verbatim on the read side;
the generator writes none of them.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Node/link connection records, 8 bytes per node | Node type (start/middle/end), on-boundary flag, median-strip flag, neighbour parcel direction, crossing multilink (display class 4b, number 12b, node 9b) plus additional-node change flags and offset. Never decoded. | observed | Section size = 8 x n_nodes on 748/748 sampled links. Bit layout is spec-only (7.2.2.1.1.3). G omits the section; whether the head unit tolerates its absence is untested. | `parser/kiwiw/road.py` |
| Additional node information | Per-node link id, lanes, guidance, street names, region numbers, etc. selected by the change-flags word. Never decoded. | spec-only | Spec 7.2.2.1.1.4 area; sizes observed only (see header table). | `parser/kiwiw/road.py` |
| Altitude information | Never present on R sampled (altitude_flag 0 everywhere). | observed | Census `altitude_flag` all False. | `-` |
| Passage regulation information | Sizes non-zero on some R links; content never decoded. | unknown | Sampled sizes; spec 7.2 sub-sections. | `parser/kiwiw/road.py` |
| Street address information | Address-range data per link, sized by header word at offset 22. Content not decoded here (see route-planning and index layers for address use). | unknown | Sampled size words only. `docs/design/target-disc.md` WP3 covers address work. | `parser/kiwiw/road.py` |

## Link identity and the link-id registry

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| On-disc absolute link ID | 32 bits: 2-bit direction (0 simple, 1 forward simple, 2 backward simple, 3 complex) + 30-bit line number; 0 reserved; 1073741823 = unfixed. Unique per link across the medium, ascending, shared by main map, route planning and guidance. Origin at record offset 16, end-differential at offset 20. | spec-only | Spec 7.2.2.1.1.1 (8-2). R values seen on one parcel; direction bits and global uniqueness not checked. | `parser/kiwiw/road.py` |
| `RoadLink.link_id` (IR only) | Positional index in the parcel's road link list per `docs/design/target-disc.md` "Link identity"; not encoded in KWI bytes. | assumed | Design doc says "positional index within its parcel's road frame" while the registry docstring says it mints arbitrary sequential integers and does not compute positional indices. Both recorded; the registry code is what runs. Neither equals the on-disc absolute link ID. | `parser/kiwiw/model.py`, `parser/kiwiw/link_id_registry.py` |
| Registry key `(level, osm_way_id, ordinal)` | Ordinal = 0-based chain index along the OSM way, assigned at parcel-split time; per level. Registry mints ids 0,1,2,... on first assign, idempotent, `items()` sorted by key. | verified | `parser/tests/test_link_id_registry.py` (way split across parcels, reassign idempotent, determinism). | `parser/kiwiw/link_id_registry.py` |
| Generated link ID fields | G writes `link_id_number_flag` = 0 and no ID fields, so no on-disc link IDs are produced; route-planning links and index LKID resolve through the registry, not through the map layer. | assumed | `parser/osm_to_parcel_geometry.py` sets `link_id_number_flag=False`; `parser/kiwiw/synth.py` writes header 16. Whether the head unit requires IDs for routing or address lookup is untested (index-idx.md, route-planning.md). | `parser/kiwiw/synth.py` |

## Vocabulary: road type (spec ch.32.2 road class code) and display class (ch.32.1)

Ch.32 exists in the archived spec and defines both code tables. The vocabulary notes in
`docs/design/osm-vocabulary-mapping.md` and `parser/kiwiw/roadtypes.py` state that the spec has no code
table; that came from reading `07A1122e.pdf` only (7.A.1 is empty) and never consulted
`spec/format_english/pdf/3200122e.pdf`. This document uses the ch.32 table as the meaning
source. R counts are level 0 (`parser/refdata/profile/map.json`). Where R's population is
implausible under the ch.32 label, the row says so.

### Road type (attribute bits 15:12)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 | Spec (overseas): freeway class 1 (Japan: highway). R: 18,241 links at L0, 1,237 at L2 (L2 pairs with display class 12), 854/759/727 at L4/L6/L8. Plausibly motorway. | spec-only | Spec ch.32.2. R count from `map.json`; label fits, no name-matched check. | `parser/refdata/vocab/road_type.json`, `parser/kiwiw/roadtypes.py` |
| 1 | Freeway class 2 (urban highway). Not on R. | spec-only | Spec ch.32.2; absent from `road_type_hist`. | `-` |
| 2 | Highway class > 91 km/h (national road). R: 848,884 at L0, 58,909 at L2, >= 95% of L4-L8. The dominant coarse-level class. Best read as R's main arterial class. | spec-only | Spec ch.32.2; `map.json`; name-matched sampling of Brisbane and Longreach. | `parser/refdata/vocab/road_type.json` |
| 3 | Throughway class 51-90 km/h (main district road). R: 370,408 at L0, 35,639 at L2. | spec-only | Spec ch.32.2; `map.json`. | `parser/refdata/vocab/road_type.json` |
| 4 | Local class 31-50 km/h (prefectural road). Not on R. | spec-only | Spec ch.32.2; absent from R census. `roadtypes.py` label "prefectural road" agrees with spec. | `parser/kiwiw/roadtypes.py` |
| 5 | Frontage road (Japan: general road 1, trunk). R: 374,388 at L0. | spec-only | Spec ch.32.2; `map.json`. | `parser/refdata/vocab/road_type.json` |
| 6 | Very low speed road < 30 km/h (Japan: general road 2). R: 3,046,886 at L0, the second most common. Plausibly residential. | spec-only | Spec ch.32.2; `map.json`. | `parser/refdata/vocab/road_type.json` |
| 7 | Private road. R: 38,493 at L0, 6 at L2, 5/3/2 at L4/L6/L8. `docs/design/osm-vocabulary-mapping.md` maps OSM primary to 7 (by rarity ranking). Spec label conflicts with that mapping. | spec-only | Spec ch.32.2; `map.json`; `docs/design/osm-vocabulary-mapping.md`. Conflict recorded: the spec label wins as the format definition, but R's use of 7 at coarse levels (roads kept when nearly everything else is dropped) suggests R does not use the overseas labels literally. | `parser/refdata/vocab/road_type.json` |
| 8 | Walkway. R: 71,032 at L0. `docs/design/osm-vocabulary-mapping.md` maps OSM secondary to 8. | spec-only | Spec ch.32.2; `map.json`. Same caveat as code 7. | `parser/refdata/vocab/road_type.json` |
| 9 | Non-navigable road. R: 5,127,756 at L0, the most common. Not present at L2+. Design F4 targets track/unsealed -> 9 and service -> 6 or 9. | spec-only | Spec ch.32.2; `map.json`; parity design F4. | `parser/refdata/vocab/road_type.json` |
| 10 | Ferry route. R: 1,772 at L0, 86 at L2, 27/10/8 at L4/L6/L8. `road_type.json` maps OSM trunk to 10; that contradicts the spec label and R's counts (ferries are rare, trunk roads are not). | spec-only | Spec ch.32.2; `map.json`; `road_type.json` (mapping under revision by design F4). Spec wins on label; mapping is a defect tracked in the parity design. | `parser/refdata/vocab/road_type.json` |
| 11 | Car train. Not on R. | spec-only | Spec ch.32.2. | `-` |
| 12 | Public-vehicle-only road. R: 38 at L0. | spec-only | Spec ch.32.2; `map.json`. | `-` |
| 13 | Carpool lane. Not on R. | spec-only | Spec ch.32.2. | `-` |
| 14-15 | Reserved. | spec-only | Spec ch.32.2. | `-` |

### Display class (table index)

Spec ch.32.1 (overseas): 15 ferry/car train, 14 under construction, 13 non-navigable, 12
walkway, 11 private road, 8 residential class (A5), 7 local class (A4), 6 throughway (A3), 5
highway class (A2), 4 freeway 2 (A1.5), 3 freeway 1 (A1); 9, 10 reserved; 2 and 1 reserved;
"class codes 15 to 3 are set in drawing order". R's use differs from these labels (see
below), and the spec says the class definitions live in metadata (see `parameters-metadata.md`).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Display class as a function of road type (R) | On R display class is a deterministic function of road type: type 10 -> 0, 8 -> 3, 7 -> 4, 3 -> 9, 2 -> 10, 0 -> 12, {5, 6} -> 7, {9, 12} -> 2. Exact integer-sum agreement of `display_class_hist` and `road_type_hist` at L0 (e.g. class 7 = 3,421,274 = 3,046,886 + 374,388) and consistent pairings at L2-L8. | verified | `parser/refdata/profile/map.json` (`display_class_hist`, `road_type_hist`, levels 0 and 2-8). Derived in `docs/design/osm-vocabulary-mapping.md`. No test asserts the function; the census does. | `parser/refdata/vocab/display_class.json` |
| Display class values on R | L0: {0, 2, 3, 4, 7, 9, 10, 12}. L2: {0, 4, 9, 10, 12}. L4-L8: {0, 4, 10, 12}. L10, L12: no road links. | verified | `map.json`; coverage test `parser/tests/test_vocab.py::test_coverage_against_reference_census` and harness check `parser/harness/checks/vocab.py`. | `parser/refdata/vocab/display_class.json` |
| Display class order vs spec ch.32.1 | R's class values are not the spec's overseas labels (spec 12 = walkway, R 12 = type 0 = freeway; spec 3 = freeway, R 3 = type 8). The ordering is not a prominence rank, as `docs/design/osm-vocabulary-mapping.md` observed. | observed | Compare `map.json` pairing above with spec ch.32.1. Meaning of R's class values comes from metadata not read here. | `parser/refdata/vocab/display_class.json` |
| Levels 10 and 12 | No road links on R. | verified | `map.json` `link_count` 0 at levels 10 and 12; `parser/tests/test_selection.py::test_level_10_and_12_have_no_road_links_in_reference_profile`. | `parser/refdata/selection.json`, `parser/kiwiw/selection.py` |

### OSM-to-code tables (build inputs, not format)

The checked-in tables are data the writer builds from and are not part of the disc format;
they are listed for provenance. Format: `parser/kiwiw/vocab.py` docstring.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| `road_type.json` ranges [0,0], [2,8], [10,12] | L0: motorway 0, trunk 10, primary 7, secondary 8, tertiary 3, unclassified/road 5, residential/living_street 6, service/busway 9, track 2. L2-L8: motorway 0, trunk 10, primary 7, everything else 2. L10/L12: none. | assumed | Derived by rarity ranking (`docs/design/osm-vocabulary-mapping.md`); the spec labels above contradict trunk -> 10 and suggest primary/secondary -> 2 and 3. Parity design F4 targets: trunk/primary -> 2 (class 10), secondary/tertiary -> 2 or 3 by level, residential -> 6, track -> 9, motorway 0. Only the value-set membership is tested (`parser/tests/test_vocab.py`). | `parser/kiwiw/vocab.py` |
| `selection.json` road admission | Highways admitted per level: L0 all 17 classes; L2 motorway, trunk, primary; L4 motorway, trunk; L6, L8 motorway; L10, L12 none. Minimum length metres 0/0/50/100/200/500/1000 for L0-L12. | assumed | Calibrated for count envelopes (`parser/kiwiw/selection.py` docstring). `parser/tests/test_selection.py` checks table consistency, not R parity. Parity design F4 says L2-L8 selection is to be rebuilt with type 2 as the backbone. | `parser/kiwiw/selection.py` |

## Open questions

1. Node attribute bits 15, 14:13, 12, 11, 10: code names (oneway, planned, tunnel, bridge,
   undecoded) conflict with the spec (validity, one-way code, planned, tunnel, bridge).
   The R sample (Melbourne, 2,147 nodes) matches the spec (bits 14:13 populated, bit 10
   populated on 45 nodes, bit 11 and 12 zero). Needs a disc-wide census of all five bits
   and a named-bridge/one-way-street spot check before renaming `RoadNode` fields. The F9
   claim that one-way is absent from the map layer rests on bit 15 only.
2. Whether R's road-type labels follow ch.32.2 (overseas column) literally. Census
   pairings fit for 0 (freeway), 2 (arterial), 10 (ferry, rarest) but 7 and 8 at coarse
   levels look like arterials. A name-matched study (parity design F4) is the decider.
3. Meaning of R's display class values (metadata, not read here); function of road type is
   verified, the label is not.
4. What determines `selected_link_flag` (47% at L0, 100% at L2, 0% at L4-L8) and
   `link_id_flag` (spec meaning: differentials omitted; holds on a 12-link sample only).
5. Header sections missing from G (address header, connection records, additional-node,
   link ids): does the head unit tolerate their absence? Shape-size word 0 in G likewise.
   Answerable only in-vehicle; the offline oracle is structural comparison against R.
6. Additional-data blocks (m = 6 on the sampled parcel), route number, passage regulation,
   altitude: content unknown or never present.
7. Coordinate range per level and parcel class (owned by `map-frame.md`; design F1).
8. Header size (offset 0) and display-scale word (offset 0 of each class section): R value
   distributions not censused.
9. Reconcile `RoadLink.link_id` semantics between the design doc (positional index) and
   `parser/kiwiw/link_id_registry.py` (arbitrary minted id); neither is the on-disc
   absolute link ID.
