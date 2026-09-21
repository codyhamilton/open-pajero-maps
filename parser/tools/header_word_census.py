#!/usr/bin/env python3
"""Map Frame header-word census of a reference disc's ALLDATA.KWI.

Words are big-endian u16 at byte offset 2*i of the 36-byte header (word 0 =
header size, 6 = dipid, 7 = pmcode high half, 9 = dsflag, 10 = rlx, 11 = rly).
Per leaf the census records the header words, nregion, the mfde table and the
in-buffer slot offsets; it is keyed by (level, parcel class, division state)
using the 2-01 class rule (`coord_scale_census.parcel_class`) with the urban
tile table read from the checked-in `coord_scale.json`.

Fit/held-out split: sha1("bs:blk:path...")[0] < 64  ->  held out (25%), by
parcel identity, deterministic. Rules are derived on the fit set only.
Reads R only through `harness.walk` and `kiwiw.volume/parcel_mgmt`; imports no
writer module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import walk  # noqa: E402
import coord_scale_census as csc  # noqa: E402

WORDS = (0, 6, 7, 9, 10, 11)
NAMES = {0: "size", 6: "dipid", 7: "pmcode", 9: "dsflag", 10: "rlx", 11: "rly"}
SPLIT_RULE = ("held out iff sha1('<bs>:<blk>:<p0>.<p1>...')[0] < 64 (~25%), "
              "by parcel identity (blockset_index, block_index, leaf_path)")
HDR = 36


def heldout(bs: int, blk: int, path) -> bool:
    key = f"{bs}:{blk}:" + ".".join(str(p) for p in path)
    return hashlib.sha1(key.encode()).digest()[0] < 64


def be16(b: bytes, o: int) -> int:
    return (b[o] << 8) | b[o + 1]


def be32(b: bytes, o: int) -> int:
    return (be16(b, o) << 16) | be16(b, o + 2)


def parse_header(data: bytes) -> dict | None:
    """Raw header facts of one Map Frame buffer (no sub-frame decode)."""
    if len(data) < HDR:
        return None
    words = [be16(data, 2 * i) for i in range(18)]
    nreg = words[17]
    de = HDR + 4 * nreg
    slots = []
    for i in range(20):
        o = de + 6 * i
        if o + 6 > len(data):
            break
        slots.append((be32(data, o), be16(data, o + 4)))
    starts = []
    for off, _ in slots[:3]:
        if off != 0xFFFFFFFF:
            v = off << 1
            if v < len(data):
                starts.append(v)
    first = min(starts) if starts else None
    return {"w": words, "nreg": nreg, "first": first, "len": len(data),
            "nent": None if first is None else (first - de) // 6,
            "rg_addr": be32(data, 28), "rg_size": words[16]}


def _work(args) -> list[dict]:
    path, keys = args
    from kiwiw import volume
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    container = walk.read_container(path)
    pdmdh, hdr = container.pdmdh, container.hdr
    ssz, lsz = hdr.sector_size, hdr.logical_sector_size
    lmrs = {l.level: l for l in pdmdh.levels}
    out = []
    with open(path, "rb") as fh:
        for level, bsi, bidx, bsx, bsy, blx, bly, boff, blen in keys:
            lmr = lmrs[level]
            bb = walk._block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
            fh.seek(boff)
            try:
                root = parse_parcel_mgmt_record(fh.read(blen), lmr)
            except Exception:  # noqa: BLE001
                continue
            for lp, entry, lb, pt in walk._iter_tree_leaves(root, bb, lmr, ()):
                fh.seek(volume.getsector(entry.dsa, ssz, lsz))
                data = fh.read(entry.size * lsz)
                h = parse_header(data)
                if h is None:
                    continue
                h.update(level=level, bs=bsi, blk=bidx, path=list(lp), div=pt,
                         dsa=entry.dsa, size=entry.size,
                         lat_lo=lb.lat_lo, lat_hi=lb.lat_hi, lon_lo=lb.lon_lo, lon_hi=lb.lon_hi, bx=blx, by=bly, bsx=bsx, bsy=bsy)
                out.append(h)
    return out


def collect(path: str, workers: int = 10, l0_stride: int = 1) -> list[dict]:
    keys = [(b.level, b.blockset_index, b.block_index, b.bsx, b.bsy, b.blx, b.bly,
             b.file_offset, b.length) for b in walk.iter_blocks(path) if b.error is None and (b.level != 0 or (b.block_index % l0_stride == 0))]
    chunks = [keys[i::workers * 8] for i in range(workers * 8)]
    recs = []
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(_work, [(path, c) for c in chunks if c]):
            recs.extend(r)
    recs.sort(key=lambda r: (r["level"], r["bs"], r["blk"], r["path"]))
    return recs


def keyof(r: dict, urban) -> tuple:
    cls = csc.parcel_class(r["level"], r["div"], (r["bs"], r["blk"], r["path"][0]), urban)
    return (r["level"], cls, csc.division_state(r["div"], r["path"][-1]))
