# Brief: 4-01 — Heavy-job memory commands and architecture docs

Consumer: Maps Execute (this unit is docs-only; Flash optional). You have only this brief and the repo.
Owned paths: `docs/WORKFLOW.md` (add heavy-job operation section), `docs/ARCHITECTURE.md` (add bounded dump I/O / memory-accounting / oomd section), `docs/plans/05-heavy-job-memory/IMPLEMENTATION.md` (Phase 4 close record only), `docs/provenance.md` (append only if a new scratch/evidence path appears — prefer pointing at existing scratch-5-0{1,2,3} entries). Harness (`parser/tools/bench_dump_memory.py`) only if a documented command string is wrong or a one-line help/default fix is required for ergonomics. Touch nothing else. Do **not** start unit 3-14, do **not** edit C/kernel surfaces, do **not** run plan close-out / `:done` trailer.
Commits: Author this brief first (orchestrator). Leave doc edits in the tree for the same worker to commit with `Workflow-Phase: 05-heavy-job-memory:4`.
Depends on: Phases 1–3 closed on master (`f3def00`+).
Runs alongside: plan04 3-14 may hold `output/.heavy.lock` via the 3-14 worktree symlink. Share the lock serially; never stack. Disk ~96% — keep verification light; delete fixtures after any re-run.
Budget: 8 files to read, about 250 lines to change, 60 tool turns. Past budget: handoff in IMPLEMENTATION.md and report `over budget`.

## Required reading, in order

1. `docs/plans/05-heavy-job-memory/DESIGN.md` Phase 4 (lines 254–266) and Domain: Evidence and heavy-job operation (lines 69–91); Architectural Implications lines 93–96.
2. `docs/plans/05-heavy-job-memory/IMPLEMENTATION.md` — measured Phase 1–3 peaks, carried limitations.
3. Existing `docs/WORKFLOW.md`, `docs/ARCHITECTURE.md`, and the three `output/scratch-5-0{1,2,3}` blocks in `docs/provenance.md`.
4. `parser/tools/bench_dump_memory.py --help` and subcommands `finalize-run`, `s07-run`, `triage-run` (residual default controller when no subcommand).

## Goal

Publish stable, serial heavy-job guidance so following the docs reproduces the Phase 1–3 memory and byte-equivalence gates, and so operators understand RSS vs `memory.peak`, the lock, and the deferred finalizer limit.

## Contract (DESIGN Phase 4 outcome — do not re-decide)

- One repo-root lock path: `output/.heavy.lock` (from repository root).
- Recommended (not mandatory) per-job transient scope: `systemd-run --user --scope -p MemoryAccounting=yes` (optional `MemoryHigh=` documented; no machine-wide cap).
- One-worker bounded benchmark / replay commands for residual, finalize, 3-07 (`s07-run`), and triage (`triage-run`), each under `flock output/.heavy.lock`.
- How to interpret KiB max RSS (`/usr/bin/time -v` / `getrusage`) vs cgroup v2 `memory.peak` (anon + page cache charged to the job, including dirty output).
- Record fixture/hash provenance (point at tracked `parser/tests/fixtures/{dump_join,finalize_dump,extend_3_07,k1_triage}_baseline/` SHA256SUMS and provenance scratch entries) and the measured Phase 1–3 peaks / limitations from IMPLEMENTATION.md.
- Following the documented commands reproduces their gates (exit 0).
- While a bounded worker holds the lock, `flock -n output/.heavy.lock true` fails; acquisition succeeds after the worker exits.
- Docs explain: oomd pressure failure mode; whole-file mmap and dirty page-cache residency; view lifetimes; side and group memory; deferred out-of-core `_finalize_dump`.
- Existing build, kernel, and plan04 PSS contracts remain intact (do not rewrite Contract H / PSS gates).

## Changes

1. **`docs/WORKFLOW.md`** — add a clear "Heavy jobs (memory)" section after the existing workflow-plugin material:
   - Lock: always `flock output/.heavy.lock <command>` for the entire process tree of any memory benchmark, dump scan/join, K1 run, or other heavy task (including fixture prep). One worker / one heavy command at a time. Existing caps (cbuild/make ≤ `-j4`, K1/harness ≤ `-j6`) do **not** authorize overlap. If `flock -n` fails, wait; never stack beside an active job (including Sol 3-13/3-14). Do not `drop_caches`. Prefer file-based EXIT markers over self-matching `pgrep` loops.
   - Recommended wrapper example wrapping the flocked command in `systemd-run --user --scope -p MemoryAccounting=yes` so oomd kills the job scope and `memory.peak` is attributable.
   - Documented reproduce commands (from repo root, with `.venv-rp/bin/python`):
     - Residual (Phase 1): `flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py --out output/scratch-5-01/results.json`
     - Finalize (Phase 2): `flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py finalize-run --out output/scratch-5-02/finalize_results.json` (`TMPDIR=output/scratch-5-02/tmp`)
     - 3-07 (Phase 3): `… s07-run --out output/scratch-5-03/s07_results.json`
     - Triage (Phase 3): `… triage-run --out output/scratch-5-03/triage_results.json`
   - Metric interpretation: max RSS in KiB counts touched mapped file pages; `memory.peak` includes dirty/unmapped page cache charged to the scope — both are gated because oomd acts on pressure from both. `tracemalloc` / logical mapped size are not RSS evidence. Plan04 multiprocess PSS gates are unchanged and separate.
   - Point to provenance for fixture seeds/hashes and IMPLEMENTATION.md for measured peaks.

2. **`docs/ARCHITECTURE.md`** — add a section (e.g. "Bounded dump I/O and heavy-job memory") covering:
   - Shared boundary `parser/kiwiw/dump_io.py` (DEFAULT_WINDOW 65536; at most one source/dest/assign window; release views before reuse; write-behind via `sync_file_range` + `posix_fadvise(DONTNEED)`).
   - Transformation adapters in `parser/tools/dump_join.py` (residual byte146; 3-07 144→152) and triage readers in `k1_triage.py`; I/O-only helper — no new C layout / per-row Python kernel.
   - Failure mode: systemd-oomd kills sibling scopes under `user@*.service` when memory pressure (PSI) stays high — often not the process that dirtied cache. Whole-file `np.memmap` + `shutil.copyfile` keep ~2.3 GiB dirty/cache outside RSS.
   - Side/group memory scales with side rows and retained aggregation cardinalities (report separately; triage RSS is not cardinality-independent).
   - K1 `_finalize_dump`: redundant full copies removed (Phase 2); **out-of-core / external-sort rewrite remains deferred** (known limitation, not live plan work).
   - Measurement: fresh worker per transient cgroup; gate max RSS and `memory.peak`; do not conflate with plan04 PSS sampler peaks (finalizer runs after sampler stop).

3. **`IMPLEMENTATION.md`** — append Phase 4 close: what landed, lock-probe evidence, which reproduce commands were re-run (or explicitly skipped with reason: 3-14 lock / disk), confirmation that build/kernel/PSS contracts untouched. Trailer line for the closing commit: `Workflow-Phase: 05-heavy-job-memory:4`.

4. Verification (binding):
   - While any holder has the lock (3-14 or a short self-held `flock` sleep), `flock -n output/.heavy.lock true` exits non-zero; after release, exits 0.
   - Prefer re-running at least the residual controller under the lock when free and after cleaning prior fixtures; if 3-14 still holds or disk forbids, record skip + rely on Phase 1–3 recorded PASS results and small `pytest` for `test_dump_join_memory` / `test_perf_inventory` (non-heavy). Do not invent new gates.
   - Confirm docs do not claim a machine-wide MemoryMax or a mandatory scope wrapper.

### Keep untouched

- `parser/kiwiw/_cenc.c`, build path, K1 rules, plan04 PSS gates, scratch-3-12 live dumps, unit 3-14 worktree.
- Do not force-add generated dumps. Do not run `:done` / plan close-out.

## Done evidence

- Brief committed before docs (`Workflow-Phase: 05-heavy-job-memory:4-brief` or equivalent brief-only commit).
- `docs/WORKFLOW.md` and `docs/ARCHITECTURE.md` contain the required guidance; existing workflow-plugin and C-first contracts still present.
- Lock probe: fail-while-held and succeed-after demonstrated (command + exit codes in IMPLEMENTATION.md).
- Closing commit on master with `Workflow-Phase: 05-heavy-job-memory:4`.
- Report JSON: status, SHAs, verification of doc commands/lock probe, blockers; `not_started`: 3-14, plan close-out.

## Report back

Under 1,200 tokens. Status + SHAs + verification table + any skip reason for full gate re-run.
