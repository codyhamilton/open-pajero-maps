# Road-density basis wording

## Intent

User request, verbatim:

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history, including what is already on master through f5a2162. Draw up designs only for remaining work that is actually still open in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp. One worker only. Stop when the remaining in-repo work you can finish is committed and pushed to master, or when you are genuinely blocked, and leave the result SHAs in the log.

## Problem

Plan 03 Phase 2 final Carried item 3 explicitly leaves the density report's
`LENGTH_BASIS` wording open. The 2-05 implementation at `2f874e3` switched
the measurement to frame bounds; the label still says leaf bounds at
`f5a2162`. This cosmetic item is explicitly left with its owner by plan 03's
Carried placement; it is separate from the frozen content phases.

## Solution Shape

The census labels its existing frame-based measurement correctly. Its
calculation and historical results retain their meaning.

### Domain: Road-density report

- Owns: `parser/tools/road_density_census.py` report metadata.
- Contract: `Census.to_dict()['length_basis']` describes frame extent divided
  by the matching coordinate maximum. Numeric fields and coordinate rules
  retain their existing calculation. Stored historical profiles are evidence
  and are not regenerated for a label correction.
- Non-goals: census kernel migration, density selection, disc measurements.

## Architectural Implications

Overview, Architecture and all four `docs/design/` documents were read.
This corrects metadata within the current analysis surface; it changes no
boundary. Plan 04 Phase 3 remains blocked and releases no dependent phase.

## Decisions

One bounded phase, one worker, refine skipped. The user's instruction to
continue authorizes implementation after this design is committed. The same
seat performs a disclosed self-review; no independent review is claimed.

## Assumption Ledger

None: the item, corrected basis and cosmetic scope are already recorded.

## Open Questions

None within this item.

## Phases

### Phase 1 — Accurate density metadata

- Outcome: `Census.to_dict()` emits frame-bounds basis wording; the existing
  density tests retain their numeric results. Plan 03 records item 3 resolved.
- Surfaces: census `LENGTH_BASIS`, plan 03 `IMPLEMENTATION.md` resolution note.
- Approach: known
- Depends on: nothing; the calculation fix already landed in `2f874e3`.

## Adversarial pass

One-worker self-review: editing a historical profile would imply a fresh
measurement; exclude that. The frozen content phases do not own this cosmetic
item, as plan 03's existing Carried placement explicitly confirms.

## Provenance Notes

No full-disc check, blocked verification or memory benchmark is rerun.
