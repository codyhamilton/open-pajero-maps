# Implementation — 39 historical background-family causes by counterfactual

Master direct. Evidence: `docs/plans/04-c-core-orchestration/triage/historical_bg/{p1,p2,p3}/`
(scripts and small JSON; large dumps stay in `output/scratch-39/`, git-ignored).
Every heavy step ran under `run_heavy_python.py` + `output/.heavy.lock`, K1 at `-j6`,
encode at `-j4`. Discs read: `87a01b14` (plan 36 replay, `output/scratch-36/G_pre311`),
`013586b5` (`scratch-3-11/G_new`), `4ed9cd80` (`scratch-14/G_new`). No protected disc,
spool or snapshot was written; the protected snapshot is unchanged (see Phase 3).

Dump rows are read with the C struct layout (natural alignment, `align=True`, as
`parser/tools/k1_triage.py` does). A first packed-layout reader misread fields after
`level`; every number below is from the aligned re-run (the only affected first-pass
figure was a nearest-source screen count, superseded).

## Phase 1 — basis reconstructed; R-G4-1 confined and explained

### 1. HEAD K1 reproduces 3C-04 on the `87a01b14` replay (`p1/cmp_pre311_3c04.json`)

HEAD K1 (`5e355cb`/`87f78fe`, `-j6`, dump off) on `87a01b14` equals the 3C-04 table
(plan 04 IMPLEMENTATION 2-08) in **every kind, checked and failing**, except
completeness failing **65 vs 752** (plan 14's representable-footprint rule,
`a890662`/`0dc5cac`). On `013586b5` it equals 3-90 rerun #3 except completeness
**52 vs 739** (`p1/cmp_311_rerun3.json`).

The Assumption 2 fallback was also run: K1 built at **`1cf40f8`** (pre plan 14) on
`87a01b14` reproduces 3C-04 **exactly in all nine kinds, completeness 752 included**
(`p1/k1old_pre311.json`).

### 2. 3-11 checked moves: confined to the 37 cells and fully explained

- **Per level:** every non-L0 level has delta 0 in every kind; the whole delta is L0
  (`p1/perlevel_311.txt`).
- **Per (block, cell row):** plan 36's `k1_rows.py` (unmodified K1, one band per
  cell row) on both discs; totals equal the whole-disc reports. **35 bands hold the
  37 changed cells; all 35 have a delta; no band without a changed cell has a
  delta** (`"confined": true`, `p1/k1-confine-3-11.json`).
- **Decode of the 37 cells** (`p1/wrap37.py`, targeted preads, `p1/wrap37.json`):
  141 leaves on both discs; road, name, region and extension sections identical;
  **background record bytes identical** (physical walk). Exactly **41 elements**
  change their unit table: on `87a01b14` each declares `physical − 4096` records in
  one class unit (the O06 count wrap); `013586b5` splits it. So the only
  K1-visible change is the **167,936 formerly unread records** (41 × 4096).
- **Every checked delta equals an exact count over those records:**

| kind | checked delta | derived from the 167,936 unread records |
|---|---|---|
| range | +861,107 | vertices = **861,107** |
| step | +693,171 | vertices − records = 861,107 − 167,936 = **693,171** |
| background + background_boundary | +839,197 + 21,910 | each vertex is checked as one or the other: **861,107** |
| interior_cover | +29 | class-2 records with every vertex on the leaf edge and area = leaf rectangle (K1's cover test): **29** (`p1/wrap37_cover.json`) |
| road_node, name_anchor, completeness | 0 | — |

  The cover count takes each element's extent from its own coordinates (the leaf
  rectangle in frame raw units); it matches 29 exactly.
- **R-G4-1 reads:** the 3-11 checked moves are confined to the 37 O06 count-wrap
  cells and are exactly the vertices, steps and whole-leaf covers of the 167,936
  records that the wrapped unit count had hidden from every reader.
- **Limits (review F7):**
  - Confinement is shown per cell row (band), not per cell. The per-kind sums
    over the 37 cells are exact, so a cancelling move elsewhere in a shared
    band is the only gap.
  - Only the background + background_boundary **sum** (861,107 vertices) is
    derived. The 839,197 / 21,910 split per kind follows K1's on-boundary test
    and is not separately derived.

### 3. 9,064 remainder regeneration: blocked (exact reason)

- Dumps (background, background_boundary, interior_cover) were regenerated at HEAD
  K1 on `013586b5`, `87a01b14` and `4ed9cd80` (`output/scratch-39/dump_*`;
  `4ed9cd80` has failing 0 in all three).
- **R01 alone reproduces exactly:** with `rules_R01_3-13.json` (R01 from `a9432c1`),
  R01 = **920,773** on `87a01b14` (L0 918,297 + L2 2,476) and **920,786** on
  `013586b5`, matching the recorded counts.
- **The 3-13 rule set cannot run:** S02–S05 test the side columns
  `s02_producer_verified` (3-07, byte 144) and `residual_crossing_verified` (3-12,
  byte 146). `k1_triage classify` exits 2 (`unknown column 's02_producer_verified'`).
  `docs/provenance.md` records both producers as deleted and "not regenerable by
  this old recipe"; `dump_join.py` needs the deleted producer-qualified side tables.
  So the **137 / 8,739 / 188 split and the 180 groups cannot be reproduced** without
  a new producer scan (a Design decision; not attempted).

### 4. Basis map (`p1/basis_311.json`)

All failing rows of the three dumped kinds outside the 37 cells are **identical, in
dump order, on all named fields** between `87a01b14` and `013586b5` (background
1,438,414; background_boundary 16,548,105; interior_cover 824, whole file
byte-identical). Inside the 37 cells: background 144 → 157 (+13, one cell),
background_boundary 1,464 → 1,938 (+474, nine cells). So **any** remainder row
outside the 37 cells maps 1:1 to the same row on the 3C-04 basis; rows inside the
37 cells are 3-11-cell rows (157 / 1,938 on `013586b5`). The remainder's own row
identities remain blocked by item 3.

## Phase 2 — counterfactual assignment (reworked after review F1)

Same HEAD K1, same spool; only the disc varies (`4ed9cd80` = 3-14 build change only).

### Build-fixed predicate

- **(a) absent on `4ed9cd80`:** holds for every row (K1 failing 0 in background,
  background_boundary and interior_cover; `p1/k1_314.json`).
- **(c) cell in the 3-14 changed list with a plan 36 P3 class:** holds for every
  tested row. R01: `eo_bg_stitch` 920,693, `eo_division_ceiling` 80
  (`p2/r01_join.json`).
- **(b) item still checked on `4ed9cd80`:** the design's item is "same cell,
  type and **shape**". The first test (`p2/r01_clause_b.py`,
  `p2/allrows_clause_b.py`) keyed the item on the raw failing **vertex**. The
  review (F1) showed that a vertex key cannot separate "fixed" from "removed",
  because a build fix moves or deletes exactly the bad vertex. That test's
  "0 present" result therefore only says that the failing vertex is not at its
  raw position on `4ed9cd80`.
- **Shape-level test** (`p2/shape_clause_b.py`, `p2/allrows/shape_clause_b.json`):
  - The item is the old record that carries the failing vertex. It persists if
    a class>0 record of the same type, in the same leaf, holds the old
    record's **non-failing** vertices at their exact raw positions. That is
    the same source-ring vertices under the same quantisation, and it can only
    be tested in footprint-equal cells.
  - **Identity guard** (re-review N1). The neighbour-masquerade probe found
    that about 5 % of best matches are another, unchanged record. So a vertex
    counts as identity-bearing only if no other old same-type record in the
    leaf holds it and it is not on the leaf's outer vertex-bbox edge. New
    records that are coordinate-identical to an unchanged other old record are
    excluded.
    - **Identity-proven:** a remaining same-type new record holds at least one
      identity-bearing vertex.
    - **Weak:** shared vertices exist, but every one is neighbour-held or on
      the leaf edge, so identity is undetermined.
    - **None:** nothing is shared once the identical neighbours are excluded.
  - The 50 % and ≥ 1 thresholds are implementer choices, not the design's.
  - Only the processed kind's failing vertices are excluded from
    "non-failing" (review N2). This is conservative: it can only lower shares.

| population (87a01b14) | rows | identity-proven (of which ≥ 50 % share) | weak (identity undetermined) | none | type absent (removed) | footprints changed |
|---|---|---|---|---|---|---|
| R01 (background) | 920,773 | **825,634** (288,476) | 94,134 | 925 | 0 | 80 |
| background non-R01 | 517,785 | 489,589 | 26,785 | 461 | 928 | 22 |
| background_boundary | 16,549,569 | 15,180,713 (6,305,975) | 1,249,396 | 92,923 | 25,821 | 716 |
| 013586b5, 37 cells: background / boundary | 157 / 1,938 | 144 / 1,680 | 13 / 242 | 0 / 16 | 0 | 0 |

  There are 0 old-mapping mismatches. The unguarded tiers (≥ 50 % / 1 – < 50 %
  share, before the guard) are kept in the same JSON. The re-review's probe
  (`output/scratch-39/review2/partial_probe.json`) found a median of 28 shared
  vertices in the partial tier and 39 in the ≥ 50 % tier. Run: under the lock,
  656 s. The per-row arrays are kept keyed by (level, cell, leaf, shape,
  vertex) in `output/scratch-39/keep/*_keyed.npz`, so they do not depend on dump
  row order.

### R01 exclusivity: disproven by count; cause per Design's ruling

- **Disproven by count.** On the 4ed9cd80 counterfactual (same K1, same spool,
  build-only change), **825,634** R01 rows satisfy all three clauses with an
  identity-proven record: (a) absent, (b) the record persists, re-encoded and
  checked with 0 failures, and (c) an `eo_bg_stitch` cell.
- **Cause, per Design's advance ruling** (2026-10-06 12:54 AEST, relayed by the
  parent): a row that the counterfactual proves was fixed by the 3-14 build
  change, and that still satisfies R01's rationale, takes the build change as
  its cause. The R01 rationale is recorded as **superseded**, not as a second
  cause. These 825,634 rows are therefore `build:eo_bg_stitch`, with R01
  (3-07 Amendment 4) superseded. Design open question 1 is answered by that
  ruling; nothing goes to Cody.
- **Rows where the build fix is not proven** (they stay `checker` R01 under
  design rule 3, with the reason; each is a named residual):
  - 94,134 rows with weak identity (shared vertices are all neighbour-held or
    on the leaf edge): **R-G5-4-a**;
  - 925 rows with no traceable record once identical neighbours are excluded,
    so (b) fails: **R-G5-4-b**;
  - 80 rows in `eo_division_ceiling` cells, whose footprints changed and so
    are untested: **R-G5-4-c**.
- `rules_bg.json`: only the R01 note changed (the rule, its predicate and order
  are unchanged). Rule matching still yields `checker` for these rows; the
  per-row cause of record is `assignment.tsv`.
- The re-review noted (N4) that the predicate cannot tell "3-14 fixed a
  defective vertex" from "3-14 stopped emitting a vertex Amendment 4 deems
  valid". Design's ruling assigns the build cause in either case.

### Remainder (R-G5-1, R-G5-2) at count level

- The rows inside the 37 cells on `013586b5` were tested directly. By the basis
  map, the rows outside them are the `87a01b14` rows above.
- At most 123,335 background rows (928 + 1,386 + 120,919 + 102) and 1,368,856
  background_boundary rows (25,821 + 92,923 + 1,249,396 + 716) of `013586b5`
  fail, or cannot be proven to satisfy, the predicate. Every other row is
  identity-proven.
- Without the remainder's row identities (Phase 1 item 3), no remainder row
  can be assigned. The 137 / 8,739 split stays blocked on the deleted
  side-column producers.

## Phase 3 — polygon 65623 classified

Source `(L0, home 1689,508, record 0, type 288)`: 1,809 stored coordinates (+1
closing; 1,810), lat −44.26…−34.39, lon 134.23…149.03; its home cell holds no other
record (no roads, no names).

### Exact producer identity by build counterfactual (`p3/`)

- **Window builds at `b7c7c42`** (the `87a01b14` producer) over L0
  `[1414,1890) × [274,750)`, the bounding rectangle of every type-288 failing row
  inside the source bbox (`p3/p65623_screen.json`), with frame dumps:
  - **ctl:** the pinned spool;
  - **cf:** the pinned spool minus this source. The CF drops the home cell from a
    private `level_0.idx`; every data file is a read-only symlink to the pinned
    spool (`p3/make_cf_spool.py`).
- **Control:** ctl frames equal `87a01b14`'s frames in **all 226,576 window cells**
  (per-cell multiset of frame sha256; 0 mismatches).
- **The source's products:** ctl background records absent from the cf frame of the
  same leaf (multiset of record bytes): **58,032 records in 58,030 leaves, all type
  288**. The cf adds no record; one name section differs (the build's name halo
  count moves by 1); nothing else changes.
- **Join** (`p3/join65623.py`, `p3/join65623.json`): every failing row in the window
  is mapped to its leaf and record, validated by re-deriving the row's raw vertex
  (vertex kinds) or type (interior_cover) from the record bytes: **0 vertex or type
  mismatches**.

| kind (87a01b14) | rows | in window | in a cell the source changes | **produced by 65623** |
|---|---|---|---|---|
| background | 1,438,558 | 296,893 | 106,493 (all other records) | **0** |
| background_boundary | 16,549,569 | 3,065,225 | 544,449 (all other records) | **0** |
| interior_cover | 824 | 297 | 16 (all other records) | **0** |
| completeness, 3C-04 rule (`1cf40f8`) | 752 | — | 0 of 703 type-288 rows in a cell the ring meets | **0** |
| completeness, HEAD rule | 65 | — | 0 of 52 type-288 rows in a cell the ring meets | **0** |
| name_anchor | 1 | 0 | source has no name record | **0** |

  Completeness rows ("a spool polygon of this type meets the cell but no decoded
  piece of it does") were tested by an exact ring–cell meet (vertex, edge
  crossing, or rectangle inside the ring; `p3/completeness65623*.py`). (An
  earlier sentence citing a 600-cell agreement sample with the cf had no
  committed artefact and is withdrawn.)
- **Why the window is exhaustive:** a record produced from this source is L0,
  type 288, and its vertices lie inside the source ring's lat/lon bbox (+0.01°
  for quantisation). Clipping to a cell or leaf only produces points of
  source ∩ leaf, and a whole-leaf cover's corners lie inside the ring.
  `p3/p65623_screen.json` applies these necessary conditions to every row:
  background 197,676 rows qualify, background_boundary 765,932, and
  interior_cover 0. The window is their bounding rectangle, so no row outside it
  can be produced by the source. Inside it, the counterfactual decides.
  - The source bbox itself also lies inside the window in cell terms. A linear
    fit of dump lat/lon to ix/iy (residual ≤ 0.51 cell) gives ix 1414.7–1888.4
    and iy 275.0–748.8, against the window `[1414,1890)×[274,750)` (the review
    checked this). So every leaf the source could produce into was rebuilt.
  - The multiset diff attributes identical twin records in a leaf arbitrarily.
    This is harmless here: 0 rows were produced, and twins carry identical
    vertices.
- **Design contract 4 (the 3C narrative's location):** 3C-04 described
  whole-cell fill pieces "4–6 cells outside" the polygon. The cells 3-06/3-07
  sampled for that claim, the covers `(1728,162)` and `(1771,203)`, have other
  demonstrated producers (`cause_table.md`). The exhaustive join above covers
  every such row on `87a01b14`, whatever its cell. The narrative's
  winding/parity contradiction was not reproduced (3-07: no proper crossing,
  and the 3,969-point grid agrees).
- **Classification (design contract 2):** **no 3C-04 failing item is produced by
  source 65623**, in any of the five kinds. The alleged disc defect has no
  failing-item footprint. Its geometry facts stand as facts, not a cause: the
  closing edge (1,908,357.17 raw; from (−34.39, 134.39) to (−38.86, 147.32)), no
  proper crossing, and the source produces 58,032 type-288 records whose vertices
  carry no failing row.

### Surfaces updated (Phase 2–3 outcomes)

- **`p2/assignment.tsv`** is count-level, not per row as the design asked:
  - R01: 825,634 `build:eo_bg_stitch` (R01 superseded, Design ruling 12:54);
    94,134 + 925 + 80 stay `checker` (R-G5-4-a/b/c);
  - the 8,876 remainder rows: `identity blocked`.

  The per-row arrays are kept keyed in `output/scratch-39/keep/` (BOM:
  `docs/provenance.md` § `output/scratch-39/`).
- **`rules_bg.json`:** the R01 note states the measured facts and the pending
  ruling. The note only; the rule and cause are unchanged.
- **`cause_table.md`:** the 65623 section is rewritten from the Phase 3
  evidence. The two older sentences that called the contract unmet are now
  marked historical.
- **OVERVIEW:** the historical-remainder clause gives the plan 39 outcome;
  R-G4-1 is removed from the open list.
- **`docs/provenance.md`:** a `scratch-39` section (review F4).
- **`p2/r01_join.json`:** its `clause_b` field is superseded by
  `p2/allrows/shape_clause_b.json`.
- **Protected snapshot** (`historical_bg/protected_after_39.json`, taken against
  plan 41's last snapshot): all 5 protected discs and the spool fingerprint are
  identical.

### Residual rows (`phase3_synthesis/residuals.tsv`)

- **R-G4-1: discharged** (Phase 1 items 1–2). The 3-11 checked moves are
  confined to the 37 O06 count-wrap cells. They equal, exactly, the vertices,
  steps and whole-leaf covers of the 167,936 formerly unread records. Limits
  as stated in item 2.
- **R-G5-3: discharged** (Phase 3). No 3C-04 failing item in any kind is
  produced by source 65623. The geometry facts stay recorded as facts.
- **R-G5-4: discharged for the proven rows** (825,634 `build:eo_bg_stitch`,
  R01 superseded per Design's 12:54 ruling), with named children:
  - **R-G5-4-a** (94,134, weak identity): more work, either a stronger
    identity test (a source counterfactual) or a Design waiver;
  - **R-G5-4-b** (925, no traceable record): R01 `checker` stands under design
    rule 3; named, and Design may reclassify;
  - **R-G5-4-c** (80, footprints changed): untested; needs a window
    counterfactual at `d35b565` or a Design waiver.
- **R-G5-1, R-G5-2: stay open** (blocks-phase3, owner Design). The basis map
  states the row mapping. At most 123,335 background and 1,368,856
  background_boundary rows fail, or cannot be proven to satisfy, the
  predicate.
  The row identities need a new producer scan for the deleted side columns;
  that is a Design ruling.
