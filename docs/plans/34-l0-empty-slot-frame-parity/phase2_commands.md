# Phase 2 — exact Execute commands

These commands are for Execute only (unit 2-02 version; Execute runs them as
`output/scratch-34/run_p2b.sh`, log `output/scratch-34/run_p2b.log`).
Run from the repo root, serially in one Bash shell. Stop on any failure;
inspect every wrapper log's exit and memory peak before proceeding.
The wrapper acquires `output/.heavy.lock`; never pass `--no-flock`.
The initial directory creation deliberately fails if either destination already
exists. Do not remove an existing destination to make the commands pass: use a
new, explicitly recorded path instead. Protected inputs are read-only.

```bash
set -euo pipefail
G=docs/plans/34-l0-empty-slot-frame-parity/phase2_gates.py
W=docs/plans/34-l0-empty-slot-frame-parity/frame_witness.py
H=".venv-rp/bin/python -B parser/tools/run_heavy_python.py"
PY=".venv-rp/bin/python -B"
mkdir -p output/scratch-34/runs
mkdir output/scratch-34/G_new
mkdir output/scratch-34/perth_new

$H --log output/scratch-34/runs/p2_before.json -- $PY $G snapshot --out output/scratch-34/protected_before.json

$H --log output/scratch-34/runs/p2_encode.json -- $PY parser/build_alldata.py --spool output/extract_timing/spool --out output/scratch-34/G_new/ALLDATA.KWI -j4

$H --log output/scratch-34/runs/p2_sha.json -- $PY $G sha --path output/scratch-34/G_new/ALLDATA.KWI --out output/scratch-34/successor_sha.json
candidate_pin=$($PY -c 'import json; print(json.load(open("output/scratch-34/successor_sha.json"))["sha256"])')

$H --log output/scratch-34/runs/p2_diff.json -- $PY $G diff --old output/scratch-29/G_new/ALLDATA.KWI --new output/scratch-34/G_new/ALLDATA.KWI --out output/scratch-34/cell_diff.json

$H --log output/scratch-34/runs/p2_r_check.json -- $PY $G r-check --diff output/scratch-34/cell_diff.json --out output/scratch-34/r_check.json

$H --log output/scratch-34/runs/p2_block_witness.json -- $PY $W probe --disc g_successor --path output/scratch-34/G_new/ALLDATA.KWI --expected-sha256 "$candidate_pin" --out output/scratch-34/g_phase2.json

$H --log output/scratch-34/runs/p2_block_check.json -- $PY $G check-witness --witness output/scratch-34/g_phase2.json --expected-sha256 "$candidate_pin" --out output/scratch-34/block_check.json

$H --log output/scratch-34/runs/p2_k1.json -- $PY parser/tools/quantisation_roundtrip.py --disc output/scratch-34/G_new/ALLDATA.KWI --spool output/extract_timing/spool -j 6 --engine c --out output/scratch-34/k1.json

$H --log output/scratch-34/runs/p2_perth_encode.json -- $PY parser/build_alldata.py --spool output/extract_timing/spool --fixture perth --out output/scratch-34/perth_new/ALLDATA.KWI -j4

$H --log output/scratch-34/runs/p2_perth_sha.json -- $PY $G sha --path output/scratch-34/perth_new/ALLDATA.KWI --out output/scratch-34/perth_sha.json

$H --log output/scratch-34/runs/p2_perth_diff.json -- $PY $G diff --old output/scratch-29/perth_base/ALLDATA.KWI --old-sha 04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728 --no-require-phase1 --new output/scratch-34/perth_new/ALLDATA.KWI --out output/scratch-34/perth_cell_diff.json

$H --log output/scratch-34/runs/p2_final_sha.json -- $PY $G sha --path output/scratch-34/G_new/ALLDATA.KWI --expected "$candidate_pin" --out output/scratch-34/successor_final_sha.json

$H --log output/scratch-34/runs/p2_after.json -- $PY $G snapshot --against output/scratch-34/protected_before.json --out output/scratch-34/protected_after.json
```

`phase2_gates.py diff` is plan 34's own cell diff, equivalent to the design's
suggested plan-31 cell diff. It neither imports nor runs plan 31.

- It streams bounded index/frame reads into disk SQLite and verifies the
  predecessor's full pin (`--old-sha`, default `2ee3456a…`).
- It compares whole-frame multisets by `(level, ix, iy)`, including
  multiplicity, at every level.
- It lists **every** changed cell and classifies each as
  `removed_outside_mask_empty_shell` or `other`, as defined in
  `phase2_cause.md`. Any `other` cell fails the gate. For AU, the three
  Phase 1 cells must be in the removed list.
- It assumes neither equal offsets nor equal file sizes, and rechecks both
  full-file hashes afterwards.

`r-check` takes the diff's removed list and resolves every L0 removed cell
on R `8c2d2027…` through plan 29's hardened reader. Every cell must be
`empty_slot` with no frames. A lookup failure, a resolved frame, or any
non-L0 removed cell fails the check. R's full pin is checked before and
after.

Perth is diffed with the same classifier against `04be2f6e…`. An identical
Perth disc gives zero changed cells.

The candidate `frame_witness.py` probe still verifies a full, explicit pin,
uses the hardened plan-29 reader and preserves Phase 1 witnesses. Its new
`--expected-sha256` requires `--path` and an explicit non-Phase-1 output path.
`check-witness` replays every index proof offline and demands 2,048
`empty_slot` cells, 0 frames and 0 lookup failures in block 0. A lookup failure
can never satisfy this gate. Execute should commit the candidate witness and
gate results under new names after inspection; do not run Phase 1 `publish`
against this candidate.

The snapshots stream SHA-256 for R, `2ee3456a…`, `4ed9cd80…` and `013586b5…`,
checking the exact historical pins; they also hash every spool file, with
relative names and sizes in the aggregate fingerprint. They must compare
identically before/after. The R mount used is
`/run/media/codyh/464210-8480/ALLDATA.KWI`; a different mount requires Execute
to explicitly adjust the snapshot input and retain the same R pin. A missing
protected input fails, and must not be dropped from the snapshot.

After all gates pass, Execute fills `disposition.json` and `.tsv` placeholders:
new disc path/SHA, cell diff path/scope, K1 report/exit/pass, Perth SHA,
protected-input snapshot paths/fingerprint, committed candidate witness and
block proof, R check. Then and only then change each verdict from
`conflict-open` to `fix-landed` and mark the precise plan-29 residual
discharged. K1 exit 0 plus its report's `pass: true`, the R check, and a
passing Perth classified diff are required.

Execute must also amend `docs/design/out-of-span-name-guard.md` explicitly:
probe-and-pad still preserves guarded versus original chunk topology/extents;
the subsequent plan-34 rule omits outside-mask exact empty shells, so
final-disc confinement is by classified cell identity.
Retained frames still obey the guard's padding/no-enlargement checks. Record
successor provenance and OVERVIEW without closing Plan 04 Phase 3. Concurrent
producer changes causing any `other` cell require separate explanation and a
new measured baseline; do not silently expand scope.

Execute may run the full authorized synthetic regression set once its own
encode/K1 authorization is in force (the worker ran the restricted selection):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_l0_empty_shell.py parser/tests/test_name_drop_guard.py parser/tests/test_build_wiring.py --basetemp output/scratch-34/tests-p2b
```
