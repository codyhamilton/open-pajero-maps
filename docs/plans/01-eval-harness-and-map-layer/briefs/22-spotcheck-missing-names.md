# Brief: 22 — `spotcheck` FAIL: missing road/place names (Sydney/Melbourne L0, Perth L2) (ad hoc)

Consumer: implementation worker. Authored by an orchestrator-dispatched investigation agent
following up on WP1 unit 15b's 2026-09-09 full-Australia build (`spotcheck` FAIL: "Sydney
level 0 missing all 3 expected road names; Melbourne level 0 missing 2 of 3; Perth level 2
missing its place name" — `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, unit
15b section).

Owned paths: none pre-assigned — depends which fix direction is chosen (see "Open
question" below); likely `parser/kiwiw/divide.py` and/or `parser/refdata/selection.json`.
**Do not start work until the collision with the envelope-check investigation (see
`docs/plans/01-eval-harness-and-map-layer/briefs/2x-*envelope*.md` if one exists) is
checked** — both trace into the same capacity/calibration machinery (`divide.py`'s
lossy-drop fallback and unit 14's `selection.json`), so a naive fix here could clobber
concurrent calibration work.
Depends on: unit 13 (`divide.py`, done), unit 14 (`selection.json`, done).

## Required reading, in order

1. `docs/design/target-disc.md` — the map layer row, "spotcheck" (fixture-table contract).
2. `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md` — unit 15b's build record
   (spotcheck FAIL detail) and unit 13's section ("lossy bisection fallback" deviation).
3. `parser/kiwiw/divide.py` — module docstring in full, then `_shrink_to_fit()` and
   `plan_divisions()`.
4. `parser/refdata/spot_checks.json` and `parser/harness/checks/spotcheck.py`.
5. `parser/osm_to_parcel_geometry.py` — `_handle_node()` (place-node extraction) and
   `_make_name_record()`'s docstring (the "place" kind is itself flagged as an unresolved
   open question by an earlier unit — read it, it may be relevant to any level-0/level-2
   place-name work here).

## Findings (this investigation)

### Sydney/Melbourne level-0 missing road names — root cause identified, not fixed

`parser/refdata/selection.json`'s level-0 rule admits every relevant `highway=` class
(`motorway` .. `busway`, 17 values) and OSM confirms York/Kent/Elizabeth Street (Sydney) and
Queen/Swanston/Collins Street (Melbourne) exist as real, currently-tagged ways in that class
set near the fixture coordinates — so this is not a `selection.json` thinning gap (cause (a)
in the dispatch brief) and not a vocab-mapping gap (cause (b)): road names at level 0 always
use the fixed `type_code=0x210`/`string_type=5` rule (`_make_name_record`), which has no
tag-dependent vocab lookup to fail.

The actual mechanism is `parser/kiwiw/divide.py`'s **lossy bisection fallback**
(`_shrink_to_fit`, added by unit 13, "expected" per its own report but never traced through
to `spotcheck` before now). WP1 unit 15b's build log recorded exactly **five
`WARNING [kiwiw.divide]` lines, at levels 8 and 0** — cells whose content, even after the
largest supported division (type 2, 4×4), still exceeds `synth.py`'s hard 131,070-byte
u16 word-count ceiling. `_shrink_to_fit` bisects the *combined* road+background+name item
count down to whatever fits, but keeps items in a fixed priority order:

```python
keep_roads = roads[:keep] if keep <= len(roads) else roads
remaining = max(0, keep - len(roads))
keep_bgs = bgs[:remaining] if remaining <= len(bgs) else bgs
remaining = max(0, remaining - len(bgs))
keep_names = names[:remaining]
```

— roads are kept first, backgrounds second, **names are kept only from whatever budget is
left over**, so under a tight budget the "names" list (which is where road-label
`NameRecord`s live, separate from `RoadLink` geometry — see `_record_texts()` in
`spotcheck.py`) is truncated to zero first. Sydney and Melbourne are exactly the kind of
extremely dense, road-chain-dominated CBD cells this fallback targets (unit 13's own report
calls out "road-chain-dominated" cells as the typical trigger). This investigation could not
confirm from inside this worktree that Sydney's/Melbourne's specific level-0 cells are two of
the five warned cells (the run's logs, `/tmp/wp1-unit15-logs/`, are correctly gitignored and
not present in a fresh worktree, and no PBF/spool is available here to re-run the extractor —
see `docs/provenance.md`), but the mechanism, the affected levels (8 and 0), and the
"road-heavy cell, names dropped" shape of the fallback all line up precisely with the
symptom. This is offered as the most probable root cause, not a confirmed one.

**Why this is not fixed here:** the fix space is exactly the envelope check's territory —
either (i) `_shrink_to_fit` should preserve *names* preferentially over some road geometry
(a drop-order change, cheap but changes which content survives an already-lossy fallback in
a way that could itself perturb envelope counts), or (ii) `selection.json` should thin
level-0 road classes more aggressively in exactly these dense CBD cells so they never reach
the hard ceiling in the first place (a calibration change, unit 14's territory, and unit 14's
own report already flags levels 4/8 as "close to the 2.0x ceiling with no finer OSM class
available to split further" — the same capacity pressure). Per this investigation's dispatch
brief, a fix that touches `selection.json`'s calibration numbers is explicitly out of scope
for a same-session fix and must not collide with concurrent envelope-check work.

### Perth level-2 missing place name — could not diagnose; live-OSM checks performed

Ruled out, using a live Overpass API query (internet was available in this session) against
current OSM data:

- **Not a vocab/selection gap**: Perth's real `place=city` node (OSM node 29277817,
  `name=Perth`) is tagged exactly `place=city`, which is in `selection.json`'s level-2
  `place` allow-list (`["city", "town"]`). Not a `bg_type.json` issue either — place-node
  extraction (`_handle_node`) never consults `bg_type.json`, it checks `place in ("suburb",
  "city", "town", "village", "locality")` directly.
- **Not a grid/parcel-boundary mismatch**: the fixture's query coordinate
  (-31.9505, 115.8605) and the real OSM node's coordinate (-31.9558967, 115.8605784, ~600m
  south) resolve to the *same* level-2 top-level cell (`ix=206, iy=216` against
  `parser/refdata/grid.json`'s reference grid), and, worked through by hand, to the same
  sub-cell even under a hypothetical 2×2 or 4×4 `divide.py` split of that cell. So a
  fixture-coordinate/actual-node offset crossing a parcel boundary is not the cause (checked
  because the other six cities' fixture coordinates are all similarly offset from their real
  OSM node by 70-500m, yet only Perth fails at level 2 — ruling this class of explanation out
  rather than assuming it).
- **Not an obvious spool/dedup bug**: `parser/kiwiw/spool.py`'s `SpoolWriter.add` appends
  every record for a given `(ix, iy)` (no per-cell cap, no overwrite-by-key), so nothing in
  that path silently discards a second or later name touching the same parcel.
- `divide.py`'s lossy fallback is very unlikely to be responsible here: unit 15b's build log
  only reported `WARNING [kiwiw.divide]` lines at levels 8 and 0, not level 2.

What was **not** ruled out, for lack of data in this worktree: whether the specific
2026-08-24 OSM PBF extract used for the 15b build (not present here; ~900MB+, not committed
per `docs/provenance.md`) had different tags/geometry for the Perth city node than the
current live OSM data queried here three weeks later, and whether the real generated
`output/ALLDATA.KWI` (also not present/regenerable in this worktree) actually resolves
`find_parcel(-31.9505, 115.8605, level=2)` to the cell this investigation computed by hand.
Confirming either requires re-running the extractor+build against a PBF (33+6 minutes wall
clock per unit 15b's own timing table) and inspecting the real spool/output directly — this
investigation did not have that data or the time budget to reproduce it.

## Open question for whoever picks this up

Coordinate with whoever is fixing the envelope check's capacity/calibration findings before
choosing a fix direction for the Sydney/Melbourne piece — the two most plausible fixes
(`divide.py`'s drop order vs. `selection.json`'s level-0 thinning) both touch shared,
concurrently-worked machinery. For the Perth piece, the next step is almost certainly a
targeted re-run: extract+build with `--fixture` scoped tightly around Perth (as unit 13's own
Perth fixture build already demonstrates is cheap relative to a full-Australia run), then
inspect the level-2 spool/output directly for cell `(206, 216)` to see whether the "Perth"
`NameRecord` was ever produced by the extractor at all, or produced and then lost downstream.

## Report back

Whether the Sydney/Melbourne hypothesis was confirmed against the real spool/build output,
which fix direction was chosen and why, and (for Perth) what the targeted re-run found.
