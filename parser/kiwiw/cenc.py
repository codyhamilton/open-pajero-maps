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
    cbuild.build_ext()  # compiles on demand; BuildError propagates unchanged
    try:
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
    except (OSError, AttributeError) as exc:
        raise cbuild.BuildError(f"cannot load C assembly library {_SO}: {exc}") from exc
    _lib = lib
    _tried = True
    return _lib


def lib():
    """The C assembly library; build, load or symbol failure raises BuildError."""
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
    # 2-02: the block walker's output table, then its input table (last: no output buffer)
    "walk": [("lat_lo", "f64"), ("lat_hi", "f64"), ("lon_lo", "f64"), ("lon_hi", "f64"),
             ("flat_lo", "f64"), ("flat_hi", "f64"), ("flon_lo", "f64"), ("flon_hi", "f64"),
             ("off", "u64"), ("len", "u32"), ("dsa", "u32"), ("level", "i32"),
             ("blockset_index", "i32"), ("block_index", "i32"), ("block", "i32"), ("frame", "i32"), ("ix", "i32"),
             ("iy", "i32"), ("frame_range", "i32"), ("status", "i32"), ("err", "i32"),
             ("p0", "u16"), ("p1", "u16"), ("p2", "u16"), ("p3", "u16"), ("p4", "u16"),
             ("p5", "u16"), ("p6", "u16"), ("size", "u16"), ("depth", "u8"), ("parcel_type", "u8"),
             ("frame_class", "u8")],
    "block": [("cov_lat_lo", "f64"), ("cov_lat_hi", "f64"), ("cov_lon_lo", "f64"),
              ("cov_lon_hi", "f64"), ("lat0", "f64"), ("lon0", "f64"), ("cell_lat", "f64"),
              ("cell_lon", "f64"), ("wlo", "f64"), ("off", "u64"), ("len", "u32"),
              ("sector_sz", "u32"), ("logical_sz", "u32"), ("grid_nx", "u32"),
              ("grid_ny", "u32"), ("level", "i32"), ("blockset_index", "i32"),
              ("block_index", "i32"), ("bsx", "i32"), ("bsy", "i32"), ("blx", "i32"),
              ("bly", "i32"), ("n_blocks_lat", "i32"), ("n_blocks_lng", "i32"),
              ("rng_normal", "i32"), ("rng_sparse", "i32"), ("rng_divided", "i32"),
              ("npl0", "u16"), ("npl1", "u16"), ("npl2", "u16"), ("npl3", "u16"),
              ("npg0", "u16"), ("npg1", "u16"), ("npg2", "u16"), ("npg3", "u16"),
              ("n_basic_map", "u16"), ("n_ext_map", "u16")],
}
_D1_TABLES = tuple(_D1_LAYOUT)                      # C table index == position
_D1_NP = {"u8": "<u1", "u16": "<u2", "u32": "<u4", "u64": "<u8", "i32": "<i4", "f64": "<f8"}
_D1_NOUT = _D1_TABLES.index("walk") + 1             # output tables 1..walk; "block" is input only
_D1_NSTATS = 18
_D1_S_FAILED, _D1_S_NS = 15, 16                      # stats slots after the row counts
_D1_ERRORS = {-1: "bad arguments", -2: "a leaf row lies outside the region",
              -3: "out of memory"}


def _d1_dtype(table: str):
    import numpy as np
    return np.dtype([(n, _D1_NP[k]) for n, k in _D1_LAYOUT[table]], align=True)


D1_LEAF_DTYPE = _d1_dtype("leaf")
D1_BLOCK_DTYPE = _d1_dtype("block")
_D1_DTYPES = {t: _d1_dtype(t) for t in _D1_TABLES}
_d1_lib = None
_d1_stats = {"ranges": 0, "calls": 0, "retries": 0, "frames": 0, "rows": 0, "failed": 0,
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
        lib.kw_d1_blocks.restype = ctypes.c_int64
        lib.kw_d1_blocks.argtypes = [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                                     ctypes.c_int64, ctypes.c_int64, ctypes.c_int64,
                                     ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
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


def _d1_run(call, region, rows, nin, cap_hint):
    """The grow-and-repeat driver shared by `d1_frames` / `d1_blocks`: `call(ptrs,
    caps, stats)` runs one C call; returns (rc-0 stats, buffers, wall seconds)."""
    import numpy as np
    nt = _D1_NOUT
    base = max(1, cap_hint) if cap_hint is not None else max(1 << 16, 2048 * nin)
    caps = np.full(nt, base, np.int64)
    if cap_hint is None:                  # vertex tables dominate: ~9k per real frame
        for tn in ("node", "point", "bgcoord"):
            caps[_D1_TABLES.index(tn)] = base * 8
    caps[1] = max(rows, 1) if cap_hint is not None else max(rows, base)
    caps[_D1_TABLES.index("walk")] = max(rows, 1) if cap_hint is not None else max(rows, base)
    caps[0] = 0
    wall = c_ns = 0.0
    while True:
        bufs = [None] + [np.zeros(int(caps[i]) * _D1_DTYPES[_D1_TABLES[i]].itemsize or 1, np.uint8)
                         for i in range(1, nt)]
        ptrs = np.array([0] + [b.ctypes.data for b in bufs[1:]], np.uint64)
        stats = np.zeros(_D1_NSTATS, np.int64)
        tc = time.perf_counter()
        rc = call(ptrs.ctypes.data, caps.ctypes.data, stats.ctypes.data)
        wall += time.perf_counter() - tc
        c_ns += float(stats[_D1_S_NS])
        _d1_stats["calls"] += 1
        if rc < 0:
            raise D1Error(_D1_ERRORS.get(rc, f"error {rc}"))
        if rc == 0:
            break
        _d1_stats["retries"] += 1
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
    s["frames"] += int(stats[1])
    s["rows"] += int(stats[1:_D1_NOUT].sum())
    s["failed"] += int(stats[_D1_S_FAILED])
    s["c_s"] += c_ns / 1e9
    s["handoff_s"] += max(0.0, wall - c_ns / 1e9)
    return t, wall


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
    t, wall = _d1_run(lambda p, c, s: lib.kw_d1_frames(
        region.ctypes.data, len(region), leaf.ctypes.data, nf, p, c, s),
        region, nf, nf, cap_hint)
    _d1_stats["py_s"] += max(0.0, (time.perf_counter() - t0) - wall)
    return D1Result(t)


def d1_blocks(region, blocks, rlo: int | None = None, rhi: int | None = None,
              cap_hint: int | None = None) -> D1Result:
    """Walk and decode every leaf of the block rows `blocks` (a `D1_BLOCK_DTYPE`
    array, see `d1_block_rows`) whose slot-midpoint lattice row lies in
    `[rlo, rhi]` (default: all) in ONE C call (a range = one band of blocks;
    repeated only to grow buffers, `d1_stats()["retries"]`). `t["walk"]` has a row
    per leaf (or per unparsable block, status 1) and `t["frame"][walk.frame]` is
    its decoded frame, exactly `harness.walk` + `parcel.decode_parcel`."""
    import numpy as np
    t0 = time.perf_counter()
    lib = _load_d1()
    if blocks.dtype != D1_BLOCK_DTYPE:
        raise D1Error("block table has the wrong dtype")
    blocks = np.ascontiguousarray(blocks)
    region = np.ascontiguousarray(region, dtype=np.uint8)
    lo = -(1 << 62) if rlo is None else int(rlo)
    hi = (1 << 62) if rhi is None else int(rhi)
    nb = len(blocks)
    t, wall = _d1_run(lambda p, c, s: lib.kw_d1_blocks(
        region.ctypes.data, len(region), blocks.ctypes.data, nb, lo, hi, p, c, s),
        region, nb, nb, cap_hint)
    _d1_stats["py_s"] += max(0.0, (time.perf_counter() - t0) - wall)
    return D1Result(t)


def d1_block_rows(keys, container, lattice_cache: dict | None = None):
    """The `D1_BLOCK_DTYPE` rows for block keys `(level, blockset_index,
    block_index, bsx, bsy, blx, bly, file_offset, length)` of a disc whose
    `harness.walk.read_container` result is `container`: one row per BLOCK
    (callers enumerate blocks, never leaves). The per-level fields (LMR,
    coverage, raw lattice, the three `coordconv.range_for` answers) are looked up
    once per level."""
    import numpy as np
    from . import coordconv
    from .mesh import CellGrid
    pd, hdr = container.pdmdh, container.hdr
    lmrs = {m.level: m for m in pd.levels}
    per: dict = {} if lattice_cache is None else lattice_cache

    def rng(level, cls, state="normal"):
        try:
            return coordconv.range_for(level, cls, state)
        except KeyError:
            return 0

    def level_fields(level):
        if level not in per:
            m, cg = lmrs[level], CellGrid.from_reference(level)
            cv = pd.coverage
            per[level] = (
                cv.lat_lo, cv.lat_hi, cv.lon_lo, cv.lon_hi, cg.disc_lat_lo, cg.disc_lon_lo,
                cg.cell_lat, cg.cell_lon, cg.disc_lon_span / 2.0 - 180.0,
                hdr.sector_size, hdr.logical_sector_size, m.grid_nx, m.grid_ny,
                m.n_blocks_lat, m.n_blocks_lng,
                rng(level, "urban" if level == 0 else "full"),
                rng(level, "sparse") if level == 0 else 0,
                rng(level, "divided", "pardiv1_sub0"),
                *m.n_parcels_lat, *m.n_parcels_lng, m.n_basic_map, m.n_ext_map)
        return per[level]

    rows = np.zeros(len(keys), D1_BLOCK_DTYPE)
    for i, (level, bsi, bidx, bsx, bsy, blx, bly, boff, blen) in enumerate(keys):
        (cla, cha, clo, chi, lat0, lon0, clat, clon, wlo, ssz, lsz, gnx, gny, nbla, nblg,
         rn, rs, rd, *tail) = level_fields(level)
        rows[i] = (cla, cha, clo, chi, lat0, lon0, clat, clon, wlo, boff, blen, ssz, lsz, gnx,
                   gny, level, bsi, bidx, bsx, bsy, blx, bly, nbla, nblg, rn, rs, rd, *tail)
    return rows


def d1_stats() -> dict:
    """Process-local D1 totals: ranges, ctypes calls (ranges + retries),
    frames, rows, failed frames, and the Python / C / handoff time split."""
    return dict(_d1_stats)


# ---------------------------------------------------------------- K1 (2-03)
# The C checker core (`_k1.c`; layouts and contract in `_k1.h`). One ctypes call
# per (block, row band) -- `k1_check_band` -- decodes through D1 in C and checks the
# point kinds against the spool; the accumulator `K1Acc` is passed across calls
# and merges by sums, max and "first N of the union" (a total sample order).

K1_SAMPLE = 10
_K1_LAYOUT = {
    "kind": [("checked", "u64"), ("failing", "u64"), ("worst", "f64"), ("nsamples", "u32")],
    "sample": [("lat", "f64"), ("lon", "f64"), ("err", "f64"), ("ix", "i32"), ("iy", "i32"),
               ("vx", "i32"), ("vy", "i32"), ("reason", "i32"), ("code", "i32"),
               ("p0", "u16"), ("p1", "u16"), ("p2", "u16"), ("p3", "u16"), ("p4", "u16"),
               ("p5", "u16"), ("p6", "u16"), ("depth", "u8")],
    # brief 3-02: the dump row, `K1_F_DUMP` in `_k1.h` (sample fields, then identity);
    # brief 3-03 appends the diagnostic columns (sentinels: 0, NaN, -1, INT32_MIN)
    "dump": [("lat", "f64"), ("lon", "f64"), ("err", "f64"), ("ix", "i32"), ("iy", "i32"),
             ("vx", "i32"), ("vy", "i32"), ("reason", "i32"), ("code", "i32"),
             ("p0", "u16"), ("p1", "u16"), ("p2", "u16"), ("p3", "u16"), ("p4", "u16"),
             ("p5", "u16"), ("p6", "u16"), ("depth", "u8"), ("kind", "u8"), ("level", "u8"),
             ("shape", "i32"), ("vert", "i32"), ("onb", "u8"), ("d_any", "f64"),
             ("any_type", "i32"), ("in_eo_same", "u8"), ("in_wn_same", "u8"),
             ("in_eo_any", "u8"), ("src_ix", "i32"), ("src_iy", "i32"), ("src_rec", "i32"),
             ("src_tall", "u8"), ("src_nv", "i32"), ("src_maxseg", "f64"), ("d_src", "f64"),
             ("dcls", "i32"), ("dnv", "i32")],
}
_K1_TABLES = tuple(_K1_LAYOUT)
K1_DUMP_FIELDS = list(_K1_LAYOUT["dump"])
_K1_STATS = ("calls", "leaves", "failed_frames", "d1_retries", "cells", "items", "rescues",
             "ns", "d1_ns")
_K1_REASONS = {0: "range", 1: "no spool record within half a raw unit", 2: "step not representable",
               3: "leaf did not decode", 4: "background", 5: "background boundary", 6: "cover",
               7: "a spool polygon of this type meets the cell but no decoded piece of it does"}
_k1_lib = None
_k1_cols = None
_k1_stats = {"calls": 0}


class K1Error(RuntimeError):
    """K1 failed, or the Python layout disagrees with `_k1.h`."""


def _k1_dtype(table: str):
    import numpy as np
    return np.dtype([(n, _D1_NP[k]) for n, k in _K1_LAYOUT[table]], align=True)


K1_DUMP_DTYPE = _k1_dtype("dump")


def _load_k1():
    global _k1_lib, _k1_cols
    if _k1_lib is None:
        cbuild.build_ext()
        lib = ctypes.CDLL(str(_SO))
        for f, args, res in (
                ("kw_k1_ntables", [], ctypes.c_int),
                ("kw_k1_table_name", [ctypes.c_int], ctypes.c_char_p),
                ("kw_k1_row_size", [ctypes.c_int], ctypes.c_int),
                ("kw_k1_nfields", [ctypes.c_int], ctypes.c_int),
                ("kw_k1_field_name", [ctypes.c_int, ctypes.c_int], ctypes.c_char_p),
                ("kw_k1_field_kind", [ctypes.c_int, ctypes.c_int], ctypes.c_char_p),
                ("kw_k1_field_off", [ctypes.c_int, ctypes.c_int], ctypes.c_int),
                ("kw_k1_sample_n", [], ctypes.c_int),
                ("kw_k1_count", [ctypes.c_int], ctypes.c_int),
                ("kw_k1_name", [ctypes.c_int, ctypes.c_int], ctypes.c_char_p)):
            fn = getattr(lib, f)
            fn.argtypes, fn.restype = args, res
        lib.kw_k1_band.restype = ctypes.c_int64
        lib.kw_k1_band.argtypes = ([ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                                    ctypes.c_int64, ctypes.c_int64, ctypes.c_void_p,
                                    ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                                    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_int64] + [ctypes.c_void_p] * 4
                                   + [ctypes.c_void_p] * 4 + [ctypes.c_int64]
                                   + [ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p])
        lib.kw_k1_tall.restype = ctypes.c_int64
        lib.kw_k1_tall.argtypes = ([ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                                    ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                                    ctypes.c_int64, ctypes.c_int64, ctypes.c_void_p,
                                    ctypes.c_int64, ctypes.c_void_p, ctypes.c_int64,
                                    ctypes.c_void_p])
        _k1_check_layout(lib)
        _k1_lib = lib
        names = lambda w: [lib.kw_k1_name(w, i).decode() for i in range(lib.kw_k1_count(w))]
        _k1_cols = {"kinds": names(0), "explained": names(1), "cols": names(2), "stats": names(3)}
        if _k1_cols["stats"] != list(_K1_STATS):
            raise K1Error(f"K1 layout: stats {_k1_cols['stats']} != {list(_K1_STATS)}")
    return _k1_lib


def _k1_check_layout(lib) -> None:
    if lib.kw_k1_ntables() != len(_K1_TABLES):
        raise K1Error(f"K1 layout: C has {lib.kw_k1_ntables()} tables, Python {len(_K1_TABLES)}")
    if lib.kw_k1_sample_n() != K1_SAMPLE:
        raise K1Error("K1 layout: sample count differs")
    for t, name in enumerate(_K1_TABLES):
        dt, spec = _k1_dtype(name), _K1_LAYOUT[name]
        if lib.kw_k1_table_name(t).decode() != name or lib.kw_k1_nfields(t) != len(spec):
            raise K1Error(f"K1 layout: table {t} differs")
        for i, (fname, kind) in enumerate(spec):
            got = (lib.kw_k1_field_name(t, i).decode(), lib.kw_k1_field_kind(t, i).decode(),
                   lib.kw_k1_field_off(t, i))
            if got != (fname, kind, dt.fields[fname][1]):
                raise K1Error(f"K1 layout: table {name} field {i}: C {got}, Python "
                              f"{(fname, kind, dt.fields[fname][1])}")
        if lib.kw_k1_row_size(t) != dt.itemsize:
            raise K1Error(f"K1 layout: table {name}: row size differs")


def k1_sample_key(r: dict):
    """The total sample order of `k1_sample_cmp` (`_k1.c`), for sample dicts."""
    def f(v):
        return float("inf") if v != v else v
    return (r["iy"], r["ix"], tuple(r["path"]), r["vx"], r["vy"], r["reason"], r["code"],
            r["lat"], r["lon"], f(r["err"]))


class K1Acc:
    """The K1 accumulator: per-kind counts and worst passing error, up to
    `K1_SAMPLE` samples per kind (sorted by `k1_sample_key`), explained counters
    and C-side stats. `merge` is a sum / max / first-N-of-union, so any partition
    and order of bands gives identical bytes."""

    def __init__(self):
        import numpy as np
        lib = _load_k1()
        self.names = list(_k1_cols["kinds"])
        self.expl_names = list(_k1_cols["explained"])
        self.kinds = np.zeros(len(self.names), _k1_dtype("kind"))
        self.smp = np.zeros(len(self.names) * K1_SAMPLE, _k1_dtype("sample"))
        self.expl = np.zeros(len(self.expl_names), np.int64)
        self.stats = np.zeros(len(_K1_STATS), np.int64)

    def _rows(self, ki):
        n = int(self.kinds["nsamples"][ki])
        out = []
        for r in self.smp[ki * K1_SAMPLE: ki * K1_SAMPLE + n]:
            d = {k: (float(r[k]) if r[k].dtype.kind == "f" else int(r[k]))
                 for k in ("lat", "lon", "err", "ix", "iy", "vx", "vy", "reason", "code")}
            d["path"] = [int(r[f"p{i}"]) for i in range(int(r["depth"]))]
            out.append(d)
        return out

    def result(self) -> dict:
        kinds = {n: {"checked": int(self.kinds["checked"][i]), "failing": int(self.kinds["failing"][i]),
                     "worst": float(self.kinds["worst"][i])} for i, n in enumerate(self.names)}
        return {"kinds": kinds,
                "explained": {n: int(self.expl[i]) for i, n in enumerate(self.expl_names)},
                "samples": {n: self._rows(i) for i, n in enumerate(self.names)},
                "stats": dict(zip(_K1_STATS, (int(v) for v in self.stats)))}

    def merge(self, other: "K1Acc") -> None:
        import numpy as np
        for i in range(len(self.names)):
            rows = self._rows(i) + other._rows(i)
            self.kinds["checked"][i] += other.kinds["checked"][i]
            self.kinds["failing"][i] += other.kinds["failing"][i]
            self.kinds["worst"][i] = max(self.kinds["worst"][i], other.kinds["worst"][i])
            rows.sort(key=k1_sample_key)
            rows = rows[:K1_SAMPLE]
            self.kinds["nsamples"][i] = len(rows)
            blk = self.smp[i * K1_SAMPLE:(i + 1) * K1_SAMPLE]
            blk[:] = np.zeros(1, blk.dtype)
            for j, d in enumerate(rows):
                for k in ("lat", "lon", "err", "ix", "iy", "vx", "vy", "reason", "code"):
                    blk[j][k] = d[k]
                blk[j]["depth"] = len(d["path"])
                for q, v in enumerate(d["path"]):
                    blk[j][f"p{q}"] = v
        self.expl += other.expl
        self.stats += other.stats

    def to_bytes(self) -> bytes:
        """Canonical bytes of the counts, samples and explained counters (not the stats)."""
        parts = []
        for arr in (self.kinds, self.smp):
            parts += [arr[n].tobytes() for n in arr.dtype.names]
        parts.append(self.expl.tobytes())
        return b"".join(parts)


def _k1_colspec():
    import numpy as np
    from . import spool as _spool
    lib = _load_k1()
    names = [c[0] for c in _spool._COLUMNS]
    colmap = np.array([names.index(n) for n in _k1_cols["cols"]], np.int32)
    esz = np.array([np.dtype(c[1]).itemsize for c in _spool._COLUMNS], np.int32)
    ckey = np.array([_spool._COUNT_KEYS.index(c[2]) for c in _spool._COLUMNS], np.int32)
    return colmap, esz, ckey


_k1_spec = None
_K1_ERRORS = {-1: "bad arguments", -2: "D1 failed (a Map Frame lies outside the region)",
              -3: "bad spool index or record", -4: "out of memory"}


_k1_tall_cache: dict = {}


def _k1_tallset(spool: "E1Spool", block_row):
    """The level's tall shapes for the band call (rows, xy, per-shape coordinate offsets,
    bounding boxes x0 x1 y0 y1), computed once per spool and lattice."""
    import numpy as np
    r = block_row[0]
    lat5 = np.array([r["lat0"], r["lon0"], r["cell_lat"], r["cell_lon"], r["wlo"]], np.float64)
    key = (id(spool), lat5.tobytes())
    hit = _k1_tall_cache.get(key)
    if hit is not None and hit[5] is spool:
        return hit
    n = int(np.frombuffer(spool.idx[8:16].tobytes(), "<u8")[0]) if len(spool.idx) >= 16 else 0
    rows, xy = k1_tall(spool, lat5, 0, n)
    if len(rows):
        off = np.zeros(len(rows) + 1, np.int64)
        np.cumsum(rows["n"], out=off[1:])
        st = off[:-1]
        bb = np.empty((len(rows), 4), np.float64)
        bb[:, 0] = np.minimum.reduceat(xy[:, 0], st)
        bb[:, 1] = np.maximum.reduceat(xy[:, 0], st)
        bb[:, 2] = np.minimum.reduceat(xy[:, 1], st)
        bb[:, 3] = np.maximum.reduceat(xy[:, 1], st)
    else:
        off, bb = np.zeros(1, np.int64), np.zeros((1, 4), np.float64)
    rows = np.ascontiguousarray(rows) if len(rows) else np.zeros(1, rows.dtype)
    xy = np.ascontiguousarray(xy) if len(xy) else np.zeros((1, 2), np.float64)
    if len(_k1_tall_cache) > 8:
        _k1_tall_cache.clear()
    hit = (rows, xy, off, np.ascontiguousarray(bb), len(off) > 1, spool)
    _k1_tall_cache[key] = hit
    return hit


class K1Dump:
    """A per-band dump row buffer with the D1-style grow-and-retry (brief 3-02):
    C fills rows in emission order and, when the buffer is full, returns 1 with the
    count it needs; Python grows and calls again. `rows` holds the (trimmed, a
    copy) `K1_DUMP_DTYPE` rows after a successful `k1_check_band`."""

    def __init__(self, cap: int = 1 << 16):
        import numpy as np
        self.dtype = K1_DUMP_DTYPE
        self.rb = self.dtype.itemsize
        self.cap = max(1, int(cap))
        self.buf = np.empty(self.cap * self.rb, np.uint8)
        self.need = np.zeros(1, np.int64)
        self.rows = np.zeros(0, self.dtype)

    def grow(self, n: int) -> None:
        import numpy as np
        self.cap = max(self.cap * 2, int(n) + max(1, int(n) // 4))
        self.buf = np.empty(self.cap * self.rb, np.uint8)


def k1_check_band(region, block_row, rlo, rhi, spool: "E1Spool", acc: K1Acc,
                  dump: "K1Dump | None" = None) -> None:
    """Check one (block, row band) in ONE C call, adding into `acc`: `block_row` is a
    one-row `D1_BLOCK_DTYPE` array, `[rlo, rhi]` the band (None: all). When `dump` is
    given, every failing item of the five kinds is also written into it (grow and
    retry if C reports the buffer too small); `dump.rows` then holds them."""
    import numpy as np
    global _k1_spec
    lib = _load_k1()
    if _k1_spec is None:
        _k1_spec = _k1_colspec()
    colmap, esz, ckey = _k1_spec
    if block_row.dtype != D1_BLOCK_DTYPE or len(block_row) != 1:
        raise K1Error("k1_check_band takes one D1_BLOCK_DTYPE row")
    block_row = np.ascontiguousarray(block_row)
    region = np.ascontiguousarray(region, dtype=np.uint8)
    lo = -(1 << 62) if rlo is None else int(rlo)
    hi = (1 << 62) if rhi is None else int(rhi)
    tall = _k1_tallset(spool, block_row)
    if dump is None:
        rc = lib.kw_k1_band(region.ctypes.data, len(region), block_row.ctypes.data, lo, hi,
                            spool.idx.ctypes.data, len(spool.idx), spool.data.ctypes.data,
                            len(spool.data), colmap.ctypes.data, esz.ctypes.data,
                            ckey.ctypes.data, len(esz), acc.kinds.ctypes.data,
                            acc.smp.ctypes.data, acc.expl.ctypes.data, acc.stats.ctypes.data,
                            tall[0].ctypes.data, tall[1].ctypes.data, tall[2].ctypes.data,
                            tall[3].ctypes.data, len(tall[0]) if tall[4] else 0,
                            None, 0, None)
    else:
        snap = (acc.kinds.copy(), acc.smp.copy(), acc.expl.copy(), acc.stats.copy())
        while True:
            dump.need[0] = 0
            rc = lib.kw_k1_band(region.ctypes.data, len(region), block_row.ctypes.data, lo, hi,
                                spool.idx.ctypes.data, len(spool.idx), spool.data.ctypes.data,
                                len(spool.data), colmap.ctypes.data, esz.ctypes.data,
                                ckey.ctypes.data, len(esz), acc.kinds.ctypes.data,
                                acc.smp.ctypes.data, acc.expl.ctypes.data, acc.stats.ctypes.data,
                                tall[0].ctypes.data, tall[1].ctypes.data, tall[2].ctypes.data,
                                tall[3].ctypes.data, len(tall[0]) if tall[4] else 0,
                                dump.buf.ctypes.data, dump.cap, dump.need.ctypes.data)
            if rc != 1:
                break
            # C mutated the accumulator before it reported "need more": roll it back
            acc.kinds[...] = snap[0]
            acc.smp[...] = snap[1]
            acc.expl[...] = snap[2]
            acc.stats[...] = snap[3]
            dump.grow(int(dump.need[0]))
        n = int(dump.need[0])
        dump.rows = dump.buf[:n * dump.rb].copy().view(dump.dtype)
    _k1_stats["calls"] += 1
    if rc < 0:
        raise K1Error(_K1_ERRORS.get(rc, f"error {rc}"))


def k1_tall(spool: "E1Spool", lat5, a: int, b: int):
    """Tall spool shapes of index rows [a, b): (rows, xy) -- structured rows
    (type, cls, n, hx, hy) and their global raw coordinates (n x 2 float64)."""
    import numpy as np
    global _k1_spec
    lib = _load_k1()
    if _k1_spec is None:
        _k1_spec = _k1_colspec()
    colmap, esz, ckey = _k1_spec
    lat5 = np.ascontiguousarray(lat5, np.float64)
    dt = np.dtype([(n, "<i4") for n in ("type", "cls", "n", "hx", "hy", "rec")])
    rcap, xcap = 1024, 1 << 14
    while True:
        rows, xy, need = np.zeros(rcap, dt), np.zeros(xcap * 2), np.zeros(2, np.int64)
        rc = lib.kw_k1_tall(spool.idx.ctypes.data, len(spool.idx), spool.data.ctypes.data,
                            len(spool.data), colmap.ctypes.data, esz.ctypes.data,
                            ckey.ctypes.data, len(esz), lat5.ctypes.data, a, b,
                            rows.ctypes.data, rcap, xy.ctypes.data, xcap, need.ctypes.data)
        if rc < 0:
            raise K1Error(_K1_ERRORS.get(rc, f"error {rc}"))
        if rc == 0:
            return rows[:need[0]].copy(), xy[:need[1] * 2].reshape(-1, 2).copy()
        rcap, xcap = max(rcap, int(need[0])), max(xcap, int(need[1]))


def k1_stats() -> dict:
    """Process-local K1 totals (`calls`: ctypes band calls)."""
    return dict(_k1_stats)
