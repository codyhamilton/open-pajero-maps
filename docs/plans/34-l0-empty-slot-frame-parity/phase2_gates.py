#!/usr/bin/env python3
"""Execute-only, guarded, streamed protected-input and cell-multiset gates.

No disc/spool I/O at import. Diff stores frame hashes in disk SQLite rather
than retaining a whole-disc byte buffer or a Python object for every frame.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

import frame_witness as fw
sys.path.insert(0, str(fw.ROOT / 'parser'))

PROTECTED = {
    'g_successor': (fw.DISCS['g_successor'], fw.PINS['g_successor']),
    'g_historical': (fw.DISCS['g_historical'], fw.PINS['g_historical']),
    'g_311': (fw.ROOT / 'output/scratch-3-11/G_new/ALLDATA.KWI',
              '013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04'),
    'r': (fw.DISCS['r'], fw.PINS['r']),
}
PERTH_PIN = '04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728'


def sha_file(path):
    with Path(path).open('rb') as fh:
        before = fw.stamp(fh)
        digest = fw.full_hash(fh)
        if fw.stamp(fh) != before:
            raise ValueError(f'input changed during hashing: {path}')
    return digest


def snapshot(args):
    discs = {}
    for name, (path, expected) in PROTECTED.items():
        measured = sha_file(path)
        if measured != expected:
            raise ValueError(f'protected pin drift: {name}: {measured}')
        discs[name] = {'path': str(path), 'sha256': measured}
    spool = fw.SPOOL
    rows = []
    for path in sorted(spool.rglob('*')):
        if path.is_file():
            rows.append({'path': str(path.relative_to(spool)), 'size': path.stat().st_size,
                         'sha256': sha_file(path)})
    if not rows:
        raise ValueError('empty spool fingerprint')
    # Names, sizes and all file bytes, including metadata, are covered.
    fingerprint = fw.sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())
    result = {'protected_discs': discs, 'spool_files': rows, 'spool_fingerprint': fingerprint}
    if args.against and fw.load(args.against) != result:
        raise ValueError('protected discs or spool changed since before snapshot')
    fw.write(args.out, result)


def frame_rows(path):
    """Stream (level, ix, iy, length, sha256, is_empty_shell) for every
    indexed leaf. `is_empty_shell` uses the builder's exact shell predicate
    (the frame is the encoder's record-less shell for that very cell)."""
    from build_alldata import is_empty_shell
    from kiwiw import volume
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    with Path(path).open('rb') as fh:
        before = fw.stamp(fh)
        def read(off, size):
            return fw.pread(fh, size, off)
        hdr = volume.parse_volume_header(read(0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(read(volume.DATAVOL_SIZE, volume.MHT_SIZE))
        entry = mht.entries[0]
        if entry.name or entry.dsa == 0xffffffff or not entry.size:
            raise ValueError('unsupported/absent PDMDH')
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        at = volume.getsector(entry.dsa, ss, ls)
        pd = volume.parse_pdmdh_full(read(at, entry.size * ls))
        levels = {m.level: m for m in pd.levels}
        for bs in pd.blocksets:
            if bs.bmt_offset == 0xffffffff * 2:
                if bs.bmt_size:
                    raise ValueError('invalid absent BMT')
            elif not bs.bmt_size:
                raise ValueError('unresolved zero-size BMT')
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]
            lmr = levels[bs.level]
            nbx, nby = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
            bsx, bsy = bs.blockset_index % (1 + lmr.n_blocksets_lng), bs.blockset_index // (1 + lmr.n_blocksets_lng)
            nx, ny = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]
            if len(table.entries) != nbx * nby:
                raise ValueError('BMT slot count mismatch')
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xffffffff:
                    if block.size:
                        raise ValueError('invalid absent block')
                    continue
                if not block.size:
                    raise ValueError('unresolved zero-size block')
                boff = volume.getsector(block.dsa, ss, ls)
                root = parse_parcel_mgmt_record(read(boff, block.size * ls), lmr)
                def leaves(rec, parent=None, depth=0):
                    if depth > 8:
                        raise ValueError('excessive parcel depth')
                    for j, leaf in enumerate(rec.entries):
                        cell = parent if parent is not None else (
                            (bsx * nbx + bi % nbx) * nx + j % nx,
                            (bsy * nby + bi // nbx) * ny + j // nx)
                        if leaf.subrecord is not None:
                            yield from leaves(leaf.subrecord, cell, depth + 1)
                        elif leaf.dsa == 0xffffffff:
                            if leaf.size:
                                raise ValueError('invalid absent parcel')
                        elif not leaf.size:
                            raise ValueError('unresolved zero-size parcel')
                        else:
                            n = leaf.size * ls
                            raw = read(volume.getsector(leaf.dsa, ss, ls), n)
                            yield (lmr.level, *cell, n, fw.sha(raw),
                                   int(is_empty_shell(raw, lmr.level, *cell)))
                yield from leaves(root)
        if fw.stamp(fh) != before:
            raise ValueError('disc changed during cell scan')


def multiset_changes(db):
    """Compare whole-frame multisets, including repeated identical leaves."""
    query = '''WITH a AS (SELECT level,ix,iy,n,sha,count(*) c FROM old GROUP BY level,ix,iy,n,sha),
                    b AS (SELECT level,ix,iy,n,sha,count(*) c FROM new GROUP BY level,ix,iy,n,sha)
               SELECT level,ix,iy FROM (SELECT * FROM a EXCEPT SELECT * FROM b)
               UNION SELECT level,ix,iy FROM (SELECT * FROM b EXCEPT SELECT * FROM a)
               ORDER BY level,ix,iy'''
    return db.execute(query)


def outside(mask, level, ix, iy):
    rect = mask.get(level)
    if rect is None:
        raise ValueError(f'no parcel mask for level {level}')
    return not (rect[0] <= ix <= rect[1] and rect[2] <= iy <= rect[3])


def diff(args):
    """Classified whole-frame multiset diff over every cell at every level.

    A changed cell is `removed_outside_mask_empty_shell` when the new disc
    indexes nothing there, every old frame there is the exact empty shell,
    and the cell lies outside its level's parcel-mask rectangle. Anything
    else is `other`. The gate passes only with zero `other` cells (all
    remaining cells' multisets identical); no cell coordinates are fixed."""
    from build_alldata import load_parcel_mask
    mask = load_parcel_mask()
    old_sha, new_sha = sha_file(args.old), sha_file(args.new)
    if old_sha != args.old_sha:
        raise ValueError('predecessor full pin mismatch')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='p2-cell-diff-', dir=args.out.parent) as tmp:
        db = sqlite3.connect(str(Path(tmp) / 'frames.sqlite'))
        try:
            db.execute('PRAGMA temp_store=FILE')
            db.execute('PRAGMA cache_size=-32768')
            counts = {}
            for table, path in (('old', args.old), ('new', args.new)):
                db.execute(f'CREATE TABLE {table} (level INT, ix INT, iy INT, n INT, sha TEXT, shell INT)')
                db.executemany(f'INSERT INTO {table} VALUES (?,?,?,?,?,?)', frame_rows(path))
                db.commit()
                db.execute(f'CREATE INDEX {table}_cell ON {table}(level,ix,iy)')
                counts[table] = db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
            removed, other, by_level = [], [], {}
            for level, ix, iy in list(multiset_changes(db)):
                old = db.execute('SELECT n,sha,shell FROM old WHERE level=? AND ix=? AND iy=?',
                                 (level, ix, iy)).fetchall()
                new = db.execute('SELECT count(*) FROM new WHERE level=? AND ix=? AND iy=?',
                                 (level, ix, iy)).fetchone()[0]
                cls = ('removed_outside_mask_empty_shell'
                       if old and not new and all(r[2] for r in old) and outside(mask, level, ix, iy)
                       else 'other')
                row = {'cell': [level, ix, iy], 'class': cls, 'old_frames': [[r[0], r[1]] for r in old],
                       'new_frame_count': new}
                (removed if cls != 'other' else other).append(row)
                by_level.setdefault(str(level), {}).setdefault(cls, 0)
                by_level[str(level)][cls] += 1
            phase1 = sorted([0, *c] for c in fw.TARGETS)
            removed_cells = [r['cell'] for r in removed]
            phase1_removed = all(c in removed_cells for c in phase1)
            passed = not other and (phase1_removed or not args.require_phase1)
            if sha_file(args.old) != old_sha or sha_file(args.new) != new_sha:
                raise ValueError('disc pin changed during diff')
            result = {'old_sha256': old_sha, 'new_sha256': new_sha, 'frame_counts': counts,
                      'changed_cell_count': len(removed) + len(other),
                      'removed_outside_mask_empty_shell_count': len(removed),
                      'other_count': len(other), 'counts_by_level': by_level,
                      'removed_cells': removed_cells, 'removed_detail': removed,
                      'other_cells': other[:200], 'other_truncated': len(other) > 200,
                      'phase1_cells': phase1, 'phase1_cells_removed': phase1_removed,
                      'require_phase1': args.require_phase1, 'pass': bool(passed),
                      'mask': {str(k): list(v) for k, v in sorted(mask.items())},
                      'comparison': 'whole indexed frame-byte multiset per parent cell, all levels; '
                                    'offsets may relocate'}
            fw.write(args.out, result)
            if not passed:
                raise ValueError(f'cell diff has {len(other)} other change(s) or misses a Phase 1 cell')
        finally:
            db.close()


def r_check(args):
    """Bounded R check: every removed cell must be `empty_slot` on R through
    plan 29's hardened reader (L0 only); a lookup failure or a resolved R
    frame fails. Non-L0 removed cells cannot use that reader and fail closed."""
    doc = fw.load(args.diff)
    if not doc.get('pass'):
        raise ValueError('diff did not pass')
    cells = [tuple(c) for c in doc['removed_cells']]
    phase1 = [tuple([0, *c]) for c in fw.TARGETS]
    if args.require_phase1 and not all(c in cells for c in phase1):
        raise ValueError('a Phase 1 cell is missing from the removed list')
    non_l0 = [list(c) for c in cells if c[0] != 0]
    r_path, r_pin = PROTECTED['r']
    if sha_file(r_path) != r_pin:
        raise ValueError('R pin mismatch')
    rows = []
    with Path(r_path).open('rb') as fh:
        before = fw.stamp(fh)
        for row in fw.disc_rows(fh, [(ix, iy) for lvl, ix, iy in cells if lvl == 0]):
            rows.append({'cell': [0, *row['cell']], 'status': row['status'],
                         'frames': len(row['frames']), 'reason': row.get('reason'),
                         'index_evidence': row.get('index_evidence')})
        if fw.stamp(fh) != before:
            raise ValueError('R changed during check')
    if sha_file(r_path) != r_pin:
        raise ValueError('R pin changed during check')
    bad = [r for r in rows if r['status'] != 'empty_slot' or r['frames']]
    passed = not bad and not non_l0 and len(rows) == len(cells)
    fw.write(args.out, {'r_sha256': r_pin, 'diff': str(args.diff), 'removed_cells': len(cells),
                        'checked_l0': len(rows), 'non_l0_unchecked': non_l0,
                        'status_counts': {s: sum(r['status'] == s for r in rows)
                                          for s in sorted({r['status'] for r in rows})},
                        'failures': [{k: r[k] for k in ('cell', 'status', 'frames', 'reason')} for r in bad],
                        'rows': rows, 'pass': passed})
    if not passed:
        raise ValueError(f'R check failed: {len(bad)} non-empty, {len(non_l0)} non-L0')


def check_witness(args):
    doc = fw.load(args.witness)
    rows = fw.validate_disc(doc, 'g_successor', args.expected_sha256)
    if doc.get('predecessor_sha256') != fw.PINS['g_successor']:
        raise ValueError('candidate predecessor mismatch')
    if any(row['status'] != 'empty_slot' or row['frames'] for row in rows.values()):
        raise ValueError('block 0 is not entirely empty_slot')
    fw.write(args.out, {'pass': True, 'disc_sha256': doc['disc_sha256'], 'cells_empty': len(rows)})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('snapshot')
    p.add_argument('--against', type=Path)
    p.set_defaults(run=snapshot)
    p = sub.add_parser('diff')
    p.add_argument('--old', type=Path, required=True)
    p.add_argument('--new', type=Path, required=True)
    p.add_argument('--old-sha', default=fw.PINS['g_successor'])
    p.add_argument('--no-require-phase1', dest='require_phase1', action='store_false')
    p.set_defaults(run=diff)
    p = sub.add_parser('r-check')
    p.add_argument('--diff', type=Path, required=True)
    p.add_argument('--no-require-phase1', dest='require_phase1', action='store_false')
    p.set_defaults(run=r_check)
    p = sub.add_parser('check-witness')
    p.add_argument('--witness', type=Path, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.set_defaults(run=check_witness)
    p = sub.add_parser('sha')
    p.add_argument('--path', type=Path, required=True)
    p.add_argument('--expected')
    def record_sha(args):
        digest = sha_file(args.path)
        fw.write(args.out, {'path': str(args.path), 'sha256': digest})
        if args.expected and digest != args.expected:
            raise ValueError('SHA-256 mismatch')
    p.set_defaults(run=record_sha)
    for p in sub.choices.values():
        p.add_argument('--out', type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        fw.require_heavy_guard()
        args.run(args)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'phase2_gates: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
