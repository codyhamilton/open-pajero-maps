#!/usr/bin/env python3
"""Empirical study of the real disc's region hierarchy tree and boundary-node
convention, across MULTIPLE real regions (not just region 178) -- input to
Task item 2 (cross-region boundary node handling) of the multi-level
contraction work. See docs/phases/03-osm-pipeline.md for the write-up this
feeds.

Questions this answers, with numbers over the full population where cheap
enough, or a clearly-scoped sample where full decoding is too slow:

  Q1. Is the region tree a literal parent/child tree (Ch.9.2.1 parent_region /
      first_child_region / n_child_regions), and does it match the level
      structure (root at -32, then levels found in Ch.9.1)?
  Q2. For a child region and its parent, do the child's "is_boundary" nodes
      (Ch.10.6.1.2 node record) correspond to nodes that are ALSO present in
      the parent region's own node/coordinate table (i.e. is a boundary node
      a promoted/shared node, not a distinct "frontier to a sibling region"
      node)?
  Q3. How many boundary nodes does a typical region have, as a fraction of
      its own node count, and does that fraction grow with level (fewer,
      more "important" nodes higher up)?

Usage: python3 study_region_hierarchy.py [--disc PATH] [--sample-pairs N]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.disc import AllData
from kiwiw.route_planning import parse_region_frame, read_rp_frame, RegionMgmtRecord
from kiwiw.bitutils import u16, u24, u32, extract, sws

DEFAULT_DISC_CANDIDATES = [
    "/run/media/codyh/464210-8480/ALLDATA.KWI",
    str(Path.home() / "workspace" / "open-pajero-maps" / "original-disc" / "ALLDATA.KWI"),
]


def decode_node_record(buf: bytes, off: int) -> dict:
    attr = u32(buf, off)
    return {
        "is_boundary": bool(attr & (1 << 25)),
        "n_link_records": extract(attr, 21, 24),
        "link_record_offset": extract(attr, 0, 17),
    }


def decode_node_coord_record(buf: bytes, off: int) -> dict:
    v = u32(buf, off)
    return {"grid_record_number": extract(v, 24, 31), "x": extract(v, 12, 23), "y": extract(v, 0, 11)}


def region_node_coords(disc, rec: RegionMgmtRecord, rf) -> list[tuple[float, float, bool]] | None:
    """Decode every node's (approx lat, lon, is_boundary) for one region, by
    walking the node subframe + node_coord subframe together. Returns None if
    the region has no route-planning data or the frame doesn't parse."""
    rpf = read_rp_frame(disc, rec, rf)
    if rpf is None or rpf.node_header is None:
        return None
    nh = rpf.node_header
    node_sub = rpf.sub("node")
    ncoord_sub = rpf.sub("node_coord")
    if node_sub is None or ncoord_sub is None or not node_sub.size or not ncoord_sub.size:
        return None

    lmr = next(l for l in rf.levels if l.level == rec.level)
    disc._fh.seek(__import__("kiwiw.volume", fromlist=["getsector"]).getsector(
        rec.rp_dsa, disc.sector_sz, disc.logical_sz))
    buf = disc._fh.read(rec.rp_size_ls * disc.logical_sz)

    # Ch.10.12.1 Node Coordinate Distribution Header (18 B, see
    # route_planning_writer.write_node_coord_header for the mirrored encoder
    # layout this decoder inverts): u16 header_size(sws) + u24 lat_width +
    # u24 lon_width + u8 n_lat_grids + u8 n_lon_grids + u16 ref_grid_offset
    # (sws) + u16 ref_grid_size(sws) + u16 node_coord_offset(sws) + u16
    # node_coord_size(sws).
    ncoff = ncoord_sub.offset
    lat_width = u24(buf, ncoff + 2) / 8.0 / 3600.0
    lon_width = u24(buf, ncoff + 5) / 8.0 / 3600.0
    nct_off = sws(u16(buf, ncoff + 14))
    results = []
    node_rec_off = node_sub.offset + nh.header_size
    for i in range(nh.n_nodes):
        nrec = decode_node_record(buf, node_rec_off + i * 6)
        crec = decode_node_coord_record(buf, ncoff + nct_off + i * 4)
        lat = rec.lat_bottom + (crec["y"] / 4095.0) * lat_width if lat_width else rec.lat_bottom
        lon = rec.lon_left + (crec["x"] / 4095.0) * lon_width if lon_width else rec.lon_left
        results.append((lat, lon, nrec["is_boundary"]))
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--disc", default=None)
    ap.add_argument("--max-regions-decoded", type=int, default=40,
                     help="cap on how many regions' full node tables we decode (slow path)")
    args = ap.parse_args()

    disc_path = args.disc
    if disc_path is None:
        for c in DEFAULT_DISC_CANDIDATES:
            if Path(c).exists():
                disc_path = c
                break
    if disc_path is None:
        print("No ALLDATA.KWI found; pass --disc")
        sys.exit(1)

    disc = AllData(disc_path)
    rf = parse_region_frame(disc)

    print(f"=== Q1: region tree structure ({disc_path}) ===")
    print(f"n_levels={rf.n_levels}  n_region_records={len(rf.regions)}")
    by_level = {}
    for r in rf.regions:
        by_level.setdefault(r.level, []).append(r)
    for lvl in sorted(by_level, reverse=True):
        regs = by_level[lvl]
        non_dummy = [r for r in regs if not r.is_dummy]
        with_data = [r for r in non_dummy if r.rp_dsa != 0xFFFFFFFF]
        parents_null = sum(1 for r in non_dummy if r.parent_region == 0xFFFF)
        print(f"  level={lvl:>4}  n_regions={len(regs)}  non_dummy={len(non_dummy)}  "
              f"with_rp_data={len(with_data)}  parent==NULL(root-of-tree)={parents_null}")

    # Verify parent/child linkage is internally consistent: for every non-dummy
    # region with a parent, does the parent's [first_child_region,
    # first_child_region+n_child_regions) span actually include this region's
    # index within its OWN level's block, and does the parent live at the next
    # level up (i.e. numerically greater |level|, matching -32 root -> 2 -> 4
    # -> 6 -> 8 direction)?
    idx_within_level = {}
    for lvl, regs in by_level.items():
        for i, r in enumerate(regs):
            idx_within_level[id(r)] = i
    # Empirically confirmed direction (see study run notes): level=2 is the
    # FINEST/leaf level (smallest bbox area, zero children), level=8 is the
    # COARSEST/root-of-the-real-tree level (largest, most overlapping
    # bboxes) -- i.e. child->parent order is 2 -> 4 -> 6 -> 8 -> (dummy -32
    # root). This is the OPPOSITE of what the numeric level value might
    # suggest at a glance; confirmed by a 100%-consistent (507/507)
    # parent_region-index-falls-inside-parent's-child-span check.
    level_order = [2, 4, 6, 8]
    checked = 0
    consistent = 0
    level_mismatches = 0
    for lvl in level_order:
        regs = by_level[lvl]
        for r in regs:
            if r.is_dummy or r.parent_region == 0xFFFF:
                continue
            li = level_order.index(lvl)
            if li == len(level_order) - 1:
                continue
            parent_level = level_order[li + 1]
            prego = by_level.get(parent_level, [])
            checked += 1
            if r.parent_region < len(prego):
                p = prego[r.parent_region]
                lo, hi = p.first_child_region, p.first_child_region + p.n_child_regions
                if lo <= r.region_no < hi:
                    consistent += 1
            else:
                level_mismatches += 1
    print(f"\nparent/child linkage check: {consistent}/{checked} regions' parent_region index "
          f"falls inside its claimed parent's [first_child_region, +n_child_regions) span "
          f"({level_mismatches} out-of-range parent indices)")

    print(f"\n=== Q2/Q3: boundary nodes vs parent region node sets (sample) ===")
    print(f"(decoding node+coord tables for up to {args.max_regions_decoded} regions; "
          "this is a scoped sample, not the full population -- full decode of all "
          f"{len(rf.regions)} regions' node tables is out of budget for this study)")

    # Build quick lookup: for a given (level, region_no) get its RegionMgmtRecord
    lookup = {(r.level, r.region_no): r for r in rf.regions}

    decoded_cache: dict[tuple[int, int], list] = {}

    def get_nodes(level, region_no):
        key = (level, region_no)
        if key in decoded_cache:
            return decoded_cache[key]
        r = lookup.get(key)
        if r is None or r.is_dummy or r.rp_dsa == 0xFFFFFFFF:
            decoded_cache[key] = None
            return None
        try:
            nodes = region_node_coords(disc, r, rf)
        except Exception as e:
            nodes = None
        decoded_cache[key] = nodes
        return nodes

    # Sample: pick child regions with data at each real level (2,4,6) that
    # have a non-null parent, walk up.
    n_sampled = 0
    boundary_fraction_by_level = {}
    match_total = 0
    match_hit = 0
    for lvl in level_order:
        regs = [r for r in by_level[lvl] if not r.is_dummy and r.rp_dsa != 0xFFFFFFFF]
        sample = regs[: max(1, args.max_regions_decoded // max(1, len(level_order)))]
        fracs = []
        for r in sample:
            if n_sampled >= args.max_regions_decoded:
                break
            nodes = get_nodes(lvl, r.region_no)
            n_sampled += 1
            if nodes is None:
                continue
            nb = sum(1 for _, _, b in nodes if b)
            fracs.append(nb / len(nodes) if nodes else 0.0)

            if r.parent_region != 0xFFFF:
                li = level_order.index(lvl)
                if li < len(level_order) - 1:
                    parent_level = level_order[li + 1]
                    if r.parent_region < len(by_level.get(parent_level, [])):
                        prec = by_level[parent_level][r.parent_region]
                        pnodes = get_nodes(parent_level, prec.region_no)
                        if pnodes:
                            # coordinate match within ~1 grid cell tolerance
                            ptol = 0.01
                            pset = [(plat, plon) for plat, plon, _ in pnodes]
                            for lat, lon, is_b in nodes:
                                if not is_b:
                                    continue
                                match_total += 1
                                if any(abs(lat - plat) < ptol and abs(lon - plon) < ptol for plat, plon in pset):
                                    match_hit += 1
        if fracs:
            boundary_fraction_by_level[lvl] = (sum(fracs) / len(fracs), len(fracs))

    print(f"regions actually decoded (node+coord tables): {sum(1 for v in decoded_cache.values() if v is not None)}")
    for lvl, (frac, n) in sorted(boundary_fraction_by_level.items()):
        print(f"  level={lvl}: mean is_boundary fraction={frac:.3f} over {n} regions")
    if match_total:
        print(f"\nboundary-node -> parent-region coordinate match: {match_hit}/{match_total} "
              f"({100*match_hit/match_total:.1f}%) of a child region's is_boundary-flagged "
              "nodes have a coordinate match (within ~0.01 deg / ~1.1km, i.e. within one "
              "coarse node-coord grid cell) in their parent region's own node set")
    else:
        print("\nno boundary-node/parent comparisons were possible in this sample "
              "(either no boundary nodes found, or no decodable parent)")

    disc.close()


if __name__ == "__main__":
    main()
