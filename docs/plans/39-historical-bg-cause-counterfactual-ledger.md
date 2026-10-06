# Historical background-family causes by counterfactual: 3-11 checked moves, 8,739 + 137 remainder, polygon 65623, R01 exclusivity

Plan 39 took the five background-family rows that plan 35 left without a
cause. It held the checker and the spool fixed and varied only the disc
(`87a01b14` 3C-04 replay → `013586b5` 3-11 → `4ed9cd80` 3-14) or only the
build (a counterfactual spool without one source). Two rows were discharged:
- **R-G4-1:** the 3-11 checked moves are exactly the 167,936 records hidden by
  the O06 count wrap;
- **R-G5-3:** polygon 65623 produces no failing item.

R01 exclusivity (R-G5-4) was **disproven** by count and discharged for the
proven rows. 825,634 R01 rows were proven, with an identity guard, to be fixed
by the 3-14 build change. Per Design's advance ruling, they take
`build:eo_bg_stitch`, and R01's rationale is recorded as superseded. The rows
whose fix is not proven (94,134 weak identity, 925 untraceable, 80 untested)
stay `checker` as named children R-G5-4-a/b/c. The remainder's row identities (R-G5-1, R-G5-2) could not
be regenerated, because their side-column producers are deleted. Their
count-level bound is stated. Plan 04 Phase 3 is **not** claimed closed.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual rows R-G4-1 and R-G5-1..4 from plan 35's `residuals.tsv`:
- the 3C-04 → `013586b5` checked moves;
- 8,739 background_boundary and 137 background historical unassigned rows;
- Region polygon 65623;
- R01 exclusivity against build.

Never relabel: a row vanishing on a later disc is not a cause. Oracle `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448` or later. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`, bounded or streamed. Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief. Do not reseat 170, 3-16 or 3-17.

## Why This Existed
Plan 04 Phase 3 requires every 3C-04 failing item to have exactly one cause.
Plan 35 left these rows open:
- **G4:** the 3-11 hop's checked moves were recorded but not explained.
- **G5:** the 8,739 background_boundary and 137 background rows (180 groups)
  had no cause, and their mapping to the 3C-04 basis was not stated.
- **G5:** the "disc defect near polygon 65623" was unestablished.
- **G5:** R01's checker attribution (920,773 rows) had never been tested
  against the build. 3-14, a build-only change, had taken R01 to 0.

## What Was Built
**Changed:** evidence under
`docs/plans/04-c-core-orchestration/triage/historical_bg/` (`p1`, `p2`, `p3`, all
scripts and small JSON; `p2/assignment.tsv`; `protected_after_39.json`); the
R01 note in `triage/rules_bg.json` (note only); the 65623 section and an R01
note in `triage/cause_table.md`; the OVERVIEW historical-remainder clause; a
`scratch-39` section in `docs/provenance.md`; and `residuals.tsv`. No source code changed. No protected disc or spool was
written; the snapshot is unchanged.

### Phase 1 — basis reconstructed; R-G4-1 explained
- **3C-04 reproduces.** HEAD K1 on the `87a01b14` replay matches 3C-04 in
  every kind except completeness (65 vs 752, plan 14's rule). K1 built at
  `1cf40f8` matches all nine kinds exactly.
- **3-11 moves confined.** Every non-L0 delta is 0. Per cell row (plan 36's
  `k1_rows.py`), 35 bands hold the 37 changed cells, and no other band moves.
- **3-11 moves explained exactly.** In the 37 cells, record bytes and the other
  sections are identical. 41 elements wrapped their unit count, which hid
  167,936 records from every reader. Each delta is an exact count over those
  records:
  - range = vertices (861,107);
  - step = vertices − records (693,171);
  - background + background_boundary = vertices;
  - interior_cover = 29 whole-leaf covers.
- **Remainder regeneration is blocked.** R01 alone reproduces (920,773 /
  920,786). The 3-13 rules S02–S05 need the side columns
  `s02_producer_verified` and `residual_crossing_verified`, whose producers are
  deleted (`docs/provenance.md`). So the 137 / 8,739 / 188 split and the 180
  groups cannot be rebuilt without a new producer scan.
- **Basis map.** Every failing row outside the 37 cells is identical, in order,
  on `87a01b14` and `013586b5`. Inside them, background goes from 144 to 157
  and background_boundary from 1,464 to 1,938.

### Phase 2 — counterfactual assignment
- **Clauses (a) and (c)** hold. 4ed9cd80 has K1 failing 0 in all three kinds,
  and every tested row's cell is in the 3-14 changed list with a plan 36 P3
  class (R01: `eo_bg_stitch` 920,693, `eo_division_ceiling` 80).
- **Clause (b), first attempt (vertex level), was withdrawn after review.** It
  keyed the item on the raw failing vertex and found none at its old position
  on `4ed9cd80`. A build fix moves or deletes exactly that vertex, so this
  cannot separate "fixed" from "removed".
- **Clause (b), shape level, with an identity guard.** The item is the old
  record that carries the failing vertex. It is identity-proven to persist if a
  same-type record in the same leaf holds at least one identity-bearing
  non-failing vertex at its exact raw position. Identity-bearing means no other
  old same-type record in the leaf holds it and it is not on the leaf edge.
  New records identical to an unchanged neighbour are excluded. Only
  footprint-equal cells can be tested. The thresholds are implementer choices.

  | population (87a01b14) | rows | identity-proven | weak (identity undetermined) | none | type absent | footprints changed |
  |---|---|---|---|---|---|---|
  | R01 | 920,773 | 825,634 | 94,134 | 925 | 0 | 80 |
  | background non-R01 | 517,785 | 489,589 | 26,785 | 461 | 928 | 22 |
  | background_boundary | 16,549,569 | 15,180,713 | 1,249,396 | 92,923 | 25,821 | 716 |

- **R01, cause per Design's advance ruling** (2026-10-06 12:54 AEST): a row
  that the counterfactual proves was fixed by the 3-14 build change, and that
  still satisfies R01's rationale, takes the build cause. The R01 rationale is
  superseded, not kept as a second cause.
  - 825,634 rows: `build:eo_bg_stitch`.
  - The 94,134 + 925 + 80 rows stay `checker` (design rule 3) as R-G5-4-a/b/c.
  - `rules_bg.json` changed only its note; the per-row cause of record is
    `historical_bg/p2/assignment.tsv`.
- **Remainder:** at most 123,335 background and 1,368,856 background_boundary
  rows of `013586b5` fail, or cannot be proven to satisfy, the predicate.
  Without the row identities, no remainder row is assigned.
- `assignment.tsv` is count-level. The per-row arrays are kept, keyed by row
  identity, in `output/scratch-39/keep/` (see Deviations).

### Phase 3 — polygon 65623 classified
- **Counterfactual build.** At `b7c7c42` (the `87a01b14` producer), over the L0
  window `[1414,1890)×[274,750)`: the pinned spool vs the same spool without
  the source's home cell. The control frames equal `87a01b14` in all 226,576
  cells. The source produces 58,032 type-288 records in 58,030 leaves.
- **The window is exhaustive.** A product must be L0, type 288, with vertices
  inside the source bbox. Every such failing row lies in the window.
- **Join** (every mapping validated against the record bytes): 0 rows produced
  in every kind.
  - background: 0 of 1,438,558;
  - background_boundary: 0 of 16,549,569;
  - interior_cover: 0 of 824;
  - completeness: 0 of 752 (3C-04 rule) and 0 of 65 (HEAD rule), with no row
    in a cell the ring meets;
  - name_anchor: 0 of 1.
- **Classification:** no 3C-04 failing item is produced by source 65623. Its
  long closing edge and the absence of any proper crossing stay recorded as
  facts, not as a cause.

## Deviations
- Design Phase 1 item 3 (regenerate the 9,064 remainder with identity tables)
  is **unmet**: the side-column producers are deleted. The block is stated
  exactly, and its consequence is bounded at count level.
- `assignment.tsv` is count-level, not per row. Per-row shape status for every
  background-family failing row lives in `output/scratch-39/shape/` (git
  ignored), keyed by row identity in `keep/`, which survives the deletion of the
  dumps (BOM in `docs/provenance.md`). It can be regenerated with
  `p2/shape_clause_b.py`.
- The first clause (b) test was vertex-level and wrongly concluded "removed by
  3-14" (review F1). For a while that overclaim was written into the R01 note,
  OVERVIEW and `residuals.tsv`; all three were corrected before close.
- A first dump reader used a packed layout and misread fields after `level`.
  Every affected step was re-run with the aligned layout.
- Short unlocked analyses may have overlapped some heavy steps. Heavy steps
  were always serial under the lock.

## Review
Claude CLI clean-context seats (disclosed; Codex weekly-limited until
2026-10-10). The texts are kept in `triage/historical_bg/reviews/`.
- **First review: FAIL.** One blocker, F1: the vertex-level clause (b)
  cannot separate "fixed" from "removed". Its overclaim (F2) had already been
  written into live surfaces. F3–F8 were documentation and BOM gaps.
- **Rework:** a shape-level clause (b), with the overclaims withdrawn and the
  `scratch-39` BOM added.
- **Re-review: PASS_WITH_FOLLOWUPS.** F1–F8 were fixed. N1 (medium) asked for
  an identity guard: about 15 % of the weak tier rested on vertices a
  neighbour could supply. N2 asked for the both-kinds failing-vertex
  exclusion. N3 found BOM sizes wrong and the per-row arrays depending on
  dump order. N4 asked for the dual-cause framing.
- **Applied after the re-review:**
  - N1: the guard was implemented and re-run (656 s, under the lock), and the
    surfaces were restated by tier.
  - N2: documented; the deviation is conservative.
  - N3: sizes corrected and keyed arrays kept.
  - N4: answered by Design's 12:54 ruling.

  The guarded re-run was not sent for a third review.

## Residual Risks
- The guard's leaf edge is the leaf's vertex bbox, an approximation of the
  leaf rectangle. Identity rests on exact shared vertices, so a new record
  from another source that lands on an identical interior vertex would pass.
  This is unlikely but not excluded.
- The rows in footprint-changed cells (80 R01; 102 background and 716
  background_boundary in total) are untested by construction.

## Follow-ups
- **R-G5-1, R-G5-2** (blocks-phase3, owner Design): the row identities need a
  new producer scan for the deleted side columns. This is a Design ruling.
- **R-G5-4-a** (94,134 rows, weak identity), **R-G5-4-b** (925 rows,
  untraceable; `checker` stands) and **R-G5-4-c** (80 rows, untested in
  `eo_division_ceiling` cells). All are blocks-phase3, owned by Design, which
  may reclassify them. a and c need more work (a per-source counterfactual, or
  a window counterfactual at `d35b565`) or a waiver.

## Decisions Worth Keeping
- A row that disappears on a later disc is classified by whether its item is
  still checked there. The item is the shape (record), not the failing vertex,
  because a fix moves the vertex. "Removed" is never "fixed".
- Dump rows are read with the C struct's natural alignment (`align=True`).
