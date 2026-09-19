#!/usr/bin/env python3
"""Brief 26c step 1: per-level parcel occupancy of the reference disc (R) vs
the generated spool (G). Read-only, offline.

R's populated cell set is read from the PDMDH block/parcel index tree
(no Map Frame decoding, only leaf sizes); G's from `output/spool/level_N.idx`.

Usage:
    python3 parser/tools/parcel_occupancy.py [--reference PATH] [--spool DIR]
        [--levels 0,2,...]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk  # noqa: E402
from kiwiw import volume  # noqa: E402
from kiwiw.spool import SpoolReader  # noqa: E402

EMPTY_FLOOR = 320


def _subtree_bytes(rec, ls: int) -> int:
    seen: set = set()
    total = 0
    stack = [rec]
    while stack:
        r = stack.pop()
        for en in r.entries:
            if en.dsa == walk.NO_DATA_DSA:
                continue
            if en.subrecord is not None:
                stack.append(en.subrecord)
            elif en.size and (en.dsa, en.size) not in seen:
                seen.add((en.dsa, en.size))
                total += en.size * ls
    return total


def ref_cells(path: str, levels=None) -> dict:
    """{level: {(ix, iy): frame_bytes}} for the reference ALLDATA.KWI.
    frame_bytes sums the distinct on-disk leaf ranges of a (possibly
    divided) cell. Cell = block-relative type-0 slot of the block root."""
    c = walk.read_container(path)
    pdmdh, hdr = c.pdmdh, c.hdr
    ss, ls = hdr.sector_size, hdr.logical_sector_size
    out: dict = {}
    with open(path, "rb") as fh:
        for lmr in pdmdh.levels:
            level = lmr.level
            if levels is not None and level not in levels:
                continue
            cells: dict = {}
            npc_lng = 1 + lmr.n_parcels_lng[0]
            npc_lat = 1 + lmr.n_parcels_lat[0]
            nbl_lng = 1 + lmr.n_blocks_lng
            nbl_lat = 1 + lmr.n_blocks_lat
            nbs_lng = 1 + lmr.n_blocksets_lng
            for bso, bs in enumerate(pdmdh.blocksets):
                if bs.level != level:
                    continue
                tbl = next((t for t in pdmdh.bmt_tables if t.blockset_ordinal == bso), None)
                if tbl is None:
                    continue
                bsy, bsx = divmod(bs.blockset_index, nbs_lng)
                for ei, e in enumerate(tbl.entries):
                    if e.dsa == walk.NO_DATA_DSA or not e.size:
                        continue
                    bly, blx = divmod(ei, nbl_lng)
                    base_ix = (bsx * nbl_lng + blx) * npc_lng
                    base_iy = (bsy * nbl_lat + bly) * npc_lat
                    fh.seek(volume.getsector(e.dsa, ss, ls))
                    buf = fh.read(e.size * ls)
                    try:
                        root = walk.parse_parcel_mgmt_record(buf, lmr)
                    except Exception:
                        continue
                    for idx, entry in enumerate(root.entries):
                        if entry.dsa == walk.NO_DATA_DSA:
                            continue
                        lpy, lpx = divmod(idx, npc_lng)
                        key = (base_ix + lpx, base_iy + lpy)
                        if entry.subrecord is not None:
                            size = _subtree_bytes(entry.subrecord, ls)
                        elif entry.size:
                            size = entry.size * ls
                        else:
                            continue
                        cells[key] = cells.get(key, 0) + size
            out[level] = cells
    return out


def spool_cells(spool_dir: str, level: int) -> set:
    return set(SpoolReader(spool_dir).cell_keys(level))


def analyse(R: dict, G: set) -> dict:
    rs = set(R)
    rg = rs - G
    sizes = sorted(R[k] for k in rg)
    n = len(sizes)
    both = sorted(R[k] for k in rs & G)
    res = {
        "R": len(rs), "G": len(G), "both": len(both), "R-G": n, "G-R": len(G - rs),
        "RmG_at_floor": sum(1 for s in sizes if s <= EMPTY_FLOOR),
        "RmG_le500": sum(1 for s in sizes if s <= 500),
        "RmG_median": sizes[n // 2] if n else 0,
        "RmG_p95": sizes[int(n * 0.95)] if n else 0,
        "RmG_bytes": sum(sizes),
        "RG_median": both[len(both) // 2] if both else 0,
    }
    if rs:
        xs = [k[0] for k in rs]
        ys = [k[1] for k in rs]
        res["R_bbox"] = (min(xs), max(xs), min(ys), max(ys))
        res["R_bbox_fill"] = round(len(rs) / ((max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)), 4)
        rows = defaultdict(list)
        for x, y in rs:
            rows[y].append(x)
        runs = []
        for v in rows.values():
            v.sort()
            runs.append(1 + sum(1 for a, b in zip(v, v[1:]) if b != a + 1))
        res["R_rows"] = len(rows)
        res["R_rows_single_run"] = sum(1 for r in runs if r == 1)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default="/run/media/codyh/464210-8480/ALLDATA.KWI")
    ap.add_argument("--spool", default="output/spool")
    ap.add_argument("--levels", default="0,2,4,6,8,10,12")
    ap.add_argument("--write-mask", metavar="PATH",
                    help="write parser/refdata/parcel_mask.json (per-level R rectangle; "
                         "only if R's populated set fills its bbox exactly)")
    args = ap.parse_args()
    levels = [int(x) for x in args.levels.split(",")]
    R = ref_cells(args.reference, set(levels))
    if args.write_mask:
        import json
        mask = {}
        for lv in levels:
            rs = R.get(lv, {})
            xs = [k[0] for k in rs]
            ys = [k[1] for k in rs]
            box = (min(xs), max(xs), min(ys), max(ys))
            if len(rs) != (box[1] - box[0] + 1) * (box[3] - box[2] + 1):
                print(f"level {lv}: R is not a full rectangle; refusing", file=sys.stderr)
                return 2
            mask[str(lv)] = {"ix_lo": box[0], "ix_hi": box[1], "iy_lo": box[2], "iy_hi": box[3]}
        with open(args.write_mask, "w") as fh:
            json.dump(mask, fh, indent=2, sort_keys=True)
            fh.write("\n")
    for lv in levels:
        r = analyse(R.get(lv, {}), spool_cells(args.spool, lv))
        print(f"level {lv}: " + ", ".join(f"{k}={v}" for k, v in r.items()), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
