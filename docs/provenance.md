# Provenance / Bill of Materials

Every file used in this project that is **not** committed to git (per `.gitignore`)
is listed here: what it is, where it came from, and how to reproduce it. Anything
large, third-party, or regenerable lives outside git — but its origin must always be
traceable from this doc, not just from memory or shell history.

When you add a new `.gitignore` rule for a class of file, add an entry here in the
same commit.

## `original-disc/pajero-whereis-2007.iso`

- **What**: raw ISO image of the user's physical reference disc (Mitsubishi Pajero
  MMCS "WhereIS" nav DVD, 2007 edition — `VERSION.TXT` reads `COMMENT=2007 ver.1;`).
- **Source**: `dd`/raw sector copy of the physical DVD-R from the vehicle's head
  unit, captured 2026-08-24 on the user's own machine. Verified byte-identical to
  the live mounted disc via `cmp`/`diff -rq` (2026-08-24).
- **Why not committed**: 2.3GB binary; also third-party copyrighted map data, not
  something we distribute — used purely as a reverse-engineering reference.
- **Reproduce**: not reproducible except by re-imaging the same physical disc.

## `spec/`

- **What**: archived copy of the official KIWI-W v1.22 format specification
  (63 PDFs + framing HTML).
- **Source**: Wayback Machine capture of
  `http://kiwi-w.mapmaster.co.jp/format_english/format_kihon.html`
  (requested snapshot `20060616222450`; most content actually resolved to the
  17 Dec 2005 crawl). Fetched via `curl` with the `fw_` framed-resource flag
  (`WebFetch` cannot reach `web.archive.org` in this environment). See
  `spec/INDEX.md` for the full per-file fetch log and chapter index.
- **Why not committed**: third-party document set; large (PDFs).
- **Reproduce**: re-run the `curl` fetch sequence documented in `spec/INDEX.md`
  against the same Wayback Machine URLs.

## `tools/kiwiread/`

- **What**: clone of `jharg/kiwiread`, a partial open-source KIWI-W reader/renderer.
- **Source**: `https://github.com/jharg/kiwiread.git` (clone; check `git log` inside
  the clone for the commit checked out).
- **Why not committed**: third-party source we study/reference, not our own code.
- **Reproduce**: `git clone https://github.com/jharg/kiwiread.git tools/kiwiread`.

## `*.osm.pbf` (e.g. `australia-260824.osm.pbf`)

- **What**: OSM data extract used as the source content for the OSM→KIWI-W pipeline
  and for all density/scaling estimates (address density, road-tag cross-tab,
  overhead scaling, route-planning scaling).
- **Source**: Geofabrik, `https://download.geofabrik.de/australia-oceania/australia-updates`
  (confirmed from the file's own embedded OSMHeader block — `writingprogram:
  osmium/1.16.0`). Filename convention is `australia-<YYMMDD>.osm.pbf` for the date
  it was downloaded (e.g. `australia-260824.osm.pbf` = downloaded 2026-08-24) — the
  file is a rolling extract, not a versioned release, so the download date is the
  only version marker and must be preserved in the filename.
- **Why not committed**: ~900MB+ binary, trivially re-downloadable.
- **Reproduce**: download the current Australia extract from
  `https://download.geofabrik.de/australia-oceania.html` (or the specific
  `-updates` path above for a smaller diff-based extract) and name it
  `australia-<YYMMDD>.osm.pbf` using the download date.

## `.venv-rp/`

- **What**: a local Python virtualenv with `osmium` installed, used to run
  OSM-correlation scripts (e.g. checking route-planning byte size against
  OSM junction counts/road-km) since the system Python is externally-managed
  and doesn't have `osmium` available.
- **Source**: `python3 -m venv .venv-rp && .venv-rp/bin/pip install osmium`.
- **Why not committed**: a local virtualenv, not project content.
- **Reproduce**: the command above. Not referenced by any committed script's
  default path — activate it manually when running OSM-correlation analysis.

## `tag_crosstab.out` / `tag_crosstab.err`

- **What**: captured stdout/stderr from running `tag_crosstab.py` against the OSM
  extract above (road-tag drivability cross-tab used in the disc-size feasibility
  analysis).
- **Source**: generated locally by running `python3 tag_crosstab.py` against
  whichever `*.osm.pbf` is present.
- **Why not committed**: regenerable output, not source material; ties to whichever
  OSM extract happened to be present when it ran (see date caveat above).
- **Reproduce**: `python3 tag_crosstab.py > tag_crosstab.out 2> tag_crosstab.err`.
