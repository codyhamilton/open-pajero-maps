# Brief: 2-08 — Overlay re-run against the redefined coordinate gate

Consumer: implementation worker; result consumed by 2-04 and by the phase gate verdict.
Owned paths: `parser/tools/overlay_test.py`, `parser/tests/test_overlay_test.py`, `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-08.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-05 (L0 sparse frame in `walk.py`) and 2-06 (y orientation) — both must be committed before you start; this unit's numbers are invalid otherwise.
Runs alongside: 2-07.
Budget: 8 files to read, about 250 lines to change, 50 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-22 (user) — Phase 2 restart", item 1 (the redefined gate) — this supersedes Phase 2's Outcome wherever they differ.
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the `2-03 overlay-test` record in full, and the "Phase 2 gate verdict: NOT CLOSED" section.
3. `parser/tools/overlay_test.py` — the module docstring (the stated rules and thresholds of the first run) and `analyze`, `pool`, `clip_stats`, `occupied_fraction`, `decode_uv`, `model_frame`, `model_cell`, `tile_frame`, `RReader`, `pick_named`, `pick_pooled`, `main`. This file is your starting point; rewrite what the redefined gate requires and keep the rest.
4. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-03.json` — grep, do not read whole: `gate`, `criteria_rules`, `named_cells[*].verdict`, `pooled_classes.*.model.matched_fraction`. It is the first run's record and stays as it is.
5. `parser/harness/walk.py` as 2-05 left it — the leaf/frame distinction and the frame range. `parser/kiwiw/coordconv.py` as 2-06 left it.
6. `parser/refdata/harness.json` — `bands.name_record_distance_tolerance` (rule, `tol` 0.005, and its `basis` text). `parser/refdata/profile/coord_scale.json` — `ranges`, `class_rule`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Decide the coordinate gate on evidence that does not depend on OSM being right: show that R decoded at the assumed per-class range beats every alternative range by a pre-stated relative margin, and that R's own geometry is consistent with that range.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-22 item 1, in full:

> **Coordinate gate redefined (relative, plus R-only measures).** The absolute overlay match-rate thresholds (`MATCH_MIN 0.8` and siblings) are low-signal: OSM and the 14-year-old proprietary R source genuinely disagree, so an absolute match rate measures source drift as much as the coordinate model. The gate is now:
> - (a) **Relative discrimination.** For each parcel class, the assumed range beats every alternative range considered — including the 32768 negative control — by a clear, *pre-stated* relative margin.
> - (b) **R-only measures pass.** Coordinate maximum vs the class range; clipped links terminating at the cell edge; occupied fraction of the cell extent (no clustering into a sub-region).
> - Match rate against OSM is reported as a **diagnostic** with a recorded source-disagreement baseline. It is not pass/fail.
> - The margin and every threshold are stated in the tool docstring **before** the run and are not tuned after seeing results. All four named cells are evaluated.

Cited, `parser/refdata/harness.json` `bands.name_record_distance_tolerance`: rule `distance_m <= tol * cell_extent_m`, `tol` 0.005, basis "R quantises to a 4096 (or 16384) grid per cell; half a percent of the cell is ~20 grid units, above quantisation and OSM-vs-survey offset yet far below cluster scale."

Settled and not to be re-derived: y is up; the divided sub-parcel frame is the parent leaf's bbox at range 4096 (sub 0 = SW quadrant); the L0 sparse frame is the 4x4 integrated-parcel tile at 16384. All three are 2-03's recorded findings, and after 2-05/2-06 the first two come from `walk.py` and `coordconv.py` rather than from this tool's local hypotheses.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; OSM extract `australia-260824.osm.pbf`. Python: `.venv-rp/bin/python`. Reads R only through `parser/harness/` reading paths; imports no writer module. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

**Everything in this section is fixed at refine time. Copy these numbers and definitions into the tool docstring before you run anything, and do not change any of them after seeing a result. Changing one is a brief violation; reporting that one is unsatisfiable is not.**

- **Thresholds, pre-stated.** `MARGIN_MATCH = 1.5`, `MARGIN_DIST = 2.0`, `MAX_REL_LO = 0.9`, `MAX_REL_HI = 1.0`, `AXIS_COVERAGE_MIN = 0.75`, `CLIP_EXACT_MIN = 0.9`, `CLIP_NEAR = 0.005`, `MIN_CLIPPED_LINKS = 50`, `MIN_LINKS = 20`, `MIN_LINKS_STRICT = 50`, `POOL_N = 12`, `GRID_N = 16`, `tol = 0.005` read from `harness.json`. They were chosen at refine time so that the discrimination cannot be produced by the cell-to-cell spread the first run showed; the first run's numbers were visible when they were chosen, and `divided_pardiv1` sat at 1.51 on the match ratio, so that class is expected to be the tight one. That is disclosed here deliberately: if it fails, it fails.
- **Criterion (a), relative discrimination, evaluated pooled per parcel class.** The alternative set for every class is, at minimum, `{ range/2, range*2, 32768 }`; for `divided_pardiv1` add the `own_bounds` and `quadrant_4096` frame hypotheses, and for `L0_sparse` add `own_leaf_16384`, `own_leaf_4096` and `tile4x4_4096` — the first run already implements all of these. A class passes (a) iff the assumed range's pooled matched fraction is `>= MARGIN_MATCH` times every alternative's **and** its pooled median matched-link distance is `<= 1/MARGIN_DIST` of every alternative's. An alternative with a zero matched fraction passes the ratio trivially; say so rather than dividing by zero.
- **Criterion (b), R-only measures, evaluated pooled per parcel class**, with no OSM input at all:
  - `coord_max_over_range`: pooled median `>= MAX_REL_LO` and pooled maximum `<= MAX_REL_HI` (no coordinate exceeds its class range).
  - `axis_coverage`: over a `GRID_N x GRID_N` grid on the frame, `max(rows containing an R vertex, columns containing an R vertex) / GRID_N`; pooled median `>= AXIS_COVERAGE_MIN`. This is the "no clustering into a sub-region" measure, stated R-only: a range that is too large confines every vertex to one corner and drives both row and column coverage down, while a legitimately sparse cell crossed by one highway still fills one axis. Also report the OSM-relative occupied fraction the first run used, as a diagnostic.
  - `clip_exact_share`: among links with a vertex within `CLIP_NEAR * range` of a frame edge, the share whose extreme coordinate is exactly 0 or exactly the range; pooled `>= CLIP_EXACT_MIN` over `>= MIN_CLIPPED_LINKS` such links. A class with fewer clipped links reports `insufficient_data` — which is not a pass.
- **`tol_extent`, resolved up front, not after the fact.** The distance tolerance scales the **frame** extent, not the leaf extent, because the band's own basis is R's quantisation grid and that grid spans the frame (`harness.json` basis text, quoted above). This is the decision the first run reached post-hoc; it is now made before the run and stated as such in the docstring. Report the leaf-basis numbers alongside as a diagnostic, as the first run did.
- **OSM match rate is a diagnostic only.** Report, per class and per named cell: matched fraction; p50/p90 residual distance of matched links in metres; and a **source-disagreement baseline** defined as the fraction of like-for-like OSM ways in the cell that have *no* R link within tolerance (roads OSM has and R does not — new construction, tracks, R's own selection). No threshold is applied to any of the three, and none of them can fail the gate. Name the baseline in the output so 2-04 can quote it.
- **All four named cells are evaluated** (Brisbane CBD, Sydney, rural QLD/Longreach, outback/Birdsville) and reported per criterion with their numbers. The gate is decided on the pooled per-class results; a named cell is a gate failure only if it fails a criterion with `>= MIN_LINKS_STRICT` links, and below that its verdict is reported as `low_n` for 2-04 to judge. Do not re-pick the named cells to get more links; the selection rule stays the first run's.
- **Take the frame and its range from `walk.py` (as 2-05 left it) rather than from this tool's local `tile_frame`/`model_frame` hypotheses**, wherever 2-05 now provides them; keep the hypothesis machinery, since criterion (a) still needs the alternatives. Take the y convention from `coordconv` and keep `decode_uv`'s `y_up` flag only for the y-down alternative, which stays in the output as evidence.
- Write `EVIDENCE-2-08.json`: the docstring's rules verbatim, every threshold, per-class and per-named-cell numbers for the model and every alternative, criterion (a) and (b) verdicts per class, the diagnostics, and a top-level `gate` object stating pass/fail per criterion. Do not write `all_pass` as a single boolean without the per-criterion breakdown behind it.

### Keep untouched

`EVIDENCE-2-03.json` — it is the first run's record and 2-04 cites both. The named-cell and pooled-cell **selection rules** from the first run (they are match-quality-independent by construction, and re-picking cells after seeing results is the exact failure this gate was redefined to avoid). Everything under `parser/kiwiw/`, `parser/harness/`, `parser/refdata/`, `docs/schema/`.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_overlay_test.py -q` passes, with the existing six tests kept and new synthetic-fixture tests for the new measures: `axis_coverage` is high for vertices spread over the frame and low for vertices confined to one quadrant; `clip_exact_share` counts an exactly-0/exactly-range endpoint and not a near-edge one; the criterion-(a) comparison rejects a case where the assumed range's advantage is below `MARGIN_MATCH`.
- The tool run twice with identical output (report the `sha256` of `EVIDENCE-2-08.json` both times).
- The docstring in the committed tool contains every threshold above, and `git log`/the commit order shows the docstring was committed before or in the same commit as the run's evidence. State in your report that no threshold changed after the first run of the tool.
- Per class: criterion (a) verdict with the ratio against the *best* alternative; criterion (b) verdict with all three numbers. Per named cell: the same, plus its link count.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

Report the gate result as it falls. This is a hard gate (DESIGN Decisions: "If the offline test does not confirm R's range model, the design is bounced for re-analysis"). A class that fails (a) or (b) is reported as a failure with its numbers; do not soften it, do not relax a threshold, and do not add a post-hoc basis or exclusion to rescue a class. If a threshold turns out to be unsatisfiable for a structural reason you can demonstrate, report `blocked` with the demonstration and let 2-04 and the orchestrator decide.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
