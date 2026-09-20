# IDX search index

The IDX layer is the set of `IDX/*.IDX` search files plus `INDEXDAT.KWI` (the Data
Management Frame, spec ch.11.2). All multi-byte values are big-endian. Ch.11 "SWS" and "D"
size/offset fields are stored halved (real = stored x 2); `sws32` leaves `0xFFFFFFFF`
(absent) untouched. Files nest: every search file starts with a 16-byte management header
`[4B decl][4B count G][4B SWS record size][4B D first-record offset]`, followed by Detailed
Search Info Records (DSIR). A DSIR points (halved, record-relative addresses) to a DCTF
definition frame, category data, a matching-data frame and optionally a next-level search
frame. Matching records are self-describing through the DCTF definition. The numeric
suffix is the state partition (201 WA, 202 NT, 203 SA, 204 QLD, 205 NSW, 206 VIC, 207 TAS),
not a zoom level. Map link/mesh references are covered by `map-frame.md` and `map-road.md`;
disc placement by `disc-layout.md`.

## Files and state partition

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Suffix 201..207 | State partition: 201 WA, 202 NT, 203 SA, 204 QLD, 205 NSW, 206 VIC, 207 TAS | observed | ZONEZSRC.IDX SRZN records SZCD 0x03000001..07 name `IDX/SADSR201..207.IDX`; ZSEL state names (WA = ...01). Older notebook "suffix = zoom level" is wrong; the ZONE table and state names win | `parser/kiwiw/search_frame.py` |
| Families with suffix | SADSR, POISR, ITSSR, FWYSR (201,203,204,205,206 only), ARSNC, POIAS | observed | listing of R `IDX/`. Only SADSR has an on-disc table naming its per-state file; suffix of the others is by convention | - |
| Families without suffix | POIDT001-013, FMCDT001, ZONE*SRC/ZSEL*, AGMSR/ARGSR/EMGSR, ARSSR, EM2SR, EM3SR, HWMAP.KWI | observed | listing of R | - |
| POIDT001-007 | Intersection info (PKIS), paired with ITSSR201-207 | assumed | inferred from ordering and file sizes; INDEXDAT filenames read directly, pairing not | - |
| POIDT008-012 | Freeway info (PKFW), paired with FWYSR 201,203,204,205,206 | assumed | same inference | - |
| POIDT013 | POI info (PKNM) | assumed | same inference | - |

## Search file management header (16 bytes)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| +0 decl (4 CH) | DFSR / DFSA / DFSM / DFM2 / DSRC / PINR by family | verified | `parser/tests/test_roundtrip_idx.py` (DFSR header); spec says 'DSRC' only, disc uses the variants, disc wins | `parser/kiwiw/search_frame.py` |
| +4 count G (u32) | Number of DSIR records (SADSR 2, POISR 3, POIDT 1) | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/search_frame.py` |
| +8 SWS record size | Halved DSIR size (SADSR 0xdc = 440, POISR 0xea = 468, nested SRT1 0xbc = 376, POIDT 0x28 = 80) | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/search_frame.py` |
| +12 D first-record offset | Halved offset of first DSIR (16 on disc) | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/search_frame.py` |
| Family record sizes | AGMSR/ARGSR/EMGSR DFSR 0x86-0x92; ARSNC/ARSSR/EM* DFSM 0xca-0xce; FMCDT DFM2 0xf8; FWYSR DFSR 0xb4; ITSSR DFSR 0xce; POIAS DSRC 0xea; ZONE DFSA 0xae; ZSEL DFSR 0xae (halved) | observed | header dumps of R | - |
| Whole-file layout (SADSR201) | header, record slots, then per record catdef, mdef, catdata, mdf, then next_level recursion in reverse record order (dedup by offset); zero gaps | verified | `parser/tests/test_roundtrip_idx_full.py` byte-identical replicate and fromscratch. Reverse order witnessed once only | `parser/kiwiw/index_writer.py` |
| SADSR201 tail (11,776 B at 15,375,908) | Unreachable DFSR with an SRAL record; copied verbatim | unknown | not reachable from any DSIR | `parser/kiwiw/index_writer.py` |
| Whole-file layout (other files) | Same rule assumed; POISR201 assembly not finished | assumed | `docs/ARCHITECTURE.md` WP3/WP4 | - |

## Detailed Search Info Record (DSIR)

Sizes and addresses are SWS-halved; addresses are record-relative (see indirection entry).

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| +0 decl (4 CH) | Search type tag (SRMX, SRHA, SRT1, SRHG, SRAL, SRFW, SRRP, SRBT, SRAG, SRME, SRAR, SRNC, SRZN, SRSZ, SRBC) | verified | `parser/tests/test_roundtrip_idx.py` DSIR records | `parser/kiwiw/search_frame.py` |
| +4..16 (12 B) | Undecoded; contains tags such as KBA2, KBST. Carried verbatim | unknown | spec puts catdef size at +12; the code layout matches the disc and wins | `parser/kiwiw/index_writer.py` |
| +16 catdef address | DCTF definition frame | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_data.py` |
| +20 catdata size, +24 catdata address | Category data | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_data.py` |
| +28 default keyboard (4 CH) | e.g. KBC1, NORM | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_data.py` |
| +32 category parent record size | 14 (halved 7); option record size +36 is 8 (halved 4) | verified | `parser/tests/test_roundtrip_idx.py`; older category-tree claim came from an un-doubled offset and is wrong | `parser/kiwiw/index_data.py` |
| +40 first-level category size, +44 first-level option count | Category tree top level | observed | dumps on R | `parser/kiwiw/index_data.py` |
| +48..60 (12 B) | Undecoded, carried verbatim | unknown | no source decodes it; not searched on disc | `parser/kiwiw/index_writer.py` |
| +60 mdef address | Matching-data definition (DCTF) | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_data.py` |
| +64 mdf size, +68 mdf address | Matching-data frame | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_data.py` |
| +72 max record size, +76 record count | Matching records | verified | `parser/tests/test_roundtrip_idx.py`; full scan counts equal declared (SADSR201 38,120 SRMX; SADSR202 2,827 / 18,260 SRT1) | `parser/kiwiw/search_frame.py` |
| +80 default POI serial | - | observed | dumps on R | `parser/kiwiw/index_data.py` |
| +84 next-level size, +88 next-level address | Nested search frame | verified | `parser/tests/test_roundtrip_idx_full.py` | `parser/kiwiw/index_data.py` |
| +92.. additional-address tail | Entries up to record size | verified | `parser/tests/test_roundtrip_idx.py` FrameRef entries | `parser/kiwiw/index_data.py` |

## Address indirection entry

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Address field | Halved, record-relative: target = record_base + 2 x field | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_data.py` |
| Entry: [4B halved absolute offset] | Absolute file offset (halved) | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_writer.py` |
| Entry: [2B halved name size, words] | Filename length | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_writer.py` |
| Entry: filename padded to even | Target file name | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/index_writer.py` |

## DCTF definition frame

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 16-byte header | 'DCTF' 'REAL' 6 zero bytes + [2B n_items]; n_items counts fields only | verified | `parser/tests/test_roundtrip_idx.py` street DCTF; off-by-one (last field dropped) corrected 2026-08-28 | `parser/kiwiw/search_frame.py` |
| Field entry (16 B) | [4B usage][4B description NORM/VRBL/FDRL/OFST/ACTN/REAL][2B element type][2B count or count-type ASCII][4B additional] | verified | `parser/tests/test_roundtrip_idx.py`; additional may be a raw integer (DCSF), so right-strip only | `parser/kiwiw/search_frame.py` |
| Element types | UB SB UW SW UL SL LG UH (nibble) HB (nibble alias) P6 BF CH BT C SG | observed | seen across R dumps; spec spells SRHA NXKD/NXFN as HB (fixed) | `parser/kiwiw/search_frame.py` |
| VRBL field | Length-prefixed; BT + UH + additional 'CMP6' is a VRBL P6 (SRHA RLXY) | observed | SRHA dumps | `parser/kiwiw/search_frame.py` |
| CMCH / CMP6 / CMUL compressed variants | Spec compression variants | spec-only | spec ch.11; none observed on R | - |

## Matching record rules

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| BFRL, NFRL | First fields; 1 byte, halved; NFRL=0 ends chain. Some frames use FDUH nibble, FDUW/FDWD word, FDUB | verified | `parser/tests/test_roundtrip_idx.py` all street records | `parser/kiwiw/search_frame.py` |
| Fields up to and including STFG | Unconditional | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/search_frame.py` |
| STFG | Presence bitmap over later fields in definition order, LSB-first, byte 0 first | verified | `parser/tests/test_roundtrip_idx.py`; SADSR201 SRMX 7f00 (38,119 of 38,120); SRT1 STFG=07 present only ZIPN, PRFX, STAD | `parser/kiwiw/search_frame.py` |
| NXKD/NXFN nibble pair | Share one byte (0x51 = class 5, serial 1) | verified | `parser/tests/test_roundtrip_idx.py` | `parser/kiwiw/search_frame.py` |
| Trailing padding | Allowed after last field | observed | dumps | `parser/kiwiw/search_frame.py` |
| NFRL adjacency in POISR deep frames | NFRL is not physical adjacency; walk physically with end_offset | observed | `iter_matching_records` docstring | `parser/kiwiw/search_frame.py` |
| RLXY (P6) | Two 3-byte geo_secs angles (bit 23 sign, low 23 bits = 1/8 arc-second); coarse link start point (spec 11.A.2.14 note 4) | verified | `parser/tests/test_roundtrip_idx.py`; 344,207 SADSR201 address records inside WA bbox, 0 outliers | `parser/kiwiw/search_frame.py` |
| Street to address-range chain | Street NXST (halved) x 2 = byte offset in address-range frame; NXCT = count. Old "Street ID to Link ID" framing wrong | verified | `parser/tests/test_roundtrip_idx.py` anchor address ranges | `parser/kiwiw/search_frame.py` |
| LKID | Inline at end of chain; not cross-checked against ALLDATA link records | unknown | field list only; no decoded values | `parser/kiwiw/search_frame.py` |

## Record families

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| SADSR SRMX street | BFRL NFRL FGFZ STFG STID NXKD NXFN NXST NXCT KYCH NAME (+RPAT RPNK RPNF RPNS RPNC in 202); 38,120 in 201 | verified | `parser/tests/test_roundtrip_idx_full.py`; STFG in 202 is 7f00 for all 2,827 | `parser/kiwiw/search_frame.py` |
| SADSR SRHA suburb | BFRL NFRL MXSG MXKY FGFZ KYCH STFG NXKD NXFN NXST NAME RLXY VRBT/CMP6; 1,285 in 201 | verified | `parser/tests/test_roundtrip_idx_full.py` | `parser/kiwiw/search_frame.py` |
| SADSR SRT1 address range | BFRL NFRL FGSA ARCD(VRUL) RLXY LKID STFG ZIPN PRFX STAD x2 SPFX SSFX STYP GDXY; 344,276 in 201; 18,260 in 202 (STFG=07) | verified | `parser/tests/test_roundtrip_idx_full.py`; 14-field frame corrected (STYP, GDXY) | `parser/kiwiw/search_frame.py` |
| ARCD | Area code; always starts 0x1e; three tiers, shared suburb id; semantics unknown | unknown | no source decodes it | - |
| SPFX SSFX STYP GDXY | Never present on R (STFG bits 0) | unknown | R scans | - |
| POISR SRMX POI | BFRL NFRL ARCD FGFZ STFG(2) CTGY(UW) ZIPN RLXY NXKD NXFN NXST NXCT KYCH NAME RPLV RPAT RPCN RPLN RPST RPSO; one record per word-suffix of a name; POISR202 10,969 records, STFG varies (fd07, fd06, fc07 ...) | observed | R walk of POISR202; docstring of `iter_matching_records` claims POISR201 populations decode byte-identically but no test covers it. `docs/ARCHITECTURE.md` says POISR decoder has bugs; docstring untested, so observed only | `parser/kiwiw/search_frame.py` |
| CTGY | Multiples of 128; includes vendor codes absent from the spec (~38% of QLD sample); category-name table undecoded | observed | sample of R | - |
| POISR SRHA / SRHG | SRHG hierarchical genre: JPTB SFTO SFBO SELN DCSF BFRL NFRL KBTP MXSG MXKY MXK2 MXAB NAME STFG NXKD NXFN NXST | observed | DCTF dump | `parser/kiwiw/search_frame.py` |
| ITSSR | SRBT (BFRL FDUH NFRL STID NCST STFG ARCD) + nested SRAL (BFRL NFRL STFG FGFZ KYCH LGNO NAME POIO POIC); ITSSR202 2,803 SRBT, STFG 0 | observed | R dump | - |
| FWYSR | SRFW (FGFZ KYCH NAME NXKD NXFN NXST) + nested SRRP (SFTO SFBO SEFG SELN DCSF BFRL NFRL KYCH NAME RLXY NXKD NXFN NXST NXSZ); FWYSR204 23 SRFW | observed | R dump. Bodies undecoded (WP4) | - |
| AGMSR/ARGSR/EMGSR | DFSR SRAG genre hierarchy (JPTB SFTO SFBO SELN DCSF BFRL NFRL KYCH KBTP STFG NXKD NXFN NXST DSRA CTGY CTG2 VOID NAME TPNM); AGMSR nested SRME (SMEN SMEL NAOF NACT) then SRAR (CTGY RLXY POIO), 519,215 records | observed | R dump. Bodies undecoded (WP4) | - |
| DB0/JG0/LR0/MB0/MZ0/ND0/NF0/NS0/VL0 suffix set | Unexplained; headers differ only in record size | unknown | R headers | - |
| ARSNC/ARSSR/EM2SR/EM3SR | DFSM SRME (SMEN u32, SMEL u8 mesh, NXKD/NXFN HB, NXST) then SRAR (CTGY RLXY POIG POIO) or SRNC (ARCD RLXY POIG POIO) | observed | R dump. Bodies undecoded (WP4) | - |
| POIAS | DSRC SRBC (STID ARCD NXKD NXFN NXOF; mdef adds CTGY VRUW, POIO) | observed | R dump | - |
| ZONE*SRC | SRZN (SZCD DCFN NXKD NXFN NXST NXFM CH*16), SELN=7, category data at 508, 26-byte records | observed | R dump | - |
| ZSEL* | SRSZ (VDID DESL SFTO SFBO SELN DCSF BFRL NFRL SZCD VDID NAME TPNM DFKB SZDI), keyboard KBC1; state names multi-language | observed | R dump | - |
| FMCDT001 | DFM2 SRBT keyed by ARCD; catdef SELN DCSF ARCD NXKD NXFN NXST, mdef BFRL NFRL NAME; 11,997 records | observed | R dump; semantics unknown | - |
| category_data name table | Category names for CTGY | unknown | undecoded | - |

## POIDT001-013 (PINR)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Header | 'PINR', count 1, size 0x28 x 2 = 80, first record at 16 | observed | R headers | `parser/kiwiw/search_frame.py` |
| DPOI record | +0 decl, +4 expansion size, +8 expansion offset (FFFFFFFF), +12 def size, +16 def addr, +20 data size, +24 data addr, +28 record size, +32 record count, +36 additional-address entries | observed | hand-decoded on POIDT012; spec gives different offsets for items 2-3 (8, 12); disc wins | - |
| 001-007 body | BFRL FDUB NFRL RLXY STFG ARCD ZIPN SPFX SSFX STYP SPF2 SSF2 STY2; record size 14; 139,405 records in 001 | observed | DCTF dump | - |
| 012 body | BFRL FDWD NFRL RLXY VRBT STFG GLKI ARCD LKID GDXY NAME; size 76; 3,187 records | observed | DCTF dump | - |
| 013 body | BFRL NFRL ARCD RLXY NAME STFG(2) LVXY MPSC GLKI LKID GDXY CTGY TELE ZIPN ADNM; size 158; 506,948 records | observed | DCTF dump; bodies undecoded (WP4) | - |

## INDEXDAT.KWI (Data Management Frame)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 'DCTR' header, 92 B | Format version '2.64_AU', created 2007-12-12, 'DENSO CORPORATION' | observed | R read | `parser/kiwiw/index_data.py` |
| Header numeric fields | Halved. Measured 356 + 13x280 = 3996 and 3996 + 13x440 = 9716 = 0x12fa x 2. `parse_data_management_frame_header` reads them raw; the measurement wins | observed | R arithmetic | `parser/kiwiw/index_data.py` |
| Title char list | "US INDEX SEARCH" after header | observed | R read | - |
| Volume record x13 (280 B, at 356) | +0 data decl (DSRC/DSBT/DFSM), +4 function decl, +8 'FNME', +12/+16 expansion size/offset, +20 keyboard NORM, +24 min PID, +32 max PID, +40 search-frame mgmt size, +44 address, +48 title list with language table | observed | R read | - |
| Function declarations | FSLZ FSAD FFRW FITS FPOI FMNC FASP FARG FAGN FMES FAGE FWM2 FWM3 | observed | R read | - |
| Referenced files | ZSELDEF0, ZONEZSRC (SAD FRW ITS POI MNC ASP), ARGSR, AGMSR, ARSSR, EMGSR, EM2SR, EM3SR | observed | R read | - |
| Bounding box | Identical in all records (whole Australia) | observed | R read | - |
| POI-info record x13 (440 B, at 3996) | Decl 'PINR' + kind PKIS x7, PKFW x5, PKNM x1; filenames POIDT001-013 | observed | R read | - |
| Expansion field at 9716 | Begins 'DFDA...DFCF...FNME INDEXDAT.KWI' | unknown | undecoded | - |

## HWMAP.KWI

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Whole file (112,190 B) | Header 0x0018 0x0000 0x0018 0x0005 0x122e ...; no known spec chapter | unknown | size and header only | - |

## Code and tests

Code: `parser/kiwiw/index_data.py`, `parser/kiwiw/index_writer.py`,
`parser/kiwiw/search_frame.py`, `parser/osm_to_address_index.py` (SADSR only, from OSM).
Round-trip: `parser/roundtrip_idx.py` (232/232), `parser/tests/test_roundtrip_idx.py`,
`parser/tests/test_roundtrip_idx_full.py` (R required; skip without it).

## Open questions

- HWMAP.KWI structure and the INDEXDAT expansion field.
- The two 12-byte DSIR gaps (+4..16, +48..60).
- ARCD semantics; category name table for CTGY; LKID cross-check against link records.
- Whether POISR/ITSSR/FWYSR/ARSNC/POIAS suffixes are recorded anywhere on disc.
- The DB0/JG0/... suffix set; FMCDT semantics; the SADSR201 unreachable tail.
- Meaning of SPFX, SSFX, STYP, GDXY (never present on R).
- POISR201 whole-file assembly and a test for its populations.
- Bodies of POIDT, ITSSR, FWYSR, AGMSR/ARGSR/EMGSR, ARSNC family, ZONE/ZSEL, FMCDT001 (WP4); OSM has no equivalent for address ranges per link, suburb hierarchy or vendor POI categories (WP3).
