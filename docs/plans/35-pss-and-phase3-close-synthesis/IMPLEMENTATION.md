# Implementation — 35 PSS at ≤ -j6 and plan 04 Phase 3 close synthesis

- Tool: the orchestrator is the Execute background worker. Phase 1 is an
  ops measurement run by Execute under the guard; it has no code unit.
  Phase 2 synthesis uses a Codex seat (if Codex is limited, Execute writes
  it and discloses that) and an independent clean-context review.
- DESIGN landed at `e2a2c71`. Disc in force: `4e6b0de7…`. Perth:
  `04be2f6e…`. Any sha mismatch stops the chain and is reported, never
  re-pinned.
- Scratch: `output/scratch-35/`. Protected inputs: `2ee3456a…`,
  `4ed9cd80…`, `013586b5…`, `4e6b0de7…`, R `8c2d2027…` and the spool, all
  hashed before and after by the plan-34 `snapshot` gate.
- No brief 3-90 execution and no "3-90" record. `-j` never exceeds 6. The
  ceiling of 9,726,501 kB stays as signed.

## Phase 1 — Ops and build gates measured on 4e6b0de7

Commands: `commands.md`. The chain `output/scratch-35/run_p1.sh` (log
`run_p1.log`) runs serially, each step under `run_heavy_python.py` and
`output/.heavy.lock`. The full `parser/tests` run is a separate guarded step
after plan 37 Phase 2 (`test_perf_inventory`) lands.

### Phase 1 measured (11:05:40–11:21:35 AEST, HEAD 9c99dcb) — evidence/

All wrapper exits 0; summary `evidence/p1_summary.json`, per-step wrapper
logs `evidence/runs.json`, chain log `evidence/run_p1.log`.

| Gate | Result |
|---|---|
| K1 `-j6` ×3 on 4e6b0de7 | PASS, failing 0 in each; wall 79.887 / 79.485 / 79.661 s (median **79.661 s** ≤ 120); `pss_peak_kb` 7,549,093 / 7,555,806 / 7,599,962 (max **7,599,962** ≤ 9,726,501) |
| K1 `-j1` determinism | PASS, failing 0; wall 417.7 s; report identical to all three `-j6` reports and the dump run after `strip_compare_excludes` (excludes `timing`, `wall_s`) |
| Empty census | `--dump-failures` counts 0 for background, background_boundary, completeness, interior_cover, name_anchor; every kind in totals failing 0 (range 285,809,587, step 227,935,489, background 176,386,506, background_boundary 64,111,046, road_node 42,994,980, name_anchor 2,317,055, completeness 1,800,514, interior_cover 1,590,566 checked; road_point 0 checked) |
| AU rebuild `-j4` | `G_rebuild` sha256 **4e6b0de785bdf454…c448** = oracle in force |
| Perth `-j1`, `-j4` | both **04be2f6e0e700ee6…b728** = pin and `scratch-29/perth_base` |
| Protected | `protected_before.json` == `protected_after.json` (4e6b0de7, 2ee3456a, 4ed9cd80, 013586b5, R 8c2d2027, spool fingerprint 328c064e… over 14 files); Perth `da13a775` and `04be2f6e` also hashed at 11:35, unchanged |
| Full `parser/tests` | pending — separate guarded step after plan 37 Phase 2 |
