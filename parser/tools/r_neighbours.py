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

2-13 adds frame adjacency (DESIGN Decisions, "Amendment 2026-09-23 (design
agent) -- the adjacency unit is the frame, not the leaf slot"): the above
leaf-slot API steps one top-level leaf slot, which is one coordinate frame
for every class except L0 sparse, where 16 leaf slots alias ONE 4x4-tile
frame -- a one-slot step self-neighbours 12 of those 16 slots. The fix is
not a special case; it is one global raw lattice per level, pre-stated
here and not tuned:

* `RAW_PER_SLOT = 4096` -- raw units per top-level leaf slot, at every
  level (spec 7.2.2.1.1.2: a basic parcel is 4096 x 4096, an integrated
  parcel up to 4096 x 8 = 32768 -- a whole multiple of the basic parcel,
  because the raw unit is the same size at both).
* A coordinate frame's extent in slots is `n = range // RAW_PER_SLOT`,
  `range` read from `coord_scale.json`'s `ranges` via
  `overlay_test.class_range` -- never inferred from observed data. n = 1
  for a basic parcel (L0 urban, an L2-L8 leaf, a divided parent), n = 4
  for an L0 sparse integrated-parcel tile.
* A frame is identified by its south-west leaf slot `(gx0, gy0)` on the
  global leaf grid plus `n` (`FrameId`). Lattice comparison is exact
  integer equality: no tolerance, no epsilon.
* Global raw coordinate: `X = gx0*RAW_PER_SLOT + x_local`, `Y =
  gy0*RAW_PER_SLOT + y_local` (`to_global`/`to_frame_local` -- the only
  place this arithmetic lives).

These constants are pre-stated, not tuned: none is changed after seeing a
result. `frame_neighbour`/`corner_frames` add frame-level adjacency
alongside the leaf-slot API without changing that API's behaviour or
signature -- 2-09's leaf-slot semantics are correct for what they say; the
gap was callers using them as frame adjacency.
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

# Pre-stated, not tuned (module docstring, "2-13 adds frame adjacency"):
RAW_PER_SLOT = 4096  # raw units per top-level leaf slot, at every level.

_COORD_SCALE_PATH = ROOT / "refdata" / "profile" / "coord_scale.json"


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


# ---------------------------------------------------------------------
# Frame adjacency (2-13): the adjacency unit is the coordinate frame, not
# the leaf slot. See the module docstring for the pre-stated constants and
# the global-lattice rule this implements.
# ---------------------------------------------------------------------

def _load_coord_scale() -> tuple[dict, dict]:
    """(ranges, class_rule) from `coord_scale.json`, read fresh each call
    (this module is a one-shot CLI/test-imported library, not a long-lived
    service, so no cache is kept)."""
    data = json.loads(_COORD_SCALE_PATH.read_text())
    return data["ranges"], data["class_rule"]


def frame_extent_slots(ranges: dict, level: int, cls: str) -> int:
    """n: leaf slots per axis a coordinate frame of class `cls` covers.
    `range` comes from `coord_scale.json`'s `ranges` via
    `overlay_test.class_range`; `n = range // RAW_PER_SLOT` (Contract:
    "never inferred from observed data"). `cls` is one of the two frame
    classes this module ever asks for: "L0_sparse" (16384 -> 4) or a
    basic-parcel class such as "L0_urban"/"L2"/"L6" (4096 -> 1)."""
    rng = ot.class_range(ranges, level, cls)
    n, rem = divmod(rng, RAW_PER_SLOT)
    if rem:
        raise ValueError(
            f"class_range {rng} for level={level} cls={cls!r} is not a "
            f"whole multiple of RAW_PER_SLOT={RAW_PER_SLOT}")
    return n


@dataclass(frozen=True)
class FrameId:
    """A coordinate frame's identity: the (gx0, gy0) leaf slot at its
    south-west corner on the level's global leaf grid, plus its extent
    `n` in slots per axis. Two frames are the same frame iff all three
    fields are equal (exact integer equality, no tolerance)."""
    gx0: int
    gy0: int
    n: int


@dataclass
class FrameNeighbour:
    status: str  # "resolved" | "outside_coverage" | "empty_slot"
    frames: list = field(default_factory=list)      # [FrameId, ...], deduped
    handles: list = field(default_factory=list)     # [[(lmr,blk,leaf_row),...], ...] parallel to frames
    crossings: list = field(default_factory=list)   # ["same_block"|"cross_block"|"cross_blockset", ...] parallel to frames
    tile_agrees: bool = True  # False if any frame's tile classification
                               # disagreed with coord_scale.json (needs context)


def frame_of(idx: LeafIndex, handle, class_rule: dict, ranges: dict) -> tuple[FrameId, bool]:
    """(FrameId, tile_agrees) for the top-level leaf slot named by
    `handle` ((lmr, blk, leaf_row), as `LeafIndex.get`/`neighbour` return
    them). `frame_class` ("l0_sparse_tile" or "leaf") comes from
    `leaf_row[5]`, the `walk._leaf_frame` tuple `RReader.leaves()`
    already attaches to every row -- the tile machinery the Contract
    names (`L0_TILE`, `_is_sparse_tile`, `_tile_bounds`), not a new
    independent derivation. `tile_agrees` cross-checks that
    classification against `coord_scale.json`'s `class_rule.urban_tiles`
    (via `overlay_test._class_key`, forced to ptype 0 -- urban/sparse is
    a property of the top-level tile, not of a particular division
    state): False means the two disagree on this tile, which the
    Contract says is a `needs context` report, not a silent pick."""
    lmr, blk, leaf_row = handle
    src_key = idx._block_key(blk)
    leaf_index = leaf_row[0][0]
    gx, gy = global_leaf_xy(lmr, *src_key, leaf_index)
    frame_info = leaf_row[5] if len(leaf_row) > 5 else None
    frame_class = frame_info[1] if frame_info is not None else "leaf"
    is_sparse = frame_class == "l0_sparse_tile"
    agrees = True
    if lmr.level == 0:
        agrees = (ot._class_key(0, 0, class_rule, blk, (leaf_index,)) == "L0_sparse") == is_sparse
    if is_sparse:
        n = frame_extent_slots(ranges, lmr.level, "L0_sparse")
        gx0, gy0 = gx - gx % walk.L0_TILE, gy - gy % walk.L0_TILE
    else:
        cls = "L0_urban" if lmr.level == 0 else f"L{lmr.level}"
        n = frame_extent_slots(ranges, lmr.level, cls)
        gx0, gy0 = gx, gy
    return FrameId(gx0=gx0, gy0=gy0, n=n), agrees


def _frame_crossing(idx: LeafIndex, src: FrameId, tgt: FrameId) -> str:
    src_key, _ = idx._addr(src.gx0, src.gy0)
    tgt_key, _ = idx._addr(tgt.gx0, tgt.gy0)
    if tgt_key == src_key:
        return "same_block"
    if tgt_key[0] == src_key[0] and tgt_key[1] == src_key[1]:
        return "cross_block"
    return "cross_blockset"


def _frames_at_slots(idx: LeafIndex, slots, class_rule: dict, ranges: dict):
    """Resolve every (gx, gy) in `slots` via `idx.get`, and dedupe the
    frames found at any resolved slot by `FrameId`, first-seen order.
    Returns (frame_statuses, frames, handles_per_frame, tile_agrees)."""
    seen: "OrderedDict" = OrderedDict()
    statuses = []
    agrees = True
    for gx, gy in slots:
        nb = idx.get(gx, gy)
        statuses.append(nb.status)
        if nb.status != "resolved":
            continue
        for h in nb.handles:
            fid, ok = frame_of(idx, h, class_rule, ranges)
            agrees = agrees and ok
            seen.setdefault(fid, []).append(h)
    return statuses, list(seen.keys()), list(seen.values()), agrees


def frame_neighbour(idx: LeafIndex, frame: FrameId, edge: str,
                     class_rule: dict, ranges: dict) -> FrameNeighbour:
    """The frame(s) across `edge` ("W"/"E"/"S"/"N") of `frame`, stepping
    by `frame.n` slots -- never one, so the source frame is never
    returned as its own neighbour (Contract). A frame's edge can face
    more than one frame of a different size (an L0 urban n=1 frame can
    sit beside an L0 sparse n=4 tile, and vice versa), so every one of
    the `frame.n` slots immediately across the edge is resolved and the
    distinct frames found there are all returned, deduped, in
    first-seen order, each with its own `same_block`/`cross_block`/
    `cross_blockset` crossing relative to `frame`."""
    dx, dy = EDGE_DELTA[edge]
    tx, ty = frame.gx0 + dx * frame.n, frame.gy0 + dy * frame.n
    if edge in ("W", "E"):
        slots = [(tx, frame.gy0 + i) for i in range(frame.n)]
    else:
        slots = [(frame.gx0 + i, ty) for i in range(frame.n)]
    statuses, frames, handles, agrees = _frames_at_slots(idx, slots, class_rule, ranges)
    if frames:
        status = "resolved"
    elif "empty_slot" in statuses:
        status = "empty_slot"
    else:
        status = "outside_coverage"
    crossings = [_frame_crossing(idx, frame, f) for f in frames]
    return FrameNeighbour(status=status, frames=frames, handles=handles,
                           crossings=crossings, tile_agrees=agrees)


def corner_frames(idx: LeafIndex, frame: FrameId, corner: str,
                   class_rule: dict, ranges: dict) -> FrameNeighbour:
    """All frames -- other than `frame` itself -- sharing the lattice
    point at `frame`'s `corner` ("SW"|"SE"|"NW"|"NE"). Spec 7.2.2.1.1.3
    (the on-boundary node flag): identical node information is held in
    neighbouring PARCELS, plural -- a corner lattice point is shared by
    up to three other frames, not one nominated edge neighbour. The four
    leaf slots whose corners meet at that lattice point are resolved and
    every distinct frame found there except `frame` is returned."""
    px = frame.gx0 if corner in ("SW", "NW") else frame.gx0 + frame.n
    py = frame.gy0 if corner in ("SW", "SE") else frame.gy0 + frame.n
    slots = [(px - 1, py - 1), (px, py - 1), (px - 1, py), (px, py)]
    statuses, frames, handles, agrees = _frames_at_slots(idx, slots, class_rule, ranges)
    others = [(f, h) for f, h in zip(frames, handles) if f != frame]
    out_frames = [f for f, _ in others]
    out_handles = [h for _, h in others]
    if out_frames:
        status = "resolved"
    elif "empty_slot" in statuses:
        status = "empty_slot"
    else:
        status = "outside_coverage"
    crossings = [_frame_crossing(idx, frame, f) for f in out_frames]
    return FrameNeighbour(status=status, frames=out_frames, handles=out_handles,
                           crossings=crossings, tile_agrees=agrees)


def to_global(frame: FrameId, x_local: int, y_local: int) -> tuple[int, int]:
    """Frame-local raw (x, y) -> this level's global raw lattice (X, Y):
    `X = gx0*RAW_PER_SLOT + x_local`, `Y = gy0*RAW_PER_SLOT + y_local`
    (Contract). The only place this arithmetic lives -- callers use this
    and `to_frame_local`, never `gx0 * 4096` themselves."""
    return frame.gx0 * RAW_PER_SLOT + x_local, frame.gy0 * RAW_PER_SLOT + y_local


def to_frame_local(frame: FrameId, gx_raw: int, gy_raw: int) -> tuple[int, int]:
    """Inverse of `to_global`: a global raw lattice (X, Y) -> `frame`'s
    local raw (x, y)."""
    return gx_raw - frame.gx0 * RAW_PER_SLOT, gy_raw - frame.gy0 * RAW_PER_SLOT


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


def census_level(rdr: "ot.RReader", level: int, class_rule: dict, ranges: dict):
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

    # Frame-level adjacency (2-13): one frame per distinct FrameId, so an
    # L0 sparse tile's 16 aliased leaf slots contribute one frame-edge
    # query per edge, not 16.
    frame_status_counts: Counter = Counter()
    frame_crossing_counts: Counter = Counter()
    tile_disagreements = 0
    seen_frames: set = set()
    frames_visited = 0

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

            fid, agrees = frame_of(idx, handle, class_rule, ranges)
            if not agrees:
                tile_disagreements += 1
            if fid not in seen_frames:
                seen_frames.add(fid)
                frames_visited += 1
                for edge in ("W", "E", "S", "N"):
                    fnb = frame_neighbour(idx, fid, edge, class_rule, ranges)
                    frame_status_counts[fnb.status] += 1
                    for c in fnb.crossings:
                        frame_crossing_counts[c] += 1
                    if not fnb.tile_agrees:
                        tile_disagreements += 1

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
        "frames_visited": frames_visited,
        "frame_edges_checked": frames_visited * 4,
        "frame_status_counts": dict(sorted(frame_status_counts.items())),
        "frame_crossing_counts": {str(k): v for k, v in sorted(
            frame_crossing_counts.items(), key=lambda kv: str(kv[0]))},
        "frame_tile_disagreements": tile_disagreements,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--levels", default="0,2,4,6,8")
    args = ap.parse_args(argv)

    levels = [int(x) for x in args.levels.split(",") if x != ""]
    rdr = ot.RReader(args.reference)
    ranges, class_rule = _load_coord_scale()
    results = [census_level(rdr, lv, class_rule, ranges) for lv in levels]

    out = {
        "tool": "r_neighbours",
        "reference": args.reference,
        "edge_tol_rel": EDGE_TOL_REL,
        "leaf_cache_size": LEAF_CACHE_SIZE,
        "sample_blocks": SAMPLE_BLOCKS,
        "sample_levels": sorted(SAMPLE_LEVELS),
        "raw_per_slot": RAW_PER_SLOT,
        "notes": {
            "l0_is_per_leaf_slot": (
                "status_counts/crossing_counts/edge_assertions above are "
                "per top-level leaf SLOT on the global leaf grid, not per "
                "L0-sparse-tile FRAME: a sparse tile aliases 16 leaf slots "
                "to one Map Frame, and each slot is still counted and "
                "looked up independently there, so a leaf-slot 'neighbour' "
                "can be the source parcel itself (2-13, DESIGN Decisions, "
                "Amendment 2026-09-23 design agent). Frame-level adjacency "
                "is now available in this module (FrameId, frame_of, "
                "frame_neighbour, corner_frames, to_global/to_frame_local) "
                "-- see frame_status_counts/frame_crossing_counts below, "
                "one entry per distinct frame -- and mirror/continuity "
                "callers (2-14 on) must use it, not leaf-slot neighbour(), "
                "for anything that can cross an L0 sparse tile edge."),
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
