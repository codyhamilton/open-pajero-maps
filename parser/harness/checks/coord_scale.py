"""`coord_scale` check: zero parcels exceeding their class range.

DESIGN.md (plan 03), "Phase 3 -- Outcome, as amended": the criterion is
**zero parcels exceeding their class range** -- an inequality with zero as
its threshold. It is *not* "maxima equal coord_scale.json": a sparse cell
legitimately never reaches its maximum. The observed per-class maxima are
reported as details (informative only); the verdict depends solely on the
exceedance count.

Each walked parcel's range is `coordconv.range_for` of its frame, obtained
through `walk.leaf_frame_range` (the same call `iter_parcels` decodes with);
a divided sub-parcel's frame is its parent slot, so it is judged at 4096.
A vertex is legal in `[0, range]` **inclusive** -- a value of exactly
`range` is what R's `share_at_max = 1.0` records.

Vertices judged: every road node (raw x/y as stored), every road
intermediate point and every background shape vertex (lat/lon inverted at
the range the decoder used) -- the same vertex set `coord_scale.json` was
censused over (`parser/tools/coord_scale_census.py`). Name anchors are not
part of that census and are not judged here. A Map Frame aliased by several
slots (an L0 sparse tile, divided-parcel slots) is judged once, keyed by
its (file offset, length).

Two entry points share one accumulator (`_accumulate`/`_finalize`):
`judge()` folds a plain iterable of `WalkedParcel`s single-process (the
unit tests' path, and `--workers 1`); `_run_coord_scale` -- at `workers >
1` -- partitions `walk.iter_blocks`' blocks across a process pool (`_work`,
one process-pool worker per shard of blocks, following
`coord_scale_census.py`'s own `collect()`/`_work` split), has each worker
fold its own shard into a local accumulator with the same `_accumulate`,
and merges the shards (`_merge`) before the same `_finalize` produces the
`CheckResult` -- so the verdict and every count are computed by the
identical per-parcel code at any worker count. See "3C-05, 2026-09-25"
below for a scope note on `parcel_extent`'s raw-value round trip.
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness import walk
from harness.context import Check, CheckResult
from kiwiw import volume
from kiwiw.model import MeshLocation
from kiwiw.parcel import decode_parcel
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record

EXAMPLES = 20


def class_key(wp) -> str:
    """`<level>/<class>/<division_state>` -- coord_scale.json's key path.
    Label only; the range itself comes from `walk.leaf_frame_range`."""
    if wp.parcel_type:
        cls = "divided"
        div = f"pardiv{wp.parcel_type}_sub{wp.leaf_path[-1]}"
    else:
        div = "normal"
        if wp.level != 0:
            cls = "full"
        else:
            cls = "sparse" if wp.frame_class == "l0_sparse_tile" else "urban"
    return f"{wp.level}/{cls}/{div}"


def _inv(v: float, lo: float, hi: float, rng: int) -> int:
    return int(round((v - lo) / (hi - lo) * rng))


def parcel_extent(wp):
    """(min raw, max raw, vertex count) over the parcel's judged vertices,
    or None when it has none. Lat/lon are inverted with `wp.frame_bounds`
    at `wp.frame_range` -- the frame and range the decoder used."""
    p = wp.parcel
    if p is None:
        return None
    b, rng = wp.frame_bounds, wp.frame_range
    lo = hi = None
    n = 0

    def take(x: int, y: int) -> None:
        nonlocal lo, hi, n
        m, M = min(x, y), max(x, y)
        lo = m if lo is None or m < lo else lo
        hi = M if hi is None or M > hi else hi
        n += 1

    road = getattr(p, "road", None)
    if road is not None:
        for link in road.links:
            for nd in link.nodes:
                take(int(nd.x), int(nd.y))
            for lat, lon in (link.points or []):
                take(_inv(lon, b.lon_lo, b.lon_hi, rng), _inv(lat, b.lat_lo, b.lat_hi, rng))
    bg = getattr(p, "background", None)
    if bg is not None:
        for sh in bg.shapes:
            for lat, lon in sh.coords:
                take(_inv(lon, b.lon_lo, b.lon_hi, rng), _inv(lat, b.lat_lo, b.lat_hi, rng))
    return None if n == 0 else (lo, hi, n)


def _new_acc() -> dict:
    return {"seen": set(), "per_class": {}, "exceed": 0, "unranged": 0,
            "examples": [], "judged": 0}


def _accumulate(acc: dict, wp) -> None:
    """Fold one `WalkedParcel` into `acc`, mutated in place -- the single
    per-parcel rule both `judge()` (sequentially) and every parallel
    worker (locally, on its own block shard) apply; `_merge` below then
    combines shards so the result is identical at any worker count.
    `acc["examples"]` carries `(sort_key, example_dict)` pairs so a merge
    of several workers' local, insertion-ordered lists can still be
    reduced to one globally-ordered, EXAMPLES-capped list in `_finalize`."""
    if wp.error is not None or wp.parcel is None:
        return
    frame_key = (wp.file_offset, wp.length)
    if frame_key in acc["seen"]:
        return
    acc["seen"].add(frame_key)
    key = class_key(wp)
    rng = walk.leaf_frame_range(wp.level, wp.parcel_type, wp.leaf_path, wp.frame_class)
    ext = parcel_extent(wp) if rng is not None and wp.frame_range is not None else None
    sort_key = (wp.level, wp.blockset_index, wp.block_index, tuple(wp.leaf_path))
    if rng is None or wp.frame_range is None:
        acc["unranged"] += 1
        if len(acc["examples"]) < EXAMPLES:
            acc["examples"].append((sort_key, {
                "class": key, "reason": "no range_for triple",
                "level": wp.level, "bs": wp.blockset_index,
                "blk": wp.block_index, "path": list(wp.leaf_path)}))
        return
    if ext is None:
        return
    lo, hi, _ = ext
    acc["judged"] += 1
    c = acc["per_class"].setdefault(key, {"range": rng, "parcels": 0, "observed_max": 0,
                                          "observed_min": 0, "exceeding": 0})
    c["parcels"] += 1
    c["observed_max"] = max(c["observed_max"], hi)
    c["observed_min"] = min(c["observed_min"], lo)
    if lo < 0 or hi > rng:
        acc["exceed"] += 1
        c["exceeding"] += 1
        if len(acc["examples"]) < EXAMPLES:
            acc["examples"].append((sort_key, {
                "class": key, "range": rng, "min": lo, "max": hi,
                "level": wp.level, "bs": wp.blockset_index,
                "blk": wp.block_index, "path": list(wp.leaf_path)}))


def _merge(accs: list) -> dict:
    """Combine several `_accumulate`d shards (one per worker) into one,
    in a fixed order independent of shard count or arrival order: sums
    and min/max are commutative, and `examples` is globally sorted by its
    `sort_key` and capped in `_finalize`, not here."""
    merged = _new_acc()
    for acc in accs:
        merged["exceed"] += acc["exceed"]
        merged["unranged"] += acc["unranged"]
        merged["judged"] += acc["judged"]
        merged["examples"].extend(acc["examples"])
        for k, c in acc["per_class"].items():
            m = merged["per_class"].setdefault(k, {"range": c["range"], "parcels": 0,
                                                    "observed_max": 0, "observed_min": 0,
                                                    "exceeding": 0})
            m["parcels"] += c["parcels"]
            m["exceeding"] += c["exceeding"]
            m["observed_max"] = max(m["observed_max"], c["observed_max"])
            m["observed_min"] = min(m["observed_min"], c["observed_min"])
    return merged


def _finalize(acc: dict) -> CheckResult:
    exceed, unranged, judged = acc["exceed"], acc["unranged"], acc["judged"]
    per_class = acc["per_class"]
    examples = [e for _, e in sorted(acc["examples"], key=lambda t: t[0])[:EXAMPLES]]
    details = {
        "criterion": "zero parcels holding a vertex outside [0, range_for(frame)] inclusive",
        "parcels_judged": judged,
        "parcels_exceeding": exceed,
        "parcels_unranged": unranged,
        "per_class": {k: per_class[k] for k in sorted(per_class)},
        "examples": examples,
    }
    bad = exceed + unranged
    msg = (f"{exceed} of {judged} parcels exceed their class range"
           f"{f'; {unranged} with no range_for triple' if unranged else ''}"
           f" ({len(per_class)} classes observed)")
    return CheckResult("FAIL" if bad else "PASS", msg, details)


def judge(parcels) -> CheckResult:
    """Pure verdict over an iterable of `WalkedParcel`s (testable without a
    disc)."""
    acc = _new_acc()
    for wp in parcels:
        _accumulate(acc, wp)
    return _finalize(acc)


def _block_keys(path: str) -> list:
    """`(level, blockset_index, block_index, bsx, bsy, blx, bly,
    file_offset, length)` per non-empty block, from `walk.iter_blocks`
    (the block-enumeration entry point `walk` already exposes -- no
    leaf decode). Errored blocks are skipped, same as `iter_parcels`
    would report them as a block-level `WalkedParcel` error that
    `_accumulate` drops (`wp.error is not None`)."""
    return [(b.level, b.blockset_index, b.block_index, b.bsx, b.bsy, b.blx, b.bly,
             b.file_offset, b.length) for b in walk.iter_blocks(path) if b.error is None]


def _decode_block_parcels(path: str, container, keys: list):
    """Yield the decoded leaf `WalkedParcel`s of the given blocks only, in
    the same nested (block, leaf) order `iter_parcels` would produce for
    those blocks -- the per-block inner loop of `walk.iter_parcels`,
    restricted to `keys` since `walk` exposes no block-filtered entry
    point of its own (`walk.py` is not an owned path here; its
    already-public block/leaf pieces -- `iter_blocks`, `leaf_frame_range`,
    and the module-level `_block_base_bounds`/`_iter_tree_leaves`/
    `_leaf_frame`/`with_range` helpers `coord_scale_census.py`'s own
    `_work` already imports this same way -- are reused, not
    reimplemented). Frame aliasing (an L0 sparse tile's 16 slots, a
    divided parcel's sub-slots) is always within one block, so a worker
    that owns a whole block dedupes it correctly with no cross-worker
    coordination."""
    pdmdh, hdr = container.pdmdh, container.hdr
    sector_sz, logical_sz = hdr.sector_size, hdr.logical_sector_size
    lmrs = {lmr.level: lmr for lmr in pdmdh.levels}
    with open(path, "rb") as fh:
        for level, bsi, bidx, bsx, bsy, blx, bly, boff, blen in keys:
            lmr = lmrs[level]
            block_bounds = walk._block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
            fh.seek(boff)
            try:
                root = parse_parcel_mgmt_record(fh.read(blen), lmr)
            except Exception:  # noqa: BLE001 -- unreadable block, no leaves to yield
                continue
            sparse_cache: dict = {}
            for leaf_path, entry, leaf_bounds, ptype in walk._iter_tree_leaves(
                    root, block_bounds, lmr, ()):
                frame_bounds, frame_class = walk._leaf_frame(
                    root, level, ptype, leaf_path, leaf_bounds, block_bounds, lmr,
                    sparse_cache)
                frame_range = walk.leaf_frame_range(level, ptype, leaf_path, frame_class)
                moff = volume.getsector(entry.dsa, sector_sz, logical_sz)
                mlen = entry.size * logical_sz
                try:
                    fh.seek(moff)
                    mapdata = fh.read(mlen)
                    loc = MeshLocation(
                        level=level, parcel_type=ptype, blockset_index=bsi,
                        block_index=bidx, parcel_index=leaf_path[-1],
                        bounds=walk.with_range(frame_bounds, frame_range),
                        sector_addr=entry.dsa, size_logical_sectors=entry.size)
                    parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                            n_ext_map=lmr.n_ext_map)
                    err = None
                except Exception as exc:  # noqa: BLE001
                    parcel = None
                    err = f"decode_parcel: {exc}"
                yield walk.WalkedParcel(
                    level=level, blockset_index=bsi, block_index=bidx,
                    parcel_type=ptype, leaf_path=leaf_path, bounds=leaf_bounds,
                    file_offset=moff, length=mlen, parcel=parcel, error=err,
                    frame_bounds=frame_bounds, frame_range=frame_range,
                    frame_class=frame_class)


def _work(args: tuple) -> dict:
    """One process-pool worker's shard: decode its assigned blocks, fold
    each leaf into a local accumulator, and return it (its `seen` set is
    local bookkeeping only and dropped before crossing the process
    boundary)."""
    path, keys = args
    container = walk.read_container(path)
    acc = _new_acc()
    for wp in _decode_block_parcels(path, container, keys):
        _accumulate(acc, wp)
    acc["seen"] = None
    return acc


def _run_coord_scale(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})
    workers = getattr(ctx, "workers", 1) or 1
    if workers <= 1:
        return judge(walk.iter_parcels(ctx.generated))
    keys = _block_keys(ctx.generated)
    # Interleaved chunks (8 per worker), same load-balancing split
    # `coord_scale_census.py`'s `collect()` uses: L0's ~1836 blocks vary
    # widely in leaf count, so round-robin striping spreads that unevenness
    # across workers far better than contiguous slices would.
    chunks = [c for c in (keys[i::workers * 8] for i in range(workers * 8)) if c]
    with ProcessPoolExecutor(workers) as ex:
        accs = list(ex.map(_work, [(ctx.generated, c) for c in chunks]))
    return _finalize(_merge(accs))


CHECKS = [
    Check(
        id="coord_scale",
        layer="map",
        description="Zero parcels hold a vertex outside their frame's "
                    "coordconv.range_for range (inclusive); per-class maxima reported.",
        run=_run_coord_scale,
    ),
]
