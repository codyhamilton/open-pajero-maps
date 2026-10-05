# Remediation 01 — Complete the independent EO representability contract

Severity: **high**. Status: **briefed**, not attempted in terminal review.

## Defect and contract

Plan 14 Phase 3 permits an absent `(cell, type)` to pass only when no demanding
shape has a representable EO footprint. Both new checkers can instead discard
real missing geometry, and can demand geometry whose EO interior is empty.

Locations at reviewed HEAD `0ecbb954d8d0b1e42777d5e9a9bef4a5b99e0bee`:

- `parser/tools/k1_representable.py:178`: only proper crossings trigger face
  decomposition. The no-crossing shortcut uses the signed area of the whole
  contour, which can cancel between distinct endpoint-touching lobes.
- `parser/tools/k1_representable.py:183` and `:200`: empty arrangements fall
  back to that same original contour, reviving canceled traversals.
- `parser/kiwiw/_k1_cmp.c:244`, `:258` and `:304`: the C implementation has
  corresponding topology omissions and fallback.
- Missing-pair callers are `parser/tools/quantisation_roundtrip.py:1032`
  and `parser/kiwiw/_k1_cmp.c:423`.

This is a shared defect: C/Python equality alone cannot detect it. Production
`parser/kiwiw/_cenc.c:695` handles endpoint contacts and collinear overlap;
`:808` explicitly dispatches repeated/touching vertices to EO processing.
The production encoder must remain independent of the checker implementation.

## Reproductions

Raw cell is `[0,4096] × [0,4096]`, multiplier 1, background type 288. Close each
ring implicitly. These tiny probes were independently repeated in terminal
review; no AU job is needed.

```python
endpoint_lobes = [
    (2000, 2000), (2100, 2000), (2100, 2100), (2000, 2100),
    (2000, 2000), (2000, 1900), (1900, 1900), (1900, 2000),
]
twice_square = [(1800, 1800), (2300, 1800),
                (2300, 2300), (1800, 2300)] * 2
twice_crossing = [(1000, 1000), (2500, 2000),
                  (1000, 2000), (2300, 1000)] * 2
```

Observed:

| Ring | Production `bg_shape` (bytes, records) | Python representable | Missing-disc completeness C / Python | Required result |
| --- | --- | --- | --- | --- |
| endpoint_lobes | (40, 2) | false | checked 1, failing 0 / checked 1, failing 0 | failing 1 |
| twice_square | (0, 0) | true | checked 1, failing 1 / checked 1, failing 1 | failing 0 |
| twice_crossing | (0, 0) | true | direct footprint probe | representable false |

The two 100×100 endpoint lobes each have nonzero EO area; opposite winding
does not remove either EO component. Traversing either closed contour twice
cancels its EO interior. These establish expectations independently of the
production probe.

To repeat the end-to-end synthetic checks, insert each case temporarily in
`parser/tests/k1_fixtures.py`'s `REPRESENTABLE_CASES` dictionary in memory,
then call `build_representable_fixture(temp_path, name)`,
`quantisation_roundtrip.roundtrip(..., workers=1)` and
`fx.k1_run(disc, spool, fx.plan_bands(disc, spool))`. The fixture produces an
absent-disc cell and the demanding spool shape. Production comparison can
use the existing test-only bg_eo probe or the plan-14 `CProbe` in a temporary
directory: `probe.run(y_coords, x_coords, 1, 288, 0, (0,4096,0,4096))`.

## Fix approach and boundaries

Implement independent EO topology covering proper crossings, repeated
vertices, endpoint-on-edge contacts and collinear overlap in both languages.
Split at the necessary contacts, preserve edge parity cancellation, and walk
the actual nonempty EO faces. An empty parity arrangement must stay empty;
an unsupported numerical case must report an explicit error. Restrict any
simple-ring shortcut to a proven simple ring. Do not call encoder geometry
from the checker, loosen tolerances, change demand counts or adjust existing
expectations to conceal disagreement.

Scope: the two footprint implementations and meaningful synthetic regression
coverage. No production encoder or rule changes. The Phase 2 research mirror
shares the shortcut; do not silently rewrite its historical evidence. If it
is reused, explicitly document its limitation or version the corrected helper.

## Done evidence

1. All three examples have the correct EO/representability result in both
   checkers, with endpoint_lobes still failing when G is absent. Cover local
   and tall selection and the existing multiple-demander OR contract.
2. Existing positive controls and sample/partition invariance pass, with no
   unrelated expectation edits. Use lightweight pytest suites first.
3. Check representative endpoint/overlap/retrace fixtures from
   `parser/tests/test_bg_eo_stitch.py` against independent parity expectations
   and the test-only production probe.
4. The orchestrator verifies after remediation that live checked remains
   1,800,514, the 776 excused keys remain backed by zero production records,
   and the older-disc positive control still detects exactly the 52 genuine
   build defects. Any full-disc run belongs outside the review sandbox.

Append a new terminal verdict to `REVIEW.md` after remediation; retain this
finding and the original review evidence.
