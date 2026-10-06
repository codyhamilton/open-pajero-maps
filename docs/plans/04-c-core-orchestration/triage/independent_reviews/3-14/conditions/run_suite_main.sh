#!/bin/bash
# Plan 43 P1 R-G8-1-e: full parser/tests in the MAIN checkout (not a worktree) at master, under the heavy lock.
set -uo pipefail
M=/home/codyh/workspace/open-pajero-maps; S=$M/output/scratch-43
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=$M/output/tmp-agent; mkdir -p $TMPDIR $S/runs
cd $M && echo "MAIN $(git rev-parse HEAD) worktree-list-first=$(git worktree list | head -1)"; git rev-parse --git-dir
$M/.venv-rp/bin/python -B parser/tools/run_heavy_python.py --cwd $M --log $S/runs/suite_main.json -- $M/.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider -rfEsx parser/tests
echo "rc $?"; echo SUITEDONE
