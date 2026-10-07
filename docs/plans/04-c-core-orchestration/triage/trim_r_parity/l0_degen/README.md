# L0 degenerate east-edge roads (plan 53 / R-G9-3-d)

## Verdict: **encoder defect** (not D1)

Independent bit-level decode of the 5 links' `raw_bytes` on tip `aeae426c` shows
every node absolute `sx=8192` → `decode_region_coord` → `xc=4096`, `nip=0`, all
`yc` identical. D1 reproduces the collapse faithfully.

## Root cause

`dv_assign` in `_e2.c` wrapped `lon > lon_hi` by subtracting 360°, mapping the
point into the **western** sub-cell, while encode clamped `x` to the parent east
edge (4096). Spool for (1755,591) has exactly **5** nodes with `lon` epsilon past
east (`1e-11`…`1e-8`); they assign to leaves 0/4/8 and match the five degenerates.

## Fix

`dv_assign`: after normalizing lon into `[0,360)`, if `delta > lon_span` return
`-1` (outside) instead of wrapping into the opposite side.

## AU census (divided L0 parents)

| | Before (`aeae426c`) | After (`0c22b266`) |
| --- | ---: | ---: |
| all-vertices-on-parent-edge **outside** leaf rect | **5969** | **128** |
| of which East-only | 5871 | 32 |
| (1755,591) | 5 | **0** |

Remaining 128 (N/S/W/E≈32) are a named residual class (not lon-wrap); optional
follow-up.

## Oracle

Successor **`0c22b266…`** vs `aeae426c…`: **565 changed / 0 added / 0 removed**.
All 534 pre-fix outside parents ⊆ changed; +19 L0 +12 higher-level = halo/trim
fallout. Perth tip **`5b86d33e…`** (was `04be2f6e…`; 49 divided parents in fixture).

See `discriminate.json`, `census.json`, `census_after.json`,
`successor_oracle_0c22b266.json`, `cells_aeae426c_to_0c22b266.tsv`.
