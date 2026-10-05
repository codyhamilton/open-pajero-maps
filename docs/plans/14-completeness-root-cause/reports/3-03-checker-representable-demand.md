# 3-03 — Checker representable demand

Status: **done with concerns**. Implementation and sandbox-runnable validation are complete; one required test needs the orchestrator's systemd user scope. All changes remain uncommitted in the working tree.

## Changes

- Independent representability filter in `_k1_cmp.c` and new `parser/tools/k1_representable.py`: EO faces, cell clipping, multiplier-aware densification, ties-to-even rounding, adjacent/closing deduplication, spike removal, and nonzero lattice area. C crossing predicates use lossless dyadic integer grids and `__int128`; Python uses exact Fractions. Neither checker calls encoder geometry code or imports research artifacts.
- Carried spool `b_mult` through C local shapes, tall rows, compaction and selection, Python construction/take/concat/pass-one serialization, and the tall-row dtype/layout assertion. Values below 1 follow the encoder's default to 1.
- Preserved demand branches, demanded-pair counts, sample order and tolerances. Branches (a)/(b) retain shape indices; batched branch (c) retains a marker and resolves its demanding indices only for missing pairs, avoiding a full per-shape centre scan on the normal path.
- Added 15 regression cases: local/tall TOL-only vertical slivers, vertex pokes, representable squares/slivers, a bowtie with exactly one surviving lobe, row-656 densification collapse, multiplier-2 survival, and multiple-demanders positive control.
- `_cenc.c`, encoder paths, other kinds, existing tests, phase artifacts and protected outputs are unchanged.

## Test evidence

Commands used plain `.venv-rp/bin/python -B -m pytest` as amended.

- Before implementation: **6 failed, 9 passed in 1.11 s**. Cases (i), (ii), (v) failed in both local/tall forms; positive controls passed. Log: `output/scratch-14/runs/k1_p3_tests_before.txt`.
- Final new suite: **15 passed in 1.11 s**. Densification cases also prove survival without densification, collapse with multiplier 1, and survival with multiplier 2. Log: `output/scratch-14/runs/k1_p3_tests_new.txt`.
- All five suites, unfiltered: **273 passed, 1 failed in 29.69 s**. Only `test_plan25_memory_guards.py::test_run_heavy_python_records_argv_and_peak` failed: systemd reports “Operation not permitted” connecting to the user scope bus. Log: `output/scratch-14/runs/k1_p3_tests_after.txt`.
- Final five-suite run excluding only that environmental failure: **273 passed, 1 deselected in 23.56 s**. This includes the existing all-kind C/Python equality, completeness sample/partition invariance, dump and remaining memory-guard checks. Log: `output/scratch-14/runs/k1_p3_tests_sandbox.txt`.
- Supplemental independent C/Python footprint probes: **1,950 agreements**, including 1,500 thin/self-crossing cases (228 unrepresentable, 1,272 representable), multiple multipliers and large raw-coordinate translations. `git diff --check` passes.
- Existing-test expectation edits: **none**.

## Orchestrator verification remaining

No live K1, identity diff or live re-encode was run, as instructed. Run the amended brief's commands through `run_heavy_python.py`, one heavy job at a time, K1 `-j6`, encode `-j4`; also rerun the systemd-dependent test outside this sandbox.

Attribution TSV verified: **799 demanders, 776 distinct keys, 776 all-unrepresentable, zero exceptions**. Baseline live completeness is **checked 1,800,514 / failing 776**; expected after is **checked 1,800,514 / failing 0**. Actual after totals are pending. Other live kinds must equal `output/scratch-14/k1_full.json`; fixture equality passed, live equality remains pending.

Expected identity diff against `output/scratch-14/dump_raw/`: **776 removed, zero surviving, zero new keys**. No predicted build-defect candidates. Actual identity diff remains pending.

Expected fresh re-encode SHA256: `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`; fresh re-encode remains pending. Protected discs were hashed before and after implementation and remain:

- `output/scratch-3-11/G_new/ALLDATA.KWI`: `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`.
- `output/scratch-14/G_new/ALLDATA.KWI`: `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.

## Departures and contract discrepancies

The required memory-guard suite cannot fully pass in this sandbox because its user-scope test invokes precisely the systemd facility the amended brief says is unavailable. Its failure is recorded; no test, wrapper or expectation was changed. All other authorized worker work is complete. No agents, commits, live K1 or live re-encode.

The brief retains the original 2-02 count of 432, while binding 3-02 evidence folds row 765 into 2-02 for **433**, giving `776 = 342 + 433 + 1`. The filter and prediction cover all 776 keys; no accounting artifact was edited. No geometry-contract contradiction or new non-trivial out-of-scope code bug was found.
