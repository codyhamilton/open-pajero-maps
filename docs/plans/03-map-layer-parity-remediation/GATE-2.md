# Phase 2 gate record — grounded criteria (2-12)

Source: DESIGN Decisions, "Amendment 2026-09-23 (user) — grounded phase gates", "#### Phase 2
— Outcome, as amended", criteria 1-5. Every criterion below was re-run for real against R in
this repo state on 2026-09-23; commands, outputs and sha256 comparisons are in
`EVIDENCE-2-12.json`. Reference disc: `/run/media/codyh/464210-8480`.

## Criterion 1 — coordinate maximum vs class range

Quoted verbatim: "No parcel holds a coordinate exceeding its class range. Spec 7.2.2.1.1.2
(road) and 7.3.2.2.1.1 (background): the u16 is bits 12:0 coordinate value and bits 15:13
relative position; a basic parcel is 4096 x 4096 and an integrated parcel up to 4096 x 8 =
32768. Per-parcel violation count. The denominator is the full-disc census in
`parser/refdata/profile/coord_scale.json`, produced by the committed
`parser/tools/coord_scale_census.py`: 28 (level, class, division) classes, 452,199
content-bearing parcels of R's 3,951,973, `exceeds_max` zero in every class."

- **Command**: `.venv-rp/bin/python parser/tools/coord_scale_census.py --reference /run/media/codyh/464210-8480 --out <scratch> --workers 10`
- **Number**: `exceeds_max` = 0 in every one of 28 classes.
- **Denominator**: 452,199 content-bearing parcels.
- Re-run `ranges` and `class_rule` are structurally identical to the committed profile.
  Cited quantity is `exceeds_max`, not `exceptions` (a different count — a class's observed
  peak not sitting at the bucket max — and not a violation).
- **PASS**

## Criterion 2 — cross-parcel continuity

Quoted verbatim: "A road link crossing a parcel boundary is stored independently on both
sides. Decoded under the assumed range and frame, the two copies of the shared endpoint must
land on the same place. Per matched pair; denominator all boundary-adjacent endpoint pairs at
a shared edge."

- **Command**: `.venv-rp/bin/python parser/tools/continuity_census.py --reference /run/media/codyh/464210-8480 --out <scratch>`
- **Number**: `over_threshold_total` = 407 across all classes (L0_urban 26, L0_sparse 328, L2
  5, L4 0, L6 9, L8 1, divided_pardiv1 38).
- **Denominator**: all boundary-adjacent endpoint pairs at a shared edge, per class (n_pairs:
  L0_urban 405, L0_sparse 3068, L2 550, L4 416, L6 383, L8 34, divided_pardiv1 984).
- Re-run is byte-identical to the committed `EVIDENCE-2-10.json` (sha256
  `8041db0f6647144db0c0eef61fa1875cedd1f5250881a335fe6c2f9c49c1a15a`, both runs) — fully
  deterministic, no drift.
- Median separation is 0.0 m in every class against alternative-range medians of
  1,182-294,864 m, so the model is strongly R-consistent. But the criterion demands zero
  violations or an enumerated residual explained record by record, and L0_sparse's 328
  over-threshold pairs are not fully enumerated (a 200-example cap falls short of 328), so
  the residual is not record-by-record explained. The tool's own `verdict` field is `fail`.
- **FAIL**

## Criterion 3 — divided sub-parcel containment

Quoted verbatim: "Spec 7.2.2.1.1.2 (2) and (3): 'For a divided parcel: The normalized
coordinate in the original basic parcel is used (Each relative position in the integrated
parcel is set to 0). However, the range of the X-axis coordinate may be restricted depending
on the parcel divided.' Every shape point of sub-parcel k (0 = SW, 1 = SE, 2 = NW, 3 = NE)
therefore lies inside quadrant k of the parent leaf's 4096 frame. Per-point violation count,
zero permitted."

- **Command**: same run as criterion 2 (one tool, one output).
- **Number**: 0 violations.
- **Denominator**: 1,037,716 shape points over 168 sub-parcels (52 content-bearing), 42
  divided parents.
- Re-run is byte-identical to the committed evidence (same sha as criterion 2's file).
- The `sub_local` reading (798,575 violations) is reported as the rejected alternative the
  criterion discriminates against, not a competing claim.
- **PASS**

## Criterion 4 — boundary-node mirror

Quoted verbatim: "A link end-node whose raw coordinate is exactly 0 or exactly the class
range is a genuine boundary crossing: the adjacent parcel holds an end-node at the mirrored
coordinate, crossed axis = range - value, other axis unchanged. Per-node violation count;
denominator all exact-coordinate nodes with a resolvable neighbour, with nodes at the
extract's outer edge excluded from the denominator rather than failed."

- **Command**: `.venv-rp/bin/python parser/tools/boundary_mirror_census.py --reference /run/media/codyh/464210-8480 --out <scratch>`
- **Numbers** (denominator/matched/violations/scale_mismatch, per class): L0_urban
  408/408/0/114; **L0_sparse 11536/2884/8652/0**; L2 4067/4061/6/111; L4 825/825/0/45; L6
  746/746/0/104; L8 66/66/0/23.
- Re-run is byte-identical to the committed `EVIDENCE-2-11.json` (sha256
  `c859bdd6caa5c32f1ded0412e982fd58f64fd547704f361d353261b739a89290`, both runs) — fully
  deterministic, no drift.
- `scale_mismatch` excludes neighbours that resolve to a divided leaf (a different
  coordinate scale) from the denominator; this means the claim's reach stops at
  undivided-to-undivided crossings and says nothing about a boundary against a divided
  neighbour.
- L0_urban, L4, L6, L8: 0 violations, **PASS**. L2: 6 of 4067 (0.15%), enumerated, **PASS
  WITH RESIDUAL**. **L0_sparse: 8652 of 11536 (75%) violations.** The tool's own `verdict`
  field labels this `pass_with_residual` because it can print `min(violations, 20)` examples
  — but the criterion's actual wording is zero violations, or an enumerated residual
  explained record by record, and 8652 of 11536 cannot be explained record by record from 20
  examples. This is a real criterion-4 failure, not a labelling artefact: majority same-block,
  with residual examples showing the neighbour resolving far from the expected mirrored
  coordinate (e.g. expected [6642,0], nearest actual [10854,0]). Not fixable within this
  unit's fixed-constant scope — may mean L0_sparse leaves don't tile edge-to-edge the way
  other classes do, or need a different mirror rule for the tile frame.
- **FAIL (L0_sparse); PASS / PASS WITH RESIDUAL for L0_urban, L2, L4, L6, L8**

## Criterion 5 — header-word rules agree exactly

Quoted verbatim: "Words 0, 6, 7, 9, 10 and 11 are predicted on every R parcel. The criterion
is exact agreement with every disagreement enumerated and individually explained — not 'at
least 99%', which was an arbitrary bar over rules that are closed-form or table-exact."

- **Command**: `.venv-rp/bin/python parser/tools/header_word_census.py --reference /run/media/codyh/464210-8480 --coord-scale <scratch>/coord_scale.json --out <scratch> --workers 10`
- **Numbers** (held-out 988,865 unless noted): word 0 — 0 disagreements with the checked
  formula (`word0*2 = 36 + 4*nregion + 6*n_entries`); word 6 — 1.0; word 7 — 0.999995
  (988,860/988,865), with a disc-wide 28-record named residual ("L0 single-link road
  parcels stored 0xFF00"); word 9 — 1.0; word 10 — 0.999977 (misses are unseen table keys
  only, 12 of 988,865); word 11 — 0.999988 (12 unseen keys).
- Re-run `header.words` is structurally identical to the committed profile.
  `header.pointer_nonframe_targets.examples` differs — this is 2-08's pre-existing carried,
  known non-regenerating concern, unrelated to this gate.
- **PASS WITH RESIDUAL** (words 0, 6, 9 exact; word 7's 28-record residual is named and
  disc-wide-exhaustive; words 10/11 miss only on table keys never seen, never on a wrong
  value)

## Overall verdict: NOT CLOSED

Criterion 2 fails (over_threshold_total=407, not fully enumerated), and criterion 4 fails
for L0_sparse (8652 of 11536 violations, a majority, not an explainable residual). Per the
brief's contract: "If any criterion fails, the verdict is NOT CLOSED... Do not soften a
failure, do not average criteria, and do not close on four of five." Criteria 1, 3 and 5
pass (criterion 5 with a named, fully-enumerated residual); criteria 2 and 4 fail. The
Phase 2 gate does not close on this re-run.

## Carried

Restated with current status:

1. **`rg_size` (word 16), item 4 — OPEN.** Nonzero on real L0 route-guidance parcels,
   absent from the DESIGN header-word exemption list. A DESIGN gap, not a code bug. The
   orchestrator must resolve it before Phase 4 (add word 16 to the exemption list, or have
   Phase 4 model it).
2. **Pointer non-frame targets (Phase 9's) — OPEN.** `header.pointer_nonframe_targets`:
   19,771 of 31,564,067 in the committed profile (L8 5.4%, L6 0.72%). No Phase 2 obligation;
   Phase 9 owns the `pointers` check allowance.
3. **Stale `LENGTH_BASIS` wording in `road_density_census.py` — OPEN.** The string still
   reads "leaf bounds extent" although the basis is now the frame (2-05's fixer changed the
   basis, not the docstring). Not touched here (not an owned path).
4. **`header.pointer_nonframe_targets.examples` does not regenerate identically — OPEN,
   confirmed again on this re-run.** Ranges, class_rule and header.words are stable; the
   examples list is not, for reasons unrelated to this gate (2-08's carried concern).
5. **New — `coord_scale_census._work` builds `WalkedParcel` without `frame_bounds` —
   confirmed.** `parser/tools/coord_scale_census.py` lines ~176-178 construct
   `walk.WalkedParcel(...)` without `frame_bounds`/`frame_range`/`frame_class`;
   `WalkedParcel.__post_init__` (`parser/harness/walk.py`) then defaults `frame_bounds` to
   `self.bounds` (the leaf bbox), so the 075fc99 fixer ("invert against the frame bbox, not
   the leaf") never takes effect inside this tool's own worker path. Harmless for criterion
   1's `ranges`/`exceeds_max` numbers, because decode and inversion in this tool use the
   same bbox and raw values round-trip exactly regardless of which bbox is nominally in
   play; the tool's own test passes only on a synthetic parcel and does not exercise this
   path against a real L0-sparse tile frame. Not fixed here, per brief scope. A future unit
   that reuses this tool's worker for anything frame-sensitive (e.g. lat/lon output) should
   fix it first.
6. **Criterion 2's `divided_pardiv1` residual (38 of 984, all fully enumerated) and
   `L0_sparse`'s under-enumerated 328 residual — new, OPEN.** The tolerance is already
   absolute-raw-units per the amendment's carried instruction (`EDGE_TOL_RAW=4`,
   `PAIR_TOL_RAW=16`), so this is not the provisional-tolerance concern from the amendment —
   it is a genuine residual that needs investigation before criterion 2 can close.
7. **Criterion 4's L0_sparse failure — new, OPEN, the decisive reason (with criterion 2)
   this gate does not close.** See Criterion 4 above.
8. Prior Phase 1 Carried items 1, 3, 5, 6, 7 remain with their original owners (unchanged
   by this unit).

## Assumption Ledger

**Verdict is NOT CLOSED, so no replacement text is written.** Per DESIGN.md line 252 ("The
Assumption Ledger entry 'Coordinate range 4096/16384 is the true full-cell range' is
deliberately left untouched, because Phase 2 is not closed here... closing it without doing
so would be a scope violation"), the entry stays exactly as it is:

> **Coordinate range 4096/16384 is the true full-cell range.** Tested in Phase 2. If false:
> hard stop, re-analyse (user decision).
