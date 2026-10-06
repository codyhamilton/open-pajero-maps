# Implementation — 38 row 246 (type 321, L0 (834,886)) clip-inclusion hypothesis

Master direct. The oracle in force is `4e6b0de7…` (no successor landed).
Phase 1 is light: it uses bounded leaf preads and one spool-cell pread by
offset/length. One streamed PBF scan ran under the heavy wrapper (`flock`),
taking 486 s with 215 MiB RSS.

## Phase 1 — R record decoded and matched; verdict

**Witness** (`witness/`):

- **`witness_246.py`:** bounded R/G leaf-slot decode through
  `RReader`/`LeafIndex`, plus one spool pread. It writes
  `row246_witness.json`.
- **`probe246.c`:** production `kw__bg_shape` on cell-local raw coordinates,
  using the spool record's type, mult and flags.
- **`pbf_scan_246.py`:** a streamed nodes → ways → relations scan of the
  pinned PBF around R's record. It writes `row246_pbf_scan.json`.

### 1. R record (DESIGN Contract 1)

The R disc is `/run/media/codyh/464210-8480/ALLDATA.KWI` (R `8c2d2027`,
protected; read by bounded pread only).

- **Slot:** `resolved`, one leaf `[1730]`.
  - File offset 360,761,152, length 22,080, sha256 `7c3b4558…0777`.
  - The leaf frame spans several of our L0 cells. Its origin is at cell
    (832,884): frame-raw (11716, 9649) is cell-raw (3524, 1457), an offset
    of 8192 = 2 cells on each axis.
- **Type 321:** the leaf holds 11 type-321 class-2 records. Exactly **one**
  is cell-local to (834,886) (meet branch a).
- **The cell-local record:**
  - Frame offset 622 (relative to the background frame), leaf offset
    13,122, file offset **360,774,274** (= leaf offset + 13,122), 66 bytes,
    sha256 `fdc96d16…083a`.
  - Header words `[33, 57371, 321, 0, 19908, 17841]`: record length 66 B,
    27 deltas (28 coordinates), code 321, mult 1.
  - The ring is **closed** (first = last).
  - Cell-raw bbox x 3524–3972, y 919–1996 (about 324 m × 608 m).
  - **area2 = +621,301**. It has real interior area, about 1.85% of the
    cell.
  - **0 edge contacts:** no vertex lies within 0.5 of x = 0/4096 or
    y = 0/4096.
  - Lat/lon bbox −31.53699 … −31.53151, 116.08939 … 116.09280.
  - Full bytes, frame-raw and cell-raw coordinates are in
    `row246_witness.json` `R.type321[7]`.

### 2. G control (Contract 2)

- **Disc:** `output/scratch-34/G_new/ALLDATA.KWI`, oracle `4e6b0de7`,
  1,692,079,168 B, mtime 2026-10-06 09:35 AEST.
  - The witness does not re-hash it. The sha was verified by that run's
    protected-disc snapshot, `output/scratch-41/bench/protected_before.json`
    (`g_oracle_in_force`), taken at 13:48 AEST.
- **Same slot:** leaf `[1730]`, 3,360 B, sha256 `a0cd4d21…efa`.
- **Records by class and code:** `class2:code288` 4 and `class2:code291` 1.
  **Type 321: 0**, confirmed.
  - Two of the four 288 records are **full-cell rectangles**, 5 coordinates
    each, and both contain R's ring centroid.
  - 288 is the L0 catch-all for a non-road ring with unrecognised tags.
  - Per-record geometry is in `G.records`.

### 3. Spool demander (Contract 3)

- **Spool cell:** (834,885) was read by the recorded offset 2,806,410,336
  and length 34,248; the index row matches. Cell sha256
  `c98706bf…e8`. **Ordinal 15:** class 2, type 321, label "green belt,
  park", mult 1, flags 0, 58 coordinates.
- **Location:** cell-raw bbox relative to (834,886) is x 3888.5–4149.8,
  y −1112.6 … +2.39. It lies almost entirely in the cell below and only
  touches y = 0 at one vertex.
- **Production `bg_shape` clip:** returns 0 B, nrec 0.
- **Python mirror:** clip ring (4021.03, 0) – (4021.433, 2.392) –
  (4021.433, 0); q = 2, area2 −0.964 unrounded and 0 after rint; not
  emitted. This reproduces plan 14's `encoder_drops_clipped_source_sliver`.
- **No OSM id:** the spool's background columns carry none (Open question 1).
  The match is by geometry only.
- **Spool type-321 features reaching the cell:** across a 5 × 5
  source-cell neighbourhood, only this one.
- **Spool class-2 features of any type** in that window that clip into the
  cell (`spool_any_type_class2_reaching_cell_5x5`): 4. They are 291 river,
  321 park, and two partial 288s. None contains R's ring centroid
  (3684, 1463). The nearest is the demander, with an R-vertex distance of
  917.9 raw units.
- **Two G full-cell 288 rectangles** come from larger unmapped-tag rings
  whose source cells lie outside that window. They enclose the cell.
  Neither can be R's record:
  - an enclosing ring clips to a full-cell record, never to R's 28-vertex
    interior ring;
  - R's slot carries no 288 at all.

### 4. Match (Contract 4; predicate fixed before measuring)

- **Predicate:** written into `witness_246.py`'s docstring and copied into
  the JSON. Every R vertex must lie within 1 raw unit of the demander's
  unrounded clip segments, or of the cell edge it touches. In addition,
  area2 must have the same sign, and |A_R − A_clip| ≤ 2 × perimeter_R.
- **Predicate notes** (review F2, F3):
  - The edge term is implemented as the nearest of the four cell lines. That
    is looser than "the edge segment it touches", so it can only add
    matches.
  - The magnitude bound 2 × perimeter is first-order.
  - The mirror clip ring is oriented positive, as `bg_shape` orients closed
    rings, before the comparison.
  - The predicate and the result landed in the same commit (`7848ac8`), so
    "fixed before measuring" is asserted rather than evidenced. The
    conclusion holds under any reasonable predicate.
- **Result: no match.**
  - All **28/28** R vertices lie more than 1 unit from both; the nearest is
    917.9 units away.
  - The magnitude differs: +621,301 against +0.964, beyond the 5,596 bound.
    The sign agrees once oriented, so it is not used as evidence.
  - Hausdorff distance R ↔ clip is 2,053.8 raw units.
- **Nearest alternative:**
  - Among the spool type-321 features reaching the cell, the demander is the
    only one, so there is no alternative.
  - Among the 11 R polygons, the other 10 are not cell-local; they lie in
    other cells of the leaf frame.
  - Among the 284 PBF code-321 candidates, all give 0 in-cell records under
    the original, clipped and unit-mult modes. No candidate has in-cell
    geometry, so no nearest in-cell alternative exists. This also excludes
    an enclosing 321-mapped area.
    - Sources: plan 30 `triage/source_parity/open_rows_account.md` (r4,
      sha256 `34c5c5bf…`) and the row-246 `discriminator_records` in
      `triage/source_parity/disposition.tsv` (`candidates_by_code` 321: 284;
      emitters 288: 11, 291: 1).
    - The listed supply gaps do not change this:
      - The vertex-limit relations are r80500, r2316598, r7493850, r8043873
        and r8653540. Their member ways are in the extract, and none has a
        node in R's box, so they cannot form R's interior ring.
      - The 29 relations with member ways missing from the extract cannot be
        inspected. A missing way that formed R's ring would be an instance
        of the stated cause, a feature absent from the pinned extract, not
        a counter-example.
- **Pinned PBF around R's record:**
  - `australia-260824.osm.pbf` was scanned over the R bbox plus about 150 m.
  - There are **3 nodes, all on one way**: w553641737 `highway=residential`
    "McGlew Road". There are no tagged nodes and no relation.
  - Stated limit: a way with no node inside the box is not seen, whether it
    crosses the box or encloses it. Such a way cannot form R's interior
    28-vertex ring. At least two enclosing unmapped-tag rings exist; they
    are the G full-cell 288s. For the demanded type, the plan 30 candidate
    result covers the enclosing case.

### 5. Verdict: **`H3-other-feature`** (H1 rejected)

R's in-cell 321 record is a separate, self-contained, closed polygon with
real interior area. It touches no cell edge and lies about 918–2,054 raw
units (roughly 0.5–1.5 km) from the edge-touching demander. It is not a clip
of the demander under any inclusion rule.

**H1 is rejected.**
- R does not keep our degenerate sliver. The sliver (q 2, area2 0) and R's
  record share no geometry.
- No inclusion rule can make our encoder emit R's record, because our source
  has no feature there.

**H2 does not apply.** H2 needs R's ring to be our demander with different
geometry. R's ring is disjoint from the demander's footprint, and has no
edge contact through which a larger version of the demander could reach it.

**Cause.** R's source data had a 321 ("green belt, park") polygon at
−31.534, 116.091 that the pinned 2026-08-24 OSM extract does not contain.
- In that extract, no OSM object has a node in the box except McGlew Road.
- At least two unmapped-tag areas enclose the cell; those are the G
  full-cell 288s.

This is a source-data difference, not an encoder rule. It is proven against
the pinned extract only. R's source vintage is unknown, so the cause is a
class of difference, not an identified OSM object. No Overpass history
query was run; external fetch was not authorised for this plan.

**Plan 14's `repaired-not-representable` science is not challenged.** The
demander sliver is in that class (area2 0 after rint), and R has no record
for it either.

Not done in Phase 1: any encoder change (non-goal).

### Phase 1 review

Claude CLI clean-context seat (disclosed; Codex is weekly-limited):
**PASS_WITH_FOLLOWUPS**. The text is kept as `reviews/p1-REVIEW.md`.

- **F1:** the any-type reach and the G full-cell 288 enclosers are now in the
  witness, and the text is corrected.
- **F2:** the mirror ring is oriented positive; the sign is no longer used as
  evidence.
- **F3:** the predicate interpretation and timing are stated.
- **F4:** the absence of a 284-candidate alternative is stated, with the
  artefact sha and the supply gaps.
- **F5:** the limit text now covers crossing ways and the unknown vintage.
- **F6:** the G disc size, mtime and snapshot are recorded.
- **F7:** both offset bases are stated.

The witness was re-run after the fixes; the verdict is unchanged.
