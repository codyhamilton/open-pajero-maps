# Brief: 32b -- Rebuild #5 (assembly only): KICKOFF ONLY

Consumer: implementation worker (fresh agent). Owned paths: none in the repo (writes
`/tmp/wp1-unit32-logs/`, overwrites `output/ALLDATA.KWI`, `output/manifest.json`, `output/report.json`).
Do not edit code. Depends on: 32 committed and pushed (`git log`). Runs alongside: nothing.

## Why assembly only
Brief 32 changes `divide.py`/`build_alldata.py`, i.e. after extraction; `output/spool` is unchanged and valid.
Do NOT `rm -rf output/` or `output/spool`.

## Steps
1. `.venv-rp/bin/python -m pytest parser/tests -q` passes on the committed tree.
2. Preflight: `output/spool` has all `level_*.idx`; `mkdir -p /tmp/wp1-unit32-logs`; copy `output/report.json`
   to `/tmp/wp1-unit32-prior-report.json`; record old sha256 (`ed2d37ec...cb339`); `df -h /home` >= 3 GB free.
3. Start: `nohup /usr/bin/time -v .venv-rp/bin/python parser/build_alldata.py > /tmp/wp1-unit32-logs/build.out.log 2> /tmp/wp1-unit32-logs/build.time.log &`
   (~11 min, ~6.8 GB RSS; the L0 halo adds some encode time). `pgrep -f build_alldata.py` once, end the turn.
   Do not poll.
## Report back
PID, log paths, old sha256, disk numbers, commit SHA of 32.
