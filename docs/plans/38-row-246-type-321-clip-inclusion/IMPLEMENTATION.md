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
  - Frame offset 622, file offset **360,774,274**, 66 bytes, sha256
    `fdc96d16…083a`.
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

- **Disc:** `output/scratch-34/G_new/ALLDATA.KWI`, oracle `4e6b0de7`. Its sha
  is in the protected-disc snapshot `output/scratch-41/bench/protected_before.json`.
- **Same slot:** leaf `[1730]`, 3,360 B, sha256 `a0cd4d21…efa`.
- **Records by class and code:** `class2:code288` 4 and `class2:code291` 1.
  **Type 321: 0**, confirmed.

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
- **Spool type-321 features reaching the cell:** across a 5 × 5 source-cell
  neighbourhood, only this one. Across **any** type, 4 features reach the
  cell (321 park, 291 river, 288 ×2). None contains R's ring centroid
  (3684, 1463). The nearest is the demander, with an R-vertex distance of
  917.9 raw units.

### 4. Match (Contract 4; predicate fixed before measuring)

- **Predicate:** written into `witness_246.py`'s docstring and copied into
  the JSON. Every R vertex must lie within 1 raw unit of the demander's
  unrounded clip segments, or of the cell edge it touches. In addition,
  area2 must have the same sign, and |A_R − A_clip| ≤ 2 × perimeter_R.
- **Result: no match.**
  - All **28/28** R vertices lie more than 1 unit from both.
  - The sign differs (+621,301 against −0.964), and so does the magnitude.
  - Hausdorff distance R ↔ clip is 2,053.8 raw units.
- **Nearest alternative:**
  - Among the spool type-321 features reaching the cell, the demander is the
    only one, so there is no alternative.
  - Among the 11 R polygons, the other 10 are not cell-local; they lie in
    other cells of the leaf frame.
  - Among the 284 PBF code-321 candidates (plan 30
    `open_rows_account.md`), all give 0 in-cell records under the original,
    clipped and unit-mult modes. This also excludes an enclosing
    321-mapped area.
- **Pinned PBF around R's record:**
  - `australia-260824.osm.pbf` was scanned over the R bbox plus about 150 m.
  - There are **3 nodes, all on one way**: w553641737 `highway=residential`
    "McGlew Road". There are no tagged nodes and no relation.
  - Stated limit: an area with no node inside the box is not seen. For the
    demanded type, the plan 30 candidate result covers that case.

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
−31.534, 116.091 that the pinned 2026-08-24 OSM extract does not contain. In
that extract the area holds only McGlew Road. This is a source-data
difference, not an encoder rule.

**Plan 14's `repaired-not-representable` science is not challenged.** The
demander sliver is in that class (area2 0 after rint), and R has no record
for it either.

Not done in Phase 1: any encoder change (non-goal).
