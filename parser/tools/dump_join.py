#!/usr/bin/env python3
"""Residual byte146 and 3-07 s02 extensions with bounded windowed I/O (plan 05).

Phase 1 residual contract is unchanged; Phase 3 moves the I/O boundary into
``kiwiw.dump_io`` and adds the 3-07 adapter (stable side sort, 144→152 rebuild,
byte144 / s02_producer_verified, boundary-only scope).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

import numpy as np

_PARSER = Path(__file__).resolve().parent.parent
if str(_PARSER) not in sys.path:
    sys.path.insert(0, str(_PARSER))
from kiwiw import dump_io  # noqa: E402

GROUP = ('level', 'ix', 'iy', 'code', 'p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'shape')
TS = {'f64': '<f8', 'i32': '<i4', 'u16': '<u2', 'u8': 'u1'}
ROW_SIZE = 152
FLAG_OFFSET = 146
RESIDUAL = 65535
DEFAULT_WINDOW = dump_io.DEFAULT_WINDOW
INT32_MIN = np.iinfo(np.int32).min

DEFAULT_SRC = 'output/scratch-3-11/dump_new_ext'
DEFAULT_SIDE = 'output/scratch-3-12'
DEFAULT_ASSIGN = 'output/scratch-3-11/classify_new'
DEFAULT_DST = 'output/scratch-3-12/dump_ext'
DEFAULT_COUNTS = 'output/scratch-3-12/joined_counts.json'

# 3-07 defaults (relative paths hard-coded by the frozen baseline)
S02_DEFAULT_DUMP = 'output/scratch-3-03/dump'
S02_DEFAULT_ROOT = 'output/scratch-3-07'
S02_DEFAULT_SIDE = 'output/scratch-3-07/side_background_boundary.npy'
S02_DEFAULT_DST = 'output/scratch-3-07/dump_attempt3'
S02_SRC_ROW = 144
S02_FLAG_OFFSET = 144


class VerifyError(Exception):
    pass


def layout_dtype(fields: list[dict]) -> np.dtype:
    """Manifest-derived aligned layout, validated for the byte146 extension."""
    dt = np.dtype([(f['name'], TS[f['type']]) for f in fields], align=True)
    if dt.itemsize != ROW_SIZE:
        raise ValueError(f'layout row size {dt.itemsize} != {ROW_SIZE}')
    for name in GROUP:
        if name not in dt.names:
            raise ValueError(f'layout lacks key field {name!r}')
    for name in dt.names:
        off = dt.fields[name][1]
        if off <= FLAG_OFFSET < off + dt.fields[name][0].itemsize:
            raise ValueError(f'byte{FLAG_OFFSET} is inside named field {name!r}; not padding')
    return dt


def _side_header(path: Path) -> tuple[int, np.dtype]:
    with open(path, 'rb') as f:
        ver = np.lib.format.read_magic(f)
        if ver == (1, 0):
            shape, _fo, dtype = np.lib.format.read_array_header_1_0(f)
        elif ver == (2, 0):
            shape, _fo, dtype = np.lib.format.read_array_header_2_0(f)
        else:
            a = np.load(path)
            return len(a), a.dtype
    if len(shape) != 1:
        raise ValueError(f'{path}: side table must be 1-D')
    return shape[0], dtype


def _side_index(path: Path | None, dt: np.dtype, *, stable: bool = False):
    """Sorted side key array and status flags."""
    if path is None:
        return None, None
    side = np.load(path)
    kd = np.dtype([(k, dt[k]) for k in GROUP])
    sk = np.empty(len(side), kd)
    for f in GROUP:
        sk[f] = side[f]
    order = np.argsort(sk, kind='stable') if stable else np.argsort(sk)
    sk = sk[order]
    sf = (side['status'][order] == 1).astype('u1')
    return sk, sf


def _flags(win: np.ndarray, sk, sf, kd: np.dtype) -> np.ndarray:
    if sk is None or len(sk) == 0:
        return np.zeros(len(win), 'u1')
    keys = np.empty(len(win), kd)
    for f in GROUP:
        keys[f] = win[f]
    pos = np.searchsorted(sk, keys)
    pc = np.minimum(pos, len(sk) - 1)
    ok = (pos < len(sk)) & (sk[pc] == keys)
    return np.where(ok, sf[pc], 0)


def _count_window(win: np.ndarray, flag: np.ndarray, assign: np.ndarray, ct) -> None:
    res = assign == RESIDUAL
    if not res.any():
        return
    lv = win['level'][res].astype(np.int64)
    cd = win['code'][res].astype(np.int64)
    comb = (lv << 32) | (cd & 0xFFFFFFFF)
    u, inv = np.unique(comb, return_inverse=True)
    inv = inv.reshape(-1)
    fl = flag[res] == 1
    total = np.bincount(inv, minlength=len(u))
    moved = np.bincount(inv[fl], minlength=len(u))
    for k, t, m in zip(u.tolist(), total.tolist(), moved.tolist()):
        level = k >> 32
        code = k & 0xFFFFFFFF
        if code >= 0x80000000:
            code -= 0x100000000
        ct[level, code, 'moved'] += m
        ct[level, code, 'remaining'] += t - m


def _plan(man, src_dir: Path, side_dir: Path, assign_dir: Path, dst_dir: Path, dt: np.dtype, need_assign: bool):
    plan = []
    for kind, info in man['kinds'].items():
        if 'row_size' in info and info['row_size'] != ROW_SIZE:
            raise ValueError(f'{kind}: manifest row_size {info["row_size"]} != {ROW_SIZE}')
        src = src_dir / info['file']
        dest = dst_dir / info['file']
        rows = dump_io.file_rows(src, ROW_SIZE)
        if os.path.lexists(dest) and (os.path.islink(dest) or os.path.samefile(src, dest)):
            raise ValueError(f'{kind}: destination {dest} is a symlink or the source itself')
        side_path = side_dir / f'side_{kind}.npy'
        if side_path.exists():
            n, sdt = _side_header(side_path)
            missing = [f for f in (*GROUP, 'status') if f not in (sdt.names or ())]
            if missing:
                raise ValueError(f'{side_path}: side table lacks fields {missing}')
        else:
            side_path = None
        assign_path = assign_dir / f'assign_{kind}.u16'
        if need_assign:
            asize = os.stat(assign_path).st_size
            if asize != rows * 2:
                raise ValueError(f'{kind}: assignment length {asize} != {rows * 2}')
        plan.append((kind, info, src, dest, side_path, assign_path, rows))
    return plan


def _extend_kind(src, dest, assign_path, rows, dt, kd, sk, sf, window_rows, ct) -> None:
    with dump_io.WindowedReader(src, dt, window_rows, rows=rows) as reader, \
            dump_io.AssignReader(assign_path, rows, window_rows) as areader, \
            dump_io.WindowedWriter(dest, ROW_SIZE, rows, window_rows) as writer:
        for lo, n, win in reader.windows():
            assign = areader.read_window(lo, n)
            flag = _flags(win, sk, sf, kd)
            _count_window(win, flag, assign, ct)
            mv = reader.window_bytes(n)
            np.frombuffer(mv, 'u1', count=n * ROW_SIZE).reshape(n, ROW_SIZE)[:, FLAG_OFFSET] = flag
            writer.write_window(lo, n, mv)
            del win, flag, assign
            mv.release()


def _verify_kind(kind, src, dest, rows, dt, kd, sk, sf, window_rows) -> None:
    if os.stat(dest).st_size != rows * ROW_SIZE:
        raise VerifyError(f'{kind}: destination length differs from source')
    with dump_io.WindowedReader(src, dt, window_rows, rows=rows) as sreader, \
            dump_io.WindowedReader(dest, dt, window_rows, rows=rows) as dreader:
        # zip windows: both iterate independently with same sizes
        sit = sreader.windows()
        dit = dreader.windows()
        for w, ((lo, n, sarr), (_lo2, n2, darr)) in enumerate(zip(sit, dit)):
            assert n == n2 and lo == _lo2
            sb = sreader.window_bytes(n)
            db = dreader.window_bytes(n)
            s = np.frombuffer(sb, 'u1', count=n * ROW_SIZE).reshape(n, ROW_SIZE)
            d = np.frombuffer(db, 'u1', count=n * ROW_SIZE).reshape(n, ROW_SIZE)
            flag = _flags(sarr, sk, sf, kd)
            ok = (np.array_equal(s[:, :FLAG_OFFSET], d[:, :FLAG_OFFSET])
                  and np.array_equal(s[:, FLAG_OFFSET + 1:], d[:, FLAG_OFFSET + 1:])
                  and np.array_equal(d[:, FLAG_OFFSET], flag))
            del s, d, flag, sarr, darr
            sb.release()
            db.release()
            if not ok:
                raise VerifyError(f'{kind}: mismatch in window {w} (rows {lo}..{lo + n - 1})')


def extend_residual(src_dir, side_dir, assign_dir, dst_dir, counts_path, window_rows: int = DEFAULT_WINDOW,
                    verify: bool = False, verify_only: bool = False, log=lambda s: print(s, flush=True)) -> int:
    """Write the byte146-extended dump + manifest + counts; returns total moved rows."""
    if window_rows < 1:
        raise ValueError('window_rows must be >= 1')
    src_dir, side_dir, assign_dir, dst_dir = Path(src_dir), Path(side_dir), Path(assign_dir), Path(dst_dir)
    man = json.loads((src_dir / 'dump_manifest.json').read_text())
    dt = layout_dtype(man['fields'])
    kd = np.dtype([(k, dt[k]) for k in GROUP])
    man = json.loads(json.dumps(man))
    man['fields'].append({'name': 'residual_crossing_verified', 'type': 'u8'})
    plan = _plan(man, src_dir, side_dir, assign_dir, dst_dir, dt, need_assign=not verify_only)
    if verify_only:
        for kind, info, src, dest, side_path, _a, rows in plan:
            sk, sf = _side_index(side_path, dt)
            _verify_kind(kind, src, dest, rows, dt, kd, sk, sf, window_rows)
            log(f'VERIFIED {kind}')
        return 0
    dst_dir.mkdir(exist_ok=True)
    counts, total = [], 0
    for kind, info, src, dest, side_path, assign_path, rows in plan:
        sk, sf = _side_index(side_path, dt)
        ct = collections.Counter()
        _extend_kind(src, dest, assign_path, rows, dt, kd, sk, sf, window_rows, ct)
        if verify:
            _verify_kind(kind, src, dest, rows, dt, kd, sk, sf, window_rows)
        del sk, sf
        info['fields'] = man['fields']
        info['row_size'] = dt.itemsize
        for (level, typ, what), n in sorted(ct.items()):
            counts.append({'kind': kind, 'level': level, 'type': typ, 'outcome': what, 'rows': n})
        moved = sum(n for (l, t, w), n in ct.items() if w == 'moved')
        total += moved
        log(f'EXTENDED {kind} moved {moved}')
    man['extension_3_12'] = {
        'source': str(src_dir), 'side_tables': str(side_dir / 'side_<kind>.npy'),
        'new_field': 'residual_crossing_verified', 'offset': 146, 'row_size': 152,
        'other_bytes_unchanged': True,
        'predicate': 'status==1: unique exact original producer; not E1 cover; explicit closed ring; longest closing edge has proper nonadjacent crossing',
        'first_matching_rule_preserved': True}
    (dst_dir / 'dump_manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    Path(counts_path).write_text(json.dumps({'strata': counts, 'moved_spool': total}, indent=2) + '\n')
    log(f'MOVED {total}')
    return total


def _s02_side_index(side_path: Path, old_dt: np.dtype):
    side = np.load(side_path)
    kd = np.dtype([(k, old_dt[k]) for k in GROUP])
    skey = np.empty(len(side), kd)
    for k in GROUP:
        skey[k] = side[k]
    order = np.argsort(skey, kind='stable')
    skey = skey[order]
    flags = (side['status'][order] == 1).astype('u1')
    expected = int(side['rows'][side['status'] == 1].sum()) if 'rows' in side.dtype.names else None
    return skey, flags, expected, kd


def extend_s02_producer(dump_dir, side_path, dst_dir, window_rows: int = DEFAULT_WINDOW,
                        log=lambda s: print(s, flush=True)) -> int:
    """144→152 extension with s02_producer_verified at byte144 (3-07 contract)."""
    if window_rows < 1:
        raise ValueError('window_rows must be >= 1')
    dump_dir, side_path, dst_dir = Path(dump_dir), Path(side_path), Path(dst_dir)
    manifest = json.loads((dump_dir / 'dump_manifest.json').read_text())
    # Source layout = manifest fields before the extension field.
    src_fields = list(manifest['fields'])
    old = np.dtype([(f['name'], TS[f['type']]) for f in src_fields], align=True)
    if old.itemsize != S02_SRC_ROW:
        raise ValueError(f'source layout row size {old.itemsize} != {S02_SRC_ROW}')
    man = json.loads(json.dumps(manifest))
    man['fields'] = list(man['fields']) + [{'name': 's02_producer_verified', 'type': 'u8'}]
    dt = np.dtype([(f['name'], TS[f['type']]) for f in man['fields']], align=True)
    if dt.fields['s02_producer_verified'][1] != S02_FLAG_OFFSET:
        raise ValueError(f's02 field offset {dt.fields["s02_producer_verified"][1]} != {S02_FLAG_OFFSET}')
    if dt.itemsize != ROW_SIZE:
        raise ValueError(f'dest layout row size {dt.itemsize} != {ROW_SIZE}')
    skey, flags, expected, kd = _s02_side_index(side_path, old)
    dst_dir.mkdir(exist_ok=True)
    matches = 0
    out_buf = bytearray(window_rows * ROW_SIZE)
    for kind, info in man['kinds'].items():
        src = dump_dir / info['file']
        dest = dst_dir / info['file']
        rows = dump_io.file_rows(src, S02_SRC_ROW)
        count = 0
        with dump_io.WindowedReader(src, old, window_rows, rows=rows) as reader, \
                dump_io.WindowedWriter(dest, ROW_SIZE, rows, window_rows) as writer:
            for lo, n, b in reader.windows():
                o = np.frombuffer(out_buf, dt, count=n)
                o[:] = np.zeros(1, dt)
                for k in old.names:
                    o[k] = b[k]
                if kind == 'background_boundary':
                    keys = np.empty(n, kd)
                    for k in GROUP:
                        keys[k] = b[k]
                    pos = np.searchsorted(skey, keys)
                    ok = pos < len(skey)
                    pos = np.minimum(pos, len(skey) - 1)
                    ok &= skey[pos] == keys
                    scope = (b['level'] == 0) & (b['code'] == 291) & (b['src_ix'] == INT32_MIN)
                    o['s02_producer_verified'] = np.where(ok & scope, flags[pos], 0)
                    count += int(o['s02_producer_verified'].sum())
                    del keys
                mv = memoryview(out_buf)[:n * ROW_SIZE]
                writer.write_window(lo, n, mv)
                mv.release()
                del o, b
        info['row_size'] = dt.itemsize
        log(f'EXTENDED {kind} {rows} producer_verified {count}')
        if kind == 'background_boundary':
            matches = count
    if expected is not None and matches != expected:
        raise AssertionError(f'aggregate match assert failed: {matches} != {expected}')
    man['extension'] = {
        'original_dump': str(dump_dir),
        'side_table': str(side_path),
        'field': 's02_producer_verified',
        'method': 'exact group key join; unique actual producer with crossing longest closing edge; all unvisited/mixed/other producers zero',
        'original_fields_unchanged': True}
    (dst_dir / 'dump_manifest.json').write_text(json.dumps(man, indent=2))
    log(f'DONE {dt.itemsize} {matches}')
    return matches


# Plan 28: completeness-only, exact native item key (including vert).
OTHER_NATIVE = (*GROUP, 'vert')
BASELINE_SHA256 = '1a91b1c26e474b2c689fef9811b73878a4ead144db97eea3aaf6f442ed30d323'


def _digest(path):
    import hashlib
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def other_selection(rows, keys=None, max_rows=None):
    selected = sorted(set(range(rows) if keys is None else keys))
    if not selected or any(k < 0 or k >= rows for k in selected):
        raise ValueError('empty or out-of-range source dump rows')
    if max_rows is not None:
        if max_rows < 1:
            raise ValueError('max_rows must be >= 1')
        selected = selected[:max_rows]
    return selected


def extend_other_mechanism(src_dir, side_path, dst_dir, window_rows=DEFAULT_WINDOW,
                           *, source_sha256=BASELINE_SHA256, keys=None, max_rows=None,
                           log=lambda s: print(s, flush=True)):
    """144→152 exact TSV join, verifying source hash and ALL 144 original bytes.

    Only selected rows are written for a window; their original dump_row mapping
    is retained in the manifest. Missing/duplicate/foreign side keys are errors.
    Side storage is bounded by the selected completeness row count, never a disc.
    """
    import csv
    if window_rows < 1:
        raise ValueError('window_rows must be >= 1')
    src_dir, side_path, dst_dir = map(Path, (src_dir, side_path, dst_dir))
    manifest = json.loads((src_dir / 'dump_manifest.json').read_text())
    if set(manifest['kinds']) != {'completeness'}:
        raise ValueError('other_mechanism requires a completeness-only manifest')
    fields = manifest['fields']
    old = np.dtype([(f['name'], TS[f['type']]) for f in fields], align=True)
    if old.itemsize != 144 or any(k not in old.names for k in OTHER_NATIVE):
        raise ValueError('expected original 144-byte native-key layout')
    info = manifest['kinds']['completeness']
    if Path(info['file']).name != info['file']:
        raise ValueError('source file must be a basename')
    src, dest = src_dir / info['file'], dst_dir / info['file']
    rows = dump_io.file_rows(src, 144)
    if info['rows'] != rows or info.get('row_size', 144) != 144:
        raise ValueError('source manifest size/count mismatch')
    if src_dir.resolve() == dst_dir.resolve() or dst_dir.is_symlink():
        raise ValueError('destination is the source or a symlink')
    inputs = (src, side_path, src_dir / 'dump_manifest.json')
    for target in (dest, dst_dir / 'dump_manifest.json'):
        if (target.is_symlink() or target.resolve() in tuple(p.resolve() for p in inputs)
                or (target.exists() and any(target.samefile(p) for p in inputs))):
            raise ValueError('destination aliases an input or is a symlink')
    before_sha = _digest(src)
    if before_sha != source_sha256:
        raise ValueError(f'source sha256 {before_sha} != {source_sha256}')
    selected = other_selection(rows, keys, max_rows)
    side = {}
    with side_path.open() as fh:
        for r in csv.DictReader(fh, delimiter='\t'):
            key = tuple(int(r[k]) for k in OTHER_NATIVE)
            rid, code = int(r['dump_row']), int(r['other_mechanism'])
            if rid in side or code not in (0, 4, 5, 7, 8):
                raise ValueError('duplicate side row or invalid mechanism code')
            side[rid] = key, code
            if len(side) > rows:
                raise ValueError('side table exceeds source row count')
    if set(side) != set(selected):
        raise ValueError('side table must cover exactly the selected source rows')
    # Validate every selected key before creating any output.
    with src.open('rb') as fh:
        for rid in selected:
            fh.seek(rid * 144)
            r = np.frombuffer(fh.read(144), old, count=1)[0]
            if tuple(int(r[k]) for k in OTHER_NATIVE) != side[rid][0]:
                raise ValueError(f'side native key differs at dump_row {rid}')
    man = json.loads(json.dumps(manifest))
    man['fields'] = fields + [{'name': 's02_producer_verified', 'type': 'u8'},
                              {'name': 'other_mechanism', 'type': 'u8'}]
    new = np.dtype([(f['name'], TS[f['type']]) for f in man['fields']], align=True)
    if new.itemsize != 152 or new.fields['other_mechanism'][1] != 145:
        raise ValueError('byte-145 extension layout mismatch')
    dst_dir.mkdir(parents=True, exist_ok=True)
    # Reusable windows only. Preserve padding and NaN payloads by copying bytes.
    with dump_io.WindowedReader(src, old, window_rows, rows=rows) as reader, \
            dump_io.WindowedWriter(dest, 152, len(selected), window_rows) as writer:
        out = np.zeros((window_rows, 152), 'u1')
        offset = 0
        chosen = set(selected)
        for lo, n, arr in reader.windows():
            ids = [rid for rid in range(lo, lo + n) if rid in chosen]
            if not ids:
                del arr
                continue
            out[:len(ids)] = 0
            mv = reader.window_bytes(n)
            raw = np.frombuffer(mv, 'u1').reshape(n, 144)
            for i, rid in enumerate(ids):
                out[i, :144] = raw[rid - lo]
                out[i, 145] = side[rid][1]
            del raw, arr
            mv.release()
            mv = memoryview(out[:len(ids)]).cast('B')
            writer.write_window(offset, len(ids), mv)
            mv.release()
            offset += len(ids)
    # Independently compare raw source rows and complete destination tails.
    with src.open('rb') as fh, dump_io.WindowedReader(dest, new, window_rows) as reader:
        for lo, n, arr in reader.windows():
            mv = reader.window_bytes(n)
            raw = np.frombuffer(mv, 'u1').reshape(n, 152)
            for i, rid in enumerate(selected[lo:lo + n]):
                fh.seek(rid * 144)
                if (raw[i, :144].tobytes() != fh.read(144) or raw[i, 144] != 0
                        or raw[i, 145] != side[rid][1] or raw[i, 146:].any()):
                    raise VerifyError(f'completeness: byte mismatch at dump_row {rid}')
            del arr, raw
            mv.release()
    if _digest(src) != before_sha:
        raise VerifyError('source changed while extending')
    man['row_size'] = 152
    man['kinds']['completeness'].update(fields=man['fields'], row_size=152, rows=len(selected))
    man['extension_other_mechanism'] = {
        'source': str(src_dir), 'source_sha256': before_sha, 'side_table': str(side_path),
        'side_sha256': _digest(side_path), 'offset': 145, 'source_dump_rows': selected,
        'original_144_bytes_verified': True, 'byte144_zero': True,
        'destination_sha256': _digest(dest)}
    (dst_dir / 'dump_manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    log(f'EXTENDED completeness {len(selected)}; original 144 bytes VERIFIED; byte144 zero')
    return len(selected)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Bounded dump join / extension adapters.')
    ap.add_argument('--mode', choices=('residual', 's02', 'other_mechanism'), default='residual')
    # residual
    ap.add_argument('--src', default=DEFAULT_SRC, help='source dump dir (read-only)')
    ap.add_argument('--side-dir', default=DEFAULT_SIDE, help='dir holding side_<kind>.npy')
    ap.add_argument('--assign-dir', default=DEFAULT_ASSIGN, help='dir holding assign_<kind>.u16')
    ap.add_argument('--dst', default=DEFAULT_DST, help='destination dump dir')
    ap.add_argument('--counts', default=DEFAULT_COUNTS, help='joined_counts.json path')
    ap.add_argument('--window-rows', type=int, default=DEFAULT_WINDOW)
    ap.add_argument('--verify', action='store_true', help='after writing, stream-check every byte outside byte146')
    ap.add_argument('--verify-only', action='store_true', help='only stream-check an existing destination')
    # s02
    ap.add_argument('--dump', default=S02_DEFAULT_DUMP, help='3-07 source dump dir (144-byte)')
    ap.add_argument('--side', default=S02_DEFAULT_SIDE, help='3-07 side_background_boundary.npy')
    ap.add_argument('--s02-dst', default=S02_DEFAULT_DST, help='3-07 destination dump dir')
    # other_mechanism: --src, --side (TSV), --dst; selection uses original dump_row.
    ap.add_argument('--source-sha256', default=BASELINE_SHA256)
    ap.add_argument('--keys', help='comma-separated original dump_row ids (new mode only)')
    ap.add_argument('--max-rows', type=int, help='limit selected rows (new mode only)')
    a = ap.parse_args(argv)
    try:
        if a.mode == 'other_mechanism':
            keys = None if a.keys is None else [int(k) for k in a.keys.split(',')]
            extend_other_mechanism(a.src, a.side, a.dst, a.window_rows,
                                   source_sha256=a.source_sha256, keys=keys, max_rows=a.max_rows)
        elif a.mode == 's02':
            extend_s02_producer(a.dump, a.side, a.s02_dst, a.window_rows)
        else:
            extend_residual(a.src, a.side_dir, a.assign_dir, a.dst, a.counts, a.window_rows,
                            verify=a.verify, verify_only=a.verify_only)
    except VerifyError as e:
        print('VERIFY FAILED:', e, file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
