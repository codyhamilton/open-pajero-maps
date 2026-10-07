# 3-14 review conditions (plan 43 Phase 1)

Evidence for residual rows R-G8-1-b/c/d/e/h. Record: `docs/plans/43-review-conditions-light/IMPLEMENTATION.md`.

| File | Row | What |
| --- | --- | --- |
| `run_k1old_314.sh`, `k1old_314.json`, `k1old_314.run.json` | R-G8-1-c | K1 at `1cf40f8` on `4ed9cd80`, `-j4`, dump off: completeness 776, background family 0 |
| `k1head_314.json`, `k1head_314.run.json` | R-G8-1-b | K1 on `4ed9cd80`, `-j4`, dump off: background family 0. Renamed from the first (cwd-slip) launch of `run_k1old_314.sh` without `--cwd`; the run JSON argv still says `--out …/k1old_314.json`. The log's `W 1cf40f8…` line is the throwaway worktree's HEAD, not the cwd's. The cwd was the master checkout; its HEAD `6a65cf9` is inferred from commit times (design land 17:34, run file 17:37, next commit 17:45), not captured in an artefact. Disc sha was re-hashed once after both K1 runs (17:42), not per run. |
| `disc_sha_4ed9cd80.txt` | b, c | disc sha re-hashed after the runs |
| `window_before.py`, `window_before.json` | R-G8-1-b | pre-3-14 per-window failing rows (context) |
| `../../../../../../parser/tests/test_bg_eo_stress.py` | R-G8-1-d | seeded stress + degenerate/termination/capacity test |
| `stress_characterise_20k.py`, `stress_20k.json` | R-G8-1-d-a | 20,000-ring decline characterisation |
| `run_golden_window.sh`, `golden_window.log`, `golden_window.run.json`, `golden_and_trim.json` | R-G8-1-h | golden shas, regenerated window TRIM lines, full-AU TRIM quotes |
| `run_suite_main.sh`, `pytest_main_checkout.log` (progress dots stripped), `pytest_main_checkout.run.json`, `pytest_dump_join_memory_main.log` | R-G8-1-e | full `parser/tests` in the main checkout at master `d185fb6`; verbose `test_dump_join_memory` there |
| `decline_locus.py`, `decline_locus.json` | R-G8-1-d-a | instrumented decline site: `_cenc.c:885` for 3/5 rings under instrumentation; all 5 size -1 uninstrumented |
