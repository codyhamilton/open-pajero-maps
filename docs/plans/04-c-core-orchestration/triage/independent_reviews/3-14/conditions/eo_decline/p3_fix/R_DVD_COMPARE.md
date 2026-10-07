# Plan 48 P3 — R-DVD per-cell compare + eo_split witnesses

Measured 2026-10-07 ~17:43 AEST. R mounted read-only at `/run/media/codyh/464210-8480`
(udisksctl loop of `original-disc/pajero-whereis-2007.iso`).

**Land status:** Design ACCEPT (2026-10-07 ~22:29 AEST). Promote successor
`88bd7852` after Flash comprehensive-review PASS. Soft residual (input ring IDs) is not a land gate.

## Method

- Discs: R = mounted DVD `ALLDATA.KWI`; old G = `output/scratch-48/census_builds/au`
  (`4e6b0de7…`); new G = `…/au_p3` (`88bd7852…`).
- Reader: `overlay_test.RReader` + `r_neighbours.LeafIndex` + `decode_parcel`
  (plan 42 `trim_witness.py` pattern).
- **Accept metric (plan 42 direction):** R-coverage-by-G — for each R background/road
  vertex, distance in parent-raw units to nearest G segment. Successor is no worse
  iff every summary (p50/mean/frac_le_10/frac_le_50, any-type and same-type for bg;
  road any-type) is equal or better vs the old oracle. Raw JSON: `r_coverage.json`.
- Aux (not the accept gate): G-vertices→R distance in `r_compare_g_to_r_aux.json`
  (noisy under OSM↔vendor offset; not used for accept).

## Verdict

- **all_cells_accept_no_worse_R_coverage = `True`**
- Both L0 cells: every R-coverage metric **equal** (old ≡ new). Roads unchanged.
- Accept path numbers confirmed; Design ACCEPT; land after Flash PASS.

## L0 (1768,573)

| side | frame_len | sector_len | n_bg | bg_fs | n_road | sha256 prefix |
|---|---:|---:|---:|---:|---:|---|
| R | 160 | 52544 | 14 | 690 | 451 | `2133d8a9ad6972b9` |
| old 4e6b0de7 | 108466 | 108480 | 1641 | 48816 | 693 | `3d289dce4063bcad` |
| new 88bd7852 | 108466 | 108480 | 1641 | 48816 | 693 | `c37cc79f13bc4100` |

### R-coverage (R verts → nearest G)

| metric | old | new | verdict |
|---|---:|---:|---|
| `bg_R_cover_any_frac_le_10` | 0.52 | 0.52 | **equal** |
| `bg_R_cover_any_frac_le_50` | 0.97 | 0.97 | **equal** |
| `bg_R_cover_any_mean` | 12.808565035041974 | 12.808565035041974 | **equal** |
| `bg_R_cover_any_p50` | 9.103969187952403 | 9.103969187952403 | **equal** |
| `bg_R_cover_same_p50` | 13.63396267192104 | 13.63396267192104 | **equal** |
| `road_R_cover_any_frac_le_10` | 0.8805809575040344 | 0.8805809575040344 | **equal** |
| `road_R_cover_any_p50` | 2.827283236416809 | 2.827283236416809 | **equal** |

### Payload / arrangement change

- old_len=108466 new_len=108466 len_delta=0
- shared_prefix=87249B shared_suffix=21160B
- same-length Hamming: **47 bytes** differ; first offsets [87249, 87251, 87257, 87259, 87260, 87261, 87262, 87263]…

### eo_split_on_vertices witness (decoded bg shape multiset)

- removed=1 added=1 (type-288 sc=2 faces)

**Same-length rotation of one EO face** (T-junction / equal-atan2 remnant class):
one type-288 sc=2 hexagon, identical vertex set and bbox, different closed-walk
start vertex. Matches `eo_split_on_vertices` restoring a planar star so the legacy
min-turn walk emits the same ring with a different cyclic start; XOR of collinear
remnants keeps net edge count → byte length unchanged (47 payload bytes differ).

- removed start=[2230.0, 3916.0] bbox=[2170.0, 3916.0, 2230.0, 3928.0] n_pts=6
- added start=[2170.0, 3928.0] bbox=[2170.0, 3916.0, 2230.0, 3928.0] n_pts=6
- vertex multiset: identical (rotated cycle).

## L0 (1817,726)

| side | frame_len | sector_len | n_bg | bg_fs | n_road | sha256 prefix |
|---|---:|---:|---:|---:|---:|---|
| R | 160 | 5440 | 13 | 2618 | 6 | `808d63383542b6a6` |
| old 4e6b0de7 | 3266 | 3296 | 31 | 2924 | 1 | `1e976eece3dc5991` |
| new 88bd7852 | 3278 | 3296 | 32 | 2936 | 1 | `4730f87b73e585f0` |

### R-coverage (R verts → nearest G)

| metric | old | new | verdict |
|---|---:|---:|---|
| `bg_R_cover_any_frac_le_10` | 0.0034158838599487617 | 0.0034158838599487617 | **equal** |
| `bg_R_cover_any_frac_le_50` | 0.012809564474807857 | 0.012809564474807857 | **equal** |
| `bg_R_cover_any_mean` | 8148.325785330655 | 8148.325785330655 | **equal** |
| `bg_R_cover_any_p50` | 8001.0 | 8001.0 | **equal** |
| `bg_R_cover_same_p50` | 6677.000000000393 | 6677.000000000393 | **equal** |
| `road_R_cover_any_frac_le_10` | 0.0 | 0.0 | **equal** |
| `road_R_cover_any_p50` | 11334.51017909465 | 11334.51017909465 | **equal** |

### Payload / arrangement change

- old_len=3266 new_len=3278 len_delta=12
- shared_prefix=1B shared_suffix=1008B

### eo_split_on_vertices witness (decoded bg shape multiset)

- removed=1 added=2 (type-288 sc=2 faces)

**One face → two faces at a T-junction split** (+12 B):
one type-288 sc=2 7-vertex ring removed; two type-288 sc=2 4-vertex rings added
sharing new vertex **(3039, 154)** on the former long edge. That vertex is the
`eo_split_on_vertices` open-interior hit: parent edge removed, sub-edges XOR-added
via `eo_edge`. Net +1 shape, bg_fs 2924→2936 (+12).

- removed: n_pts=7 bbox=[2924.0, 66.0, 3129.0, 267.0] first3=[[2924.0, 267.0], [3026.0, 166.0], [3129.0, 66.0]]
- added[0]: n_pts=4 bbox=[2924.0, 154.0, 3039.0, 267.0] first3=[[2980.0, 215.0], [2924.0, 267.0], [3039.0, 154.0]]
- added[1]: n_pts=4 bbox=[3039.0, 66.0, 3129.0, 154.0] first3=[[3104.0, 95.0], [3039.0, 154.0], [3129.0, 66.0]]
- shared split vertex in both added rings: `(3039.0, 154.0)`.

## Input-ring residual

Decoded G faces name the **output** arrangement change. Naming the exact OSM/
spool **input** rings whose edges entered `eo_split_on_vertices` needs a per-cell
EO_DIAG or instrumented rebuild (deferred; soft residual). Output witnesses above identify the split class;
input ring IDs are **not** a land gate per Design ACCEPT.

## Paths

- `r_coverage.json` — accept-gate numbers
- `r_compare_g_to_r_aux.json` — G→R aux (not gate)
- G discs: `output/scratch-48/census_builds/au{,/../au_p3}/ALLDATA.KWI`

