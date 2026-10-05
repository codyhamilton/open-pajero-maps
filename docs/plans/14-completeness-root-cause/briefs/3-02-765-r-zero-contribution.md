# Brief: 3-02 — dump_row 765: prove the R polygon contributes 0 cell-local records

Consumer: Codex `gpt-6.1-sol`, reasoning high, in worktree `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached HEAD at the plan tip).
Owned paths: `docs/plans/14-completeness-root-cause/triage/r_contribution_3-02.py`, `docs/plans/14-completeness-root-cause/triage/r_contribution_3-02.tsv`, `docs/plans/14-completeness-root-cause/triage/phase3_groups.md`, `docs/plans/14-completeness-root-cause/triage/phase3_membership.tsv`, `docs/plans/14-completeness-root-cause/reports/3-02-765-r-zero-contribution.md`, scratch under `output/scratch-14/r_contribution/` and `output/scratch-14/runs/`. Touch nothing else. Do not edit any Phase 1/2 artefact, including `phase2_membership.tsv`.
Commits: Commit to the current detached HEAD when done evidence passes, with a plain-summary title and no trailer. Do not push.
Report: before committing, write `docs/plans/14-completeness-root-cause/reports/3-02-765-r-zero-contribution.md` (a handoff; rubric in `tools/quality/checks/execution-report.json`) and include it in the commit.
Depends on: nothing.
Runs alongside: nothing (single worktree; heavy work is serialised).
Budget: 10 files to read, about 300 lines of new script, 50 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/14-completeness-root-cause/IMPLEMENTATION.md` (done, not done, what you learned), commit, and report `over budget`.

## Required reading, in order

1. `docs/plans/14-completeness-root-cause/DESIGN.md` — "Phase 3", the "Phase 3 refine" record (the **Design ruling on 765** is binding), and the Phase 2 Units table (the 2-02 membership definition).
2. `docs/plans/14-completeness-root-cause/triage/phase2_open_questions.md` — Q-tile-alias.
3. `output/scratch-14/witnesses/` — the R witness for dump_row 765. Also the 2-01 reject row for 765 in `triage/2-01_g-omits-cell-local-dvd-type_rejects.tsv`.
4. `docs/plans/14-completeness-root-cause/triage/cell_local_2-01.py` — `decode_slot_shapes`, `clip_rect` (R slot decode in global raw coordinates).
5. `docs/plans/14-completeness-root-cause/triage/complete_repair_2-02.py` — `decompose_eo_faces`, `encoder_piece_densified`, `CProbe`, `cell_b4` (reuse these by import).
6. `parser/tools/run_heavy_python.py` — usage.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Discharge the Design proof obligation for dump_row 765, key `(0, 1307, 1756, 291)`: show from actual geometry and emitted output that the single R polygon of code 291 in that R slot contributes **0 records** to cell (1307,1756). Then apply the ruling's branch.

## Contract

Design ruling (binding, quoted in DESIGN "Phase 3 refine"):
- 765 is its own Phase 3 unit. The proof uses the actual polygon geometry and the emitted output, not counts. Examples: the polygon lies outside the cell, or it clips or filters to nothing in the repaired source.
- **If proven:** in the Phase 3 record, amend the 2-02 definition to "R polygons contributing 0 cell-local records", cite the proof, fold 765 into 2-02, and re-check that all 432 still hold under the amended definition.
- **If not proven:** 765 stays a separate root-cause group with its own mechanism.
- Until this unit closes, the 2-03 accounting `776 = 342 + 432 + 335 + 765` is unchanged.

Inputs:
- R disc: `/run/media/codyh/464210-8480/ALLDATA.KWI` (read by byte range only; never copy the whole file).
- G disc: `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`).
- Spool: `output/extract_timing/spool`.

## Changes

- New `triage/r_contribution_3-02.py`. For a given key it:
  1. Decodes the R slot that covers the key cell and lists every R polygon of the key's type, with full decoded coordinates (global raw) and the R shape's mult.
  2. For each such polygon, records its bbox relative to the target cell rectangle `[ix·4096, (ix+1)·4096) × [iy·4096, (iy+1)·4096)`, using `cell_b4`'s convention.
  3. Applies the repaired-source path: `decompose_eo_faces` → clip each face to the target cell → `encoder_piece_densified(face, mc)` → production C `bg_shape` via `CProbe` for the target cell. It records mirror emits and C records.
  4. Records the **emitted-output** check: whether any decoded R piece of that type has ≥3 vertices and a non-zero rounded area inside the target cell. This is the R-side analogue of the checker's `present` set.
  5. A polygon contributes 0 records if C records = 0 **and** the emitted-output check finds nothing in the cell. State which proof applies: outside the cell, clips to nothing, or filters to nothing.
- Run on 765 first. Then run on all 432 rows of `triage/2-02_r-absent-complete-repair-zero_members.tsv` to re-check them under the amended definition. For those rows the R slot has no polygon of the type (`R_polygon_count == 0`), so each must report 0 polygons and 0 contribution. Assert this per row from the decode; do not copy the Phase 1 count.
- **Proven branch:**
  - `phase3_groups.md` states the amended 2-02 definition verbatim ("R polygons contributing 0 cell-local records") and cites the 765 proof JSON and TSV row.
  - It records 432/432 re-check results and the folded accounting `776 = 342 (2-01) + 433 (2-02 amended) + 1 (Q-source-335)`.
  - `phase3_membership.tsv` has the same columns as `phase2_membership.tsv`, plus `phase3_group`. It covers 776 rows, exhaustive and disjoint; assert both.
- **Not-proven branch:**
  - `phase3_groups.md` names 765 as its own group, with the mechanism the evidence shows: which polygon, which records, in which cell.
  - The accounting stays `342 + 432 + 1 + 1`. `phase3_membership.tsv` reflects that.
- Leave dump_row 335 as `open-question:Q-source-335` in either branch. 3-01 names its source, and its disposition is not this unit's.
- Runs go through `run_heavy_python.py --log output/scratch-14/runs/r_contribution_<n>.json`.

### Keep untouched

- Every Phase 1/2 artefact and `parser/`.
- The protected outputs: `output/scratch-3-11/G_new` (`013586b5…`), `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`), and `output/extract_timing/spool`.
- Never delete anything under an `output` path.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `… r_contribution_3-02.py --keys 765` → exit 0. The proof JSON shows the R 291 polygon's decoded coordinates, its bbox versus cell (1307,1756), mirror emits, C records, and the emitted-output result, plus a stated verdict `proven` or `not proven`.
- `… --keys 2-02` → 432/432 rows with 0 R polygons of the type and 0 contribution. If not, each failing row is named, and the proven branch is **not** taken.
- `phase3_membership.tsv` has 776 rows; the disjointness and exhaustiveness assertions pass. The group counts match the branch taken.
- Both protected disc shas are unchanged (record both).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then:
- the verdict on 765 and its proof (geometry numbers);
- the 432 re-check result;
- the branch taken and the resulting accounting;
- the check output before and after;
- any deviation from this brief and why;
- any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
