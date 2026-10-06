#!/bin/bash
# Plan 43 P2 (R-G8-4-a/b, R-G8-2-f). Serial under the heavy lock (run_heavy_python). Worktrees: 1cf40f8 (K1 with the
# pre plan 14 completeness rule) and ac1a64d (3-17's commit: k1_triage/dump_io unchanged since f3def00, zero-row rejection).
set -uo pipefail
M=/home/codyh/workspace/open-pajero-maps-14-completeness; S=/home/codyh/workspace/open-pajero-maps/output/scratch-43
WK=/home/codyh/workspace/open-pajero-maps-43-k1old; WC=/home/codyh/workspace/open-pajero-maps-43-cli317
C=$M/docs/plans/04-c-core-orchestration/triage/independent_reviews/3-17/conditions
export PYTHONDONTWRITEBYTECODE=1 TMPDIR=$S/tmp; mkdir -p $TMPDIR $S/runs $S/p2
PY=$M/.venv-rp/bin/python; H="$PY -B $M/parser/tools/run_heavy_python.py"; R=$S/rules
step(){ nm=$1; cwd=$2; shift 2; echo "== $nm $(date +%T)"; $H --cwd $cwd --log $S/runs/$nm.json -- "$@" > $S/p2/$nm.stdout 2> $S/p2/$nm.stderr; rc=$?; echo "rc $nm $rc" | tee $S/p2/$nm.rc; }
cd $M
for w in "$WK 1cf40f8" "$WC ac1a64d"; do set -- $w; [ -d $1 ] || { git worktree add -q --detach $1 $2 && ln -s /home/codyh/workspace/open-pajero-maps/output $1/output; }; echo "$1 $(git -C $1 rev-parse HEAD)"; done
# R-G8-4-a: forced-zero dump (unchanged dump_join) and completeness-only classify, current CLI and 3-17-era CLI
rm -rf $S/p2/dump_forced $S/p2/cls_*
step join_forced $M $PY -B parser/tools/dump_join.py --mode other_mechanism --src $M/output/scratch-14/dump_raw --side $S/side_forced.tsv --dst $S/p2/dump_forced --window-rows 25
step cls_completeness_cur $M $PY -B parser/tools/k1_triage.py classify --dump $S/p2/dump_forced --rules $R/rules_completeness_cur.json --out $S/p2/cls_completeness_cur
step cls_completeness_at317 $WC $PY -B parser/tools/k1_triage.py classify --dump $S/p2/dump_forced --rules $R/rules_completeness_at317.json --out $S/p2/cls_completeness_at317
# K1 at 1cf40f8 on 4ed9cd80 with all five kinds dumped (name_anchor row; zero-row kinds; completeness regenerability check)
rm -rf $S/p2/dump_k1old_all
step k1old_all $WK $PY -B parser/tools/quantisation_roundtrip.py --disc $M/output/scratch-14/G_new/ALLDATA.KWI --spool $M/output/extract_timing/spool -j 4 --engine c --out $S/p2/k1old_all.json --dump-failures $S/p2/dump_k1old_all --dump-kinds background,background_boundary,interior_cover,name_anchor,completeness
sha256sum $M/output/scratch-14/G_new/ALLDATA.KWI $S/p2/dump_k1old_all/*.bin $M/output/scratch-14/dump_raw/completeness.bin > $S/p2/k1old_all.sha256
# R-G8-4-b: full CLI on a dump with zero-row kinds: 3-17-era CLI (unchanged at 3-17) and current CLI
step cli_full_at317 $WC $PY -B parser/tools/k1_triage.py classify --dump $S/p2/dump_k1old_all --rules $R/rules_all_at317.json --out $S/p2/cls_full_at317
step cli_full_cur $M $PY -B parser/tools/k1_triage.py classify --dump $S/p2/dump_k1old_all --rules $R/rules_all_cur.json --out $S/p2/cls_full_cur
# S2e: name_anchor kind-only view (manifest projection, same bytes)
rm -rf $S/p2/view_name_anchor; mkdir -p $S/p2/view_name_anchor
$PY -B -c "import json,sys; m=json.load(open('$S/p2/dump_k1old_all/dump_manifest.json')); m['kinds']={'name_anchor': m['kinds']['name_anchor']}; json.dump(m, open('$S/p2/view_name_anchor/dump_manifest.json','w'), indent=1)"
ln -s $S/p2/dump_k1old_all/name_anchor.bin $S/p2/view_name_anchor/name_anchor.bin
step cls_name_anchor_at317 $WC $PY -B parser/tools/k1_triage.py classify --dump $S/p2/view_name_anchor --rules $R/rules_name_anchor_at317.json --out $S/p2/cls_name_anchor_at317
step cls_name_anchor_cur $M $PY -B parser/tools/k1_triage.py classify --dump $S/p2/view_name_anchor --rules $R/rules_name_anchor_cur.json --out $S/p2/cls_name_anchor_cur
for w in $WK $WC; do rm -f $w/output && git worktree remove $w; done
echo P2DONE
