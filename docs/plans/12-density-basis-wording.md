# Road-density basis wording

The stale density basis label was corrected to frame bounds. Plan 03 Phase 2
final Carried item 3 is resolved; the calculation already used frame bounds.

## Intent

User request, verbatim:

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history, including what is already on master through f5a2162. Draw up designs only for remaining work that is actually still open in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp. One worker only. Stop when the remaining in-repo work you can finish is committed and pushed to master, or when you are genuinely blocked, and leave the result SHAs in the log.

## Why This Existed

The metadata still said leaf extent after `2f874e3` moved the calculation to
frame bounds. Plan 03 explicitly carried the cosmetic discrepancy outside
the frozen content work.

## What Was Built

Changed `parser/tools/road_density_census.py`'s `LENGTH_BASIS` and appended
the resolution in plan 03. Design: `77e7592`. Implementation: `0e66f5d`.
The emitted report says frame bounds extent / coord_max. Numeric fields,
historical profiles, coordinate rules and public report keys are preserved.

## Deviations

One worker performed implementation and disclosed self-review, as requested.
Workflow feedback for design, brief and report returned `not delivered` with
no version queued. No external approval or execution identity is claimed.

## Review

Self-review confirms the changed label matches `parcel_metrics`'s frame
bounds and range, and no numerical code or historical profile changed.
This is not an independent review.

## QA

Existing density tests: 4 passed in 0.05 s. Direct report emission inspected;
`git diff --check` passed. No blocked/full-disc verification was repeated.

## Residual Risks

No fresh density measurement was performed or needed for this label change.

## Follow-ups

None within this correction. Plan 04 blockers and dependent phases stand.
