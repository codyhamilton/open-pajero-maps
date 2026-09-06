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
