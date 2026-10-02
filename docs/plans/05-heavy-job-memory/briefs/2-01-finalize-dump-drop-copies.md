# Brief: 2-01 — K1 dump finalizer drops redundant full copies

Consumer: Flash executor (opencode). You have only this brief and the repo.
Owned paths: `parser/tools/quantisation_roundtrip.py` (`_finalize_dump` only — do not rewrite other functions), `parser/tools/bench_dump_memory.py` (extend with a Phase-2 finalize mode; keep Phase-1 residual mode working), `parser/tests/test_quantisation_roundtrip.py` (add finalize equivalence / part-deletion / stable-order cases), `parser/tests/fixtures/finalize_dump_baseline/` (new; vendored frozen pre-change `_finalize_dump`), `docs/provenance.md` (append Phase-2 scratch entries only), `output/scratch-5-02/` (git-ignored scratch). Touch nothing else.
Commits: Leave changes in the working tree. Do not commit; the orchestrator commits.
Depends on: Phase 1 (harness patterns in `bench_dump_memory.py`).
Runs alongside: nothing. Single unit, no parallelism.
Budget: 10 files to read, about 400 lines to change, 90 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/05-heavy-job-memory/IMPLEMENTATION.md` (done, not done, what you learned) and report `over budget`.

## Required reading, in order

1. `docs/plans/05-heavy-job-memory/DESIGN.md` — binding: Contract (K1 dump finalizer) lines 63–67, Contract (measurement) lines 72–78, Contract (operation) lines 87–91, Assumption 9 lines 177–184, Phase 2 lines 226–235. Read by those ranges only.
2. `parser/tools/quantisation_roundtrip.py` — `DUMP_ORDER` (~93–94) and `_finalize_dump` (~1350–1384) only. Do not read the whole file.
3. `parser/tools/bench_dump_memory.py` — measurement pattern (`run_scoped`, worker, controller gates, `SCRATCH`, heavy-lock discipline). Skim the controller and worker; reuse, do not rewrite Phase 1.
4. `parser/tests/test_k1_dump.py` lines 1–110 — existing dump equivalence expectations (row counts, manifest, worker-count independence). Do not change this file unless a Phase-2 case truly belongs there; prefer `test_quantisation_roundtrip.py`.
5. `kiwiw.cenc.K1_DUMP_DTYPE` / `K1_DUMP_FIELDS` — `itemsize` must be 144; fields drive the manifest.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Change `_finalize_dump` so it no longer holds every per-task part alive beside their concatenation and no longer copies the sorted array through `tobytes()`, while producing byte-identical per-kind `.bin` files, identical `dump_manifest.json`, identical returned counts, and the same part deletion as the frozen pre-change function. On the bounded 1,000,013-row fixture, every paired fresh-worker max RSS must fall by at least one full array (140,626 KiB).

## Contract

Settled; cited from DESIGN.md. Do not re-decide.

- Finalizer contract, DESIGN lines 63–67:
  - Unchanged: per-kind output bytes, canonical order (`argsort(order=DUMP_ORDER, kind="stable")` semantics), manifest bytes, returned counts, part deletion.
  - Removed: holding parts alive alongside their concatenation, and the `tobytes()` copy of the sorted array.
  - Sorted rows are written without an intermediate full-size bytes object.
- Phase 2 outcome, DESIGN lines 228–231:
  - Call `_finalize_dump` directly on a deterministic bounded set of per-task part files. No K1 run.
  - Parts: 1,000,013 rows of `cenc.K1_DUMP_DTYPE` spread over at least 8 parts, with duplicate sort keys whose stable order is observable.
  - Fresh-worker max RSS lower than baseline by ≥ `1000013 * 144 / 1024 = 140626` KiB in **every** paired run.
  - Existing quantisation dump tests pass (`parser/tests/test_k1_dump.py`, `parser/tests/test_quantisation_roundtrip.py`).
- Approach, DESIGN line 233: read parts into one preallocated array and release them as consumed; keep the identical stable `argsort(order=DUMP_ORDER, kind="stable")` permutation; write gathered rows without `tobytes()` (e.g. `ndarray.tofile` / `readinto` / buffer write — no `Path.write_bytes(arr.tobytes())`, no `bytes(arr)`, no `memoryview(arr).tobytes()` that materialises a full copy).
- Non-goals (DESIGN line 67): no external-sort / out-of-core rewrite; no changes to `cenc.K1Dump` ownership copies; no K1 worker-side memory changes; do not edit functions other than `_finalize_dump` inside `quantisation_roundtrip.py`.

## Changes

Decisions you should not have to re-derive.

1. **Vendor the frozen baseline first**, before editing production `_finalize_dump`. Copy the current function body (and only the imports/constants it needs: `Path`, `json`, `numpy`, `DUMP_ORDER`, and a `cenc`-compatible dtype lookup) into `parser/tests/fixtures/finalize_dump_baseline/finalize_dump_baseline.py` as `finalize_dump_baseline(dump_dir, kinds, ntasks, log)`. Record SHA256 of that file in `parser/tests/fixtures/finalize_dump_baseline/SHA256SUMS`. The baseline must preserve today's algorithm exactly: `np.fromfile` all existing parts into a list → `np.concatenate` → stable `argsort(order=DUMP_ORDER, kind="stable")` → `Path.write_bytes(arr.tobytes())` → delete parts as today does (today deletes each part immediately after `fromfile`, before concatenate). Do not "improve" the baseline.
2. **Candidate `_finalize_dump`** in `parser/tools/quantisation_roundtrip.py`:
   - For each kind, discover `part_{i:05d}_{name}.bin` for `i in range(ntasks)` exactly as today.
   - Determine total row count from part file sizes (`st_size // itemsize`) before allocating; reject / treat truncated non-multiples as today would (today's `fromfile` reads whole dtype rows only — match that).
   - Preallocate one `np.empty(total, dtype=cenc.K1_DUMP_DTYPE)` (or `np.zeros(0, ...)` when no parts).
   - Read each part into a contiguous slice of that array, then drop the temporary and `unlink` the part before reading the next (never retain a list of all part arrays). Prefer `readinto` on a view of the destination slice to avoid a per-part full temporary when practical; a short-lived per-part array that is `del`'d before the next read is acceptable.
   - If `len(arr) > 1`: `arr = arr[np.argsort(arr, order=DUMP_ORDER, kind="stable")]` — identical call, including `kind="stable"`.
   - Write `(dump_dir / f"{name}.bin")` from the array buffer without `tobytes()` (use `arr.tofile(...)` or an equivalent buffer write that does not allocate a full-size `bytes`).
   - Manifest, log line, and returned `counts` dict must be byte/value identical to the baseline for the same inputs (same `json.dumps(..., indent=2, sort_keys=True) + "\n"` shape as today).
3. **Correctness tests** in `parser/tests/test_quantisation_roundtrip.py` (small fixtures, no heavy lock):
   - `test_finalize_dump_matches_baseline_bytes`: ≥8 parts, deterministic rows of `K1_DUMP_DTYPE`, including duplicate `DUMP_ORDER` keys whose relative order differs under unstable sort; candidate vs vendored baseline → equal `.bin` SHA256 per kind, equal `dump_manifest.json` bytes, equal returned counts, and **no** `part_*.bin` left.
   - `test_finalize_dump_empty_kinds`: no parts → empty `.bin` (or zero-length write matching baseline), counts 0, manifest present.
   - `test_finalize_dump_single_row` / missing middle parts: gaps in `ntasks` where some `part_*` files are absent (today skips missing) — candidate matches baseline.
   - Do not launch a K1 run. Import `_finalize_dump` from `tools.quantisation_roundtrip` and the vendored baseline function.
4. **Measurement harness** — extend `parser/tools/bench_dump_memory.py` with a Phase-2 finalize controller (subcommand or `--mode finalize` / `finalize-run` — pick one clear CLI; keep the existing residual default working and Phase-1 tests green):
   - Scratch root: `output/scratch-5-02/` (create; set `TMPDIR=output/scratch-5-02/tmp` for subprocesses). Never use host `/tmp` defaults for fixtures.
   - Fixture generator: seeded, deterministic, **1,000,013** rows of `cenc.K1_DUMP_DTYPE`, written as **≥8** `part_{i:05d}_{kind}.bin` files for one kind (e.g. `background_boundary`), with intentional duplicate sort keys. Fsync + pre-read in the controller before each pair. Workers must not inherit a materialised in-memory fixture.
   - Each worker: fresh process via `systemd-run --user --scope -p MemoryAccounting=yes -- /usr/bin/time -v -o <marker>/time.txt ...` (same pattern as Phase 1). Mode `baseline` calls the vendored `finalize_dump_baseline`; mode `candidate` calls production `_finalize_dump`. Copy a fresh part tree into the worker's private dir each run (parts are deleted by finalize).
   - Record max RSS (KiB from `/usr/bin/time -v`) and cgroup `memory.peak` / `memory.stat` as Phase 1 does. **Gate only on max RSS for Phase 2** (DESIGN Phase 2): for every pair, `baseline_rss - candidate_rss >= 140626`. Also gate: every pair output SHA256 (all `.bin` + `dump_manifest.json`) equal; returned counts equal; median candidate wall ≤ 2× baseline median wall; all workers exit 0.
   - Three paired runs (baseline then candidate, alternating). Write results JSON under `output/scratch-5-02/`.
   - If your sandbox cannot read `/proc/self/cgroup` or cannot invoke `systemd-run`, implement the code paths and small tests fully, leave the heavy measurement unrun, and report `done with concerns` naming that gap — the orchestrator will measure outside the sandbox under `flock output/.heavy.lock`.
5. **Inventory / provenance**: no new production module file is required. If you add a substantial new helper module, register it in `parser/perf_inventory.json` under the existing class rule and keep `test_perf_inventory.py` passing. Append short `docs/provenance.md` entries only for new git-ignored scratch under `output/scratch-5-02/`.
6. **Keep Phase 1 green**: `python -m pytest parser/tests/test_dump_join_memory.py parser/tests/test_perf_inventory.py -q` must still pass after your bench edits.

Operational constraints, all binding:

- Temp files stay inside the repo: `output/scratch-5-02/` (git-ignored via `output/`). Set `TMPDIR=output/scratch-5-02/tmp` for every measured subprocess.
- Every heavy run (1M-row fixture generation, baseline/candidate workers, hashing of big files) runs only under `flock output/.heavy.lock <command>` held for the entire process tree. If `flock -n output/.heavy.lock true` fails, wait; do not stack. Small correctness tests are not heavy and run outside the lock.
- No K1 run, no cbuild, no `drop_caches`, no subagents.
- Host memory is tight (swap often full). Keep the finalize fixture to one kind × 1,000,013 rows; do not add a 2M-row finalize growth gate unless it fits easily — Phase 2's DESIGN outcome does not require doubled-row growth.
- Do not modify `output/scratch-3-12/` or any plan-04 triage paths. Do not touch unrelated dirty working-tree files (`docs/plans/04-c-core-orchestration/triage/*`, existing `docs/provenance.md` dirty hunks beyond your append).
- Launch long jobs in the background with an EXIT marker file under `output/scratch-5-02/` and poll with `test -f` + bounded sleep. Never `pgrep -f` / `ps | grep` loops.
- If Flash sandbox blocks `/proc` or `systemd-run` (Phase 1 failure mode): finish implementation + small tests, skip the heavy RSS run, report clearly.

### Keep untouched

- `parser/tools/dump_join.py`, `parser/kiwiw/*`, `parser/tools/k1_triage.py`, `output/scratch-3-*`, Phase 3 surfaces.
- Functions in `quantisation_roundtrip.py` other than `_finalize_dump`.
- Unrelated dirty files in the working tree (plan-04 triage).

## Done evidence

Identify or write the failing check before changing production `_finalize_dump`. Report its output before and after.

- After vendoring baseline and writing tests (before candidate change): a test that runs candidate==baseline on today's identical code may pass; introduce a deliberate temporary divergence OR assert the candidate path will use prealloc (e.g. fail a test that inspects that `write_bytes`/`tobytes` is gone after the change). Practical sequence: vendor baseline → add equivalence tests against current `_finalize_dump` (should pass) → change `_finalize_dump` → tests still pass → add a source-level guard test that `_finalize_dump`'s source does not contain `.tobytes()` / `write_bytes` for the dump write.
- `python -m pytest parser/tests/test_quantisation_roundtrip.py parser/tests/test_k1_dump.py parser/tests/test_dump_join_memory.py parser/tests/test_perf_inventory.py -q` → all pass (skip C-missing skips as today).
- `cd parser/tests/fixtures/finalize_dump_baseline && sha256sum -c SHA256SUMS` → OK.
- `flock output/.heavy.lock python parser/tools/bench_dump_memory.py finalize-run --out output/scratch-5-02/results.json` (exact CLI per your choice; document it) → exit 0, every pair `baseline_rss - candidate_rss >= 140626`, output SHA256 equal, wall ≤2×. If sandbox-blocked, say so and leave the command ready.
- `git status --short` shows only owned paths (plus any pre-existing unrelated dirty files you did not stage).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, check output before/after, deviations, contradictions with DESIGN (never resolve silently). Short table: per pair baseline vs candidate max RSS (KiB), delta KiB, `memory.peak`, wall; output SHA equality. Name the CLI for the finalize controller. Say whether you ran the heavy measurement or left it for the orchestrator.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
