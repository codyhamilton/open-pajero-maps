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
from array import array
from itertools import chain
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


_SRC = Path(__file__).with_name("_cenc.c")
_SO = Path(__file__).with_name("_cenc.so")
_OUT_CAP = 0x20000
_NO_LIMIT = (1 << 62)
_lib = None
_tried = False


def _build() -> bool:
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        return False
    fd, tmp = tempfile.mkstemp(suffix=".so", dir=str(_SO.parent))
    os.close(fd)
    try:
        subprocess.run([cc, "-O2", "-ffp-contract=off", "-fPIC", "-shared", "-o", tmp,
                        str(_SRC), "-lm"], check=True, capture_output=True)
        os.replace(tmp, _SO)  # atomic: concurrent builders never see a partial .so
        return True
    except (subprocess.CalledProcessError, OSError):
        return False
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _load_lib():
    global _lib, _tried
    if _tried:
        return _lib
    _tried = True
    if os.environ.get("KIWIW_NO_C"):
        return None
    try:
        if not _SO.exists() or _SO.stat().st_mtime < _SRC.stat().st_mtime:
            if not _build():
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
    n = _m_fn(raw, len(raw), level, ix, iy, ctypes.addressof(b4), _rect4(bounds),
              _m_addr_sizes(), _m_addr, float(cr))
    if n < 0:
        return None
    return (ctypes.string_at(_m_addr, n),
            {"road": _m_sizes[0], "background": _m_sizes[1], "name": _m_sizes[2]})


def _m_addr_sizes() -> int:
    return ctypes.addressof(_m_sizes)
