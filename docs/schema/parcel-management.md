# Parcel management

The Parcel-related Data Management Frame (spec ch.6): the index that maps a
geographic cell at a zoom level to the on-disc Map Frame holding that cell's
content. It is the first record of `ALLDATA.KWI` after the volume header and
Management Header Table (Management Header Table entry 0; see `disc-layout.md`).
Map Frame contents are in `map-frame.md`; sector-address encoding (DSA/BS) is in
`disc-layout.md`.

Nesting, top to bottom:

```
PDMDH (30 B)                        one per disc, coverage box + sizes
 +- LMR x n_lmr (lmr_size each)     one per level (12,10,8,6,4,2,0; descending)
 +- BSMR x n_bsmr (10 B each)       one per block set, grouped by level, ascending block-set number
 +- BMT x (block sets that exist)   one Block Management Table per BSMR with bmt_size > 0
     +- BMR (6 B) x n_blocks        DSA + size of one block's Parcel Management Record
         +- Parcel Management Record (in its own buffer elsewhere in the file)
             +- 4-byte header, then (gn_lat*gn_lng) mapinfo slots (6 B: DSA + size)
                 +- leaf: DSA/size of a Map Frame;  size==0 and DSA!=FFFFFFFF: subrecord (divided parcel)
```

Encodings. All multi-byte integers are big-endian. `SWS`/`D` = stored halved: the
byte value is 2x the stored 16-bit word, except the sentinel 0xFFFF (32-bit
sentinel FFFFFFFF where the field is 4 bytes). Latitude/longitude fields are 3 bytes:
bit 23 = south/west sign, low 23 bits = 1/8 arc-second. "Level" is the zoom-level
number (12 coarsest to 0 finest); it is *not* a state index (see `index-idx.md`).
Sizes in BMR/mapinfo `size` fields are in logical sectors (32 B); see `disc-layout.md`.

Grid hierarchy per level: block set (coarsest) > block > parcel, each an
N-lat x N-lng row-major array. The per-axis product is the level's global cell grid
`nx` (longitude) by `ny` (latitude); a cell is addressed globally as `(ix, iy)`.
Ordering at every tier: latitude is the outer (slow) axis, longitude the inner
(fast) axis, both ascending from the south-west corner of the coverage box
(`flat = lat_index * n_lng + lng_index`).

The reference disc (R) has 7 LMRs, 601 BSMRs, 2307 BMRs (2113 non-empty), and a
PDMDH record of 21072 bytes padded to 21088 (sector multiple).

## PDMDH header (spec ch.6.1)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u16 SWS header size | Size of the PDMDH record proper (R: 21072 B incl. LMR, BSMR, BMT tables) | verified | `parser/tests/test_roundtrip_alldata_header.py` (`test_pdmdh_record_byte_identical`, needs R mounted); `parser/refdata/grid.json` `pdmdh.record_size`=21072; spec ch.6.1 says "size of the distribution header" (30 B by struct layout): code and R agree the field holds the whole record size, the spec wording is ambiguous | `parser/kiwiw/volume.py`, `parser/kiwiw/volume_writer.py` |
| 2..3 u16 (RESERVED) | Reserved per spec | observed | R bytes 2..7 all zero (`parser/refdata/grid.json` `pdmdh.header_gap_hex`); carried verbatim, byte-identical round trip only proves carry | `parser/kiwiw/volume.py` |
| 4..5 u16 File Name Designation | Bit 0 = 1 if parcel management is kept in named files; R 0 (inline BMT/records, no file names) | observed | R bytes 4..5 zero (`parser/refdata/grid.json` `pdmdh.header_gap_hex`); spec ch.6.1 (2). Code treats bytes 2..7 as one undecoded blob | `parser/kiwiw/volume.py` |
| 6..7 u16 (RESERVED) | Reserved per spec | observed | R zero (`parser/refdata/grid.json` `pdmdh.header_gap_hex`) | `parser/kiwiw/volume.py` |
| 8..10 geonum | Latitude of upper edge of coverage: 35.3333 (35 deg 20') | verified | `parser/tests/test_roundtrip_alldata_header.py` byte identity; `parser/refdata/grid.json` `coverage.lat_hi`; `parser/tests/test_mesh.py` locates real coordinates against it | `parser/kiwiw/volume.py`, `parser/kiwiw/bitutils.py` |
| 11..13 geonum | Latitude of lower edge: -50.0 | verified | as above, `coverage.lat_lo`; `parser/tests/test_grid_data.py` | `parser/kiwiw/volume.py` |
| 14..16 geonum | Longitude of left edge: 90.0 E | verified | `parser/tests/test_grid_data.py` (`test_coverage_and_lon_span` asserts 90.0) | `parser/kiwiw/volume.py` |
| 17..19 geonum | Longitude of right edge: -142.0 (i.e. 218 E). Right < left: the box crosses the antimeridian; longitude span = 128 deg | verified | `parser/tests/test_grid_data.py` (asserts -142.0 and span 128.0) | `parser/kiwiw/volume.py`, `parser/kiwiw/grid.py` |
| 20..21 u16 SWS LMR size | Size of one Level Management Record: 170 B on R (40 base + 2 expansion word + 2*(16+32+16)). Spec ch.6.1 (4) says "size is 20 (40 bytes)": that is the base part only; the record grows by the expansion field (ch.6.1.1.1) | verified | `parser/tests/test_roundtrip_alldata_header.py` (`test_lmr_size_is_fully_explained_by_frame_index_tables`) | `parser/kiwiw/volume.py` |
| 22..23 u16 BSMR size | Raw 5 = 10 bytes (spec: "5 (10 bytes)"). Code stores the raw word, not SWS-decoded | verified | `parser/tests/test_roundtrip_alldata_header.py`; `parser/refdata/grid.json` `pdmdh.bsmr_size`=5 | `parser/kiwiw/volume.py` |
| 24..25 u16 BMR size | Raw 3 = 6 bytes per Block Management Record (spec ch.6.1 (6): size of one BMR; the 12-byte file-name part is absent because file designation is off) | verified | `parser/tests/test_roundtrip_alldata_header.py` (2307 BMT entries parsed at 6 B); `parser/refdata/grid.json` `pdmdh.bmr_size`=3 | `parser/kiwiw/volume.py` |
| 26..27 u16 n_lmr | Number of Level Management Records: 7 | verified | `parser/tests/test_roundtrip_alldata_header.py` asserts 7 | `parser/kiwiw/volume.py` |
| 28..29 u16 n_bsmr | Total number of Block Set Management Records: 601 | verified | `parser/tests/test_roundtrip_alldata_header.py` asserts 601 | `parser/kiwiw/volume.py` |
| 30.. LMR array | `n_lmr` records of `lmr_size`, immediately after the header, descending level order (12,10,8,6,4,2,0) | verified | `parser/tests/test_grid_data.py` (`test_levels_present_in_order`); byte-identical round trip | `parser/kiwiw/volume.py` |
| BSMR array | Starts at `30 + n_lmr*lmr_size` = 1220; `n_bsmr*10` bytes | verified | `parser/tests/test_roundtrip_alldata_header.py` (writer places it from the same formula and must match R) | `parser/kiwiw/volume.py`, `parser/kiwiw/alldata_writer.py` |
| BMT array | Starts at 1220 + 6010 = 7230; BMTs packed in BSMR order with no gaps (7230 + 2307*6 = 21072 = record size) | observed | Arithmetic checked on R (BMT offsets 7230, 7236, 7242 ... contiguous); no test asserts contiguity, the writer is round-tripped byte-identical | `parser/kiwiw/volume.py` |
| record_size..total_size | Zero padding to a logical-sector multiple (21072 -> 21088 = 659 sectors) | verified | `parser/tests/test_roundtrip_alldata_header.py` byte identity of the padding | `parser/kiwiw/volume_writer.py` |

## Level Management Record (spec ch.6.1.1)

One per level. 40-byte base part then expansion field. Offsets are within the record.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0..1 bits 15:10 | Level number (12,10,8,6,4,2,0 on R). Spec range -31..+31, -32 null | verified | `parser/tests/test_grid_data.py` (`test_levels_present_in_order`) | `parser/kiwiw/volume.py` |
| 0..1 bits 9:8 | Reserved | assumed | Spec ch.6.1.1 (1) says reserved; write path emits 0 (`parser/kiwiw/volume_writer.py` has no field for it) and R round-trips byte-identical, so it is 0 on R | `parser/kiwiw/volume_writer.py` |
| 0..1 bits 7:4 upper_level | Spec: number of regular parcels integrated on the next-higher level (0=1x1, 1=2x2, 2=4x4 ...). R: 0 at level 12, 2 at all other levels. Code field name `upper_level`. Only level 0 shows 4x4 integrated slots on R (see Integrated parcels); levels 2..10 have value 2 yet no shared slots | observed | R census of 7 LMRs (`parser/refdata/grid.json` `levels[*].upper_level`); shared-slot census below. Meaning unresolved for levels 2..10 | `parser/kiwiw/volume.py` |
| 0..1 bits 3:0 lower_level | Spec: number of regular parcels divided on the next-lower level (0=1, 1=1/4, 2=1/16 ...). R: 2 at levels 12..2, 0 at level 0. Consistent with `nx` growing 4x per level step (1,4,16,64,256,1024,4096) | observed | `parser/refdata/grid.json` `levels[*].lower_level` and `nx`/`ny` ratios | `parser/kiwiw/volume.py` |
| 2..3 bits 15:12 n_basic_map | Basic Main Map Data Frame management records: 3 (road, background, name) at every level | observed | `parser/refdata/grid.json` (3 at all 7 levels); `parser/harness/checks/decode.py` reads it | `parser/kiwiw/volume.py` |
| 2..3 bits 11:8 n_ext_map | Extended Main Map frame records: 9 at every level. The Map Frame mfde table on R is 20 entries, not 3+9 (see `map-frame.md`) | observed | `parser/refdata/grid.json` (9 at all levels); mismatch documented in `parser/kiwiw/parcel.py` `decode_parcel` docstring | `parser/kiwiw/volume.py`, `parser/kiwiw/parcel.py` |
| 2..3 bits 7:4 n_basic_route | Basic Route Guidance frame records: 2 at levels 0 and 2, 0 elsewhere | verified | `parser/tests/test_grid_data.py` (`test_n_basic_route_by_level`: level 0 == 2, level 4 == 0) | `parser/kiwiw/volume.py` |
| 2..3 bits 3:0 n_ext_route | Extended Route Guidance frame records: 0 at every level | observed | `parser/refdata/grid.json` | `parser/kiwiw/volume.py` |
| 4..23 5 x u32 display scale flags | Data-source scale denominators for display-scale selection, FFFFFFFF = unused. Level 12: 40960000, 81920000; 10: 10240000, 20480000; 8: 2560000, 5120000; 6: 640000, 1280000; 4: 160000, 320000; 2: 40000, 80000; 0: 5000, 10000, 20000. Remaining flags FFFFFFFF | observed | `parser/refdata/grid.json` `levels[*].display_flags`; byte identity only proves carry. How the head unit uses them is not tested | `parser/kiwiw/volume.py` |
| 24 u8 n_blocksets_lat | Latitudinal block sets minus 1 (spec: values 1,2,4,8,16) | verified | `parser/tests/test_mesh.py` (real coordinates resolve to correct parcels only if the decomposition is right); `parser/refdata/grid.json` | `parser/kiwiw/volume.py` |
| 25 u8 n_blocksets_lng | Longitudinal block sets minus 1 | verified | `parser/tests/test_mesh.py`; `parser/tests/test_grid_data.py` | `parser/kiwiw/volume.py` |
| 26 u8 n_blocks_lat | Latitudinal blocks per block set minus 1 (spec: 1..256, powers of 2) | verified | `parser/tests/test_mesh.py`; `parser/tests/test_grid_data.py` | `parser/kiwiw/volume.py` |
| 27 u8 n_blocks_lng | Longitudinal blocks per block set minus 1 | verified | `parser/tests/test_mesh.py`; `parser/tests/test_grid_data.py` | `parser/kiwiw/volume.py` |
| 28..29 u8,u8 n_parcels[0] (lat, lng) | Parcels per block minus 1, type 0 (the regular grid) | verified | as above; `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode` recomputes `nx`,`ny` from the disc) | `parser/kiwiw/volume.py` |
| 30..31 n_parcels[1] | Divided-parcel type 1 grid: (1,1) => 2x2 at every level | observed | `parser/refdata/grid.json` (all 7 levels [1,1]); `parser/tests/test_divide.py` builds and re-locates type 1 | `parser/kiwiw/divide.py` |
| 32..33 n_parcels[2] | Divided-parcel type 2 grid: (3,3) => 4x4 at every level | observed | `parser/refdata/grid.json` (all levels [3,3]); no type 2 record exists on R (see Divided parcels) | `parser/kiwiw/divide.py` |
| 34..35 n_parcels[3] | Divided-parcel type 3 grid: (0,0) => 1x1 at every level | observed | `parser/refdata/grid.json`. Spec ch.6.1.1 (18) treats type 3 as a third divided-parcel size; `parser/kiwiw/divide.py` docstring calls type 3 "integration". Spec wins: integration is expressed by shared slots, not a parcel type (ch.6.3.1.1) | `parser/kiwiw/parcel_mgmt.py` |
| 36..37 u16 D bsmr_offset | Byte offset from PDMDH start to this level's first BSMR (value x 2): 1220, 1230, 1310, 1390, 1470, 2110, 4670 for levels 12..0 = previous + 10 * block-set count | observed | Arithmetic on `parser/refdata/grid.json` (each start = previous + 10 * block-set count; last + 2560 = 7230 = BMT start); the writer recomputes it (`parser/kiwiw/alldata_writer.py`), harness compares to R (`parser/harness/checks/container.py`). Reader `locate_parcel` selects BSMRs by level and index, never through this field | `parser/kiwiw/volume.py`, `parser/kiwiw/alldata_writer.py` |
| 38..39 u16 SWS node_record_size | Size of a road node record: 8 bytes at every level (spec: 4 = 8 B, larger if extended) | observed | `parser/refdata/grid.json` (8 at all levels); road decode in `map-road.md` | `parser/kiwiw/volume.py` |
| Derived grid_nx | `(1+nbs_lng)*(1+nbl_lng)*(1+npc_lng[0])`: 1, 4, 16, 64, 256, 1024, 4096 for levels 12..0 | verified | `parser/tests/test_grid_data.py` (`test_level_0_grid_is_4096_square`, `test_level_12_grid_is_1_by_1`, `test_matches_disc_lmr_decode`) | `parser/kiwiw/grid.py`, `parser/kiwiw/volume.py` |
| Derived grid_ny | `(1+nbs_lat)*(1+nbl_lat)*(1+npc_lat[0])`: same values as `nx` on R at every level | verified | `parser/tests/test_grid_data.py` | `parser/kiwiw/grid.py`, `parser/kiwiw/volume.py` |
| Cell size | `lat_span/ny`, `lon_span/nx`; lat span 85.3333, lon span 128 (wrapped). Level 0: 75 x 112.5 arc-seconds | verified | `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode` compares `cell_lat`, `cell_lon` exactly against the disc) | `parser/kiwiw/grid.py`, `parser/kiwiw/mesh.py` |

Per-level block-set / block / parcel dimensions (lat x lng), from
`parser/refdata/grid.json`, checked by `parser/tests/test_grid_data.py` and
`parser/tests/test_mesh.py`:

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Level 12 | block sets 1x1, blocks 1x1, parcels 1x1 => 1x1 cells (whole coverage in one parcel) | verified | `parser/tests/test_grid_data.py` (`test_level_12_grid_is_1_by_1`) | `parser/kiwiw/grid.py` |
| Level 10 | block sets 2x4, blocks 1x1, parcels 2x1 => 4x4 | verified | `parser/refdata/grid.json`; `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode`) | `parser/kiwiw/grid.py` |
| Level 8 | block sets 2x4, blocks 1x1, parcels 8x4 => 16x16 | verified | `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode`) | `parser/kiwiw/grid.py` |
| Level 6 | block sets 2x4, blocks 1x1, parcels 32x16 => 64x64 | verified | `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode`) | `parser/kiwiw/grid.py` |
| Level 4 | block sets 8x8, blocks 1x1, parcels 32x32 => 256x256 | verified | `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode`) | `parser/kiwiw/grid.py` |
| Level 2 | block sets 16x16, blocks 2x2, parcels 32x32 => 1024x1024 | verified | `parser/tests/test_grid_data.py` (`test_matches_disc_lmr_decode`) | `parser/kiwiw/grid.py` |
| Level 0 | block sets 16x16, blocks 4x8, parcels 64x32 => 4096x4096 | verified | `parser/tests/test_grid_data.py` (`test_level_0_grid_is_4096_square`) | `parser/kiwiw/grid.py` |

## Level Management Record expansion field (spec ch.6.1.1.1)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 40..41 bits 15:14 | Reserved | assumed | Spec reserved; R round-trips with the code's zero (`parser/tests/test_roundtrip_alldata_header.py`) | `parser/kiwiw/volume_writer.py` |
| 40..41 bits 13:10 | Number of road display classes minus 1: 16 on R | verified | `parser/tests/test_roundtrip_alldata_header.py` (`test_lmr_size_is_fully_explained_by_frame_index_tables`: 42 + 2*(16+32+16) = 170 fixes the three counts) | `parser/kiwiw/volume.py` |
| 40..41 bits 9:5 | Number of background display classes minus 1: 32 on R | verified | `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 40..41 bits 4:0 | Number of name display classes minus 1: 16 on R | verified | `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 42.. road table (u16 x 16) | Spec: display class codes (ch.32) in road-frame order. R: 15,14,...,0 at every level. Code name `road_frame_table` ("index table") predates the spec reading; spec name wins | observed | `parser/refdata/grid.json`: identical at all 7 levels. Byte identity proves carry only; the mapping from entry to display class is not tested | `parser/kiwiw/volume.py` |
| background table (u16 x 32) | Display class codes for background frames. R: `[11,27,31,29,26,25,27,30,28,24,23,22,21,20,18,17,12,11,19,16,15,14,13,8,7,6,5,4,3,2,1,0]` (11 and 27 each appear twice), identical at all levels | observed | `parser/refdata/grid.json`. Duplicates are unexplained (see Open questions) | `parser/kiwiw/volume.py` |
| name table (u16 x 16) | Display class codes for name frames. R: 15,14,...,0 at every level | observed | `parser/refdata/grid.json` | `parser/kiwiw/volume.py` |
| Adjustment field | Zero pad so record = `lmr_size`. R: none (`raw_tail_hex` empty) | verified | `parser/tests/test_roundtrip_alldata_header.py` (`test_lmr_size_is_fully_explained_by_frame_index_tables`) | `parser/kiwiw/volume.py` |

## Block Set Management Record (spec ch.6.1.2)

10 bytes; one-to-one with a Block Management Table. Ordered descending by level,
ascending block-set number within a level, block sets low latitude to high, and
within a latitude row west to east (`blockset_index = bsy * n_lng + bsx`).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0..1 bits 15:10 | Level number | verified | `parser/tests/test_roundtrip_alldata_header.py`; `parser/refdata/grid.json` `blocksets[*].level` | `parser/kiwiw/volume.py` |
| 0..1 bits 9:8 | Reserved | assumed | Spec reserved; zero on R by byte-identical round trip | `parser/kiwiw/volume_writer.py` |
| 0..1 bits 7:0 | Block set number within the level (0..255) | verified | `parser/tests/test_mesh.py` (block-set selection `bsy*nbs_lng+bsx` must be right to reach real parcels); order checked on R (level descending, index ascending across all 601) | `parser/kiwiw/mesh.py` |
| 2..5 u32 D bmt_offset | Byte offset from PDMDH start to this block set's BMT (x2). FFFF:FFFF (decodes to 2*FFFFFFFF = 8589934590 in code) when the block set has no BMT | verified | `parser/tests/test_roundtrip_alldata_header.py`; `parser/tests/test_mesh.py` reads BMTs through it | `parser/kiwiw/volume.py`, `parser/kiwiw/mesh.py` |
| 6..9 u32 SWS bmt_size | BMT size in bytes (x2); 0 with FFFF:FFFF offset when absent. `bmt_size / (2*bmr_size)` must equal `(1+nbl_lat)*(1+nbl_lng)` | verified | `parser/kiwiw/volume.py` `parse_pdmdh_full` raises on mismatch for all 2307 entries; `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| Block set census | Block sets by level, with a BMT / total: L12 1/1, L10 6/8, L8 6/8, L6 6/8, L4 20/64, L2 63/256, L0 63/256. The block sets without BMT lie outside the populated area | verified | `parser/refdata/grid.json` `blocksets[*].has_bmt`; `parser/tests/test_grid_data.py` loads it; writer takes the list from it (`parser/kiwiw/alldata_writer.py`) | `parser/kiwiw/grid.py`, `parser/kiwiw/alldata_writer.py` |

## Block Management Table and Record (spec ch.6.2)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| BMT layout | Array of `(1+nbl_lat)*(1+nbl_lng)` BMRs, south-west block first, longitude inner (`block_flat = bly*nbl_lng + blx`). Block number = array position | verified | `parser/tests/test_mesh.py`; spec ch.6.2, 6.2.1 | `parser/kiwiw/mesh.py`, `parser/kiwiw/volume.py` |
| BMR 0..3 u32 DSA | Sector address of the block's Parcel Management Record buffer; FFFFFFFF if the block has no data | verified | `parser/tests/test_roundtrip_alldata_header.py`; `parser/harness/checks/decode.py` (every non-empty BMT entry must lie inside the file) | `parser/kiwiw/volume.py` |
| BMR 4..5 u16 BS | Size of the whole block buffer in logical sectors, including any divided-parcel subrecords and trailing slack. 0 if absent. Spec (ch.6.2.1.1 (2)) agrees: size includes division records | verified | `parser/tests/test_roundtrip_alldata_header.py`; `parser/kiwiw/parcel_mgmt.py` tail handling | `parser/kiwiw/volume.py` |
| BMR 6..17 file name | 12-byte file name, present only with the PDMDH file-designation flag | spec-only | Spec ch.6.2.1.1 (3). R has no file names (`bmr_size` = 6 B) | - |
| Empty BMR census | R: 2307 BMRs, 2113 with DSA and size, 194 empty (level 0: 180, level 2: 14; others none) | observed | Read-only census of R (`parse_pdmdh_full`) | `parser/kiwiw/volume.py` |
| Block buffer size on R | Each buffer is larger than its record footprint (root record + subrecords) by slack of ~8-12 KB at level 0/2 (stale mastering space, not read by kiwiread); carried as `tail_raw`. 2107 of 2113 buffers have a non-empty tail | observed | R census; `parser/kiwiw/model.py` `ParcelMgmtRecord` docstring; `parser/kiwiw/parcel_mgmt.py` | `parser/kiwiw/parcel_mgmt.py` |
| BMR DSA monotonic in BMT order | Whether the head unit requires or R shows block DSAs increasing with block index | unknown | `docs/design/map-layer-parity-remediation.md` lists it as an open ordering check | - |

## Parcel Management Record (spec ch.6.3)

Lives in the block buffer addressed by a BMR. A slot's `dsa` for a subrecord is a
D-encoded byte offset (x2) *within the same buffer*.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0..1 bits 15:10 | Reserved | assumed | Spec ch.6.3 (1); `parse_parcel_mgmt_record` extracts only bits 0:9 and R round-trips | `parser/kiwiw/parcel_mgmt.py` |
| 0..1 bits 9:8 parcel_type | Parcels Type Number: 0 for a record referenced from a BMR, 1..3 for a divided-parcel record; selects `n_parcels[pt]` for the slot grid | verified | `parser/tests/test_mesh_divided_locate.py`; `parser/tests/test_divide.py`; R: 2113 root records type 0, 42 subrecords all type 1 | `parser/kiwiw/parcel_mgmt.py`, `parser/kiwiw/mesh.py` |
| 0..1 bits 7:0 list_type | Parcel Management List Type Number (spec: 0..254, 255 null). Selects the slot layout (0: 6-byte slots; spec 1/2: 8-byte slots with a second size; 100: file-name slots). R: 0 in every record | verified | `parser/kiwiw/parcel_mgmt.py` and `parser/kiwiw/mesh.py` reject non-zero; every R record parses (2113 roots + 42 subrecords) | `parser/kiwiw/parcel_mgmt.py` |
| List types 1, 2, 100 | Slot formats with (whole size, basic/road size) or a 12-byte name. Not present on R; parser refuses them | spec-only | Spec ch.6.3.1.1.2 to .4, ch.6.3.2.1.2 to .4 | - |
| 2..3 u16 D | Offset to the Route Guidance Parcel Management List, relative to record start; FFFF when the level has no route guidance list. Code calls it `header_gap_raw` and carries it verbatim | observed | R census: FFFF in 1923 of 2155 records; the remaining 190 are level-0 roots whose value x2 = 4 + 6*2048 = 12292 in 185 cases (the list starts right after the main list) and differs in 5 (unexamined). Spec ch.6.3 item 2 | `parser/kiwiw/parcel_mgmt.py` |
| 4.. mapinfo array | `(1+n_parcels_lat[pt]) * (1+n_parcels_lng[pt])` slots of 6 bytes: DSA(u32) + BS(u16), row-major, south row first, west first (`idx = lpy*gn_lng + lpx`) | verified | `parser/tests/test_mesh.py`; `parser/tests/test_mesh_divided_locate.py`; roundtrip via `parser/kiwiw/parcel_writer.py` | `parser/kiwiw/parcel_mgmt.py`, `parser/kiwiw/mesh.py` |
| Slot: DSA=FFFFFFFF, size=0 | No parcel at this cell | verified | `parser/tests/test_mesh_divided_locate.py`; R: 55296 of 3.76M level-0 slots | `parser/kiwiw/parcel_mgmt.py` |
| Slot: size != 0 | Leaf: DSA/size locate the cell's Map Frame (size in logical sectors) | verified | `parser/tests/test_mesh.py` (Melbourne, Sydney decode real frames) | `parser/kiwiw/parcel_mgmt.py` |
| Slot: size == 0, DSA != FFFFFFFF | Divided parcel: DSA = D-encoded offset (x2) of a nested record in the same buffer | verified | `parser/tests/test_mesh_divided_locate.py`; `parser/tests/test_divide.py` (`test_find_parcel_resolves_divided_subparcel`) | `parser/kiwiw/parcel_mgmt.py` |
| Max depth | Recursion limit 6 in code; spec says divided records must not be divided further (depth 2). R depth: 2 (root + one subrecord level) | observed | R census: 42 subrecords, none nested. Code limit is a guard, not a format value | `parser/kiwiw/parcel_mgmt.py` |

## Route guidance parcel list (spec ch.6.3.2)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Route list placement | Follows the main list in the same buffer at the offset in header bytes 2..3, same slot layout | observed | On R the 185 level-0 records where it can be checked start at offset 12292 = 4 + 2048*6. The list is inside `tail_raw` for the parser (never decoded). See `route-planning.md` | `parser/kiwiw/parcel_mgmt.py` |
| Which levels have one | Spec: present iff `n_basic_route`+`n_ext_route` > 0 (levels 0 and 2 on R). R: level-0 records with a list: 190 of 1836 non-empty; level 2: 0 of 238 despite `n_basic_route`=2 | observed | R census. Unexplained (Open questions) | - |
| Divided route sublists | Placed adjacent to the parent list | spec-only | Spec ch.6.3.2 | - |

## Divided and integrated parcels (spec ch.6.3.1.1)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Divided parcel, type 1 (2x2) | A slot holding a nested record of `(1+n_parcels_lat[1])*(1+n_parcels_lng[1])` = 4 slots; each slot a leaf or FFFFFFFF. Child cell = quarter of the parent cell. R: 42 subrecords (13 at level 0, 4 level 2, 13 level 4, 7 level 6, 5 level 8), all type 1, all 4 leaves present | verified | `parser/tests/test_mesh_divided_locate.py`; `parser/tests/test_divide.py`; `parser/tests/test_mesh.py` (Melbourne resolves into a divided sub-parcel) | `parser/kiwiw/parcel_mgmt.py`, `parser/kiwiw/mesh.py`, `parser/kiwiw/divide.py` |
| Divided parcel, type 2 (4x4) | Same, 16 slots. Not present on R. The writer emits it when a type-1 quadrant is still oversize | assumed | `parser/kiwiw/divide.py` builds it; `parser/tests/test_divide.py` round-trips it through our own reader; spec ch.6.3.1.1 allows it; never seen on R and head-unit acceptance untested | `parser/kiwiw/divide.py` |
| Divided parcel, type 3 (1x1) | LMR field is (0,0) at every level; meaning of a 1x1 division is unclear. Not present on R | unknown | `parser/refdata/grid.json`; conflicting readings recorded under the LMR n_parcels[3] row | - |
| Subrecord placement | On R every subrecord sits contiguously after the root record's `4 + 6*n_slots` bytes, in slot order, 28 bytes each (4 + 4*6); header word 2..3 is FFFF; list_type 0 | observed | R census over all 19 blocks holding subrecords that carry no route list (offsets equal `footprint + 28*k`) | `parser/kiwiw/alldata_writer.py` |
| Divided cell geometry | A divided parent contributes bounds narrowed by `lpx/gn_lng`, `lpy/gn_lat` at depth 2+. At depth 1 the record's own cell is the parent cell (no narrowing) | verified | `parser/tests/test_mesh_divided_locate.py` (bounds asserts); `parser/tests/test_mesh.py` | `parser/kiwiw/mesh.py` |
| Integrated parcels (level 0) | Several adjacent slots of one record carry the same DSA and size (one shared Map Frame). Spec: integrated group must be a rectangle, up to 8x8. R level 0: 231300 frames each shared by exactly 16 slots (aligned 4x4 groups: `ix % 4 == 0`, `iy % 4 == 0`, checked on 19200 groups), plus 4019 unshared slots; total 3704819 leaf slots. No shared slots at levels 2..12 | observed | R census over all 1836 level-0 buffers (group sizes: {16: 231300, 1: 4019}); alignment on the first 150 blocks; spec ch.6.3.1.1 | - |
| Integrated group: size field | Every slot of the group repeats the full DSA and size | observed | Same census (equal `(dsa, size)` pairs in a group; `size` checked on the four most shared frames = 11 sectors) | - |
| Integrated group vs `upper_level` | Level 0 has `upper_level` = 2 (4x4) and groups of 16, matching. Levels 2..10 also have 2 but no groups | unknown | R census above; spec ch.6.1.1 (3) describes the field as regular parcels integrated on the next-higher level, not slots sharing a frame | - |
| Integrated Map Frame bounds | What `llpid`/parcel bounds a shared frame declares (whole 4x4 group or one cell) | unknown | Not examined; see `map-frame.md` | `parser/kiwiw/parcel.py` |
| Writer emission of integration | `build_alldata` gives each slot its own Map Frame; no integrated group is written | observed | `parser/kiwiw/alldata_writer.py` allocates one frame per slot; the schema records what R does, the choice to omit it is not a format fact | `parser/kiwiw/alldata_writer.py` |

## Parcel lookup and iteration order

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Cell index | `ix = clamp(floor((lon - lon_lo wrapped) / cell_lon))`, `iy = clamp(floor((lat - lat_lo)/cell_lat))` over `nx`, `ny`; wrapped longitude delta uses span 128 | verified | `parser/tests/test_mesh.py`; `parser/tests/test_grid_data.py` | `parser/kiwiw/mesh.py` |
| Cell to tiers | `px = ix % npc_lng`, `blx = (ix // npc_lng) % nbl_lng`, `bsx = ix // (npc_lng*nbl_lng)`; the same for latitude. Then `bset_flat = bsy*nbs_lng + bsx`, `block_flat = bly*nbl_lng + blx`, `slot = py*npc_lng + px` | verified | `parser/tests/test_mesh.py` (Perth, Melbourne, Sydney resolve to correct places); 799/800 street-name agreement against an independent index oracle (analysis, not a repo test) | `parser/kiwiw/mesh.py`, `parser/kiwiw/alldata_writer.py` |
| Ordering at all three tiers | Row-major, latitude outer/ascending, longitude inner/ascending, from the south-west corner. Spec ch.6 (block sets, block records, main map parcel list) states it explicitly. `kiwiread.c` `divbsmr()` decomposes with the lat count at every level: a debug helper, disagrees with the spec, spec and mesh code win | verified | `parser/tests/test_mesh.py`; spec ch.6 (0600122e.pdf) sections 6, 6.1.2, 6.2, 6.3.1 | `parser/kiwiw/mesh.py` |
| Parcel-order bug (root cause) | Old `locate_parcel` recomputed the first-level slot from the fractional position within the finest cell (`local_*_frac * gn`), double-counting `n_parcels[0]` already folded into `ix`/`iy`. Bounds stayed right but the wrong slot was read (Perth CBD returned Rockingham names). Fix: depth 1 uses `(px, py)` directly; the fractional form is used only at depth 2+ (divided records). The axis order was never wrong | verified | `parser/tests/test_mesh.py` (Sydney/Parramatta asserts real Sydney names; comment records the corrected Hunter Valley claim) | `parser/kiwiw/mesh.py` |
| Block set order in file | BSMR array: level descending (12,10,...,0), block-set number ascending within a level, all 601 | verified | `parser/tests/test_roundtrip_alldata_header.py`; checked on R | `parser/kiwiw/alldata_writer.py` |
| BMT data placement order | BMTs for block sets are packed contiguously in BSMR order inside the PDMDH record | observed | R offsets 7230, 7236, 7242 ... contiguous | `parser/kiwiw/volume_writer.py` |
| Block buffer placement | Block buffers of one block set are contiguous, each starting where the previous ended, in BMT order (observed on one level-8 region, 6 blocks) | observed | One level-8 region on R; not rechecked disc-wide | `parser/kiwiw/alldata_writer.py` |
| Leaf placement order within a block | Real leaf Map Frames of a block appear in ascending file offset in ascending row-major slot order (`iy`, then `ix`) for blocks without divided slots. R level 6: 4 of 4 non-divided blocks; spec is silent on Map Frame placement. Frames are not contiguous (gaps 1.6 KB to ~480 KB, other content interleaved) | observed | R check via `parser/analyze_leaf_zorder.py` loader (`kiwiw.alldata_writer.load_region`): sorted-by-offset slot order == sorted slot order in 4 of 4 blocks (2 divided blocks skipped); `parser/tests/test_parcel_mask.py` (`test_order_is_iy_ix_ascending`) asserts only the writer's own order | `parser/kiwiw/alldata_writer.py` |
| 2x2-tile Z-order hypothesis | Predicted order (2x2 tiles, tile row-major, cells (0,0),(0,1),(1,0),(1,1)) does not match R | observed | `parser/analyze_leaf_zorder.py --level 6` on R: 0 match, 4 mismatch (first divergence at index 2: predicted 16 after 1, real 2), 2 skipped as recursive. Hypothesis rejected; the script was written to test it | `parser/analyze_leaf_zorder.py` |
| Divided-parcel frame placement | Position of the sub-frames of a divided parcel relative to the parent's siblings | unknown | Not examined on R; the writer places them in slot order at the point of their parent | `parser/kiwiw/alldata_writer.py` |

## Populated area

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Populated cell set | On R every level's populated set is one full rectangle of cells (every cell has a Map Frame, empty or not). Level 0: ix 576..2303, iy 0..2143 = 1728 x 2144 = 3704832 cells (13 of them divided slots, so 3704819 leaf slots plus divided) | verified | `parser/refdata/parcel_mask.json` (`parser/tools/parcel_occupancy.py` refuses a non-rectangle); `parser/tests/test_parcel_mask.py` | `parser/build_alldata.py` |
| Mask rectangles | L12 (0..0, 0..0); L10 ix 0..2, iy 0..2; L8 ix 2..8, iy 0..8; L6 ix 9..35, iy 0..33; L4 ix 36..143, iy 0..133; L2 ix 144..575, iy 0..535; L0 ix 576..2303, iy 0..2143 | verified | `parser/refdata/parcel_mask.json`; `parser/tests/test_parcel_mask.py` (`test_mask_loader_round_trip` asserts the level set and level-0 values) | `parser/build_alldata.py` |
| Cell to mask index | Mask indices are the global `(ix, iy)` of the level's grid above | verified | `parser/tests/test_parcel_mask.py` | `parser/build_alldata.py` |

## Open questions

1. Meaning of LMR `upper_level` versus observed integration: level 0 shows 4x4
   groups of 16 shared slots, levels 2..10 carry the same field value and show none.
2. Whether the head unit requires 4x4 integration at level 0 (the writer emits one
   frame per slot), and what bounds an integrated frame declares (`map-frame.md`).
3. Route guidance list: present in only 190 of 1836 level-0 buffers and no level-2
   buffer, though both levels declare `n_basic_route` = 2; 5 level-0 lists start at an
   offset other than right after the main list. The parser never decodes it.
4. Header bytes 2..3 of the root record (route list offset) are carried verbatim on
   R; the writer's from-scratch records emit 0000, R uses FFFF for no list.
5. LMR background display-class table repeats 11 and 27; the entry-to-frame mapping
   is untested.
6. Divided types 2 and 3 never occur on R; type 3's meaning is unresolved (spec
   third divided size versus code comment "integration").
7. Display scale flags: role in head-unit scale selection is untested.
8. `n_basic_map`+`n_ext_map` (12) versus the 20-entry mfde table on R.
9. Whether the head unit needs BMR DSAs monotonic, blocks contiguous, or leaves in
   row-major order; R shows the pattern on the samples checked, not on the whole disc.
