# Architecture

System shape and stage contracts live in `docs/design/target-disc.md` (program of record). This
doc records the shape at a glance and, importantly, **what is not yet known**, so unknowns are
not re-derived. Evidence for each item is in the cited doc.

## Shape

OSM PBF (Australia) → geometry extraction to a per-cell spool → assembly to `ALLDATA.KWI` →
(future) index and route-planning layers → UDF-bridge image → burn. Evaluation is offline:
`parser/compare_disc.py` compares the generated disc to the reference disc.

## Unknowns

Not resolved by WP1; each needs a spike (format analysis or census) before its work package can
be designed. None of these should be decided by guess.

### Map layer (addressed by `docs/plans/03-map-layer-parity-remediation/`)

- Whether R's parcel-local coordinate range (4096/16384) is the true full-cell range (strong hypothesis).
- What Map Frame header words 6, 7, 9–11 and the link flags `link_id_flag` / `selected_link_flag` mean to the head unit.
- Whether the head unit reads header word 0 or `dipid`, requires `A=` / `1=` name tags for search, or has per-buffer size limits below the u16 ceiling.

### WP2 — route planning

- Ext frames `0xAF100100` (≈62% of ext bytes) and `0xAF100300`: undecoded, currently omitted without evidence.
- Turn restrictions: only 1 of 57,372 OSM restriction relations resolved in region 178; cause not diagnosed; via-way restrictions skipped.
- Road class and flag mapping for RP links is a first-pass guess; `is_suburb`, `is_semi_urban_highway`, `is_rotary` always false.
- OSM has 14–27× R's routing nodes; region byte budgets untested.
- Whether RP-layer and map-layer link ids must agree in R's encoding.

### WP3 — address and POI

- Address ranges: R is per road link with side/parity flags; OSM has points. Snap/interpolate method unvalidated.
- Suburb/parent-place hierarchy (SRHA, three ARCD tiers) has no direct OSM equivalent.
- POI category codes include vendor codes absent from the spec (e.g. 0xCF80, ≈38% of the QLD sample); category-name table undecoded.
- POISR decoder has known bugs; whole-file assembly unfinished.

### WP4 — remaining index families

- Record bodies undecoded: POIDT (incl. the 39 MB POIDT013), ITSSR, FWYSR, AGMSR/ARGSR/EMGSR (and the unexplained `DB0/JG0/LR0/MB0/MZ0/ND0/NF0/NS0/VL0` suffix set), ARSNC/ARSSR/EM2SR/EM3SR, ZONE\*/ZSEL\*, FMCDT001, HWMAP (blob).
- NT and TAS have no FWYSR in R; emergency and zone data have no practical OSM source.

### WP5

- Low risk; disc stamp and coverage bounds must be recomputed for G.
