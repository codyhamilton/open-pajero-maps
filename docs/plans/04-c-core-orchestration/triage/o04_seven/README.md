# O04 seven-row presence witness and disposition

Lasting evidence for seven completeness rows: dump_row 138, 236, 282, 284,
317, 496 and 563 (record: `docs/plans/33-o04-spool-successor-seven.md`;
contract: `docs/design/presence-non-deviation-witness.md`).

- `presence_witness.py`
  - `--disc g_successor|g_historical|r` probes discs. These are heavy reads;
    run them under `parser/tools/run_heavy_python.py`.
  - `publish` turns the probe JSONs into `presence_witness.tsv` and `.json`.
- `disposition.py publish` is light. It reads only committed JSON and
  writes `disposition.tsv` and `.json`.
- Result: all seven rows are **proven-non-deviation**, with 0 conflict-open.
  For each row the demanded type count is 0 on G successor `2ee3456a…`,
  G historical `4ed9cd80…` and R `8c2d2027…`. K1 completeness on the
  successor: 1,800,514 checked / 0 failing (retained citation). The O04
  spool defect is kept as a spool-hygiene residual; the source is unchanged.

Reproduce from the repo root:

```bash
H=".venv-rp/bin/python -B parser/tools/run_heavy_python.py"
P=docs/plans/04-c-core-orchestration/triage/o04_seven/presence_witness.py
$H --log output/scratch-33/runs/g_successor.json -- .venv-rp/bin/python -B $P --disc g_successor --path output/scratch-29/G_new/ALLDATA.KWI --output output/scratch-33/g_successor.json
$H --log output/scratch-33/runs/g_historical.json -- .venv-rp/bin/python -B $P --disc g_historical --path output/scratch-14/G_new/ALLDATA.KWI --output output/scratch-33/g_historical.json
$H --log output/scratch-33/runs/r.json -- .venv-rp/bin/python -B $P --disc r --path /run/media/codyh/464210-8480/ALLDATA.KWI --output output/scratch-33/r.json
.venv-rp/bin/python -B $P publish --g-successor output/scratch-33/g_successor.json --g-historical output/scratch-33/g_historical.json --r output/scratch-33/r.json
.venv-rp/bin/python -B docs/plans/04-c-core-orchestration/triage/o04_seven/disposition.py publish
```

The retained probe JSONs record the tool hashes that were in force when
they ran. After these files were moved here, `presence_witness.py`'s own
hash changed (its `ROOT` depth), so `publish` over the old probes must be
preceded by fresh probes. `disposition.py publish` still reproduces the
committed outputs exactly. The `readers()` dependency on plan 30's
`fingerprint.py` must follow that file if plan 30 is closed out.
