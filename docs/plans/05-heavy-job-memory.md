# Heavy-job memory usage

Plan 05 cut peak residency and dirty page-cache charge for residual dump joins, the K1 dump finalizer, the 3-07 extension, and `k1_triage` readers after systemd-oomd pressure kills on the Ubuntu host. Bounded windowed I/O, a leaner finalizer, and stable lock/scope docs landed on master. Byte and aggregate semantics were preserved on the seeded fixtures; every phase memory gate that was measured passed. Live `scratch-3-12/extend.py` was left on the whole-file baseline at plan-05 close-out; plan 17 later switched it to a thin wrapper over the tracked residual `dump_join` adapter.

## Intent

User request, verbatim:

> run workflow design→execute on memory-usage optimisation for heavy jobs (esp. output/scratch-3-12/extend.py and similar dump joins). Ubuntu OOM'd several times. Profile is numpy/C-buffer heavy (memmap ~2.5Gi background_boundary + chunk asserts with np.array_equal that materialise full-chunk copies), not Python object-graph. Concurrent Claude RC + Sol + OpenCode amplify pressure. Goal: cut peak RSS without changing semantics (byte146 padding field join; other bytes unchanged). Prefer streaming/memmap, drop or sample asserts, avoid materialising full-chunk copies, document heavy.lock discipline.

## Why This Existed

Host kills were systemd-oomd pressure kills on `user@1000.service`, not always the kernel OOM killer picking the heaviest RSS process. Residual extension copied the whole dump then whole-file `memmap`'d it; triage and 3-07 used multi-million-row memmap slices; `_finalize_dump` held about three full arrays after the plan04 PSS sampler had stopped. RSS alone missed dirty page cache from `copyfile`. Concurrent agents amplified pressure and often killed siblings (terminals, browsers).

## What Was Built

**Changed:** `parser/kiwiw/dump_io.py` (new); `parser/tools/dump_join.py` (new residual + 3-07 adapters); `parser/tools/bench_dump_memory.py` (new measurement controller); `parser/tools/k1_triage.py`; `parser/tools/quantisation_roundtrip.py` (`_finalize_dump` only); tests and vendored baselines under `parser/tests/`; `parser/perf_inventory.json`; `docs/WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/provenance.md` (scratch-5-0{1,2,3}).

### Phase 1 — Residual bounded I/O

Streaming pread/pwrite windows (default 65,536 rows), write-behind + page-cache drop, no whole-file copy, no production full-chunk asserts, opt-in `--verify`. Vendored frozen `extend.py`/`study.py`/`witness.py` replayed in an isolated root that refuses real `output/` outside scratch-5-01. On 1,000,013-row fixtures, cand/base max RSS ≈ 0.17 and `memory.peak` ≈ 0.20–0.26; growth and wall ≤2× gates passed; output SHA equal.

### Phase 2 — Finalize drops redundant copies

`_finalize_dump` preallocates, `readinto`s parts and unlinks as consumed, keeps stable `argsort(order=DUMP_ORDER)`, writes by chunked permutation (no full `tobytes()` / second gather). RSS fell by ≥ one full fixture array (~140,626 KiB gate; ≈272 MiB observed) every pair; bytes and counts identical to the frozen baseline.

### Phase 3 — Shared dump_io + 3-07 + triage

Extracted `dump_io` (WindowedReader/Writer, AssignReader/Writer, zero-row reject). Residual moved onto it; `extend_s02_producer` (stable side sort, 144→152 rebuild); triage `summary`/`classify`/`enumerate` windowed with `_own_key` for retained aggregation keys. 3-07 and triage fixed-cardinality 1M gates ≤50% RSS/peak; Phase 1 residual re-check still PASS. Scratch `extend_dump_attempt3.py` became a thin wrapper over the tracked adapter.

### Phase 4 — Stable commands and architecture

WORKFLOW: one repo-root `output/.heavy.lock`, one-worker serial rule, recommended `systemd-run --user --scope -p MemoryAccounting=yes` wrapper, reproduce commands for residual / finalize / s07 / triage, KiB RSS vs `memory.peak`. ARCHITECTURE: window/write-behind contract, oomd failure mode, side/group cardinality accounting, deferred out-of-core finalizer. Lock probe fail-while-held / succeed-after demonstrated; residual documented command re-run under flock PASS.

## Deviations

- Scratch `output/scratch-3-12/extend.py` left on the whole-file baseline at close-out (Assumption 6 tension with plan04 3-13); durable path kept as the tracked adapter + isolated harness. Follow-up landed in plan 17 (thin wrapper over `dump_join`).
- Empty-kind: candidate rejects before write; baseline left partial output then failed on `memmap` — matches validation-before-write / Assumption 7.
- Phase 2 candidate write uses chunked permutation slices rather than a single gathered array write (same bytes, lower peak).
- High-cardinality triage 1M RSS pair not separately measured; unit late-first / window-straddle identity stands in.
- Phase 4 skipped finalize/s07/triage controller re-runs (disk ~96%); relied on Phase 2–3 PASS plus residual re-verify.
- Harness extras: `--verify-only`, `check-root`; replay root constrained under `output/scratch-5-01/`.

## Review

Terminal independent review at `120bc78` / `2e2363a`: **PASS_WITH_FOLLOWUPS**. Phases 1–4 met (with the substitutions above). No blocker or high findings. Intent matched; ledger held except the open scratch-3-12 switch. Plan was sufficient to place gates and QA. Mechanical stale WORKFLOW paths into the plan folder were rewritten on close-out.

## QA

Bounded serial evidence under `output/.heavy.lock`, fresh `systemd-run --user --scope` workers, paired baseline/candidate, three pairs per gate where required. Pytest at close-out wrap: 128 passed (`test_dump_join_memory`, `test_extend_s02_memory`, `test_k1_triage`, `test_quantisation_roundtrip`, `test_perf_inventory`). Vendored fixture `sha256sum -c` OK across baselines. Full-disc confirmation was evidence-only (Assumption 10), not a phase gate.

## Residual Risks

- The live scratch-3-12 path is now the `dump_join` wrapper / tracked CLI (plan 17); the whole-file risk remains only if the vendored baseline under `parser/tests/fixtures/dump_join_baseline/` is re-run live outside the isolated replay harness.
- Finalize still holds one full in-memory kind array (out-of-core deferred).
- `memory.peak` spreads under concurrent load; the advisory lock cannot stop a job that never takes it.
- High-cardinality triage RSS remains unmeasured at 1M rows.

## Follow-ups

- ~~Switch `output/scratch-3-12/extend.py` to `dump_join` after plan04 3-13 is accepted (Assumption 6).~~ **Closed — landed in plan 17** (thin wrapper over tracked `dump_join` residual defaults).
- Optional high-cardinality triage 1M RSS pair if a regression is suspected (Architecture / WORKFLOW limitations).
- Optional serial re-run of finalize / s07 / triage documented commands when disk headroom allows.
- Out-of-core `_finalize_dump` remains a known limitation in `docs/ARCHITECTURE.md`, not live plan work.

## Decisions Worth Keeping

- Gate both max RSS and cgroup `memory.peak`; recommend per-job transient scopes so oomd kills the job, not a sibling.
- Vendor frozen baselines into tracked fixtures; replay only in roots that cannot resolve into live `output/`.
- Extract I/O (`dump_io`) separately from transformation adapters; do not unify join/witness semantics.
- Remove production full-chunk asserts; prove with bounded SHA equality plus opt-in streaming verify.
