# 1-01 fingerprint census handoff

Status: light implementation and census complete; ready for Execute's guarded disc verification and merge. Changes are uncommitted as instructed. Phase 1's successor presence outcome cannot be claimed until those commands complete.

The census validates exhaustive 342-key membership and plan-28 joins, proof/witness identity, retained G counts, R polygon/vertex/branch counts and the existing spool mechanism. It hashes every data input and computes signatures from decoded coordinates. The synthetic test command is:

```bash
.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_parity_fingerprint.py --basetemp output/scratch-30/tests
```

Tests cover translation/scale normalisation while preserving start/winding, deterministic full census and hashes, wrong spans, a third same-span/13-vertex signature, broken joins/witness identity, populated successor merge, rejection of pin/hash/key/dump/count/control corruption without changing outputs, capped pread and the disc CLI alias. No real disc/spool is a test input. Final result: **22 passed in 3.48s**. The light census command also exits 0 and generates the measured evidence below.

Measured evidence: **341 × 288 + 1 × 321 (246)**; rules **O01 340 + O05 2**; signatures **T1 191 + T2 150**; **0 template exceptions**; all 341 template spans meet 1e-9° tolerance and all have branch c. The type-321 row remains separate, with 11 matching polygons and one branch-a cell-local polygon. Geographic labels are **west 85 / east 86 / south_offshore 129 / other 42**, under the explicit midpoint/window rule in `phase1_note.md`. The input manifest contains 688 SHA256 entries.

Departure from Ground wording: both computed templates have positive signed doubled area +2 in normalised (longitude x, latitude y), so their winding is the same; start corners differ. The note records this measured correction. There are no implementation departures from the brief. Historical zero counts remain explicitly retained/pending control, and successor count/hash columns remain blank under the binding prohibition on worker disc reads.

Remaining actions for Execute, sequentially from the repository root:

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/g_successor.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/source_parity/fingerprint.py --disc output/scratch-29/G_new/ALLDATA.KWI --pin successor --output output/scratch-30/g_successor.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/g_historical.json -- .venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/source_parity/fingerprint.py --disc output/scratch-14/G_new/ALLDATA.KWI --pin historical --output output/scratch-30/g_historical.json
.venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/source_parity/fingerprint.py merge --successor-json output/scratch-30/g_successor.json --historical-json output/scratch-30/g_historical.json
```

Both heavy commands stream the pin check and perform bounded per-cell pread/decode for only the 342 keys. Historical disagreement fails before writing a result; merge also requires exact historical control equality and exact key/pin/hash provenance. Wrapper logs capture argv and memory.peak under scratch-30.

Execute must apply the append-only census wording corrections outside this unit's ownership and commit the result. No ALLDATA.KWI, R disc or spool was opened by this worker. No protected or concurrent-worker surface was touched or run. No disposition was assigned. Known limitation: guarded decoder execution on the actual two G discs is deliberately untested here; the listed probes and historical control settle that before Phase 1 closes.
