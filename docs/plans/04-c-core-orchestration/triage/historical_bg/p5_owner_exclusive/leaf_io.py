"""Leaf record-byte and spool-candidate helpers for plan 44 (shared by control + Phase 2)."""
from __future__ import annotations
import importlib.util
import os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
from kiwiw import volume, mesh
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
from kiwiw.coordconv import decode_region_coord
from kiwiw.spool import SpoolReader

_OC = ROOT / "docs/plans/04-c-core-orchestration/triage/oracle_chain"
_spec_oc = importlib.util.spec_from_file_location("oracle_chain_p44", _OC / "oracle_chain.py")
oc = importlib.util.module_from_spec(_spec_oc)
_spec_oc.loader.exec_module(oc)
_spec_sec = importlib.util.spec_from_file_location("sections_p44", _OC / "hop_3_14" / "sections.py")
sec = importlib.util.module_from_spec(_spec_sec)
_spec_sec.loader.exec_module(sec)

U16 = lambda b, o: int.from_bytes(b[o:o+2], "big")


def frames(path, cellset):
    out = {}
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size: continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * nby + bi // nbx) * ny
                if not any((lm.level, x, y) in cellset for x in range(bx, bx + nx) for y in range(by, by + ny)): continue
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if (lm.level, bx + x, by + y) not in cellset: continue
                    out[(lm.level, bx + x, by + y, tuple(leaf))] = (entry.dsa, entry.size, ss, ls)
    return out


def leaf_records(fh, ent):
    """Yield (shape_index, type_code, wire_bytes, vertices[(x,y),...]) for class>0 background records."""
    dsa, size, ss, ls = ent
    buf = os.pread(fh.fileno(), size * ls, volume.getsector(dsa, ss, ls)); buf = buf[:U16(buf, 0) * 2]
    bg = sec.split(buf)["background"]
    if not bg: return
    hlen = sec.u16(bg, 0) * 2; off = 2; s = 0
    while off < hlen:
        w = sec.u16(bg, off); po = w * 2; off += 4
        if w == 0xFFFF: continue
        n = sec.u16(bg, po); u0 = po + 2; p = u0 + 4 * n
        for i in range(n):
            val = sec.u16(bg, u0 + 4 * i + 2); cnt, cls = val & 0xFFF, val >> 14
            for _ in range(cnt):
                L = (sec.u16(bg, p) & 0xFFF) * 2; code = sec.u16(bg, p + 4)
                wire = bytes(bg[p:p+L])
                verts = []
                if cls:
                    nco = sec.u16(bg, p + 2) & 0x7FF; mult = 1 << (sec.u16(bg, p + 6) & 7)
                    d = np.frombuffer(bg, np.int8, 2 * nco, p + 12).astype(np.int64).reshape(-1, 2) * mult
                    x0 = decode_region_coord(sec.u16(bg, p + 8)); y0 = decode_region_coord(sec.u16(bg, p + 10))
                    xs = np.concatenate(([x0], x0 + np.cumsum(d[:, 0])))
                    ys = np.concatenate(([y0], y0 + np.cumsum(d[:, 1])))
                    verts = list(zip(xs.tolist(), ys.tolist()))
                    yield s, code, wire, verts
                s += 1; p += L


def leaf_rect_raw(level: int, depth: int) -> tuple[float, float, float, float]:
    """Clip rect in undivided-frame raw units for a leaf at `depth` under an undivided parent.

    Undivided leaf (depth 0 path empty / depth 1 with single home): full frame [0,0,cr,cr].
    Divided: E2 uses sx,sy sub-rects — for plan 44 control we start with undivided leaves
    (depth<=1 is the common R01 case) and treat deeper leaves via the path's sub-index
    when parcel_type is known. Default: full frame.
    """
    cr = float(mesh.g_frame_range(level))
    return (0.0, 0.0, cr, cr)


def cell_b4(level: int, ix: int, iy: int):
    g = mesh.CellGrid.from_reference(level)
    b = mesh.frame_bounds(ix, iy, g)
    return (b.lat_lo, b.lat_hi, b.lon_lo, b.lon_hi), float(b.coord_range)


def latlon_to_raw(lat, lon, b4, cr):
    """Mirror Bounds.to_xy: raw x along lon, y along lat, range cr."""
    lat_lo, lat_hi, lon_lo, lon_hi = b4
    y = (lat - lat_lo) / (lat_hi - lat_lo) * cr
    x = (lon - lon_lo) / (lon_hi - lon_lo) * cr
    return x, y


_SPOOL_KEY_CACHE: dict[tuple[int, str], list[tuple[int, int]]] = {}
_SPOOL_CELL_CACHE: dict[tuple[int, str, int, int], dict] = {}

def clear_spool_caches() -> None:
    """Drop spool cell/key caches (mass runs: call every N leaves to bound RSS)."""
    _SPOOL_KEY_CACHE.clear()
    _SPOOL_CELL_CACHE.clear()



def _spool_keys(spool: SpoolReader, level: int) -> list[tuple[int, int]]:
    """Cached sorted (ix, iy) keys for a level (ascending iy, ix)."""
    key = (level, str(spool.spool_dir))
    if key not in _SPOOL_KEY_CACHE:
        _SPOOL_KEY_CACHE[key] = spool.cell_keys(level)
    return _SPOOL_KEY_CACHE[key]


def _spool_cell(spool: SpoolReader, level: int, ix: int, iy: int):
    """Fetch one cell's content via index binary search; cache per (level,ix,iy)."""
    import bisect
    ck = (level, str(spool.spool_dir), ix, iy)
    if ck in _SPOOL_CELL_CACHE:
        return _SPOOL_CELL_CACHE[ck]
    keys = _spool_keys(spool, level)
    # keys are (ix, iy) listed in ascending (iy, ix) — search on (iy, ix)
    pair = (iy, ix)
    # Build parallel list once? cell_keys returns (ix,iy); convert for bisect
    # Linear fallback for tiny neighbourhood is fine if we cache keys as (iy,ix)
    yx_keys = _SPOOL_KEY_CACHE.get(("yx", level, str(spool.spool_dir)))
    if yx_keys is None:
        yx_keys = [(y, x) for x, y in keys]
        _SPOOL_KEY_CACHE[("yx", level, str(spool.spool_dir))] = yx_keys
    i = bisect.bisect_left(yx_keys, pair)
    if i >= len(yx_keys) or yx_keys[i] != pair:
        _SPOOL_CELL_CACHE[ck] = None
        return None
    # iter_cells start=i stop=i+1
    content = None
    for _x, _y, content in spool.iter_cells(level, i, i + 1):
        break
    _SPOOL_CELL_CACHE[ck] = content
    return content


def spool_level_cells(spool: SpoolReader, level: int) -> dict[tuple[int, int], dict]:
    """Legacy whole-level cache (avoid in hot paths; prefer _spool_cell)."""
    key = ("all", level, str(spool.spool_dir))
    if key not in _SPOOL_CELL_CACHE:
        _SPOOL_CELL_CACHE[key] = {(ix, iy): c for ix, iy, c in spool.iter_level(level)}
    return _SPOOL_CELL_CACHE[key]


def spool_candidates(spool: SpoolReader, level: int, ix: int, iy: int, rect, b4, cr,
                     neighbourhood: int = 1):
    """Background shapes in the (2r+1)×(2r+1) neighbourhood of (ix,iy) whose bbox meets `rect`.

    Yields (source_id, ring_xy_raw). source_id = (home_ix, home_iy, record_ordinal, type_code).
    `neighbourhood=1` is the 3×3 Assumption-1 window; widen if verdicts change.
    Rings are projected into THIS cell's b4/cr (same convention as the encoder's to_xy).
    """
    from bg_owner_exclusive import bbox_meets_rect
    for dx in range(-neighbourhood, neighbourhood + 1):
        for dy in range(-neighbourhood, neighbourhood + 1):
            hx, hy = ix + dx, iy + dy
            content = _spool_cell(spool, level, hx, hy)
            if not content:
                continue
            for ri, bg in enumerate(content.get("backgrounds") or []):
                coords = getattr(bg, "coords", None) or []
                if len(coords) < 3:
                    continue
                ring = [latlon_to_raw(lat, lon, b4, cr) for lat, lon in coords]
                if ring and ring[0] != ring[-1]:
                    ring = ring + [ring[0]]
                if not bbox_meets_rect(ring, (rect[0] - 1, rect[1] - 1, rect[2] + 1, rect[3] + 1)):
                    continue
                tc = int(getattr(bg, "type_code", 0) or 0)
                yield (hx, hy, ri, tc), ring
