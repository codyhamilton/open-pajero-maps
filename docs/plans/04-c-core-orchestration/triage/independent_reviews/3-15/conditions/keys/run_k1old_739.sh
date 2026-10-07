#!/bin/bash
# Plan 47 P1: K1 built at 1cf40f8 on 013586b5, dump completeness, -j4.
set -uo pipefail
M=/home/codyh/workspace/open-pajero-maps-14-completeness
W=/home/codyh/workspace/open-pajero-maps-47-k1old
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/home/codyh/workspace/open-pajero-maps/output/scratch-47/tmp
S=/home/codyh/workspace/open-pajero-maps/output/scratch-47
mkdir -p "$TMPDIR" "$S/runs" "$S/fresh_dump_311"
PY=$M/.venv-rp/bin/python
H="$PY -B $M/parser/tools/run_heavy_python.py"
cd "$W" && echo "W $(git rev-parse HEAD)"
# Disc sha before
sha256sum $M/output/scratch-3-11/G_new/ALLDATA.KWI | tee $S/disc_sha_013586b5.txt
$H --cwd "$W" --log $S/runs/k1old_739.json -- \
  $PY -B parser/tools/quantisation_roundtrip.py \
  --disc $M/output/scratch-3-11/G_new/ALLDATA.KWI \
  --spool $M/output/extract_timing/spool \
  -j 4 --engine c \
  --out $S/k1old_739.json \
  --dump-failures $S/fresh_dump_311 \
  --dump-kinds completeness
echo "rc $?"
sha256sum $M/output/scratch-3-11/G_new/ALLDATA.KWI | tee -a $S/disc_sha_013586b5.txt
echo K1_739_DONE
