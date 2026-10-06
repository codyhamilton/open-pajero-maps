# Phase 2 — role and limits of the date-matched relation snapshot

- **What it is.** `output/scratch-30/attic/relation_snapshot_260824.json`
  (sha256 `39a836dd…`, 78,833,302 B, ODbL) is an Overpass attic snapshot at
  `2026-08-24T20:20:50Z`, the pinned PBF's replication timestamp. It covers
  the 61 relations in `relation_requests.json`, their 56 direct child
  relations, 32,573 member ways and 71 member nodes. The pin, queries and
  checks are in `phase2_snapshot_pin.json`; provenance is in
  `docs/provenance.md`.
- **Role.** It is a second pinned source (DESIGN Amendment 1) for the plan 30
  PBF relation probe only.
  - It supplies member-way geometry that the Geofabrik extract clipped away.
    All 3,619 missing ways existed upstream at the timestamp
    (`missing_way_attic_proof.json`).
  - It supplies tags and members only for the 5 relations the legacy cache
    never retained.
  - The pinned cache wins wherever it has the data.
- **Limits.**
  - Nothing from it enters the build: no spool, encoder, vocabulary,
    selection or disc input. It provides no R coordinates.
  - Relations outside the 61 (plus their area-role children) are ignored.
  - A supply that depends on snapshot ways (rows 396, 397, 775 via r2647638
    EEZ, 16 snapshot ways) proves that the date-matched source has the
    demanded-code feature in the cell. Implementing it needs the complete
    relation as a build input. That is a Design/implement decision, not
    made here.
  - It cannot prove a row unfixable when demanded-type features reach the
    cell (row 246).
- **Effect.** The result moved from 338 / 0 / 4 to 341 / 0 / 1 with no
  regression (`reports/2-03-date-matched-relation-snapshot.md`).
