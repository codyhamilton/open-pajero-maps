# Brief: 33b -- Rebuild #6 (assembly only): KICKOFF ONLY

Consumer: implementation worker (fresh agent). Writes `/tmp/wp1-unit33-logs/`, overwrites `output/ALLDATA.KWI`,
`output/manifest.json`, `output/report.json`. No code edits. Depends on: 33 committed and pushed.

Assembly only: `output/spool` is unchanged and valid. Do NOT `rm -rf output/` or `output/spool`.
## Steps
1. `.venv-rp/bin/python -m pytest parser/tests -q` passes on the committed tree.
2. Preflight: all `output/spool/level_*.idx` present; `mkdir -p /tmp/wp1-unit33-logs`; copy `output/report.json` to
   `/tmp/wp1-unit33-prior-report.json`; record old ALLDATA.KWI sha256 (`c978b840...c2c44`); `df -h /home` >= 3 GB.
3. Start (own session): `setsid nohup /usr/bin/time -v .venv-rp/bin/python parser/build_alldata.py > /tmp/wp1-unit33-logs/build.out.log 2> /tmp/wp1-unit33-logs/build.time.log &`
   (~17 min, ~6.8 GB RSS). Confirm liveness with `pgrep -f build_alldata.py` once; end the turn; do not poll.
## Report back
PID, log paths, old sha256, disk numbers, commit SHA of 33.
