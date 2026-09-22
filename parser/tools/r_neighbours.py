#!/usr/bin/env python3
"""R leaf-neighbour lookup (Plan 03 unit 2-09): given one decoded leaf slot,
find the leaf slot on the other side of one of its four edges, whether that
neighbour sits in the same block, a different block of the same blockset, or
a different blockset entirely.

Built for 2-10 (cross-parcel continuity) and 2-11 (boundary-node mirror),
both of which need this because DESIGN Decisions, Amendment 2026-09-23
(user), Phase 2 criterion 4 states the mirror invariant was tested only on
same-block neighbours and "block- and blockset-crossing neighbour lookup
must exist before it is load-bearing."

Leaf slots at one level lie on a single **global** integer leaf grid:
`(gx, gy) = (base_ix + leaf_x, base_iy + leaf_y)` where `base_ix`/`base_iy`
come from `harness.walk._block_base_bounds`'s own formula
(`base_ix = (bsx * nbl_lng + blx) * npc_lng`, `base_iy` symmetric on lat).
Adjacency is therefore integer arithmetic on that grid (this module's job),
not float bbox comparison (this module's *verification* of that arithmetic,
via `_slot_bounds`, reusing `walk._narrow_bounds`).

Reads R only through `harness.walk` reading paths and `overlay_test.RReader`
(reused unmodified); imports no writer module. y increases northward
(coordconv, 2-06), so edge "N" is +gy and "S" is -gy.

Edge-sharing tolerance: `EDGE_TOL_REL` = 1e-6, relative to the leaf's own
span on the compared axis. `header_word_census.divided_adjacency_census`
uses an absolute `eps = 1e-9` degrees for its bbox-touches predicate; here
the two bboxes being compared are computed independently (source leaf's own
narrow_bounds vs a fresh narrow_bounds computed from the target block), so a
tolerance relative to the leaf span is more robust to the very different
absolute leaf sizes across levels (L0 leaves are ~1/32 of a block; L12
leaves are much larger).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from harness import walk  # noqa: E402
import overlay_test as ot  # noqa: E402

EDGE_TOL_REL = 1e-6
EDGE_DELTA = {"W": (-1, 0), "E": (1, 0), "S": (0, -1), "N": (0, 1)}
LEAF_CACHE_SIZE = 64  # bounded LRU of decoded-block leaf lists (L0 has ~1,836
                       # non-empty blocks; the index must not hold them all).
SAMPLE_LEVELS = {0, 2, 4}
SAMPLE_BLOCKS = 40  # stated block count for the L0/L2/L4 sample (see main())


def global_leaf_xy(lmr, bsx: int, bsy: int, blx: int, bly: int, leaf_index: int):
    """(gx, gy) of top-level leaf `leaf_index` of block (bsx,bsy,blx,bly) on
    the level's global leaf grid, using `walk._block_base_bounds`'s own
    formula (npc_* at parcel_type 0, since that is the top-level grid)."""
    gn_lng = 1 + lmr.n_parcels_lng[0]
    gn_lat = 1 + lmr.n_parcels_lat[0]
    nbl_lng = 1 + lmr.n_blocks_lng
    nbl_lat = 1 + lmr.n_blocks_lat
    leaf_x, leaf_y = leaf_index % gn_lng, leaf_index // gn_lng
    base_ix = (bsx * nbl_lng + blx) * gn_lng
    base_iy = (bsy * nbl_lat + bly) * gn_lat
    return base_ix + leaf_x, base_iy + leaf_y


def grid_dims(lmr):
    """(nx, ny): the level's global leaf grid extent, from the LMR fields
    `walk`/`volume` already derive it from (same identity as `lmr.grid_nx`/
    `lmr.grid_ny`, restated here as the lookup's own contract)."""
    return lmr.grid_nx, lmr.grid_ny


@dataclass
class Neighbour:
    status: str  # "resolved" | "outside_coverage" | "empty_slot"
    handles: list = field(default_factory=list)  # [(lmr, blk, leaf_row), ...]
    divided: bool = False
    crossing: Optional[str] = None  # "same_block" | "cross_block" | "cross_blockset"
    gx: int = 0
    gy: int = 0


class LeafIndex:
    """Built once per level over `rdr.blocks(level)`: an O(1) map from a
    block's (bsx, bsy, blx, bly) address to its `blk` handle. `get(gx, gy)`
    locates the covering block by pure grid arithmetic (no decode), then
    reads -- and caches, bounded by `LEAF_CACHE_SIZE`, evicted LRU -- that
    one block's leaf list via `rdr.leaves()` on demand. It stores block
    handles and (transiently, bounded) leaf-list rows, never decoded
    parcels: `rdr.leaves()` computes geometry only, it does not call
    `decode_parcel`.
    """

    def __init__(self, rdr: "ot.RReader", level: int):
        self.rdr = rdr
        self.lmr, blks = rdr.blocks(level)
        self.nx, self.ny = grid_dims(self.lmr)
        self.gn_lng = 1 + self.lmr.n_parcels_lng[0]
        self.gn_lat = 1 + self.lmr.n_parcels_lat[0]
        self.nbl_lng = 1 + self.lmr.n_blocks_lng
        self.nbl_lat = 1 + self.lmr.n_blocks_lat
        self.nbs_lng = 1 + self.lmr.n_blocksets_lng
        self.nbs_lat = 1 + self.lmr.n_blocksets_lat
        self.blocks: dict = {}
        for blk in blks:
            key = self._block_key(blk)
            self.blocks[key] = blk
        self._leaf_cache: "OrderedDict" = OrderedDict()

    def _block_key(self, blk):
        _, bs_index, ei, _, _ = blk
        bsy, bsx = divmod(bs_index, self.nbs_lng)
        bly, blx = divmod(ei, self.nbl_lng)
        return (bsx, bsy, blx, bly)

    def _addr(self, gx: int, gy: int):
        """((bsx,bsy,blx,bly), leaf_index) covering (gx, gy) -- valid grid
        arithmetic even when the coordinate is off-grid or the block does
        not exist; callers guard those cases separately."""
        colidx, leaf_x = divmod(gx, self.gn_lng)
        rowidx, leaf_y = divmod(gy, self.gn_lat)
        bsx, blx = divmod(colidx, self.nbl_lng)
        bsy, bly = divmod(rowidx, self.nbl_lat)
        leaf_index = leaf_y * self.gn_lng + leaf_x
        return (bsx, bsy, blx, bly), leaf_index

    def leaves(self, key):
        """Leaf rows of the block at `key` (as `rdr.leaves()` returns them),
        via a bounded LRU cache keyed by block address."""
        if key in self._leaf_cache:
            self._leaf_cache.move_to_end(key)
            return self._leaf_cache[key]
        rows = self.rdr.leaves(self.lmr, self.blocks[key])
        self._leaf_cache[key] = rows
        self._leaf_cache.move_to_end(key)
        if len(self._leaf_cache) > LEAF_CACHE_SIZE:
            self._leaf_cache.popitem(last=False)
        return rows

    def slot_bounds(self, key, leaf_index: int):
        """The top-level leaf *slot*'s bbox (not a divided sub-leaf's),
        independent of `leaves()`/the cache: narrowed straight from the
        block's own bbox, the same arithmetic `RReader.leaves` uses before
        it recurses into a divided parcel."""
        blk = self.blocks[key]
        bb = blk[4]
        return walk._narrow_bounds(bb, self.gn_lat, self.gn_lng, leaf_index)

    def get(self, gx: int, gy: int) -> Neighbour:
        if gx < 0 or gy < 0 or gx >= self.nx or gy >= self.ny:
            return Neighbour(status="outside_coverage", gx=gx, gy=gy)
        key, leaf_index = self._addr(gx, gy)
        if key not in self.blocks:
            return Neighbour(status="outside_coverage", gx=gx, gy=gy)
        rows = self.leaves(key)
        matched = [r for r in rows if r[0][0] == leaf_index]
        if not matched:
            return Neighbour(status="empty_slot", gx=gx, gy=gy)
        matched.sort(key=lambda r: r[0])
        divided = any(len(r[0]) > 1 for r in matched)
        handles = [(self.lmr, self.blocks[key], r) for r in matched]
        return Neighbour(status="resolved", handles=handles, divided=divided,
                          gx=gx, gy=gy)

    def neighbour(self, handle, edge: str) -> Neighbour:
        """The `Neighbour` across `edge` ("W"/"E"/"S"/"N") of `handle`'s leaf
        slot. `handle` is a `(lmr, blk, leaf_row)` triple, e.g. one element
        of another `Neighbour.handles`."""
        lmr, blk, leaf_row = handle
        src_key = self._block_key(blk)
        leaf_index = leaf_row[0][0]
        gx, gy = global_leaf_xy(lmr, *src_key, leaf_index)
        dx, dy = EDGE_DELTA[edge]
        target = self.get(gx + dx, gy + dy)
        tgt_key, _ = self._addr(target.gx, target.gy)
        if tgt_key == src_key:
            crossing = "same_block"
        elif tgt_key[0] == src_key[0] and tgt_key[1] == src_key[1]:
            crossing = "cross_block"
        else:
            crossing = "cross_blockset"
        target.crossing = crossing
        return target


def verify_edge(idx: LeafIndex, handle, edge: str, neighbour: Neighbour):
    """Assert the source leaf slot's bbox and the resolved target's bbox
    share the crossed edge, within `EDGE_TOL_REL` of the leaf span. Returns
    (ok, detail) -- `detail` is populated only on failure, with the ids and
    numbers a finding needs."""
    lmr, blk, leaf_row = handle
    src_key = idx._block_key(blk)
    leaf_index = leaf_row[0][0]
    src = idx.slot_bounds(src_key, leaf_index)
    tgt_key, tgt_leaf_index = idx._addr(neighbour.gx, neighbour.gy)
    tgt = idx.slot_bounds(tgt_key, tgt_leaf_index)

    if edge in ("E", "W"):
        span = src.lon_hi - src.lon_lo
        tol = abs(span) * EDGE_TOL_REL
        a, b = (src.lon_hi, tgt.lon_lo) if edge == "E" else (src.lon_lo, tgt.lon_hi)
        ok = abs(a - b) <= tol
        lat_ok = (abs(src.lat_lo - tgt.lat_lo) <= abs(src.lat_hi - src.lat_lo) * EDGE_TOL_REL
                  and abs(src.lat_hi - tgt.lat_hi) <= abs(src.lat_hi - src.lat_lo) * EDGE_TOL_REL)
        ok = ok and lat_ok
    else:
        span = src.lat_hi - src.lat_lo
        tol = abs(span) * EDGE_TOL_REL
        a, b = (src.lat_hi, tgt.lat_lo) if edge == "N" else (src.lat_lo, tgt.lat_hi)
        ok = abs(a - b) <= tol
        lon_ok = (abs(src.lon_lo - tgt.lon_lo) <= abs(src.lon_hi - src.lon_lo) * EDGE_TOL_REL
                  and abs(src.lon_hi - tgt.lon_hi) <= abs(src.lon_hi - src.lon_lo) * EDGE_TOL_REL)
        ok = ok and lon_ok

    if ok:
        return True, None
    return False, {
        "edge": edge, "src_key": list(src_key), "src_leaf_index": leaf_index,
        "tgt_key": list(tgt_key), "tgt_leaf_index": tgt_leaf_index,
        "src_bounds": [src.lat_lo, src.lat_hi, src.lon_lo, src.lon_hi],
        "tgt_bounds": [tgt.lat_lo, tgt.lat_hi, tgt.lon_lo, tgt.lon_hi],
    }


def _top_level_groups(rows):
    """`rows` (as `rdr.leaves()`/`LeafIndex.leaves()` return them) grouped
    by top-level leaf index, one representative row per group (any sub-leaf
    row identifies the same top-level slot -- `neighbour()` only reads
    `leaf_row[0][0]`)."""
    groups: "OrderedDict" = OrderedDict()
    for row in rows:
        groups.setdefault(row[0][0], row)
    return groups


def census_level(rdr: "ot.RReader", level: int):
    idx = LeafIndex(rdr, level)
    keys = list(idx.blocks.keys())
    if level in SAMPLE_LEVELS:
        chosen = ot.spread([(k, idx.blocks[k]) for k in keys], SAMPLE_BLOCKS)[:SAMPLE_BLOCKS]
        chosen_keys = [k for k, _ in chosen]
        sample_rule = (f"spread({SAMPLE_BLOCKS} of {len(keys)} blocks, on-disc "
                        "order, overlay_test.spread), every leaf of each")
    else:
        chosen_keys = keys
        sample_rule = f"full population ({len(keys)} blocks)"

    status_counts: Counter = Counter()
    crossing_counts: Counter = Counter()
    divided_resolved = 0
    assert_pass = 0
    assert_fail = 0
    failures = []
    leaves_visited = 0

    for key in chosen_keys:
        rows = idx.leaves(key)
        groups = _top_level_groups(rows)
        for leaf_index, row in groups.items():
            leaves_visited += 1
            handle = (idx.lmr, idx.blocks[key], row)
            for edge in ("W", "E", "S", "N"):
                nb = idx.neighbour(handle, edge)
                status_counts[nb.status] += 1
                crossing_counts[nb.crossing] += 1
                if nb.status == "resolved":
                    if nb.divided:
                        divided_resolved += 1
                    ok, detail = verify_edge(idx, handle, edge, nb)
                    if ok:
                        assert_pass += 1
                    else:
                        assert_fail += 1
                        if len(failures) < 20:
                            failures.append(detail)

    return {
        "level": level,
        "sample_rule": sample_rule,
        "blocks_visited": len(chosen_keys),
        "leaves_visited": leaves_visited,
        "neighbours_checked": leaves_visited * 4,
        "status_counts": dict(sorted(status_counts.items())),
        "crossing_counts": {str(k): v for k, v in sorted(
            crossing_counts.items(), key=lambda kv: str(kv[0]))},
        "divided_resolved_count": divided_resolved,
        "edge_assertions": {"passed": assert_pass, "failed": assert_fail,
                             "failures": failures},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--levels", default="0,2,4,6,8")
    args = ap.parse_args(argv)

    levels = [int(x) for x in args.levels.split(",") if x != ""]
    rdr = ot.RReader(args.reference)
    results = [census_level(rdr, lv) for lv in levels]

    out = {
        "tool": "r_neighbours",
        "reference": args.reference,
        "edge_tol_rel": EDGE_TOL_REL,
        "leaf_cache_size": LEAF_CACHE_SIZE,
        "sample_blocks": SAMPLE_BLOCKS,
        "sample_levels": sorted(SAMPLE_LEVELS),
        "notes": {
            "l0_is_per_leaf_slot": (
                "L0 figures below are per top-level leaf slot on the global "
                "leaf grid, not per L0-sparse-tile frame (a sparse tile "
                "aliases 16 leaf slots to one Map Frame; each slot is "
                "still counted and looked up independently here)."),
        },
        "levels": results,
    }
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    Path(args.out).write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"wrote {args.out} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
