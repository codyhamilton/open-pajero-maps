#!/bin/bash
# Plan 43 P2b: classify runs on the rebuilt dump_ext43 (build_ext.py). Full CLI (R-G8-4-b) and kind views (S2b/c/e),
# 3-17-era CLI (worktree ac1a64d) and current CLI. Under the heavy wrapper.
set -uo pipefail
M=/home/codyh/workspace/open-pajero-maps-14-completeness; S=/home/codyh/workspace/open-pajero-maps/output/scratch-43
WC=/home/codyh/workspace/open-pajero-maps-43-cli317; R=$S/rules; D=$S/p2/dump_ext43
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=$S/tmp
PY=$M/.venv-rp/bin/python; H="$PY -B $M/parser/tools/run_heavy_python.py"
step(){ nm=$1; cwd=$2; shift 2; echo "== $nm $(date +%T)"; $H --cwd $cwd --log $S/runs/$nm.json -- "$@" > $S/p2/$nm.stdout 2> $S/p2/$nm.stderr; rc=$?; echo "rc $nm $rc" | tee $S/p2/$nm.rc; }
cd $M; [ -d $WC ] || { git worktree add -q --detach $WC ac1a64d && ln -s /home/codyh/workspace/open-pajero-maps/output $WC/output; }
rm -rf $S/p2/x_* $S/p2/view_*
for k in completeness name_anchor; do
  mkdir -p $S/p2/view_$k
  $PY -B -c "import json; m=json.load(open('$D/dump_manifest.json')); m['kinds']={'$k': m['kinds']['$k']}; json.dump(m, open('$S/p2/view_$k/dump_manifest.json','w'), indent=1)"
  ln -s $D/$k.bin $S/p2/view_$k/$k.bin
done
for tag in at317 cur; do cwd=$M; [ $tag = at317 ] && cwd=$WC
  step x_full_$tag $cwd $PY -B parser/tools/k1_triage.py classify --dump $D --rules $R/rules_all_$tag.json --out $S/p2/x_full_$tag
  for k in completeness name_anchor; do
    step x_view_${k}_$tag $cwd $PY -B parser/tools/k1_triage.py classify --dump $S/p2/view_$k --rules $R/rules_${k}_$tag.json --out $S/p2/x_view_${k}_$tag
  done
done
rm -f $WC/output && git worktree remove $WC; echo P2BDONE
