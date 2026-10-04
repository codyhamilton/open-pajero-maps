---
brief_id: 216
design_id: 214
---

# Brief: plan 03 Phase 3C carried item 4 — library load errors

Consumer: Codex implementing the existing carried item.
Owned paths: `parser/kiwiw/cenc.py`, `parser/kiwiw/cbuild.py`,
`parser/tests/test_cenc.py`, and an appended resolution in
`docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md`.
Commits: commit on `chm/maps-status-continue` after focused checks pass.
Depends on: nothing. Runs alongside: nothing.
Budget: 7 files to read, about 100 lines to change, 30 tool calls. Past the
budget, record a handoff in IMPLEMENTATION.md and report over budget.

## Required reading

1. `docs/plans/10-c-library-load-errors/DESIGN.md` — Domain: assembly library binding and Phase 1.
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — Phase 3C Carried item 4.
3. `docs/plans/04-c-core-orchestration/DESIGN.md` — Architectural Implications, carried items 3–7 excluded.
4. `parser/kiwiw/cenc.py` — `_load_lib` and `lib()`.
5. `parser/kiwiw/cbuild.py` — module and `BuildError` docstrings.
6. `parser/tests/test_cenc.py` — column-table test.
7. `parser/tests/test_build_wiring.py` — tiny successful build checks.

## Goal and contract

Resolve the actual carried loader error and stale fallback description.
Binding contract, quoted from DESIGN.md Domain: assembly library binding:

> A failure leaves the binding uninitialized. Repeated successful loads reuse the same fully configured object. No valid library API, C computation, or output bytes change.

`cenc.lib()` returns a fully configured cached library or raises `BuildError`.
Compiler `BuildError` propagates unchanged. Load `OSError` and missing-symbol
`AttributeError` become `BuildError` with path and exception chaining. A failed
load leaves no partially initialized cache and allows a repaired load to retry.
Success signatures and object caching stay unchanged.

## Changes

Normalize errors narrowly around library opening and assembly signature setup.
Publish the cache only after all three symbols configure successfully. Remove
the obsolete degrade-to-Python paragraph and clarify the load error contract
in `lib()` and `BuildError` docstrings.
Remove the column test's obsolete optional-C marker if it no longer applies.
Use isolated monkeypatched cache/CDLL/build state to exercise each failure
without corrupting or replacing an actual shared library.

### Keep untouched

C sources, all other loader families, build hashing, rules, check tolerances,
pins, disc/spool/scratch/symlink inputs and .venv-rp. No 3-90 or other blocked
verification rerun; no heavy full-disc test or new performance measurement.

## Done evidence

Write focused regressions first and report their failures before implementation.
Cover open failure, each of three missing assembly symbols, compiler failure,
retry after failure, and successful cache/signature setup.
- `.venv-rp/bin/python -m pytest parser/tests/test_cenc.py -q` → all pass without skips. Open and symbol failures must chain their original exception because that is the existing carried defect; compiler failure propagation, retry and cache checks prove normalization does not leave a poisoned cache.
- `.venv-rp/bin/python -m pytest parser/tests/test_build_wiring.py parser/tests/test_indexed_assembly.py -q` → all pass without skips. These existing tiny fixtures require working assembly symbols and verify successful output behavior after changing the loader.
- `git diff --check` → exit 0.
- Append the resolution to plan 03, retaining its original carried record and content freeze. No disc verification claim is made.

## Report back

What changed, before/after regression results, focused suite result, limitations
and deviations. Do not turn unrelated findings into more work units.
