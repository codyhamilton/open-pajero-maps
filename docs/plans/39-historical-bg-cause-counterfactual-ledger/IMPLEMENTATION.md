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

## Phase 2 — counterfactual assignment (R01 complete; all rows tested; remainder identity blocked)

Same HEAD K1, same spool; only the disc varies (`4ed9cd80` = 3-14 build change only).

### Build-fixed predicate on all 920,773 R01 rows

- **(a) absent on `4ed9cd80`:** holds for all (K1 failing 0 in background,
  background_boundary and interior_cover; `p1/k1_314.json`).
- **(c) cell in the 3-14 changed list with a plan 36 P3 class:** holds for all.
  `eo_bg_stitch` 920,693, `eo_division_ceiling` 80 (`p2/r01_join.json`). The
  517,785 non-R01 background rows are also all in changed cells (517,763 /22).
- **(b) item still checked on `4ed9cd80`:** item = the failing G vertex (level,
  cell, leaf path, type, raw vertex). Test (`p2/r01_clause_b.py`): every row's
  (shape, vert) is first re-derived from the `87a01b14` record bytes (raw vertex and
  type; **0 mapping mismatches**); then the same leaf on `4ed9cd80` (only where plan
  36 P3 says footprints are equal) is searched for a record of the same type with a
  vertex at the same raw position.
  - **920,693 rows: the item is gone on `4ed9cd80`** (288: 620,286; 291: 277,391;
    289: 15,823; 578: 7,193). **0 present.**
  - **80 rows** (the `eo_division_ceiling` cells) have changed footprints, so leaf
    identity is undefined; untested.
  - **Control** (`p2/r01_clause_b_control.json`): over 400 random R01 leaves, 79.2%
    of the 340,772 ordinary vertices are found on `4ed9cd80` by the same test, and
    0 of the 8,442 R01 vertices in those leaves.
- **Verdict (design rules 3–4):** no R01 row satisfies the build-fixed predicate,
  because (b) fails: 3-14 **removed** the items rather than fixing them. Per the
  design, removed items are never `build-fixed`. **R01's checker attribution stands
  for 920,693 rows, with the reason "item removed by 3-14 (`removed-by-3-14`)"**, and
  is not contradicted by the counterfactual. The 31 type-291 fills of the L0/291
  window that might "overlap build" are inside this population and fail (b) the same
  way. Open question 1 (dual-cause) is not raised: no row satisfies both.
- **80 rows remain named:** R01 rows in `eo_division_ceiling` cells, clause (b)
  untestable by leaf identity.
- `rules_bg.json`: unchanged (the design allows notes only, and no predicate change
  is proven). The R01 note text update is left to close-out with review.

### All background and background_boundary rows (`p2/allrows_clause_b.py`)

The same clause (b) test, run over **every** failing row of the two kinds on
`87a01b14` (`p2/allrows/allrows_clause_b.json`; per-row status in
`output/scratch-39/allrows/<kind>.status.u8`, 1 present, 2 removed, 3 footprints
changed, 4/6 leaf missing, 5 mapping mismatch):

| kind (87a01b14) | rows | item removed on `4ed9cd80` | footprints changed (untestable) | present | mapping mismatch / leaf missing |
|---|---|---|---|---|---|
| background | 1,438,558 | **1,438,456** | 102 | **0** | 0 |
| of which non-R01 | 517,785 | 517,763 | 22 | 0 | 0 |
| background_boundary | 16,549,569 | **16,548,853** | 716 | **0** | 0 |

- **No failing row of either kind has its item still present on `4ed9cd80`.**
  Every testable row is `removed-by-3-14`; the untestable rows are exactly those
  in the plan 36 P3 cells whose footprints changed (background 80 R01 + 22 non-R01).
- **The 3-11 basis** (`p2/allrows_311_cells.py`, `p2/allrows/allrows_311_cells.json`):
  the remainder was counted on `013586b5`. By the basis map, its rows outside the 37
  cells are the `87a01b14` rows above. The rows inside the 37 cells were tested
  directly on `013586b5`. Background: 157 of 157 removed on `4ed9cd80`.
  Background_boundary: 1,938 of 1,938 removed. There are 0 mapping mismatches and
  no row in a footprint-changed cell. So the 102 / 716 footprint-changed rows all
  lie outside the 37 cells, on both bases.
- **Consequence for the 9,064 remainder:** the row identities stay unreproducible
  (item 3). Even so, every failing background and background_boundary row of
  `013586b5` is either `removed-by-3-14` or one of the 102 / 716 rows in
  footprint-changed cells. So, at count level, each remainder row is one or the
  other. No remainder row can be `build-fixed` (clause (b) fails for every
  testable row), so the counterfactual assigns no new build cause. The
  137 / 8,739 / 188 split and the 180 groups stay blocked on the side-column
  producers (item 3).
- Runs: under the lock; `87a01b14` all rows 394 s (peak RSS 4.8 GiB), `013586b5`
  37 cells 145 s; both exit 0.

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
  piece of it does") were tested by an exact ring–cell meet (vertex, edge crossing,
  or rectangle inside the ring) and by the cf; the meet test agrees with the cf on
  600 sampled cells (300 changed: all meet; 300 unchanged: none).
- **Classification (design contract 2):** **no 3C-04 failing item is produced by
  source 65623**, in any of the five kinds. The alleged disc defect has no
  failing-item footprint. Its geometry facts stand as facts, not a cause: the
  closing edge (1,908,357.17 raw; from (−34.39, 134.39) to (−38.86, 147.32)), no
  proper crossing, and the source produces 58,032 type-288 records whose vertices
  carry no failing row.

### Surfaces updated (Phase 2–3 outcomes)

- **`p2/assignment.tsv`** is count-level, not per-row as the design asked: R01
  920,693 `checker` / `removed-by-3-14` and 80 `unattributed` (R-G5-4-a); the
  8,876 remainder is `identity blocked`. Per-row status for every
  background-family failing row on `87a01b14` is in
  `output/scratch-39/allrows/<kind>.status.u8`. It is regenerable by
  `p2/allrows_clause_b.py`, and the remainder can join it by row index once its
  identities exist.
- **`rules_bg.json`:** the R01 note gained the plan 39 result (note only; rule
  and cause unchanged).
- **`cause_table.md`:** the 65623 section is rewritten from the Phase 3 evidence.
- **OVERVIEW:** the historical-remainder clause now gives the plan 39 outcome;
  R-G4-1 is removed from the open list.
- **Protected snapshot** (`historical_bg/protected_after_39.json`, taken against plan
  41's `wall/guard/protected_before.json`): all 5 protected discs and the spool
  fingerprint are identical.

### Residual rows (`phase3_synthesis/residuals.tsv`)

- **R-G4-1: discharged** (Phase 1 items 1–2). The 3-11 checked moves are confined
  to the 37 O06 count-wrap cells and equal, exactly, the vertices, steps and
  whole-leaf covers of the 167,936 formerly unread records.
- **R-G5-3: discharged** (Phase 3). No 3C-04 failing item in any kind is produced
  by source 65623; the geometry facts stay recorded as facts.
- **R-G5-4: discharged, with child R-G5-4-a.** R01 exclusivity against build holds
  for 920,693 rows (`removed-by-3-14`, clause (b) fails; the 31 type-291 fills
  included). **R-G5-4-a** (new, blocks-phase3, owner Design): the 80 R01 rows in
  `eo_division_ceiling` cells, whose footprints changed so that clause (b) cannot be
  tested by leaf identity.
- **R-G5-1, R-G5-2: stay open (blocks-phase3, owner Design).** The basis map now
  states the row mapping: outside the 37 cells, 1:1 and identical in order; inside
  them, 3-11-cell rows. The all-rows test puts every remainder row at
  `removed-by-3-14` or in a footprint-changed cell at count level. The row
  identities (137 / 8,739 and the 180 groups) need a new producer scan for the
  deleted side columns; that is a Design ruling.
