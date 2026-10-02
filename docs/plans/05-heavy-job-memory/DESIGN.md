# Heavy-job memory usage

## Intent

User request, verbatim:

> run workflow design→execute on memory-usage optimisation for heavy jobs (esp. output/scratch-3-12/extend.py and similar dump joins). Ubuntu OOM'd several times. Profile is numpy/C-buffer heavy (memmap ~2.5Gi background_boundary + chunk asserts with np.array_equal that materialise full-chunk copies), not Python object-graph. Concurrent Claude RC + Sol + OpenCode amplify pressure. Goal: cut peak RSS without changing semantics (byte146 padding field join; other bytes unchanged). Prefer streaming/memmap, drop or sample asserts, avoid materialising full-chunk copies, document heavy.lock discipline.

## Problem

The kills are not kernel OOM. `journalctl` shows `systemd-oomd` killing whole sibling scopes (a terminal on 2026-09-26, Firefox on 2026-10-02) because memory pressure (PSI) on `user@1000.service` exceeded 50% for more than 20 s with reclaim activity. When this design was written, the 8 GiB of swap was full and about 17 GiB was buff/cache. Two things drive that pressure. One is anonymous memory that cannot be reclaimed once swap is full. The other is dirty or heavily reused page cache that reclaim must work through. A heavy job therefore hurts the user's session in two ways: through its own resident set, and through file pages it dirties or keeps active even when they are not mapped. Under oomd, the scope that gets killed is often not the one causing the pressure.

The residual extension is chunked but its residency is not. `output/scratch-3-12/extend.py:10` copies the whole source with `shutil.copyfile`, which leaves about 2.34 GiB of dirty page cache outside the process RSS. Line 11 then maps the whole destination read-write and touches every row with `out[:,146]=0`. Its whole-file source and destination mappings keep touched pages in the process's page tables across the scan. The current boundary dump has 16,550,043 rows × 152 bytes = 2,515,606,536 bytes (2.343 GiB) per mapping. That alone exceeds the reported free RAM before counting the other agents.

At 250,000 rows, the comparison of the first 146 bytes can also allocate a 36,500,000-element boolean temporary. `np.asarray(b).view('u1')` is a view and does not copy the chunk, so the user's "full-chunk copy" is really a chunk-sized boolean temporary of about 36.5 MB per assertion. The assertions also read the destination back, which keeps its pages hot. Removing copies or assertions alone cannot fix the whole-output residency or the dirty-copy problem. The largest side table has 216,488 packed 78-byte rows, about 16.9 MB. Its packed join keys are 31 bytes each. Side keys are stored as `i32` and are cast into the dump's narrower `u8`/`u16` key fields on assignment, and that cast is part of the join's semantics. Sorting the side table has a measurable but much smaller footprint.

Related surfaces have different semantics. `scratch-3-07/extend_dump_attempt3.py` widens 144-byte records to 152 bytes and normalizes padding through a whole-file `w+` mapping. `scratch-3-08/prepare_dump.py` materializes only the three small kinds (739, 824 and 1 rows) and symlinks the two background files, so it has no material memory footprint. `parser/tools/k1_triage.py` uses 2,000,000-row chunks over whole-file read-only mappings and keeps multiple keys and masks plus aggregation state whose size depends on cardinality. It is the heavy command most often re-run, and plan04 3-13 re-runs it.

`parser/tools/quantisation_roundtrip.py:1350–1384` (`_finalize_dump`) runs after the K1 worker pool has joined and after the PSS sampler has stopped, so the recorded K1 dump peak (about 7.9 GiB PSS for 3-03) does not include it. For each kind it keeps every per-task `fromfile` part alive while it concatenates, gathers the stable-sorted rows into a new array, and copies that array again with `tobytes()`. For `background_boundary` (16.5 M × 144 B ≈ 2.38 GB) that is about three full copies at once, roughly 7 GB of anonymous memory in the parent process. It is the largest unmeasured anonymous spike in the heavy-job set.

Ground was read-only: scripts, stable docs, manifest/header metadata, file sizes, the oomd journal and cgroup capabilities. There were no dump scans, no imports of scratch scripts and no heavy runs. A transient `systemd-run --user --scope` works and exposes `memory.peak` on cgroup v2. `docs/OVERVIEW.md`, `docs/ARCHITECTURE.md` and both documents in `docs/design/` exist and were read. The one missing stable contract is operational guidance on memory and the heavy-job lock, supplied in Phase 4.

## Solution Shape

Phase 1 makes the residual extension stream bounded input and output windows. It writes byte146 inside those windows, does not copy the whole file first, writes completed output windows back to disk and drops them from cache, and has no production full-chunk byte assertions. A frozen baseline, replayed in isolation, serves as a bounded equivalence oracle. Phase 2 removes the redundant full-array copies from the K1 dump finalizer. Phase 3 reuses the proven window lifecycle for the 3-07 extension and the triage readers, keeping each transformation's own layout and join policy. Phase 4 publishes the serial measurement and heavy-job commands. Scratch entry points keep their defaults. Tracked adapters and validation keep the change reproducible after the ignored scratch files are gone.

### Domain: Dump transformation and ownership

- Owns: the residual and 3-07 scratch entry points and tracked adapters in `parser/tools/dump_join.py` (new). Each adapter owns its existing transformation, not source-witness attribution.
- Contract (residual): the adapter consumes the current manifest-derived aligned 152-byte layout, the side tables and the row-aligned little-endian u16 assignments.
  - Key: exactly `GROUP = (level, ix, iy, code, p0, p1, p2, p3, p4, p5, p6, shape)`, typed as the dump's fields. Side key columns are converted with the same NumPy field-assignment cast as the baseline (`sk[f]=side[f]`, `i32`→`u8`/`u16` wraps). Out-of-range side values therefore collide exactly as they do today.
  - Flag: for each source row, byte146 is 1 iff the first matching sorted side record has `status == 1`, and 0 otherwise. Missing or empty side tables produce 0. Byte146 is always written from the flag and never copied from the source.
  - Sort: preserve the original default (non-stable) NumPy structured `argsort` call on the same key array, and do not silently substitute a stable sort.
  - Accounting: assignments equal to 65535 select accounting rows only, not which rows get the flag.
  - Preserved: source order, bytes `[0,146)` and `[147,152)`, NaN payloads, padding, manifest metadata (including the `extension_3_12` path strings) and joined counts remain equal to the current script's output.
  - Files: input files are read-only. Writable destinations are private regular files written from the source windows, with no whole-file copy-then-patch.
- Contract (3-07): the adapter keeps the stable side sort, the leftmost exact match, the same key cast and the boundary-only level0/code291/sentinel scope. It rebuilds each 152-byte output row by zeroing the row and copying named fields, then sets byte144. The old unnamed padding is not a raw-copy contract. Preserve its aggregate match assertion.
- Unchanged: `prepare_dump.py` (3-08) keeps byte145, its whole-array preparation of the small kinds and its read-only background symlinks (Assumption 9). `finalise_rules_side.py` remains the owner of mechanism values and witness rules and is not converted into a generic join.
- Non-goals: changing K1 predicates, tolerances, cause rules, source witnesses, generated disc bytes, the C ABI or the canonical dump order. Deduplicating side keys or changing which duplicate wins.

### Domain: Bounded dump I/O

- Owns: window lifetimes, first in `dump_join.py` and then shared in `parser/kiwiw/dump_io.py` (new), plus the triage reader integration.
- Contract: windows.
  - Each active transformation holds at most one bounded source, destination and assignment window at a time.
  - Release every derived view before closing or reusing a window. Slicing a whole-file mapping is not a window, and flushing an entire mapping is not a residency bound.
  - The default window is 65,536 rows. Changing it leaves bytes and aggregates identical.
- Contract: validation before writing.
  - Validate row size, field offsets, complete-row file length and assignment length before writing anything. Handle partial final windows.
  - Zero-length mapped kinds remain unsupported, as in the baseline. Reject them instead of inventing successful empty outputs.
  - Preserve consumer defaults, paths and output formats. No eager full-dump arrays, no full-output initialization, and no retained chain of window views.
- Contract: write-behind. Writable destinations start writeback on each completed window and drop windows already written back from the page cache. The job's dirty and cached output therefore stays bounded to a few windows instead of the whole file (for example with `sync_file_range` plus `posix_fadvise(DONTNEED)`, or an equivalent). The output bytes and the final durability (flush or close) are unchanged.
- Contract: layouts.
  - Layouts are validated against the manifest and the existing C/binding descriptors.
  - The 144-byte base and the 152-byte extensions are distinct supported layouts, not interchangeable guesses.
  - New helper code owns I/O only. It adds no C layout declaration and no per-row Python kernel. Existing NumPy bulk operations stay bulk operations.
  - `parser/perf_inventory.json` classifies new modules under the architecture's existing rule.
- Contract: memory scaling.
  - Window workspace scales with window rows. Sorted side indexes scale with side-table rows.
  - Triage persistent state owns independent key values and must not keep chunk or unique-array backing storage alive through structured scalars.
  - Account separately for distinct GROUP keys, source keys, source/GROUP pairs and rule/GROUP pairs, and hold all of these cardinalities fixed in row-scaling tests. Record them separately from window workspace, and do not claim a cardinality-independent total triage RSS.
  - Preserve first-matching-rule classification, exact counts, sentinel/NaN normalization, grouping across window boundaries, and deterministic summary and enumeration ordering.
- Contract (K1 dump finalizer, `parser/tools/quantisation_roundtrip.py` `_finalize_dump`):
  - Unchanged: per-kind output bytes, the canonical order (`argsort(order=DUMP_ORDER, kind="stable")` semantics), manifest bytes, returned counts and part deletion.
  - Removed: holding parts alive alongside their concatenation, and the `tobytes()` copy of the sorted array.
  - The sorted rows are written without an intermediate full-size bytes object.
- Non-goals: removing the ownership copies from `cenc.K1Dump`, changing long-lived spool or container mappings, an external-sort or out-of-core rewrite of `_finalize_dump`, and changes to K1 worker-side memory.

### Domain: Evidence and heavy-job operation

- Owns: the tracked bounded validation in `parser/tools/bench_dump_memory.py` and `parser/tests/test_dump_join_memory.py` (both new), the existing triage and quantisation tests, and the guidance in `docs/WORKFLOW.md`.
- Contract (measurement): each measured worker is a fresh process in its own transient cgroup (`systemd-run --user --scope -p MemoryAccounting=yes`).
  - Record two peaks and gate on both: (a) maximum RSS from `/usr/bin/time -v` or `getrusage(RUSAGE_SELF)` in KiB, which includes touched mapped file pages, and (b) the scope's cgroup v2 `memory.peak`, which includes anonymous memory plus page cache charged to the job, such as dirty output.
  - Also record `memory.stat` (`anon`, `file`, `file_dirty`, `file_writeback`) at exit and the scope's `memory.pressure` totals.
  - Inputs are generated, fsynced and pre-read by the controller before each paired run, so input cache state is identical for baseline and candidate and is not charged to the worker. Never use `drop_caches`. Targeted `posix_fadvise` on fixture files is allowed.
  - Fixture generation, hashing and the controller are separate processes, and workers must not inherit a materialized fixture.
  - `tracemalloc` and logical mapped size are not RSS evidence. The existing plan04 multiprocess PSS gates remain unchanged.
  - Wall time is recorded. A candidate's median wall time over its three runs may not exceed 2× the baseline's, so memory is not bought with pathological slowness.
- Contract (frozen baseline):
  - Before any ignored script changes, vendor its source verbatim into tracked validation fixtures with its SHA256. This covers `extend.py` and the `study.py`/`witness.py` definitions it imports (`ROOT`, `DUMP`, `MAN`, `DT`, `GROUP`, `dump`), and likewise for 3-07.
  - Replay runs with its working directory set to an isolated fixture root (under `output/heavy-job-memory/` or `/tmp`) that reproduces the relative paths the script hard-codes (`output/scratch-3-11/...`, `output/scratch-3-12/...`). The source is not edited. The harness refuses to start if the resolved paths reach the real repository `output/`, so a replay can never overwrite `output/scratch-3-12/dump_ext` or `joined_counts.json`. No path normalization of manifests is then needed.
  - Record the baseline source SHA, fixture seed, input hashes, Python and NumPy versions, row and window counts, side and group cardinalities, both peaks, wall time and output hashes.
  - Baseline replay is confined to validation and is not an alternative production implementation.
- Contract (verification):
  - Production paths do not run full-chunk byte assertions, sampled or otherwise.
  - An opt-in `verify` mode of the adapter streams the source and destination in the same bounded windows and checks every byte outside the written flag byte. It keeps the same memory gates as the transformation and is how a full-dump check is run when one is wanted.
- Contract (operation):
  - Every memory benchmark, dump scan or join, K1 run and other heavy task holds the same repo-root `output/.heavy.lock` for its entire process tree, including heavy fixture preparation and validation.
  - Run one worker and one heavy command at a time. Existing caps remain cbuild/make ≤ -j4 and K1/harness ≤ -j6, and they do not authorize overlap.
  - Do not drop caches. Poll file-based exit markers instead of self-matching process loops. If another heavy job is active, wait for it even if it skipped the advisory lock, and never stack a job beside Sol 3-13.
  - Recommended (not mandatory) wrapper: run heavy jobs inside their own `systemd-run --user --scope`. oomd then kills the job's scope rather than a terminal or browser, and the job's `memory.peak` and pressure stay attributable. An optional per-job `MemoryHigh=` throttle is documented, but no machine-wide cap is imposed.

## Architectural Implications

- This is an offline analysis and storage change. The full-Australia deliverable, schema facts, build oracle and C-first kernel boundary do not change. The `_finalize_dump` change preserves dump bytes and order exactly. Range/window orchestration and the existing vectorized operations remain the established approach, with no new per-record Python algorithm.
- Phase 4 adds the bounded dump-reader boundary, write-behind, memory-accounting limitations (RSS vs cgroup charge vs PSS) and the oomd failure mode to `docs/ARCHITECTURE.md`. It consolidates lock guidance currently scattered through plan04 briefs and `docs/provenance.md` into `docs/WORKFLOW.md`. The deferred out-of-core finalizer is recorded there as a known limitation, not as live plan work.
- The scratch scripts are git-ignored and untracked. The production adapters, the vendored frozen baseline and the measurement entry point must be tracked, so landing on master includes a reviewable and replayable fix rather than only local scratch edits. Never force-add generated dumps or witness datasets.
- Execution coordinates ownership with the active plan04 worker (3-13 re-runs `k1_triage.py classify` and reads `scratch-3-12`) before changing shared scratch entry points or `k1_triage.py`. Inputs may be read outside protected paths. `output/scratch-2-07`, `output/scratch-3-06` and `output/scratch-3-11/G` remain untouched. Use fresh plan-specific output under `output/heavy-job-memory/` or `/tmp`.

## Decisions

Headless: every scope question is ledgered below. Four phases in the stated order, all **known**. Each fits one worker and skips `refine`, and `execute` briefs each inline. Delivery now is design only: no implementation, benchmark or commit. The orchestrator lands reviewed changes on master after the adversarial pass. No `PROVENANCE.md`.

## Assumption Ledger

### Assumption 1 — Layout compatibility

- Question: Are the 144/152-byte dump layouts fixed, and is byte146 always padding?
- Answer chosen: Support the observed 144-byte base and 152-byte extensions with checked manifests and descriptors. Byte146 can be written only in the validated residual 152-byte input. Reject incompatible layouts before writing.
- Rationale: 3-07 uses byte144, 3-08 uses byte145 and 3-12 uses byte146. A blanket raw-copy policy would change 3-07's padding semantics.
- If wrong: add a separately specified layout adapter and equivalence case before accepting that layout. Do not infer new offsets.

### Assumption 2 — Numeric reduction targets

- Question: What reduction can be promised without an invented machine-wide cap?
- Answer chosen:
  - Phase 1 candidate max RSS and scope `memory.peak` are each ≤ 50% of the frozen baseline on a seeded 1,000,013-row, 152-byte fixture with 216,488 side rows and fixed accounting strata.
  - The candidate's doubled-row run (2,000,013 rows, same side tables and groups) may add no more than one source-plus-destination window on either metric: `2 × 65,536 × 152 = 19,922,944` bytes = 19,456 KiB.
  - Report absolute measured peaks too, and make no unmeasured full-disc claim.
- Rationale: estimated fixture baseline.
  - Max RSS: about 304 MB of touched source and destination mappings, plus side and sort state (tens of MB), the 36.5 MB assertion temporaries and the interpreter.
  - `memory.peak`: about 152 MB of dirty copied output plus anonymous memory.
  - Candidate: about 20 MB of windows, write-behind output, and the same side state.
  - Both 50% gates hold even if fixed costs are double the estimate. At full scale the baseline file term grows to about 4.7 GiB while the candidate's stays near 20 MB. 50% is a conservative, testable floor, not a measured claim. The cgroup gate exists because RSS alone would pass a candidate that still dirties the whole output in the page cache.
- If wrong: a failed gate is a failed phase. Inspect native allocations and residency and correct the implementation. Any revised target needs a ledger amendment with evidence, not a silent pass. Large real side and group populations still require measured reporting.

### Assumption 3 — Shared helper scope

- Question: Is a shared streaming join/helper worth including, or should everything remain local?
- Answer chosen: Phase 1 proves the local residual fix first. Phase 3 extracts only bounded I/O and uses separate transformation adapters for 3-07 and the `k1_triage` readers. Defer broad parser readers and any external sort.
- Rationale: these surfaces share storage pressure but not join or witness semantics.
- If wrong: widen the design through an explicit phase-count or scope decision. Do not sneak an external sort or witness rewrite into Phase 3.

### Assumption 4 — Assertion and semantic proof policy

- Question: May production byte assertions be removed or sampled, and is a bounded proof enough to land?
- Answer chosen:
  - Remove the full-chunk production byte assertions outright. Sampling is not used, because it adds a code path without adding proof.
  - Keep layout, length and error checks and meaningful aggregate assertions (3-07's match count).
  - Provide an opt-in bounded streaming `verify` mode for whole-file checks.
  - Validate every output byte on bounded fixtures against the vendored baseline, including unchanged padding and NaN payloads. The bounded proof closes the phases.
- Rationale: the windowed candidate copies source windows and writes one column, so the invariant is structural. Exact bounded equivalence covers the copy semantics better than runtime sampling, and a streaming verifier keeps validation from becoming the new peak.
- If wrong: require a full-dump comparison (Assumption 10) before landing. Never equate sampled validation with a byte-identity proof.

### Assumption 5 — Duplicate keys, casts and accounting

- Question: Can joins assume unique side keys, normalize key casts, or use residual membership to limit flag writes?
- Answer chosen: none of the three. Preserve each script's sort and leftmost-match policy and its narrowing field-assignment cast. Equivalence cases include conflicting duplicate statuses and side keys that only collide after the `i32`→`u8`/`u16` wrap. Residual assignment affects counts only in 3-12.
- Rationale: these are observable current behaviors, and changing any of them could alter byte146 or the counts.
- If wrong: uniqueness or range validation may become a validated precondition in a separate contract change. Restricting flags requires explicit semantic authorization.

### Assumption 6 — Reproducibility, baseline isolation and scheduling

- Question: How do ignored scripts land on master, how is the frozen baseline kept durable and safe, and may small bounded proofs overlap active jobs?
- Answer chosen:
  - Tracked adapters and harness preserve runnable source, and the scratch entry points use them.
  - The baseline is vendored verbatim, with its imported definitions, into tracked fixtures. It is replayed in an isolated working directory that refuses to resolve into the real `output/`.
  - Treat these native-memory benchmarks as heavy even though they are bounded, and run them serially under the lock after the active job exits.
  - Documentation goes in the existing stable docs, not a new scheduler service.
- Rationale: local ignored edits are not a durable fix. The scripts' hard-coded relative paths would overwrite the live `scratch-3-12` outputs if replayed from the repository root. An advisory lock cannot control an already-running job that does not take it.
- If wrong: an explicitly chosen tracked research-script location can replace the adapter surface before execution. Different overlap rules need measured host headroom and a new decision.

### Assumption 7 — Empty-file compatibility

- Question: Should zero-row mapped kinds gain successful handling when the current `np.memmap` entry points reject them?
- Answer chosen: no. Preserve rejection of zero-length mapped kinds, checked without writing outputs. Exact successful-output equivalence applies to the baseline's nonempty supported inputs, and empty-file cases prove rejection separately. Empty or missing side tables remain supported where the current residual script supports them.
- Rationale: the first adversarial pass found that an empty-kind success case would extend behavior beyond this memory-only contract. It cannot be claimed as byte equivalence with the frozen baseline.
- If wrong: explicitly authorize the empty-output behavior, define its manifests, counts and symlinks, and validate the expected results separately from the failing baseline.

### Assumption 8 — Which memory metric represents the OOM risk

- Question: Is `/usr/bin/time -v` maximum RSS the right gate, given that the kills come from oomd pressure?
- Answer chosen: not on its own. Gate on both max RSS and the per-worker cgroup `memory.peak`, and report `anon`/`file`/`file_dirty` and the PSI totals. Docs recommend per-job transient scopes. Max RSS stays because the intent names peak RSS and it captures whole-file mapping residency. `memory.peak` captures dirty page cache that RSS cannot see, such as the 2.34 GiB `copyfile`.
- Rationale: RSS counts touched clean file pages that are cheap to reclaim, and does not count unmapped dirty page cache. oomd acts on pressure from both. A fix that only shrinks RSS could leave the kill trigger in place.
- If wrong: if `memory.peak` proves too noisy between paired runs (spread over 10% of baseline), gate on `anon + file_dirty + file_writeback` sampled at ≥ 100 Hz instead, and amend this entry with the measured spread.

### Assumption 9 — 3-08 preparation and the K1 dump finalizer

- Question: Does `prepare_dump.py` belong in scope, and should `_finalize_dump` stay deferred?
- Answer chosen:
  - Drop `prepare_dump.py` from the change set. It materializes only kinds of 739, 824 and 1 rows and symlinks the background files, so a 1,000,013-row gate for it would measure a fixture that cannot occur.
  - Bring `_finalize_dump`'s copy removal into scope as Phase 2. Byte-identical order is still required and the out-of-core sort stays deferred.
- Rationale: the finalizer holds about 3 full copies (≈7 GB for `background_boundary`) after the sampler stops. It is tracked production code on the K1 dump path, the cut needs no new algorithm, and leaving it out would leave the largest anonymous spike of the stated heavy-job class in place.
- If wrong: if the finalizer change cannot keep byte-identical output with a stable sort, revert that phase to a documented limitation and stop. Do not substitute a different ordering.

### Assumption 10 — Full-dump confirmation

- Question: Is a full-scale run part of acceptance?
- Answer chosen: no. Before Phase 1 changes the scratch entry point, the executor may record the SHA256 of the existing `output/scratch-3-12/dump_ext/*.bin` under the lock. That hash is a supplementary oracle for a later full candidate run written to a fresh directory (never `dump_ext`) or for a streaming `verify`. It is evidence only, not a phase gate.
- Rationale: the existing output was produced by the baseline script, but it lives in an ignored and mutable directory and is 2.5 GB. Gating on it would require heavy runs, and in-vehicle and full-scale checks are last-mile.
- If wrong: make the full-dump hash equality a Phase 1 gate, run serially after 3-13 exits.

## Open Questions

None block the headless design. Actual peak values, the noise between paired cgroup runs, whether a full-dump replay is safe, and the overhead that depends on side and group cardinality are execution evidence, not grounds to run a job during design.

## Phases

The union of these outcomes is acceptance. Count and order are fixed at headless sign-off, and the approach is known throughout.

Rules that apply to every phase's evidence:

- All evidence runs are bounded and serial under the heavy lock, each worker in its own transient scope.
- Baseline and candidate use identical fixture files, the same installed environment, fresh workers and the same pre-read input cache state.
- Repeat three paired runs and publish every peak (max RSS and `memory.peak`). Each reduction gate must hold for every pair, not just on average.
- Construct fixtures that satisfy the original aggregate assertions. Grow the 3-07 fixture with zero-flag rows so its unchanged side-table row weights remain valid.
- Cardinality includes every persistent key and pair population, not just the accounting strata.
- Generated fixtures are deterministic and independent of local witness datasets. The vendored baseline checksum freezes the oracle against later scratch edits.

### Phase 1 — Residual extension cuts peak memory with identical bytes

- Outcome:
  - Running the residual extension entry point with its defaults, in an isolated fixture root, produces dump bytes, manifest and joined counts identical to the vendored baseline.
  - On the bounded 1,000,013-row fixture, its max RSS and scope `memory.peak` are each at most half the baseline's, and the doubled-row run meets Assumption 2's growth bound on both metrics. Median wall time is within 2× of the baseline's.
  - Preservation is proven by exact SHA256 equality of every produced dump, manifest and counts file, plus the bounded `verify` mode.
  - Cases cover status 0/1, exact misses, missing and empty side tables, duplicate keys with conflicting statuses, side keys that collide only after the narrowing cast, assignment 65535 and non-residual rows, nonzero padding and NaN payloads, and final partial windows.
  - Empty mapped kinds prove rejection by both baseline and candidate separately.
  - Window sizes of 1, 65,536 and one that does not divide the row count give identical bytes.
- Surfaces: `output/scratch-3-12/extend.py`; new tracked `parser/tools/dump_join.py`, `parser/tools/bench_dump_memory.py` and `parser/tests/test_dump_join_memory.py` with the vendored baseline fixture; `parser/perf_inventory.json` and its existing inventory gate.
- Approach: known. Per-window mappings or `pread`/`pwrite`, view lifetime control, write-behind with cache drop, no whole-file copy, and no production assertions. Keep the existing key join and sort call.
- Depends on: nothing. Baseline vendoring and measurement belong to this phase, not to a preliminary phase that would delay the first cut.
- Refine: skipped. One worker carries the local transformation and its evidence.
- Units:
  - `briefs/1-01-extend-residual-bounded-io.md` — single unit, no parallel units.

### Phase 2 — K1 dump finalizer drops redundant full copies

- Outcome:
  - Calling `_finalize_dump` directly on a deterministic bounded set of per-task part files produces the same per-kind `.bin` bytes, manifest bytes, returned counts and part deletion as the frozen pre-change function. No K1 run is involved. The parts are 1,000,013 rows of `cenc.K1_DUMP_DTYPE` spread over at least 8 parts, with duplicate sort keys whose stable order is observable.
  - The fresh-worker max RSS of the finalization is lower than the baseline's by at least one full array of the fixture (row count × itemsize, in KiB), in every paired run.
  - The existing quantisation dump tests pass.
- Surfaces: `parser/tools/quantisation_roundtrip.py` (`_finalize_dump` only), `parser/tests/test_quantisation_roundtrip.py`, `parser/tools/bench_dump_memory.py`.
- Approach: known. Read parts into one preallocated array and release them as they are consumed, keep the identical stable `argsort(order=DUMP_ORDER)` permutation, and write the gathered rows without `tobytes()`.
- Depends on: Phase 1 (harness).
- Refine: skipped. One worker, one function.

### Phase 3 — 3-07 extension and triage use the proven storage boundary

- Outcome:
  - The 3-07 extension entry point and triage `summary`, `classify` and `enumerate` produce bytes and artifacts identical to the baseline on bounded supported fixtures across window splits. Zero-length mapped kinds prove rejection separately.
  - The 3-07 fixture includes its 144→152 padding policy, scope and narrowing cast. Triage preserves group aggregation when a group straddles windows, and preserves first-match rule precedence.
  - The 3-07 adapter and each triage command reach ≤ 50% of the baseline's max RSS and `memory.peak` on their own 1,000,013-row fixed-cardinality fixture.
  - Doubling rows, with every retained key and pair population held fixed, adds at most one source-plus-destination window for that layout: 18,944 KiB for 144→152 and 9,728 KiB for read-only 152-byte triage.
  - Additional bounded high-cardinality triage fixtures, with late first appearances and groups spanning windows, produce identical artifacts and candidate peaks no greater than their paired baselines.
  - Retained aggregation keys do not own whole chunk or unique-array backing storage. Every retained-state cardinality and absolute peak is reported, and this gate does not imply a bound on arbitrarily many groups.
  - Phase 1's byte and memory gates still pass after extraction.
- Surfaces: new `parser/kiwiw/dump_io.py`; `parser/tools/dump_join.py`, `bench_dump_memory.py`; `output/scratch-3-07/extend_dump_attempt3.py`; `parser/tools/k1_triage.py`; `parser/tests/test_dump_join_memory.py`, the existing `test_k1_triage.py`, `test_k1_dump.py` and `test_perf_inventory.py`; `parser/perf_inventory.json`. `prepare_dump.py` and `finalise_rules_side.py` are unchanged compatibility consumers.
- Approach: known. Extract the proven I/O boundary, keep transformation-specific sorts, casts, padding and aggregation, and keep the C-output ownership copies.
- Depends on: Phase 1.
- Refine: skipped. One worker owns the helper extraction and its consumers in sequence.

### Phase 4 — Heavy-job commands reproduce the memory proof serially

- Outcome:
  - Stable docs give one repo-root lock path, the recommended per-job transient-scope wrapper, one-worker bounded benchmark and replay commands, and how to interpret KiB RSS against `memory.peak`.
  - They also record fixture and hash provenance, the measured Phase 1–3 peaks and the limitations.
  - Following the documented commands reproduces their memory and byte-equivalence gates.
  - While a bounded worker holds the lock, a second non-blocking probe fails to acquire it, and acquisition succeeds after the worker exits.
  - The docs explain the oomd pressure failure mode, whole-file mmap and dirty page-cache residency, view lifetimes, side and group memory, and the deferred out-of-core finalizer.
  - Existing build, kernel and PSS contracts remain intact.
- Surfaces: `docs/WORKFLOW.md`, `docs/ARCHITECTURE.md`; the existing bounded harness only if command ergonomics require adjustment. Phase evidence belongs to the execute record, not to a new provenance file.
- Approach: known. Consolidate the existing flock discipline and publish the proven commands and results. No scheduler, no daemon and no mandatory memory cap.
- Depends on: Phases 1–3.
- Refine: skipped. One worker carries the documentation and the bounded command verification.

## Provenance Notes

Ground locations:

- `extend.py:10–32`: whole-file copy, whole-output initialization, join and byte assertions.
- `study.py:7–12`: hard-coded relative `DUMP`/`ROOT`, manifest-derived `DT`, and the `GROUP` import from `scratch-3-07/witness.py:17`.
- `extend_dump_attempt3.py:14–36`: layout, stable join and normalization.
- `prepare_dump.py:13–20`: byte145, symlinks and small-kind preparation.
- `k1_triage.py:29,62–76,251–299,414–447,519–530`: layout, chunk readers and consumers.
- `quantisation_roundtrip.py:1350–1384,1505–1513`: the finalizer, which runs after `sampler.stop()`.

Other facts from Ground:

- The side tables are `i32` keyed, with 78-byte rows.
- The triage group, source and composite key widths are 36, 40 and 64 bytes, in addition to the sort indexes and masks.
- `parser/kiwiw/spool.py:436–443` already uses `pread` to avoid multi-GB mapped-page RSS.
- `cenc.py:889` copies a reusable C buffer to establish ownership and must not lose that protection.
- The oomd kills on 2026-09-26 and 2026-10-02 are recorded in the user journal.
- Lock precedent: plan04 briefs and `docs/provenance.md`.

Avoid: Python-object profilers as the primary metric, cache dropping, a blanket raw-byte copy across different layouts, and a smaller chunk size as the sole answer to full-file residency.

The first clean-context adversarial pass found no critical issue and two high findings:

- Triage key and pair cardinalities were omitted, and structured scalars were keeping unique-array storage alive. The design adds independent aggregation-key ownership, scaling across all cardinalities and high-cardinality proof cases.
- Successful empty-kind equivalence against the current scripts is impossible. Assumption 7 keeps empty-file rejection instead of adopting that reviewer's proposed compatibility expansion.

The second (Opus) adversarial pass made these changes:

- Re-grounded the failure mode as oomd pressure kills and added the cgroup `memory.peak` gate and write-behind (Assumption 8).
- Isolated the vendored baseline replay from the live `scratch-3-12` outputs (Assumption 6).
- Pinned the narrowing key cast (Assumption 5).
- Replaced assertion sampling with a streaming `verify` mode (Assumption 4).
- Dropped the memory-irrelevant 3-08 surface and brought the finalizer's copy removal into scope as Phase 2 (Assumption 9).
- Added a wall-time guard and a supplementary full-dump hash (Assumption 10).
