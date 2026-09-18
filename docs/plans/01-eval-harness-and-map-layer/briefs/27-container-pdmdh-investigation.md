# Brief: 27 — Container check PDMDH blob-length FAIL persists after dune->bay fix (ad hoc)

Consumer: implementation worker. Authored by the orchestrator (not `refine`), same pattern as
ad-hoc briefs 17 and 19. Triggered by unit 25b: after the brief 19/24 `natural=dune` ->
`natural=bay` fix and a fresh full-Australia rebuild, the `container` check still FAILs with a
byte-identical symptom (R=21,088 / G=18,624, 2,464-byte gap), contradicting brief 19's
prediction.

Owned paths: `parser/harness/checks/container.py`, `parser/tests/test_harness_container.py`,
this brief, `IMPLEMENTATION.md`. Do not touch `selection.json`, `selection.py`,
`osm_to_parcel_geometry.py` or `divide.py` (envelope work is designed elsewhere). Do not delete
or rebuild `output/`; read the live `output/ALLDATA.KWI` only. Commit and push.
Depends on: 25b. Runs alongside: envelope-recalibration design (disjoint paths).

## Required reading
1. `PLAN.md` "Build record (2026-09-16)" and `IMPLEMENTATION.md` unit 25b entry.
2. `parser/harness/checks/container.py` (`_pdmdh_common`) and `parser/refdata/harness.json`
   `container_allowlist` (already allowlists `record_size`, `bsmr_bmt_offset`,
   `bsmr_bmt_size`, `bmt_dsa`, `bmt_size`).
3. `parser/kiwiw/alldata_writer.py` `has_bmt` (content-driven BMT emission; do not edit).

## Goal
Root-cause the PDMDH gap using `compare_disc.py --checks container` plus a per-blockset walk
of R's and G's PDMDH; fix WP1-scope causes with tests; declare anything else.

## Done evidence
- `.venv-rp/bin/python -m pytest parser/tests -q` all pass.
- `compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI
  --checks container` -> PASS on the existing output (no rebuild).
- Any out-of-scope cause recorded as a declared deviation in `IMPLEMENTATION.md`.
