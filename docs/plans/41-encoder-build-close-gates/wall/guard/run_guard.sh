#!/bin/bash
# Plan 41 P1 continuation: guard fix (c82f92e) gate cycle + post-fix EO profile. Serial, heavy wrapper. Waits for plan 39 P3.
M=/home/codyh/workspace/open-pajero-maps-14-completeness; cd $M
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
while ! grep -q P3DONE output/scratch-39/p3/run.log 2>/dev/null; do sleep 10; done
PYA=$M/.venv-rp/bin/python; H="$PYA -B $M/parser/tools/run_heavy_python.py"
G=docs/plans/04-c-core-orchestration/triage/l0_empty_slot/phase2_gates.py
S=$M/output/scratch-41/guard; SP=/home/codyh/workspace/open-pajero-maps/output/extract_timing/spool
W=/home/codyh/workspace/open-pajero-maps-41-guard; WP=/home/codyh/workspace/open-pajero-maps-41-prof-guard
A4e6=4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448
P04=04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728
step(){ nm=$1; shift; echo "== $nm $(date +%T)"; $H --log $S/runs/$nm.json "$@"; echo "rc $nm $?"; }
mkdir -p $S/runs
echo "W $(git -C $W rev-parse HEAD)"
step before -- $PYA -B $G snapshot --out $S/protected_before.json
step equiv --cwd $W -- $PYA -B $S/equiv.py $SP $S/equiv.json > $S/equiv.log 2>&1
for pj in 1 4; do
  mkdir -p $S/perth_j$pj
  step perth_j$pj --cwd $W -- $PYA -B parser/build_alldata.py --spool $SP --fixture perth --out $S/perth_j$pj/ALLDATA.KWI --bench $S/perth_j$pj/bench.json -j $pj > $S/perth_j$pj/build.log 2>&1
  step perth_j${pj}_sha -- $PYA -B $G sha --path $S/perth_j$pj/ALLDATA.KWI --expected $P04 --out $S/perth_j$pj/sha.json
done
for r in 1 2 3; do
  mkdir -p $S/r$r
  step r$r --cwd $W -- $PYA -B parser/build_alldata.py --spool $SP --out $S/r$r/ALLDATA.KWI --bench $S/r$r/bench.json -j 4 > $S/r$r/build.log 2>&1
  step r${r}_sha -- $PYA -B $G sha --path $S/r$r/ALLDATA.KWI --expected $A4e6 --out $S/r$r/sha.json
  rm -f $S/r$r/ALLDATA.KWI
done
mkdir -p $S/prof/pf; rm -f $S/prof/pf/*
step prof --cwd $WP -- env KW_PROF_DIR=$S/prof/pf $PYA -B parser/build_alldata.py --spool $SP --out $S/prof/ALLDATA.KWI --bench $S/prof/bench.json -j 4 > $S/prof/build.log 2>&1
step prof_sha -- $PYA -B $G sha --path $S/prof/ALLDATA.KWI --expected $A4e6 --out $S/prof/sha.json
rm -f $S/prof/ALLDATA.KWI
export TMPDIR=$S/suite_tmp; rm -rf "$TMPDIR"; mkdir -p "$TMPDIR"
step suite --cwd $W -- $PYA -B -m pytest -q -p no:cacheprovider --basetemp="$TMPDIR/pt" parser/tests > $S/pytest.log 2>&1
tail -3 $S/pytest.log
step after -- $PYA -B $G snapshot --against $S/protected_before.json --out $S/protected_after.json
echo "GUARDDONE $(date +%T)"
