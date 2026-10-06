# Plan 30 row 246: type-321 record in L0 (834,886) — proven cause H3-other-feature

Plan 38 closed in two phases with a **proven cause**. The clip-inclusion
hypothesis (H1) is rejected; the verdict is **H3-other-feature**.

- **R's record:** a 28-vertex interior park ring (type 321, area2 +621,301,
  0 edge contacts, about 324 × 608 m, near −31.534, 116.091).
- **No match:** it matches no clip of the spool demander.
- **Source:** no geometry in the pinned 2026-08-24 OSM extract can produce
  it. No OSM object has a node in R's box except McGlew Road. None of the
  284 code-321 candidates has in-cell geometry.
- **Cause class:** "source-data: R feature absent from pinned OSM extract".
- **Changes:** no encoder change, so no successor oracle; the oracle in force
  stays `4e6b0de7`.
- **Records:**
  - Plan 30 row 246 has an append-only correction row in
    `triage/source_parity/disposition.tsv`.
  - `residuals.tsv` R-G9-1 is discharged.
- **Witness:** kept at
  `docs/plans/04-c-core-orchestration/triage/source_parity/row246/`.
- **Review:** the P1 review is by a Claude CLI clean-context seat
  (disclosed; Codex is weekly-limited).

Plan 04 Phase 3 is **not** claimed closed.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Plan 38: plan 30 row 246. Byte-decode R's in-cell 321 record, match it to the kept edge-touching 321 relation, and test the clip-inclusion-rule hypothesis (R keeps boundary-touching or degenerate clips; our encoder drops them). The outcome is either a fix where no other cell or kind changes (K1 0 everywhere; disc diff confined; new successor oracle recorded) or a proven cause. Never a relabel. Oracle `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448` or later. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`, bounded or streamed. Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Why This Existed
Plan 30 is closing at 341 supply-path / 0 unfixable / 1 carried. Row 246 is the carried row: `residuals.tsv` R-G9-1, `maps-parity-carried`.

**Ground (master `b10e787`):**

| Fact | Value | Source |
| --- | --- | --- |
| Row key | L0 (834,886), code 321, p0..p6 = 0, dump_row 246, plan 28 rule O05 | `30-2-01-source-data-parity/fingerprint.tsv` |
| R | 11 polygons of type 321 near the cell. **1 is cell-local** (meet branch a, leaf_path [1730], 28 coords). Normalised local signature spans the full 0–1 range on both axes | fingerprint `R_cell_local_meets`, `R_local_signatures`; `output/scratch-14/cell_local/proofs/246.json` |
| G | 0 type-321 records in the cell on `4ed9cd80` and `2ee3456a`. `4e6b0de7` differs only in 5 empty shells | fingerprint `G_*_type_count`; plan 34 |
| Spool demander | background ordinal 15 of source cell (0,834,885), branch b, 58 coords. Spool offset 2,806,410,336, length 34,248. Trigger vertex at cell_raw (4021.43, 2.39), lat/lon (−31.5416545, 116.0931811), on the shared edge | fingerprint `spool_demander_identity`; `output/scratch-14/witnesses/0246_requirement.json` |
| Clip | `clipped_ring_q` 2, `clipped_ring_area2` 0, `encoder_emits` False, mechanism `encoder_drops_clipped_source_sliver` | fingerprint |
| Supply search | PBF gap-free. 284 code-321 candidates reach the windows (natural=wood 274, scrub 10). Every one gives 0 in-cell records under original, clipped and unit-mult | `open_rows_account.md` (r4) |
| Related science | Plan 14 / 3-15: 188 + 86 completeness demands are sub-unit slivers that `rint` annihilates (`checker:repaired-not-representable`). K1 completeness now demands only representable footprints (`a890662`, `0dc5cac`) | `completeness_3-15_cell_local.md` L18 |

**Tension to resolve, not assume.** A 28-coord R polygon whose local signature spans the cell is not obviously a degenerate edge clip. The hypothesis is only true if R's record decodes to a boundary-hugging or zero/near-zero-area ring that matches our clipped sliver. If R's polygon has real interior area, the cause is elsewhere: different source geometry, or a different feature.

## What Landed

Master direct; no `parser/` change.
- **Phase 1:** R record decode, G control, spool demander clip through the
  production `bg_shape`, fixed predicate, and a streamed PBF box scan under
  the heavy lock. Verdict H3; the review follow-ups F1–F7 are applied.
- **Phase 2:** proven-cause disposition (correction row), R-G9-1
  discharged, R-G9-2 owner clarified, OVERVIEW updated.
- **Close-out:**
  - The witness was moved to `triage/source_parity/row246/`.
  - Its repo-root lookup and probe include are made path-independent.
  - It was re-run at the new path and gives byte-identical
    `row246_witness.json`.

Master direct. The oracle in force is `4e6b0de7…` (no successor landed).
Phase 1 is light: it uses bounded leaf preads and one spool-cell pread by
offset/length. One streamed PBF scan ran under the heavy wrapper (`flock`),
taking 486 s with 215 MiB RSS.

## Phase 1 — R record decoded and matched; verdict

**Witness** (now `docs/plans/04-c-core-orchestration/triage/source_parity/row246/`):

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
**PASS_WITH_FOLLOWUPS**. The text is kept as `triage/source_parity/row246/reviews/p1-REVIEW.md`.

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

## Phase 2 — proven cause (H3 branch)

- **Outcome branch:** DESIGN Contract 2.4 (H2/H3). The proven cause is
  recorded with the R bytes and the source evidence, all from Phase 1.
- **No fix:** no encoder change, so no successor oracle, no blast-radius
  build, and no K1, Perth or goldens step. Nothing changed in `parser/`. The
  oracle in force stays `4e6b0de7`.
- **Disposition:** an append-only correction row for dump_row 246 in
  `triage/source_parity/disposition.tsv`. The verdict is
  `proven-cause:H3-other-feature`, with cause class "source-data: R feature
  absent from pinned OSM extract". The original `conflict-open` row stays;
  there are now 343 data rows.
- **`residuals.tsv`:**
  - R-G9-1 is discharged by plan 38 Phase 2.
  - R-G9-2 is unchanged in substance. Its owner text now records that plan
    38 took row 246 only, because the 341-row implement unit is a DESIGN
    non-goal.
- **OVERVIEW:** the plan 30 bullet and the "what remains" row name the
  proven cause.
- **Limit:** R's source vintage is unknown, so the R-side feature is not
  identified as an OSM object. The proof is that the pinned extract has no
  geometry that could produce R's ring.
- **Witness:** at close it moves to `triage/source_parity/row246/`.

## Commits

- `7848ac8` — P1 witness and verdict (`:1`).
- `10e6dbe` — P1 review follow-ups (`:1`).
- `d67a7a9` — P2 proven cause, disposition correction, residuals and
  OVERVIEW (`:2`).
- Close-out (`:done`).

## Not done

- The R-side feature is not identified as an OSM object: R's source vintage
  is unknown, and no external history query was authorised.
- R-G9-2 (341 supply-path rows) is out of scope (DESIGN non-goal) and stays
  with the successor implement unit (Design).
- The terminal review is the same disclosed Claude CLI seat. Codex
  confirmation waits for the Codex reset (2026-10-10 11:50 AEST).
