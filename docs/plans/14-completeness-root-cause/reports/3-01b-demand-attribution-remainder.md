# 3-01b — Demand attribution remainder (kickoff split of 3-01)

Status: **done**. The Execute orchestrator ran it directly with the committed `triage/demand_attribution_3-01.py`, unedited.

## Against the brief

- 3-01's 25-key timing projected 601.5 s for 776 keys, so the remaining 750 keys ran in two windows through `run_heavy_python.py`:
  - W1: dump_rows 25–399 except 335, 374 keys. 128.8 s wall, `memory.peak` 4184 MiB. Log `output/scratch-14/runs/attribution_w1.json`.
  - W2: dump_rows 400–775, 376 keys. 81.7 s wall, 1381 MiB. Log `attribution_w2.json`.
- Each window attributed every selected key. `w{1,2}.log` show 374 and 376 `error=None` lines. The script's `publish` merged all 776 proofs into the regenerated `triage/demand_attribution_3-01.{tsv,md}`.
- Result (`output/scratch-14/attribution/summary.json`):
  - 776/776 keys attributed; 799 distinct demanders.
  - First-matching branch: a = 1 (dump_row 656), b = 797, c = 1 (dump_row 335).
  - Error rows: 0. C/Python checker disagreements: 0. Mirror/C disagreements: 0.
  - **Every demander is unrepresentable** (production C records 0). `all_demanders_unrepresentable` = 776. Representable-demand exceptions: **none**.
- 3-03 prediction: live completeness failing goes 776 → **0** and `checked` stays unchanged. Every 2-01, 2-02, 335, and 765 key leaves the failing set.
- dump_row 765 is demanded by `L0:home(1307,1755):ordinal=1` via branch (b), its Phase 1 source, and is unrepresentable.
- Protected shas are unchanged: `output/scratch-14/G_new/ALLDATA.KWI` `4ed9cd801bdd7099…`, `output/scratch-3-11/G_new/ALLDATA.KWI` `013586b58490873f…`.

## Departures

- The first attempt of each window exited 126 because the wrapper argv lacked the interpreter. It was re-run as `run_heavy_python.py … -- .venv-rp/bin/python -B <script>`.

## Known problems

- `demand_attribution_3-01.py` exits 1 after `publish` when `--keys` is a long list. The per-run summary filename is built from the whole key list (`OSError: [Errno 36] File name too long`, `w1.log:377–393`). Proofs and the published TSV/note are written before the failure and are complete. Wall times are in the wrapper logs. The fix belongs to whoever next edits the script: hash or truncate the key list in the filename. It is not fixed here because the brief froze the script.
