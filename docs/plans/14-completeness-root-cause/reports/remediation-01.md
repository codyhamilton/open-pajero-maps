# Remediation 01 — F1 EO representability

Status: **done** within the brief's sandbox scope. Changes are uncommitted;
no heavy jobs ran. Done-evidence item 4 remains assigned to the orchestrator.

The two checker implementations now split proper crossings, repeated-vertex
contacts, endpoints on edges and collinear overlap endpoints before counting
segment traversal parity. Empty parity returns empty, with no original-ring
fallback. Only proven simple rings use the original contour shortcut.
Python uses exact Fraction predicates; C uses the existing lossless dyadic
grids, exact determinants and rational parameter comparisons. Both order
outgoing edges exactly and propagate face parity from the exterior, avoiding
floating interior samples. A forest of even edges joins boundary components
through zero-width cuts so nested holes retain their empty interiors.
C merges concurrent intersections by equal edge parameters and reports an
explicit error for unsupported grids, collapsed distinct intersection
coordinates, or inconsistent topology; Python reports topology errors too.
Clipping, wire arithmetic, multipliers, demand counts and encoder sources
were not changed. The historical Phase 2 mirror was neither modified nor
reused; the corrected helper documents its departure from that mirror.

Changed files: `parser/tools/k1_representable.py`, `parser/kiwiw/_k1_cmp.c`,
`parser/tests/test_k1_completeness_representable.py`, additive entries in
`parser/tests/k1_fixtures.py`, and this report. Scratch evidence is under
`output/scratch-14/remediation/`.

Fresh reproductions at the initial worktree state and after the final fix:

| Ring | Production bytes / records, before and after | C representable before → after | Python representable before → after | C checked/failing before → after | Python checked/failing before → after |
| --- | --- | --- | --- | --- | --- |
| endpoint_lobes | 40 / 2 | false → true | false → true | 1/0 → 1/1 | 1/0 → 1/1 |
| twice_square | 0 / 0 | true → false | true → false | 1/1 → 1/0 | 1/1 → 1/0 |
| twice_crossing | 0 / 0 | true → false | true → false | 1/1 → 1/0 | 1/1 → 1/0 |

Every checked/failing result in the table was obtained for **both local and
tall selection**. `before.json` and `after.json` retain the per-path results;
`reproduce.py` repeats the final tiny probes. The direct checker C probe uses
the static footprint function, independently of the production probe.

Permanent coverage checks all three examples, the two endpoint lobes' separate
nonzero areas, cancellation, local/tall selection and the multiple-demander OR
contract with canceled contours plus a surviving square. It also checks
`test_bg_eo_stitch.py`'s duplicate square, partial overlap, touching lobes,
hole, short-fragment retrace and frame overlap in both orientations against
source ray parity and decoded production-probe output. A cell wholly inside a
retraced hole remains empty in both checkers and production. Unsupported C
per-axis grid extent returns error -3.

Final validation, exit 0, **395 passed in 29.84 s** (`tests-final.log`):

```sh
.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider \
  parser/tests/test_k1_completeness_representable.py \
  parser/tests/test_k1_completeness.py \
  parser/tests/test_quantisation_roundtrip.py \
  parser/tests/test_k1_background.py parser/tests/test_k1_dump.py \
  parser/tests/test_bg_eo_stitch.py
```

This includes existing positive controls, sample equality and partition/order/
merge invariance. Final targeted suite: **43 passed in 7.93 s**. No existing
expected verdict was changed. An initial new unsupported-grid test incorrectly
used separate supported axis scales; its input was corrected to exceed a
single axis's supported extent. `git diff --check` passes.

No implementation departure or remaining failure is known in the scoped
checks. Instruction contradiction: the brief's last line asks for a terminal
verdict in `REVIEW.md`, while its owned-path instructions explicitly prohibit
editing that file and assign the append to the orchestrator. `REVIEW.md` is
unchanged. The orchestrator must append that verdict and perform item 4:
verify live checked remains 1,800,514, all 776 excused keys still have zero
production records, and the older-disc control still detects exactly the 52
genuine defects. Those full-disc results are not claimed by this report.
