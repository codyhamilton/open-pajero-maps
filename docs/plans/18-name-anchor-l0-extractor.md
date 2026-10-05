# Extractor fix for carried name_anchor L0 (0,541) / leaf 928

`assign_to_parcel` (extractor + mesh twin) returns `None` for out-of-span
longitude the same way it already did for out-of-range latitude, so O03-class
names are never clamped into edge cell `(0,541)`. Unit tests and a synthetic
PBF→spool fixture prove the contract. On-disc O03 / K1 `name_anchor` pin
remains until a future extract+encode. Plan 04 Phase 3 was not closed.

## Intent

From the signed design, verbatim:

> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Fix the extractor so an out-of-span longitude is not clamped into an edge cell (O03: L0 cell (0,541), leaf 928; spool lon 77.519 vs encoded 90.0). Prove with synthetic PBF / fixture spool. Land on master. No feature branch. No pull request. No G re-encode. No full-AU rebuild. Completeness (Quality ticket 3) stays open and is not redesigned here.

## Why This Existed

K1 still reported one `name_anchor` failure on the discs in force: L0 `(0,541)`,
leaf `[928]`, disc lon `90.0`. Plan 04 Phase 3 carried it as spool/extractor
defect **O03**. Spool stored the source name at lon **77.519…** (Île Saint-Paul);
extractor `assign_to_parcel` rejected out-of-range lat with `None` but clamped
a negative wrapped lon delta into `[0, nx−1]`, yielding cell `(0,541)`. Encoder
`to_xy` then faithfully clamped into the cell rectangle. Counterfactual: remove
only that out-of-span name → name_anchor **1→0**. Plan 03 unit 3-10 had named
the extractor half of this fix but was held; `test_parcel_geometry.py` still
documented lon-out edge clamp.

## What Was Built

**Changed:** `parser/osm_to_parcel_geometry.py`, `parser/kiwiw/mesh.py`,
`parser/tests/test_parcel_geometry.py`, `parser/tests/test_descriptor.py`,
`parser/tests/test_extractor_scale.py`, new
`parser/tests/test_name_anchor_o03_extractor.py`, triage
`rules_other.json` O03 note + `cause_table.md` pointer.
Design: `00cabd8`. Phase close: `16e2931`.

After `_lon_delta`, if `dlon < 0 or dlon >= disc_lon_span` return `None`;
no clamp-into-edge. In-span and antimeridian-inside points still assign.
Mesh twin matches (descriptor equality including O03 / just-outside-span
points). Synthetic PBF: O03 place node + in-span control → zero O03 name in
any L0 cell / no `(0,541)` admission; control present once in its cell.
Gates: **67 passed** across the four test modules above.

No encoder / `_cenc.c` / `dv_assign` change, no G re-encode / full-AU, no
assembly drop guard, no plan 14 Phases 2–3, no plan 04 Phase 3 close, no
reseat of 170 / 3-16 / 3-17.

## Deviations

Refine skipped (approach known — plan 03 brief 3-10 extractor half). Flash
implemented code + tests (67 passed) then exited before commit/EXIT_DONE;
executor finished triage docs, report, commit with
`Workflow-Phase: 18-name-anchor-l0-extractor:1`, push, and this close-out.
Tip rebased past concurrent plan 17 close-out and later design commits before
the phase commit. Assigned instance: OpenCode DeepSeek Flash.

Assumption 4 disclosure: `WAY_CROSS_180` arithmetic centroid lon `0.0` is
outside AU span; its road **name** is no longer edge-clamped into `(0,iy)`.
Scale-test oracle updated (road names 3→2 when roads expected). Road geometry
for that way still splits on in-span points.

## Review

No independent `REVIEW.md`. Phase outcome is in the phase-1 report (collapsed
here) and IMPLEMENTATION ledger: contract, unit + synthetic PBF proof, and
triage pointer met the signed outcome.

## QA

Focused gates: **67 passed**
(`test_parcel_geometry` + `test_descriptor` + `test_extractor_scale` +
`test_name_anchor_o03_extractor`). Contract smoke: O03 / west-of-lo → `None`;
in-span control assigns. `git diff --check` clean on the phase commit. No
disc, encode, or live K1 gate.

## Residual Risks

On-disc O03 / K1 `name_anchor` failing remains **1** until a future
extract+encode clears the historical pin — explicitly out of acceptance for
this plan. Callers that previously depended on lon edge-clamp (e.g. name
admission via an out-of-span centroid) now skip; enumerate further cases if a
fixture shows overlap-assignment need (plan 03 3-09 territory) — do not
silently restore lon clamp.

## Follow-ups

Optional evidence-only window/full re-extract+encode when Cody orders it to
clear live K1 name_anchor 1→0. Assembly drop guard on stale spools is a
separate follow-up if wanted for defense-in-depth. Completeness remains plan
14. Plan 04 Phase 3 stays open.
