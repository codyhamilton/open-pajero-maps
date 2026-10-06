#!/bin/bash
cd /home/codyh/workspace/open-pajero-maps-14-completeness
trap 'echo "FAILED at line $LINENO (exit $?) $(date +%T)"' ERR
set -euo pipefail
H=".venv-rp/bin/python -B parser/tools/run_heavy_python.py"
PY=".venv-rp/bin/python -B"
G=docs/plans/04-c-core-orchestration/triage/l0_empty_slot/phase2_gates.py
S=output/scratch-35
D=output/scratch-34/G_new/ALLDATA.KWI
SP=output/extract_timing/spool
echo "HEAD $(git rev-parse HEAD) $(date +%T)"; git status --short | grep -v '^??' || true
mkdir $S/G_rebuild $S/perth_j1 $S/perth_j4
step(){ n=$1; shift; echo "== $n $(date +%T)"; $H --log $S/runs/$n.json -- "$@"; }
step p1_before $PY $G snapshot --out $S/protected_before.json
step p1_sha_oracle $PY $G sha --path $D --expected 4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448 --out $S/sha_oracle.json
step p1_sha_perth $PY $G sha --path output/scratch-29/perth_base/ALLDATA.KWI --expected 04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728 --out $S/sha_perth_pin.json
for i in 1 2 3; do step p1_k1_j6_$i $PY parser/tools/quantisation_roundtrip.py --disc $D --spool $SP -j 6 --engine c --out $S/k1_j6_$i.json; done
step p1_k1_j1 $PY parser/tools/quantisation_roundtrip.py --disc $D --spool $SP -j 1 --engine c --out $S/k1_j1.json
step p1_k1_dump $PY parser/tools/quantisation_roundtrip.py --disc $D --spool $SP -j 6 --engine c --out $S/k1_dump.json --dump-failures $S/dump
step p1_encode_au $PY parser/build_alldata.py --spool $SP --out $S/G_rebuild/ALLDATA.KWI -j4
step p1_sha_rebuild $PY $G sha --path $S/G_rebuild/ALLDATA.KWI --expected 4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448 --out $S/sha_rebuild.json
step p1_perth_j1 $PY parser/build_alldata.py --spool $SP --fixture perth --out $S/perth_j1/ALLDATA.KWI -j1
step p1_perth_j4 $PY parser/build_alldata.py --spool $SP --fixture perth --out $S/perth_j4/ALLDATA.KWI -j4
step p1_sha_perth_j1 $PY $G sha --path $S/perth_j1/ALLDATA.KWI --expected 04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728 --out $S/sha_perth_j1.json
step p1_sha_perth_j4 $PY $G sha --path $S/perth_j4/ALLDATA.KWI --expected 04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728 --out $S/sha_perth_j4.json
step p1_after $PY $G snapshot --against $S/protected_before.json --out $S/protected_after.json
echo "ALLDONE $(date +%T)"
