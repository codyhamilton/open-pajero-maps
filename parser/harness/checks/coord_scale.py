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
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness import walk
from harness.context import Check, CheckResult

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


def judge(parcels) -> CheckResult:
    """Pure verdict over an iterable of `WalkedParcel`s (testable without a
    disc)."""
    seen: set = set()
    per_class: dict = {}
    exceed = 0
    unranged = 0
    examples: list = []
    judged = 0
    for wp in parcels:
        if wp.error is not None or wp.parcel is None:
            continue
        frame_key = (wp.file_offset, wp.length)
        if frame_key in seen:
            continue
        seen.add(frame_key)
        key = class_key(wp)
        rng = walk.leaf_frame_range(wp.level, wp.parcel_type, wp.leaf_path, wp.frame_class)
        ext = parcel_extent(wp) if rng is not None and wp.frame_range is not None else None
        if rng is None or wp.frame_range is None:
            unranged += 1
            if len(examples) < EXAMPLES:
                examples.append({"class": key, "reason": "no range_for triple",
                                 "level": wp.level, "bs": wp.blockset_index,
                                 "blk": wp.block_index, "path": list(wp.leaf_path)})
            continue
        if ext is None:
            continue
        lo, hi, _ = ext
        judged += 1
        c = per_class.setdefault(key, {"range": rng, "parcels": 0, "observed_max": 0,
                                       "observed_min": 0, "exceeding": 0})
        c["parcels"] += 1
        c["observed_max"] = max(c["observed_max"], hi)
        c["observed_min"] = min(c["observed_min"], lo)
        if lo < 0 or hi > rng:
            exceed += 1
            c["exceeding"] += 1
            if len(examples) < EXAMPLES:
                examples.append({"class": key, "range": rng, "min": lo, "max": hi,
                                 "level": wp.level, "bs": wp.blockset_index,
                                 "blk": wp.block_index, "path": list(wp.leaf_path)})
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


def _run_coord_scale(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})
    return judge(walk.iter_parcels(ctx.generated))


CHECKS = [
    Check(
        id="coord_scale",
        layer="map",
        description="Zero parcels hold a vertex outside their frame's "
                    "coordconv.range_for range (inclusive); per-class maxima reported.",
        run=_run_coord_scale,
    ),
]
