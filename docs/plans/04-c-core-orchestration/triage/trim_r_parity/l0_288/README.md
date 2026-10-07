# L0 (1755,591) type-288 provenance census (plan 51)

Oracle tip `aeae426c…` (`output/scratch-50/G_new`). Plan 50 did **not** alter this parent
(not in the 341 targets); parent type-288 count remains **8777** (plan 42 unchanged).

## Dominant mechanism (≥95%)

**`land-local-catchall-emission`** — **98.31%** of parent type-288 items
(8629 / 8777) are already in the pinned spool cell as L0 vocab catch-all
(`match {} → 288`) under `selection.json` `background_all: true`.

| Class | Count | Fraction |
| --- | ---: | ---: |
| land-local (spool catch-all) | 8629 | 98.31% |
| overlap-share-in (G − spool lower bound) | 148 | 1.69% |
| marine-share-in (separable) | 0 | 0% |
| encoder-synthesised | 0 | 0% |
| unknown | 0 | 0% |

DESIGN Assumption 1 (mostly marine-relation spill) is **wrong** for this cell.
All 8629 local labels decode to the placeholder `unknown type 0x120` (288).

## Sub (2,1) = leaf index 6

| Metric | Value |
| --- | --- |
| Frame bytes | 131072 (cap 131070) |
| Type-288 kept | 6401 |
| Type-288 dropped (shrink) | 227 |
| Pre-shrink type-288 | 6628 |
| Roads kept | 0 |
| Roads dropped (shrink) | 207 |

Kind-order pressure: type-288 accounts for **94.63%** of (288 + dropped-road)
vertices in the trim dump. Absent those 6628 items, dv_shrink would not cut the
207 roads (sibling leaves retain roads under the same cap).

## R (same parent)

1 leaf, 21 backgrounds: **0×288**, 19×1024, 1×321, 1×291; 179 road links.
R road length in (2,1): 3695 raw (plan 42).

## Phase 2 disposition

**Proven-cause** (no code / oracle change). Rule citation:

1. `parser/refdata/selection.json` L0 `background_all: true`
2. `parser/refdata/vocab/bg_type.json` L0 `match:{} → 288`
3. `docs/design/osm-vocabulary-mapping.md` (288 catch-all is a decision)
4. `docs/schema/map-background.md` + plan 03 F6 (excess buildings; replace catch-all)

F6-style selection replacement is national product work, not a cell-local patch.
Kind-order road→bg→name was **not** flipped (needs Cody). Road volume loss remains
a named residual under current policy.

See `census.json`.
