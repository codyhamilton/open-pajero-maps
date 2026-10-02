# Review: brief 1-01 (residual extension, bounded windowed I/O)

Verdict: ACCEPT

## What I re-ran
- `sha256sum -c SHA256SUMS` in `parser/tests/fixtures/dump_join_baseline/`: extend.py, study.py and witness.py all OK.
- `.venv-rp/bin/python -m pytest parser/tests/test_dump_join_memory.py parser/tests/test_perf_inventory.py -q`: 17 passed. The suite includes the baseline-replay vs candidate equivalence on a few-thousand-row multi-kind fixture at window sizes default, 1, 65536 and 997, plus `test_collide_after_wrap`, empty-kind rejection, validation-before-write, verify and corruption, and replay-root refusal. This is my one small candidate-vs-baseline equivalence.
- I did not re-run the 1M measurement. `results.json` and `bench.log` are internally consistent and the harness gates are asserted in code, so a repeat would add little.

## Findings by review bar
1. Semantic equivalence: matches the baseline.
   - The side index is built exactly as the baseline builds it: `sk[f]=side[f]` per field, then plain `np.argsort(sk)` with no `kind=`, then `sk[order]`, then `sf=(status[order]==1)`. Nothing is deduplicated, widened or stabilised.
   - Per-window lookup uses `searchsorted`, a clamped index and an equality compare, as in the baseline.
   - Byte146 comes from the flag alone, and a missing or empty side table gives 0. The tests use random source bytes, so the source byte146 is nonzero and gets overwritten.
   - Bytes 0-145 and 147-151, NaN payloads and padding are copied from the source window verbatim. The tail needs no special handling, because the row size is validated and `size % 152 == 0`.
   - `_count_window` replaces `np.unique(axis=0)` with a packed int64 key (`level<<32 | code&mask`), with negative codes handled. It creates the same moved/remaining keys, including zero-count ones, and the output is sorted before writing. The counts JSON and stdout are byte-identical in the tests.
   - The test asserts that the non-stable argsort differs from a stable one, so tie order is actually exercised.
2. Streaming write: correct.
   - Each kind uses `pread` into one reusable bytearray window and a `pwrite` to an `O_TRUNC|O_NOFOLLOW` private file.
   - There is no copyfile and no memmap.
   - `sync_file_range` is issued per window, then the previous window is waited on and dropped with `posix_fadvise(DONTNEED)`, and the source and assignment windows are dropped too. Final `fsync` and a length check follow.
   - The production path has no `array_equal`. The only `array_equal` calls are in `--verify`, and they run per window.
   - Window-size independence is tested.
   - Views are released with `del` and `.release()`.
3. Measurement validity: supported.
   - The workers are fresh processes inside `systemd-run --user --scope`, wrapped in `/usr/bin/time -v`.
   - Max RSS comes from `time -v`. `memory.peak`, anon, file, file_dirty and pressure come from a post-transformation self-cgroup snapshot. The snapshot is taken after the transformation, so it is slightly imprecise, but `memory.peak` is a high-water mark and is not affected.
   - The baseline runs in an isolated replay root with a shim witness. `check_isolated` realpaths every path and refuses anything under the real `output/` outside scratch-5-01. The refusal is tested, including a symlink to the real `scratch-3-12`, and the test confirms the real directory was untouched.
   - `bench.log` and `results.json` show:

     | | RSS (KiB) | `memory.peak` (bytes) |
     |---|---|---|
     | baseline | ~422k | ~264.3M |
     | candidate | ~69.5k | ~64.1M |
     | ratio | 0.165 | 0.243 |

   - Baseline `memory.peak` has a 0.02% spread. Baseline wall was 10.77s and candidate wall 3.59s, a ratio of 0.33.
   - The 2M run grew -204 KiB on RSS and +36 KiB on `memory.peak`, against a 19,456 KiB bound.
   - Every pair has equal output SHA256s (the dump bin, manifest and counts) and equal stdout hashes. The verify mode run also passes the memory gates (77.5M RSS, 83M peak).
   - The gates for the half-size bounds, growth, wall, SHA and verify are asserted in `controller()`, and the exit status is 1 on any failure. `bench.EXIT` is 0 and `failed` is `[]`.
   - Minor: the growth gate uses the median 1M candidate as its reference, not the worst. The log shows min/max too, and all variants are far inside the bound.
4. Deviations: acceptable.
   - `--verify-only` is a reasonable addition for checking an existing destination, such as `dump_ext` later. It is opt-in and has its own tests, and a corrupted data, tail or flag byte exits 1 and names the window.
   - `check-root` exposes the refusal as a CLI and is tested.
   - Empty-kind brief contradiction: the baseline fails after `copyfile` through the `np.memmap` ValueError, so partial output is left. The candidate raises in `_plan` before any write, which matches the DESIGN "validation before writing" and Assumption 7. The test asserts both are rejected and the candidate leaves nothing. This is the better reading, and I consider it resolved.
   - The candidate also rejects a manifest `row_size` other than 152, and a destination that is a symlink or the same file as the source. These are stricter than the baseline but harmless.
5. Scope hygiene.
   - `git status` shows only owned paths changed.
   - No file under `output/scratch-3-12`, `scratch-3-11`, `scratch-2-07`, `scratch-3-06` or `scratch-3-07` is newer than the brief, so nothing there was modified.
   - `perf_inventory.json` has both modules as `orchestration`, and the inventory test passes.
   - `docs/provenance.md` has an appended entry covering scratch-5-01 (fixtures, results, bench.log, markers and `dump_ext.sha256`) with reproduce commands.
   - Both the `scratch-5-01` fixtures and `dump_ext.sha256` are present as the provenance entry describes.

## Conditions / notes (non-blocking)
- The orchestrator still owns the scratch switch-over (Assumption 6) after 3-13 exits. A full-dump replay against `dump_ext.sha256` is evidence only.
- `tmp/` and the `bench/fixture-*` directories remain in the git-ignored scratch, and are documented.
