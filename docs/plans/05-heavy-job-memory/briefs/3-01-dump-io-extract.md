# Brief: 3-01 — Extract dump_io; 3-07 + triage use the proven storage boundary

Consumer: Flash executor (opencode / deepseek-flash). You have only this brief and the repo. If `/proc` or `systemd-run` is sandboxed, finish implementation + small tests, leave heavy RSS unrun, and report `done with concerns` — the orchestrator measures outside the sandbox under `flock output/.heavy.lock`.
Owned paths: `parser/kiwiw/dump_io.py` (new), `parser/tools/dump_join.py` (refactor residual onto dump_io; add 3-07 adapter), `parser/tools/k1_triage.py` (summary/classify/enumerate readers + classify assign writer onto dump_io; keep rule/aggregation logic), `parser/tools/bench_dump_memory.py` (extend with Phase-3 3-07 and triage modes; keep Phase-1 residual and Phase-2 finalize working), `parser/tests/test_dump_join_memory.py` (Phase-1 still green + 3-07 equivalence cases), `parser/tests/test_k1_triage.py` (window-split / key-ownership cases as needed), `parser/tests/fixtures/extend_3_07_baseline/` (new; vendored frozen 3-07 baseline), `parser/perf_inventory.json` (register `dump_io.py` only; do not change existing entries' class), `docs/provenance.md` (append Phase-3 scratch entries only), `output/scratch-3-07/extend_dump_attempt3.py` (thin wrapper calling the tracked adapter; keep defaults), `output/scratch-5-03/` (git-ignored scratch). Touch nothing else.
Commits: Leave changes in the working tree. Do not commit; the orchestrator commits.
Depends on: Phase 1 (dump_join + residual harness) and Phase 2 (finalize mode in bench; do not regress).
Runs alongside: nothing owned by this unit. Host may have a separate plan04 3-14 Sol seat — share `output/.heavy.lock` (serial); do not touch `_cenc.c`, `cenc.py` C paths, or 3-14 briefs.
Budget: 14 files to read, about 900 lines to change, 120 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/05-heavy-job-memory/IMPLEMENTATION.md` (done, not done, what you learned) and report `over budget`.

## Required reading, in order

1. `docs/plans/05-heavy-job-memory/DESIGN.md` — binding: Contract (3-07) lines 37–38, Domain Bounded dump I/O lines 41–62 (windows, validation, write-behind, layouts, memory scaling / triage cardinalities), Contract (measurement) 72–78, Assumptions 1–3, 7–8, Phase 3 lines 239–252. Read by those ranges only.
2. `parser/tools/dump_join.py` — proven I/O helpers to extract (`_sync_file_range`, `_drop`, `_pread_full`, `_pwrite_full`, window write-behind loop in `_extend_kind` / `_verify_kind`). Keep residual semantics unchanged.
3. `output/scratch-3-07/extend_dump_attempt3.py` (whole, 41 lines) — baseline 3-07 behaviour.
4. `parser/tools/k1_triage.py` — `_memmap`, `CHUNK`, `cmd_summary` / `cmd_classify` / `cmd_enumerate` chunk loops, `_merge_group` / `_merge_rows` / `_merge_one` (key ownership).
5. `parser/tools/bench_dump_memory.py` — reuse `run_scoped` / controller patterns; do not rewrite Phase 1 or Phase 2.
6. `parser/tests/test_dump_join_memory.py`, `parser/tests/test_k1_triage.py`, `parser/perf_inventory.json` (class rule for a new kiwiw module — match an existing offline / orchestration entry such as `spool.py` or `dump_join.py`).

Read ranges and grep; do not re-read whole large files; truncate long tool output.

## Goal

Extract the proven bounded dump I/O boundary into `parser/kiwiw/dump_io.py`, adapt the 3-07 extension and triage `summary`/`classify`/`enumerate` to use it, keep transformation-specific sorts/casts/padding/aggregation and C-output ownership copies untouched, and prove byte/artifact identity plus ≤50% max RSS and `memory.peak` on 1M-row fixtures (with growth gates). Phase 1 residual gates must still pass after extraction.

## Contract

Settled; cited from DESIGN.md. Do not re-decide.

- Shared I/O, DESIGN "Domain: Bounded dump I/O":
  - At most one bounded source, destination and assignment window at a time; release every derived view before closing/reusing a window; default window **65,536** rows; changing window leaves bytes and aggregates identical.
  - Validate row size, field offsets, complete-row file length (and assignment length where applicable) before writing; handle partial final windows; reject zero-length mapped kinds (Assumption 7) without inventing empty successes.
  - Write-behind: `sync_file_range` + `posix_fadvise(DONTNEED)` (or equivalent) on completed destination windows; drop consumed source windows from cache. Final fsync/close unchanged.
  - Helper owns I/O only — no C layout declarations, no per-row Python kernels. Existing NumPy bulk ops stay bulk.
  - Triage persistent state: retained aggregation keys must **not** keep chunk or unique-array backing alive through structured scalars; copy keys into independent storage (e.g. `np.array(ukey[i])` / frombuffer copy). Hold cardinalities fixed in row-scaling tests; report them separately. Preserve first-matching-rule classification, exact counts, sentinel/NaN normalization, grouping across window boundaries, deterministic summary/enumeration ordering.
- 3-07 contract, DESIGN line 37: keep **stable** side sort (`argsort(..., kind='stable')`), leftmost exact match, same key cast (`sk[f]=side[f]`), boundary-only scope `(level==0)&(code==291)&(src_ix==-2147483648)`. Rebuild each 152-byte output row by zeroing the row and copying named fields, then set byte144 / `s02_producer_verified`. Old unnamed padding is **not** a raw-copy contract. Preserve the aggregate match assertion (`matches == int(side['rows'][side['status']==1].sum())`).
- Phase 3 outcome, DESIGN 241–248:
  - 3-07 entry point and triage summary/classify/enumerate: bytes and artifacts identical to baseline on bounded supported fixtures across window splits; zero-length mapped kinds prove rejection separately.
  - 3-07 fixture covers 144→152 padding, scope, narrowing cast. Triage: groups straddling windows + first-match rule precedence preserved.
  - 3-07 adapter and **each** triage command ≤ 50% baseline max RSS and `memory.peak` on their own 1,000,013-row fixed-cardinality fixture.
  - Doubling rows (retained key/pair populations fixed) adds at most one source+destination window for that layout: **18,944 KiB** for 144→152 (`2×65536×(144+152)/1024`) and **9,728 KiB** for read-only 152-byte triage (`65536×152/1024`).
  - Additional bounded high-cardinality triage fixtures (late first appearances, groups spanning windows): identical artifacts; candidate peaks ≤ paired baselines.
  - Phase 1 byte and memory gates still pass after extraction.
- Non-goals: `prepare_dump.py`, `finalise_rules_side.py` unchanged; no C-output ownership-copy removal; no Phase 4 docs; no unit 3-14; no inventing product next-steps.

## Changes

Decisions you should not have to re-derive.

1. **`parser/kiwiw/dump_io.py` (new)** — extract from Phase-1 `dump_join` the reusable boundary:
   - `DEFAULT_WINDOW = 65536`
   - `sync_file_range` / `drop` / `pread_full` / `pwrite_full` (same behaviour as today, including ctypes fallback for `sync_file_range`)
   - `file_rows(path, row_size) -> int` validating `size % row_size == 0` and rejecting `rows == 0` with a clear error
   - Read iterator / context: open read-only, yield `(lo, n, ndarray_view_or_copy over reusable buffer)` for windows; drop each consumed source window; release views before next window
   - Write path: open `O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW` (or known-length assign writer — see below), `pwrite` windows, write-behind previous window, final fsync
   - For **classify assign** (`u16` length known up front): create/truncate to exact byte length (or `ftruncate`), then windowed `pwrite` with write-behind (no whole-file `np.memmap(..., mode='w+')`)
   - Public API should be importable as `from kiwiw import dump_io` / `from kiwiw.dump_io import ...`. Keep helpers small and documented.

2. **Refactor `dump_join.extend_residual`** onto `dump_io` without changing residual bytes, counts, CLI, or verify behaviour. Phase-1 tests must stay green. Do not silently change the non-stable residual `argsort`.

3. **3-07 adapter** in `dump_join.py` (e.g. `extend_s02_producer` + CLI flag/subcommand — pick one clear entry; residual CLI defaults must keep working):
   - Vendor baseline first into `parser/tests/fixtures/extend_3_07_baseline/`: copy `extend_dump_attempt3.py` verbatim + minimal replay shims; record SHA256SUMS. Compute source hash before editing; stop if live scratch file is missing.
   - Candidate: windowed read of **144-byte** source rows; windowed write of **152-byte** dest rows (zero row, copy named fields from 144-byte dtype, set flag at offset 144); side index with **stable** sort; scope mask as baseline; aggregate assert preserved; manifest `extension` dict and field append match baseline including path strings as produced under the isolated replay root.
   - Isolated replay root under `output/scratch-5-03/` mirroring hard-coded `output/scratch-3-07/` and `output/scratch-3-03/dump/` relatives; refuse if resolved paths escape into real repo `output/` outside `scratch-5-03` (same pattern as Phase 1 `check_isolated`).
   - Switch `output/scratch-3-07/extend_dump_attempt3.py` to a thin wrapper that calls the tracked adapter with the same defaults (do **not** force-add generated dumps).

4. **`k1_triage.py`**: replace whole-file `_memmap` chunk slices with `dump_io` windowed reads. Default window = `dump_io.DEFAULT_WINDOW` (65536). Keep `CHUNK` as an alias of that default or remove it — do not leave a 2M whole-file mapping. Fix retained-key ownership in `_merge_group` / `_merge_rows` / `_merge_one`: store an independent copy of each new key (`np.array(ukey[i])` or equivalent), never a void scalar into the unique array. Classify: windowed assign writes with write-behind. Preserve output TSV/partition byte identity vs current behaviour on fixtures (including groups that straddle windows and first-match rule precedence). Reject zero-row kinds consistently with dump_io validation where DESIGN requires rejection.

5. **Tests (small, no heavy lock)**:
   - Phase 1: `pytest parser/tests/test_dump_join_memory.py parser/tests/test_perf_inventory.py` still pass.
   - 3-07: equivalence vs vendored baseline on bounded fixture covering status 0/1, misses, scope-only flag writes, narrowing cast, stable duplicate order, nonzero padding/NaNs, window sizes 1 / 65536 / non-divisor; empty-kind rejection separate.
   - Triage: existing `test_k1_triage.py` pass; add cases for window-straddling groups and independent key ownership (candidate artifacts identical across window sizes; retained dict values do not reference window buffers).
   - Existing `test_k1_dump.py` / quantisation dump tests remain green if you touch shared imports carefully (you should not need to edit them).

6. **Measurement harness** — extend `bench_dump_memory.py` with Phase-3 modes (clear CLI, e.g. `s07-run` and `triage-run`); keep residual default and `finalize-run` working:
   - Scratch: `output/scratch-5-03/`; `TMPDIR=output/scratch-5-03/tmp`.
   - 3-07: 1,000,013-row 144-byte source fixture + side table with fixed row weights; grow with zero-flag rows so side weights stay valid; 2,000,013-row growth run. Three paired baseline(vendored)/candidate runs. Gates: every pair cand ≤0.5× base on max RSS **and** `memory.peak`; growth ≤18,944 KiB on both; median wall ≤2×; output SHA256 equal.
   - Triage: separate 1,000,013-row 152-byte fixed-cardinality fixture for **each** of summary / classify / enumerate (enumerate may reuse classify assign prepared by the controller, but measure each command’s worker alone). Growth ≤9,728 KiB. Same 50% RSS/`memory.peak` gates vs a whole-file-memmap baseline worker (vendored frozen memmap reader under fixtures preferred). High-cardinality bounded fixture: identical artifacts; cand peak ≤ base peak.
   - Fresh scoped workers (`systemd-run --user --scope -p MemoryAccounting=yes` + `/usr/bin/time -v`), same cgroup trailer pattern as Phase 1. Never `drop_caches`. Controllers generate/fsync/pre-read fixtures; workers do not inherit materialised arrays.
   - If sandbox blocks measurement: implement + small tests; skip heavy run; report clearly.

7. **Inventory / provenance**: register `parser/kiwiw/dump_io.py` as `orchestration` (offline I/O helper; windowed pread/pwrite; no per-row Python loop). Append short `docs/provenance.md` entries for `output/scratch-5-03/` only.

Operational constraints, all binding:

- Temp files only under `output/scratch-5-03/` (and existing 5-01/5-02 if re-checking Phase 1). Set `TMPDIR` accordingly.
- Every heavy run under `flock output/.heavy.lock` for the whole process tree. If `flock -n` fails, **wait** — do not stack beside Sol 3-14 or other heavy jobs. Small tests outside the lock.
- cbuild ≤ -j4; K1 ≤ -j6; **no K1 run**, no cbuild, no cache drops, no subagents, no Cursor CloudAgent.
- Do not revert `aa7e840` / `a9432c1` / Phase 2 commits. Leave uncommitted `causes_residual.md` dirt alone. Do not start Phase 4 or unit 3-14. Do not touch `_cenc.c`.
- Background long jobs with EXIT markers under `output/scratch-5-03/`; poll `test -f` + sleep. Never `pgrep -f` loops.
- Host swap is often full — keep fixtures to one kind × ~1M rows per measured worker; serialise aggressively.

### Keep untouched

- `parser/kiwiw/_cenc.c`, `parser/kiwiw/cenc.py` ownership copies, plan04 3-14 surfaces, `prepare_dump.py`, `finalise_rules_side.py`, Phase 4 docs, unrelated dirty working-tree files.

## Done evidence

Identify or write the failing check before changing code. Initial failing check: `parser/kiwiw/dump_io.py` does not exist / Phase-3 tests absent.

- `python -m pytest parser/tests/test_dump_join_memory.py parser/tests/test_k1_triage.py parser/tests/test_perf_inventory.py -q` → all pass (including new 3-07 / window-split / key-ownership cases).
- Vendored 3-07 baseline `sha256sum -c SHA256SUMS` OK.
- `flock output/.heavy.lock python parser/tools/bench_dump_memory.py s07-run --out output/scratch-5-03/s07_results.json` → exit 0, gates hold.
- `flock output/.heavy.lock python parser/tools/bench_dump_memory.py triage-run --out output/scratch-5-03/triage_results.json` → exit 0, gates hold for summary, classify, enumerate.
- Phase-1 residual re-check still passes (or cite prior results.json if re-run is blocked only by lock contention — prefer a quick re-run of residual controller when lock is free).
- `git status --short` shows only owned paths; no 3-14 / `_cenc.c` / `causes_residual.md` mixed in.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed; check output before/after; deviations; measured tables (per pair RSS/`memory.peak`/wall for 3-07 and each triage command; growth; SHA equality). Name contradictions rather than resolving them silently. Do not spawn agents beyond read-only research helpers.
