# Plan 30 — exact per-row account of the conflict-open rows

## Status after unit 2-03 (r4, 2026-10-06 11:59 AEST): 341 / 0 / **1**

Design ruling (a) was executed with the date-matched snapshot `39a836dd…`
(`reports/2-03-date-matched-relation-snapshot.md`).

- **Rows 396, 397, 775 → supply-path.** Source: r2647638 Australia (EEZ),
  131 cache ways + 16 snapshot ways, boundary-clipped, demanded code 288.
- **Row 246 stays conflict-open** (`outlier/stratum evidence insufficient`).
  - The PBF leg is gap-free.
  - 284 code-321 candidates reach the windows (natural=wood 274, scrub 10).
    All give 0 in-cell records under original, clipped and unit-mult.
  - The spool's retained 321 demander touches the cell edge (vertex 18,
    −31.5416545, 116.0931811; `encoder_drops_clipped_source_sliver`). A
    demanded-type feature therefore reaches the cell, and Amendment 1 §4
    cannot prove absence.
  - Unresolved: whether an honest repair (sliver retention or a semantic
    mapping) would supply the record. Owner: Design.

The account below is the **historical 2-02 state** (f1a1368, 4 rows) that
motivated the ruling. Its gap lists are superseded for rows 396/397/775 and
for row 246's source gaps.

Generated from `disposition.tsv` (published at f1a1368; 338 supply-path / 0 unfixable-proven / 4 conflict-open). For Design: each row is open because it has no positive in-cell supply witness and the listed relation gaps in the pinned PBF (`2026-08-24T20:20:50Z`) block a proof either way. Relation ids are `r<id>`; way counts are member ways absent from the pinned extract.

Gaps common to all four rows: 39; union: 47.

## dump_row 246 — L0 (834, 886), demanded code 321, stratum 321-outlier

- Lattice identity: none (type-321 outlier; independent evidence required)
- Cause class: supply discriminator incomplete
- Row-specific gaps (not common to all four): r2316598, r7493850, r8043873, r8653540
- missing relation member way (29): r307866 (37 ways), r311776 (22 ways), r2177258 (19 ways), r2186658 (16 ways), r2202162 (1746 ways), r2647601 (924 ways), r2647638 (16 ways), r3411897 (8 ways), r3778630 (42 ways), r6063092 (1 ways), r6063105 (2 ways), r8425531 (4 ways), r8444293 (1 ways), r8444294 (3 ways), r8444307 (4 ways), r8448061 (1 ways), r8601871 (1 ways), r8602049 (2 ways), r8602089 (3 ways), r8602092 (3 ways), r8602094 (3 ways), r9299402 (8 ways), r10342563 (5 ways), r11741662 (18 ways), r19269186 (459 ways), r19269193 (531 ways), r19285282 (29 ways), r19285354 (73 ways), r20827987 (7 ways)
- native-C vertex limit (5): r80500, r2316598, r7493850, r8043873, r8653540
- nested area relation member (3): r12026353, r18183905, r18194886
- relation has no outer ring (1): r19342817
- relation-not-retained-member-limit (5): r4095122, r15480206, r16308779, r16308787, r16308826

## dump_row 396 — L0 (2049, 1224), demanded code 288, stratum 288-template

- Lattice identity: T1 (Phase-1 sequence plus aligned 4x4 L0 grid)
- Cause class: supply discriminator incomplete
- Row-specific gaps (not common to all four): r10156269, r15832632, r16623818, r3225677, r8653540
- crossing/touching relation boundaries (1): r16623818
- missing relation member way (29): r307866 (37 ways), r311776 (22 ways), r2177258 (19 ways), r2186658 (16 ways), r2202162 (1746 ways), r2647601 (924 ways), r2647638 (16 ways), r3411897 (8 ways), r3778630 (42 ways), r6063092 (1 ways), r6063105 (2 ways), r8425531 (4 ways), r8444293 (1 ways), r8444294 (3 ways), r8444307 (4 ways), r8448061 (1 ways), r8601871 (1 ways), r8602049 (2 ways), r8602089 (3 ways), r8602092 (3 ways), r8602094 (3 ways), r9299402 (8 ways), r10342563 (5 ways), r11741662 (18 ways), r19269186 (459 ways), r19269193 (531 ways), r19285282 (29 ways), r19285354 (73 ways), r20827987 (7 ways)
- native-C vertex limit (5): r80500, r3225677, r8653540, r10156269, r15832632
- nested area relation member (3): r12026353, r18183905, r18194886
- relation has no outer ring (1): r19342817
- relation-not-retained-member-limit (5): r4095122, r15480206, r16308779, r16308787, r16308826

## dump_row 397 — L0 (2050, 1224), demanded code 288, stratum 288-template

- Lattice identity: T1 (Phase-1 sequence plus aligned 4x4 L0 grid)
- Cause class: supply discriminator incomplete
- Row-specific gaps (not common to all four): r15832632, r3225677, r8653540
- missing relation member way (29): r307866 (37 ways), r311776 (22 ways), r2177258 (19 ways), r2186658 (16 ways), r2202162 (1746 ways), r2647601 (924 ways), r2647638 (16 ways), r3411897 (8 ways), r3778630 (42 ways), r6063092 (1 ways), r6063105 (2 ways), r8425531 (4 ways), r8444293 (1 ways), r8444294 (3 ways), r8444307 (4 ways), r8448061 (1 ways), r8601871 (1 ways), r8602049 (2 ways), r8602089 (3 ways), r8602092 (3 ways), r8602094 (3 ways), r9299402 (8 ways), r10342563 (5 ways), r11741662 (18 ways), r19269186 (459 ways), r19269193 (531 ways), r19285282 (29 ways), r19285354 (73 ways), r20827987 (7 ways)
- native-C vertex limit (4): r80500, r3225677, r8653540, r15832632
- nested area relation member (3): r12026353, r18183905, r18194886
- relation has no outer ring (1): r19342817
- relation-not-retained-member-limit (5): r4095122, r15480206, r16308779, r16308787, r16308826

## dump_row 775 — L0 (1363, 1958), demanded code 288, stratum 288-template

- Lattice identity: T2 (Phase-1 sequence plus aligned 4x4 L0 grid)
- Cause class: supply discriminator incomplete
- Row-specific gaps (not common to all four): none
- missing relation member way (29): r307866 (37 ways), r311776 (22 ways), r2177258 (19 ways), r2186658 (16 ways), r2202162 (1746 ways), r2647601 (924 ways), r2647638 (16 ways), r3411897 (8 ways), r3778630 (42 ways), r6063092 (1 ways), r6063105 (2 ways), r8425531 (4 ways), r8444293 (1 ways), r8444294 (3 ways), r8444307 (4 ways), r8448061 (1 ways), r8601871 (1 ways), r8602049 (2 ways), r8602089 (3 ways), r8602092 (3 ways), r8602094 (3 ways), r9299402 (8 ways), r10342563 (5 ways), r11741662 (18 ways), r19269186 (459 ways), r19269193 (531 ways), r19285282 (29 ways), r19285354 (73 ways), r20827987 (7 ways)
- native-C vertex limit (1): r80500
- nested area relation member (3): r12026353, r18183905, r18194886
- relation has no outer ring (1): r19342817
- relation-not-retained-member-limit (5): r4095122, r15480206, r16308779, r16308787, r16308826

## What Design must rule

- (a) admit a pinned complete-relation snapshot of the 61 ids in `relation_requests.json` at the PBF timestamp as a second source pin and re-run `pbf-cache`; or
- (b) rule these rows `unfixable-proven` because their supply evidence lies outside the pinned source (not authorised by the current DESIGN).

Execute fetched no external data. Plan 30 stays open.

## Root cause of the class-1 gaps: extract clipping (proven 2026-10-06)

The 29 class-1 relations (missing relation member ways) have **3,619
distinct member ways** (3,988 relation–way pairs) that are absent from the
pinned PBF `australia-260824.osm.pbf`. Its sha256 is `433a1da2…`, and its
header gives `osmosis_replication_timestamp` 2026-08-24T20:20:50Z
(re-read from the PBF header with pyosmium).

- **Existed upstream at the timestamp.** One Overpass attic query,
  `[date:"2026-08-24T20:20:50Z"] way(id:…); out meta geom;` sent to
  `https://overpass-api.de/api/interpreter` (query text:
  `attic/q1_missing_ways.overpassql`), returned **all 3,619 ways**. The newest
  version timestamp is 2026-08-24T04:53:50Z, before the PBF timestamp, and no
  way is missing from the response.
- **Clipped by the extract.**
  - 3,386 of the ways lie wholly outside the PBF header bbox
    (68.133419, −57.092814, 169.001567, −8.809565).
  - The other 233 touch the bbox, but none of their nodes is inside the
    Geofabrik `australia.poly` extract polygon (1 ring, 22 vertices; same
    bbox as the header).
  - An osmium `complete_ways` extract keeps every way with a node inside the
    polygon, so these ways were dropped by the extract boundary.
- **Conclusion:** the class-1 gap is extract clipping, not missing upstream
  data. The relations are complete in OSM at the pinned timestamp.

Evidence: `missing_way_attic_proof.json`, with per-relation counts, query
and response sha256 (the 17 MB response stays at
`output/scratch-30/attic/q1_missing_ways.json`, sha `ffdc7732…`) and the
polygon sha. `attic/missing_ways.json` holds the requested id list. The
polygon is Geofabrik's current file, fetched 2026-10-06; its bbox matches the
PBF header.
