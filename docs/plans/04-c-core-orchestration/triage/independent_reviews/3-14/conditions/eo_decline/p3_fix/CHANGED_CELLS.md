# Plan 48 P3 — AU changed cells (successor of 4e6b0de7)

## Fix
`eo_split_on_vertices` in `parser/kiwiw/_cenc.c`: after the parity filter and before `eo_connect`, split any edge that has an existing vertex in its open interior. Parent edge is removed; sub-edges are XOR-added via `eo_edge` so an existing shorter collinear remnant cancels. Face walk remains legacy min-turn.

## Why the five seeded declines recovered
EO_DIAG named H2 equal-atan2 ties (and H1 crossings). For r359 the equal-atan2 pair from vertex 1 has the shorter destination exactly on the longer edge (T-junction). Splitting restores a planar star; the walk no longer hits an already-used half-edge; parity checks pass. Same class for the other four.

## AU confinement (`oracle_chain.py diff`)
| level | ix | iy | old_bytes | new_bytes | status |
|------:|---:|---:|----------:|----------:|--------|
| 0 | 1768 | 573 | 108466 | 108466 | changed (same length) |
| 0 | 1817 | 726 | 3266 | 3278 | changed (+12) |

Both are L0 leaves whose EO background arrangement exercised the T-junction split. No added/removed cells. Disc size unchanged (1692079168). Perth `04be2f6e` byte-identical; census guard_hits=0.

## R-DVD per-cell compare (2026-10-07 ~17:43 AEST)

R mounted at `/run/media/codyh/464210-8480`. Method: plan 42 R-coverage-by-G
(`RReader` + leaf decode; R verts → nearest G segment). Details: `R_DVD_COMPARE.md`,
`r_coverage.json`.

| cell | R-coverage vs old | payload | eo_split witness |
|------|-------------------|---------|------------------|
| L0 (1768,573) | **equal** on all metrics (accept) | same length 108466; 47 B differ | one type-288 sc=2 hexagon **rotated** (same vertices/bbox) |
| L0 (1817,726) | **equal** on all metrics (accept) | 3266→3278 (+12) | one 7-pt type-288 ring → **two** 4-pt rings sharing split vertex (3039,154) |

**all_cells_accept_no_worse_R_coverage = true.** Design HOLD LAND remains until
reconfirm + Flash. Input-ring IDs for the split not instrumented this turn.

## Residual

Prior residual (R not measured) **discharged** by `R_DVD_COMPARE.md`. Soft residual: input-ring IDs for `eo_split_on_vertices` (needs EO_DIAG rebuild).
