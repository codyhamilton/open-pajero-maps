# Remediation 01 — retain and validate the R index evidence for absence

Severity: **medium**. Structural evidence/correctness finding R1 in `../REVIEW.md`.

## Defect and location

The plan chooses branch A because the original DVD lacks the O03 name. The
committed `witnesses/r.json` and `r_successor.json` contain six `empty_slot`
labels, three `outside_coverage` labels and no covering frames. They contain
no index offsets, index bytes/hashes, decoded DSA/size or reason identifying
the actual absence branch. `r_reader_control.json` proves that the same
reader resolves Perth (four frames, 739 names), but records only aggregates
for both Perth and the target block.

`witness_p1.py:132–144` initializes `empty_slot` before the lookup, then
returns that status if the blockset/table lookup fails or the BMT entry has
no size. `:195` also uses it when no leaf was yielded. These are different
claims. The shared `volume.parse_pdmdh_full` skips a BMT whose offset is
outside the buffer as well as a legitimate absent table. `verdict()` accepts
all of these `empty_slot` rows without checking an absence proof. A working
populated-cell control does not distinguish these paths at the target.

This review does **not** establish that R has the name or that the saved
result is wrong. It establishes that the committed negative witness cannot
show which index bytes prove absence, and that lookup failure can be treated
as successful absence. R is the design's arbiter, so Phase 1 outcomes 4–5
and Phase 2 A4 remain partial until this is closed.

## Scope and approach

Own `witness_p1.py`, `r_reader_control.py`, the relevant plan-29 witnesses,
`phase1_witness.md`, an appended implementation entry and
`reports/remediation-01.md`. Leave all changes uncommitted for the orchestrator. Synthetic
controls may be added to `parser/tests/test_successor_oracle_tools.py`.
Do not edit the shared parser or any plan-28 surface. Do not change the
guard, checker, tolerance, source spool or generated discs.

1. Retain the bounded index evidence that leads to each absence: absolute
   offset, length, raw hex and SHA-256, decoded fields and a specific absence
   reason. Include sufficient header/LMR/BSMR information to identify the
   selected level, blockset and block. If the BMT entry proves the whole
   block absent, one shared proof referenced by the six cells is enough;
   otherwise retain the relevant parcel-slot path and sentinel bytes.
2. Distinguish format-defined absence from failed lookup or invalid index
   bounds. Validate the relevant BSMR/table extent before relying on the
   shared parser's skipped-table result. An unexplained missing lookup,
   non-sentinel invalid offset or malformed slot must raise or yield an
   unresolved result that makes `verdict` fail. Decide and document the
   legitimate absent-table/absent-block states from the format contract;
   do not merely rename the current default status.
3. Require the new absence evidence in `verdict`. Retain support for genuine
   resolved frames and the existing outside-coverage cells. Preserve the
   nine-cell search and the historical R pin; a full R hash is unnecessary.
4. Give `r_reader_control.py` an explicit `--out` option. Retain index/frame
   identity and at least one decoded name-record byte/hash control for
   Perth, alongside the existing counts. Keep the target block census.
5. Hand bounded R reads to the orchestrator under `run_heavy_python.py`.
   Regenerate the negative witness and control, then refresh the committed
   R witnesses/verdict/note from measured outputs. Never fill sentinel
   values by hand. Preserve the prior review and append the new verdict.

## Verification and commands for the orchestrator

Use synthetic controls for a real empty sentinel, a populated slot, a
missing lookup, an invalid table offset and a malformed slot. Only the
actual empty state may support verdict A. Run permitted focused tests with
`--basetemp output/scratch-29/review/tests`; all scratch output stays under
`output/scratch-29/review/`. A fixer must not open the protected inputs.

After the reader changes, the orchestrator runs these from the repo root
(the reviewer has not run them):

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/review/r_index_run.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/witness_p1.py r-witness --disc /run/media/codyh/464210-8480/ALLDATA.KWI --keep-names --out output/scratch-29/review/r_index.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/review/r_control_run.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/r_reader_control.py --out output/scratch-29/review/r_reader_control.json
.venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/witness_p1.py verdict --r output/scratch-29/review/r_index.json --out output/scratch-29/review/verdict.json --note output/scratch-29/review/phase1_witness.md
```

Done evidence: valid, reproducible index-byte proofs for the six in-coverage
cells; the populated reader control still resolves; malformed/missing
lookups cannot give verdict A; the measured verdict remains A without drift
or concerns, or the contrary observation is escalated rather than hidden.
Leave the small measured evidence uncommitted for the orchestrator and
request an appended independent assessment. No AU encode, live K1, Perth
build, 3-90 run or full suite is needed for this finding.
