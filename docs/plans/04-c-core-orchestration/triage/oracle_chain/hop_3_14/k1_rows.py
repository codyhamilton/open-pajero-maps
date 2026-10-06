"""Plan 36 Phase 3 outcome 4: per-kind K1 `checked` counts per (block, cell row).

`run`: run the unmodified K1 C checker (parser/tools/quantisation_roundtrip.py,
`cenc.k1_check_band`) over one disc with every band exactly one cell row of one
block, and write one TSV row per (level, block key, row) with the per-kind
`checked` counts. K1Acc merges by sums, so any band partition gives the same
totals (quantisation_roundtrip docstring); the TSV totals are checked against a
recorded whole-disc report when `--whole` is given.

`compare`: given the two row TSVs and the hop's changed-cell list, report the
per-kind whole-disc delta, the delta inside rows that hold a changed cell of that
block, and every row with a non-zero delta and no changed cell (must be empty).

Read-only on the discs; run under run_heavy_python.py + output/.heavy.lock.

Usage:
  k1_rows.py run --disc D --sha S --spool SP --out ROWS.tsv [--whole K1.json] [-j 6]
  k1_rows.py compare --old ROWS_A.tsv --new ROWS_B.tsv --cells CELLS.tsv --out OUT.json
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]


def _qr():
    spec = importlib.util.spec_from_file_location('quantisation_roundtrip',
                                                  ROOT / 'parser' / 'tools' / 'quantisation_roundtrip.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules['quantisation_roundtrip'] = m
    spec.loader.exec_module(m)
    return m


QR = None


def _row(task):
    idx, key, r = task
    cenc, st = QR._k1_state()
    acc = cenc.K1Acc()
    row = cenc.d1_block_rows([key], st['container'], st['cache'])[0:1]
    cenc.k1_check_band(st['region'], row, r, r, QR._k1_spool(cenc, st, key[0]), acc)
    res = acc.result()['kinds']
    return idx, [res[k]['checked'] for k in QR.KINDS]


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def run(a) -> int:
    global QR
    QR = _qr()
    from kiwiw import cenc
    if a.out.exists():
        raise SystemExit('k1_rows: output exists')
    if sha256(a.disc) != a.sha:
        raise SystemExit(f'k1_rows: sha mismatch {a.disc}')
    t0 = time.time()
    disc, spool = str(a.disc), str(a.spool)
    container = QR.walk.read_container(disc)
    keys = QR._block_keys(disc)
    lat = {lv: QR.Lattice(lv) for lv in sorted({k[0] for k in keys})}
    meta, tasks = [], []
    for k in keys:
        c0, c1, r0, r1 = QR.key_cells(container, k, lat[k[0]])
        for r in range(r0, r1 + 1):
            meta.append((k, c0, c1, r))
            tasks.append((len(tasks), k, r))
    print(f'k1_rows: {len(keys)} blocks, {len(tasks)} row bands ({time.time() - t0:.1f}s)', flush=True)
    QR._G.clear()
    QR._G.update({'spool': spool, 'disc': disc})
    cenc_, st = QR._k1_state()
    for lv in lat:
        k0 = next(k for k in keys if k[0] == lv)
        cenc._k1_tallset(QR._k1_spool(cenc_, st, lv), cenc.d1_block_rows([k0], st['container'], st['cache'])[0:1])
    gc.collect()
    gc.freeze()
    out = [None] * len(tasks)
    pool = QR._pool(a.j)
    try:
        for n, (idx, counts) in enumerate(QR._imap(pool, _row, tasks), 1):
            out[idx] = counts
            if n % 5000 == 0:
                print(f'k1_rows: {n}/{len(tasks)} ({time.time() - t0:.1f}s)', flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
        gc.unfreeze()
        QR._G.clear()
    totals = [0] * len(QR.KINDS)
    with open(a.out, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['level', 'key', 'c0', 'c1', 'row', *QR.KINDS])
        for (k, c0, c1, r), counts in zip(meta, out):
            w.writerow([k[0], ':'.join(str(x) for x in k[:7]), c0, c1, r, *counts])
            totals = [x + y for x, y in zip(totals, counts)]
    tot = dict(zip(QR.KINDS, totals))
    print(json.dumps({'disc_sha256': a.sha, 'bands': len(tasks), 'totals': tot,
                      'wall_s': round(time.time() - t0, 1)}), flush=True)
    if a.whole:
        whole = {k: v['checked'] for k, v in json.loads(a.whole.read_text())['totals'].items()}
        if whole != tot:
            print(f'k1_rows: totals differ from {a.whole}: {whole}', flush=True)
            return 3
        print(f'k1_rows: totals equal {a.whole}', flush=True)
    return 0


def _load(p):
    with open(p) as f:
        rd = csv.reader(f, delimiter='\t')
        head = next(rd)
        kinds = head[5:]
        rows = {}
        for r in rd:
            rows[(r[1], int(r[4]))] = (int(r[0]), int(r[2]), int(r[3]), [int(x) for x in r[5:]])
    return kinds, rows


def compare(a) -> int:
    if a.out.exists():
        raise SystemExit('k1_rows: output exists')
    ko, old = _load(a.old)
    kn, new = _load(a.new)
    if ko != kn or set(old) != set(new):
        raise SystemExit('k1_rows: row sets or kinds differ (block layout changed)')
    cells = {}
    with open(a.cells) as f:
        for r in csv.DictReader(f, delimiter='\t'):
            cells.setdefault((int(r['level']), int(r['iy'])), []).append(int(r['ix']))
    whole = [0] * len(ko)
    inside = [0] * len(ko)
    outside_rows = []
    rows_changed = rows_with_cells = 0
    for key in sorted(old):
        lv, c0, c1, ro = old[key]
        d = [n - o for o, n in zip(ro, new[key][3])]
        has = any(c0 <= ix <= c1 for ix in cells.get((lv, key[1]), ()))
        rows_with_cells += has
        whole = [x + y for x, y in zip(whole, d)]
        if any(d):
            rows_changed += 1
            if has:
                inside = [x + y for x, y in zip(inside, d)]
            else:
                outside_rows.append({'level': lv, 'key': key[0], 'row': key[1], 'delta': dict(zip(ko, d))})
    res = {'schema': 1, 'kind': 'k1_checked_row_confinement',
           'old_rows': {'path': str(a.old), 'sha256': sha256(a.old)},
           'new_rows': {'path': str(a.new), 'sha256': sha256(a.new)},
           'cells_list': {'path': str(a.cells), 'sha256': sha256(a.cells)},
           'bands': len(old), 'bands_with_changed_cell': rows_with_cells, 'bands_with_delta': rows_changed,
           'whole_delta': dict(zip(ko, whole)), 'delta_in_changed_rows': dict(zip(ko, inside)),
           'delta_rows_without_changed_cell': outside_rows,
           'confined': not outside_rows and whole == inside,
           'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: res[k] for k in ('bands', 'bands_with_changed_cell', 'bands_with_delta',
                                          'whole_delta', 'confined')}))
    return 0 if res['confined'] else 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--disc', type=Path, required=True)
    r.add_argument('--sha', required=True)
    r.add_argument('--spool', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--whole', type=Path)
    r.add_argument('-j', type=int, default=6)
    c = sub.add_parser('compare')
    for k in ('old', 'new', 'cells', 'out'):
        c.add_argument('--' + k, type=Path, required=True)
    a = ap.parse_args(argv)
    return run(a) if a.cmd == 'run' else compare(a)


if __name__ == '__main__':
    sys.exit(main())
