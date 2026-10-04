# Fixture precheck execution

Run: Codex, one worker, workspace open-pajero-maps-status-continue-3,
started 2026-10-05 Australia/Brisbane. No service run identity claimed.

## Ground

Plan 01's recorded way-bbox follow-up remains absent at `5742465`.
Spool totals are already collected during `_finalize_index` at `6a6c986`.
Plan 04 3-90 is blocked and no full-disc check is scheduled here.

## 1-01-fixture-precheck

Before implementation, the regression failed because a disjoint fixture road
reached full-grid splitting. The handler now caches full target-cell extents
per level, computes one way bbox and skips provably disjoint levels. Whole-grid
levels bypass rejection. Longitude interval images preserve wrapping; edge
columns conservatively retain longitude-clamped inputs. A 1e-9 degree guard
retains numerical boundary ambiguities. Nodes, splitting, ordinal generation,
centroids, filters and caps retain their existing code.

Recorded plan 01's precheck resolution and the already-landed spool totals;
Architecture documents admission. No frozen content or checker work was built.

Verification: first extraction file 11 passed in 28.57 s. After adding per-level
and boundary-guard cases, all six affected suites passed: **84 passed in 28.41 s**,
no skips. Three enabled/bypassed synthetic PBF fixture extractions had identical
index/data bytes, covering place, road and background names and the antimeridian.
Existing full-grid tests passed. `git diff --check` passed. Test fixtures used
new `/dev/shm/maps-fixture-precheck*-20261005` paths; the prior-seat Python
environment was used read-only with bytecode disabled. Protected inputs stayed
untouched. No full-PBF wall, build-byte or Phase 3 closure claim is made.

Design and brief feedback returned `not delivered`, with nothing queued.
One-worker self-review; no independent approval or service identity claimed.

### Carried

None within this precheck. Existing Phase 3 blockers and dependent work stand.
