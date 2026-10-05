# Phase 1 presence witness handoff

The probe/publish implementation and seven-row identity census are ready for
Execute. Presence verification is **pending**: the current TSV/JSON name all
seven rows as exceptions with missing successor, historical and R probes.
Their unknown type counts are blank/null, never zero. Phase 1 is not verified.

The hashed plan-28 discriminators, mechanism predicates, R-contribution table,
reconciliation note, and available hash-matching attribution proofs reaffirm
O04/spool for dump_rows 138, 236, 282, 284, 317, 496, 563. The penultimate strata
are emit-piece {138, 284, 496} and demand-removed {236, 282, 317, 563}.
Retained R-zero assertions are labelled separately from new presence proof.
Saved scratch-14 frame summaries were inspected as light evidence; they lack
the retained index/frame bytes needed by this publisher's replay contract, so
they were not substituted for the guarded probes.

G probes reuse plan 30's bounded pread adapter, streamed full-file SHA256 and
`disc_rows` count control. All three discs use plan 29's hardened `index_lookup`
from its closed-out `triage/name_anchor/` home. Each resolved leaf is decoded
with the existing `cell_local_2-01.py::decode_slot_shapes`; offsets, lengths,
frame SHA256, bounds, coordinate range, polygon type census, raw frame bytes,
and retained index bytes support offline replay. Empty slots require replayed
index sentinels. Lookup/decode failures and outside-coverage labels cannot
prove absence. Background directories and basic subframe extents are validated
before the permissive parcel decoder can turn malformed data into zero shapes.

The presence contract counts class-2 polygons with at least three decoded
coordinates and the demanded type in indexed covering frames. A zero covering
frame count proves cell-local absence; any positive count is an exception,
including potential sparse-tile aliases, and requires investigation.

G pins are fully streamed and verified; file identity is checked before/after
hashing and probing. R cites the complete historical pin in committed
`triage/name_anchor/witnesses/r.json`; it is not rehashed. Per-read and aggregate
retained probe evidence bounds are 64 MiB. Probe JSONs belong in scratch-33.
Publisher checks pins, all seven native keys, source/reader hashes, decoded
counts and byte replay; a changed source/reader requires fresh probes.

## Execute commands

Run sequentially from `/home/codyh/workspace/open-pajero-maps-14-completeness`.
The wrapper itself obtains `flock output/.heavy.lock` and memory accounting.
These disc commands were **not run by the unit worker**.

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-33/runs/g_successor.json -- .venv-rp/bin/python -B docs/plans/33-o04-spool-successor-seven/presence_witness.py --disc g_successor --path output/scratch-29/G_new/ALLDATA.KWI --output output/scratch-33/g_successor.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-33/runs/g_historical.json -- .venv-rp/bin/python -B docs/plans/33-o04-spool-successor-seven/presence_witness.py --disc g_historical --path output/scratch-14/G_new/ALLDATA.KWI --output output/scratch-33/g_historical.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-33/runs/r.json -- .venv-rp/bin/python -B docs/plans/33-o04-spool-successor-seven/presence_witness.py --disc r --path /run/media/codyh/464210-8480/ALLDATA.KWI --output output/scratch-33/r.json
.venv-rp/bin/python -B docs/plans/33-o04-spool-successor-seven/presence_witness.py publish --g-successor output/scratch-33/g_successor.json --g-historical output/scratch-33/g_historical.json --r output/scratch-33/r.json
```

Probe exit 2 means unresolved evidence was written; inspect the row reason.
Publish exit 2 means exceptions were written and Phase 1 remains unverified.
All commands must exit 0 and the published JSON must show
`absence_proven_count: 7`, `exceptions: []`, `phase1_verified: true` before
Execute records the phase outcome. Review the seven per-row byte/decode proofs.

## Synthetic verification

```bash
.venv-rp/bin/python -B -m pytest -q parser/tests/test_o04_presence_witness.py --basetemp output/scratch-33/tests
```

Only this test file is in scope. Changes remain uncommitted. No disc, R-disc or
spool was opened by the worker; no spool edit, disposition, completeness reseat
or plan-04 Phase-3 close is included.

## Execute measured result (2026-10-06, guarded)

Run chain `output/scratch-33/run_p1.{sh,log}`; g_successor, g_historical, r and publish each exit 0 under `run_heavy_python.py` (peaks 1.60 GB / 94 MB / 40 MB / 48 MB cgroup). G full pins verified by the probes; R pin `8c2d2027…` cited from plan 29.

Result: **7/7 `absence-proven`, 0 exceptions.** For every row the demanded-type count in the target cell is 0 on G successor `2ee3456a…`, G historical `4ed9cd80…` and R, each from a **resolved** slot with frame bytes (offset, length, hex, sha256) and decoded shape-type counts. No row relies on an empty slot or a lookup failure. Probe JSON sha256: g_successor `d3f23cbf…`, g_historical `9831eeff…`, r `43ff796b…`.
