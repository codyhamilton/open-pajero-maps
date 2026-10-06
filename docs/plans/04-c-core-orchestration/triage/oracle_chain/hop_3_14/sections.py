"""Plan 36 Phase 3: per-cell sub-layer section comparison for a hop (read-only).

For every cell in a changed-cell list, read the old and new Map Frames (all
leaves, routed footprints) and split each frame by its Main Map Data Frame
Entry table (parcel.decode_parcel layout) into sections:
  header   - Map Frame header bytes 2..36 (bytes 0..1 are the frame length)
  regions  - region list
  table    - mfde table entries for indexes >= 3 (raw), i.e. ext pointers
  road / background / name - sub-frame bytes (entries 0 / 1 / 2)
  ext      - in-buffer bytes of entries >= 3
  rest     - every byte not covered above (must be empty or identical)
Per cell the sorted (footprint, section-hash) lists are compared per section;
the mfde offsets/sizes of entries 0..2 are excluded because they move whenever
an earlier section changes length.

Bounded preads per frame via oracle_chain.iter_frames; run under
run_heavy_python.py + output/.heavy.lock.

Usage: sections.py --old A --new B --old-sha X --new-sha Y --cells CELLS.tsv --out OUT.tsv --summary OUT.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
spec = importlib.util.spec_from_file_location('oracle_chain', HERE.parent / 'oracle_chain.py')
oc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oc)
SECTIONS = ('header', 'regions', 'table', 'road', 'background', 'name', 'ext', 'rest')
CEILING = 131070


def u16(b, o):
    return (b[o] << 8) | b[o + 1]


def u32(b, o):
    return (b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]


def split(buf: bytes) -> dict:
    """Return {section: bytes}; mirrors parcel.decode_parcel's table-length rule."""
    n = len(buf)
    nregion = u16(buf, 34)
    de = 36 + nregion * 4
    def entry(i):
        o = de + i * 6
        if o + 6 > n:
            return None
        raw_off, raw_size = u32(buf, o), u16(buf, o + 4)
        if raw_off == 0xFFFFFFFF:
            return None
        return raw_off << 1, (raw_size << 1) if raw_size != 0xFFFF else 0xFFFF
    basic = [entry(i) for i in range(3)]
    starts = [e[0] for e in basic if e and e[0] < n]
    total = max((min(starts) - de) // 6, 3) if starts else 3
    covered = bytearray(n)
    out = {}
    def take(name, a, b):
        a, b = max(0, min(a, n)), max(0, min(b, n))
        out[name] = out.get(name, b'') + buf[a:b]
        covered[a:b] = b'\x01' * (b - a)
    take('header', 2, 36)
    covered[0:2] = b'\x01\x01'
    take('regions', 36, de)
    covered[de:de + total * 6] = b'\x01' * max(0, min(total * 6, n - de))
    out['table'] = buf[de + 18:de + total * 6]
    for i, name in enumerate(('road', 'background', 'name')):
        e = basic[i]
        out.setdefault(name, b'')
        if e and e[1] not in (0, 0xFFFF) and e[0] < n:
            take(name, e[0], e[0] + e[1])
    out.setdefault('ext', b'')
    for i in range(3, total):
        e = entry(i)
        if e and e[1] not in (0, 0xFFFF) and e[0] < n:
            take('ext', e[0], e[0] + e[1])
    out['rest'] = np.frombuffer(buf, np.uint8)[np.frombuffer(bytes(covered), np.uint8) == 0].tobytes()
    return out


def load_cells(path):
    with open(path) as f:
        return {(int(r['level']), int(r['ix']), int(r['iy'])) for r in csv.DictReader(f, delimiter='\t')}


def side(path, cells):
    per = defaultdict(list)
    with open(path, 'rb') as f:
        fd = f.fileno()
        for level, ix, iy, length, digest, leaf, pos, fallback, fp in oc.iter_frames(path, routed=True):
            key = (level, ix, iy)
            if key not in cells:
                continue
            buf = os.pread(fd, length, pos)
            secs = split(buf)
            per[key].append((fp, length, {k: hashlib.sha256(v).hexdigest()[:16] for k, v in secs.items()},
                             {k: len(v) for k, v in secs.items()}))
    return per


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('old', 'new', 'cells', 'out', 'summary'):
        ap.add_argument('--' + k, type=Path, required=True)
    ap.add_argument('--old-sha', required=True)
    ap.add_argument('--new-sha', required=True)
    a = ap.parse_args(argv)
    if a.out.exists() or a.summary.exists():
        raise SystemExit('sections: output exists')
    for p, want in ((a.old, a.old_sha), (a.new, a.new_sha)):
        if oc.sha(p) != want:
            raise SystemExit(f'sections: sha mismatch {p}')
    cells = load_cells(a.cells)
    old, new = side(a.old, cells), side(a.new, cells)
    patterns, topo, ceiling, missing = Counter(), 0, 0, []
    with open(a.out, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(['level', 'ix', 'iy', 'old_leaves', 'new_leaves', 'footprints_equal', 'sections_changed',
                    'old_max_len', 'new_max_len', 'at_ceiling', 'bg_bytes_old', 'bg_bytes_new'])
        for key in sorted(cells):
            o, n = sorted(old.get(key, []), key=lambda r: r[0]), sorted(new.get(key, []), key=lambda r: r[0])
            if not o or not n:
                missing.append(list(key))
            fpe = [r[0] for r in o] == [r[0] for r in n]
            if fpe:
                changed = [s for s in SECTIONS if [r[2][s] for r in o] != [r[2][s] for r in n]]
            else:
                changed = [s for s in SECTIONS if sorted(r[2][s] for r in o) != sorted(r[2][s] for r in n)]
            pat = ('topology+' if not fpe else '') + ('+'.join(changed) or 'none')
            patterns[pat] += 1
            topo += not fpe
            mo, mn = max((r[1] for r in o), default=0), max((r[1] for r in n), default=0)
            atc = max(mo, mn) >= CEILING - 64
            ceiling += atc
            w.writerow([*key, len(o), len(n), int(fpe), pat, mo, mn, int(atc),
                        sum(r[3]['background'] for r in o), sum(r[3]['background'] for r in n)])
    summary = {'schema': 1, 'kind': 'hop_sections', 'old_sha256': a.old_sha, 'new_sha256': a.new_sha,
               'cells': len(cells), 'patterns': dict(patterns.most_common()), 'topology_changed': topo,
               'near_ceiling': ceiling, 'missing_side': missing,
               'cells_list': {'path': str(a.cells), 'sha256': oc.sha(a.cells)},
               'out': {'path': str(a.out), 'sha256': oc.sha(a.out)},
               'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    a.summary.write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: summary[k] for k in ('cells', 'patterns', 'topology_changed', 'near_ceiling')}))
    return 0 if not missing else 2


if __name__ == '__main__':
    sys.exit(main())
