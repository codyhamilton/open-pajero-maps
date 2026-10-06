"""Plan 36 Phase 3: per-leaf section detail for the hop cells whose section
pattern is not background-only (read-only).

For every cell in sections.tsv whose `sections_changed` is not `background`,
write per side (old/new) and per leaf: routed footprint, frame length, the
section sizes and hashes (sections.split) and the raw Main Map Data Frame Entry
table (index, offset, size in bytes; None for an absent entry). This is the
input for the byte predicates in cells_causes.py.

Usage: detail.py --old A --new B --old-sha X --new-sha Y --sections S.tsv --out OUT.json
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hop_sections', HERE / 'sections.py')
sx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sx)
oc = sx.oc


def table(buf):
    n = len(buf)
    de = 36 + sx.u16(buf, 34) * 4
    starts = []
    for i in range(3):
        o = de + i * 6
        if o + 6 <= n and sx.u32(buf, o) != 0xFFFFFFFF and (sx.u32(buf, o) << 1) < n:
            starts.append(sx.u32(buf, o) << 1)
    total = max((min(starts) - de) // 6, 3) if starts else 3
    out = []
    for i in range(total):
        o = de + i * 6
        if o + 6 > n:
            break
        off, size = sx.u32(buf, o), sx.u16(buf, o + 4)
        out.append(None if off == 0xFFFFFFFF else [off << 1, (size << 1) if size != 0xFFFF else 0xFFFF])
    return out


def side(path, cells):
    per = {}
    with open(path, 'rb') as f:
        fd = f.fileno()
        for level, ix, iy, length, digest, leaf, pos, fallback, fp in oc.iter_frames(path, routed=True):
            key = (level, ix, iy)
            if key not in cells:
                continue
            buf = os.pread(fd, length, pos)
            secs = sx.split(buf)
            per.setdefault(key, []).append({
                'footprint': fp, 'length': length,
                'sizes': {k: len(v) for k, v in secs.items()},
                'hashes': {k: hashlib.sha256(v).hexdigest()[:16] for k, v in secs.items()},
                'table': table(buf)})
    for v in per.values():
        v.sort(key=lambda r: r['footprint'])
    return per


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('old', 'new', 'sections', 'out'):
        ap.add_argument('--' + k, type=Path, required=True)
    ap.add_argument('--old-sha', required=True)
    ap.add_argument('--new-sha', required=True)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit('detail: output exists')
    for p, want in ((a.old, a.old_sha), (a.new, a.new_sha)):
        if oc.sha(p) != want:
            raise SystemExit(f'detail: sha mismatch {p}')
    with open(a.sections) as f:
        cells = {(int(r['level']), int(r['ix']), int(r['iy'])) for r in csv.DictReader(f, delimiter='\t')
                 if r['sections_changed'] != 'background'}
    old, new = side(a.old, cells), side(a.new, cells)
    res = {'schema': 1, 'kind': 'hop_section_detail', 'old_sha256': a.old_sha, 'new_sha256': a.new_sha,
           'sections': {'path': str(a.sections), 'sha256': oc.sha(a.sections)},
           'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'cells': [{'cell': list(k), 'old': old.get(k, []), 'new': new.get(k, [])} for k in sorted(cells)]}
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'cells': len(cells)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
