# Brief: 32 -- Per-kind budgets in the hard-ceiling fallback; L0 road-name halo (spotcheck regressions)

Consumer: implementation worker. Owned paths: `parser/kiwiw/divide.py`, `parser/build_alldata.py`
(plumbing), `parser/tests/test_divide.py`, this brief, IMPLEMENTATION.md. No rebuild; do NOT touch
`output/` or `output/spool`; do NOT edit `spot_checks.json`, `synth.py`, `harness/`.
Depends on: 31/31b record (rebuild #4). Verified by the assembly-only rebuild (32b/32c).

## Root causes (live rebuild #4 `output/`, read-only)

1. Envelope L0 bg 130,106, L8 road 121,712, L8 bg 130,558. `plan_divisions` last tier, when `measure` raises
   (frame > 131,070 B), called `_shrink_to_fit` (unprioritised count bisect; keeps names, then bgs, then the
   first N roads in input order), then re-measured kinds on the *original* content `c`, not the shrunk one.
   That re-measure raised again, `sizes` became `None`, `_kind_breach({})` was empty, and `_trim_kinds` never ran.
   So the 3 fallback cells (L8 (3,3), L8 (3,0), L0 (2,1)) escaped both the per-kind budgets and the priority
   order. Also: L8 (3,0) holds 2,417 links, all motorway/trunk (pinned at L>=2), 136,924 B vs budget 99,794 B.
2. Spotcheck Perth L0 "Hay Street", Adelaide L0 "Pulteney Street". Not name trim and not dedupe. Per-kind
   escalation (brief 29) divides both CBD cells to type 2 (type-1 quadrants breach bg 28-74 KB and name 34 KB
   vs R's 25.9 KB / 24.6 KB budgets). `_retile_content` assigns each name to the one sub-cell containing its
   point, and `find_parcel` returns only the leaf containing the query point. Perth leaf
   (lat -31.953125..-31.9479, lon 115.859375..115.8671875, 288 names) has no Hay Street (nearest instance
   0.0017 deg south); Adelaide leaf lacks Pulteney (0.0045 deg east). Rebuild #3 left these cells whole.
   Streets do not cross these sub-cells, so no per-chain rule can restore them.

## Changes
1. `divide._shrink_priority` (used at the last tier when `kind_limits` is set): cut each budgeted kind to its
   priority-ordered prefix that meets its own budget (measured with other kinds emptied, so no ceiling error);
   if the frame still exceeds the ceiling reduce roads, then backgrounds, then names (road names last), each to
   the largest priority prefix that encodes. The L>=2 motorway/trunk pin is not honoured here (it only orders).
   Drops are added to `trim_stats` (so `trimmed_items` counts them) with a stderr WARNING per kind. Without
   `kind_limits` the old `_shrink_to_fit` path is unchanged.
2. Road-name halo: `plan_divisions(name_halo=True)` appends to each divided sub-cell (types 1/2, not cells
   that were trimmed/shrunk) the string_type-5 names of the parent cell that sit outside the sub-cell but within
   one sub-cell width/height, whose text the sub-cell lacks (nearest instance per text, nearest first), as many
   as still meet the name budget and the frame threshold, with lat/lon pinned 1% inside the sub-cell edge.
   `build_alldata.NAME_HALO_LEVELS = (0,)`: L0 only (R L0 name density ~10x G's, declared deviation; L2-L8 name
   counts already 0.75-1.2x). Counter `halo_names` per level printed and written to `manifest.json`.
3. L8 name trim (37/287 = 12.9%) deliberately unchanged: the budget is R's idx-2 max (366 B) and the brief 30
   copy is a separate frame, so counting it would not move idx-2; no clearly-correct change. Report as-is for
   the user's deviation decision.
4. Tests (`test_divide.py`): budgets+priority in fallback, ceiling reduction order, `plan_divisions` fallback
   honours budgets, halo candidates/budget bound.

## Fixture / real-data evidence
`--fixture perth --levels 0 2 4 6 8 --out /tmp/perth32/perth32.kwi`: all kind maxima <= R at L0-L8; spot point
resolves William/Wellington/Hay (was Hay missing; perth29 288 names -> 437). Adelaide real cell: halo adds 199
names (name 10,246 -> 16,164 B <= 24,568), includes Pulteney Street. Real L8 spool through `plan_divisions`
(read-only): 3,3 bg 1,471 dropped; 3,0 roads 1,215/2,417 dropped, bg/names kept; L8 name trim 37 as before.
pytest parser/tests -q: 278 passed.

## Expected at full scale (verify in 32c)
Envelope: only the two declared count residuals (L0 name_count, L12 parcel_count). Spotcheck 14/14. Trim
table: L8 road now nonzero (~1.2k links, one cell), L0 bg trim slightly changed; L0 bg 1.388% still >1%.
