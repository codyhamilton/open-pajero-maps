# EO clipper face-walk decline: root cause, census, and eo_split_on_vertices fix

Plan 48 named why five seeded EO face-walk declines fired (H2 equal-atan2 ties and H1 rounding non-planarity), landed an output-neutral `eo_census` sidecar proving AU/Perth guard_hits=0, and fixed the clipper with `eo_split_on_vertices` (T-junction / vertex-on-edge split before `eo_connect`, legacy min-turn walk kept). All 20,000 stress rings and the five seeded declines pass. Perth stayed `04be2f6e…`. AU could not stay byte-identical: Design accepted confined successor `88bd7852…` (two L0 cells) after R-DVD showed no-worse coverage on both. R-G8-1-d-a is discharged. Soft residual: input-ring IDs into the split are not instrumented (not a land gate). Wall median-of-5 remains deferred (single-run within plan-41 noise).

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Cody's ask (2026-10-06, 19:34 AEST), for R-G8-1-d-a:
> - **P1:** root-cause why the `_cenc.c:885` guard fires on the 5 seeded rings. Add a tracked tool or test that proves "no AU/Perth input reaches the guard" from instrumentation, not just from builds completing.
> - **P2:** fix the clipper so all 20,000 pass, flipping ring 359 from expected failure to pass. … If a byte-identical fix is impossible, the changed disc becomes a recorded successor oracle with its diff confined and explained.

## Why This Existed
Plan 43 regenerated EO stress coverage but left R-G8-1-d-a open: seeded ring 359 (and four others in the 20k set) made `eo_clip` decline on an already-used half-edge. Production builds had never hit it, but the mechanism was unproven and the xfail remained.

## What Was Built
**Changed:**
- `parser/kiwiw/_cenc.c` — `EO_DIAG` hook; thread-local `eo_stats`; **`eo_split_on_vertices`** before `eo_connect`;
- `parser/tools/eo_walk_diag.py`, `eo_guard_census.py`; `cbuild` / `build_alldata` census sidecar;
- `parser/tests/test_bg_eo_stress.py` (`KNOWN_DECLINES=∅`, r359 pass), `test_eo_guard_census.py`, `test_eo_walk_diag.py`;
- Evidence under `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-14/conditions/eo_decline/` (dumps, census, `p3_fix/`);
- Successor oracle `88bd7852…` at `output/scratch-48/G_new`; `oracle_chain` AU hop; provenance / live-pin note.

### Phase 1 — decline root cause
EO_DIAG dumps + Fraction checks named H2 (r359, r8475, r19650) and H1 (r11892, r14503). All five declined at the used-half-edge site, not `np≥ne`.

### Phase 2 — no-incidence census
AU/Perth `-j4` builds with census: sha unchanged at `4e6b0de7` / `04be2f6e`, **guard_hits=0**, declines=0. Sidecar `eo_census.json` beside ALLDATA (disc-neutral).

### Phase 3 — robust walk + successor
`eo_split_on_vertices` (Design (ii)-class). Stress 1k+20k nfail=0; five seeded declines pass. Perth MATCH. AU → successor `88bd7852` (L0 `(1768,573)` rotation; `(1817,726)` 7-pt→two 4-pt at `(3039,154)`). R-DVD equal coverage on both cells. Design ACCEPT + Flash PASS-WITH-CONCERNS LAND (`632adb4`).

## Deviations
- AU byte-identity gate unmet; successor path taken with confined 2-cell diff + R-DVD (Design-allowed).
- Wall gate: single-run ~37.49 s (plan-41 median 37.38, noise 0.51); median-of-5 deferred.
- Exact OSM/spool input-ring IDs into `eo_split_on_vertices` not instrumented (soft residual; Design: not a land gate).
- Exact-angular and cyclic-order experiments rejected (parity fail without split; cyclic+split equivalent to split-only for gates).

## Review
- Phase 1 Flash: APPROVE / PASS-WITH-CONCERNS (mechanism witnesses).
- Phase 2 Flash: PASS-WITH-CONCERNS (sha+guard_hits; wall single-run note).
- Phase 3 Flash: **PASS-WITH-CONCERNS**, land **LAND** — checklist A–E met; F partial on median wall and pre-land suite tip (land commit restamped promotion).

## QA
Full `parser/tests` 1478 passed / 10 skipped at pre-land tip; `test_oracle_chain` + pin contract green after hop add. K1 not re-run on successor this close (Perth unchanged; AU confined 2 cells with R no-worse); carried as follow-up if Design requires restamp.

## Residual Risks
- Soft: input-ring ID instrumentation for split witnesses.
- Soft: wall median-of-5 not yet measured under flock after land.
- Soft: `eo_split_on_vertices` returns 0 after 16 rounds without a named non-convergence decline site (no production hit observed).

## Follow-ups
- Optional AU wall median-of-5 at `-j4` under flock when free.
- Optional EO_DIAG input-ring ID capture if Design later requires it.
- Plan 56+ memory-profile band before treating later residency designs as proven.
