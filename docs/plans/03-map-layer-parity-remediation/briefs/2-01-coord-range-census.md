# Brief: 2-01 — Coordinate-range census: R per level and parcel class

Consumer: implementation worker; result consumed by 2-02, 2-03, 2-04 and Phase 3 (`coordconv.range_for`).
Owned paths: `parser/tools/coord_scale_census.py` (new), `parser/refdata/profile/coord_scale.json` (new; you write the `ranges` and `class_rule` sections only, 2-02 adds `header`), `parser/refdata/profile/density.json` (regenerate only if the L0 basis changes), `parser/tests/test_coord_scale_census.py` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: nothing (Phase 1 closed).
Runs alongside: nothing in this phase that edits the same files; 2-02 starts after you finish.
Budget: 7 files to read, about 300 lines to change, 40 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Domain "Native encoding model" Contract; Phase 2 Outcome; Assumption Ledger first item (hard stop).
2. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F1.
3. `parser/harness/walk.py` — `iter_parcels`, `WalkedParcel`; `parser/kiwiw/parcel.py` — `decode_parcel` (decode paths; read only).
4. `parser/tools/road_density_census.py` and `parser/refdata/profile/density.json` — its `length_basis` (Carried item 4: the L0 length uses an unverified 16384 heuristic).
5. `parser/kiwiw/coordconv.py` — `COORD_RANGE`, `decode_region_coord` (read only).
6. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — Carried list.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Establish from R, per (level, parcel class, division state), the true parcel-local coordinate maximum `R`, and a deterministic, content-independent rule assigning a parcel to a class. Classes to cover: L2-L8 full cell (expected 4096), sparse L0 (expected 16384), urban L0 (expected 4096), divided sub-parcels (expected 2048/4096). "Expected" is the hypothesis under test, not the answer: report what R shows, including any parcel whose maximum is neither.

## Contract

Cited: "`parser/refdata/profile/coord_scale.json`: for each level and parcel class, the R-observed coordinate maximum and the deterministic rule assigning a parcel to a class" and "The parcel-class rule must be content-independent (a function of grid position/level/division), so Phase 5 generalisation cannot invalidate it. `range_for(level, parcel_class, division_state) -> int`" (DESIGN, Native encoding model). Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Census tools read R only through `parser/harness/` reading paths and must not import writer modules. Output is deterministic (sorted keys, no timestamps).

## Changes

- Census tool: walk every R parcel (parallelise per block; report wall time), decode node/intermediate-point coordinates in all road and background sub-frames, record per parcel: level, grid position, division state, per-axis observed max, max over clipped-link end points. Aggregate: per (level, class, division state) the modal max, the fraction of parcels at the mode, and the exceptions listed (count plus up to 20 examples with block/parcel ids).
- Class rule: find the function of (level, grid position or block, division state) that assigns urban vs sparse at L0 and predicts the range. It must not use decoded content extent (Phase 5 changes content). If no content-independent rule reaches at least 99% on the census, report `blocked` with the confusion table; do not add a content-based rule.
- Carried item 4: use the census to check the 16384 L0 heuristic in `density.json`. If the L0 range was right for the parcels used, record that in the report; if not, re-run `road_density_census.py` with the corrected basis and commit the regenerated `density.json` (this is the only reason to touch it).
- Write `coord_scale.json` with `ranges` (per level/class/division: `max`, `share_at_max`, `n`) and `class_rule`; leave a `header` key absent for 2-02.

### Keep untouched

`parser/kiwiw/*`, `parser/harness/*`, `parser/refdata/harness.json`, `parser/refdata/profile/map.json`.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests/test_coord_scale_census.py -q` passes (synthetic parcel fixtures; includes a determinism test and a test that the class rule takes no content input).
- `.venv-rp/bin/python parser/tools/coord_scale_census.py --reference /run/media/codyh/464210-8480 --out parser/refdata/profile/coord_scale.json` run twice, `sha256sum` identical; an entry for every level R populates.
- The report states, per (level, class, division), the modal max and share at the mode, the rule's accuracy on the census (target >= 99%), and the verdict on the 4096/16384 hypothesis with the numbers.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. If the evidence contradicts the coordinate-range hypothesis, report `blocked` with the numbers: this phase is a gate and the design is bounced, not patched.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

