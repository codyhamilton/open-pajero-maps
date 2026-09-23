"""Coordinate -> parcel locator.

This is a from-scratch rewrite of kiwiread.c's `isin()`/global-state tile
locate approach. It:

- handles longitude wraparound explicitly (this disc's box spans E90 to
  W142, i.e. crosses +/-180 -- kiwiread.c's fix, `(_rx + 360 - _lx)`, is
  reproduced here as `_lon_span()`).
- computes the target grid cell analytically (floor-division of the
  coordinate delta by the level's cell size) instead of brute-force
  scanning every block/blockset, which is both faster and avoids depending
  on iteration order matching kiwiread's global mutable state.
- recurses into "divided/integrated parcel" sub-lists (parcel type pt in
  1..3, spec calls this out as "added in future" and under-specified) by
  re-reading each level's own `type` field rather than assuming a fixed
  recursion depth.

Cross-check performed: for the known-good Melbourne coordinate
(-37.813629, 144.963058), kiwiread.c (patched) reports `bs:22 block:23
parcel:542`, bbox `[-37.833333,144.937500] to [-37.812500,144.968750]`.
This module's `locate_parcel()` reproduces the same (blockset, block,
top-level-parcel) indices and bbox for that coordinate at level 0 -- see
parser/tests/test_mesh.py.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional, Sequence

from .bitutils import extract, sws, u16, u32
from .model import BoundingBox, MeshLocation
from .volume import Pdmdh, getsector

NO_DATA_DSA = 0xFFFFFFFF
MAX_SUBPARCEL_DEPTH = 6

# L0 leaves sit on a 4x4-leaf "integrated parcel" tile grid (same constant
# as tools/coord_scale_census.L0_TILE).
L0_TILE = 4


def _lon_span(lo: float, hi: float) -> float:
    span = hi - lo
    return span + 360.0 if span < 0 else span


def _lon_delta(lo: float, lon: float, span: float) -> float:
    delta = lon - lo
    while delta < 0:
        delta += 360.0
    while delta > span:
        delta -= 360.0
    return delta


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


@dataclass
class _Bmt:
    dsa: int
    size: int


def _read_bmt_array(buf: bytes, byte_off: int, count: int) -> list[_Bmt]:
    out = []
    for i in range(count):
        off = byte_off + i * 6
        out.append(_Bmt(dsa=u32(buf, off), size=u16(buf, off + 4)))
    return out


# ---------------------------------------------------------------------
# A leaf's coordinate FRAME (bbox + `coordconv.range_for` range). The one
# implementation of the frame-shape rule: `harness.walk` (whole-disc walk),
# `alldata_writer.load_region` and `locate_frame` (point lookup) all call it.
# ---------------------------------------------------------------------

def narrow_bounds(bounds: BoundingBox, gn_lat: int, gn_lng: int, idx: int) -> BoundingBox:
    """`bounds` narrowed to flat index `idx` (row-major, lat outer) of a
    `gn_lat` x `gn_lng` grid."""
    lpy, lpx = divmod(idx, gn_lng)
    lon_step = (bounds.lon_hi - bounds.lon_lo) / gn_lng
    lat_step = (bounds.lat_hi - bounds.lat_lo) / gn_lat
    lon_lo = bounds.lon_lo + lpx * lon_step
    lat_lo = bounds.lat_lo + lpy * lat_step
    return BoundingBox(lat_lo=lat_lo, lat_hi=lat_lo + lat_step,
                        lon_lo=lon_lo, lon_hi=lon_lo + lon_step)


def tile_bounds(bounds: BoundingBox, gn_lat: int, gn_lng: int, idx: int) -> BoundingBox:
    """Bbox of the L0_TILE x L0_TILE aligned leaf tile containing slot `idx`
    of a `gn_lat` x `gn_lng` leaf grid spanning `bounds`."""
    ly, lx = divmod(idx, gn_lng)
    ty, tx = ly // L0_TILE * L0_TILE, lx // L0_TILE * L0_TILE
    lon_step = (bounds.lon_hi - bounds.lon_lo) / gn_lng
    lat_step = (bounds.lat_hi - bounds.lat_lo) / gn_lat
    lat_lo = bounds.lat_lo + ty * lat_step
    lon_lo = bounds.lon_lo + tx * lon_step
    return BoundingBox(lat_lo=lat_lo, lat_hi=lat_lo + L0_TILE * lat_step,
                        lon_lo=lon_lo, lon_hi=lon_lo + L0_TILE * lon_step)


def is_sparse_tile(entries: Sequence, gn_lng: int, idx: int) -> bool:
    """True iff the aligned 4x4 tile holding top-level slot `idx` of an L0
    normal record is an L0 *sparse* tile: all 16 slots are populated leaves
    aliasing ONE Map Frame byte range. `entries` are the record's mapinfo
    slots (anything with `.dsa`/`.size`; a subrecord slot has size 0). On R
    this partitions L0 exactly: 231,300 tiles resolve to 1 distinct
    (dsa, size), the other 252 to 16 (the urban tiles of the 2-01 rule)."""
    ly, lx = divmod(idx, gn_lng)
    ty, tx = ly // L0_TILE * L0_TILE, lx // L0_TILE * L0_TILE
    seen = set()
    for dy in range(L0_TILE):
        for dx in range(L0_TILE):
            j = (ty + dy) * gn_lng + tx + dx
            if j >= len(entries):
                return False
            e = entries[j]
            if e.dsa == NO_DATA_DSA or not e.size:
                return False
            seen.add((e.dsa, e.size))
    return len(seen) == 1


def leaf_frame_range(level: int, ptype: int, leaf_path: tuple, frame_class: str) -> Optional[int]:
    """`coordconv.range_for` of one leaf, by coord_scale.json's
    content-independent `class_rule`: division != 0 -> 'divided' (state
    pardiv<type>_sub<idx>); level 0 -> 'sparse' when the frame is the 4x4
    tile (`is_sparse_tile`), else 'urban'; any other level -> 'full'.
    None when `range_for` has no such frame (a genuinely unranged class)."""
    from .coordconv import range_for
    if ptype:
        cls = "divided"
    elif frame_class == "l0_sparse_tile":
        cls = "sparse"
    else:
        cls = "urban" if level == 0 else "full"
    div_state = "normal" if ptype == 0 else f"pardiv{ptype}_sub{leaf_path[-1]}"
    try:
        return range_for(level, cls, div_state)
    except KeyError:
        return None


def leaf_frame_shape(level: int, ptype: int, leaf_path: tuple, leaf_bounds: BoundingBox,
                     block_bounds: BoundingBox, lmr,
                     sparse: Callable[[int], bool]) -> tuple[BoundingBox, str]:
    """(frame_bounds, frame_class) of one leaf. The 16 slots of an L0 sparse
    tile alias ONE Map Frame whose coordinates span the tile (range 16384);
    a divided sub-parcel's coordinates are absolute in its PARENT slot's
    4096 frame (spec 7.2.2.1.1.2); every other leaf is its own frame.
    `sparse(top_slot)` answers `is_sparse_tile` for the block's top-level
    record (callers memoise it per tile)."""
    gn_lat = 1 + lmr.n_parcels_lat[0]
    gn_lng = 1 + lmr.n_parcels_lng[0]
    if ptype and len(leaf_path) > 1:
        return narrow_bounds(block_bounds, gn_lat, gn_lng, leaf_path[0]), "divided_parent"
    if level == 0 and ptype == 0 and len(leaf_path) == 1 and sparse(leaf_path[0]):
        return tile_bounds(block_bounds, gn_lat, gn_lng, leaf_path[0]), "l0_sparse_tile"
    return leaf_bounds, "leaf"


def leaf_frame(level: int, ptype: int, leaf_path: tuple, leaf_bounds: BoundingBox,
               block_bounds: BoundingBox, lmr, sparse: Callable[[int], bool]
               ) -> tuple[BoundingBox, str]:
    """`leaf_frame_shape`, with the frame bbox carrying its range: the bounds
    a leaf's Map Frame decodes (and re-encodes) against."""
    fb, fc = leaf_frame_shape(level, ptype, leaf_path, leaf_bounds, block_bounds, lmr, sparse)
    return replace(fb, coord_range=leaf_frame_range(level, ptype, leaf_path, fc)), fc


def sparse_memo(entries: Sequence, gn_lng: int) -> Callable[[int], bool]:
    """A per-block memoised `is_sparse_tile` over `entries`."""
    cache: dict = {}

    def sparse(idx: int) -> bool:
        ly, lx = divmod(idx, gn_lng)
        key = (ly // L0_TILE, lx // L0_TILE)
        if key not in cache:
            cache[key] = is_sparse_tile(entries, gn_lng, idx)
        return cache[key]
    return sparse


def locate_parcel(fh, zdat0: bytes, pdmdh: Pdmdh, level: int, lat: float, lon: float,
                   sector_sz: int, logical_sz: int) -> MeshLocation | None:
    """The leaf containing (lat, lon) at `level`; `bounds` is the leaf
    slot's own box (no coordinate range). To decode it, use `locate_frame`."""
    found = _locate(fh, zdat0, pdmdh, level, lat, lon, sector_sz, logical_sz)
    return None if found is None else found[0]


def locate_frame(fh, zdat0: bytes, pdmdh: Pdmdh, level: int, lat: float, lon: float,
                  sector_sz: int, logical_sz: int) -> MeshLocation | None:
    """`locate_parcel`, but `bounds` is the leaf's decode FRAME (`leaf_frame`:
    the L0 sparse tile, a divided sub-parcel's parent slot, else the leaf)
    carrying its `coordconv.range_for` range -- the bounds `decode_parcel`
    needs, identical to what `harness.walk.iter_parcels` decodes with."""
    found = _locate(fh, zdat0, pdmdh, level, lat, lon, sector_sz, logical_sz)
    return None if found is None else replace(found[0], bounds=found[1])


def _locate(fh, zdat0: bytes, pdmdh: Pdmdh, level: int, lat: float, lon: float,
            sector_sz: int, logical_sz: int) -> tuple[MeshLocation, BoundingBox] | None:
    """Locate the parcel containing (lat, lon) at the given map level;
    returns (location with leaf bounds, the leaf's ranged frame bounds).

    `fh` is an open file handle on ALLDATA.KWI (for reading the actual
    parcel/road/background/name data once located); `zdat0` is the
    already-read Parcel Data Management Record blob (mhr entry whose name
    is empty and which contains the PDMDH/LMR/BSMR/BMT tables -- typically
    mhr[0]).
    """
    lmr = next((l for l in pdmdh.levels if l.level == level), None)
    if lmr is None:
        raise ValueError(f"no LMR for level {level}")

    lon_span = _lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo

    nx, ny = lmr.grid_nx, lmr.grid_ny
    mx = lon_span / nx
    my = lat_span / ny

    dlon = _lon_delta(pdmdh.coverage.lon_lo, lon, lon_span)
    dlat = lat - pdmdh.coverage.lat_lo

    ix = _clamp(int(dlon / mx), 0, nx - 1)
    iy = _clamp(int(dlat / my), 0, ny - 1)

    nbs_lng, nbs_lat = 1 + lmr.n_blocksets_lng, 1 + lmr.n_blocksets_lat
    nbl_lng, nbl_lat = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
    npc_lng, npc_lat = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]

    px = ix % npc_lng
    tmp = ix // npc_lng
    blx = tmp % nbl_lng
    bsx = tmp // nbl_lng

    py = iy % npc_lat
    tmp = iy // npc_lat
    bly = tmp % nbl_lat
    bsy = tmp // nbl_lat

    bset_flat = bsy * nbs_lng + bsx
    bs_rec = next((b for b in pdmdh.blocksets if b.level == level and b.blockset_index == bset_flat), None)
    if bs_rec is None or bs_rec.bmt_size == 0:
        return None

    n_blocks = nbl_lat * nbl_lng
    bmt_entries = _read_bmt_array(zdat0, bs_rec.bmt_offset, n_blocks)
    block_flat = bly * nbl_lng + blx
    bmt = bmt_entries[block_flat]
    if bmt.dsa == NO_DATA_DSA or bmt.size == 0:
        return None

    poff = getsector(bmt.dsa, sector_sz, logical_sz)
    pdat = _pread(fh, bmt.size * logical_sz, poff)

    # Cell bounds for the matched top-level parcel (before any further
    # divided/integrated-parcel subdivision).
    cell_lon_lo = pdmdh.coverage.lon_lo + ix * mx
    cell_lat_lo = pdmdh.coverage.lat_lo + iy * my
    bounds = BoundingBox(lat_lo=cell_lat_lo, lat_hi=cell_lat_lo + my,
                          lon_lo=cell_lon_lo, lon_hi=cell_lon_lo + mx)

    # (lpx, lpy) for the first loop iteration (depth 1, always parcel type
    # 0 -- the type referenced directly by a block management record) are
    # exactly (px, py) computed above: `ix`/`iy` already fold in the
    # n_parcels_lng[0]/n_parcels_lat[0] factor (see `grid_nx`/`grid_ny` in
    # volume.py), so `px`/`py` *are* this block's parcel-grid coordinates,
    # not merely an intermediate step towards them.
    #
    # BUG FIXED HERE (was: recomputing lpx/lpy from `local_lat_frac`/
    # `local_lon_frac` -- the fractional position *within* the already
    # finest-grained cell that ix/iy identify -- multiplied a second time
    # by the same gn_lng/gn_lat factor already baked into ix/iy. That
    # produced an index that tracked the query point's sub-cell decimal
    # position rather than its real (px, py) parcel-grid coordinates: the
    # displayed `bounds` (computed straight from ix/iy) stayed correct,
    # but the array entry actually fetched was effectively arbitrary --
    # e.g. a Perth CBD query (-31.95312, 115.86719) landed on a real
    # parcel record but one containing Rockingham/Baldivis street and
    # place names, ~40 km south.
    # the cross-checked derivation and validation.
    lpx, lpy = px, py

    # The block's box, for the leaf's coordinate frame (`leaf_frame`).
    block_bounds = BoundingBox(
        lat_lo=pdmdh.coverage.lat_lo + (iy - py) * my,
        lat_hi=pdmdh.coverage.lat_lo + (iy - py) * my + npc_lat * my,
        lon_lo=pdmdh.coverage.lon_lo + (ix - px) * mx,
        lon_hi=pdmdh.coverage.lon_lo + (ix - px) * mx + npc_lng * mx)
    top_entries: list = []
    path: list[int] = []

    poff_in_buf = 0
    depth = 0
    parcel_index = None
    parcel_type = 0
    while True:
        depth += 1
        if depth > MAX_SUBPARCEL_DEPTH:
            return None
        p_type_raw = u16(pdat, poff_in_buf)
        pt = extract(p_type_raw, 8, 9)
        lt = extract(p_type_raw, 0, 7)
        if lt != 0:
            # Unexpected list-type value; kiwiread.c asserts lt==0 for
            # every real parcel management record seen on this disc.
            return None

        gn_lat = 1 + lmr.n_parcels_lat[pt]
        gn_lng = 1 + lmr.n_parcels_lng[pt]
        if depth > 1:
            # Genuine divided/integrated-subparcel recursion: `lpx`/`lpy`
            # here *do* need to come from the fractional position within
            # the just-narrowed `bounds` (set at the bottom of the
            # previous iteration), since this subdivision is additional
            # to what `ix`/`iy` already captured.
            lpx = _clamp(int(local_lon_frac * gn_lng), 0, gn_lng - 1)
            lpy = _clamp(int(local_lat_frac * gn_lat), 0, gn_lat - 1)
        idx = lpy * gn_lng + lpx
        k = gn_lat * gn_lng

        mapinfo_off = poff_in_buf + 4
        if depth == 1:
            top_entries = _read_bmt_array(pdat, mapinfo_off, k)
        path.append(idx)
        entry_off = mapinfo_off + idx * 6
        dsa = u32(pdat, entry_off)
        size = u16(pdat, entry_off + 4)
        parcel_index = idx
        parcel_type = pt

        if dsa == NO_DATA_DSA:
            return None
        if size != 0:
            # Leaf: narrow `bounds` to this sub-cell if we recursed at all.
            if depth > 1 or pt != 0:
                sub_lon = bounds.lon_lo + lpx * (bounds.lon_hi - bounds.lon_lo) / gn_lng
                sub_lat = bounds.lat_lo + lpy * (bounds.lat_hi - bounds.lat_lo) / gn_lat
                bounds = BoundingBox(
                    lat_lo=sub_lat, lat_hi=sub_lat + (bounds.lat_hi - bounds.lat_lo) / gn_lat,
                    lon_lo=sub_lon, lon_hi=sub_lon + (bounds.lon_hi - bounds.lon_lo) / gn_lng,
                )
            loc = MeshLocation(
                level=level, parcel_type=pt, blockset_index=bset_flat,
                block_index=block_flat, parcel_index=idx, bounds=bounds,
                sector_addr=dsa, size_logical_sectors=size,
            )
            frame, _ = leaf_frame(level, pt, tuple(path), bounds, block_bounds, lmr,
                                  sparse_memo(top_entries, npc_lng))
            return loc, frame

        # Subparcel: descend. `dsa` here is actually a [D]-encoded offset
        # into the same pdat buffer (kiwiread.c: `showbmt(..., D(add), j)`).
        # At depth 1 `bounds` is already this type-0 record's own (ix, iy)
        # cell, so the (lpx, lpy) selection above adds no further narrowing
        # (re-narrowing shrank divided parcels to a ~9 m wrong box, brief
        # 28). At depth > 1 the sub-cell selection is a genuine subdivision.
        if depth == 1:
            new_bounds = bounds
        else:
            new_bounds_lon_lo = bounds.lon_lo + lpx * (bounds.lon_hi - bounds.lon_lo) / gn_lng
            new_bounds_lat_lo = bounds.lat_lo + lpy * (bounds.lat_hi - bounds.lat_lo) / gn_lat
            new_bounds = BoundingBox(
                lat_lo=new_bounds_lat_lo, lat_hi=new_bounds_lat_lo + (bounds.lat_hi - bounds.lat_lo) / gn_lat,
                lon_lo=new_bounds_lon_lo, lon_hi=new_bounds_lon_lo + (bounds.lon_hi - bounds.lon_lo) / gn_lng,
            )
        local_lat_frac = (lat - new_bounds.lat_lo) / (new_bounds.lat_hi - new_bounds.lat_lo)
        local_lon_frac = (lon - new_bounds.lon_lo) / (new_bounds.lon_hi - new_bounds.lon_lo)
        bounds = new_bounds
        poff_in_buf = sws(dsa)


def _pread(fh, size: int, offset: int) -> bytes:
    fh.seek(offset)
    return fh.read(size)
