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

## `parser/refdata/` (committed, derived data)

- **What**: `grid.json` (reference disc PDMDH/LMR/BSMR parameters — coverage
  box, per-level block-set/block/parcel counts, cell sizes) and
  `mht29_frame.bin` (the 2048-byte language/country-code frame addressed by
  management header record 29). Unlike the rest of this document, these
  files *are* committed to git — the map-layer build reads them instead of
  the mounted reference disc, per the Grid contract and copy-through
  management data decisions in `docs/design/target-disc.md`.
- **Source**: derived once from the mounted reference disc's `ALLDATA.KWI`
  (`original-disc/pajero-whereis-2007.iso`, see above) by
  `parser/extract_reference_data.py`.
- **Why documented here anyway**: it is derived, not authored, and a future
  re-derivation against a different reference disc would change it — so its
  provenance and regeneration command belong in this BOM even though the
  files themselves are tracked.
- **Reproduce**: `.venv-rp/bin/python parser/extract_reference_data.py`
  (defaults to the reference disc mounted at
  `/run/media/codyh/464210-8480/ALLDATA.KWI`; pass `--alldata` to point at a
  different mount). Re-running against the same disc is byte-identical.

## `parser/refdata/profile/map.json` (committed, derived data)

- **What**: the reference profile — a full per-level census of the mounted
  reference disc's map layer (parcel/link/background/name counts and
  vocabulary histograms, Map Frame size stats, the mfde entry-count/absent-
  slot/nregion census, and the map-layer byte totals) that
  `parser/harness/checks/{vocab,envelope,mfde}.py` judge a generated disc
  against. Same rationale as `grid.json` above: committed so the harness
  never needs the mounted disc to judge a build, documented here anyway
  because it's derived and a re-derivation against a different reference
  disc would change it.
- **Source**: derived once from the mounted reference disc's `ALLDATA.KWI`
  (`original-disc/pajero-whereis-2007.iso`, see above) by
  `parser/harness/profile.py`'s `build_profile()`, invoked via
  `parser/compare_disc.py --profile`.
- **Reproduce**: `.venv-rp/bin/python parser/compare_disc.py --profile
  --reference /run/media/codyh/464210-8480` (or any mount/path to the
  reference disc's root or `ALLDATA.KWI`; `--profile-out` overrides the
  output path). Re-running against the same disc is byte-identical
  (confirmed twice during WP1 unit 03/03b, ~15 minutes wall time each).

## `output/spool/`

- **What**: on-disk spool of per-(level, ix, iy) parcel content (roads,
  backgrounds, names) written by `osm_to_parcel_geometry.py`'s one-pass OSM
  extraction, and read back by `build_alldata.py` to encode Map Frames.
  Intermediate pipeline state, not a deliverable.
- **Source**: `.venv-rp/bin/python parser/osm_to_parcel_geometry.py` (no
  flags — full-Australia default, all seven levels) against the dated
  Australia OSM PBF extract. WP1 units 15/15b's full run: 6.9 GB, 33:23.02
  wall clock, 8,188,004 KB peak RSS.
- **Why not committed**: large (multi-GB), fully regenerable from the PBF.
- **Reproduce**: the command above. Non-deterministic input dependency: the
  OSM PBF extract's own date/content, not the code, determines its bytes.

## `output/ALLDATA.KWI`

- **What**: the generated, full-Australia map-layer container — WP1's
  deliverable, built from `output/spool/` by `build_alldata.py`.
- **Source**: `.venv-rp/bin/python parser/build_alldata.py` (no flags —
  reads `output/spool` by default, writes `output/ALLDATA.KWI`). WP1 units
  15/15b's full run: 814,121,408 bytes, SHA-256
  `5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66`,
  confirmed byte-identical across two independent runs from the same spool
  (6:44.39 and 6:44.96 wall clock respectively, ~3.36 GB peak RSS each).
- **Why not committed**: large (814 MB), fully regenerable from
  `output/spool/`.
- **Reproduce**: the command above, given a matching `output/spool/`.

## `output/manifest.json`

- **What**: `build_alldata.py`'s own per-run manifest — spool stats, per-level
  parcel/byte counts and divided-parent counts, total size and SHA-256 of the
  `ALLDATA.KWI` it just wrote.
- **Source**: written automatically alongside `output/ALLDATA.KWI` by the
  same `build_alldata.py` invocation.
- **Why not committed**: regenerable output tied 1:1 to `output/ALLDATA.KWI`.
- **Reproduce**: the command above.

## `output/report.json`

- **What**: `compare_disc.py`'s per-check JSON report (container, decode,
  pointers, envelope, mfde, mht29, shape, spotcheck, vocab) for the
  2026-09-09 full-Australia build against the mounted reference disc. See
  `docs/plans/01-eval-harness-and-map-layer/PLAN.md`'s "Build record
  (2026-09-09)" and `docs/design/target-disc.md`'s file table for the
  findings this report drove.
- **Source**: `.venv-rp/bin/python parser/compare_disc.py --reference
  /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report
  output/report.json`.
- **Why not committed**: regenerable output tied to a specific build and to
  the mounted reference disc's availability.
- **Reproduce**: the command above, given a matching `output/ALLDATA.KWI`
  and the reference disc mounted at the given path.
