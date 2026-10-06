# Plan 35 Phase 2 — independent review (plan 04 Phase 3 close synthesis)

**Verdict: REMEDIATE**

**Seat:** Claude CLI clean-context reviewer, used because Codex was weekly-limited.
Tree: detached HEAD at master `873f161`. Method: comprehensive-review skill, light checks only.

The gate states are correct. Phase 3 does not close: there is no PASS trailer, and the
residual branch follows. The verdict is REMEDIATE for two reasons:

- residuals.tsv leaves out one open item, the L8 road TRIM BLOCKER (F1). DESIGN requires
  residuals.tsv to name every open item, and the OVERVIEW blocker list to match it exactly.
- R-G4-1 misstates which hops are unreconciled and who owns them (F2).

Both fixes are bookkeeping only. No rerun is needed. Briefs are inline below because this
review may touch only this file.

## Per-gate re-derivation

| Gate | Synthesis state | My state | Agrees | Note |
|---|---|---|---|---|
| G1 | RESIDUAL | RESIDUAL | y | oracle_chain.tsv rows check out: AU 3-11 37; AU 3-14 246,123 (L0 244,060 / L2 1,944 / L6 118 / L8 1); Perth 3-14 795; plan 29 1 cell. The R-G1-* rows map to design 36 phases. |
| G2 | PASS | PASS | y | All 9 kinds fail 0 on `4e6b0de7`. The dump run's counts are 0, but `--dump-failures` covers only 5 kinds (DUMP_KINDS). range/step/road_node/road_point rest on totals of 0 (F6). |
| G3 | PASS | PASS | y | The P2 suite at `873f161` gives 1383 passed / 7 skipped, exit 0, wall 702.38 s, peak 11,474,386,944 B. This matches `output/scratch-35/runs/p2_pytest.json` and `evidence/pytest_p2_tail.txt` (`40facaca`). The parcel_mask root cause is a stale test, not a masked defect (see below). |
| G4 | RESIDUAL | RESIDUAL | y | All 8 deltas recompute exactly. The text and owner are wrong, because intermediate per-hop counts do exist (F2). |
| G5 | RESIDUAL | RESIDUAL | y | 8,739 / 137 / 180 groups confirmed; 9,064 = 8,739 + 137 + 188. The per-kind × per-cause table that DESIGN G5 asks for is missing (F4). |
| G6 | PASS | PASS | y | -j6 walls 79.887 / 79.485 / 79.661 s; PSS max 7,599,962 kB, under the 9,726,501 kB ceiling. -j1 run: 417.7 s, 6,501,586 kB. All four reports are identical after stripping `timing`/`wall_s`. |
| G7 | PASS | PASS | y | Rebuild sha is `4e6b0de7…`; Perth -j1 = -j4 = pin `04be2f6e…`; protected discs unchanged. Between P1 HEAD `9c99dcb` and `873f161`, only tests and `parser/perf_inventory.json` changed, so the sha holds at the close HEAD. The synthesis does not say this (F7). |
| G8 | RESIDUAL | RESIDUAL | y | The 3-14 not-accepted treatment is correct: BOUNCE on stale tip `67e48d9`, then Design overrule against `a10585a`, landed `414c5fe`, and no `CHM-3-14-adversarial.md` exists. 3-15/16/17 have no review file. |
| G9 | RESIDUAL | RESIDUAL | y | Plan 30 at 341 / 0 / 1 (row 246) is confirmed against disposition_summary `1318c873`. The L8 TRIM carry is missing (F1). "Design 36 not executed" is stale: Phase 1 is in progress (F5). |
| G10 | RESIDUAL (non-gating) | RESIDUAL (non-gating) | y | The OVERVIEW states the CHM hold cleared, plan 30 at 341/0/1, and +60 B attributed by plan 07 (`docs/plans/07-g-new-nonpayload.md`: 34×(−4) + 7×(+28) = +60, PASS at `176383a`). The bullets equal the blocks-phase3 rows as they stand. After F1 they need one more bullet only if F1 is classed blocks-phase3. |

**Branch:** at least one gate is RESIDUAL, so the residual branch and the absence of a
trailer are correct. The verdict wording in synthesis.md follows from the table.

### parcel_mask root cause (G3)

- `5182c83` (plan 34) added `_empty_shell_header`, `is_empty_shell` and
  `_omit_outside_mask_shells`. Together they omit outside-mask exact empty shells
  (pt = sx = sy = 0), mirroring R, which writes frames only where content exists.
- The old test's synthetic cell (720,30) holds only an out-of-span name, so its frame is an
  exact shell, and the new code correctly omits it.
- `a906818` changes only the test, plus a note in the plan 34 record. It keeps the old
  expectation for (720,30) as an omission and adds cell (721,30), which has an in-span name
  and passes through byte-stable. The test's original intent (spooled content outside the
  mask survives) is therefore still asserted.
- My run of the test file gave 4 passed.
- **Judgment:** a stale test, correctly fixed. This is not a relabel.
- The process gap is recorded as F3.

## Findings

### High

**F1. The L8 road TRIM BLOCKER on the oracle in force is not carried anywhere.**

- **Evidence:** `evidence/run_p1.log` L134 reads
  `level 8: TRIM road: dropped 308/14,012 (2.198%) in 1 sub-cells ** >1% BLOCKER **`.
  L152–153 add L0 road 207/3,015,057 and background 227/11,029,580 trimmed.
- **History:**
  - 3-14 recorded this as a "known budget (Design ticket for any expand-to-zero
    follow-up; not 3-14 scope)".
  - Briefs 3-15, 3-16 and 3-17 each mark it out of scope.
  - No later plan discharges it.
- **Gap:** it appears in none of gates.tsv, residuals.tsv or synthesis.md.
- **Why it matters:** this is encoder content drop on `4e6b0de7` with no R-parity proof.
  K1 cannot see it, because K1 compares against the encoder's own retained set.
- **Fix:** add a residual row (G9, or G5 if Design prefers), class maps-parity-carried at
  minimum. Use blocks-phase3 if Design rules that a >1% BLOCKER line is a parity gap.
  Owner: unowned → Design (expand-to-zero ticket). Cite run_p1.log L134 and L152–153.
  Mirror the row in synthesis.md and, if it is blocks-phase3, in the OVERVIEW blocker list.

### Medium

**F2. R-G4-1 says no hop record reconciles the moves, but per-hop checked counts exist.**

- **Error:** gates.tsv G4 and R-G4-1 treat the whole 3C-04 → now move as unreconciled, with
  owner "3-11 / plan 29 / plan 34 hops: unowned → Design".
- **Recorded counts:**
  - **`013586b5` (3-11):** plan 04 IMPLEMENTATION, 3-90 rerun #3 (≈L698–705).
    - Deltas vs 3C-04: range +861,107; step +693,171; road_node 0; name_anchor 0;
      background +839,197; background_boundary +21,910; completeness 0;
      interior_cover +29.
  - **`4ed9cd80` (3-14):** `triage/name_anchor/witnesses/successor_k1_compare.json`
    baseline (plan 14 rem01 k1_live).
    - Deltas vs `013586b5`: range −24,243,765; step −25,202,484; road_node −790;
      name_anchor −927; background +1,215,204; background_boundary −25,457,252;
      interior_cover −1,479.
  - **`2ee3456a` (plan 29):** expected == new (range −1, name_anchor −1). This hop is
    reconciled.
  - **`4e6b0de7` (plan 34):** `pin_contract.tsv` totals equal plan 34 phase2/k1.json and
    P1, so this hop's delta is 0.
- **What stays unexplained:** only the 3C-04 → 3-11 and 3-11 → 3-14 hops. The 3-14 hop
  carries almost all of the movement.
- **Fix:** split R-G4-1 into those two hops, cite the two records above, and drop plans 29
  and 34 from the owner field. G4 stays RESIDUAL.

**F3. The plan 34 regression shows a review-coverage gap.**

- Plan 34 landed after "53 restricted tests" with no full suite run, so its terminal review
  missed the parcel_mask break.
- `a906818` (the test edit) has had no independent review other than this one.
- **Fix:** add a G8 note or a maps-parity-carried row stating that `a906818` was reviewed
  here. Also add a process follow-up: a plan that touches the encoder runs the full suite
  before close.

**F4. The G5 figure does not give the per-kind × per-cause count table that DESIGN G5 asks for.**

- The synthesis gives group totals only.
- The 3C-04 failing counts differ from the 3-11-disc counts the attribution used
  (bg 1,438,558 vs 1,438,571; bb 16,549,569 vs 16,550,043; completeness 752 vs 739).
  The mapping between the two sets is not stated.
- **Fix:** add the table and a one-line note on the basis difference.

### Low

**F5.** "Design 36 not executed" (G1/G9 notes) is stale. Design 36 IMPLEMENTATION.md
records Phase 1 under way (3-11 predecessor replay at `b7c7c42`). It should read
"in progress, not closed".

**F6.** G2's "dump counts 0" should say that it covers the 5 DUMP_KINDS only. The other
kinds rest on fail = 0 totals, and the `.bin` files are 0 bytes.

**F7.** G7 should state that `9c99dcb..873f161` touches no build code, which is why the P1
rebuild sha still stands at the close HEAD.

**F8.** Build wall versus the plan 04 DESIGN L48 H budget.

- DESIGN L48 says the full build stays ≪ 60 s; at 3C close it was 12.16 s.
- The P1 AU encode wall here was 115.99 s at -j4. Plan 34 recorded 118 s, so this is not a
  plan 35 regression, but no plan has named the mechanism.
- The H-budget unit tests pass, but the end-to-end wall is not gated. The synthesis is
  silent on it.
- **Fix:** add a maps-parity-carried row (owner: Design) or cite where the budget was
  rebased.

## Inline remediation brief (in place of `briefs/remediation-NN.md`)

1. In residuals.tsv:
   - add the F1 row;
   - split and re-own R-G4-1 per F2;
   - add the F3 and F8 rows.
2. Update gates.tsv G2, G4, G5, G7 and G9 notes per F2 and F4–F7. Do not change any gate
   state.
3. Update synthesis.md to match. If F1 is classed blocks-phase3, add it to the OVERVIEW
   blocker list so the list again equals the blocks-phase3 rows exactly.
4. Get a re-review of the diff only. No K1, encode or pytest rerun is needed.

## Checks run

- Hashed every evidence file cited in gates.tsv; all prefixes match the citations.
- Read the k1_j6_1/2/3, k1_j1, k1_dump and p1_summary JSONs. Recomputed the medians and
  maxima and compared the reports after stripping `timing`/`wall_s`.
- Read the sha_rebuild, sha_perth_j1/j4 and protected before/after files.
- Read `output/scratch-35/runs/p2_pytest.json` and `evidence/pytest_p2_tail.txt`.
- Reconciled the +17 test count: test_parity_disposition 39 → 53, test_per_rule_f2_identity
  +3.
- Ran `PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_parcel_mask.py --basetemp …/scratch-35/review/t`:
  4 passed.
- Read the `git show` / `git diff` output for `5182c83`, `a906818` and `9c99dcb..873f161`.
- Recomputed the G4 deltas, and the per-hop deltas from the plan 04 3-90 rerun #3, plan 14
  `successor_k1_compare.json` and plan 29/34 records.
- Checked the G5 figures against phase2_disposition.md, cause_table (`05627155`) and the
  3-17 section.
- Checked G8 against the review_3-* files, plan review records 14/28/29/31–34/37 and the
  3-14 IMPLEMENTATION section.
- Checked G9 against plan 30 disposition_summary and open_rows_account.md, and the design
  36 DESIGN/IMPLEMENTATION files.
- Checked G10 against the OVERVIEW diff and plan 07.
- Read `evidence/run_p1.log` (TRIM lines and encode wall) and the plan 34 measurement
  section.
- **Not checked:**
  - whether plan 28 assigns all 188 historical completeness rows (cited, not re-derived);
  - the plan 25 record of the CHM clearance date;
  - whether the review_3-12/3-13 conditions were discharged.
- **Deviation, disclosed:**
  - To count the old test_parity_disposition's tests, I briefly wrote
    `parser/tests/_rv_old_pd.py` (copied from `0f3e530`) and deleted it at once.
    `git status` shows `parser/` clean.
  - Old-file copies remain in `output/scratch-35/review/`.
- **Not done:** no ALLDATA.KWI, R disc or spool access; no K1, encode, dump, classify or
  full pytest; no network; no commit.

## Re-review (remediation)

**Verdict: PASS**

Same seat (Claude CLI, clean context). Scope: the uncommitted gates.tsv, residuals.tsv,
synthesis.md and `git diff docs/OVERVIEW.md`. Diff-focused and light; no rerun.

| Finding | Resolved | Check |
|---|---|---|
| F1 | y | R-G9-3 cites `evidence/run_p1.log` L134 (L8 road 308/14,012, 2.198%, `>1% BLOCKER`) and L152–153 (L0 road 207/3,015,057; background 227/11,029,580). All three lines match the log verbatim. Class maps-parity-carried, with "Design may promote"; owner unowned → Design (expand-to-zero ticket). The row is mirrored in the G9 note and in synthesis.md. The sub-cell (3,0) identity comes from the plan 04 3-14 TRIM ruling (IMPLEMENTATION L233), not from the log, and the row cites both. |
| F2 | y | R-G4-1 covers the 3C-04 → `013586b5` hop (unowned → Design). R-G4-2 covers the `013586b5` → `4ed9cd80` hop (plan 36 Phase 3; design 36 L129 outcome 4 is "K1 `checked` hop delta confined to changed cells"). Per-hop counts are recorded in the G4 figure. Plans 29 and 34 are stated as reconciled and removed from the owner field. |
| F3 | y | The G8 note records the review of `a906818`. R-G8-5 is the process follow-up (full `parser/tests` before close for encoder/build plans), classed non-gating (process). |
| F4 | y | The G5 figure now has a per-kind × cause table and a basis note: bg/bb sums are on the 3-11 disc (1,438,571 / 16,550,043), against 3C-04 1,438,558 / 16,549,569, and completeness 752 vs 739. The note states the row mapping is unstated, and R-G5-1/2 carry that. |
| F5 | y | G1, G9 and synthesis say "Design 36 in progress (Phase 1), not closed". |
| F6 | y | G2 names the 5 DUMP_KINDS, the 0 B `.bin` files, and that range/step/road_node/road_point rest on fail = 0 totals. |
| F7 | y | G7 and synthesis state that `9c99dcb..873f161` changes, outside `parser/tests`, only `parser/perf_inventory.json`. I confirmed this with `git diff --name-only`: the only non-docs paths are `parser/perf_inventory.json` and three test files. |
| F8 | y | R-G9-4: 115.99 s vs DESIGN L48 "≪ 60 s", maps-parity-carried, owner unowned → Design. `evidence/runs.json` `p1_encode_au` gives `time_v_elapsed_s` 115.99. |

**Gate states and verdict:** unchanged. G2/G3/G6/G7 are PASS; G1/G4/G5/G8/G9 are
RESIDUAL; G10 is RESIDUAL (non-gating). The residual branch with no trailer still follows.

**OVERVIEW blocker list = blocks-phase3 rows:**

- The blocks-phase3 rows are R-G1-1..4, R-G4-1, R-G4-2, R-G5-1..4 and R-G8-1..4.
- The four OVERVIEW bullets cover exactly these: plan 36 (G1), the 3-11/3-14 hop `checked`
  moves (G4), the historical remainder plus polygon 65623 plus R01 (G5), and the 3-14 to
  3-17 reviews (G8).
- R-G9-3 is maps-parity-carried, so it correctly has no bullet.

**Recomputed figures:**

- **G4 per-hop sums.** Each 3-11 + 3-14 + plan 29 + plan 34 total equals the G4 total:
  - range: +861,107 − 24,243,765 − 1 + 0 = −23,382,659
  - step: +693,171 − 25,202,484 = −24,509,313
  - road_node: −790
  - name_anchor: −927 − 1 = −928
  - background: +839,197 + 1,215,204 = +2,054,401
  - background_boundary: +21,910 − 25,457,252 = −25,435,342
  - interior_cover: +29 − 1,479 = −1,450
  - completeness: 0
- **G5 cause counts:**
  - Plan 04 IMPLEMENTATION and phase2_disposition.md L11–12 give R01 920,786, S03 517,648,
    S04 14,602,251 and S02 1,939,053.
  - cause_table.md L15/17/23/24 give O02 821, completeness 564 + 188 = 752, and O03 1.
    S05 3 brings interior_cover to 824.
  - background: 920,786 + 517,648 + 137 = 1,438,571.
  - background_boundary: 1,939,053 + 14,602,251 + 8,739 = 16,550,043.
  - The `checker:repaired-not-representable` ×188 label is at plan 04 IMPLEMENTATION L243.

**New findings:** none blocking.

- *Nit (no action required):* the G7 figure gives 700.38 s, which is pytest's own time
  (`pytest_p2_tail.txt`). My first review gave 702.38 s, which is the wrapper `wall_s`
  (`p2_pytest_run.json`). Both are correct for their source.
