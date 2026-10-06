# Encoder/build close gates: full-AU encode wall regression and the full-suite-before-close rule

Plan 41 closed two Design-owned residual rows with the same root: encoder and
build plans had been closing without build-side gates. Phase 2 added a repo rule
and a checker. Every plan that touches the encoder or build must now quote the
full suite, the full-AU encode wall and the sha gate before it closes. This
discharged R-G8-5. Phase 1 benched seven commits and named the two regressions
behind the full-AU encode wall: 3-14's EO stitch and plan 29's name guard. It
landed two byte-identical fixes, which took the `-j4` median from 113.06 s to
**37.38 s**, below the design's < 60 s target at `-j4`. It then measured every
second of the remaining 17.10 s gap above the pre-regression 20.27 s. Encoder
output never changed: AU `4e6b0de7`, Perth `04be2f6e`. R-G9-4 and R-G8-1-a stay
open only for Cody's ruling on the budget basis (`-j4` vs `-j12`, via Design).
Plan 04 Phase 3 is **not** claimed closed.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual rows R-G9-4 (build wall time against the "well under 60 s" budget) and R-G8-5 (rule: full test suite before any close). Say whether R-G8-5 is a workflow-plugin rule or a repo rule. Oracle `4e6b0de7…` or later; build output bytes must not change. Heavy work only under flock plus the wrapper (encode ≤ `-j4`). Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Why This Existed
- **The encode wall.** Plan 35 measured full-AU encode at 115.99 s at `-j4`.
  Plan 04's Contract H says the full build stays ≪ 60 s (12.16 s at `-j12` at
  the 3C close). A plan 36 replay of the pre-3-11 encoder ran in 26 s at `-j4`
  on the same host, so the regression came later. No plan had named its
  mechanism, even though the regression rule requires one for any rise above
  run-to-run spread.
- **The suite rule.** Plan 34 changed encoder emission and closed on 53
  restricted tests. Its review missed a broken `test_parcel_mask`.

## What Was Built
**Changed:**
- `docs/WORKFLOW.md` § "Encoder/build close gates (plan 41)";
- `parser/tools/close_gates.py`, `parser/tests/test_close_gates.py`,
  `parser/perf_inventory.json`;
- `parser/kiwiw/_cenc.c` (`eo_left`; `a95501c`);
- `parser/kiwiw/cenc.py` (`E1Spool` name guard; `c82f92e`), with a test in
  `parser/tests/test_name_drop_guard.py`;
- `residuals.tsv`; bench and profile evidence under
  `docs/plans/04-c-core-orchestration/triage/build_wall/`.

### Phase 2 — close-gate rule and checker
- **A repo rule, not a plugin rule (R-G8-5).** The trigger surfaces and the
  `parser/tests` command under `.venv-rp` are specific to this repo. The plugin's
  skills name no suite. A generic plugin variant was routed to the Workflow
  System Manager by the parent.
- **Trigger:** the diff from design-land to HEAD touches `parser/kiwiw/*.c|*.h`,
  `cenc.py`, `build_alldata.py`, `alldata_writer.py`, `disc.py` or goldens.
- **Gates:** the phase-closing IMPLEMENTATION must quote three marker lines:
  - (a) the full-suite summary line "at <sha>", with no failure, error,
    deselection or filter, and the sha not stale;
  - (b) the encode wall as a median of ≥ 3 at `-j4`, with spread and baseline;
  - (c) the AU / Perth sha gate, with no FAIL or MISMATCH.
- **Checker:** `close_gates.py --base <sha> --impl <path> [--impl-rev REV]`
  must exit 0 with `pass` quoted. It is light (one git diff and one text scan)
  and has 19 tests.
- **Worked examples:** plan 34 is missing (a), (b) and (c) at its close
  (exit 1). Plan 37 is not triggered. Plan 41 is a triggered pass, on `_cenc.c`
  and `cenc.py`.

### Phase 1 — regressions named, two byte-identical fixes, gap measured
- **Bench:** full AU at `-j4`, three runs per commit in throwaway worktrees,
  every disc sha-checked against its commit's oracle:

  | commit | step | median (s) | spread |
  |---|---|---|---|
  | `9269ebb` | 3-11 tip | 21.01 | 1.86 |
  | `33006aa` | pre 3-14 | 20.27 | 2.03 |
  | `d35b565` | 3-14 EO stitch | 86.95 | 0.64 |
  | `a890662` | K1 completeness | 85.89 | 0.35 |
  | `ecfae1c` | plan 29 name guard | 116.75 | 3.19 |
  | `5182c83` | plan 34 emission | 113.81 | 3.81 |
  | `ec90121` | master at measure | 113.06 | 0.14 |
  | `a95501c` | fix 1 | 66.56 | 1.38 |
  | `c82f92e` | fix 2 | **37.38** | 0.51 |

- **Regression 1, `d35b565` (+66.7 s).** This was measured with per-stage call
  timers in an instrumented copy that leaves the bytes unchanged.
  - `bg_shape` CPU rose from 23.7 s to 296.6 s over the same ~30.9M calls, all
    of it in the new `eo_clip`.
  - The `eo_left` side test is O(n·m) `hypotl`. It accounts for about 75 % of
    the rise: 161.5 s in stage 2 (the per-chain checks), plus about 44 s inside
    stage 5, which calls `eo_left` once per emitted face. Stage 5 fell from
    66.8 s to 23.0 s with fix 1 and no other C change.
  - The profile pair is `33006aa` against master `ec90121`, not
    `d35b565` against its parent. The bench steps after `d35b565` (`a890662`,
    `5182c83`, `ec90121`) are within spread, so the master `bg_shape` rise is
    `d35b565`'s.
- **Fix 1, `a95501c`.** `eo_left` now skips an edge whose bounding box is
  farther than `4·step + 1e-9` from the sample point. Such an edge cannot lower
  the monotone minimum `step`, so the result is unchanged. `4·step` and `d/4`
  are exact scalings, and the degenerate-support skip is a no-op either way.
  The 1e-9 margin covers the long-double error of the computed distance
  (about 1e-19 × |coordinate|) while cell-local coordinates stay far below
  1e9. This took the wall from 113.06 s to 66.56 s.
- **Regression 2, `ecfae1c` (+30.9 s).** `_guard_names` was a Python scan of all
  432,295 L0 spool cells, repeated in every worker process at every level. It
  dropped 1 name in all of AU. Perth also paid it (+28 s).
- **Fix 2, `c82f92e`.** Each worker still runs the guard once per level, but
  as one vectorised pass over the name columns instead of a per-cell Python
  decode. (The commit title's "once per level" means exactly this.) Only cells
  flagged by the screen take the old per-cell repack. The repack re-derives
  the verdict and raises if it disagrees on a flagged cell. A layout that is
  not 8-byte aligned falls back to the per-cell scan, which has its own test.
  - Equivalence on the real spool, at every level: data, lengths and drop
    counts are identical to the per-cell path (`_guard_cell`, the old loop body
    moved unchanged). At L0 the guard takes 0.67 s against 25.0 s per process.
  - Wall: 66.56 s to 37.38 s. Perth `-j1` went from 36.7 s to 11.08 s, and
    `-j4` from 30.3 s to 2.96 s.
- **Close gates at `c82f92e`** (marker lines as quoted at the phase close):

  Close gate (a) full suite: 1449 passed, 7 skipped in 598.87s at c82f92e

  Close gate (b) encode wall: median 37.38 s of 3 at -j4 (spread 0.51 s) vs baseline 66.56 s (a95501c fix median of 3)

  Close gate (c) sha gate: AU 4e6b0de7 PASS (3/3), Perth 04be2f6e PASS (-j1 and -j4)


  - full suite: 1449 passed, 7 skipped;
  - AU `4e6b0de7` 3/3;
  - Perth `04be2f6e` at `-j1` and `-j4`;
  - `close_gates.py --base 6e12b36`: pass, exit 0;
  - protected discs and spool fingerprint unchanged.
- **The 17.10 s gap above 20.27 s, measured** (`docs/plans/04-c-core-orchestration/triage/build_wall/guard/gap_table.json`).
  Level walls and outside-encode time were measured directly; the level deltas
  sum to 17.14 s. Within the encode, stage CPU came from the instrumented copy
  and was converted to wall as CPU × 0.811 / 4 workers. The 0.811 factor is the
  ratio of uninstrumented to instrumented post-fix C time against an
  instrumented `33006aa` pre, since `33006aa` has no uninstrumented
  per-level record:

  | cause | wall-equivalent (s) |
  |---|---|
  | `eo_clip` stage 1 segment sweep | 7.33 |
  | `eo_clip` stage 5 complex EO face path (includes per-face `eo_left`) | 4.65 |
  | `eo_clip` stage 2 residual `eo_left` per-chain loop | 2.30 |
  | `chains()` | 1.03 |
  | `eo_clip` stages 3–4 and rest of `bg_shape` | 0.79 |
  | plan 29 name guard (inside the L0 E1 stage; 1.06 s per process, concurrent) | 0.91 |
  | outside encode | −0.02 |
  | **sum / residual** | **16.99 / +0.11** |

  All of the gap is assigned to named, measured components. The unassigned
  +0.11 s is well inside both the `33006aa` baseline spread (2.03 s) and the
  mixed-basis uncertainty (about ±0.3 s). It combines the even-parallelism
  error, scale bias, E2 Python and handoff time, the L2–L12 E1 deltas
  (including the L2 guard, 0.04 s) and run noise. The level partition is
  direct; the per-stage split is a CPU apportionment. The 3-14 EO stitch is
  about 16.1 s of the gap and the guard about 0.9 s. The guard's CPU (4.23 s
  over 4 workers) is most of the L0 `py_s` delta (E1 + E2, +4.75 s).

## Deviations
- Phase 2 landed before Phase 1, in queue order (the design marks them
  independent).
- Fix 2 is a second performance change beyond the design's single "fix". It was
  Execute's reversible decision, gated in full. The direct post-fix EO profile
  was Design's request.
- An earlier gap-table draft counted the guard twice (as `py_s`/4 and again
  inside the E1 delta), which made the residual −1.08 s. It was corrected
  before the record.
- The pre-regression E1 time and the 0.811 scale use the instrumented
  `33006aa` run (instrumented post E1 is 2.58 s against 2.43 s uninstrumented).
  Stage timers are summed over all levels, not split per level (L2–L12 add
  1.07 s).
- The mechanism profile used master `ec90121` rather than `d35b565` itself
  (justified above by the within-spread bench steps).
- The Phase 1 working text first gave `eo_left` 59 % of the rise and blamed
  stage 5 on linear vertex/edge searches. That was never measured; the review
  corrected it to about 75 %, as above.

## Review
Claude CLI clean-context seats (disclosed; Codex weekly-limited), both
**PASS_WITH_FOLLOWUPS**. Light reads plus re-runs of `make_gap.py`,
`close_gates.py` and the guard tests. The review texts are kept in
`docs/plans/04-c-core-orchestration/triage/build_wall/reviews/`.
- **Phase 2 (`ec90121`):** six findings, all fixed in `a428eab`: restricted,
  stale or failing gate lines are now rejected, and the checker has 19 tests.
- **Phase 1 and continuation (`dd0bef7`):** no blocking findings. Both fixes
  were found byte-identical by argument and by sha, the close gates true, the
  gap table reproducible, and no decision attributed to Cody. Eight
  low-to-medium findings were applied at close:
  - F1: `eo_left`'s share and the stage 5 label;
  - F2: the residual's wording and the scale basis;
  - F3: "once per level";
  - F4: the one-sided raise and the equivalence reference;
  - F5: a new fallback test, `test_unaligned_layout_fallback_matches_vectorised_screen`;
  - F6: the `py_s` label;
  - F7: the profile basis;
  - F8: the margin bound.

## Residual Risks
- **The budget basis is unresolved.** 37.38 s is below 60 s at `-j4`, but
  plan 04's reference was 12.16 s at `-j12`, and `-j12` is above the plan 25
  cap. No `-j12` run was made.
- Short unlocked analyses may have overlapped some timed runs. The spreads are
  reported (0.51 s at the close).

## Follow-ups
- **R-G9-4** (maps-parity-carried) and **R-G8-1-a** (blocks-phase3, Design may
  reclassify): mechanism measured, under 60 s at `-j4`; open only for Cody's
  budget-basis ruling, via Design (`residuals.tsv`).
- The generic plugin variant of the suite rule went to the Workflow System
  Manager (parent-routed).
- Further byte-identical EO work (stages 1 and 5) is possible if the ruling
  requires a lower wall.

## Decisions Worth Keeping
- Fix performance only byte-identically. A fix is proven by the AU and Perth
  shas plus the full suite, never by re-pinning.
- A rise above spread names its mechanism with a measurement. Apportioning by
  subtraction is not accepted as a cause.
