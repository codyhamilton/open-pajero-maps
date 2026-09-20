# Disc layout: files, container and All Data Management Frame

Layer: the physical disc (ISO 9660 / UDF volume and its top-level files), the
`ALLDATA.KWI` container (Data Volume, Management Header Table, placement of everything
it points at), `LOADING.KWI`, and the parcel/mesh addressing arithmetic that locates a
frame. Frame *content* lives in the other schema files (`parcel-management.md`,
`map-frame.md`, `route-planning.md`, `index-idx.md`, `parameters-metadata.md`).

Spec: ch.1.2.7-1.2.11 (address/size types), ch.2 (medium layout), ch.5 (All Data
Management Frame), ch.30 (loading module). Ch.32-34 (image/voice frames) are listed only
as file inventory; their internals are not decoded (see `parameters-metadata.md`).

Nesting: ISO volume -> top-level files -> `ALLDATA.KWI` = Data Volume (0..2048) + a
2048-byte Management Header Table (MHT) + everything the MHT and PDMDH point at. All
multi-byte integers on disc are big-endian. All in-file addresses are relative to the
start of the file that holds them (spec DSA rule), never to the disc.

Numbering: the spec numbers management header records from 1; `kiwiw` uses 0-based
`MhrEntry.index`. Rows below give both ("rec 29 / spec 30").

## Addressing and size types (ch.1.2.7-1.2.11)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| DSA / SA, 4 B | `[sector index:24][disc side:1][layer:1][logical-sector offset:6]`; byte offset = `sector_index*sector_size + offset*logical_sector_size` (2048 and 32 on R) | verified | Every pointer in the 3 header regions and all in-place frame pointers round-trip through `getsector`/`encode_sector_addr`: `parser/tests/test_roundtrip_alldata_header.py`, `parser/tests/test_roundtrip_alldata_full.py`. | `parser/kiwiw/volume.py`, `parser/kiwiw/alldata_writer.py` |
| DSA side/layer flag bits (bit 7, bit 6 of low byte) | Spec: side A/B, single/double layer. Code masks with 0x3F and ignores them | observed | All 13 populated MHT entries on R have low byte 0x00 or a plain offset with both flags clear (measured). Never exercised elsewhere. | `parser/kiwiw/volume.py` |
| DSA null, `0xFFFFFFFF` | "insignificant" address; used for absent MHT records, empty BMT entries, absent frame slots | verified | spec ch.1.2.7; empty-slot round trip in `parser/tests/test_roundtrip_alldata_full.py`; MHT null entries round trip in `parser/tests/test_roundtrip_alldata_header.py`. | `parser/kiwiw/alldata_writer.py` |
| DSA alignment | Every addressed structure starts on a 32-byte (logical sector) boundary; writer raises on a misaligned offset | verified | Structural: the encoding cannot express other offsets; in-place test above. `parser/tests/test_roundtrip_alldata_full.py` | `parser/kiwiw/alldata_writer.py` |
| BS, 2 B | Size in logical sectors; 0 = null; max 65535 * 32 = 2,097,120 B | spec-only | spec ch.1.2.8. Writer raises if a frame exceeds it (`frame too large for a u16 logical-sector size`). No R frame at the limit measured. | `parser/kiwiw/frame_table.py` |
| SWS / D | Halved 2-byte / 4-byte sizes and displacements (unit = short word); all-ones = null | verified | spec ch.1.2.9/1.2.11; `bitutils.unsws()` raises on odd values; PDMDH/BMT round trip. Detail in `parcel-management.md`. | `parser/kiwiw/bitutils.py` |

## Files on the disc

R is a UDF-bridge disc. Observed by reading the R image (`original-disc/pajero-whereis-2007.iso`): ISO 9660 primary descriptor at sector 16 (`CD001`), a type-2 supplementary descriptor at sector 17 (escape `%/@`, i.e. Joliet), terminator at 18, and a UDF Anchor Volume Descriptor Pointer (tag id 2) at sector 256. Only the ISO 9660 view was walked; the UDF and Joliet trees were not compared.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| ISO volume identifier | `464210-8480`; system, set, publisher identifiers empty | observed | Read from PVD of the R image; `docs/design/target-disc.md` (UDF bridge, volume id `464210-8480`). Whether the head unit reads or checks it is unknown. | - |
| ISO application identifier | Text beginning `Session Offset : 0 VTC Sector ...` (mastering-tool stamp) | observed | PVD of R image; 2007-12-25 09:12:33 creation date. | - |
| ISO volume size | 1,166,832 sectors of 2048 B (= image size 2,389,671,936 B) | observed | PVD of R image. | - |
| Directory tree | Root holds 21 files plus dirs `COVERAGE/` (1 file), `DN/` (1 file), `IDX/` (99 files, dir extent 3 sectors). Names are ISO level-1 style (`NAME.EXT;1`) | observed | Walk of R image root. | - |
| Root file set | `ALLDATA.KWI`, `LOADING.KWI`, `METADATA.KWI`, `SPEC.KWI`, `COUNTRY.KWI`, `VERSION.TXT`, `COVERAGE.BIN`, `INDEXDAT.KWI`, `HWMAP.KWI`, `DICVCE56.KWI`, `GRA256D.KWI`, `KGRA256.KWI`, `PCT256D.KWI`, `KPCT256.KWI`, `PCT2DAT.KWI`, `KPCT2DT.KWI`, `PCT2MNG.KWI`, `KGRPDAT.KWI`, `VAR256D.KWI`; plus `DN/CLUSTER.DAT`, `COVERAGE/AUC.BMP` | observed | Listing of R (sizes). Spec ch.2.1 names only four basic files (ALLDATA, METADATA, SPEC, LOADING); the rest are vendor additions or defined in other chapters. R wins. | - |
| Physical file order on R | Root/DN/COVERAGE/IDX dir extents (sectors 927-932), then `LOADING.KWI` (940), `ALLDATA.KWI` (16242, immediately after LOADING), then `HWMAP`, `DICVCE56`, `KGRPDAT`, `PCT2MNG`, `PCT2DAT`, `KPCT2DT`, `GRA256D`, `KGRA256`, `PCT256D`, `KPCT256`, `VAR256D`, `COUNTRY`, `METADATA`, `SPEC`, `VERSION.TXT`, `CLUSTER.DAT`, `COVERAGE.BIN`, `AUC.BMP`, `INDEXDAT.KWI`, then `IDX/*` | observed | Extent LBAs read from the R image. Nothing in-file depends on ISO placement (all DSAs are file-relative), so order is not required by the format; whether the head unit needs `ALLDATA.KWI` at any LBA is unknown. | - |
| `ALLDATA.KWI` size | 1,529,729,025 B on R, i.e. 1 byte past a sector multiple; last byte `0xFF`, the 63 bytes before it are zero | observed | Measured on R. Cause unknown; G is written as a whole number of logical sectors. | `parser/kiwiw/alldata_writer.py` |
| `IDX/` names | 99 files: `<PFX>SR201..207` per state (SADSR, POISR, ITSSR: 7 each; FWYSR: 5, missing 202 and 207), `POIAS201..207`, `POIDT001..013`, `ARSNC201..207`, `FMCDT001`, `AGMSR/ARGSR/EMGSR` (1 plain + 9 suffixed `DB0 JG0 LR0 MB0 MZ0 ND0 NF0 NS0 VL0` each), `ARSSR`, `EM2SR`, `EM3SR`, `ZONEVSRC`, `ZONEZSRC`, 10 `ZSEL*` files | observed | Census of the R `IDX/` listing (count 99). The `2##` suffix is a state partition, 201 WA, 202 NT, 203 SA, 204 QLD, 205 NSW, 206 VIC, 207 TAS, not a zoom level (`docs/design/target-disc.md`). Semantics of the 3-letter `DB0..VL0` suffixes unknown. Contents: `index-idx.md`. | `parser/kiwiw/index_writer.py` |
| Copy-through vs regenerate policy | Copied unchanged: `LOADING.KWI`, `DICVCE56.KWI`, `GRA256D`, `KGRA256`, `PCT256D`, `KPCT256`, `PCT2DAT`, `KPCT2DT`, `KGRPDAT`, `VAR256D`. Regenerated: everything referencing links/coordinates (ALLDATA, IDX, INDEXDAT, HWMAP), and the small identity files | assumed | Policy in `docs/design/target-disc.md` (file-by-file table). Head-unit acceptance of copied blobs against a regenerated ALLDATA is untested. | - |

## Image/voice/support files (inventory only)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| `GRA256D.KWI`, `PCT256D.KWI`, `PCT2DAT.KWI` + `K*` partners, `VAR256D.KWI`, `KGRPDAT.KWI` | Image data frames (spec ch.33) and their key tables, tied together by `PCT2MNG.KWI` group ids | observed | Filename/size fit on R; pixel/palette content not decoded. | `parser/kiwiw/misc.py` |
| `DICVCE56.KWI` | Voice data frame (spec ch.34) | observed | Size and disc-stamp header only, R. | `parser/kiwiw/misc.py` |
| `HWMAP.KWI`, `INDEXDAT.KWI` | Named by MHT records 18 and 2 (see MHT); internals undecoded | unknown | Size/header sniff only, R; owner WP4 in `docs/design/target-disc.md`. | - |

## `LOADING.KWI` (spec ch.30)

One Loading Module Management Frame followed by module code. Size on R 31,338,496 B = 2048 (frame) + 15,301 * 2048 (code).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 (2 B) Number of systems n | 1 on R | observed | Hex of R file; spec ch.30.2. No test asserts it. | `parser/kiwiw/misc.py` |
| 2 (2 B) reserved | 0 | observed | R hex. | `parser/kiwiw/misc.py` |
| 4.. System Identification Information (16 B each): manufacturer id 12 B, module count 2 B, reserved 2 B | R: `DENSO`, 1 module | observed | R hex; spec ch.30.2.1. | `parser/kiwiw/misc.py` |
| 20 Module Identification (64 B): category 1 B, reserved 3 B, module name 52 B, version 8 B | R: category `0x01`, name `KH07`, version `1000`. Category bits: 7 diagnostic, 6 test, 1..0 (00 initial, 01 program, 10 library, 11 data); `0x01` = program | observed | R hex, offsets 20, 24, 76 match spec ch.30.2.2.1 field offsets. Not decoded by code beyond `KH07` string sighting. | - |
| 84 Module Management Information (256 B): valid-from 2 B, valid-to 2 B, title 64 B, maker info 182 B, code DSA 4 B (offset 250), code size BS 2 B (offset 254) | R: dates 0, title and maker info empty, DSA field `0x00000001`, size `15301` | observed | R hex at 84, 334, 338. Not parsed by code. | - |
| Module code DSA interpretation | On R the code starts at byte 2048 but the DSA reads `0x00000001`; read as spec DSA (sector<<8 + n*32) it would point at byte 32. Size 15301 matches 2048-byte blocks exactly | unknown | Conflict: spec ch.30 says DSA (ch.1.2.7); R data is consistent only with a plain 2048-B sector count. Winner: R (observed), for a copied file this is moot. | - |
| Module code | Opaque head-unit program (~31 MB); size is a multiple of the block size | observed | R size arithmetic above; content not decoded. Copied unchanged. | `parser/kiwiw/misc.py` |

## `ALLDATA.KWI` regions on R (byte offsets in file)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0..2048 Data Volume | Media identification (below) | verified | `parser/tests/test_roundtrip_alldata_header.py` (byte-identical rebuild). | `parser/kiwiw/volume_writer.py` |
| 2048..4096 Management Header Table | 113 x 18 B records + 14 B tail (below) | verified | same test. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume_writer.py` |
| 4096..6144 record-29 frame | 2048 B language/country code list, referenced by MHT record 29; carried byte-identical from R | verified | `parser/tests/test_alldata_writer.py::test_mht29_copy_through`; bytes in `parser/refdata/mht29_frame.bin`. Content grammar (`0x1301 0x0101 ...`, then `us eng ger fre spa ita dut swe dan por nor fin # au` and `aus`) is not decoded. | `parser/kiwiw/alldata_writer.py` |
| 6144..27232 PDMDH + LMR + BSMR + BMT | Parcel-related Data Management Record, 21,088 B (21,072 record + 16 B pad), 7 LMR, 601 BSMR, 165 BMT tables | verified | `parser/tests/test_roundtrip_alldata_header.py`; fields in `parcel-management.md`. | `parser/kiwiw/volume_writer.py` |
| 27232..~26.6 MB block records | One Parcel Management Record per block, packed contiguously with no gaps in level order 12, 10, 8, 6, 4, 2, 0 (each level's range starts where the previous ended: 27264, 27456, 28896, 47680, 171424, 1641312; level 0 ends at 26,596,192) | observed | Measured min/max block offset per level from the BMT of R (7 levels, 2307 entries). Not asserted by a test. | `parser/kiwiw/alldata_writer.py` |
| ~26.6 MB..: Map Frames (leaves) | Leaf frames in increasing offset order with variable gaps (1.6 KB to ~480 KB in the sampled region), other-level content interleaved | observed | R sample; weak. Placement rule of the original tool not derived. | - |
| 532,979,712 MHT rec 1 / spec 2 (region mgmt, 160 B) | Region-related data management header, inside the leaf area | observed | MHT entry on R (dsa `0x03F89400`, size 5). Contents in `route-planning.md`. | - |
| 683.9..684.8 MB: MHT recs 5, 3, 20, 6 | Graphics (rec 5 / spec 6, 64 B @683,939,840), parameters (rec 3 / spec 4, 128 B @684,670,976), rec 20 / spec 21 (64 B @684,605,440), rec 6 / spec 7 (451,808 B @684,736,512) | observed | MHT entries measured on R; first bytes of rec 3 show `0xAF12xxxx` ext-frame ids, rec 6 begins `0x0003 'ri' ...` with the 12-byte maker stamp `0f613c003c357d00000007 22`. Spec ch.5.2 calls spec 7 "Voice", but voice is `DICVCE56.KWI` (rec 25); what rec 6 holds is unknown. Contents: `parameters-metadata.md`, `route-planning.md`. | - |

## Data Volume (ch.5.1, offset 0, 2048 B)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 (64 B) System-specific identification: MID 12 B + maker text 52 B | R: MID then `AFAU:2.64,AGAU:2.64\n` (same string as `SPEC.KWI` SUPERMETA) | verified | `parser/tests/test_roundtrip_alldata_header.py`. Meaning of maker text is maker-defined (spec ch.5.1 note 1). | `parser/kiwiw/volume.py` |
| 64 (64 B) Data author identification: MID + 52 B binary | R: MID then binary bytes (`0f613c003c357d 00000000 52` ...), not text; `VolumeHeader.data_author_id` string is a lossy truncation | verified | Round trip is byte-identical only because the raw hex is carried (`maker_defined_hex`); meaning unknown. | `parser/kiwiw/volume.py` |
| 128 (32 B) System identification: MID 12 B + 20 B | R: MID only, remainder zero | verified | same test. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| MID (12 B): PID 8 B (lat 3 + exp 1, lon 3 + exp 1), floor i8, reserved, date u16 | Maker office position, floor, days since 1997-01-01. R: 34.9976 N, 137.0088 E, floor 0, date 1826, identical in all three MIDs; spec says all `0xFF` if system-independent | verified | Round trip; values decoded from R. Whether the head unit reads any MID is unknown; G copies R's values. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 160 (64 B) Format version | `FORMAT VERSION KIWI01-22-00\n` on R (space where spec shows `_`, trailing `0x0A`, zero pad) | verified | Round trip. Spec: `FORMAT_VERSION_KIWIaa-bb-cc`. R wins on the separator. | `parser/kiwiw/volume.py` |
| 224 (64 B) Data version | `DATA VERSION 07/12/21/01\n` (yy/mm/dd/serial, mass-production form) | verified | Round trip; spec ch.5.1 note 5. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 288 (128 B) Disk title | `AU \n` on R, no rule in spec | verified | Round trip. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 416 (8 B) Data contents: 4 words. Word 0 bit 15 main map, 14 route planning, 13 index data | R word 0 = `0xE000`, words 1..3 = 0 | verified | Round trip (low bits and words 1..3 carried in extras). Whether the head unit gates features on these bits is unknown. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 424 (32 B) Media version | `V 05.07.20` (Vaa.bb.cc) | verified | Round trip; spec ch.5.1 note 8. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 456 (16 B) Data coverage: lower-left PID, upper-right PID | R: S50, E90 to N35.3333, W142 (box crosses +/-180); exponent bytes 0 | verified | Round trip; kiwiread output on R; agrees with PDMDH coverage (`docs/design/target-disc.md` cross-file consistency). Longitude is expressed east-positive with the right edge wrapped negative. | `parser/kiwiw/volume.py` |
| 472 (2 B) Logical sector size | 32 (spec range 32..256 B) | verified | Round trip; every DSA decode uses it. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 474 (2 B) Sector size | 2048 (fixed for CD/DVD-ROM per spec ch.1.2.7) | verified | Round trip. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 476 (2 B) Background default: bit 15 in-map parcels (0 land, 1 sea), bit 14 out-of-map parcels | R: `0x4000` = in-map land, out-of-map sea | verified | Round trip. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |
| 478 (14 B) reserved | Zero on R | verified | Carried verbatim (`reserved_478_hex`), round trip. | `parser/kiwiw/volume.py` |
| 492 (256 B) Level Management Information (ch.5.1.1: count r, then per data type a header `[type:8][levels:8]` and per level `[level:8+8 rsvd][n block mgmt records:16]`) | All zero on R, so the structure is untested; the levels are instead described by the PDMDH/LMR (`parcel-management.md`) | spec-only | spec ch.5.1.1 (data types 01 main map, 02 route guidance, 03 route planning, 04/05 additional). R all-zero verified by round trip only as opaque bytes. | `parser/kiwiw/volume.py` |
| 748 (1300 B) reserved | Zero on R | verified | Carried verbatim, round trip. `parser/tests/test_roundtrip_alldata_header.py` | `parser/kiwiw/volume.py` |

## Management Header Table (ch.5.2, offset 2048, 2048 B)

Record layout (18 B): DSA 4 B, size 2 B (logical sectors of the management header), management file name 12 B (left-justified, NUL padded; empty = record lives in this file).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Record 0..17: DSA 4, size 2, name 12 | Layout of one Management Header Record | verified | Round trip of all 113 records: `parser/tests/test_roundtrip_alldata_header.py`. | `parser/kiwiw/volume.py` |
| Record count | Table is 113 x 18 B + 14 B zero tail. Spec ch.5.2 says 33 records + one 1454-byte "maker original: RESERVED" record 34 | verified | Conflict: spec shows one opaque 1454-B record; R uses that area as 80 more 18-B records (rec 34 is `COUNTRY.KWI`). R wins (`test_management_header_table_byte_identical` asserts `entries[34].name == "COUNTRY.KWI"`). Older `parse_mhr_table` reads only 34 records. | `parser/kiwiw/volume.py` |
| Named record: name set | DSA is relative to the top of the named file and size is the size of that file's own management header; R sets DSA 0 for these | observed | R entries with names below; spec ch.5.2 note 1. Semantics for 0-DSA not otherwise checked. | `parser/kiwiw/volume.py` |
| Unused record convention | Records 0..47 unused = (`0xFFFFFFFF`, 0, no name); records 48..112 unused = (0, 0, no name) | observed | Census of R MHT (all 113 records read). G reproduces both. | `parser/kiwiw/alldata_writer.py` |
| rec 0 / spec 1: DSA `0x300` = byte 6144, size 659 (21,088 B) | Parcel-related data management (PDMDH) | verified | Round trip; `test_pdmdh_record_byte_identical` asserts inline (no name). | `parser/kiwiw/alldata_writer.py` |
| rec 1 / spec 2: DSA `0x03F89400`, size 5 | Region-related data management | observed | R MHT; contents in `route-planning.md`. | - |
| rec 2 / spec 3: name `INDEXDAT.KWI`, DSA 0, size 3 | Index data management, in a separate file | observed | R MHT; spec ch.5.2 record 3 is "Index Data Management". | - |
| rec 3 / spec 4: DSA `0x0519E800`, size 4 | Management of various parameters | observed | R MHT; contents in `parameters-metadata.md`. | - |
| rec 4 / spec 5 | Infrastructure data management | observed | Absent (`0xFFFFFFFF`) on R. | - |
| rec 5 / spec 6: DSA `0x05188300`, size 2 | Graphics data management | observed | R MHT. Spec places graphics data here; the disc's image files are named records (rec 26, 30) or separate files. Relationship unresolved. | - |
| rec 6 / spec 7: DSA `0x051A0800`, size 14119 | Spec: voice data management. R: a 451,808-B in-file frame | unknown | R MHT; see region table above. | - |
| rec 18 / spec 19: name `HWMAP.KWI`, size 2 | Highway map, extended part 1 (reserved) area used by the vendor | observed | R MHT. | - |
| rec 20 / spec 21: DSA `0x0519C800`, size 2 | Extended part 1, in-file | observed | R MHT; content begins `0016 95f9 0000 278d`. Meaning unknown. | - |
| rec 25 / spec 26: `DICVCE56.KWI`, size 2; rec 26 / spec 27: `KGRPDAT.KWI`, size 2; rec 30 / spec 31: `PCT2MNG.KWI`, size 1; rec 34 / spec 35: `COUNTRY.KWI`, size 1 | Extended-part-1 records naming vendor files | observed | R MHT. Only `COUNTRY.KWI` is asserted by a test (record index 34). | `parser/kiwiw/alldata_writer.py` |
| rec 29 / spec 30: DSA `0x200` = byte 4096, size 64 (2048 B) | Points at the record-29 frame; spec calls this range RESERVED extended part 1 | verified | `parser/tests/test_alldata_writer.py::test_mht29_copy_through`. | `parser/kiwiw/alldata_writer.py` |
| Extended part boundaries | Spec: basic records 1..16, extended part 1 17..32, maker part 33..48 | spec-only | spec ch.5.2. R uses records in the maker range and beyond (spec 35 = COUNTRY), so the split is not followed. | - |

## Mesh addressing (ch.6, used by all locators)

Grid definitions (cell size, counts per level) are PDMDH/LMR fields, documented in `parcel-management.md`. Only the arithmetic that turns coordinates into (block set, block, parcel) is here.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Coverage box and wrap | Coverage is PDMDH lower-left/upper-right; longitude span is `right - left`, plus 360 when negative (R: 90 E to 142 W) | verified | `parser/tests/test_mesh.py` (Melbourne cell matches patched kiwiread, `bs 22 block 23 parcel 542`). | `parser/kiwiw/mesh.py` |
| Cell index | `ix = floor(dlon / (lon_span / nx))`, `iy = floor(dlat / (lat_span / ny))`, clamped; `nx = (1+nbs_lng)(1+nbl_lng)(1+npc_lng)` and likewise for y | verified | `parser/tests/test_mesh.py`, `parser/tests/test_mesh_divided_locate.py`, and level-wide in-place round trips. | `parser/kiwiw/mesh.py` |
| Cell decomposition | Row-major, latitude outer, longitude inner: `px = ix % npc`, then `blx = (ix // npc) % nbl`, `bsx = (ix // npc) // nbl` (same for y) | verified | same tests; in-place assembly re-derives every leaf position from it. `parser/tests/test_mesh.py` | `parser/kiwiw/mesh.py`, `parser/kiwiw/alldata_writer.py` |
| Block set, block, parcel lookup | BSMR ordinal -> BMT (per block set, `(1+nbl_lat)(1+nbl_lng)` entries) -> block record -> per-slot `(DSA, size)` entry | verified | `parse_pdmdh_full` raises if any BMT entry count disagrees with the LMR; 2307 entries checked on R (`parser/tests/test_roundtrip_alldata_header.py`). | `parser/kiwiw/mesh.py`, `parser/kiwiw/volume.py` |
| Divided/integrated parcel recursion | Parcel type 1..3 slot points (halved offset, size 0) at a nested record; recursion depth cap 6 in code | verified | `parser/tests/test_mesh_divided_locate.py`; spec ch.6 under-specifies types 1..3. Layout in `parcel-management.md`. | `parser/kiwiw/mesh.py` |

## Allocation rules used by the writer

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Fixed prefix | Data Volume 0, MHT 2048, record-29 frame 4096, PDMDH 6144 (matches R) | verified | `parser/tests/test_alldata_writer.py`; header round trip. | `parser/kiwiw/alldata_writer.py` |
| Padding | Each frame and block record is zero-padded to a multiple of 32 B; the stored size is the padded length in logical sectors | verified | In-place byte identity, `parser/tests/test_roundtrip_alldata_full.py`. | `parser/kiwiw/alldata_writer.py` |
| Block order on G | Blocks ordered (level, block set, block); within a block type-0 frames in slot order first, then divided sub-frames grouped by parent slot, then the block record follows its frames | assumed | Build policy of the vectorised layout, checked against the per-object layout by `parser/tests/test_alldata_writer.py::test_indexed_matches_object_path`. R places all block records first (level 12 to 0) and frames later; no evidence the head unit depends on either order. | `parser/kiwiw/frame_table.py` |
| Block record size | `4 + 6 * slots` header+entries plus, per divided parent, `4 + 6 * gn` sub-record bytes, rounded up to 32 B | verified | De novo re-parse consistency and in-place identity for levels 8, 6, 4, 2 (`parser/tests/test_roundtrip_alldata_full.py`). Layout in `parcel-management.md`. | `parser/kiwiw/frame_table.py` |
| Build-time frame table `FRAME_DTYPE` `(ix, iy, pt, sx, sy, fid, len, off)` | Spill-file index of encoded frames before placement; not an on-disc structure | verified | Object path and indexed path produce identical files: `parser/tests/test_alldata_writer.py::test_indexed_matches_object_path`. | `parser/kiwiw/frame_table.py` |
| Whole-disc capacity | Single-layer DVD-R, image at most 4,700,000,000 B | assumed | `docs/design/target-disc.md`; dual-layer support of the head unit unknown. | - |
| Other MHT targets on G (`INDEXDAT`, `HWMAP`, records 1, 3, 5, 6, 20) | Currently written as absent (`0xFFFFFFFF`, 0) with names kept | assumed | `output/ALLDATA.KWI` MHT (2026-09-19 build), `docs/design/target-disc.md` (owned by WP2/WP4). Head-unit behaviour with absent records unknown. | `parser/kiwiw/alldata_writer.py` |

## Open questions

- What creates the 1-byte overhang of `ALLDATA.KWI` on R, and does the head unit care?
- Does the head unit validate the Data Volume MIDs, format/data/media version strings, or Data Contents bits? G copies R's values or writes a synthetic string; nothing tests acceptance.
- What are MHT rec 5 (spec 6, graphics) and rec 6 (spec 7, 451,808 B) and rec 20 (spec 21) in `ALLDATA.KWI`? Spec labels do not match R.
- Level Management Information (offset 492) is zero on R; is it ever read?
- Are the DSA side/layer flag bits ever set, and does a single-layer DVD-R need them clear?
- Does the head unit depend on ISO placement (LBA order, `ALLDATA.KWI` position, Joliet vs UDF view)? Only the ISO 9660 view of R was walked.
- Leaf placement order in R (gaps, interleaving across levels) is not derived; G uses its own order.
- `LOADING.KWI` code DSA `0x00000001` conflicts with the ch.1.2.7 DSA definition.
- Meaning of the `DB0..VL0` IDX suffixes; owned by `index-idx.md`.
