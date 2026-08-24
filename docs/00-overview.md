# Open Pajero Maps

## Goal

Build a replacement navigation DVD for an older Mitsubishi Pajero MMCS unit, sourced
entirely from OpenStreetMap data, to replace the manufacturer's unsupported 2007/2012-era
disc. The original manufacturer no longer publishes map updates for this hardware.

The disc currently mounted (the user's own) is used only as reference material to
understand the on-disc format the MMCS expects — it is not redistributed.

## Scope decisions (locked in during planning, 2026-08-24)

- **Region**: single region first. The reference disc's own coverage is Australia
  (per `COUNTRY.KWI` / `SPEC.KWI`), so start there — likely narrowed to one state for
  the earliest end-to-end test, widening once the pipeline works.
- **Feature depth**: full parity is the target — roads/routing, POIs, and address
  search — but built up incrementally (see Phase 3 sub-checkpoints below), not
  attempted all at once.
- **Test access**: the user can burn and test discs directly in the vehicle relatively
  easily, so the plan favors frequent in-vehicle validation over purely offline proof.

## Format identified

The disc is **KIWI-W** (a Japanese consortium format from Denso/Aisin/Toyota/Navteq-era,
also used historically by Volvo, Toyota/Lexus, Audi and others of that vintage),
despite the `.KWI` extension being easy to mistake for something Kenwood-specific.

Confirmed via hex inspection of the mounted disc:
- `METADATA.KWI`: WGS84 coordinates, ISO-8859-1 charset, multi-language name support.
- `SPEC.KWI`: references `AFAU`/`AGAU` (Australia format/data versions 2.64).
- `COUNTRY.KWI`: encodes "AUSTRALIA".

## Key references found during feasibility research

- **Official KIWI-W v1.22 format specification**, archived on the Wayback Machine:
  https://web.archive.org/web/20060616222450/http://kiwi-w.mapmaster.co.jp/format_english/format_kihon.html
  Table of contents (from `menu.html`): Document Rules, Data Configuration on a Medium,
  Hierarchical Structure of Maps, Configuration of Datamanagement Frame, All Data
  Management Frame, Main Map Data Frame, Route Guidance Data Frame, Region Data
  Management Frame, Route Planning Data Frame, Management Pattern of Index Data,
  Parameters, Metadata, Reference, Loading Module Management Format, Main Map Data
  Metadefinition Data, Image Data Frames, Voice Data Frame.
  `WebFetch` cannot reach `web.archive.org` directly in this environment — use `curl`
  instead, following the frameset (`menu.html` + individual chapter pages).
- **Existing partial reverse-engineering tool**: https://github.com/jharg/kiwiread —
  parses `ALLDATA.KWI` and `LOADING.KWI`: data-volume header, the 4-level
  block-set/block/parcel/subparcel mesh hierarchy, road multilink/polyline geometry
  (delta-encoded coordinates), background/name frames; renders to BMP/SVG. Notably
  contains an `osm.c` that rasterizes OSM XML to a bitmap named `ausmap.bmp` — strong
  circumstantial evidence a prior author was working this exact Australian dataset.
  Treat as a study/fork starting point, not a finished tool: read-only, hardcoded
  paths/coordinates, no route planning, full index data, or voice data support.
- **Community precedent (discouraging, but informative)**: an OSM community forum
  thread about exporting OSM to KIWI-W for Volvo/Toyota units concluded the effort is
  a multi-month-to-multi-year undertaking, with no publicly completed exporter to date.
  This sets realistic expectations — treat this as a genuinely large project, and prove
  feasibility cheaply before committing to the hard part.

## Physical disc facts

- UDF filesystem, ~2.3GB used — fits a standard single-layer DVD-R/DVD+R.
- Top-level files/dirs on the reference disc: `ALLDATA.KWI` (~1.5GB, main map data),
  `COUNTRY.KWI`, `COVERAGE/` (contains `AUC.BMP`), `COVERAGE.BIN`, `DICVCE56.KWI`,
  `DN/` (contains `CLUSTER.DAT`), `GRA256D.KWI`, `HWMAP.KWI`, `IDX/` (many `.IDX` files,
  ~797MB total), `INDEXDAT.KWI`, `KGRA256.KWI`, `KGRPDAT.KWI`, `KPCT256.KWI`,
  `KPCT2DT.KWI`, `LOADING.KWI` (~31MB, likely boot/loader), `METADATA.KWI`,
  `PCT256D.KWI`, `PCT2DAT.KWI`, `PCT2MNG.KWI`, `SPEC.KWI`, `VAR256D.KWI`,
  `VERSION.TXT` (`COMMENT=2007 ver.1;`).

## Phase plan

Five phases, each a decision checkpoint. See `docs/phases/` for the detail on each.
Do not start the OSM writer (Phase 3) until Phase 2's byte-identical round-trip is
proven on real hardware — that's the actual proof the format is understood, not just
plausible-looking.

0. Project docs, archive, and inventory — *in progress*
1. Format analysis (full parser + intermediate representation)
2. Writer prototype: round-trip the existing disc unchanged, validate in-vehicle
3. OSM ingestion and content pipeline (roads → names → POIs → address search)
4. Full disc assembly and validation

## Open risks / unknowns

- Whether the MMCS validates checksums, coverage bounds, or version/cluster tables at
  boot in ways not yet reverse-engineered (would block Phase 2 even with correct map
  data).
- Whether `LOADING.KWI`'s executable/loader content is version-locked to the map data
  in a way that constrains what "new" data it will accept.
- True scope of KIWI-W format drift between hardware/years — `kiwiread` was written
  against different source discs (Audi mentioned), so this disc's specific variant
  needs independent confirmation, not assumed compatibility.
- Whether OSM data in the target region has sufficient tagging depth (speed limits,
  turn restrictions, addr:* completeness) to hit the "full parity" bar, especially for
  address search.

## Decision log

- 2026-08-24: Scope locked to single region (Australia) first, full-parity target,
  in-vehicle testing assumed available. Plan approved.
- 2026-08-24: Phase 0 research complete (spec archive + kiwiread build/test). Findings:
  - Full official KIWI-W v1.22 spec archived (68 files, `spec/format_english/`, see
    `spec/INDEX.md`) — includes byte-level offset/length tables for road data, name
    data, route guidance, index/search frames, and POI search. Much stronger reference
    than expected going in.
  - `kiwiread` builds (two trivial modern-gcc fixes) and **successfully parses this
    disc's real data**: header/volume metadata decode cleanly (`FORMAT VERSION
    KIWI01-22-00`, matching the archived spec version), and after fixing one bug in
    the tool's tile-locate math (antimeridian-wraparound: this disc's top-level
    bounding box spans `E90` to `W142`, i.e. crosses ±180°, which the tool's `_rx - _lx`
    width calc didn't handle), it correctly located and rendered a real Melbourne
    parcel to SVG with legible embedded name text. This is strong validation that the
    core container format (MHR/LMR/BSMR tables, block/parcel hierarchy) is well
    understood and `kiwiread`'s parsing logic is directly reusable/portable for
    Phase 1 — only its coordinate/tile-index driver layer needs rewriting (it was
    built against a non-wraparound European disc).
  - `osm.c` in that repo is a rough one-directional OSM-XML→bitmap sketch with no
    real XML parsing and zero KIWI-W-encoding capability — not reusable for the
    write direction, confirmed as expected.
  - See `docs/phases/00-inventory.md` for full detail.
- 2026-08-25: Phase 1 (format analysis) substantially complete, run as 3 parallel
  subagents covering main map data, index/search data, and small metadata/image
  files. A Python parser package now lives at `parser/kiwiw/` with a CLI
  (`parser/dump_parcel.py`) and tests (`parser/tests/`). Key outcomes (full detail
  in `docs/phases/01-format-analysis.md`):
  - **Main map data (roads/background/names) works end-to-end on real data** —
    tested at 3 real Australian coordinates (Melbourne, Sydney Harbour, Hunter
    Valley), correctly decoding real road names and place names, cross-validated
    against `kiwiread.c`'s independently-confirmed Melbourne bbox.
  - **Street address search and POI search both extract real, plausible data**
    (e.g. real WA street names, real Perth business names/addresses) from
    `SADSR*.IDX`/`POISR*.IDX` — the container/indirection mechanics are solid.
  - **New critical open blocker**: coordinate (lat/lon) decoding for individual
    address/POI *index* records (as opposed to main map road/name geometry, which
    *is* solved) is unsolved — two candidate encodings tried, neither worked. This
    must be the first thing tackled early in Phase 3, since without it we can't
    match OSM data to real coordinates for a regenerated address/POI index.
  - Other open items carried into Phase 2/3: parcel-local coordinate encoding for
    main-map background geometry is only medium-confidence (inferred, not
    spec-confirmed); road-type codes are only ~50% identified; divided/integrated
    parcel recursion beyond depth 1 is unverified; the 201-207 filename-suffix
    zoom-level hypothesis for index files is unconfirmed.
  - Most files identified as safe to copy through unchanged in Phase 4 (firmware,
    voice prompts, UI graphics/tiles); a handful of small disc-identity files
    (`COUNTRY.KWI`, `SPEC.KWI`, `METADATA.KWI`, `COVERAGE.BIN`, `DN/CLUSTER.DAT`,
    `VERSION.TXT`) will need regeneration, mostly straightforward except a
    cross-file "disc stamp" and cluster-index whose generation rule isn't
    understood yet.
  - Next: Phase 2 (round-trip writer) — but consider resolving the index-record
    coordinate blocker first since it's now the single biggest known risk, and
    Phase 2's plan (write the inverse of the Phase 1 parser, byte-diff against the
    original) is more valuable once that gap is closed.
- 2026-08-25: Follow-up investigation into the index-record coordinate blocker
  (single subagent, focused re-read of the archived Ch.11.A.2.4/11.A.2.8/11.A.2.14
  PDFs plus systematic byte-offset experiments against real `SADSR201.IDX`/
  `POISR201.IDX` records). **Coordinate decoding is still not solved**, but the
  investigation narrowed the problem substantially and shipped two new CONFIRMED
  structural findings into `parser/kiwiw/index_data.py` (full detail in
  `docs/phases/01-format-analysis.md`):
  - The same halved-storage ("SWS/D") convention already known for 16-bit and
    32-bit fields elsewhere on the disc also applies at **1-byte width** to the
    "Relation to Previous/Following Record" chain-link fields in Matching Data
    Records (real value = stored value * 2).
  - The exact real on-disc byte framing of the SADSR "Street Name Search
    (alphabetical order) Matching Data Record" is now confirmed: 1-byte
    `relprev`/`relnext` + a 16-byte undecoded prefix + a length-prefixed ASCII
    search key, with the search key starting at record offset 18 (not the
    spec-literal-field-list offset of 13). Chain-walking via `relnext` is
    implemented (`iter_alphabetical_matching_records`) and verified
    self-consistent across 25+ real consecutive records.
  - Extensive testing of that 16-byte prefix under both previously-rejected
    coordinate formulas still produced no plausible Australian (or even
    valid-range) lat/lon at any sub-offset. New leading hypothesis (not yet
    confirmed): the coordinate field is legitimately **omitted** for this record
    variant (the spec marks it conditional/'c' here, since an alphabetical list
    has no need for distance-sorting), and real address coordinates are instead
    resolved indirectly — Street ID -> Link ID -> main-map link geometry — per
    Ch.11.A.2.14's footnote on how POI/address records reference the main map,
    rather than being stored inline in the index at all.
  - POI records (`POISR*.IDX`) remain a separate, still-untouched sub-problem:
    the spec describes their `RLXY` field there as a variable-length bit-packed
    type (same family as the already-solved main-map background coordinate
    encoding), not a fixed-width field, so the SADSR fixed-offset approach
    doesn't transfer directly.
  - **Recommended next step**: before Phase 3, follow a real Street ID from a
    SADSR record through to `ALLDATA.KWI` Link ID / road geometry to test the
    indirection hypothesis end-to-end against a real, known WA location: this
    is now the most promising lead, more promising than further fixed-offset
    guessing on the index record itself.
- 2026-08-24: Raw ISO dump of `/dev/sr0` completed successfully
  (`original-disc/pajero-whereis-2007.iso`, 2,389,671,936 bytes, matches
  `blockdev --getsize64`, md5 `85fd52724443195d72a08ad8befccec7`) and a full file
  catalogue with best-guess purpose per file was written to
  `docs/phases/00-inventory.md`. Notable: `POISR205.IDX`/`POISR206.IDX` (~177MB/132MB)
  are the single largest data files on the disc after `ALLDATA.KWI` itself — POI
  search data dominates the index volume, more than street address search. **Phase 0
  is complete.** Next: Phase 1 format analysis, starting with cross-referencing the
  `IDX/` filename-prefix guesses against the archived Chapter 11 sub-section PDFs.
- 2026-08-25: Follow-up pass specifically testing the "Street ID -> Link ID ->
  main-map geometry" hypothesis from the previous entry, end-to-end against real
  `SADSR201.IDX` data (GADEN ROAD / GINGIN BROOK ROAD / GINGIN ROAD, real WA
  streets). **Hypothesis not confirmed** (full detail in
  `docs/phases/01-format-analysis.md`, "Street ID -> Link ID indirection
  hypothesis, tested end-to-end"). Progress made: re-read the archived
  Ch.11.A.2.14/11.A.2.4 PDFs and confirmed the exact spec chain this hypothesis
  describes (alphabetical record -> Address Range Search record -> Street
  Address POI Information record, which is where real RLXY/Link ID actually
  live per the spec); and found that the alphabetical record's previously
  "16 opaque bytes" splits cleanly into four 4-byte fields
  (`area_code`/`street_id`/`next_level_field`/`tail`, zero remainder) --
  implemented as properties on `AlphabeticalMatchingRecord` in
  `parser/kiwiw/index_data.py`. The blocker: none of six tried offset/base
  transforms for `next_level_field` (the pointer candidate) resolve to the
  expected Address Range Search record shape. Recommendation, if this is still
  unresolved by Phase 3: treat it as a hard-time-boxed research spike rather
  than an open blocker, since Phase 3 could instead match OSM street names
  directly to the already-solved main-map link geometry and skip reproducing
  the original disc's exact index indirection chain.
- 2026-08-25: **Address/POI search chain SOLVED end-to-end.** A typed street name
  now resolves to a real WA lat/lon, and so does a POI name — closing the last
  known gap in "full feature parity" (main map roads/names/geometry were already
  solved). Full writeup: `docs/phases/01-format-analysis.md`, "Address / POI
  search chain: SOLVED end-to-end". New code `parser/kiwiw/search_frame.py`,
  fix + corrected record layout in `parser/kiwiw/index_data.py`, demo
  `parser/demo_address_search.py` (replaces `demo_street_id_link.py`).
  - **Root cause of the three-pass blocker was a one-line bug in our own
    parser**, not a gap in the format: the 4-byte absolute file offset inside an
    "Additional \*\*\*Address" table entry is itself SWS-halved. We were reading
    it raw, so every frame pointer in every `.IDX` resolved to half its true
    offset — i.e. to garbage. That is why the "category tree" looked unparseable,
    why the alphabetical records seemed to be in the wrong frame, and why none of
    the six previously-tried pointer transforms could ever have worked.
  - **The index files are self-describing.** Each Matching Data Frame is preceded
    by a `DCTF` Matching Data Definition Frame listing its records' fields, types
    and counts; combined with each record's `STFG` presence bitmap (per-byte,
    LSB-first, covering the fields declared after it) this parses any record in
    any search frame with zero hardcoded offsets. The new module is generic over
    street, address-range and POI frames alike.
  - Chain: `SADSR201.IDX` DFSR -> `SRMX` -> alphabetical street records
    (38,120) -> `NXST`×2 into a *nested* DFSR/`SRT1` "ADDRESS RANGE" frame ->
    address-range records (344,276) carrying **inline** `RLXY` coordinates and
    `LKID` link IDs. `RLXY` is the `P6` type = two 3-byte angles decoded by the
    *existing* `bitutils.geo_secs()` — no new coordinate decoder was needed; the
    previous passes' "coordinate formula" search was chasing the wrong problem.
  - **Validation (HIGH confidence).** Decisive check: decoding all 344,276
    address ranges yields lat -35.125..-14.292, lon 113.438..128.938 with *zero*
    outliers — Western Australia's real extent, including the artificial 129°E
    NT/SA border meridian. The 108,511 geocoded POIs reproduce the same box
    independently. Shape checks corroborate: GREAT EASTERN HIGHWAY spans Perth to
    Kalgoorlie (121.44), ALBANY HIGHWAY spans Perth to Albany (-35.04), HANNAN
    STREET lands in Kalgoorlie, BURSWOOD CAR RENTALS lands in Burswood. All three
    frames parse to exactly their declared record counts.
  - **Remaining (non-blocking):** `ARCD` area-code and POI `CTGY` category
    *values* are not yet mapped to names (the tables are located, not parsed);
    `LKID` has not been cross-checked against `ALLDATA.KWI` yet, see next point.
  - **Side finding — a pre-existing bug in already-"solved" main-map code.** The
    working index chain is now an independent geographic oracle, and it caught
    `dump_parcel.py` returning Rockingham streets (~40 km south) for a Perth CBD
    parcel whose *bounds* it computes correctly. `mesh.py`'s parcel-index /
    iteration-order assumption (already flagged "unconfirmed, row-major
    lat-then-lng" in the phase doc) selects the wrong parcel record. Not fixed
    here — out of scope for this pass — but now cheap to debug, and it should be
    fixed before Phase 2 byte-diffing, since it means main-map parcel addressing
    is not actually verified.
