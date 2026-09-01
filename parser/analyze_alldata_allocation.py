#!/usr/bin/env python3
"""Allocation-rule survey across `ALLDATA.KWI` levels 0/2/4, extending the
level-6/8 evidence in `docs/phases/02-roundtrip.md`'s "Whole-file
ALLDATA.KWI assembly" section from "one region's worth of evidence" to a
much larger real-disc sample.

Two questions, both asked of the SAME loaded regions used by
`roundtrip_alldata_full.py` (`kiwiw.alldata_writer.load_region`), so the
"real offsets" analyzed here are exactly the ones the round-trip harness
also byte-diffs -- this script does not introduce a second, independent
notion of "the real layout":

1. **Block-index-order packing.** Within one block set, are the real
   blocks (in Block Management Table entry order) packed back-to-back
   with zero gap (`offset[i+1] == offset[i] + length[i]`)? The level-6/8
   pass observed this on ONE region; this reports it over every block set
   loaded here.

2. **Leaf (Map Frame) placement order.** No allocation rule was
   previously found for this. This script checks several candidate
   traversal orders against each block's real leaf offsets and reports,
   per candidate, how often consecutive real offsets are (a) monotonic
   increasing, (b) tightly contiguous (zero gap), looking for ANY order
   that explains the real layout -- not just re-stating "still not
   contiguous."

Usage:
    python3 analyze_alldata_allocation.py --level 4 --blocksets <all non-empty>
    python3 analyze_alldata_allocation.py --level 2 --blocksets <all non-empty>
    python3 analyze_alldata_allocation.py --level 0 --blocksets <sample>
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwiw import alldata_writer as aw
from kiwiw import volume

DEFAULT_ROOT = "/run/media/codyh/464210-8480"


def list_nonempty_blocksets(path: str, level: int) -> list[tuple[int, int]]:
    """Return [(blockset_index, n_real_blocks), ...] for every non-empty
    block set at `level`, sorted by blockset_index."""
    with open(path, "rb") as fh:
        raw_header = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_header)
        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        prdm = mht.entries[0]
        prdm_off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        prdm_size = prdm.size * hdr.logical_sector_size
        fh.seek(prdm_off)
        raw_prdm = fh.read(prdm_size)
        pdmdh = volume.parse_pdmdh_full(raw_prdm)

    rows = []
    for t in pdmdh.bmt_tables:
        bs = pdmdh.blocksets[t.blockset_ordinal]
        if bs.level != level:
            continue
        n_real = sum(1 for e in t.entries if e.dsa != 0xFFFFFFFF and e.size)
        if n_real:
            rows.append((bs.blockset_index, n_real))
    rows.sort()
    return rows


# ---------------------------------------------------------------------
# Question 1: block-index-order packing
# ---------------------------------------------------------------------

def analyze_block_packing(region: aw.LoadedRegion) -> dict:
    """Group loaded blocks by (bmt_table_ordinal), sort by entry_index
    (== Block Management Table order == the order blocksets are walked
    on the real disc), and check zero-gap contiguity between consecutive
    real blocks."""
    by_table: dict[int, list[aw.LoadedBlock]] = {}
    for b in region.blocks:
        by_table.setdefault(b.bmt_table_ordinal, []).append(b)

    n_blocksets = 0
    n_blocksets_clean = 0
    exceptions = []
    for table_ordinal, blocks in by_table.items():
        blocks_sorted = sorted(blocks, key=lambda b: b.entry_index)
        n_blocksets += 1
        clean = True
        for a, c in zip(blocks_sorted, blocks_sorted[1:]):
            expected = a.original_offset + a.length
            if c.original_offset != expected:
                clean = False
                exceptions.append({
                    "table_ordinal": table_ordinal,
                    "entry_a": a.entry_index, "entry_c": c.entry_index,
                    "expected_offset": expected, "actual_offset": c.original_offset,
                    "gap": c.original_offset - expected,
                })
        if clean:
            n_blocksets_clean += 1
    return {
        "n_blocksets": n_blocksets,
        "n_blocksets_clean": n_blocksets_clean,
        "exceptions": exceptions,
    }


# ---------------------------------------------------------------------
# Question 2: leaf placement order -- try several candidate orderings
# ---------------------------------------------------------------------

def _leaf_orderings(block: aw.LoadedBlock) -> dict[str, list[aw.LoadedLeaf]]:
    """Candidate traversal orders for one block's leaves, each a
    plausible "the mastering tool wrote them in this order" hypothesis."""
    leaves = block.leaves
    orderings = {
        "walk_order": list(leaves),  # order _walk_tree appended them (DFS, row-major-narrowing)
        "dsa_order": sorted(leaves, key=lambda l: l.entry.dsa),
        "size_order": sorted(leaves, key=lambda l: l.entry.size),
        "geo_lat_then_lon": sorted(
            leaves, key=lambda l: (l.bounds.lat_lo, l.bounds.lon_lo)),
        "geo_lon_then_lat": sorted(
            leaves, key=lambda l: (l.bounds.lon_lo, l.bounds.lat_lo)),
    }
    return orderings


def analyze_leaf_placement(region: aw.LoadedRegion) -> dict:
    """For each block and each candidate ordering, check whether
    consecutive real offsets in that order are (a) monotonic increasing,
    (b) exactly contiguous (zero gap)."""
    order_names = None
    stats = {}  # order_name -> {"n_blocks":.., "n_monotonic":.., "n_contiguous":.., "total_pairs":.., "contiguous_pairs":..}
    per_block_examples = []

    for block in region.blocks:
        if len(block.leaves) < 2:
            continue
        orderings = _leaf_orderings(block)
        if order_names is None:
            order_names = list(orderings.keys())
            for name in order_names:
                stats[name] = dict(n_blocks=0, n_monotonic=0, n_contiguous=0,
                                    total_pairs=0, contiguous_pairs=0)
        example_row = {"entry_index": block.entry_index, "n_leaves": len(block.leaves)}
        for name, ordered in orderings.items():
            s = stats[name]
            s["n_blocks"] += 1
            offsets = [l.original_offset for l in ordered]
            lengths = [l.length for l in ordered]
            monotonic = all(offsets[i] < offsets[i + 1] for i in range(len(offsets) - 1))
            if monotonic:
                s["n_monotonic"] += 1
            n_pairs = len(offsets) - 1
            n_contig = sum(
                1 for i in range(n_pairs)
                if offsets[i] + lengths[i] == offsets[i + 1]
            )
            s["total_pairs"] += n_pairs
            s["contiguous_pairs"] += n_contig
            if n_contig == n_pairs:
                s["n_contiguous"] += 1
            example_row[name] = {"monotonic": monotonic, "contig_pairs": f"{n_contig}/{n_pairs}"}
        per_block_examples.append(example_row)

    return {"stats": stats, "examples": per_block_examples[:5]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--blocksets", type=int, nargs="+", required=True)
    args = ap.parse_args()

    alldata_path = os.path.join(args.root, "ALLDATA.KWI")
    if not os.path.exists(alldata_path):
        print(f"SKIP: {alldata_path} not present (disc not mounted)")
        return 0

    print(f"Loading level {args.level}, block sets {args.blocksets} ...")
    region = aw.load_region(alldata_path, args.level, args.blocksets)
    n_leaves = sum(len(b.leaves) for b in region.blocks)
    print(f"Loaded {len(region.blocks)} block(s), {n_leaves} leaf parcel(s).\n")

    print("=== Question 1: block-index-order packing ===")
    bp = analyze_block_packing(region)
    print(f"{bp['n_blocksets_clean']}/{bp['n_blocksets']} block sets: "
          f"all real blocks zero-gap contiguous in BMT-entry order")
    if bp["exceptions"]:
        print(f"  {len(bp['exceptions'])} exception(s), first 5:")
        for e in bp["exceptions"][:5]:
            print(f"    {e}")
    print()

    print("=== Question 2: leaf placement order candidates ===")
    lp = analyze_leaf_placement(region)
    for name, s in lp["stats"].items():
        pct_mono = 100 * s["n_monotonic"] / s["n_blocks"] if s["n_blocks"] else 0
        pct_contig_blocks = 100 * s["n_contiguous"] / s["n_blocks"] if s["n_blocks"] else 0
        pct_contig_pairs = (100 * s["contiguous_pairs"] / s["total_pairs"]
                             if s["total_pairs"] else 0)
        print(f"  {name:20s}: monotonic {s['n_monotonic']}/{s['n_blocks']} blocks "
              f"({pct_mono:.1f}%), fully-contiguous {s['n_contiguous']}/{s['n_blocks']} blocks "
              f"({pct_contig_blocks:.1f}%), pairwise-contiguous {s['contiguous_pairs']}/"
              f"{s['total_pairs']} ({pct_contig_pairs:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
