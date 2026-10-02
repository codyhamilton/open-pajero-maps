# Implementation: 05-heavy-job-memory

Run identity:

- Tool: Claude Code orchestrator
- Session: https://claude.ai/code/session_01KFbprktJzdCyubbCXezU5h
- Start time: Fri Oct  2 12:50:25 PM UTC 2026

## Phase 1 — Residual extension cuts peak memory with identical bytes

### 1-01-extend-residual-bounded-io

Flash (opencode) attempt ended early: its sandbox rejected `/proc/self` and `systemd-run`; it left only the vendored baseline. Re-dispatched on Sonnet 5.5 (not sandboxed that way); independent Sonnet 5.5 review: ACCEPT (`review_1-01.md`).

Built: `parser/tools/dump_join.py` (streaming pread/pwrite window write; narrowing cast, non-stable argsort, leftmost-match and byte146-from-flag preserved; opt-in `--verify`, plus `--verify-only`), `parser/tools/bench_dump_memory.py` (paired baseline/candidate in transient `systemd-run --user --scope`, max RSS + `memory.peak` + memory.stat, isolated replay root refusing real `output/`, `check-root`), `parser/tests/test_dump_join_memory.py` (17 pass with perf_inventory test), vendored baseline in `parser/tests/fixtures/dump_join_baseline/` (SHA256SUMS), `parser/perf_inventory.json`, `docs/provenance.md`.

Deviations: `--verify-only` and `check-root` added; replay root must sit under `output/scratch-5-01/`. Brief contradiction: baseline leaves partial output on an empty kind before `np.memmap` raises; candidate rejects before writing. Recorded in the review.

Measured (1,000,013 rows; fresh processes; controller run `bench_dump_memory.py`):

| | worker run | orchestrator re-run (concurrent with Sol 3-13 oracle) |
|---|---|---|
| max RSS cand/base | 0.165 | 0.166 / 0.169 / 0.166 |
| memory.peak cand/base | 0.243 | 0.199 / 0.245 / 0.256 |
| median wall cand/base | 0.333 | 0.310 |
| 2M-row growth vs 1M (bound 19,456 KiB) | −204 KiB RSS, +36 KiB peak | +436 KiB RSS, −3,052 KiB peak |
| output SHA256 (bin, manifest, counts, stdout) | equal ×3 | equal ×3 |

Baseline `memory.peak` spread was 0.02% in the worker run and 27.6% in the orchestrator re-run (concurrent load); all gates pass with the ratios ≤0.26 in either case.

### Phase 1 close

Verification: orchestrator independent re-run of the controller (all PASS, above) plus the Sonnet review's re-run of `sha256sum -c` and pytest. Outcome (≥50% lower max RSS and `memory.peak`, identical bytes, bounded growth, wall ≤2×) holds.

**Carried**
1. The scratch entry point `output/scratch-3-12/extend.py` is not switched to `dump_join.py` (Assumption 6 tension): plan04 3-13 reads scratch-3-12. Switch after 3-13 is accepted.
2. Growth gate references the median 1M candidate, not the worst; passes with large margin either way.
3. `memory.peak` baseline spread depends on concurrent load; Assumption 8 fallback (anon+dirty+writeback) not exercised.

## Phase 2 — K1 dump finalizer drops redundant full copies

### 2-01-finalize-dump-drop-copies

Flash (opencode / deepseek-flash) authored the first cut; concurrent Codex Sol also touched the same surfaces and left a blocked handoff. Orchestrator finished: resolved duplicate harness, fixed the stable-order fixture (padding-byte markers, not unique `dcls`), switched the candidate write to chunked permutation slices (no second full gather / no `tobytes()`), re-ran tests and the RSS gate under `flock output/.heavy.lock`.

Built: `_finalize_dump` prealloc + `readinto` + per-part unlink + stable `argsort(order=DUMP_ORDER, kind="stable")` + chunked `tofile` by permutation; vendored `parser/tests/fixtures/finalize_dump_baseline/`; `bench_dump_memory.py` `finalize-genfixture` / `finalize-worker` / `finalize-run`; five finalize tests in `test_quantisation_roundtrip.py`; `docs/provenance.md` scratch-5-02 entry.

Measured (1,000,013 rows × 144 B; 8 parts; fresh scoped workers; controller `finalize-run`; results `output/scratch-5-02/finalize_results3.json`):

| pair | base max RSS KiB | cand max RSS KiB | delta KiB (gate 140626) | wall base/cand s |
|---|---:|---:|---:|---|
| 0 | 471004 | 199072 | 271932 | 1.85 / 0.93 |
| 1 | 471060 | 198832 | 272228 | 1.86 / 0.99 |
| 2 | 470576 | 198740 | 271836 | 1.72 / 0.97 |

Output SHA256 equal on every pair (`.bin` + manifest); counts equal; parts deleted; median wall ratio 0.524. Earlier full-gather candidate peaked ~330 MiB and pair1 missed the gate by tens–hundreds of KiB; chunked write cleared it with margin. Tests: `146 passed` (`test_quantisation_roundtrip`, `test_k1_dump`, `test_dump_join_memory`, `test_perf_inventory`).

### Phase 2 close

Verification: orchestrator measurement under heavy.lock (all PASS, above) plus pytest. Outcome (byte-identical finalize vs frozen baseline; max RSS lower by ≥ one full array every pair; existing dump tests pass) holds.

**Carried**
1. Chunked permutation write (64 Ki rows) is an allowed elaboration of DESIGN's "write the gathered rows without tobytes()": same stable `argsort` permutation and identical bytes, without a second full-size gather array. Needed for a reliable ≥140626 KiB RSS delta under host memory noise.
2. Stable-order observability uses unnamed dtype padding at byte 65, not unique `dcls` (NumPy uses omitted named fields as tie-breakers when `DUMP_ORDER` keys collide).
3. Flash sandboxed `/proc` intermittently; measurement was run by the orchestrator outside that sandbox (self-measure). Phase 1 residual harness remains the default `bench_dump_memory` entry point.

## Phase 3 — 3-07 extension and triage use the proven storage boundary

### 3-01-dump-io-extract

Flash WIP resumed after infra interrupt on `flash/05-p3-dump-io-window-boundary` @ `37a6b6d`. Finished extraction + consumers + gates; concurrent 3-14 Sol seat shared `output/.heavy.lock` (serial) and did not touch `_cenc.c`.

Built: `parser/kiwiw/dump_io.py` (DEFAULT_WINDOW=65536; sync_file_range/drop/pread/pwrite; `file_rows` rejects zero-row; WindowedReader/Writer; AssignReader/Writer with write-behind); `dump_join.py` residual refactored onto dump_io + `extend_s02_producer` (stable side sort, 144→152 rebuild, scope/cast/aggregate assert); `k1_triage.py` windowed summary/classify/enumerate + `_own_key` for retained aggregation keys; `bench_dump_memory.py` `s07-run` / `triage-run`; vendored `extend_3_07_baseline/` + `k1_triage_baseline/`; tests `test_extend_s02_memory.py` + window/key-ownership/high-card cases in `test_k1_triage.py`; inventory + provenance scratch-5-03. Scratch `output/scratch-3-07/extend_dump_attempt3.py` is a thin wrapper (gitignored under `output/`).

Deviations:
1. Triage enumerate growth initially reused the 1M classify assign against the 2M fixture (AssignReader length check correctly failed). Fixed by a separate `enum-growth-prep` classify on the growth fixture; re-run PASS.
2. High-cardinality peak≤baseline gate covered by unit-level late-first / window-straddle identity (`test_high_cardinality_late_first_identical`); full 1M high-card RSS pair not added (disk ~12G free, serial with 3-14). Fixed-cardinality 1M triage RSS gates already hold at ≤0.36 peak.

Tests: `34 passed` (`test_dump_join_memory`, `test_k1_triage`, `test_perf_inventory`, `test_extend_s02_memory`); fixture `sha256sum -c` OK.

Measured 3-07 (`s07-run`, 1,000,013 rows 144→152; results `output/scratch-5-03/s07_results.json`):

| pair | rss cand/base | peak cand/base | SHA |
|---:|---:|---:|---|
| 0 | 0.208 | 0.320 | equal |
| 1 | 0.207 | 0.323 | equal |
| 2 | 0.208 | 0.322 | equal |

Growth (2M vs median 1M cand): +176 KiB RSS, −172 KiB peak (bound 18,944); wall_ok; controller PASS.

Measured triage (`triage-run` after growth-assign fix; `output/scratch-5-03/triage_results.json`):

| cmd | pair rss ratios | pair peak ratios | growth ΔRSS/Δpeak KiB (bound 9,728) |
|---|---|---|---|
| summary | 0.176 / 0.185 / 0.178 | 0.210 / 0.210 / 0.210 | +616 / +784 |
| classify | 0.192 / 0.191 / 0.192 | 0.283 / 0.287 / 0.285 | +60 / +592 |
| enumerate | 0.208 / 0.209 / 0.208 | 0.360 / 0.357 / 0.354 | −308 / −952 |

All pairs SHA-equal; wall_ok; controller PASS. Phase-1 residual re-check under heavy.lock (`results_p3_recheck.json`): RSS ratios 0.176/0.175/0.181, peak 0.260/0.260/0.258, SHA equal ×3, growth +8 KiB RSS / +10,192 KiB peak (bound 19,456), wall 0.309; EXIT 0.

### Phase 3 close

Verification: pytest 34 pass + s07_controller PASS + triage_controller PASS + residual re-check. Outcome (dump_io boundary; 3-07 + triage byte identity; ≤50% max RSS and memory.peak on 1M fixtures; growth gates; Phase 1 gates still hold) holds.

**Carried**
1. High-cardinality triage peak≤baseline at 1M rows not separately measured; unit artifact identity across windows + fixed-cardinality 50% gates stand in. Revisit if a high-card RSS regression is suspected.
2. Scratch `extend_dump_attempt3.py` wrapper lives under gitignored `output/`; tracked adapter is `dump_join.extend_s02_producer`.
3. Host disk stayed ~96–98% full; scratch fixtures deleted after measurement; share `output/.heavy.lock` with plan04 3-14.

Workflow-Phase: 05-heavy-job-memory:3

## Phase 4 — Heavy-job commands reproduce the memory proof serially

### 4-01-heavy-job-docs

Docs-only unit (Maps Execute). Brief authored first @ `f040c7f`
(`Workflow-Phase: 05-heavy-job-memory:4-brief`).

Built:

- `docs/WORKFLOW.md` — "Heavy jobs (memory)": repo-root lock
  `output/.heavy.lock`, one-worker serial rule, recommended
  `systemd-run --user --scope -p MemoryAccounting=yes` wrapper (optional
  `MemoryHigh=`; no machine-wide cap), bounded reproduce commands for residual /
  `finalize-run` / `s07-run` / `triage-run`, KiB RSS vs `memory.peak`
  interpretation, fixture SHA pointers, Phase 1–3 peak summary + limitations.
- `docs/ARCHITECTURE.md` — "Bounded dump I/O and heavy-job memory":
  `dump_io` window / write-behind / view-lifetime contract; adapter ownership;
  oomd pressure failure mode vs whole-file mmap/`copyfile`/multi-array
  finalizer; side/group cardinality accounting; deferred out-of-core
  `_finalize_dump` as a known limitation. Build, kernel, and plan04 PSS
  contracts left intact.
- No harness change (documented command strings already match
  `bench_dump_memory.py`).

Verification:

| Check | Result |
|---|---|
| `pytest` dump_join / extend_s02 / k1_triage / perf_inventory | 34 passed |
| Vendored `dump_join_baseline` + `finalize_dump_baseline` `sha256sum -c` | OK |
| `flock -n output/.heavy.lock true` while plan04 3-14 held lock | exit 1 |
| Self-held lock then non-blocking probe / probe after release | `probe_while_self_held_exit=1`, `probe_after_release_exit=0` (log `output/scratch-5-01/lock_probe.log`, AEST 06:10) |
| Full residual controller (documented WORKFLOW command) | **PASS** exit 0 under `flock` → `output/scratch-5-01/phase4_residual_results.json` (RSS ratios ≈0.18, peak ≈0.26–0.27, SHA equal ×3, growth/wall/verify PASS). Fixtures deleted after. |
| Finalize / s07 / triage controller re-run | **skipped** (disk ~96%; Phase 2–3 already PASS'd with the same documented commands). |

### Phase 4 close

Outcome (stable docs: one lock path, recommended scope wrapper, one-worker
commands, RSS vs `memory.peak`, provenance + measured peaks + limitations,
lock-probe fail-while-held / succeed-after, oomd/mmap/dirty/view/side/group +
deferred out-of-core finalizer; build/kernel/PSS intact) holds for the
documentation surface. Residual documented command re-run under flock PASS'd after 3-14
released; finalize/s07/triage left to prior Phase 2–3 evidence (disk).

**Carried**

1. Finalize / s07 / triage controllers not re-run in Phase 4 (disk); residual
   documented command re-verified PASS. Parent may re-run the others serially.
2. High-cardinality triage 1M RSS pair and out-of-core finalizer remain as in
   Phase 3 / DESIGN (not Phase 4 scope).
3. Plan close-out / `Workflow-Phase: …:done` not run here — parent decides.

Workflow-Phase: 05-heavy-job-memory:4
