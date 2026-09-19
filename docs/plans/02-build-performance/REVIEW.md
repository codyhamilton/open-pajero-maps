# Review — plan 02 build performance

- **Verdict: PASS_WITH_FOLLOWUPS**
- Reviewed SHA: 7e5b3b0 (work committed directly on `master`; PR branch cut from it)
- Lenses: contract/correctness, intent/assumptions, failure modes/performance (single reviewer).

## Acceptance criteria
| Criterion | Status | Evidence |
|---|---|---|
| Full build sha 51c254ac…, size 1,397,923,200, ≤6 min, ≤3 GB | met | `-j 12`: 262.9 s, 2,995 MB tree-summed RSS, sha matches |
| Perth fixture sha | met | e275879f… at `-j 1`, `-j 4`, and under PYTHONHASHSEED 1/999 |
| Worker count 1 vs 12 identical (full) | partial | 12 verified on full; 1 verified on full pre-Phase 4 (771 s) and on Perth post-change; unit test j=1/2/5 with mask fill |
| Converter stats equal; converted-spool build matches | met | Phase 2 record |
| `osm_to_parcel_geometry --fixture perth` new-format spool | partial | not run end-to-end; Perth built from the converted full spool. Writer covered by `test_spool_binary.py` |
| Tests incl. fuzz, spool equivalence, streaming | met | 288 passed |
| Different PYTHONHASHSEED identical | met | Perth, above |
| Provenance / no large binaries staged | met | provenance updated; largest tracked file 164 KB |
| RSS independent of output size | partial | streaming spill verified; levels-12–2 vs full comparison not recorded |

## Findings
- **medium (follow-up)** RSS margin is thin: 2,995 MB vs 3,000 MB limit. The metric sums RSS over forked workers, which double-counts shared copy-on-write pages, so real usage is lower, but the margin is slim. Lower `-j` or the pending window (`2×jobs`) if it regresses.
- **low (follow-up)** `_plan_chunks` weights use a fixed empty-cell constant (512); it only affects balance, never bytes.
- **low (follow-up)** Full `-j 1` run and the extractor `--fixture perth` end-to-end run were not repeated after the final change.

No blocker/high findings; nothing fixed in place, no briefs.

## Intent and assumptions
Byte identity is preserved by design: chunks are whole-row ranges merged in order, counters are additive, timings stay out of the manifest. Assumption "cells are independent" holds (halo uses only the parent cell's names). Numpy `rint` == half-to-even is guarded by the scalar-oracle fuzz.

## Plan sufficiency
Sufficient; criteria were measurable. The RSS metric definition (sum vs proportional) should have been pinned.

## Residual risks
Thin RSS margin; the untested extractor-to-new-spool end-to-end path.
