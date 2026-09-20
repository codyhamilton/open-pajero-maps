# Phase 0 — Project docs, archive, and inventory

## Goal

Get the ground truth pinned down before any parsing/writing work starts: an exact
raw copy of the source disc, the official spec archived locally, the existing
`kiwiread` tool built and run against this specific disc, and a file-by-file
catalogue tying disc contents to spec chapters where known.

## Tasks

- [x] Raw ISO image of `/dev/sr0` (not just a filesystem-level copy) → `original-disc/pajero-whereis-2007.iso` (2,389,671,936 bytes, matches `blockdev --getsize64`, md5 `85fd52724443195d72a08ad8befccec7`)
- [x] File catalogue with sizes and best-guess purpose → below
- [x] Archived KIWI-W v1.22 spec fetched locally → `spec/` (68 files, full byte-level spec, see `spec/INDEX.md`)
- [x] `kiwiread` cloned, built, run against this disc's `ALLDATA.KWI`/`LOADING.KWI` → `tools/kiwiread/` (works, see Findings)

Phase 0 is now complete. Ready to start Phase 1 (format analysis).

## File catalogue

Top-level (sizes in bytes):

| File | Size | Best-guess purpose |
|---|---|---|
| `ALLDATA.KWI` | 1,529,729,025 | Main map data volume (Ch. 5/6/7) — roads, background, names. Confirmed by `kiwiread`. |
| `LOADING.KWI` | 31,338,496 | Loading module (Ch. 30) — boot/executable resources for the head unit. Confirmed by `kiwiread`. |
| `COUNTRY.KWI` | 113 | Country/language table — encodes "AUSTRALIA" (seen via hex dump in planning). |
| `SPEC.KWI` | 34 | `SUPERMETA::=AFAU:2.64, AGAU:2.64` — format/data version tags for AU. |
| `METADATA.KWI` | 164 | Language list, charset (ISO-8859-1), coordinate system (WGS84) — Ch. 13 Metadata. |
| `VERSION.TXT` | 19 | Plain text: `COMMENT=2007 ver.1;`. |
| `COVERAGE.BIN` | 21 | Small binary, likely coverage-region flags/bounds summary. |
| `COVERAGE/AUC.BMP` | 30,648 | Bitmap of Australia coverage outline (for on-screen coverage display). |
| `DN/CLUSTER.DAT` | 272 | Small binary, purpose unconfirmed — "DN" possibly "Data Number"/disc-set/cluster table for multi-disc sets. |
| `INDEXDAT.KWI` | 100,980 | Index data-management frame, likely Ch. 11.2. |
| `DICVCE56.KWI` | 4,377,384 | Voice-guidance-related (name suggests "voice" dictionary) — Ch. 34 Voice Data Frame. |
| `HWMAP.KWI` | 112,190 | Likely "highway map" overview data, possibly freeway/highway search support layer. |
| `GRA256D.KWI`, `KGRA256.KWI` | 1,165,934 / 5,954 | Likely graphics/image tile data pair (256-related = probably 256x256 tile size) — Ch. 33 Image Data Frames. `K`-prefixed file is likely a small key/index table for the larger data file — this pairing pattern (`XXX.KWI` + `KXXX.KWI`) repeats for PCT/GRA below. |
| `PCT256D.KWI`, `KPCT256.KWI` | 2,082,630 / 5,954 | Same pairing pattern, likely a second image/palette tile set ("PCT" = palette/picture?). |
| `PCT2DAT.KWI`, `KPCT2DT.KWI` | 2,070,740 / 4,668 | Same pattern again, a second-generation/alternate PCT set. |
| `PCT2MNG.KWI` | 174 | Small management/header file for the PCT2 set. |
| `KGRPDAT.KWI` | 4,668 | Small key/group data file, likely paired with GRA/PCT sets above. |
| `VAR256D.KWI` | 181,132 | Likely variable-length supplementary data for the "256" tile sets. |

`IDX/` (all files map to Chapter 11 "Management Pattern of Index Data" search structures — filename prefixes strongly suggest which sub-section):

| Prefix pattern | Likely Ch. 11 section | Notes |
|---|---|---|
| `SADSR2##.IDX` | 11.A.2.4 Street Address Search | Large files (up to ~35MB), the core address-search index — critical for "full parity" address search goal. |
| `POISR2##.IDX`, `POIDT0##.IDX`, `POIAS2##.IDX` | 11.A.2.8 POI Search / 11.A.2.14 POI Information | Largest files on the whole disc (`POISR205`/`206` are ~177MB/132MB) — POI search is the single biggest data category by volume. |
| `FWYSR2##.IDX` | 11.A.2.7 Freeway Search | |
| `ITSSR2##.IDX` | 11.A.2.6 Intersection Search | |
| `ZONEVSRC.IDX`, `ZONEZSRC.IDX`, `ZSEL*.IDX` | 11.A.2.2/11.A.2.3 Zone Selection/Search | The 10 `ZSEL*0.IDX` files (all 1762 bytes) are likely per-mesh or per-level zone-selection tables. |
| `AGMSR*.IDX`, `ARGSR*.IDX`, `ARSNC2##.IDX`, `ARSSR.IDX` | Likely 11.A.2.5 Genre Search or 11.9 Search Meshes | "AGM"/"ARG"/"ARS" prefixes unconfirmed — needs Ch. 11 PDF cross-reference in Phase 1. |
| `EMGSR*.IDX`, `EM2SR.IDX`, `EM3SR.IDX` | Unconfirmed — possibly "emergency" services search category, or a genre/category tier. |
| `FMCDT001.IDX` | Unconfirmed. |

The repeated `*SR201..207.IDX` suffix pattern (7 files per prefix, e.g. `FWYSR201`–`FWYSR206`/`207`, `ITSSR201`–`207`, `POISR201`–`207`, `SADSR201`–`207`) almost certainly corresponds to the 7 zoom/display levels `kiwiread` found in `ALLDATA.KWI`'s LMR table (levels 12,10,8,6,4,2,0) — i.e. each search index is itself split per zoom level, matching the main map's own level hierarchy. Confirming this mapping precisely (which numeric suffix = which level) is a Phase 1 task. **Corrected 2026-09-04: the suffix is a state/territory partition, not a zoom level** — decoded address-range bounding boxes give 201=WA, 202=NT, 203=SA, 204=QLD, 205=NSW, 206=VIC, 207=TAS (all seven confirmed). See `docs/design/target-disc.md`.

**Precise mapping of these index-file prefixes to spec sections is a Phase 1 task** — cross-reference against the now-archived Chapter 11 sub-section PDFs (`spec/format_english/pdf/11A2*.pdf`) rather than guessing further here.

## Findings

### `kiwiread` build and test against this disc (2026-08-24)

**Setup.** Cloned https://github.com/jharg/kiwiread into `tools/kiwiread/`. It is
two small C files (`kiwiread.c`, `bmp.c`) plus a stub `osm.c`, built with a
one-line `Makefile` (`gcc -g -o kiwiread kiwiread.c bmp.c -lm`). No external
library dependencies (no libpng/libjpeg needed — `bmp.c` is a from-scratch
BMP/SVG writer).

**Build.** Did not compile out of the box on this machine (Ubuntu-ish glibc,
recent gcc, `-Wimplicit-function-declaration` is now an error by default).
Two source fixes were needed, both trivial and unrelated to the KIWI-W format
itself:
- `kiwiread.c` used `ntohs`/`ntohl` without including `<arpa/inet.h>` — added
  the include.
- `typecolor()` is defined after its first use — added a forward prototype
  near the top of the file.

With those two fixes it builds cleanly (only pre-existing `-Wformat` /
`-Waddress-of-packed-member` / `const`-discard warnings remain, all benign).

**Path/coordinate hardcoding.** As expected from the prior investigation, the
tool hardcodes `open("audi/ALLDATA.KWI", ...)` and `open("/media/LOADING.KWI",
...)`, and hardcodes a single target coordinate ("AUSTIN", 30.310801,
-97.711401 — Texas, obviously outside this disc's coverage) inside the
recursive tile-locate function. We could not symlink into `/media/` (no root),
so we edited the two `open()` calls in-place to point directly at
`/run/media/codyh/464210-8480/{ALLDATA,LOADING}.KWI`, and added three more
`isin(...)` probe blocks alongside the Austin one for Melbourne
(-37.813629, 144.963058), Sydney (-33.868820, 151.209290), matching the same
pattern (`printf(... "@@@ MELBOURNE" ...); drawme = 1;`).

**Result: header/metadata parse cleanly.** Run against this disc's real files,
`kiwiread` parses the `ALLDATA.KWI` volume header without any crash or
assertion failure and prints sane, disc-appropriate values:
```
fmt:FORMAT VERSION KIWI01-22-00
data:DATA VERSION 07/12/21/01
title:AU
media_ver:V 05.07.20
lower left: S50.000000 E90.000000
upper right: N35.333333 W142.000000
```
The format version string (`KIWI01-22-00`) matches the v1.22 spec already
archived in `spec/`, confirming this AU/Mitsubishi disc uses the same base
KIWI-W container version the tool was written against (it was apparently a
minor/vendor variant on the Audi disc, not a different major format). The
34-entry Media Header Record (MHR) table, the 7-level LMR hierarchy
(levels 12,10,8,6,4,2,0), and the ~1844-entry Block Set Management Record
(BSMR) table for the top data volume all decode structurally without
triggering the code's internal `assert()`s (e.g. `assert(nblocks*6 ==
SWS(bsmr->bmt_size))`, `assert(lt == 0)`), and populated (non-`0xffffffff`)
block offsets line up with real, non-uniform coverage gaps consistent with an
Australia-only disc (e.g. contiguous runs of real offsets, then long runs of
"no data here" blocksets).

**Bug found: tile-locate math breaks on this disc's antimeridian-crossing
bounding box.** With just the path edits, none of Austin/Melbourne/Sydney
ever matched (no `@@@` lines printed, and the program exited after dumping
the full BSMR table for the top-level data volume, never recursing into
`showbmt()`'s parcel-lookup path with a valid match). Root cause: this disc's
top-level bounding box is printed as lower-left `S50,E90` to upper-right
`N35.33,W142` — i.e. the box's right edge is expressed as a *negative*
longitude, and `kiwiread` computes width as a plain `_rx - _lx` (see
`kiwiread.c` around line 1727 and the per-parcel width calc at ~line 1513),
giving `-142 - 90 = -232` (visible directly in the tool's own diagnostic
output: `map size : 1x1 [-232.000000, 85.333333]`). That negative width then
propagates into `_mx`/`_my` per-parcel deltas, and `isin()`'s simple
`x <= lx+dx` range check silently never matches a real in-range longitude.
This is **not a structural format mismatch** — it's an off-by-assumption bug
in the reference tool's tile-locate driver, which was evidently only ever
exercised against a disc (Audi/Europe) whose bounding box doesn't cross the
±180° meridian. This AU disc's box does (it spans from 90°E across the
Pacific to what is effectively ~218°E, i.e. it's a big shared "AU region"
top-level tile, not just Australia's landmass).

To confirm this diagnosis, we patched the one line (`_mx = (_rx - _lx < 0 ?
(_rx + 360 - _lx) : (_rx - _lx)) / nx;`) as a local test-only fix (kept in
`tools/kiwiread/kiwiread.c` for now, not upstreamed) and reran: Melbourne
now matches on the first try —
```
l: 0 pt: 0  bs:22 block:23 parcel: 542 @@@ MELBOURNE
[-37.833333,144.937500] to [-37.812500,144.968750]
```
— a tight, correct bounding box around the requested coordinate, decoded from
a real parcel with a legible embedded name string ("DOVE RIVER
CONSERVATION..."), and the tool went on to write a genuine vector render to
`out.svg` (28KB, 57 `<polygon>`/`<polyline>`/`<text>` elements — real
coordinate data, not a placeholder). Note `bmp_write(bm, "poly.bmp")` is a
red herring: because the bitmap was allocated via `bmp_allocsvg()`,
`bmp_write()` just closes out the already-open SVG file handle and returns
(see `bmp.c` ~line 913) — the "poly.bmp" filename argument passed in is
unused. The real output artifact of a successful run is the SVG named at
allocation time (`out.svg`), not a BMP.

One secondary oddity observed once real data renders: some drawn polygon
coordinates in `out.svg` fall far outside the nominal 4096x4096 canvas
(e.g. thousands of pixels negative) — likely a scale/zoom-constant
(`mconst`) mismatch for background/coastline-type records at this disc's
zoom level vs. whatever the tool's constants were tuned for on the Audi
disc. Not investigated further; flagged as a thing to watch for in Phase 1
if background polygon geometry looks wrong.

**Files produced during this test:** `tools/kiwiread/run_output.txt` (full
run against real disc paths, pre-wraparound-fix — shows clean header parse,
full BSMR dump, no coordinate match), `tools/kiwiread/run_output_wraparound_test.txt`
(post-fix run — shows the Melbourne match and SVG write), `tools/kiwiread/out.svg`
(the rendered tile). `tools/kiwiread/kiwiread` is the built binary (not
committed if `.gitignore`d — check before committing binaries).

**`osm.c` skim.** Confirmed: it's a rough, one-directional OSM→bitmap sketch,
not a KIWI-W encoder and not really reusable as-is. It `mmap()`s a raw OSM
XML file and uses `strstr`/`sscanf` directly on the text (no real XML
parser — the `xml_node`/`xml_attr` structs are declared but never used) to:
pull out all `<node id lat lon>` tags into a singly-linked list; then scan
all `<way>...</way>` blocks, sniff a `k="highway" v="..."` tag to pick a
stroke color (residential/primary/trunk, else default green), resolve each
child `<nd ref>` through the node list, and draw a filled polygon (closed
way) or polyline (open way) into a fixed 4000x4000 `bitmap_t` via `bmp.c`'s
software rasterizer; final image written to `ausmap.bmp`. It has no error
handling for malformed/missing attributes, a fixed 2000-point-per-way buffer
with no bounds check, doesn't handle relations/multipolygons/tag-driven
styling beyond the three highway classes, and — most importantly for our
purposes — has zero code for encoding data back into KIWI-W's container
format. It's useful only as a rough reference for "here's how someone once
rasterized OSM ways for a sanity-check comparison image"; Phase 3's
OSM→KIWI-W pipeline will need to be written from scratch, though `bmp.c`'s
SVG/BMP writer is plausibly reusable as-is for visualization/debugging
during that phase.

**Implication for Phase 1.** `kiwiread`'s low-level container parsing
(volume header / MHR / LMR / BSMR / BMT table walk, road/name/background
sub-record decoders in `showmap()`/`showrt()`, the `swapw`/`swapl`/`extract()`
bitfield helpers) transfers to this disc essentially unmodified — same
format version, same record layouts, no assertion failures, real data found
at expected offsets. That's a solid base to build a real Phase 1 parser on:
port/clean up `kiwiread.c`'s struct definitions and table-walking logic
rather than re-deriving them from the spec from scratch. What does **not**
transfer as-is is the tile-locate/coordinate-math layer (`isin()`, the
`_lx/_ly/_rx/_ry`/`_mx/_my` global-state approach, and probably the
`mconst` scale constants) — that code was written under Euro-disc
assumptions (no antimeridian crossing, different zoom-level scale) and needs
to be rewritten properly (e.g. handle longitude wraparound explicitly, derive
scale constants from each LMR record rather than assuming a fixed constant)
rather than reused verbatim. Recommend Phase 1 treat `kiwiread.c` as a
reference/porting source for structs and table-walk order, but write a fresh,
disc-agnostic coordinate/tile-index layer.

## Decisions / deviations from plan

(record anything that didn't go as expected here)
