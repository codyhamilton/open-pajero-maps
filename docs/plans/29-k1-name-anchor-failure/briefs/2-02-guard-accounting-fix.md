# Brief: 2-02 — drop-guard accounting fix (fresh fixer)

Consumer: Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`.
Owned paths: `parser/build_alldata.py`, `parser/kiwiw/cenc.py`, `parser/tests/test_name_drop_guard.py`. Touch nothing else (in particular, do not edit the failing tests named below; they are the contract).
Commits: leave changes in the working tree. Execute commits.
Report: write `docs/plans/29-k1-name-anchor-failure/reports/2-02-guard-accounting-fix.md` (rubric `/home/codyh/workspace/workflow-plugin/tools/quality/checks/execution-report.json`).
Depends on: 2-01 (uncommitted in the tree: route (a) guard in `build_alldata.py` / `cenc.py`; see `reports/2-01-drop-guard-successor-oracle.md` and `phase2_routes.md`).
Budget: about 10 files to read, about 120 lines to change, 60 tool turns.

## Required reading

1. `docs/plans/29-k1-name-anchor-failure/phase2_routes.md` and `reports/2-01-drop-guard-successor-oracle.md`.
2. `git diff parser/build_alldata.py parser/kiwiw/cenc.py`: the 2-01 guard, including the probe-and-pad block in `_e2_job` and `E1Spool(guard_names=True)` / `name_drops`.
3. `parser/tests/test_build_wiring.py` (`test_e1_e2_once_per_range`, `_build`) and `parser/tests/test_bench_record.py` (`test_bench_output_byte_identical_to_unbenched`).

## Defects (measured by Execute, full suite 2026-10-06 05:05)

1. **Bench call accounting.** `test_build_wiring.py::test_e1_e2_once_per_range` fails with `calls.e1 == calls.e2 == ranges`, 1 ≠ 2. `test_bench_record.py::test_bench_output_byte_identical_to_unbenched` fails with 189 ≠ 190. In both, the probe `cenc.e2(...)` on the unfiltered spool in a chunk with drops is counted as a production E2 call/range. Exclude the probe from the e1/e2 stats deltas. Recording it under a separate counter is allowed. The tests must pass unedited.
2. **Drop count is not window-correct.** The Perth-window build in `test_bench_record` (an L0 rectangle inside Perth, rows about 839..887) prints `level 0: out-of-span names dropped: 1`, but the only out-of-span name in the in-force spool is at L0 cell (0,541), outside that window. The count, and the probe trigger, must reflect only names in the cells/rows actually encoded by that build or range. The full AU build must still report exactly L0 1 and every other level 0. The manifest key `out_of_span_names_dropped` is unchanged in shape.
3. **Verify the synthetic drop in `test_build_wiring`.** That fixture build prints `level 6: out-of-span names dropped: 9`. Establish whether those 9 synthetic names are genuinely outside the plan-18 lattice span (`assign_to_parcel`/mesh twin → None). If they are in span, the guard is wrong: fix it and say so. If they are genuinely out of span, state the evidence in your report.

## Constraints

- **AU output bytes:** for the in-force spool, the encoded bytes must not change. Execute re-encodes and requires sha `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`. If your fix must change bytes, stop and report why.
- **No behaviour change for builds with zero in-window drops.** No probe, no padding, and output identical to pre-plan-29 code.
- **Heavy-run rule:** you may run only these, with `--basetemp output/scratch-29/tests/fix`:
  - `parser/tests/test_name_drop_guard.py`;
  - `parser/tests/test_build_wiring.py`;
  - `parser/tests/test_successor_oracle_tools.py`.

  Do **not** run `test_bench_record.py` (it reads the real spool), any encode, K1, or disc/spool read. List the commands for Execute instead.

## Done evidence

- The two named failing tests: give Execute the command to run them.
- `test_name_drop_guard.py`: add a case where a windowed build away from the out-of-span cell counts 0 and performs no probe. It must fail before the fix and pass after.
- `test_build_wiring.py` passes in the sandbox (synthetic).

## Report back

Under 1,000 tokens. Status: `done` | `done with concerns` | `blocked`. Then:
- what changed;
- the before/after test output;
- defect 3's finding;
- the commands for Execute;
- deviations.
