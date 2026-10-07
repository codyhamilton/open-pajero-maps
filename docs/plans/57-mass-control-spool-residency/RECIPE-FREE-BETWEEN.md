# Plan 57 Phase 3 — Free-between recipe (control → fresh scope → mass)

Standing: no R bump; do **not** auto-discharge plan 44 R-G5-4 residuals.
Wrapper takes `output/.heavy.lock` itself — do **not** wrap with an outer `flock` (deadlocks).

## Recipe (fresh process scopes)

1. **Finish control** under wrapper:
   ```bash
   .venv-rp/bin/python -B parser/tools/run_heavy_python.py \
     --log output/scratch-57/runs/control.json -- \
     .venv-rp/bin/python -B \
     docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive/control.py \
     -n 200 --seed 44 --r-cap 8 --cache-clear-every 50 --cache-max-cells 4096
   ```
2. **Exit the process** (wrapper scope ends). In-process spool caches die with that interpreter — a follow-up `clear_spool_caches()` in a *new* Python cannot clear the exited process (Codex review note). Optional: sample MemAvailable / run `gc` only as host hygiene. Plan 56 inter-phase samples used `clear_spool_caches+gc` between separate wrapper scopes; MemAvailable stayed ~20–21 GiB.
3. **Start mass** under a **fresh** `run_heavy_python.py` scope (new cgroup / new peak log):
   ```bash
   .venv-rp/bin/python -B parser/tools/run_heavy_python.py \
     --log output/scratch-57/runs/mass.json -- \
     .venv-rp/bin/python -B \
     docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive/mass_decide.py \
     --r 8 --cache-clear-every 50 --cache-max-cells 4096 \
     --resume-from <prior_decisions.tsv.gz> \
     --out <out.tsv.gz> --summary <summary.json>
   ```

## Same-process sequencing (discouraged)

If control and mass must share one interpreter: call `clear_spool_caches()` and drop large locals before mass; measure RSS delta. Prefer fresh wrapper scopes (above).

## Resume path

`--resume-from` skips leaf rows already present in a prior decisions TSV (row identity: level,ix,iy,shape,vert,code). Already-emitted rows are not rewritten. New rows use tip `mass_decide` decision function. Byte-identical for resumed rows vs prior snapshot is the honesty bar (Assumption 3).

## Plan 44 residuals

R-G5-4-a/b / still-outside@16 remain plan 44 product track. This recipe only bounds residency.
