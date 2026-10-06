# Implementation — 41 encoder/build close gates

Master direct. Phase 2 (light) landed before Phase 1 (heavy bench), by queue
order; the design marks both independent.

## Phase 2 — close-gate rule and checker

- **Classification (R-G8-5):** a **repo rule**. The trigger (encoder and
  build surfaces) and the command (`parser/tests` under `.venv-rp`) are
  specific to this repo.
  - The workflow plugin's close-out skill has no suite rule and names no
    project.
  - A generic plugin variant ("run the project's declared full suite before
    closing a phase that touches production code") is routed to the Workflow
    System Manager by the parent. It is not drafted here.
- **Rule:** `docs/WORKFLOW.md` § "Encoder/build close gates (plan 41)".
  - **Trigger:** the design-land..HEAD diff touches any of:
    - `parser/kiwiw/*.c` or `*.h`;
    - `parser/kiwiw/cenc.py`;
    - `parser/build_alldata.py`;
    - `parser/kiwiw/alldata_writer.py`;
    - `parser/kiwiw/disc.py`;
    - `parser/tests/fixtures/goldens/`.
  - **Gates:** IMPLEMENTATION quotes three marker lines before the
    phase-closing commit:
    - (a) the full suite summary line at the HEAD sha, with no failures or
      errors;
    - (b) the encode wall: median of three at `-j4`, spread, baseline;
    - (c) the AU / Perth sha gate.
- **Checker:** `parser/tools/close_gates.py --base <sha> [--head REV] --impl
  <path> [--impl-rev REV]`.
  - Light, no lock: one `git diff --name-only` and one text scan.
  - Output: JSON with the trigger paths, each gate's matched line, the
    missing gates and pass.
  - Exit codes: 0 pass or not triggered, 1 missing, 2 usage/git error.
  - `perf_inventory.json` entry: orchestration.
- **Tests:** `parser/tests/test_close_gates.py`, 9 tests at P2 (19 after the review follow-up):
  - all gates present;
  - a failing or erroring suite line is not gate (a);
  - each gate needs every field (5 cases);
  - trigger patterns;
  - the plan 34 worked example, skipped if that history is absent.

  `test_close_gates.py` + `test_perf_inventory.py`: 13 passed.
- **Worked examples** (`close_gates.py --impl-rev <close>`):

  | plan | base → close | trigger | result |
  |---|---|---|---|
  | 34 | `9fb00da` → `4ab27e8` (P2 close) | yes: `parser/build_alldata.py` | **missing (a), (b), (c)** (exit 1) |
  | 37 | `517781e` → `5facd75` (P2 close) | no | pass (exit 0) |
  | 41 P2 | `6e12b36` → this close | no (docs/tools only) | pass, not triggered (triggered pass: open, P1 close) |

  - **Plan 34:** in substance, (a) was never run (53 restricted tests: the
    missed `test_parcel_mask`), and (b) was not measured at close. The
    successor sha was recorded (`successor_sha.json`, Perth sha) but not as
    a gate line, so (c) is missing by the marker rule.
  - **Plan 41's own triggered-pass example: open, recorded at the P1
    close.** P1 quotes gates (a)–(c) and runs `close_gates.py --base 6e12b36
    --impl-rev <P1 close>` whether or not a fix lands. P1 touches `_cenc.c`
    only if a performance fix lands; if nothing triggers, the P1 close
    records that no triggered-pass example exists yet.
- **Residuals:** R-G8-5 is discharged (repo rule plus checker; plugin
  variant routed). R-G9-4 is owned by plan 41 Phase 1.

### Phase 2 review follow-up

Claude CLI seat (clean context; Codex weekly-limited), review of `ec90121`:
**PASS_WITH_FOLLOWUPS**. The text is kept at `reviews/p2-REVIEW.md`. All six
findings are fixed:

- **F1 (gate (a) accepted restricted, shaless or stale runs).** The
  following are now rejected: `deselected`, a `parser/tests/<file>.py`
  filter, a `-k` filter, and a line with no `at <sha>`. The sha is resolved
  as a commit. It must lie in base..head and be at or after the last
  trigger-surface commit, or the gate reports `stale`.
- **F2.** A gate (c) line with FAIL, MISMATCH or "differs" is rejected.
- **F3.** Gate (b) needs numeric spread and baseline values and `of 3` (or
  more).
- **F4.** Each field is now a lookahead, so field order is free. `sec` is
  accepted and gate (c) is case-insensitive. The **last** marker line per
  gate is the one judged.
- **F5.** The 41 P2 row now says "not triggered; triggered pass open, P1
  close". The P1 obligation is recorded above.
- **F6.** WORKFLOW.md requires `close_gates.py` to exit 0, with its `pass`
  quoted, before a triggered phase closes.
- **Tests:** 19 in `test_close_gates.py`, with new probes for deselected,
  file and `-k` filters, a shaless line, a (c) failure, (b) TBD or `of 1`,
  phrasing freedom with last-line-wins, and sha resolution/stale on a
  temporary git repo. With `test_perf_inventory.py`: **23 passed**.
- **Worked examples re-run:** plan 34 is still missing (a), (b), (c) with no
  marker lines, exit 1. Plan 37 is not triggered, exit 0.

## Phase 1 — wall regression attributed; byte-identical fix; measured floor

All runs used the heavy wrapper and lock (`run_heavy_python.py`), full AU at
`-j4`, on the shared spool. Each commit ran in a throwaway worktree, 3 runs
per commit, and every disc was sha-checked and then deleted.

- **Protected discs:** the snapshot before and after
  (`wall/protected_{before,after}.json`) is unchanged across all 5 entries:
  `013586b5`, `4ed9cd80`, `4e6b0de7`, `2ee3456a` and R `8c2d2027`.
- **Ordering disclosure:** the bench started early while the lock was idle.
  Light work (reviews, witnesses) ran in parallel with some runs. It never
  held the lock, but it may add noise; the spreads are reported.

### Bench table (`wall/bench_table.json`)

Wall is the wrapper `wall_s` of `build_alldata.py` (median of 3). Encode is
the build log's "encode total". L0 is the level-0 encode time.

| commit | what | runs (s) | median | spread | encode | L0 | AU sha (3/3) | Perth warm `-j4` |
|---|---|---|---|---|---|---|---|---|
| `9269ebb` | 3-11 tip | 21.01 / 22.31 / 20.45 | 21.01 | 1.86 | 12.0 | 11.7 | `013586b5` | 5.0 s `da13a775` |
| `33006aa` | pre 3-14 | 20.27 / 20.90 / 18.87 | 20.27 | 2.03 | 12.1 | 11.7 | `013586b5` | 5.4 s `da13a775` |
| `d35b565` | **3-14 EO stitch** | 86.40 / 87.04 / 86.95 | **86.95** | 0.64 | 78.8 | 76.4 | `4ed9cd80` | 7.6 s `04be2f6e` |
| `a890662` | K1 completeness | 85.59 / 85.95 / 85.89 | 85.89 | 0.35 | 77.2 | 74.9 | `4ed9cd80` | 7.8 s `04be2f6e` |
| `ecfae1c` | **plan 29 name guard** | 115.04 / 118.23 / 116.75 | **116.75** | 3.19 | 107.8 | 103.8 | `2ee3456a` | **36.1 s** `04be2f6e` |
| `5182c83` | plan 34 emission | 116.55 / 112.74 / 113.81 | 113.81 | 3.81 | 105.8 | 101.6 | `4e6b0de7` | 34.8 s `04be2f6e` |
| `ec90121` | master at measure | 113.06 / 113.08 / 112.95 | 113.06 | 0.14 | 104.9 | 100.9 | `4e6b0de7` | 35.5 s `04be2f6e` |
| **`a95501c`** | **this fix** | 65.96 / 67.34 / 66.56 | **66.56** | 1.38 | 57.9 | 54.7 | `4e6b0de7` | Perth `-j1` 36.7 s / `-j4` 30.3 s, `04be2f6e` |

The "Perth warm" column is the first Perth build in each worktree, so it
includes any one-off compile. The fix row's Perth figures are cold `-j1` and
`-j4` builds.

### Regressions (Contract H rule: a rise above the spread names its mechanism)

There are **two regressing commits**. Every other step is within spread.

1. **`d35b565` (3-14 EO-aware background stitch): +66.7 s** median (20.27 →
   86.95; spreads 2.03 / 0.64). The whole rise is in L0 encode (11.7 →
   76.4 s).
   - **Mechanism, measured:** call timers in throwaway worktrees
     (`wall/prof_patch.py`). Both instrumented discs are sha-identical to
     plain builds (`013586b5`, `4e6b0de7`). See `wall/prof_summary.json`.
   - `bg_shape` CPU, summed over 4 workers: **23.7 s → 296.6 s**, over
     30.89M vs 30.90M calls.
   - The new time is all in `eo_clip`:
     - **stage 2, `eo_left` per-chain side checks: 161.5 s.** This is
       O(n) per atomic edge: every source edge gets a `hypotl` distance
       for every chain endpoint pair and every emitted face, so a polygon
       spanning many cells pays O(n·m) per cell;
     - stage 5, the complex EO face path: 66.8 s (linear
       `eo_vertex`/`eo_edge` searches);
     - stage 1, the segment sweep: 35.9 s;
     - the duplicate-vertex check: 2.6 s; the tie check: 1.1 s;
     - `chains()` 7.9 → 12.8 s.
   - **Hot function: `eo_clip` → `eo_left`**, 59% of the increase.
2. **`ecfae1c` (plan 29 out-of-span name guard): +30.9 s** median (85.89 →
   116.75; spreads 0.35 / 3.19). L0 rose 74.9 → 103.8 s, and Perth warm
   rose 7.8 → 36.1 s.
   - **Mechanism, from code and arithmetic; per-call timing was not
     measured.**
     - `E1Spool(..., guard_names=True)` runs `_guard_names()` in **every
       worker process, for every level**.
     - That is a Python loop over every spool cell, with
       `spool.decode_columns` (~40 `frombuffer` views) plus numpy span
       tests per cell.
     - L0 has 432,295 cells, so each of the 4 workers repeats the same
       whole-level scan, at about 60 µs per cell ≈ 26 s.
   - The Perth fixture build pays it too: it opens the full L0 spool, which
     is why Perth rose by about 28 s with the same disc bytes.
   - The guard drops 1 name in all of AU.

`5182c83` (−2.9 s) and `ec90121` (−0.75 s) are within spread.

### Fix landed: `a95501c` (byte-identical)

- **The change:** in `eo_left`, an edge whose bounding box lies farther than
  `4·step + 1e-9` from the sample point is skipped before the `hypotl`.
  - Such an edge has distance `d > 4·step`, so `step = fminl(step, d/4)`
    cannot change. `step` only shrinks, so the bound tightens as the loop
    runs.
  - The degenerate-support skip (`d <= 128·DBL_EPSILON·scale`) applies
    only to near-zero `d`, which the prefilter never excludes.
  - The minimum is order-independent, so the result is unchanged.
- **Evidence:**
  - AU `4e6b0de7` 3/3.
  - Perth `04be2f6e` at both `-j1` and `-j4`.
  - The full suite is green with goldens (gate (a)).
- **Effect:** AU median **113.06 → 66.56 s**. Encode 104.9 → 57.9 s, L0
  100.9 → 54.7 s.

### Outcome 3: measured floor plus the budget question (not < 60 s)

- **Floor:** the byte-identical fix gives a median of **66.56 s** (spread
  1.38) at `-j4`.
  - Pre-regression (`33006aa`): 20.27 s.
  - DESIGN target: < 60 s.
  - Plan 04's "full build ≪ 60 s" was 12.16 s at `-j12` at the 3C close.
- **The excess over pre-regression (~46 s) has two named parts:**
  - **the name guard:** about 29 s at L0 per the `ecfae1c` step (Perth
    +28 s);
  - **the remaining EO cost:** stages 1 and 5 and the residual stage-2
    loop. This is about 17 s by subtraction, not separately re-profiled
    after the fix.
- **Candidate second byte-identical fix (not attempted):** run the name
  guard once per level, in the parent before the pool or cached, or scan
  only the name-anchor columns.
  - It would need its own gate cycle: full suite, AU 3 runs, Perth. That
    was not queued, per the 14:36 instruction to add no heavy jobs.
  - **Estimate (not a measurement):** about 66.6 − 29 ≈ 37 s, which would
    be under 60 s at `-j4`.
- **Budget basis:** whether the budget is set at `-j4` (the encode cap) or
  `-j12` is **Cody's call via Design**. Phase 1 measures and reports it
  and does not decide.
  - No `-j12` run was made: it is above the plan 25 cap.

### Close gates (plan 41 Phase 2 rule; triggered by `parser/kiwiw/_cenc.c` in `a95501c`)

Close gate (a) full suite: 1448 passed, 7 skipped in 696.50s at ca85ede

Close gate (b) encode wall: median 66.56 s of 3 at -j4 (spread 1.38 s) vs baseline 113.06 s (ec90121 bench median of 3, wall/bench_table.json)

Close gate (c) sha gate: AU 4e6b0de7 PASS (3/3), Perth 04be2f6e PASS (-j1 and -j4)

- **(a):** run under the wrapper with `TMPDIR` on disk
  (`output/scratch-41/suite/pytest2.log`). The full `parser/tests` run
  with nothing deselected was at the worktree tree of `ca85ede`, which
  contains `a95501c` and only docs commits after it.
  - A first attempt was killed and is **void**: tmpfs `/tmp` hit the user
    quota mid-run, giving mass errors.
- **(b) and (c):** from `wall/fix_runs.json`. The fix worktree's diff
  equals `a95501c`.
- **`close_gates.py`:** `.venv-rp/bin/python -B parser/tools/close_gates.py --base 6e12b36 --impl docs/plans/41-encoder-build-close-gates/IMPLEMENTATION.md` at head `5e355cb` gives `"trigger": true`, `"trigger_paths": ["parser/kiwiw/_cenc.c"]`, `"missing": []`, **`"pass": true`**, exit 0.
  - This is **plan 41's own triggered-pass example**, which Phase 2 left
    open.

### Residuals

- **R-G9-4** (full AU wall vs "≪ 60 s"): the mechanism is named for both
  regressions. The byte-identical fix landed (113 → 66.6 s), and the
  remainder is named.
  - It stays open pending Cody's budget ruling and the candidate guard fix.
  - Updated in `residuals.tsv`.
- **R-G8-1-a** (3-14 b6 build wall FAIL): the cause is measured
  (`eo_clip`/`eo_left`) and the fix landed.
  - The 3-14 share of the wall is now about 17 s by subtraction.
  - Still open until the budget ruling.


## Phase 1 continuation — name guard once per level; EO cost profiled

Execute took the candidate second byte-identical fix (reversible, within
Execute's remit) through a full gate cycle. Design asked for a direct post-fix
profile of the remaining EO cost (stages 1, 5 and the residual stage-2 loop),
so that the whole gap above the pre-regression wall has measured, named causes.
The budget basis (`-j4` vs `-j12`) remains **Cody's call via Design**; this
section measures and does not decide.

### Fix landed: `c82f92e` (byte-identical)

- **The change** (`parser/kiwiw/cenc.py`, `E1Spool._guard_names`): the plan 18
  admission test now runs **once per level, vectorised over the name columns
  only** (`_name_rejects`: cell headers and the `s_present`/`s_lat`/`s_lon`
  columns gathered from the record layout of `spool.encode_columns`). Only cells
  with a rejected anchor take the unchanged per-cell repack (`_guard_cell`, the old
  loop body), which re-derives the verdict; a disagreement raises. A layout that is
  not 8-byte aligned falls back to the per-cell scan of every cell. The wrap-around
  loops are elementwise, so applying them to all names at once gives the per-cell
  result.
- **Equivalence on the pinned spool, every level** (`wall/guard/equiv.json`): the
  private data, lengths and drop counts are identical to the per-cell scan. L0:
  432,295 cells, 1 drop, **0.67 s vs 25.0 s** per process.
- **Test:** `test_vectorised_screen_matches_per_cell_scan` (mixed cells, wrap,
  out-of-span south, empty cell) in `parser/tests/test_name_drop_guard.py`.
- **Effect:** AU median **66.56 → 37.38 s** at `-j4` (runs 37.27 / 37.38 / 37.78,
  spread 0.51). Perth `-j1` 11.08 s, `-j4` 2.96 s (were 36.7 / 30.3 s).
- **The measured median, 37.38 s, is below the < 60 s target at `-j4`.** Whether
  `-j4` is the budget basis is Cody's call via Design.

### Gap above pre-regression, measured (`wall/guard/gap_table.json`, `make_gap.py`)

Pre-regression `33006aa` median 20.27 s; post-fix `c82f92e` median 37.38 s; **gap
17.10 s**. Level walls and the outside-encode time are measured directly; per-stage
C time comes from the existing `prof_patch.py` timers in a throwaway instrumented
copy of `c82f92e` (disc sha `4e6b0de7`; instrumented wall 45.59 s), plus a
per-process timer around the name guard.

- **By level (measured walls):** L0 11.7 → 27.79 s (+16.09); L2 0.3 → 1.09 (+0.79);
  L4 0.1 → 0.21 (+0.11); L6–L12 +0.17 together. Outside encode (assemble)
  7.9 → 7.88 s (−0.02). Levels plus outside: +17.14 s against the 17.10 s gap
  (0.04 s is rounding of the per-level medians).
- **How a level's wall splits:** E1 stage (`prepass_s`: the E1 pool run plus the
  parent's routing sort) + E2 stage. The plan 29 name guard runs **inside the E1
  workers** (`E1Spool(guard_names=True)`, once per process per level on its first
  E1 job), so its wall is inside the E1-stage delta. The `eo_clip` growth is in
  `bg_shape`, inside E2.
- **C CPU summed over the 4 workers:** instrumented 44.56 → 120.13 s;
  uninstrumented post 105.83 s, so timer overhead scales the instrumented delta by
  0.811. Wall-equivalent = CPU delta × 0.811 / 4.

| cause | measured | wall-equivalent | reconciled share of the gap |
|---|---|---|---|
| `eo_clip` stage 1 segment sweep (pair intersections) | +36.18 C CPU s | 7.33 s | **7.38 s** |
| `eo_clip` stage 5 complex EO face path | +22.96 C CPU s | 4.65 s | **4.69 s** |
| `eo_clip` stage 2 residual `eo_left` loop (after `a95501c`; was 161.5 s) | +11.36 C CPU s | 2.30 s | **2.32 s** |
| `chains()` (7.94 → 13.00 s) | +5.07 C CPU s | 1.03 s | 1.03 s |
| `eo_clip` stage 3 duplicate-vertex check | +2.62 C CPU s | 0.53 s | 0.54 s |
| `eo_clip` stage 4 successor tie check | +1.09 C CPU s | 0.22 s | 0.22 s |
| rest of `bg_shape` | +0.18 C CPU s | 0.04 s | 0.04 s |
| **subtotal: 3-14 EO stitch (E2 stage, all levels)** | **+79.47 C CPU s** | **16.10 s** | **16.22 s** |
| L0 E1 stage: plan 29 name guard (1.052–1.065 s per process, the 4 run concurrently) | E1 wall 1.51 → 2.43 s | 0.91 s | 0.91 s |
| outside encode (assemble) | 7.9 → 7.88 s | −0.02 s | −0.02 s |
| **sum** | | **16.99 s** | **17.11 s** |
| **residual vs the 17.10 s gap** | | **+0.11 s** | 0 (rounding) |

- **Reading the table:** the E1-stage delta and the outside-encode delta are
  direct wall measurements. The C stage rows are CPU deltas turned into wall by
  the even-parallelism assumption; that assumption leaves +0.11 s (0.7 %)
  unassigned. The last column scales the C rows by one common factor, 1.0066, so
  the partition sums to the measured gap.
- **The name guard row:** the guard's measured per-process time (1.06 s) is
  0.15 s more than the E1-stage delta (0.91 s). The rest of E1 therefore differs
  by −0.15 s between the two builds (run-to-run noise and the other E1 changes
  between `33006aa` and `c82f92e`). Its CPU, 4.23 s over 4 workers, is most of
  the L0 E1 `py_s` delta (+4.75 s).
- **Correction to an earlier draft:** the draft added the guard twice, once as
  `py_s`/4 (1.19 s) and again inside the E1 delta. That made the sum 18.18 s and
  the residual −1.08 s. `make_gap.py` now adds it once.
- **What this does not split:** the stage timers are summed over all levels, not
  per level. L2–L12 add 1.07 s of wall; this is the same `bg_shape` growth plus the
  L2 guard (0.04 s per process).
- Timer counts lose at most 4,095 calls per worker (flush cadence).

### Close gates (plan 41 Phase 2 rule; triggered by `parser/kiwiw/cenc.py` in `c82f92e`)

Close gate (a) full suite: 1449 passed, 7 skipped in 598.87s at c82f92e

Close gate (b) encode wall: median 37.38 s of 3 at -j4 (spread 0.51 s) vs baseline 66.56 s (a95501c fix median of 3, wall/fix_runs.json)

Close gate (c) sha gate: AU 4e6b0de7 PASS (3/3), Perth 04be2f6e PASS (-j1 and -j4)

- **(a):** `parser/tests` in full, nothing deselected, run in the `c82f92e`
  worktree under the wrapper with `TMPDIR` on disk
  (`output/scratch-41/guard/pytest.log`).
- **(b), (c):** `wall/guard/guard_runs.json` (`run_guard.sh`); the instrumented
  profile disc is also `4e6b0de7`.
- **Protected discs:** snapshot before and after the cycle identical, all 5 entries
  and the spool fingerprint (`wall/guard/protected_{before,after}.json`).
- **Ordering disclosure:** plan 39 heavy jobs ran between gate steps, each taking
  the lock in turn (never two heavy jobs at once). Short unlocked plan 39 analyses
  (seconds each) may have overlapped some timed runs; the AU spread is 0.51 s.
- **`close_gates.py`:** `.venv-rp/bin/python -B parser/tools/close_gates.py --base 6e12b36 --impl docs/plans/41-encoder-build-close-gates/IMPLEMENTATION.md` at head `c82f92e` gives `"trigger": true`, `"trigger_paths": ["parser/kiwiw/_cenc.c", "parser/kiwiw/cenc.py"]`, `"missing": []`, **`"pass": true`**, exit 0.

### Residuals (continuation)

- **R-G9-4:** measured median 37.38 s at `-j4`, below 60 s at `-j4`. Every
  second of the 17.10 s gap above pre-regression has a measured, named cause
  (residual +0.11 s, the even-parallelism error). Open only for Cody's budget-basis ruling
  (via Design). Updated in `residuals.tsv`.
- **R-G8-1-a:** the post-3-14 C stage split is now measured on current master
  (table above) and the build is under the ~1 min budget at `-j4`. Discharge awaits
  the same ruling; Design may reclassify. Updated in `residuals.tsv`.
