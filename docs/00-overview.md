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
- 2026-08-24: Raw ISO dump of `/dev/sr0` completed successfully
  (`original-disc/pajero-whereis-2007.iso`, 2,389,671,936 bytes, matches
  `blockdev --getsize64`, md5 `85fd52724443195d72a08ad8befccec7`) and a full file
  catalogue with best-guess purpose per file was written to
  `docs/phases/00-inventory.md`. Notable: `POISR205.IDX`/`POISR206.IDX` (~177MB/132MB)
  are the single largest data files on the disc after `ALLDATA.KWI` itself — POI
  search data dominates the index volume, more than street address search. **Phase 0
  is complete.** Next: Phase 1 format analysis, starting with cross-referencing the
  `IDX/` filename-prefix guesses against the archived Chapter 11 sub-section PDFs.
