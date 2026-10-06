#!/bin/bash
# Plan 39 P1 item 2: per-(block, cell row) K1 checked on 87a01b14 replay and 013586b5, via plan 36's k1_rows.py (unmodified K1). Serial under the heavy wrapper.
cd /home/codyh/workspace/open-pajero-maps-14-completeness
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=/home/codyh/workspace/open-pajero-maps-14-completeness/output/scratch-39/tmp
PY=.venv-rp/bin/python; H="$PY -B parser/tools/run_heavy_python.py"; S=output/scratch-39; SP=output/extract_timing/spool
KR=docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/k1_rows.py
$H --log $S/runs/rows_pre311.json -- $PY -B $KR run --disc output/scratch-36/G_pre311/ALLDATA.KWI --sha 87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862 --spool $SP --out $S/rows/rows-pre311.tsv --whole $S/k1_pre311.json -j 6; echo "rc1 $?"
$H --log $S/runs/rows_311.json -- $PY -B $KR run --disc output/scratch-3-11/G_new/ALLDATA.KWI --sha 013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04 --spool $SP --out $S/rows/rows-311.tsv --whole $S/k1_311.json -j 6; echo "rc2 $?"
$PY -B $KR compare --old $S/rows/rows-pre311.tsv --new $S/rows/rows-311.tsv --cells output/scratch-36/diff-3-11-au.cells.tsv --out $S/rows/k1-confine-3-11.json; echo "rc3 $?"
echo ROWSDONE
