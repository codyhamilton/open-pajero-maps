"""ctypes bindings for the C build kernels in `_cenc.so` (plan 03).

`cbuild.build_ext()` compiles the sources on demand (gcc, `-ffp-contract=off`)
into `_cenc.so` beside this file; a failed build raises (no Python fallback).
Entry points: E1 (`e1`) and E2 (`e2`), each called once per row range
(DESIGN.md Contract B); E2 also divides, retiles, trims and adds the name halo
(3C-09), so nothing per (sub-)cell or per shape crosses this boundary. What is
left besides is the column-name accessor and the assembly copy helpers
(`lib()`).
"""
from __future__ import annotations

import ctypes
import time
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


# ---------------------------------------------------------------- D1 (2-01)
# The C frame decoders (`_d1.c`; layouts in `_d1.h`). One ctypes call per range
# of leaf frames; the row layout below mirrors the header's X-macro lists and is
# checked against the library's own accessors at load (a mismatch raises).

_D1_LAYOUT = {
    "leaf": [("off", "u64"), ("lat_lo", "f64"), ("lat_hi", "f64"), ("lon_lo", "f64"),
             ("lon_hi", "f64"), ("len", "u32"), ("coord_range", "i32"), ("n_basic_map", "u16"),
             ("n_ext_map", "u16")],
    "frame": [("llpid_lat", "f64"), ("llpid_lon", "f64"), ("off", "u64"),
              ("frame_size", "u32"), ("region_list_off", "u32"), ("region_list_len", "u32"),
              ("tail_off", "u32"), ("tail_len", "u32"), ("road_base", "u32"),
              ("road_size", "u32"), ("bg_base", "u32"), ("bg_size", "u32"),
              ("name_base", "u32"), ("name_size", "u32"),
              ("mfde_first", "u32"), ("mfde_n", "u32"), ("dclass_first", "u32"),
              ("dclass_n", "u32"), ("link_first", "u32"), ("link_n", "u32"),
              ("node_first", "u32"), ("node_n", "u32"), ("point_first", "u32"),
              ("point_n", "u32"), ("addl_first", "u32"), ("addl_n", "u32"),
              ("bgelem_first", "u32"), ("bgelem_n", "u32"), ("bgunit_first", "u32"),
              ("bgunit_n", "u32"), ("bgshape_first", "u32"), ("bgshape_n", "u32"),
              ("bgcoord_first", "u32"), ("bgcoord_n", "u32"), ("nlist_first", "u32"),
              ("nlist_n", "u32"), ("nrec_first", "u32"), ("nrec_n", "u32"),
              ("status", "i32"), ("nregion", "u16"), ("n_intersections", "u16"),
              ("road_header_size_raw", "u16"), ("lvl_field_raw", "u16"),
              ("bg_header_size_raw", "u16"), ("name_header_size_raw", "u16"),
              ("llcode_cx", "u8"), ("llcode_cy", "u8"), ("has_road", "u8"),
              ("n_display_classes", "u8"), ("n_additional_data", "u8"),
              ("route_planning_level", "u8"), ("has_bg", "u8"), ("has_name", "u8")],
    "mfde": [("raw_off", "u32"), ("ext_off", "u32"), ("ext_len", "u32"), ("raw_size", "u16"),
             ("has_ext", "u8")],
    "dclass": [("flags_off", "u32"), ("raw_offset_word", "u16"), ("raw_count_word", "u16"),
               ("has_flags", "u8"), ("flags_len", "u8")],
    "addl": [("data_off", "u32"), ("data_len", "u32"), ("raw_offset_word", "u16"),
             ("raw_size_word", "u16"), ("has_raw", "u8")],
    "link": [("frame", "i32"), ("raw_off", "u32"), ("raw_len", "u32"), ("node_first", "u32"),
             ("point_first", "u32"), ("n_points", "u32"), ("n_nodes", "u16"),
             ("display_class", "u8"), ("road_type", "u8"), ("altitude_flag", "u8"),
             ("route_type_guidance_flag", "u8"), ("pseudo3d_updown", "u8"),
             ("route_planning_tag", "u8"), ("link_id_flag", "u8"), ("selected_link_flag", "u8"),
             ("toll_flag", "u8"), ("route_number_flag", "u8"), ("infra_link_flag", "u8"),
             ("link_id_number_flag", "u8")],
    "node": [("lat", "f64"), ("lon", "f64"), ("x", "i32"), ("y", "i32"), ("oneway", "u8"),
             ("planned", "u8"), ("tunnel", "u8"), ("bridge", "u8")],
    "point": [("lat", "f64"), ("lon", "f64"), ("x", "i32"), ("y", "i32")],
    "bgelem": [("unit_first", "u32"), ("unit_n", "u32"), ("raw_offset_word", "u16"),
               ("raw_size_word", "u16"), ("n_raw", "u16")],
    "bgunit": [("boff_word", "u16"), ("val", "u16")],
    "bgshape": [("frame", "i32"), ("raw_off", "u32"), ("raw_len", "u32"),
                ("coord_first", "u32"), ("coord_n", "u32"), ("type_code", "u16"),
                ("n_coords", "u16"), ("mult_const", "u16"), ("shape_class", "u8"),
                ("underground", "u8"), ("pen_up", "u8")],
    "bgcoord": [("lat", "f64"), ("lon", "f64"), ("x", "i32"), ("y", "i32")],
    "nlist": [("rec_first", "u32"), ("rec_n", "u32"), ("raw_offset_word", "u16"),
              ("raw_count_word", "u16")],
    "nrec": [("lat", "f64"), ("lon", "f64"), ("frame", "i32"), ("raw_off", "u32"),
             ("raw_len", "u32"), ("text_off", "u32"), ("text_len", "u32"),
             ("angle_deg", "i32"), ("type_code", "u16"), ("string_type", "u8"),
             ("priority", "u8"), ("vertical", "u8"), ("display_scale_flag", "u8"),
             ("angle_flags", "u8"), ("has_latlon", "u8"), ("has_angle", "u8")],
}
_D1_TABLES = tuple(_D1_LAYOUT)                      # C table index == position
_D1_NP = {"u8": "<u1", "u16": "<u2", "u32": "<u4", "u64": "<u8", "i32": "<i4", "f64": "<f8"}
_D1_NSTATS = 16
_D1_ERRORS = {-1: "bad arguments", -2: "a leaf row lies outside the region",
              -3: "out of memory"}


def _d1_dtype(table: str):
    import numpy as np
    return np.dtype([(n, _D1_NP[k]) for n, k in _D1_LAYOUT[table]], align=True)


D1_LEAF_DTYPE = _d1_dtype("leaf")
_D1_DTYPES = {t: _d1_dtype(t) for t in _D1_TABLES}
_d1_lib = None
_d1_stats = {"ranges": 0, "calls": 0, "frames": 0, "rows": 0, "failed": 0,
             "py_s": 0.0, "c_s": 0.0, "handoff_s": 0.0}


class D1Error(RuntimeError):
    """D1 rejected its input, or the Python layout disagrees with `_d1.h`."""


def _load_d1():
    global _d1_lib
    if _d1_lib is None:
        cbuild.build_ext()
        lib = ctypes.CDLL(str(_SO))
        for f, args, res in (
                ("kw_d1_ntables", [], ctypes.c_int),
                ("kw_d1_table_name", [ctypes.c_int], ctypes.c_char_p),
                ("kw_d1_row_size", [ctypes.c_int], ctypes.c_int),
                ("kw_d1_nfields", [ctypes.c_int], ctypes.c_int),
                ("kw_d1_field_name", [ctypes.c_int, ctypes.c_int], ctypes.c_char_p),
                ("kw_d1_field_kind", [ctypes.c_int, ctypes.c_int], ctypes.c_char_p),
                ("kw_d1_field_off", [ctypes.c_int, ctypes.c_int], ctypes.c_int)):
            fn = getattr(lib, f)
            fn.argtypes, fn.restype = args, res
        lib.kw_d1_frames.restype = ctypes.c_int64
        lib.kw_d1_frames.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                                     ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
                                     ctypes.c_void_p]
        _d1_check_layout(lib)
        _d1_lib = lib
    return _d1_lib


def _d1_check_layout(lib) -> None:
    if lib.kw_d1_ntables() != len(_D1_TABLES):
        raise D1Error(f"D1 layout: C has {lib.kw_d1_ntables()} tables, Python {len(_D1_TABLES)}")
    for t, name in enumerate(_D1_TABLES):
        dt, spec = _D1_DTYPES[name], _D1_LAYOUT[name]
        if lib.kw_d1_table_name(t).decode() != name:
            raise D1Error(f"D1 layout: table {t} is {lib.kw_d1_table_name(t)!r}, not {name!r}")
        if lib.kw_d1_nfields(t) != len(spec):
            raise D1Error(f"D1 layout: table {name}: C has {lib.kw_d1_nfields(t)} fields, "
                          f"Python {len(spec)}")
        for i, (fname, kind) in enumerate(spec):
            got = (lib.kw_d1_field_name(t, i).decode(), lib.kw_d1_field_kind(t, i).decode(),
                   lib.kw_d1_field_off(t, i))
            if got != (fname, kind, dt.fields[fname][1]):
                raise D1Error(f"D1 layout: table {name} field {i}: C {got}, Python "
                              f"{(fname, kind, dt.fields[fname][1])}")
        if lib.kw_d1_row_size(t) != dt.itemsize:
            raise D1Error(f"D1 layout: table {name}: C row {lib.kw_d1_row_size(t)} bytes, "
                          f"Python {dt.itemsize}")


class _Labels(dict):
    """code -> label, computed on first use by `fn`."""

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def __missing__(self, key):
        v = self[key] = self._fn(key)
        return v


def _name_label(key) -> str:
    from .roadtypes import background_type_label
    st, code = key
    if st in (1, 4, 5, 6):
        return background_type_label(code)
    return f"UNHANDLED string_type={st} (kiwiread.c aborts here)"


class D1Result:
    """Columns from one `d1_frames` call: `t[table]` is a structured array
    (a copy, trimmed to its rows); `bg_labels` / `name_labels` resolve the type
    codes to the label strings the Python decoders attach."""

    def __init__(self, t):
        from .roadtypes import background_type_label
        self.t = t
        self.bg_labels = _Labels(background_type_label)
        self.name_labels = _Labels(_name_label)


def d1_frames(region, leaf, cap_hint: int | None = None) -> D1Result:
    """Decode every leaf frame in `leaf` (a `D1_LEAF_DTYPE` array of frame
    positions in the uint8 array `region`) in one C call; grow the output
    buffers and repeat if C reports it needs more rows (counted in
    `d1_stats()["calls"]`). Frames Python would raise on get `status != 0`."""
    import numpy as np
    t0 = time.perf_counter()
    lib = _load_d1()
    if leaf.dtype != D1_LEAF_DTYPE:
        raise D1Error("leaf table has the wrong dtype")
    leaf = np.ascontiguousarray(leaf)
    region = np.ascontiguousarray(region, dtype=np.uint8)
    nf = len(leaf)
    nt = len(_D1_TABLES)
    base = max(1, cap_hint) if cap_hint is not None else max(1 << 16, 2048 * nf)
    caps = np.full(nt, base, np.int64)
    if cap_hint is None:                  # vertex tables dominate: ~9k per real frame
        for tn in ("node", "point", "bgcoord"):
            caps[_D1_TABLES.index(tn)] = base * 8
    caps[1] = max(nf, 1) if cap_hint is not None else max(nf, base)
    caps[0] = 0
    wall = c_ns = 0.0
    while True:
        bufs = [None] + [np.zeros(int(caps[i]) * _D1_DTYPES[_D1_TABLES[i]].itemsize or 1, np.uint8)
                         for i in range(1, nt)]
        ptrs = np.array([0] + [b.ctypes.data for b in bufs[1:]], np.uint64)
        stats = np.zeros(_D1_NSTATS, np.int64)
        tc = time.perf_counter()
        rc = lib.kw_d1_frames(region.ctypes.data, len(region), leaf.ctypes.data, nf,
                              ptrs.ctypes.data, caps.ctypes.data, stats.ctypes.data)
        wall += time.perf_counter() - tc
        c_ns += float(stats[15])
        _d1_stats["calls"] += 1
        if rc < 0:
            raise D1Error(_D1_ERRORS.get(rc, f"error {rc}"))
        if rc == 0:
            break
        for i in range(1, nt):
            if stats[i] > caps[i]:
                caps[i] = int(stats[i] + stats[i] // 4)
    t = {}
    for i in range(1, nt):
        name = _D1_TABLES[i]
        dt = _D1_DTYPES[name]
        t[name] = bufs[i][:int(stats[i]) * dt.itemsize].copy().view(dt)
    s = _d1_stats
    s["ranges"] += 1
    s["frames"] += nf
    s["rows"] += int(stats[1:14].sum())
    s["failed"] += int(stats[14])
    s["c_s"] += c_ns / 1e9
    s["handoff_s"] += max(0.0, wall - c_ns / 1e9)
    s["py_s"] += max(0.0, (time.perf_counter() - t0) - wall)
    return D1Result(t)


def d1_stats() -> dict:
    """Process-local D1 totals: ranges, ctypes calls (ranges + retries),
    frames, rows, failed frames, and the Python / C / handoff time split."""
    return dict(_d1_stats)
