#!/bin/bash
# Plan 41 P1: full-AU encode wall bench, -j4, 3 runs per commit, throwaway worktrees. Discs deleted after sha.
cd /home/codyh/workspace/open-pajero-maps-14-completeness
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
CUR=$PWD; PYA=$CUR/.venv-rp/bin/python
H="$PYA -B $CUR/parser/tools/run_heavy_python.py"
G=docs/plans/04-c-core-orchestration/triage/l0_empty_slot/phase2_gates.py
S=$CUR/output/scratch-41/bench
SP=/home/codyh/workspace/open-pajero-maps/output/extract_timing/spool
A013=013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04
A4ed=4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72
A2ee=2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae
A4e6=4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448
HEADC=$(git rev-parse --short=7 HEAD)
step(){ n=$1; shift; echo "== $n $(date +%T)"; $H --log $S/runs/$n.json "$@"; echo "rc $n $?"; }
step before -- $PYA -B $G snapshot --out $S/protected_before.json
for pair in 9269ebb:$A013 33006aa:$A013 d35b565:$A4ed a890662:$A4ed ecfae1c:$A2ee 5182c83:$A4e6 $HEADC:$A4e6; do
  c=${pair%%:*}; exp=${pair#*:}
  W=/home/codyh/workspace/open-pajero-maps-41-$c
  [ -d $W ] || git worktree add -q --detach $W $c
  echo "WT $c $(git -C $W rev-parse HEAD)"
  mkdir -p $S/$c/warm
  step ${c}_warm_perth --cwd $W -- $PYA -B parser/build_alldata.py --spool $SP --fixture perth --out $S/$c/warm/ALLDATA.KWI -j 4
  step ${c}_warm_perth_sha -- $PYA -B $G sha --path $S/$c/warm/ALLDATA.KWI --out $S/$c/sha_perth.json
  for r in 1 2 3; do
    mkdir -p $S/$c/r$r
    step ${c}_r$r --cwd $W -- $PYA -B parser/build_alldata.py --spool $SP --out $S/$c/r$r/ALLDATA.KWI -j 4 > $S/$c/r$r/build.log 2>&1
    echo "rc_build ${c}_r$r $(tail -n 1 $S/$c/r$r/build.log | cut -c1-80)"
    step ${c}_r${r}_sha -- $PYA -B $G sha --path $S/$c/r$r/ALLDATA.KWI --expected $exp --out $S/$c/sha_r$r.json
    rm -f $S/$c/r$r/ALLDATA.KWI
  done
  rm -f $S/$c/warm/ALLDATA.KWI
done
step after -- $PYA -B $G snapshot --against $S/protected_before.json --out $S/protected_after.json
echo "ALLDONE $(date +%T)"
