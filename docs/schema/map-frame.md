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
| 0, u16 word 0, Header Size (SWS) | word0*2 = 36 + 4*nregion + 6*n_mfde_entries, which is also the first in-buffer data-slot offset. Held-out 988,865/988,865 (1.0), zero disagreements anywhere on R. Correction: the plan-01 claim that word 0 equals buffer size is wrong, and `synth.py` writing total_size//2 is wrong. The earlier "897 of 939 L6 leaves" figure compared against a fixed 20-entry table: the 42 leaves that differ are exactly the L6 nregion=1 leaves with n_entries 21, 22 or 23 (19 + 15 + 8), and each borders a divided parcel (a divided neighbour needs one extra adjacency entry per sub-parcel), so the exceptions are content-independent | observed | `parser/refdata/profile/coord_scale.json` `header.words.0` and `header.word0_exceptions` (`the_42`); spec ch.7.1.1 | `parser/kiwiw/synth.py` |
| 2, 8 bytes, PID | Parcel id: 3-byte geonum lat (1/8 arc-second, bit 23 = negative), exp byte, 3-byte geonum lon, exp byte | observed | Lat/lon decode consistent with placement; exp bytes not decoded and written as 0 | `parser/kiwiw/parcel.py` |
| 10, u8 cy | llcode row: grid cell y of the parcel | observed | Non-zero for most L2-L8 parcels (e.g. L2 217,473 of 231,564 have both cy and cx non-zero) | `parser/kiwiw/parcel.py` |
| 11, u8 cx | llcode column: grid cell x of the parcel | observed | As above | `parser/kiwiw/parcel.py` |
| 12, u16 dipid (header word 6) | Divided/integrated parcel id; bit layout in the dipid table. Rule fits R at held-out accuracy 1.0 (per-(level, class, division) constant) | observed | See dipid table; `parser/refdata/profile/coord_scale.json` `header.words.6` | `parser/kiwiw/synth.py` |
| 14, u16 + u16 pmcode (header words 7 and 8) | Word 7 is the Area Number in the high byte, low byte 0: 0x1200 (Area Number 18) iff road data exists at L0 (for L2, iff any L0 descendant parcel has a road sub-frame), else 0xFF00 (255); L4 and above are always 0xFF00. Word 8 is 0. Accuracy on R: L0 3,704,843/3,704,871, L2 231,564/231,564, L4-L12 15,538/15,538; held-out 988,860/988,865 (0.999995). Residual tolerance, not an exemption: 28 L0 parcels with a single road link are stored 0xFF00 where the rule says 0x1200. Generator consequence (Phase 4): L2 headers depend on their L0 children, so the generator needs an L2 post-pass. The meaning of Area Number 18 in the metafile is unknown (see `UNKNOWNS.md`); the rule is descriptive of R. Supersedes the earlier "blocked" status and the plan-01 constant-zero claim | observed | `parser/refdata/profile/coord_scale.json` `header.words.7` (`residual_tolerance`, `phase4_scope`, `area_18_meaning`); `docs/plans/03-map-layer-parity-remediation/WORD7-ANALYSIS.md` (Result, Adoption) | `parser/kiwiw/synth.py` |
| Area Number 18 meaning | What Area Number 18 (word 7 = 0x1200) refers to. It names a metafile area entry; the metafile is neither on the disc nor in the archived spec. First test: locate a metafile source (head-unit firmware or a spec revision that defines it) and check that entry 18 relates to road-bearing L0 areas. Until then the pmcode rule is descriptive of R only | unknown | `docs/plans/03-map-layer-parity-remediation/WORD7-ANALYSIS.md`; `parser/refdata/profile/coord_scale.json` `header.words.7.area_18_meaning` | `parser/kiwiw/synth.py` |
| 18, u16 dsflag (header word 9) | Display/scale flag; 0x0064 in every parcel on R (held-out accuracy 1.0); G writes the same constant | observed | `parser/refdata/profile/coord_scale.json` `header.words.9` | `parser/kiwiw/synth.py` |
| 20, u16 rlx (header word 10) | Relative X of the parcel origin; bit 15 is 0 at L0-L8 and 1 at L10, L12. Content-independent: an exact table keyed (level, lat_lo, lat_span, lon_span), 2,921 fit keys, held-out 0.999977 (misses are unseen keys). The closed-form WGS84 model scores only 0.972924 and is evidence only | observed | `parser/refdata/profile/coord_scale.json` `header.words.10` | `parser/kiwiw/synth.py` |
| 22, u16 rly (header word 11) | Relative Y; same table rule as rlx, held-out 0.999988 | observed | `parser/refdata/profile/coord_scale.json` `header.words.11` | `parser/kiwiw/synth.py` |
| 24, u16 geomagnetic 1 | Geomagnetic word; 0 everywhere sampled | observed | Census on R sample; spec ch.7.1.1 | `parser/kiwiw/parcel.py` |
| 26, u16 geomagnetic 2 | As above | observed | Census on R sample | `parser/kiwiw/parcel.py` |
| 28, u32 rg_addr | Route-guidance frame address; L2-L12 always 0xFFFFFFFF. At L0 37,180 of 37,500 are absent, 320 (about 0.85%) real. Conflict: plan-01 says 7/7 cities real at L0; that was a small sample of cities, the census wins | observed | Census on R sample; see `route-planning.md` | `parser/kiwiw/parcel.py` |
| 32, u16 rg_size (header word 16) | Route-guidance frame size (SWS); 0 when absent, nonzero on real L0 route-guidance parcels. Not modelled by 2-02 and not on the DESIGN header-word exemption list: the orchestrator must either add it to the list or Phase 4 must model it | observed | Census on R sample; plan 03 Phase 2 gate record (`IMPLEMENTATION.md`) | `parser/kiwiw/parcel.py` |
| 34, u16 nregion | Count of region-list entries: 0 or 1 per level; L0 histogram {0: 65536, 1: 3639335}; 1 at L0-L8, 0 at L10 and L12 (dominant) | verified | `parser/refdata/profile/map.json` nregion_hist; `parser/harness/checks/mfde.py` | `parser/kiwiw/synth.py` |
| 26-30 and 34, words 13, 14, 15 and 17: n_intersections, route_planning_level, n_additional_data, nregion | WP2-owned words that may differ from the model in Phase 4. R census over 3,951,973 parcels: n_intersections is 0 everywhere; n_additional_data is 65,535 on 3,931,302 parcels (2,901 distinct values); route_planning_level is 65,535 on 3,931,302 (479 distinct); nregion 0: 69,915, 1: 3,882,058; ext-frame slots (mfde index 3 up) counted per level | observed | `parser/refdata/profile/coord_scale.json` `header.wp2_exempt` | `parser/kiwiw/synth.py` |

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
4096 units, an integrated parcel up to 8x (32768). The full-disc census
(`parser/refdata/profile/coord_scale.json`, `ranges`, `class_rule`) settles the class ranges
below. The class is content-independent: class = f(level, division, grid) only.

This section states the grounded Phase 2 gate criteria (DESIGN Decisions, "Amendment
2026-09-23 (user) — grounded phase gates", criteria 2 and 4 restated by "Amendment
2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot") as
measured by the committed, re-run tools. **Phase 2 is CLOSED** (`GATE-2.md`, 2-15): all
five criteria pass, three at zero violations (1, 3) or a residual explained record by
record (5), and criteria 2 and 4 pass under the corrected frame-adjacency model — the
coordinate frame is an n x n block of leaf slots on one global raw lattice
(`X = gx0*4096 + x_local`, one physical raw unit at every level), not a per-leaf-slot
comparison. The decisive fix was L0_sparse's boundary mirror: 8,652 of 11,536 (75%)
violations under the old leaf-slot adjacency (2-12) down to 0 of 721 under frame
adjacency (2-13/2-14, reconfirmed 2-15).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Class rule | division != 0 is divided; else level != 0 is full; at L0, urban if the leaf's 4x4 tile is in `urban_tiles`, else sparse. Leaf index i in a block: x = i % 32, y = i // 32, tile = (y // 4, x // 4) | observed | `coord_scale.json` `class_rule` (L0 rule accuracy 1.0 on 222,192 parcels, 2-06 fixer record) | `parser/tools/coord_scale_census.py` |
| L2-L10 full, L0 urban | Class range 4096; peak 4096 in every class. Share of parcels at the maximum: L2 0.992647 (n 214,890), L4 0.992342 (13,973), L6 1.0 (911), L8 1.0 (58), L0 urban 0.998999 (3,995) | observed | `coord_scale.json` `ranges` | `parser/kiwiw/coordconv.py` |
| L12 full | Class range 4096, observed peak 3072 (n = 1) | observed | `coord_scale.json` `ranges` (12, full, normal) | `parser/kiwiw/coordconv.py` |
| L0 sparse | Class range 16384 (n 218,197; peak 16384; share at max 0.994624). The frame these coordinates are expressed in is the 4x4 integrated-parcel tile (16384 = 4 x 4096), not the leaf: every one of the 16 leaf slots in a tile is given the tile's bounds. Confirmed as a global-raw-lattice frame, not an independent scale constant, by criterion 4's `L0_urban <-> L0_sparse` cross-class crossing (113 matched, 1 violation, 2-15) | verified | `coord_scale.json` `ranges`; `parser/harness/walk.py` `frame_bounds`/`frame_range`/`frame_class` (2f874e3); `EVIDENCE-2-08.json` `l0_sparse_frame_check` (12 of 12 sparse cells are tile-class); `EVIDENCE-2-15.json` `criterion_4_mirror.classes.L0_sparse` (721/721/0) | `parser/harness/walk.py` |
| Divided sub-parcels (pardiv1) | Sub-parcel 0 range 2048; sub-parcels 1, 2, 3 range 4096, at every level L0-L8. Coordinates are absolute in the parent leaf's frame at 4096, not renormalised per sub-parcel | observed | `coord_scale.json` `ranges` (e.g. L0 n 13, peaks 2048/4096/4096/4096) | `parser/kiwiw/divide.py` |
| y orientation | y increases northward (y-up) in the raw coordinate frame: y = 0 is the south edge of the parcel frame. Pooled 12 cells x 7 classes: the y-up model beats y-down (cells passing: L0 sparse 3 vs 0, L0 urban 5 vs 0, L2 1 vs 0, L4 4 vs 0, L6 2 vs 0, L8 2 vs 0, divided 0 vs 0) | observed | `EVIDENCE-2-08.json` `pooled_classes.*.model` vs `model_y_down`; `parser/kiwiw/coordconv.py` (fixed 39c9c2f) | `parser/kiwiw/coordconv.py` |
| **Criterion 1 — coordinate max vs class range** | No parcel coordinate exceeds its class range. `exceeds_max` (a different count from `exceptions`, which is a non-max observed peak, not a violation) is 0 in every one of 28 (level, class, division) classes, over the full-disc denominator of 452,199 content-bearing parcels. Re-run 2026-09-23 against R (2-15, post 2-13's `frame_bounds` fix): `ranges` and `class_rule` structurally identical to the committed profile, `exceeds_max` unmoved. **PASS** | verified | `coord_scale.json` `ranges` (28 classes, `exceeds_max`); `EVIDENCE-2-15.json` `criterion_1` | `parser/tools/coord_scale_census.py` |
| **Criterion 2 — cross-parcel continuity** | Restated (design-agent amendment): a road link crossing a **frame** boundary is stored independently on both sides; the two copies of the shared endpoint occupy the same point on the level's global raw lattice. Per matched pair; denominator all boundary endpoint pairs at a shared frame edge, the adjacency unit being the frame, not the leaf slot; pairing is **exact lattice equality**, zero tolerance (`EDGE_TOL_RAW`/`PAIR_TOL_RAW` retired). Re-run 2026-09-23 (`EVIDENCE-2-15.json`, sha `da70cd59...`): L0_urban 473/470/3 pass with residual, L0_sparse 686/686/0 pass, L2 547/547/0 pass, L4 416/416/0 pass, L6 379/379/0 pass, L8 33/33/0 pass, divided_pardiv1 983/979/4 pass with residual. 7 total residuals, every one enumerated and individually traced (duplicate-node collisions, a genuine offset, dead-end-at-midline sibling lookups — none a coordinate-model disagreement), well under `RESIDUAL_ENUM_CAP` (400 committed; DESIGN.md's design-agent amendment cites 200 for the same cap — an unresolved, moot-at-this-scale discrepancy). **PASS WITH RESIDUAL** | verified | `EVIDENCE-2-15.json` `criterion_2_and_3.criterion_2_continuity`; `EVIDENCE-2-14.json` `criterion_2`; DESIGN Decisions, design-agent amendment | `parser/tools/continuity_census.py` |
| **Criterion 3 — divided-parcel quadrant containment** | Spec 7.2.2.1.1.2 (2) and (3): a divided parcel's normalized coordinate uses the original basic-parcel frame with each sub-parcel's relative position set to 0 — the 2x2 sub-parcel model. Every shape point of sub-parcel k (0=SW,1=SE,2=NW,3=NE) must lie inside quadrant k of the parent leaf's 4096 frame (`parent_local` reading). Unaffected by the design-agent amendment. Re-run 2026-09-23: 168 sub-parcels (52 content-bearing), 1,037,716 shape points, 0 violations. **PASS** | verified | `EVIDENCE-2-15.json` `criterion_2_and_3.criterion_3_quadrant`; spec 7.2.2.1.1.2 (2), (3) | `parser/tools/continuity_census.py` |
| **Criterion 4 — boundary-node mirror** | Restated (design-agent amendment): a link end node exactly on a frame edge is answered by an end node at the identical global (X, Y) in a frame sharing that point, at exact integer equality, zero tolerance. A node at a frame corner is satisfied by **any** of the frames sharing that point (spec 7.2.2.1.1.3, "neighbouring parcels", plural). `scale_mismatch` is **no longer an exclusion**: a 4096 frame facing a 16384 frame is an ordinary crossing, in the denominator. Re-run 2026-09-23 (`EVIDENCE-2-15.json`, sha `23854cf5...`): L0_urban 522/521/1 pass with residual (cross-class vs L0_sparse: 113 matched, 1 violation); **L0_sparse 721/721/0 pass** — the decisive fix, down from 8,652 of 11,536 (75%) failing under the retired leaf-slot adjacency (2-12); L2 4065/4061/4 pass with residual (2 corner nodes, both matched under the any-sharing-frame rule); L4 825/825/0 pass; L6 746/746/0 pass; L8 66/66/0 pass. 5 total violations, every one enumerated and traced (L2's 4 are 0-2 raw unit rounding; L0_urban's 1 is a ~51 raw unit offset, measured but not independently traced further). **PASS WITH RESIDUAL** | verified | `EVIDENCE-2-15.json` `criterion_4_mirror`; `EVIDENCE-2-14.json` `criterion_4`; `EVIDENCE-2-12.json` `criterion_4` (prior L0_sparse failure); spec 7.2.2.1.1.3 | `parser/tools/boundary_mirror_census.py` |
| Retired measures (2026-09-22 gate), dispositions | The occupied-fraction "no clustering" clause: retired, not carried — for divided sub-parcels its ceiling is geometric (criterion 3 tests the quadrant model directly), for full-leaf classes it already reaches 1.0 and discriminates nothing, and criterion 2 catches a corner-collapsing decode directly and two-sidedly. `axis_coverage` at 0.75 for divided: retired — 9/16 (8/16 for sub 3) is the geometric ceiling for a correctly decoded sub-quadrant, not a clustering failure; `axis_coverage` stands unchanged for full-leaf classes, which reach 1.0. `clip_exact_share`: retired, not retuned — its premise ("near an edge implies should be exact") is false; the crossing-to-dead-end ratio is a property of road density per level (R carries only motorway/trunk/primary at L6/L8), so no threshold separates a right model from a wrong one. Criterion 4 replaces it with an exact mirror check | observed | DESIGN Decisions, Amendment 2026-09-23, Phase 2 criteria 3 and 4, and the paragraph after criterion 4 | — |
| G COORD_RANGE = 1<<15 | G scale constant; docstring says not spec-confirmed. R's class ranges are 4096/16384/2048, never 32768. Replaced in Phase 3 | assumed | `coord_scale.json` `ranges`; `parser/kiwiw/coordconv.py` | `parser/kiwiw/coordconv.py` |

## Open questions

- Bit 13 of dipid: true polarity and meaning (spec and R disagree).
- Exact per-sub-frame maximum: 131,070 or 131,068 bytes.
- Header PID exp bytes; tail_raw; slot 4 content; slot 10 residual variant at L0-L4.
- Why 65,536 L0 parcels have nregion 0.
- Whether the entries-20+ census should become a checked-in test (currently ad hoc).
- Sub-frame ordering beyond slots 0-2 on R.
