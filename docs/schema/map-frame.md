# Map Frame

The Map Frame is the binary of one map parcel (spec ch.7). It holds a 36-byte header,
a region list (4 bytes x nregion), the mfde sub-frame directory (6-byte entries), then
the sub-frames themselves. Everything is big-endian. Offsets and sizes in the mfde
directory are stored halved (SWS, "sws" words) and decoded by doubling. The parcel
wrapper, placement and BMT live in `parcel-management.md`; the road, background and
name sub-frames are in `map-road.md`, `map-background.md` and `map-name.md`; region
data and route-planning frames are in `route-planning.md`. Flags are in `flags.md`.

Census basis for "observed" rows below: a read-only sample of R (37,500 L0 leaves,
every 40th of the first 1.5M; all L2 231,564, L4 14,511, L6 939, L8 78, L10 9, L12 1),
plus the census `parser/refdata/profile/map.json`.

## Frame layout

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Header, 36 bytes | Fixed header at frame offset 0 | verified | `parser/tests/test_synth_map_frame.py`; spec ch.7.1.1 | `parser/kiwiw/parcel.py` |
| Region list, 4 x nregion bytes | Follows the header | verified | `parser/harness/checks/mfde.py`; `parser/refdata/profile/map.json` nregion_hist | `parser/kiwiw/parcel.py` |
| mfde table, 6 x n_entries bytes | Sub-frame directory | verified | `parser/tests/test_synth_map_frame.py`; `parser/harness/checks/mfde.py` | `parser/kiwiw/parcel.py` |
| Sub-frames | Placed after the table; must be even length | observed | Even offsets and sizes follow from halved encoding; placement order beyond slot 0-2 not established | `parser/kiwiw/synth.py` |
| tail_raw | 6-16 bytes after the last sub-frame; meaning unknown, carried verbatim | unknown | Seen on R parcels; content not decoded | `parser/kiwiw/parcel.py` |
| Byte identity | Parse then write reproduces the frame exactly (needs mounted disc, skips otherwise) | verified | `parser/tests/test_roundtrip_parcel_content.py` | `parser/kiwiw/parcel_writer.py` |

## Header (36 bytes)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0, u16 word 0, Header Size (SWS) | Header size in words, through the end of the mfde table: word0*2 = 36 + 4*nregion + 6*n_entries = first in-buffer slot offset. 100% of the sample (939/939 at L6). Conflict: plan-01 DESIGN s2 and `test_header_fields_per_design` say it equals buffer size; the remediation doc says it equals the first slot in 897 of 939 L6 leaves. Winner: the census, no exceptions. `synth.py` writes total_size//2, which is wrong | observed | Ad hoc census on R (not checked in); spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| 2, 8 bytes, PID | Parcel id: 3-byte geonum lat (1/8 arc-second, bit 23 = negative), exp byte, 3-byte geonum lon, exp byte | observed | Lat/lon decode consistent with placement; exp bytes not decoded and written as 0 | `parser/kiwiw/parcel.py` |
| 10, u8 cy | llcode row: grid cell y of the parcel | observed | Non-zero for most L2-L8 parcels (e.g. L2 217,473 of 231,564 have both cy and cx non-zero) | `parser/kiwiw/parcel.py` |
| 11, u8 cx | llcode column: grid cell x of the parcel | observed | As above | `parser/kiwiw/parcel.py` |
| 12, u16 dipid | Divided/integrated parcel id; bit layout in the dipid table | observed | See dipid table | `parser/kiwiw/synth.py` |
| 14, u16 + u16 pmcode | Parcel management code: word 7 is 0xFF00 (area 255) mostly, or 0x1200 (area 18: L0 3538 of 37,500; L2 33,408 of 231,564); word 8 is 0. Conflict: plan-01 says constant 0x00000000 (49 reads). Winner: the census | observed | Census on R sample; spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| 18, u16 dsflag | Display/scale flag; 0x0064 in 100% of the sample | observed | Census on R sample; G writes the same constant | `parser/kiwiw/synth.py` |
| 20, u16 rlx | Relative X of the parcel origin; bit 15 is 0 at L0-L8 and 1 at L10, L12. Examples: L2 about 336-340, L4 about 1358, L12 35330 | observed | Census on R sample; spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| 22, u16 rly | Relative Y; examples L2 225, L4 about 900, L12 35082 | observed | Census on R sample | `parser/kiwiw/synth.py` |
| 24, u16 geomagnetic 1 | Geomagnetic word; 0 everywhere sampled | observed | Census on R sample; spec ch.7.1.1 | `parser/kiwiw/parcel.py` |
| 26, u16 geomagnetic 2 | As above | observed | Census on R sample | `parser/kiwiw/parcel.py` |
| 28, u32 rg_addr | Route-guidance frame address; L2-L12 always 0xFFFFFFFF. At L0 37,180 of 37,500 are absent, 320 (about 0.85%) real. Conflict: plan-01 says 7/7 cities real at L0; that was a small sample of cities, the census wins | observed | Census on R sample; see `route-planning.md` | `parser/kiwiw/parcel.py` |
| 32, u16 rg_size | Route-guidance frame size (SWS); 0 when absent | observed | Census on R sample | `parser/kiwiw/parcel.py` |
| 34, u16 nregion | Count of region-list entries: 0 or 1 per level; L0 histogram {0: 65536, 1: 3639335}; 1 at L0-L8, 0 at L10 and L12 (dominant) | verified | `parser/refdata/profile/map.json` nregion_hist; `parser/harness/checks/mfde.py` | `parser/kiwiw/synth.py` |

### dipid bits (header offset 12)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Bits 15:14 = 11 | Undivided parcel (0xE000 at L2-L10, 0xC000 at L12) | observed | Census on R sample | `parser/kiwiw/synth.py` |
| Bits 15:14 = 01 | Divided parcel, type 1 (2x2); value 0x6100 plus low byte 0x00/0x01/0x10/0x11 giving sub-parcel position (L2-L8) | observed | Census on R sample; `parser/refdata/profile/map.json` parcel_count_by_type | `parser/kiwiw/divide.py` |
| Bits 15:14 = 10 | Integrated parcel: 0xA033 (size nibbles 3,3 = 4x4 basic parcels); about 99.9% of L0 stride sample, 49 of 37,500 are 0xE000. Resolves plan-01 unexplained "10" code | observed | Census on R sample; spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| Bit 13 | Observed 1 whenever the table has adjacent entries 12-19, 0 at L12 (no adjacency). Conflict: spec says 0 = information contained, 1 = none, opposite polarity. Winner: R observation; polarity meaning stays unresolved | unknown | Census on R sample; spec ch.7.1.1 note 13 | `parser/kiwiw/synth.py` |
| G divided leaves | G does not write dipid on divided leaves (stale "until unit 13" comment) | observed | `parser/kiwiw/synth.py` | `parser/kiwiw/synth.py` |

## Region list

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Entry, u32 = (level << 10, region) | One entry per region; e.g. 0x08000000 for RP level 2, 0x10, 0x18, 0x20 for levels 4, 6, 8 | observed | `parser/refdata/profile/map.json` region_list_hex_hist | `parser/kiwiw/parcel.py` |
| nregion = 0 minority | 65,536 L0 parcels have no region list; reason not determined | unknown | `parser/refdata/profile/map.json` nregion_hist | `parser/kiwiw/synth.py` |

Region semantics and the RP frames they point at: `route-planning.md`.

## mfde entry format

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| u32 D | Frame-relative offset, stored halved, decoded by doubling; spec field is u32 | verified | `parser/tests/test_synth_map_frame.py`; `parser/tests/test_roundtrip_parcel_content.py` | `parser/kiwiw/parcel.py` |
| u16 SWS | Sub-frame size, stored halved | verified | `parser/tests/test_synth_map_frame.py` | `parser/kiwiw/parcel.py` |
| Absent entry (0xFFFFFFFF, 0) | Not-present sentinel; 0xFFFF is not doubled by `sws()` | verified | `parser/tests/test_synth_map_frame.py`; `parser/refdata/profile/map.json` absent | `parser/kiwiw/synth.py` |
| Table length | Self-describing: (word0*2 - 36 - 4*nregion) / 6. The code instead uses the lowest in-buffer offset among slots 0-2 | observed | Census on R sample (word 0 rule); `parser/kiwiw/parcel.py` | `parser/kiwiw/parcel.py` |
| Entry count | 20 at L0-L10 (dominant), 12 at L12; long tail of 21-35 entries explained by divided-neighbour entries | verified | `parser/harness/checks/mfde.py`; `parser/tests/test_harness_mfde.py`; `parser/refdata/profile/map.json` entry_count_hist | `parser/kiwiw/synth.py` |

## Directory slots

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Slot 0 | Road sub-frame (basic) | verified | `parser/harness/checks/mfde.py`; spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| Slot 1 | Background sub-frame (basic); always in_buffer at every level | verified | `parser/tests/test_build_alldata.py`; `parser/refdata/profile/map.json` per_entry_index_class_hist | `parser/kiwiw/synth.py` |
| Slot 2 | Name sub-frame (basic) | verified | `parser/harness/checks/mfde.py`; spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| Slots 3-11 | Nine extended slots (n_ext_map = 9 in grid.json) | observed | `parser/refdata/grid.json`; `parser/refdata/profile/map.json` | `parser/kiwiw/synth.py` |
| Slots 3, 5-9, 11 | Absent in 100% of R parcels | observed | `parser/refdata/profile/map.json` per_entry_index_class_hist | `parser/kiwiw/synth.py` |
| Slot 4 | In buffer only at L0 (1,689 of 3,704,871 L0 parcels); content not decoded | unknown | `parser/refdata/profile/map.json` | `parser/kiwiw/parcel.py` |
| Slot 10 | At L6-L12 byte-identical duplicate of the name frame when a name is present; L0-L4 has a residual variant not decoded | observed | Brief 30 census; `parser/tests/test_synth_map_frame.py` (idx10 duplicate) | `parser/kiwiw/synth.py` |
| Route-planning slots | None in the mfde table. Route guidance is reached via header rg_addr/rg_size, RP via the region list | observed | Per-index class histogram shows no RP slots; see `route-planning.md` | `parser/kiwiw/parcel.py` |
| Slots 12-19 | Adjacent Parcel Address Information, order upper, UR, right, LR, lower, LL, left, UL | observed | Spec ch.7.1.1 note 13; R absent counts at L0: idx12/16 = 6912, idx13/15/17/19 = 15472, idx14/18 = 8576 (pair up as expected) | `parser/kiwiw/synth.py` |
| Slots 12-19 at L12 | No adjacency slots; table has 12 entries | verified | `parser/tests/test_synth_map_frame.py` | `parser/kiwiw/synth.py` |
| Divided-neighbour entry (slots 12-19, size 0, offset not 0xFFFFFFFF) | Layout [u16 D halved][u16 info][u16 size=0]; info bits 15:12 = Y divisions - 1, 11:8 = X divisions - 1, 3:0 = adjacent parcel count - 1. D points sequentially into table positions 20+; n_entries = 20 + sum(count). 100% of 15,537 R leaves at L4-L10 (ad hoc scripts, not checked in). Supersedes plan-01 and brief 21 "pointers at 4-cell stride" reading | observed | `docs/plans/01-eval-harness-and-map-layer.md` | `parser/kiwiw/parcel.py` |
| Entries 20+ | Adjacent-parcel addresses for divided neighbours; at rural L0 neighbours are 4x4 integrated, so their frames are 4 cells away (inference) | assumed | Inference from the census above | `parser/kiwiw/parcel.py` |

## Ext frames

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Ext frame inside Map Frame | In-buffer slot with index >= 3, carried verbatim (ext_frame_raw); G places basic sub-frames first, then ext | verified | `parser/tests/test_synth_map_frame.py`; `parser/tests/test_roundtrip_parcel_content.py` | `parser/kiwiw/parcel.py` |
| Ext frame content | Not decoded here; see `route-planning.md` | unknown | R has ext_in_buffer up to 11,410 bytes at L0 (`parser/refdata/profile/map.json` frame_kind_max_bytes) | `parser/kiwiw/parcel.py` |

## Divided and integrated parcels

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Type 1 | 2x2 division | observed | `parser/refdata/grid.json` n_parcels_lat/lng [0,1,3,0]; only type 1 seen on R (L0 count {0: 3704819, 1: 52}) | `parser/kiwiw/divide.py` |
| Type 2 | 4x4 division; no type-2 leaves on R at L0 | spec-only | `parser/refdata/grid.json`; spec ch.7.1.1 | `parser/kiwiw/divide.py` |
| Type 3 | 1x1 | spec-only | `parser/refdata/grid.json` | `parser/kiwiw/divide.py` |
| Planner | Divides 2x2 first, then 4x4 | assumed | Build convention; G writes type 1/2 only | `parser/kiwiw/divide.py` |
| Integrated | Parcels merged 1x1 up to 8x8 basic parcels (spec); R shows 4x4 at rural L0 | observed | R census; spec ch.7.2 | `parser/kiwiw/synth.py` |

## Size limits

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Per sub-frame | mfde u16 SWS word count caps a sub-frame at 131,070 bytes as coded. 0xFFFF is the sentinel, so the true max may be 131,068. Sources: code ceiling vs sentinel reading; undecided | unknown | `parser/build_alldata.py` (U16_MAPFRAME_BYTE_CEILING); `parser/kiwiw/parcel.py` | `parser/build_alldata.py` |
| Whole frame | No whole-frame cap in the format: R frames reach 136,096 (L0), 129,952 (L2), 146,368 (L4), 158,560 (L6), 151,712 (L8) | verified | `parser/refdata/profile/map.json` mapframe_size | `parser/build_alldata.py` |
| Offset field | u32 D (halved) | spec-only | spec ch.7.1.1 | `parser/kiwiw/parcel.py` |
| Per-kind R maxima | L0: background 25,908, name 24,568, road 106,114, ext_in_buffer 11,410 (other levels in the census) | verified | `parser/refdata/profile/map.json` frame_kind_max_bytes | `parser/build_alldata.py` |

## Coordinates

Spec ch.7.2: a 13-bit coordinate plus 3-bit relative position; a basic parcel spans
4096 units, an integrated parcel up to 8x (32768).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| L2-L10 range | Maximum decoded coordinate 0..4096 (L12: 3072) | observed | R census and the independent 8-point sample in `docs/schema/map-background.md` (coordinate-range row). Sample-level only; the full census is plan 03 Phase 2 | `parser/kiwiw/coordconv.py` |
| L0 urban | 0..4096 | observed | As above | `parser/kiwiw/coordconv.py` |
| L0 rural | 0..16384, explained by 4x4 integrated parcels (4 x 4096) | observed | As above; dipid 0xA033 census | `parser/kiwiw/coordconv.py` |
| Divided sub-parcels | 2048 or 4096 | observed | As above | `parser/kiwiw/divide.py` |
| True full-cell range equals the observed maximum | Whether 4096 (16384 at L0 rural) is the cell's full range, i.e. whether the head unit scales by it. Hypothesis; the spec allows 4096 per basic parcel | unknown | `docs/schema/map-background.md` (same question, same status). Decided by plan 03 Phase 2 | `parser/kiwiw/coordconv.py` |
| G COORD_RANGE = 1<<15 | G scale constant; docstring says not spec-confirmed. Spec supports up to 32768 only for 8x8 integrated | assumed | `parser/kiwiw/coordconv.py` | `parser/kiwiw/coordconv.py` |

## Open questions

- Bit 13 of dipid: true polarity and meaning (spec and R disagree).
- Exact per-sub-frame maximum: 131,070 or 131,068 bytes.
- Header PID exp bytes; tail_raw; slot 4 content; slot 10 residual variant at L0-L4.
- Why 65,536 L0 parcels have nregion 0.
- Whether the entries-20+ census should become a checked-in test (currently ad hoc).
- Sub-frame ordering beyond slots 0-2 on R.
