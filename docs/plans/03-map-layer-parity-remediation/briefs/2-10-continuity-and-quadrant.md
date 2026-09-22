# Brief: 2-10 — cross-parcel continuity and divided quadrant containment (criteria 2 and 3)

Consumer: implementation worker; the numbers are consumed by the Phase 2 gate verdict (2-12) as criteria 2 and 3.
Owned paths: `parser/tools/continuity_census.py` (new), `parser/tests/test_continuity_census.py` (new), `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-10.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-09 (`parser/tools/r_neighbours.py` — the leaf-neighbour lookup).
Runs alongside: 2-11.
Budget: 10 files to read, about 350 lines to change, 55 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (user) — grounded phase gates": the definition of a grounded criterion, "#### Phase 2 — Outcome, as amended" criteria 2 and 3, the "Carried into the re-run" paragraph, and the Assumption Ledger entry "Coordinate range 4096/16384 is the true full-cell range".
2. `docs/plans/03-map-layer-parity-remediation/briefs/2-09-neighbour-lookup.md` — the neighbour API you consume (`LeafIndex`, `neighbour`, `status`, `crossing`, `handles`, `divided`), plus 2-09's handback for any signature it changed.
3. `parser/tools/overlay_test.py` — `DECODER_RANGE`, `_raw`, `_links`, `decode_uv`, `extent_m`, `RReader` (`blocks`, `leaves`, `decode`), `_class_key`, `tile_frame`, `spread`, `model_frame`, `class_range`. This is the substrate: raw coordinates, frame handling and class keys all exist already. Do not modify it.
4. `parser/harness/walk.py` — `_leaf_frame`, `_frame_range`, `_narrow_bounds`, `_tile_bounds`, `WalkedParcel`'s docstring.
5. `parser/refdata/profile/coord_scale.json` — `ranges` (per class `max`, including `"0".divided.pardiv1_sub0.max = 2048`) and `class_rule`.
6. `docs/schema/map-frame.md` — the parcel-division section (2x2 type-1 layout, sub-parcel ordering) and the coordinate-frame section.
7. `parser/tests/test_overlay_test.py` — the synthetic-fixture and tool-import patterns, including the PARENT bbox fixture used for a divided sub0.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Two per-record invariants with stated denominators, measured without the circularity the amendment named:

- **Criterion 2** — geometry that meets a shared parcel edge is continuous across it once both sides are projected under the frame hypothesis, and is *not* continuous under the alternatives.
- **Criterion 3** — every shape point of divided sub-parcel *k* falls inside quadrant *k* of the parent leaf's frame.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23, Phase 2 criterion 2: "Geometry crossing a shared parcel edge is continuous under the hypothesis and discontinuous under the alternatives. Median edge-node separation, with the alternative-hypothesis separations beside it; the pass condition is zero pairs above one raw coordinate unit, or an enumerated residual."

Cited, the same amendment, criterion 3: "Every shape point of divided sub-parcel k falls inside quadrant k of the parent leaf's 4096 frame. Per-point violation count over every divided parcel on the disc; zero violations."

Cited, the same amendment, on criterion 2's status: "**criterion 2's divided result is provisional** until it is re-measured at a tolerance fixed in absolute raw units rather than as a percentage of range" — a range-relative edge-selection tolerance is circular, because the quantity under test sets which nodes are selected.

Cited, the same amendment, on thresholds: a grounded check's threshold is "stated in the tool's docstring before any run". **Every constant below is fixed at refine time. Put them in the module docstring with the words "pre-stated, not tuned", and do not change one after seeing a result. If a constant turns out to be wrong, that is a `needs context` report, not an edit.**

Pre-stated constants:

- `EDGE_TOL_RAW = 4` — a node is an edge node when its raw crossed-axis coordinate is within 4 **raw coordinate units** of 0 or of the class range. Absolute, identical for every class and every hypothesis.
- `PAIR_TOL_RAW = 16` — two edge nodes on opposite sides of the edge pair up when their along-edge raw coordinates agree within 16 raw units, after mapping both to the shared edge's own parameter (see below). Absolute.
- `PASS_RAW_UNITS = 1.0` — pass means every matched pair's projected separation is at most one raw coordinate unit expressed in metres, i.e. `max(width_m, height_m) / range` of the frame in question. Zero pairs above it, or a residual enumerated pair by pair with ids, coordinates and separations.
- `MIN_PAIRS_PER_CLASS = 300` for the full-leaf classes; the divided class is measured over its **whole population**, not a sample.

Anti-circularity, binding: selection (`EDGE_TOL_RAW`) and pairing (`PAIR_TOL_RAW`) run **once**, under the frame hypothesis of record, in raw units. The resulting pair set is then re-scored **unchanged** under every alternative. No alternative may add, drop or re-pair a node. Say this in the docstring and make it structurally true in the code: one function produces the pair list, a second scores a pair list under a frame model.

Hypothesis of record, settled and not to be re-derived: the frame is `overlay_test.model_frame` — parent bbox at the sub's range for a divided sub-parcel, the 4x4 tile bbox for an L0 sparse tile, the leaf bbox otherwise (2-05, commit 2f874e3) — with the class range from `class_range` and y increasing northward (2-06). Alternatives to score: `range / 2`, `range * 2`, `DECODER_RANGE` (32768), and for the divided class additionally the sub-parcel's own leaf bbox at its own range. Report each alternative's median and minimum separation with **no pass threshold**: they are two-sidedness evidence, and the amendment asks only that they be discontinuous.

Reproduction targets from the retired scratchpad census, for comparison only — they are not a pass condition and you must not tune toward them: median 0.0 m at L2, L4, L6, L8, L0 urban and L0 sparse; `divided_pardiv1` median 122 m, provisional. If your absolute-unit measurement disagrees with any of these, report the disagreement with numbers; **a worse divided number is a finding about the format, not a bug to hide.**

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. R only; **no OSM input at all**, and no OSM-derived comparison — this is an internal-consistency check. Python: `.venv-rp/bin/python`. Reads R through `parser/harness/` reading paths, `overlay_test.RReader` and `r_neighbours`; imports no writer module. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

`parser/tools/continuity_census.py`, one tool with two censuses and one `main()` writing `EVIDENCE-2-10.json`.

**Continuity census (criterion 2).** For each class, walk a deterministic sample of leaves (state the rule: `overlay_test.spread` over the level's block list, then leaves in index order, until `MIN_PAIRS_PER_CLASS` pairs or the population is exhausted; L8 and the divided class are small, so state the population you found). For each leaf and each edge in `("E", "N")` — E and N only, so each shared edge is visited once — resolve the neighbour with `r_neighbours`, decode both sides with `RReader.decode`, take link end-nodes (`_links(...)["ends"]`), select edge nodes by `EDGE_TOL_RAW` on the crossed axis, pair by `PAIR_TOL_RAW` on the along-edge axis, and score each pair as the great-circle or planar metre distance between the two `decode_uv` results. Handle these cases explicitly, each counted in the JSON and none silently dropped: `outside_coverage` and `empty_slot` from `r_neighbours` (excluded from the denominator), a neighbour that is a divided parent, an edge whose two frames differ in along-edge extent (`scale_mismatch`: convert the along-edge tolerance by the exact frame-scale ratio if the extents are exact multiples, otherwise exclude and count), and an edge node with no partner within `PAIR_TOL_RAW` (`unpaired` — reported per class, since a high unpaired share undercuts the median even when the paired residual is zero).

For the divided class, pairs are the **sibling** edges inside one parent: sub0|sub1, sub2|sub3 share a vertical edge; sub0|sub2, sub1|sub3 share a horizontal one. Sub-parcel ordering, settled: sub0 = SW, sub1 = SE, sub2 = NW, sub3 = NE.

**Quadrant census (criterion 3).** Over **every divided parcel on the disc at every level** (no sampling), decode each sub-parcel and test every shape point — road node x/y, road intermediate points, and background vertices, the same three sources `coord_scale_census.parcel_measure` enumerates — for raw containment in quadrant *k* of the parent frame: with `HALF = 2048` and `(qx, qy)` from k (sub0 → (0,0), sub1 → (1,0), sub2 → (0,1), sub3 → (1,1)), require `qx*HALF <= x <= (qx+1)*HALF` and `qy*HALF <= y <= (qy+1)*HALF`, bounds inclusive, in the **parent's** 4096 frame. If the stored coordinates are sub-local (0..2048) rather than parent-local, the containment statement is about the offset you add; make which one R actually uses an explicit, reported finding with the numbers for both readings, and do not pick the reading that passes without saying you did. Zero violations is the pass condition; report `n_parents`, `n_subparcels`, `n_points`, `violations`, and up to 10 violation examples. Report the population you found against the recorded 42 divided parents (13 L0, 4 L2, 13 L4, 7 L6, 5 L8) and the 52 content-bearing sub-parcels; a difference is a finding, not something to reconcile silently. If any parcel uses a division type other than type 1 (2x2), stop and report `needs context` — the recorded census found none.

**Evidence JSON.** Per class: `n_leaves`, `n_pairs`, `median_m`, `p90_m`, `max_m`, `over_threshold`, the excluded-case counts, `unpaired`, and the alternative-hypothesis medians. Plus the quadrant block, the pre-stated constants echoed verbatim, the sample rule in words, and a `verdict` per criterion of `"pass"`, `"pass_with_residual"` or `"fail"` by the rules above. **A `fail` is written as `fail`.**

### Keep untouched

`parser/tools/overlay_test.py`, `parser/tools/r_neighbours.py`, `parser/tools/coord_scale_census.py`, `parser/tools/header_word_census.py`, `parser/harness/**`, `parser/kiwiw/**`, `parser/refdata/**`, `docs/schema/**`, `docs/plans/**/DESIGN.md`. Do not update the Assumption Ledger; 2-12 handles the ledger.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_continuity_census.py -q` passes, with synthetic-fixture tests (no disc) for: an exactly continuous pair scoring 0 m under the hypothesis and non-zero under `range * 2`; the pair set being identical across hypotheses (assert it, do not eyeball it); a node 5 raw units from the edge not being selected while one 4 units away is; `scale_mismatch` and `unpaired` counted rather than dropped; quadrant containment passing for an in-quadrant point and failing for a point one unit outside, for all four k.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts before and after).
- `.venv-rp/bin/python parser/tools/continuity_census.py --reference /run/media/codyh/464210-8480 --out docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-10.json` run **twice** with identical output (report the `sha256` both times).
- In your handback, a table: per class, `n_pairs`, median m, max m, `over_threshold`, `unpaired`, and the `range * 2` median beside it; then the quadrant line (`n_subparcels`, `n_points`, `violations`); then the two verdicts. Give the divided-class number plainly whatever it is.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. State explicitly whether any pre-stated constant was changed after a run — the answer must be no.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
