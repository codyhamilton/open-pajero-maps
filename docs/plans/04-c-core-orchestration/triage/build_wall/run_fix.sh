#!/bin/bash
# Plan 41 P1: byte-identical fix candidate (eo_left prefilter), throwaway worktree. Also sha the two profile discs.
cd /home/codyh/workspace/open-pajero-maps-14-completeness
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
CUR=$PWD; PYA=$CUR/.venv-rp/bin/python
H="$PYA -B $CUR/parser/tools/run_heavy_python.py"
G=docs/plans/04-c-core-orchestration/triage/l0_empty_slot/phase2_gates.py
S=$CUR/output/scratch-41; SP=/home/codyh/workspace/open-pajero-maps/output/extract_timing/spool
W=/home/codyh/workspace/open-pajero-maps-41-fix
A4e6=4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448
P04=04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728
step(){ nm=$1; shift; echo "== $nm $(date +%T)"; $H --log $S/fix/runs/$nm.json "$@"; echo "rc $nm $?"; }
mkdir -p $S/fix/runs
step prof_pre_sha -- $PYA -B $G sha --path $S/prof/pre/ALLDATA.KWI --expected 013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04 --out $S/prof/pre/sha.json && rm -f $S/prof/pre/ALLDATA.KWI
step prof_head_sha -- $PYA -B $G sha --path $S/prof/head/ALLDATA.KWI --expected $A4e6 --out $S/prof/head/sha.json && rm -f $S/prof/head/ALLDATA.KWI
for pj in 1 4; do
  mkdir -p $S/fix/perth_j$pj
  step fix_perth_j$pj --cwd $W -- $PYA -B parser/build_alldata.py --spool $SP --fixture perth --out $S/fix/perth_j$pj/ALLDATA.KWI -j $pj > $S/fix/perth_j$pj/build.log 2>&1
  step fix_perth_j${pj}_sha -- $PYA -B $G sha --path $S/fix/perth_j$pj/ALLDATA.KWI --expected $P04 --out $S/fix/perth_j$pj/sha.json
done
for r in 1 2 3; do
  mkdir -p $S/fix/r$r
  step fix_r$r --cwd $W -- $PYA -B parser/build_alldata.py --spool $SP --out $S/fix/r$r/ALLDATA.KWI -j 4 > $S/fix/r$r/build.log 2>&1
  step fix_r${r}_sha -- $PYA -B $G sha --path $S/fix/r$r/ALLDATA.KWI --expected $A4e6 --out $S/fix/r$r/sha.json
  echo "shark r$r $?"; rm -f $S/fix/r$r/ALLDATA.KWI
done
echo "ALLDONE $(date +%T)"
