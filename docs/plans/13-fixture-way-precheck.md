# Fixture way bounds precheck

The recorded plan 01 fixture precheck was completed. Disjoint ways now avoid
full-grid splitting for a fixture level, with byte-identical synthetic spools
against the existing extraction path when the check is bypassed.

## Intent

User request, verbatim:

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history, including what is already on master through f5a2162. Draw up designs only for remaining work that is actually still open in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp. One worker only. Stop when the remaining in-repo work you can finish is committed and pushed to master, or when you are genuinely blocked, and leave the result SHAs in the log.

## Why This Existed

Plan 01's low follow-up called for a cheap way-bbox rejection during fixture
extraction. At `f5a2162`, every admitted road was still split over the full grid
before non-fixture cells were discarded. The separate spool-total follow-up
was already implemented by `6a6c986` and was reconciled in the plan 01 record.

## What Was Built

Changed `parser/osm_to_parcel_geometry.py`, `test_extractor_scale.py`,
Architecture and the plan 01 follow-up record. Design: `a0d75e6`.
Implementation: `8355950`.

The handler caches full admitted cell extents per level, computes bounds once
per way and conservatively rejects disjoint levels before splitting. It keeps
cell margins outside the requested bbox, crossing ways, numerical boundaries,
wrapped longitude intervals and existing edge-column clamping. Full-grid
levels bypass rejection; nodes, splitting, centroids, chain ordinals, filters
and name caps retain their existing behavior. The lasting admission contract
is in [Architecture](../ARCHITECTURE.md#pipeline).

## Deviations

One worker implemented and performed the disclosed self-review. Workflow
feedback for design, brief and report returned `not delivered`, with no version
queued. No external approval, independent review or run identity is claimed.
No PR was opened, under the user's direct-master instruction.

## Review

Self-review found the phase outcome met with no remaining in-scope finding.
Bounds include interpolation and centroids, and whole-cell extents preserve
the existing admission. Edge-column longitude rejection is disabled to preserve
clamping. The design's assumptions held and supplied sufficient contracts and
QA. This is not an independent review.

## QA

The disjoint-fixture unnecessary-split regression failed before the fix.
Final six-suite run: **84 passed in 28.41 s**, no skips (extraction, geometry,
selection, link identity, spool and name vocabulary). Three synthetic PBF
fixture runs with enabled/bypassed precheck produced identical index/data
bytes, including roads, place/background names and antimeridian cases.
Boundary, cell-margin, crossing, wrapped, empty-target and per-level cases
passed; existing full-grid extraction passed. `git diff --check` passed.

Verification used new `/dev/shm` fixture directories and the prior-seat Python
environment read-only with bytecode disabled. Existing scratch, symlink targets,
disc, spool and .venv-rp were preserved. No blocked verification was repeated.

## Residual Risks

Wide antimeridian bboxes and edge columns may retain unnecessary work. This is
deliberately conservative. No full-PBF timing, fresh real-disc build-byte result
or Phase 3 closure was measured or claimed.

## Follow-ups

None within this precheck. Plan 04 Phase 3 blockers and its dependent work stand.
