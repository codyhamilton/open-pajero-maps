# Brief: 31 -- Rebuild #4 (assembly only): KICKOFF ONLY

Consumer: implementation worker (fresh agent). Owned paths: none in the repo (writes
`/tmp/wp1-unit31-logs/`, overwrites `output/ALLDATA.KWI`, `output/manifest.json`, `output/report.json`).
Do not edit code. Depends on: 28, 29, 30 committed and pushed (`git log` confirms all three).
Runs alongside: nothing.

## Why assembly only
28 changes the reader only; 29 (division/trim) and 30 (mfde idx10) act in `build_alldata.py`/`synth.py`,
i.e. after extraction. `output/spool` from rebuild #3 (2026-09-19, ALLDATA sha256 `16329332...a7e8d8`) is
still valid for them, so skip the ~34 min extraction. Do NOT `rm -rf output/`.

## Steps
1. `.venv-rp/bin/python -m pytest parser/tests -q` passes on the committed tree.
2. Preflight: `output/spool` present with all `level_*.idx`; copy `output/report.json` to
   `/tmp/wp1-unit31-prior-report.json` and record old sha256; `df -h /home` >= 3 GB free
   (new KWI ~1.4 GB written over the old one; stop if not).
3. Start: `nohup /usr/bin/time -v .venv-rp/bin/python parser/build_alldata.py > /tmp/wp1-unit31-logs/build.out.log 2> /tmp/wp1-unit31-logs/build.time.log &`
   (expected ~9-10 min, ~6.6 GB RSS). Check `pgrep -f build_alldata.py` once and end the turn.
   Do not poll.
## Report back
PID, log paths, old sha256, disk numbers, commit SHAs of 28/29/30.
