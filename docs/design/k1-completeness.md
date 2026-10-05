# K1 completeness demand

K1 `completeness` checks, for each `(cell, type)` that a spool class-2 polygon demonstrably meets, that the decoded disc holds at least one polygon piece of that type in that cell. The C checker (`parser/kiwiw/_k1_cmp.c`) and the Python oracle (`parser/tools/quantisation_roundtrip.py`, `_required_cells` and the completeness block of `_check_block`) give equal verdicts.

## Demand

A pair is demanded when a polygon of the type meets the cell by one of three branches:
- (a) the polygon lies inside one cell rectangle and its ring, rounded to the raw lattice, has non-zero area;
- (b) a crossing polygon has a vertex at least one raw unit inside the cell;
- (c) the cell centre is inside a polygon of the type: `Region.inside`, even-odd per polygon, with `TOL` slack along the scan line.

The demanded-pair count is the kind's `checked` value.

## Failure requires a representable footprint

A demanded pair whose piece is absent fails only if at least one of its demanding shapes has a **representable in-cell footprint**. The test is:
1. take the shape's even-odd faces;
2. clip each face to the cell;
3. densify with the shape's own multiplier (`lim = 127·mult − 1`);
4. round to the lattice (`rint`);
5. apply adjacent-duplicate and spike removal;
6. require at least three distinct points and non-zero lattice area.

Even-odd topology covers proper crossings, repeated vertices, endpoint-on-edge contacts and collinear overlap. Parity cancellation is preserved, so a retraced contour is empty. There is no fallback to the original contour. Unsupported numeric cases raise an error; they never pass silently.

A pair whose demanders are all unrepresentable passes. The wire format cannot carry its footprint, so no builder could emit a piece there.

## Independence

The test is an independent implementation of the wire contract, in C (`_k1_cmp.c`) and Python (`parser/tools/k1_representable.py`). It never calls the encoder's `emit_piece`, `kw__bg_shape` or EO/clip code: a checker that reuses the encoder cannot catch an encoder drop. The per-shape multiplier is carried through local and tall shapes (`k1_shapes`, the `k1_tall` rows in `parser/kiwiw/cenc.py`, and the Python `Shapes`).

## Guarantees and tests

- Branches, `TOL`, `SEARCH` and `checked` are unchanged by the representability filter. Only `failing` can move.
- Positive controls (`parser/tests/test_k1_completeness_representable.py`) must keep failing when G lacks the piece:
  - a representable square;
  - a sliver that survives densify and rounding;
  - a bowtie with one representable lobe;
  - two lobes touching at a vertex;
  - a ring that survives only with multiplier 2;
  - any representable second demander.
- Real-data control: on the pre-3-14 disc `scratch-3-11/G_new` (`013586b5…`), the checker fails exactly the 52 keys that the later build fix repaired.

## Per-rule assignment of completeness rows

Promoted from plan 28 ([record](../plans/28-phase1-per-rule-classify-recovery.md)).

- Each completeness failure row gets its per-rule assignment from the classifier, run over a dump extended with the byte-145 `other_mechanism` column. The column is produced by `parser/tools/dump_join.py --mode other_mechanism`. That mode is read-only on its inputs: it refuses path, symlink and hard-link aliases of the source binary, manifest and side table. The side table comes from `docs/plans/04-c-core-orchestration/triage/per_rule_completeness_mechanism.py`.
- The classifier runs on the completeness projection of `rules_other.json`. The projection holds rules O01, O04, O05 and O06, with their raw rule objects byte-preserved and their order fixed (`per_rule_rules_completeness_projection.json`, with hashes in `per_rule_projection_hashes.json`). O06 is excluded from completeness because a contract proof holds against `_cenc.c`.
- `NO_RULE` is a valid recorded outcome. The classifier's `PARTITION FAIL` exit 1 on this projection is expected and is not an evidence gap. Every row has a recorded assignment even when no rule fires.
- Current contract (plan 28, 776 rows): O01 363, O05 132, O04 7, O06 0, NO_RULE 274. These join one-to-one onto the 342 + 434 proven plan-14 causes as 769 consistent and 7 conflict-proven (the O04 spool rows). Pins and joins: `per_rule_classify_assignment.tsv`, `per_rule_phase2_join.tsv`.
- Regression tests: `parser/tests/test_dump_join_other_mechanism.py` and `parser/tests/test_dump_join_memory.py`.
