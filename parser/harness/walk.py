"""Streaming whole-disc walker: the harness's own read-only traversal of an
`ALLDATA.KWI`, over every level / block set / block / leaf, in on-disc table
order.

Deliberately not a reuse of the KIWI-W assembler module's own
`load_region()`/`_walk_tree()` helpers (in `parser/kiwiw/`, named for the
whole-file assembler it belongs to): those exist to load one requested
(level, blockset_indices) region fully into memory for the round-trip/
allocation encoders, and that module builds output rather than only
reading it, so the harness must never import it (see
`docs/design/target-disc.md`, "Architectural Implications": "the harness
imports only the parser's *reading* paths"). This module reimplements the
same block/mapinfo-tree bounds arithmetic (`_block_base_bounds`/
`_narrow_bounds`, ported here rather than shared) as a *streaming*
generator: nothing decoded is retained past the single leaf/block being
yielded.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

# `kiwiw` lives at `parser/kiwiw`; this module lives at `parser/harness/walk.py`,
# so its grandparent directory (`parser/`) is what needs to be importable --
# matching the sys.path idiom every top-level `parser/*.py` script already uses.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import volume
from kiwiw.model import BoundingBox, Parcel, ParcelMgmtRecord
from kiwiw.parcel import decode_parcel
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
from kiwiw.model import MeshLocation

NO_DATA_DSA = 0xFFFFFFFF


# ---------------------------------------------------------------------
# Container-level reads (header / extras / MHT / full PDMDH), no level
# filter -- the same reads the assembler module's `load_region()` helper
# performs before it narrows to one level/blockset selection.
# ---------------------------------------------------------------------

@dataclass
class Container:
    hdr: volume.VolumeHeader
    extras: volume.VolumeHeaderExtras
    mht: volume.ManagementHeaderTable
    pdmdh: volume.Pdmdh
    prdm_offset: int
    file_size: int


def read_container(path: str) -> Container:
    """Read the Data Volume header, its extras, the full Management Header
    Table and the full PDMDH (with every level's LMR, every BSMR, and
    every blockset's Block Management Table -- `parse_pdmdh_full()` builds
    all of these unconditionally, unlike `load_region()` which is handed
    one level to filter to)."""
    import os

    file_size = os.path.getsize(path)
    with open(path, "rb") as fh:
        raw_header = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_header)
        extras = volume.parse_volume_header_extras(raw_header)
        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        prdm = mht.entries[0]
        if prdm.name:
            raise NotImplementedError("file-based PDMDH not supported")
        prdm_off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        prdm_size = prdm.size * hdr.logical_sector_size
        fh.seek(prdm_off)
        raw_prdm = fh.read(prdm_size)
        pdmdh = volume.parse_pdmdh_full(raw_prdm)
    return Container(hdr=hdr, extras=extras, mht=mht, pdmdh=pdmdh,
                      prdm_offset=prdm_off, file_size=file_size)


# ---------------------------------------------------------------------
# Bounds bookkeeping (reimplemented from the assembler module's private
# helpers of the same name -- pure grid arithmetic, no encoder dependency).
# ---------------------------------------------------------------------

def _lon_span(lo: float, hi: float) -> float:
    span = hi - lo
    return span + 360.0 if span < 0 else span


def _block_base_bounds(pdmdh: volume.Pdmdh, lmr, bsx: int, bsy: int, blx: int, bly: int) -> BoundingBox:
    lon_span = _lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    mx = lon_span / lmr.grid_nx
    my = lat_span / lmr.grid_ny
    npc_lng = 1 + lmr.n_parcels_lng[0]
    npc_lat = 1 + lmr.n_parcels_lat[0]
    nbl_lng = 1 + lmr.n_blocks_lng
    nbl_lat = 1 + lmr.n_blocks_lat
    base_ix = (bsx * nbl_lng + blx) * npc_lng
    base_iy = (bsy * nbl_lat + bly) * npc_lat
    base_lon = pdmdh.coverage.lon_lo + base_ix * mx
    base_lat = pdmdh.coverage.lat_lo + base_iy * my
    return BoundingBox(lat_lo=base_lat, lat_hi=base_lat + npc_lat * my,
                        lon_lo=base_lon, lon_hi=base_lon + npc_lng * mx)


def _narrow_bounds(bounds: BoundingBox, gn_lat: int, gn_lng: int, idx: int) -> BoundingBox:
    lpy, lpx = divmod(idx, gn_lng)
    lon_step = (bounds.lon_hi - bounds.lon_lo) / gn_lng
    lat_step = (bounds.lat_hi - bounds.lat_lo) / gn_lat
    lon_lo = bounds.lon_lo + lpx * lon_step
    lat_lo = bounds.lat_lo + lpy * lat_step
    return BoundingBox(lat_lo=lat_lo, lat_hi=lat_lo + lat_step,
                        lon_lo=lon_lo, lon_hi=lon_lo + lon_step)


# ---------------------------------------------------------------------
# WalkedParcel / iter_parcels
# ---------------------------------------------------------------------

@dataclass
class WalkedParcel:
    """One yielded unit of `iter_parcels()`: either a decoded leaf Map
    Frame, or (when `leaf_path == ()`) a marker for a whole block that
    failed to parse as a Parcel Management Record at all -- there is no
    leaf to report in that case, so the block's own file offset/length
    stand in and `parcel` is `None`."""
    level: int
    blockset_index: int
    block_index: int
    parcel_type: int
    leaf_path: tuple
    bounds: BoundingBox
    file_offset: int
    length: int
    parcel: Optional[Parcel]
    error: Optional[str]


def _iter_tree_leaves(rec: ParcelMgmtRecord, bounds: BoundingBox, lmr, path: tuple):
    """Yield (leaf_path, entry, child_bounds, parcel_type) for every real
    leaf reachable from `rec` -- parcel_type is the *enclosing* record's
    parcel_type (0 = normal, 1..3 = pardiv1..3), since that is what
    determines the mapinfo grid dimensions the leaf's index was drawn
    from."""
    gn_lat = 1 + lmr.n_parcels_lat[rec.parcel_type]
    gn_lng = 1 + lmr.n_parcels_lng[rec.parcel_type]
    for idx, entry in enumerate(rec.entries):
        if entry.dsa == NO_DATA_DSA:
            continue
        child_bounds = _narrow_bounds(bounds, gn_lat, gn_lng, idx)
        child_path = path + (idx,)
        if entry.subrecord is not None:
            yield from _iter_tree_leaves(entry.subrecord, child_bounds, lmr, child_path)
        elif entry.size:
            yield child_path, entry, child_bounds, rec.parcel_type


def iter_parcels(path: str) -> Iterator[WalkedParcel]:
    """Stream every leaf Map Frame of `path`'s `ALLDATA.KWI`, over every
    level / block set / block, in on-disc table order. Decoding happens
    one leaf at a time; nothing decoded is retained across iterations.

    Progress lines (with `flush=True`) are printed per level, and every
    200 blocks at level 0 (the reference disc has 1836 non-empty blocks
    at level 0, by far the largest level)."""
    container = read_container(path)
    hdr, pdmdh = container.hdr, container.pdmdh
    sector_sz, logical_sz = hdr.sector_size, hdr.logical_sector_size

    with open(path, "rb") as fh:
        for lmr in pdmdh.levels:
            level = lmr.level
            print(f"[harness.walk] level {level}: starting", flush=True)
            nbs_lng = 1 + lmr.n_blocksets_lng
            nbl_lng = 1 + lmr.n_blocks_lng
            blocks_done = 0
            leaves_done = 0
            for bs_ordinal, bs in enumerate(pdmdh.blocksets):
                if bs.level != level:
                    continue
                bmt_table = next(
                    (t for t in pdmdh.bmt_tables if t.blockset_ordinal == bs_ordinal), None)
                if bmt_table is None:
                    continue
                bsy, bsx = divmod(bs.blockset_index, nbs_lng)
                for entry_index, bmt_entry in enumerate(bmt_table.entries):
                    if bmt_entry.dsa == NO_DATA_DSA or not bmt_entry.size:
                        continue
                    boff = volume.getsector(bmt_entry.dsa, sector_sz, logical_sz)
                    blen = bmt_entry.size * logical_sz
                    bly, blx = divmod(entry_index, nbl_lng)
                    block_bounds = _block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)

                    fh.seek(boff)
                    bbuf = fh.read(blen)
                    try:
                        root = parse_parcel_mgmt_record(bbuf, lmr)
                    except Exception as exc:  # noqa: BLE001 -- decode-clean check needs the text
                        yield WalkedParcel(
                            level=level, blockset_index=bs.blockset_index,
                            block_index=entry_index, parcel_type=0, leaf_path=(),
                            bounds=block_bounds, file_offset=boff, length=blen,
                            parcel=None, error=f"parse_parcel_mgmt_record: {exc}")
                        blocks_done += 1
                        continue

                    for leaf_path, entry, leaf_bounds, ptype in _iter_tree_leaves(
                            root, block_bounds, lmr, ()):
                        moff = volume.getsector(entry.dsa, sector_sz, logical_sz)
                        mlen = entry.size * logical_sz
                        try:
                            fh.seek(moff)
                            mapdata = fh.read(mlen)
                            loc = MeshLocation(
                                level=level, parcel_type=ptype,
                                blockset_index=bs.blockset_index,
                                block_index=entry_index, parcel_index=leaf_path[-1],
                                bounds=leaf_bounds, sector_addr=entry.dsa,
                                size_logical_sectors=entry.size)
                            parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                                    n_ext_map=lmr.n_ext_map)
                            err = None
                        except Exception as exc:  # noqa: BLE001
                            parcel = None
                            err = f"decode_parcel: {exc}"
                        yield WalkedParcel(
                            level=level, blockset_index=bs.blockset_index,
                            block_index=entry_index, parcel_type=ptype,
                            leaf_path=leaf_path, bounds=leaf_bounds,
                            file_offset=moff, length=mlen, parcel=parcel, error=err)
                        leaves_done += 1

                    blocks_done += 1
                    if level == 0 and blocks_done % 200 == 0:
                        print(f"[harness.walk] level 0: {blocks_done} blocks, "
                              f"{leaves_done} leaves so far", flush=True)

            print(f"[harness.walk] level {level}: done, {blocks_done} blocks, "
                  f"{leaves_done} leaves", flush=True)


# ---------------------------------------------------------------------
# iter_blocks: each block's parsed ParcelMgmtRecord with its BMT
# coordinates, without descending into leaves.
# ---------------------------------------------------------------------

@dataclass
class WalkedBlock:
    level: int
    blockset_index: int
    block_index: int
    bsx: int
    bsy: int
    blx: int
    bly: int
    bmt_dsa: int
    bmt_size: int
    file_offset: int
    length: int
    root: Optional[ParcelMgmtRecord]
    error: Optional[str]


def iter_blocks(path: str) -> Iterator[WalkedBlock]:
    """Yield every non-empty block's parsed `ParcelMgmtRecord` plus its BMT
    coordinates (block-set x/y, block x/y within the block set), in
    on-disc table order. Does not descend into leaf Map Frames."""
    container = read_container(path)
    hdr, pdmdh = container.hdr, container.pdmdh
    sector_sz, logical_sz = hdr.sector_size, hdr.logical_sector_size

    with open(path, "rb") as fh:
        for lmr in pdmdh.levels:
            level = lmr.level
            nbs_lng = 1 + lmr.n_blocksets_lng
            nbl_lng = 1 + lmr.n_blocks_lng
            for bs_ordinal, bs in enumerate(pdmdh.blocksets):
                if bs.level != level:
                    continue
                bmt_table = next(
                    (t for t in pdmdh.bmt_tables if t.blockset_ordinal == bs_ordinal), None)
                if bmt_table is None:
                    continue
                bsy, bsx = divmod(bs.blockset_index, nbs_lng)
                for entry_index, bmt_entry in enumerate(bmt_table.entries):
                    if bmt_entry.dsa == NO_DATA_DSA or not bmt_entry.size:
                        continue
                    boff = volume.getsector(bmt_entry.dsa, sector_sz, logical_sz)
                    blen = bmt_entry.size * logical_sz
                    bly, blx = divmod(entry_index, nbl_lng)
                    fh.seek(boff)
                    bbuf = fh.read(blen)
                    try:
                        root = parse_parcel_mgmt_record(bbuf, lmr)
                        err = None
                    except Exception as exc:  # noqa: BLE001
                        root, err = None, f"parse_parcel_mgmt_record: {exc}"
                    yield WalkedBlock(
                        level=level, blockset_index=bs.blockset_index,
                        block_index=entry_index, bsx=bsx, bsy=bsy, blx=blx, bly=bly,
                        bmt_dsa=bmt_entry.dsa, bmt_size=bmt_entry.size,
                        file_offset=boff, length=blen, root=root, error=err)
