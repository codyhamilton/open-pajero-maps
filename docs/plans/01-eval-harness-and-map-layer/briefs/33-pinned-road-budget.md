# Brief: 33 -- Pinned motorway/trunk roads no longer exempt from the road kind budget (L8 road sub-frame)

Consumer: implementation worker. Owned paths: `parser/kiwiw/divide.py`, `parser/tests/test_divide.py`, this brief,
IMPLEMENTATION.md. No rebuild; do NOT touch `output/`, `output/spool`, `spot_checks.json`, name priority.
Verified by the assembly-only rebuild (33b/33c).

## Root cause (read-only, real L8 spool through `plan_divisions`, live report.json)
The residual envelope FAIL (L8 road max 121,080 > R 99,794) was NOT the fallback cell (3,0) (that one now ends
at 99,766 B, 1,215/2,417 dropped, within budget). The 121,080 B frame is L8 parcel (6,2) type-2 sub-cell (3,1):
2,011 links, all motorway/trunk. Its whole frame is under the 131,070 ceiling, so it goes through
`_trim_kinds`, which floors the road prefix at `n_pinned` (L>=2 motorway/trunk never trimmed). All links are
pinned, so nothing is dropped (and the cell is not counted in trim_stats). Same for parcel (7,3) sub-cell (2,0),
118,462 B (also > budget). Not padding/measure mismatch (harness and `_measure_one` use the same mfde size), not
the ceiling. R's own L8 road max is 99,794, so R never carries more; no R content is dropped.
## Change
`divide._trim_kinds`: if the pinned prefix alone exceeds the kind limit, the pin is released for that cell
(links are still trimmed in priority order: motorway, trunk first, longest first). Pin still holds whenever the
pinned links fit. Test `test_pinned_roads_trimmed_when_they_alone_exceed_budget`; old zero-budget pin test now
uses a budget the pinned links fit.
## Evidence
Real L8 spool, all parents with >=1,500 links (4 cells) via `plan_divisions` with budgets: emitted kind max
road 99,786 (<=99,794), bg 119,896 (<=120,946), name 356 (<=366). Drops: (6,2) 749 roads, (7,3) 667, (7,4) 1,215
(fallback); (7,2) names only. Total ~2.6k roads over 4 cells, trim stays far below 1% of L8 roads.
pytest parser/tests -q: 279 passed (halo/spotcheck-related tests unchanged; L0 halo path untouched).
## Expected in 33c
Envelope: only L0 name_count and L12 parcel_count; L8 road trim slightly higher (~4 cells); spotcheck 14/14.
