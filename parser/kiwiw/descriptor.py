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
  total-128 division block (3C-09; E2 reads it, E1 ignores it; the
                     header version stays 1 because `_e1.c` is not changed):
      +0  u8[8]      magic b"KWLDIV01"
      +8  i32 x 4    pardiv1 sub-parcel ranges (sub 0..3; -1 = none)
     +24  i32 x 16   pardiv2 sub-parcel ranges (sub 0..15; -1 = none)
     +88  u8 x 16    road keep rank by road type (0..15)
    +104  u8         road keep rank of any other type
    +105  u8         name halo on this level (0/1)
    +106  u8         name keep rank of a repeated (text, type)
    +107  u8         name keep rank of any other type
    +108  u8 x 8     name keep rank by name type (0..7)
    +116  u32        pinned road types (bit t = type t always kept first)
    +120  u8 x 8     zero

E1 row layout (`E1_ROW_DTYPE`, 32 bytes): tix i32, tiy i32, six i32,
siy i32, cell_off u64 (source record's .data offset), shape u32 (index
among the source cell's backgrounds), kind u8 (0 edge, 1 interior cover),
3 zero pad bytes.

E2 (3C-07) outputs. Frame index row (`E2_INDEX_DTYPE`, 36 bytes packed):
ix i32, iy i32, level u8, pt u8, sx u8, sy u8, off u64 (absolute offset of
the frame in E2's output fd), len u32, road u32, bg u32, name u32 (the
frame's section sizes). Declined row (`E2_DECLINED_DTYPE`, 28 bytes
packed): ix i32, iy i32, reason u32 (1 = needs division), off u64, len u64
(unused since 3C-09: 0), len u64 (0). E2 divides every parent itself, so a
declined row is a build error.
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

E2_INDEX_DTYPE = np.dtype({
    "names": ["ix", "iy", "level", "pt", "sx", "sy", "off", "len", "road", "bg", "name"],
    "formats": ["<i4", "<i4", "u1", "u1", "u1", "u1", "<u8", "<u4", "<u4", "<u4", "<u4"],
    "offsets": [0, 4, 8, 9, 10, 11, 12, 20, 24, 28, 32],
    "itemsize": 36})

E2_DECLINED_DTYPE = np.dtype({
    "names": ["ix", "iy", "reason", "off", "len"],
    "formats": ["<i4", "<i4", "<u4", "<u8", "<u8"],
    "offsets": [0, 4, 8, 12, 20],
    "itemsize": 28})


DIV_MAGIC = b"KWLDIV01"
DIV_BYTES = 128
_DIV = struct.Struct("<8s4i16i16sBBBB8sI8x")
assert _DIV.size == DIV_BYTES

# Keep-order data for over-limit trimming (was `divide.py`'s tables): road
# rank by type (lower = kept first; type 10 ranks 7 on level 0, else 5),
# name rank by type, the rank of a repeated (text, type), and the road types
# pinned ahead of every other road from level 2 up.
ROAD_RANK = {12: 0, 0: 1, 4: 2, 3: 3, 9: 4, 10: 5, 7: 6}
ROAD_RANK_L0 = {10: 7}
ROAD_RANK_DEFAULT = 8
NAME_RANK = {5: 0, 6: 2}
NAME_RANK_DEFAULT = 1
NAME_RANK_DUP = 3
PINNED_ROAD_TYPES = (12, 0)
PIN_FROM_LEVEL = 2


def _div_block(level: int, name_halo: bool) -> bytes:
    def rng(pt, n):
        out = []
        for sub in range(n):
            try:
                out.append(mesh.g_frame_range(level, pt, sub))
            except KeyError:
                out.append(-1)
        return out
    rr = bytearray([ROAD_RANK_DEFAULT] * 16)
    for t, r in ROAD_RANK.items():
        rr[t] = ROAD_RANK_L0.get(t, r) if level == 0 else r
    nr = bytearray([NAME_RANK_DEFAULT] * 8)
    for t, r in NAME_RANK.items():
        nr[t] = r
    pin = 0
    if level >= PIN_FROM_LEVEL:
        for t in PINNED_ROAD_TYPES:
            pin |= 1 << t
    return _DIV.pack(DIV_MAGIC, *rng(1, 4), *rng(2, 16), bytes(rr), ROAD_RANK_DEFAULT,
                     1 if name_halo else 0, NAME_RANK_DUP, NAME_RANK_DEFAULT, bytes(nr), pin)


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
          kind_limits: dict | None = None, grid: mesh.CellGrid | None = None,
          name_halo: bool = False) -> bytes:
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
    div_off = mask_off + _pad8(len(mask))
    total = div_off + DIV_BYTES
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
    buf[div_off:total] = _div_block(level, name_halo)
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
    v = _DIV.unpack_from(buf, len(buf) - DIV_BYTES)
    if v[0] != DIV_MAGIC:
        raise ValueError("descriptor has no division block")
    d["div"] = {"range1": tuple(v[1:5]), "range2": tuple(v[5:21]), "road_rank": tuple(v[21]),
                "road_rank_default": v[22], "name_halo": v[23], "name_rank_dup": v[24],
                "name_rank_default": v[25], "name_rank": tuple(v[26]), "pin_mask": v[27]}
    return d
