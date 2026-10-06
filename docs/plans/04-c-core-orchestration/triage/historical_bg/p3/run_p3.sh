#!/bin/bash
# Plan 39 P3: window builds at b7c7c42 (87a01b14 producer) over L0 [1414,1890)x[274,750), pinned spool vs CF spool (minus source 65623). Serial, heavy wrapper, -j4.
W=/home/codyh/workspace/open-pajero-maps-39-b7c7c42
M=/home/codyh/workspace/open-pajero-maps-14-completeness
cd $M; export PYTHONDONTWRITEBYTECODE=1 TMPDIR=$M/output/scratch-39/tmp
while ! grep -q ROWSDONE output/scratch-39/rows/run.log; do sleep 10; done
PY=$M/.venv-rp/bin/python; H="$PY -B parser/tools/run_heavy_python.py"; D=$M/output/scratch-39/p3
for v in ctl cf; do
  sp=output/extract_timing/spool; [ $v = cf ] && sp=output/scratch-39/p3/spool_cf65623
  mkdir -p $D/$v
  $H --log $D/run_$v.json --cwd $W -- $PY -B parser/build_alldata.py --spool $W/$sp --out $D/$v/ALLDATA.KWI -j 4 --window 0 1414 274 1890 750 --frame-dump $D/$v/frames; echo "rc $v $?"
done
echo P3DONE
