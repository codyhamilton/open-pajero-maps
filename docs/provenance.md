# Provenance / Bill of Materials

Every file used in this project that is **not** committed to git (per `.gitignore`)
is listed here: what it is, where it came from, and how to reproduce it. Anything
large, third-party, or regenerable lives outside git — but its origin must always be
traceable from this doc, not just from memory or shell history.

When you add a new `.gitignore` rule for a class of file, add an entry here in the
same commit.

## `.venv-rp/` — local Python test environment

- **What:** an isolated environment created in the status-continue worktree;
  it is not a symlink to another checkout. System numpy is available through
  system site packages; pytest 9.1.1, pluggy 1.6.0 and iniconfig 2.3.0 were
  installed from the configured Python package index.
- **Why not committed:** regenerable third-party dependencies.
- **Reproduce:** `python3 -m venv --system-site-packages .venv-rp`, then
  `.venv-rp/bin/python -m pip install pytest==9.1.1 pluggy==1.6.0 iniconfig==2.3.0`.
- Existing environments, scratch, disc and spool inputs are preserved.

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

- **What**: a local Python virtualenv with `osmium` and `numpy` installed, used to run
  OSM-correlation scripts (e.g. checking route-planning byte size against
  OSM junction counts/road-km) since the system Python is externally-managed
  and doesn't have `osmium` available.
- **Source**: `python3 -m venv .venv-rp && .venv-rp/bin/pip install osmium numpy`
  (numpy 2.5.3 at plan 02; a hard dependency of the assembly stage's vectorized
  encoders / binary spool reader).
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

## `parser/refdata/parcel_mask.json` (committed, derived data)

- **What**: per-level coverage rectangle `{ix_lo, ix_hi, iy_lo, iy_hi}` inside which
  the reference disc has a Map Frame for every cell (its populated set is a full
  rectangle at all 7 levels; L0 1728x2144 = 3,704,832 cells). Read by
  `build_alldata.load_parcel_mask()`; `_encode_level` emits empty frames for masked
  cells the spool lacks.
- **Source**: the reference disc's `ALLDATA.KWI` PDMDH/block index tree.
- **Reproduce**: `.venv-rp/bin/python parser/tools/parcel_occupancy.py --write-mask
  parser/refdata/parcel_mask.json` (needs the mounted disc and `output/spool`; refuses
  if R's set is not an exact rectangle).

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

## `parser/refdata/{selection,harness,spot_checks}.json` and `vocab/` (committed, authored)

- **What**: decisions, not measurements. `selection.json` (per-level feature selection,
  calibrated to `profile/map.json` by tag-only osmium passes over the Australia extract),
  `harness.json` (envelopes and container-diff allowlist), `spot_checks.json` (city
  coordinates and expected names), `vocab/*.json` (tag to code tables).
- **Source**: authored in this repo against the census in `profile/map.json`; the
  inline `_comment` fields record the calibration.
- **Reproduce**: not regenerated. Edit by hand and rerun `compare_disc.py` to check the
  envelopes.

## `output/spool/`

- **What**: on-disk spool of per-(level, ix, iy) parcel content (roads,
  backgrounds, names) written by `osm_to_parcel_geometry.py`'s one-pass OSM
  extraction, and read back by `build_alldata.py` to encode Map Frames.
  Intermediate pipeline state, not a deliverable.
- **Source**: `.venv-rp/bin/python parser/osm_to_parcel_geometry.py` (no
  flags — full-Australia default, all seven levels) against the dated
  Australia OSM PBF extract. WP1 units 15/15b's full run: 6.9 GB, 33:23.02
  wall clock, 8,188,004 KB peak RSS.
- **Format (plan 02)**: binary columnar (`kiwiw/spool.py`, `.data` + `.idx` with magic
  `KWSPIDX1`); ~4.5 GB. Spools written before plan 02 are pickle (6.9 GB) and are
  converted once with
  `.venv-rp/bin/python parser/tools/convert_spool.py --i-trust-this-pickle <old> <new>`
  (plan 24: trusted-input gate required; production stays pickle-free).
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

## `output/compare_report.json`

- **What**: `compare_disc.py` report from unit 1-09 of plan 03 (strengthened harness on the
  current G), bound to `output/manifest.json` (`generated_sha256` 51c254ac...2743).
- **Source**: same command as `output/report.json` with `--report output/compare_report.json`.
- **Why not committed**: regenerable, tied to the build and the mounted disc. Reproduce: the command above.

## `output/extract_timing/`

- **What**: scratch dir of the 1-07 timed run of `osm_to_parcel_geometry.py` (spool, `START.txt`,
  `run.log` with `/usr/bin/time -v`); wall 26:03.27, 12 cores, upper bound (other units ran concurrently).
- **Why not committed**: large regenerable spool and log.
- **Reproduce**: `/usr/bin/time -v .venv-rp/bin/python parser/osm_to_parcel_geometry.py --pbf australia-260824.osm.pbf --spool output/extract_timing/spool`.

## `output/report.json`

- **What**: `compare_disc.py`'s per-check JSON report (container, decode,
  pointers, envelope, mfde, mht29, shape, spotcheck, vocab) for the
  2026-09-09 full-Australia build against the mounted reference disc. See
  `docs/plans/01-eval-harness-and-map-layer.md`'s "Build record
  (2026-09-09)" and `docs/design/target-disc.md`'s file table for the
  findings this report drove.
- **Source**: `.venv-rp/bin/python parser/compare_disc.py --reference
  /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report
  output/report.json`.
- **Why not committed**: regenerable output tied to a specific build and to
  the mounted reference disc's availability.
- **Reproduce**: the command above, given a matching `output/ALLDATA.KWI`
  and the reference disc mounted at the given path.

## `parser/kiwiw/_cenc.so`

- **What**: shared library of the whole-cell Map Frame encoder (`parser/kiwiw/_cenc.c`)
  used by `build_alldata.py` (plan 03) and by `synth._bg_fast`. Pure build artifact.
- **Source**: compiled from the committed `_cenc.c`; `kiwiw/cenc.py` builds it
  automatically on first import via `kiwiw/cbuild.py` (atomically, rebuilt when a
  content hash over the source bytes + compile flags no longer matches the stamp
  in `_cenc.so.hash` -- not mtime, so a worktree/stash mtime skew never causes a
  stale reuse or a spurious rebuild; see 3C-02).
  `KIWIW_NO_C=1` or a missing compiler falls back to the pure-Python path, which is the
  byte-identity oracle.
- **Why not committed**: platform-specific compiled binary.
- **Reproduce**: `gcc -O2 -ffp-contract=off -fPIC -shared parser/kiwiw/_cenc.c -o
  parser/kiwiw/_cenc.so -lm` (`-ffp-contract=off` is required for float parity).

## `parser/kiwiw/_cenc.so.hash`, `parser/kiwiw/ctest/_ctest_bin`, `parser/kiwiw/ctest/_ctest_bin.hash`

- **What**: Contract T (plan 03, 3C-02) build-product bookkeeping. `_cenc.so.hash`
  is the content-hash stamp (source bytes + compile flags) that `kiwiw/cbuild.py`
  uses to decide whether `_cenc.so` is stale. `ctest/_ctest_bin` is the layer (b) C
  unit-test binary, compiled from every `parser/kiwiw/ctest/*.c` file (each
  `#include`s the extension source(s) it exercises, so no source is compiled
  twice and `static` internals stay testable without exporting them);
  `_ctest_bin.hash` is its own content-hash stamp, hashed over both the `ctest/*.c`
  files and the extension sources they `#include` (an edit to `_cenc.c` alone must
  still invalidate the test binary even though no `ctest/*.c` file's own bytes
  changed).
- **Source**: built on demand by `kiwiw/cbuild.py`'s `build_ext()`/`build_test_bin()`,
  called from `kiwiw/cenc.py` and `parser/tests/test_c_units.py` respectively.
  Same atomic temp-file-then-`os.replace` install as `_cenc.so`; each `.hash` file
  is written only after that rename.
- **Why not committed**: platform-specific compiled/derived build artifacts.
- **Reproduce**: run `parser/tests/test_c_units.py` (or import `kiwiw.cbuild` and
  call `build_ext()`/`build_test_bin()` directly) with a C compiler on `PATH`.

## `output/goldens-3C/` (local-only Contract T goldens, 3C-03)

- **What**: Contract T (c) goldens too large to commit (limit used: ~2 MB fixture
  spool per golden, ~10 MB for all committed goldens). Each `<name>/` holds a
  closed fixture spool (`spool/level_<L>.{idx,data}`), the expected frames
  (`frames.bin`, `frames.tsv`) and `golden.json`. Currently one:
  `l0_divided_trim_halo` (L0 window `1755 591 1756 592`, the full-AU build's
  only trimmed L0 cell; 6.5 MB spool). The list lives in
  `parser/tests/fixtures/goldens/local.json`; `parser/tests/test_goldens.py`
  skips a listed golden when its directory is absent. `output/goldens-3C/index/`
  caches `golden_capture.py`'s bounding-box index per spool level (regenerated
  automatically).
- **Source**: the spool of record `output/extract_timing/spool` and the build at
  the 3-11 reference (`87a01b14…`).
- **Why not committed**: size.
- **Reproduce**: `.venv-rp/bin/python parser/tools/golden_capture.py capture
  --out output/goldens-3C --name l0_divided_trim_halo --level 0 --window 1755
  591 1756 592 --covers "divided L0 parent with trim and name halo"`; verify
  with `golden_capture.py prove --golden output/goldens-3C/l0_divided_trim_halo
  --digest <full-AU --frame-digest listing> --work <dir> -j 12` (under
  `flock output/.heavy.lock`).

## D1 equivalence sample (G and R discs)

- **What**: `parser/tests/fixtures/d1_sample.json` (committed, ~6 KB) lists the
  leaves and whole blocks `parser/tests/test_d1_equivalence.py` compares D1
  (`kw_d1_blocks`) against `harness.walk` + `decode_parcel`. The discs it indexes
  are NOT committed: G at `output/scratch-3-11/G/ALLDATA.KWI` (the 3-11 reference
  build, size recorded in the file) and R at `/run/media/codyh/464210-8480/ALLDATA.KWI`
  (the reference disc). The test skips a disc that is absent.
- **Rule**: recorded verbatim in the file (`rule`, `seed` 20260930, `constants`),
  re-derived by `test_sample_rule_reproduces`.
- **Reproduce**: `D1_SAMPLE_WRITE=1 .venv-rp/bin/python -m pytest
  parser/tests/test_d1_equivalence.py -k rule` (both discs present), then rerun
  without the variable.

## `parser/tests/fixtures/bg_split/under_4096_100.bin` (committed, captured fixture, 3-11)

- **What**: the pre-3-11 (`HEAD`) `enc_bg` frame bytes for a synthetic L0 cell
  (1780,814) holding 100 class-2/type-288 background shapes — a `<4096` cell, so
  `enc_bg` must still emit one 12-bit unit and the split path must leave it
  byte-identical. 1,968 bytes, sha256 `4aa4f054…b750d`. Consumed by
  `parser/tests/test_bg_count_split.py` (which imports the repo's `parser/` for
  `kiwiw` via a `sys.path` insert, since the fixture lives beside it).
- **Source**: `output/scratch-3-11/capture_fixture.py`, run against the
  pre-3-11 encoder so the fixture records HEAD output, not this unit's
  (byte-identical for this `<4096` cell, but the record should be HEAD).
- **Reproduce**: copy `parser/` to a scratch root, overwrite its
  `parser/kiwiw/_cenc.c` with `git show HEAD:parser/kiwiw/_cenc.c`, build the
  extension, then run `output/scratch-3-11/capture_fixture.py` from that root.

## `output/scratch-2-07/` (Phase 2 full-disc evidence, 2-07)

- **What**: uncommitted evidence of the one full-disc Phase 2 run: K1 reports
  `k1_{a,b,c,j1}.json` (+ `.log`), `determinism.txt`, `d1_decode.json/.log`,
  `py_checks.tsv` with `py_<check>.json/.log`, `gates.txt`, `goldens.log`,
  `hbudget.log`, `status.txt` (ends `ALLDONE`) and `run.sh`. The bounded failing
  samples that Phase 3 triage starts from live in each `k1_*.json` level's
  `failures[]`; the 2-08 verify record in
  `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` cites the counts and walls.
- **Source**: `output/scratch-2-07/run.sh`, executed once under
  `output/.heavy.lock` against the 3-11 reference disc G
  (`output/scratch-3-11/G/ALLDATA.KWI`, see above) and `output/spool`.
- **Why not committed**: regenerable, large run output (`output/` is gitignored).
- **Reproduce**: `bash output/scratch-2-07/run.sh` (needs G, `output/spool`, and
  the reference disc mounted; the K1/PSS walls are machine-dependent).

### output/scratch-3-06/ (Phase 3 forensics, not committed)
Python-only forensic dossier for plan 04 Phase 3 unit 3-06: `dossier.md`, scripts (`common.py`, `build_tall.py`, `d1_d3.py`, `d456.py`, `d7.py`, `d8.py`), tall-shape caches (`tall_{0,2,6}.npz`) and logs. Inputs: `output/scratch-3-11/G/ALLDATA.KWI`, `output/extract_timing/spool`, `output/scratch-2-07/k1_a.json`. Reproduce: `.venv-rp/bin/python output/scratch-3-06/build_tall.py` then `d1_d3.py`, `d456.py`, `d7.py`, and `d8.py` under `flock output/.heavy.lock`. Consumed by 3-07/3-08.

### output/scratch-3-02/dump/ (K1 failure dump, Phase 3 unit 3-02, not committed)
Every failing item of the five failing kinds on G, as fixed-width 80-byte rows
(`K1_F_DUMP` in `parser/kiwiw/_k1.h`, mirrored by `cenc.K1_DUMP_DTYPE`), one
`<kind>.bin` per kind plus `dump_manifest.json` (per kind: rows, row size, field
list). Rows: `background` 1,438,558, `background_boundary` 16,549,569,
`interior_cover` 824, `completeness` 752, `name_anchor` 1 (17,989,704 rows,
1,439,176,320 bytes; `du` 1.4 GB). The `background.bin` 115,084,640 B,
`background_boundary.bin` 1,323,965,520 B, `interior_cover.bin` 65,920 B,
`completeness.bin` 60,160 B, `name_anchor.bin` 80 B. This is the triage input
for 3-03/3-05..3-08. **Source**: the brief-3-02 full-disc dump run under
`flock output/.heavy.lock` against G (`output/scratch-3-11/G/ALLDATA.KWI`) and
`output/extract_timing/spool`. **Reproduce** (opt-in dump mode; wall ~2.6 min on
an idle machine, peak RSS ~4.3 GB): `flock output/.heavy.lock .venv-rp/bin/python
parser/tools/quantisation_roundtrip.py --disc output/scratch-3-11/G/ALLDATA.KWI
--spool output/extract_timing/spool -j 12 --dump-failures output/scratch-3-02/dump
--out output/scratch-3-02/k1_dump.json`. Rows are canonically ordered, so the
bytes are independent of `-j` and of the band split.

### output/scratch-3-03/dump/ (K1 diagnostic dump, Phase 3 unit 3-03, not committed)
The same five failing kinds with the brief-3-03 diagnostic columns appended
(`onb`, `d_any`/`any_type`, `in_eo_same`/`in_wn_same`/`in_eo_any`, the nearest
same-type source `src_*`/`d_src`, and the DISC shape's `dcls`/`dnv`), so rows are
144 bytes (`K1_F_DUMP` in `parser/kiwiw/_k1.h`, mirrored by `cenc.K1_DUMP_DTYPE`).
Counts are unchanged (`background` 1,438,558, `background_boundary` 16,549,569,
`interior_cover` 824, `completeness` 752, `name_anchor` 1) and the first 21
(3-02) columns are byte-identical to `output/scratch-3-02/dump/`; `dump_manifest.json`
carries the field list. **Source**: the same full-disc dump run as 3-02 under
`flock output/.heavy.lock` against G and `output/extract_timing/spool`, but with
`--dump-failures output/scratch-3-03/dump --out output/scratch-3-03/k1_dump.json`
(wall 221.8 s on a quiet machine, peak PSS ~7.9 GiB). `output/scratch-3-03/head_nodump.json`,
`wt_nodump.json` and `head_nodump.log`/`wt_nodump.log` are the dump-off A/B against
a `8d96e3a` git worktree (checked out under `output/scratch-3-03/headwt`, removed
after the run): both reports are identical
to `output/scratch-2-07/k1_a.json` excluding timing, walls 67.4 s (HEAD) and 62.8 s
(working tree). The `dump_l6_j1/`, `dump_l6_j12/` trees are the `--levels 6`
byte-equality pair. Regenerable, so not committed.

### output/scratch-3-05/ (K1 triage tool output, Phase 3 unit 3-05, not committed)
Summaries and assignments written by `parser/tools/k1_triage.py` over a K1 failure dump (`summary` → `totals.tsv`, `by_level_type.tsv`, group tables; `classify` → per-rule assignment files and `rules.json`). Regenerable: `.venv-rp/bin/python parser/tools/k1_triage.py summary --dump output/scratch-3-03/dump --out output/scratch-3-05/summary` (about 2.3 min, ~3.4 GB RSS); the dump itself is the 3-02/3-03 entries above.

### output/scratch-3-07/ (3-07 cause-table scratch, Phase 3, not committed)
Witness scripts, side tables (`side_background_boundary.npy`, partial: S02 producer scan stopped at the 10,000-ring pin cap), `pins_S02.tsv`, counterfactual windows (`spool_cf/`, `cf_*`) and `dump_attempt3/` (2.6 GB): the 3-03 dump (`output/scratch-3-03/dump`) with one appended u8 column `s02_producer_verified`, built by `output/scratch-3-07/extend_dump_attempt3.py` from the side table. Committed `triage/rules_bg.json` rule S02 needs that column; `classify` against the original dump exits 2. These artefacts and scratch-only producer scripts were deleted (plan-28 Ground); older worktree links are dangling. They are **not regenerable by this old recipe**. The tracked `parser/tools/dump_join.py --mode s02` can reproduce the join only if its deleted producer-qualified side table is supplied; it does not reconstruct that table. The historical scan was partial until the pin-cap decision. Reviews: `output/scratch-3-07/review/`, `review3/`.

### output/scratch-3-08/ (3-08 cause-table scratch, Phase 3, not committed)
Side tables (`side_interior_cover.npy`, `side_completeness.npy`, `side_name_anchor.npy`, `sources_other.json`), audit scripts, counterfactuals (`cf_count_wrap`, `cf_name`, `cf_completeness`) and `dump_other/` (272 KB for the three small kinds, plus read-only symlinks to `output/scratch-3-07/dump_attempt3` big files): the 3-03 dump with `s02_producer_verified` (byte 144, 3-07) and `other_mechanism` (byte 145, 3-08, previously padding). Committed `triage/rules_other.json` needs these columns; on the original dump `classify` exits 2. These artefacts and the scratch-only producer scripts were deleted (plan-28 Ground). They are **not regenerable by this old recipe**, and `other_mechanism` had no tracked producer. Plan 28 below provides a fresh completeness-only measurement under the current contract; it does not restore 3-08 bytes or reconstruct the other kinds. Reviews: `output/scratch-3-08/review/`.

### output/scratch-3-12/ (new-disc residual attribution, not committed)

- **Inputs:** `output/scratch-3-11/G_new/ALLDATA.KWI`, manifest SHA256
  `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`,
  `output/extract_timing/spool`, `scratch-3-11/dump_new_ext` (152-byte rows,
  inherited producer/other-mechanism columns at bytes144/145), and
  `scratch-3-11/classify_new`. Baseline residual15,128,966 rows. Original
  spool, original dumps, old disc and historical evidence are read-only inputs.
- **Source tables:** `side_background.npy`, `side_background_boundary.npy`,
  `side_interior_cover.npy`, generated by `aggregate.py` from
  `build_producers.jsonl`. Each row stores the complete native group key
  `(level,ix,iy,code,p0..p6,shape)`, status, original source home/record,
  source vertex count, closing/longest indices, closing-crossing count, cover
  flag. Status1 means a unique byte-exact original producer, not an E1 cover
  replacement, explicit closure, longest edge is closing and has a proper
  nonadjacent crossing; other/ambiguous/unmatched statuses are not assigned.
  Exhaustive residual probe:425,416 group/stratum entries;70,999 distinct
  qualifying source rings (rule source counts overlap). Actual assigned rows
  and per-rule source contributions are recorded by native classify and
  `pins_residual.tsv`, not estimated from the sample.
- **Producer method:** `probe_samples.py --input residual_groups.jsonl
  --prefix build_ --build-bounds` uses unchanged E1 with all original source
  cells retained, actual G_new record bytes, unchanged C per-ring encoder
  exposed by `probe_bg.c/.so`, build `kw_bounds` operation order and actual
  integer leaf clip rectangles. Initial walker-bound probes missed eight
  items; `nominal_producers.jsonl` resolves all eight and the entire probe was
  repeated with build arithmetic. The retained `full_` trace is historical,
  not the definitive source table. No missing match is presumed synthetic.
- **Dump extension:** `extend.py` (live, gitignored) is a thin wrapper over the
  tracked residual adapter `parser/tools/dump_join.py` with its unchanged
  `DEFAULT_*` residual paths; the durable equivalent is
  `.venv-rp/bin/python parser/tools/dump_join.py` (mode `residual`, defaults).
  It writes `dump_ext` from `dump_new_ext`, populating
  `residual_crossing_verified` (u8) at **byte146, previously padding**, via the
  bounded windowed I/O path; semantics are unchanged (other bytes identical,
  row size remains152, exact full-key join of status1, default0; inherited
  fields/flags stay unchanged). `dump_ext/dump_manifest.json` records the
  extension. `rules_bg.json` S03/S04/S05 depend on this field; R01/S02 retain
  priority. This scratch dump/side-table dependency is required to reproduce
  classification. The vendored whole-file baseline
  `parser/tests/fixtures/dump_join_baseline/extend.py` (SHA `1b13b844…`) stays
  frozen in fixtures for replay and is not overwritten by the wrapper.
- **Independent witnesses:** `independent.py` reads the established all-level
  spool caches in scratch-3-07 without writing them; no K1/Python checker
  imports. Uniform distinct-group seeds2026100212 (initial) and2026100213
  (after producer predicate),200 groups per kind/level/type/sentinel stratum
  or census when fewer. `qualified_witness.jsonl`:4,056/4,056 INVALID;
  `witness_S05.jsonl`:3/3 INVALID at actual leaf centres. `column_study.json`
  and `geometry_distributions.json` contain row-weighted actual leaf geometry
  and explicitly group-weighted producer source-size distributions. Path
  fields beyond dump `depth` can be nonzero: actual leaf joins truncate at
  depth, while native group keys and original bytes are preserved.
- **Controls/remainder:** `cf_current/{type291,type288}` has fresh original
  9/9 G_new frame gates and identical modified j1/j4 builds, reading the
  existing immutable one-coordinate modified spools from scratch-3-07.
  K1 controls use j1. `exception_tests.jsonl` and `exception_witness.jsonl`
  record failed hypotheses for all180 remaining background-family groups;
  `small_hypotheses.jsonl` joins all188 completeness groups to accepted
  failed repairs in scratch-3-08. `remaining_groups.tsv` has every key/count
  and the report names each next untested predicate. No blanket cause.
- **Reproduce:** under `flock output/.heavy.lock`, serially run `study.py`;
  compile `probe_bg.c` with `gcc -O2 -ffp-contract=off -fPIC -shared ... -lm`;
  run `run_witness.py`, the definitive producer command above, `aggregate.py`,
  `rerun_counterfactual.py`, `extend.py`, `select_qualified.py`,
  `run_witness.py --input qualified_samples.jsonl --prefix qualified_`,
  `run_witness.py --input exception_samples.jsonl --prefix exception_`,
  `exception_tests.py`, `cover_and_small.py`. Combine updated bg rules and
  unchanged other rules into `rules_all.json`, then run native
  `parser/tools/k1_triage.py classify --dump output/scratch-3-12/dump_ext
  --rules output/scratch-3-12/rules_all.json --out output/scratch-3-12/classify`.
  Expected exit1 / PARTITION FAIL:9,064 unattributed rows. Finish with
  `geometry_distributions.py`, `audit_assignments.py`, `write_report.py`.
  Script paths here are all under scratch-3-12. Build workers1/4; K1/harness
  never beyond6; one heavy job at a time. All writes stay in the repository.
- **Consumer/status:** `triage/causes_residual.md` (historical), fix-unit authors, and 3-13. Independent review of 3-12 is in `triage/review_3-12.md` (ACCEPT-WITH-CONDITIONS A–D). Follow-up Conditions A–C closed under 3-13 (`causes_rootcause.md` / `review_3-13.md`); Condition D keeps the 9,064 unattributed. Outputs are regenerable large evidence, gitignored; no commit or code fix from 3-12 alone.

### output/scratch-5-01/ (plan 05 Phase 1 memory evidence, not committed)

- **What**: git-ignored (under `output/`) scratch for brief 1-01: `bench/fixture-1m/`
  and `bench/fixture-2m/` (seeded 1,000,013- and 2,000,013-row 152-byte residual
  fixtures, 216,488 side rows, seed 20260502; replay roots and worker markers are
  created under `bench/run-*` and removed after each run), `results.json` (paired
  baseline/candidate max RSS, cgroup `memory.peak`, anon/file/dirty, wall, SHA256s),
  `bench.log`, `*.EXIT` markers, `tmp/`, `tests-<pid>/` (removed by the tests), and
  `dump_ext.sha256` (supplementary read-only SHA256 of the existing
  `output/scratch-3-12/dump_ext/*.bin`, evidence only).
- **Source**: generated; the baseline replayed there is the vendored
  `parser/tests/fixtures/dump_join_baseline/` (SHA256SUMS tracked, copies of
  `output/scratch-3-12/{extend,study}.py` and `output/scratch-3-07/witness.py`).
- **Reproduce**: `flock output/.heavy.lock .venv-rp/bin/python
  parser/tools/bench_dump_memory.py --out output/scratch-5-01/results.json`
  (exit 0 only if every gate passes); `dump_ext.sha256`: `flock output/.heavy.lock
  sha256sum output/scratch-3-12/dump_ext/*.bin > output/scratch-5-01/dump_ext.sha256`.

### output/scratch-5-02/ (plan 05 Phase 2 K1 dump-finalizer memory benchmark, not committed)

- **What**: git-ignored (under `output/`) scratch for brief 2-01: `fixture/parts/`
  (one kind, `background_boundary`, 1,000,013 deterministic rows of the 144-byte
  `cenc.K1_DUMP_DTYPE` split over `part_*.bin` files with duplicate sort keys),
  `runs/` (fresh per-run part copies and worker markers, removed after each run),
  `finalize_results.json` (paired baseline/candidate max RSS, cgroup `memory.peak`,
  anon/file/dirty, wall, output SHA256s, counts, gates) and `tmp/`.
- **Source**: generated by `parser/tools/bench_dump_memory.py finalize-genfixture` and
  measured by `finalize-run`; the frozen pre-change function replayed there is the
  tracked `parser/tests/fixtures/finalize_dump_baseline/` (SHA256SUMS tracked).
- **Reproduce**: `flock output/.heavy.lock .venv-rp/bin/python
  parser/tools/bench_dump_memory.py finalize-run --out
  output/scratch-5-02/finalize_results.json`, with `TMPDIR=output/scratch-5-02/tmp`;
  exit 0 only if every gate passes. All generated files stay in the repo and are
  git-ignored via the `output/` rule.

### output/scratch-5-03/ (plan 05 Phase 3 dump_io / 3-07 / triage memory evidence, not committed)

- **What**: git-ignored scratch for brief 3-01: `fixture-1m/` / `fixture-2m/` (3-07 144-byte dumps),
  `triage-fixture-1m/` / `triage-fixture-2m/`, `bench/`, `s07_results.json`, `triage_results.json`, `tmp/`.
- **Source**: generated by `parser/tools/bench_dump_memory.py` `s07-run` / `triage-run`.
- **Reproduce**: `flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py s07-run --out output/scratch-5-03/s07_results.json` and `... triage-run --out output/scratch-5-03/triage_results.json`.

### output/scratch-3-14/ (unit 3-14 EO-aware background stitching, not committed)

- **What:** private baseline/fixed nine-window discs and frame dumps, AU/Perth
  corrected discs, SHA records, per-leaf/per-cell inventories, differing-cell
  TSVs, payload/topology explanations, K1 raw/extended failure dumps and fresh
  producer census, classification, deterministic worker-count builds, recaptured
  goldens and test logs. No original oracle is overwritten. The worktree's input
  links point read-only at the main checkout's scratch-3-07/08/11/12/13,
  extract_timing spool and original local goldens; its heavy lock links to the
  main checkout's lock, not a separate lock file.
- **Source:** unchanged original `output/extract_timing/spool`; old AU
  `scratch-3-11/G_new/ALLDATA.KWI` SHA256
  `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`, old Perth
  `scratch-3-11/perth_fix/ALLDATA.KWI` SHA256
  `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc`.
- **Reproduce:** the private `precheck.py`, `goldens_audit.py`, `windows.py`,
  `inventory.sh`, `compare_cells.py`, `dump_new.py`, `classify_new.py`,
  `explain_cells.py` and `finish_gates.py` record exact commands/joins. Run
  each heavy stage serially under `flock output/.heavy.lock`; build/K1/walk
  workers are at most four. `run_full.sh` builds the full AU and Perth with
  `parser/build_alldata.py`, `--spool output/extract_timing/spool`, `-j4`,
  adding `--fixture perth` for Perth. Scratch uses the prior read-only
  `block_keys`, frame inventory and producer-probe helpers; probe C includes
  this worktree's `_cenc.c`. New background producer flags are verified
  against actual new record bytes, never inherited by shape index. Other-kind
  side flags are reused only for byte-unchanged cells; remaining changed-cell
  failures are conservatively unattributed.
- **Test captures:** `parser/tests/fixtures/bg_eo/simple_sha256.json` holds
  six ordinary-ring frame hashes captured at `8b9a65e` by `frame()` in
  `test_bg_eo_stitch.py`. They must remain unchanged. The adjacent `probe.c`
  is source, compiled into pytest's temporary directory for hidden clipper
  room-retry/subrectangle tests. Geometry expectations are independent ray
  parity and Chebyshev segment distance. No expected geometry comes from
  another encoder. Changed real goldens are recorded in
  `scratch-3-14/goldens_changes.json`; unchanged fixtures are not recaptured.

### output/scratch-3-15/ (unit 3-15 completeness cell-local representability, not committed)

- **What:** git-ignored science evidence: `inventory_739_776.py` + `inventory_summary.json` / `+37_census.tsv` / `pre_only_cleared.tsv` / `historic188_status.tsv` (full-key set-diff of the 739 pre-3-14 and 776 post-3-14 completeness dumps); `probe_bg.c` / `probe_bg.so` / `probe_check.py` (hidden `kw__bg_shape` clip probe built from this worktree's `parser/kiwiw/_cenc.c`); `representability_188.py` / `.jsonl` / `_summary.json` / `.md` (complete even-odd topology repair via `scratch-3-13/split.decompose` + independent clip/densify/round over the 188 historic keys); `mechanism_776.py` / `mechanism_776_recomputed.jsonl` / `.json` (from-scratch spool-side O01/O05/O04 reimplementation; pre-739 control passes); `moved_keys.tsv` / `moved_rules.tsv` / `moved_disposition.tsv` / `moved_analysis.py`; `recount_776.json` / `recount_776_final.json` / `recount_776_FINAL.json`; `contract_comparison.json` / `.tsv` / `_summary.json` (legacy pre-3-14 vs 3-14 stitch clip probe); `added89_full_repair.jsonl`.
- **Source:** unchanged read-only inputs `output/scratch-3-11/dump_new_ext/completeness.bin` (739 rows, sha `01e5f7ba…`), `output/scratch-3-12/small_hypotheses.jsonl`, `output/scratch-3-08/{completeness_repair,completeness_rings}.json`, `output/scratch-3-13/split.py`; 3-14 `source` `open-pajero-maps-3-14/output/scratch-3-14/dump_ext/completeness.bin` (776 rows, sha `78340d3d…`) and `k1_full.json`. No existing scratch or oracle overwritten.
- **Reproduce:** `.venv-rp/bin/python output/scratch-3-15/<script>.py` from the main checkout under `flock output/.heavy.lock`; the C probe compiles with `gcc -O2 -ffp-contract=off -fPIC -shared probe_bg.c -lm -o probe_bg.so`. `probe_bg.c` includes this worktree's `_cenc.c` (3-14 EO stitch); `scratch-3-08/probe_bg.so` is the legacy pre-stitch contract.

### output/scratch-3-16/ (unit 3-16 89-key window counterfactual, not committed)

- **What:** science evidence for only the 89 `added_89` completeness keys from
  the 3-15 packet: `keys89.json`, `inputs.json`, `run.py`, copied `split.py`,
  `libkiwiw.so`/hash, private `spool_faces/`, `source_changes.json`,
  `home_audit.json`, `results.json`, `tally.json`, and `key_00/` through
  `key_88/`. Each key retains a one-cell original-spool baseline and EO-face
  counterfactual disc/frame dump, baseline frame byte gate, C D1 target geometry,
  C K1 original-spool JSON/completeness dump, and outcome. `audit.py`,
  `region_audit.json`, `legacy_spool_degree_control.json`, `audit_summary.json`
  and `SHA256SUMS` retain the cold verification. Discs/dumps are never staged.
- **Source:** `7a12618`'s science packet, retained under the sibling
  `open-pajero-maps-3-15/output/scratch-3-15/`: `contract_comparison.json`
  `added_89` keys (SHA `1fe735cf…`), meeting-source identities from
  `mechanism_776_recomputed.jsonl` (SHA `bd123cd7…`). Original source is
  `open-pajero-maps/output/extract_timing/spool`; byte oracle is the existing
  3-14 `G_new/ALLDATA.KWI` (SHA `4ed9cd80…`). No completeness re-census or
  disc diff to reconstruct keys. Only their 34 meeting sources are decomposed
  into 156 exact EO faces in a private L0 copy; other fields/sources are kept.
  The source helper is the retained 3-13 `split.py` (SHA `3f3d932d…`);
  decomposition uses original spool degree doubles. Original inputs are read
  only; bytecode writes are disabled. Original home-record and L0 index hashes
  are checked after the run. Existing scratch-3-11/14/15 is never overwritten.
- **Reproduce:** in a fresh sibling worktree at base `9b44b59`, copy the retained
  `keys89.json`, `run.py`, `split.py` and `audit.py` into its fresh
  `output/scratch-3-16/`, link the shared heavy lock, and run
  `flock output/.heavy.lock env PYTHONDONTWRITEBYTECODE=1
  /home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python
  output/scratch-3-16/run.py`; the script refuses existing spool/window
  destinations. Verify retained evidence with the same command ending in
  `audit.py`. Both use the unchanged production encoder/decoder/checker;
  cbuild writes only private `scratch-3-16/libkiwiw.so`. The lock is a symlink
  to the main checkout's `output/.heavy.lock`. Builds/K1 use one worker;
  compilation is serial, no cache drops, no full-AU encode. The retained
  legacy probe is read only for the enumerated source-degree control.
- **Consumer/status:** plan 04 Execute and Design;
  [science packet](plans/04-c-core-orchestration/triage/completeness_3-16_window_cf.md)
  and committed full-key TSV. **0 pass / 89 fail / 0 untested**; all baseline
  byte gates pass and every counterfactual frame is unchanged. No target
  piece appears; no C amendment justified by gate (b). Accept-with-honesty
  for these tested keys, with the face-bypass limitation explicit. No encoder,
  checker, rule or ledger change; Phase 3 remains open.


### output/scratch-08-zero-row-classify/ (empty-kind CLI verification, not committed)

- **What:** `verify.py`, copied single-kind manifests and rule snapshots in
  `kind_views/`, read-only symlinks to existing dump binaries, CLI commands and
  stdout/stderr, `classify/<kind>/` outputs, `inputs.json` and
  `verification.json`, plus before/after disc SHA256 files. No binary is copied
  or regenerated.
- **Source:** sibling `open-pajero-maps-3-17/output/scratch-3-17/kind_views/`
  for background, background_boundary, and name_anchor; binaries resolve into
  the unchanged sibling 3-14 `dump_ext/`. The non-empty reference is 3-17's
  `classify_kinds/name_anchor/`. The read-only disc is 3-14's
  `G_new/ALLDATA.KWI`, SHA256
  `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
- **Reproduce:** copy those three kind-view manifests and `rules.before.json`
  snapshots into a fresh local scratch directory, symlink each source binary,
  and invoke `.venv-rp/bin/python -B parser/tools/k1_triage.py classify --dump
  <view> --rules <view>/rules.before.json --out <fresh-kind-output>` for each
  kind. Use the main checkout's `.venv-rp/bin/python` if the local worktree has
  no environment. Assert empty kinds exit 0 with zero partition rows and empty
  assignments; compare all name_anchor output bytes with the retained reference.
  Hash the disc before and after, and compare input hashes after the replay.
  Run serially under `flock output/.heavy.lock`, sharing the main checkout's lock.
- **Consumer:** plan 08's verification. The replay covers exactly these three
  kind views; it makes no completeness measurement or all-kind success claim.

### output/scratch-3-17/ (unit 3-17 ledger re-baseline, not committed)

- **What:** fresh `disc.sha256`, `inputs.json` (read-only input hashes/sizes),
  original `rules_bg.before.json` / `rules_other.before.json` and concatenated
  `rules_all.before.json`; `classify.py`, full invocation/exit/stdout/stderr and
  partial `classify/`; `classify_kinds.py`, scratch `kind_views/<kind>/`
  single-kind manifest/rule projections with read-only binary symlinks and
  command/stdout/stderr, and `classify_kinds/<kind>/` outputs; `identity_audit.py`,
  `identity_summary.json` and `historic_<kind>_rows.tsv` with every historic
  native row/full key and current match/assignment. `record.py` writes the
  documentation and checks retained input hashes again before recording.
- **Source:** existing read-only sibling
  `open-pajero-maps-3-14/output/scratch-3-14/G_new/ALLDATA.KWI`, SHA256
  `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`,
  its `new_sha256.txt`, `k1_full.json` / `.log`, and unchanged `dump_ext/`.
  Historic identities come from the main checkout's `scratch-3-12/dump_ext/`
  and `classify/assign_*.u16`; the completeness selection is checked against
  sibling 3-15 `historic188_status.tsv`. No old disc substituted, missing key
  reconstructed, existing scratch overwritten or bytecode written.
- **Reproduce:** retain the pre-note rule snapshots; on a fresh scratch
  destination at base `ced98f8`, run `classify.py`, `classify_kinds.py`, then
  `identity_audit.py` with the main checkout's `.venv-rp/bin/python -B`.
  The first script requires a separately saved fresh `disc.sha256`.
  The full existing CLI rejects zero-row background; single-kind views retain
  unchanged binary/schema/predicates. All three empty kinds also reject zero
  rows; completeness emits `PARTITION FAIL`, name_anchor has a kind-only
  `PARTITION OK`. Scripts and diagnostic output stay in this worktree's
  `output/scratch-3-17/`. No K1 run, encode, C build or heavy operation required.
- **Consumer/status:** [3-17 re-baseline](plans/04-c-core-orchestration/triage/rebaseline_3-17_9064.md),
  done with concerns. Historic background/boundary rows are absent from the
  failing set; every historic completeness row matches and stays unattributed.
  Raw mechanism flags are distinguished from the prior corrected 3-15 tally;
  no assigned build row, no rule registration and no Phase 3 closure.


## `output/scratch-3-90/` — fresh verification rerun, 2026-10-04

- **What:** private verification evidence at worktree `/home/codyh/workspace/open-pajero-maps-3-90`; final native failure dump `dump/`, K1 reports `k1_{a,b,c,j1,dump}.json`, timing-only-normalized reports, raw logs, derived `rules_merged.json`, fresh AU and two Perth build outputs, and numbered PASS/FAIL reports. This is a blocked attempt, not a closed Phase 3 partition.
- **Source:** HEAD `4182996d37f9419e4fe6368c6a2a1a924f783f0f`, prescribed symlinked 3-11 `G_new/ALLDATA.KWI` SHA256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`, symlinked original spool and Python environment. Inputs preserved in place; no main-checkout output deleted. Dump manifest SHA256 `a54b07e6bb5706a02ee7174e36754da6b90816ae89310e8d04949a0b8031b996`.
- **Reproduce:** `run.py` records exact sequential invocations recovered from 2-07 conventions; every heavy invocation uses `flock output/.heavy.lock`. Three dump-off K1 runs at -j12, one -j1, one -j12 dump run, final tracked background-then-other rules classify, full AU build, Perth -j1/-j4, exact full pytest -q -x. `strip_timing.py` removes only timing. Do not substitute this dump's missing historical side columns; native classify failure is retained.
- **Pins:** existing committed `triage/pinned_candidates.tsv` SHA256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a` is a truncated historical candidate view; no new non-git final pinned list produced.
- **Why not committed:** regenerable multi-GB dump/build/test artifacts. Preserve the final dump and logs for later phases to resolve oracle, attribution, pin and determinism gates.


## `output/scratch-3-90/fresh-59994c23/` — Ledger brief 121 fresh verification, 2026-10-04

- **What:** new native final failure dump `dump/`, five newly generated K1 reports/raw logs, timing-only canonical files, final tracked merged rules, classifier rejection, visible pinned group keys and unproven set-diff report, one AU/two Perth build products, full pytest and numbered check reports. Verification remains blocked; no closed partition asserted. Earlier scratch products were preserved and not used as fresh evidence.
- **Source:** parent HEAD `59994c23d8a924f1dd035646e44febdaa60ee09c`; oracle input `output/scratch-3-11/G_new/ALLDATA.KWI` SHA256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`, symlinked original spool and `.venv-rp`, all retained. Fresh dump manifest SHA256 `a54b07e6bb5706a02ee7174e36754da6b90816ae89310e8d04949a0b8031b996`.
- **Reproduce:** this subdirectory's `run.py` contains sequential commands; three -j12 dump-off K1 runs, one -j1, one -j12 dump, unchanged final-rule classify, AU -j12 and Perth -j1/-j4 builds, full `.venv-rp/bin/python -m pytest parser/tests -q -x`. Heavy invocations use `flock output/.heavy.lock`. `strip_timing.py` removes only timing; `record_fresh.py` derives the required verdicts from this run's products.
- **Pins:** named committed `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv`, SHA256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a`; explicit 100-row truncated historical view, not a final exhaustive list. No new external pinned list was created.
- **Why outside git:** regenerable multi-GB dump/build artifacts and raw test/run evidence; later phases need these to resolve the oracle, attribution, pins and determinism blockers. Preserve this subdirectory and its inputs.

## `output/scratch-3-90/fresh-66d17c92/` — Ledger brief 121 fresh verification rerun #2, 2026-10-04

- **What:** new native final failure dump `dump/`, five newly generated K1 reports/raw logs (`k1_{a,b,c,j1,dump}.json`/`.log`), timing-only canonical files, final tracked merged rules, classifier rejection, visible pinned group keys and unproven set-diff report, one full-AU and two Perth build products, full pytest output and numbered check reports. Verification remains blocked; no closed partition asserted. Earlier scratch products (`fresh-59994c23/` and ancestors) were preserved and not used as fresh evidence.
- **Source:** start HEAD `66d17c92a96bfefeac6af5f79eca1dcf26b4ef32`; oracle input `output/scratch-3-11/G_new/ALLDATA.KWI` SHA256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`, symlinked original spool and `.venv-rp`, all retained. Fresh dump manifest SHA256 `a54b07e6bb5706a02ee7174e36754da6b90816ae89310e8d04949a0b8031b996`.
- **Reproduce:** this subdirectory's `run.py` (sequential commands) plus `run2.py` (completion of checks 4–7 from the same run's outputs after a harness-report bug): three `-j12` dump-off K1 runs, one `-j1`, one `-j12` dump, unchanged final-rule classify, AU `-j12` and Perth `-j1`/`-j4` builds, full `.venv-rp/bin/python -m pytest parser/tests -q -x`. Heavy invocations use `flock output/.heavy.lock`. `strip_timing.py` removes only `timing`.
- **Pins:** named committed `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv`, SHA256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a`; explicit 100-row truncated historical view, not a final exhaustive list. No new non-git final pinned list was created.
- **Why outside git:** regenerable multi-GB dump/build artifacts and raw test/run evidence; later phases need these to resolve the oracle, attribution, pin, determinism and memory-ceiling blockers. Preserve this subdirectory and its inputs.

## `output/scratch-3-90/fresh-6c3933c2/` — Ledger brief 121 fresh verification rerun #3, 2026-10-04

- **What:** new native final failure dump `dump/`, five newly generated K1 reports/raw logs (`k1_{a,b,c,j1,dump}.json`/`.log`), timing-only canonical files, final tracked merged rules, classifier rejection, visible pinned group keys and unproven set-diff report, one full-AU and two Perth build products, full pytest output and numbered check reports. Verification remains blocked; no closed partition asserted. Earlier scratch products (`fresh-66d17c92/`, `fresh-59994c23/` and ancestors) were preserved and not used as fresh evidence.
- **Source:** start HEAD `6c3933c2ca7420c5bc6ad1b91663d92dfff3c508`; oracle input `output/scratch-3-11/G_new/ALLDATA.KWI` SHA256 `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`, symlinked original spool and `.venv-rp`, all retained. Fresh dump manifest SHA256 `a54b07e6bb5706a02ee7174e36754da6b90816ae89310e8d04949a0b8031b996`.
- **Reproduce:** this subdirectory's `run.py` records the exact sequential commands; three `-j12` dump-off K1 runs, one `-j1`, one `-j12` dump, unchanged final-rule classify, AU `-j12` and Perth `-j1`/`-j4` builds, full `.venv-rp/bin/python -m pytest parser/tests -q -x`. Heavy invocations use `flock output/.heavy.lock`. `strip_timing.py` removes only `timing`.
- **Pins:** named committed `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv`, SHA256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd0948855a`; explicit 100-row truncated historical view, not a final exhaustive list. No new non-git final pinned list was created.
- **Why outside git:** regenerable multi-GB dump/build artifacts and raw test/run evidence; later phases need these to resolve the oracle, attribution, pin, determinism and recurring memory-ceiling blockers. Preserve this subdirectory and its inputs.


## `output/scratch-14/` — plan 14 Phase 1 completeness evidence, 2026-10-05

- **Disc:** Execute restored the existing oracle under flock; SHA256
  `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`
  matched. This evidence pass reads that restored `G_new/ALLDATA.KWI`; no
  re-encode or new oracle. R is `/run/media/codyh/464210-8480/ALLDATA.KWI`;
  spool is `output/extract_timing/spool`.
- **What:** fresh `k1_full.json` / `.log`, completeness-only `dump_raw/`
  (776 unique native rows), gap-annotated `dump_ext/`, classify invocation and
  rejection logs, per-row R/G byte/decode and spool/K1 requirement `witnesses/`,
  input pins, summary and byte-range audit. `classify_completeness/` is the
  requested destination; classify exits 2 before emitting partition outputs
  because `other_mechanism` evidence is absent. No fabricated mechanism bytes.
- **Reproduce:** [plan-14 evidence note](plans/04-c-core-orchestration/triage/completeness_evidence.md)
  and its committed build/audit helpers; heavy work uses
  `flock output/.heavy.lock`, K1 `-j 6`, existing main-checkout `.venv-rp`.
  [Plan 14 record](plans/14-completeness-root-cause.md)
  records the assignment-evidence fallback. Scratch bytes remain outside git;
  the complete native-key TSV and evidence interpretation are committed.
  Protected scratch-3-11 and historical science inputs remain unchanged.
- **Phase 2 unit 2-01 (added 2026-10-06):** `cell_local/` holds the committed
  reproducer's outputs -- `proofs/<dump_row>.json` (per-seed R cell-local
  decode, G cell decode, and clipped-source round/drop test) and `summary.json`.
  Produced by committed
  `plans/04-c-core-orchestration/triage/cell_local_2-01.py` under
  `flock output/.heavy.lock`; reads only R, G (`G_new/`), and the spool. No
  re-encode.
- **Spool incident + recovery (2026-10-06 00:44–02:01):** a resume-setup symlink
  step resolved through the worktree's `output` link and replaced the live
  `output/extract_timing/spool` with a self-symlink (contents lost). Restored by
  re-extracting `australia-260824.osm.pbf` with tree `34a04cc` (last master
  commit before the Sep-21 spool-of-record run; later extractor commits
  `8355950`/`16e2931` change 138/775 witness cells and are NOT the record).
  Proof: L0 counts equal `extract_timing/run.log`; 775/775 Phase-1
  `source_cell_sha256` pins match; full-AU `-j4` re-encode at `f385ef5` →
  `4ed9cd80…` (byte-identical to `G_new`). Record in
  `spool_recovery/INCIDENT.md`; run logs `runs/spool_rebuild_34a04cc.json`,
  `runs/G_verify_encode.json` (run_heavy_python argv + memory.peak). The
  non-record tip extract is parked at `spool_recovery/spool_16e2931_NOT_RECORD/`.
- **Phase 2 unit 2-02 (added 2026-10-06):** `complete_repair/` holds
  `proofs/<dump_row>.json` (EO faces, per-face clipped q/area2 with and without
  densify, production C `bg_shape` record counts), `summary.json`,
  `positive_control.json`, `c_positive_control.json`, and `cprobe/`
  (`probe_bg.c` `#include`s `parser/kiwiw/_cenc.c` read-only; compiled
  `gcc -O2 -ffp-contract=off -fPIC -shared`). Produced by committed
  `plans/04-c-core-orchestration/triage/complete_repair_2-02.py --all-seeds`
  via `parser/tools/run_heavy_python.py` (flock); reads only G sha pin and spool.
- **Phase 3 (added 2026-10-06):**
  - `attribution/`: unit 3-01/3-01b demand attribution.
    - Contents: `proofs/<dump_row>.json` (the checking block's actual `Region`, every demanding shape with a/b/c branch, the EO-face mirror verdict, and production C `bg_shape` records), `summary.json`, `geometry_335.json`, cached tall sets, and `w{1,2}.log`.
    - Produced by the committed `plans/04-c-core-orchestration/triage/demand_attribution_3-01.py` via `run_heavy_python.py`.
  - `r_contribution/`: unit 3-02 R-side proofs.
    - Contents: `765.json` and the per-row 2-02 re-check JSON, built from R slot byte-range decodes of `/run/media/codyh/464210-8480/ALLDATA.KWI`.
    - Produced by the committed `triage/r_contribution_3-02.py`.
  - `p3/`: unit 3-03 orchestrator verification.
    - `k1_p3.{json,log}`: live K1 `-j6` on `4ed9cd80…` after the checker change; completeness 1,800,514 checked, 0 failing; other kinds identical to `k1_full.json`.
    - `dump/`: completeness dump, 0 rows.
    - `G_reencode/ALLDATA.KWI`: full re-encode `-j4` with the rebuilt `_cenc.so`, sha `4ed9cd801bdd7099…`, identical to the disc in force. About 1.6 GB, regenerable.
    - `reencode.log`.
  - **Regenerated 2026-10-06 04:10 (operator slip):** a `--help` smoke test of the moved triage scripts ran `build_evidence.py` (no argument parser; killed by a 120 s timeout) and `verify_evidence.py` for real, outside the plan-25 wrapper.
    - Rewritten: `dump_ext/`, `classify_{invocation.json,stdout,stderr}`, `evidence_verification.json`. Witnesses and discs were untouched.
    - Verified: `dump_ext/completeness.bin` is byte-identical to `dump_raw`; the audit is PASS with unchanged figures (776 rows, 1,791 byte ranges, 775 source witnesses, 1 gap); classify exits 2 as recorded.
  - `p3/indep/`: orchestrator independent check of 3-03.
    - Old checker (`0b19b5e`) and new checker K1 runs on `scratch-3-11/G_new` (`013586b5…`, read only): `{old,new}_k1_311.{json,log}`, the completeness dumps, and `sets.json`.
    - Result: new failing 52 = exactly the keys fixed by the 3-14 build.
  - Wrapper logs: `runs/{attribution_*,r_contribution_*,p3_tests,k1_p3,p3_reencode,indep_old_k1_311,indep_new_k1_311}.json`.


### output/scratch-28/ (plan-14 completeness per-rule recovery)

Tracked producer: `docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.py`.
Inputs are the pinned 776 × 144-byte `scratch-14/dump_raw/completeness.bin`
(SHA256 `1a91b1c26e474b2c689fef9811b73878a4ead144db97eea3aaf6f442ed30d323`),
committed plan-04/14 TSVs, and saved `scratch-14/attribution/proofs/` JSONs.
No spool or disc open; current production C probes run on saved in-memory
rings. Each side row records predicate inputs and its light path. Optional
legacy control skipped. This is a fresh measurement, not historical-byte
restoration; see `docs/plans/04-c-core-orchestration/triage/per_rule_phase1_note.md` and the plan 28 record `docs/plans/28-phase1-per-rule-classify-recovery.md`.

Worker verification: `scratch-28/window25/` contains 25 side rows, the byte-145
dump, real classifier outputs, assignment TSV and generated controls; O01 2,
O04 6, O05 3, NO_RULE 14. Classifier exit 1 is valid. Window command argv and
exit codes are recorded in `scratch-28/window_verification.json`.
New fixture before/after logs are `scratch-28/tests/{before,after}.txt`.
Existing replay tests use a runtime pytest plugin in `scratch-28/tests/` to
relocate their temporary trees there; no plan-05 repository code is edited.

Full baseline execution was run by Execute on 2026-10-06 ~04:36 AEST, in this order, each taking
the plan-25 lock/memory guard and saving its run log. Commands write the
complete tracked TSVs, projection/hashes, controls and run metadata, plus
`scratch-28/dump_mech/` and `scratch-28/classify/`:

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-28/runs/produce.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.py produce --all-rows
```

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-28/runs/projection.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.py projection
```

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-28/runs/dump-join.json -- .venv-rp/bin/python -B parser/tools/dump_join.py --mode other_mechanism --src output/scratch-14/dump_raw --side docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.tsv --dst output/scratch-28/dump_mech --window-rows 25
```

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-28/runs/classify.json -- .venv-rp/bin/python -B parser/tools/k1_triage.py classify --dump output/scratch-28/dump_mech --rules docs/plans/04-c-core-orchestration/triage/per_rule_rules_completeness_projection.json --out output/scratch-28/classify --window-rows 25
```

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-28/runs/publish.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.py publish
```

Expected exits: 0, 0, 0, 1 (valid NO_RULE partition; 0 also valid if measured
complete), 0. Continue to publish after classify exit 1; exit 2 is a failure.
The full-run predictions are yardsticks, never assignments. The generated
controls preserve the 34-versus-31 arithmetic contradiction in DESIGN and
name identity-control mismatches with predicate inputs; exact 3-17 row
comparisons cannot be inferred from counts alone.

Measured: exits 0, 0, 0, 1, 0, with `run_p1.sh` / `run_p1.log` in scratch-28.
- Codes: 4: 363, 5: 132, 7: 7, 0: 274; all 776 rows on the light path, no evidence gap.
- Classify: `PARTITION FAIL` with O01 363 / O05 132 / O04 7 / NO_RULE 274, equal to the 3-15 yardstick.
- Controls: 188/188 historic `NO_RULE`; 89 added split O04 3 / NO_RULE 86.
- `dump_raw` re-hashed `1a91b1c2…` before and after the run.
- Peak memory 81 MB (produce, 57 s).

### output/scratch-29/ (plan 29 K1 name-anchor failure, historical successor)

Not committed; regenerable from the in-force spool. Record: `docs/plans/29-k1-name-anchor-failure.md`.
- `G_new/ALLDATA.KWI` + `manifest.json`: the plan-29 successor, now **historical** (superseded by plan 34's `4e6b0de7…`; kept and protected, never overwritten). sha256 `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`, 1,692,105,152 bytes. Built from `output/extract_timing/spool` (fingerprint unchanged) with the plan-29 route (a) assembly drop guard, `-j4`. The manifest has `out_of_span_names_dropped` L0 1, every other level 0.
- `G_verify/ALLDATA.KWI`: an independent re-encode after the 2-02 accounting fix. Its sha equals `G_new`.
- Diff against the historical oracle `scratch-14/G_new` (`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`, still kept and protected): 146 changed bytes, all inside the L0 (0,541) leaf [928] frame (`docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_diff.json`). `4ed9cd80…` stays the historical oracle for every earlier record.
- `k1_live.json`: live K1 `-j6` on the successor exits 0. name_anchor 2,317,055 checked / 0 failing; completeness 1,800,514 / 0. `compare_k1` passes (`runs/p2_compare_k1b.json`): name checked and range checked each fall by exactly the 1 dropped name, and every other kind is unchanged.
- `perth_base/`, `perth_new/`: the Perth fixture at `cc96570` and with plan-29 code are identical, `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`.
- `run_p2.{sh,log}`, `run_p2b.{sh,log}`, `runs/*.json`: guarded heavy-run logs (`run_heavy_python.py` + `flock output/.heavy.lock`).

### output/scratch-34/ (plan 34 L0 empty-slot frame parity, oracle disc in force)

Not committed; regenerable from the in-force spool. Record: `docs/plans/34-l0-empty-slot-frame-parity.md`; lasting witnesses and gates: `docs/plans/04-c-core-orchestration/triage/l0_empty_slot/`.
- `G_new/ALLDATA.KWI` + `manifest.json`: the **oracle disc in force** (protected; successor of `2ee3456a…`), sha256 `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`, 1,692,079,168 bytes. Built from `output/extract_timing/spool` (fingerprint unchanged) with the plan-34 outside-mask empty-shell omission, `-j4`. Oracle record: `successor_oracle_4e6b0de7.json`.
- Classified diff vs `scratch-29/G_new`: 5 L0 cells `removed_outside_mask_empty_shell`, 0 other (`phase2/au_cell_diff.json`); R `empty_slot` for all 5 (`phase2/r_check.json`); live K1 `-j6` failing 0 (`k1.json`).
- `perth_new/`: identical to `04be2f6e…`.
- `run_p2b.{sh,log}`, `runs/*.json`: guarded heavy-run logs.

### output/scratch-36/ (plan 36 hop replay, region accounting, routed proofs)

Not committed; regenerable. Lasting small witnesses are copied to `docs/plans/04-c-core-orchestration/triage/oracle_chain/evidence/`.
- `G_pre311/ALLDATA.KWI`: the pre-3-11 AU disc, rebuilt byte-exact from a throwaway worktree at `b7c7c42` with `output/extract_timing/spool` at `-j4`. sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 bytes (`sha_pre311.json`). Not a protected disc; it is the historical 3-11 `from` pin.
- `diff-3-11-au.{json,cells.tsv}`: multiset cell diff `87a01b14 → 013586b5`, 37 changed L0 cells, equal to the retained `Gnew.diff_cells.txt`.
- `routed-3-11-au.{json,cells.tsv}`: routed diff, 0 routed-only and 0 baseline-missing cells.
- `region-3-11-au.{json,spans.tsv}`: `region_accounting.py account`. Partition complete, 0 unaccounted bytes, +164 payload, padding 21,570,746 → 21,570,806 over the 41 plan-07 spans.
- `region-3-14-{au,perth}.{json,spans.tsv}` (first tool) and `r2/region-{3-11-au,3-14-au,3-14-perth}.{json,spans.tsv}` (fail-closed tool `183d0ee0…`): 3-14 hop region accounting, AU `013586b5 → 4ed9cd80` and Perth `da13a775 → 04be2f6e`. All complete, 0 unaccounted. The AU JSON is 57 MB and is summarised in `triage/oracle_chain/hop_3_14/container-au.json`.
- `pdmdh-fields-3-14.json`: classification of the PDMDH bytes outside BMT address fields (committed copy in `hop_3_14/`).
- `run_p1_{replay,routed,region}`, `run_p2_region`, `run_r2_region` `.{sh,log}`, `runs/*.json`, `protected_{before,after}*.json`: guarded heavy-run logs and protected-disc snapshots, all unchanged.

### output/scratch-30/attic/ (plan 30 second pinned source: date-matched OSM relation snapshot)

Admitted by plan 30 DESIGN Amendment 1 (Design ruling option (a), 2026-10-06). Not committed (79 MB); the pin is committed at `docs/plans/30-2-01-source-data-parity/phase2_snapshot_pin.json`.

- `relation_snapshot_260824.json`: sha256 `39a836ddb6a1a215abda481f11a286bc8aea63091e27f9470b2adf1447fd47c9`, 78,833,302 bytes. It is canonical JSON with these contents:
  - 117 relations: the 61 in `relation_requests.json` plus 56 direct child relations;
  - 32,573 member ways with node ids and coordinates;
  - 71 member nodes.
- Source: public Overpass API `https://overpass-api.de/api/interpreter`, as three batched POST attic queries with `[date:"2026-08-24T20:20:50Z"]`. That date equals the pinned PBF's `osmosis_replication_timestamp` (`australia-260824.osm.pbf`, sha256 `433a1da2…`). Exact query texts are `docs/plans/30-2-01-source-data-parity/attic/snap_b{1,2,3}.overpassql`.
- Raw responses are `snap_b{1,2,3}.json`, with sha256 `8d493181…`, `6b9739e0…` and `4ef1a8bd…`. They were fetched on 2026-10-06 between 10:58 and 11:02 AEST. All 61 relations are present, no member way is missing, and the newest relation version is 2026-08-23T07:43:34Z.
- Root-cause query: `q1_missing_ways.json` (sha256 `ffdc7732…`, query `attic/q1_missing_ways.overpassql`). The extract polygon is Geofabrik `australia.poly` (sha256 `4353c3c7…`).
- Licence: ODbL 1.0. Data © OpenStreetMap contributors.
- Use: only member-way and member-node geometry for those 61 relations, in the plan 30 `pbf-cache` relation probe. Nothing else enters any build, spool or disc.
- Files are read-only (`chmod a-w`) and protected like the spool.

