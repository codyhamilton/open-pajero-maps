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

### R-G8-1-e → regenerated

- `run_suite_main.sh`: full `parser/tests` in the main checkout `/home/codyh/workspace/open-pajero-maps` (the primary worktree, `git rev-parse --git-dir` = `.git`; detached at master `d185fb6`, clean before and after), its own `.venv-rp`, `TMPDIR` on disk (`output/tmp-agent`), under the heavy lock.
- Result (`pytest_main_checkout.log`, `.run.json`): **1458 passed, 10 skipped, 1 xfailed, exit 0, 351.8 s**. Skips are environment: R disc not mounted (3), `scratch-3-11/G` absent (3 + 4 e1 spool/manifest). The xfail is `test_known_decline_ring_359` (R-G8-1-d-a). `test_dump_join_memory`: 13/13 PASSED in the same checkout (`pytest_dump_join_memory_main.log`, verbose).
- Interruptions, recorded: the first two launches (17:45, 18:42 AEST) were killed by host reboots at 17:53 and 18:47 AEST (journal: `systemd-reboot`); their partial logs are kept in scratch only. The third launch completed.

### Phase 1 verification

- Entry points re-run: `quantisation_roundtrip.py` (K1@`1cf40f8` and K1@master on `4ed9cd80`), `build_alldata.py --window` on the golden spool, `pytest parser/tests` in the main checkout, `pytest parser/tests/test_bg_eo_stress.py`. Each result above is read from its own output file, not from a report.
- `residuals.tsv`: R-G8-1-b `discharged (superseded-by-proof)`; R-G8-1-c, -d, -e, -h `discharged (regenerated)`; new R-G8-1-d-a `blocks-phase3` (encoder finding, owner Design).
- `artifact_feedback`: not reachable from this harness; no worker reports exist (units implemented directly), recorded per the skill.
- Workers: none (orchestrator-direct units).

### Carried

1. R-G8-1-d-a: the EO face-walk decline (5 / 20,000 seeded rings) is an encoder robustness finding with no AU incidence; a fix needs its own design (Design to own or reclassify).
2. R-G8-1-b per-window boundary counts differ from the 3-13 table (HEAD-checker dump rows vs 3-13 counting); context only, not reconciled.

## Phase 2: 3-17 / 3-15 classify conditions

Evidence folder: `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-17/conditions/` (README indexes every file). Two throwaway worktrees, removed after: `open-pajero-maps-43-k1old` at `1cf40f8` (K1) and `open-pajero-maps-43-cli317` at `ac1a64d` (3-17's commit; `k1_triage.py` / `dump_io.py` as at 3-17, unchanged since `f3def00`, with the zero-row rejection that `8b6eb55` later removed).

### R-G8-4-a → regenerated

- `forced_zero.py`: `dump_raw/completeness.bin` re-hashed `1a91b1c2…`; plan 31 cell list re-hashed `77ff1d86…` (246,123 cells). Side table = plan 28's `per_rule_completeness_mechanism.tsv` with `other_mechanism` set to 0 on every row whose cell is in that list: **34 rows** (O05 code 5 ×30, O04 code 7 ×4), the 3-14 extension's "zeroes it on changed cells".
- `dump_join.py --mode other_mechanism` (unchanged tool) → `dump_forced`; `k1_triage classify` with the completeness rules (identical at `ac1a64d` and master) on both CLIs, and again as the single-kind view of the rebuilt `dump_ext43` (below). All four runs give the same per-row assignment: **776 manifest / 468 assigned / 308 unattributed, PARTITION FAIL (exit 1); O01 checker 363, O04 spool 3, O05 checker 102**, all L0 — the 3-17 figures exactly.
- Per row (`compare.py` → `completeness_forced_assignment.tsv`, committed): versus plan 28's assignment exactly 34 rows change, they are exactly plan 37's 34 forced-zero rows, and each lands on plan 37's predicted 3-17 rule (NO_RULE).
- name_anchor kind view: K1@`1cf40f8` on `4ed9cd80` dumped all five kinds (`k1old_all.json`: completeness 776, name_anchor 1, background family 0). Its fresh `completeness.bin` hashes `1a91b1c2…`, so the retained dump is regenerated byte-identically. The name_anchor row is the plan 29 row (L0 (0,541), leaf [928], raw (0,370), lat −38.7273, lon clamped 90.0; Île Saint-Paul, review 3-08 item 7); its cell is not in the plan 31 changed list, so the 3-14 extension inherited its mechanism byte, O03's `other_mechanism == 6`. `build_ext.py` writes that byte (the inherited value, not a new assignment). View result, both CLIs: **1 row → O03 spool, PARTITION OK for that kind alone** (exit 0).
- Deviation, recorded: the original 3-17 `dump_ext` came from the 3-14 dump extension (lost). `dump_ext43` is rebuilt from committed inputs: completeness from `dump_forced`, name_anchor from the fresh K1 row plus the inherited byte, three zero-row kinds. Its native 144 bytes for completeness are checked equal to the fresh K1 dump.

### R-G8-4-b → regenerated

- Full CLI on `dump_ext43` (zero-row background, background_boundary, interior_cover), rules = `rules_bg` + `rules_other` as at `ac1a64d` (3-17's `rules_all.before.json` shape): **3-17-era CLI exits 1** with `ValueError: …/dump_ext43/background.bin: zero-row kinds are unsupported (as in the baseline)`, no partition — the 3-17 S2a stderr, reproduced (`runs/x_full_at317.{stderr,rc}`).
- For the record, the current CLI on the same dump with master rules exits 1 with a whole-dump partition: zero-row kinds 0/0, completeness 468/308, name_anchor 1/1, PARTITION FAIL (`runs/x_full_cur.*`).

### R-G8-2-f → superseded-by-proof, with a named unverifiable part

- Proven: R-G8-4-a reproduces the 3-17 counts exactly and the per-row delta equals plan 37's 34-row identity, so the forced-zero explanation (34 = O05 30 + O04 4) is proven per row against the plan 31 cell list.
- Not provable: the literal equality of the 3-15 text's `AU.differing_cells.tsv` with plan 31's list. That file was never committed and has no producer in the repo. New child **R-G8-2-f-a**, `unverifiable:never-committed`. Whether it is non-material is Cody's rule to apply; it is listed, not decided here.

### Phase 2 verification

- Entry points re-run: `dump_join.py --mode other_mechanism`, `k1_triage.py classify` (3-17-era and current, whole dump and single-kind views), `quantisation_roundtrip.py` K1@`1cf40f8` with failure dumps. Results read from the run outputs (`runs/*.partition.txt`, `*.cause_counts.tsv`, `*.rc`, `*.stderr`) and `compare.json` (`match_317: true`, `delta_equals_plan37_34: true`, `delta_rule_matches_plan37_prediction: true`).
- `residuals.tsv`: R-G8-4-a, R-G8-4-b `discharged (regenerated)`; R-G8-2-f `discharged (superseded-by-proof)`; new R-G8-2-f-a `blocks-phase3` (named unverifiable, Cody via Design).
- `docs/provenance.md`: `output/scratch-43/` section added.
- `artifact_feedback`: not reachable from this harness; no worker reports (orchestrator-direct units).

### Carried

1. R-G8-2-f-a: listed for Cody's rule (never-committed file; no regeneration path).

## Review follow-ups (terminal review PASS_WITH_FOLLOWUPS, Claude CLI, 2026-10-06 19:23 AEST)

Applied 2026-10-07. Findings F1–F7:

1. **F1 (medium):** opened **R-G8-1-b-a** for the window_before vs 3-13 boundary count mismatch (HEAD-checker dump rows vs 3-13 counting; root cause not named). The after-0 supersession is unaffected. Fill sentence restated below to a single column: `background_type` for fill (matches the 3-13 table for every window that has a fill figure; the 0/291 window's type-291 fill is 62 and all-types 69 = 62 + 7 type-288 R01, as the 3-13 text notes).
2. **F2 (low):** R-G8-1-d-a reworded to "decline site located (`:885`; arms not split)". Committed `decline_locus.py` / `decline_locus.json` (3/5 rings pin `:885` under instrumentation; all 5 size -1 uninstrumented). Build-error cites `_cenc.c:1070`, `_e2.c:48`. "No AU input" scoped to built spools.
3. **F3 (low):** R-G8-2-f reworded to "plan 37 identity re-executed through the classify CLI; consistent". R-G8-4-a notes "premise shared with R-G8-2-f-a".
4. **F4 (low):** `build_ext.py` and this record cite `cause_table.md:36` as the source of byte 6; S2e verifies CLI on an inferred byte.
5. **F5 (low):** 3-14 conditions README notes the k1head rename, the misleading `W` line, the inferred `6a65cf9`, and the single post-both-runs disc hash (17:42).
6. **F6 (low):** stress-test docstring records that the "guard" is the child timeout and that eo_connect's connection branch is not separately asserted.
7. **F7 (low):** provenance and P2 deviations updated below.

### Fill sentence (restated, F1)

Per-window fill from `window_before.json`, column `background_type` (the window's target type code): 32, 62, 32, 23, 17, 0; the three S05 windows 0. The 0/291 window's `background_all_types` is 69 (= 62 type 291 + 7 type 288 R01), matching the 3-13 table's fill 69. Boundary counts remain unreconciled (R-G8-1-b-a).

### P2 deviations (F4, F7)

- Original 3-17 `dump_ext` lost; `dump_ext43` rebuilt (as above).
- S2e name_anchor byte 6 is inferred from `cause_table.md:36` + unchanged cell + extension inherit rule; not recovered 3-17 bytes. The run verifies CLI/rule semantics on that byte.
- Four early `run_p2.sh` steps (full CLI and name_anchor view on the 144-byte K1 dump) exited 2 on missing extension columns; superseded by `run_p2b.sh` on `dump_ext43`. Recorded in the 3-17 conditions README; kept here as a deviation.

## Terminal review

- Seat: Claude CLI clean-context (disclosed; Codex weekly-limited). Verdict: **PASS_WITH_FOLLOWUPS** (`output/scratch-43/review/REVIEW.md`, kept under `triage/independent_reviews/3-14/conditions/review-REVIEW.md` at close-out).
- No blocker or high findings. Follow-ups applied above.
