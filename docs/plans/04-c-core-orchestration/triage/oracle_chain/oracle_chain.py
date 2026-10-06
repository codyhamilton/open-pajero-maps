#!/usr/bin/env python3
"""Measure/publish existing oracle hops; never build or sign a new oracle.

Execute must run disc/census reads through run_heavy_python.py. `publish`
only reads small evidence files. Disc comparison uses independent frame-to-
cell maps on both layouts, not absolute byte offsets: relocation alone must
not turn every subsequent cell into a changed cell. Frame multisets match
the historical cells.py/group_cells.py definition (whole Map Frame, excluding
sector padding). SQLite holds the census on disk; reads are at most 8 MiB.
This is an identity gate, not a payload/root-cause classifier. New changed
cells remain explicitly unexplained until separate explanation evidence exists.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from fractions import Fraction
import hashlib
import itertools
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[5]
PLAN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'parser'))
CHUNK = 8 * 1024 * 1024
AU0 = '87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862'
AU1 = '013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04'
AU2 = '4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72'
AU3 = '2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae'
P0 = 'da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc'
P1 = '04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728'
LIST37_SHA = '9f2b0e554465d030637fa7d19b4ceaf88b6283b1d4d86810de5ccd4dece50e5e'
SIGN_RECORD = ROOT / 'docs/plans/04-c-core-orchestration/IMPLEMENTATION.md'
NAME_ANCHOR = ROOT / 'docs/plans/04-c-core-orchestration/triage/name_anchor'
PLAN29_RECORD = ROOT / 'docs/plans/29-k1-name-anchor-failure.md'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()


def small_bytes(path):
    if Path(path).stat().st_size > CHUNK:
        raise ValueError(f'not a small evidence file: {path}')
    return Path(path).read_bytes()


def evidence(path):
    path = Path(path)
    try:
        label = str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        # Shared output is a symlink, but keep its checkout-relative spelling.
        try:
            label = str(path.absolute().relative_to(ROOT))
        except ValueError:
            label = str(path)
    return {'path': label, 'sha256': hashlib.sha256(small_bytes(path)).hexdigest()}


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def read_exact(f, offset, size):
    if offset < 0 or not 0 <= size <= CHUNK:
        raise ValueError(f'read exceeds bound: {offset}/{size}')
    data = os.pread(f.fileno(), size, offset)
    if len(data) != size:
        raise ValueError(f'short read: {offset}/{size}')
    return data


def tree_leaves(rec, lmr, x=Fraction(0), y=Fraction(0),
                width=None, height=None, path=(), footprint=False):
    """Exact cell arithmetic, including divided/integrated root layouts.

    Sub-leaves belong to their containing base cell, as in cells.py. Sparse
    aliases are deliberately counted once per occupied slot, not deduplicated
    by frame address. This preserves the historical cell signature contract.
    """
    width = Fraction(1 + lmr.n_parcels_lng[0]) if width is None else width
    height = Fraction(1 + lmr.n_parcels_lat[0]) if height is None else height
    nx = 1 + lmr.n_parcels_lng[rec.parcel_type]
    ny = 1 + lmr.n_parcels_lat[rec.parcel_type]
    if len(rec.entries) != nx * ny:
        raise ValueError('parcel slot count disagrees with layout')
    for i, entry in enumerate(rec.entries):
        if entry.dsa == 0xFFFFFFFF:
            continue
        cx, cy = x + (i % nx) * width / nx, y + (i // nx) * height / ny
        leaf = path + (i,)
        if entry.subrecord is not None:
            yield from tree_leaves(entry.subrecord, lmr, cx, cy,
                                   width / nx, height / ny, leaf, footprint)
        elif entry.size:
            if footprint:
                # Exact block-relative rectangle in base-cell units; stable
                # under relocation and independent of leaf ordinals.
                yield int(cx), int(cy), leaf, entry, (cx, cy, width / nx, height / ny)
            else:
                yield int(cx), int(cy), leaf, entry


def iter_frames(path, routed=False):
    """Read one bounded metadata block/frame at a time, with no decoding.

    With routed=True each row also carries the leaf's exact absolute
    geographic footprint (x:y:w:h in base-cell units, rational strings)."""
    from kiwiw import volume
    from kiwiw.bitutils import u16
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    with Path(path).open('rb') as f:
        hdr = volume.parse_volume_header(read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(
            read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]
        if prdm.name:
            raise ValueError('file-based PDMDH unsupported')
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        if ss <= 0 or ls <= 0:
            raise ValueError('invalid sector sizes')
        off = volume.getsector(prdm.dsa, ss, ls)
        pd = volume.parse_pdmdh_full(read_exact(f, off, prdm.size * ls))
        levels = {m.level: m for m in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]
            lm = levels[bs.level]
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng)
            bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                boff = volume.getsector(block.dsa, ss, ls)
                root = parse_parcel_mgmt_record(read_exact(f, boff, block.size * ls), lm)
                bx = (bsx * nbx + bi % nbx) * nx
                by = (bsy * nby + bi // nbx) * ny
                # One block's cache avoids repeatedly hashing sparse aliases.
                cache = {}
                for item in tree_leaves(root, lm, footprint=routed):
                    x, y, leaf, entry = item[:4]
                    pos = volume.getsector(entry.dsa, ss, ls)
                    key = (pos, entry.size)
                    if key not in cache:
                        buf = read_exact(f, pos, entry.size * ls)
                        length = u16(buf, 0) * 2
                        # Match the historical inventory's explicit fallback.
                        fallback = not 0 < length <= len(buf)
                        if fallback:
                            length = len(buf)
                        cache[key] = (length, hashlib.sha256(buf[:length]).hexdigest(), fallback)
                    length, digest, fallback = cache[key]
                    row = (lm.level, bx + x, by + y, length, digest,
                           '.'.join(map(str, leaf)), pos, fallback)
                    if routed:
                        fx, fy, fw, fh = item[4]
                        row += (f'{bx + fx}:{by + fy}:{fw}:{fh}',)
                    yield row


def cell_signatures(db, side):
    rows = db.execute('SELECT level,ix,iy,length,hash FROM frames WHERE side=? '
                      'ORDER BY level,ix,iy,length,hash', (side,))
    for key, group in itertools.groupby(rows, lambda r: r[:3]):
        h, total, leaves = hashlib.sha256(), 0, 0
        for _, _, _, length, digest in group:
            h.update(f'{length}\t{digest}\n'.encode())
            total += length
            leaves += 1
        yield key, (total, h.hexdigest(), leaves)


def routed_signatures(db, side):
    """Per base cell: sorted (footprint, length, hash) triples.

    Unlike cell_signatures this keeps which exact footprint routes to which
    whole frame, so swapped divided payloads or changed subdivision geometry
    change the signature. Offsets and sector padding never enter it."""
    rows = db.execute('SELECT level,ix,iy,footprint,length,hash FROM frames WHERE side=? '
                      'ORDER BY level,ix,iy,footprint,length,hash', (side,))
    for key, group in itertools.groupby(rows, lambda r: r[:3]):
        h, total, leaves = hashlib.sha256(), 0, 0
        for _, _, _, fp, length, digest in group:
            h.update(f'{fp}\t{length}\t{digest}\n'.encode())
            total += length
            leaves += 1
        yield key, (total, h.hexdigest(), leaves)


def changed_cells(old, new):
    """Merge sorted cell signatures; distinguish missing cells from changes."""
    a, b = next(old, None), next(new, None)
    while a is not None or b is not None:
        if b is None or (a is not None and a[0] < b[0]):
            yield a[0], 'removed', a[1], None
            a = next(old, None)
        elif a is None or b[0] < a[0]:
            yield b[0], 'added', None, b[1]
            b = next(new, None)
        else:
            if a[1] != b[1]:
                yield a[0], 'changed', a[1], b[1]
            a, b = next(old, None), next(new, None)


def diff(old, new, old_sha, new_sha, out, cells, work_dir):
    """Execute-only heavy entry point. Fresh outputs; hash both before/after."""
    old, new, out, cells, work_dir = map(Path, (old, new, out, cells, work_dir))
    inputs = {old.resolve(), new.resolve()}
    for p in (out, cells, work_dir):
        if (p.resolve() in inputs or any(p.resolve() in src.parents for src in inputs)
                or p.name == 'ALLDATA.KWI' or 'spool' in str(p).lower()):
            raise ValueError(f'unsafe output path: {p}')
        if p.exists():
            raise ValueError(f'output already exists; choose a new scratch path: {p}')
    if out.resolve() == cells.resolve() or work_dir.resolve() in (out.resolve(), cells.resolve()):
        raise ValueError('outputs must be distinct')
    before = [sha(old), sha(new)]
    if before != [old_sha, new_sha]:
        raise ValueError(f'input SHA mismatch: {before}')
    work_dir.mkdir(parents=True, exist_ok=False)
    dbpath = work_dir / 'frames.sqlite'
    counts, fallback = {}, {}
    with sqlite3.connect(dbpath) as db:
        db.execute('PRAGMA cache_size=-8192')
        db.execute('PRAGMA temp_store=FILE')
        db.execute('CREATE TABLE frames (side TEXT, level INTEGER, ix INTEGER, iy INTEGER, '
                   'length INTEGER, hash TEXT, leaf TEXT, offset INTEGER)')
        for side, path in (('old', old), ('new', new)):
            counts[side], fallback[side] = 0, 0
            for frame in iter_frames(path):
                db.execute('INSERT INTO frames VALUES (?,?,?,?,?,?,?,?)', (side, *frame[:7]))
                counts[side] += 1
                fallback[side] += int(frame[7])
                if counts[side] % 100000 == 0:
                    db.commit()
                    print(f'{side}: {counts[side]} leaves', flush=True)
            db.commit()
        db.execute('CREATE INDEX cell_order ON frames(side,level,ix,iy,length,hash)')
        totals, by_level = Counter(), {}
        cells.parent.mkdir(parents=True, exist_ok=True)
        with cells.open('x') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n')
            w.writerow(('level', 'ix', 'iy', 'status', 'old_bytes', 'new_bytes',
                        'old_cell_sha256', 'new_cell_sha256', 'old_leaves', 'new_leaves'))
            for key, status, a, b in changed_cells(cell_signatures(db, 'old'), cell_signatures(db, 'new')):
                totals[status] += 1
                by_level.setdefault(str(key[0]), Counter())[status] += 1
                w.writerow((*key, status, a[0] if a else '', b[0] if b else '',
                            a[1] if a else '', b[1] if b else '',
                            a[2] if a else 0, b[2] if b else 0))
    after = [sha(old), sha(new)]
    if after != before:
        raise ValueError('protected input changed during measurement')
    result = {'schema': 1, 'kind': 'cell_diff', 'old': str(old), 'new': str(new),
              'old_sha256': before[0], 'new_sha256': before[1],
              'protected_after_sha256': after, 'protected_unchanged': True,
              'old_size': old.stat().st_size, 'new_size': new.stat().st_size,
              'cells': {'path': str(cells), 'sha256': sha(cells)},
              'counts': {s: totals[s] for s in ('changed', 'added', 'removed')},
              'counts_by_level': by_level, 'leaf_counts': counts,
              'frame_length_fallbacks': fallback,
              'unexplained_count': sum(totals.values()),
              'unexplained_cells': {'path': str(cells), 'selector': 'all rows'},
              'confinement': 'Whole-Map-Frame multiset differences by cell on independent layouts; '
                             'excludes sector padding and container/index bytes.',
              'residuals': ['Payload causes not measured; all listed cells are unexplained.',
                            'Container/index/padding relocation is outside this cell-identity measurement.']}
    write_json(out, result, exclusive=True)
    return result


def read_cell_list(path):
    with Path(path).open(newline='') as f:
        r = csv.reader(f, delimiter='\t')
        next(r)
        return {(int(a), int(b), int(c)) for a, b, c, *_ in r}


def routed_diff(old, new, old_sha, new_sha, baseline, out, cells, work_dir):
    """Execute-only supplement to `diff` (REVIEW R1).

    Compares routed cell contents (exact footprint -> whole frame) on both
    layouts and reconciles them with the retained multiset diff `baseline`.
    Every multiset change is necessarily a routed change; the gate is that the
    routed list contains every baseline cell. Routed-only cells are the cells
    whose routing/footprints changed while their frame multiset did not."""
    old, new, baseline, out, cells, work_dir = map(Path, (old, new, baseline, out, cells, work_dir))
    inputs = {old.resolve(), new.resolve()}
    for p in (out, cells, work_dir):
        if (p.resolve() in inputs or any(p.resolve() in src.parents for src in inputs)
                or p.name == 'ALLDATA.KWI' or 'spool' in str(p).lower()):
            raise ValueError(f'unsafe output path: {p}')
        if p.exists():
            raise ValueError(f'output already exists; choose a new scratch path: {p}')
    if len({out.resolve(), cells.resolve(), work_dir.resolve()}) != 3:
        raise ValueError('outputs must be distinct')
    base = json.loads(small_bytes(baseline))
    if [base.get('old_sha256'), base.get('new_sha256')] != [old_sha, new_sha]:
        raise ValueError('baseline diff is for a different hop')
    base_cells = Path(base['cells']['path'])
    if not base_cells.is_absolute():
        base_cells = ROOT / base_cells
    if sha(base_cells) != base['cells']['sha256']:
        raise ValueError('baseline cell list hash mismatch')
    multiset = read_cell_list(base_cells)
    if len(multiset) != base['unexplained_count']:
        raise ValueError('baseline cell list count mismatch')
    before = [sha(old), sha(new)]
    if before != [old_sha, new_sha]:
        raise ValueError(f'input SHA mismatch: {before}')
    work_dir.mkdir(parents=True, exist_ok=False)
    counts, fallback = {}, {}
    totals, by_level = Counter(), {}
    routed_only, missing = [], []
    with sqlite3.connect(work_dir / 'frames.sqlite') as db:
        db.execute('PRAGMA cache_size=-8192')
        db.execute('PRAGMA temp_store=FILE')
        db.execute('CREATE TABLE frames (side TEXT, level INTEGER, ix INTEGER, iy INTEGER, '
                   'footprint TEXT, length INTEGER, hash TEXT)')
        for side, path in (('old', old), ('new', new)):
            counts[side], fallback[side] = 0, 0
            for frame in iter_frames(path, routed=True):
                db.execute('INSERT INTO frames VALUES (?,?,?,?,?,?,?)',
                           (side, *frame[:3], frame[8], frame[3], frame[4]))
                counts[side] += 1
                fallback[side] += int(frame[7])
                if counts[side] % 100000 == 0:
                    db.commit()
                    print(f'{side}: {counts[side]} leaves', flush=True)
            db.commit()
        db.execute('CREATE INDEX route_order ON frames(side,level,ix,iy,footprint,length,hash)')
        routed = set()
        cells.parent.mkdir(parents=True, exist_ok=True)
        with cells.open('x') as f:
            w = csv.writer(f, delimiter='\t', lineterminator='\n')
            w.writerow(('level', 'ix', 'iy', 'status', 'in_multiset_list',
                        'old_routed_sha256', 'new_routed_sha256', 'old_leaves', 'new_leaves'))
            for key, status, a, b in changed_cells(routed_signatures(db, 'old'),
                                                   routed_signatures(db, 'new')):
                routed.add(key)
                totals[status] += 1
                by_level.setdefault(str(key[0]), Counter())[status] += 1
                listed = key in multiset
                if not listed:
                    routed_only.append(list(key))
                w.writerow((*key, status, int(listed), a[1] if a else '', b[1] if b else '',
                            a[2] if a else 0, b[2] if b else 0))
        missing = sorted(multiset - routed)
    after = [sha(old), sha(new)]
    if after != before:
        raise ValueError('protected input changed during measurement')
    result = {'schema': 1, 'kind': 'routed_cell_diff', 'old': str(old), 'new': str(new),
              'old_sha256': before[0], 'new_sha256': before[1],
              'protected_after_sha256': after, 'protected_unchanged': True,
              'baseline': evidence(baseline), 'baseline_cells': {'path': str(base_cells), 'sha256': base['cells']['sha256'],
                                                                 'count': len(multiset)},
              'cells': {'path': str(cells), 'sha256': sha(cells)},
              'routed_counts': {s: totals[s] for s in ('changed', 'added', 'removed')},
              'routed_counts_by_level': by_level, 'routed_changed_total': len(routed),
              'leaf_counts': counts, 'frame_length_fallbacks': fallback,
              'baseline_cells_missing_from_routed': len(missing),
              'routed_only_count': len(routed_only), 'routed_only_cells': routed_only[:1000],
              'routed_only_cells_truncated': len(routed_only) > 1000,
              'multiset_list_complete_under_routing': not routed_only and not missing,
              'identity': 'per base cell: sorted (exact absolute footprint x:y:w:h in base-cell units, '
                          'whole-frame length, SHA-256); offsets and sector padding excluded',
              'residuals': ['Payload causes not measured; all changed cells remain unexplained.',
                            'Container/index/padding bytes are outside this cell-identity measurement.']}
    write_json(out, result, exclusive=True)
    if missing:
        raise ValueError(f'{len(missing)} baseline cells absent from the routed list')
    return result


def check_census(path, expected, out):
    """Guarded streaming audit of retained 317-MB Gnew.cells.tsv."""
    wanted = {tuple(map(int, s.split(':'))) for s in small_bytes(expected).decode().splitlines()}
    found, count = set(), 0
    with Path(path).open() as f:
        for line in f:
            fields = line.rstrip('\n').split('\t')
            if len(fields) != 5:
                raise ValueError('bad historical census row')
            key = tuple(map(int, fields[:3]))
            if key in wanted:
                if key in found:
                    raise ValueError('duplicate expected cell in census')
                found.add(key)
            count += 1
    if count != 3951970 or found != wanted:
        raise ValueError(f'census mismatch: rows={count}, expected cells={len(found)}')
    result = {'kind': 'census_audit', 'path': str(path), 'sha256': sha(path),
              'expected': evidence(expected),
              'rows': count, 'expected_cells_present': len(found), 'pass': True}
    write_json(out, result, exclusive=True)
    return result


def retained37(scratch):
    path, expected = scratch / 'Gnew.diff_cells.txt', scratch / 'Gnew.expected37.txt'
    data = small_bytes(path)
    if hashlib.sha256(data).hexdigest() != LIST37_SHA or data != small_bytes(expected):
        raise ValueError('3-11 authoritative/predicted list SHA mismatch')
    cells = [list(map(int, line.split(':'))) for line in data.decode().splitlines()]
    if len(cells) != 37 or len({tuple(c) for c in cells}) != 37 or any(c[0] != 0 for c in cells):
        raise ValueError('3-11 is not exactly 37 unique L0 cells')
    scanpath = scratch / 'Gnew.scan.json'
    scan = json.loads(small_bytes(scanpath))
    scanned = {tuple(c) for c, *_ in scan['dup_class_elems']}
    if (scanned != {tuple(c) for c in cells} or scan['multi_unit_elems'] != 41
            or scan['mism'] != [] or scan['max_unit_decl'] != 4095):
        raise ValueError('3-11 scan does not support the count-split scope')
    return cells, [evidence(path), evidence(expected), evidence(scanpath)]


def successor_witness(path):
    w = json.loads(small_bytes(path))
    target = {'kind': 'frame', 'level': 0, 'cell': [0, 541], 'leaf': [928]}
    if (w['old_sha256'] != AU2 or w['new_sha256'] != AU3 or
            w['old_size'] != w['new_size'] or w['changed_leaf_list'] != [target] or
            w['confined_to_cell_0_541'] is not True):
        raise ValueError('successor witness hop/scope mismatch')
    end, nbytes = -1, 0
    for row in w['changed_ranges']:
        if row['start'] < end or row['end'] <= row['start']:
            raise ValueError('overlapping/invalid successor ranges')
        if any(row[side] != target for side in ('old', 'new')):
            raise ValueError('successor changes outside leaf 928')
        end = row['end']
        if end > w['old_size']:
            raise ValueError('successor range outside disc')
        nbytes += row['end'] - row['start']
    if nbytes != 146 or nbytes != w['changed_bytes']:
        raise ValueError('successor changed-byte total mismatch')
    return w


def measured_row(path, old_sha, new_sha, row):
    m = json.loads(small_bytes(path))
    if (m['kind'] != 'cell_diff' or [m['old_sha256'], m['new_sha256']] != [old_sha, new_sha]
            or m['protected_after_sha256'] != [old_sha, new_sha] or not m['protected_unchanged']):
        raise ValueError('measurement belongs to another hop or changed inputs')
    counts, levels, previous = Counter(), {}, None
    with Path(m['cells']['path']).open() as f:
        for c in csv.DictReader(f, delimiter='\t'):
            key = tuple(int(c[k]) for k in ('level', 'ix', 'iy'))
            if previous is not None and key <= previous:
                raise ValueError('cell list not sorted/unique')
            previous = key
            if c['status'] not in ('changed', 'added', 'removed'):
                raise ValueError('invalid change status')
            counts[c['status']] += 1
            levels.setdefault(str(key[0]), Counter())[c['status']] += 1
    if sha(m['cells']['path']) != m['cells']['sha256']:
        raise ValueError('measured list SHA mismatch')
    if dict(levels) != m['counts_by_level'] or any(counts[s] != m['counts'][s] for s in ('changed','added','removed')):
        raise ValueError('measured list count mismatch')
    if m['unexplained_count'] != sum(counts.values()):
        raise ValueError('new cell diff cannot silently explain cells')
    row.update(status='measured-identities-residual-causes', changed_count=sum(counts.values()),
               counts_by_level=levels, authoritative_list=m['cells'],
               unexplained_count=m['unexplained_count'], unexplained_cells=m['unexplained_cells'],
               confinement=m['confinement'], residuals=m['residuals'], measurement=evidence(path))
    return row


def publish(scratch, dest, au_diff=None, perth_diff=None, census=None):
    """Publish verified small witnesses or explicit missing-evidence residuals."""
    cells, supporting = retained37(scratch)
    successor = NAME_ANCHOR / 'witnesses/successor_diff.json'
    w = successor_witness(successor)
    common = {'signing_record': evidence(SIGN_RECORD)}

    def row(region, unit, start, end, **fields):
        return dict(common, region=region, signing_unit=unit, from_sha256=start, to_sha256=end,
                    **fields)

    rows = [row('AU', '3-11', AU0, AU1, status='retained-list-verified',
                changed_count=37, counts_by_level={'0': {'changed': 37}},
                authoritative_list=supporting[0], changed_cells=cells, supporting_evidence=supporting[1:],
                unexplained_count=0, unexplained_cells=[],
                confinement='Exactly 37 predicted L0 cells; 37/37, no extra cells.',
                residuals=['Pre-3-11 disc and old census not located; no fresh byte replay of this hop.',
                           'Historical review carries +60 bytes of non-payload growth without attribution.',
                           'Large Gnew.cells.tsv audit deferred to guarded Execute command.'])]
    for region, start, end, recorded, measurement in (
            ('AU', AU1, AU2, {'0':244060, '2':1944, '6':118, '8':1}, au_diff),
            ('Perth', P0, P1, {'0':784, '2':11}, perth_diff)):
        r = row(region, '3-14', start, end, status='residual-missing-cell-list', changed_count=None,
                counts_by_level=None, authoritative_list=None, unexplained_count=None,
                unexplained_cells={'selector': 'entire hop; exact identities unavailable'},
                recorded_counts_by_level=recorded, recorded_changed_count=sum(recorded.values()),
                recorded_added=0, recorded_removed=0,
                confinement='Historical cell census only; exact-cell confinement unproven.',
                residuals=['Retained changed-cell list and explanations.json not located in inventoried outputs.',
                           'Historical zero-unexplained census is not re-proven; '
                           + ('7 AU' if region == 'AU' else '3 Perth') + ' non-payload explanations were inference.'])
        if measurement:
            measured_row(measurement, start, end, r)
            measured = {lv: sum(v.values()) for lv, v in r['counts_by_level'].items()}
            r['matches_recorded_counts'] = (measured == recorded and all(
                not v.get('added', 0) and not v.get('removed', 0)
                for v in r['counts_by_level'].values()))
            if not r['matches_recorded_counts']:
                r['residuals'].append('Measured counts differ from the signed historical census; do not re-sign.')
        rows.append(r)
    rows.append(row('AU', 'plan 29', AU2, AU3, status='committed-leaf-proof-verified',
                    signing_record=evidence(PLAN29_RECORD), changed_count=1,
                    counts_by_level={'0': {'changed':1}}, changed_leaf_count=1, changed_bytes=w['changed_bytes'],
                    changed_cells=[[0,0,541]], changed_leaves=w['changed_leaf_list'],
                    authoritative_list=evidence(successor), unexplained_count=0, unexplained_cells=[],
                    confinement=w['confinement_rule'] + ' Leaf [928] only.', residuals=[]))
    for unit, start, record in (('3-11', P0, SIGN_RECORD), ('plan 29', P1, PLAN29_RECORD)):
        text = small_bytes(record).decode()
        if start not in text:
            raise ValueError('Perth unchanged record does not contain the full pin')
        rows.append(row('Perth', unit, start, start, status='unchanged-recorded', changed_count=0,
                        counts_by_level={}, authoritative_list=None, supporting_evidence=[evidence(record)],
                        unexplained_count=0, unexplained_cells=[],
                        confinement='N/A: signed record says Perth unchanged at this full digest.',
                        residuals=['Recorded equality reused; no fresh disc hash by this worker.']))
    if census:
        audit = json.loads(small_bytes(census))
        if (audit.get('kind') != 'census_audit' or audit.get('pass') is not True
                or audit.get('rows') != 3951970 or audit.get('expected_cells_present') != 37
                or audit.get('expected') != evidence(scratch / 'Gnew.expected37.txt')
                or Path(audit['path']).resolve() != (scratch / 'Gnew.cells.tsv').resolve()):
            raise ValueError('invalid 3-11 census audit')
        rows[0]['supporting_evidence'].append(evidence(census))
        rows[0]['census_audit'] = audit
        rows[0]['residuals'].pop()
    result = {'schema':1, 'disc_in_force_sha256':AU3, 'phase3_closed':False,
              'scope':'Existing signed hops; no new re-oracle. Unknown counts are null, never zero.',
              'hops':rows}
    dest.mkdir(parents=True, exist_ok=True)
    write_json(dest / 'oracle_chain.json', result)
    fields = ['region','signing_unit','from_sha256','to_sha256','status','changed_count',
              'changed_leaf_count','changed_bytes','counts_by_level','authoritative_list',
              'signing_record','supporting_evidence','confinement','unexplained_count',
              'unexplained_cells','recorded_changed_count','recorded_counts_by_level','residuals']
    with (dest / 'oracle_chain.tsv').open('w') as f:
        writer = csv.DictWriter(f, fields, delimiter='\t', lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            writer.writerow({k: json.dumps(v, sort_keys=True) if isinstance(v,(dict,list)) else v
                             for k,v in r.items()})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    d = sub.add_parser('diff', help='Execute-only streaming frame-to-cell comparison')
    for flag in ('old','new','out','cells','work-dir'):
        d.add_argument('--'+flag, type=Path, required=True)
    d.add_argument('--old-sha', required=True)
    d.add_argument('--new-sha', required=True)
    r = sub.add_parser('routed-diff', help='Execute-only routed/footprint supplement to diff (R1)')
    for flag in ('old','new','baseline','out','cells','work-dir'):
        r.add_argument('--'+flag, type=Path, required=True)
    r.add_argument('--old-sha', required=True)
    r.add_argument('--new-sha', required=True)
    c = sub.add_parser('check-census', help='Execute-only audit of retained large census')
    c.add_argument('--path', type=Path, required=True)
    c.add_argument('--expected', type=Path, required=True)
    c.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('publish', help='Publish small retained/measured evidence; no disc reads')
    p.add_argument('--scratch-3-11', type=Path, default=ROOT/'output/scratch-3-11')
    p.add_argument('--dest', type=Path, default=PLAN)
    p.add_argument('--au-diff', type=Path)
    p.add_argument('--perth-diff', type=Path)
    p.add_argument('--census', type=Path)
    args = vars(ap.parse_args())
    command = args.pop('command')
    try:
        if command == 'publish':
            args['scratch'] = args.pop('scratch_3_11')
            result = publish(**args)
        elif command == 'diff':
            result = diff(**args)
        elif command == 'routed-diff':
            result = routed_diff(**args)
        else:
            result = check_census(**args)
    except (ValueError, OSError, KeyError) as e:
        ap.exit(1, f'oracle_chain: {e}\n')
    print(json.dumps({'command':command, 'hops':len(result.get('hops',[])),
                      'counts':result.get('counts') or result.get('routed_counts')}, sort_keys=True))


if __name__ == '__main__':
    main()
