#!/usr/bin/env python3
"""Whole-`ALLDATA.KWI`-file assembly round-trip harness.

Unlike `roundtrip_alldata_header.py` (container/mesh layer only: Data
Volume + MHT + PDMDH/LMR/BSMR/BMT, at their real, original file offsets)
and `roundtrip_parcel_content.py` (4 hand-picked coordinates' block record
+ Map Frame), this harness exercises `kiwiw/alldata_writer.py`'s
allocation/layout logic across one or more *whole block sets* -- every
real block, every leaf parcel (and every road/background/name sub-frame)
they reach -- and checks two distinct things:

1. "In-place" mode (`assemble_inplace`): re-emit every structure at the
   *exact* file offset the real disc used, and byte-diff against the real
   file there. A pass proves the allocation *rule* is understood well
   enough to reproduce the original's own layout choices, not just that
   the structural encoding is correct (which the existing per-piece
   harnesses already established).

2. "De novo" mode (`assemble_denovo`): pack the same content into a
   brand-new, freshly chosen contiguous layout with every cross-reference
   pointer recomputed, then re-parse that fresh buffer with the existing
   read-side parser and confirm it decodes to the same semantic content
   as the original. This is NOT a byte-identity claim against the real
   file (the layout is deliberately different) -- it is a self-consistency
   claim: the writer's own new offsets are internally coherent.

Default target: every real (non-empty) block set at level 8 (6 block
sets, 6 blocks, 78 leaf parcels on the reference disc) -- deliberately a
whole level's real content, not a hand-picked coordinate. Pass `--level`/
`--blocksets` to point at a different region (see docs/phases/02-roundtrip.md
for the survey of candidate regions across all 7 levels).
"""
from __future__ import annotations

import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwiw import alldata_writer as aw
from kiwiw import parcel, parcel_mgmt, volume

DEFAULT_ROOT = "/run/media/codyh/464210-8480"


def _diff_report(name: str, offset: int, expected: bytes, actual: bytes) -> str:
    if expected == actual:
        return f"PASS: {name} @ {offset} ({len(actual)} bytes) byte-identical"
    if len(expected) != len(actual):
        return (f"FAIL: {name} @ {offset}: length mismatch "
                f"(real {len(expected)} vs rebuilt {len(actual)})")
    for i in range(len(actual)):
        if expected[i] != actual[i]:
            return (f"FAIL: {name} @ {offset}: first diff at +{i} "
                    f"(real={expected[i]:#04x} rebuilt={actual[i]:#04x})")
    return f"FAIL: {name} @ {offset}: unexpected byte mismatch"  # unreachable


def run_inplace(region: aw.LoadedRegion, real_bytes: bytes) -> tuple[int, int]:
    checks = aw.assemble_inplace(region)
    n_pass = n_fail = 0
    for c in checks:
        expected = real_bytes[c.offset : c.offset + len(c.rebuilt)]
        report = _diff_report(c.name, c.offset, expected, c.rebuilt)
        print(report)
        if report.startswith("PASS"):
            n_pass += 1
        else:
            n_fail += 1
    return n_pass, n_fail


def run_denovo(region: aw.LoadedRegion) -> tuple[int, int]:
    """Re-parse the de novo buffer with the real read-side parser and
    confirm every relocated block/leaf still resolves to the same
    semantic content as the original decode. Returns (n_ok, n_bad)."""
    result = aw.assemble_denovo(region)
    buf = io.BytesIO(result.buf)

    raw_hdr = buf.read(volume.DATAVOL_SIZE)
    hdr2 = volume.parse_volume_header(raw_hdr)
    raw_mht = buf.read(volume.MHT_SIZE)
    mht2 = volume.parse_management_header_table(raw_mht)
    prdm2 = mht2.entries[0]
    off2 = volume.getsector(prdm2.dsa, hdr2.sector_size, hdr2.logical_sector_size)
    if off2 != result.pdmdh_offset:
        print(f"FAIL: de novo MHT entry 0 resolves to {off2}, expected {result.pdmdh_offset}")
        return 0, 1
    buf.seek(off2)
    raw_pdmdh = buf.read(prdm2.size * hdr2.logical_sector_size)
    pdmdh2 = volume.parse_pdmdh_full(raw_pdmdh)

    lmr = next(l for l in pdmdh2.levels if l.level == region.level)

    n_ok = n_bad = 0
    for block in region.blocks:
        table = pdmdh2.bmt_tables[block.bmt_table_ordinal]
        bmt_entry = table.entries[block.entry_index]
        new_off = result.block_offsets[id(block)]
        boff = volume.getsector(bmt_entry.dsa, hdr2.sector_size, hdr2.logical_sector_size)
        if boff != new_off:
            print(f"FAIL: block (table={block.bmt_table_ordinal}, entry={block.entry_index}) "
                  f"resolves to {boff}, expected {new_off}")
            n_bad += 1
            continue
        buf.seek(boff)
        bbuf = buf.read(bmt_entry.size * hdr2.logical_sector_size)
        root2 = parcel_mgmt.parse_parcel_mgmt_record(bbuf, lmr)
        if root2.tail_raw == block.root.tail_raw and len(root2.entries) == len(block.root.entries):
            print(f"PASS: block (table={block.bmt_table_ordinal}, entry={block.entry_index}) "
                  f"re-parses consistently at new offset {new_off}")
            n_ok += 1
        else:
            print(f"FAIL: block (table={block.bmt_table_ordinal}, entry={block.entry_index}) "
                  f"re-parsed content differs from original decode")
            n_bad += 1

        for leaf in block.leaves:
            new_leaf_off = result.leaf_offsets[id(leaf.entry)]
            buf.seek(new_leaf_off)
            mapdata2 = buf.read(leaf.length)
            p2 = parcel.decode_parcel(leaf.parcel.location, mapdata2,
                                       n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
            same = (
                p2.frame.tail_raw == leaf.parcel.frame.tail_raw
                and p2.frame.mfde_raw == leaf.parcel.frame.mfde_raw
                and (p2.road.links if p2.road else None)
                    == (leaf.parcel.road.links if leaf.parcel.road else None)
                and (p2.background.shapes if p2.background else None)
                    == (leaf.parcel.background.shapes if leaf.parcel.background else None)
                and (p2.name.records if p2.name else None)
                    == (leaf.parcel.name.records if leaf.parcel.name else None)
            )
            if same:
                print(f"PASS: parcel @ real sector {leaf.entry.dsa} "
                      f"re-parses consistently at new offset {new_leaf_off}")
                n_ok += 1
            else:
                print(f"FAIL: parcel @ real sector {leaf.entry.dsa} "
                      f"re-parsed content differs from original decode")
                n_bad += 1

    return n_ok, n_bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--level", type=int, default=8)
    ap.add_argument("--blocksets", type=int, nargs="+", default=[0, 1, 2, 4, 5, 6])
    args = ap.parse_args()

    alldata_path = os.path.join(args.root, "ALLDATA.KWI")
    if not os.path.exists(alldata_path):
        print(f"SKIP: {alldata_path} not present (disc not mounted)")
        return 0

    print(f"Loading level {args.level}, block sets {args.blocksets} from {alldata_path} ...")
    region = aw.load_region(alldata_path, args.level, args.blocksets)
    n_leaves = sum(len(b.leaves) for b in region.blocks)
    print(f"Loaded {len(region.blocks)} block(s), {n_leaves} leaf parcel(s).\n")

    with open(alldata_path, "rb") as fh:
        real_bytes = fh.read()

    print("=== In-place (original layout) byte-identity check ===")
    ip_pass, ip_fail = run_inplace(region, real_bytes)
    print(f"\nIn-place: {ip_pass}/{ip_pass + ip_fail} regions byte-identical.\n")

    print("=== De novo (freshly allocated layout) re-parse self-consistency check ===")
    dn_ok, dn_bad = run_denovo(region)
    print(f"\nDe novo: {dn_ok}/{dn_ok + dn_bad} relocated structures re-parse consistently.\n")

    ok = ip_fail == 0 and dn_bad == 0
    print("OVERALL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
