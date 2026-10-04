"""Bounded dump window I/O (plan 05, Phase 3, brief 3-01).

Owns window lifetimes for dump transforms and triage readers: at most one
source / destination / assignment window at a time, write-behind on completed
destination windows, and page-cache drop of consumed windows.  Transformation
semantics (joins, sorts, casts, aggregation) stay in the callers.

Default window is 65,536 rows.  Changing the window leaves bytes and aggregates
identical.  Zero-row mapped kinds are rejected (Assumption 7).  Offline helper:
no C layout declarations, no per-row Python kernels.
"""
from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
from typing import Iterator

import numpy as np

DEFAULT_WINDOW = 65536
SFR_WAIT_BEFORE, SFR_WRITE, SFR_WAIT_AFTER = 1, 2, 4

_libc = None


def sync_file_range(fd: int, off: int, n: int, flags: int) -> None:
    """Start/finish writeback of a file range (advisory; durability is the final fsync)."""
    global _libc
    fn = getattr(os, 'sync_file_range', None)
    try:
        if fn is not None:
            fn(fd, off, n, flags)
            return
        if _libc is None:
            _libc = ctypes.CDLL(None, use_errno=True)
            _libc.sync_file_range.argtypes = [
                ctypes.c_int, ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint]
        if _libc.sync_file_range(fd, off, n, flags) != 0:
            e = ctypes.get_errno()
            raise OSError(e, os.strerror(e))
    except (OSError, AttributeError) as e:
        if isinstance(e, OSError) and e.errno not in (
                errno.EINVAL, errno.ENOSYS, errno.ESPIPE, errno.EBADF):
            raise


def drop(fd: int, off: int, n: int) -> None:
    try:
        os.posix_fadvise(fd, off, n, os.POSIX_FADV_DONTNEED)
    except OSError as e:
        if e.errno not in (errno.EINVAL, errno.ESPIPE):
            raise


def pread_full(fd: int, mv: memoryview, off: int) -> None:
    done, want = 0, len(mv)
    while done < want:
        got = os.preadv(fd, [mv[done:]], off + done)
        if got <= 0:
            raise OSError(f'short read at offset {off + done}')
        done += got


def pwrite_full(fd: int, mv: memoryview, off: int) -> None:
    done, want = 0, len(mv)
    while done < want:
        done += os.pwritev(fd, [mv[done:]], off + done)


def file_rows(path, row_size: int, *, allow_empty: bool = False) -> int:
    """Return row count; reject non-multiples and, by default, zero-row kinds."""
    if row_size < 1:
        raise ValueError(f'row_size must be >= 1, got {row_size}')
    size = os.stat(path).st_size
    if size % row_size:
        raise ValueError(
            f'{path}: {size} bytes is not a whole number of {row_size}-byte rows')
    rows = size // row_size
    if rows == 0 and not allow_empty:
        raise ValueError(f'{path}: zero-row kinds are unsupported (as in the baseline)')
    return rows


class WindowedReader:
    """Read-only windowed dump reader over a reusable buffer.

    Each yielded ``(lo, n, arr)`` uses a view into the reader's buffer that is
    valid only until the next yield or ``close``.  Callers must release derived
    views before the next window (DESIGN contract).
    """

    def __init__(self, path, dtype, window_rows: int = DEFAULT_WINDOW, rows: int | None = None):
        if window_rows < 1:
            raise ValueError('window_rows must be >= 1')
        self.path = Path(path)
        self.dtype = np.dtype(dtype)
        self.row_size = int(self.dtype.itemsize)
        self.window_rows = int(window_rows)
        self.rows = file_rows(self.path, self.row_size) if rows is None else int(rows)
        if self.rows < 1:
            raise ValueError(f'{self.path}: zero-row kinds are unsupported (as in the baseline)')
        self._fd = os.open(self.path, os.O_RDONLY)
        self._buf = bytearray(self.window_rows * self.row_size)
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self) -> None:
        if not self._closed:
            os.close(self._fd)
            self._closed = True

    def window_bytes(self, n: int) -> memoryview:
        """Reusable buffer prefix for the current window (valid during windows() yield)."""
        return memoryview(self._buf)[:n * self.row_size]

    def windows(self) -> Iterator[tuple[int, int, np.ndarray]]:
        if self._closed:
            raise ValueError('reader is closed')
        for lo in range(0, self.rows, self.window_rows):
            n = min(self.window_rows, self.rows - lo)
            off, nb = lo * self.row_size, n * self.row_size
            mv = memoryview(self._buf)[:nb]
            pread_full(self._fd, mv, off)
            arr = np.frombuffer(self._buf, self.dtype, count=n)
            try:
                yield lo, n, arr
            finally:
                del arr
                mv.release()
                drop(self._fd, off, nb)


class WindowedWriter:
    """Writable destination with write-behind and page-cache drop of prior windows."""

    def __init__(self, path, row_size: int, rows: int, window_rows: int = DEFAULT_WINDOW,
                 exist_ok_trunc: bool = True):
        if window_rows < 1:
            raise ValueError('window_rows must be >= 1')
        if rows < 1:
            raise ValueError('zero-row kinds are unsupported (as in the baseline)')
        if row_size < 1:
            raise ValueError('row_size must be >= 1')
        self.path = Path(path)
        self.row_size = int(row_size)
        self.rows = int(rows)
        self.window_rows = int(window_rows)
        flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW
        if exist_ok_trunc:
            flags |= os.O_TRUNC
        self._fd = os.open(self.path, flags, 0o666)
        os.ftruncate(self._fd, self.rows * self.row_size)
        self._prev: tuple[int, int] | None = None
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def write_window(self, lo: int, n: int, mv: memoryview) -> None:
        if self._closed:
            raise ValueError('writer is closed')
        if n < 1 or lo < 0 or lo + n > self.rows:
            raise ValueError(f'bad window lo={lo} n={n} rows={self.rows}')
        off, nb = lo * self.row_size, n * self.row_size
        if len(mv) != nb:
            raise ValueError(f'buffer length {len(mv)} != {nb}')
        pwrite_full(self._fd, mv, off)
        sync_file_range(self._fd, off, nb, SFR_WRITE)
        if self._prev is not None:
            sync_file_range(
                self._fd, self._prev[0], self._prev[1],
                SFR_WAIT_BEFORE | SFR_WRITE | SFR_WAIT_AFTER)
            drop(self._fd, self._prev[0], self._prev[1])
        self._prev = (off, nb)

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._prev is not None:
                sync_file_range(
                    self._fd, self._prev[0], self._prev[1],
                    SFR_WAIT_BEFORE | SFR_WRITE | SFR_WAIT_AFTER)
                drop(self._fd, self._prev[0], self._prev[1])
            os.fsync(self._fd)
            if os.fstat(self._fd).st_size != self.rows * self.row_size:
                raise OSError(f'{self.path}: destination length differs from planned rows')
        finally:
            os.close(self._fd)
            self._closed = True


class AssignReader:
    """Bounded reader for little-endian u16 assignment files."""

    def __init__(self, path, rows: int, window_rows: int = DEFAULT_WINDOW):
        if window_rows < 1:
            raise ValueError('window_rows must be >= 1')
        self.path = Path(path)
        self.rows = int(rows)
        self.window_rows = int(window_rows)
        asize = os.stat(self.path).st_size
        if asize != self.rows * 2:
            raise ValueError(f'{self.path}: assignment length {asize} != {self.rows * 2}')
        self._fd = os.open(self.path, os.O_RDONLY)
        self._buf = bytearray(self.window_rows * 2)
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def close(self) -> None:
        if not self._closed:
            os.close(self._fd)
            self._closed = True

    def read_window(self, lo: int, n: int) -> np.ndarray:
        if self._closed:
            raise ValueError('reader is closed')
        amv = memoryview(self._buf)[:n * 2]
        pread_full(self._fd, amv, lo * 2)
        drop(self._fd, lo * 2, n * 2)
        arr = np.frombuffer(self._buf, '<u2', count=n).copy()
        amv.release()
        return arr


class AssignWriter:
    """Windowed u16 assignment writer with write-behind (classify output)."""

    def __init__(self, path, rows: int, window_rows: int = DEFAULT_WINDOW):
        if window_rows < 1:
            raise ValueError('window_rows must be >= 1')
        if rows < 1:
            raise ValueError('zero-row kinds are unsupported (as in the baseline)')
        self.path = Path(path)
        self.rows = int(rows)
        self.window_rows = int(window_rows)
        self.row_size = 2
        self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o666)
        os.ftruncate(self._fd, self.rows * 2)
        self._prev: tuple[int, int] | None = None
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def write_window(self, lo: int, n: int, values: np.ndarray) -> None:
        if self._closed:
            raise ValueError('writer is closed')
        if n < 1 or lo < 0 or lo + n > self.rows:
            raise ValueError(f'bad window lo={lo} n={n} rows={self.rows}')
        raw = np.asarray(values, dtype='<u2')
        if raw.shape != (n,):
            raise ValueError(f'assign window shape {raw.shape} != ({n},)')
        off, nb = lo * 2, n * 2
        mv = memoryview(raw.tobytes())  # small window; n <= window_rows
        # Prefer buffer protocol without full copy when contiguous little-endian u2:
        if raw.dtype == np.dtype('<u2') and raw.flags.c_contiguous:
            mv = memoryview(raw).cast('B')
        pwrite_full(self._fd, mv, off)
        sync_file_range(self._fd, off, nb, SFR_WRITE)
        if self._prev is not None:
            sync_file_range(
                self._fd, self._prev[0], self._prev[1],
                SFR_WAIT_BEFORE | SFR_WRITE | SFR_WAIT_AFTER)
            drop(self._fd, self._prev[0], self._prev[1])
        self._prev = (off, nb)

    def close(self) -> None:
        if self._closed:
            return
        try:
            if self._prev is not None:
                sync_file_range(
                    self._fd, self._prev[0], self._prev[1],
                    SFR_WAIT_BEFORE | SFR_WRITE | SFR_WAIT_AFTER)
                drop(self._fd, self._prev[0], self._prev[1])
            os.fsync(self._fd)
            if os.fstat(self._fd).st_size != self.rows * 2:
                raise OSError(f'{self.path}: assignment length differs from planned rows')
        finally:
            os.close(self._fd)
            self._closed = True
