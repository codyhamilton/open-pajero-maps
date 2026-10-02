# Brief: 1-01 — Residual extension with bounded windowed I/O

Consumer: Flash executor (opencode). You have only this brief and the repo.
Owned paths: `parser/tools/dump_join.py` (new), `parser/tools/bench_dump_memory.py` (new), `parser/tests/test_dump_join_memory.py` (new), `parser/tests/fixtures/dump_join_baseline/` (new, vendored baseline), `parser/perf_inventory.json` (entries for the new modules only), `docs/provenance.md` (append entries only), `output/scratch-5-01/` (git-ignored scratch). Touch nothing else. In particular do not modify any file under `output/scratch-3-12/`; the candidate lives in `parser/tools/dump_join.py`, and switching the ignored scratch entry point over is left to the orchestrator after plan04 3-13 exits.
Commits: Leave changes in the working tree. Do not commit; the orchestrator commits.
Depends on: nothing.
Runs alongside: nothing. Single unit, no parallelism.
Budget: 12 files to read, about 700 lines to change, 120 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/05-heavy-job-memory/IMPLEMENTATION.md` (done, not done, what you learned) and report `over budget`.

## Required reading, in order

1. `docs/plans/05-heavy-job-memory/DESIGN.md` — binding: "Domain: Dump transformation and ownership" (Contract (residual)), "Domain: Bounded dump I/O" (windows, validation before writing, write-behind, layouts, memory scaling), "Domain: Evidence and heavy-job operation" (measurement, frozen baseline, verification, operation), Assumptions 2, 4, 5, 6, 7, 8, 10, and "Phase 1". Read by line range (lines 27-91, 104-191, 210-222).
2. `output/scratch-3-12/extend.py` (32 lines) — the baseline you are replacing. Read it whole.
3. `output/scratch-3-12/study.py` lines 1-12 — `ROOT`, `DUMP`, `MAN`, `DT`, `dump`, and the `GROUP` import.
4. `output/scratch-3-07/witness.py` lines 1-20 — `GROUP` at line 17; do not read the rest (it pulls in `kiwiw` and spool code).
5. `parser/perf_inventory.json` and `parser/tests/test_perf_inventory.py` — the inventory class rule and gate for new modules.
6. `parser/kiwiw/spool.py` lines 430-445 — existing `pread` precedent.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make the residual byte146 extension stream bounded source, destination and assignment windows with write-behind, so peak RSS and cgroup `memory.peak` fall to at most half the frozen baseline's, with output bytes, manifest and joined counts identical to the baseline.

## Contract

Settled; cited from DESIGN.md. Do not re-decide.

- Residual contract, DESIGN "Contract (residual)":
  - Key: "exactly `GROUP = (level, ix, iy, code, p0, p1, p2, p3, p4, p5, p6, shape)`, typed as the dump's fields. Side key columns are converted with the same NumPy field-assignment cast as the baseline (`sk[f]=side[f]`, `i32`→`u8`/`u16` wraps). Out-of-range side values therefore collide exactly as they do today."
  - Flag: "byte146 is 1 iff the first matching sorted side record has `status == 1`, and 0 otherwise. Missing or empty side tables produce 0. Byte146 is always written from the flag and never copied from the source."
  - Sort: "preserve the original default (non-stable) NumPy structured `argsort` call on the same key array, and do not silently substitute a stable sort."
  - Accounting: "assignments equal to 65535 select accounting rows only, not which rows get the flag."
  - Preserved: source order, bytes `[0,146)` and `[147,152)`, NaN payloads, padding, manifest metadata (including the `extension_3_12` path strings) and joined counts equal the baseline's output.
  - Files: "input files are read-only. Writable destinations are private regular files written from the source windows, with no whole-file copy-then-patch."
- Windows, DESIGN "Contract: windows" and "validation before writing": at most one bounded source, destination and assignment window at a time; release every derived view before closing or reusing a window; default window 65,536 rows; validate row size, field offsets, complete-row file length and assignment length before writing anything; handle partial final windows; zero-length mapped kinds are rejected (Assumption 7), not turned into empty successful outputs.
- Write-behind, DESIGN "Contract: write-behind": start writeback on each completed window and drop written-back windows from the page cache (`sync_file_range` plus `posix_fadvise(DONTNEED)`, or equivalent). Output bytes and final durability (flush/close/fsync) are unchanged.
- Verification, DESIGN "Contract (verification)": production paths run no full-chunk byte assertions, sampled or otherwise. An opt-in `verify` mode streams source and destination in the same bounded windows and checks every byte outside byte146, under the same memory gates.
- Layout: the 152-byte residual layout is derived from the manifest (`DT = np.dtype(..., align=True)` over `MAN['fields']`) and validated; byte146 must be the padding byte of that layout. Reject incompatible layouts before writing. New code is I/O plus the existing NumPy bulk operations; no per-row Python loop, no C declarations.
- Phase 1 outcome, DESIGN "Phase 1": "Running the residual extension entry point with its defaults, in an isolated fixture root, produces dump bytes, manifest and joined counts identical to the vendored baseline. On the bounded 1,000,013-row fixture, its max RSS and scope `memory.peak` are each at most half the baseline's, and the doubled-row run meets Assumption 2's growth bound on both metrics. Median wall time is within 2x of the baseline's." Growth bound (Assumption 2): the 2,000,013-row run (same side tables and groups) adds at most `2 x 65,536 x 152 = 19,922,944` bytes = 19,456 KiB on either metric over the 1,000,013-row candidate run.
- Cases required (DESIGN Phase 1): status 0/1; exact misses; missing and empty side tables; duplicate keys with conflicting statuses; side keys that collide only after the narrowing cast; assignment 65535 and non-residual rows; nonzero padding and NaN payloads; final partial windows. Empty mapped kinds prove rejection by both baseline and candidate separately. Window sizes 1, 65,536, and one that does not divide the row count give identical bytes.

## Changes

Decisions you should not have to re-derive.

1. Vendor the baseline first, before writing candidate code. Copy verbatim into `parser/tests/fixtures/dump_join_baseline/`: `extend.py`, `study.py`, and `witness.py` (from `output/scratch-3-07/`). Record SHA256 in a tracked `SHA256SUMS` in that directory. Expected source hashes, verify they match before copying and stop if not:
   - `1b13b844fbd3a632010ab522c4cc20e3165b7f95eabbde32f84c4b2747571b0b`  `output/scratch-3-12/extend.py`
   - `f9ae57761a2a1651831924996fe971319dcf2b4eea8856cc878bd1d91c0ed45e`  `output/scratch-3-12/study.py`
   - `42d33e399237671a031e01f83645a9d2f3dae436244f6d14efe2e69020f6e8f9`  `output/scratch-3-07/witness.py`
   The vendored `witness.py` imports `kiwiw` through a repo-relative path and is not importable from an isolated root. For replay, the harness materialises a shim `witness.py` in the replay root containing only the `GROUP = (...)` line copied programmatically from the vendored witness (assert the extracted tuple equals the contract's `GROUP`). The vendored `extend.py` and `study.py` are not edited; if you need a shim, the shim is generated in the replay root, never in the fixtures directory.
2. Isolated replay root: a working directory under `output/scratch-5-01/replay-<run>/` that reproduces the relative paths the baseline hard-codes: `output/scratch-3-11/dump_new_ext/` (manifest + kind files), `output/scratch-3-11/classify_new/assign_<kind>.u16`, `output/scratch-3-12/side_<kind>.npy`, and `output/scratch-3-07/witness.py` (the shim). The baseline runs as a subprocess with `cwd` set to that root and `PYTHONPATH` pointing only at it. Before launching, the harness resolves every path it will pass or the script will hard-code and refuses to start (non-zero exit, no side effects) if any resolves, after `realpath`, under the real repository `output/` outside `output/scratch-5-01/`, or if a replay-root path is a symlink into it. Test this refusal. Never touch real `output/scratch-3-12/dump_ext`, `output/scratch-3-12/joined_counts.json`, the `output/scratch-3-11` oracle, `output/scratch-2-07`, `output/scratch-3-06`. Fixture inputs are generated, not copied from real dumps.
3. Candidate module `parser/tools/dump_join.py`: public function for the residual extension with parameters for source dump dir, side-table dir, assignment dir, destination dir, counts path and `window_rows=65536`, plus a CLI `main()` whose defaults equal the baseline's relative paths and outputs (`dump_ext` under the 3-12 root, `joined_counts.json`, `dump_manifest.json` with the `extension_3_12` dict and `residual_crossing_verified` field exactly as the baseline builds them, including the `str(DUMP)` and `str(ROOT/'side_<kind>.npy')` path strings relative as in baseline), and a `--verify` flag (opt-in, default off).
4. Narrowing-cast contract: build side keys exactly as the baseline: `kd=np.dtype([(k,DT[k]) for k in GROUP])`, `sk=np.empty(len(side),kd)`, `for f in GROUP: sk[f]=side[f]`; then `order=np.argsort(sk)` (default kind, no `kind=` argument), `sk=sk[order]`, `sf=(side['status'][order]==1).astype('u1')`. Per window build keys by `keys[f]=window[f]` and use `np.searchsorted(sk,keys)`, clamped index, equality compare, leftmost-first semantics as in the baseline. Do not dedupe, widen, range-check or stable-sort.
5. Collide-after-wrap test (required, named `test_collide_after_wrap`): a side table where one `i32` side key value (e.g. 256 or 65536+k in a `u8`/`u16` field) wraps to equal a dump key that the unwrapped value would miss, plus a duplicate-key pair with conflicting statuses whose winner depends on the non-stable sort. Candidate bytes and counts must equal baseline replay bytes and counts. Use the same `argsort` call on the same key array so tie order matches; if a tie order cannot be made to match, report it, do not switch to a stable sort.
6. byte146 comes from the flag: for every row written, byte146 is the flag (0 if side is None or empty), never copied from the source. A source fixture row with nonzero byte146 must come out as the flag.
7. Streaming window write, instead of `shutil.copyfile`: for each kind, open the source read-only and the destination `O_WRONLY|O_CREAT|O_TRUNC` private regular file; per window `pread` the source rows (or a per-window read-only mapping that is closed with all views released), build the destination window as a bytes/ndarray copy with byte146 set to the flag, `pwrite` it, and per completed window call `os.sync_file_range(fd, off, n, SYNC_FILE_RANGE_WRITE)` (via `ctypes` if `os.sync_file_range` is unavailable) for the previous window, then `os.posix_fadvise(fd, off, n, POSIX_FADV_DONTNEED)` for windows already written back, and `POSIX_FADV_DONTNEED` on source windows already consumed. Final `os.fsync` and close preserve durability. Assignment u16 values are read per window with the same bounded approach. The destination file length must equal the source's before and after.
8. Counts: keep the baseline's `collections.Counter` accounting per window using bulk NumPy (`np.unique` over the residual mask's `(level, code)` pairs; no per-row Python loop), producing identical `joined_counts.json` bytes (`json.dumps({'strata':counts,'moved_spool':total},indent=2)+'\n'`), identical `EXTENDED`/`MOVED` stdout lines.
9. No production byte assertions. Replace baseline's `np.array_equal` asserts with nothing in the main path; the `--verify` mode streams the source and the written destination in the same windows and checks every byte outside offset 146 (and that byte146 equals the recomputed flag), failing with a non-zero exit and index of the first mismatching window. Verify mode runs under the same memory gates (measure it).
10. Row-count, layout and length validation before any write: `src_size % row_size == 0`, row_size == `DT.itemsize == 152`, byte146 not inside any named field, assignment length `== rows`, rows `> 0` else raise and write nothing (matching the baseline's `np.memmap` rejection; test baseline and candidate reject empty kinds separately and neither leaves outputs).
11. Fixture generator (in `bench_dump_memory.py` or a helper imported by it and the tests): deterministic seeded generator (record seed) producing a manifest with the 152-byte aligned layout, kind files, assignment `.u16` files, and side tables (`.npy`, `i32` keyed, 78-byte rows, 216,488 rows for the memory fixture, fixed accounting strata). Memory fixture: 1,000,013 rows (and a 2,000,013-row variant with the same side tables and groups). Small correctness fixtures: a few thousand rows covering all required cases, in the tests, runnable without any heavy job.
12. Measurement harness `parser/tools/bench_dump_memory.py` (controller process separate from fixture generation, hashing, and worker): each worker is a fresh process launched as `systemd-run --user --scope -p MemoryAccounting=yes -- /usr/bin/time -v -o <marker-dir>/time.txt <python> ...` with a unit name you choose; the controller reads the scope's cgroup v2 `memory.peak` (and `memory.stat` `anon`, `file`, `file_dirty`, `file_writeback`, and `memory.pressure` totals) before the scope is torn down (the scope exits when the worker does, so have the worker wrapper read its own cgroup files from `/proc/self/cgroup` just before exit and write them to a JSON file; keep this reader outside the measured allocation by running it after the transformation and in a tiny trailer, and say in the report if this is imprecise), and max RSS from `/usr/bin/time -v` (KiB). Fixtures are generated, fsynced, and pre-read by the controller before each paired run (`posix_fadvise` on fixture files is allowed; never `drop_caches`); the worker must not inherit a materialised fixture. Run three paired runs (baseline then candidate, alternating) on the 1,000,013-row fixture and one run at 2,000,013 rows for the candidate; record every peak, wall time, median wall times, row and window counts, side and group cardinalities, baseline source SHA, fixture seed, input hashes, Python and NumPy versions and output SHA256s into a JSON results file under `output/scratch-5-01/`. Gates (exit non-zero if any fails): every pair candidate max RSS <= 0.5 x baseline and candidate `memory.peak` <= 0.5 x baseline; doubled-row candidate adds <= 19,456 KiB over the 1,000,013-row candidate on both metrics; candidate median wall <= 2 x baseline median wall; every output SHA256 (dump bins, manifest, counts) candidate == baseline. Per Assumption 8, if the `memory.peak` spread between pairs exceeds 10% of baseline, report the spread; do not silently change the gate.
13. Supplementary hash (Assumption 10, evidence only, not a gate): you may record, once, under the heavy lock, the SHA256 of the existing `output/scratch-3-12/dump_ext/*.bin` read-only into `output/scratch-5-01/dump_ext.sha256`. Reading only; never write to or run anything against `dump_ext`.
14. Inventory: register `parser/tools/dump_join.py` and `parser/tools/bench_dump_memory.py` in `parser/perf_inventory.json` under the existing class rule (match how an existing offline-tool module is classified), and keep `parser/tests/test_perf_inventory.py` passing.
15. Provenance: any new git-ignored large output you leave behind (`output/scratch-5-01/` fixtures, results JSON, `dump_ext.sha256`) gets an entry appended to `docs/provenance.md` stating what it is, which command regenerates it, and that it is git-ignored under `output/`. Keep entries short.

Operational constraints, all binding:

- Temp files stay inside the repo: use `output/scratch-5-01/` (git-ignored via `output/`). Never use `/tmp` or `$TMPDIR` defaults; set `TMPDIR=output/scratch-5-01/tmp` for every subprocess and create it.
- Every heavy run (fixture generation at 1M+ rows, baseline and candidate workers, measurement harness, hashing of big files, verify at scale) runs only under `flock output/.heavy.lock <command>` held for the entire process tree, one at a time. No K1 run, no cbuild. If `flock -n output/.heavy.lock true` fails, another job is active: wait for it, do not stack. Small correctness tests (few thousand rows) are not heavy and run outside the lock.
- Plan04 worker 3-13 reads `output/scratch-3-12`. Do not modify or delete anything there; read-only if you must read.
- Launch long jobs in the background writing a file EXIT marker (`<cmd>; echo $? > output/scratch-5-01/<name>.EXIT`) and wait by polling that marker file with `test -f` and a bounded sleep loop. Never use `pgrep -f` or `ps | grep` loops to detect completion.
- Do not spawn subagents.
- Do not use `drop_caches`.

### Keep untouched

- Everything under `output/scratch-3-12/`, `output/scratch-3-11/`, `output/scratch-3-07/`, `output/scratch-2-07/`, `output/scratch-3-06/`.
- `parser/tools/k1_triage.py`, `parser/tools/quantisation_roundtrip.py`, `parser/kiwiw/*` (Phase 3 owns `dump_io.py`; do not create it here).
- Existing entries in `parser/perf_inventory.json` and `docs/provenance.md`.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after. The initial failing check is `pytest parser/tests/test_dump_join_memory.py` (no such file or module yet: fails at collection).

- `python -m pytest parser/tests/test_dump_join_memory.py parser/tests/test_perf_inventory.py -q` → all pass, including `test_collide_after_wrap`, the empty-kind rejection (baseline and candidate), window sizes 1, 65536 and a non-dividing size producing identical SHA256s, the replay-root refusal test, and the all-cases equivalence against the vendored baseline replay.
- `cd parser/tests/fixtures/dump_join_baseline && sha256sum -c SHA256SUMS` → OK for all three vendored files.
- `flock output/.heavy.lock python parser/tools/bench_dump_memory.py --out output/scratch-5-01/results.json` (in background with an EXIT marker) → exit 0, and `results.json` shows for every one of the three pairs candidate max RSS <= 50% of baseline and candidate `memory.peak` <= 50% of baseline, all output SHA256 equal, doubled-row candidate within +19,456 KiB on both metrics, median wall ratio <= 2.
- `python parser/tools/dump_join.py --help` and a `--verify` run on the small fixture exit 0; a deliberately corrupted destination byte makes `--verify` exit non-zero.
- `git status --short` shows only owned paths changed; `git status --short output/scratch-3-12` shows nothing; `git check-ignore output/scratch-5-01` is ignored.
- While a harness run holds the lock, `flock -n output/.heavy.lock true` fails (exit 1); it succeeds after the EXIT marker appears.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. Give the measured numbers in a short table: per pair baseline vs candidate max RSS (KiB), `memory.peak` (bytes), wall time; the doubled-row growth in KiB for both metrics; the median wall ratio; output SHA256 equality. Say which large git-ignored outputs you recorded in `docs/provenance.md`.

Known tension to report rather than resolve: DESIGN says "the scratch entry points use them" (Assumption 6), but this brief forbids editing `output/scratch-3-12/` while 3-13 reads it. The candidate CLI defaults mirror `extend.py`; the scratch switch-over is the orchestrator's later step.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
