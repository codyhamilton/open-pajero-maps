# Remediation 02 — Decide and record row 335's Phase 3 disposition

Severity: **medium**. Status: **briefed**, not attempted in terminal review.

## Defect and why it matters

At reviewed HEAD `0ecbb954d8d0b1e42777d5e9a9bef4a5b99e0bee`,
`triage/phase3_membership.tsv` still assigns native dump_row 335 to
`open-question:Q-source-335`; `IMPLEMENTATION.md:157` explicitly says it has
no Design group disposition. `IMPLEMENTATION.md:161` nevertheless records
live unattributed 0 and closes Phase 3.

`DESIGN.md`'s Phase 3 outcome requires live unattributed count to equal the
open-question count. The current counts are **0 versus 1**.
`DESIGN.md:177` expressly requires a later ruling before resolving 335.
Unlike row 765, that ruling has never been recorded. A reviewer cannot make
this membership/design decision as a mechanical correction.

## Existing evidence

Identity: `(level=0, ix=1379, iy=1138, code=288, p0..p6=0, shape=-1, vert=-1)`.

- `triage/demand_attribution_3-01.md` and the corresponding TSV row name
  `tall=39083:L0:home(1379,1143):ordinal=0`, branch (c).
- `output/scratch-14/attribution/proofs/335.json` and `geometry_335.json`
  show the triangular sliver missing the centre by 0.348 raw; `TOL=0.5`
  admits it. Both mirror and production `bg_shape` emit zero records.
- Phase 1 witnesses show R and G both lack type 288.
- The saved Phase 3 completeness dump is empty: this key actually left the
  failing set along with all other 775 keys.

The source-evidence gap has therefore been resolved scientifically. This is
an unrecorded disposition, not a request to fabricate a new cause or redo
the live job.

## Approach

Obtain/record the design judgment within the normal remediation process:
either include 335 in the amended zero-cell-local-R-contribution group
(342 + 434 = 776), or give it a separate proven checker disposition
(342 + 433 + 1 = 776, all three disposed). Cite the source and byte witnesses
and explicitly discharge the earlier conditional ruling. Update only the
Phase 3 membership, group note and close record to match that decision.
Preserve the historical Phase 1/2 source gap and membership as recorded.

If Design declines both dispositions, the phase must remain partial and its
closure/count contract must be reconsidered explicitly. Do not merely
rename the open question or alter the live checker to restore a known false
failure. No geometry-code change is needed for this finding.

## Done evidence

- A recorded ruling cites the proof and identifies one Phase 3 disposition
  for the complete native key.
- Phase 3 membership remains exhaustive and disjoint over the same 776
  keys, with counts consistent in `phase3_groups.md` and `IMPLEMENTATION.md`.
- Unresolved completeness open-question count equals live unattributed 0;
  carried source-data parity observations remain explicitly outside this
  narrower checker closure, and plan 04 Phase 3 remains open.
- Append the resolution and new verdict to `REVIEW.md`; retain prior entries.
