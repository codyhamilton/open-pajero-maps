# Route guidance and route planning

Covers spec ch.8 (Route Guidance), ch.9 (Region Data Management) and ch.10 (Region /
Route Planning data), including the ext frames 0xAF100100 and 0xAF100300. All multi-byte
values are big-endian. "D" (offset) and "SWS" (size) fields are stored halved (real = stored
x 2); `0xFFFFFFFF` / `0xFFFF` means "no entity". Geo values are in 1/8 arc-second units.
Nesting: ch.9 region tree (root, level 8, 6, 4, 2) whose leaf-or-inner region records point
to one RP frame each; an RP frame holds 9 basic + 6 ext management entries pointing to
sub-frames. Ch.8 route guidance is not modelled at all by the code (map frame rg fields are
emitted absent; see `map-frame.md`, `parcel-management.md`). Status counts here rest on
R measurements made with ad hoc read-only scripts, not repo checks, so no row is `verified`:
the tests in `parser/tests/test_route_planning.py`, `test_boundary_links.py` and
`test_contraction.py` are writer-to-decoder round trips on synthetic data only.

## Ch.9 region data management header (50 B fixed + level records)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| header_size | 130 on R = 50 + 16 x 5 levels | observed | R: header_size 130, 5 levels (root -32, 8, 6, 4, 2) | `parser/kiwiw/route_planning.py` |
| rmt_file, ctc_file, ctc_dsa, ctc_size | Empty / 0 on R | observed | R: rmt_file and ctc_file empty, ctc_dsa = ctc_size = 0 | `parser/kiwiw/route_planning.py` |
| Level management record (16 B) | Per level: n_basic 9, n_ext 6, node rec 6, link rec 6, link cost rec 14, regulation rec 2, between-links cost rec 4, region rec 24 | observed | R: every non-root LMR has these values | `parser/kiwiw/route_planning_writer.py` |
| Level numbering | Root -32 (dummy, 1 region), 8 (1357), 6 (51), 4 (105), 2 (369) | observed | R census: 1883 region records, all type code 0 | `parser/kiwiw/route_planning.py` |
| Level 2 dummies | 18 of the 369 level-2 records are dummies (first 12 B 0xFF); 351 real | observed | R census; notebook 01 counts 351 real regions, R total incl. dummies is 369 | `parser/kiwiw/route_planning_writer.py` |
| Tree shape | Root parents all 1357 level-8 regions; 1326 level-8 regions are childless, 31 have children (level 6 -> 4 -> 2 by child links); 187 regions have children | observed | R census. `docs/archive/03-osm-pipeline.md` says "every level-8 region has children"; the census wins | `parser/kiwiw/route_planning.py` |

## Ch.9 region management record (24 B)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| type code | 0 = DSA + size in logical sectors of 32 B | observed | R: all 1883 records are type 0 | `parser/kiwiw/route_planning_writer.py` |
| DSA / size | RP frame location and length | observed | R; round-trips synthetic in `parser/tests/test_route_planning.py` | `parser/kiwiw/route_planning.py` |
| child links | Child region indices used to build the tree | observed | R tree census | `parser/kiwiw/route_planning.py` |
| dummy record | First 12 B 0xFF | observed | R level-2 dummies | `parser/kiwiw/route_planning_writer.py` |

## Ch.10 RP frame header and management entries

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| header_size | 110 on R (98 = 8 + 15 x 6 plus 12 B expansion). Writer emits 98 | observed | R: 110 in all sampled regions | `parser/osm_to_route_planning.py` |
| Region number | Equals the RMT index within level | observed | R sample | `parser/kiwiw/route_planning.py` |
| practical_mgmt_code | 0xFF000000 in 106 of 120 sampled regions, 0x12000000 in 14; meaning unknown | unknown | R sample | `parser/kiwiw/route_planning.py` |
| Management entry (6 B x 15) | 4 B D offset + 2 B SWS size, both halved; 9 basic then 6 ext | spec-only | spec ch.10.2; consistent with R sub-frame sizes on samples | `parser/kiwiw/route_planning.py` |
| Basic order | node, link, link_cost, upper_node, upper_link, passage_code, statistical_cost, node_coord, road_ref | observed | R sample; spec ch.10.2 | `parser/kiwiw/route_planning.py` |
| Header expansion (12 B) | 0xFF x 12 in 1326 regions (level 8 without boundary nodes); otherwise four 3 B geo-like values (lat_top, lat_bottom, lon_left, lon_right order) snapped to a grid, not the region bbox | unknown | R sample of 538 non-0xFF regions; semantics not decoded. Writer omits it | `parser/osm_to_route_planning.py` |
| Absent sub-frames | statistical_cost and upper_link always absent; upper_node absent at level 8, present in some level 2/4/6; passage_code present in about half of level 8 | observed | R 120-region sample | `parser/kiwiw/route_planning.py` |
| upper_node (10.8) | Small table with 0xFFFF entries (e.g. 124 B); layout not decoded | unknown | spec ch.10.8; R sample | `parser/kiwiw/route_planning.py` |
| passage_code frame (10.11) | Tiny frames (e.g. 10 B `01010003247e7f000000`); not decoded, spec table not implemented | unknown | spec ch.10.11; R sample | - |

## Node frame header and rank records

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Node frame header | n_nodes, n_links, rank count; 10 B rank records | observed | R: 1 rank per region; sum of link counts equals header n_links in 8 of 8 samples | `parser/kiwiw/route_planning.py` |
| rp_level (rank) | 3 for level 8; mixed 0..3 for level 2 | observed | R sample | `parser/kiwiw/route_planning.py` |
| avg_travel_time (rank flag) | False in all sampled ranks | observed | R 120 regions | `parser/kiwiw/route_planning.py` |

## Node record (6 B)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| link count (4 bits) | Stored value is count - 1 (0..14 -> 1..15). Code treats raw as the count | observed | R: sum(raw+1) equals header n_links exactly in 8 of 8; road ref accounting exact for 17050 of 17050 records (95.4% with raw). Spec ch.10.7 agrees. R and spec win over code | `parser/kiwiw/route_planning.py` |
| link_record_offset (18 bits) | In 2-byte word units (byte offset = value x 2). Code and writers treat it as bytes | observed | R: contiguity verified in 87 of 120 regions (33 failures have bit 30 set, see below). R wins over code | `parser/kiwiw/route_planning.py`, `parser/osm_to_route_planning.py` |
| bit 31 delete flag | Node deleted | observed | 0 in all samples; code ignores | - |
| bit 30 upper-level correspondence table exists | Boundary node has an upper-level table (spec ch.10.7.1.5); not decoded | unknown | Set in the 33 regions failing offset contiguity | - |
| uppermost_identical_level (bits 29..27) | Relative: number of upper levels containing the identical node. 0..3 at level 2, 0..2 at level 4, 0..1 at level 6, 0 at level 8. Writer's `level//2` absolute encoding conflicts; R and spec win | observed | R 120-region sample (171293 nodes) | `parser/kiwiw/route_planning_writer.py` |
| is_aggregated | Node belongs to an aggregated intersection | observed | R: 14650 of 171293 | `parser/kiwiw/route_planning_writer.py` |
| is_boundary | Region boundary node (links are 8 B) | observed | R: 781 of 171293 | `parser/kiwiw/route_planning_writer.py` |
| parcel_boundary, traffic_light, rotary | Flags | observed | R: 0 of 171293 each; writer always writes false | `parser/kiwiw/route_planning_writer.py` |
| is_suburb, is_semi_urban | Flags | unknown | Writer always false; R value not separately recorded | `parser/kiwiw/route_planning_writer.py` |

## Link record (6 B, or 8 B on boundary nodes), regulation and between-links cost records

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Per-node block | Link records, then regulation records (2 B), then between-links cost records (4 B), even padded | observed | R contiguity check, 87 of 120 regions | `parser/kiwiw/route_planning.py` |
| region number (2 B, boundary links) | Neighbour region; 0xFFFF = none | observed | R: 2316 boundary links carry real region numbers | `parser/kiwiw/route_planning.py` |
| adj word bit 15 delete, bit 14 infra-link | Spec-defined, not decoded by code | observed | R: delete and infra 0 in 428951 links | - |
| suburb, semi-urban flags | Link flags | observed | R: 0 in 428951 links | `parser/kiwiw/route_planning_writer.py` |
| reverse flag | Link in reverse direction | observed | R: 214379 of 428951 | `parser/kiwiw/route_planning.py` |
| following_same_road | 0xF = none | observed | R: none in 426778 of 428951 | `parser/kiwiw/route_planning.py` |
| link_id_origin | RP link id; writer values are synthetic. Agreement with main-map link id unresolved | unknown | WP2 open item, no evidence either way | `parser/osm_to_route_planning.py` |
| Regulation record (2 B) | exit_link_no + passage_code, between-links bit | observed | R: 236327 records, 232083 with between-links bit set. Writer emits `is_between_links` False and no between-links cost | `parser/kiwiw/route_planning_writer.py` |
| Passage code values | 127 (231996), 1 (4186), 2 (88) on R; spec table (ch.10.11) not decoded | unknown | R census | - |
| Between-links cost record (4 B) | Turn cost between two links | observed | R: 32726, all with aggregated-intersection flag set | `parser/kiwiw/route_planning_writer.py` |
| Turn restrictions from OSM | Mapping to regulation records | unknown | Only 1 of 57372 relations resolved in region 178; via-way skipped; cause undiagnosed (WP2 open item) | `parser/build_route_graph.py` |

## Link cost table

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Header (6 B) | SWS size, n_with_time, n_without_time | observed | R: n_with_time 0 in 120 regions, sizes fit 6 + 14n exactly | `parser/kiwiw/route_planning.py` |
| Record without time word | 14 B. Spec lists 16 B with average travel time; R wins | observed | R 120 regions | `parser/kiwiw/route_planning_writer.py` |
| Record with time word | 16 B | spec-only | spec ch.10.6; not seen on R | `parser/kiwiw/route_planning_writer.py` |
| Cost field semantics (class, length, toll etc.) | Fields as decoded | unknown | Not checked against R by any test | `parser/kiwiw/route_planning.py` |

## Node coordinates

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Header (18 B) | Sample `0009 025800 038400 03 03 0009 000c 0015 0c34` | observed | R sample | `parser/kiwiw/route_planning.py` |
| Reference grid counts | Ref-grid table size does not equal the simple product of the two counts | unknown | R: 24 B with counts 3,3 | `parser/kiwiw/route_planning_writer.py` |
| Coordinate record (4 B) | grid record number 8 bits, X 12 bits, Y 12 bits | spec-only | spec ch.10.9 | `parser/kiwiw/route_planning_writer.py` |

## Road reference table (ch.10.13)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Count | u16 record count, then variable-length aggregated node records | observed | R: nibble-array size accounting exact for 17050 of 17050 records (150 regions) using count = raw + 1 | `parser/kiwiw/route_planning.py` |
| Aggregated clustering | How OSM nodes are clustered into aggregated intersections | assumed | Heuristic in `parser/build_route_graph.py`; no R comparison | `parser/build_route_graph.py` |

## Ext frames (each: 12 B MID, 4 B data id, payload)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| MID | DISC_STAMP_12B `0f6788003c47220003000722` | observed | `docs/archive/01-format-analysis.md` ext-frame census (1864 regions) | `parser/kiwiw/route_planning_writer.py` |
| Populated slots | Every region has 2 or 3 populated slots (487 with 2, 1377 with 3) | observed | notebook 01 census; corrects its earlier "1 to 2" | - |
| 0xAF100100 (slot 0) | All regions, variable length, 62.1% of ext bytes, word-structured with 0x7FFF sentinel | unknown | `parser/analyze_ext_frames.py` census. Writer emits data id 0 and empty payload, which does not match R | `parser/kiwiw/route_planning_writer.py` |
| 0xAF100200 (slot 1) | Level 6 only (51 of 51), fixed 106 B | unknown | census | - |
| 0xAF100300 (slot 2) | Level 8 only, in 1326 of 1357, exactly where region has no boundary nodes. 4 B header (0x0002, count) + count x 12 B: u32 id (increasing), u16 small, u16 value twice, u16 zero | observed | length 4 + 12 x count in 1326 of 1326; 3165 distinct ids (`parser/analyze_ext_frame_shape.py`). Semantics unknown | - |
| 0xAF100600 (slot 5) | All regions, fixed 4 B `00 02 00 00` | observed | census | - |
| Firmware requirement | Whether firmware needs AF100100 / AF100300 | unknown | Untested; in-vehicle testing is last-mile | - |

## Ch.8 Route guidance

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| RG distribution header | SWS size, PID 8 B, position code, divided/integrated id, practical mgmt code 4 B, base map flag, 6 x n basic + 6 x m ext records | spec-only | spec ch.8.1 | - |
| Sub-frames 8.4 to 8.7 | Guidance data, intersection / road / toward names, spot guidance, direction indicator, road structure, building and facility, caution point, character string, shape and pattern | spec-only | spec ch.8 | - |
| Extended data (8.3) | [MID 12][N 4][data], "not yet fixed" in spec | spec-only | spec ch.8.3 | - |
| Map frame rg_addr / rg_size | Emitted absent (0xFFFFFFFF, 0) | assumed | `docs/archive/02-roundtrip.md`; `map-frame.md` | `parser/kiwiw/synth.py` |
| Parcel `routeoff` | D offset into a route-guidance list | unknown | `parcel-management.md`; R contents not decoded | - |

## Contraction hierarchy levels and boundary links

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Level assignment | Edge-difference priority, lazy update, bounded witness search; DEFAULT_LEVEL_FRACTIONS (0.55, 0.25, 0.13, 0.07) | assumed | Heuristic, not a measured disc statistic. Shortest-path preservation tested synthetically only in `parser/tests/test_contraction.py` | `parser/kiwiw/contraction.py` |
| Boundary links | 8 B link records with neighbour region | observed | R: 2316 boundary links; synthetic round trip `parser/tests/test_boundary_links.py` | `parser/kiwiw/route_planning_writer.py` |
| >14 links per node ("undecided" case) | Writer raises NotImplementedError | unknown | Not exercised | `parser/kiwiw/route_planning_writer.py` |

## Open questions

- Semantics of ext AF100100, AF100200, AF100300, and whether the firmware needs them.
- The 12 B RP header expansion and practical_mgmt_code values.
- Bit 30 upper-level correspondence tables, upper_node (10.8), passage_code (10.11).
- Node-coordinate reference grid count semantics.
- Whether RP link ids must equal main-map link ids.
- Turn restriction mapping from OSM to regulation and between-links records.
- Ch.8 route guidance frames and the parcel `routeoff` field.
- Fixing decoder/writer conventions (link count raw + 1, offset in 2-byte units, relative uppermost level) is a code change and not yet done.
