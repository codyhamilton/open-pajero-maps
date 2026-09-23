# Phase 2 gate record — grounded criteria (2-15, supersedes 2-12)

Source: DESIGN Decisions, "Amendment 2026-09-23 (user) — grounded phase gates", "#### Phase 2
— Outcome, as amended", criteria 1-5; criteria 2 and 4 as restated by "Amendment 2026-09-23
(design agent) — the adjacency unit is the frame, not the leaf slot". Every criterion below was
re-run for real against R in this repo state on 2026-09-23, after 2-13 (frame adjacency, global
raw lattice) and 2-14 (continuity/mirror re-run on frame adjacency). Commands, outputs and
sha256 comparisons are in `EVIDENCE-2-15.json`. Reference disc: `/run/media/codyh/464210-8480`.

## Criterion 1 — coordinate maximum vs class range

Quoted verbatim: "No parcel holds a coordinate exceeding its class range. Spec 7.2.2.1.1.2
(road) and 7.3.2.2.1.1 (background): the u16 is bits 12:0 coordinate value and bits 15:13
relative position; a basic parcel is 4096 x 4096 and an integrated parcel up to 4096 x 8 =
32768. Per-parcel violation count. The denominator is the full-disc census in
`parser/refdata/profile/coord_scale.json`... 28 (level, class, division) classes, 452,199
content-bearing parcels of R's 3,951,973, `exceeds_max` zero in every class."

- **Command**: `.venv-rp/bin/python parser/tools/coord_scale_census.py --reference /run/media/codyh/464210-8480 --out <scratch> --workers 10`
- **Number**: `exceeds_max` = 0 in every one of 28 classes.
- **Denominator**: 452,199 content-bearing parcels.
- **sha256** (two runs, identical): `b2d21b66e18f9d2f39ecf6f7334ef23f541c7adc394875a15b3b5c84b0a72485`
  — matches `EVIDENCE-2-12.json`'s figure exactly.
- `ranges` and `class_rule` are structurally identical to the committed
  `parser/refdata/profile/coord_scale.json`.
- **New obligation this unit checks (brief):** 2-13's `frame_bounds`/`frame_range`/`frame_class`
  fix (GATE-2 Carried 5, 2-12) is confirmed threaded through `coord_scale_census.py`'s `_work`
  worker (read at lines ~168-197: `WalkedParcel(..., frame_bounds=frame_bounds, ...)` and
  `MeshLocation(bounds=frame_bounds)` now share one bbox). Criterion 1's numbers did not move —
  `ranges`, `class_rule` and `exceeds_max` are exactly as before the fix, as 2-13 predicted.
- **PASS**

## Criterion 2 — cross-parcel continuity (design-agent restated wording)

Quoted verbatim (restated): "A road link crossing a frame boundary is stored independently on
both sides; the two copies of the shared endpoint occupy the same point on the level's global
raw lattice. Per matched pair; denominator all boundary endpoint pairs at a shared frame edge,
the adjacency unit being the frame, not the leaf slot... pairing is exact lattice equality."
`EDGE_TOL_RAW`/`PAIR_TOL_RAW` are retired under this design's retirement rule.

- **Command**: `.venv-rp/bin/python parser/tools/continuity_census.py --reference /run/media/codyh/464210-8480 --out <scratch>`
- **sha256** (two runs, identical): `da70cd597ed800763c4b9368664948842fc65205faecdd0df560d754e4b6d377`
  — matches `EVIDENCE-2-14.json`'s figure exactly.
- **Per class** (denominator/matched/violations/verdict): L0_urban 473/470/3/pass_with_residual,
  L0_sparse 686/686/0/pass, L2 547/547/0/pass, L4 416/416/0/pass, L6 379/379/0/pass, L8 33/33/0/pass,
  divided_pardiv1 983/979/4/pass_with_residual.
- **Overall**: `over_threshold_total` = 7, `violations_total` = 7, tool's own `verdict`
  field `pass_with_residual`. Every residual is `over_threshold_fully_enumerated: true`.
- **RESIDUAL_ENUM_CAP**: committed tool value is 400; DESIGN.md's design-agent amendment states
  200 for the same cap. **Contradiction, not resolved here**: the two committed sources disagree
  on the cap's value; both exceed 7 with large margin, so it does not change the verdict, but it
  is an open discrepancy (already noted by 2-14, carried forward, still open).
- **Residual, individually traced, not a plausible story:**
  - L0_urban's 3: 2 are duplicate-node collisions — two source nodes decode to the same global
    boundary point but the tool's greedy `Counter`-based exact match consumes only one counted
    target instance, so the second reports unmatched with `nearest_actual_global` identical to
    `source_global` (0 separation). Traced by reading `continuity_census.py`'s matching loop —
    this is a property of multiple links sharing one boundary node, not a coordinate
    disagreement. The third has a genuine 126-raw-unit offset in y (source_raw `[4096,443]`,
    edge E), consistent with the design-agent amendment's "dead end terminating on the boundary
    without crossing" mechanism.
  - `divided_pardiv1`'s 4: all are sibling-midline lookups with **no** node found at all in the
    mirrored sub-parcel — the same dead-end-at-midline mechanism (a link end terminates at the
    shared quadrant boundary without crossing into the sibling sub-parcel), traced in
    `continuity_census.py`'s `_sibling_pairs`.
- **Scale note carried from 2-14**: the committed tool's actual population is far smaller than
  the design-agent amendment's uncommitted probe figures (e.g. `divided_pardiv1` 983 nodes here
  vs 3,300 cited there) because the committed tool samples (`SAMPLE_BLOCKS=60`) rather than
  scanning the whole disc — a scope difference, not a regression, already reported by 2-14 and
  carried here unresolved.
- **PASS WITH RESIDUAL**

## Criterion 3 — divided sub-parcel containment

Quoted verbatim: "Spec 7.2.2.1.1.2 (2) and (3)... Every shape point of sub-parcel k (0 = SW,
1 = SE, 2 = NW, 3 = NE) therefore lies inside quadrant k of the parent leaf's 4096 frame.
Per-point violation count, zero permitted." Unaffected by the design-agent amendment.

- **Command**: same run as criterion 2 (one tool, one output file).
- **Number**: 0 violations.
- **Denominator**: 1,037,716 shape points over 168 sub-parcels (52 content-bearing), 42 divided
  parents.
- Byte-identical to criterion 2's output (same sha as above).
- **PASS**

## Criterion 4 — boundary-node mirror (design-agent restated wording)

Quoted verbatim (restated): "A link end node exactly on a frame edge is answered by an end node
at the identical global (X, Y) in a frame sharing that point. Per node, at exact integer
equality, zero tolerance... A node at a frame corner is satisfied by any of the frames sharing
that point... `scale_mismatch` is no longer an exclusion: under the lattice a 4096 frame facing
a 16384 frame is an ordinary crossing and must be in the denominator."

- **Command**: `.venv-rp/bin/python parser/tools/boundary_mirror_census.py --reference /run/media/codyh/464210-8480 --out <scratch>`
- **sha256** (two runs, identical): `23854cf540b3c6519f0945f7fb787890859787f1e3ef214a3f1fb646ad6733e4`
  — matches `EVIDENCE-2-14.json`'s figure exactly.
- **Per class** (denominator/matched/violations/scale_mismatch/verdict): L0_urban
  522/521/1/0/pass_with_residual (`cross_class_split` vs L0_sparse: 113 matched, 1 violation);
  **L0_sparse 721/721/0/0/pass**; L2 4065/4061/4/111/pass_with_residual (2 corner nodes, both
  matched under the any-sharing-frame reading); L4 825/825/0/45/pass; L6 746/746/0/104/pass;
  L8 66/66/0/23/pass.
- **L0_sparse is the headline result of this unit's chain**: 2-12 measured 8,652 of 11,536
  (75%) violations here under the old leaf-slot adjacency; the frame-adjacency fix (2-13) plus
  this restated criterion (2-14, re-confirmed here) brings it to **721/721, zero violations**,
  reproducing the design-agent amendment's decisive re-measurement figure exactly.
- **Cross-class evidence, named as the brief requires**: the `L0_urban <-> L0_sparse`
  `cross_class_split` — 113 matched, 1 violation — is the committed, re-run two-sided
  cross-class crossing evidence for 16384 = 4 x 4096 (a smaller-sample counterpart to the
  design-agent amendment's uncommitted 5,352/5,353 probe figure; that figure walked the whole
  urban population across 69 blocks, this committed run samples 40 blocks per its own
  `sample_rule`).
- **Residual, individually traced**: L2's 4 all have offsets of 0-2 raw units
  (`(dx,dy)` in `{(-2,0),(0,-1),(0,1),(0,-1)}`) — rounding, matching the design-agent
  amendment's cited L2/L4 character. L0_urban's 1 has offset `(14,-49)`, about 51 raw units —
  larger than rounding, consistent with the amendment's dead-end-at-boundary bucket, but not
  independently confirmed beyond this offset measurement (no further per-record trace was run;
  reporting the measurement honestly rather than a plausible story).
- **RESIDUAL_ENUM_CAP**: same 400-vs-200 discrepancy as criterion 2 (carried, unresolved);
  moot at 5 total violations against either value.
- **PASS WITH RESIDUAL**

## Criterion 5 — header-word rules agree exactly

Quoted verbatim: "Words 0, 6, 7, 9, 10 and 11 are predicted on every R parcel. The criterion is
exact agreement with every disagreement enumerated and individually explained." Unaffected by
the design-agent amendment.

- **Command**: `.venv-rp/bin/python parser/tools/header_word_census.py --reference /run/media/codyh/464210-8480 --coord-scale <scratch>/coord_scale.json --out <scratch>/header.json --workers 10`
- **sha256** (two runs, identical): `eef25d9012197535ab6cec7d2da88f81fe7cca84e147cc8dc27f64c3dedb0a33`
  — matches `EVIDENCE-2-12.json`'s figure exactly.
- **Numbers** (held-out 988,865): word 0 — 1.0, 0 disagreements with the checked formula; word 6
  — 1.0; word 7 — 0.999995 (988,860/988,865), the 5 held-out misses are the "L0 single-link road
  parcels stored 0xFF00" mechanism (28-record disc-wide-exhaustive figure in
  `WORD7-ANALYSIS.md`, held-out sampling naturally finds fewer); word 9 — 1.0; word 10 —
  0.999977 (12 unseen table keys); word 11 — 0.999988 (12 unseen table keys).
- `header.words` structurally identical to the committed profile.
- **PASS WITH RESIDUAL** (unchanged mechanism and disposition from 2-12).

## Overall verdict: CLOSED

Per the brief's binding contract: "if any criterion fails, the verdict is NOT CLOSED... do not
soften a failure, do not average criteria, do not close on four of five." No criterion fails on
this re-run. Criteria 1 and 3 pass at zero violations. Criteria 2, 4 and 5 pass with residuals
that are each fully enumerated (denominator, matched, violations, and — for criteria 2 and 4 —
every record's source identifiers and raw coordinates) and individually traced to a specific,
named mechanism (rounding, duplicate-node collision, or dead-end-at-a-boundary/midline without
crossing), not asserted on a plausible story. The residual totals (criterion 2: 7, criterion 4:
5, combined 12) sit well under `RESIDUAL_ENUM_CAP` under either cited value (400 committed, 200
per the design-agent amendment). The decisive figure the design-agent amendment named —
`L0_sparse`'s mirror result — reproduces exactly at 721/721/0, and the `L0_urban <-> L0_sparse`
cross-class crossing (113/114) is the committed two-sided evidence for 16384 = 4 x 4096.

`.venv-rp/bin/python -m pytest parser/tests -q`: 407 passed before and after (no code changed by
this unit). `.venv-rp/bin/python parser/tools/lint_schema.py`: 513 unverified rows, 0 errors,
before and after.

## Carried

Restated with current status:

1. **`rg_size` (word 16), item 4 — still OPEN.** Nonzero on real L0 route-guidance parcels,
   absent from the DESIGN header-word exemption list. A DESIGN gap, not a code bug; not owned by
   this unit. The orchestrator must resolve it before Phase 4.
2. **Pointer non-frame targets (Phase 9's) — still OPEN.** `header.pointer_nonframe_targets`:
   Phase 9 owns the `pointers` check allowance. No Phase 2 obligation.
3. **Stale `LENGTH_BASIS` wording in `road_density_census.py` — still OPEN.** Not touched here
   (not an owned path).
4. **`header.pointer_nonframe_targets.examples` does not regenerate identically — still OPEN,**
   unrelated to this gate (2-08's carried concern); not re-checked here since criterion 5 does
   not depend on it.
5. **CLOSED by 2-13.** `coord_scale_census._work` now threads `frame_bounds`/`frame_range`/
   `frame_class`; confirmed by reading the code in this unit (see Criterion 1 above).
6. **CLOSED by 2-13/2-14.** Criterion 2's `L0_sparse` under-enumerated 328 residual (2-12) is
   gone under frame adjacency: `L0_sparse` now measures 686/686/0, `pass`. The `divided_pardiv1`
   residual persists in a different, smaller form (4 of 983 here vs 38 of 984 in 2-12), fully
   enumerated and traced above; not a new open item, folded into this record's criterion 2
   section.
7. **CLOSED by 2-13/2-14.** Criterion 4's `L0_sparse` failure (8,652 of 11,536 violations, 2-12)
   is the decisive fix of this unit's chain: 721/721/0 under frame adjacency, reproducing the
   design-agent amendment's cited re-measurement.
8. **New, OPEN — `RESIDUAL_ENUM_CAP` value contradiction.** `parser/tools/continuity_census.py`
   and `parser/tools/boundary_mirror_census.py` both set `RESIDUAL_ENUM_CAP = 400`; DESIGN.md's
   design-agent amendment states `RESIDUAL_ENUM_CAP = 200` for the same cap. First reported by
   2-14, still unresolved; moot for every run so far (residuals never approach either value) but
   the two committed/authoritative sources disagree and neither this unit nor 2-14 is in scope
   to change `parser/**` or `DESIGN.md`'s criteria text to reconcile it.
9. **New, OPEN — minor tool-behaviour finding, not a correctness bug.** Two of `continuity_census.py`'s
   three `L0_urban` criterion-2 residuals are an artefact of the tool's greedy exact-match: when
   two source nodes decode to the same global boundary point, only one counted target instance is
   consumed, so the second reports `unmatched` with zero true separation (`nearest_actual_global
   == source_global`). This does not affect any criterion's pass/fail here (the residual is still
   correctly counted and enumerated) but inflates the residual count by up to 1-2 records per
   affected class; a future unit touching `continuity_census.py` may want to dedupe source nodes
   the way target nodes are already deduped (`node_dedup` note in `EVIDENCE-2-14.json`). Not
   fixed here — `parser/**` is out of scope for this unit.
10. Prior Phase 1 Carried items 1, 3, 5, 6, 7 remain with their original owners (unchanged by
    this unit).

## Assumption Ledger

**Verdict is CLOSED.** Per DESIGN.md's Decisions, "Amendment 2026-09-23 (user) — grounded phase
gates", "#### Schema rows this amendment supersedes": "Whoever closes Phase 2 must update that
entry in the same change; closing it without doing so would be a scope violation." The
Assumption Ledger entry "**Coordinate range 4096/16384 is the true full-cell range.**" is
updated in this same commit (see `DESIGN.md` Assumption Ledger) to state that Phase 2 tested it
and what it now rests on: the global raw lattice at 4096 raw units per top-level leaf slot, a
coordinate frame as an n x n block of slots at range n x 4096 (n = 1 basic, n = 4 the L0 sparse
integrated-parcel tile), and the cross-class `L0_urban <-> L0_sparse` measurement (criterion 4,
113 matched / 1 violation this run, 5,352/5,353 in the design-agent amendment's uncommitted
full-population probe) as the two-sided evidence that 16384 is exactly 4 x 4096 and not an
independent constant.
