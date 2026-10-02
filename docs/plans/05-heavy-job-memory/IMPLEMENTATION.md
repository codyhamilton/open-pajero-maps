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

Brief authored; implementation pending.
