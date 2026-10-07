# Plan 45 Phase 2 — window determinism (R-G8-1-f)

Window `(0,828,745,831,748)`:

| Build | sha256 |
| --- | --- |
| d35b565 -j1 | `c4965442effea2ea…` MATCH historical |
| d35b565 -j4 | `c4965442effea2ea…` MATCH |
| tip (spool_overlay) -j1 | `c4965442effea2ea…` |
| tip -j4 | `c4965442effea2ea…` (= -j1) |
| -j12 | `unverifiable:cap` (encode ≤-j4) |

See `determinism.json`.
