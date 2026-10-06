# Plan 43 implementation record

Run identity: Execute seat (Grok Bot executor, Cursor session), started 2026-10-06 17:35 AEST. Design landed at `616fe4c` (draft read at `6538530`). Master direct. Refine skipped per Decision 1; each phase is one unit implemented directly by the orchestrator (no worker ran; small bounded units with the design hot). Heavy runs serial under `flock output/.heavy.lock` via `run_heavy_python.py`, `-j4`. Reviewer seat for the terminal review: Claude CLI clean context (disclosed; Codex weekly-limited until 2026-10-10 11:50 AEST).

## Phase 1: 3-14 conditions b, c, d, e, h

Evidence folder: `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-14/conditions/` (README there indexes every file).

### R-G8-1-c → regenerated

- `run_k1old_314.sh`: K1 built at `1cf40f8` (pre plan 14 completeness rule, the K1 plan 39 P1 used for `k1old_pre311.json`), throwaway worktree `open-pajero-maps-43-k1old` (removed after), disc `scratch-14/G_new/ALLDATA.KWI`, sha `4ed9cd80…` re-hashed after the run (`disc_sha_4ed9cd80.txt`), spool `extract_timing/spool`, `-j4`, dump off. Wrapper `--cwd` = the worktree (`k1old_314.run.json` `cwd` field).
- Result (`k1old_314.json`): background 0 / 176,386,506; background_boundary 0 / 64,111,046; interior_cover 0 / 1,590,566; completeness **776** / 1,800,514; name_anchor 1 (the known plan 29 row, outside this claim). S02–S05 kinds 0, R01 population 0 (background failing 0), completeness exactly 776. Wall 109.6 s.
- Deviation, recorded: the first launch omitted the wrapper's `--cwd`, so the child ran from the wrapper's repo (master `6a65cf9`), not the worktree; it reported completeness 0 (the current representability rule). It was kept as a HEAD K1 run, not as the old-rule result (`k1head_314.json`, `k1head_314.run.json`, `cwd` field = master checkout); it is used for R-G8-1-b below.

### R-G8-1-b → superseded-by-proof

- Claim (3-14 review b4): the nine 3-13 CF windows clear target residuals to 0 on the original spool under the 3-14 encoder.
- Proof: whole-disc K1 on the 3-14 disc `4ed9cd80…` (built by the 3-14 encoder from the original spool), background / background_boundary / interior_cover failing 0. Two runs: plan 39 `historical_bg/p1/k1_314.json` (HEAD K1; the report itself carries no sha; its run script `historical_bg/p1/run_k1.sh` binds the path, and the path held `4ed9cd80` at plan 39's close, `historical_bg/protected_after_39.json`), and this plan's `k1head_314.json` (HEAD K1 `6a65cf9`, `-j4`, dump off, same path, sha `4ed9cd80` re-hashed right after: `disc_sha_4ed9cd80.txt`). Identical per-kind totals. The nine windows are subsets of the disc.
- Context (not required for the after-0 claim): `window_before.py` → `window_before.json`, pre-3-14 failing rows per committed window from plan 39's keyed arrays (`output/scratch-39/keep/`, 87a01b14 basis; no window overlaps the 37 3-11 cells, so these equal the 013586b5 counts). Fill counts equal the 3-13 table exactly (32, 69 = 62 type 291 + 7 type 288 R01, 32, 23, 17, 0; the three S05 windows 0). Boundary counts are higher than the 3-13 table (403 vs 255, 1,224 vs 829, 117 vs 90, 191 vs 60, 108 vs 108, 264 vs 132, 452 vs 196, 304 vs 132, 120 vs 120): HEAD-checker dump rows vs the 3-13 report's counting; not reconciled, context only.

### R-G8-1-d → regenerated, with a finding

- `parser/tests/test_bg_eo_stress.py` (tracked): seed 4314, 1,000 random self-crossing rings (each checked to have a proper self-crossing) against the `bg_shape` probe (`fixtures/bg_eo/probe.c`), rect [0,0,4096,4096]; per ring: termination (the probe runs in a child process with a 600 s timeout), size within room, the blob parses exactly, record count equals parsed polygons, every vertex inside the rect, 80 parity queries away from the outline, and a capacity check (room one byte short returns -2, then the retry is byte-identical). Ten explicit cases: collinear, zero-area retrace, repeated vertices, touching the leaf edge, on the leaf edge only, single point, spike outside the rect, island-hole-island and nested bowties (components that never meet the rect edge, i.e. the `eo_connect` path), and many coincident retraces.
- Result: 10 explicit cases pass; the seeded run passes every check except **one decline**: ring 359 returns -1. Root cause located: the EO face walk in `eo_clip` meets an already-used half-edge and the guard "never close a partial walk with a chord" (`_cenc.c:885`) declines. It terminates. In production a decline becomes an E2 "declined" row, which the build treats as an error; every AU build has completed, so no AU input reaches it. Characterisation (`stress_characterise_20k.py` → `stress_20k.json`): 5 declines in 20,000 seeded rings (0.025 %), all -1, no parity, bounds or capacity failure in 1,594,246 queries.
- Test shape: the seeded test asserts the decline set is exactly `{r359}`; `test_known_decline_ring_359` is `xfail(strict=True)`, so a fix or a new decline trips the suite. This is a test, not a fix: new named residual **R-G8-1-d-a** against the encoder.

### R-G8-1-h → regenerated

- `golden_and_trim.json`: current golden `l0_divided_trim_halo` file shas and sizes (`frames.bin` `905d9c95…`, 310,268 B; mtime 2026-10-03 06:36 AEST, the post-3-14 recapture).
- Lost `finish_gates.log` window numbers regenerated: `run_golden_window.sh` rebuilds the golden window (L0 cell (1755,591), from the golden's fixture spool) at master `6a65cf9`: `TRIM road: dropped 207/1,083 (19.114%)` and `TRIM background: dropped 227/8,824 (2.573%)`, exactly the cited lines, and the frames are byte-identical to the golden (`golden_window.log`).
- Full-AU absolutes: the cited plan 36 logs are scratch; the six lines (pre-3-14 and at-3-14 L8 road 308/14,012, L0 road 207/3,015,057, L0 background 227/11,029,580) are now quoted in `golden_and_trim.json` with the log's sha.
- `scratch-3-12/G_build.log`: absent; citation dropped. The before-3-14 L8 line is carried by `output/scratch-3-11/G_new_build.log:10` and the E_pre314 log line.
