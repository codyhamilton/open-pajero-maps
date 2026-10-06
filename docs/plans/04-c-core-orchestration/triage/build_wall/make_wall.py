"""Assemble this directory (plan 41 build wall evidence) from output/scratch-41 (light)."""
import json, glob, re, shutil, statistics
from pathlib import Path
S = Path('output/scratch-41'); W = Path(__file__).resolve().parent; W.mkdir(parents=True, exist_ok=True)
SLOTS = {0: 'bg_shape total', 1: 'eo_clip stage 1: segment sweep (pair intersections)', 2: 'eo_clip stage 2: eo_left per-chain side checks',
         3: 'eo_clip stage 3: whole-ring duplicate-vertex check', 4: 'eo_clip stage 4: successor tie check',
         5: 'eo_clip stage 5: complex EO face path', 6: 'chains()'}
prof = {}
for v in ('pre', 'head'):
    agg = {k: [0.0, 0] for k in range(16)}; calls = 0
    for f in glob.glob(str(S / 'prof' / v / 'pf' / '*.tsv')):
        for line in open(f):
            a = line.split('\t')
            if a[0].isdigit():
                agg[int(a[0])][0] += float(a[1]); agg[int(a[0])][1] += int(a[2])
            elif a[0] == 'calls':
                calls += int(a[1])
    b = json.load(open(S / 'prof' / v / 'bench.json'))
    sha = json.load(open(S / 'prof' / v / 'sha.json'))
    prof[v] = {'wall_s_instrumented': round(b['wall_s'], 2), 'bg_shape_calls': calls,
               'cpu_s_by_slot': {SLOTS[k]: round(agg[k][0], 2) for k in SLOTS},
               'entries_by_slot': {SLOTS[k]: agg[k][1] for k in SLOTS},
               'level_wall_s': {lv: round(x['wall_s'], 2) for lv, x in b['levels'].items()},
               'disc_sha256': sha.get('sha256'), 'sha_pass': sha.get('pass', sha.get('ok'))}
prof['note'] = ('CPU seconds summed over the -j4 worker processes (CLOCK_MONOTONIC per call; timer overhead inflates the '
                'instrumented wall). Stages are cumulative-split timestamps inside eo_clip; stage 2 runs only for non-whole rings.')
prof['commits'] = {'pre': '33006aa (pre 3-14)', 'head': '20b4bf9 (master at measure time; parser/kiwiw unchanged from ec90121 to the fix parent)'}
(W / 'prof_summary.json').write_text(json.dumps(prof, indent=1) + '\n')
EXP = {True: '04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728', False: '4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448'}
fix = {'patch': 'eo_left bbox-gap prefilter (a95501c)', 'runs': []}
for r in ('fix_perth_j1', 'fix_perth_j4', 'fix_r1', 'fix_r2', 'fix_r3'):
    j = S / 'fix' / 'runs' / f'{r}.json'
    if not j.exists(): continue
    d = json.load(open(j)); sub = r.replace('fix_', '')
    log = (S / 'fix' / sub / 'build.log').read_text() if (S / 'fix' / sub / 'build.log').exists() else ''
    m = re.search(r'encode total ([\d.]+)s', log); lv = {int(a): float(b) for a, b in re.findall(r'^level (\d+): \d+ parcels.*\[([\d.]+)s\]', log, re.M)}
    sj = S / 'fix' / sub / 'sha.json'; sd = json.load(open(sj)) if sj.exists() else {}
    fix['runs'].append({'run': r, 'wall_s': round(d['wall_s'], 2), 'exit': d['exit'], 'encode_total_s': float(m.group(1)) if m else None,
                        'level_s': lv, 'sha256': sd.get('sha256'), 'expected': EXP[r.startswith('fix_perth')],
                        'pass': sd.get('sha256') == EXP[r.startswith('fix_perth')]})
au = [x['wall_s'] for x in fix['runs'] if x['run'].startswith('fix_r')]
if au:
    fix['au_median_wall_s'] = statistics.median(au); fix['au_spread_s'] = round(max(au) - min(au), 2)
    fix['au_median_encode_s'] = statistics.median([x['encode_total_s'] for x in fix['runs'] if x['run'].startswith('fix_r')])
(W / 'fix_runs.json').write_text(json.dumps(fix, indent=1) + '\n')
shutil.copy(S / 'bench' / 'bench_table.json', W / 'bench_table.json')
for f in ('bench/run_bench.sh', 'bench/table.py', 'prof_patch.py', 'run_prof.sh', 'fix_patch.py', 'run_fix.sh', 'make_wall.py'):
    shutil.copy(S / f, W / Path(f).name)
pa = S / 'bench' / 'protected_after.json'
if pa.exists(): shutil.copy(pa, W / 'protected_after.json')
shutil.copy(S / 'bench' / 'protected_before.json', W / 'protected_before.json')
print(json.dumps(prof['pre']['cpu_s_by_slot'])); print(json.dumps(prof['head']['cpu_s_by_slot'])); print(fix.get('au_median_wall_s'), fix.get('au_spread_s'), fix.get('au_median_encode_s'))
