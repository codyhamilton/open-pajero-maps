# Plan 25 — OOM memory RCA report

## Class

**Leak/spike class:** **inconclusive on killer argv** + **new completeness-path class (capped)**.

- Host: global kernel OOM; `cursor` killed (`oom_score_adj=300`); largest resident was
  `python` **2881900 ≈ 6612 MiB anon** during plan-14 Phase 2 / Flash **2-02** wall-clock.
  Exact argv **not recovered**. Ruled out as the 00:19 resident: finished
  `cell_local_2-01.py` / `proto.py` (earlier PIDs).
- Bounded harness (this plan): windowed `cell_local_2-01.py` with R+G+spool present
  stays **~60–70 MiB** RSS / **~56–60 MiB** `memory.peak` for 8 and 32 seeds — **not**
  the 6.5 GiB pattern. So the completed 2-01 path under plan-25 bounds is not the
  unexplained 6.5 GiB spike; the 6.5 GiB cmdline remains unnamed.

Closed-set labels used: **inconclusive — needs Cody sample** (exact 2881900 argv);
completeness triage path treated as **new completeness-path class** now **named + capped**
via Phase 2b guards.

## Phase 2 harness peaks (Brisbane 2026-10-06)

Lock: `/home/codyh/workspace/open-pajero-maps/output/.heavy.lock` (shared).
Wrapper: `parser/tools/run_heavy_python.py` (flock + `MemoryAccounting=yes`).

| Stand-in | max RSS | memory.peak | anon (cgroup) | wall | log |
| --- | ---: | ---: | ---: | ---: | --- |
| `cell_local --max-seeds 8` | 64.1 MiB (65644 KiB) | 56.2 MiB | ~8.6 MiB | ~1.4 s | `output/scratch-25/runs/cell_local_max8.json` |
| `cell_local --max-seeds 32` | 67.6 MiB | 59.2 MiB | ~8.5 MiB | ~1.5 s | `output/scratch-25/runs/cell_local_max32.json` |

**Published stand-in ceiling (cell_local-class, R+G+spool present):** **512 MiB**
`memory.peak` for `--max-seeds ≤ 64` under the wrapper + flock. Observed peaks are
~8× below that. Full 343/`--all-seeds` is **not** an acceptance gate while HOLD is up.

Nearest plan-05 fixture class: triage/finalize fixtures are different code paths;
no claim that plan 05 alone clears this hold.

## Phase 2b guards landed

1. **`parser/tools/run_heavy_python.py`** — records full argv, wall, max RSS,
   cgroup `memory.peak`; fail-closed if peak missing. WORKFLOW recipe updated.
2. **`parser/tools/whole_file_guard.py`** — refuse whole-file reads ≥ 64 MiB
   (ALLDATA / `level_0.data` cannot be silently `read_bytes`’d).
3. **`cell_local_2-01.py`** — requires `--max-seeds` or `--all-seeds`; strips proof
   coords from RAM after write; batch `gc.collect`; refuses whole-file discs;
   windowed runs do **not** overwrite committed membership TSVs.
4. Tests: `parser/tests/test_plan25_memory_guards.py`.

## Hold-lift criteria (proposed for CHM)

See `IMPLEMENTATION.md`. **This report does not clear the hold.**

### Hold-lift evidence status

| Criterion path | Status |
| --- | --- |
| **(a)** 6.5 GiB path named and capped | **Not met** — argv for 2881900 still unknown |
| **(b)** harness ceiling proof for cell_local-class with R+G+spool | **Met for stand-in** — peaks ≪ 512 MiB ceiling for ≤32 seeds; guards refuse uncapped |
| CHM explicit clear | **Required** — not done by this plan |

Recommend: CHM may clear HOLD for **encode/K1 resume under flock + `run_heavy_python.py`**
once satisfied that (b) + Phase 2b caps are enough operationally; **do not** reseat
plan-14 Phase 2/3 completeness science until CHM says so. Flash seats must use the
wrapper so the next spike has recoverable argv.
