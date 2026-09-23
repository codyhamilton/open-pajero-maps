"""Give a background shape to every cell it overlaps, as R does (Plan 03, 3-09).

The extractor spools each background shape in the one cell holding its
centroid (`osm_to_parcel_geometry`). Since 3-07 every cell clips its
background geometry to its own rectangle, so the part of a shape that crosses
into a neighbouring cell was clipped away and the neighbour never had it: G
mirrored ~2% of edge-crossing vertices where R mirrors 75-87%. R gives a
background shape to every frame it overlaps.

This module is an assembly-time pre-pass over the spool of record (no
re-extraction, no spool format change). Per level it finds, for every shape
whose extent leaves its own cell, the other cells its geometry overlaps in the
level's global cell lattice (the lattice 3-07 clips in: cell `(ix, iy)` spans
`[ix, ix+1] x [iy, iy+1]` in `gx = (lon - disc_lon_lo) / cell_lon`,
`gy = (lat - disc_lat_lo) / cell_lat`, exactly the frame-local raw lattice
divided by the range):

- **edge cells** -- a segment of the shape passes within `EPS` of the cell's
  closed rectangle (a conservative supercover). These receive the shape
  unchanged and clip it themselves; a candidate whose clip is empty writes
  nothing.
- **interior cells** (polygons only) -- no segment comes near the cell and the
  cell's centre is inside the ring (even-odd, as `clip._pip`). Such a cell is
  wholly covered, and its clip is the frame-corner rectangle whatever the
  ring's shape (`clip._ring_pieces`' no-chain branch). It receives, instead of
  the full ring, a 4-corner ring around the cell a quarter-cell outside it,
  whose clip is that same rectangle -- so a large polygon's interior costs 5
  points per cell, not its whole outline.

Only cells the build emits receive shapes (spool cells, plus the coverage
mask's cells when mask fill is on); overlapped cells that do not exist are
counted as skipped. Within a cell the order is: the cell's own shapes in spool
order, then borrowed shapes by source `(iy, ix)` and spool index -- the global
shape id order of the pre-pass, which scans the spool in stream order.

Output of `build_level` is a directory of arrays (pairs sorted by target
`(iy, ix)` then shape id, per-shape metadata, raw coordinate stores), read by
`RowOverlap` in each encoding worker for its rows. Nothing depends on the
chunking or the worker count.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import numpy as np

from .spool import _COLUMNS, SpoolReader, columns_to_content, decode_columns, \
    encode_columns, merge_columns

EPS = 1e-6          # cell units (4096 raw per cell -> ~0.004 raw)
COVER_MARGIN = 0.25  # substitute ring: a quarter cell outside the cell


def _key(ix, iy):
    return (np.asarray(iy, np.int64) << 32) | (np.asarray(ix, np.int64) & 0xFFFFFFFF)


def _unkey(k):
    k = np.asarray(k, np.int64)
    return (k & 0xFFFFFFFF).astype(np.int64), (k >> 32).astype(np.int64)


# --------------------------------------------------------------- geometry

def shape_cells(gx, gy, closed: bool, nx: int | None = None, ny: int | None = None):
    """`(edge, inner)` cell lists `[(ix, iy), ...]` of one shape in cell
    coordinates (see module docstring). With `nx`/`ny`, only cells of the
    grid are returned."""
    e, i = _shape_cell_keys(np.asarray(gx, np.float64), np.asarray(gy, np.float64),
                            closed, nx, ny)
    ex, ey = _unkey(e)
    ix_, iy_ = _unkey(i)
    return list(zip(ex.tolist(), ey.tolist())), list(zip(ix_.tolist(), iy_.tolist()))


def _shape_cell_keys(gx, gy, closed, nx=None, ny=None):
    lo_x, hi_x = (-1, nx) if nx is not None else (-(1 << 30), 1 << 30)
    lo_y, hi_y = (-1, ny) if ny is not None else (-(1 << 30), 1 << 30)
    if closed and len(gx) > 1 and (gx[0] != gx[-1] or gy[0] != gy[-1]):
        gx = np.append(gx, gx[0])
        gy = np.append(gy, gy[0])
    if len(gx) == 1:
        gx = np.append(gx, gx)
        gy = np.append(gy, gy)
    ax, ay, bx, by = gx[:-1], gy[:-1], gx[1:], gy[1:]
    xmin, xmax = np.minimum(ax, bx), np.maximum(ax, bx)
    ymin, ymax = np.minimum(ay, by), np.maximum(ay, by)
    xlo = np.floor(xmin - EPS).astype(np.int64)
    xhi = np.floor(xmax + EPS).astype(np.int64)
    ylo = np.floor(ymin - EPS).astype(np.int64)
    yhi = np.floor(ymax + EPS).astype(np.int64)
    small = (xhi - xlo <= 1) & (yhi - ylo <= 1)
    parts = []
    for dx in (0, 1):
        for dy in (0, 1):
            m = small & (xlo + dx <= xhi) & (ylo + dy <= yhi)
            if m.any():
                parts.append(_key(xlo[m] + dx, ylo[m] + dy))
    for s in np.nonzero(~small)[0].tolist():
        c = np.arange(max(xlo[s], lo_x), min(xhi[s], hi_x) + 1, dtype=np.int64)
        if not len(c):
            continue
        if bx[s] == ax[s]:
            r0 = np.full(len(c), ylo[s])
            r1 = np.full(len(c), yhi[s])
        else:
            xa = np.maximum(c - EPS, xmin[s])
            xb = np.minimum(c + 1 + EPS, xmax[s])
            t = (by[s] - ay[s]) / (bx[s] - ax[s])
            ya = ay[s] + (xa - ax[s]) * t
            yb = ay[s] + (xb - ax[s]) * t
            r0 = np.floor(np.minimum(ya, yb) - EPS).astype(np.int64)
            r1 = np.floor(np.maximum(ya, yb) + EPS).astype(np.int64)
        r0 = np.maximum(r0, lo_y)
        r1 = np.minimum(r1, hi_y)
        cnt = np.maximum(r1 - r0 + 1, 0)
        if cnt.sum() == 0:
            continue
        rep = np.repeat(np.arange(len(c)), cnt)
        off = np.repeat(np.cumsum(cnt) - cnt, cnt)
        parts.append(_key(c[rep], r0[rep] + np.arange(len(rep)) - off))
    edge = np.unique(np.concatenate(parts)) if parts else np.zeros(0, np.int64)
    if nx is not None:
        ex, ey = _unkey(edge)
        edge = edge[(ex >= 0) & (ex < nx) & (ey >= 0) & (ey < ny)]
    if not closed:
        return edge, np.zeros(0, np.int64)
    # Interior: even-odd scanline at each row centre.
    m = ay != by
    ax, ay, bx, by = ax[m], ay[m], bx[m], by[m]
    rlo = np.ceil(np.minimum(ay, by) - 0.5).astype(np.int64)
    rhi = np.ceil(np.maximum(ay, by) - 0.5).astype(np.int64) - 1
    if ny is not None:
        rlo = np.maximum(rlo, 0)
        rhi = np.minimum(rhi, ny - 1)
    cnt = np.maximum(rhi - rlo + 1, 0)
    if cnt.sum() == 0:
        return edge, np.zeros(0, np.int64)
    rep = np.repeat(np.arange(len(ax)), cnt)
    r = rlo[rep] + np.arange(len(rep)) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    yc = r + 0.5
    x = ax[rep] + (yc - ay[rep]) / (by[rep] - ay[rep]) * (bx[rep] - ax[rep])
    o = np.lexsort((x, r))
    r, x = r[o], x[o]
    r, xa, xb = r[0::2], x[0::2], x[1::2]
    c0 = np.ceil(xa - 0.5).astype(np.int64)
    c1 = np.floor(xb - 0.5).astype(np.int64)
    if nx is not None:
        c0 = np.maximum(c0, 0)
        c1 = np.minimum(c1, nx - 1)
    cnt = np.maximum(c1 - c0 + 1, 0)
    if cnt.sum() == 0:
        return edge, np.zeros(0, np.int64)
    rep = np.repeat(np.arange(len(c0)), cnt)
    cc = c0[rep] + np.arange(len(rep)) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    inner = np.unique(_key(cc, r[rep]))
    inner = inner[~np.isin(inner, edge, assume_unique=True)]
    return edge, inner


def cover_ring(bounds) -> list[tuple[float, float]]:
    """The substitute ring of an interior cell: its bounds grown by a quarter
    cell, counter-clockwise, closed. Clips to the frame-corner rectangle."""
    mlat = (bounds.lat_hi - bounds.lat_lo) * COVER_MARGIN
    mlon = (bounds.lon_hi - bounds.lon_lo) * COVER_MARGIN
    a, b = bounds.lat_lo - mlat, bounds.lat_hi + mlat
    c, d = bounds.lon_lo - mlon, bounds.lon_hi + mlon
    return [(a, c), (a, d), (b, d), (b, c), (a, c)]


# ---------------------------------------------------------------- pre-pass

def _grid(level):
    from osm_to_parcel_geometry import TileGrid
    return TileGrid.from_reference(level)


class _Exists:
    def __init__(self, spool_keys: np.ndarray, mask_rect):
        self.keys = spool_keys
        self.rect = mask_rect

    def __call__(self, keys: np.ndarray) -> np.ndarray:
        pos = np.searchsorted(self.keys, keys)
        pos = np.minimum(pos, max(len(self.keys) - 1, 0))
        ok = (self.keys[pos] == keys) if len(self.keys) else np.zeros(len(keys), bool)
        if self.rect is not None:
            x, y = _unkey(keys)
            x0, x1, y0, y1 = self.rect
            ok |= (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        return ok


def _in_window(keys, window):
    x, y = _unkey(keys)
    return keys[(x >= window[0]) & (x <= window[1]) & (y >= window[2]) & (y <= window[3])]


def _scan(job):
    """Scan spool cells `[a, b)` of a level: every shape reaching outside its
    own cell, with its receiving cells. Returns arrays + stats."""
    spool_dir, level, a, b, out_dir, chunk, mask_rect, window = job
    g = _grid(level)
    rd = SpoolReader(spool_dir)
    idx = rd._load_idx(level)
    exists = _Exists(np.sort(_key(idx.ix, idx.iy)), mask_rect)
    store_path = os.path.join(out_dir, f"store_{chunk:05d}.f64")
    tk, ts, tc = [], [], []
    meta = {k: [] for k in ("cls", "type", "ncoords", "mult", "flags", "off", "n")}
    labels = []
    skipped = 0
    lsid = 0
    pos = 0
    with open(store_path, "wb") as st:
        for ix, iy, raw in rd.iter_cell_raw(level, a, b):
            cols = decode_columns(raw)
            n = cols["b_nstored"]
            if not len(n):
                continue
            lat, lon = cols["c_lat"], cols["c_lon"]
            gx = (lon - g.disc_lon_lo) / g.cell_lon
            gy = (lat - g.disc_lat_lo) / g.cell_lat
            ends = np.cumsum(n.astype(np.int64))
            starts = ends - n
            nz = n > 0
            if not nz.any():
                continue
            s_nz = starts[nz]
            span = np.zeros(len(n), bool)
            span[nz] = ((np.floor(np.minimum.reduceat(gx, s_nz) - EPS) < ix)
                        | (np.floor(np.maximum.reduceat(gx, s_nz) + EPS) > ix)
                        | (np.floor(np.minimum.reduceat(gy, s_nz) - EPS) < iy)
                        | (np.floor(np.maximum.reduceat(gy, s_nz) + EPS) > iy))
            if window is not None:
                wx0, wx1, wy0, wy1 = window
                span[nz] &= ((np.floor(np.maximum.reduceat(gx, s_nz) + EPS) >= wx0)
                             & (np.floor(np.minimum.reduceat(gx, s_nz) - EPS) <= wx1)
                             & (np.floor(np.maximum.reduceat(gy, s_nz) + EPS) >= wy0)
                             & (np.floor(np.minimum.reduceat(gy, s_nz) - EPS) <= wy1))
            if not span.any():
                continue
            lab_len = cols["b_label_len"]
            lab_end = np.cumsum(lab_len.astype(np.int64))
            blob = cols["blob_bg_label"]
            own = int(_key(ix, iy))
            for k in np.nonzero(span)[0].tolist():
                s, e = int(starts[k]), int(ends[k])
                edge, inner = _shape_cell_keys(gx[s:e], gy[s:e], bool(cols["b_class"][k] == 2),
                                               g.nx, g.ny)
                edge = edge[edge != own]
                inner = inner[inner != own]
                if window is not None:
                    edge, inner = _in_window(edge, window), _in_window(inner, window)
                ee, ei = exists(edge), exists(inner)
                skipped += int((~ee).sum() + (~ei).sum())
                edge, inner = edge[ee], inner[ei]
                if not (len(edge) or len(inner)):
                    continue
                if len(edge):
                    xy = np.empty((e - s, 2), np.float64)
                    xy[:, 0], xy[:, 1] = lat[s:e], lon[s:e]
                    st.write(xy.tobytes())
                    meta["off"].append(pos)
                    pos += e - s
                else:
                    meta["off"].append(-1)
                meta["n"].append(e - s)
                meta["cls"].append(int(cols["b_class"][k]))
                meta["type"].append(int(cols["b_type"][k]))
                meta["ncoords"].append(int(cols["b_ncoords"][k]))
                meta["mult"].append(int(cols["b_mult"][k]))
                meta["flags"].append(int(cols["b_flags"][k]))
                labels.append(blob[lab_end[k] - lab_len[k]:lab_end[k]].tobytes())
                for arr, cover in ((edge, 0), (inner, 1)):
                    if len(arr):
                        tk.append(arr)
                        ts.append(np.full(len(arr), lsid, np.int64))
                        tc.append(np.full(len(arr), cover, np.uint8))
                lsid += 1
    rd.close()
    cat = (lambda xs, dt: np.concatenate(xs) if xs else np.zeros(0, dt))
    return (cat(tk, np.int64), cat(ts, np.int64), cat(tc, np.uint8),
            {k: np.array(v, np.int64) for k, v in meta.items()}, labels, store_path,
            skipped)


def _scan_ranges(reader: SpoolReader, level: int, n_chunks: int):
    _iy, length = reader.cell_weights(level)
    n = len(length)
    if n == 0:
        return []
    if n_chunks <= 1:
        return [(0, n)]
    cum = np.cumsum(length.astype(np.float64))
    cuts = np.searchsorted(cum, cum[-1] * np.arange(1, n_chunks) / n_chunks) + 1
    edges = [0] + sorted({int(c) for c in cuts if 0 < c < n}) + [n]
    return list(zip(edges[:-1], edges[1:]))


def build_level(spool_dir: str, level: int, parent_dir: str, mask_rect=None,
                pool=None, jobs: int = 1, window=None) -> tuple[str | None, dict]:
    """Run the pre-pass for `level`; returns `(overlap_dir, stats)`
    (`overlap_dir` None when no shape reaches another existing cell).

    `mask_rect` (inclusive `(ix_lo, ix_hi, iy_lo, iy_hi)`) adds the
    mask-filled cells to the existing set; `window` (same form, a fixture's
    cell range) restricts receivers to it -- a window's cells get exactly what
    the whole-disc pass would give them."""
    reader = SpoolReader(spool_dir)
    try:
        ranges = _scan_ranges(reader, level, jobs * 4 if pool is not None and jobs > 1 else 1)
    finally:
        reader.close()
    stats = {"shared_shapes": 0, "edge_cells": 0, "interior_cells": 0,
             "skipped_missing_cells": 0}
    if not ranges:
        return None, stats
    os.makedirs(parent_dir, exist_ok=True)
    out = tempfile.mkdtemp(prefix=f".overlap_L{level}_", dir=parent_dir)
    jobs_ = [(spool_dir, level, a, b, out, i, mask_rect, window) for i, (a, b) in enumerate(ranges)]
    results = pool.map(_scan, jobs_, chunksize=1) if len(jobs_) > 1 else [_scan(jobs_[0])]
    keys, sids, cover, stores, labels = [], [], [], [], []
    meta = {}
    base = 0
    for ci, (tk, ts, tc, m, lab, store, sk) in enumerate(results):
        keys.append(tk)
        sids.append(ts + base)
        cover.append(tc)
        for k, v in m.items():
            meta.setdefault(k, []).append(v)
        meta.setdefault("store", []).append(np.full(len(m["n"]), ci, np.int64))
        labels += lab
        stores.append(os.path.basename(store))
        stats["skipped_missing_cells"] += sk
        base += len(m["n"])
    keys = np.concatenate(keys)
    sids = np.concatenate(sids)
    cover = np.concatenate(cover)
    if not len(keys):
        shutil.rmtree(out)
        return None, stats
    o = np.lexsort((sids, keys))
    np.save(os.path.join(out, "keys.npy"), keys[o])
    np.save(os.path.join(out, "sids.npy"), sids[o])
    np.save(os.path.join(out, "cover.npy"), cover[o])
    for k, v in meta.items():
        np.save(os.path.join(out, f"m_{k}.npy"), np.concatenate(v))
    lab_len = np.array([len(x) for x in labels], np.int64)
    np.save(os.path.join(out, "m_lablen.npy"), lab_len)
    np.save(os.path.join(out, "m_labend.npy"), np.cumsum(lab_len))
    Path(out, "labels.bin").write_bytes(b"".join(labels))
    Path(out, "stores.txt").write_text("\n".join(stores))
    stats["shared_shapes"] = int(base)
    stats["interior_cells"] = int(cover.sum())
    stats["edge_cells"] = int(len(cover) - stats["interior_cells"])
    return out, stats


# ------------------------------------------------------------------ reader

class LevelOverlap:
    """Worker-side view of one level's pre-pass output."""

    def __init__(self, path: str, level: int):
        self.path = path
        self.level = level
        self.grid = _grid(level)
        ld = (lambda n, mm=None: np.load(os.path.join(path, n), mmap_mode=mm))
        self._keys = ld("keys.npy", "r")
        self._sids = ld("sids.npy", "r")
        self._cover = ld("cover.npy", "r")
        self.m = {k: ld(f"m_{k}.npy", "r") for k in ("cls", "type", "ncoords", "mult",
                                                     "flags", "off", "n", "store",
                                                     "lablen", "labend")}
        lp = os.path.join(path, "labels.bin")
        self.labels = np.memmap(lp, "u1", "r") if os.path.getsize(lp) else np.zeros(0, "u1")
        self.stores = Path(path, "stores.txt").read_text().split("\n")
        self._fds: dict[int, int] = {}

    def close(self):
        for fd in self._fds.values():
            os.close(fd)
        self._fds.clear()

    def rows(self, row_lo=None, row_hi=None) -> "RowOverlap":
        a = 0 if row_lo is None else int(np.searchsorted(self._keys, _key(0, row_lo)))
        b = len(self._keys) if row_hi is None else int(np.searchsorted(self._keys,
                                                                      _key(0, row_hi)))
        return RowOverlap(self, np.array(self._keys[a:b]), np.array(self._sids[a:b]),
                          np.array(self._cover[a:b]))

    def _coords(self, sid: int) -> np.ndarray:
        st = int(self.m["store"][sid])
        fd = self._fds.get(st)
        if fd is None:
            fd = self._fds[st] = os.open(os.path.join(self.path, self.stores[st]), os.O_RDONLY)
        n = int(self.m["n"][sid])
        buf = os.pread(fd, n * 16, int(self.m["off"][sid]) * 16)
        return np.frombuffer(buf, np.float64).reshape(n, 2)


class RowOverlap:
    """Borrowed shapes of the cells in one row range."""

    def __init__(self, lo: LevelOverlap, keys, sids, cover):
        self.lo, self.keys, self.sids, self.cover = lo, keys, sids, cover

    def extra_columns(self, ix: int, iy: int):
        k = int(_key(ix, iy))
        a = int(np.searchsorted(self.keys, k, "left"))
        b = int(np.searchsorted(self.keys, k, "right"))
        if a == b:
            return None
        from osm_to_parcel_geometry import parcel_bounds
        m = self.lo.m
        sids = self.sids[a:b].tolist()
        cov = self.cover[a:b].tolist()
        xy = []
        ring = None
        for sid, c in zip(sids, cov):
            if c:
                if ring is None:
                    ring = np.array(cover_ring(parcel_bounds(ix, iy, self.lo.grid)), np.float64)
                xy.append(ring)
            else:
                xy.append(self.lo._coords(sid))
        sids_a = np.array(sids, np.int64)
        nst = np.array([len(p) for p in xy], np.int64)
        coords = np.concatenate(xy)
        le = m["labend"]
        ll = m["lablen"][sids_a]
        blob = b"".join(self.lo.labels[int(le[s]) - int(m["lablen"][s]):int(le[s])].tobytes()
                        for s in sids)
        cols = {name: np.zeros(0, dt) for name, dt, _k in _COLUMNS}
        cols.update({
            "b_class": m["cls"][sids_a].astype("<i4"), "b_type": m["type"][sids_a].astype("<i4"),
            "b_ncoords": np.where(cov, 4, m["ncoords"][sids_a]).astype("<i4"),
            "b_mult": m["mult"][sids_a].astype("<i4"), "b_flags": m["flags"][sids_a].astype("u1"),
            "b_nstored": nst.astype("<i4"), "b_label_len": ll.astype("<i4"),
            "c_lat": np.ascontiguousarray(coords[:, 0]), "c_lon": np.ascontiguousarray(coords[:, 1]),
            "blob_bg_label": np.frombuffer(blob, "u1"),
        })
        return cols

    def merge_raw(self, ix: int, iy: int, raw):
        """The cell's spool record (or None for a mask-filled empty cell)
        with its borrowed shapes appended."""
        extra = self.extra_columns(ix, iy)
        if extra is None:
            return raw
        if raw is None:
            return encode_columns(extra)
        return encode_columns(merge_columns([decode_columns(raw), extra]))

    def merge_content(self, ix: int, iy: int, content: dict) -> dict:
        extra = self.extra_columns(ix, iy)
        if extra is None:
            return content
        add = columns_to_content(extra)["backgrounds"]
        return {"roads": content.get("roads") or [], "names": content.get("names") or [],
                "backgrounds": list(content.get("backgrounds") or []) + add}


_OPEN: dict = {}


def open_rows(path: str | None, level: int, row_lo=None, row_hi=None):
    """`RowOverlap` for `[row_lo, row_hi)` of the pre-pass at `path` (None ->
    None). Keeps the most recent level's arrays open per process."""
    if path is None:
        return None
    lo = _OPEN.get(path)
    if lo is None:
        for old in _OPEN.values():
            old.close()
        _OPEN.clear()
        lo = _OPEN[path] = LevelOverlap(path, level)
    return lo.rows(row_lo, row_hi)


def remove(path: str | None) -> None:
    if path is None:
        return
    lo = _OPEN.pop(path, None)
    if lo is not None:
        lo.close()
    shutil.rmtree(path, ignore_errors=True)
