# Implementation

- Tool: Codex API, main agent /root
- Run: maps-status-continue, branch chm/maps-status-continue
- Start: 2026-10-05 Australia/Brisbane
- Baseline: 5c5823e4c267dd64bc986038caddb3ed4b745f60 (fetched origin/master)

## Phase 1 — Plan 03 carried item 4

The existing carried item is scoped by `briefs/carried-4-load-errors.md`.
Design 214 rated 0.864 against repository mean 0.872 (five prior designs);
the service flagged no outlying criterion. Execution id: 17, direct Codex
implementation of the small unit while no worker is running.

Independent design review found no blockers. Its two docstring/phase-scope
clarifications were applied. Initial brief 216 ratings flagged missing budget
dimensions, insufficient contract citation and weak verification rationale;
the brief was amended to state these explicitly before execution.
Final design rating 0.873 vs repo 0.872; amended brief 0.735 vs repo 0.632;
neither flagged any outlying criterion.

### carried-4-load-errors — done

Execution 17 changed only the assembly loader's failure reporting and its
docstrings, plus focused regressions. Compiler BuildError propagates unchanged;
load OSError and missing assembly symbols become BuildError with the path and
exception chained. Cache publication follows complete symbol setup. Failure
leaves retry possible; valid signatures and caching stay unchanged.

Before implementation, the seven new cases produced **5 failed, 2 passed**:
open failure returned None, three missing symbols leaked AttributeError, and
the retry case likewise leaked AttributeError. After implementation,
`.venv-rp/bin/python -m pytest parser/tests/test_cenc.py
parser/tests/test_build_wiring.py parser/tests/test_indexed_assembly.py -q`
produced **13 passed in 4.36 s**, no skips, including the real C column table
and tiny indexed builds. `git diff --check` passed. No blocked verification
was repeated and no disc, spool, scratch, symlink or other checkout accessed.

### Phase verification

The fault-injection entry point `cenc.lib()` demonstrated every error and
cache contract. Existing tiny indexed assembly fixtures exercised the valid
library. The stale fallback paragraph is gone. Phase 1 outcome is met.

**Carried:** None within this item. Plan 04's recorded blockers and plan 03's
frozen content work remain outside the design. No full-disc or memory claim.
