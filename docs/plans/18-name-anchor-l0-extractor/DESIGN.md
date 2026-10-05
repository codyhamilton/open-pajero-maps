---
design_id:
---

# Extractor fix for carried name_anchor L0 (0,541) / leaf 928

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Fix the extractor so an out-of-span longitude is not clamped into an edge cell (O03: L0 cell (0,541), leaf 928; spool lon 77.519 vs encoded 90.0). Prove with synthetic PBF / fixture spool. Land on master. No feature branch. No pull request. No G re-encode. No full-AU rebuild. Completeness (Quality ticket 3) stays open and is not redesigned here.

## Problem

K1 still reports exactly one `name_anchor` failure on the discs in force: L0 cell `(0,541)`, leaf path `[928]`, disc raw `(0,370)`, disc lon `90.0`. Plan 04 Phase 3 carried it as spool/extractor defect **O03** (`docs/plans/04-c-core-orchestration/triage/rules_other.json`, `cause_table.md`, `review_3-08.md`). It is not an acceptance target for Phase 3 close; it is a pinned spool item until extraction stops producing it.

Committed forensics already pin the mechanism (no new science required):

- Spool stores the source name at lon **77.51903576666666** (Île Saint-Paul region) with unmodified longitude (`_make_name_record` / `_handle_node`).
- Extractor `assign_to_parcel` (`parser/osm_to_parcel_geometry.py`) rejects out-of-range **latitude** with `None`, but after `_lon_delta` can return a **negative** delta west of `disc_lon_lo` (AU coverage `lon_lo=90.0`, span `128.0` from `parser/refdata/grid.json`), it **clamps** `ix` into `[0, nx−1]`. For this point the pre-clamp raw ix is **−399**; clamp yields cell `(0,541)`.
- Encoder `_cenc.c:to_xy` then faithfully clamps the out-of-frame lon into the cell rectangle → disc lon **90.0**, leaf **928**. Review 3-08: encoder clamp is a documented mirror of `_clamp_coord`; **the extractor should have dropped the name**. Counterfactual on the original window: remove only that out-of-span name → name_anchor **1→0**; original G frame byte gate **1/1**.

Plan 03 unit **3-10** (`briefs/3-10-name-cell-clamp.md`) already named this fix (extractor `None` for out-of-span lon + assembly drop on the then-current spool) but was **held / re-scoped** for Phase 3C and never landed. Plan 04 froze plan 03's remaining Phase 3 units; O03 stayed carried. `test_parcel_geometry.py` still documents that out-of-lon returns an edge cell rather than `None`.

This is an **extractor contract fix**, already root-caused. It is not a checker tolerance change, not an encoder change, and not a completeness redesign. Verified on `origin/master` at `b40f012` from committed triage / extractor / encoder records — no live disc or completeness dump required for the design. Plans **01–05** and **07–16** occupy those numbers on master; **17** is the live-extend dump_join draft (handed to Execute); **06** is not a work unit. This plan is **18**.

## Solution shape

One bounded change: make disc-coverage `assign_to_parcel` treat out-of-span longitude the same as out-of-span latitude — return `None` — so names (and any other callers) never land in an edge cell by clamp. Keep antimeridian wrap for points that are genuinely inside the span. Prove with unit tests on the O03 coordinates against AU coverage, plus a synthetic PBF → spool fixture that shows the out-of-span place name is absent from L0 `(0,541)` (and not admitted elsewhere by the same clamp). Do **not** re-encode G, do **not** full-AU rebuild, do **not** require Cody disc remount. Existing on-disc O03 remains a historical pin until a future extract+encode (out of scope). Completeness Phases 2–3 of plan 14 continue separately.

### Domain: disc-coverage assign_to_parcel

- Owns: `assign_to_parcel` / `_lon_delta` contract on the extractor grid (`parser/osm_to_parcel_geometry.py`) and the matched mesh twin (`parser/kiwiw/mesh.py`) so `test_descriptor` equality stays true.
- Contract: for a point with latitude inside `[disc_lat_lo, disc_lat_lo + disc_lat_span)` and longitude whose wrapped delta is **not** in `[0, disc_lon_span)`, return `None`. Points with delta in that half-open interval still return `(ix, iy)` with `ix = int(dlon / cell_lon)` (no clamp-into-edge). Lat-out behaviour unchanged. Call sites that already skip `par is None` (including `_handle_node` name admission) therefore omit the O03-class name from the spool.
- Non-goals: no change to `_cenc.c:to_xy` / encoder clamp; no C `dv_assign` (parent-scoped division, not disc coverage); no assembly-time drop of names already on an existing spool; no road/background clip or selection redesign; no re-extract of the live AU spool as a phase gate.

### Domain: synthetic / fixture proof

- Owns: the acceptance proof that the fix stops O03-class admission without a full-AU build.
- Contract: (1) unit tests fail before / pass after for AU-like coverage: lon just west of `lon_lo` (including O03 lat/lon) → `None`; in-span corners and antimeridian-inside points still assign; mesh and extractor agree. (2) A synthetic PBF (osmium SimpleWriter pattern already used by `test_extractor_scale.py`) with a named place node at the O03 coordinates, extracted into a temp spool for L0 against AU `TileGrid.from_reference(0)` (or an equivalent coverage box with `lon_lo=90`), yields **no** name record in cell `(0,541)` and does not place that node in any cell via lon-clamp; a control in-span named node still appears in its assigned cell. Pytest is the gate.
- Non-goals: no full-AU encode; no K1 on the live disc as acceptance; no claim that existing G discs lose the O03 failure until a future extract+encode; no plan 14 completeness dumps; no 3-90 fresh-verify re-run.

## Decisions

1. Plan number is **18**. Standalone plan; it lands the **extractor half** of held plan 03 unit 3-10 as the O03 fix. It does not reopen plan 03 Phase 3, does not mega-close Phase 3 / 3-90, and does not absorb plan 14 completeness.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — plan 03 brief 3-10 extractor half + existing synthetic-PBF extractor tests).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Gates are unit + synthetic PBF/fixture spool only. No G re-encode; no full-AU rebuild; no Cody disc rebuild.
6. Keep `osm_to_parcel_geometry.assign_to_parcel` and `mesh.assign_to_parcel` behaviour-identical (descriptor tests). Leave encoder and C division untouched.
7. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: can this close without remounting a disc, re-encoding AU, or re-running plan 14 completeness dumps?
- Answer chosen: yes. Root cause and counterfactual are already committed under O03. Acceptance is synthetic/fixture only.
- Rationale: ticket forbids G re-encode / full-AU; Maps Quality Assessor ticket asks for synthetic PBF/fixture spool proof.
- If wrong: Cody orders an optional evidence-only re-extract+window encode later — still not this plan's acceptance gate.

### Assumption 2

- Question: fix only the Python extractor `assign_to_parcel`, or also the assembly drop guard from plan 03 3-10?
- Answer chosen: extractor (and mesh twin) only. Assembly drop existed to repair an already-built spool without re-extract; this ticket forbids G re-encode and asks for fixture-spool proof of extraction.
- Rationale: once assign returns `None`, new extracts never admit O03-class names; dropping from a stale spool without re-encode cannot clear on-disc O03 anyway.
- If wrong: Cody wants the assembly guard too for defense-in-depth on old spools — add as a follow-up plan, do not block this extractor contract.

### Assumption 3

- Question: must live K1 `name_anchor` failing go 1→0 in this plan?
- Answer chosen: no. That requires extract+encode of the AU disc. Record in docs that O03 remains the on-disc pin until that future rebuild; the extractor defect class is closed by fixture proof.
- Rationale: ticket explicitly bars full-AU / G re-encode as acceptance.
- If wrong: Cody expands scope to a bounded window rebuild under heavy lock — still separate from completeness plan 14 Phases 2–3.

### Assumption 4

- Question: does changing lon-out to `None` break callers that relied on edge clamp (roads/backgrounds via centroids)?
- Answer chosen: proceed; callers already treat `None` as skip. Report any fixture caller that depended on clamp in Execute notes. Antimeridian-inside points must keep working (covered by existing wrap tests + new cases).
- Rationale: plan 03 3-10 already required checking callers; lat-out already returns `None`; clamp-into-edge was the defect.
- If wrong: a shape whose centroid is outside span but geometry overlaps coverage would be dropped at that level — enumerate with a small fixture and decide with Cody whether overlap-assignment (plan 03 3-09 territory) is needed; do not silently restore lon clamp.

### Assumption 5

- Question: is plan 17 (live dump_join switch) a dependency?
- Answer chosen: no. Independent surface (extractor vs residual extend entry). May land in either order on master.
- Rationale: no shared code path with O03 admission.
- If wrong: none material — still no reseat of 17's dump_join work here.

## Open questions

1. After this lands, when should a full or windowed re-extract+encode clear on-disc O03 / K1 name_anchor 1→0? **Out of scope** — evidence-only when Cody orders it; not this plan's acceptance.
2. Should triage `rules_other.json` O03 note be edited to say "fixed in extractor plan 18; on-disc pin until re-encode", or left as historical cause text with a pointer only in this plan's IMPLEMENTATION? **Default:** update the live O03 note / cause_table pointer factually when those files are touched; do not delete the rule or claim live failing is already 0.

## Phases

### Phase 1 — Out-of-span lon returns None; synthetic O03 name not spooled

- Outcome: `assign_to_parcel` in `parser/osm_to_parcel_geometry.py` and `parser/kiwiw/mesh.py` returns `None` when wrapped lon delta is outside `[0, disc_lon_span)` (same posture as lat-out), and still assigns in-span and antimeridian-inside points. Unit tests cover: (a) lon just west of AU `lon_lo=90` → `None`; (b) O03 coordinates lat `−38.727284749`, lon `77.51903576666666` on L0 AU reference grid → `None` (today would be `(0,541)`); (c) mesh ≡ extractor on the descriptor point set plus the new cases; (d) existing parcel-geometry / extractor tests updated so they no longer expect lon-out edge clamp. A synthetic PBF fixture (named place node at O03 coords + an in-span control name) extracted to a temp spool shows **zero** name records in L0 cell `(0,541)` for the out-of-span node and a present control name in its in-span cell. Encoder / `_cenc.c` / C `dv_assign` unchanged. No G re-encode. No full-AU. Disc sha unchanged. Plan 14 Phases 2–3 not redesigned. Plan 04 Phase 3 not marked closed. 170 / 3-16 / 3-17 not reseated. Docs touched only as needed so O03 is recorded as extractor-fixed with on-disc pin until future extract+encode (`rules_other.json` note and/or `cause_table.md` / provenance pointer; this plan folder under `docs/plans/18-name-anchor-l0-extractor/` when Execute lands).
- Surfaces: `parser/osm_to_parcel_geometry.py` (`assign_to_parcel` / lon-out path); `parser/kiwiw/mesh.py` (matched `assign_to_parcel`); tests under `parser/tests/` (`test_parcel_geometry.py`, `test_descriptor.py`, new or extended synthetic-PBF extractor test beside `test_extractor_scale.py`); triage/docs pointers for O03 as above. Encoder, K1, classify rules predicates, dump_join, and plan 14 completeness science are **read-only**.
- Approach: known
- Depends on: master tip with O03 triage records and extractor tests (present at `b40f012`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `b40f012b1da99bee5a1e1ea2f12f864893fd04a3` (“Close plan 15 SADSR SRMX STFG vs R”).
- Candidate: Maps Quality Assessor ticket — extractor fix for carried name_anchor L0 (0,541) / leaf 928 (completeness lane KEEP prior ticket 3); out-of-span lon → encoder clamp; DVD-visible; spool lon 77.519 vs encoded 90.0; prove with synthetic PBF/fixture spool; no G re-encode / no full-AU rebuild.
- Evidence cited (committed): `docs/plans/04-c-core-orchestration/triage/rules_other.json` O03; `triage/cause_table.md` O03 block (spool lon 77.519…, encoder `to_xy` → lon 90.0 raw(0,370) leaf928, cf_name 1→0); `triage/review_3-08.md` item 7 (Île Saint-Paul, assign_to_parcel clamp, extractor should have dropped); `briefs/3-06-spool-forensics-dossier.md` D7; plan 04 DESIGN Phase 3 carry of name_anchor L0 (0,541) leaf 928; `parser/osm_to_parcel_geometry.py` `assign_to_parcel` / `_lon_delta` / `_handle_node`; `parser/kiwiw/mesh.py` matched assign; `parser/kiwiw/_cenc.c` `to_xy` clamp; `parser/refdata/grid.json` coverage `lon_lo=90.0` `lon_hi=-142.0`; `parser/tests/test_parcel_geometry.py` documented lon-out clamp behaviour; `docs/plans/03-map-layer-parity-remediation/briefs/3-10-name-cell-clamp.md` (held extractor half); `parser/tests/test_extractor_scale.py` synthetic PBF precedent.
- Rejected for this design: full-AU / G re-encode as acceptance; assembly-only drop without extractor fix; encoder clamp change; plan 14 completeness Phases 2–3 redesign; plan 16 reseat (already closed); plan 17 dump_join surfaces; 3-90 / Phase 3 mega-close; unsigned plan 04 phases 4–6 / plan 06; reseat of 170 / 3-16 / 3-17.
- Draft format followed: `/workspace/maps-design-drafts/17-live-extend-dump-join/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated. Prior Quality ticket 3 (completeness) remains kept / separate.
