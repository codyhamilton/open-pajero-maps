# Guarded Execute commands — Phase 1

Run from the repository root, in this order. The wrapper acquires
`output/.heavy.lock`; do not add `--no-flock`. Probes reject execution without
the wrapper and held lock. Inputs are read-only. Each G probe streams and
verifies the complete fixed pin before reading indexes and frames. R's pin
is cited from plan 29, not remeasured.

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/g_successor.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/l0_empty_slot/frame_witness.py probe --disc g_successor
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/g_historical.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/l0_empty_slot/frame_witness.py probe --disc g_historical
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/r.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/l0_empty_slot/frame_witness.py probe --disc r
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/spool.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/l0_empty_slot/frame_witness.py probe --spool output/extract_timing/spool
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/publish.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/l0_empty_slot/frame_witness.py publish
```

Expected outputs: `witnesses/g_successor.json`, `g_historical.json`, `r.json`,
`spool.json`, `summary.json`, and the generated `phase1_note.md`. Publish reads
only JSON evidence and existing parser source. It replays every index lookup,
frame classification and retained spool source before writing the summary.
`byte_pool` stores deduplicated absolute extents (offset, length, hex, sha256);
`byte_ref` resolves into that pool. Every cell retains its complete index path.
The note lists every additional G-frame/R-empty cell as a Phase 2 residual.

The disc defaults are `output/scratch-29/G_new/ALLDATA.KWI` (successor),
`output/scratch-14/G_new/ALLDATA.KWI` (historical), and
`/run/media/codyh/464210-8480/ALLDATA.KWI` (R). If Execute needs a different mount
or an equivalent copy, append `--path <path>` to that disc probe; G pins remain
fixed. Any unexpected R frame is decoded and retained by its probe; publish
refuses the expected-empty Phase 1 verdict for that drift.

Spool scan reads only level 0, streams all index rows and reads bounded records
for own cells or background routing. E1/E2 use same-level sources. Empty source
cells, pre-guard name identities, background edge/interior source shapes and
absolute source index/data offsets are retained. Per-frame source relationships
are parent-cell assembly inputs before filtering, division and trimming; the
Phase 2 investigation still needs to prove emitted record identity and cause.
The isolated E1 routing build writes only `output/scratch-34/e1_routing.so` and
its hash, using the existing `_e1.c` rather than rebuilding the parser library.

Synthetic verification only:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_l0_frame_witness.py --basetemp output/scratch-34/tests
```

Execute must inspect nonzero exits and wrapper memory logs. Pin mismatch,
malformed/truncated records, lookup failure, incomplete census, payload proof
drift, or source-layout/routing drift cannot be published as absence or parity.
No protected input is modified, and no fix, O03 reseat, K1 run or Phase 3 close
is part of these commands.
