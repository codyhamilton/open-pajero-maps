#!/usr/bin/env python3
"""Stream disc differences; Execute invokes this through run_heavy_python.py."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT / 'parser'), str(ROOT / 'parser/tools')]
CHUNK = 8 * 1024 * 1024
RULE = ('Equal file sizes; at least one changed byte; every differing byte is '
        'inside a frame covering level 0 cell [0,541] in BOTH discs. '
        'Header, PDMDH, BMT, block slot tables, padding and unmapped changes fail.')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            digest.update(chunk)
    return digest.hexdigest()


def differing_ranges(old, new, chunk_size=CHUNK):
    """Maximal half-open ranges, including differences across chunk boundaries."""
    if not 0 < chunk_size <= CHUNK:
        raise ValueError('chunk must be 1..8 MiB')
    import numpy as np
    ranges, active, offset = [], None, 0
    with Path(old).open('rb') as a, Path(new).open('rb') as b:
        while True:
            x, y = a.read(chunk_size), b.read(chunk_size)
            if not x and not y:
                break
            n = max(len(x), len(y))
            mask = np.ones(n, bool)
            common = min(len(x), len(y))
            mask[:common] = np.frombuffer(x[:common], 'u1') != np.frombuffer(y[:common], 'u1')
            edges = np.flatnonzero(np.diff(np.concatenate(([False], mask, [False]))))
            for lo, hi in zip(edges[::2], edges[1::2]):
                lo, hi = offset + int(lo), offset + int(hi)
                if active is not None and active[1] == lo:
                    active[1] = hi
                else:
                    if active is not None:
                        ranges.append(active)
                    active = [lo, hi]
            offset += n
    if active is not None:
        ranges.append(active)
    return ranges


def structure(path, ranges):
    """Bounded metadata reads; retain only structures intersecting changed bytes."""
    from bisect import bisect_right
    from kiwiw import volume
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    ends = [hi for lo, hi in ranges]
    spans = []

    def add(lo, size, kind, **fields):
        hi = lo + size
        i = bisect_right(ends, lo)
        if size and i < len(ranges) and ranges[i][0] < hi:
            spans.append({'start': lo, 'end': hi, 'kind': kind, **fields})

    with Path(path).open('rb') as f:
        def read(off, size):
            if not 0 <= size <= CHUNK or off < 0:
                raise ValueError(f'metadata read exceeds bound: {off}/{size}')
            data = os.pread(f.fileno(), size, off)
            if len(data) != size:
                raise ValueError(f'short metadata read: {off}/{size}')
            return data
        hdr = volume.parse_volume_header(read(0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(read(volume.DATAVOL_SIZE, volume.MHT_SIZE))
        add(0, volume.DATAVOL_SIZE + volume.MHT_SIZE, 'header')
        for ordinal, management in enumerate(mht.entries):
            if ordinal and not management.name and management.size and management.dsa != 0xFFFFFFFF:
                add(volume.getsector(management.dsa, hdr.sector_size, hdr.logical_sector_size),
                    management.size * hdr.logical_sector_size, 'header', management_record=ordinal)
        entry = mht.entries[0]
        if entry.name:
            raise ValueError('file-based PDMDH unsupported')
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        off = volume.getsector(entry.dsa, ss, ls)
        pd = volume.parse_pdmdh_full(read(off, entry.size * ls))
        add(off, entry.size * ls, 'PDMDH')
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]
            lv = next(m for m in pd.levels if m.level == bs.level)
            nbx, nby = 1 + lv.n_blocks_lng, 1 + lv.n_blocks_lat
            bsx, bsy = bs.blockset_index % (1 + lv.n_blocksets_lng), bs.blockset_index // (1 + lv.n_blocksets_lng)
            nx, ny = 1 + lv.n_parcels_lng[0], 1 + lv.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                add(off + table.offset + bi * 6, 6, 'BMT', level=lv.level,
                    blockset=bs.blockset_index, block=bi)
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                boff = volume.getsector(block.dsa, ss, ls)
                size = block.size * ls
                blx, bly = bi % nbx, bi // nbx
                root = parse_parcel_mgmt_record(read(boff, size), lv)
                add(boff, size, 'block_padding', level=lv.level, block=bi)
                def slots(rec, prefix=()):
                    add(boff + rec.offset, 4, 'block_header', level=lv.level, leaf=list(prefix))
                    for j, e in enumerate(rec.entries):
                        leaf = prefix + (j,)
                        cell = [(bsx * nbx + blx) * nx + leaf[0] % nx,
                                (bsy * nby + bly) * ny + leaf[0] // nx]
                        add(boff + rec.offset + 4 + j * 6, 6, 'block_slot_table',
                            level=lv.level, cell=cell, leaf=list(leaf))
                        if e.subrecord is not None:
                            slots(e.subrecord, leaf)
                        elif e.dsa != 0xFFFFFFFF and e.size:
                            add(volume.getsector(e.dsa, ss, ls), e.size * ls, 'frame',
                                level=lv.level, cell=cell, leaf=list(leaf))
                slots(root)
    return spans


def mapped_ranges(ranges, old_spans, new_spans):
    priority = {'unmapped': 0, 'header': 1, 'PDMDH': 1, 'block_padding': 1,
                'BMT': 2, 'block_header': 2, 'block_slot_table': 2, 'frame': 3}
    from bisect import bisect_right
    # Span indexes avoid scanning the full metadata list for every byte range.
    def segments(spans):
        boundaries = sorted({v for s in spans for v in (s['start'], s['end'])})
        events = {}
        for i, s in enumerate(spans):
            events.setdefault(s['start'], []).append((True, i))
            events.setdefault(s['end'], []).append((False, i))
        active, labels = set(), []
        for p in boundaries:
            for opening, i in events[p]:
                active.add(i) if opening else active.discard(i)
            s = max((spans[i] for i in active), key=lambda s: priority[s['kind']], default={'kind': 'unmapped'})
            labels.append({k: v for k, v in s.items() if k not in ('start', 'end')})
        return boundaries, labels
    indexes = [segments(s) for s in (old_spans, new_spans)]
    out = []
    for lo, hi in ranges:
        cuts = {lo, hi}
        for boundaries, labels in indexes:
            a, b = bisect_right(boundaries, lo), bisect_right(boundaries, hi - 1)
            cuts.update(boundaries[a:b])
        edges = sorted(cuts)
        for a, b in zip(edges, edges[1:]):
            row = {'start': a, 'end': b}
            for side, (boundaries, labels) in zip(('old', 'new'), indexes):
                i = bisect_right(boundaries, a) - 1
                row[side] = labels[i] if i >= 0 else {'kind': 'unmapped'}
            out.append(row)
    return out


def compare(old, new):
    ranges = differing_ranges(old, new)
    mapped = mapped_ranges(ranges, structure(old, ranges), structure(new, ranges))
    confined = (bool(ranges) and Path(old).stat().st_size == Path(new).stat().st_size
                and all(r[s]['kind'] == 'frame' and r[s]['level'] == 0
                        and r[s]['cell'] == [0, 541] for r in mapped for s in ('old', 'new')))
    leaves = {json.dumps(r[s], sort_keys=True) for r in mapped for s in ('old', 'new')
              if r[s]['kind'] == 'frame'}
    return {'old': str(old), 'new': str(new), 'old_sha256': sha(old), 'new_sha256': sha(new),
            'old_size': Path(old).stat().st_size, 'new_size': Path(new).stat().st_size,
            'changed_ranges': mapped, 'changed_leaf_list': [json.loads(s) for s in sorted(leaves)],
            'changed_bytes': sum(hi - lo for lo, hi in ranges),
            'confinement_rule': RULE, 'confined_to_cell_0_541': confined}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--old', type=Path)
    ap.add_argument('--new', type=Path)
    ap.add_argument('--sha-only', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.sha_only:
        if args.old or args.new:
            ap.error('--sha-only cannot be combined with --old/--new')
        result = {'disc': str(args.sha_only), 'sha256': sha(args.sha_only)}
    else:
        if not args.old or not args.new:
            ap.error('--old and --new are required for a comparison')
        result = compare(args.old, args.new)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'changed_ranges'}, sort_keys=True))
    return 0 if args.sha_only or result['confined_to_cell_0_541'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
