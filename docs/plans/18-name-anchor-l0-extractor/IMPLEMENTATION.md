# Implementation — 18 name_anchor L0 extractor

- Tool: OpenCode DeepSeek Flash (assigned instance)
- Session: design landed; Phase 1 executed
- Started: 2026-10-06 ~00:12 Australia/Brisbane
- Closed: 2026-10-06 ~00:25 Australia/Brisbane (executor finish after Flash gates)

## Phase 1

Done. `assign_to_parcel` (extractor + mesh) returns `None` for wrapped lon
outside `[0, disc_lon_span)`. Unit tests cover west-of-lo, O03 coords → not
`(0,541)`, and mesh≡extractor. Synthetic PBF fixture proves O03-class name
absent from L0 spool / cell `(0,541)` with in-span control present.

Gates: `test_parcel_geometry.py` + `test_descriptor.py` +
`test_extractor_scale.py` + `test_name_anchor_o03_extractor.py` — **67 passed**.

No G re-encode / full-AU. Plan 14 Phases 2–3 untouched. Plan 04 Phase 3 not
closed. 170 / 3-16 / 3-17 not reseated. On-disc O03 pin remains until future
extract+encode. `rules_other.json` O03 note + `cause_table.md` pointer updated.

Deviation (expected, Assumption 4): `WAY_CROSS_180` arithmetic centroid lon
`0.0` is out of AU span; its road name is no longer edge-clamped into `(0,iy)`
— scale-test oracle updated 3→2 road names when roads expected.
