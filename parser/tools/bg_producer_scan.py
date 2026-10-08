#!/usr/bin/env python3
"""Plan 46: tracked background producer scan.

Rebuilds per-dump-row producer class (design 44 unique-byte | unique-fragment
under Moore R=8 ∪ bbox-meet) and historical bit predicates
(s02_producer_verified, residual_crossing_verified) via a C shim compiled from
a pinned `_cenc.c`.

Does not change K1 or rules order. Streaming by (level, ix, iy) leaf groups.
With --disc, unique-byte uses leaf record wire bytes (required for historical
bit predicates). Without --disc, unique-byte is skipped (fragment-only path).
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import gzip
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

_PARSER = Path(__file__).resolve().parent.parent
_TOOLS = Path(__file__).resolve().parent
sys.path[:0] = [str(_PARSER), str(_TOOLS)]

from bg_owner_exclusive import (  # noqa: E402
    compile_probe, load_probe, find_producer,
)

SHIM_SRC = _TOOLS / "_bg_producer_scan.c"
DEFAULT_R = 8
GROUP = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape")


def _find_cc() -> str:
    from kiwiw import cbuild
    return cbuild._find_cc()


def _cflags() -> list[str]:
    from kiwiw import cbuild
    return list(cbuild.CFLAGS)


def compile_shim(cenc_c: Path | str | None = None, out: Path | str | None = None) -> Path:
    """Build _bg_producer_scan.so against `cenc_c` (default in-tree `_cenc.c`)."""
    cenc_c = Path(cenc_c) if cenc_c else _PARSER / "kiwiw" / "_cenc.c"
    if out is None:
        import hashlib
        h = hashlib.sha256(cenc_c.read_bytes() + SHIM_SRC.read_bytes()).hexdigest()[:12]
        out = Path(tempfile.gettempdir()) / f"bg_ps_shim_{h}.so"
    else:
        out = Path(out)
    if out.exists() and out.stat().st_mtime >= max(cenc_c.stat().st_mtime, SHIM_SRC.stat().st_mtime):
        return out
    with tempfile.TemporaryDirectory(prefix="bg_ps_") as tmp:
        tmp = Path(tmp)
        (tmp / "kiwiw").mkdir()
        (tmp / "kiwiw" / "_cenc.c").write_bytes(cenc_c.read_bytes())
        # Headers / sibling sources pinned with cenc_c when present (else in-tree).
        _src_dir = cenc_c.parent if any(cenc_c.parent.glob("*.h")) else _PARSER / "kiwiw"
        for hdr in list(_src_dir.glob("*.h")) + [s for s in _src_dir.glob("_*.c") if s.name != "_cenc.c"]:
            (tmp / "kiwiw" / hdr.name).write_bytes(hdr.read_bytes())
        cenc_path = tmp / "kiwiw" / "_cenc.c"
        src = tmp / "bg_ps.c"
        src.write_text(SHIM_SRC.read_text().replace("CENC_PATH", str(cenc_path)))
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [_find_cc(), *_cflags(), "-shared", str(src), "-lm", "-o", str(out)],
            check=True, cwd=str(_PARSER),
        )
    return out


def load_shim(so: Path | str):
    lib = ctypes.CDLL(str(so))
    lib.bg_ps_clip.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64,
        ctypes.c_int64, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_double,
        ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
    ]
    lib.bg_ps_clip.restype = ctypes.c_int64
    lib.bg_ps_ring_stats.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
    ]
    lib.bg_ps_ring_stats.restype = ctypes.c_int64
    lib.bg_ps_ring_stats2.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_double, ctypes.c_double,
        ctypes.c_void_p,
    ]
    lib.bg_ps_ring_stats2.restype = ctypes.c_int64
    return lib


def ring_stats(shim, latlon: list[tuple[float, float]], scale=None) -> dict:
    """Return closure / longest-edge / crossing stats for a lat/lon ring.

    scale=(sx, sy) = (cr/dlon, cr/dlat): edge lengths in raw lattice units (plan 46 RC6,
    the historical kw_bounds arithmetic). None = degrees (diagnostic only).
    """
    if len(latlon) < 4:
        return {"closed": 0, "closing": -1, "longest": -1, "closing_is_longest": 0, "crossings": 0}
    lat = np.ascontiguousarray([p[0] for p in latlon], dtype=np.float64)
    lon = np.ascontiguousarray([p[1] for p in latlon], dtype=np.float64)
    out = np.zeros(5, dtype=np.int64)
    if scale is None:
        rc = int(shim.bg_ps_ring_stats(lat.ctypes.data, lon.ctypes.data, len(latlon), out.ctypes.data))
    else:
        rc = int(shim.bg_ps_ring_stats2(lat.ctypes.data, lon.ctypes.data, len(latlon),
                                        ctypes.c_double(float(scale[0])), ctypes.c_double(float(scale[1])),
                                        out.ctypes.data))
    if rc < 0:
        return {"closed": 0, "closing": -1, "longest": -1, "closing_is_longest": 0, "crossings": 0}
    return {
        "closed": int(out[0]),
        "closing": int(out[1]),
        "longest": int(out[2]),
        "closing_is_longest": int(out[3]),
        "crossings": int(out[4]),
    }


def residual_crossing_bit(producer_class: str, stats: dict) -> int:
    """Historical residual_crossing_verified==1 requires unique-byte producer + ring predicates.

    Fragment-only rows get bit 0 (DESIGN: historical bits remain byte-exact predicates).
    """
    if producer_class != "unique-byte":
        return 0
    if not stats.get("closed"):
        return 0
    if not stats.get("closing_is_longest"):
        return 0
    if int(stats.get("crossings", 0)) < 1:
        return 0
    return 1


def s02_producer_bit(producer_class: str, stats: dict, *, level: int, code: int) -> int:
    """s02_producer_verified: L0 type-291 boundary with residual-crossing predicates + unique-byte."""
    if level != 0 or code != 291:
        return 0
    return residual_crossing_bit(producer_class, stats)


def load_dump_kind(dump_dir: Path, kind: str):
    man = json.loads((dump_dir / "dump_manifest.json").read_text())
    bg = man["kinds"][kind]
    T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
    offset = 0
    names, formats, offsets = [], [], []
    for f in bg["fields"]:
        fmt = T[f["type"]]
        align = np.dtype(fmt).alignment
        if offset % align:
            offset += align - (offset % align)
        names.append(f["name"]); formats.append(fmt); offsets.append(offset)
        offset += np.dtype(fmt).itemsize
    dt = np.dtype({"names": names, "formats": formats, "offsets": offsets, "itemsize": bg["row_size"]})
    path = dump_dir / bg["file"]
    return np.memmap(path, dtype=dt, mode="r"), bg["rows"], man


def scan_leaf_rows(
    rows: np.ndarray,
    indices: np.ndarray,
    *,
    probe,
    shim,
    spool_cands: list,
    rect=(0.0, 0.0, 4096.0, 4096.0),
    cr: float = 4096.0,
    disc_by_shape: dict | None = None,
    scale=None,
) -> list[dict]:
    """Scan dump rows that share a leaf; `spool_cands` is list of (cid, ring_xy_raw, latlon).

    disc_by_shape: optional {shape: (code, wire_bytes, verts)} from leaf_records.
    """
    b4_enc = (0.0, float(cr), 0.0, float(cr))
    by_shape: dict[int, list[int]] = defaultdict(list)
    for i in indices:
        by_shape[int(rows["shape"][i])].append(int(i))

    out = []
    # RC5: a record's type is its source's type (E2 merge copies the source columns), so only
    # same-type rings can produce it; clip_ring forces tc=code, which would otherwise make a
    # same-geometry ring of another type a spurious byte hit.
    cands_by_tc: dict = defaultdict(list)
    for cid, ring, _ll in spool_cands:
        cands_by_tc[int(cid[3])].append((cid, ring))
    cands_ll = {cid: ll for cid, _ring, ll in spool_cands}
    clip_cache: dict = {}  # leaf-scoped (rect/b4/cr fixed)

    for shape, idxs in by_shape.items():
        i0 = idxs[0]
        code = int(rows["code"][i0])
        level = int(rows["level"][i0])
        wire = b""
        verts = [(int(rows["vx"][i]), int(rows["vy"][i])) for i in idxs]
        failing: set = set()
        if disc_by_shape and shape in disc_by_shape:
            d_code, wire, d_verts = disc_by_shape[shape]
            if d_code == code:
                verts = [(int(x), int(y)) for x, y in d_verts]
                # dump verts that fall on the disc ring are the failing set for IB
                dump_verts = {(int(rows["vx"][i]), int(rows["vy"][i])) for i in idxs}
                failing = dump_verts & set(verts)
        cands_xy = cands_by_tc.get(code, [])
        status, pid = find_producer(
            probe, wire, cands_xy, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
            record_verts=verts, failing=failing, clip_cache=clip_cache, piecewise=True,
        )
        if status == "producer_none" and not wire:
            # dump-only fallback (no disc): IB over dump verts
            status, pid = find_producer(
                probe, b"", cands_xy, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                record_verts=verts, failing=set(verts), clip_cache=clip_cache,
            )
        stats = {"closed": 0, "closing_is_longest": 0, "crossings": 0}
        prod_hx = prod_hy = prod_ri = -1
        if pid is not None and pid in cands_ll:
            stats = ring_stats(shim, cands_ll[pid], scale=scale)
            prod_hx, prod_hy, prod_ri = int(pid[0]), int(pid[1]), int(pid[2])
        gate_b = status
        if status == "producer_none":
            gate_b = "producer_home_outside_R_cap"
        elif status == "producer-ambiguous":
            gate_b = "producer_ambiguous"
        rbit = residual_crossing_bit(status, stats)
        s02 = s02_producer_bit(status, stats, level=level, code=code)
        for i in idxs:
            out.append({
                "row_index": int(i),
                "level": level,
                "ix": int(rows["ix"][i]),
                "iy": int(rows["iy"][i]),
                "depth": int(rows["depth"][i]),
                "p0": int(rows["p0"][i]), "p1": int(rows["p1"][i]),
                "p2": int(rows["p2"][i]), "p3": int(rows["p3"][i]),
                "p4": int(rows["p4"][i]), "p5": int(rows["p5"][i]),
                "p6": int(rows["p6"][i]),
                "shape": shape,
                "vert": int(rows["vert"][i]),
                "code": code,
                "vx": int(rows["vx"][i]),
                "vy": int(rows["vy"][i]),
                "producer_class": gate_b,
                "producer_raw": status,
                "producer_hx": prod_hx,
                "producer_hy": prod_hy,
                "producer_ri": prod_ri,
                "residual_crossing_verified": rbit,
                "s02_producer_verified": s02,
                "mechanism": (
                    "unique-byte-crossing" if rbit else
                    ("fragment" if status == "unique-fragment" else gate_b)
                ),
            })
    return out


from collections import OrderedDict

# Bounded LRU of per-cell numpy rings (plan 57-59 pattern: cell-keyed, capped).
# Plan 46 memory root cause: an unbounded-in-practice 60k-cell cache of decoded
# cells + duplicated Python coord lists grew RSS linearly (killed at 7.4 GiB/shard).
_RING_NP: "OrderedDict" = OrderedDict()
_RING_NP_MAX = 4096


def set_ring_cache_max(n: int) -> None:
    global _RING_NP_MAX
    _RING_NP_MAX = max(1, int(n))
    while len(_RING_NP) > _RING_NP_MAX:
        _RING_NP.popitem(last=False)


def direct_spool_cell(spool, level, ix, iy):
    """One cell's content, identical to leaf_io._spool_cell / SpoolReader.iter_cells(i, i+1).

    iter_cell_columns converts the whole level index to Python lists on every call
    (~20 ms at L0); this reads the single record directly via the same index entry,
    the same _read_cell, decode_columns and columns_to_content.
    """
    from kiwiw.spool import decode_columns, columns_to_content
    idx = spool._load_idx(level)
    if idx is None:
        return None
    key = (level, str(spool.spool_dir))
    yx = _YX.get(key)
    if yx is None:
        yx = (np.asarray(idx.iy, dtype=np.int64) << 32) | (np.asarray(idx.ix, dtype=np.int64) & 0xFFFFFFFF)
        if len(yx) > 1 and not bool(np.all(np.diff(yx) > 0)):
            raise RuntimeError("spool index not strictly ascending (iy, ix)")
        _YX[key] = yx
    want = (int(iy) << 32) | (int(ix) & 0xFFFFFFFF)
    i = int(np.searchsorted(yx, want, "left"))
    if i >= len(yx) or int(yx[i]) != want:
        return None
    return columns_to_content(decode_columns(
        spool._read_cell(level, int(idx.offset[i]), int(idx.length[i]))))


_YX: dict = {}


def _cell_rings(spool, level, hx, hy, _spool_cell):
    """Per-cell numpy rings: [(ri, tc, lat, lon, latmin, latmax, lonmin, lonmax)] (LRU)."""
    key = (level, hx, hy)
    got = _RING_NP.get(key)
    if got is not None:
        _RING_NP.move_to_end(key)
        return got
    content = (direct_spool_cell(spool, level, hx, hy) if _spool_cell is None
               else _spool_cell(spool, level, hx, hy))
    out = []
    if content:
        for ri, bg in enumerate(content.get("backgrounds") or []):
            coords = getattr(bg, "coords", None) or []
            if len(coords) < 3:
                continue
            a = np.asarray(coords, dtype=np.float64)
            lat, lon = a[:, 0].copy(), a[:, 1].copy()
            tc = int(getattr(bg, "type_code", 0) or 0)
            out.append((ri, tc, lat, lon, lat.min(), lat.max(), lon.min(), lon.max()))
    del content
    _RING_NP[key] = out
    if len(_RING_NP) > _RING_NP_MAX:
        _RING_NP.popitem(last=False)
    return out


def fast_spool_candidates(spool, level, ix, iy, rect, b4, cr, neighbourhood, _spool_cell,
                          extra_homes=()):
    """Bit-identical, faster equivalent of leaf_io.spool_candidates + _enrich_cands.

    Same iteration order (dx outer, dy inner, ring ordinal), same projection
    arithmetic ((v - lo) / (hi - lo) * cr, per element, IEEE double), same closure
    append and bbox test (rect ± 1). The bbox prefilter uses lat/lon extrema: the
    projection is a composition of correctly-rounded monotone operations with
    positive scale, so projected extrema equal projected lat/lon extrema.
    Yields (cid, ring_xy, raw_coords).
    extra_homes (plan 46): home cells beyond Moore(R) whose tall shapes' bbox meets this
    cell (FarHomes); scanned after Moore(R) with the identical per-ring test.
    """
    lat_lo, lat_hi, lon_lo, lon_hi = b4
    dlat = lat_hi - lat_lo
    dlon = lon_hi - lon_lo
    x0, y0, x1, y1 = rect[0] - 1, rect[1] - 1, rect[2] + 1, rect[3] + 1
    out = []
    homes = [(ix + dx, iy + dy) for dx in range(-neighbourhood, neighbourhood + 1)
             for dy in range(-neighbourhood, neighbourhood + 1)]
    homes += [h for h in extra_homes
              if abs(h[0] - ix) > neighbourhood or abs(h[1] - iy) > neighbourhood]
    for hx, hy in homes:
        if True:
            for ri, tc, lat, lon, la0, la1, lo0, lo1 in _cell_rings(
                    spool, level, hx, hy, _spool_cell):
                xmin = (lo0 - lon_lo) / dlon * cr
                xmax = (lo1 - lon_lo) / dlon * cr
                ymin = (la0 - lat_lo) / dlat * cr
                ymax = (la1 - lat_lo) / dlat * cr
                if xmax < x0 or xmin > x1 or ymax < y0 or ymin > y1:
                    continue
                xs = ((lon - lon_lo) / dlon * cr).tolist()
                ys = ((lat - lat_lo) / dlat * cr).tolist()
                ring = list(zip(xs, ys))
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                coords = list(zip(lat.tolist(), lon.tolist()))  # raw spool (lat, lon), unclosed
                out.append(((hx, hy, ri, tc), ring, coords))
    return out


def leaf_clip_geometry(level, ix, iy, path, ptype, cell_b4):
    """(b4, cr, rect) exactly as E2 clips a leaf (plan 46 root cause 3).

    Undivided leaf: the cell's frame, rect = [0, cr]^2. Divided leaf (record parcel_type
    1/2, i.e. 2x2/4x4; leaf sub index c = sy*nx + sx as in tree_leaves): E2's
    dv_tier_setup clips against the PARENT bounds with rect = (sx*cr/nx, sy*cr/nx,
    (sx+1)*cr/nx, (sy+1)*cr/nx) in integer arithmetic and cr = the sub-parcel range,
    which is the parent slot's frame range (coordconv.range_for / mesh.g_frame_range).
    """
    from kiwiw import mesh
    b4, cr = cell_b4(level, ix, iy)
    if ptype in (1, 2) and len(path) >= 2:
        nx = 2 if ptype == 1 else 4
        c = int(path[-1])
        if not 0 <= c < nx * nx:
            raise ValueError(f"sub index {c} outside pardiv{ptype}")
        crs = int(mesh.g_frame_range(level, ptype, c))
        sx, sy = c % nx, c // nx
        rect = (float(sx * crs // nx), float(sy * crs // nx),
                float((sx + 1) * crs // nx), float((sy + 1) * crs // nx))
        return b4, float(crs), rect
    if ptype not in (0, None):
        raise ValueError(f"unsupported parcel_type {ptype} for leaf {(level, ix, iy, path)}")
    return b4, float(cr), (0.0, 0.0, float(cr), float(cr))


class FarHomes:
    """Home cells of tall shapes (bbox leaves home +-1 cell; the K1 tall set, `cenc.k1_tall`)
    indexed by the cells their bbox meets (+-1 cell margin). Moore(R) U FarHomes.query is a
    superset of every ring whose bbox meets the leaf: a non-tall ring lies within home +-1.
    Plan 46 root cause 2: Moore(R=8) alone missed producers homed farther away (3-12 used
    E1 routing with all original sources). Built in bounded index chunks; coordinates are
    discarded, only (home, cell bbox) is kept."""

    TILE = 16

    def __init__(self, spool_dir, level: int, chunk: int = 4096):
        from kiwiw import cenc
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from quantisation_roundtrip import Lattice, RAW
        lat = Lattice(level)
        lat5 = np.array([lat.lat0, lat.lon0, lat.cell_lat, lat.cell_lon, lat._wlo], np.float64)
        sp = cenc.E1Spool(str(spool_dir), level)
        n = len(sp.xs)
        H, C = [], []
        for a in range(0, n, chunk):
            rows, xy = cenc.k1_tall(sp, lat5, a, min(n, a + chunk))
            if not len(rows):
                continue
            off = np.zeros(len(rows) + 1, np.int64)
            np.cumsum(rows["n"], out=off[1:])
            st = off[:-1]
            bx0 = np.minimum.reduceat(xy[:, 0], st); bx1 = np.maximum.reduceat(xy[:, 0], st)
            by0 = np.minimum.reduceat(xy[:, 1], st); by1 = np.maximum.reduceat(xy[:, 1], st)
            H.append(np.stack([rows["hx"], rows["hy"]], 1).astype(np.int64))
            C.append(np.stack([np.floor(bx0 / RAW) - 1, np.floor(bx1 / RAW) + 1,
                               np.floor(by0 / RAW) - 1, np.floor(by1 / RAW) + 1], 1).astype(np.int64))
            del rows, xy
        self.home = np.concatenate(H) if H else np.zeros((0, 2), np.int64)
        self.cell = np.concatenate(C) if C else np.zeros((0, 4), np.int64)
        T = self.TILE
        buckets: dict = defaultdict(list)
        for k, (cx0, cx1, cy0, cy1) in enumerate(self.cell.tolist()):
            for tx in range(cx0 // T, cx1 // T + 1):
                for ty in range(cy0 // T, cy1 // T + 1):
                    buckets[(tx, ty)].append(k)
        self.buckets = {k: np.asarray(v, np.int64) for k, v in buckets.items()}
        self.n_tall = len(self.home)

    def query(self, ix: int, iy: int) -> list:
        b = self.buckets.get((ix // self.TILE, iy // self.TILE))
        if b is None:
            return []
        c = self.cell[b]
        m = (c[:, 0] <= ix) & (ix <= c[:, 1]) & (c[:, 2] <= iy) & (iy <= c[:, 3])
        return sorted({(int(x), int(y)) for x, y in self.home[b[m]].tolist()})


def leaf_order(rows, nrows: int, tile: int = 32, chunk: int = 1 << 22):
    """Vectorised leaf grouping in tiled spatial order (no per-row Python objects).

    Returns (order[int64], starts[int64]) with leaves = order[starts[k]:starts[k+1]].
    Sort key: level, iy//tile, ix//tile, iy, ix, depth, p0..p6 (p_j zeroed for j >= depth),
    so a shard's Moore(R) working set is ~(tile+2R)^2 cells and fits the LRU.
    """
    cols = {}
    for name, dt in (("level", np.int64), ("ix", np.int64), ("iy", np.int64), ("depth", np.int64)):
        a = np.empty(nrows, dt)
        for lo in range(0, nrows, chunk):
            a[lo:lo + chunk] = rows[name][lo:lo + chunk]
        cols[name] = a
    ps_ = []
    for j in range(7):
        a = np.empty(nrows, np.int64)
        for lo in range(0, nrows, chunk):
            v = rows[f"p{j}"][lo:lo + chunk].astype(np.int64)
            v[cols["depth"][lo:lo + chunk] <= j] = 0
            a[lo:lo + chunk] = v
        ps_.append(a)
    keys = [*reversed(ps_), cols["depth"], cols["ix"], cols["iy"],
            cols["ix"] // tile, cols["iy"] // tile, cols["level"]]
    order = np.lexsort(keys)
    del keys
    allk = [cols["level"], cols["ix"], cols["iy"], cols["depth"], *ps_]
    change = np.zeros(nrows, bool)
    change[0] = True
    for a in allk:
        s = a[order]
        change[1:] |= s[1:] != s[:-1]
        del s
    starts = np.append(np.nonzero(change)[0], nrows).astype(np.int64)
    return order.astype(np.int64), starts


def _rss_mib() -> float:
    """Anonymous RSS (heap) in MiB. File-backed memmap pages (dump/order/disc) are
    reclaimable page cache and excluded; the plan-46 OOM was anonymous growth."""
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("RssAnon:"):
                return int(line.split()[1]) / 1024
    return 0.0


def _enrich_cands(spool, level, raw_cands, _spool_cell):
    """Attach lat/lon rings once per candidate (cell cache hits)."""
    enriched = []
    for cid, ring in raw_cands:
        hx, hy, ri, _tc = cid
        content = _spool_cell(spool, level, hx, hy)
        bg = (content.get("backgrounds") or [])[ri]
        # Raw spool coords, NOT closed here: residual_crossing_verified requires
        # *explicit* closure in the source ring (documented semantics).
        coords = [tuple(c) for c in (getattr(bg, "coords", None) or [])]
        enriched.append((cid, ring, coords))
    return enriched


def build_side_table(results: list[dict], path: Path) -> dict:
    """Group-level side_<kind>.npy: status=1 iff any row in group has residual/s02 bit.

    For residual mode dump_join uses status==1. We set status from residual_crossing_verified.
    Separate S02 side uses s02_producer_verified.
    """
    # residual side: one row per GROUP with status + rows count
    groups: dict[tuple, dict] = {}
    for d in results:
        key = tuple(d[k] for k in GROUP)
        g = groups.get(key)
        if g is None:
            g = {"status": 0, "rows": 0, "s02": 0, "rbit": 0,
                 "producer_class": d["producer_class"],
                 "producer_hx": d["producer_hx"], "producer_hy": d["producer_hy"],
                 "producer_ri": d["producer_ri"]}
            groups[key] = g
        g["rows"] += 1
        if d["residual_crossing_verified"]:
            g["status"] = 1
            g["rbit"] = 1
        if d["s02_producer_verified"]:
            g["s02"] = 1
    dt = np.dtype([
        ("level", "<u1"), ("ix", "<i4"), ("iy", "<i4"), ("code", "<i4"),
        ("p0", "<u2"), ("p1", "<u2"), ("p2", "<u2"), ("p3", "<u2"),
        ("p4", "<u2"), ("p5", "<u2"), ("p6", "<u2"), ("shape", "<i4"),
        ("status", "<i1"), ("rows", "<i4"),
        ("s02", "<u1"), ("rbit", "<u1"),
        ("producer_hx", "<i4"), ("producer_hy", "<i4"), ("producer_ri", "<i4"),
    ])
    arr = np.zeros(len(groups), dtype=dt)
    for i, (key, g) in enumerate(groups.items()):
        for j, name in enumerate(GROUP):
            arr[i][name] = key[j]
        arr[i]["status"] = g["status"]
        arr[i]["rows"] = g["rows"]
        arr[i]["s02"] = g["s02"]
        arr[i]["rbit"] = g["rbit"]
        arr[i]["producer_hx"] = g["producer_hx"]
        arr[i]["producer_hy"] = g["producer_hy"]
        arr[i]["producer_ri"] = g["producer_ri"]
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, arr)
    return {
        "n_groups": len(groups),
        "n_status1": int((arr["status"] == 1).sum()),
        "n_s02_groups": int((arr["s02"] == 1).sum()),
        "rows_status1": int(arr["rows"][arr["status"] == 1].sum()) if len(arr) else 0,
        "rows_s02": int(arr["rows"][arr["s02"] == 1].sum()) if len(arr) else 0,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--kind", choices=("background", "background_boundary"), required=True)
    ap.add_argument("--cenc", type=Path, default=None, help="pinned _cenc.c for shim+probe")
    ap.add_argument("--disc", type=Path, default=None,
                    help="ALLDATA.KWI for unique-byte (leaf_records); required for historical bits")
    ap.add_argument("--r", type=int, default=DEFAULT_R)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--side-out", type=Path, default=None,
                    help="optional side_<kind>.npy path (group status from residual bit)")
    ap.add_argument("--s02-side-out", type=Path, default=None,
                    help="optional S02 side table (status from s02 bit)")
    ap.add_argument("--limit-leaves", type=int, default=0, help="smoke: max leaves")
    ap.add_argument("--cache-max-cells", type=int, default=4096,
                    help="LRU cap for per-cell ring cache (and leaf_io cache on --slow-cands)")
    ap.add_argument("--tile", type=int, default=32, help="spatial tile for leaf order")
    ap.add_argument("--order-cache", type=Path, default=None,
                    help="dir with order.npy/starts.npy shared across shards (built if absent)")
    ap.add_argument("--build-order-only", action="store_true")
    ap.add_argument("--max-rss-mib", type=int, default=3072,
                    help="abort (exit 3) if RSS exceeds this; 0 disables")
    ap.add_argument("--slow-cands", action="store_true",
                    help="use leaf_io.spool_candidates (reference path) instead of the fast path")
    ap.add_argument("--shard", type=str, default="0/1",
                    help="k/n: process the k-th of n contiguous spatial leaf chunks")
    ap.add_argument("--spool", type=Path, default=Path("output/extract_timing/spool"))
    ap.add_argument("--no-far-homes", action="store_true",
                    help="Moore(R) only (pre-fix behaviour; diagnostics)")
    ap.add_argument("--only-leaves", type=Path, default=None,
                    help="JSON list of [level, ix, iy, [path...]]: scan only these leaves (probe)")
    args = ap.parse_args(argv)

    from kiwiw.spool import SpoolReader
    root = _PARSER.parent
    sys.path[:0] = [
        str(root / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
    ]
    from leaf_io import (  # noqa: E402
        spool_candidates, cell_b4, leaf_rect_raw, frames, leaf_records, _spool_cell,
        set_spool_cell_cache_max,
    )
    set_spool_cell_cache_max(args.cache_max_cells)  # reference path only
    set_ring_cache_max(args.cache_max_cells)

    rows, nrows, man = load_dump_kind(args.dump, args.kind)
    print(f"loaded {args.kind} rows={nrows}", flush=True)
    so_dir = args.out.parent.resolve()
    so_dir.mkdir(parents=True, exist_ok=True)
    so_probe = compile_probe(args.cenc, so_dir / "probe_scan.so")
    so_shim = compile_shim(args.cenc, so_dir / "shim_scan.so")
    probe = load_probe(so_probe)
    shim = load_shim(so_shim)
    spool = SpoolReader(args.spool)

    # Leaf grouping: order cache shared by shards (built once, memory-mapped).
    oc = args.order_cache
    if oc is not None and (oc / "order.npy").exists():
        order = np.load(oc / "order.npy", mmap_mode="r")
        starts = np.load(oc / "starts.npy")
    else:
        order, starts = leaf_order(rows, nrows, tile=args.tile)
        if oc is not None:
            oc.mkdir(parents=True, exist_ok=True)
            np.save(oc / "order.npy.tmp.npy", order); np.save(oc / "starts.npy.tmp.npy", starts)
            os.replace(oc / "order.npy.tmp.npy", oc / "order.npy")
            os.replace(oc / "starts.npy.tmp.npy", oc / "starts.npy")
    nleaves = len(starts) - 1
    print(f"leaves={nleaves} rss={_rss_mib():.0f}MiB", flush=True)
    if args.build_order_only:
        return 0
    sk, sn = (int(x) for x in args.shard.split("/"))
    llo, lhi = nleaves * sk // sn, nleaves * (sk + 1) // sn
    if args.limit_leaves:
        lhi = min(lhi, llo + args.limit_leaves)
    print(f"shard {sk}/{sn}: leaves {llo}..{lhi}", flush=True)

    only = None
    if args.only_leaves:
        only = {(int(l), int(x), int(y), tuple(int(v) for v in p))
                for l, x, y, p in json.loads(args.only_leaves.read_text())}

    def leaf_key(k):
        i0 = int(order[starts[k]])
        d = int(rows["depth"][i0])
        return (int(rows["level"][i0]), int(rows["ix"][i0]), int(rows["iy"][i0]),
                tuple(int(rows[f"p{j}"][i0]) for j in range(d)))

    def leaf_iter():
        for k in range(llo, lhi):
            lk = leaf_key(k)
            if only is not None and lk not in only:
                continue
            idxs = np.sort(np.asarray(order[starts[k]:starts[k + 1]], dtype=np.int64))
            yield lk, idxs

    cellset = set()
    for k in range(llo, lhi):
        lk = leaf_key(k)
        if only is None or lk in only:
            cellset.add(lk[:3])

    disc_fr = {}
    disc_pt: dict = {}
    disc_fh = None
    if args.disc:
        print(f"indexing frames from {args.disc} cells={len(cellset)} ...", flush=True)
        disc_fr = frames(str(args.disc), cellset, ptype_out=disc_pt)
        print(f"frames={len(disc_fr)} divided={sum(1 for v in disc_pt.values() if v)}", flush=True)
        disc_fh = open(args.disc, "rb")
    far: dict = {}
    n_far_leaves = 0
    n_divided_leaves = 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "row_index", "level", "ix", "iy", "depth",
        "p0", "p1", "p2", "p3", "p4", "p5", "p6",
        "shape", "vert", "code", "vx", "vy",
        "producer_class", "producer_raw",
        "producer_hx", "producer_hy", "producer_ri",
        "residual_crossing_verified", "s02_producer_verified", "mechanism",
    ]
    class_counts = Counter()
    group_agg: dict[tuple, dict] = {}  # per group (bounded by groups in shard)
    peak_rss = 0.0
    n_done = 0
    n_rows = 0
    rbit_rows = s02_rows = 0
    residual_prods: set[tuple] = set()
    try:
        with gzip.open(args.out, "wt", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
            w.writeheader()
            for lk, idxs in leaf_iter():
                level, ix, iy, path = lk
                ptype = disc_pt.get(lk, 0)
                b4, cr, rect = leaf_clip_geometry(level, ix, iy, path, ptype, cell_b4)
                n_divided_leaves += bool(ptype)
                if args.slow_cands:
                    raw_cands = list(spool_candidates(
                        spool, level, ix, iy, rect, b4, cr, neighbourhood=args.r))
                    enriched = _enrich_cands(spool, level, raw_cands, _spool_cell)
                else:
                    extra = ()
                    if not args.no_far_homes:
                        if level not in far:
                            far[level] = FarHomes(args.spool, level)
                            print(f"far-homes L{level}: tall={far[level].n_tall} "
                                  f"rss={_rss_mib():.0f}MiB", flush=True)
                        extra = far[level].query(ix, iy)
                        n_far_leaves += any(abs(h[0] - ix) > args.r or abs(h[1] - iy) > args.r
                                            for h in extra)
                    enriched = fast_spool_candidates(
                        spool, level, ix, iy, rect, b4, cr, args.r, None, extra_homes=extra)

                disc_by_shape = None
                if disc_fh is not None:
                    ent = disc_fr.get(lk)
                    if ent is not None:
                        disc_by_shape = {
                            s: (code, wire, verts)
                            for s, code, wire, verts in leaf_records(disc_fh, ent)
                        }

                leaf_out = scan_leaf_rows(
                    rows, np.asarray(idxs, dtype=np.int64),
                    probe=probe, shim=shim, spool_cands=enriched, rect=rect, cr=float(cr),
                    disc_by_shape=disc_by_shape,
                    scale=(float(cr) / (b4[3] - b4[2]), float(cr) / (b4[1] - b4[0])),
                )
                for d in leaf_out:
                    class_counts[d["producer_class"]] += 1
                    key = tuple(d[k] for k in GROUP)
                    g = group_agg.get(key)
                    if g is None:
                        g = {"status": 0, "rows": 0, "s02": 0, "rbit": 0,
                             "producer_raw": d["producer_raw"],
                             "producer_hx": d["producer_hx"], "producer_hy": d["producer_hy"],
                             "producer_ri": d["producer_ri"]}
                        group_agg[key] = g
                    g["rows"] += 1
                    if d["residual_crossing_verified"]:
                        g["status"] = 1
                        g["rbit"] = 1
                        rbit_rows += 1
                        if d["producer_hx"] >= 0:
                            residual_prods.add((d["level"], d["producer_hx"], d["producer_hy"], d["producer_ri"]))
                    if d["s02_producer_verified"]:
                        g["s02"] = 1
                        s02_rows += 1
                    w.writerow({k: d[k] for k in fields})
                    n_rows += 1
                n_done += 1
                if n_done % 50 == 0:
                    rss = _rss_mib()
                    peak_rss = max(peak_rss, rss)
                    if args.max_rss_mib and rss > args.max_rss_mib:
                        print(f"RSS_CEILING rss={rss:.0f}MiB > {args.max_rss_mib}MiB at leaf {n_done}; abort",
                              flush=True)
                        raise SystemExit(3)
                if n_done % 500 == 0:
                    print(
                        f"  leaves {n_done}/{lhi - llo} rows {n_rows} rss={_rss_mib():.0f}MiB "
                        f"ringcache={len(_RING_NP)} top={class_counts.most_common(4)} "
                        f"rbit_rows={rbit_rows} s02_rows={s02_rows}",
                        flush=True,
                    )
    finally:
        if disc_fh is not None:
            disc_fh.close()

    side_stats = {}
    if args.side_out or args.s02_side_out:
        dt = np.dtype([
            ("level", "<u1"), ("ix", "<i4"), ("iy", "<i4"), ("code", "<i4"),
            ("p0", "<u2"), ("p1", "<u2"), ("p2", "<u2"), ("p3", "<u2"),
            ("p4", "<u2"), ("p5", "<u2"), ("p6", "<u2"), ("shape", "<i4"),
            ("status", "<i1"), ("rows", "<i4"),
            ("s02", "<u1"), ("rbit", "<u1"),
            ("producer_hx", "<i4"), ("producer_hy", "<i4"), ("producer_ri", "<i4"),
        ])
        arr = np.zeros(len(group_agg), dtype=dt)
        for i, (key, g) in enumerate(group_agg.items()):
            for j, name in enumerate(GROUP):
                arr[i][name] = key[j]
            arr[i]["status"] = g["status"]
            arr[i]["rows"] = g["rows"]
            arr[i]["s02"] = g["s02"]
            arr[i]["rbit"] = g["rbit"]
            arr[i]["producer_hx"] = g["producer_hx"]
            arr[i]["producer_hy"] = g["producer_hy"]
            arr[i]["producer_ri"] = g["producer_ri"]
        if args.side_out:
            args.side_out.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.side_out, arr)
            side_stats["residual"] = {
                "n_groups": len(arr),
                "n_status1": int((arr["status"] == 1).sum()),
                "n_s02_groups": int((arr["s02"] == 1).sum()),
                "rows_status1": int(arr["rows"][arr["status"] == 1].sum()) if len(arr) else 0,
                "rows_s02": int(arr["rows"][arr["s02"] == 1].sum()) if len(arr) else 0,
            }
        if args.s02_side_out:
            s02arr = arr.copy()
            s02arr["status"] = s02arr["s02"].astype(s02arr["status"].dtype)
            args.s02_side_out.parent.mkdir(parents=True, exist_ok=True)
            np.save(args.s02_side_out, s02arr)
            side_stats["s02"] = {
                "n_groups": len(s02arr),
                "n_status1": int((s02arr["status"] == 1).sum()),
                "rows_status1": int(s02arr["rows"][s02arr["status"] == 1].sum()) if len(s02arr) else 0,
            }

    sc = Counter(g["producer_raw"] for g in group_agg.values())
    peak_rss = max(peak_rss, _rss_mib())
    summary = {
        "kind": args.kind,
        "n_rows_scanned": n_rows,
        "n_leaves": n_done,
        "shard": args.shard,
        "cenc": str(args.cenc) if args.cenc else None,
        "R": args.r,
        "far_homes": not args.no_far_homes,
        "far_tall_shapes": {str(k): v.n_tall for k, v in far.items()},
        "leaves_with_far_homes": n_far_leaves,
        "divided_leaves": n_divided_leaves,
        "only_leaves": str(args.only_leaves) if args.only_leaves else None,
        "disc": str(args.disc) if args.disc else None,
        "class_counts_rows": dict(class_counts),
        "class_counts_shapes": dict(sc),
        "residual_crossing_true_rows": rbit_rows,
        "s02_true_rows": s02_rows,
        "residual_crossing_true_shapes": sum(1 for g in group_agg.values() if g["rbit"]),
        "s02_true_shapes": sum(1 for g in group_agg.values() if g["s02"]),
        "peak_rss_mib_sampled": round(peak_rss, 1),
        "leaf_range": [llo, lhi],
        "qualifying_source_rings_residual": len(residual_prods),
        "side_stats": side_stats,
        "out": str(args.out),
    }
    args.out.with_suffix(args.out.suffix + ".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
