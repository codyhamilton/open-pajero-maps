import sys, json, random, subprocess
sys.path[:0]=['parser/tests','parser']
import test_bg_eo_stress as t
from pathlib import Path
from kiwiw import cbuild
so='/home/codyh/workspace/open-pajero-maps/output/scratch-43/probe.so'
subprocess.run([cbuild._find_cc(),*cbuild.CFLAGS,'-shared','parser/tests/fixtures/bg_eo/probe.c','-lm','-o',so],check=True)
t.N_RINGS=20000; rings=t.seeded_rings()
cp=Path('/home/codyh/workspace/open-pajero-maps/output/scratch-43/c20k.json'); op=cp.with_suffix('.out.json')
cp.write_text(json.dumps({f'r{i}':r for i,r in enumerate(rings)}))
subprocess.run([sys.executable,'-B','parser/tests/test_bg_eo_stress.py','--child',so,str(cp),str(op)],check=True,timeout=800)
r=json.loads(op.read_text()); print(r['n'], r['queries'], len(r['failures']), sorted({f['error'] for f in r['failures']})[:5], [f['case'] for f in r['failures']][:20])
