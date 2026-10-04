# Fixture way bounds precheck

## Intent

User request, verbatim:

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history, including what is already on master through f5a2162. Draw up designs only for remaining work that is actually still open in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp. One worker only. Stop when the remaining in-repo work you can finish is committed and pushed to master, or when you are genuinely blocked, and leave the result SHAs in the log.

## Problem

Plan 01 Follow-ups records a cheap way-level bbox precheck for fixture runs
on the full PBF. `_GeomHandler._handle_way` still splits every admitted road
across the full grid before discarding cells outside the fixture. The separate
spool-total follow-up already landed at `6a6c986`; it is not work here.

## Solution Shape

Fixture extraction rejects a way for a level only when its coordinate bounds
cannot produce output in that level's admitted cells. This is a conservative
early rejection before expensive splitting, not a replacement geometry or
selection algorithm. Full-grid extraction retains its path.

### Domain: Extraction admission

- Owns: `_GeomHandler` in `parser/osm_to_parcel_geometry.py`.
- Contract: the precheck uses the extent of whole admitted target cells,
  not just the requested geographic bbox. It keeps intersecting/crossing ways,
  ways on cell boundaries, and names/backgrounds whose centroid is admitted.
  It preserves existing longitude wrapping and edge-cell clamping, including
  ambiguous antimeridian cases by retaining them conservatively. Bounds are
  computed once per way and admission is evaluated per level. The existing
  split, chain ordinals, selection, cap order and emitted records are unchanged.
- Non-goals: changing tile assignment or clipping, extraction port to C,
  content changes, fixture-only deliverables or a full-country benchmark.

### Domain: Evidence

- Owns: existing extraction tests and plan 01 follow-up resolution.
- Contract: disjoint fixture roads avoid the splitting entry point; paired
  extraction with precheck enabled and bypassed yields identical spool bytes
  on synthetic PBFs with road, place and background names. Tests cover crossing,
  boundary, whole-cell margin, multi-level and longitude edge cases. Existing
  full-grid extraction tests pass. Performance claims are limited to avoiding
  the unnecessary call; no country-scale timing improvement is asserted.

## Architectural Implications

Overview, Architecture and all `docs/design/` documents were read. Extraction
remains Python as plan 04 Decision 9 states. This plan 01 follow-up does not
build frozen plan 03 content or release plan 04's dependent phases.

## Decisions

One phase and one worker; skip refine. Commit the design and brief before
implementation under the user's instruction to continue. Disclose self-review
instead of invoking another worker. Preserve all existing protected inputs.

## Assumption Ledger

- Question: does fixture rejection use exact fixture bounds?
  Answer: use full target cells, matching existing admission. Exact bounds
  would drop legitimate output in a cell's margin and change spool identity.
- Question: may the precheck fix unusual longitude assignment?
  Answer: preserve it. Edge columns may accept clamped out-of-coverage points;
  retain those cases rather than change existing output. A format/geography
  correction would need its own design and evidence.

## Open Questions

None within this follow-up.

## Phases

### Phase 1 — Disjoint ways avoid fixture splitting

- Outcome: fixture extraction skips splitting provably disjoint ways per
  level and produces the same spool bytes as bypassing the precheck on the
  equivalence set; full-grid tests pass. Plan 01 records this follow-up resolved.
- Surfaces: extraction handler, `parser/tests/test_extractor_scale.py`, plan 01
  follow-up resolution, Architecture extraction contract.
- Approach: known
- Depends on: nothing; extraction is outside the blocked Phase 3 checker work.

## Adversarial pass

One-worker self-review identified three false-rejection risks: boundary cells
extend beyond a fixture bbox; endpoints outside a fixture can cross it; and
longitude clamping/wrapping can admit unexpected points. The contract preserves
all three and tests compare output with the existing path. Numeric boundary
guards must be conservative. No full-PBF performance claim is required.
