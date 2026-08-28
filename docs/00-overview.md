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
- Whether the route-planning "ext" frames (Ch.10.5, vendor-proprietary, 12.7% of all
  route-planning bytes) are required by the head unit's routing firmware to function,
  or safely omittable — **partially resolved 2026-08-27**: the 12-byte "User
  Identification ID" (confirmed = the disc-build stamp) and one of the four
  Data-Identification-Code types (a constant 4-byte version flag, `0xAF100600`) are
  now confirmed safe to reproduce as constants (~0.2% of ext bytes). The other two
  types — `0xAF100100` (62.1% of ext bytes, present in every region) and
  `0xAF100300` (37.7%, level-8-only) — had their byte *shape* (not semantic meaning)
  further analyzed 2026-08-27: `0xAF100300`'s record layout is now fully pinned (HIGH
  confidence: 4-byte header + count×12-byte records, 100% exact fit, no exceptions),
  and its presence was found to be the exact logical inverse of a region having
  boundary nodes at level 8 — but *why* is still unknown, and `0xAF100100`'s shape
  remains unresolved beyond ruling out a fixed-tuple/matrix layout. **Decision
  2026-08-27: since purpose/semantics for both remain unresolved and cannot be
  reproduced faithfully, the writer will proceed WITHOUT generating these two ext
  types for the initial from-scratch build** (the disc-round-trip/regenerate-original
  path is unaffected, since there we copy real bytes rather than needing to
  synthesize them) — in-vehicle testing will show whether the head unit tolerates
  their absence; if not, this is the first thing to revisit. See
  `docs/phases/01-format-analysis.md`'s ext-frame census and shape-analysis
  subsections for full evidence and ranked hypotheses.

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
- 2026-08-25: **Phase 2 (round-trip writer) started — first real
  byte-identical wins.** Targeted the smallest, most fully-understood files
  rather than `ALLDATA.KWI`/`IDX/*` (full detail:
  `docs/phases/02-roundtrip.md`). New code: `parser/kiwiw/misc_writer.py`
  (inverse of each `parse_*` in `parser/kiwiw/misc.py`), harness
  `parser/roundtrip_misc.py`, regression test
  `parser/tests/test_roundtrip_misc.py`.
  - **5 of 7 targeted files round-trip byte-identical** against the real
    mounted disc: `PCT2MNG.KWI`, `COVERAGE.BIN`, `DN/CLUSTER.DAT`,
    `COUNTRY.KWI`, `VERSION.TXT`.
  - Notable finding: `COUNTRY.KWI` round-trips exactly *despite* its
    trailing TLV-like block being explicitly flagged "not spec-confirmed" in
    Phase 1, because the parser stored that unconfirmed region verbatim
    (`raw_tail`) instead of forcing it through a lossy reinterpretation.
    Lesson for future Phase 2 work on `ALLDATA.KWI`/`IDX/*`: preserve
    not-yet-understood byte regions raw rather than round-tripping them
    through a partial model.
  - **2 honest failures, not smoothed over:** `SPEC.KWI`/`METADATA.KWI`
    fail by 1-2 bytes because `parse_bnf_metadata` (shared Phase 1 code,
    deliberately not modified here) collapses each file's irregularly-
    whitespaced `KEY ::= value ;` statements into a plain dict, which can't
    reconstruct the original spacing quirks. Root cause and exact byte diff
    are in `docs/phases/02-roundtrip.md`.
  - **Not attempted:** `ALLDATA.KWI` (main map data) and `IDX/*.IDX`
    (search index) writers — both substantially harder (medium-confidence
    coordinate decoding, ~50%-identified road-type codes, several
    known-unhandled record kinds in the main map; self-describing
    `DCTF`/`STFG` regeneration for the index chain) and explicitly deferred,
    see the roundtrip doc's "what remains" section for the recommended
    next steps.
- 2026-08-25: **Parcel-index bug (the "Side finding" above) root-caused and
  fixed in `mesh.py`.** Full derivation and validation:
  `docs/phases/01-format-analysis.md`, "Parcel iteration-order bug: ROOT
  CAUSE FOUND AND FIXED".
  - **Root cause was not the row-major ordering itself.** The archived spec
    (`0600122e.pdf`, Ch. 6.1.2/6.2.1/6.3.1) explicitly states row-major,
    latitude-outer/longitude-inner ordering at every level of the
    blockset/block/parcel hierarchy — `mesh.py`'s existing convention there
    was already correct, so the earlier "unconfirmed, row-major lat-then-lng"
    caveat in the phase doc is now **resolved: confirmed correct**. The real
    bug was that `locate_parcel()` computed the top-level parcel's array
    index by taking the query point's *fractional position within its own
    already-finest grid cell* and multiplying it by the same per-level
    parcel-count factor that had *already* been folded into the grid indices
    used to find that cell in the first place — double-applying the factor.
    The parcel's displayed *bounds* never depended on that buggy index (they
    come straight from the grid indices), so bounds stayed correct while the
    actual data record fetched was effectively arbitrary. This is exactly
    why a Perth CBD query reported a correct Perth CBD bounding box but
    decoded Rockingham/Baldivis street and place names ~40 km south.
  - **Fix**: use the already-correctly-computed grid coordinates directly for
    the first (top-level, depth-1) parcel lookup; only use the
    fractional-position calculation for genuine deeper divided/integrated
    sub-parcel recursion (depth > 1), where it's actually needed since that
    subdivision isn't captured by the outer grid indices.
  - **Validation**: the reported Perth CBD coordinate now decodes real
    Perth CBD content ("190 ST GEORGES TERRACE", Perth CBD/Northbridge/West
    Perth/Kings Park suburb labels). Broad statistical cross-check against
    the address-search oracle (`search_frame.py`): 800 randomly sampled real
    WA street/address-range coordinates fed through the fixed `mesh.py`,
    checking whether the located main-map parcel's own decoded name records
    mention the same street — **799/800 (99.9%) agreement, 0 parcels not
    found**; the one miss still landed in the correct immediate neighbourhood
    (a parcel-boundary edge case, not a wrong-suburb error). The three
    original Phase 1 test coordinates (Melbourne, Sydney Harbour, and one
    previously mislabeled "regional NSW/Hunter Valley" point that is actually
    in Sydney's Camellia/Granville area) were re-run and now decode more
    specific, more plausible real content; the old results for two of them
    are reinterpreted as likely undetected instances of this same bug rather
    than genuine independent confirmations. `parser/tests/test_mesh.py`
    updated accordingly (containment-based bbox check for the now-deeper
    Melbourne subparcel result, corrected Sydney/Camellia commentary); no
    regressions in `parser/tests/test_roundtrip_misc.py`.
  - **Confidence: HIGH.** Main-map parcel selection (not just bounds) is now
    independently cross-checked against a large, real, oracle-verified
    sample rather than a single hand-picked coordinate — clearing the
    concern raised in the "Side finding" entry above before Phase 2
    byte-diffing work on `ALLDATA.KWI` begins.
- 2026-08-25: **`SPEC.KWI`/`METADATA.KWI` whitespace-loss round-trip gap
  fixed — Phase 2 misc-file round-trip now 7/7, up from 5/7.** Full
  writeup: `docs/phases/02-roundtrip.md`, "Update: SPEC.KWI/METADATA.KWI
  whitespace loss fixed". The two files' irregular per-statement whitespace
  (no general rule found — e.g. METADATA.KWI's `CHCD` statement has a
  leading space and a space before `::=` that neither `LANG` nor `COOR`
  have) turned out not to need a whitespace-formatting model at all:
  `parse_bnf_metadata` (`parser/kiwiw/misc.py`) now returns a `BnfMetadata`
  dataclass holding the *raw* `text.split(";")` chunks verbatim
  (`raw_statements`) alongside the same stripped-key/value `dict[str, str]`
  convenience view as before (`fields`), and `write_bnf_metadata`
  (`parser/kiwiw/misc_writer.py`) just rejoins `raw_statements` with `;` —
  an exact inverse of `split`, not a best-effort reformat. Only two call
  sites existed (`parser/roundtrip_misc.py`, unaffected since it treats the
  parsed value opaquely; `parser/tests/test_roundtrip_misc.py`, updated
  from an expected-failure test to two passing byte-identical tests). This
  supersedes, not erases, the earlier 2026-08-25 "Phase 2 round-trip
  writer" entry above's "2 documented, honest failures" — those two
  failures are now fixed, and the phase doc's own copy of that finding is
  marked resolved rather than rewritten.
- 2026-08-25: **Phase 2 extended to `ALLDATA.KWI`'s container/mesh layer —
  3/3 regions byte-identical (25,184 bytes).** This closes "what remains"
  item 2 in `docs/phases/02-roundtrip.md` (see its section "ALLDATA.KWI
  container/mesh layer: byte-identical" for the full writeup). New code:
  `parser/kiwiw/volume_writer.py`, parse-side additions in
  `parser/kiwiw/volume.py` / `model.py` / `bitutils.py`, harness
  `parser/roundtrip_alldata_header.py`, regression test
  `parser/tests/test_roundtrip_alldata_header.py`.
  - **Targets, all byte-identical against the real mounted disc:** the
    Ch. 5.1 Data Volume (2048 B at offset 0), the Ch. 5.2 Management
    Header Table (2048 B at 2048), and the Ch. 6 Parcel-related Data
    Management Record — PDMDH header + 7 LMRs + 601 BSMRs + 165 Block
    Management Tables (2307 block entries) + padding (21,088 B at 6144).
  - **Phase 1's "high confidence" rating for this layer is confirmed** —
    but the write direction still forced out three things a read-only
    parser had no reason to notice: (a) the LMR is **170 bytes**, and its
    previously strode-over 128-byte remainder is three `u16` sub-frame
    index tables sized exactly by the extended-info word's road/background
    /name frame counts (`42 + 2*(16+32+16) = 170`, zero bytes left over on
    all 7 levels); (b) the Management Header Table is a single 2048-byte
    table whose spec-"RESERVED" maker-original area is used by this disc as
    **more of the same 18-byte records** — `kiwiread.c` and our
    `parse_mhr_table()` both stop at 34 records, one short of the real
    in-use `COUNTRY.KWI` entry at index 34; (c) the 165 BMT tables tile
    offsets 7230..21072 of the management record with **zero gaps or
    overlaps**, and every table's entry count matches the entry count its
    level's LMR implies — independent structural corroboration of the
    block/parcel addressing that the recently fixed `mesh.py` lookup relies
    on.
  - **Anti-self-deception measures** (this is the point of Phase 2, so they
    are documented rather than assumed): writer buffers are poison-filled
    with `0xA5` instead of zeros so a forgotten region cannot accidentally
    match a zero-filled original; raw disc bytes are never handed to the
    writer, only the parsed IR; record offsets are re-derived from the
    parsed structure rather than copied; and six negative controls
    (perturbing one decoded value each, plus dropping a whole BMT table)
    were verified to produce FAILs.
  - **Honest remainder:** 1694 of the Data Volume's 2048 bytes are carried
    through verbatim, though only **27 of those are non-zero** (inside the
    maker-defined halves of the MID:C identification fields, which the
    spec leaves to the manufacturer; note the "data author" one is binary,
    so Phase 1's `data_author_id` *string* is a truncation and could not
    have rebuilt it). The rest are the spec's RESERVED areas plus the
    256-byte Level Management Information area, which is entirely zero on
    this disc — **so that sub-structure remains untested**. The other two
    regions are 99.3% and 99.9% rebuilt from decoded typed fields.
  - **Not attempted, stated explicitly:** the separate 2048-byte management
    frame at file offset 4096 (pointed at by management header record 29),
    and all parcel content — road, background and name frames, plus the
    parcel management records the BMT entries point at. The phase doc's
    "concrete next steps" section proposes the staged path: parcel
    management records first, then the Map Frame header + Main Map Data
    Frame Entry table (structure only, sub-frame payloads left opaque),
    and only then per-frame content writers with undecoded record kinds
    preserved as raw bytes.
  - No regressions: `parser/tests/test_mesh.py`, `parser/roundtrip_misc.py`
    (still 7/7) and `parser/dump_parcel.py` all behave as before.
- 2026-08-25: **Route planning data (Ch.9/Ch.10) format and size-scaling
  investigated.** Full writeup: `docs/phases/01-format-analysis.md`, "Route
  planning / region data (Ch.9 + Ch.10, 2026-08-25)". This is the last major
  region of `ALLDATA.KWI` that was uncharacterized in the size-budget
  analysis (9.9% of the file). Confirmed it must be regenerated from OSM road
  topology — it's a routing graph, not content-independent like voice data.
  - Structural/framing layer (region tables, per-region subframe directory,
    node/link census headers) decoded and validated against **all 1,864 real
    regions on the disc (100% of the population)**: subframe-size totals
    account for 99.98% of the disc's own declared per-region byte counts.
    Individual record layouts are fully bit-specified in the spec with no
    ambiguity found, but not yet round-tripped byte-for-byte in code.
  - Size scales with the routing graph's own node/link counts, not road-km or
    region area: `route_planning_bytes ≈ 4,695 + 10.26·n_nodes + 18.36·n_links`
    (R²=0.983, n=1,864). An OSM-junction-count proxy is the best *external*
    stand-in (r²=0.68) if node/link counts aren't known yet, but road-km
    (r²=0.35) and region bbox area (r²=0.03) are poor predictors — Ch.9
    region bboxes turned out not to be spatial partition tiles, they overlap
    heavily.
  - **Genuine open unknown**: 12.7% of route-planning bytes are vendor-
    proprietary "ext" frames the spec explicitly leaves undefined. Whether
    the head unit's firmware requires this data to function is untested.
  - **Scope for a writer**: the Ch.9/Ch.10 byte-encoding work itself is
    low-to-moderate (day-to-low-single-digit-days range) once a routing graph
    model exists. The real bottleneck is building that graph in the first
    place — a CH/highway-hierarchy-style multi-level graph contraction from
    OSM roads (ranks, 4 coarsening tiers, boundary-node bookkeeping, turn
    restrictions, aggregated-intersection clustering) — comparable in scope
    to a route-planning preprocessor built from scratch, and dwarfing the
    encoding work.
  - Next: fold the confirmed node/link-count scaling formula into the
    size-budget artifact's route-planning projection (replacing the earlier
    unverified km-fraction placeholder), and decide whether resolving the
    "ext" frame question is worth a dedicated investigation before Phase 3
    planning proceeds further.
  - Size-budget artifact updated same day with these findings (route-plan
    column footnote + §07 gap-list item rewritten to reflect the decoded
    format and node/link-count formula rather than the old km-fraction
    placeholder).
- 2026-08-25: **First working Ch.9/Ch.10 route-planning writer prototype,
  built and tested.** Full writeup: `docs/phases/03-osm-pipeline.md`, "Early,
  out-of-sequence work: route-planning writer prototype". Per explicit
  instruction, the writer matches vendor structure by default (every spec
  field/frame present, including the undocumented "ext" frames) rather than
  omitting anything without positive evidence it's unused. New code:
  `parser/kiwiw/route_planning_writer.py`, `parser/build_route_graph.py`,
  `parser/osm_to_route_planning.py` (committed `41d062e`).
  - Tested against region 178/level 2 (real disc region, WA): OSM-derived
    graph encodes to 114,216 bytes and round-trips fully self-consistently
    through the decoder. No regressions (`parser/tests/` 13/13).
  - Found and resolved a genuine spec-vs-disc discrepancy: Link Cost Records
    are 14 bytes, not the spec's implied 16, when a rank's `avg_travel_time`
    flag is false.
  - **Key quantified finding**: OSM's raw major-road intersection graph for
    this region's exact bbox is **26.6x** larger (2,819 nodes/5,567 links) than
    the real disc's own graph (106 nodes/282 links) — direct evidence of how
    much CH/highway-hierarchy-style contraction a real pipeline must perform,
    previously only assumed qualitatively.
  - Confirms the byte-encoding work is tractable (~1 session); the real
    bottleneck remains building genuine multi-level graph contraction across
    many regions with cross-region boundary handling — not attempted yet,
    this prototype covers one standalone region only.
- 2026-08-27: **Dedicated ext-frame content census, all 1,864 real regions
  (not a sample).** Full writeup:
  `docs/phases/01-format-analysis.md`, "Ch.10.5/10.5.1 'ext' frame content
  census". New script: `parser/analyze_ext_frames.py`. Findings, in
  confidence order:
  - **CONFIRMED**: the 12-byte MID ("User Identification ID") field is the
    same cross-file disc-build stamp already found elsewhere on the disc,
    byte-identical in all 5,105 populated ext slots. Safe to reproduce as a
    constant.
  - **CONFIRMED**: of the 4 distinct "Data Identification Code" values seen
    (`0xAF100100/0200/0300/0600`), one (`0xAF100600`) is a constant 4-byte
    flag in literally every one of the 1,864 regions. Safe to reproduce as a
    constant. Together with the MID finding, this resolves ~0.2% of ext-frame
    bytes as confirmed-safe stamp/versioning data.
  - **Correction to the prior "1-2 of 6 slots populated" finding**: every
    real region populates exactly 2 or 3 of the 6 ext slots, never fewer or
    more — confirmed disc-wide, not just spot-checked.
  - **Refuted**: ext-frame presence does not correlate with boundary/frontier
    regions — all 187 regions with child regions (and all 1,677 without)
    carry populated ext data equally. The "cross-region boundary link table"
    theory doesn't hold on this disc.
  - **Still open, NOT safe to omit**: the other two Data Identification
    Codes — `0xAF100100` (62.1% of all ext bytes, present in every region,
    medium-confidence read as a sentinel-filled cost/distance table) and
    `0xAF100300` (37.7%, level-8-only, weak circumstantial link to the
    disc-unused basic "Upper Level Link" subframe) — remain functionally
    unresolved. Together these two hold 99.8% of all ext-frame bytes, so the
    byte-budget risk is essentially unchanged even though the *field-level*
    ambiguity is now mostly resolved (2 of 4 codes confirmed, but they're the
    two smallest).
  - Confirms the size-budget cross-check from the 2026-08-25 route-planning
    finding: the four codes' bytes sum to exactly 19,164,296 B, matching that
    section's population-wide ext total.
  - No external precedent search (web) was performed this pass — remains a
    genuinely open avenue, not a source ruled out.
- 2026-08-27: **Aggregated-intersection clustering (Ch.10.13 Road Reference
  Table) implemented — was previously deferred as a "decision," now
  measured and built.** Full writeup: `docs/phases/01-format-analysis.md`,
  "Ch.10.13 Road Reference Table (aggregated-intersection clustering,
  2026-08-27)", and `docs/phases/03-osm-pipeline.md`, "Aggregated-
  intersection clustering implemented". New/changed code:
  `parser/survey_road_reference_table.py` (new), `parser/kiwiw/route_planning.py`
  (`parse_road_reference_table` + node/link/link-cost record decoders
  added), `parser/kiwiw/route_planning_writer.py` (`RpAggregatedNode`,
  `write_aggregated_node_record`, non-empty `write_road_reference_table`),
  `parser/build_route_graph.py` (`cluster_nodes`), `parser/osm_to_route_planning.py`
  (wired in + road-ref round-trip check), `parser/tests/test_route_planning.py`
  (new, 7 tests).
  - **Measured, disc-wide (100% of 1,864 real regions), not assumed**: the
    table is populated on 89.6% of regions (1,670/1,864), 218,440
    Aggregated Node Information records total, 92.4% of them in level-8
    regions. This falsifies the prior "always write it empty" prototype
    simplification — it was NOT a safe no-op.
  - **Clustering rule implemented** (best-effort OSM-side heuristic, since
    there's no way to check it node-for-node against the real disc's own
    clustering): merge (1) OSM `junction=roundabout`/`circular` node
    rings, and (2) connected components of non-boundary nodes joined by
    links shorter than 20 m — the latter targeting the real disc's own
    dominant pattern (median 2 composition links / 1 subordinate node per
    record, i.e. usually two nodes merging into one).
  - **Byte layout**: the record's fixed envelope is HIGH confidence
    (zero decode errors across all 218,440 records; `node_number`
    100%-cross-validated against the Node Table's `is_aggregated` flag).
    The internal variable-length arrays' padding rule was reverse-
    engineered from byte arithmetic (the spec text for this item was
    garbled in the archived PDF) — a "pad to the next even record-relative
    offset" rule lands on exact byte-accounting for 95.6% of all real
    records; documented as MEDIUM-HIGH/best-effort, not spec-confirmed.
  - **Validation**: re-running the region-178 prototype (see the
    2026-08-25 entry above) with clustering enabled drops the raw-OSM-vs-
    real node ratio from 26.6x to **14.3x** (2,819 -> 1,518 nodes, 402
    clusters), with a full RP-frame round trip through both the shared
    decoder and this script's own record decoders reporting zero problems
    — including a new check that the written road-reference table decodes
    back to the exact cluster metadata produced. All 25 tests in
    `parser/tests/` pass (18 pre-existing + 7 new).
  - Independent of the parallel multi-level/CH-contraction work: this
    clustering is a final post-processing pass on an already-built
    single-region graph and doesn't touch cross-region boundary handling;
    it does not yet propagate the `RpNode.global_id`/
    `uppermost_identical_level` fields added by that parallel work onto
    merged cluster nodes (currently just takes the representative's) —
    flagged for whoever combines the two, not resolved here.
- 2026-08-27: **Real multi-level (2/4/6/8) Contraction Hierarchies
  implemented — replaces the OSM-highway-class heuristic with genuine CH
  node contraction, and wires real cross-region boundary Link Records.**
  Full writeup: `docs/phases/03-osm-pipeline.md`, "Real multi-level
  (2/4/6/8) CH contraction + cross-region boundary links". New/changed
  code: `parser/kiwiw/contraction.py` (new — edge-difference priority,
  bounded witness search, level assignment by contraction rank),
  `parser/study_region_hierarchy.py` (new — real-disc region-tree study),
  `parser/build_route_hierarchy.py` (new — the multi-region orchestrator:
  one flat OSM graph -> global CH contraction -> 4-level parent/child
  region tree -> per-region `RpGraph`s -> Ch.9/Ch.10 encoding),
  `parser/kiwiw/route_planning_writer.py` (`RpNode.uppermost_identical_level`/
  `global_id` fields, `RpLink.region_number` field), `parser/osm_to_route_planning.py`
  (variable-size 6/8-byte link-record decode + `region_number` wired
  through `encode_rp_frame`), `parser/tests/test_contraction.py` (new, 5
  tests), `parser/tests/test_boundary_links.py` (new, 3 tests).
  - **Region tree confirmed a genuine parent/child tree, not spatial
    tiling** — 507/507 (100%) parent/child index-consistency, decoded
    across all 1,883 real region records (100% of the population). Level
    order confirmed empirically (2 finest -> 8 coarsest), correcting an
    initial wrong assumption (author first guessed the opposite direction,
    caught by directly measuring mean area/children/nodes per level).
  - **Spec-confirmed boundary-node definition** (via `pdftotext` on the
    archived spec PDF): a boundary node is one with a link to another
    region; Ch.10.7.1.1's Region Number field (present as an extra 2 bytes
    on ALL of a boundary node's link records, not just the crossing one)
    already had writer-side support in the very first prototype commit —
    unused until now. Wired up as "escape links" from a boundary node to
    its own instance in the parent region.
  - **CH correctness validated, not just asserted**: 100/100 sampled
    shortest-path checks match with 0 mismatches at every one of the 4
    levels, both on synthetic graphs (`test_contraction.py`) and on the
    real OSM extract's flat graph (`build_route_hierarchy.py`'s own
    `validate()`), comparing shortest path in the CH-contracted graph
    (restricted to that level's surviving nodes) against the original,
    fully uncontracted graph.
  - **End-to-end run over real OSM data**: a 3,475-node flat graph
    (motorway/trunk/primary/secondary+tertiary classes, matching what's
    actually present across the real disc's 4 levels per the study) built
    a 9-region 4-level tree (4 level-2 + 2 level-4 + 1 level-6 + 1 level-8,
    + the dummy root), 7/7 parent/child consistency, 8/8 regions
    round-tripped byte-for-byte with zero problems including the new
    boundary-link checks. `parser/tests/`: 28/28 pass.
  - **What's still assumed, not proven**: the per-level node-population
    split (`DEFAULT_LEVEL_FRACTIONS`) is a defensible geometric-decay
    shape, not a measured disc statistic (no real per-level population
    figure was ever established — only level order and per-level
    road-class narrowing were). The specific choice of "boundary link goes
    to the parent region" is one defensible reading of the spec's broader
    "link to another region" definition (which also covers same-level
    sibling regions, not exercised by this test area's tree shape).
    `uppermost_identical_level`'s bit encoding is not independently
    spec-confirmed. The region tree itself (2x2 leaf grid, pairwise merge)
    is a small demonstration shape, not a load-balanced country-scale
    tiling strategy — building that at scale remains future work.
  - Independent of / composes with the parallel clustering work above:
    this task's region tree produces a plain `RpGraph` per region, which
    could still be passed through `cluster_nodes()` as a final
    post-processing step; no shared files were modified by both efforts in
    a conflicting way. Turn restrictions, non-default ext frames unchanged
    (out of scope).
- 2026-08-27: Dedicated ext-frame *shape* analysis (structure, not semantics) for
  the two still-unresolved Data Identification Codes, via a new read-only script
  `parser/analyze_ext_frame_shape.py` (100% of the 1,864 real regions, no
  sampling). Findings (full detail + confidence levels in
  `docs/phases/01-format-analysis.md`):
  - **`0xAF100300` (level-8-only) — shape now fully pinned, HIGH confidence**:
    100.00% exact fit as `4-byte header (tag 0x0002 + count) + count×12-byte
    records`, zero exceptions across 1,326 occurrences. Each record decomposes
    into `[u32 strictly-increasing ID][u16 field, range 0-223][u16 value][u16
    duplicate of that value][u16 zero tail]`. The ID field draws from only 3,165
    distinct values reused across 599,181 record instances (mean reuse 189x) —
    looks like a small shared registry, not a per-link unique ID. New structural
    finding: this code's presence is the *exact* logical inverse of a region
    having boundary nodes at level 8 (100%, 1,357/1,357 regions, zero
    exceptions) — directly relevant to the boundary/escape-link work above, but
    the inverse relationship argues against a literal cross-region link table
    reading. Semantic purpose still unknown.
  - **`0xAF100100` (all regions, 62.1% of ext bytes) — shape still unresolved,
    MEDIUM confidence at best**: no fixed record size fits cleanly at any tested
    width (2-32 bytes), ruling out a simple fixed-tuple/matrix layout. The
    `0x7FFF` sentinel is placed with perfectly uniform word-granularity.  77.5%
    of non-sentinel 16-bit values are >=4096, consistent with cost/distance-style
    content. Correlation tested against every known per-region quantity (nodes,
    links, boundary nodes, boundary-nodes-squared, road-reference-table records,
    child-region count, escape-link count) — none fits (r=0.07-0.35, near-zero
    exact match). This pass narrows what it isn't more than what it is.
  - **Decision**: since neither code's purpose/semantics is resolved, they
    cannot be faithfully reproduced — see the "Open risks" entry above for the
    resulting decision to build the from-scratch writer without generating
    these two ext types for now, deferring to in-vehicle testing to see if
    that's tolerated.
- 2026-08-28: **`IDX/*.IDX` search-index writer landed — 232/232 structural
  checks byte-identical, including a full scan of all 38,120 street records.**
  New `parser/kiwiw/index_writer.py` (inverse of `kiwiw/search_frame.py`),
  harness `parser/roundtrip_idx.py`, regression tests
  `parser/tests/test_roundtrip_idx.py`. Full detail in
  `docs/phases/02-roundtrip.md`; summary:
  - The generic self-describing frame machinery (`DCTF` definition-frame
    writer + `STFG`-gated Matching Data Record writer) is a single
    implementation reused unchanged for street name, address-range, and POI
    records — confirming the read side's "no hardcoded offsets" design also
    inverts cleanly. Validated: **all 38,120 street records** (full scan, not
    a sample), the anchor streets GADEN ROAD / GINGIN BROOK ROAD / GINGIN
    ROAD's address-range records, 2,000 sampled POI records, and all 3
    BURSWOOD CAR RENTALS POI records — every one byte-identical.
  - The SWS-halved "Additional ***Address" indirection-table entry (the field
    that bit the read side badly three times, per the decision-log entry
    above) round-trips exactly on every entry tested (6 of them, covering
    both SADSR201.IDX and POISR201.IDX, both the street and the nested
    address-range frames).
  - `DFSR` search-frame headers and the 92-byte Detailed Search Info Records
    (`SRMX`/`SRHA`/`SRT1`) round-trip exactly, using an explicit-known-fields
    IR with two small undecoded gaps (12 bytes at record offset 4, 12 bytes
    at offset 48) carried verbatim rather than reinterpreted — same
    discipline as `COUNTRY.KWI`'s `raw_tail`.
  - Negative controls confirmed live: perturbing a record's `STID`, a
    record's `KYCH` name, or a `FieldDef.count` in the definition frame each
    produce a different rebuild than the original — the passes above are not
    the harness comparing bytes to themselves.
  - **What is explicitly NOT attempted**: full-file reassembly of a whole
    `SADSR*.IDX`/`POISR*.IDX` from scratch. Every check above validates one
    structural piece against real bytes *at that piece's own byte range* in
    the existing file; nothing here re-derives *where in the file* a
    definition frame, matching-data frame, or additional-address entry
    should itself be placed — that's the disc's file-layout allocation
    strategy, a materially bigger and separate problem, left open the same
    way `ALLDATA.KWI` parcel content was left open after the container/mesh
    layer pass. `ARCD`/`CTGY` *values* remain located-but-not-mapped-to-names
    (unchanged from the read side) — since nothing here re-interprets them
    (they pass through as opaque integers in the generic record encoder),
    this doesn't block round-tripping, only semantic understanding.
  - One inferred, unvalidated branch flagged honestly rather than silently
    assumed: `write_frame_ref_entry`'s NUL-pad-to-even-length behavior for an
    odd-length filename never fires on this disc (both `IDX/SADSR201.IDX`
    and `IDX/POISR201.IDX` are 16 ASCII bytes, already even) — so that
    specific code path is unexercised by any real byte on this disc.
- 2026-08-28: **`ALLDATA.KWI` parcel-content writer landed — 8/8 checks
  byte-identical across 4 real parcels in 3 different Australian cities.**
  New `parser/kiwiw/parcel_writer.py` (inverse of `parcel_mgmt.py`/
  `parcel.py`/`road.py`/`background.py`/`name.py`), harness
  `parser/roundtrip_parcel_content.py`, regression tests plus 4
  negative-control tests in `parser/tests/test_roundtrip_parcel_content.py`.
  Full detail (all findings, confidence levels, and coverage caveats) in
  `docs/phases/02-roundtrip.md`'s "Parcel content writer" section; summary:
  - Both structural layers targeted by this pass are now byte-identical on
    Melbourne Docklands, Sydney Harbour, Sydney/Camellia-Granville, and
    Perth CBD: the Ch. 6 Parcel Management Record a Block Management Table
    entry addresses (24928/24832/24832/24640 bytes), and the Ch. 7 Map
    Frame + road/background/name content a leaf entry points at (28160/
    51808/81920/55552 bytes; 238/344/587/361 road links; 23/35/31/122
    background shapes; 82/193/282/241 name records — all byte-identical).
  - Confirmed (cross-referenced against `tools/kiwiread/kiwiread.c` as
    ground truth) and named a previously-mysterious field:
    `struct parman_t.routeoff`, a [D]-encoded pointer into the
    route-guidance parcel management list (out of scope, preserved
    verbatim). Also fixed a real read-side bug found while chasing this
    round-trip: the Name Data Record's `na` field (documented in
    kiwiread.c as "Size of Minimum Graphics Record") is the authoritative
    per-record length for every `string_type`, not just some; the old
    per-type length math for `string_type=4` was 2 bytes short, and the
    resulting cascading misalignment was the actual cause of the
    previously-observed phantom "`string_type=0`" records on every real
    parcel — not a real record kind. `name.py` no longer aborts decoding a
    name-data-list on an unrecognized `string_type` as a result.
  - Also discovered and fixed: the Main Map Data Frame Entry (mfde) table's
    true length is not derivable from any single LMR field
    (`n_basic_map`/`n_ext_map`/`n_basic_route`/`n_ext_route`) — it is
    self-describing, ending exactly where the road sub-frame's own content
    begins. Empirically 20 entries on every one of the 4 tested real
    parcels (medium confidence — empirically derived, not spec-confirmed;
    not verified on a parcel with different `n_basic_map`/`n_ext_map`).
    Two smaller previously-uncaptured real fields also fixed: the Road
    Data Frame's per-display-class "Display Flag" (kiwiread.c's
    `dispflag`) and its "Additional Data Management Records" content
    (table was already captured; the content those offsets point at was
    not).
  - Two **medium-confidence, not spec-confirmed** "leftover bytes" findings
    carried as raw/verbatim rather than modeled: a Block buffer's own
    declared size consistently runs 8.3–12.5 KB past everything the Parcel
    Management Record tree reaches (`ParcelMgmtRecord.tail_raw`), and a Map
    Frame buffer similarly has 6-16 trailing bytes past everything its own
    structure reaches (`MapFrame.tail_raw`, some fragments looking like
    stray ASCII text). Both cross-checked against kiwiread.c's own
    traversal logic (`showbmt()`), which never reads past the same point
    either — read as disc-mastering artifacts, not parser gaps, but this is
    an inference ("no known reader reaches it"), not a spec citation.
  - Negative controls confirmed live: perturbing one byte in a
    `ParcelMgmtRecord.tail_raw`, a `RoadLink.raw_bytes`, a
    `NameRecord.raw_bytes`, or a `MapFrame.tail_raw` each correctly breaks
    the round-trip.
  - **Coverage caveat, disclosed honestly**: all 4 test points are level 0
    with identical `n_basic_map=3`/`n_ext_map=9`; the mfde-table-length
    fallback path (used when no in-buffer offset exists among indices 0-2)
    is untested on real data; other levels are unexercised. mfde entries
    beyond index 2 whose offset resolves *outside* the buffer are inferred
    (not confirmed) to be route-guidance-related content belonging to the
    sibling route-planning layer, and are correctly left undereferenced —
    a boundary point worth flagging to whichever agent owns that layer.
  - This closes the last content-layer gap the 2026-08-25 `ALLDATA.KWI`
    container/mesh-layer entry above left open ("Parcel content remains
    untouched"). What's left for Phase 2's stated goal is unchanged:
    whole-file reassembly of `IDX/*.IDX` (this pass didn't touch that), and
    actual disc reassembly + in-vehicle testing.
- 2026-08-28: **Whole-file assembly (allocation/layout) landed for both
  `ALLDATA.KWI` and `IDX/*.IDX` — the last item "what remains" flagged after
  every prior Phase 2 pass.** Two parallel efforts, full detail in
  `docs/phases/02-roundtrip.md`'s new "Whole-file `ALLDATA.KWI` assembly"
  and "Whole-file `IDX/*.IDX` assembly" sections.
  - **`ALLDATA.KWI`** (new `parser/kiwiw/alldata_writer.py`, harness
    `parser/roundtrip_alldata_full.py`, tests
    `parser/tests/test_roundtrip_alldata_full.py`): reassembled whole real
    block sets (level 8, all 6 block sets/78 leaf parcels; level 6, one
    block set/227 leaf parcels) two ways — `assemble_inplace()` replicates
    the original's own offsets (byte-identical, 87/87 and 231/231 checks)
    and `assemble_denovo()` packs the same content into a fresh contiguous
    layout with rewritten pointers (internally self-consistent via re-parse
    only, 84/84 and 228/228). Allocation-rule confidence: sector alignment
    HIGH (exact inverse of `getsector()`); a block set's blocks are packed
    contiguously in block-index order — MEDIUM (one region's worth of
    evidence); leaf (Map Frame) placement order across the disc — WEAK, no
    rule found, real offsets increase but with unexplained gaps. Levels
    0/2/4 (holding most of the disc's real content) are not yet exercised.
  - **`IDX/*.IDX`** (new `parser/roundtrip_idx_full.py`, tests
    `parser/tests/test_roundtrip_idx_full.py`): whole `SADSR201.IDX`
    (15,387,684 bytes) reassembled byte-identical in "replicate" mode;
    "fromscratch" mode proven decode-equivalent via re-parse only.
    Allocation rule: zero-gap/zero-padding sequential packing, recursive —
    HIGH confidence for forward ordering (zero exceptions across the whole
    reachable tree), WEAK for `next_level` recursion order (reverse
    record order, witnessed only once). `POISR201.IDX` attempted but not
    completed — different top-level shape, decode bugs in 4 of 5 matching
    populations, left fully outstanding.
  - **Two genuine format bugs found and fixed** while chasing full-frame
    (not just prefix) byte accounting: `DCTF` definition frames' entry
    count excludes the header itself, not "including itself" as previously
    documented (`search_frame.parse_definition_frame`,
    `index_writer.write_definition_frame`) — under-parsed every definition
    frame on the disc by exactly one trailing field, invisible until now
    because that field is always STFG-gated off; and a `.strip("\x00 ")` vs
    `.rstrip("\x00 ")` bug that silently mis-padded a raw-integer-valued
    field decoded as ASCII. Both confirmed via the full existing suite
    re-run afterward with zero regressions (`roundtrip_idx.py` still
    232/232, all 38,120 street records still full-scan clean).
  - A pre-existing decode-overrun bug in SRHA's own "city name" matching
    records (1,285 records, never previously exercised) was found and
    documented, not silently fixed — the assembler falls back to verbatim
    copy for that population and flags it in its report rather than
    crashing or hiding it.
  - **Next / not yet done**: levels 0/2/4 of `ALLDATA.KWI`, `POISR201.IDX`
    whole-file assembly, and — the actual Phase 2 goal — assembling a full
    disc image (combining these with untouched loader/voice/image
    resources) and burning it for in-vehicle testing.
