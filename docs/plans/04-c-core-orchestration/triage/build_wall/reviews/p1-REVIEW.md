Verdict: PASS_WITH_FOLLOWUPS

Reviewer: Claude CLI clean-context seat (disclosed; Codex weekly-limited until 2026-10-10). Authored none of the work.
Scope: plan 41 Phase 1 and its continuation at dd0bef7 (= origin/master). Fixes a95501c and c82f92e. Records `wall/` and `wall/guard/`. Raw data in `output/scratch-41/`.
Commands run (light only):
- `make_gap.py` re-run with its JSON dump disabled. The output is identical to the committed `gap_table.json`.
- `close_gates.py` at dd0bef7, at `--head c82f92e`, and at `--impl-rev 48fe7ba`.
- `pytest parser/tests/test_name_drop_guard.py`: 10 passed.
- JSON and log reads.

## Clause table

| Phase 1 outcome clause | Judgement | Evidence |
|---|---|---|
| 1. Bench table: 7 commits, medians, spreads, shas | MET | `bench_table.json`: all 7 commits, 3/3 shas each, all matching the DESIGN oracles. |
| 2. Regressing commits and hot function named; per-level decomposition | MET, with an attribution error | Two steps exceed the spread (d35b565, ecfae1c). The guard's per-cell cost is now measured: `equiv.json` L0 `per_cell_scan_s` 25.0 per process. **But** stage 5 was mis-named and eo_left's share understated (F1). The profile was not taken at d35b565 itself (F7). |
| 3. Byte-identical fix with `-j4` median < 60 s (AU, Perth, goldens, full suite) | MET at `-j4` | `guard_runs.json`: 37.27/37.38/37.78, all `4e6b0de7`. Perth `04be2f6e` at `-j1` and `-j4`. `pytest.log`: `1449 passed, 7 skipped`; argv is the full `parser/tests` with no `-k` or deselect, and the worktree HEAD is c82f92e (`run.log` `W c82f92e…`). Protected discs and the spool fingerprint are identical before and after. The budget basis is correctly left to Cody via Design. |
| 4. R-G9-4 updated (and R-G8-1-a) | MET, with wording follow-ups | Both rows match `gap_table.json`. They carry the F2 and F3 wording issues. |
| a95501c is output-identical | PROVEN (see note) | Each skipped iteration is a no-op in the original, so the state matches after every iteration: (i) bbox gap ≤ true Euclidean distance; (ii) a skipped edge has true d > 4·step + 1e-9, and `4*step` and `d/4` are exact power-of-two scalings, so `fminl` leaves step unchanged; (iii) the 128·ε skip is also a no-op, so which branch would have fired is irrelevant; (iv) NaN compares false and is never skipped. Order independence is not needed. The only open term is the computed-vs-true-d error bound (F8). |
| c82f92e gives the same verdict as the per-cell scan for every cell | PROVEN by inspection plus equiv | The gather matches `spool.py` exactly (9×u64 header in `_COUNT_KEYS` order, then `_COLUMNS` order with each column padded to 8). Alignment is checked (`off%8`, `len%8`), so f64 indices are exact. The wrap loops update only offending elements, so each element sees the same operation sequence. Empty cells add 0 to `bincount(minlength=n)`. Unflagged cells keep `drops=0`, as before. The screen reads everything before any in-cell repack. `equiv.json` covers L0–L12, all 7 levels, against a full per-cell scan. The raise is one-sided (F4). The fallback path is untested (F5). |
| Gap table: "every second of 17.10 s measured and named" | SUPPORTED at level granularity; per-stage precision overstated | Reproduces exactly from the raw data. The level deltas plus outside-encode give 17.14 against 17.10. The guard is counted once (`accounting_s` has no py_s term). Scale 0.811, factor 1.0066, and the L2–L12 figure of 1.07 all check. The mixed basis and the meaning of the +0.11 s residual are mis-stated (F2). |
| Close-gate lines truthful; `close_gates.py` exits 0 | TRUE | At dd0bef7: `pass: true`, `missing: []`, trigger `_cenc.c`, `cenc.py`, exit 0. It also passes at `--head c82f92e` and `--impl-rev 48fe7ba`. No `parser/` change after c82f92e. |
| Attribution | CLEAN | The guard fix is stated as Execute's reversible decision. The EO profile is stated as Design's ask. The budget basis is "Cody's call via Design" throughout. No decision is attributed to Cody. |

## Findings

1. **Medium: stage 5 was mis-attributed, and eo_left's share was understated (Phase 1 record, R-G8-1-a).**
   - Evidence:
     - `_cenc.c:899` calls `eo_left` once per emitted face inside stage 5.
     - Instrumented stage 5 CPU fell from 66.84 s (`prof_summary.json` head, ec90121) to 22.96 s (`gap_table.json`, c82f92e). The only C change between them is a95501c; stage 1 is stable (35.93 → 36.18), so the instrumentation is comparable.
     - So ≈44 s of "stage 5" was eo_left. eo_left was then ≈205 of the 273 s bg_shape rise (~75%), not 59%.
     - The Phase 1 text "stage 5 … 66.8 s (linear `eo_vertex`/`eo_edge` searches)" was never measured.
     - In the continuation table, the "stage 2 residual eo_left loop" row is not the whole residual eo_left cost; some of it sits in the stage 5 row.
   - Fix:
     - Amend the Phase 1 bullet: stage 5 includes per-face `eo_left`; a95501c removed ≈44 s of it; eo_left ≈75% of the increase.
     - Drop the eo_vertex/eo_edge claim, or mark it unmeasured.
     - Relabel the stage 5 row "complex EO face path (includes per-face eo_left)" in IMPL, `make_gap.py` names, and R-G9-4 / R-G8-1-a.

2. **Medium-low: the gap residual is over-precise and mis-named.**
   - Evidence:
     - `scale = (post_unins − pre_INS)/(post_ins − pre_ins)`. 33006aa has no uninstrumented bench.json; this appears in the `make_gap.py` comment but not in IMPL, which calls 0.811 simply "timer overhead".
     - Pre-side timer overhead (31M bg_shape + 6.2M chains timer pairs) inflates `pre_ins`, so the scale is biased low. A plausible ~1.5 s CPU correction gives scale ≈0.83 and a residual ≈−0.3 s.
     - The "direct" E1 delta is also mixed-basis: instrumented pre `prepass_s` 1.51 against uninstrumented post 2.43. Instrumented post is 2.58, so instrumentation alone moves it ≈0.15 s.
     - The 33006aa baseline spread is 2.03 s.
     - The +0.11 s therefore lumps together the even-parallelism error, scale bias, E2 Python/handoff deltas, L2–L12 E1 deltas (including the L2 guard) and run noise. The factor 1.0066 spreads all of that across the EO rows.
   - The level partition (17.14 against 17.10) is solid. The per-stage split is an apportionment.
   - Fix:
     - In IMPL and R-G9-4, say "all of the gap is assigned to named components; unassigned remainder +0.11 s, well inside the baseline spread (2.03 s) and the mixed-basis uncertainty (≈±0.3 s)".
     - Add a table note that the scale and the L0 E1 delta use an instrumented 33006aa pre.
     - Stop calling the +0.11 s "the even-parallelism error".

3. **Low: "once per level" is inaccurate.**
   - Evidence: `build_alldata.py:227-233`. `_e1spool` still builds `E1Spool(guard_names=True)` in each worker for each level: 4× at L0, 4.23 s CPU. Before the fix the guard also ran once per process per level, so the gain is entirely from vectorisation.
   - IMPL contradicts itself: "runs once per level" in one place, "once per process per level" in another. The commit title and R-G8-1-a repeat the inaccurate phrase.
   - Fix: say "one vectorised pass over the name columns per worker per level (was a per-cell Python decode)".

4. **Low: "a disagreement raises" overstates the runtime check.**
   - Evidence: `cenc.py` compares only cells where the screen flags a reject. A screen false-negative cannot be detected.
   - Equivalence rests on the code argument above plus `equiv.json`. Note that `equiv.py`'s reference is the refactored `_guard_cell`/`_admission_rejects`, not 87f78fe's code. The refactor is identical by inspection, and the AU/Perth shas close the gap.
   - Fix: say "a disagreement on a flagged cell raises", and name the reference used by `equiv.py`.

5. **Low: the not-8-byte-aligned fallback is untested.**
   - Evidence: the new test exercises only the fast path. `_name_rejects(grid).tolist()` would fail on `None`.
   - Fix: add a test that forces the fallback (monkeypatch `_name_rejects` to return `None`, or use a copy with odd padding). Assert the same `drops`, `lengths` and bytes.

6. **Low: `py_s` is mislabelled.**
   - Evidence: IMPL says "most of the L0 E1 `py_s` delta (+4.75 s)". Level `py_s` merges E1 and E2 Python time (`build_alldata.py:481-490`).
   - Fix: call it "L0 `py_s` (E1+E2)".

7. **Low: the profile basis deviates from Contract 2 without saying so.**
   - Evidence: DESIGN asks for a profile "at that commit and its parent". The head profile is master ec90121 (disc 4e6b0de7), not d35b565. Attributing the bg_shape rise to d35b565 relies on the bench steps (a890662, 5182c83 and ec90121 within spread).
   - Fix: state the substitution and the reasoning in IMPL Phase 1.

8. **Info: a95501c's margin bound is asserted, not stated.**
   - Evidence: computed d ≥ true d − O(ε_ld·(|u|+|v|)), with ε_ld ≈ 1.1e-19. The 1e-9 margin holds while cell-local coordinates (`(lon−lon_lo)/dlon·range`, `_cenc.c:923`) stay well below ~1e9. AU and Perth bytes are identical.
   - Fix: put the coordinate bound in the comment or record so the "dwarfs" claim can be checked.

No blocking findings. The close gates are true, both fixes are byte-identical by argument and by sha, and the `-j4` budget basis is correctly left with Cody via Design.
