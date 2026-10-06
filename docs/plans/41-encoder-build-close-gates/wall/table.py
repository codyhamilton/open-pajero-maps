import json, re, statistics, sys
from pathlib import Path
S = Path(__file__).resolve().parent
order = ['9269ebb', '33006aa', 'd35b565', 'a890662', 'ecfae1c', '5182c83']
order += [p.name for p in S.iterdir() if p.is_dir() and p.name not in order and p.name != 'runs']
rows = []
for c in order:
    if not (S / c).is_dir(): continue
    walls, lv, enc, asm, shas = [], {}, [], [], []
    for r in (1, 2, 3):
        j = S / 'runs' / f'{c}_r{r}.json'
        if not j.exists(): continue
        walls.append(json.loads(j.read_text())['wall_s'])
        log = (S / c / f'r{r}' / 'build.log').read_text()
        for m in re.finditer(r'^level (\d+): \d+ parcels.*\[([\d.]+)s\]', log, re.M):
            lv.setdefault(int(m.group(1)), []).append(float(m.group(2)))
        m = re.search(r'encode total ([\d.]+)s', log); enc.append(float(m.group(1)) if m else None)
        m = re.search(r'\[assemble ([\d.]+)s\]', log); asm.append(float(m.group(1)) if m else None)
        sj = S / c / f'sha_r{r}.json'
        if sj.exists():
            d = json.loads(sj.read_text()); shas.append((d.get('sha256') or '')[:8] + ('' if d.get('pass', d.get('ok', True)) else '!'))
    pj = S / c / 'sha_perth.json'
    perth = json.loads(pj.read_text()).get('sha256', '')[:8] if pj.exists() else ''
    pw = S / 'runs' / f'{c}_warm_perth.json'
    rows.append({'commit': c, 'n': len(walls), 'walls': walls,
                 'median': statistics.median(walls) if walls else None,
                 'spread': (max(walls) - min(walls)) if walls else None,
                 'encode_total_median': statistics.median([e for e in enc if e]) if any(enc) else None,
                 'assemble_median': statistics.median([a for a in asm if a]) if any(asm) else None,
                 'level_median_s': {k: statistics.median(v) for k, v in sorted(lv.items())},
                 'shas': shas, 'perth_sha': perth,
                 'perth_wall_j4_warm': json.loads(pw.read_text())['wall_s'] if pw.exists() else None})
(S / 'bench_table.json').write_text(json.dumps(rows, indent=1) + '\n')
for r in rows:
    print(r['commit'], r['n'], [round(w, 2) for w in r['walls']], 'med', r['median'] and round(r['median'], 2),
          'spr', r['spread'] and round(r['spread'], 2), 'enc', r['encode_total_median'], 'asm', r['assemble_median'],
          'L0', r['level_median_s'].get(0), r['shas'], 'perth', r['perth_sha'], r['perth_wall_j4_warm'])
