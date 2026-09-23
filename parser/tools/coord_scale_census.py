#!/usr/bin/env python3
"""Coordinate-range census of a reference disc's ALLDATA.KWI.

Per parcel (leaf Map Frame): the observed per-axis maximum of the parcel-local
coordinates over every road node, road intermediate point and background
shape vertex, plus the maximum over clipped-link end points (first/last node
of each link). Aggregated per (level, parcel class, division state) into the
modal maximum, its share, and exceptions.

Raw coordinates are recovered from the decoder's lat/lon, which assumes the
2**15 range (`decode_region_coord` values scaled by 32768 over the leaf
bounds); road nodes carry their raw x/y directly.

The parcel-class rule (`parcel_class`) is a function of (level, grid
position, division state) only; it takes no decoded content. Reads R only
through `harness.walk`; imports no writer module.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk  # noqa: E402

EXCEPTION_EXAMPLES = 20
# Observed-max buckets: a parcel's "observed range" is the smallest of these
# that holds its maximum (R's ranges are powers of two); anything larger is
# reported verbatim.
NAMES = {0: "normal", 1: "pardiv1", 2: "pardiv2", 3: "pardiv3"}


def _raw(lat: float, lon: float, b, rng: float) -> tuple[int, int]:
    """Invert xy_to_latlon at `rng`, which must be the range the decoder
    used for this parcel (`wp.frame_range`, its frame's `range_for`)."""
    x = (lon - b.lon_lo) / (b.lon_hi - b.lon_lo) * rng
    y = (lat - b.lat_lo) / (b.lat_hi - b.lat_lo) * rng
    return int(round(x)), int(round(y))


def parcel_measure(wp) -> dict | None:
    """Per-axis maxima for one walked parcel, or None if it has no geometry."""
    p = wp.parcel
    if p is None:
        return None
    b = wp.frame_bounds  # decode anchors lat/lon on the frame, not the leaf
    rng = wp.frame_range  # ...and at the frame's range
    mx = my = -1
    end_max = -1
    road_max = -1
    n = 0
    road = getattr(p, "road", None)
    if road is not None:
        for link in road.links:
            for i, nd in enumerate(link.nodes):
                mx, my = max(mx, nd.x), max(my, nd.y)
                road_max = max(road_max, nd.x, nd.y)
                n += 1
                if i in (0, len(link.nodes) - 1):
                    end_max = max(end_max, nd.x, nd.y)
            for lat, lon in (link.points or []):
                x, y = _raw(lat, lon, b, rng)
                mx, my = max(mx, x), max(my, y)
                road_max = max(road_max, x, y)
                n += 1
    bg = getattr(p, "background", None)
    if bg is not None:
        for sh in bg.shapes:
            for lat, lon in sh.coords:
                x, y = _raw(lat, lon, b, rng)
                mx, my = max(mx, x), max(my, y)
                n += 1
    if n == 0:
        return None
    return {"max_x": mx, "max_y": my, "max": max(mx, my), "end_max": end_max,
            "road_max": road_max}


L0_TILE = 4  # L0 leaves sit on a 4x4-leaf tile grid; index = y*L0_GRID_W + x
L0_GRID_W = 32


def division_state(division: int, sub_index: int) -> str:
    """Division state of a leaf: "normal", or "pardiv<k>_sub<i>" for sub-parcel
    i of a divided parcel of type k (parcel_type 1..3)."""
    return "normal" if division == 0 else f"pardiv{division}_sub{sub_index}"


def l0_tile(leaf_index: int) -> tuple[int, int]:
    """(tile_y, tile_x) of an L0 leaf index in its block's 32-wide grid."""
    return (leaf_index // L0_GRID_W) // L0_TILE, (leaf_index % L0_GRID_W) // L0_TILE


def parcel_class(level: int, division: int, grid: tuple, urban_tiles) -> str:
    """Content-independent class of a parcel: a function of level, division
    state and grid position only (`grid` = (blockset_index, block_index,
    leaf_index)); `urban_tiles` is the census table of L0 4x4 tiles
    {(blockset, block, tile_y, tile_x)} that hold a 4x4 leaf subdivision.
    No decoded content is an input. Sub-parcels (division != 0) share the
    class of their level ("full" above L0, and "sparse"/"urban" is not
    defined for them at L0: they are "divided")."""
    if division != 0:
        return "divided"
    if level != 0:
        return "full"
    bs, blk, idx = grid
    ty, tx = l0_tile(idx)
    return "urban" if (bs, blk, ty, tx) in urban_tiles else "sparse"


def derive_urban_tiles(recs: list[dict]) -> set:
    """Tiles whose leaf layout (grid occupancy, not content) is subdivided:
    any L0 normal leaf off the tile anchor (x%4, y%4) != (0, 0)."""
    t = set()
    for r in recs:
        if r["level"] == 0 and r["div"] == 0:
            p = r["path"][0]
            if (p % L0_GRID_W) % L0_TILE or (p // L0_GRID_W) % L0_TILE:
                t.add((r["bs"], r["blk"], *l0_tile(p)))
    return t


def _grid(r: dict) -> tuple:
    return (r["bs"], r["blk"], r["path"][0])


def _div_key(r: dict) -> str:
    return division_state(r["div"], r["path"][-1])


def _record(wp, m: dict) -> dict:
    return {"level": wp.level, "bs": wp.blockset_index, "blk": wp.block_index,
            "path": list(wp.leaf_path), "div": wp.parcel_type, **m}


def _work(args) -> list[dict]:
    path, keys = args
    container = walk.read_container(path)
    pdmdh, hdr = container.pdmdh, container.hdr
    from kiwiw import volume
    from kiwiw.model import MeshLocation
    from kiwiw.parcel import decode_parcel
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    ssz, lsz = hdr.sector_size, hdr.logical_sector_size
    lmrs = {l.level: l for l in pdmdh.levels}
    out = []
    seen = set()
    with open(path, "rb") as fh:
        for level, bsi, bidx, bsx, bsy, blx, bly, boff, blen in keys:
            lmr = lmrs[level]
            bb = walk._block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
            fh.seek(boff)
            try:
                root = parse_parcel_mgmt_record(fh.read(blen), lmr)
            except Exception:  # noqa: BLE001
                continue
            sparse_cache: dict = {}
            for lp, entry, lb, pt in walk._iter_tree_leaves(root, bb, lmr, ()):
                if (entry.dsa, entry.size) in seen:
                    continue  # divided-parcel slots share frames
                seen.add((entry.dsa, entry.size))
                moff = volume.getsector(entry.dsa, ssz, lsz)
                fh.seek(moff)
                data = fh.read(entry.size * lsz)
                # 2-13: the real coordinate frame (walk._leaf_frame), not the
                # leaf slot bbox -- an L0 sparse leaf's frame is the 4x4 tile
                # (range 16384; DESIGN Decisions, Amendment 2026-09-23 design
                # agent). Feed the SAME frame to decode_parcel's MeshLocation
                # and to WalkedParcel.frame_bounds: xy_to_latlon (decode) and
                # parcel_measure's _raw() (invert) must round-trip through
                # one bbox, or criterion 1's maxima move for no reason.
                frame_bounds, frame_class = walk._leaf_frame(
                    root, level, pt, lp, lb, bb, lmr, sparse_cache)
                frame_range = walk.leaf_frame_range(level, pt, lp, frame_class)
                try:
                    loc = MeshLocation(level=level, parcel_type=pt, blockset_index=bsi,
                                       block_index=bidx, parcel_index=lp[-1],
                                       bounds=walk.with_range(frame_bounds, frame_range),
                                       sector_addr=entry.dsa, size_logical_sectors=entry.size)
                    parcel = decode_parcel(loc, data, n_basic_map=lmr.n_basic_map,
                                           n_ext_map=lmr.n_ext_map)
                except Exception:  # noqa: BLE001
                    continue
                wp = walk.WalkedParcel(level=level, blockset_index=bsi, block_index=bidx,
                                       parcel_type=pt, leaf_path=lp, bounds=lb,
                                       file_offset=moff, length=len(data), parcel=parcel,
                                       error=None, frame_bounds=frame_bounds,
                                       frame_range=frame_range, frame_class=frame_class)
                m = parcel_measure(wp)
                if m is None:
                    continue
                r = _record(wp, m)
                r["bx"], r["by"], r["bsx"], r["bsy"] = blx, bly, bsx, bsy
                r["hdr"] = [int.from_bytes(parcel.frame.header.raw_bytes[i:i + 2], "little")
                            for i in range(0, 36, 2)]
                out.append(r)
    return out


def collect(path: str, workers: int) -> list[dict]:
    keys = [(b.level, b.blockset_index, b.block_index, b.bsx, b.bsy, b.blx, b.bly,
             b.file_offset, b.length) for b in walk.iter_blocks(path) if b.error is None]
    chunks = [keys[i::workers * 8] for i in range(workers * 8)]
    recs = []
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(_work, [(path, c) for c in chunks if c]):
            recs.extend(r)
    recs.sort(key=lambda r: (r["level"], r["bs"], r["blk"], r["path"]))
    return recs


def bucket(m: int) -> int:
    """Smallest power-of-two range holding max m (coords 0..R inclusive)."""
    r = 1024
    while r < m:
        r *= 2
    return r


def aggregate(recs: list[dict], urban_tiles) -> dict:
    groups: dict = {}
    for r in recs:
        cls = parcel_class(r["level"], r["div"], _grid(r), urban_tiles)
        groups.setdefault((r["level"], cls, _div_key(r)), []).append(r)
    ranges: dict = {}
    for (lvl, cls, div), rs in sorted(groups.items()):
        bk = Counter(bucket(r["max"]) for r in rs)
        mode, cnt = sorted(bk.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        exc = [r for r in rs if bucket(r["max"]) != mode]
        ranges.setdefault(str(lvl), {}).setdefault(cls, {})[div] = {
            "max": mode, "share_at_max": round(cnt / len(rs), 6), "n": len(rs),
            "observed_peak": max(r["max"] for r in rs),
            "exceeds_max": sum(1 for r in rs if r["max"] > mode),
            "exceptions": {"count": len(exc),
                           "examples": [{"bs": r["bs"], "blk": r["blk"],
                                         "parcel": r["path"], "max": r["max"]}
                                        for r in exc[:EXCEPTION_EXAMPLES]]},
        }
    return ranges


def validate(recs: list[dict], urban_tiles) -> dict:
    """Rule accuracy against R's own declaration of the L0 class (header
    word 6: 224 = urban, 13216 = sparse; used as a label only, never by the
    rule) and the observed-peak consistency of every class."""
    l0 = [r for r in recs if r["level"] == 0 and r["div"] == 0]
    ok = sum(1 for r in l0 if (parcel_class(0, 0, _grid(r), urban_tiles) == "urban")
             == (r["hdr"][6] == 224))
    anchor_only = sum(1 for r in l0 if (((r["path"][0] % L0_GRID_W) % L0_TILE > 0
                                         or (r["path"][0] // L0_GRID_W) % L0_TILE > 0)
                                        == (r["hdr"][6] == 224)))
    return {"l0_normal_parcels": len(l0), "rule_correct": ok,
            "rule_accuracy": round(ok / len(l0), 6),
            "offset_only_rule_accuracy": round(anchor_only / len(l0), 6),
            "label": "R Map Frame header word 6 (224 urban, 13216 sparse)"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dump", help="also write per-parcel records (jsonl) here")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args()
    t0 = time.time()
    recs = collect(str(Path(args.reference) / "ALLDATA.KWI"), args.workers)
    print(f"walked {len(recs)} parcels in {time.time() - t0:.0f}s", file=sys.stderr)
    urban = derive_urban_tiles(recs)
    v = validate(recs, urban)
    out = {
        "class_rule": {
            "description": ("class = f(level, division, grid) only, no content. "
                            "division != 0 -> 'divided'; level != 0 -> 'full'; level 0 -> "
                            "'urban' if the leaf's 4x4 tile is in urban_tiles else 'sparse'. "
                            "Leaf index i in a block: x = i % 32, y = i // 32, "
                            "tile = (y // 4, x // 4). Division state = 'normal' or "
                            "'pardiv<parcel_type>_sub<leaf index within the divided parcel>'."),
            "l0_grid_width": L0_GRID_W, "l0_tile": L0_TILE,
            "urban_tiles_key": ["blockset_index", "block_index", "tile_y", "tile_x"],
            "urban_tiles": sorted(list(t) for t in urban),
            "validation": v,
        },
        "ranges": aggregate(recs, urban),
    }
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(v), file=sys.stderr)
    if args.dump:
        with open(args.dump, "w") as f:
            for r in recs:
                f.write(json.dumps(r, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
