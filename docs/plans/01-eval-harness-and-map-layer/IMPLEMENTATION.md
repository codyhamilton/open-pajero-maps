## Run

- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01QRzfHS6ESmqmdTRpx1R6m3
- Started: 2026-09-06T06:33:27Z

## Scope of this run

Executing the first two phases of the Execution Phases lane structure only:
Phase 1 = unit 01 (Reference container data). Phase 2 = units 02 (Harness core)
and 07 (Extractor at country scale), which run alongside each other once 01
lands. Units 03–15 are out of scope for this run and remain for a future
`execute` invocation. No close-out in this run — the plan folder stays in
place with the remaining units pending.

## Unit 01 — Reference container data

**Status: done.** Commit `e58b08f` (pushed to `origin/master`).

Delivered `parser/extract_reference_data.py` (reads mounted `ALLDATA.KWI`,
writes `parser/refdata/grid.json` + `mht29_frame.bin`), `parser/kiwiw/grid.py`
(`ReferenceGrid.load/.level(n)/.mht29_frame_bytes()/.to_level_mgmt_record(n)`,
imports only `kiwiw.model` and stdlib), `parser/refdata/README.md`, one
`docs/provenance.md` entry, `parser/tests/test_grid_data.py` (7 new tests incl.
a disc-mounted cross-check against `build_tile_grid_from_lmr`).

Verified against the mounted reference disc: every measured value in the
brief's table matched exactly (7 LMRs in order 12/10/8/6/4/2/0, blockset/
block/parcel counts, grid nx×ny, `lmr_size=170`, `n_bsmr=601`, `n_basic_map=3`/
`n_ext_map=9`, `n_basic_route=2` only at levels 0/2, `node_record_size=8`,
frame tables 16/32/16, coverage lat −50.0..35.3333 / lon 90.0..−142.0
(lon_span=128.0), MHT entry 29 byte 4096/2048 bytes containing the language
code list with `au`). Byte-identical re-run confirmed. Full suite: 139 passed
(baseline 132 + 7 new).

No contradictions reported. One judgment call: `ReferenceGrid` stores the
parsed JSON as a plain dict rather than a fully-typed dataclass tree per
level — `level(n)` still exposes every needed field and
`to_level_mgmt_record(n)` returns a proper typed `LevelMgmtRecord` for unit
12.

## Unit 02 — Harness core

**Status: done.** Commit `1b9dedd` (pushed to `origin/master`).

Delivered `parser/harness/` (`walk.py`, `context.py`, `registry.py`, `report.py`,
`checks/decode.py`, `checks/shape.py`), `parser/compare_disc.py` (thin CLI),
`parser/refdata/harness.json`, `parser/tests/test_harness_core.py`.

Reference self-check (`compare_disc.py --reference /run/media/codyh/464210-8480
--generated .../ALLDATA.KWI --checks decode,pointers,shape,mht29`): all four
PASS, exit 0. Wall time 31m22.9s. Per-level leaf counts: 12=1, 10=9, 8=78,
6=939, 4=14511, 2=231564, 0=3,704,871 — 3,951,973 leaves decoded with zero
errors; every BMT/mapinfo/mfde pointer resolves, no poison leaks; `mht29`
byte-identical; `shape` matches the reference grid exactly.

Full suite: 152 passed. Forbidden-import grep over `parser/harness/` clean.

**Deviation**: done-evidence command 2 (`compare_disc.py --generated
output/ALLDATA.KWI --checks decode` on a current build) could not run —
`output/ALLDATA.KWI` doesn't exist and `build_alldata.py` was mid-edit by the
concurrent unit 07 worker in this shared worktree at the time
(`ImportError: cannot import name 'DEFAULT_ALLDATA'`). Judged as expected
fallout of concurrent work, not a defect in unit 02's deliverable — the CLI
itself is fully exercised by the other three done-evidence commands.

**Bug found and fixed during implementation** (not a brief contradiction):
first draft of the `pointers` check skipped leaves where `decode_parcel()`
raised, which caused a false PASS on the brief's own negative-control case (a
corrupted mfde offset can itself make `decode_parcel()` raise while decoding a
sub-frame). Fixed by having `pointers` re-parse the mfde table directly from
the raw leaf buffer, independent of whether the full decode succeeds.

No contradictions reported against the brief.

## Unit 07 — Extractor at country scale

**Status: done.** Commit `024ed7b` (pushed to `origin/master`).

Delivered restructured `parser/osm_to_parcel_geometry.py` (streaming per-way
tiling into all requested levels, `level_filter` seam for unit 14, longitude
wrap handling), new `parser/kiwiw/spool.py` (`SpoolWriter`/`SpoolReader`: one
append-only `.data` pickle stream plus a `.idx` file per level holding
`{"cells": [(ix,iy,[offsets]),...], "totals": {...}}` sorted by `(iy,ix)`),
and `parser/tests/test_extractor_scale.py`.

Full-Australia run (`australia-260824.osm.pbf`, 11,464,956 ways / 134,709,031
nodes) across all 7 levels in one pass: exit 0, wall time 1:27:24, peak RSS
~9.7 GB, spool size ~21 GB. Per-level parcel counts: L12=1, L10=6, L8=40,
L6=363, L4=4347, L2=44780, L0=349529. Full suite: 152/152 passing (after unit
02 landed; 148/148 in unit 07's own scope standalone).

**Deviations**: `DEFAULT_PBF` made repo-root-relative instead of a hardcoded
home-dir path; `DEFAULT_BBOX` kept as a compatibility alias to
`FIXTURE_BBOXES["perth"]`; `parser/tests/test_grid_data.py` (outside unit 07's
owned-files list) was edited to inline a local disc-decode helper after
`build_tile_grid_from_lmr` was removed, keeping the suite green.

**Contradiction reported (not silently resolved)**: removing
`build_tile_grid_from_lmr`, `DEFAULT_ALLDATA`, and the old
`extract_parcel_geometry(pbf_path, grid, verbose)` signature — as the brief
requires — leaves `parser/build_alldata.py` (out of unit 07's owned paths)
non-functional, since it still imports/calls the old shapes. No current test
imports `build_alldata.py` as a module, so pytest is unaffected. **Resolution
recorded here**: this is expected, not a defect — brief 12
(`briefs/12-assembler-all-levels.md`) already owns a full rewrite of both
`alldata_writer.py` and `build_alldata.py` against the new `ReferenceGrid`
and spool reader, explicitly removing `_SYNTH_CELL_SIZES`/`_make_synth_grid`/
the disc-fallback path. `build_alldata.py` stays broken until unit 12 runs;
no brief amendment needed. Flagging this here so a resumed run knows
`build_alldata.py` is intentionally in a broken intermediate state, not a
regression to chase.

## Run summary (this execution)

Phases 1–2 complete: units 01, 02, 07 all landed on `master`
(`e58b08f`, `1b9dedd`, `024ed7b`), each independently committed, pushed, and
verified against their own done-evidence. Full test suite green at 152/152.
Units 03–15 remain for a future `execute` invocation; their briefs are
already written and unaffected by this run's deviations. No plan-folder
close-out in this run — see Scope note above.

## Run 2

- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01QRzfHS6ESmqmdTRpx1R6m3
- Started: 2026-09-07T00:00:00Z

### Scope of this run

Executing the next two phases per the Execution Phases lane structure:
Phase 3 = units 03, 04, 05 (all depend only on 02, which is done; dispatched
alongside each other on disjoint files). Phase 4 = unit 03b (fresh agent,
depends on 03's kickoff, verifies the real-disc runs and commits unit 03).
Units 04 and 05 commit themselves directly per their briefs.

## Unit 03 / 03b — Reference profile (census) and profile-based checks

**Status: done, with three genuine findings recorded (not silently resolved).**

Unit 03 (implementation worker) delivered `parser/harness/profile.py`,
`parser/harness/checks/{vocab,envelope,mfde}.py`, the `--profile` branch of
`parser/compare_disc.py`, and `parser/tests/test_harness_profile.py`
(synthetic-fixture tests only, all passing). It started two real-disc
background runs against the mounted reference disc and handed off per its
brief's kickoff/handoff split.

Unit 03b (this fresh agent) verified those runs, re-ran `--profile` a second
time in the foreground (15m20s; `git status --porcelain parser/refdata/profile`
shows no change once the first run's output is staged — byte-identical), ran
`.venv-rp/bin/python -m pytest parser/tests -q` (164 passed), and committed
the whole unit together with `parser/refdata/profile/map.json`.

**The self-check (`--reference` and `--generated` both the reference disc)
does NOT pass all three checks, contrary to the brief's done-evidence
expectation.** All three FAILs were run down to root cause; none are fixed
here per this unit's brief ("report it rather than editing unit 03's code to
make it pass").

1. **`vocab` FAIL — genuine finding, not a bug.** `string_type=1` occurs
   1,042,019 times at level 0 across the full census (5.5% of level-0 name
   records: histogram `{1: 1042019, 4: 8877667, 5: 7603420, 6: 1557999}`).
   The 2026-09-05 refinement's "string type 1 never occurs at level 0" was a
   one-city (Brisbane) spot check that does not hold at country scale. This
   also surfaces a live contradiction between `PLAN.md`'s global acceptance
   bullet ("`string_type=1` does not appear") and its own refinement findings
   two paragraphs later ("String type 1 is legitimate at levels >= 2" /
   "forbidden [only] at level 0") — `checks/vocab.py` already implements the
   level-0-only reading and documents the contradiction inline, but `PLAN.md`
   itself is not amended here (per this brief and the plan's own rule:
   report contradictions, do not resolve them silently).
2. **`mfde` FAIL — genuine finding, not a bug.** The full census shows mfde
   entry count and `nregion` are NOT constant per level as the 2026-09-05
   single-parcel-per-level spot check implied — each is a dominant value
   plus a small minority tail (e.g. level 0 entry-count histogram
   `{20: 3690753, 21: 5752, 22: 113, ..., 35: 32}`; level-0 `nregion` is
   `{0: 65536, 1: 3639335}`, not uniformly 1). `checks/mfde.py` enforces
   *every* parcel equal to the profile's *dominant* value, so a self-check
   against a real disc whose own histograms have more than one key at a
   level fails by construction — levels 0/2/4/6/8 (multi-valued) FAIL,
   10/12 (single-valued) PASS, exactly matching the "10 mfde/nregion
   failure(s)" reported (5 levels x 2 fields). The absent-slot encoding and
   per-entry-index presence-class portions of the same check both PASS
   (no offenders in `entry_index_class_offenders`, one absent value
   `(0xFFFFFFFF, 0)` observed everywhere). This narrows the plan's open
   question ("mfde entries 3..19") further for unit 06: entry count and
   `nregion` both vary per parcel within a level in the real data, not just
   per level.
3. **`envelope` FAIL — likely a real bug in `profile.py`'s byte-total
   accounting, not fixed here.** The capacity projection reports
   `generated_map_bytes=4,707,306,016` against a 4,700,000,000 budget (over
   by ~7.76 MB) -- but the actual `ALLDATA.KWI` on the mounted reference disc
   is only 1,529,729,025 bytes. `build_profile()`'s `mapframes_bytes_total`
   (summed from `walk.iter_parcels()`'s per-leaf `length`, i.e.
   `entry.size * logical_sector_size` from `harness/walk.py`) is
   4,680,715,968 bytes -- level 0 alone accounts for 4,543,141,152 of that --
   already ~3x the entire physical file, which is impossible for a subset of
   the file's own bytes. The independently-computed `blocks_bytes_total`
   (summed straight from the PDMDH's BMT tables) is only 26,568,960 bytes,
   ~176x smaller than the leaf-frame total it is supposed to contain, so the
   two accounting paths disagree with each other as well as with the file
   size. Likely candidates (not confirmed): leaf frames shared/aliased
   across multiple parcel-index slots by the divided-parcel mechanism
   (`briefs/13-divided-parcels.md`) being summed once per referencing slot
   instead of once per unique on-disk byte range, or a units/field mismatch
   in how `iter_parcels()` computes a leaf's `length` versus how BMT block
   sizes are computed. Not fixed here; flagged for whoever owns
   `checks/envelope.py`'s capacity projection (touches unit 06's slot
   contract and the level-0 budget trade-off) to run down further.

None of the three FALs were "waved away as expected" -- each was traced to
either a corrected hypothesis (vocab, mfde) or a suspected code defect
(envelope) using the full profile data now checked in, and is recorded here
rather than silently patched.

**Full per-level tables** (from `parser/refdata/profile/map.json`, the
checked-in census):

- **Leaf counts** (matches unit 02's independent decode check exactly):
  L12=1, L10=9, L8=78, L6=939, L4=14511, L2=231564, L0=3,704,871.
- **Name string-type histogram**: L0 `{1:1042019, 4:8877667, 5:7603420,
  6:1557999}`; L2 `{1:25465, 5:14704}`; L4 `{1:4042}`; L6 `{1:1022}`;
  L8 `{1:209}`; L10 `{1:8}`; L12 `{1:8}`.
- **mfde entry-count histogram**: L0 `{20:3690753, 21:5752, 22:113, 23:22,
  24:4163, 25:2308, 26:672, 27:16, 28:160, 29:448, 30:368, 31:48, 33:16,
  35:32}`; L2 `{20:231532, 21:16, 22:16}`; L4 `{20:14433, 21:35, 22:28,
  23:14, 25:1}`; L6 `{20:895, 21:20, 22:16, 23:8}`; L8 `{20:56, 21:9, 22:6,
  23:5, 24:1, 26:1}`; L10 `{20:9}`; L12 `{12:1}`. Absent-slot value
  `(0xFFFFFFFF, 0)` at every level, no other value ever observed.
- **`nregion` histogram**: L0 `{0:65536, 1:3639335}`; L2 `{0:4096,
  1:227468}`; L4 `{0:256, 1:14255}`; L6 `{0:16, 1:923}`; L8 `{0:1, 1:77}`;
  L10 `{0:9}`; L12 `{0:1}`.
- **Map-layer byte totals** (`byte_totals_by_layer`): `pdmdh_blob_bytes`
  21,088; `blocks_bytes` 26,568,960; `mapframes_bytes` 4,680,715,968
  (per-level: L0 4,543,141,152; L2 115,116,704; L4 14,917,536; L6 5,225,536;
  L8 2,303,392; L10 7,840; L12 3,808); `total_bytes` 4,707,306,016.
  `other_mht_entries` non-map total: 454,272 bytes. Real on-disk
  `ALLDATA.KWI` size: 1,529,729,025 bytes (see finding 3 above for the
  discrepancy).
- **Road/display-class vocab**: matches the 2026-09-05 spot check
  (L0 road types `{0,2,3,5,6,7,8}` / display classes `{3,4,7,9,10,12}`;
  L2-8 types `{0,2,3}` / classes `{9,10,12}`) -- confirmed at full scale.

**Wall times**: first `--profile` run (unit 03's kickoff background job):
not separately timed (ran back-to-back with the self-check in one `&&`
chain; see `/tmp/wp1-unit03-profile.log`). Second `--profile` run (this
unit, foreground, for the reproducibility check): 15m20s. Self-check
(`vocab,envelope,mfde` against the same disc): timing not isolated from the
profile run in `/tmp/wp1-unit03-selfcheck.log`, but both commands together
completed before this unit started.

**Deviation from done evidence**: the brief's done-evidence bullet
"`--checks vocab,envelope,mfde` -> all PASS" is not met -- all three FAIL,
for the reasons above. Reported per the brief rather than edited to pass.
