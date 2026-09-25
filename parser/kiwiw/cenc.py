"""ctypes binding for the whole-cell C encoder `_cenc.c` (plan 03).

`load()` compiles `_cenc.c` on demand (gcc, `-ffp-contract=off` for float
parity with the Python oracle) into `_cenc.so` beside it and returns a
`CellEncoder`, or None when no compiler is available / `KIWIW_NO_C=1` -- callers
then use the pure-Python path, which stays the oracle. The kernel only answers
"this cell fits and has no kind breach" (-> frame bytes); anything else
returns None and the caller re-runs the Python path for that cell.
"""
from __future__ import annotations

import ctypes
import time
from array import array
from itertools import chain
import os
from pathlib import Path

from . import cbuild

_SRC = Path(__file__).with_name("_cenc.c")
_SO = Path(__file__).with_name("_cenc.so")
_OUT_CAP = 0x20000
_NO_LIMIT = (1 << 62)
_lib = None
_tried = False

# 3C-01 bench instrumentation: process-local call counters and wrapper (ctypes
# marshalling) wall time for the legacy per-cell entry points, named so E1/E2
# counts (`e1`, `e2`) slot in alongside them later. Off by default -- only
# `build_alldata.py --bench` pays the per-call timing overhead (set_bench()).
_CALL_NAMES = ("kw_encode_cell", "kw_measure_cell", "kw_bg_shape")
_BENCH = False
_calls: dict[str, int] = {n: 0 for n in _CALL_NAMES}
_wrap_ns: dict[str, float] = {n: 0.0 for n in _CALL_NAMES}


def set_bench(on: bool) -> None:
    """Enable/disable per-call wrapper timing (`--bench`). With `on=False`
    neither the counters nor the timers move, so an un-benched build pays no
    extra cost."""
    global _BENCH
    _BENCH = on


def reset_worker_stats() -> None:
    """Zero this process's call counters and the C-side time accumulators
    (3C-01). Called once per chunk so `worker_stats()` reports that chunk's
    share only."""
    global _calls, _wrap_ns
    _calls = {n: 0 for n in _CALL_NAMES}
    _wrap_ns = {n: 0.0 for n in _CALL_NAMES}
    lib = _load_lib()
    if lib is not None:
        buf = (ctypes.c_double * 3)()
        lib.kw_get_reset_c_times(buf)  # discard: reset only


def worker_stats() -> dict:
    """This process's `kw_encode_cell`/`kw_measure_cell`/`kw_bg_shape` call
    counts and C/handoff time split since the last `reset_worker_stats()`
    (Contract H: C time is the C-side entry-point timer; handoff is wrapper
    time outside C). Python time is the caller's to compute (chunk wall minus
    `c_s` minus `handoff_s`)."""
    lib = _load_lib()
    c = {n: 0.0 for n in _CALL_NAMES}
    if lib is not None:
        buf = (ctypes.c_double * 3)()
        lib.kw_get_reset_c_times(buf)
        c = {"kw_encode_cell": buf[0], "kw_measure_cell": buf[1], "kw_bg_shape": buf[2]}
    handoff = {n: max(0.0, _wrap_ns[n] / 1e9 - c[n]) for n in _CALL_NAMES}
    return {"calls": dict(_calls), "c_s": sum(c.values()), "handoff_s": sum(handoff.values())}


def _load_lib():
    global _lib, _tried
    if _tried:
        return _lib
    _tried = True
    if os.environ.get("KIWIW_NO_C"):
        return None
    try:
        try:
            cbuild.build_ext()  # compiles on demand through cbuild (3C-02)
        except cbuild.BuildError:
            # Unchanged behaviour: no compiler / a failed build falls back
            # to the Python oracle here (deleted only by 3C-08/3C-12).
            return None
        lib = ctypes.CDLL(str(_SO))
        lib.kw_encode_cell.restype = ctypes.c_int64
        lib.kw_encode_cell.argtypes = [
            ctypes.c_char_p, ctypes.c_int64, ctypes.c_int, ctypes.c_int64, ctypes.c_int64,
            ctypes.POINTER(ctypes.c_double), ctypes.c_int64,
            ctypes.POINTER(ctypes.c_int64), ctypes.c_void_p, ctypes.c_double]
        lib.kw_bg_shape.restype = ctypes.c_int64
        lib.kw_bg_shape.argtypes = [
            ctypes.c_void_p, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
            ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
            ctypes.c_double, ctypes.c_void_p]
        lib.kw_measure_cell.restype = ctypes.c_int64
        lib.kw_measure_cell.argtypes = [
            ctypes.c_char_p, ctypes.c_int64, ctypes.c_int, ctypes.c_int64, ctypes.c_int64,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_double]
        lib.kw_copy_frames.restype = ctypes.c_int64
        lib.kw_copy_frames.argtypes = [
            ctypes.c_int, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64]
        lib.kw_write_rows.restype = ctypes.c_int64
        lib.kw_write_rows.argtypes = [
            ctypes.c_int, ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_int64, ctypes.c_int64]
        lib.kw_get_reset_c_times.restype = None
        lib.kw_get_reset_c_times.argtypes = [ctypes.POINTER(ctypes.c_double)]
        _lib = lib
    except OSError:
        _lib = None
    return _lib


class CellEncoder:
    def __init__(self, lib, level: int, grid, threshold: int, kind_limits):
        self._fn = lib.kw_encode_cell
        self._level = level
        self._grid = (ctypes.c_double * 4)(grid.disc_lat_lo, grid.disc_lon_lo,
                                           grid.cell_lat, grid.cell_lon)
        self._threshold = threshold
        kl = kind_limits or {}
        self._lim = (ctypes.c_int64 * 3)(*(kl.get(k, _NO_LIMIT)
                                           for k in ("road", "background", "name")))
        self._out = ctypes.create_string_buffer(_OUT_CAP)
        self._addr = ctypes.addressof(self._out)

    def encode(self, raw: bytes | None, ix: int, iy: int, *,
               coord_range: int) -> bytes | None:
        """`coord_range`: the cell frame's coordinate range (`range_for`);
        the kernel converts every vertex from lat/lon at it."""
        if _BENCH:
            t0 = time.perf_counter_ns()
            n = self._fn(raw, len(raw) if raw else 0, self._level, ix, iy, self._grid,
                         self._threshold, self._lim, self._addr, float(coord_range))
            _wrap_ns["kw_encode_cell"] += time.perf_counter_ns() - t0
            _calls["kw_encode_cell"] += 1
        else:
            n = self._fn(raw, len(raw) if raw else 0, self._level, ix, iy, self._grid,
                         self._threshold, self._lim, self._addr, float(coord_range))
        return None if n < 0 else ctypes.string_at(self._addr, n)


def make_encoder(level: int, grid, threshold: int, kind_limits):
    lib = _load_lib()
    if lib is None:
        return None
    return CellEncoder(lib, level, grid, threshold, kind_limits)


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
    t0 = time.perf_counter_ns() if _BENCH else 0
    while True:
        n = _bg_fn(flat.buffer_info()[0], len(coords), shape.mult_const, shape.type_code,
                   flags, 1 if shape.shape_class == 2 else 0, b4.buffer_info()[0],
                   rect, ctypes.addressof(_bg_out), _bg_room, float(coord_range),
                   ctypes.addressof(_bg_nrec))
        if n != -2 or _bg_room >= (1 << 26):
            break
        _bg_room <<= 2
        _bg_out = ctypes.create_string_buffer(_bg_room)
    if _BENCH:
        _wrap_ns["kw_bg_shape"] += time.perf_counter_ns() - t0
        _calls["kw_bg_shape"] += 1
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


_m_out = ctypes.create_string_buffer(_OUT_CAP)
_m_addr = ctypes.addressof(_m_out)
_m_sizes = (ctypes.c_int64 * 3)()
_m_fn = None


def measure_content(level: int, ix: int, iy: int, bounds, content: dict, *,
                    coord_range: int | None = None):
    """C probe of one (sub-)cell content dict: `(frame, {road,background,name})`
    exactly as `build_alldata._measure_one`, or None when the kernel declines
    (over the ceiling, unmodelled input) -- the caller then runs the Python path.
    `coord_range` resolves as in `synth.frame_range` (explicit, else
    `bounds.coord_range`, else `ValueError`), so it matches the Python
    encoders handed the same `bounds`."""
    global _m_fn
    if _m_fn is None:
        lib = _load_lib()
        _m_fn = lib.kw_measure_cell if lib is not None else False
    if _m_fn is False:
        return None
    from .spool import content_to_columns, encode_columns
    from .synth import frame_range
    cr = frame_range(bounds, coord_range)
    try:
        raw = encode_columns(content_to_columns(content))
    except (AttributeError, TypeError, ValueError, UnicodeError):
        return None
    b4 = (ctypes.c_double * 4)(bounds.lat_lo, bounds.lat_hi, bounds.lon_lo, bounds.lon_hi)
    if _BENCH:
        t0 = time.perf_counter_ns()
        n = _m_fn(raw, len(raw), level, ix, iy, ctypes.addressof(b4), _rect4(bounds),
                  _m_addr_sizes(), _m_addr, float(cr))
        _wrap_ns["kw_measure_cell"] += time.perf_counter_ns() - t0
        _calls["kw_measure_cell"] += 1
    else:
        n = _m_fn(raw, len(raw), level, ix, iy, ctypes.addressof(b4), _rect4(bounds),
                  _m_addr_sizes(), _m_addr, float(cr))
    if n < 0:
        return None
    return (ctypes.string_at(_m_addr, n),
            {"road": _m_sizes[0], "background": _m_sizes[1], "name": _m_sizes[2]})


def _m_addr_sizes() -> int:
    return ctypes.addressof(_m_sizes)
