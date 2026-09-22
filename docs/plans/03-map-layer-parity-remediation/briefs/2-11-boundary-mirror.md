# Brief: 2-11 — boundary-node mirror check across resolved neighbours (criterion 4)

Consumer: implementation worker; the numbers are consumed by the Phase 2 gate verdict (2-12) as criterion 4.
Owned paths: `parser/tools/boundary_mirror_census.py` (new), `parser/tests/test_boundary_mirror_census.py` (new), `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-11.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-09 (`parser/tools/r_neighbours.py` — the leaf-neighbour lookup).
Runs alongside: 2-10.
Budget: 9 files to read, about 300 lines to change, 50 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (user) — grounded phase gates": the definition of a grounded criterion, "#### Phase 2 — Outcome, as amended" criterion 4, and the "Carried into the re-run" paragraph naming the same-block limitation.
2. `docs/plans/03-map-layer-parity-remediation/briefs/2-09-neighbour-lookup.md` — the neighbour API you consume (`LeafIndex`, `neighbour`, `status`, `crossing`, `handles`, `divided`), plus 2-09's handback for any signature it changed.
3. `parser/tools/overlay_test.py` — `DECODER_RANGE`, `_raw`, `_links` (note `"ends"` is the first and last node of each link), `RReader`, `_class_key`, `model_frame`, `class_range`, `spread`. Do not modify it.
4. `parser/harness/walk.py` — `_leaf_frame`, `_frame_range`, `_narrow_bounds`, `_tile_bounds`.
5. `parser/refdata/profile/coord_scale.json` — `ranges` per class, `class_rule`.
6. `docs/schema/map-frame.md` — the coordinate-frame section and the road-link/node structure.
7. `parser/tests/test_overlay_test.py` — the synthetic-fixture and tool-import patterns.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Show, per node and at exact integer equality, that a link end-node sitting exactly on a parcel edge is answered by a mirrored end-node in the parcel on the other side of that edge — including when that parcel is in another block or another blockset, which is the part the earlier census never tested.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23, Phase 2 criterion 4: "A link end-node whose raw coordinate is exactly 0 or exactly the class range is a genuine boundary crossing: the adjacent parcel holds an end-node at the mirrored coordinate, crossed axis = range - value, other axis unchanged. Per-node violation count; denominator all exact-coordinate nodes with a resolvable neighbour, with nodes at the extract's outer edge excluded from the denominator rather than failed."

Cited, the same amendment, "Carried into the re-run": "The mirror invariant was tested only on same-block neighbours, so block- and blockset-crossing neighbour lookup must exist before it is load-bearing."

Cited, the same amendment, on thresholds: a grounded check's threshold is "stated in the tool's docstring before any run". **The constants below are fixed at refine time. Put them in the module docstring with the words "pre-stated, not tuned", and do not change one after seeing a result. A constant that turns out to be wrong is a `needs context` report, not an edit.**

Pre-stated constants:

- `EXACT_ONLY = True` — a node qualifies only when its raw crossed-axis coordinate is **exactly** `0` or **exactly** the class range as an integer. No epsilon, no rounding window. Raw values recover exactly because decode and inversion use the same bbox (`DECODER_RANGE = 32768`), so "exact" is literal integer equality; if a class's raw values are not integral, that is a finding to report, not a reason to introduce a tolerance.
- `MIRROR_TOL_RAW = 0` — the mirrored node must satisfy `crossed == range - value` and `along_edge == value_along`, both at exact integer equality. The recorded scratchpad result was "matched to 0 raw units", so 0 is the pre-stated threshold.
- `MIN_NODES_PER_CLASS = 300` — the minimum qualifying nodes per class before a class's figure is reportable; L6, L8 and any smaller class are measured over their **whole population**.
- Pass condition: **zero violations** over the denominator, or a residual enumerated node by node with ids, both parcels' identifiers, and both raw coordinates.

Denominator, binding, and each exclusion counted separately in the output — never folded into the violation count, never folded into the denominator:

- `outside_coverage` — no neighbour cell on the level's global grid or no such block on the disc. This is the extract's outer edge; **excluded, not failed**, exactly as the criterion says.
- `empty_slot` — the neighbour block exists but the leaf slot is `NO_DATA`. Excluded, counted.
- `scale_mismatch` — the two frames differ in along-edge extent or in range, so "crossed axis = range - value" is not a statement about a single shared frame. This covers an L0 sparse tile frame facing a differently-framed neighbour and a divided parent facing an undivided leaf (`divided=True` from `r_neighbours`). Excluded, counted, and reported per class so the gate can see how much of R the mirror statement does not cover.

Everything else is in the denominator and is either `matched` or a `violation`.

Crossing evidence, binding: report `matched` and `violations` broken down by `r_neighbours`' `crossing` value (`same_block`, `cross_block`, `cross_blockset`). The amendment's condition for this criterion being load-bearing is that the cross-block and cross-blockset paths were exercised, so a zero in either of those columns must be stated plainly in the handback rather than left to be inferred from a table.

Reproduction targets from the retired scratchpad census, for comparison only and not a pass condition: L6 316/316 and L8 64/64 matched, same-block neighbours only. Report your figures beside them. Your denominators should be **larger** than those, because block-crossing nodes are now resolvable; if they are not, say so.

Settled and not to be re-derived: the frame of record is `overlay_test.model_frame` with `class_range` (2-05, commit 2f874e3), y increases northward (2-06), and edges are W/E on longitude and S/N on latitude.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. R only; **no OSM input at all**. Python: `.venv-rp/bin/python`. Reads R through `parser/harness/` reading paths, `overlay_test.RReader` and `r_neighbours`; imports no writer module. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

`parser/tools/boundary_mirror_census.py`, with `main()` writing `EVIDENCE-2-11.json`.

- Walk per class over a **stated deterministic sample**: full population at L6, L8 and any level with fewer leaves than the sample rule would select; for L0 urban, L0 sparse, L2 and L4, `overlay_test.spread` over the level's block list with a stated block count, then every leaf of each chosen block, until `MIN_NODES_PER_CLASS` qualifying nodes or exhaustion. Write the rule into the JSON in words.
- For each leaf: decode with `RReader.decode`, take link end-nodes, and for each of the four edges keep the nodes whose crossed-axis raw coordinate is exactly `0` (W or S) or exactly the range (E or N). Resolve that edge's neighbour with `r_neighbours`, classify the exclusions above, and on a resolved same-scale neighbour decode it and look for an end-node at `(range - value, value_along)` at exact equality. Visit all four edges (unlike 2-10's continuity census, a node is a property of one parcel, and both directions must hold).
- A qualifying node exactly at a **corner** (both axes exact) has two edges and therefore two neighbour statements; count it once per edge, and say so in the JSON, so the denominator is defined as node-edge incidences rather than nodes. Name the count of corner nodes separately.
- Record, for every violation, the source parcel identifiers, the edge, the raw coordinates, the neighbour's identifiers and its nearest end-node in raw units, so the residual can be read without re-running.
- Evidence JSON, per class: `n_leaves`, `n_candidate_nodes`, `denominator`, `matched`, `violations`, `outside_coverage`, `empty_slot`, `scale_mismatch`, `corner_incidences`, the `crossing` breakdown of `matched` and `violations`, up to 20 violation examples, the pre-stated constants echoed verbatim, the sample rule in words, and a `verdict` of `"pass"`, `"pass_with_residual"` or `"fail"`. **A `fail` is written as `fail`.**

### Keep untouched

`parser/tools/overlay_test.py`, `parser/tools/r_neighbours.py`, `parser/tools/continuity_census.py` (2-10 owns it), `parser/harness/**`, `parser/kiwiw/**`, `parser/refdata/**`, `docs/schema/**`, `docs/plans/**/DESIGN.md`. Do not update the Assumption Ledger; 2-12 handles the ledger.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_boundary_mirror_census.py -q` passes, with synthetic-fixture tests (no disc) for: a node at exactly the range matching a neighbour node at exactly 0 with the along-edge value unchanged; a node one raw unit off the edge not qualifying at all; a mirrored candidate one raw unit off failing rather than matching (`MIRROR_TOL_RAW = 0` is enforced); `outside_coverage`, `empty_slot` and `scale_mismatch` each landing in their own counter and out of the denominator; a corner node producing two incidences; and the `crossing` breakdown summing to `matched + violations`.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts before and after).
- `.venv-rp/bin/python parser/tools/boundary_mirror_census.py --reference /run/media/codyh/464210-8480 --out docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-11.json` run **twice** with identical output (report the `sha256` both times).
- In your handback, a table: per class, `denominator`, `matched`, `violations`, and the three exclusion counts; then the `crossing` breakdown for `matched`; then the verdict. Say outright whether `cross_block` and `cross_blockset` each carried at least one match.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. State explicitly whether any pre-stated constant was changed after a run — the answer must be no.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
