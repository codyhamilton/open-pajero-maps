#!/bin/bash
# Plan 43 P1 R-G8-1-h: rebuild the finish_gates golden window l0_divided_trim_halo (golden.json window [1755,591,1756,592], half-open as build_alldata --window: one L0 cell)
# from its fixture spool at master; capture the TRIM lines (replaces the lost finish_gates.log) and byte-check the frames.
set -uo pipefail
M=/home/codyh/workspace/open-pajero-maps-14-completeness; S=/home/codyh/workspace/open-pajero-maps/output/scratch-43
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=$S/tmp; mkdir -p $TMPDIR $S/runs $S/golden
cd $M && echo "HEAD $(git rev-parse HEAD)"
PY=$M/.venv-rp/bin/python
$PY -B parser/tools/run_heavy_python.py --cwd $M --log $S/runs/golden_window.json -- $PY -B parser/build_alldata.py --spool output/goldens-3C/l0_divided_trim_halo/spool --levels 0 --window 0 1755 591 1756 592 -j 4 --out $S/golden/ALLDATA.KWI --frame-dump $S/golden/frames
echo "rc $?"
sha256sum $S/golden/frames.bin output/goldens-3C/l0_divided_trim_halo/frames.bin
cmp $S/golden/frames.bin output/goldens-3C/l0_divided_trim_halo/frames.bin && echo FRAMES_IDENTICAL
