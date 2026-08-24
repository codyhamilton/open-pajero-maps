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
`parman_t.type` field to decide the next subdivision grid -- this is
**unverified beyond depth 1** on this disc (no test coordinate happened to
land in a divided parcel), flagged as a risk for Phase 2/3 if other
regions use deeper subdivision. Note the resulting (blockset_index,
block_index, parcel_index) numbers in my output do **not** match
kiwiread's printed indices for the same Melbourne parcel (38/14/1946 vs.
kiwiread's 22/23/542) -- only the geographic bbox and underlying sector
address should be expected to agree; the flat-index numbering itself
depends on an unconfirmed iteration-order assumption (row-major
lat-then-lng) that isn't spec-stated and doesn't need to match kiwiread's
own (possibly differently-ordered) internal bookkeeping as long as both
land on the same real sector address, which they do here.

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

### Street ID -> Link ID indirection hypothesis, tested end-to-end (2026-08-25)

Follow-up to the 2026-08-25 "coordinate decoding still not solved"
pass above. This pass tested the leading hypothesis it left behind:
that street-level coordinates for SADSR alphabetical-order records are
not stored inline at all, but resolved via Street ID -> Link ID ->
`ALLDATA.KWI` main-map geometry (per the Ch.11.A.2.14 "POI Information
Frame" footnote). Parser code: `parser/kiwiw/index_data.py`
(`AlphabeticalMatchingRecord` gained `area_code`/`street_id`/
`next_level_field`/`tail` properties), demo: `parser/demo_street_id_link.py`.
Tested against the real mounted disc, real `SADSR201.IDX`, real WA
street names (GADEN ROAD, GINGIN BROOK ROAD, GINGIN ROAD).

**Result: the hypothesis is NOT confirmed end-to-end. This is an honest
negative/partial result, not a workaround-in-disguise.**

**What *did* come out of this pass (genuine progress on framing, not on
coordinates):**

- Re-read the archived Ch.11.A.2.14 (POI Information Frame) and
  Ch.11.A.2.4 (Street Address Search) PDFs in full via `pdftotext`.
  Found the exact spec chain the hypothesis describes:
  Street Address Search Frame -> Street Name Search (alphabetical order)
  Matching Data Record's "Offset to Next-level Data Frame" field should
  point at an **Address Range Search Matching Data Record**
  (Ch.11.A.2.4.4.5: `[1B relprev][1B relnext][4B offset-to-POI-info]
  [2B POI-info-record-count][1B street-address-flag][variable street
  address][variable area code]...`), whose own "Offset to POI
  Information" field (a direct, non-Street-ID-keyed pointer) finally
  reaches a **Street Address POI Information Record**
  (Ch.11.A.2.14.1.4: `[1B relprev][1B relnext][1B street-address-flag]
  [variable street address][variable RLXY lat/lon][variable Link ID]
  [1B link-serial-number]`) -- this record is where real RLXY + Link ID
  actually live. Footnote 4 on that record confirms the RLXY here is
  "the coordinates of the link start point ... necessary to search for
  a link ID stored as main map data ... in PID format", i.e. exactly the
  coarse parcel-locating coordinate the previous pass was looking for,
  just one indirection layer further away than assumed.
- Got the exact literal field table for the SADSR alphabetical Matching
  Data Record itself (Ch.11.A.2.4.5.2.5.1), confirming: `[1B relprev]
  [1B relnext][1B fuzzy flag, c][6B lat/lon, c][4B area code, a]
  [variable search key, a][1B language number, c][variable name, c]
  [4B Street ID, a][1/2B next-level-frame class, a][1/2B next-level-
  frame serial, a][4B offset-to-next-level-frame, a][1B padding, a]`.
- **New clean finding: the real 16-byte `raw_prefix` splits exactly
  into four 4-byte big-endian fields with zero remainder**
  (`area_code`/`street_id`/`next_level_field`/`tail`), which is a much
  better fit than the previous pass's fuzzy byte-range description and
  is itself further evidence that the conditional (`'c'`) fuzzy-flag
  and lat/lon fields really are omitted on this disc (1+6+4=11 leaves 5
  bytes unaccounted for; 4+4+4+4=16 leaves none). Verified against 3
  real consecutive WA street records (GADEN ROAD, GINGIN BROOK ROAD,
  GINGIN ROAD) plus a 2000-record sample for the `tail` field's value
  distribution.
- `area_code` (bytes [0:4)) matches the spec's mandatory Area Code
  field well: near-constant across long alphabetical runs
  (`80 7f 00 46` throughout the F's, `80 7f 00 47` throughout the G's).
- `tail` (bytes [12:16)) is a small integer (range 1-51 across a
  2000-record sample) -- never plausible as a byte offset in this
  15MB file, consistent with the spec's small packed "Next-level Data
  Frame Class"/"Serial Number" fields rather than a pointer.
- `street_id` (bytes [4:8)) increases quasi-monotonically per record, as
  before -- consistent with a sequentially-assigned ID, though its
  storage *position* (before the name, not after, per the disc's real
  field order) still doesn't match the spec's literal declared order,
  same caveat as elsewhere in this module.

**What did NOT work -- the actual blocker:** `next_level_field` (bytes
[8:12)), the best remaining candidate for the spec's "Offset to
Next-level Data Frame" pointer, does not resolve to a
plausible Address Range Search Matching Data Record under any tried
transform. Tried on the real GINGIN ROAD record
(`next_level_field = 0x1b6e3a` = 1,797,690): raw absolute, raw absolute
doubled (the sws32 halving convention already confirmed for other
32-bit fields on this disc), and both of those added to
`next_level.file_offset` (2,523,498) and to
`matching_data_frame.file_offset` (117,186) as bases. All six land
in-bounds (file is 15,387,684 bytes) but none produce the expected
`[1B][1B][4B][2B][1B]...` shape; several instead land on byte patterns
that look like *other* `area_code`/`street_id`/`next_level_field`/`tail`
Street-Name-alphabetical-style records elsewhere in the same file (i.e.
structurally self-similar to the source record, not to the expected
target type), which is circumstantial evidence the transform (or the
field identification itself) is still wrong, not that the file lacks
the data. Full detail and exact byte dumps: `parser/demo_street_id_link.py`.
Also checked and ruled out: `matching_data_frame.file_offset` (117186)
is not the flat alphabetical record array either (no length-prefixed
strings found there in a 3000-byte scan) -- it's a separate,
denser table of small repeating fixed-width groups, consistent with
the previously-identified Category Parent/Option tree, not plain
records.

**Confidence: LOW that this specific pointer identification is correct;
MEDIUM-HIGH that the general Street ID -> Link ID architecture
described in the spec is real** (the spec text itself is unambiguous
and internally consistent about this being how the format works,
independent of whether this pass found the right bytes on this disc).

**Recommended next steps for whoever picks this up:**
1. Don't re-try the six transforms above on `next_level_field` -- they're
   ruled out. Instead, directly decode the Category Parent/Option tree
   at `matching_data_frame.file_offset` (7-byte parent = 3-byte offset +
   4-byte count; 4-byte option = 1-byte char + 3-byte offset, per
   Ch.11.A.2.1's stated sizes, already noted in the previous pass) --
   this is the one sub-structure in this file we've located but not
   actually parsed field-by-field, and it may be the real path to the
   Address Range Search frame rather than a field inside the
   alphabetical record itself.
2. Consider that `next_level_field`/`street_id` might need to be read
   together as an 8-byte compound key (both increase monotonically at
   similar rates -- could be a single 64-bit ID split for alignment
   reasons) rather than as two independent 4-byte fields.
3. A second real disc (different manufacturer/year) would help
   disambiguate "this field's real position differs from the spec's
   declared order" (already seen twice in this file) from "this field
   isn't what we think it is at all."
4. If this remains unresolved going into Phase 3, budget for treating
   address-search coordinate resolution as a research spike with a
   hard time-box, not an open-ended blocker -- the main-map road/name
   geometry (already fully solved, see above) may be sufficient to
   build a workable address search by *matching OSM street names to
   main-map link geometry directly* (skip the original disc's index
   pointer chain entirely, since we're regenerating from OSM anyway and
   don't need to preserve the original disc's exact indirection, only
   its consumed *shape*).

## Decisions / deviations from plan

(record anything that didn't go as expected here)
