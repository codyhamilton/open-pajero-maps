#!/usr/bin/env python3
"""What does the route-planning region's byte size actually scale with?

Standalone companion to `estimate_overhead_scaling.py`, which established
that ALLDATA.KWI contains a 150,959,968-byte "Region / Route-Planning Data"
region (9.9% of the 1.53 GB file) that the main-map mesh never reaches, and
identified mhr[1] as the spec Chapter 9 "Region Data Management Frame"
header for it.

The size-budget report currently assumes, as a placeholder, that a rebuilt
disc's route-planning data scales with total road-km. This script tests
that assumption empirically instead:

  STEP 1 -- decode the Chapter 9 Region Management Table off the real disc.
            Per spec 9.2.1 each Region Management Record is:
              0   3 B  B:N  uppermost latitude   (bit23 = S/W sign,
              3   3 B  B:N  lowest latitude       bits22..0 = 1/8-second)
              6   3 B  B:N  leftmost longitude
              9   3 B  B:N  rightmost longitude
             12   2 B  N    corresponding higher-level region number
             14   2 B  N    foremost lower-level region number
             16   2 B  N    number of lower-level regions
             18   ?      Data Storage Location Record, layout chosen by the
                         "Region Management Record Type Code" in the
                         distribution header (9.1 field 2):
                           type 0   : DSA(4) + BS(2)          -> 24 B record
                           type 1   : DSA(4) + BS(2) + BS(2)  -> 26 B record
                           type 100 : DSA(4) + BS(2) + C(12)  -> 36 B record
            That yields, per region, a real byte size and a real bbox.

  STEP 2 -- for each region bbox, compute road statistics from the Australia
            OSM extract in ONE streaming pass (pyosmium): total road-km,
            major-class road-km (motorway/trunk/primary/secondary/tertiary
            + their _link forms), and a junction proxy (highway nodes
            referenced by >= 3 distinct road ways).

  STEP 3 -- correlate per-region route-planning bytes against each statistic
            (Pearson r, r^2, and a zero-intercept proportional fit) and
            report which one the disc's own data actually tracks.

Reads the disc read-only; touches no parser/kiwiw module.

Usage:
    python3 estimate_route_planning_scaling.py --regions-only     # step 1
    python3 estimate_route_planning_scaling.py                    # all steps
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.bitutils import sws, u16, u24, u32
from kiwiw.disc import AllData
from kiwiw.volume import getsector

NO_DATA_DSA = 0xFFFFFFFF
LS = 32  # logical sector size

DEFAULT_ALLDATA = "/run/media/codyh/464210-8480/ALLDATA.KWI"
DEFAULT_PBF = str(Path(__file__).resolve().parent.parent / "australia-260824.osm.pbf")

MAJOR = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link",
}
# Everything we count as "a road" at all (drivable network). Deliberately
# excludes footway/cycleway/path/steps/pedestrian etc., which no automotive
# router would index.
ROADS = MAJOR | {
    "unclassified", "residential", "living_street", "service", "track",
    "road", "busway",
}


# --------------------------------------------------------------------------
# STEP 1: Chapter 9 region management table
# --------------------------------------------------------------------------
def bn_coord(buf: bytes, off: int) -> float | None:
    """Spec 9.2.1 (1): 3-byte B:N latitude/longitude. bit23 = south/west
    flag, bits 22..0 = magnitude in 1/8-second units. FFFFFF = dummy."""
    v = u24(buf, off)
    if v == 0xFFFFFF:
        return None
    deg = (v & 0x7FFFFF) / 8.0 / 3600.0
    return -deg if (v >> 23) & 1 else deg


def decode_regions(alldata: str) -> dict:
    disc = AllData(alldata)
    fh = disc._fh
    e = disc.mhr[1]
    hoff = getsector(e.dsa, disc.sector_sz, disc.logical_sz)
    fh.seek(hoff)
    hdr = fh.read(e.size * LS)

    header_size = sws(u16(hdr, 0))
    type_code = u16(hdr, 2) & 0xFF
    n_regions = u32(hdr, 4)
    rmt_dsa = u32(hdr, 8)
    rmt_bs = u16(hdr, 12)
    n_levels = hdr[46]
    lmr_size = sws(u16(hdr, 48))

    levels = []
    for i in range(n_levels):
        o = 50 + i * lmr_size
        lc = u16(hdr, o)
        level = lc >> 10
        if level >= 32:
            level -= 64
        levels.append({
            "level_code": lc,
            "level": level,
            "n_basic_frames": (lc >> 4) & 0xF,
            "n_ext_frames": lc & 0xF,
            "n_regions": u16(hdr, o + 2),
            "region_rec_size": sws(u16(hdr, o + 4)),
            "node_rec_size": sws(u16(hdr, o + 6)),
            "link_rec_size": sws(u16(hdr, o + 8)),
            "link_cost_rec_size": sws(u16(hdr, o + 10)),
            "btwn_restrict_rec_size": sws(u16(hdr, o + 12)),
            "btwn_cost_rec_size": sws(u16(hdr, o + 14)),
        })

    rmt_off = getsector(rmt_dsa, disc.sector_sz, disc.logical_sz)
    fh.seek(rmt_off)
    rmt = fh.read(rmt_bs * LS)

    regions = []
    pos = 0
    for lv in levels:
        rsz = lv["region_rec_size"]
        for rn in range(lv["n_regions"]):
            b = rmt[pos:pos + rsz]
            pos += rsz
            if len(b) < 24:
                break
            dsa = u32(b, 18)
            bs = u16(b, 22)
            regions.append({
                "level": lv["level"],
                "region_no": rn,
                "rec_size": rsz,
                "lat_max": bn_coord(b, 0),
                "lat_min": bn_coord(b, 3),
                "lon_min": bn_coord(b, 6),
                "lon_max": bn_coord(b, 9),
                "parent": u16(b, 12),
                "first_child": u16(b, 14),
                "n_children": u16(b, 16),
                "dsa": dsa,
                "bs": bs,
                "byte_off": (None if dsa == NO_DATA_DSA
                             else getsector(dsa, disc.sector_sz, disc.logical_sz)),
                "bytes": 0 if dsa == NO_DATA_DSA else bs * LS,
            })

    return {
        "header_offset": hoff,
        "header_size": header_size,
        "type_code": type_code,
        "n_regions_declared": n_regions,
        "rmt_offset": rmt_off,
        "rmt_bytes": rmt_bs * LS,
        "levels": levels,
        "regions": regions,
    }


# --------------------------------------------------------------------------
# STEP 2: OSM statistics per bbox
# --------------------------------------------------------------------------
def osm_stats(pbf: str, boxes: list[tuple[float, float, float, float]]) -> list[dict]:
    """One streaming pass over the PBF. `boxes` are (lon_min, lat_min,
    lon_max, lat_max). A way segment is credited to every box containing its
    midpoint. Returns one dict per box."""
    import osmium

    n = len(boxes)

    class H(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.total_km = [0.0] * n
            self.major_km = [0.0] * n
            # junction proxy: node -> count of distinct road ways touching it
            self.deg = {}
            self.nodebox = {}

        def way(self, w):
            hw = w.tags.get("highway")
            if hw is None or hw not in ROADS:
                return
            is_major = hw in MAJOR
            try:
                nodes = list(w.nodes)
            except Exception:
                return
            prev = None
            for nd in nodes:
                if not nd.location.valid():
                    prev = None
                    continue
                lat, lon = nd.location.lat, nd.location.lon
                if prev is not None:
                    plat, plon = prev
                    mlat, mlon = (lat + plat) / 2, (lon + plon) / 2
                    d = haversine(plat, plon, lat, lon)
                    for i, (x0, y0, x1, y1) in enumerate(boxes):
                        if x0 <= mlon <= x1 and y0 <= mlat <= y1:
                            self.total_km[i] += d
                            if is_major:
                                self.major_km[i] += d
                prev = (lat, lon)
            # junction accounting on endpoints AND shared interior nodes
            for nd in nodes:
                r = nd.ref
                self.deg[r] = self.deg.get(r, 0) + 1
                if r not in self.nodebox and nd.location.valid():
                    self.nodebox[r] = (nd.location.lat, nd.location.lon)

    h = H()
    h.apply_file(pbf, locations=True, idx="flex_mem")

    junc = [0] * n
    for r, c in h.deg.items():
        if c < 3:
            continue
        loc = h.nodebox.get(r)
        if loc is None:
            continue
        lat, lon = loc
        for i, (x0, y0, x1, y1) in enumerate(boxes):
            if x0 <= lon <= x1 and y0 <= lat <= y1:
                junc[i] += 1

    return [{"total_km": h.total_km[i], "major_km": h.major_km[i],
             "junctions": junc[i]} for i in range(n)]


def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# STEP 3: correlation
# --------------------------------------------------------------------------
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def prop_fit(xs, ys):
    """Zero-intercept y = k*x fit, plus its R^2 about the mean of y.
    This is the fit that matters for a size budget: 'bytes per unit of x'."""
    sxx = sum(x * x for x in xs)
    if sxx == 0:
        return None, None
    k = sum(x * y for x, y in zip(xs, ys)) / sxx
    my = sum(ys) / len(ys)
    ss_res = sum((y - k * x) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return k, (1 - ss_res / ss_tot if ss_tot else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alldata", default=DEFAULT_ALLDATA)
    ap.add_argument("--pbf", default=DEFAULT_PBF)
    ap.add_argument("--regions-only", action="store_true")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    info = decode_regions(args.alldata)
    print("=== Chapter 9 Region Data Management Distribution Header ===")
    print(f"  at byte {info['header_offset']:,}  header_size={info['header_size']} B")
    print(f"  region management record type code = {info['type_code']}")
    print(f"  total region management records    = {info['n_regions_declared']:,}")
    print(f"  region management table @ {info['rmt_offset']:,} ({info['rmt_bytes']:,} B)")
    print(f"  levels = {len(info['levels'])}")
    for lv in info["levels"]:
        print(f"    level {lv['level']:>3}: n_regions={lv['n_regions']:>5} "
              f"rec={lv['region_rec_size']} node={lv['node_rec_size']} "
              f"link={lv['link_rec_size']} cost={lv['link_cost_rec_size']} "
              f"basic_frames={lv['n_basic_frames']} ext={lv['n_ext_frames']}")

    regs = info["regions"]
    total = sum(r["bytes"] for r in regs)
    real = [r for r in regs if r["bytes"] and r["lat_max"] is not None]
    print(f"\n  decoded {len(regs)} region records; {len(real)} with real data+bbox")
    print(f"  sum of region data sizes = {total:,} B")

    by_level = {}
    for r in regs:
        by_level.setdefault(r["level"], []).append(r)
    for lv in sorted(by_level):
        rs = by_level[lv]
        b = sum(x["bytes"] for x in rs)
        print(f"    level {lv:>3}: {len(rs):>5} records, {b:>13,} B")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(info, indent=1))

    if args.regions_only:
        return

    # Correlate at each level that has enough usable regions.
    for lv in sorted(by_level):
        rs = [r for r in by_level[lv]
              if r["bytes"] and r["lat_max"] is not None and r["lon_max"] is not None]
        if len(rs) < 3:
            print(f"\nlevel {lv}: only {len(rs)} usable regions -- too few to correlate.")
            continue
        boxes = [(r["lon_min"], r["lat_min"], r["lon_max"], r["lat_max"]) for r in rs]
        print(f"\n=== level {lv}: OSM pass over {len(boxes)} region bboxes ===")
        stats = osm_stats(args.pbf, boxes)
        for r, s in zip(rs, stats):
            r.update(s)
            r["area_km2"] = (haversine(r["lat_min"], r["lon_min"], r["lat_min"], r["lon_max"])
                             * haversine(r["lat_min"], r["lon_min"], r["lat_max"], r["lon_min"]))
        report(rs)
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(info, indent=1))


def report(rs):
    ys = [r["bytes"] for r in rs]
    print(f"\n{'reg':>4} {'bytes':>12} {'total_km':>11} {'major_km':>11} "
          f"{'junctions':>10} {'area_km2':>11}  bbox")
    for r in sorted(rs, key=lambda x: -x["bytes"]):
        print(f"{r['region_no']:>4} {r['bytes']:>12,} {r['total_km']:>11,.0f} "
              f"{r['major_km']:>11,.0f} {r['junctions']:>10,} {r['area_km2']:>11,.0f}"
              f"  [{r['lon_min']:.3f},{r['lat_min']:.3f} .. "
              f"{r['lon_max']:.3f},{r['lat_max']:.3f}]")

    print(f"\n  n = {len(rs)} regions")
    print(f"  {'predictor':<14} {'pearson r':>10} {'r^2':>8} "
          f"{'k (B/unit)':>14} {'prop R^2':>10}")
    for key, label in (("total_km", "total road-km"), ("major_km", "major road-km"),
                       ("junctions", "junction count"), ("area_km2", "region area")):
        xs = [r[key] for r in rs]
        r_ = pearson(xs, ys)
        k, pr2 = prop_fit(xs, ys)
        print(f"  {label:<14} {(f'{r_:>10.4f}' if r_ is not None else '        --')} "
              f"{(f'{r_*r_:>8.4f}' if r_ is not None else '      --')} "
              f"{(f'{k:>14,.1f}' if k is not None else '            --')} "
              f"{(f'{pr2:>10.4f}' if pr2 is not None else '        --')}")


if __name__ == "__main__":
    main()
