# Group note — `r-absent-complete-repair-zero` (unit 2-02)

Phase 2 science group. Closed by the plan-14 reproducer
`triage/complete_repair_2-02.py`, not by restating 3-15's
`checker:repaired-not-representable` label (DESIGN Assumption 5).

## Membership rule

Phase 1 rows with `R_polygon_count == 0`, except native dump_row **335**
(source-evidence gap; goes to 2-03). That is **432** seeds. A seed is a
**member** iff every even-odd-repaired face of its meeting spool source
yields **0** representable demanded-type pieces after clipping to the target
cell. This must hold under both:

1. the Python mirror of `_cenc.c:emit_piece` **including densify**
   (`lim = 127·mc − 1`), then rint/dedup/spike/`q<3`/`area2==0`; and
2. production C `kw__bg_shape` (scratch probe `#include`s `_cenc.c`), run on
   the original ring and on every repaired face.

## Result

**432 / 432 members, 0 rejects.** 1,664 EO faces, of which 495 clip into the
target cell. Every one quantises to `area2 = 0` or `q < 3`. Production C
records: 0 for every original ring and 0 for every repaired face.

## Artefacts

- `triage/complete_repair_2-02.py`: the reproducer
- `triage/2-02_r-absent-complete-repair-zero_members.tsv` (432 rows)
- `triage/2-02_r-absent-complete-repair-zero_rejects.tsv` (header only)
- the plan 14 record `docs/plans/14-completeness-root-cause.md` (2-02 handoff, summarised)
- scratch proofs: `output/scratch-14/complete_repair/`

## 3-16 citation (exclusion only)

All 89 `in_added_89` members appear in `completeness_3-16_outcomes.tsv` as
`fail` (0/89 EO-stitch face-bypass recovery). That result is cited only to
exclude EO-stitch bypass. The positive close is this unit's complete-repair
zero-emit result.

## Expected movement (Phase 3, not applied)

There are two possible outcomes:

- The checker stops demanding these 432 identities, so failing completeness
  drops by 432.
- Proven non-deviation: R lacks the type in all 432 (Phase 1 `R_polygon_count
  == 0`) and G lacks it (`G_polygon_count == 0`). G matches R under the
  builder clip/densify/round contract, so the demand is inapplicable.
