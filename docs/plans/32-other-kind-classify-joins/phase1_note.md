# Successor failing-dump census

The fresh dump was produced by Execute, as recorded in [IMPLEMENTATION.md](IMPLEMENTATION.md), under `run_heavy_python.py` and `output/.heavy.lock`. This worker inspected only its manifest, small bins, K1 report, guard log, and the plan-29 control. No disc or spool was opened. The successor pin is inherited from the recorded run and [plan 29](../29-k1-name-anchor-failure.md), rather than newly measured by this worker:

`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`.

| Kind | Dump bytes | Manifest row size | Dump rows | K1 failing | Plan-29 successor failing |
| --- | ---: | ---: | ---: | ---: | ---: |
| interior_cover | 0 | 144 | 0 | 0 | 0 |
| name_anchor | 0 | 144 | 0 | 0 | 0 |
| background | 0 | 144 | 0 | 0 | 0 |
| background_boundary | 0 | 144 | 0 | 0 | 0 |

All four bins have SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Their exact native-key sets are empty, as are their native dump-row intervals `[0, 0)`. The observed branch is **`all_live_empty`**. The plan-29 failing-count control matches all four kinds; it is a control, while the fresh plan-32 dump is the census evidence.

The dump source is `output/scratch-32/dump/`. Evidence hashes:

| Evidence | SHA256 |
| --- | --- |
| `dump/dump_manifest.json` | `c29ed9f0bd2fb382729f7fba2d200c9ab3b514aca8154a27e4aaa34a59536839` |
| `k1_dump_report.json` | `ade63d88ec6b0cefb659e2ecff3db38cbb99e8e327666e0770b75529d19480dc` |
| `runs/k1_dump.json` | `4d3d893aedc3488ba5898768d8aef3de0a6a47731062975321ad7a24fa78d4ad` |
| [Plan-29 control](../04-c-core-orchestration/triage/name_anchor/witnesses/successor_k1_compare.json) | `d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b` |

The K1 report records six workers, PASS, 83.1 s wall time, and summed-PSS peak **7,478,057 kB**. The guard log records exit 0 and cgroup `memory.peak` **5,940,453,376 bytes**. These are different measurements; this plan does not use either to close the separate PSS gate. The generated census records the guard argv, source paths and hashes, workers, and both named memory measurements.

Completeness is excluded and remains owned by [plan 28](../28-phase1-per-rule-classify-recovery.md). Point kinds `range`, `step`, `road_node`, and `road_point` are `out_of_scope`, each with K1 failing 0. If a future report has a nonzero point-kind count, the tool names it in `carried_point_kinds`.

## Reproduction and handoff

From the repository root, Execute runs these sequentially. The wrapper supplies the heavy lock and memory accounting. No new K1 run is required:

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-32/runs/census.json -- .venv-rp/bin/python -B docs/plans/32-other-kind-classify-joins/census.py census
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-32/runs/publish.json -- .venv-rp/bin/python -B docs/plans/32-other-kind-classify-joins/census.py publish
```

The first command writes `census.tsv` and `census.json`. It validates integer row counts against manifest and K1 totals, captures provenance, and records plan-29 control pass/fail. A control failure is recorded with exit 1; malformed or inconsistent inputs return exit 2 before writing. Nonempty in-scope kinds produce `nonempty_kinds=[...]` with exact native dump-row intervals tied to hashed bins. That branch requires recovery before discharge.

The second command rehashes the source evidence and refuses stale/edited census data, nonempty kinds, or a failed control. Only the empty branch writes the four header-only assignment TSVs, with plan 28's native assignment columns. The empty native-key sets are recorded in `census.json` and the publish stdout. These are empty assignment stubs; no classifier run or `PARTITION OK` result is asserted.

The worker leaves the guarded commands to Execute as required by the brief. The generated census and assignment files must be included in Execute's evidence commit after both commands succeed. The worker's synthetic test is:

```sh
.venv-rp/bin/python -B -m pytest -q parser/tests/test_other_kind_census.py --basetemp output/scratch-32/tests
```

Phase 1 makes no OVERVIEW blocker-clear claim. No classify recovery, PSS synthesis, plan-04 Phase 3 closure, 3-90 rerun, or successor-disc modification is performed.
