# Brief: 26c — parcel_count gap: prove the cause, then fill empty cells or declare the deviation

Consumer: implementation worker. Analysis first (read-only, offline), then a bounded code change.
Owned paths: a new analysis script `parser/tools/parcel_occupancy.py` (+ test), and, only for
step 3, the parcel enumeration in `parser/build_alldata.py::_encode_level`. **Sequencing:** another
worker is editing assembler/PDMDH code concurrently -- do step 3 only after that work is
committed (check `git log -- parser/build_alldata.py parser/kiwiw`); steps 1-2 can start now.
Do not touch `parser/harness/`. Commit and push code+tests; no rebuild here (26 owns it).
Depends on: 25b. Runs alongside: 26a (disjoint files).

## Diagnosis (evidence from 25b `output/report.json` and read-only inspection)

parcel_count G/R: L0 429,084/3,704,871 (0.116x); L2 22,991/231,564 (0.099x); L4 1,758/14,511
(0.121x); L6 243/939 (0.26x); L8 65/78 (0.83x, ok); L10 4/9 (0.44x); L12 2/1 (2.0x, edge).
`parcel_count` = leaf slots in `harness/profile.py::_LevelAccumulator.add_leaf`
(sum of `parcel_count_by_type`), so it counts *emitted frames*, not content volume.
`build_alldata._encode_level` iterates `reader.iter_level(level)`, i.e. only cells the spool
has content for; `divide.plan_divisions` adds sub-frames only for oversize cells (G L0 has
52+ divided cells as R has 52 type-1 leaves: divided accounting is NOT the gap). It is not
selection-driven either: L0 admits every road and every background way.
R, in contrast, emits a frame for far more cells than have admitted content: R L2 mean frame
is 497 B (min 320 B, the empty-frame floor) with 231,564 frames over a 1024x1024 level grid, and
R L0 has 3.70M frames of the 16.8M-cell grid (~22%) at ~1.2 KB mean. Rough area check: the
Australian bounding box is ~2.1M L0 cells (~1.0M land at ~7.6 km2/cell), so R's 3.7M cannot be
land-with-content only -- R evidently populates a contiguous coverage mask (including sea /
outback cells with near-empty frames). Ratios ~0.1x uniform across L0/L2/L4 with convergence
at L8 (coarse cells all contain content) fit "G omits empty/sparse cells R keeps".
STATUS: strongly indicated, NOT proven. Step 1 proves or refutes it.

## Changes

1. Analysis script: decode R's parcel-management leaf table per level (existing
   `harness/profile` / `kiwiw` readers on `/mnt`-independent reference data as the profile
   builder already does -- read-only) to obtain R's populated cell set {(ix,iy)}; read
   `output/spool/level_N.idx` for G's cell set. Report per level: |R|, |G|, |R&G|, |R-G|,
   |G-R|; for R-G cells the R frame size distribution (fraction at 320 B floor / <=500 B),
   and bounding-box/land-mask shape (is R contiguous within a hull? does it include ocean?).
   Expected if hypothesis holds: G-R ~ 0, R-G ~ 90% at the floor size.
2. Decision gate (record in report; write the result into the IMPLEMENTATION.md entry):
   - If R-G cells are (near-)empty frames within a coverage mask: implement step 3.
   - If R-G cells carry real content G's selection misses (e.g. R draws land/sea backgrounds
     not in OSM extract): step 3 does not apply; write it up as a **declared deviation** (see
     below) -- generating that content is WP2 scope, and not fabricating it is correct.
3. Fill: check in a compact occupancy mask per level as reference data
   (`parser/refdata/parcel_mask_L{n}.bin` run-length or bitmap; sizes: L0 16.8M bits ~2 MB
   raw, RLE far smaller -- same class as `grid.json`, record it in `docs/provenance.md` if
   generated from R), and make `_encode_level` also emit minimal-empty frames for masked cells
   the spool lacks (the shared empty-frame encoder already returns the 2-byte minimal frame
   for `shapes=[]`; confirm it satisfies decode/pointers/mht29 and R's 320 B floor by the
   existing checks). Capacity check: (|R-G| x 320 B) must stay under the 4.7 GB projection.
   Fixture builds must remain byte-stable outside the filled cells (add a test).
4. Tests: mask loader round-trip; `_encode_level` emits empty frames only for masked-and-absent
   cells; decode check on a synthetic mask.

## Proposed deviation (for PLAN.md acceptance) if step 1 refutes fill
"Map-layer parcel_count at levels 0/2/4/6 (and 10) is outside [0.5,2]x because R materialises
frames for cells whose content is not derivable from the OSM extract; G emits frames only for
cells with admitted content. Reported, not closed; WP2/out of scope." Also propose, in every
case: L12 parcel_count 2/1 is a 2.0x edge (R has 1 global parcel; G has 2 because level 12
emits a divided/duplicate cell) -- check whether G's 2 is a divided pair and fix in step 3's
scope or declare.

## Report back
Occupancy table, the gate decision, evidence for/against the hypothesis, capacity delta,
any contradiction with brief 20/25b. Non-trivial out-of-scope bugs: report, do not fix.
