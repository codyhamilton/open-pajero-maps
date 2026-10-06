#!/bin/bash
# Plan 41 P1 mechanism: call-timer profile (throwaway instrumented worktrees, bytes unchanged) full-AU -j4.
cd /home/codyh/workspace/open-pajero-maps-14-completeness
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
CUR=$PWD; PYA=$CUR/.venv-rp/bin/python
H="$PYA -B $CUR/parser/tools/run_heavy_python.py"
G=docs/plans/04-c-core-orchestration/triage/l0_empty_slot/phase2_gates.py
S=$CUR/output/scratch-41/prof; SP=/home/codyh/workspace/open-pajero-maps/output/extract_timing/spool
step(){ n=$1; shift; echo "== $n $(date +%T)"; $H --log $S/runs/$n.json "$@"; echo "rc $n $?"; }
mkdir -p $S/runs
for pair in pre:013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04 head:4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448; do
  n=${pair%%:*}; exp=${pair#*:}; W=/home/codyh/workspace/open-pajero-maps-41-prof-$n
  mkdir -p $S/$n/pf; rm -f $S/$n/pf/*
  step prof_$n --cwd $W -- env KW_PROF_DIR=$S/$n/pf $PYA -B parser/build_alldata.py --spool $SP --out $S/$n/ALLDATA.KWI --bench $S/$n/bench.json -j 4 > $S/$n/build.log 2>&1
  step prof_${n}_sha -- $PYA -B $G sha --path $S/$n/ALLDATA.KWI --expected $exp --out $S/$n/sha.json
  rm -f $S/$n/ALLDATA.KWI
done
echo "ALLDONE $(date +%T)"
