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
  converted once with `.venv-rp/bin/python parser/tools/convert_spool.py <old> <new>`.
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
Witness scripts, side tables (`side_background_boundary.npy`, partial: S02 producer scan stopped at the 10,000-ring pin cap), `pins_S02.tsv`, counterfactual windows (`spool_cf/`, `cf_*`) and `dump_attempt3/` (2.6 GB): the 3-03 dump (`output/scratch-3-03/dump`) with one appended u8 column `s02_producer_verified`, built by `output/scratch-3-07/extend_dump_attempt3.py` from the side table. Committed `triage/rules_bg.json` rule S02 needs that column; `classify` against the original dump exits 2. Regenerate: run the 3-07 producer scan script(s) then `extend_dump_attempt3.py` (see `triage/causes_bg.md`, section on the side-table extension); the scan is partial by design until the pin-cap decision. Reviews: `output/scratch-3-07/review/`, `review3/`.

### output/scratch-3-08/ (3-08 cause-table scratch, Phase 3, not committed)
Side tables (`side_interior_cover.npy`, `side_completeness.npy`, `side_name_anchor.npy`, `sources_other.json`), audit scripts, counterfactuals (`cf_count_wrap`, `cf_name`, `cf_completeness`) and `dump_other/` (272 KB for the three small kinds, plus read-only symlinks to `output/scratch-3-07/dump_attempt3` big files): the 3-03 dump with `s02_producer_verified` (byte 144, 3-07) and `other_mechanism` (byte 145, 3-08, previously padding). Committed `triage/rules_other.json` needs these columns; on the original dump `classify` exits 2. Reproduce: 3-07 entry, then the scripts in `output/scratch-3-08/` (see `triage/cause_table.md`). Reviews: `output/scratch-3-08/review/`.

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
- **Dump extension:** `extend.py` copies `dump_new_ext` into `dump_ext`,
  populates `residual_crossing_verified` (u8) at **byte146, previously padding**,
  and checks every other byte against the input. Row size remains152. Exact
  full-key join of status1, default0; inherited fields/flags stay unchanged.
  `dump_ext/dump_manifest.json` records the extension. `rules_bg.json`
  S03/S04/S05 depend on this field; R01/S02 retain priority. This scratch
  dump/side-table dependency is required to reproduce classification.
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
- **Consumer/status:** `triage/causes_residual.md`, fix-unit author and
  mandatory Sonnet 5.5 reviewer. Review is outstanding after a 35-second local
  model-availability timeout and a 90-second concrete review request timeout
  (`review/request_result.json`); no independent reviewer acceptance is claimed.
  Outputs are regenerable large evidence, gitignored; no commit or code fix.
