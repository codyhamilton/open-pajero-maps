# Brief: 3-01 — cbuild content hash covers headers

Consumer: every later Phase 3 C unit (3-02, 3-03, 3-04 and the fix units edit `_k1.h`/`_d1.h`; a stale `.so` after a header-only edit gives false test results).
Owned paths: `parser/kiwiw/cbuild.py`, new `parser/tests/test_cbuild_headers.py`. Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: nothing (Phase 2 closed at `a576413`).
Runs alongside: 3-06 only.
Tier: Flash. Review: Sonnet 5.5. Not RE-risky.
Budget: 3 files to read, about 40 lines of `cbuild.py` and 80 lines of test, 25 tool turns. Past the budget, stop and report `over budget`.

## Required reading, in order

1. `parser/kiwiw/cbuild.py` — whole file (150 lines): `_content_hash`, `is_stale`, `_compile`, `build_ext`, `build_test_bin`.
2. `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` — the "2-03" concerns paragraph (the header-staleness hazard).
3. `parser/kiwiw/ctest/` listing (`ls`) to see what `build_test_bin` hashes.

## Goal

An edit to any `parser/kiwiw/*.h` makes `build_ext()` and `build_test_bin()` rebuild, so Phase 3's header edits (`_k1.h`, `_d1.h`) can never run against a stale product.

## Contract

Cited from the module docstring: "a sha256 over every source's bytes plus the flag list, stored beside the product as `<product>.hash`. Content hash, not mtime". The hash file format stays one hex digest; the build stays atomic.

## Changes

- Add a module constant `EXT_HEADERS` = `tuple(sorted(_HERE.glob("*.h")))` evaluated at call time (a function `_ext_headers()`; a new header must be picked up without editing a list). Include these files in the hashed set of `build_ext` and `build_test_bin` (`hashed = compiled + ext_sources + headers`). They are NOT passed to gcc as inputs (`-shared` command line unchanged).
- Keep the `build_ext` and `build_test_bin` signatures backward compatible: add one keyword `headers: tuple[Path, ...] | None = None` (None means `_ext_headers()`); tests pass an explicit tuple.
- Do not change `CFLAGS`, `EXT_SOURCES`, or compile arguments. The built `.so` bytes may change only through the normal rebuild this edit triggers once; the full-AU build sha must not change (gcc output depends on the sources, not on the hash file).

### Keep untouched

`_content_hash` ordering (`sorted(..., key=str)`), atomic replace, hash written after rename, `BuildError`.

## Done evidence

Write the test first; run it against the unmodified `cbuild.py` and report the failure.

- `parser/tests/test_cbuild_headers.py` builds in `tmp_path`: `a.c` that `#include "b.h"` and returns a macro from it; `build_ext(sources=(a.c,), out=tmp/x.so, headers=(b.h,))`; asserts a second call does not rebuild (hash file mtime unchanged); edits `b.h` (changes the macro); asserts `is_stale` is true via the public path (the next `build_ext` call rebuilds and loading the `.so` through `ctypes` returns the new value). Same for `build_test_bin` with a `ctest` dir in `tmp_path`.
- Real-tree check, in the test: append a trailing comment line to a copy is NOT allowed (do not edit the real header). Instead assert `_ext_headers()` contains `_k1.h` and `_d1.h`.
- `.venv-rp/bin/python -m pytest parser/tests/test_cbuild_headers.py parser/tests/test_perf_inventory.py parser/tests/test_goldens.py parser/tests/test_k1_points.py -q --basetemp=output/scratch-3-01/pytest` → all pass; before the change the new test fails.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
