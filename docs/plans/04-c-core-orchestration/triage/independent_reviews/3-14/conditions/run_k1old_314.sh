#!/bin/bash
# Plan 43 P1 R-G8-1-c: K1 built at 1cf40f8 (pre plan 14 completeness rule) on 4ed9cd80, dump off, -j4. Heavy wrapper + lock.
set -uo pipefail
M=/home/codyh/workspace/open-pajero-maps-14-completeness; W=/home/codyh/workspace/open-pajero-maps-43-k1old
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/home/codyh/workspace/open-pajero-maps/output/scratch-43/tmp
S=/home/codyh/workspace/open-pajero-maps/output/scratch-43; mkdir -p $TMPDIR $S/runs
PY=$M/.venv-rp/bin/python; H="$PY -B $M/parser/tools/run_heavy_python.py"
cd $W && echo "W $(git rev-parse HEAD)"
$H --cwd $W --log $S/runs/k1old_314.json -- $PY -B parser/tools/quantisation_roundtrip.py --disc $M/output/scratch-14/G_new/ALLDATA.KWI --spool $M/output/extract_timing/spool -j 4 --engine c --out $S/k1old_314.json
echo "rc $?"
sha256sum $M/output/scratch-14/G_new/ALLDATA.KWI > $S/k1old_314.disc_sha.txt
echo K1OLDDONE
