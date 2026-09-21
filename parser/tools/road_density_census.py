#!/usr/bin/env python3
"""Per-level road-density census of a reference disc's ALLDATA.KWI.

For each level: links, vertices (nodes + intermediate points), vertices per
link, total road length (km) and vertices per km, as totals plus mean/p50/p90.
Reads only through `harness.walk` (no writer modules).

Length basis: the true coordinate model is unsettled until Phase 2, so each
parcel's raw coordinates are recovered from the decoder's lat/lon (which
assumes a 2**15 range) and rescaled as raw / coord_max * leaf extent, where
coord_max is 4096, or 16384 for an L0 parcel whose raw coordinates exceed 4096.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk  # noqa: E402

DECODER_RANGE = float(1 << 15)
KM_PER_DEG = 111.32
LENGTH_BASIS = ("leaf bounds extent / coord_max; coord_max from refdata/profile/coord_scale.json "
                "by the content-independent class rule (level, grid position, division): "
                "4096 (L2-L12 full, urban L0, divided sub 1-3), 2048 (divided sub 0), "
                "16384 (sparse L0); raw recovered from decoder lat/lon at range 32768; "
                "equirectangular km")
COORD_SCALE = Path(__file__).resolve().parent.parent / "refdata" / "profile" / "coord_scale.json"


def _pct(vals: list, p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p
    lo = int(math.floor(k))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _stats(vals: list) -> dict:
    n = len(vals)
    return {"mean": round(sum(vals) / n, 4) if n else 0.0,
            "p50": round(_pct(vals, 0.5), 4), "p90": round(_pct(vals, 0.9), 4)}


_CS: dict = {}


def _class_range(wp) -> int | None:
    """R-census range for a walked parcel by the class rule, or None if `wp`
    carries no grid position (synthetic callers) so the caller falls back."""
    if not hasattr(wp, "blockset_index"):
        return None
    if not _CS:
        import coord_scale_census as csc
        d = json.loads(COORD_SCALE.read_text())
        _CS["r"] = d["ranges"]
        _CS["u"] = {tuple(t) for t in d["class_rule"]["urban_tiles"]}
        _CS["csc"] = csc
    csc = _CS["csc"]
    div = wp.parcel_type
    cls = csc.parcel_class(wp.level, div, (wp.blockset_index, wp.block_index, wp.leaf_path[0]),
                           _CS["u"])
    return _CS["r"][str(wp.level)][cls][csc.division_state(div, wp.leaf_path[-1])]["max"]


def parcel_metrics(wp) -> dict | None:
    """(per-link vertex counts, length_km) for one walked parcel, or None."""
    parcel = wp.parcel
    if parcel is None or parcel.road is None or not parcel.road.links:
        return None
    # Span and range must come from the SAME frame: the stored coordinates
    # are expressed in the walker's frame (L0 sparse = the 4x4 tile at
    # 16384), not in the leaf slot. Synthetic callers without a frame fall
    # back to bounds (frame == leaf).
    b = getattr(wp, "frame_bounds", None) or wp.bounds
    lon_span, lat_span = b.lon_hi - b.lon_lo, b.lat_hi - b.lat_lo
    chains = []
    for link in parcel.road.links:
        pts = link.points or [(n.lat, n.lon) for n in link.nodes]
        raw = [((lon - b.lon_lo) / lon_span * DECODER_RANGE,
                (b.lat_hi - lat) / lat_span * DECODER_RANGE) for lat, lon in pts]
        chains.append(raw)
    peak = max((c for ch in chains for p in ch for c in p), default=0.0)
    cm = getattr(wp, "frame_range", None) or _class_range(wp)
    coord_max = float(cm) if cm else (16384.0 if (wp.level == 0 and peak > 4096.5) else 4096.0)
    mid_lat = math.radians((b.lat_lo + b.lat_hi) / 2)
    kx = lon_span / coord_max * KM_PER_DEG * math.cos(mid_lat)
    ky = lat_span / coord_max * KM_PER_DEG
    length = 0.0
    for ch in chains:
        for (x0, y0), (x1, y1) in zip(ch, ch[1:]):
            length += math.hypot((x1 - x0) * kx, (y1 - y0) * ky)
    return {"vertices": [len(c) for c in chains], "length_km": length,
            "coord_max": int(coord_max)}


class Census:
    def __init__(self) -> None:
        self.lv: dict = {}
        self._seen: set = set()  # (file_offset, length): divided-parcel slots share frames

    def add(self, wp) -> None:
        key = (getattr(wp, "file_offset", None), getattr(wp, "length", None))
        if key != (None, None):
            if key in self._seen:
                return
            self._seen.add(key)
        m = parcel_metrics(wp)
        if m is None:
            return
        a = self.lv.setdefault(wp.level, {"per_link": [], "parcels": [], "km": 0.0,
                                          "coord_max": {}})
        a["per_link"].extend(m["vertices"])
        v = sum(m["vertices"])
        a["parcels"].append((len(m["vertices"]), v, m["length_km"]))
        a["km"] += m["length_km"]
        a["coord_max"][str(m["coord_max"])] = a["coord_max"].get(str(m["coord_max"]), 0) + 1

    def to_dict(self, coverage: str = "") -> dict:
        levels = {}
        for lvl in sorted(self.lv):
            a = self.lv[lvl]
            links, verts = len(a["per_link"]), sum(a["per_link"])
            pv = [(v / km) for _, v, km in a["parcels"] if km > 0]
            levels[str(lvl)] = {
                "links": links, "vertices": verts, "parcels_with_roads": len(a["parcels"]),
                "length_km": round(a["km"], 3),
                "vertices_per_link": {"total": round(verts / links, 4) if links else 0.0,
                                      **_stats(a["per_link"])},
                "vertices_per_km": {"total": round(verts / a["km"], 4) if a["km"] else 0.0,
                                    "per_parcel": _stats(pv)},
                "links_per_parcel": _stats([n for n, _, _ in a["parcels"]]),
                "vertices_per_parcel": _stats([v for _, v, _ in a["parcels"]]),
                "length_km_per_parcel": _stats([k for _, _, k in a["parcels"]]),
                "parcels_by_coord_max": dict(sorted(a["coord_max"].items())),
            }
        return {"length_basis": LENGTH_BASIS, "levels": levels}


def run(reference: str) -> dict:
    c = Census()
    for wp in walk.iter_parcels(str(Path(reference) / "ALLDATA.KWI")):
        c.add(wp)
    return c.to_dict()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    t0 = time.time()
    d = run(args.reference)
    Path(args.out).write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out} in {time.time() - t0:.0f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
