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
