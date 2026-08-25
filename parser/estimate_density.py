#!/usr/bin/env python3
"""Standalone density-estimation script for Phase 3 planning (OSM-volume
budgeting against the 4.7GB DVD target).

Does NOT modify any parser/writer code. Walks the real disc's
block-set -> block -> parcel (-> subparcel*) mesh for every one of the 7
map levels, using the same coordinate math as `kiwiw.mesh.locate_parcel()`
but generalized to enumerate *every* leaf parcel at a level rather than a
single point query. For each leaf parcel it reads the Map Frame header to
get the road/background/name sub-frame byte offsets+sizes directly (cheap,
no full geometry decode needed for byte counts), and optionally does a full
`kiwiw.road`/`kiwiw.name` decode on a sample to get real road-km and name
counts to pair against those byte counts.

Usage:
    python3 estimate_density.py --alldata /run/media/codyh/464210-8480/ALLDATA.KWI [--probe]

--probe: just print per-level grid/blockset/block counts and a leaf-parcel
census (byte sizes only, no geometry decode) so we can gauge scale before
committing to a full run. Safe to run first.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.bitutils import extract, sws, u16, u32
from kiwiw.disc import AllData
from kiwiw.model import BoundingBox, MeshLocation
from kiwiw.name import decode_name_frame
from kiwiw.road import decode_road_frame
from kiwiw.volume import getsector

NO_DATA_DSA = 0xFFFFFFFF
MAX_SUBPARCEL_DEPTH = 6
BMT_SIZE = 6


def _lon_span(lo: float, hi: float) -> float:
    span = hi - lo
    return span + 360.0 if span < 0 else span


def read_bmt_array(buf: bytes, byte_off: int, count: int):
    out = []
    for i in range(count):
        off = byte_off + i * 6
        if off + 6 > len(buf):
            out.append((NO_DATA_DSA, 0))
            continue
        out.append((u32(buf, off), u16(buf, off + 4)))
    return out


def walk_subparcel(pdat: bytes, poff_in_buf: int, lmr, bounds, depth: int):
    """Yields (parcel_type, dsa, size, bounds) for every LEAF parcel entry
    reachable from the parcel-management record at `poff_in_buf` within
    `pdat` -- generalizes kiwiread.c's / kiwiw.mesh's single-coordinate
    walk into "visit every entry". `bounds` is (lat_lo, lat_hi, lon_lo,
    lon_hi) for the *whole* array being walked (narrowed further per-entry
    below, exactly mirroring kiwiw.mesh.locate_parcel's subdivision math)."""
    if depth > MAX_SUBPARCEL_DEPTH:
        return
    if poff_in_buf < 0 or poff_in_buf + 4 > len(pdat):
        return
    p_type_raw = u16(pdat, poff_in_buf)
    pt = extract(p_type_raw, 8, 9)
    lt = extract(p_type_raw, 0, 7)
    if lt != 0:
        return  # malformed / unexpected -- kiwiread.c asserts lt==0 always
    gn_lat = 1 + lmr.n_parcels_lat[pt]
    gn_lng = 1 + lmr.n_parcels_lng[pt]
    mapinfo_off = poff_in_buf + 4
    lat_lo, lat_hi, lon_lo, lon_hi = bounds
    lat_w = (lat_hi - lat_lo) / gn_lat
    lon_w = (lon_hi - lon_lo) / gn_lng
    n = gn_lat * gn_lng
    for idx in range(n):
        entry_off = mapinfo_off + idx * 6
        if entry_off + 6 > len(pdat):
            continue
        dsa = u32(pdat, entry_off)
        size = u16(pdat, entry_off + 4)
        if dsa == NO_DATA_DSA:
            continue
        lpx = idx % gn_lng
        lpy = idx // gn_lng
        sub_lon_lo = lon_lo + lpx * lon_w
        sub_lat_lo = lat_lo + lpy * lat_w
        sub_bounds = (sub_lat_lo, sub_lat_lo + lat_w, sub_lon_lo, sub_lon_lo + lon_w)
        if size != 0:
            yield (pt, dsa, size, sub_bounds)
        else:
            new_off = sws(dsa)
            yield from walk_subparcel(pdat, new_off, lmr, sub_bounds, depth + 1)


def iter_level_leaf_parcels(pdmdh, lmr, fh, zdat0, sector_sz, logical_sz):
    """Enumerate every leaf parcel management entry at this LMR's level,
    yielding (parcel_type, dsa, size_logical_sectors, bounds)."""
    level = lmr.level
    lon_span = _lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    nx, ny = lmr.grid_nx, lmr.grid_ny
    mx = lon_span / nx
    my = lat_span / ny
    nbs_lng, nbs_lat = 1 + lmr.n_blocksets_lng, 1 + lmr.n_blocksets_lat
    nbl_lng, nbl_lat = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
    npc_lng, npc_lat = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]
    n_blocks = nbl_lat * nbl_lng

    for bs in pdmdh.blocksets:
        if bs.level != level or bs.bmt_size == 0:
            continue
        bset_flat = bs.blockset_index
        bsx = bset_flat % nbs_lng
        bsy = bset_flat // nbs_lng
        n_entries = bs.bmt_size // BMT_SIZE
        bmt_entries = read_bmt_array(zdat0, bs.bmt_offset, min(n_entries, n_blocks))
        for block_flat, (bdsa, bsize) in enumerate(bmt_entries):
            if bdsa == NO_DATA_DSA or bsize == 0:
                continue
            blx = block_flat % nbl_lng
            bly = block_flat // nbl_lng
            poff = getsector(bdsa, sector_sz, logical_sz)
            fh.seek(poff)
            pdat = fh.read(bsize * logical_sz)
            block_lon_lo = pdmdh.coverage.lon_lo + (bsx * nbl_lng * npc_lng + blx * npc_lng) * mx
            block_lat_lo = pdmdh.coverage.lat_lo + (bsy * nbl_lat * npc_lat + bly * npc_lat) * my
            block_bounds = (
                block_lat_lo, block_lat_lo + my * npc_lat,
                block_lon_lo, block_lon_lo + mx * npc_lng,
            )
            yield from walk_subparcel(pdat, 0, lmr, block_bounds, depth=1)


def read_frame_sizes(fh, dsa, size, sector_sz, logical_sz):
    """Cheap path: read just the Map Frame header + mfde table to get
    road/background/name frame byte offsets+sizes, without decoding
    geometry. Mirrors kiwiw.parcel.decode_parcel's header logic."""
    moff = getsector(dsa, sector_sz, logical_sz)
    fh.seek(moff)
    mapdata = fh.read(size * logical_sz)
    if len(mapdata) < 36:
        return None, mapdata
    nregion = u16(mapdata, 34)
    de_off = 36 + nregion * 4
    entries = []
    for i in range(3):
        eoff = de_off + i * 6
        if eoff + 6 > len(mapdata):
            entries.append((0xFFFFFFFF, 0))
            continue
        raw_off = u32(mapdata, eoff)
        raw_size = u16(mapdata, eoff + 4)
        entries.append((sws(raw_off), sws(raw_size)))
    return entries, mapdata


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def polyline_km(points):
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:]):
        total += haversine_km(lat1, lon1, lat2, lon2)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alldata", default="/run/media/codyh/464210-8480/ALLDATA.KWI")
    ap.add_argument("--probe", action="store_true",
                     help="Cheap census only: grid sizes + leaf-parcel counts "
                          "+ byte sizes from headers, no geometry decode.")
    ap.add_argument("--sample-per-level", type=int, default=3000,
                     help="Max parcels to fully geometry-decode per level "
                          "for the km/name-count ratio (levels with fewer "
                          "leaf parcels than this get a full census instead).")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    random.seed(args.seed)
    t0 = time.time()

    disc = AllData(args.alldata)
    pdmdh = disc.pdmdh
    zdat0 = disc._zdat0
    fh = disc._fh
    sector_sz = disc.sector_sz
    logical_sz = disc.logical_sz

    print(f"# Coverage bbox: lat {pdmdh.coverage.lat_lo:.4f}..{pdmdh.coverage.lat_hi:.4f}, "
          f"lon {pdmdh.coverage.lon_lo:.4f}..{pdmdh.coverage.lon_hi:.4f}")
    print(f"# {len(pdmdh.levels)} levels: {[l.level for l in pdmdh.levels]}")
    print(f"# {len(pdmdh.blocksets)} block sets total")

    results = {}

    for lmr in sorted(pdmdh.levels, key=lambda l: l.level):
        level_bsets = [b for b in pdmdh.blocksets if b.level == lmr.level and b.bmt_size > 0]
        print(f"\n=== Level {lmr.level} === grid {lmr.grid_nx}x{lmr.grid_ny}, "
              f"{len(level_bsets)}/{sum(1 for b in pdmdh.blocksets if b.level==lmr.level)} "
              f"block sets in use, road/bg/name frame counts "
              f"{lmr.n_road_frames}/{lmr.n_background_frames}/{lmr.n_name_frames}")

        # PASS 1: cheap traversal-only pass (no per-parcel content reads) to
        # find every dsa's *multiplicity* and the geographic UNION of all
        # mesh cells that reference it. This matters because a real,
        # confirmed pattern on this disc (level 0 especially) is that many
        # adjacent finest-grid cells share one physical parcel record --
        # e.g. dsa=20530211 near (-50.0, 108.0) is referenced by exactly the
        # 4x4 contiguous block of nominal finest cells covering
        # lat[-50.0..-49.9167] x lon[108.0..108.125] (verified by hand
        # against this exact run). Decoding that frame's road/name geometry
        # against only the FIRST cell's (1/16th-size) bounds would silently
        # compress all its coordinates into 1/4 of their real lat/lon span
        # per axis -- so the union bbox, not the first-seen cell, is used
        # below as the frame's real bounds.
        n_leaf = 0
        union = {}  # dsa -> [lat_lo, lat_hi, lon_lo, lon_hi, size, count]
        for pt, dsa, size, bounds in iter_level_leaf_parcels(pdmdh, lmr, fh, zdat0, sector_sz, logical_sz):
            n_leaf += 1
            u = union.get(dsa)
            if u is None:
                union[dsa] = [bounds[0], bounds[1], bounds[2], bounds[3], size, 1]
            else:
                u[0] = min(u[0], bounds[0]); u[1] = max(u[1], bounds[1])
                u[2] = min(u[2], bounds[2]); u[3] = max(u[3], bounds[3])
                u[5] += 1

        n_unique = len(union)
        total_multiplicity = sum(u[5] for u in union.values())
        shared_frames = sum(1 for u in union.values() if u[5] > 1)
        print(f"  mesh-cell references: {n_leaf} total -> {n_unique} UNIQUE physical parcel "
              f"records ({shared_frames} shared by >1 cell; avg multiplicity "
              f"{total_multiplicity/n_unique:.2f}x) -- union bbox used as each frame's real bounds")

        # PASS 2: one content read per unique dsa, using the union bbox.
        n_with_road = 0
        n_with_name = 0
        total_road_bytes = 0
        total_name_bytes = 0
        total_bg_bytes = 0
        leaf_cache = []  # (dsa, size, bounds, road_off, road_size, name_off, name_size, mapdata)

        for dsa, (lat_lo, lat_hi, lon_lo, lon_hi, size, mult) in union.items():
            bounds = (lat_lo, lat_hi, lon_lo, lon_hi)
            entries, mapdata = read_frame_sizes(fh, dsa, size, sector_sz, logical_sz)
            if entries is None:
                continue
            (road_off, road_size), (bg_off, bg_size), (name_off, name_size) = entries
            has_road = road_size and road_off != 0xFFFFFFFF
            has_name = name_size and name_off != 0xFFFFFFFF
            has_bg = bg_size and bg_off != 0xFFFFFFFF
            if has_road:
                n_with_road += 1
                total_road_bytes += road_size
            if has_name:
                n_with_name += 1
                total_name_bytes += name_size
            if has_bg:
                total_bg_bytes += bg_size
            if has_road or has_name:
                leaf_cache.append((dsa, size, bounds, road_off, road_size, name_off, name_size, mapdata))

        print(f"  UNIQUE leaf parcels: {n_unique} total, {n_with_road} with road data "
              f"({n_with_road/n_unique*100:.1f}%), {n_with_name} with name data "
              f"({n_with_name/n_unique*100:.1f}%)")
        print(f"  total bytes (deduped): road={total_road_bytes:,}  name={total_name_bytes:,}  "
              f"background={total_bg_bytes:,}")

        level_result = dict(
            level=lmr.level, n_leaf=n_leaf, n_unique=n_unique, n_with_road=n_with_road,
            n_with_name=n_with_name, total_road_bytes=total_road_bytes,
            total_name_bytes=total_name_bytes, total_bg_bytes=total_bg_bytes,
            shared_frames=shared_frames,
        )

        if not args.probe:
            candidates = [c for c in leaf_cache if c[4] > 0]  # has road bytes
            name_candidates = [c for c in leaf_cache if c[6] > 0]
            sample = candidates if len(candidates) <= args.sample_per_level else \
                random.sample(candidates, args.sample_per_level)
            name_sample = name_candidates if len(name_candidates) <= args.sample_per_level else \
                random.sample(name_candidates, args.sample_per_level)

            sample_road_km = 0.0
            sample_road_bytes = 0
            n_links_sampled = 0
            for (dsa, size, bounds, road_off, road_size, name_off, name_size, mapdata) in sample:
                bb = BoundingBox(lat_lo=bounds[0], lat_hi=bounds[1], lon_lo=bounds[2], lon_hi=bounds[3])
                buf = mapdata[road_off: road_off + road_size]
                try:
                    frame = decode_road_frame(buf, bb)
                except Exception:
                    continue
                for link in frame.links:
                    n_links_sampled += 1
                    sample_road_km += polyline_km(link.points)
                sample_road_bytes += road_size

            sample_name_bytes = 0
            n_names_sampled = 0
            for (dsa, size, bounds, road_off, road_size, name_off, name_size, mapdata) in name_sample:
                bb = BoundingBox(lat_lo=bounds[0], lat_hi=bounds[1], lon_lo=bounds[2], lon_hi=bounds[3])
                buf = mapdata[name_off: name_off + name_size]
                try:
                    frame = decode_name_frame(buf, bb)
                except Exception:
                    continue
                n_names_sampled += len(frame.records)
                sample_name_bytes += name_size

            print(f"  SAMPLE (road): {len(sample)}/{len(candidates)} parcels fully decoded, "
                  f"{n_links_sampled} links, {sample_road_km:.2f} km, {sample_road_bytes:,} bytes"
                  + (f"  -> {sample_road_bytes/sample_road_km:.2f} bytes/km" if sample_road_km > 0 else "  -> n/a (0 km)"))
            print(f"  SAMPLE (name): {len(name_sample)}/{len(name_candidates)} parcels fully decoded, "
                  f"{n_names_sampled} name records, {sample_name_bytes:,} bytes"
                  + (f"  -> {sample_name_bytes/n_names_sampled:.2f} bytes/record" if n_names_sampled > 0 else "  -> n/a (0 records)"))

            level_result.update(dict(
                sample_n_parcels_road=len(sample), sample_n_candidates_road=len(candidates),
                sample_n_links=n_links_sampled, sample_road_km=sample_road_km,
                sample_road_bytes=sample_road_bytes,
                sample_n_parcels_name=len(name_sample), sample_n_candidates_name=len(name_candidates),
                sample_n_names=n_names_sampled, sample_name_bytes=sample_name_bytes,
            ))

        results[lmr.level] = level_result

    disc.close()

    # Overall summary
    print("\n\n=== OVERALL SUMMARY ===")
    total_road_bytes = sum(r["total_road_bytes"] for r in results.values())
    total_name_bytes = sum(r["total_name_bytes"] for r in results.values())
    total_bg_bytes = sum(r["total_bg_bytes"] for r in results.values())
    total_leaf = sum(r["n_leaf"] for r in results.values())
    total_unique = sum(r["n_unique"] for r in results.values())
    print(f"Total mesh-cell references across all 7 levels: {total_leaf:,} "
          f"-> {total_unique:,} UNIQUE physical parcel records (dedup by sector address)")
    print(f"Total road-frame bytes (all levels):       {total_road_bytes:,}")
    print(f"Total name-frame bytes (all levels):       {total_name_bytes:,}")
    print(f"Total background-frame bytes (all levels): {total_bg_bytes:,}")

    if not args.probe:
        agg_road_km = sum(r.get("sample_road_km", 0.0) for r in results.values())
        agg_road_bytes_sampled = sum(r.get("sample_road_bytes", 0) for r in results.values())
        agg_names = sum(r.get("sample_n_names", 0) for r in results.values())
        agg_name_bytes_sampled = sum(r.get("sample_name_bytes", 0) for r in results.values())
        if agg_road_km > 0:
            print(f"\nAggregate sampled road: {agg_road_bytes_sampled:,} bytes / {agg_road_km:.1f} km "
                  f"= {agg_road_bytes_sampled/agg_road_km:.2f} bytes/km")
        if agg_names > 0:
            print(f"Aggregate sampled name: {agg_name_bytes_sampled:,} bytes / {agg_names:,} records "
                  f"= {agg_name_bytes_sampled/agg_names:.2f} bytes/record")

    print(f"\n(elapsed {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
