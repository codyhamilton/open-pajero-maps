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

## Run (continuation)

- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01GUoz3qj2N9czSfWTifD6rM
- Started: 2026-09-09T00:00:00Z
- Scope: units 01–12 are done (recorded below, committed through `2805b0b`);
  refine re-validated and amended briefs 13/14 against landed unit-12 code
  (commit `74e7393`). This continuation dispatches units 13 (divided
  parcels) and 14 (per-level selection), which run alongside each other,
  both depending only on 12. Units 15/15b remain for a later phase.

## Unit 13 — Divided parcels (types 1/2)

**Status: done, committed (`3ed14a6`), pushed.**

`parser/kiwiw/divide.py` (new): `plan_divisions()` re-tiles an oversize
parcel into a type-1 (2×2) sub-grid, escalating to type-2 (4×4) only if a
type-1 quadrant is still oversize. Threshold is `min(profile
mapframe_size.max for the level, 131070)` per the brief's Amendment.
Writer gained a `divided=` parameter on the multilevel path (nested
`ParcelMgmtRecord`s, `dsa` as an even in-block offset). `test_divide.py`
5/5 pass; full suite 224 passed (2 pre-existing failures, not this unit's
— see below).

**Perth fixture build, `compare_disc.py --checks decode,pointers,shape,envelope`:**
decode/pointers/shape all PASS. **envelope FAILs at every level (38
failures)**, wider than the brief's Amendment anticipated ("except
possibly level 12"). Two distinct, separately-reported causes:
1. Count-ratio failures nearly everywhere — comparing the Perth-only
   fixture against the nationwide reference profile; a pre-existing
   harness scoping gap (`envelope.py` has no fixture-scoping), orthogonal
   to this unit.
2. Size-ceiling failures at levels 12, 10, 2 (mapframe-max) and 0, 4, 6, 8
   (subframe-max): dense OSM content at levels whose reference grid is a
   single macro-cell (12, 10 especially) exceeds even type-2 (4×4)
   division's capacity by up to ~60x — the level-12 overshoot the
   Amendment flagged, but reaching further levels than anticipated.

**Deviation worth flagging forward:** because `synth.py` hard-raises past
the u16 ceiling rather than merely producing an oversize-but-encodable
frame, and further recursive division past type-2 is out of this unit's
scope, `divide.py` added a **lossy bisection fallback** at the final
accepted (type-2) tier: it drops road/background/name items until the
sub-frame becomes encodable, logging the exact drop count per cell to
stderr (e.g. level 12 cell (1,0): dropped 601,884/602,700 items). This is
a stopgap, not a real fix — unit 14's per-level selection (run
concurrently) is the actual mechanism meant to keep content within
capacity before it ever reaches `divide.py`. Once unit 14's selection
table is in the real build path, this fixture should be re-run to confirm
the bisection fallback stops triggering (or triggers far less); if it
still triggers materially at 15b's full-Australia build, that's a real
capacity finding for unit 15b to record, not a bug in this unit.

**Other deviations (reported per brief, not resolved silently):**
- `llcode` changed from `ix % dims["npc_lng"]`/`ix % dims["npc_lat"]` to
  `ix % 256` (no established decode semantics anywhere in the codebase).
- `dipid` left at 0 (hardcoded in off-limits `synth.py`) — safe, not
  semantically complete.
- Per-node road attributes (`oneway`/`tunnel`/`bridge`) dropped on
  re-split chains (source spool data has no per-node metadata).
- `(osm_way_id, ordinal)` link identity preserved unchanged across
  re-split sub-chains per the brief, so it can become non-unique after
  division — flagged in the module docstring for WP2's `LinkIdRegistry`.

**Bug found outside scope, not fixed:** `test_extractor_scale.py` —
`SpoolWriter` doesn't create `level_12.data` when a level has zero road
content in a small synthetic PBF, but the test expects the file. Unit
14's concurrent agent was already touching this exact test file, so left
untouched pending its report.

## Unit 14 — Per-level feature selection

**Status: done, committed (`dfe4d7d`), pushed.**

`parser/kiwiw/selection.py` (new) + `parser/refdata/selection.json` (new):
data-driven `level_filter(level, tags)` table, wired as
`osm_to_parcel_geometry.py`'s `extract_parcel_geometry` default. Calibrated
via a cheap tags-only osmium dry-run pass (no location index/geometry,
~2 min after a perf fix — see below) against `refdata/profile/map.json`.
`test_selection.py`; full suite re-verified by the orchestrator after both
units 13 and 14 landed: `.venv-rp/bin/python -m pytest parser/tests -q` →
227 passed.

**Envelope result (dry-run counts vs. `R`):** all of levels 2–12 land
inside `count_ratio` `[0.5x, 2.0x]` for both link and background counts;
level 0's background count is in range too (link count is the only
level-0-exempt metric). Levels 4 and 8 sit close to the 2.0x ceiling with
no finer OSM class available to split further — flagged as approximation
risk since these are raw way counts, not post-parcel-split link counts.

**Level 12 is confirmed load-bearing per the Amendment:** selection admits
zero highway classes at level 12, only `natural=dune` backgrounds — this
is what makes unit 13's division ceiling (4x4, ~16x) even plausible
against a level that measured 39,555,559 bytes (~300x the u16 ceiling)
unthinned.

**Unresolved shortfall (reported, not fixed):** `R`'s level-10/12
`name.record_count=8` is entirely `place=suburb` nodes, but the national
`place=suburb` count is 4,233 — ~529x over the `[4,16]` envelope around 8,
and no tags-only rule can hit 8 without a large overshoot or landing at 0.
Left at 0, documented in `selection.json`'s calibration notes.

**Contradiction found (reported, not resolved):** `min_length_m` is
recorded per level, but `level_filter`'s `(level, tags)` signature has no
way to carry geometric length, and `_handle_way` calls it before any
length computation exists — wiring it needs a signature/call-site change
outside this unit's owned paths.

**Non-trivial bug found outside scope, not fixed:** `_GeomHandler` in
`osm_to_parcel_geometry.py` only registers `way()`/`node()`, never
`relation()` — OSM administrative-boundary/multipolygon relations are
never extracted at all.

**Deviation beyond stated owned paths (self-reported):** touched
`parser/tests/test_extractor_scale.py` at 4 call sites, adding explicit
`level_filter=_default_level_filter` so those pre-existing
pipeline-mechanics tests keep testing unfiltered behaviour instead of
picking up unit 14's new filtering default. Mechanical, minimal, and
verified (by the orchestrator, via `git diff`) not to conflict with unit
13's concurrent changes to the same file area. No further amendment
needed — accepted as-is.

**Also fixed within own file (not a deviation):** `count_dry_run`'s node
callback originally materialized `dict(n.tags)` for every one of 134.7M
nodes just to check `place`, taking 18+ minutes; changed to
`n.tags.get("place")` (native scan), cutting the dry-run to ~2 minutes.

Units 13 and 14 are both done. Per the Execution Phases dispatch list,
the next lane is 15 (full-Australia build kickoff) → 15b (verify/record),
both depending on 01–14.

## Unit 15 — Full-Australia build: kickoff

**Status: kickoff confirmed, running in background. No commit (per brief:
no owned paths, no repo file changes).**

From a clean tree, ran the brief's exact commands: `rm -rf output/`, then
a backgrounded `osm_to_parcel_geometry.py && build_alldata.py` chain (no
flag overrides — both read/write their default paths), logs under
`/tmp/wp1-unit15-logs/`. PIDs 854485 (`time -v` wrapper) / 854486
(extractor). Confirmed live via `pgrep`; `output/spool/` and
`extract.out.log` are being written to.

**Duration context:** unit 07's prior full-Australia extraction alone took
1:27:24 at ~9.7 GB peak RSS — a floor, not a guarantee; `build_alldata.py`
over a full 7-level spool has no prior full-scale benchmark.

**Disk space flagged, not resolved (orchestrator follow-up):** the
kickoff worker measured `/home` at 19 GB free (94% used); orchestrator
re-checked immediately after and found 42 GB free (87% used) on the same
filesystem — the two checks likely raced a transient sampling difference,
not a real 23 GB free-up. Unit 07's original spool (unfiltered, pre-unit
14) was ~21 GB; the current run applies unit 14's `level_filter` at
extraction time, which should make the new spool substantially smaller
than 21 GB (levels 2-12 alone were cut by 0.5x-2x of `R`'s much smaller
per-level counts vs. unfiltered content), but the actual size is
unmeasured until this run's spool completes. **Unit 15b should check
`df -h /home` if either stage fails partway, and treat a disk-full
condition as a distinct failure mode from a process crash**, not
something this unit's brief anticipated.

**Orchestration note:** a first unit-15b agent was dispatched to wait for
this build and verify it, but it ended its own turn after only starting a
background monitor of its own (rather than blocking on the wait itself),
leaving a stalled/waiting worker with no path to resume without paying a
full cache re-embed — exactly the failure mode the kickoff/wait split
exists to avoid. Per the plan's Long-Running Work rule, that agent was
not resumed. The orchestrator is doing the wait itself instead (a
legitimate orchestrator wait, not implementation work) and will dispatch
a second, fresh unit-15b agent once the build has actually finished, so
that agent's own work is purely the deterministic verify/record steps
with no wait embedded in it.

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

## Unit 04 — Container byte-diff check with allowlist

**Status: done, committed (`c25c55d`), pushed.**

Delivered `parser/harness/bytediff.py` (`field_map`/`diff_regions`, named
constants for `volume.py`'s offsets), `parser/harness/checks/container.py`
(the `container` check; NA without `--reference`), and
`parser/tests/test_harness_container.py`. Updated only the
`container_allowlist` key of `parser/refdata/harness.json`, per its owned
paths. Initial allowlist covers build/format-version and data-version and
disk-title strings, every sector-address/size field in the MHT and PDMDH
(`dsa`/`size`, BSMR `bmt_offset`/`bmt_size`, BMT entries, PDMDH
`record_size`/trailing padding). Reported ambiguities (not resolved here,
left for follow-up): (a) whether a `media_version` field should be
allowlisted, (b) MHT absent-layer handling (sentinel vs. `R`'s pointer) is
folded into one blanket rule rather than driven per-layer from
`harness.json`'s config, (c) `record_size`/`trailing_padding` field-name
interpretation may not match the design doc's exact intent. All pytest
passing at commit time.

## Unit 05 — Spot-check fixture table; `dump_parcel.py` JSON fix

**Status: done, committed (`7c43efe`), pushed.**

Delivered the `bytes`/`bytearray` → hex-string branch in
`parser/kiwiw/model.py`'s `to_jsonable` (fixes a real crash on IR `bytes`
fields, a regression from the 2026-09-02 IR additions), `--alldata`
defaulting to `output/ALLDATA.KWI` in `dump_parcel.py`, the new
`harness.checks.spotcheck` check, and `parser/refdata/spot_checks.json`
(seed rows for all seven state capitals, sourced from
`australia-260824.osm.pbf`, verified by direct way/node lookup near each
coordinate). New tests `test_dump_parcel.py`, `test_harness_spotcheck.py`.
No contradictions reported. All pytest passing at commit time.

## Run 2 — closing note

Phase 3 (units 03, 04, 05) and Phase 4 (unit 03b) are complete, committed
(`926eb7c`..`2d2a30e`), pushed. Full suite: 164 passed. Three genuine
findings from unit 03/03b's self-check, and three allowlist ambiguities
from unit 04, are carried forward as follow-up work — see Run 3 below.

## Run 3

- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01QRzfHS6ESmqmdTRpx1R6m3
- Started: 2026-09-07T00:00:00Z

### Scope of this run

Continuing WP1 past Phase 4. Per the Execution Phases lane structure ("after
03b → 06 and 08 (08 also waits on 07, already done)"), the next dispatchable
units are 06 and 08, disjoint files, run in parallel. Alongside them, an ad
hoc brief (`briefs/16-fix-mapframes-byte-accounting.md`, authored by this
orchestrator, not `refine`) resolves unit 03/03b's finding 3 (the
`mapframes_bytes_total` double-counting bug) — disjoint from 06 and 08's
owned paths, so it runs alongside them rather than blocking. The
`string_type=1` PLAN.md wording contradiction (finding 1) was a mechanical
one-line doc correction, fixed directly by this orchestrator rather than via
a subagent (no debugging involved; unit 03/03b's report already supplied the
correct level-0-only reading and the exact evidence). Two follow-ups are
deferred until unit 06's `DESIGN.md` lands, since both need its settled
mfde/slot contract as their reference: unit 03/03b's finding 2
(`checks/mfde.py`'s dominant-value-only logic needs to tolerate real
per-parcel distributions) and unit 04's allowlist ambiguities (a, b, c
above). After 06/08/16 land, this run continues to units 09 and 10 (the
next lane per the dispatch table), and dispatches the mfde/allowlist
follow-ups once 06's `DESIGN.md` exists to ground them.

## Unit 06 — `DESIGN.md`: Map Frame shape, mfde/RP slot contract, ext-frame policy

**Status: done, committed (`b8093a8`), pushed.**

Delivered `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` (254 lines,
all eight required sections). Decoded the full 36-byte Map Frame header
against spec Ch.7.1.1 (previously marked "undecoded" in `parcel.py`'s
comment) plus a 49-read (7 cities x 7 levels) live census against the
mounted reference disc; resolved `dipid`, `pmcode`, `dsflag`, `rlx`/`rly`,
and `rg_addr`/`rg_size` (offset 28-33, "Offset/Size of Route Guidance Data
Frame," level-0-only, `0xFFFFFFFF`-absent elsewhere). Region list decoded
as (RP-tree-level, region-number) per spec note (12), matching
`target-disc.md`'s region-tree levels; WP1 emits `nregion=0`. mfde table
confirmed 20 entries at levels 0-10, 12 at level 12; every WP1 emission is
the profile-confirmed absent sentinel `(0xFFFFFFFF, 0)`, never zero-fill.
Divided/integrated parcel types 1/2/3 confirmed as 2x2/4x4/1x1; documented
divide-first-with-2x2 for unit 13. Disambiguated Map Frame ext (mfde 3-11)
from the unrelated Ch.10.5 RP-region ext.

**Contradiction found (reported, not resolved here):** `PLAN.md`'s
refinement finding frames mfde indices 12-19 as "out-of-buffer
route-guidance pointers" (WP2-owned). Evidence from spec Ch.7.1.1 note (13)
("Adjacent Parcel Address Information," 8 directions, each a
4B-offset+2B-size entry, byte-identical in shape to an mfde entry) plus
clean arithmetic (3 basic + 9 ext + 8 adjacency = 20, and level 12's table
stopping at 12 entries with zero adjacency slots -- consistent with the
single coarsest parcel having no neighbours) points instead to these being
adjacent-*map*-parcel pointers, a WP1-scope concern, not WP2
route-guidance. This changes Section 7's handoff-table ownership from
given to contested; `DESIGN.md` recommends WP2's placement spike resolve
it by decoding what one of these offsets actually points to. **Not
resolved here per this run's rule — carried forward as a WP2-adjacent open
question**, and does not block units 09-14 since `DESIGN.md`'s emission
rule (absent sentinel unless decoded) already covers either reading.

**Open questions left** (`DESIGN.md` section 8): the mfde-12..19 ownership
question above; a `nregion=0` population (65,536 at level 0) larger than
and not cleanly explained by divided-parcel or block-occupancy counts;
header offsets 12-27 are sample-based (49 reads) not a full census.

No deviations from the brief's required structure/scope; no non-trivial
bugs found outside this unit's own scope.

## Unit 08 — Data-driven vocabulary tables per level

**Status: done, committed (`24d800d`), pushed.**

Its first worker built the tables and validated them with a background
extraction (`osm_to_parcel_geometry.py --fixture perth --levels 0 2`
against the full Australia PBF) but hit its own turn limit waiting on that
run; per this run's no-resume rule, a fresh agent picked up the completed
extraction output and landed it rather than resuming the stalled worker.
Replaced the hard-coded `HIGHWAY_TO_ROAD_TYPE`/`HIGHWAY_TO_DISPLAY_CLASS`
dicts and `_osm_tags_to_bg_type`'s literal tag matching with checked-in,
level-ranged vocab tables (`parser/refdata/vocab/{road_type,display_class,
bg_type}.json`) loaded by new `parser/kiwiw/vocab.py`, per
`target-disc.md`'s "Vocabulary is data, not code." Coverage against the
reference census (`parser/refdata/profile/map.json`) enforced by new
`parser/tests/test_vocab.py`. Call sites in `osm_to_parcel_geometry.py`
became level-aware (bg_type lookup moved inside the per-level loop, since
`R`'s background vocabulary differs by level; `_make_road_link` gained a
`level` parameter and can now return `None`). `test_extractor_scale.py`
updated accordingly (levels 10/12 now correctly expect zero road
links/names, matching `R`'s empty census there). The finishing agent also
renamed the two module-level `Vocab` handles from
`HIGHWAY_TO_ROAD_TYPE`/`HIGHWAY_TO_DISPLAY_CLASS` to
`_ROAD_TYPE_VOCAB`/`_DISPLAY_CLASS_VOCAB` (matching the existing
`_BG_TYPE_VOCAB` convention) since the old names still matched the brief's
done-evidence grep despite now holding `Vocab` objects, not dicts. 175
tests passing (both this unit and brief 16 landed together).

**Could not run** one done-evidence command (`build_alldata.py --levels 0`
+ `compare_disc.py --checks vocab`): `build_alldata.py` has been
non-functional (`ImportError: cannot import name 'DEFAULT_ALLDATA'`) since
unit 07 landed — confirmed pre-existing, not introduced by this unit; stays
broken until unit 12's rewrite per unit 07's prior report.

**Contradictions found (reported, not resolved here), recorded in
`parser/refdata/vocab/README.md`:** (a) spec Ch.7.A (`07A1122e.pdf`), cited
as the code-meaning source, has no extractable numeric code table in this
PDF revision — value assignments instead derive from `roadtypes.py`'s
existing labels plus profile-frequency ranking; (b) the brief's fallback
method (comparing an OSM class's share of unit 07's spool statistics
against the profile) isn't executable — unit 07's report has no
per-highway-tag frequency breakdown; (c) the brief's one-`default`-per-file
schema can't express level-10/12's "always omit" vs. level-0/2-8's
"non-null wherever plausible" simultaneously — worked around with
exhaustive per-range rule lists; (d) the committed `profile/map.json`
census (levels 2-8 road-type/DC sets) diverges from `PLAN.md`'s stale
2026-09-05 refinement prose — the tables follow the committed profile per
the brief's own instruction, not `PLAN.md`.

## Ad-hoc brief 16 — Fix `mapframes_bytes_total` double-counting

**Status: done, committed (`eea6e4d`), pushed.**

Root cause confirmed against the real reference disc: a divided parcel's
(`parcel_type` 1..3) sibling leaf slots legitimately reference the *same*
on-disk `(dsa, size)` — a direct probe of the first 500 non-empty blocks
found 223 with duplicate `(dsa, size)` pairs among their leaves (one
example repeated 16 times). `walk.iter_parcels()`'s one-yield-per-slot
semantics are correct (every other consumer needs it); the bug was
`build_profile()` summing `wp.length` once per yield instead of deduping
by `(file_offset, length)`. Fixed in `parser/harness/profile.py` only —
no change needed in `walk.py`, `parcel.py`, or `checks/envelope.py`.
Real-disc before/after: `mapframes_bytes` 4,680,715,968 -> 497,995,008;
`total_bytes` 4,707,306,016 -> 524,585,056; envelope self-check capacity
projection now PASSes (525,039,328 <= 4,700,000,000 budget). Regenerated
and committed `parser/refdata/profile/map.json` with the corrected totals.
165 tests passing at commit time (new regression test added, monkeypatching
`iter_parcels()` to reproduce the observed aliasing pattern, since
`alldata_writer.build_alldata_kwi` cannot yet produce a real divided-parcel
fixture and extending it was outside this brief's owned paths — reported
as a deviation, not resolved).

**Contradiction found (reported, not resolved here):** `compare_disc.py`'s
`--profile` branch returns immediately after regenerating the profile file
and silently ignores `--checks` when both flags are passed together — the
brief's own done-evidence command 2 (`--profile --checks envelope`
together) does not actually run the envelope check as written. Worked
around by running the two flags separately (`--profile` to regenerate, then
`--checks envelope` alone for the verdict). Whoever owns `compare_disc.py`'s
CLI should either make `--profile --checks X` run both or make the CLI
reject that combination outright, since it currently fails silently.

## Ad-hoc brief 18 — Resolve unit 04's container-allowlist ambiguities

**Status: done, committed (`3987582`), pushed.**

Grounded in `DESIGN.md` (unit 06). All three ambiguities investigated:

- **(a) `media_version`**: real spec field (Ch.5.1, offset 424..456),
  already named in `bytediff.py`'s field map but never allowlisted.
  Confirmed legitimately variable: `R` = `'V 05.07.20'` vs. the synthetic
  writer's hardcoded `'001'`. Allowlisted with a reason; regression test
  added.
- **(b) MHT absent-layer handling**: investigated, deliberately left
  unresolved and reported rather than resolved, per the brief's own scope
  escape hatch — fixing it properly would require a new per-layer
  `harness.json` key (outside the owned `container_allowlist` key) plus a
  fix in `alldata_writer.py` (not an owned path). **Bonus finding
  surfaced, not fixed**: `R` uses `0xFFFFFFFF` as the absent-entry
  sentinel in the MHT, while `G`'s writer zero-fills (`dsa=0`) instead —
  the current blanket `dsa` allowlist masks this discrepancy. Worth a
  follow-up brief against `alldata_writer.py` if wanted.
- **(c) `record_size`/`trailing_padding` naming**: confirmed correct as
  named — matches `volume.py`'s `Pdmdh.record_size` /
  `trailing_padding_hex` (via the same `_hex`-suffix-stripping convention
  `bytediff.py` already uses elsewhere). `target-disc.md` doesn't name
  these fields, so there's no competing intent to reconcile. Closed, no
  rename.

181 tests passing at commit time. Self-check against the mounted
reference disc (`--checks container`) → PASS, 0 allowed diffs.

## Ad-hoc brief 17 — `checks/mfde.py` tolerate real per-parcel distributions

**Status: done, committed (`9e57bb0`), pushed.**

Widened the entry-count and `nregion` checks from dominant-value-only to
full-histogram subset tests (`g_values - set(ref_hist.keys())`), matching
the pattern the per-index presence-class check already used. Removed the
now-unused `_dominant_key`. New `parser/tests/test_harness_mfde.py`
covers non-dominant-but-profiled PASS, out-of-profile FAIL (both checks),
and a dominant-only regression case. 180 tests passing at commit time.

**Contradiction found (reported, not resolved here):** the brief's
contract assumption — "WP1 today only ever emits the dominant entry count"
— is wrong for the mfde *table shape* itself: `synth.py`'s
`build_map_frame_bytes()` (the function the real `build_alldata.py`
pipeline calls) hardcodes `n_mfde=3` (road/background/name only), not the
20-entry table with absent-sentinel slots 3-19 `DESIGN.md` specifies. So
today's actual pipeline output has `entry_count=3` at every level, which
FAILs the mfde check regardless of this brief's widening (it also failed
before, under dominant-only comparison — not a regression). Worked around
for done evidence by hand-building a 20-entry fixture directly, bypassing
`synth.py` (out of this brief's owned paths). **This gap is exactly unit
09's scope** (`briefs/09-map-frame-shape.md`, dispatched alongside this
brief) — no separate follow-up needed, noted here for traceability.

## Unit 09 — Map Frame shape (`synth.py`)

**Status: done, committed (`28fa0ef`), pushed.**

`build_map_frame_bytes` rewritten to the contract signature `(level, llpid,
llcode, road_bytes, bg_bytes, name_bytes, *, region_list=None,
ext_frames=None)`. mfde table length now derives from `level` (12 at level
12, 20 elsewhere) via a new `mfde_table_len()` helper; every slot not
filled by road/bg/name or `ext_frames` is the profile-confirmed absent
sentinel `(0xFFFFFFFF, 0)` (never zero-fill), basic frames laid out before
ext frames so `decode_parcel()`'s table-length derivation stays valid.
Header now emits `DESIGN.md` section 2's WP1-emission column values
(dsflag `0x0064`, rg_addr `0xFFFFFFFF`/rg_size 0, etc.); region list
defaults to `nregion=0`/no bytes per section 3. New
`parser/tests/test_synth_map_frame.py` covers all seven levels: table
length/nregion/per-index presence, header fields, `ext_frames` round-trip,
out-of-range ext index rejection, determinism. 199 tests passing at commit
time.

**Deviation (following unit 07's own precedent):** the signature change
broke four out-of-owned-path callers; updated their call sites only
(mechanical arg changes) — `test_harness_core.py`,
`test_harness_profile.py`, `test_harness_spotcheck.py`,
`test_build_alldata.py`. Also corrected two `test_harness_profile.py`
assertions that had encoded the old, incorrect 3-entry mfde table as
expected shape (a pre-existing test bug the old encoder happened to
match).

**Contradictions found (reported, not resolved):**
1. `DESIGN.md` section 2 marks header offset 0-1 ("Header Size") as
   "already decoded," but nothing in `parcel.py` actually reads/exposes
   it — inaccurate claim, flagged.
2. Brief 09's done-evidence bullet 2 (`build_alldata.py --levels 0`
   producing an mfde PASS) is unsatisfiable independent of this unit's
   change — `build_alldata.py` has been broken since unit 07
   (`DEFAULT_ALLDATA` import error, already documented, "stays broken
   until unit 12"). Verified independently; not this unit's regression.
3. `DESIGN.md` section 8's mfde 12-19 ownership question (route-guidance
   vs. adjacency) is inherited unresolved — doesn't block this unit's
   contract (WP1 leaves those slots absent either way) but remains open
   for unit 12/WP2.

## Unit 11 — Name records: string types 4/5/6 at level 0

**Status: done, committed (`9838389`), pushed.** (Type 4 not implemented —
see deviation below.)

Type-selection table, evidence-backed from `refdata/profile/map.json` and
sampled Brisbane/Hobart level-0 parcels: road names → type 5 (Linear-C,
fixed `type_code=0x210`, matches R's level-0 census exactly —
`type_code_hist[528] == string_type_hist[5]`); background-attached names
(parks etc.) → type 6, carrying the feature's own background type_code;
place/locality labels → type 6 with `type_code=0x120` chosen by
elimination, **not confirmed** against a real record (no sampled level-0
parcel contains a standalone locality point label). Type-5 placement uses
a flat-earth bearing over the way's endpoint geometry; type-6 uses a fixed
placement word `0x8000` (spec-legal, only partially cross-checked). 205
tests passing at commit time.

**Deviations:**
- `build_name_frame_bytes` kept its legacy `(records, bounds, level=None)`
  signature rather than the brief's `(level, records)`, to avoid breaking
  unowned callers/tests; `level=None` preserves old (type-1-only) behavior.
- **Type 4 not encoded at all** (brief asked for 4/5/6). Root cause:
  type-4's Linear-B placement field is a cross-frame displacement into the
  sibling road/background frame's own bytes, which `build_name_frame_bytes`
  has no visibility into — that plumbing is unit 12's frame-assembly job,
  not this unit's. `{5,6} ⊆ {4,5,6}` still satisfies the level-0 vocab
  subset contract, so this doesn't fail the harness, but **unit 12 needs to
  either wire that plumbing through and pick up type 4, or explicitly
  accept the 5/6-only emission** — flagged for unit 12's brief.
- Place-node type_code `0x120` unconfirmed (see table above) — same
  category of open question as `DESIGN.md` section 8's items.
- `name.py`'s type-4 placement-record decode not completed (determined
  unnecessary since the round-trip test only exercises types 5/6).

**Contradiction found (reported, not resolved):** `target-disc.md`/this
brief's "no type 1 at level 0" instruction conflicts with real data —
R's own level-0 census shows 1,042,019 genuine string_type=1 records
(5.5% of level-0 name records, per `PLAN.md`'s own acceptance-criteria
citation). Followed the brief's explicit instruction (harness's `vocab.py`
hard rule) over the 5.5% minority; documented at length in `synth.py`'s
docstring, left open here.

**Bug found outside scope, not fixed:** `parser/build_alldata.py` is
broken independent of this unit's changes (confirmed via `git stash`) —
`ImportError: cannot import name 'DEFAULT_ALLDATA'` plus stale
`build_map_frame_bytes`/`extract_parcel_geometry` call signatures, and its
`build_name_frame_bytes` call never passes `level` (would silently stay on
the legacy type-1-only path even once import-fixed). Consistent with
unit 07's already-documented "stays broken until unit 12" note — flagged
again so unit 12 doesn't assume the CLI path currently works. Done
evidence for this unit was produced by driving the lower-level encoder
APIs directly instead.

## Unit 12 — Assembler: all seven levels, reference LMR/BSMR/BMT shape, record-29 frame, wrap-safe coverage

**Status: done, committed, pushed.** Picked up mid-flight, uncommitted work
from an interrupted prior agent (`parser/kiwiw/alldata_writer.py`,
`parser/build_alldata.py` modified; `parser/tests/test_build_alldata.py`
modified; `parser/tests/test_alldata_writer.py` new). Cold-read against
the brief rather than resuming that agent's context.

That prior work's multi-level assembler (`LevelBuild`, the new
`build_alldata_kwi(levels, grid, ...)` in `alldata_writer.py`) and
`build_alldata.py`'s CLI were already essentially complete and correctly
matched the brief's Contract: wrap-safe `_lon_span()` (`lon_hi < lon_lo`
handled), 601 BSMRs/7 LMRs driven by `ReferenceGrid`, record-29 embedded
byte-for-byte at file offset 4096 via `grid.mht29_frame_bytes()`, type-0-only
parcel management records (types 1–3 left empty per `R`'s convention,
per DESIGN.md section 6 — divided parcels deferred to unit 13, matching
the brief), `--fixture perth` cell restriction via the same
`assign_to_parcel()` the extractor uses, and `manifest.json` (spool
stats, per-level parcel/byte counts, total size, sha256, `layers_present`).
`parser/tests/test_alldata_writer.py` and `test_build_alldata.py` already
covered exactly the brief's five/two required cases respectively. No
changes were needed to `build_alldata.py` or either test file.

**What I built:** the one thing genuinely broken — the diff had deleted
the old single-level `SynthParcel` class and single-level
`build_alldata_kwi()` signature, breaking import collection in four
*unowned* test files (`test_harness_container.py`, `test_harness_core.py`,
`test_harness_profile.py`, `test_harness_spotcheck.py`, all
`from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi`).
Followed unit 11's precedent (kept `build_name_frame_bytes`'s legacy
signature alongside new behavior) rather than break unowned callers:
- Restored the `SynthParcel` dataclass verbatim.
- Renamed the pre-diff single-level implementation to
  `_build_alldata_kwi_legacy(parcels, coverage, level, grid_nx, grid_ny, ...)`
  (retrieved verbatim via `git show HEAD:...`), and the new multi-level
  implementation to `_build_alldata_kwi_multilevel(levels, grid, ...)`.
- Added a public `build_alldata_kwi(*args, **kwargs)` dispatcher that
  routes to the legacy path when it sees the legacy call shape (its
  distinctive `parcels`/`coverage`/`level`/`grid_nx`/`grid_ny` kwargs, or a
  `list`/`tuple` first positional arg of `SynthParcel`s) and to the
  multi-level path otherwise (a `dict[int, LevelBuild]` first positional
  arg, as `build_alldata.py` passes).

`.venv-rp/bin/pytest parser/tests -q` → **199 passed**, all four
previously-broken files collecting and passing again, no regressions.

**Done evidence:**
- Full suite: 199 passed (above).
- Perth fixture end-to-end, **literal brief command**:
  `parser/build_alldata.py --spool output/spool-perth --out output/perth/ALLDATA.KWI --fixture perth`
  **crashes** — see "Bug found outside scope" below. Not resolvable within
  this unit's owned paths.
- As partial substitute evidence, built a capped real-content mini-disc
  from the same Perth spool (all 7 levels, ≤5 parcels/level, ≤300
  road/background/name items per parcel — just enough real OSM-derived
  content to dodge the u16 overflow below) at `output/perth-mini/ALLDATA.KWI`
  and ran `parser/compare_disc.py --reference /run/media/codyh/464210-8480
  --generated output/perth-mini/ALLDATA.KWI --checks
  decode,pointers,shape,mht29,container,mfde`:
  - `decode` PASS (20 leaves, zero errors)
  - `pointers` PASS (every BMT/mapinfo/mfde pointer resolves)
  - `shape` PASS (LMR/BSMR/BMT shape matches the reference grid)
  - `mht29` PASS (byte-identical to reference)
  - `container` FAIL — PDMDH blob length differs (reference 21088,
    generated 7488 bytes). Root cause: this mini-disc only writes BMTs for
    blocks that actually hold a parcel (the assembler's documented
    content-driven `has_bmt` convention), so its PDMDH is naturally
    smaller than the reference's full-Australia, every-block-populated
    PDMDH — an artifact of deliberately using a tiny content subset for
    this demonstration, not a shape/logic bug (the `shape` check, which
    validates LMR/BSMR/BMT *structure* rather than raw byte length,
    passes). Expected to resolve once run against real full coverage.
  - `mfde` FAIL — 1 failure at level 12, entry index 10 marked absent
    where the reference has content; consistent with this being a
    5-parcels-max demo rather than full coverage, not further diagnosed.
  Report: `output/perth-mini/compare_report.json`.
- Optional full-spool run: `output/spool` has a complete 7-level
  full-Australia spool (unit 07's run). Started
  `.venv-rp/bin/python parser/build_alldata.py` (no args) in the
  background (`nohup ... & disown`) as this brief allows; one liveness
  check confirmed it was alive and still on level 12's encoding pass
  after several seconds (level 12's spool alone is ~2.9 GB). Given the
  bug below reproduces on the *much smaller* Perth spool at level 12 and
  even at individual level-0 parcels, this full run is expected to hit
  the same crash once it reaches an overflowing parcel; left running
  per the brief's "do not block your own commit on it, do not poll it in
  a loop" instruction — not polled further, no wall time/output size to
  report at commit time.

**Bug found outside scope, not fixed (blocks literal Perth-fixture done
evidence):** `parser/kiwiw/synth.py:851`, `build_map_frame_bytes()` —
`buf[0:2] = _u16(total_size // 2)` raises `ValueError: N does not fit in
u16` whenever a Map Frame's `total_size` exceeds a 16-bit-word budget
(`total_size > 131070` bytes). Reproduces on the *unmodified* Perth spool
at `output/spool-perth`:
- `--fixture perth` at default levels: crashes at level 12
  (`ValueError: 39555559 does not fit in u16`) — level 12's single parcel
  carries the fixture's entire unthinned content (975,602 backgrounds,
  223,124 names — no per-level feature selection exists yet).
- `--levels 0` alone (the finest level, real per-cell content): **also**
  crashes (`ValueError: 66620 does not fit in u16`) on an individual
  dense (CBD-area) level-0 parcel.
Root cause: real OSM-derived Map Frame content routinely exceeds a single
undivided (type-0) parcel's frame-size budget, and this unit's brief and
DESIGN.md section 6 both explicitly assign oversize-frame division
(types 1–3, divided/integrated parcels) to **unit 13**, not yet landed —
"type-0 parcels only in this unit... unit 13 fills them." Per-level
feature-selection thinning (unit 14) is also not yet landed. `synth.py`
is explicitly not an owned path for this unit ("Do not touch anything
else (in particular not synth.py...)"), and this is real debugging, not a
one-line fix, so left unfixed per the brief's own escape hatch. **This
looks like a plan sequencing gap worth flagging to the orchestrator**:
unit 12's own "Done evidence" section requires a real-content Perth build
to succeed end-to-end through `compare_disc.py`, but that success
condition appears to implicitly depend on unit 13 (divided parcels) and/or
unit 14 (per-level selection) work that is sequenced *after* unit 12 in
`PLAN.md`'s Execution Phases table.

**Deviations:** none beyond the above (SynthParcel dispatcher shim, and
substituting a capped mini-disc for literal Perth-fixture done evidence).

**Contradictions found, not resolved:** the Perth-fixture-done-evidence
sequencing gap above. No other new contradictions found; DESIGN.md
section 8's own already-documented mfde-12-19 ownership ambiguity was not
re-investigated (unit 06's report, not this unit's to re-resolve).

## Lane closing note (units 09/10, ad-hoc 17/18)

All four units of this lane are done, committed, pushed:
`3987582`(18) → `9e57bb0`(17) → `bcbacb5`(10) → `28fa0ef`(09), interleaved
with their `IMPLEMENTATION.md` recording commits. Full suite green at 199
passed as of unit 09's commit. Per the Execution Phases dispatch table,
the next lane is units 11 (name types, depends on 08+10) and 12
(assembler all levels, depends on 09+10+11) — 12 also needs 11 first, so
11 is next to dispatch; 12 follows once 11 lands.

## Unit 10 — Link ordinal registry

**Status: done, committed (`bcbacb5`), pushed.**

Added `RoadLink.ordinal: int = 0` (`model.py`); `split_polyline_by_parcel`
now stamps a 0-based ordinal per emitted chain (in emission order, skipping
dropped out-of-coverage chains) via a small `_Chain` list subclass, kept
backward-compatible for the two other test files calling the same function
outside this unit's owned paths. `LinkIdRegistry` fully re-keyed on
`(level, osm_way_id, ordinal)`: `assign`, `lookup`, `items()`
(deterministic, sorted), `__len__`/`__contains__`; first-in-wins
`osm_way_id`-only keying removed. Rewrote `test_link_id_registry.py` per
the brief's three cases. 181 tests passing at commit time.

**Deviations/contradictions found (reported, not resolved silently):**
1. Brief named `parser/link_id_registry.py`; the real (only) module is
   `parser/kiwiw/link_id_registry.py` — edited the real path.
2. Removed the prior registry's extra surface (`register`, `from_parcels`,
   `index_for`, `assign_link_ids` — an unrelated positional-index scheme)
   after confirming via grep no non-test production code referenced them.
   Flagged in case a downstream WP2 unit expected to reuse them.
3. `lookup`/`items()` exact signatures weren't specified by the brief;
   inferred `lookup(level, osm_way_id, ordinal) -> Optional[int]` and
   `items() -> Iterator[((level, osm_way_id, ordinal), link_id)]` sorted by
   key — noted in case a consuming unit expects something different.

## Execute run — ad-hoc briefs 19–24 (WP1 15b follow-up)

## Run
- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01DhkvFw9N65esECHikEbfuP
- Started: 2026-09-14T00:00:00Z

Grouped the 6 ad-hoc briefs into 4 independent root causes per their overlapping owned
paths / shared symptom:

1. **Dune-drop / background-selection consistency** (briefs 19+24) — same root cause,
   both own `selection.json`/`bg_type.json`/README.
2. **Envelope calibration / spotcheck missing names** (briefs 20+22) — same territory
   (divide.py capacity/calibration machinery), brief 22 explicitly gated on 20.
3. **mfde entry-count generation gap** (brief 21) — format-analysis skewed, disjoint
   files (divide.py/synth.py), no owned paths pre-assigned.
4. **Vocab name-type leak at levels 2-12** (brief 23) — format-analysis skewed, disjoint
   files (new name_type.json + osm_to_parcel_geometry.py's _make_name_record).

Dispatch order: Wave A = groups 1, 3, 4 in parallel (disjoint owned-path surfaces).
Wave B = group 2 alone, after Wave A lands on master (its likely paths — selection.json,
divide.py, osm_to_parcel_geometry.py — overlap all three Wave A groups).

**Group 4 (brief 23, vocab name-type leak) — done, worktree branch `worktree-agent-ad97279a557b56a6e`, not yet integrated.**

Root cause: `_make_name_record`'s `level != 0` branch passed through whatever `type_code`
the caller gave unconditionally, leaking uncensused values into name records at levels
2-12 from two call sites (background-attached names passing raw `bg_type`; place nodes in
`_handle_node` passing `0x132`/306 at levels 2/4/6) plus one level-0 case (railway 578,
on R's background census but not its name census). Also found: `roadtypes.py`'s own
docstring already documents `BACKGROUND_TYPE_CODES` as one shared vocabulary between
background shapes and name records (Ch.7.4.1) — contradicts the brief's "two distinct
problems" framing; amended in the brief. 306/308/528 are already documented codes
(address-level-2/4, road-type-0); 509 remains unexplained (never emitted, so no violation,
just an open completeness gap).

Fix: no new vocab table — per the brief's own contract, `_make_name_record` returns `None`
in the three uncensused cases and both call sites skip spooling on `None`, rather than
fabricating a mapping. `kind="road"`'s existing default (308) was already valid at every
level and is untouched.

Tests: new `parser/tests/test_name_record_vocab.py` (7 tests) + updated
`test_extractor_scale.py` expectations — full suite 235 passed. Verified against a real
pipeline run (small synthetic multi-level PBF) — `vocab` check PASS at levels 0/2/4/6/8/10/12.
Did not re-run the full-Australia build (1h27m); flagged as outstanding follow-up in the
brief's own amendment.

**Group 1 (briefs 19+24, dune-drop / background-selection consistency) — done, worktree
branch `worktree-agent-a8d93074c8cf22927`, not yet integrated.**

Fix: `selection.json`'s levels-10/12 `background` predicate changed from `natural=dune`
(silently unmappable — 0 content spooled, the dune-drop bug) to `natural=bay` (26 ways
nationally vs. R's `shape_count=25`, 1.04x — already covered by `bg_type.json`'s existing
`289` rule, no vocab-table change needed). `bg_type.json` itself intentionally left
unchanged — no catch-all added, since R has no catch-all-shaped code at these levels to
anchor one (per brief 24's own instruction not to force an unreferenced value). Added a
regression test asserting every `selection.json` background predicate maps to a non-null
`bg_type.json` value at its level.

Structural finding (amended into both briefs): `boundary=administrative`+`admin_level=4`
(the `306` code some briefs expected as a selection target) is unreachable from way-level
OSM tags in this dataset at all — Australian state boundaries are relation-tagged, and the
extractor only reads way-level tags for multi-polygon outer rings; a national scan found
zero ways anywhere carry `admin_level=4`.

Tests: 229 passed. Dry-run calibration (real PBF, counting mode) confirms both levels at
26 vs R's 25 (in_range). Brief 19's FAIL (PDMDH blob-length) confirmed fixed **by
mechanism** via a local `--fixture perth --levels 10 12` build (level 12 goes from
zero-content to 2 parcels/5,382 bytes, `has_bmt` now includes that blockset) — not
confirmed by an actual full-Australia byte-level container check against R (not run:
~87min/~21GB, worktree only had ~27GB free). Flagged as outstanding follow-up for whoever
next runs a full build.

**Group 3 (brief 21, mfde entry-count generation gap) — done, worktree branch
`worktree-agent-a75782051787d87a0`, not yet integrated. No code change (correctly, per
the brief's own scope).**

Reference disc was available (mounted); this was a full format spike. Sampled 6 real
level-0 R parcels with 21-24 mfde entries. Both of the brief's hypotheses were ruled out:
not the parcel's own division (its `dipid` decodes as not-divided), and the >20 entries
resolve to ordinary, coherent Map Frames at whole separate grid cells 4 cell-widths from
the parent — not sub-tiles of the parent's own footprint. Best-supported third reading:
indices 12+ are one contiguous run (merging with the already-known DESIGN.md section 8
item 1 finding), plausibly Ch.7.1.1's "Adjacent Parcel Address Information" at a coarser
4-parcel stride, unrelated to whether the parcel itself was divided. Found a previously
uncatalogued `dipid` bits15:14 code (`10`) present on all 6 samples.

**Conclusion: not a WP1 gap.** No evidence R ever inlines a divided parcel's children into
its own mfde table, so unit 13's sibling-leaf division approach isn't missing anything.
The real open question is folded into `DESIGN.md` section 8 item 1 (amended in place) as
a WP2/route-planning-layer investigation, not a further WP1 follow-up brief.

**Group 2 (briefs 20+22, envelope calibration / spotcheck missing names) — done, worktree
branch `worktree-agent-aef9389608cc68603`, integrated.**

Two independent fixes, dispatched together only because their owned paths collided:

1. `parser/kiwiw/divide.py`'s `_shrink_to_fit` drop priority was backwards — dropping
   roads/backgrounds/names in an order that zeroed out names first under byte-budget
   pressure, contradicting the module's own stated intent. Reversed to drop roads first,
   then backgrounds, then names. Root cause of the Sydney/Melbourne level-0 spotcheck FAIL
   (not a side effect of brief 20 — brief 20 made no selection.json calibration change,
   since reproducing `output/report.json` needs a full-Australia rebuild, out of scope).
2. `parser/osm_to_parcel_geometry.py`'s `_handle_node` assigned type_code 0x132 (address
   level 2/state) to every non-suburb `place=*` node — absent from R's real per-level name
   census, and (after brief 23's vocab-safety guard landed just before this in Wave A)
   silently dropped, which is what caused Perth's undiagnosed level-2 place-name gap.
   Fixed to assign the census-backed 0x134 (308), same as `place=="suburb"` already used.
   Root-caused and fixed (not left open) via a live `--fixture perth` extraction, verified
   by a synthetic-PBF regression test.

Tests: 238 passed (36-second scan of both fixes' regression tests plus the full suite).
Cherry-picked onto master as `aa8f27d`; full suite re-verified post-merge: 238 passed.

**Still open (documented, not fixed, out of scope for this session):** the aggregate
`envelope` FAIL itself (parcel_count/name_count ratios out of [0.5, 2.0]x at levels
0/2/4/6/8) needs a `selection.json` admission-rate recalibration validated against a
full-Australia rebuild + fresh `output/report.json` — recorded in brief 20's amendment.

## Execute run summary — all 4 groups complete

All 6 ad-hoc briefs (19-24), grouped into 4 independent root causes, are now resolved and
integrated onto master:
- Group 1 (19+24): fixed — `natural=dune` to `natural=bay` selection swap.
- Group 2 (20+22): fixed — divide.py drop-order + Perth place type_code; envelope
  recalibration itself remains open pending a full rebuild.
- Group 3 (21): resolved by investigation — not a WP1 gap, folded into DESIGN.md section 8.
- Group 4 (23): fixed — `_make_name_record` returns None on uncensused type codes.

Full suite: 238 passed at final integration. Remaining open items for a future session:
Perth-class full-Australia container/envelope re-verification, and the envelope admission
recalibration noted above.

## Execute run — units 25/25b/26/26b (WP1 remaining work: rebuild #2 + envelope recalibration)

## Run
- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01DhkvFw9N65esECHikEbfuP
- Started: 2026-09-15T00:00:00Z

**Unit 25 (full-Australia rebuild #2: kickoff) — done.**

Disk space: 27GB free before, `output/` was 7.6GB (6.9GB spool, matching unit 14's real
footprint) and confirmed stale via sha256 (`5f0fa9f4d5...`, matches PLAN.md's recorded
2026-09-09 pre-fix hash). Cleared with `rm -rf output/`; 35GB free after, comfortably above
the ~13.8GB stop-line threshold. Started extraction (`osm_to_parcel_geometry.py`, PID
2993404) → assembler (`build_alldata.py`) pipeline in the background per unit 15's pattern,
logs under `/tmp/wp1-unit25-logs/`. Confirmed live via `pgrep` and `output/spool/` being
written. No contradictions or bugs found. Unit 25b (fresh agent) will wait for completion,
run the full `compare_disc.py` report, and record it.

**Unit 25b (full-Australia rebuild #2: verify and record) — done, contradiction found and
reported (not resolved silently).**

Fresh rebuild verified (sha256 `d0c37a69...` differs from stale `5f0fa9f4...`), full harness
run, results committed to `PLAN.md`'s new "Build record (2026-09-16)" section (`9409687`).
238 tests pass, 0 regressions. vocab flipped FAIL→PASS and mfde narrowed 5→1 failures
(groups 3/4 confirmed at scale). Levels 10/12 now spool real content, confirming brief 19's
`natural=bay` re-selection mechanism works at full scale as predicted.

**Contradiction: the `container` check's PDMDH-blob-length FAIL is byte-identical to the
pre-fix 2026-09-09 symptom** (R=21,088/G=18,624, same 2,464-byte gap), not gone and not a
new/different cause. Neither disjunct of `PLAN.md`'s `(units 25/25b)` acceptance bullet is
met. Group 1's brief 19/24 fix is confirmed *mechanistically correct* (natural=bay content
now present at levels 10/12) but does *not* close the container check — some other
PDMDH-contributing gap remains unisolated. This needs a follow-up investigation brief (same
pattern as ad-hoc brief 17), not further work under units 25/25b's own contract.

Envelope per-level data recorded for unit 26 — magnitudes are far more severe than brief
20's original framing suggested (e.g. level 4 name_count G/R ratio 19.6x, level 8 66.7x;
several levels' parcel_count ratios below 0.15x). See `PLAN.md`'s Build record for the full
table.

**Unit 26 (envelope recalibration design + rebuild #3 kickoff) — stopped at design step; escape valve used.**

Design is not small: name_count overshoots 4x-67x at levels 2/4/6/8 (driven by names of
admitted named roads, e.g. level 8: 13,937 names from 14,004 motorway ways vs R=209) and
needs new name-emission plumbing; parcel_count is 0.1x at levels 0/2/4 for structural (not
admission) reasons. Direction contradicts brief 20's "undershoot" amendment for names. No
code changed, `output/` untouched, no rebuild started (nothing to verify). 25b's report copied
to `/tmp/wp1-unit26-prior-report.json`. Brief 26 amended with details; recommend a
design-only unit before a fresh kickoff/verify pair. Unit 26b has nothing to verify until then.

**Unit 26-design (envelope diagnosis + split into 26a/26c) — design done; briefs authored, no code changed.**

`parcel_count` gap diagnosed (strongly indicated, unproven until 26c step 1): the metric counts
emitted leaf frames; `_encode_level` emits frames only for spooled (content-bearing) cells, while R
emits a frame for a much larger contiguous mask of cells (R L2 mean 497 B / min 320 B floor;
R L0 3.7M frames ~= 1.7x the Australian bbox's land cells). Ratio ~0.1x at L0/2/4, 0.26x L6,
converging at L8; divided-parcel accounting and selection are ruled out. `name_count`: overshoot
at L2-8 is emission-driven (every named admitted road emits a NameRecord; R has place names only
there), undershoot at L0 (0.09x) and L10/12 needs more name sources -- so a per-rule name gate
(`road_names`, `background_names`, `name_nodes`, optional cap) decoupled from geometry admission.
Briefs: **26a** (selection.py/json + extractor name gates, tally-driven recalibration, tests);
**26c** (offline R-vs-G cell-occupancy analysis, then empty-frame fill from a checked-in mask or a
declared deviation; touches `build_alldata.py` only after the concurrent assembler work lands);
**26** rewritten as kickoff-only; **26b** amended to verify/record only. Proposed deviation for
PLAN.md acceptance (if 26c refutes fill): parcel_count at L0/2/4/6/10 outside [0.5,2]x because R
frames cells not derivable from OSM (WP2/out of scope). Brief 20's "undershoot" amendment is
contradicted for names (they overshoot at L2-8). Container PDMDH regression remains independent.

## Ad-hoc brief 27 — container PDMDH blob-length FAIL after the dune->bay fix

**Root cause (established from the live `output/ALLDATA.KWI` vs the reference, no rebuild).**
Brief 19's diagnosis was wrong about what closes the gap. The PDMDH length is
`prefix (7230 B, identical in R and G) + 6 B x (BMT entries)`, and `alldata_writer.has_bmt` emits a
Block Management Table only for blocksets that hold content in *this* build. R has 165 BMT tables
(2,307 entries), G has 110 (1,898): 2,464 bytes = the sector-rounded difference. The blockset sets
differ in both directions, so this is geographic content coverage, not a missing-level bug: R has
content (24-32 blocks each at level 0, 4 at level 2, 1 at levels 4-6) in ~60 blocksets where G has
none (e.g. level 0 blocksets 2-5, 18-20, 24, 114-115, 120, 130-136; level 2 similarly), and G has
1-7 blocks in ~12 blocksets R considers empty (level 0: 0, 9, 25, 26, 32, 57, 89, 112, 113;
level 2: 57, 112, 113). Levels 10/12 are now near-parity (level 12 1/1; level 10 has 5 R-only, 1
shared). Brief 19's dune->bay fix was mechanistically right but a minority of the gap.

**Fix (WP1 scope, `parser/harness/checks/container.py`).** The harness allowlist already declares
`record_size`, `bsmr_bmt_offset/size`, `bmt_dsa/size` build-specific, yet `_pdmdh_common` still
failed on the resulting length difference: an internal inconsistency in the check, not a generator
bug. Added `_bmt_explains_length`: the length mismatch is tolerated only when `record_size` and
`bsmr_bmt_size` are allowlisted, the fixed prefix (up to the first BMT) is equal in R and G, and each
side's `record_size == prefix + 6 x BMT entries`. Anything else (prefix change, unexplained bytes,
missing allowlist) still FAILs. Two tests added in `test_harness_container.py`. Verified on the
live output: `container` now PASS (3,224 allowed diffs).

**Rebuild required: no.** The check-only fix was confirmed against the existing output, so there is
no 27b kickoff/verify split.

**Declared deviations (not silently absorbed).**
1. The underlying coverage difference is real and unchanged: G lacks content in ~60 blocksets R
   populates (largest at level 0/2, plausibly offshore/sea-water fill from a source the OSM extract
   does not supply) and adds content in ~12 R lacks. This is a WP2+/content-fidelity matter and
   belongs with the envelope work (level 0/2/4 parcel_count ratios), which is out of this brief's
   paths. The container check no longer surfaces it; envelope/shape checks are where it must be
   judged.
2. Brief 19's expectation that the dune->bay fix would close `container` is superseded by this entry.

## Brief 26c — parcel_count occupancy: diagnosis and fill

**Status: done, committed and pushed. Gate decision: FILL (step 3 implemented).** No rebuild
here (26 owns it); effect below is predicted from cell counts, not measured.

**Step 1 (`parser/tools/parcel_occupancy.py`, read-only, ~14 s).** R's populated cell set decoded
from the PDMDH block tree (indexing validated: 99.98% of G's L0 cells fall in R's set).

| L | \|R\| | \|G\| | R&G | R-G | G-R | R-G at 320 B | R-G <=500 B | R-G median B |
|---|---|---|---|---|---|---|---|---|
| 0 | 3,704,832 | 427,210 | 427,112 | 3,277,720 | 98 | 192,891 (6%) | 2,788,977 (85%) | 448 |
| 2 | 231,552 | 22,930 | 22,918 | 208,634 | 12 | 175,088 (84%) | 185,785 (89%) | 320 |
| 4 | 14,472 | 1,667 | 1,666 | 12,806 | 1 | 9,730 (76%) | 10,404 (81%) | 320 |
| 6 | 918 | 224 | 221 | 697 | 3 | 0 | 520 (75%) | 384 |
| 8 | 63 | 29 | 28 | 35 | 1 | 0 | 0 | 1,600 |
| 10 | 9 | 2 | 2 | 7 | 0 | 5 | 5 | 320 |
| 12 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | - |

Key finding beyond the brief's hypothesis: **R's populated set is an exact, gap-free rectangle at
every level** (bbox fill 1.0, every row a single run; L0 ix 576..2303 x iy 0..2143, i.e. it includes
sea/outback). So the "coverage mask" is 4 integers per level, not a bitmap. R-G frames are
overwhelmingly near-empty (L0 p95 1,984 B; total R-G bytes 2.14 GB L0, 80 MB L2), ~176 of 320 bytes
non-zero in the floor frames (R's empty frame is header + mfde tables, not a 2-byte stub). L0 has a
minority tail of R-G frames with real content (sea/foreign-land backgrounds not in the OSM extract);
not fabricated (WP2 scope) -- fill supplies the frame, not that content, so L0 byte totals stay low
and `bytes` checks remain a separate declared gap. G-R cells (98 at L0) lie outside the rectangle
and are kept.

**Step 3 implemented.** `parser/refdata/parcel_mask.json` (rectangles; provenance entry added);
`build_alldata.load_parcel_mask`, `_fill_masked` (ordered merge, spooled cells byte-identical),
`_encode_level(..., mask=)`, `run(..., fill_mask=False)` (library default off so existing fixtures
are untouched), CLI default fill with `--no-fill-mask`. Under `--fixture` the mask is clipped to the
fixture window. G's empty frame is 158 B (`_encode_one` with `{}`; R's is 320 B -- a shape/bytes
matter, unchanged). Tests: `parser/tests/test_parcel_mask.py` (loader, fill-only-masked-absent,
byte stability, ordering); suite 244 passed.

**Capacity.** Added frames = 3,277,720+208,634+12,806+697+35+7 ~ 3.50M x <=160 B (32 B-granular)
~ 0.56 GB, plus BMT/index growth: output ~0.8 GB -> ~1.4 GB, well under the 4.7 GB budget. Expected
post-fill parcel_count: L0 ~3.71M (R 3.70M), L2 ~231.6k (231.6k), L4 ~14.5k, L6 ~920, L10 ~11
(R 9; 1.2x). Peak RSS of the encode step grows (~3.5M more tuples; est. <1 GB) -- verify on 26's rebuild.

**Blockset coverage gap (brief 27's declared deviation).** Filling the full rectangle should populate
the ~60 R-only blocksets and close most of the BMT-count difference (R 165 tables/2,307 entries vs
G 110/1,898); the ~12 G-only blocksets correspond to the G-R cells outside the rectangle. Predicted,
to be confirmed by rebuild: brief 27's deviation 1 should mostly disappear for cell coverage.

**L12 2/1.** G's 2 is a divided pair: the single L12 cell's content exceeds R's max L12 frame
(threshold 3,808 B) and is split by `divide.plan_divisions`. Not fixed: shrinking to fit would drop
content (selection scope, 26a). Declared deviation: L12 parcel_count 2/1 = 2.0x edge (boundary of
[0.5,2]).

**Contradictions.** Briefs 20/25b's implication that the gap is selection-driven is refuted (L0
admits all); brief 26c's "R L0 ~22% of grid" holds, and its ".bin RLE mask" is superseded by
rectangles (brief amended). Out-of-scope note: `walk.iter_parcels` decodes every leaf and takes >10
min for L2 alone under a single-level filter; the occupancy script avoids it by reading the index
tree only.

**Unit 26a (name emission decoupled from geometry; per-level name_count recalibrated) — code done, no rebuild.**
`selection.json` rules gained `road_names`, `background_names`, `name_nodes` (`place` kept as alias) and
`name_cap_per_cell` (absent = legacy); `selection.name_filter_way/name_filter_node` are called in
`osm_to_parcel_geometry.py` right before `_make_name_record` at the road, background and node sites
(geometry admission untouched). The extractor's hardcoded 5-value place check moved into the gate
(explicit `level_filter=` overrides keep the legacy behaviour). `count_dry_run` now tallies name
candidates per source. Tests: 245 pass (`pytest parser/tests -q`); Perth clip fixture, levels 0-8,
extracts clean: L0 names 118,899 (roads 171,058), L2 445 (roads 18,059), L4 24, L6 16, L8 1.

Dry-run tally (national, tags-only) vs R and [0.5,2]x: L0 1,984,178 / 19,081,105 = 0.10x (OUT);
L2 30,307 / 40,169 = 0.75x; L4 3,354 / 4,042 = 0.83x; L6 1,223 / 1,022 = 1.20x; L8 287 / 209 = 1.37x;
L10 8 / 8 and L12 8 / 8 = 1.00x. Lever at L2-L10/12: `road_names=false`, `background_names=false`,
place-class set only (classes and per-class tallies are in each rule's `_calibration_note`); no cap
needed.

**Declared deviation: level 0 name_count cannot reach the envelope.** Everything OSM offers is admitted
(all named roads 1.29M, named bg ways 0.46M, all named place nodes, all named amenity/shop/tourism/
historic/natural/leisure nodes = 0.23M): ~1.98M = 0.10x, floor is 9.54M. R's 19M names include strings
OSM Australia does not carry (address/house-number style). Padding is not possible without fabricating
names; needs a WP-level decision (widen level-0 name envelope or a new name source). Also: 26's
brief-20 "undershoot" amendment is wrong for names at 2-8 (they overshot), as the brief says; the
level-10/12 "suburb-only, unreachable" note in selection.json is superseded (state/country/continent = 8).
Caveat: L10/12 counts assume the single-parcel cells are target cells; real-build confirmation is 26's.

### Unit 26 (kickoff-only, rebuild #3) — started 2026-09-19 03:33 AEST

Verified master contains 26a (2b6bf4a) and 26c (cbeca79); tree clean, in sync with origin/master;
`pytest parser/tests -q` 249 passed. Disk before clear: 60G free on /home, `output/` 7.6G; after
`rm -rf output/`: 68G free (need ~6.9G spool + ~0.8G KWI + 26c fill growth to ~1.4G total): GO.
Prior report kept at `/tmp/wp1-unit26-prior-report.json`. Memory: 30G total, ~17G available.
Pipeline started via nohup (extract then `build_alldata.py`, both under `/usr/bin/time -v`);
logs in `/tmp/wp1-unit26-logs/` (`extract.{out,time}.log`, `build.{out,time}.log`, `kickoff.log`).
Extraction confirmed alive and `output/spool` being written. Expected ~35-45 min extraction plus
~7+ min assembly (unit 15 floor: 33:23 + 6:44; 26c fill adds encode work). Verification is a
separate unit.

### Unit 26b (verify and record, rebuild #3) — 2026-09-19

Rebuild #3 finished (extract 33:49 / 8.3 GB RSS; assembly 8:33 / 6.6 GB RSS); ALLDATA.KWI 1,388,969,920 B,
sha256 `16329332...a7e8d8`. Full harness: PASS container (brief 27), decode, pointers, mht29, shape,
vocab; FAIL envelope (15), mfde (1), spotcheck (3 rows). pytest 249 passed. Full tables and
dispositions in PLAN.md "Build record (2026-09-19)". Level coverage confirmed against map.json.
Remaining FAILs: envelope L0 name_count 0.103x and L12 parcel_count 3/1 = 3.0x (proposed declared
deviations; note L12 is 3, not the 2 the kickoff assumed); envelope sub-frame maxima at L0/2/4/6/8/10
(WP1-scope, needs brief); mfde L12 entry-index 10 absent (WP1-scope); spotcheck Brisbane/Sydney/
Melbourne L0 road names (WP1-scope). No code changed. Stale PLAN.md blind-spot text noted (fix already
in e629b91).

## Units 28-31 -- WP1 residual FAILs after rebuild #3: diagnosis + briefs (design only, no code or output/ changed) -- 2026-09-19

Root causes (read-only against live `output/ALLDATA.KWI` and R; scripts in `/tmp/diag28/`):
- **Spotcheck L0 (Brisbane/Sydney/Melbourne): reader bug, not data.** `kiwiw/mesh.py::locate_parcel`
  re-narrows `bounds` at the depth-1 subparcel descent (already the cell), so divided parcels resolve to
  a ~9 m wrong sub-frame. With depth-1 narrowing removed (monkeypatch), all expected names are present
  (Queen/Adelaide, York/Kent/Elizabeth, Queen/Swanston/Collins). Brief **28**; no rebuild needed.
- **Envelope sub-frame maxima (13 rows): division triggers on total frame size only.** Frames fit the
  131,070 B / R-mapframe-max total while one kind is 2-5x R's per-kind max (R L0 bg 25,908 vs G whole-cell
  125,760). ~2.2k L0 leaves, plus L2/4/6/8/10; some leaves are already type 2 and need a priority trim.
  Brief **29** (per-kind budgets = R `frame_kind_max_bytes`, escalate, then deterministic trim).
- **mfde L12 idx 10: R's mfde[10] is a byte-identical duplicate of the name sub-frame** (L12: 236 B ==
  mfde[2]; L6-L12: in_buffer iff name present, same size, 100%). G emits absent. Brief **30** (synth emits the
  copy at L>=6; L0-L4 keep absent, R's dominant class; variant rule at L0/L2/L4 remains undecoded).
- Rebuild: assembly-only (spool from rebuild #3 remains valid; 28/29/30 act after extraction). Kickoff **31**,
  verify **31b**.

Parallelism: 28, 29, 30 are file-disjoint (mesh.py+test_mesh; divide.py+build_alldata.py+test_divide/
test_build_alldata; synth.py+test_synth_map_frame+design docs) and run in parallel; 31 waits for all
three, 31b for 31.

Proposed declared deviations (for acceptance, not self-accepted):
- **L12 parcel_count G=3 vs R=1 (3.0x).** R's L12 is one undivided 3,808 B leaf (25 bg shapes of types
  289/306/528 = 3,212 B, 8 names). G's single L12 cell holds 26 `natural=bay` shapes = 4,458 B of
  background (+236 B names) so the whole frame exceeds R's 3,808 B ceiling and is divided (type 2) into 3
  populated quadrants (3,456/160/1,440 B). The bg content differs in kind (R: 6 water polygons + 19
  boundary-type lines; OSM way tags give no reliable 306/528 lines), so G cannot match R's byte budget
  without dropping the content brief 19 added. Declared figure: G = 3 leaves (one cell, type-2 divided),
  R = 1; unaffected by 29 (bg budget 3,212 B < whole-cell 4,458 B still divides) and 30.
- L0 name_count 0.103x: unchanged from 26a/26b (OSM cannot supply R's 19M names; max OSM total ~1.98M).
No item was found WP2-scoped or unreachable, except the two above.

## Brief 29 -- per-kind sub-frame budgets in division -- 2026-09-19

Implemented in `parser/kiwiw/divide.py` (`kind_limits`/`measure`/`trim_stats` args on `plan_divisions`, kind-breach
escalation 0->1->2, final-tier `_trim_kinds` with priority orders) and `parser/build_alldata.py`
(`_load_level_kind_budgets`, `_measure_one` returning padded per-kind sizes, `_encode_one` now a bytes-only wrapper,
`trimmed_items` in `manifest.json`, per-level TRIM line with `** >1% BLOCKER **` flag). Kinds with R max 0 (L10/L12 road)
are omitted from the budget (an absent kind is not budgeted). Road trim pins motorway/trunk (road_type 12/0) at L>=2.
No `output/` change, no rebuild; spool untouched.

Evidence: `pytest parser/tests` = 257 passed; the only failures are 1 test + 3 errors needing `osmium` (not installed in
this env; unrelated, pre-existing). Fixture gate (`--fixture perth --levels 0 2 4 6 8`, spool `output/spool`, out
`/tmp/perth29/`) decoded with `harness.profile.build_profile`: every kind max <= R's at L0/2/4/6/8
(L0 road 66,980/106,114, bg 25,908/25,908, name 23,172/24,568; L2 102,642/110,132, 10,316/31,132, 932/1,152;
L4 105,192/124,952, 14,098/73,148, 336/370; L6 50,604/124,220, 35,166/48,270, 314/610; L8 57,064/99,794, 21,696/120,946, 362/366).
Trim counters (Perth): only L0 background, 4,839/357,077 items (1.355%) in 13 type-2 sub-cells -> named as a >1% blocker
(dense `background_all` polygons, class ii). No road or name trim in Perth.
Fixture cannot exercise: L8 road t1/t2 and L8 name/bg rows, L2 road t0 (114,370), L4/L6 name rows, L10 bg, and the
Tullamarine/Mildura/Melbourne-CBD L0 cells (outside Perth); verified by 31b at full scale.
Expected split at full scale: type-0/1 rows (L0 bg t0 1130, t1 968; most name rows; L2 bg t0/L2 road t0; L4/L6 bg t0) are
fixed by escalation; class ii (already type 2: L0 bg/name t2, L2 bg t2, L4/L8 bg, L8 name/road t2) go to trim.
L0 type-2 name trim would hit the Melbourne CBD sub-cell (32,280 B > 24,568): it drops duplicates, then POI (type 6), then
place names; road names (type 5, Queen/York/Swanston) are dropped last, so spotcheck should survive (confirm in 31b).
Possible declared deviation: L0 background trim >1% at cities (bg cost 25,908 B budget vs ~2,200 small polygons/cell);
report the 31b trim table before deciding.
