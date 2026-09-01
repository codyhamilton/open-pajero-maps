#!/usr/bin/env python3
"""Test the "2x2-tile Z-order" leaf-placement hypothesis discovered while
extending Phase 2's ALLDATA.KWI whole-file-assembly work to levels 0/2/4.

Hypothesis: within one block's flat top-level parcel grid (row-major,
raw flat index = row * grid_width + col, same indexing `mesh.py` already
uses), the REAL on-disc placement order of leaf Map Frames is not the raw
row-major walk order, but a "2x2-tile Z-order": group the grid into 2x2
tiles (tile row = row//2, tile col = col//2), visit tiles in row-major
tile order, and within each tile visit the up-to-4 real sub-cells in the
fixed order (0,0), (0,1), (1,0), (1,1) -- skipping any sub-cell that has
no real data. Only entries actually present (dsa != NO_DATA, size != 0,
no subrecord recursion) are included.

This script recomputes that predicted order purely from each block's own
Parcel Management Record entries (no offsets used), then compares it
against the REAL on-disc order (sorting the same leaves by their real
`original_offset`). A block "matches" if the two orderings are identical
element-for-element.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwiw import alldata_writer as aw

DEFAULT_ROOT = "/run/media/codyh/464210-8480"
NO_DATA = 0xFFFFFFFF


def predicted_2x2_zorder(root, grid_width: int) -> list[int]:
    real = []
    for i, e in enumerate(root.entries):
        if e.dsa != NO_DATA and e.size and e.subrecord is None:
            r, c = divmod(i, grid_width)
            real.append((r, c, i))
    present = {(r, c): i for r, c, i in real}
    tiles = sorted(set((r // 2, c // 2) for r, c, _ in real))
    order = []
    for tr, tc in tiles:
        for sr in (0, 1):
            for sc in (0, 1):
                key = (2 * tr + sr, 2 * tc + sc)
                if key in present:
                    order.append(present[key])
    return order


def has_recursion(root) -> bool:
    return any(e.subrecord is not None for e in root.entries)


def check_block(block: aw.LoadedBlock, grid_width: int):
    """Returns ("match"|"mismatch"|"skip_recursive"|"skip_too_few", details)."""
    root = block.root
    if has_recursion(root):
        return "skip_recursive", None
    leaves = block.leaves
    if len(leaves) < 2:
        return "skip_too_few", None
    flat_idx_of_entry = {id(e): i for i, e in enumerate(root.entries)}
    walk_flat_idx = [flat_idx_of_entry[id(l.entry)] for l in leaves]
    by_offset_flat_idx = [
        walk_flat_idx[i]
        for i in sorted(range(len(leaves)), key=lambda i: leaves[i].original_offset)
    ]
    predicted = predicted_2x2_zorder(root, grid_width)
    if predicted == by_offset_flat_idx:
        return "match", len(predicted)
    # find first divergence for diagnostics
    first_diff = next(
        (i for i in range(min(len(predicted), len(by_offset_flat_idx)))
         if predicted[i] != by_offset_flat_idx[i]), None)
    return "mismatch", {
        "n_predicted": len(predicted), "n_real": len(by_offset_flat_idx),
        "first_diff_at": first_diff,
        "predicted_around": predicted[max(0, (first_diff or 0) - 2):(first_diff or 0) + 3],
        "real_around": by_offset_flat_idx[max(0, (first_diff or 0) - 2):(first_diff or 0) + 3],
    }


def run(path: str, level: int, blocksets: list[int], grid_width: int) -> dict:
    region = aw.load_region(path, level, blocksets)
    tally = {"match": 0, "mismatch": 0, "skip_recursive": 0, "skip_too_few": 0}
    mismatches = []
    n_leaves_matched = 0
    for block in region.blocks:
        status, detail = check_block(block, grid_width)
        tally[status] += 1
        if status == "match":
            n_leaves_matched += detail
        if status == "mismatch":
            mismatches.append((block.bmt_table_ordinal, block.entry_index, detail))
    return {"level": level, "n_blocks": len(region.blocks), "tally": tally,
            "n_leaves_matched": n_leaves_matched, "mismatches": mismatches}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--blocksets", type=int, nargs="+", required=True)
    ap.add_argument("--grid-width", type=int, default=32,
                     help="1 + LMR.n_parcels_lng[0] for the target level (32 on this disc "
                          "for levels 0/2/4/6/8's parcel_type 0)")
    args = ap.parse_args()

    alldata_path = os.path.join(args.root, "ALLDATA.KWI")
    if not os.path.exists(alldata_path):
        print(f"SKIP: {alldata_path} not present (disc not mounted)")
        return 0

    result = run(alldata_path, args.level, args.blocksets, args.grid_width)
    t = result["tally"]
    print(f"Level {result['level']}, {result['n_blocks']} block(s) loaded:")
    print(f"  MATCH (2x2 Z-order predicts exact real order): {t['match']}")
    print(f"  MISMATCH: {t['mismatch']}")
    print(f"  skip (recursive/divided parcel, not tested): {t['skip_recursive']}")
    print(f"  skip (fewer than 2 leaves, order is vacuous): {t['skip_too_few']}")
    print(f"  total leaves covered by a MATCHing block: {result['n_leaves_matched']}")
    for table_ordinal, entry_index, detail in result["mismatches"][:5]:
        print(f"    MISMATCH block(table={table_ordinal}, entry={entry_index}): {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
