# Parameters, metadata and small files

The small files beside `ALLDATA.KWI` and `IDX/`, plus the parameter (spec Ch.12) and
metadata (spec Ch.13) frames, the one copy-through frame inside `ALLDATA.KWI`
(management header record 29), the cross-file disc stamp and the coverage bounds.
Files at the volume root are ordinary ISO 9660 files; nothing nests. Binary files are
**big-endian** (except `COVERAGE/AUC.BMP`, which is a standard little-endian Windows
BMP). Text files are 7-bit ASCII with `;`-terminated statements. Layer boundaries: file
inventory and container/volume layer are in `disc-layout.md`; the PDMDH coverage box
and grid are in `parcel-management.md`; the disc stamp as an ext-frame MID is in
`route-planning.md`.

Seven files round-trip byte-identical (`parser/roundtrip_misc.py`,
`parser/tests/test_roundtrip_misc.py`): `SPEC.KWI`, `METADATA.KWI`, `VERSION.TXT`,
`COUNTRY.KWI`, `COVERAGE.BIN`, `DN/CLUSTER.DAT`, `PCT2MNG.KWI`. Those tests read R at
`/run/media/codyh/464210-8480` and skip when it is not mounted, so "verified" here
means verified whenever R is present. Round-trip proves the parser keeps every byte; it
does not prove the meaning of a field. Where a field is carried verbatim, it is marked
`unknown`. Files not round-tripped (`LOADING.KWI`, `COVERAGE/AUC.BMP`, the K/D image
files, `DICVCE56.KWI`) are copy-through (`docs/design/target-disc.md`, WP5); the
`misc.py` header decoders for them are unexercised by any test.

Spec Ch.13 defines metadata as BNF with keywords `DMHT`, `RBPM`, `MBDF`, `ROOT`, `LANG`,
`CHCD`, `SPDL`, `MDIA`, `SUBD`. R uses only `LANG`, `CHCD`, `COOR`; `COOR` and
`SUPERMETA` are not in the Ch.13 we hold (spec ch.13 examples are Japanese-market).

## METADATA.KWI (164 bytes, Ch.13 BNF)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| whole file | `KEY::=value ;` statements, ASCII, no NUL/newline; raw text between `;` kept verbatim (whitespace is irregular: no space before `::=` on `LANG`/`COOR`, spaces on `CHCD`) | verified | `parser/roundtrip_misc.py` `check_metadata_kwi` asserts byte identity; `parser/tests/test_roundtrip_misc.py` | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| `LANG` | Comma-separated language names, 13 on R: US English, UK English, German, French, Spanish, Italian, Dutch, Swedish, Danish, Portuguese, Norwegian, Finish (sic), Australian English | observed | R read 2026-09; spec ch.13.2.6 defines `LANG` with English general names, examples list is different (Japanese, English...), so R's names are not from the spec list | `parser/kiwiw/misc.py` |
| `CHCD` | Character code: `ISO 8859-1` | observed | R; spec ch.13.2.7 allows `ISO`/`SJIS`/`ANSI`... as bare tokens, R's `ISO 8859-1` extends that form | `parser/kiwiw/misc.py` |
| `COOR` | Coordinate datum: `WGS84` | observed | R; keyword absent from spec ch.13 | `parser/kiwiw/misc.py` |
| Language order vs `COUNTRY.KWI` | The 13 `LANG` entries correspond 1:1, in order, to the 13 language codes in `COUNTRY.KWI` | observed | R comparison, no test | `parser/kiwiw/misc.py` |
| `ROOT`, `SPDL`, `DMHT`, `RBPM`, `MBDF`, `MDIA`, `SUBD` | Other Ch.13 statements (road class codes, speed limit bins, frame lists, media options, subdirectories) | spec-only | spec ch.13.2.1-13.2.10; not present in R's METADATA.KWI | - |
| Trailing bytes | File ends after the last `;` with no newline | observed | R, 164 bytes | `parser/kiwiw/misc_writer.py` |

## SPEC.KWI (34 bytes) and VERSION.TXT (19 bytes)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| SPEC.KWI whole file | `SUPERMETA::=AFAU:2.64, AGAU:2.64 ;` BNF-style statement, raw text kept | verified | `parser/roundtrip_misc.py` `check_spec_kwi`; `parser/tests/test_roundtrip_misc.py` | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| `SUPERMETA` value | List of `<code>:<version>` pairs; `AFAU`/`AGAU` presumed data-set identifiers (Australia) with version 2.64 | unknown | Tokens read from R; not in spec ch.13; meaning of `AFAU`/`AGAU`/`2.64` never established, and whether the head unit enforces them is untested | `parser/kiwiw/misc.py` |
| VERSION.TXT whole file | `COMMENT=2007 ver.1;` (single `KEY=value;`) | verified | `parser/roundtrip_misc.py` `check_version_txt` (round-trips only because the file has one statement; the writer is lossy in general) | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| `COMMENT` | Free-text edition label | observed | R | `parser/kiwiw/misc.py` |

## COUNTRY.KWI (113 bytes)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u8 `version_or_count` | 0x01 on R; meaning not established | unknown | R value 0x01; carried verbatim | `parser/kiwiw/misc.py` |
| 1 u8 `num_language_codes` | 0x0d = 13 = number of `LANG` entries in METADATA.KWI | observed | R; equals METADATA `LANG` count, no test asserts equality | `parser/kiwiw/misc.py` |
| 2 `#` then codes | `#` + concatenated 2-3 char codes with no separators: `us eng ger fre spa ita dut swe dan por nor fin` | verified | round-trip byte identity: `parser/tests/test_roundtrip_misc.py::test_country_kwi_byte_identical` (parser only splits with a hard-coded code list, `_KNOWN_LANG_CODES`, a guess for other discs) | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| second `#` + `au` | Last code (Australian English) after a second `#` | verified | `parser/tests/test_roundtrip_misc.py::test_country_kwi_byte_identical` | `parser/kiwiw/misc.py` |
| `country_id` u8 | 0x12 on R, follows the last code; meaning unknown | unknown | R value 0x12; carried in dataclass field | `parser/kiwiw/misc.py` |
| ISO code | NUL-terminated lowercase alpha-3 `aus` | verified | `parser/tests/test_roundtrip_misc.py::test_country_kwi_byte_identical`; ISO 3166-1 alpha-3 reading is an inference (n=1) | `parser/kiwiw/misc.py` |
| Tail (65 bytes after `aus\0`) | Repeating `00 00 01 2d` groups (10x, `-` placeholder) and two `00 00 05 "AUSTRALIA"` groups; TLV reading is a hypothesis | unknown | Carried verbatim in `raw_tail`; `name_records` parse is lossy and not used by the writer; spec ch.13 gives no grammar (country codes explicitly exempt from ISO, ch.13.1(2)) | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |

## COVERAGE.BIN (21 bytes) and COVERAGE/AUC.BMP

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u16 `count` | 0x0001, presumed number of coverage entries | unknown | R value; presumption only | `parser/kiwiw/misc.py` |
| 2 u16 `unknown` | 0x0012 (18); meaning not established (same value as COUNTRY `country_id` 0x12, possibly the same country/region id) | unknown | R value; coincidence with COUNTRY.KWI byte is an observation, not tested | `parser/kiwiw/misc.py` |
| 4 u8 path length + path | Length-prefixed DOS path `COVERAGE\AUC.BMP` (16 bytes) | verified | `parser/tests/test_roundtrip_misc.py::test_coverage_bin_byte_identical`; length byte equals path length on R | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| `COVERAGE/AUC.BMP` | Standard Windows BMP, `BM`, 40-byte DIB header, 176x168, 8 bpp palette, uncompressed, 30648 bytes, pixel data at 1078 | observed | R header read with `parse_bmp_header` (spot-check 2026-09); no test, file is copied not regenerated | `parser/kiwiw/misc.py` |
| Bitmap content vs. coverage bounds | The bitmap presumably draws the covered area (Australia); its relation to the PDMDH coverage box is not measured | unknown | Not decoded; `docs/design/target-disc.md` WP5 says regenerate only if coverage changes | - |
| Coverage box (lat -50.0 .. +35.333, lon E90 .. W142 crossing 180) | Numerical coverage bounds used by the map layer, from the PDMDH, not from these files | verified | `parser/refdata/grid.json` `coverage`; `parser/tests/test_grid_data.py` asserts values against R; see `parcel-management.md` | `parser/kiwiw/grid.py` |

## DN/CLUSTER.DAT (272 bytes)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 14 x u16 header (28 bytes) | R words: `14, 0, 0x0f67, 0x8800, 0x3c47, 0x2200, 0x0300, 0x0722, 0, 61, 0, 14, 0, 122` | verified | byte-identical round-trip `parser/tests/test_roundtrip_misc.py::test_cluster_dat_byte_identical` (header words are held as-is) | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| words 2..7 (bytes 4..15) | 12-byte disc stamp, see below | observed | Cross-file match measured on R | `parser/kiwiw/misc.py` |
| word 9 = 61 | Equals the number of pairs; not named in `misc.py` (parser uses word 13) | observed | R value 61 = pair count | - |
| word 13 = 122 | Count of u16 words after the header (2 x pairs) | observed | Arithmetic against file size 272 = 28 + 61*4 | `parser/kiwiw/misc.py` |
| words 0 and 11 = 14 | Equal to header word count; repeated field or coincidence | unknown | R values only | - |
| 61 x (u16 key, u16 value) | Sparse-ID to dense-index remap; keys form three runs (134..146, 166..191, 250..271), values 3..58 unordered; which side is the cluster id is inferred | unknown | Round-trip proves bytes only; semantics inferred from Phase 0 "cluster index" hypothesis, no consumer traced. WP5 lists "cluster index rules", which do not exist yet | `parser/kiwiw/misc.py` |

## Disc stamp (12 bytes `0f 67 88 00 3c 47 22 00 03 00 07 22`)

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Presence in files | Verbatim at file offset 0 of `KGRA256.KWI`, `KPCT256.KWI`, `KPCT2DT.KWI`, `KGRPDAT.KWI`, `DICVCE56.KWI`; offset 4 of `VAR256D.KWI`; offset 4 of `DN/CLUSTER.DAT` | observed | R `xxd` spot-check 2026-09 of all seven; no test asserts the cross-file match | `parser/kiwiw/misc.py` (`DISC_STAMP_12B`) |
| Presence in ALLDATA | Same 12 bytes used as User Classification ID (MID) of route-planning ext frames | observed | `parser/analyze_ext_frames.py` counts matches against R; generator emits it via `parser/osm_to_route_planning.py`; see `route-planning.md` | `parser/kiwiw/misc.py` |
| Meaning | Edition/build fingerprint stamped by the authoring tool; not a decodable date or checksum | unknown | No decoding found; head-unit acceptance of a different stamp untested | - |
| Bytes following the stamp | Differ per file (`af55 0500 002a` in KGRA256/KPCT256, zeros in KPCT2DT/KGRPDAT, `0021 6594 0000 001a` in DICVCE56, `0012 0100` in VAR256D) | unknown | R; not decoded; the K/D files are copied whole so not needed | - |

## PCT2MNG.KWI (174 bytes) image manifest

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| 0 u16 `num_groups` | 3 on R | verified | round-trip `parser/tests/test_roundtrip_misc.py::test_pct2mng_byte_identical` | `parser/kiwiw/misc.py`, `parser/kiwiw/misc_writer.py` |
| 2 u16 `filename_field_width` | 12 | verified | `parser/tests/test_roundtrip_misc.py::test_pct2mng_byte_identical` | `parser/kiwiw/misc.py` |
| 4 u16 `num_records` | 7 | verified | `parser/tests/test_roundtrip_misc.py::test_pct2mng_byte_identical` | `parser/kiwiw/misc.py` |
| record (24 B) `group_id` u32 | Family id: 1 (PCT2DAT/KPCT2DT), 10 (GRA256D/KGRA256/VAR256D), 11 (PCT256D/KPCT256) | verified | `parser/tests/test_roundtrip_misc.py::test_pct2mng_byte_identical`; family reading matches file names on R | `parser/kiwiw/misc.py` |
| record `role` u16 | 0 = D data file, 2 = K index file, 1 = VAR256D variant | observed | R values; role-name semantics are inferred from the file-name pairing | `parser/kiwiw/misc.py` |
| record `reserved` u32 | Always 0 on R; writer always emits 0 (not retained in the dataclass) | verified | `parser/tests/test_roundtrip_misc.py::test_pct2mng_byte_identical` passes only because R has 0 | `parser/kiwiw/misc_writer.py` |
| record `variant` u16 | 2 for the six paired files, 4 for VAR256D | unknown | R values; meaning not established | `parser/kiwiw/misc.py` |
| record filename 12 B | NUL-padded ASCII | verified | `parser/tests/test_roundtrip_misc.py::test_pct2mng_byte_identical` | `parser/kiwiw/misc.py` |

## LOADING.KWI and other copy-through files

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| `LOADING.KWI` 0 u16 systems, 2 u16 reserved | Number of accommodated systems (1) and reserved 0 | observed | R read via `parse_loading_header`; layout from spec ch.30.1/30.2 (Ch.30 not in the chapter list we hold beyond that header) | `parser/kiwiw/misc.py` |
| `LOADING.KWI` system record (16 B at offset 4) | 12 B manufacturer ID `DENSO` NUL padded, u16 modules (1), u16 reserved | observed | R read (spot-check 2026-09); spec ch.30.2 | `parser/kiwiw/misc.py` |
| `LOADING.KWI` module id/management/code | ASCII `KH07` seen after the header; 31,338,496-byte file is otherwise an opaque head-unit payload | unknown | Not decoded; copied whole | - |
| `GRA256D`, `PCT256D`, `PCT2DAT`, `VAR256D` (D files) and `KGRA256`, `KPCT256`, `KPCT2DT`, `KGRPDAT` (K files), `DICVCE56`, `HWMAP` | Image/tile/voice data and their indexes; content-independent so copied | unknown | Sizes and stamp headers seen on R; internal structure not decoded (`HWMAP.KWI` is WP4 and may be map-dependent, see `docs/design/target-disc.md`) | - |
| Disc stamp effect on copied files | Copied files carry R's stamp; a generated disc built with a different stamp would mismatch them | assumed | We build with R's stamp unchanged; no test | `parser/kiwiw/misc.py` |

## ALLDATA management header record 29 (`parser/refdata/mht29_frame.bin`, 2048 bytes)

The record is spec Ch.5.2 record 30 (0-based 29), RESERVED, extended part 1 (see
`disc-layout.md`), sitting at ALLDATA offset 4096..6144. It is copied through
verbatim into every generated disc and never regenerated. Because it is carried
verbatim, every field below is unknown except where R bytes are quoted.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Whole 2048 B | Manufacturer-defined language/country code list, copy-through | verified | Generated frame equals the refdata bytes: `parser/tests/test_alldata_writer.py::test_mht29_copy_through`, `parser/harness/checks/shape.py` check `mht29`, `parser/tests/test_grid_data.py` (equals R's frame on disc) | `parser/kiwiw/alldata_writer.py`, `parser/kiwiw/grid.py` |
| 0x00..0x03 | `01 35 01 01`: leading header bytes | unknown | R bytes; not decoded | - |
| 0x04..0x0f | `8f 81 08 00 41 88 88 00 00 00 01 40`: fixed run recurring at 0x44 (`8f81 0800 4188 8800 0000 01`); differs from the 12-byte disc stamp | unknown | R bytes; recurrence measured, meaning unknown | - |
| 0x10..0x3f | `01 01 0d # us eng ger fre spa ita dut swe dan por nor fin # au 12 aus 00`, i.e. the COUNTRY.KWI head (13 codes, id 0x12, `aus`) | observed | Byte comparison with `COUNTRY.KWI` head; identical code text, so the two are the same list in two containers; no test asserts it | - |
| 0x40..0x4f | Second block `01 01 8f81 0800 4188 8800 0000 01 23 au` then zero fill to ~0x7a | unknown | R bytes | - |
| ~0x7a..0x7ff | Table of short records beginning `00 06 00 52 00 41 43 01 43 01 ...` (reads as repeating 3-word groups of `4x xx` values with small tags); zero fill to the end | unknown | R bytes only; no decoding attempted; could be a character range or code-mapping table | - |

## Parameters frames (spec Ch.12)

The spec defines a Parameters Distribution Header (header size u16, count u16, pointer
table of 20-byte entries: 12 B MID all-`ff`, 4 B classification `001201`/`001202`/
`001203`, u16 offset, u16 size) and Drawing, 3-D Symbol and Route Number
Display-frame data frames. This project has not located or decoded such frames on R;
the management header entry for parameters is not modelled by the small-file code.

| Field | Meaning | Status | Evidence | Code |
|---|---|---|---|---|
| Parameters Distribution Header | Header size u16, count u16, pointer table, management list | spec-only | spec ch.12.1 | - |
| Pointer entry (20 B) | MID 12 B (`ff`*12), classification code (0x001201 drawing, 0x001202 3-D symbol, 0x001203 route number frame), offset u16, size u16 | spec-only | spec ch.12.1.1.1 | - |
| Drawing parameter mgmt record | u32 offset, u32 size, flag byte (bit7 line-style palette, bit6 map-element drawing params), 3 reserved | spec-only | spec ch.12.1.2.1 | - |
| 3-D symbol / route number mgmt record | u32 offset, u32 size | spec-only | spec ch.12.1.2.2, 12.1.2.3 | - |
| Presence on R and in the disc writer | Whether R's ALLDATA has a parameters entity and whether G omits or copies it | unknown | No decode in `parser/` or notebook; see `disc-layout.md` for management header entries | - |

## Open questions

1. `COUNTRY.KWI` tail grammar, `version_or_count`, `country_id`, and their relation to
   `COVERAGE.BIN` word 2 (both 0x12): n=1 disc, no way to separate hypotheses.
2. `DN/CLUSTER.DAT` key/value semantics and whether the head unit requires it to match
   the map content; WP5 "cluster index rules" are not yet defined.
3. Whether the head unit checks the 12-byte disc stamp against ALLDATA ext-frame MIDs,
   and what the bytes mean; determines whether stamp can change on G.
4. `mht29_frame.bin` internal structure beyond the language-list text; carried verbatim
   and never regenerated.
5. `SUPERMETA` tokens `AFAU`/`AGAU`/`2.64`, and whether the head unit reads
   `SPEC.KWI`/`METADATA.KWI` at all.
6. `COVERAGE/AUC.BMP` content vs. PDMDH coverage box; whether the bitmap needs redrawing.
7. Ch.12 parameters frames: is there a parameters entity on R, and if so where.
8. `PCT2MNG.KWI` `variant` values 2 vs 4.
9. Ch.13 keywords `ROOT`/`SPDL`/etc. are absent from R's METADATA.KWI; whether the unit
   would honour them is untested.
