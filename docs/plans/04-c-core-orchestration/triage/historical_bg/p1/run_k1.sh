#!/bin/bash
# Plan 39 P1/P2 K1 runs at HEAD K1 (fixed checker + spool; vary disc only). Under the heavy wrapper (flock).
cd /home/codyh/workspace/open-pajero-maps-14-completeness
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/home/codyh/workspace/open-pajero-maps-14-completeness/output/scratch-39/tmp
mkdir -p $TMPDIR
PY=.venv-rp/bin/python; H="$PY -B parser/tools/run_heavy_python.py"; S=output/scratch-39; SP=output/extract_timing/spool
K="parser/tools/quantisation_roundtrip.py"
step(){ nm=$1; shift; echo "== $nm $(date +%T)"; $H --log $S/runs/$nm.json -- "$@"; echo "rc $nm $?"; }
mkdir -p $S/runs
echo "HEAD $(git rev-parse HEAD)"
step k1_pre311 $PY -B $K --disc output/scratch-36/G_pre311/ALLDATA.KWI --spool $SP -j 6 --engine c --out $S/k1_pre311.json
step k1_311_dump $PY -B $K --disc output/scratch-3-11/G_new/ALLDATA.KWI --spool $SP -j 6 --engine c --out $S/k1_311.json --dump-failures $S/dump_311 --dump-kinds background,background_boundary,interior_cover
step k1_314_dump $PY -B $K --disc output/scratch-14/G_new/ALLDATA.KWI --spool $SP -j 6 --engine c --out $S/k1_314.json --dump-failures $S/dump_314 --dump-kinds background,background_boundary,interior_cover
step k1_pre311_dump $PY -B $K --disc output/scratch-36/G_pre311/ALLDATA.KWI --spool $SP -j 6 --engine c --out $S/k1_pre311_d.json --dump-failures $S/dump_pre311 --dump-kinds background,background_boundary,interior_cover
du -sh $S/dump_* ; echo "K1DONE $(date +%T)"
