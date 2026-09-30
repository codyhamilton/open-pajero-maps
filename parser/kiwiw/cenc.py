"""ctypes bindings for the C build kernels in `_cenc.so` (plan 03).

`cbuild.build_ext()` compiles the sources on demand (gcc, `-ffp-contract=off`)
into `_cenc.so` beside this file; a failed build raises (no Python fallback).
Entry points: E1 (`e1`) and E2 (`e2`), each called once per row range
(DESIGN.md Contract B); E2 also divides, retiles, trims and adds the name halo
(3C-09), so nothing per (sub-)cell crosses this boundary any more. What is
left besides is `bg_shape_records` (`kw_bg_shape`, used by `synth` and its
tests only, off the build path; 3C-12 deletes it with `synth`), the
column-name accessor and the assembly copy helpers (`lib()`).
"""
from __future__ import annotations

import ctypes
import time
from array import array
from itertools import chain
from pathlib import Path

from . import cbuild

_SO = Path(__file__).with_name("_cenc.so")
_lib = None
_tried = False


def _load_lib():
    global _lib, _tried
    if _tried:
        return _lib
    try:
        cbuild.build_ext()  # compiles on demand through cbuild (3C-02); raises on failure
        lib = ctypes.CDLL(str(_SO))
        lib.kw_bg_shape.restype = ctypes.c_int64
        lib.kw_bg_shape.argtypes = [
            ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
            ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
            ctypes.c_double, ctypes.c_void_p]
        lib.kw_col_name.restype = ctypes.c_char_p
        lib.kw_col_name.argtypes = [ctypes.c_int]
        lib.kw_copy_frames.restype = ctypes.c_int64
        lib.kw_copy_frames.argtypes = [
            ctypes.c_int, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
        lib.kw_write_rows.restype = ctypes.c_int64
        lib.kw_write_rows.argtypes = [
            ctypes.c_int, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_int64, ctypes.c_int64]
        _lib = lib
    except OSError:
        _lib = None
    _tried = True
    return _lib


_bg_room = 1 << 16
_bg_out = ctypes.create_string_buffer(_bg_room)
_bg_nrec = ctypes.c_int64(0)
_bg_fn = None


def _rect4(bounds):
    r = getattr(bounds, "clip_rect", None)
    return None if r is None else (ctypes.c_double * 4)(*(float(v) for v in r))


def bg_shape_records(shape, bounds, coord_range: int) -> list[bytes] | None:
    """A line/polygon's records, clipped to the parcel (`kiwiw.clip`), via C
    at `coord_range`; None when the kernel declines (use the Python oracle)."""
    global _bg_fn, _bg_out, _bg_room
    if _bg_fn is None:
        lib = _load_lib()
        _bg_fn = lib.kw_bg_shape if lib is not None else False
    if _bg_fn is False:
        return None
    coords = shape.coords
    try:
        flat = array("d", chain.from_iterable(coords))
    except (TypeError, ValueError):
        return None
    if len(flat) != 2 * len(coords):
        return None
    b4 = array("d", (bounds.lat_lo, bounds.lat_hi, bounds.lon_lo, bounds.lon_hi))
    rect = _rect4(bounds)
    flags = (1 if shape.underground else 0) | (2 if shape.pen_up else 0)
    while True:
        n = _bg_fn(flat.buffer_info()[0], len(coords), shape.mult_const, shape.type_code,
                   flags, 1 if shape.shape_class == 2 else 0, b4.buffer_info()[0],
                   rect, ctypes.addressof(_bg_out), _bg_room, float(coord_range),
                   ctypes.addressof(_bg_nrec))
        if n != -2 or _bg_room >= (1 << 26):
            break
        _bg_room <<= 2
        _bg_out = ctypes.create_string_buffer(_bg_room)
    if n < 0:
        return None
    raw = ctypes.string_at(ctypes.addressof(_bg_out), n)
    recs, pos = [], 0
    for _ in range(_bg_nrec.value):
        ln = (((raw[pos] << 8) | raw[pos + 1]) & 0xFFF) * 2
        recs.append(raw[pos:pos + ln])
        pos += ln
    if pos != n:  # a record over the 12-bit length field: let Python decide
        return None
    return recs


def lib():
    """The loaded C library (or None) -- for the assembly copy helpers."""
    return _load_lib()


# ---------------------------------------------------------------- E1 (3C-06)
# The C level pre-pass (`_e1.c`; DESIGN.md Contract B, "E1"). One ctypes
# call per row range; no Python fallback (a build failure raises).

E1_COUNTERS = ("shared_shapes", "edge_cells", "interior_cells", "skipped_missing_cells")
_E1_NSLOTS = 8          # counters[0..3] above, 4 cells, 5 shapes, 6 leaving, 7 C ns
_E1_ERRORS = {-1: "bad descriptor", -2: "bad spool index", -3: "bad spool record",
              -4: "out of memory"}
_e1_lib = None
_e1_stats = {"ranges": 0, "calls": 0, "rows": 0, "cells": 0, "shapes": 0, "leaving": 0,
             "py_s": 0.0, "c_s": 0.0, "handoff_s": 0.0}


class E1Error(RuntimeError):
    """E1 rejected its input (descriptor, spool index or record)."""


def _load_e1():
    global _e1_lib
    if _e1_lib is None:
        cbuild.build_ext()
        lib = ctypes.CDLL(str(_SO))
        lib.kw_e1.restype = ctypes.c_int64
        lib.kw_e1.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                              ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
                              ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
        _e1_lib = lib
    return _e1_lib


class E1Spool:
    """One level's spool `.idx` and `.data`, memory-mapped read-only for E1
    (zero-copy: C reads the mapped pages directly)."""

    def __init__(self, spool_dir, level: int):
        import numpy as np
        self.level = level
        d = Path(spool_dir)
        self.idx = np.memmap(d / f"level_{level}.idx", dtype=np.uint8, mode="r")
        p = d / f"level_{level}.data"
        self.data = (np.memmap(p, dtype=np.uint8, mode="r") if p.stat().st_size
                     else np.zeros(0, np.uint8))

    def close(self) -> None:
        self.idx = self.data = None


_E1_I64_MIN, _E1_I64_MAX = -(1 << 63), (1 << 63) - 1
_e1_buf = None


def e1(desc: bytes, spool: E1Spool, row_lo: int | None, row_hi: int | None,
       cap_hint: int | None = None):
    """Run E1 over source rows `[row_lo, row_hi)` (`None` = unbounded).
    Returns `(rows, counters)`: a `descriptor.E1_ROW_DTYPE` array (a copy)
    and `{name: int}` over `E1_COUNTERS`. If the output buffer is too small
    C reports the rows it needs; the buffer grows and the call repeats (the
    repeat is counted in `e1_stats()["calls"]`)."""
    import numpy as np
    from .descriptor import E1_ROW_DTYPE, MAGIC, parse_level
    global _e1_buf
    t0 = time.perf_counter()
    # (a bad magic is C's to reject; this only pairs a good one with its spool)
    if bytes(desc[:8]) == MAGIC and parse_level(desc) != spool.level:
        raise E1Error(f"descriptor level {parse_level(desc)} != spool level {spool.level}")
    rb = E1_ROW_DTYPE.itemsize
    lib = _load_e1()
    if cap_hint is not None:
        _e1_buf = np.empty(max(1, cap_hint) * rb, np.uint8)
    elif _e1_buf is None:
        _e1_buf = np.empty((1 << 16) * rb, np.uint8)
    lo = _E1_I64_MIN if row_lo is None else int(row_lo)
    hi = _E1_I64_MAX if row_hi is None else int(row_hi)
    dbuf = np.frombuffer(desc, np.uint8)
    idx, data = spool.idx, spool.data
    wall = c_ns = 0.0
    while True:
        cnt = np.zeros(_E1_NSLOTS, np.int64)
        tc = time.perf_counter()
        n = lib.kw_e1(dbuf.ctypes.data, len(dbuf), idx.ctypes.data, len(idx),
                      data.ctypes.data, len(data), lo, hi,
                      _e1_buf.ctypes.data, len(_e1_buf) // rb, cnt.ctypes.data)
        wall += time.perf_counter() - tc
        c_ns += float(cnt[7])
        _e1_stats["calls"] += 1
        if n < 0:
            raise E1Error(_E1_ERRORS.get(n, f"error {n}"))
        if n <= len(_e1_buf) // rb:
            break
        _e1_buf = np.empty(int(n + n // 4) * rb, np.uint8)
    # raw bytes (pad included), then viewed: a structured copy skips the pad
    rows = _e1_buf[:n * rb].copy().view(E1_ROW_DTYPE)
    s = _e1_stats
    s["ranges"] += 1
    s["rows"] += int(n)
    s["cells"] += int(cnt[4]); s["shapes"] += int(cnt[5]); s["leaving"] += int(cnt[6])
    s["c_s"] += c_ns / 1e9
    s["handoff_s"] += max(0.0, wall - c_ns / 1e9)
    s["py_s"] += max(0.0, (time.perf_counter() - t0) - wall)
    return rows, {k: int(cnt[i]) for i, k in enumerate(E1_COUNTERS)}


def e1_stats() -> dict:
    """Process-local E1 totals: ranges, ctypes calls (ranges + retries),
    rows, and the Python / C / handoff time split."""
    return dict(_e1_stats)


# ---------------------------------------------------------------- E2 (3C-07)
# The C Stage 1 kernel (`_e2.c`; DESIGN.md Contract B, "E2"). One ctypes
# call per target row range; C grows its own output buffers and hands back
# their addresses, which are copied out here. No Python fallback.

E2_COUNTERS = ("cells", "frames", "declined", "frame_bytes", "total_road", "total_bg",
               "total_name", "borrowed_shapes", "cover_rings", "dropped_road", "dropped_bg",
               "dropped_name", "trimmed_cells_road", "trimmed_cells_bg", "trimmed_cells_name",
               "halo_names")
_E2_NSLOTS = 17         # counters above, then 16 = C ns
_E2_ERRORS = {-1: "bad descriptor", -2: "bad spool index", -3: "bad spool record",
              -4: "out of memory", -5: "bad rows (order, or target not a receiving cell "
              "of the range)", -6: "frame write failed",
              -7: "descriptor column table differs from _cenc.c COLS[]"}
_e2_lib = None
_e2_stats = {"ranges": 0, "cells": 0, "frames": 0, "declined": 0,
             "py_s": 0.0, "c_s": 0.0, "handoff_s": 0.0}


class E2Error(RuntimeError):
    """E2 rejected its input (descriptor, spool, rows) or could not write."""


def _load_e2():
    global _e2_lib
    if _e2_lib is None:
        cbuild.build_ext()
        lib = ctypes.CDLL(str(_SO))
        lib.kw_e2.restype = ctypes.c_int64
        lib.kw_e2.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                              ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                              ctypes.c_int64, ctypes.c_int64, ctypes.c_int, ctypes.c_uint64,
                              ctypes.c_void_p, ctypes.c_void_p]
        _e2_lib = lib
    return _e2_lib


def e2(desc: bytes, spool: E1Spool, rows, row_lo: int | None, row_hi: int | None,
       fd: int, off: int):
    """Run E2 over target rows `[row_lo, row_hi)` (`None` = unbounded) of the
    descriptor's window. `rows` are the E1 rows targeting that range, routed
    (target (iy, ix), then source (iy, ix), then shape). Frames are written
    to `fd` from byte `off` on; a cell too big for one frame is divided, retiled,
    trimmed and given its name halo in C, and its sub-frames are indexed
    (`pt` 1/2, `sx`, `sy`). Returns `(index, declined, counters)`:
    `descriptor.E2_INDEX_DTYPE` / `E2_DECLINED_DTYPE` arrays and `{name: int}`
    over `E2_COUNTERS`. A declined row (reason 2: cannot be encoded even after
    division; `off` = `len` = 0) is transitional -- the build treats it as an
    error."""
    import numpy as np
    from .descriptor import (E1_ROW_DTYPE, E2_DECLINED_DTYPE, E2_INDEX_DTYPE, MAGIC,
                             parse_level)
    t0 = time.perf_counter()
    if bytes(desc[:8]) == MAGIC and parse_level(desc) != spool.level:
        raise E2Error(f"descriptor level {parse_level(desc)} != spool level {spool.level}")
    if rows.dtype != E1_ROW_DTYPE:
        raise E2Error("rows are not descriptor.E1_ROW_DTYPE")
    rows = np.ascontiguousarray(rows)
    lib = _load_e2()
    lo = _E1_I64_MIN if row_lo is None else int(row_lo)
    hi = _E1_I64_MAX if row_hi is None else int(row_hi)
    dbuf = np.frombuffer(desc, np.uint8)
    idx, data = spool.idx, spool.data
    cnt = np.zeros(_E2_NSLOTS, np.int64)
    bufs = (ctypes.c_void_p * 2)()
    tc = time.perf_counter()
    rc = lib.kw_e2(dbuf.ctypes.data, len(dbuf), idx.ctypes.data, len(idx),
                   data.ctypes.data, len(data), rows.ctypes.data if len(rows) else None,
                   len(rows), lo, hi, int(fd), int(off), bufs, cnt.ctypes.data)
    wall = time.perf_counter() - tc
    if rc < 0:
        raise E2Error(_E2_ERRORS.get(rc, f"error {rc}"))

    def take(i, n, dt):
        if n == 0:
            return np.zeros(0, dt)
        return np.frombuffer(ctypes.string_at(bufs[i], n), np.uint8).view(dt).copy()

    index = take(0, int(cnt[1]) * E2_INDEX_DTYPE.itemsize, E2_INDEX_DTYPE)
    declined = take(1, int(cnt[2]) * E2_DECLINED_DTYPE.itemsize, E2_DECLINED_DTYPE)
    c_s = float(cnt[16]) / 1e9
    s = _e2_stats
    s["ranges"] += 1
    s["cells"] += int(cnt[0]); s["frames"] += int(cnt[1]); s["declined"] += int(cnt[2])
    s["c_s"] += c_s
    s["handoff_s"] += max(0.0, wall - c_s)
    s["py_s"] += max(0.0, (time.perf_counter() - t0) - wall)
    return index, declined, {k: int(cnt[i]) for i, k in enumerate(E2_COUNTERS)}


def e2_stats() -> dict:
    """Process-local E2 totals: ranges, cells, frames, declined, and the
    Python / C / handoff time split."""
    return dict(_e2_stats)
