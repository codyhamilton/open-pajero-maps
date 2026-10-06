Verdict: FAIL

Reviewer: Claude CLI clean-context seat (disclosed; Codex weekly-limited until 2026-10-10). Scope: plan 39 P1–P3, commits `1725292`, `7ef7450`, `dd0bef7` (HEAD `dd0bef7`). I authored none of the work. Only light reads were run, plus one bounded probe over 60 cells (`output/scratch-39/review/shape_probe.py`). No builds, no K1 runs, no lock taken, no tracked files touched.

The FAIL comes from one structural defect (F1). Clause (b) keys the item on the exact raw vertex. A build fix that moves or eliminates the bad vertex therefore always registers as "removed". As a result, "R01 exclusivity holds", the R-G5-4 discharge and "none is build-fixed" (R-G5-1/2) are unsupported, and these claims are now written into `rules_bg.json`, `OVERVIEW.md` and `residuals.tsv`. P1 and P3 hold up apart from documentation fixes.

## Clause table

| # | Clause | Result | Evidence |
|---|---|---|---|
| P1.1 | HEAD K1 on `87a01b14` = 3C-04 (completeness 65 vs 752 disclosed); on `013586b5` = rerun #3 (52 vs 739); `1cf40f8` K1 = 3C-04 in all 9 kinds | PASS | `compare_3c04.py` reference constants equal plan 04 IMPLEMENTATION L78–87 (2-08) and L698–707 (rerun #3) digit for digit; `cmp_*.json` deltas are 0 except completeness −687; summing `k1old_pre311.json` over levels gives 752 / 1,438,558 / 16,549,569 / 824 exactly |
| P1.2 | R-G4-1 confinement and exact explanation | PASS (minor gaps F7) | `wrap37.json`: 41 elements in 37 distinct cells, every `unread_old` = 4096, Σ 167,936 records / 861,107 vertices; `decl_old = physical − 4096` for all; record bytes and non-bg sections identical; 839,197 + 21,910 = 861,107; 861,107 − 167,936 = 693,171; cover 29. `k1-confine-3-11.json`: 35/35 bands, no delta outside |
| P1.3 | Remainder regeneration blocked, reason stated truthfully | PASS | `run_classify.log`: `rule S02: unknown column 's02_producer_verified'`, exit 2; `docs/provenance.md` L380/L383 say "not regenerable by this old recipe" |
| P1.4 | Basis map | PASS | `basis_311.json`: rows outside the 37 cells identical in order (1,438,414 / 16,548,105 / 824); inside them +13 / +474 |
| P1 BOM | scratch-39 recorded in `docs/provenance.md` | **FAIL** (F4) | `grep scratch-39 docs/provenance.md` returns nothing; 5.7 GB untracked |
| P2.(a),(c) | Absent on `4ed9cd80`; cell class from plan 36 P3 | PASS | `k1_314.json` failing 0 in all three kinds; `r01_join.json` `eo_bg_stitch` 920,693 / `eo_division_ceiling` 80 |
| P2.(b) | Item still checked on `4ed9cd80` | **FAIL** (F1) | Item identity includes the raw vertex, which is the quantity a build fix changes; see probe |
| P2 R01 | "Exclusivity holds"; R01 stays checker, reason `removed-by-3-14` | **FAIL** (F1, F2) | Not supported by the test. Design open question 1 (dual cause) should have been raised |
| P2 all-rows | Every row removed or footprint-changed | Numbers PASS, meaning FAIL | `status.u8` bincounts: bg {2: 1,438,456, 3: 102}, bb {2: 16,548,853, 3: 716}; matches the JSON. "Removed" carries the F1 artefact |
| P2 assignment.tsv | Count-level deviation from per-row | Acceptable as disclosed | Disclosed in IMPLEMENTATION and in the tsv; the per-row status lives in scratch, so it is regenerable but not committed |
| P3.1 | 65623 control and CF valid; join correct | PASS | `join65623.json`: 226,576/226,576 control cells, 0 mismatches; 58,032 type-288 records in 58,030 leaves; every in-window row of the changed cells validated against record bytes; produced 0 in each kind (`produced_rows_*.tsv` are header-only) |
| P3 window exhaustive | No producible row outside the window | PASS (my check) | A linear fit of dump lat/lon to ix/iy (residual ≤ 0.51 cell) puts the source bbox at ix 1414.7–1888.4, iy 274.97–748.75, so it sits inside `[1414,1890)×[274,750)`. The record justifies the window by failing rows, not by the source bbox (F6) |
| P3 completeness | Ring–cell meet | PASS, with an unbacked sub-claim (F6) | `completeness65623*.py`: 0 type-288 rows in a cell the ring meets. No artefact backs the "600 sampled cells agree with CF" claim |
| P3.4 | Locate the 3C "disc defect near 65623" footprint and check it on all discs | NOT DONE (F5) | Absent from IMPLEMENTATION |
| P3.2 | cause_table 65623 section rewritten | PARTIAL (F3) | The next paragraph still says the contract is "unmet and explicitly reported" |
| Residuals | R-G4-1 discharged | PASS | — |
| | R-G5-3 discharged | PASS (subject to F3, F5) | — |
| | R-G5-4 discharged → R-G5-4-a | **FAIL** (F1, F2) | — |
| | R-G5-1/2 open, honest reason | Reason PASS; added text FAIL | The open reason (deleted side-column producers) is honest. The added "none is build-fixed" inherits F1 |
| Attribution | Decisions attributed to Cody/Design | PASS | No invented rulings. "A new producer scan is a Design ruling" is stated as pending |

## Findings

**F1 — BLOCKER. The clause (b) identity key makes "fixed" indistinguishable from "removed". The `removed-by-3-14` label is an artefact.**
- *Evidence.*
  - The design defines (b) as "its item is still checked on 4ed9cd80 (same cell, type and **shape**; checked, not removed)".
  - `p2/r01_clause_b.py` instead keys on `(level, cell, leaf, type, raw vertex)`.
  - 3-14 (`d35b565`, `eo_clip` in `bg_shape`) is the even-odd stitch fix. Its stated purpose is to stop emitting the chord/clip connector vertices that 3-12 (C) identified as the failing vertices. Any fix of that kind moves or deletes the bad vertex, so (b) fails by construction for every fixed row.
  - The control confirms the test is vertex-sensitive, not shape-sensitive. Even for non-failing vertices in footprint-equal `eo_bg_stitch` leaves, 20.8% (70,726 of 340,772) are "absent". The 0% for failing vertices against 79% for ordinary ones is exactly the signature of a targeted fix.
  - `r01_join.json` itself says `clause_b_item_still_checked: "NOT TESTED ... no per-item checked identity on 4ed9cd80"`.
  - **Reviewer probe** (`output/scratch-39/review/shape_probe.py`, 60 random R01 cells, footprint-equal only, 1,338 R01 rows, reason 4, `onb` 0):
    - 1,338/1,338: a class>0 record of the same type is still in the same leaf on `4ed9cd80`;
    - 1,338/1,338: the original record's bytes no longer appear;
    - 0 failing vertices are at the same raw position;
    - the nearest same-type vertex is a median of 110 raw away (51 within 16 raw, 1,010 within 256 raw, max 1,516).

  So the shapes persist in re-encoded form, and K1 checks them with 0 failing (background checked rises to 176,386,506). Under the design's own wording, that is prima facie (b) **satisfied**, not failed.
- *Consequence.* The following claims are unsupported:
  - "R01 exclusivity vs build holds for 920,693 rows";
  - "removed rather than fixed";
  - "Open question 1 is not raised: no row satisfies both";
  - "no remainder row can be build-fixed".

  The plan's own rule ("a row vanishing on a later disc is not a cause") is broken in reverse: the vanishing is used to confirm checker and to deny build.
- *Fix.*
  1. Redefine the item at shape level: same leaf, same type, and a record traceable to the same spool source. Use the dump `src_*` fields, or a window CF at `d35b565` (spool minus source) as in P3. Then decide (b) by "the source still produces a checked record in the leaf".
  2. Rerun on R01 and on all rows.
  3. If (b) holds for R01, the rows satisfy both the checker rationale (Amendment 4) and build-fixed. Raise design open question 1 (dual cause) to Cody via Design. Do not discharge R-G5-4.
  4. Until then, revert the R-G5-4 status to open and restate it as "predicate result undetermined: vertex-level test cannot separate fix from removal".

**F2 — HIGH. The overclaim has been written into live surfaces.**
- *Evidence.*
  - The `rules_bg.json` R01 note (in commit `7ef7450`) says "R01 exclusivity vs build holds … removed by 3-14 rather than fixed".
  - `docs/OVERVIEW.md` says "R01 exclusivity holds for 920,693 rows".
  - `residuals.tsv` R-G5-4 reads "DISCHARGED".
  - The R-G5-1/2 text reads "none is build-fixed".
  - Even without F1, failing the build-fixed predicate does not prove exclusivity. It only means the design's sufficient condition for build was not met. Design outcome 2 asks for "proven, disproven or mixed".
- *Fix.* Reword all four surfaces to the measured fact only: "failing vertex absent at the same raw position on `4ed9cd80` (0 of 920,693); shape-level clause (b) not yet tested". Keep R-G5-4 `blocks-phase3`.

**F3 — MEDIUM. `cause_table.md` contradicts itself.**
- *Evidence.* The rewritten 65623 paragraph says it is "classified". The very next paragraph (unchanged) still ends: "The contract requiring classification of polygon 65623's alleged defect is therefore **unmet and explicitly reported**".
- *Fix.* Drop or rewrite that sentence to point at the plan 39 classification.

**F4 — MEDIUM. The BOM entry for scratch-39 is missing (project CLAUDE.md rule; design P1 Surfaces lists `docs/provenance.md (scratch-39)`).**
- *Evidence.* `docs/provenance.md` has no `scratch-39` entry. It also does not record the following, which the record depends on:
  - the `open-pajero-maps-39-b7c7c42` worktree;
  - `p3/spool_cf65623` (symlinks plus a private `level_0.idx`);
  - the dumps (5.7 GB total);
  - `allrows/*.status.u8`, which `assignment.tsv` cites as the per-row record.
- *Fix.* Add a `scratch-39` section: contents, producers (`run_k1.sh`, `run_rows.sh`, `run_p3.sh`, `make_cf_spool.py`, `allrows_clause_b.py`), regeneration commands, and the deletion policy (design decision 4).

**F5 — LOW–MEDIUM. Design P3 contract 4 is not addressed.**
- *Evidence.* The design says: "If the old 3C narrative's 'disc defect near 65623' refers to a specific cell or footprint, it is located from the 3C record and checked on all discs." IMPLEMENTATION is silent on this. The P3 evidence covers `87a01b14` only.
- *Fix.* Either state "the 3C record names no specific cell/footprint", citing where you looked (the D4/D6 covers `(1728,162)` and `(1771,203)` are other sources per cause_table), or locate it and check it on `87a01b14`, `013586b5` and `4ed9cd80`.

**F6 — LOW. Two P3 statements lack backing.**
- *Evidence.*
  - (a) "The meet test agrees with the cf on 600 sampled cells (300/300)": no script or output for this exists in `p3/` or `output/scratch-39/`.
  - (b) The window is justified as "bounding rectangle of type-288 failing rows inside the source bbox". That shows the window covers the candidates, not that it covers every leaf the source could produce into. I verified that it does contain the source bbox in cell terms (ix 1414.7–1888.4, iy 275.0–748.8).
- *Fix.* Commit the sample script and output, or drop the sentence. State the source-bbox-to-cell containment explicitly. Optionally note that identical-byte twin records in a leaf are attributed arbitrarily by the multiset diff (harmless here: 0 produced rows, and twin records carry identical vertices).

**F7 — LOW. Two gaps in the R-G4-1 explanation.**
- *Evidence.*
  - (a) Confinement is at band level (35 bands), not per cell as design contract 2 asks. Exactness of Σ counts over the 37 cells closes this only modulo cancelling deltas elsewhere in a shared band.
  - (b) Only the *sum* bg + bb = 861,107 is derived. The 839,197 / 21,910 split per kind is not.
- *Fix.* One sentence noting (a). For (b), either classify the 861,107 unread vertices by K1's boundary test and match the split, or reword R-G4-1 to "sum explained; split per kind follows K1's on-boundary test, not derived".

**F8 — LOW. Stale or contradictory record text.**
- *Evidence.*
  - The IMPLEMENTATION P2 section says "`rules_bg.json`: unchanged … note text update is left to close-out", but `7ef7450` (P2) edits the note, and "Surfaces updated" says it changed.
  - `r01_join.json` still says clause (b) "NOT TESTED".
  - `OVERVIEW.md` and `residuals.tsv` link to `docs/plans/39-historical-bg-cause-counterfactual-ledger.md`, which does not exist until close-out.
- *Fix.* Align the P2 text with the commit. Annotate `r01_join.json` as superseded by `r01_clause_b.json`. Make sure close-out creates the linked record.

**F9 — INFO. `assignment.tsv` at count level.** This is a disclosed deviation, and it is acceptable only together with F4 (a BOM for the per-row `status.u8`). After F1 is fixed, its R01 row must change cause/reason. The remainder row's "removed-by-3-14 or footprint-changed" must not be read as a cause.

## Required to reach PASS

F1, F2, F3 and F4. F5–F8 can be follow-ups.
