# Phase 1 — Format analysis

## Goal

A full, lossless parser for every file type on the disc, backed by a written
reference doc mapping each file to its KIWI-W spec chapter, plus the disc's actual
mesh/tile hierarchy (block-set -> block -> parcel -> subparcel: lat/lon divisions,
scale levels). Deliverable is a parser library (Python) that can losslessly parse
every `.KWI`/`.IDX`/`.BIN` file into an intermediate structured representation
(e.g. JSON-serializable dicts/dataclasses), plus a dump/diff CLI tool, living under
`parser/`.

Inputs available: full archived spec at `spec/format_english/pdf/*.pdf` (see
`spec/INDEX.md`), `kiwiread`'s validated C parsing logic at `tools/kiwiread/`
(builds and correctly decodes this disc's header + mesh/tile hierarchy + a real
parcel — see `docs/phases/00-inventory.md` "Findings"), and the file catalogue with
best-guess purposes also in `docs/phases/00-inventory.md`.

## Sub-tasks (parallelized across subagents)

1. **Main map data frame (Ch. 5, 6, 7)** — port/extend `kiwiread`'s validated
   struct-level parsing of `ALLDATA.KWI` (MHR/LMR/BSMR tables, block/parcel
   hierarchy, road multilink/polyline geometry, background/name frames) into a
   Python parser producing a full intermediate representation, going beyond what
   `kiwiread` currently decodes (it renders to SVG but doesn't expose/dump every
   field). Cross-reference field-level layouts against the Ch. 7 sub-section PDFs
   (7.1-7.5, 7.A) for anything `kiwiread` doesn't already handle.
2. **Index/search data frames (Ch. 11)** — decode `INDEXDAT.KWI` and every file
   under `IDX/`, using the Ch. 11 sub-section PDFs (`spec/format_english/pdf/11*.pdf`)
   to confirm what each filename prefix (`SADSR*`, `POISR*`/`POIDT*`/`POIAS*`,
   `FWYSR*`, `ITSSR*`, `ZONE*`/`ZSEL*`, `AGMSR*`/`ARGSR*`/`ARSNC*`/`ARSSR*`,
   `EMGSR*`/`EM2SR`/`EM3SR`, `FMCDT001`) actually is and how it's structured. This
   is required for the "full parity" address-search and POI-search goal, and these
   are the largest files on the disc after `ALLDATA.KWI` (`POISR205/206.IDX` alone
   are ~177MB/132MB).
3. **Small metadata/coverage/loading/image files** — decode `COUNTRY.KWI`,
   `SPEC.KWI`, `METADATA.KWI`, `COVERAGE.BIN`, `COVERAGE/AUC.BMP`, `DN/CLUSTER.DAT`,
   `VERSION.TXT` (Ch. 2, 3, 4, 13), `LOADING.KWI` (Ch. 30), and the image/tile file
   pairs `GRA256D.KWI`+`KGRA256.KWI`, `PCT256D.KWI`+`KPCT256.KWI`,
   `PCT2DAT.KWI`+`KPCT2DT.KWI`+`PCT2MNG.KWI`, `KGRPDAT.KWI`, `VAR256D.KWI`,
   `HWMAP.KWI`, `DICVCE56.KWI` (Ch. 33/34, voice/image data). Lower priority than
   1/2 for the "roads first" incremental goal, but needed for full disc assembly
   later (Phase 4) even if most of this content ends up copied through unchanged.

## Findings

(filled in as each sub-task completes)

### Small metadata/coverage/loading/image files (sub-task 3, 2026-08-24)

Parser code: `parser/kiwiw/misc.py`. Verified against the actual mounted
disc at `/run/media/codyh/464210-8480/`. Confidence levels are called out
per-field in that module's docstrings; summary below.

**Fully decoded, high confidence:**

- **`SPEC.KWI`, `METADATA.KWI`, `VERSION.TXT`** — plain ASCII, Ch.13
  BNF-style `KEY::=value;` text (or `KEY=value;` for VERSION.TXT). No binary
  framing at all. `METADATA.KWI` confirms 13 languages, `CHCD=ISO 8859-1`,
  `COOR=WGS84`. `SPEC.KWI` = `SUPERMETA::=AFAU:2.64, AGAU:2.64`.
  `VERSION.TXT` = `COMMENT=2007 ver.1`.
- **`COVERAGE/AUC.BMP`** — standard Windows BMP (BITMAPFILEHEADER +
  40-byte BITMAPINFOHEADER), magic `BM`, file-size field matches actual size
  (30648 bytes), 176x168, 8bpp palette-indexed, uncompressed. No KIWI-specific
  handling needed; any standard BMP library round-trips it losslessly.
- **`COVERAGE.BIN`** (21 bytes) — `[u16][u16][u8 path_len][path]`. The
  path-length byte (0x10=16) exactly matches the length of the path string
  that follows (`COVERAGE\AUC.BMP`), confirming the `[len][path]` framing.
  The two leading 16-bit fields (0x0001, 0x0012) are *not* confirmed —
  plausible guesses are "number of coverage entries" and an unknown
  size/id field, respectively.
- **`PCT2MNG.KWI`** (174 bytes) — a manifest of every image/tile file on the
  disc. Header `[num_groups=3][field_width=12][num_records=7]` (all `u16`),
  then 7 x 24-byte records `[group_id:u32][role:u16][reserved:u32=0]
  [variant:u16][filename:12B NUL-padded ASCII]`. This **directly confirms**
  Phase 0's "K-prefixed files are index/key tables paired with D data files"
  hypothesis: `group_id` ties families together (1 → PCT2DAT.KWI/KPCT2DT.KWI;
  0x0a → GRA256D.KWI/KGRA256.KWI/VAR256D.KWI; 0x0b → PCT256D.KWI/KPCT256.KWI),
  and `role` is 0 for the "D" data file, 2 for the "K" key/index file, 1 for
  VAR256D.KWI (a same-family variant with no index partner of its own).
- **`LOADING.KWI` top-level header (Ch. 30)** — byte-for-byte match against
  the archived Ch.30.1/30.2 field tables: `[num_systems:u16=1][reserved:u16]`
  then one 16-byte System Identification Information record:
  `[Manufacturer Identifier: 12B ASCII="DENSO"][num_modules:u16=1][reserved:u16]`.
  Confirms **LOADING.KWI is a DENSO-supplied loading-module/firmware blob**
  (module id readable as ASCII `"KH07"`, a `"1000"`-looking version string
  nearby), not map content. The ~31MB Module Code payload itself was *not*
  decoded further (opaque, high-entropy-looking binary/firmware) — this
  wasn't judged worth pursuing since it's a head-unit resource blob with no
  OSM equivalent to regenerate from.
- **Cross-file "disc stamp" (new, unexpected finding)** — a 12-byte sequence
  (`0f 67 88 00 3c 47 22 00 03 00 07 22`) recurs byte-identically as a header
  prefix in `DN/CLUSTER.DAT` (at word offset 2), `KGRA256.KWI`,
  `KPCT256.KWI`, `KPCT2DT.KWI`, `KGRPDAT.KWI`, `DICVCE56.KWI` (all at file
  offset 0), and `VAR256D.KWI` (at file offset 4). Exposed as
  `kiwiw.misc.DISC_STAMP_12B`. Read as a disc-build/edition fingerprint
  stamped into many auxiliary files by the authoring tool; semantics of the
  12 bytes themselves are not decoded (not an obvious date/checksum we could
  confirm) but the cross-file match itself is solid (not a guess).

**Decoded with caveats (byte-pattern-matched, not spec-confirmed):**

- **`COUNTRY.KWI`** (113 bytes) — the archived Ch.13 text explicitly says
  country-selection codes are carved out of the ISO character-exchange rules
  it otherwise documents, and gives no byte-level grammar for a file like
  this in the chapters we have (n=1 disc sample, so no cross-check
  possible). What's solid: byte[1]=0x0d=13 is a count of language codes that
  follow, and those codes — `us,eng,ger,fre,spa,ita,dut,swe,dan,por,nor,fin`
  (concatenated, no separators, reconstructed exactly from the raw bytes) +
  `au` (after a second `#` delimiter) — correspond 1:1, in order, to
  METADATA.KWI's 13-language list. After that, a country-id byte (0x12) and
  NUL-terminated ISO-3166-1-alpha-3 code (`aus`) are unambiguous. The
  trailing ~65 bytes look like repeating TLV records (tag 0x01 = 1-byte
  payload, always `0x2d` / `-`, seen 10x, plausibly "no translated name for
  this language slot"; tag 0x00 + length-like byte 0x05 preceding a 9-byte
  ASCII "AUSTRALIA", seen 2x) but this is offered as a hypothesis only, not
  a confirmed grammar.
- **`DN/CLUSTER.DAT`** (272 bytes) — 14 big-endian 16-bit header words (28
  bytes) followed by a flat array of 61 `(key, value)` 16-bit pairs.
  CONFIRMED arithmetically: header word[13] (=122) equals the count of
  16-bit words remaining after the header (61 pairs x 2). The keys form 3
  contiguous runs (134-146, 166-191, 250-271 on this disc) each mapped to a
  small, shuffled-looking integer (roughly 3-58, not in key order) —
  consistent with Phase 0's "cluster index" guess (a sparse-ID ->
  dense-index remapping table), but which side is the "cluster ID" and which
  is the "remapped index" is inferred, not confirmed. header words[0] and
  [11] are both 14 — possibly the same field in two nested sub-headers, or
  coincidence; not resolved.

**Characterized only (stretch goal, not attempted further):**

- **`GRA256D.KWI`/`PCT256D.KWI`/`PCT2DAT.KWI` (+ their `K*` index files) and
  `VAR256D.KWI`, `KGRPDAT.KWI`, `HWMAP.KWI`, `DICVCE56.KWI`** — Ch.33 (Image
  Data Frame: Image Management Distribution Header → Palette Set → Color
  Table → Image Data → Image Service Info) and Ch.34 (Voice Data Frame:
  Voice Distribution Header → boundary-adjustment padding → general-purpose
  voice data → "proper" voice data for place names) confirm the *expected
  shape* of these files matches their filenames' implications (raster
  tile/UI-graphics data for the `*256*` family, voice-prompt audio including
  place-name snippets for `DICVCE56.KWI`), and `PCT2MNG.KWI` (above) confirms
  the D/K pairing structurally. Full field-level decode of the image pixel
  data / voice codec frames was not attempted (explicitly a stretch goal per
  task brief). `HWMAP.KWI` was only size/header-sniffed, not decoded.

**Recommendation for Phase 4 (disc assembly):**

- **Copy through unchanged, high confidence:** `COVERAGE/AUC.BMP`,
  `LOADING.KWI` (firmware/UI resource blob, no map-content dependency),
  `DICVCE56.KWI` (voice prompts — OSM has no equivalent to regenerate from),
  and almost certainly all of `GRA256D.KWI`/`KGRA256.KWI`/`PCT256D.KWI`/
  `KPCT256.KWI`/`PCT2DAT.KWI`/`KPCT2DT.KWI`/`PCT2MNG.KWI`/`KGRPDAT.KWI`/
  `VAR256D.KWI`/`HWMAP.KWI` (UI chrome/graphics, not map data).
- **Will need regeneration (small, structured, disc-identity-dependent):**
  `COUNTRY.KWI`, `SPEC.KWI`, `METADATA.KWI`, `COVERAGE.BIN`,
  `DN/CLUSTER.DAT`, `VERSION.TXT` — all tiny and all reference/derive from
  disc-specific facts (country, coverage-bitmap path, version string, and
  possibly the disc-stamp/cluster-index data whose regeneration rule is
  still unconfirmed). These are cheap to regenerate once Phase 4 knows the
  final coverage area and version metadata, but `DN/CLUSTER.DAT`'s cluster
  index and the cross-file "disc stamp" bytes need their generation logic
  understood first if we don't want to just copy the original's placeholder
  values through (which may or may not be safe if the firmware validates
  them against the actual disc content).

### Main map data frame parser (sub-task 1, 2026-08-24/25)

Parser code: `parser/kiwiw/` (package: `bitutils.py`, `model.py`, `volume.py`,
`mesh.py`, `road.py`, `background.py`, `name.py`, `parcel.py`, `disc.py`,
`roadtypes.py`, `coordconv.py`), CLI: `parser/dump_parcel.py`, integration
tests: `parser/tests/test_mesh.py`. Ported/extended from `tools/kiwiread/kiwiread.c`
(read in full, both halves), cross-referenced against `spec/format_english/pdf/0500122e.pdf`
(Ch.5 Data Volume, field-for-field byte-offset match confirmed) and
`0600122e.pdf` (Ch.6 PDMDH/LMR, byte-offset match confirmed).

**Works end-to-end on the real disc.** `dump_parcel.py --alldata
/run/media/codyh/464210-8480/ALLDATA.KWI --lat <LAT> --lon <LON> --level 0`
locates and fully decodes a real parcel to JSON. Header parse reproduces
Phase 0's exact values (`FORMAT VERSION KIWI01-22-00`, `DATA VERSION
07/12/21/01`, box S50/E90 to N35.33/W142, 7 levels 12..0). Tested against
3 real Australian coordinates:
- **Melbourne** (-37.813629, 144.963058): parcel bbox
  `[-37.833333,144.9375]` to `[-37.8125,144.96875]` -- **matches
  kiwiread.c's independently-validated ground truth exactly** (see Phase 0
  findings) after fixing a bug described below. Decoded 29 road links, 14
  background shapes (mostly `0x123` "river", plausible for this rural
  parcel), 97 name records including real local road names ("BOUNDARY
  ROAD", "CHAMBERLAIN ROAD", "OLD HEATHCOTE ROAD" -- genuine central-Victoria
  road names, consistent with Phase 0's "DOVE RIVER CONSERVATION" find at
  the same spot).
- **Sydney Harbour** (-33.868820, 151.209290): correctly resolves to a
  mostly-water parcel, name records include "TASMAN SEA" -- no roads,
  which is geographically sane for that exact point.
- **Regional NSW** (-33.8148, 151.0011, near the Hunter Valley/Yengo NP):
  13 road links, 40 name records including "YENGO NATIONAL PARK" and
  "POKOLBIN STATE FOREST" -- both genuine real places at that location, a
  strong end-to-end sanity check that coordinate decoding, name-string
  decoding, and mesh location are all self-consistent.

**Bug found and fixed while porting (own bug, not kiwiread.c's):** the C
`lmr_t` struct's `nblocksets`/`nblocks` sub-structs are declared
`{uint8_t lat; uint8_t lng;}` (lat byte first). My first pass read them in
the opposite order, which silently produced a valid-looking but wrong
grid (square-ish but 2x too coarse in longitude) -- parcel lookups still
"worked" (no crash, plausible-looking bbox) but were wrong by a factor of
2 in one axis. Caught by cross-checking computed grid dimensions against
kiwiread's known-good Melbourne bbox to 6 decimal places; after the fix
lat span matched exactly (0.020833deg) and the lon span/offset matched
exactly too. This is a strong argument for the test in
`parser/tests/test_mesh.py` staying in the suite going forward -- byte
order bugs like this are easy to reintroduce and don't fail loudly.

**Mesh locator (`mesh.py`) is a rewrite, not a port**, per the Phase 0
recommendation: computes the target (blockset, block, parcel) indices
analytically via floor-division of the coordinate delta (handling the
antimeridian wraparound explicitly, `_lon_span()`/`_lon_delta()`), then
reads only the specific BSMR/BMT/parcel-management entries needed, rather
than kiwiread's brute-force scan-and-global-state approach. It also
generalizes kiwiread's fixed-depth-2 "divided/integrated parcel" (pardiv)
recursion into an arbitrary-depth loop that re-reads each level's own
`parman_t.type` field to decide the next subdivision grid -- at the time
this section was first written no test coordinate had exercised depth > 1;
this has since been exercised on real data (Melbourne resolves into a real
divided sub-parcel post-fix) as part of the parcel-index bug fix below, see
"Parcel iteration-order bug: ROOT CAUSE FOUND AND FIXED". Note the
resulting (blockset_index, block_index, parcel_index) numbers in my output
do **not** match kiwiread's printed indices for the same Melbourne parcel
(38/14/1946 vs. kiwiread's 22/23/542) -- only the geographic bbox and
underlying sector address should be expected to agree; kiwiread's own flat
indices come from a debug-only helper (`divbsmr()`) whose bookkeeping isn't
necessarily consistent with the on-disc layout either (see the fix-up note
below), so this mismatch is expected and not itself evidence of a bug.

> **UPDATE (2026-08-25):** the "unconfirmed iteration-order assumption
> (row-major lat-then-lng)" this paragraph originally flagged here has
> since been **checked against the archived spec text and confirmed
> correct** -- see "Parcel iteration-order bug: ROOT CAUSE FOUND AND FIXED"
> further down this document. The spec (`0600122e.pdf`, Ch. 6.1.2/6.2.1/
> 6.3.1) explicitly states row-major, latitude-outer/longitude-inner
> ordering at every level, exactly matching what this module already
> computed for `bset_flat`/`block_flat`. A real bug *was* found and fixed
> in this module, but it was a redundant fractional-recomputation of the
> parcel array index (double-applying a subdivision factor already folded
> into the outer grid indices) -- not an ordering/axis mistake. See that
> section for the full root cause, fix, and validation (799/800 agreement
> across 800 real, independently-oracle-verified WA coordinates).

**Confidence levels / open uncertainty, called out in module docstrings:**
- `volume.py`, Ch.5/6 struct layouts: **high** -- byte-for-byte matches
  the spec PDF tables directly (see `0500122e.pdf`/`0600122e.pdf`).
- `road.py` bitfield layout: **high** for structure (matches kiwiread.c's
  spec-section-cited comments and decodes real toll/tunnel/bridge/oneway
  flags without garbage values), **low** for the human-readable
  `road_type` code labels (`roadtypes.py`) -- the Ch.7.A "Road Type"
  appendix PDF (`07A1122e.pdf` section 7.A.1) has a header but **no
  extractable table content** via `pdftotext` (possibly an image, possibly
  genuinely blank in this spec revision -- 7.A.2/7.A.3 are explicitly
  marked "(added in future)" but 7.A.1 has no such marker either). Real
  parcels contain road_type codes beyond the 0/3/4/5/6/7 set kiwiread.c
  assigns colors to (e.g. code 9 seen in both Melbourne and Hunter Valley
  parcels) with no name at all -- genuinely unknown, not just unconfirmed.
- `background.py`/`name.py` type-code table (`BACKGROUND_TYPE_CODES`):
  **medium** -- transcribed directly from kiwiread.c's `types[]` table,
  which reads like a real spec code table (e.g. water/address-level/park
  codes line up with what actually renders), but not independently
  cross-checked against a Ch.7.3 PDF code-table page in this pass.
- `coordconv.py` (parcel-local pixel -> lat/lon): **medium** -- the two
  BackgroundFrame conversion here derives the coordinate encoding as the
  standard 13-bit-value + 3-bit-region combination (`extract(v,0,12) +
  region*4096`) reaching a magnitude of ~2^15, mapped linearly across the
  small leaf-parcel bbox `mesh.py` resolves. This is inferred (not
  spec-confirmed) from Phase 0's observation that kiwiread.c's rendered
  background polygons sometimes land thousands of pixels outside its
  nominal 4096x4096 canvas -- consistent with the true range being ~2^15,
  not 2^12/2^13. Decoded road/background/name coordinates for all 3 test
  parcels land inside (or very near) their parcel's own bbox, which is
  the sanity check available; north/south axis direction (does raw `y`
  increase toward the parcel's northern or southern edge?) is an
  unverified assumption and would only affect within-parcel mirroring,
  not gross placement.
- `n_intersections` in `RoadFrame` was seen as `65535` (0xFFFF) on a real
  parcel -- likely a "not applicable"/sentinel value rather than a literal
  count of 65535 intersections, not confirmed either way.
- Name Data Frame string types 0/2/3/7 (whatever isn't 1/4/5/6) are
  **not decoded** -- kiwiread.c itself `exit()`s on encountering one; this
  port instead stops that one name-list early and emits an
  `UNHANDLED string_type=N` placeholder record so one bad record doesn't
  lose the rest of the parcel. Not hit on any of the 3 test coordinates,
  so unverified whether/how often it occurs elsewhere.
- Additional Data records in the road frame (7.2, `[m]` count) and the
  Data Extended region-list bytes before the mfde table in `parcel.py`
  are skipped-past (offsets respected) but never decoded -- kiwiread.c
  doesn't decode them either.
- **Not implemented at all:** file-based parcel management records
  (`bmtfile_t`, i.e. a parcel-management table referenced by filename
  rather than inline sector address) -- `disc.py` raises
  `NotImplementedError` if the top-level PDMDH-bearing MHR entry has a
  filename set; not encountered on this disc's record 1, so the AU disc
  doesn't exercise this path as far as we've tested, but other levels or
  discs might.

**Implication for Phase 2 (round-trip writer):** the container-level
understanding (volume header, LMR/BSMR/BMT/parcel-management tables, mesh
math) is now on solid, independently-cross-checked footing and directly
reusable/invertible for a writer. The biggest open risk for Phase 2 is the
**coordinate encoding uncertainty** in `coordconv.py` -- if we're wrong
about the exact numeric range/direction, a writer built on this
understanding will place geometry at the wrong relative position within a
parcel even if the parcel-selection/mesh math is right. Second risk: road
type codes are only ~50% identified (6 of the codes seen used), which
matters for Phase 3's OSM `highway=*` -> KIWI-W road-type mapping.

### Index/search data frame decoding (sub-task 2, 2026-08-24)

> **Partly superseded** by "Address / POI search chain: SOLVED
> end-to-end (2026-08-25)" below. The framing findings here hold, but
> every *resolved offset* quoted in this section is half its true value
> (see the additional-address halving bug), and its conclusions about
> what lives where -- the category tree, the alphabetical records, the
> undecodable coordinates -- are corrected there.

Parser code: `parser/kiwiw/index_data.py` (new submodule, fits the sibling
package's dataclass/docstring conventions from `bitutils.py`/`model.py`).
Cross-referenced against the archived Ch.11 sub-section PDFs
(`1101122e`/`1102122e`/`1103122e`/`1109122e`/`11A20{1,2,3,4,5,6,7,8}122e`/
`11A21{4,5}122e`). Tested against the real mounted disc at
`/run/media/codyh/464210-8480/`.

**Confirmed working end-to-end on real data (highest confidence):**

- **`INDEXDAT.KWI`** = Ch.11.2 Data Management Frame. Signature `DCTR`
  confirmed at offset 0. Fully decoded 96-byte header: format version
  string matches `SPEC.KWI`'s version exactly, BCD-encoded creation
  timestamp matches the disc's real file dates, and the 32-byte copyright
  field decodes to the literal ASCII string `DENSO CORPORATION` — three
  independent confirmations this struct layout is right. Also decodes the
  volume-management-record and POI-information-management-record
  count/size/offset fields (not yet cross-checked against actual record
  content, but the header itself is solid).
- **The 32-bit "SWS/D" halved-storage convention** (new finding, sibling
  to `bitutils.sws()`'s 16-bit version) — Chapter 11 "additional address"
  fields store `real_value / 2`, doubled on read, except the sentinel
  `0xFFFFFFFF` (32-bit all-ones) which means "field not present" and must
  be read as `None` rather than doubled. Exposed as `index_data.sws32()`.
  Confirmed by successfully resolving multiple different address fields
  in real `SRMX` records to valid, in-bounds, signature-matching targets
  only after applying this transform; naive absolute- or plain-relative-
  offset interpretations both failed.
- **The "Additional Address" (FNME-style) indirection mechanism** — a
  `DetailedSearchInfoRecord`'s (`SRMX`) address-looking fields are
  themselves halved, record-relative pointers into a small table entry:
  `[4-byte absolute file offset][2-byte word-count size][filename
  string]`. This was the hardest single discovery of this sub-task and is
  what unlocks every downstream sub-frame. Implemented as
  `index_data._resolve_additional_address()`.
- **`SADSR201.IDX`** (Street Address Search, Ch.11.A.2.4) — parses the
  `DFSR` management-frame header and the `SRMX` Detailed Search Info
  Record at offset 16 (all field offsets match the spec table exactly:
  keyboard-type string at +28, category-definition address at +16,
  category-data address at +24, matching-data-definition address at +60,
  matching-data-frame address at +68 with a size/count pair at +72/+76,
  next-level address at +88). Following the `next_level` pointer and
  scanning for length-prefixed printable-ASCII strings (`[1-byte
  length][ASCII]`) yields **real, alphabetically-sorted Western
  Australian street names** — e.g. `GINGIN ROAD` (a real WA town/road) —
  confirming both the indirection mechanism and the string convention
  simultaneously.
- **`POISR201.IDX`** (POI Search, Ch.11.A.2.8) — same `DFSR`/`SRMX`
  framing as SADSR (structurally confirms these two share the same
  top-level search-frame type, matching the spec's implication that POI
  and Street Address searches are both instances of the generic
  step-by-step search frame). Its `next_level` field is the
  `0xFFFFFFFF` sentinel (POI hybrid search has no next-level frame, unlike
  street address search — a real structural difference, not a bug).
  Falling back to `matching_data_frame` and scanning for length-prefixed
  strings yields **real Perth, WA business names and street addresses**
  — e.g. `BURSWOOD CAR RENTALS` (Burswood is a real Perth suburb) and `48
  FARRINGTON ROAD, PERTH, WESTERN AUSTRALIA` — a strong plausibility
  check on real Australian data.
- **Category/alphabetical index tree byte layout** — Parent Record = 7
  bytes (3-byte offset + 4-byte count, matches spec's stated "Category
  Parent Record Size=7"); Option Record = 4 bytes (1-byte char + 3-byte
  offset, matches "Category Option Record Size=4"). Found at the same
  structural location (via the field I initially expected to be
  "category data" but which actually resolves through the field labeled
  `matching_data_frame` — see caveat below) in both SADSR201 (offset
  117186) and POISR201 (offset 73330).

**Caveat — spec field *names* vs. actual content don't line up 1:1:**
the `SRMX` record's field positions match the Ch.11.A.2.4/2.8 spec tables
exactly (this part is solid), but which named frame-type is *actually*
stored behind each resolved address differs from a naive reading of the
field names. Concretely: the field at spec offset +24 ("Category Data
Frame Address") resolves, for SADSR201, to a target that is just
zero-padding/filename-table debris, not a category tree; the readable
alphabetical-index/category-tree bytes described above were instead found
via the field at offset +68 ("Matching Data Frame Address"), and the real
street/POI name strings were found via `next_level` (SADSR) /
`matching_data_frame` (POISR, since its own `next_level` is absent). This
is flagged honestly rather than smoothed over — the *addressing
mechanism* and *field byte-offsets* are confirmed, but the semantic
name-to-content mapping needs more disc samples (ideally a second disc,
or a deeper walk of the category tree itself) to nail down definitively.

**Structurally confirmed (real header signature bytes match a shared
inner-record "declaration" pair across a filename family), but full
record layout NOT decoded** — obtained by reading the first 32 bytes of
one representative file per remaining prefix and comparing the 4-char
top-level declaration + inner search-type tag against the spec PDFs:

| Prefix family | Header signature | Ch.11 mapping | Confidence |
|---|---|---|---|
| `FWYSR201` | `DFSR` / `SRFW` | 11.A.2.7 Freeway Search | Structural (signature confirmed; record body not decoded) |
| `ITSSR201` | `DFSR` / `SRBT` | Intersection Search (exact 11.A.2.x sub-number not pinned down) | Structural |
| `FMCDT001` | `DFM2` / `SRBT` | Shares inner `SRBT` tag with ITSSR but a **different** top-level declaration (`DFM2` vs `DFSR`) — likely a generic B-tree/telephone-style lookup mechanism reused for unrelated content, not the same search type as ITSSR | Weak/best-guess — signature overlap noted, relationship NOT resolved |
| `AGMSR*`, `ARGSR*`, `EMGSR*` | `DFSR` / `SRAG` | Genre/category search family (11.A.2.5-like) — all three share byte-identical inner framing, strongly suggesting they're the Automobile/Area/Emergency variants of the same genre-search mechanism | Structural (family grouping is solid; which spec sub-appendix maps to which prefix individually is a guess) |
| `ARSNC201`, `ARSSR*`, `EM2SR`, `EM3SR` | `DFSM` / `SRME` | Mesh-dependent/nearby-data search (11.A.2.10/11.A.2.11-like — "SRME" reads as "SeaRch MEsh") | Structural (distinct top-level declaration `DFSM`, not `DFSR`, so this is a genuinely different search-frame type from the SADSR/POISR/FWYSR family, not just a naming variant) |
| `ZONEVSRC`, `ZONEZSRC` | `DFSA` / `SRZN` | 11.A.2.3 Zone Search | Structural, matches Phase 0's filename-pattern guess |
| `ZSELAND0` (+ other `ZSEL*`) | `DFSR` / `SRSZ` | 11.A.2.2 Zone Selection — the distinct signature (`SRSZ` vs. `SRZN`) confirms this is a genuinely different sub-chapter from `ZONE*`, not just a synonym | Structural |
| `POIAS201` | `DSRC` / `SRBC` | Likely POI genre/category-association search (candidate: 11.A.2.9 Q-POI Genre Selection) — notably has a **different top-level declaration** (`DSRC`) than every other search-frame file on the disc (all others are `DFSR`/`DFSA`/`DFSM`/`DFM2`) | Weak/best-guess — the "different top-level declaration" fact is solid, the specific sub-chapter guess is not |
| `POIDT013` | `PINR` / `DPOI` | Ch.11.4 POI Information Frame (same structure as `POIDT001`, already partly explored) | Structural, high confidence this is the same frame type as POIDT001 |

**The 201-207 numeric suffix / 7 zoom-level hypothesis: UNCONFIRMED, not
refuted.** Evidence gathered is circumstantial only: file sizes grow
monotonically across the `201`-`207` suffix range in a pattern
consistent with denser data at higher zoom levels (e.g. `POISR205.IDX`/
`POISR206.IDX` are the two largest, ~177MB/132MB, as noted in Phase 0). A
direct test (comparing each suffix's coverage bbox, pulled via
`INDEXDAT.KWI`'s volume management records, against the 7 known LMR
levels 12/10/8/6/4/2/0 from `ALLDATA.KWI`) was attempted but abandoned
partway through due to an unresolved offset-alignment issue — this
should be picked up by whoever next touches `index_data.py` before
relying on the mapping for Phase 3.

**Coordinate (lat/lon / PID) decoding for individual SADSR/POISR
records: STILL NOT SOLVED, but substantially narrowed (2026-08-25
follow-up pass).** Parser code: `parser/kiwiw/index_data.py`
(`AlphabeticalMatchingRecord`, `iter_alphabetical_matching_records`).

Two earlier candidate encodings were tried against byte regions
naively adjacent to confirmed real street/POI name strings and both
failed (near-zero or implausible results): the spec Ch.1.2.13 4-word
bit-packed PID format, and the sibling parser's
`bitutils.geo_secs()`/`parcel_id_bounds()` compact
3-byte-lat+1-byte-exp/3-byte-lon+1-byte-exp format.

This pass re-read the archived Ch.11.A.2.4 (Street Address Search) and
Ch.11.A.2.8 (POI Search) PDFs in full rather than guessing at bit
layouts, and made real progress on the *framing* even though the
*coordinate* itself is still unresolved:

- **New CONFIRMED finding: 1-byte SWS/D halving.** The "Relation to the
  Top of the Previous/Following Record" fields in Matching Data Records
  are 1-byte fields using the same halved-storage convention already
  documented for 16-bit (`bitutils.sws()`) and 32-bit (`index_data.sws32()`)
  fields elsewhere on the disc — real value = stored value * 2. Confirmed
  by walking real `SADSR201.IDX` records via `relnext` and checking that
  each record's `relprev` exactly equals the previous record's `relnext`
  (verified self-consistent across 25+ consecutive real records).
- **New CONFIRMED finding: exact record framing for the Street Name
  Search (alphabetical order) Matching Data Record** (Ch.11.A.2.4.5.2.5.1)
  as actually stored on this disc: `[1B relprev][1B relnext][16B raw
  prefix, undecoded][1B search-key length][search-key ASCII]`, i.e. the
  search key starts at record-relative offset 18 — not offset 13/14 as a
  literal reading of the spec's declared field list (fuzzy flag + 6-byte
  lat/lon + 4-byte area code = 11 bytes) would suggest. This offset (18)
  was derived independently two ways that agree: (a) treating `relnext`
  as a byte-displacement to the next record and brute-forcing the prefix
  length that makes it match the measured spacing between consecutive
  length-prefixed name strings (18 was the unique best fit, 18/19
  transitions matched vs. <3 for any other tried offset), and (b) walking
  the `relnext` chain forward from a known record and confirming it lands
  exactly on the next real street name every time. Implemented as
  `iter_alphabetical_matching_records()`.
- **The "missing" 7 bytes (18 actual vs. 11 spec-literal) were NOT found
  to decode as a coordinate under any tried scheme**, despite extensive
  testing: neither the plain 3-byte-lat+3-byte-lon `geo_secs` reading nor
  the literal Ch.1.2.13 2-word-per-axis bit-packed reading, at any of the
  several candidate byte offsets within the 16-byte raw prefix, produced
  values in Australia's real bounds (lat roughly -10..-44, lon
  113..154) or even in valid global lat/lon bounds. What *is* observed in
  the raw prefix bytes: a 4-byte chunk that's constant across long runs
  of consecutive alphabetically-sorted records (changing only
  occasionally, consistent with a per-suburb/zone reference rather than
  per-record geography); an 8-byte chunk that increases
  quasi-monotonically as the alphabetical list progresses (consistent
  with a sequentially-assigned Street ID, since streets are presumably
  numbered in roughly the order they were compiled/sorted — not
  consistent with geographic coordinates, which don't correlate with
  alphabetical name order); and a final 4-byte chunk that was `00 00 00
  01` (constant) on every sampled record, consistent with "Area Code".
- **Leading hypothesis, not yet confirmed:** the spec's own field table
  for this exact record variant (11.A.2.4.5.2.5, fields 3 and 5 in the
  Matching Data Definition Frame) marks *both* "Fuzzy Search Flag" and
  "Latitude and Longitude" (`RLXY`) as classification **'c'
  (conditional/optional)** — the spec explains elsewhere that RLXY is
  "used for sorting in order of distance," which an alphabetically-sorted
  street list has no need for. The leading theory is that this disc's
  street-name search records simply **omit the coordinate field
  entirely** (both conditional fields dropped, consistent with the
  observed 18-byte length not matching a with-fuzzy-and-RLXY 25-byte
  layout, though it's also short of an even fully-omitted 12-byte layout —
  the extra bytes are presumably Street ID + Area Code taking more room
  than the spec's compact 4+4 byte estimate). Reading the archived
  Ch.11.A.2.14 (POI Information Frame) text supports this: it explicitly
  states that for regular street-address data, the "necessary" latitude
  and longitude for locating a link in the main map is obtained by
  resolving the **Link ID** into main-map data (a stored parcel/link
  reference), not by storing a coordinate directly on the address record
  — i.e. this may be architecturally correct, not a decoding failure:
  street-level coordinates may genuinely live only in `ALLDATA.KWI`
  (already solved, see the main map data frame section above), reached
  via Street ID -> Link ID, rather than duplicated in the index.
- **POI records (`POISR*.IDX`) were also examined and are a distinct,
  still-harder case.** The Ch.11.A.2.8 "POI Search Matching Data Record"
  table declares its own `RLXY` field as `'VRBL'`/`'BT'` (variable-length,
  bit-packed) type, not the fixed 6-byte PID-minus-tail format used
  elsewhere — i.e. structurally the *same family* of compact bit-packed
  coordinate encoding as the main-map background/road geometry in
  `coordconv.py`, not a simple fixed-width field at all. Byte-region
  scanning around real POI records (e.g. the real "BURSWOOD CAR RENTALS"
  Perth business) turned up a similarly-shaped constant/quasi-monotonic
  byte pattern to the SADSR case, but the bit-packed variable-width
  nature of this field means the fixed-offset scanning approach used for
  SADSR doesn't directly apply — this needs its own dedicated pass
  (likely modeled on how `coordconv.py` derives its main-map bit-packed
  coordinate scheme) rather than being solved as a side effect of the
  SADSR investigation.
- **Recommended next steps for whoever picks this up:** (1) don't
  re-attempt fixed-width PID decoding on the SADSR alphabetical matching
  record's raw prefix — this was tried thoroughly and ruled out; (2)
  instead follow the Street ID found in the raw prefix through to
  `ALLDATA.KWI`'s Link ID / road-link geometry to test the
  "coordinates live only in the main map, reached via a reference chain"
  hypothesis, ideally cross-checking a specific real street (e.g.
  "GINGIN ROAD", confirmed real in this same file) against its known
  real-world WA location; (3) separately, POI record coordinates likely
  need bit-level unpacking of the `RLXY`/`P6`/`BT` variable field format,
  which is a different sub-problem from the SADSR one and hasn't been
  attempted at the bit level yet. This is still the single biggest gap
  standing between "we can extract names" and "we can build a real
  address/POI search index," and should remain a priority early in
  Phase 3.

**Implication for Phase 3 (OSM ingestion pipeline):**
1. The container/indirection mechanics (`DCTR` header, `SWS32` halving,
   FNME-style additional-address tables, length-prefixed name strings)
   are solid and reusable as-is for both reading the original disc and,
   eventually, writing a replacement.
2. Real street names (SADSR) and real POI names+addresses (POISR) can
   already be extracted end-to-end — this is a working foundation for
   validating any OSM-derived replacement index against the original.
3. The category/alphabetical tree (7-byte parent + 4-byte option records)
   is structurally understood well enough to be reproduced by a writer,
   though the semantic field-to-content mapping caveat above should be
   resolved with more samples before committing to it.
4. **Coordinate decoding is the critical blocker** — without it, matching
   OSM addresses/POIs to real disc coordinates (or generating a new
   SADSR/POISR pair from OSM data) isn't possible yet. This should be the
   first thing tackled in Phase 3, likely by cross-referencing a POI
   record's bytes against its *known* real-world coordinate (e.g. by
   finding the same business in OSM/other sources) rather than guessing
   at bit layouts blind.
5. The zoom-level (`201`-`207`) hypothesis for POISR/SADSR should be
   verified (or replaced) before Phase 3 assumes a particular file
   corresponds to a particular display scale.

### Address / POI search chain: SOLVED end-to-end (2026-08-25)

Supersedes both 2026-08-25 sections above ("coordinate decoding still not
solved" and the "Street ID -> Link ID indirection hypothesis"). A typed
street name now resolves to a real Western Australian lat/lon, and so
does a POI name. Code: `parser/kiwiw/search_frame.py` (new, generic),
`parser/kiwiw/index_data.py` (bug fixed, record layout corrected), demo:
`parser/demo_address_search.py`.

#### The bug that blocked three passes

The "Additional \*\*\*Address" table entry (Ch.11.2.2 note 9) that every
frame pointer resolves through is
`[4B absolute file offset][2B name size in words][filename]` -- and
**that 4-byte offset is itself SWS-halved**, like every other size and
offset on this disc. `index_data._resolve_additional_address()` was
using it raw. Consequence: *every* frame address in the file resolved to
a location at half its true offset, i.e. to garbage. That is why the
category tree "wasn't a flat record array", why the alphabetical records
appeared to live in the next-level frame, and why none of the six tried
transforms for the next-level pointer could work -- the base they were
being added to was wrong.

With `* 2` applied, all five of SADSR201.IDX's frame addresses land
exactly on their expected signatures. One-line fix, whole chain falls
out.

#### The index files are self-describing -- stop guessing offsets

The second realisation: each Matching Data Frame has a **Matching Data
Definition Frame** (`DCTF`, Ch.11.5) listing its records' fields in
order. 16 bytes per entry:
`[4B usage][4B description type][2B element type][2B count or count-type]
[4B additional info]`; the declaration entry's last 2 bytes hold the
entry count including itself. Description types seen: `NORM` (scalar),
`VRBL` (length-prefixed vector, `count-type` naming the length field's
type), `FDRL` (record-relative displacement), `OFST` (frame-relative
offset), `REAL` (the declaration). Element types seen: `UB`/`UW`/`UL`/
`LG` (1/2/4/4 B), `UH` (a nibble), `P6` (6 B coordinate), `BF` (count is
in *bits*), `CH` (chars).

So `parser/kiwiw/search_frame.py` parses the definition frame and drives
a generic record decoder from it. The same code path handles the street
name frame, the address range frame and the POI frame with no per-file
constants. CONFIRMED: it walks all three frames and arrives at exactly
the record count each frame declares (38,120 / 344,276 / 108,511), with
each record's parsed length fitting inside the length its own `NFRL`
announces.

#### The `STFG` "Stored Data Flag" presence bitmap

Records are variable-shape: `STFG` is a bitmap saying which of the
*following* fields are present. CONFIRMED rule, derived by hand-decoding
real records and then verified across all three frames:

- Fields up to **and including** `STFG` are unconditional.
- After it, one bit per following field in declaration order, **LSB
  first within each byte**, byte 0 first.
- Leftover bytes before the next record are the spec's padding field.

E.g. street records carry `STFG = 7f 00` (STID..KYCH present, NAME
absent), address ranges `07` (ZIPN/PRFX/STAD present), a geocoded POI
`fc 07`, and a degenerate representative POI `81 2f`. Each parse lands
exactly on the record boundary `NFRL` announces.

#### The chain

```
IDX/SADSR201.IDX
  DFSR management frame @0        2 records x 440 B, first at 16
   +- SRMX  @16   "STREET ADDRESS"  (all-city street name search)
   |    matching data definition -> @1040   (DCTF, 16 entries)
   |    matching data frame      -> @234372 (38,120 records, max 60 B)
   |         BFRL NFRL FGFZ STFG STID NXKD NXFN NXST NXCT KYCH [NAME ...]
   |    next-level frame         -> @5046996
   +- SRHA  @456  (city selection)

  @5046996: a *nested* DFSR management frame
   +- SRT1  @5047012  "ADDRESS RANGE"
        matching data definition -> @5047388 (DCTF, 14 entries)
        matching data frame      -> @5047628 (344,276 records, max 30 B)
             BFRL NFRL FGSA ARCD RLXY LKID STFG [ZIPN PRFX STAD ...]
```

The street record's `NXST` (an `OFST`/`LG` field, **SWS-halved**) times 2
is the byte displacement, from the start of the address-range matching
data frame, of that street's first Address Range record; `NXCT` is how
many consecutive records belong to it. `NXKD`/`NXFN` are one nibble each
sharing a byte, invariably `0x51` = class 5 ("next-level matching data")
/ detailed-search-record serial 1.

#### `RLXY` is the `P6` type -- and it is stored inline

The disc's definition frame for the address-range frame declares `RLXY`
(P6) and `LKID` *inline on the address-range record*, where the spec's
worked example instead used `POIO`/`POIC` pointers off to a separate
Street Address POI Information frame. The definition frame is
authoritative, and this is one indirection *fewer* than the previous
pass predicted.

`P6` = 6 bytes: a 3-byte latitude then a 3-byte longitude, each decoded
by the **existing** `kiwiw.bitutils.geo_secs()` -- bit 23 is the sign
(1 = south/west), the low 23 bits are the angle in 1/8 arc-second units.
That is a Ch.1.2.13 PID with its two exponent bytes dropped. No new
coordinate decoder was needed; the main-map one was already correct.

Per Ch.11.A.2.14 footnote 4 this is "the coordinates of the link start
point", i.e. a coarse link-locating coordinate (values quantise to a
parcel-ish grid), not a house-accurate position. `STAD` gives the house
numbers at the two ends of the link *in link direction*, so the start
value is frequently greater than the end value; interpolating a precise
house position is the head unit's job, against the main map's link
geometry.

#### Validation

1. **Whole-file statistics (the decisive one).** Decoding all 344,276
   address-range records gives lat `-35.1250 .. -14.2917`, lon
   `113.4375 .. 128.9375`, **zero** outliers. Western Australia really
   runs from -35.13 (West Cape Howe) to -13.69 (Cape Londonderry) and
   from 112.92 (Steep Point) to exactly 129.00 (the straight-line
   NT/SA border). Reproducing that box, including the artificial 129 deg
   meridian, is not something a wrong decode does by accident. The
   108,511 POI records reproduce the same box independently.
2. **Spot checks against known geography.** Not just points but *shapes*:
   - `ST GEORGES TERRACE` -> 152 ranges, all at -31.953, 115.852..115.867
     (Perth CBD, one street).
   - `STIRLING HIGHWAY` -> 346 ranges, -32.052..-31.969 / 115.766..115.828
     (the Perth->Fremantle corridor).
   - `GREAT EASTERN HIGHWAY` -> 817 ranges, 115.891..**121.438** -- the
     real highway runs Perth to Kalgoorlie.
   - `ALBANY HIGHWAY` -> 1,137 ranges, -31.969..**-35.042** -- Perth to
     Albany.
   - `HANNAN STREET` -> -30.75, 121.44 = Kalgoorlie's main street.
   - `WANNEROO ROAD` -> -31.906..-31.042, north out of Perth.
   - `GINGIN BROOK ROAD` -> -31.292, 115.563 (Gingin).
   - POI `BURSWOOD CAR RENTALS` -> -31.970, 115.894 (Burswood).
   - POI `POLE A A\48 FARRINGTON ROAD, PERTH` -> -32.080, 115.858
     (Farrington Road, Leeming/Murdoch).
3. **Self-consistency.** Record counts match the declared counts exactly
   in all three frames; every record's field parse fits its own `NFRL`.

**Confidence: HIGH / CONFIRMED** for the chain, the `DCTF` definition
frame, the `STFG` bitmap, the `P6` coordinate, `NXST`/`NXCT`, `LKID`'s
position, and the additional-address halving. The address-search half of
"full feature parity" is now understood well enough to regenerate.

#### Corrections to earlier entries in this document

- The category Parent record is **14 bytes** and the Option record
  **8 bytes**, not 7 and 4: those spec figures are SWS-halved like
  everything else. Arithmetic proof: first-level category size
  `0x93` (= 294 real) with `0x23` = 35 options, and `14 + 35*8 = 294`
  exactly.
- `matching_data_frame.file_offset` for SRMX is @234372 and *does* hold
  the flat alphabetical record array. The earlier claim that it held a
  category tree came from reading the un-doubled offset @117186.
- `next_level.file_offset` does **not** hold the alphabetical records;
  it holds a nested `DFSR`/`SRT1` management frame.
- The six ruled-out transforms for `next_level_field` were not the
  problem: the field identification was right all along (it is `NXST`),
  and the byte alignment was one off (bytes [8:12) of `raw_prefix` is
  correct, but `[0:4)` was `FGFZ`+`STFG`+the top byte of `STID`, not an
  area code -- the real area code is `ARCD` on the address-range
  record). The missing pieces were the `* 2` and the corrected base.
- The "Street ID -> Link ID" framing was aimed at the wrong field: `STID`
  is not a link key. `NXST` is the pointer, and `LKID` is inline at the
  end of the chain.

#### Loose ends (none blocking)

- `ARCD` area-code *semantics* are unknown. The values are 4-byte, always
  with a constant leading `0x1e` (e.g. `0x1e01f5d0` Perth CBD,
  `0x1e000462` Albany, `0x1e007ec8` Gingin, `0x1e008815` the Stirling
  Highway suburbs). Presumably a suburb/locality id shared with the
  city-selection frame (`SRHA`) -- decoding `SRHA` should name them.
- POI `CTGY` is a `UW` whose values are all multiples of 128
  (`0xcf80`, `0x5280`, `0x2300`, ...), so the code is probably in the
  high 9 bits. The category-name table (`category_data`) is located but
  not parsed.
- `VRBL` fields declare `CMCH`/`CMP6` "compressed" additional-info, but
  on this disc the character vectors are plain ASCII; no compression
  variant has been observed and none is implemented.
- The POI index stores a separate record per *word suffix* of a name
  ("A AA BURSWOOD CAR RENTALS" / "AA BURSWOOD CAR RENTALS" /
  "BURSWOOD CAR RENTALS" / "CAR RENTALS"), each pointing at the same
  coordinate. Worth knowing before generating a replacement: index size
  scales with words per name, and this is what makes POISR205/206 the
  largest files on the disc.
- `LKID` -> `ALLDATA.KWI` link record has *not* been cross-checked yet,
  because of the parcel-index anomaly below.

#### Side finding: a pre-existing main-map parcel-index bug

Now that the index chain works, it is an independent geographic oracle
for the main map -- and it immediately caught something.
`dump_parcel.py --lat -31.95312 --lon 115.86719 --level 0` computes the
right *bounds* (-31.9583..-31.9375, 115.84375..115.875 = Perth CBD,
blockset 51 / block 9 / parcel 536) but returns name records for
Rockingham/Port Kennedy streets (ENNIS AVENUE, GNANGARA DRIVE,
HARRINGTON WATERS DRIVE, INVESTIGATOR DRIVE, ABBEYTOWN CIRCLE, BONDI
CRESCENT). Feeding those six names back through the now-working SADSR
chain puts all of them at ~-32.32, 115.766 -- ~40 km south. So the bbox
maths is right and the parcel *selection* is wrong: `mesh.py`'s flat
parcel-index / iteration-order assumption (already flagged in this
document as "unconfirmed, row-major lat-then-lng") is fetching the wrong
parcel record. Not fixed here (out of scope for this pass) but now cheap
to debug, since any street name gives a known-good coordinate to test
against.

### Parcel iteration-order bug: ROOT CAUSE FOUND AND FIXED (2026-08-25)

Follow-up to "Side finding: a pre-existing main-map parcel-index bug"
above, now that the address/POI search chain gives an independent
geographic oracle for Western Australia. Fixed in `parser/kiwiw/mesh.py`
(`locate_parcel()`); regression tests updated in
`parser/tests/test_mesh.py`.

**Root cause.** `locate_parcel()` computes the global grid cell `(ix, iy)`
containing the query point by floor-dividing the coordinate delta by the
level's *finest* cell size (`mx`/`my`), where the finest cell size already
divides all the way down through blockset -> block -> top-level parcel
(`LevelMgmtRecord.grid_nx`/`grid_ny` in `volume.py` are the product of all
three counts). That means `ix`/`iy` -- and the `(px, py)` derived from them
by successively floor-dividing/mod-ing out the blockset and block counts
-- are *already* the correct parcel-array coordinates within the matched
block; no further computation is needed to find the top-level parcel's
place in that block's flat array.

The buggy code didn't use `(px, py)` for that first lookup. Instead it
computed the *fractional position within that already-finest cell*
(`local_lat_frac`/`local_lon_frac`, values in `[0, 1)`, meant only for
descending into genuine divided/integrated sub-parcels one level further
than the block-level grid already resolves) and multiplied that fraction
by the *same* per-level parcel-count that had already been folded into
`ix`/`iy`. The result tracked the query point's arbitrary decimal position
inside its own leaf cell rather than the cell's real address, and so
picked an effectively unrelated entry out of the block's parcel array.

This explains the exact reported symptom: the parcel *bounds* shown were
computed straight from `ix`/`iy` (never touched by the bug) and so were
always right, while the *record actually fetched* (`dsa`/`size`, i.e. the
sector address of the real road/background/name data) came from the
bogus index and was, in effect, arbitrary -- e.g. a Perth CBD query
(-31.95312, 115.86719) reported a correct Perth CBD bounding box but
decoded Rockingham/Baldivis street and place names from ~40 km south.

**The fix.** `mesh.py` now sets `lpx, lpy = px, py` (the values already
computed from `ix`/`iy`) for the loop's first iteration (depth 1, always
parcel type 0 -- the type directly referenced by a block management
record), and only falls back to the `local_lat_frac`/`local_lon_frac`
fractional computation for genuine deeper divided/integrated-subparcel
recursion (depth > 1), where it's needed because that subdivision is
*not* already accounted for by `ix`/`iy`. No change to the block/blockset
level indexing (`bset_flat`/`block_flat`), which was already correct --
see the spec cross-reference below.

**Spec cross-reference (confirms the ordering convention itself was
already right).** `spec/format_english/pdf/0600122e.pdf` (Ch. 6) states,
verbatim, for all three levels:
- Block sets (6.1): "placed from the reference point ... side to side in
  the longitudinal direction on one latitudinal level and another" and
  "placed from low latitudes to high latitudes."
- Block management records (6.2.1): "placed from the block set management
  origin ... side to side in the longitudinal direction on one latitudinal
  level after another" / "from low latitudes to high latitudes."
- Main map parcel management records (6.3.1): "placed from low latitudes
  to high latitudes" (implicitly the same longitude-inner convention as
  the two levels above it).

I.e. row-major with **latitude as the outer/slow axis and longitude as
the inner/fast axis** (`flat_index = lat_index * n_lng + lng_index`) at
every level. This is exactly what `mesh.py` already computed for
`bset_flat`, `block_flat`, and the (now-fixed) parcel `idx` -- so the
previously-flagged "unconfirmed, row-major lat-then-lng" note in this
document is **CONFIRMED CORRECT** by the archived spec text; the actual
bug was the redundant/misapplied fractional recomputation described
above, not the axis-ordering convention itself.

(Note: `tools/kiwiread/kiwiread.c`'s own debug-only `divbsmr()` helper,
used solely to drive its hardcoded-coordinate `isin()` sanity checks,
decomposes flat indices using the `.lat` field as the modulus at every
level regardless of axis -- which looks backwards for the longitude
component under this same spec text unless every level's lat/lng counts
happen to be equal. This was a red herring investigated during this pass:
`kiwiread.c`'s tool-specific quirk does not reflect the on-disc data
layout, which the archived spec describes explicitly and which the
independent oracle below confirms `mesh.py`'s row-major convention gets
right.)

**Validation.**

1. **The originally-reported case.** `dump_parcel.py --lat -31.95312 --lon
   115.86719 --level 0` now decodes real Perth CBD content at that
   parcel -- `"190 ST GEORGES TERRACE"`, `A=PERTH CBD, PERTH,WESTERN
   AUSTRALIA`, `A=WEST PERTH, ...`, `A=NORTHBRIDGE, ...` -- in place of
   the previous Rockingham/Baldivis names. St Georges Terrace's real
   longitude extent, independently established via the search-frame
   oracle in the "SOLVED end-to-end" section above, is 115.852..115.867;
   the query's 115.86719 sits right at that eastern end, exactly where
   "190 ST GEORGES TERRACE" (a real, high street-numbered address at that
   end) should be.
2. **Broad cross-check against the search-frame oracle (the main
   validation for this fix).** Script:
   sample real Western Australian streets from `SADSR201.IDX` via
   `kiwiw.search_frame.StreetAddressIndex.iter_streets()`, take a
   real address-range coordinate for each via `.address_ranges()` (an
   independently-decoded, oracle-confirmed lat/lon -- see "Address / POI
   search chain: SOLVED end-to-end" above), feed that coordinate into
   `AllData.find_parcel()` (i.e. the fixed `mesh.py`), and check whether
   the returned main-map parcel's own decoded name records mention that
   same street name.
   - **800 randomly sampled real street/coordinate pairs: 799/800 (99.9%)
     exact street-name match** between the oracle's street name and a
     name record decoded from the mesh-located parcel. A smaller 200-pair
     run independently got 199/200 (99.5%) -- consistent.
   - **0 of 800 queries failed to locate a parcel at all** (no `None`
     results, no coverage gaps hit).
   - The single recurring miss (`SOMERVILLE STREET` at -31.94271,
     115.86719) still decoded a parcel containing `ABERDEEN STREET`,
     `GRAHAM FARMER FREEWAY`, `LITTLE SHENTON LANE`, and
     `A=NORTHBRIDGE`/`A=WEST PERTH` -- i.e. still the correct immediate
     Perth inner-city neighbourhood, just not the exact adjacent parcel
     that happens to carry the Somerville Street name record (a
     parcel-grid-boundary edge case, not a suburb-scale error).
   - This is materially different from an exact-record match (the two
     data structures -- main-map parcels and the address-search index --
     are independent, differently-tiled representations of the same real
     world, so *some* near-boundary disagreement is expected and
     acceptable per this task's validation bar); what it demonstrates is
     that the fixed `mesh.py` selects the *geographically correct*
     parcel for a real coordinate at a ~99.9% rate across a large,
     randomly sampled, independently-oracle-verified set, which is the
     property that was broken before the fix.
3. **Regression re-check against the 3 original Phase 1 test
   coordinates** (`parser/tests/test_mesh.py`, both now passing):
   - **Melbourne** (-37.813629, 144.963058): now resolves one level
     deeper than before (a real divided/integrated sub-parcel, previously
     "unverified beyond depth 1" -- this fix is the first time that
     recursion path has actually been exercised against real data), and
     decodes real, plausible content: `"TELSTRA DOME"`,
     `A=DOCKLANDS, MELBOURNE,VICTORIA`, `A=WEST MELBOURNE, ...`. This
     nests correctly inside kiwiread.c's independently-established
     top-level cell bbox (the deeper subdivision is finer than what
     kiwiread.c's own debug tool prints, so containment -- not exact
     equality -- is the correct check; updated in the test).
   - **Sydney Harbour** (-33.868820, 151.209290): now decodes
     `"GOVERNMENT HOUSE"`, `"BULLETIN PLACE"`,
     `A=SYDNEY CBD, SYDNEY,NEW SOUTH WALES` -- real Circular Quay / Sydney
     CBD content, more specific than (but consistent with) the old
     generic `"TASMAN SEA"` water-body label for the same harbour-edge
     point.
   - **The coordinate previously labelled "Regional NSW / Hunter Valley"**
     (-33.8148, 151.0011): this is actually a **correction to an earlier,
     wrong claim in this document**, not just a re-test. That coordinate
     is nowhere near the Hunter Valley/Yengo NP (which is ~100 km further
     north, around lat -32.7..-32.9) -- it sits in Sydney's
     Parramatta/Camellia/Granville area. The original Phase 1 pass
     decoded `"YENGO NATIONAL PARK"`/`"POKOLBIN STATE FOREST"` there and
     took that as a positive real-place cross-check, but given the
     coordinate's actual real-world location, that was this same
     parcel-index bug manifesting -- it just wasn't caught at the time
     because no independent oracle existed yet to check against. Post-fix
     this coordinate correctly decodes real Camellia/Granville, Sydney
     content (`A=CAMELLIA, SYDNEY,NEW SOUTH WALES`,
     `A=GRANVILLE, SYDNEY,NEW SOUTH WALES`), which matches its real
     location. `parser/tests/test_mesh.py` is updated with this
     correction recorded in a comment, and its assertion strengthened to
     check for `"SYDNEY"` in the decoded names rather than merely that
     *some* road data was found.

**Confidence: HIGH.** The fix is a small, well-understood change (use the
already-correct `(px, py)` for the first lookup instead of recomputing a
value that double-counted a factor already folded into `ix`/`iy`), the
axis-ordering convention it preserves is directly confirmed by the
archived spec text (not just inferred), and it's now validated against
799/800 independently-oracle-confirmed real coordinates spanning
Western Australia -- a materially larger and more rigorous check than the
single hand-picked coordinate this bug was originally caught on.

**Implication for Phase 2/3:** main-map parcel selection (not just parcel
*bounds*) is now on solid, independently-cross-checked footing across a
large real sample, clearing the "not actually verified" concern flagged
when this bug was first found. The divided/integrated subparcel recursion
path (depth > 1) is now confirmed exercised and correct against real data
for at least one real case (Melbourne), partially addressing (though not
exhaustively closing) the separate "unverified beyond depth 1" caveat
from the original parcel work.

## Decisions / deviations from plan

(record anything that didn't go as expected here)
