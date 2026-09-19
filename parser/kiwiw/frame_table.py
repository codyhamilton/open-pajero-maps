"""Indexed frame storage + vectorised layout for the ALLDATA.KWI assembler
(plan 02, step 2/3).

Encode workers append frames to their own spill file and describe them as
rows of a numpy `FRAME_DTYPE` array (a `FrameTable`), so neither frame bytes
nor per-frame Python objects cross the process boundary. `IndexedLayout`
computes every frame/block position from those arrays with numpy, producing
exactly the layout the per-object path in `alldata_writer` produces (that path
stays as the byte-identity oracle); `write_frames` copies frames with a
GIL-free C loop across threads.
"""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np

FRAME_DTYPE = np.dtype([("ix", "<i4"), ("iy", "<i4"), ("pt", "u1"), ("sx", "u1"),
                        ("sy", "u1"), ("fid", "<u2"), ("len", "<u4"), ("off", "<u8")])


@dataclass
class FrameTable:
    """Every frame of one level: `rec[i]` = (ix, iy, parcel_type, sub_ix,
    sub_iy, spill file id, length, offset). `files[fid]` is the spill path.
    Rows are in canonical stream order (which fixes divided sub-frame order)."""
    files: list[str]
    rec: np.ndarray = field(default_factory=lambda: np.zeros(0, FRAME_DTYPE))

    @property
    def n_frames(self) -> int:
        return len(self.rec)


class ChunkSpill:
    """Per-process append-only frame file (one per encode worker)."""

    def __init__(self, directory: str):
        self.path = os.path.join(directory, f"kwi_spill_{os.getpid()}_{uuid.uuid4().hex[:8]}.bin")
        self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        self.end = 0

    def append(self, data: bytes | bytearray) -> int:
        off, mv, p = self.end, memoryview(data), 0
        while p < len(mv):
            p += os.pwrite(self._fd, mv[p:], off + p)
        self.end += len(mv)
        return off

    def close(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1


def merge_tables(tables: list[tuple[str, np.ndarray]]) -> FrameTable:
    """Concatenate per-chunk `(spill_path, rec)` results (in stream order)."""
    files: list[str] = []
    fid_of: dict[str, int] = {}
    parts = []
    for path, rec in tables:
        fid = fid_of.get(path)
        if fid is None:
            fid = fid_of[path] = len(files)
            files.append(path)
        if len(rec):
            rec["fid"] = fid
            parts.append(rec)
    return FrameTable(files, np.concatenate(parts) if parts else np.zeros(0, FRAME_DTYPE))


def _sector_addr(off: np.ndarray, sector_sz: int, logical_sz: int) -> np.ndarray:
    if np.any(off % logical_sz):
        raise ValueError("frame offset not logical-sector aligned")
    sec, rem = np.divmod(off, sector_sz)
    sub = rem // logical_sz
    if sec.size and int(sec.max()) > 0xFFFFFF:
        raise ValueError("sector index does not fit in 24 bits")
    return ((sec << 8) | sub).astype(np.uint32)


class IndexedLayout:
    """Vectorised equivalent of the object path's bucket/place loops.

    Blocks are ordered by (level, blockset, block); within a block the type-0
    frames come first in slot order, then divided sub-frames grouped by parent
    slot (stream order inside a parent); the block record follows its frames.
    """

    def __init__(self, levels, dims, lmr_by_level, sector_sz: int, logical_sz: int,
                 locate_np, footprint_entries):
        self.sector_sz, self.logical_sz = sector_sz, logical_sz
        self.dims, self.lmr_by_level = dims, lmr_by_level
        self.tables = {lvl: lb.table for lvl, lb in levels.items()}
        self.files: list[str] = []
        blocks_l, key_l, group_l, local_l, rec_l, fid_base = [], [], [], [], [], 0
        lvl_l = []
        for lvl in sorted(self.tables):
            t = self.tables[lvl]
            if t is None or t.n_frames == 0:
                continue
            d = dims[lvl]
            n_slots = d["npc_lat"] * d["npc_lng"]
            n_blocks = d["nbl_lat"] * d["nbl_lng"]
            rec = t.rec.copy()
            rec["fid"] += fid_base
            fid_base += len(t.files)
            self.files += t.files
            bs, bl, lx, ly = locate_np(rec["ix"].astype(np.int64), rec["iy"].astype(np.int64), d)
            blocks_l.append(bs * n_blocks + bl)
            local_l.append(ly * d["npc_lng"] + lx)
            group_l.append((rec["pt"] != 0).astype(np.int8))
            lvl_l.append(np.full(len(rec), lvl, np.int16))
            rec_l.append(rec)
        if not rec_l:
            raise ValueError("indexed layout: no frames")
        rec = np.concatenate(rec_l)
        lvl_a = np.concatenate(lvl_l)
        blockkey = np.concatenate(blocks_l)
        local = np.concatenate(local_l)
        group = np.concatenate(group_l)
        # level is the primary key; blockkey (bs * n_blocks + bl) orders (bs, bl)
        order = np.lexsort((np.arange(len(rec)), local, group, blockkey, lvl_a))
        self.rec = rec[order]
        self.lvl = lvl_a[order]
        self.blockkey = blockkey[order]
        self.local = local[order]
        self.group = group[order]
        self._check_conflicts()

        lg = self.logical_sz
        self.padded = ((self.rec["len"].astype(np.int64) + lg - 1) // lg) * lg
        # block boundaries
        change = np.ones(len(self.rec), bool)
        change[1:] = (self.blockkey[1:] != self.blockkey[:-1]) | (self.lvl[1:] != self.lvl[:-1])
        self.first = np.flatnonzero(change)
        self.n_blocks = len(self.first)
        self.blk_lvl = self.lvl[self.first]
        self.blk_key = self.blockkey[self.first]
        self.frame_bytes = np.add.reduceat(self.padded, self.first)

        # divided parents -> sub-record sizes
        is_div = self.group == 1
        self.blk_sub_bytes = np.zeros(self.n_blocks, np.int64)
        self.blk_n_div = np.zeros(self.n_blocks, np.int64)
        if is_div.any():
            di = np.flatnonzero(is_div)
            newp = np.ones(len(di), bool)
            newp[1:] = ((self.blockkey[di][1:] != self.blockkey[di][:-1])
                        | (self.lvl[di][1:] != self.lvl[di][:-1])
                        | (self.local[di][1:] != self.local[di][:-1]))
            pi = di[newp]
            gn = np.zeros(len(pi), np.int64)
            for lvl in np.unique(self.lvl[pi]):
                lmr = lmr_by_level[int(lvl)]
                sel = self.lvl[pi] == lvl
                for pt in np.unique(self.rec["pt"][pi][sel]):
                    m = sel & (self.rec["pt"][pi] == pt)
                    gn[m] = (1 + lmr.n_parcels_lat[int(pt)]) * (1 + lmr.n_parcels_lng[int(pt)])
            blk_of = np.searchsorted(self.first, pi, side="right") - 1
            np.add.at(self.blk_sub_bytes, blk_of, 4 + 6 * gn)
            np.add.at(self.blk_n_div, blk_of, 1)
            self.parent_idx, self.parent_gn, self.parent_blk = pi, gn, blk_of
        slots = np.zeros(self.n_blocks, np.int64)
        for l in np.unique(self.blk_lvl):
            slots[self.blk_lvl == l] = dims[int(l)]["npc_lat"] * dims[int(l)]["npc_lng"]
        self.blk_slots = slots
        sub_cursor = footprint_entries(slots) + self.blk_sub_bytes
        self.block_total = ((sub_cursor + lg - 1) // lg) * lg

    def _check_conflicts(self) -> None:
        r = self.rec
        same = (self.blockkey[1:] == self.blockkey[:-1]) & (self.lvl[1:] == self.lvl[:-1]) \
            & (self.local[1:] == self.local[:-1])
        dup0 = same & (self.group[1:] == 0) & (self.group[:-1] == 0)
        if dup0.any():
            i = int(np.flatnonzero(dup0)[0]) + 1
            raise ValueError(f"level {int(self.lvl[i])}: duplicate parcel at "
                             f"ix={int(r['ix'][i])} iy={int(r['iy'][i])}")
        both = same & (self.group[1:] == 1) & (self.group[:-1] == 0)
        if both.any():
            i = int(np.flatnonzero(both)[0]) + 1
            raise ValueError(
                f"level {int(self.lvl[i])}: block key {int(self.blockkey[i])} local slot "
                f"{int(self.local[i])} has both a type-0 parcel and divided sub-frames -- "
                f"plan_divisions() should never yield both for the same parent cell")

    @property
    def present_blocksets(self) -> set[tuple[int, int]]:
        out = set()
        for lvl in np.unique(self.blk_lvl):
            n_blocks = self.dims[int(lvl)]["nbl_lat"] * self.dims[int(lvl)]["nbl_lng"]
            for bs in np.unique(self.blk_key[self.blk_lvl == lvl] // n_blocks):
                out.add((int(lvl), int(bs)))
        return out

    def place(self, cursor0: int) -> None:
        """Assign file offsets, given where the first block's frames begin."""
        span = self.frame_bytes + self.block_total
        base = cursor0 + np.cumsum(span) - span
        excl = np.cumsum(self.padded) - self.padded
        blk_of = np.repeat(np.arange(self.n_blocks), np.diff(np.append(self.first, len(self.rec))))
        self.item_off = base[blk_of] + (excl - excl[self.first][blk_of])
        self.block_off = base + self.frame_bytes
        self.total_size = int(cursor0 + span.sum())
        self.item_dsa = _sector_addr(self.item_off, self.sector_sz, self.logical_sz)
        self.item_size = (self.padded // self.logical_sz)
        if self.item_size.size and int(self.item_size.max()) > 0xFFFF:
            raise ValueError("frame too large for a u16 logical-sector size")
        self.block_dsa = _sector_addr(self.block_off, self.sector_sz, self.logical_sz)
        self.block_size = self.block_total // self.logical_sz

    # ---- block records -------------------------------------------------
    def simple_block_rows(self, lvl: int, footprint: int, block_total: int):
        """(block ordinals, [n, block_total] u8 array) for `lvl`'s blocks that
        carry no divided parents: header, entries, zero tail."""
        sel = np.flatnonzero((self.blk_lvl == lvl) & (self.blk_n_div == 0))
        n_slots = int(self.dims[lvl]["npc_lat"] * self.dims[lvl]["npc_lng"])
        arr = np.zeros((len(sel), block_total), np.uint8)
        if not len(sel):
            return sel, arr
        ent = arr[:, 4:4 + 6 * n_slots].reshape(len(sel), n_slots, 6)
        ent[:, :, 0:4] = 0xFF  # NO_DATA_DSA; size stays 0
        ord_of = np.full(self.n_blocks, -1, np.int64)
        ord_of[sel] = np.arange(len(sel))
        blk_of_item = np.repeat(np.arange(self.n_blocks),
                                np.diff(np.append(self.first, len(self.rec))))
        m = (self.lvl == lvl) & (ord_of[blk_of_item] >= 0)
        rows = ord_of[blk_of_item[m]]
        cols = self.local[m]
        ent[rows, cols, 0:4] = self.item_dsa[m].astype(">u4").view(np.uint8).reshape(-1, 4)
        ent[rows, cols, 4:6] = self.item_size[m].astype(">u2").view(np.uint8).reshape(-1, 2)
        return sel, arr

    # ---- writing -------------------------------------------------------
    def write_frames(self, lib, out_fd: int, threads: int) -> None:
        import ctypes
        srcs = [os.open(p, os.O_RDONLY) for p in self.files]
        try:
            fds = (ctypes.c_int * len(srcs))(*srcs)
            r = self.rec
            fid = np.ascontiguousarray(r["fid"])
            soff = np.ascontiguousarray(r["off"])
            dst = np.ascontiguousarray(self.item_off.astype(np.uint64))
            ln = np.ascontiguousarray(r["len"])
            pad = np.ascontiguousarray(self.padded.astype(np.uint32))
            n = len(r)
            cap = int(pad.max()) if n else 0

            def part(a, b):
                res = lib.kw_copy_frames(
                    out_fd, b - a, ctypes.addressof(fds), fid[a:].ctypes.data,
                    soff[a:].ctypes.data, dst[a:].ctypes.data, ln[a:].ctypes.data,
                    pad[a:].ctypes.data, cap)
                if res:
                    raise OSError(f"frame copy failed at item {a + (-res - 1)}")

            step = max(1, -(-n // (threads * 8)))
            with ThreadPoolExecutor(threads) as ex:
                list(ex.map(lambda a: part(a, min(n, a + step)), range(0, n, step)))
        finally:
            for fd in srcs:
                os.close(fd)


def locate_np(ix: np.ndarray, iy: np.ndarray, d: dict):
    """Vectorised `alldata_writer._locate`."""
    bsx, rx = np.divmod(ix, d["nbl_lng"] * d["npc_lng"])
    blx, lx = np.divmod(rx, d["npc_lng"])
    bsy, ry = np.divmod(iy, d["nbl_lat"] * d["npc_lat"])
    bly, ly = np.divmod(ry, d["npc_lat"])
    return bsy * d["nbs_lng"] + bsx, bly * d["nbl_lng"] + blx, lx, ly
