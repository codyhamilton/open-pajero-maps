---
design_id: 214
---

# C library load errors

## Intent

User request, verbatim (relevant portion):

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history. Draw up designs only for remaining work that is actually in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp.

## Problem

Plan 03's Phase 3C closed at `0cf5d99` with carried item 4: a stale
`cbuild.py` description of a Python fallback and `cenc._load_lib` leaking
`AttributeError` when a loaded library lacks an assembly symbol. The current
tree still has both. A library open failure instead returns `None`, hiding its
cause until assembly raises a generic error. The architecture already requires
C and says build failure raises `BuildError`.

This is that existing carried item, not a new K1 or content unit. Plan 04's
Architectural Implications explicitly leave plan 03 carried items 3–7 outside
its scope; this item has no dependency on its blocked Phase 3.

## Solution Shape

The assembly binding returns a completely configured library or raises a
`cbuild.BuildError` preserving the original load or symbol exception. Successful
loads keep their cache. Failed loads do not cache a partial library or prevent
a later repaired library from loading. The stale fallback description is
replaced with the existing mandatory-C contract.

### Domain: assembly library binding

- Owns: `cenc._load_lib`, reached through `cenc.lib`, and its assembly symbol configuration.
- Contract: a compiler failure propagates its existing `BuildError`; an `OSError` opening the shared library or an `AttributeError` resolving `kw_col_name`, `kw_copy_frames`, or `kw_write_rows` raises `BuildError` with the library path and original exception chained. A failure leaves the binding uninitialized. Repeated successful loads reuse the same fully configured object. No valid library API, C computation, or output bytes change.
- Non-goals: consolidate E1/E2/D1/K1 loaders, inspect every ABI symbol, change compilation or hashes, alter C code, or introduce a fallback.

## Architectural Implications

The stable mandatory-C rule in `docs/ARCHITECTURE.md` and `docs/OVERVIEW.md`
stands. `docs/design/target-disc.md` and the vocabulary mapping are unaffected.
Stable status reconciliation is separately authorized bookkeeping outside
this phase's functional outcome. It uses the existing landed records:
07's padding finding, 08/09's classify fixes, and 04's blocked 3-90. This does
not close plan 04 or unfreeze plan 03's content phases.

## Decisions

One phase implements plan 03 carried item 4 only. No heavy check, disc access,
3-90 replay, or full-Australia build is needed for a binding error-path change.
Focused fault injection and the existing tiny assembly wiring tests establish
the changed behavior and successful path. Refine is skipped: one worker.

The user's instruction to design and continue authorizes this bounded change
and direct fast-forward landing. Commit on `chm/maps-status-continue` and push
`HEAD:master`; never force-push or open a PR.

## Assumption Ledger

### Assumption 1

- Question: should open failures remain `None`, while only missing symbols become `BuildError`?
- Answer chosen: both load failures raise `BuildError`; preserve the original exception and permit retry.
- Rationale: there is no optional-C mode. Both mean the mandatory assembly library is unusable. `alldata_writer` already aborts on `None`.
- If wrong: narrow normalization to missing symbols before landing; do not add a fallback or change any C algorithm.

## Open Questions

None that block this phase. Plan 04's oracle, native joins, exhaustive pins,
historic completeness, PSS and review-chain blockers are outside this change.

## Phases

### Phase 1 — Resolve plan 03 carried item 4

- Outcome: `cenc.lib()` with a missing library or any missing assembly symbol raises `BuildError` with the original exception chained and the path identified; compiler `BuildError` propagates; a repaired library can load after failure; a valid library loads once, configures the same signatures, and the existing column-table and tiny indexed assembly/wiring tests pass. `cbuild.py` no longer describes a Python fallback.
- Surfaces: `parser/kiwiw/cenc.py` (loader and `lib()` contract docstring), `parser/kiwiw/cbuild.py` (fallback and `BuildError` docstrings), focused loader regressions in `parser/tests/test_cenc.py`, and a resolution appended to plan 03's implementation record.
- Approach: known
- Depends on: nothing; the Phase 3C build is already landed.

## Provenance Notes

Ground read the committed plans and history at `5c5823e4c267dd64bc986038caddb3ed4b745f60`
after fetching current `origin/master`. This carried item is explicitly in
`docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md`, not inferred
from a generic improvement or invented unit. Historical test flakes and
optional memory measurements are not silently turned into new signed work.
