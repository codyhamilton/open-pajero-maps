# Report: 2-02 — drop-guard accounting fix

Status: **done**. Runner note: the Codex seat for 2-02 hit its usage limit at about 05:11 AEST (it resets at 06:18 AEST). Before that it had added only two test cases to `parser/tests/test_name_drop_guard.py`. Execute (the orchestrator) completed the fix directly, which is a deviation from "Codex for new seats".

What changed:
- `parser/kiwiw/cenc.py`: `E1Spool.name_drops(lo, hi, rect=None)` now reads each name's cell index (`idx` int32 at offset 48, via `self.xs`) and counts only out-of-span names inside the build window rect. Defect 2 is fixed: a window away from L0 (0,541) counts 0 and does no probe.
- `parser/build_alldata.py`: the E1/E2 job tuples carry `cell_range = _combined_cell_range(...)` as a trailing element. The E2 stats `s1` are captured before the probe, so the probe's `cenc.e2` call is no longer counted by the bench or the wiring (defect 1).
- Defect 3: the 9 synthetic names in the `test_build_wiring` fixture (lat −1 / lon 1) are genuinely out of span. The fixer's test asserts that `assign_to_parcel` returns None for them; it passed. No guard change was needed.
- Execute fixed the fixer's test setup: `SpoolWriter` has no `append`.

Check output:
- `test_name_drop_guard.py` + `test_build_wiring.py`: 12 passed.
- The new windowed-zero case was not run against pre-fix code. It is expected to fail there by reasoning, because pre-fix `name_drops` ignores the window.
- Perth window build (`output/scratch-29/run_p2b.log`): every level drops 0. `perth_new` sha `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728` equals the pre-plan-29 baseline `perth_base` (built at `cc96570`).
- AU re-encode with the fixed code: `output/scratch-29/G_verify/ALLDATA.KWI` sha `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae` equals `G_new`. L0 drops 1, other levels 0, 110.9 s, peak 4.49 GB under the guard.
- Full parser suite (`output/scratch-29/runs/p2_parser_tests2.json`): 1 failed / 1060 passed / 7 skipped. The only failure is the pre-existing `test_perf_inventory`; the two guard-caused failures are gone.
