# Phase 1 evidence-table handoff

Implemented against detached HEAD `276cc3b` in this worktree. The existing G
disc was read without re-encoding and matched
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
R and the spool were readable. This worktree had no `.venv-rp`; the existing
`/home/codyh/workspace/open-pajero-maps/.venv-rp/bin/python` was used with `-B`.
No environment was deleted or replaced.

The Phase 1 outcome read from [DESIGN.md](../DESIGN.md) was:

> on the disc in force (`4ed9cd80…` or a recorded successor), a committed evidence table lists every currently failing completeness identity exactly once. Each row has full native key, classify assignment (O01/O04/O05/O06/`NO_RULE`/other), flags `in_historic_188` and `in_added_89` against the committed 3-17 table and 3-16 TSV, an R byte/decode witness, a G byte/decode witness, and a spool/K1 requirement witness (or an explicit `evidence gap` open question for that column). The table header states: failing total, attributed by rule, unattributed total, and the numeric drift vs 3-17 (776 failing, 308 unclassified) and 3-15 (274 unattributed). No cause is named. No rule file is edited. 3-16 / 3-17 / design-170 files are not rewritten.

Fresh completeness-only K1 ran under `flock output/.heavy.lock`, `--engine c`,
`-j 6`. It exited 1 with 776 completeness failures and wrote
`output/scratch-14/k1_full.json`, its log, and `dump_raw/`. Every full native
identity is unique; all 188 historic and all 89 added identities are present,
with no intersection. The other 499 identities belong to neither recorded set.

[The table](../triage/completeness_evidence.tsv) and
[its note](../triage/completeness_evidence.md) contain the per-row evidence and
count interpretation. The committed `build_evidence.py` provides the witness
method; `verify_evidence.py` audits identities, flags, witness references and
the underlying byte ranges. Scratch products are under `output/scratch-14/`.

Audit **PASS**: 776 unique identities, 188 historic / 89 added flags and
1,791 distinct byte ranges checked against the actual discs/spool. All 776
G target counts are zero. R target counts are zero in 433 rows, one in 342,
and eleven in one; neither disc has an enumeration/decode gap. Concrete
spool requirement triggers were recovered for 775 rows. Native row 335
`(0,1379,1138,288,0,0,0,0,0,0,0,-1,-1)` has a retained K1 demand witness but
an explicit source-evidence gap: which source and exact requirement branch
establish that demand? No conclusion is drawn from these presence counts.

The material deviation is the brief's explicit assignment-gap fallback.
`output/scratch-3-07` / `scratch-3-08` and the sibling 3-14 links no longer
resolve; no retained side table or recomputation harness was recovered from
the output search. The historical experimental mechanism predicates were not
reconstructed from rule notes. Fresh raw rows have no `other_mechanism`.
`dump_ext/` retains the raw bytes unchanged and records that missing evidence
in manifest metadata. Unchanged-rule classify was attempted and exited 2:
`rule O01: unknown column 'other_mechanism'`. No partition or assignments were
produced. All 776 assignment entries therefore say `evidence-gap`, rather than
`NO_RULE`; no mechanism values were fabricated. The live failing count is
measured, but definitive live attributed/unclassified totals remain open.
The note states numeric differences for this evidence ledger separately from
the historical classifier totals.

Unfinished: recover or reproducibly recompute each row's mechanism witness,
then obtain a real classify partition; resolve row 335's source witness.
This handoff makes no root-cause
finding and does not close plan 04 Phase 3 or add a phase-closing trailer.
No encoder, checker, rule, 3-16, 3-17, design-170 or plan-15 file was edited.
The G oracle hash was rechecked after the evidence pass; the protected
scratch-3-11 disc remained
`013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04`.
Rule and encoder/checker source checksums matched their pre-edit pins.
The protected disc was read only. Nothing was pushed and no PR
or workflow-service post was made.
