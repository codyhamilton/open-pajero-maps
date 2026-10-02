#!/usr/bin/env python3
"""Residual byte146 extension with bounded windowed I/O (plan 05, Phase 1, brief 1-01).

Replaces the memory behaviour of the scratch-3-12 ``extend.py`` (whole-file
``copyfile`` + two whole-file memmaps) without changing a single output byte.
Output contract (DESIGN.md, "Contract (residual)"):

* key: exactly ``GROUP``, side key columns converted by the same NumPy
  field-assignment cast as the baseline (``sk[f]=side[f]``; ``i32`` wraps into
  ``u8``/``u16``); the default non-stable structured ``argsort`` is kept;
* byte146 of every row is 1 iff the first matching sorted side record has
  ``status == 1`` (0 for a miss, a missing side table or an empty one); it is
  always written from the flag and never copied from the source;
* assignments equal to 65535 select accounting rows only;
* bytes ``[0,146)`` and ``[147,152)`` (NaN payloads, padding) and row order are
  copied untouched; manifest and ``joined_counts.json`` equal the baseline's.

Memory: one source/destination window (a single reusable buffer) and one
assignment window at a time, ``window_rows`` rows each (default 65,536).  Each
completed destination window starts writeback (``sync_file_range``) and the
previous window is waited on and dropped from the page cache
(``posix_fadvise(DONTNEED)``); consumed source windows are dropped too.  The
final ``fsync``/close are unchanged.  Production paths run no byte assertions;
``--verify`` re-streams source and destination in the same windows and checks
every byte outside byte146.  Offline tool: NumPy bulk operations only.
"""
from __future__ import annotations

import argparse
import collections
import ctypes
import errno
import json
import os
import sys
from pathlib import Path

import numpy as np

GROUP = ('level', 'ix', 'iy', 'code', 'p0', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'shape')
TS = {'f64': '<f8', 'i32': '<i4', 'u16': '<u2', 'u8': 'u1'}
ROW_SIZE = 152
FLAG_OFFSET = 146
RESIDUAL = 65535
DEFAULT_WINDOW = 65536

DEFAULT_SRC = 'output/scratch-3-11/dump_new_ext'
DEFAULT_SIDE = 'output/scratch-3-12'
DEFAULT_ASSIGN = 'output/scratch-3-11/classify_new'
DEFAULT_DST = 'output/scratch-3-12/dump_ext'
DEFAULT_COUNTS = 'output/scratch-3-12/joined_counts.json'

_SFR_WAIT_BEFORE, _SFR_WRITE, _SFR_WAIT_AFTER = 1, 2, 4
_libc = None


class VerifyError(Exception):
    pass


def _sync_file_range(fd: int, off: int, n: int, flags: int) -> None:
    """Start/finish writeback of a file range (advisory; durability is the final fsync)."""
    global _libc
    fn = getattr(os, 'sync_file_range', None)
    try:
        if fn is not None:
            fn(fd, off, n, flags)
            return
        if _libc is None:
            _libc = ctypes.CDLL(None, use_errno=True)
            _libc.sync_file_range.argtypes = [ctypes.c_int, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint]
        if _libc.sync_file_range(fd, off, n, flags) != 0:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
    except (OSError, AttributeError) as e:
        if isinstance(e, OSError) and e.errno not in (errno.EINVAL, errno.ENOSYS, errno.ESPIPE, errno.EBADF):
            raise


def _drop(fd: int, off: int, n: int) -> None:
    try:
        os.posix_fadvise(fd, off, n, os.POSIX_FADV_DONTNEED)
    except OSError as e:
        if e.errno not in (errno.EINVAL, errno.ESPIPE):
            raise


def _pread_full(fd: int, mv: memoryview, off: int) -> None:
    done, want = 0, len(mv)
    while done < want:
        got = os.preadv(fd, [mv[done:]], off + done)
        if got <= 0:
            raise OSError(f'short read at offset {off + done}')
        done += got


def _pwrite_full(fd: int, mv: memoryview, off: int) -> None:
    done, want = 0, len(mv)
    while done < want:
        done += os.pwritev(fd, [mv[done:]], off + done)


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


def _side_index(path: Path | None, dt: np.dtype):
    """Sorted side key array and status flags, built exactly as the baseline."""
    if path is None:
        return None, None
    side = np.load(path)
    kd = np.dtype([(k, dt[k]) for k in GROUP])
    sk = np.empty(len(side), kd)
    for f in GROUP:
        sk[f] = side[f]
    order = np.argsort(sk)
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
        size = os.stat(src).st_size
        if size % ROW_SIZE:
            raise ValueError(f'{kind}: {size} bytes is not a whole number of {ROW_SIZE}-byte rows')
        rows = size // ROW_SIZE
        if rows == 0:
            raise ValueError(f'{kind}: zero-row kinds are unsupported (as in the baseline)')
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
    sfd = os.open(src, os.O_RDONLY)
    afd = os.open(assign_path, os.O_RDONLY)
    dfd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o666)
    buf = bytearray(window_rows * ROW_SIZE)
    abuf = bytearray(window_rows * 2)
    try:
        prev = None  # (offset, nbytes) of the previous destination window
        for lo in range(0, rows, window_rows):
            n = min(window_rows, rows - lo)
            off, nb = lo * ROW_SIZE, n * ROW_SIZE
            mv = memoryview(buf)[:nb]
            amv = memoryview(abuf)[:n * 2]
            _pread_full(sfd, mv, off)
            _drop(sfd, off, nb)
            _pread_full(afd, amv, lo * 2)
            _drop(afd, lo * 2, n * 2)
            win = np.frombuffer(buf, dt, count=n)
            flag = _flags(win, sk, sf, kd)
            _count_window(win, flag, np.frombuffer(abuf, '<u2', count=n), ct)
            np.frombuffer(buf, 'u1', count=nb).reshape(n, ROW_SIZE)[:, FLAG_OFFSET] = flag
            _pwrite_full(dfd, mv, off)
            _sync_file_range(dfd, off, nb, _SFR_WRITE)
            if prev is not None:
                _sync_file_range(dfd, prev[0], prev[1], _SFR_WAIT_BEFORE | _SFR_WRITE | _SFR_WAIT_AFTER)
                _drop(dfd, prev[0], prev[1])
            prev = (off, nb)
            del win, flag
            mv.release()
            amv.release()
        if prev is not None:
            _sync_file_range(dfd, prev[0], prev[1], _SFR_WAIT_BEFORE | _SFR_WRITE | _SFR_WAIT_AFTER)
            _drop(dfd, prev[0], prev[1])
        os.fsync(dfd)
        if os.fstat(dfd).st_size != rows * ROW_SIZE:
            raise OSError(f'{dest}: destination length differs from source')
    finally:
        os.close(dfd)
        os.close(afd)
        os.close(sfd)


def _verify_kind(kind, src, dest, rows, dt, kd, sk, sf, window_rows) -> None:
    """Stream source and destination in windows; every byte outside byte146 must match."""
    if os.stat(dest).st_size != rows * ROW_SIZE:
        raise VerifyError(f'{kind}: destination length differs from source')
    sfd = os.open(src, os.O_RDONLY)
    dfd = os.open(dest, os.O_RDONLY)
    sbuf = bytearray(window_rows * ROW_SIZE)
    dbuf = bytearray(window_rows * ROW_SIZE)
    try:
        for w, lo in enumerate(range(0, rows, window_rows)):
            n = min(window_rows, rows - lo)
            off, nb = lo * ROW_SIZE, n * ROW_SIZE
            smv, dmv = memoryview(sbuf)[:nb], memoryview(dbuf)[:nb]
            _pread_full(sfd, smv, off)
            _pread_full(dfd, dmv, off)
            s = np.frombuffer(sbuf, 'u1', count=nb).reshape(n, ROW_SIZE)
            d = np.frombuffer(dbuf, 'u1', count=nb).reshape(n, ROW_SIZE)
            flag = _flags(np.frombuffer(sbuf, dt, count=n), sk, sf, kd)
            ok = (np.array_equal(s[:, :FLAG_OFFSET], d[:, :FLAG_OFFSET])
                  and np.array_equal(s[:, FLAG_OFFSET + 1:], d[:, FLAG_OFFSET + 1:])
                  and np.array_equal(d[:, FLAG_OFFSET], flag))
            del s, d, flag
            smv.release()
            dmv.release()
            _drop(sfd, off, nb)
            _drop(dfd, off, nb)
            if not ok:
                raise VerifyError(f'{kind}: mismatch in window {w} (rows {lo}..{lo + n - 1})')
    finally:
        os.close(dfd)
        os.close(sfd)


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Residual byte146 extension with bounded windowed I/O.')
    ap.add_argument('--src', default=DEFAULT_SRC, help='source dump dir (read-only)')
    ap.add_argument('--side-dir', default=DEFAULT_SIDE, help='dir holding side_<kind>.npy')
    ap.add_argument('--assign-dir', default=DEFAULT_ASSIGN, help='dir holding assign_<kind>.u16')
    ap.add_argument('--dst', default=DEFAULT_DST, help='destination dump dir')
    ap.add_argument('--counts', default=DEFAULT_COUNTS, help='joined_counts.json path')
    ap.add_argument('--window-rows', type=int, default=DEFAULT_WINDOW)
    ap.add_argument('--verify', action='store_true', help='after writing, stream-check every byte outside byte146')
    ap.add_argument('--verify-only', action='store_true', help='only stream-check an existing destination')
    a = ap.parse_args(argv)
    try:
        extend_residual(a.src, a.side_dir, a.assign_dir, a.dst, a.counts, a.window_rows,
                        verify=a.verify, verify_only=a.verify_only)
    except VerifyError as e:
        print('VERIFY FAILED:', e, file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
