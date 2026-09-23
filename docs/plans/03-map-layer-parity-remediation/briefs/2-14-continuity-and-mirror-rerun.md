# Brief: 2-14 — continuity and mirror re-run on frame adjacency (criteria 2, 3, 4)

Consumer: 2-15, the Phase 2 gate verdict, which consumes these numbers as criteria 2, 3 and 4.
Owned paths: `parser/tools/continuity_census.py`, `parser/tools/boundary_mirror_census.py`, `parser/tests/test_continuity_census.py`, `parser/tests/test_boundary_mirror_census.py`, `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-14.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-13 (frame adjacency, the corner query and the global-lattice conversion in `parser/tools/r_neighbours.py`).
Runs alongside: nothing.
Budget: 12 files to read, about 450 lines to change, 60 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff (done, not done, what you learned) **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot", in full; then, in the 2026-09-23 (user) amendment, "#### Phase 2 — Outcome, as amended" criteria 2, 3 and 4 and the **Retirement rule** and **grounded/necessarily-statistical** definitions. Where the two conflict on criteria 2 and 4, the design-agent amendment governs and says so.
2. `docs/plans/03-map-layer-parity-remediation/GATE-2.md` — criteria 2 and 4 and Carried items 5, 6, 7. This is what you are fixing.
3. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-10.json` and `EVIDENCE-2-11.json` — the failing figures you must reproduce-then-supersede. Do not edit or delete either file; they are the record of the previous run.
4. 2-13's handback (the frame-adjacency API and signatures) and `parser/tools/r_neighbours.py` as 2-13 left it.
5. `parser/tools/continuity_census.py` and `parser/tools/boundary_mirror_census.py` — all of both.
6. `parser/tools/overlay_test.py` — `RReader`, `_links` (note `"ends"` is the first and last node of each link), `_class_key`, `model_frame`, `class_range`, `spread`, `_raw`, `DECODER_RANGE`. Do not modify it.
7. `parser/harness/walk.py` — `_leaf_frame`, `_frame_range`, `_tile_bounds`, `L0_TILE`.
8. `parser/refdata/profile/coord_scale.json` — `ranges`, `class_rule`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Re-establish criteria 2, 3 and 4 with the frame as the adjacency unit and the level's global raw lattice as the comparison, at exact integer equality, with every residual record enumerated. Criterion 3 already passes at zero violations and must keep passing unchanged; criteria 2 and 4 failed only because the neighbour step was one leaf slot where the L0 sparse frame is a 4x4 tile.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23 (design agent), criterion 2 as restated:

> A road link crossing a frame boundary is stored independently on both sides; the two copies of the shared endpoint occupy the same point on the level's global raw lattice. Per matched pair; denominator all boundary endpoint pairs at a shared **frame** edge, the adjacency unit being the frame, not the leaf slot. Endpoint selection is exact — a node qualifies only when its raw crossed-axis coordinate is exactly 0 or exactly the frame range — and pairing is exact lattice equality.

Cited, the same amendment, criterion 4 as restated:

> A link end node exactly on a frame edge is answered by an end node at the identical global (X, Y) in a frame sharing that point. Per node, at exact integer equality, zero tolerance. Denominator: all exact-coordinate nodes with at least one resolvable sharing frame, nodes at the extract's outer edge excluded from the denominator rather than failed, and counted-and-reported exclusions retained. A node at a frame corner is satisfied by **any** of the frames sharing that point (7.2.2.1.1.3, "neighbouring parcels", plural), not by one nominated edge neighbour. `scale_mismatch` is no longer an exclusion.

Cited, the same amendment, on tolerances retired: "This retires `EDGE_TOL_RAW` and `PAIR_TOL_RAW` under this design's own retirement rule: the grounded exact measure was found underneath the tolerance-based one, so the tolerance is retired rather than retuned. The alternative-range scoring (half, double, 32768, the two divided renormalisations) is kept, because it is what makes the criterion two-sided."

**Pre-stated, not tuned.** Every constant below goes in the owning module's docstring with the words "pre-stated, not tuned" before any run, and none changes after a result. A constant that turns out to be wrong is a `needs context` report, not an edit.

- `RESIDUAL_ENUM_CAP = 400` — above the 152-record measured residual with margin. **Binding: if a criterion's residual exceeds the cap, the verdict is `fail`, not a truncated residual.** A cap below the residual is exactly why 2-12 failed criterion 2.
- Exact-only selection and exact lattice equality in both tools. No `EDGE_TOL_RAW`, no `PAIR_TOL_RAW`, no epsilon. If a class's raw values are not integral, that is a finding to report, not a reason to reintroduce a tolerance.
- `MIN_NODES_PER_CLASS = 300` / `MIN_PAIRS_PER_CLASS = 300` unchanged; L6, L8 and any smaller class are measured over their **whole population**.
- Pass condition per criterion: zero violations over the stated denominator, or a residual enumerated **record by record** with both parcels' identifiers and both raw coordinates.

Binding, on the verdict logic — this is a defect in its own right, independent of the adjacency bug. `boundary_mirror_census` currently reads `elif len(violation_examples) >= min(violations, 20): verdict = "pass_with_residual"`, which labels a class `pass_with_residual` whenever it can print twenty examples, whatever share of the denominator they cover; that is how a 75 % violation rate came back labelled `pass_with_residual` and had to be overridden by hand in GATE-2. Replace it in **both** tools with: `pass` at zero violations; `pass_with_residual` only when every violation is enumerated in the output; `fail` otherwise. A `fail` is written as `fail`.

Expected figures from the design agent's scratchpad probes, **for comparison, not as a pass condition** — your committed run is the evidence, and a disagreement with these is a finding to report, not a number to chase:

- L0 sparse, frame adjacency, 9 blocks / 1,152 tiles: 721 candidate nodes, 721 matched, **0 violations** (was 11,536 / 2,884 / 8,652).
- L0 urban, whole urban population (252 urban tiles, 69 blocks, 2,863 frames with content), per edge incidence: denominator 100,958, matched 100,818, 140 violations; `L0_urban -> L0_sparse` **5,352 of 5,353**; `L0_urban -> L0_urban` 95,466 of 95,605.
- Per node: L0 168,712 / 93 failures; L2 4,063 / 4; L4 6,933 / 1; L6 746 / 0; L8 66 / 0. Corner nodes scored per node, any sharing frame: L0 40 / 1, L2 2 / 0.
- Divided `pardiv1`, whole population, exact midline, no tolerance: 3,300 midline nodes (L0 1,951, L2 345, L4 738, L6 224, L8 95), **53 failures** (L0 3, L2 1, L4 44, L6 4, L8 1). This closes the amendment's carried "provisional" divided concern; report it explicitly as such.
- Total residual to enumerate: **152 records** (93 + 1 + 4 + 1 + 53).

Binding, on the residual: the amendment says "None of this is an explanation until 2-14 enumerates it record by record; the criterion is not satisfied by a plausible story about a residual." So for **every** residual record, output the source parcel identifiers, the edge or midline, the raw coordinates, the counterpart frame's identifiers, and the nearest actual node in raw units — and in the handback, group the records by offset magnitude and say for each group what mechanism it is consistent with. The amendment's own reading, to confirm or contradict: 1–2 raw units at L2/L4 is R's two copies disagreeing by rounding; 44–245 raw units at L0_urban (one at 1,243) is a link terminating *on* the boundary without crossing, the same mechanism that retired `b_clip_exact_share`. If the records do not support that reading, say so.

`scale_mismatch` handling, explicit: it stops being an exclusion and its population moves **into** the denominator, because a 4096 frame facing a 16384 frame is the strongest evidence for the range model and the old check discarded it (114 such at L0_urban). Keep the counter and report it as a *reported subset of the denominator* with its own matched/violation split, so 2-15 can see the cross-class evidence separately. A neighbour that resolves to a **divided** leaf is a genuinely different coordinate scale and stays excluded-and-counted; say so in the JSON in words.

Criterion 3 is not redesigned. It passes at 0 violations over 1,037,716 shape points, is spec-cited (7.2.2.1.1.2 (2) and (3)) and tolerance-free. Keep `criterion3` and its `sub_local` rejected-alternative reporting intact and confirm the same numbers come back.

Settled and not to be re-derived: the frame of record is `overlay_test.model_frame` with `class_range` (2-05, 2f874e3); y increases northward (2-06); edges are W/E on longitude and S/N on latitude; `RAW_PER_SLOT = 4096` at every level (2-13).

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. R only; **no OSM input at all**. Python: `.venv-rp/bin/python`. Reads R through `parser/harness/` reading paths, `overlay_test.RReader` and `r_neighbours`; imports no writer module. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

Both census tools, rebuilt onto 2-13's frame adjacency and global lattice, with one `EVIDENCE-2-14.json` carrying both criteria's output (or two top-level sections in it — say which in the handback).

- Continuity: pair endpoints across a shared **frame** edge. Selection exact, pairing exact lattice equality. Keep `_sibling_pairs` for `divided_pardiv1` but read the midline exactly, with no tolerance. Keep the alternative-range scoring (half, double, 32768, the two divided renormalisations) and report each alternative's figures beside the model's, because that two-sidedness is the criterion's whole point.
- Mirror: per **node**, at global-lattice equality, over all four edges. A corner node is satisfied by any sharing frame via 2-13's corner query; report corner nodes separately, as nodes, and state the per-edge figure too so the 2-11 comparison is possible.
- Both: `RESIDUAL_ENUM_CAP` enforced as a verdict condition, the corrected verdict logic, the pre-stated constants echoed verbatim into the JSON, and the sample rule written out in words.
- Report, per class: `n_frames`, `n_candidate_nodes` (or `n_pairs`), `denominator`, `matched`, `violations`, each exclusion counter separately, the `crossing` breakdown of matched and violations, the cross-class (`scale_mismatch`-population) split, the corner figures, every residual record up to the cap, and the `verdict`.

### Keep untouched

`parser/tools/r_neighbours.py` (2-13 owns it; if it needs a change, report `needs context` rather than editing), `parser/tools/overlay_test.py`, `parser/tools/coord_scale_census.py`, `parser/tools/header_word_census.py`, `parser/harness/**`, `parser/kiwiw/**`, `parser/refdata/**`, `docs/schema/**`, `docs/plans/**/DESIGN.md`, `GATE-2.md`, `EVIDENCE-2-10.json`, `EVIDENCE-2-11.json`. Do not update the Assumption Ledger and **do not write a gate verdict** — 2-15 owns both.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_boundary_mirror_census.py parser/tests/test_continuity_census.py -q` passes, with synthetic-fixture tests (no disc) for: **all 16 aliased slots of one sparse tile contributing one candidate node set, not sixteen** (the denominator-inflation regression); a node at the range of an n = 4 frame matching a node at 0 in the adjacent n = 4 frame at the same global (X, Y); an n = 1 frame's node matching an n = 4 frame's node across their shared edge (the cross-class case); a mirrored candidate one raw unit off failing rather than matching; a node one raw unit inside the edge not qualifying at all; a corner node satisfied by a diagonal sharing frame when no edge neighbour holds it; a residual larger than `RESIDUAL_ENUM_CAP` producing `fail` and not a truncated residual; and the corrected verdict logic returning `fail` for a many-violation, few-examples case that the old logic called `pass_with_residual`.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts before and after).
- Both tools run against R, written into `EVIDENCE-2-14.json`, run **twice** with identical output (report the `sha256` both times).
- In the handback: a per-class table for each criterion (denominator, matched, violations, exclusions, verdict); the total residual count against the cap; the divided `pardiv1` exact-midline figures with the statement that the amendment's provisional marking is or is not resolved; whether `cross_block` and `cross_blockset` each carried at least one match; and the cross-class `L0_urban <-> L0_sparse` figure called out by name.
- `.venv-rp/bin/python parser/tools/lint_schema.py` — report before and after; no new errors.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. State explicitly whether any pre-stated constant was changed after a run — the answer must be no. Do **not** declare Phase 2 closed; state the per-criterion figures and let 2-15 give the verdict.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
