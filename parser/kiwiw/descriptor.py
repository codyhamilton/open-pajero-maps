"""The level descriptor (plan 03, 3C-06; DESIGN.md Contract B, "The level
descriptor"): one contiguous little-endian bytes buffer with a versioned
header, built by Python once per level and handed to C (E1 now, E2 in
3C-07). It carries data only -- grid, frame ranges, window, limits, the
spool column layout and the cell-existence bitmap -- never a rule.

Layout (the C reader, `_e1.c`, documents the same table):

    off  type        field
      0  u8[8]       magic b"KWLDESC1"
      8  u32         version (1)
     12  u32         header_bytes (168)
     16  u64         total_bytes (whole buffer, a multiple of 8)
     24  i32 x 4     level, nx, ny, frame_class (FRAME_CLASS_CODES)
     40  f64 x 4     disc_lat_lo, disc_lon_lo, cell_lat, cell_lon
     72  i32 x 4     range[parcel_type 0..3]: 0 = undivided frame's range,
                     t = pardiv<t> sub-parcel range, -1 = level has none
     88  i32 x 4     window (ix_lo, ix_hi, iy_lo, iy_hi), inclusive
    104  i32         max_frame (131070, the frame byte ceiling)
    108  i32         threshold (the level's division threshold, bytes)
    112  i64 x 3     kind_limits (road, bg, name); NO_LIMIT = none
    136  u64         mask_off
    144  u64         mask_len (bytes)
    152  u32         cols_off
    156  u32         n_cols
    160  u32         n_count_keys (9)
    164  u8 x 4      role: column index of b_class, b_nstored, c_lat, c_lon
    168  cols table  n_cols x (u8 elem_size, u8 count_key_index) in
                     `spool._COLUMNS` order, zero-padded to 8
         mask        existence bitmap: bit iy*nx + ix, LSB-first per byte;
                     set for every spool cell and every cell of the mask
                     rect; zero-padded to 8

E1 row layout (`E1_ROW_DTYPE`, 32 bytes): tix i32, tiy i32, six i32,
siy i32, cell_off u64 (source record's .data offset), shape u32 (index
among the source cell's backgrounds), kind u8 (0 edge, 1 interior cover),
3 zero pad bytes.
"""
from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from . import mesh
from .spool import _COLUMNS, _COUNT_KEYS, IDX_MAGIC

MAGIC = b"KWLDESC1"
VERSION = 1
HEADER_BYTES = 168
NO_LIMIT = 1 << 62
MAX_FRAME_BYTES = 131070
FRAME_CLASS_CODES = {"urban": 0, "full": 1}
ROLE_COLUMNS = ("b_class", "b_nstored", "c_lat", "c_lon")

_HDR = struct.Struct("<8sIIQ4i4d4i4iii3qQQIII4B")
assert _HDR.size == HEADER_BYTES

E1_ROW_DTYPE = np.dtype({
    "names": ["tix", "tiy", "six", "siy", "cell_off", "shape", "kind"],
    "formats": ["<i4", "<i4", "<i4", "<i4", "<u8", "<u4", "u1"],
    "offsets": [0, 4, 8, 12, 16, 24, 28],
    "itemsize": 32})


def _pad8(n: int) -> int:
    return (n + 7) & ~7


def _range_table(level: int) -> list[int]:
    out = [mesh.g_frame_range(level)]
    for pt in (1, 2, 3):
        try:
            out.append(mesh.g_frame_range(level, pt, 0))
        except KeyError:
            out.append(-1)
    return out


def build(level: int, ix, iy, *, mask_rect=None, window=None, threshold: int = 0,
          kind_limits: dict | None = None, grid: mesh.CellGrid | None = None) -> bytes:
    """The descriptor for `level`, whose existing cells are the spool cells
    `(ix, iy)` plus `mask_rect` (inclusive `(ix_lo, ix_hi, iy_lo, iy_hi)`).
    `window` (inclusive rect) limits receiving cells; default the whole level."""
    g = grid or mesh.CellGrid.from_reference(level)
    nx, ny = g.nx, g.ny
    bits = np.zeros((ny, nx), bool)
    ix = np.asarray(ix, np.int64)
    iy = np.asarray(iy, np.int64)
    if len(ix):
        if ix.min() < 0 or ix.max() >= nx or iy.min() < 0 or iy.max() >= ny:
            raise ValueError("spool cell outside the level grid")
        bits[iy, ix] = True
    if mask_rect is not None:
        x0, x1, y0, y1 = mask_rect
        bits[max(y0, 0):min(y1, ny - 1) + 1, max(x0, 0):min(x1, nx - 1) + 1] = True
    mask = np.packbits(bits.ravel(), bitorder="little").tobytes()
    win = tuple(window) if window is not None else (0, nx - 1, 0, ny - 1)
    kl = kind_limits or {}
    lim = [int(kl.get(k)) if kl.get(k) is not None else NO_LIMIT for k in ("road", "bg", "name")]
    cols = b"".join(bytes((np.dtype(dt).itemsize, _COUNT_KEYS.index(key)))
                    for _n, dt, key in _COLUMNS)
    names = [n for n, _dt, _k in _COLUMNS]
    cols_off = HEADER_BYTES
    mask_off = cols_off + _pad8(len(cols))
    total = mask_off + _pad8(len(mask))
    hdr = _HDR.pack(MAGIC, VERSION, HEADER_BYTES, total,
                    level, nx, ny, FRAME_CLASS_CODES[mesh.g_frame_class(level)],
                    g.disc_lat_lo, g.disc_lon_lo, g.cell_lat, g.cell_lon,
                    *_range_table(level), *win, MAX_FRAME_BYTES, int(threshold), *lim,
                    mask_off, len(mask), cols_off, len(_COLUMNS), len(_COUNT_KEYS),
                    *(names.index(n) for n in ROLE_COLUMNS))
    buf = bytearray(total)
    buf[:HEADER_BYTES] = hdr
    buf[cols_off:cols_off + len(cols)] = cols
    buf[mask_off:mask_off + len(mask)] = mask
    return bytes(buf)


def spool_cells(spool_dir, level: int) -> tuple[np.ndarray, np.ndarray]:
    """`(ix, iy)` of every cell in the level's spool index (empty if none)."""
    p = Path(spool_dir) / f"level_{level}.idx"
    if not p.exists():
        return np.zeros(0, np.int32), np.zeros(0, np.int32)
    raw = np.memmap(p, dtype=np.uint8, mode="r")
    if bytes(raw[:8]) != IDX_MAGIC:
        raise ValueError(f"{p}: not a spool index")
    n = int(raw[8:16].view("<u8")[0])
    ix = raw[48:48 + 4 * n].view("<i4")
    iy = raw[48 + 4 * n:48 + 8 * n].view("<i4")
    return np.array(ix), np.array(iy)


def build_for_spool(spool_dir, level: int, **kw) -> bytes:
    """`build` with the existing cells read from the spool's index."""
    ix, iy = spool_cells(spool_dir, level)
    return build(level, ix, iy, **kw)


def parse_level(buf: bytes) -> int:
    """The level field of a descriptor (header check only)."""
    if bytes(buf[:8]) != MAGIC:
        raise ValueError("not a level descriptor")
    return struct.unpack_from("<i", buf, 24)[0]


def parse(buf: bytes) -> dict:
    """Decode a descriptor into a dict (tests and diagnostics)."""
    h = _HDR.unpack_from(buf)
    d = {"magic": h[0], "version": h[1], "header_bytes": h[2], "total_bytes": h[3],
         "level": h[4], "nx": h[5], "ny": h[6], "frame_class": h[7],
         "disc_lat_lo": h[8], "disc_lon_lo": h[9], "cell_lat": h[10], "cell_lon": h[11],
         "range": tuple(h[12:16]), "window": tuple(h[16:20]), "max_frame": h[20],
         "threshold": h[21], "kind_limits": tuple(h[22:25]),
         "n_count_keys": h[29], "roles": tuple(h[30:34])}
    mask_off, mask_len, cols_off, n_cols = h[25], h[26], h[27], h[28]
    c = buf[cols_off:cols_off + 2 * n_cols]
    d["columns"] = [(c[2 * i], c[2 * i + 1]) for i in range(n_cols)]
    nx, ny = d["nx"], d["ny"]
    bits = np.unpackbits(np.frombuffer(buf, np.uint8, mask_len, mask_off), bitorder="little")
    d["mask"] = bits[:nx * ny].reshape(ny, nx).astype(bool)
    return d
