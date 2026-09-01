"""Phase 2 round-trip regression tests for whole-`ALLDATA.KWI`-file
assembly: `kiwiw/alldata_writer.py`'s allocation/layout logic, exercised
across whole real block sets (every block, every leaf parcel they reach)
rather than the 4 hand-picked coordinates `test_roundtrip_parcel_content.py`
checks.

Two claims, kept explicitly distinct (see docs/phases/02-roundtrip.md):

- "In-place" (`assemble_inplace`): reproducing the original disc's own
  file offsets is byte-identical against the real file.
- "De novo" (`assemble_denovo`): packing the same content into a
  brand-new contiguous layout with recomputed pointers is only checked by
  re-parsing the result and confirming it decodes to the same content --
  NOT byte-identical against the real file (the layout is deliberately
  different).

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips
if not present, same convention as test_roundtrip_parcel_content.py.
"""
import copy
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import alldata_writer as aw
from kiwiw import parcel, parcel_mgmt, volume

ROOT = "/run/media/codyh/464210-8480"
ALLDATA_PATH = os.path.join(ROOT, "ALLDATA.KWI")

# Level 8, every real block set on the reference disc: 6 block sets, 6
# blocks, 78 leaf parcels -- a whole level's real content, not a single
# hand-picked coordinate. (See docs/phases/02-roundtrip.md for the survey
# of candidate regions across all 7 levels and why this one was chosen:
# small enough to be a fast regression test, large enough to be a
# meaningful "whole region" rather than one point.)
LEVEL = 8
BLOCKSETS = [0, 1, 2, 4, 5, 6]

# Small, fast, real regression subsets at levels 4 and 2, added 2026-08-28
# when whole-file assembly coverage was extended from levels 6/8 only to
# 0/2/4 (see docs/phases/02-roundtrip.md for the full-population and
# level-0-sample runs -- those are far too large/slow for a pytest
# regression suite and were instead run ad hoc via
# `roundtrip_alldata_full.py --level 4/2/0 --blocksets ...`, with every
# check passing over the FULL level-4 population (20/20 block sets),
# the FULL level-2 population (63/63 block sets), and an 18-block-set
# level-0 sample). These two small subsets exist only so a plain `pytest`
# run also exercises levels 4 and 2, not just level 8.
LEVEL4 = 4
BLOCKSETS4 = [1, 2]  # 2 of the 20 real level-4 block sets

LEVEL2 = 2
BLOCKSETS2 = [2, 3]  # 2 of the 63 real level-2 block sets


def _open_region(level=LEVEL, blocksets=BLOCKSETS):
    if not os.path.exists(ALLDATA_PATH):
        print(f"SKIP: {ALLDATA_PATH} not present (disc not mounted)")
        return None
    return aw.load_region(ALLDATA_PATH, level, blocksets)


# ---------------------------------------------------------------------
# Positive: in-place byte-identity, across a whole level's real content.
# ---------------------------------------------------------------------

def _check_inplace_byte_identical(region, level, blocksets):
    with open(ALLDATA_PATH, "rb") as fh:
        real_bytes = fh.read()

    checks = aw.assemble_inplace(region)
    n_pass = 0
    for c in checks:
        expected = real_bytes[c.offset : c.offset + len(c.rebuilt)]
        ok = expected == c.rebuilt
        assert ok, f"{c.name} @ {c.offset}: not byte-identical"
        n_pass += 1
    print(f"PASS: {n_pass}/{len(checks)} in-place regions byte-identical "
          f"(level {level}, block sets {blocksets})")


def test_inplace_byte_identical():
    region = _open_region()
    if region is None:
        return
    _check_inplace_byte_identical(region, LEVEL, BLOCKSETS)


def test_inplace_byte_identical_level4():
    region = _open_region(LEVEL4, BLOCKSETS4)
    if region is None:
        return
    _check_inplace_byte_identical(region, LEVEL4, BLOCKSETS4)


def test_inplace_byte_identical_level2():
    region = _open_region(LEVEL2, BLOCKSETS2)
    if region is None:
        return
    _check_inplace_byte_identical(region, LEVEL2, BLOCKSETS2)


# ---------------------------------------------------------------------
# Positive: de novo re-parse self-consistency, same whole-level region.
# ---------------------------------------------------------------------

def _check_denovo_reparse_self_consistent(region, level, blocksets):
    result = aw.assemble_denovo(region)
    buf = io.BytesIO(result.buf)

    raw_hdr = buf.read(volume.DATAVOL_SIZE)
    hdr2 = volume.parse_volume_header(raw_hdr)
    raw_mht = buf.read(volume.MHT_SIZE)
    mht2 = volume.parse_management_header_table(raw_mht)
    prdm2 = mht2.entries[0]
    off2 = volume.getsector(prdm2.dsa, hdr2.sector_size, hdr2.logical_sector_size)
    assert off2 == result.pdmdh_offset, "de novo MHT entry 0 does not resolve to the PDMDH blob"
    buf.seek(off2)
    raw_pdmdh = buf.read(prdm2.size * hdr2.logical_sector_size)
    pdmdh2 = volume.parse_pdmdh_full(raw_pdmdh)
    lmr = next(l for l in pdmdh2.levels if l.level == region.level)

    n_checked = 0
    for block in region.blocks:
        table = pdmdh2.bmt_tables[block.bmt_table_ordinal]
        bmt_entry = table.entries[block.entry_index]
        new_off = result.block_offsets[id(block)]
        boff = volume.getsector(bmt_entry.dsa, hdr2.sector_size, hdr2.logical_sector_size)
        assert boff == new_off, "relocated BmtEntry.dsa does not resolve to the new block offset"
        buf.seek(boff)
        bbuf = buf.read(bmt_entry.size * hdr2.logical_sector_size)
        root2 = parcel_mgmt.parse_parcel_mgmt_record(bbuf, lmr)
        assert root2.tail_raw == block.root.tail_raw
        assert len(root2.entries) == len(block.root.entries)
        n_checked += 1

        for leaf in block.leaves:
            new_leaf_off = result.leaf_offsets[id(leaf.entry)]
            buf.seek(new_leaf_off)
            mapdata2 = buf.read(leaf.length)
            p2 = parcel.decode_parcel(leaf.parcel.location, mapdata2,
                                       n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
            assert p2.frame.tail_raw == leaf.parcel.frame.tail_raw
            assert p2.frame.mfde_raw == leaf.parcel.frame.mfde_raw
            assert ((p2.road.links if p2.road else None)
                    == (leaf.parcel.road.links if leaf.parcel.road else None))
            assert ((p2.background.shapes if p2.background else None)
                    == (leaf.parcel.background.shapes if leaf.parcel.background else None))
            assert ((p2.name.records if p2.name else None)
                    == (leaf.parcel.name.records if leaf.parcel.name else None))
            n_checked += 1

    print(f"PASS: {n_checked} de novo relocated structures re-parse consistently "
          f"(level {level}, block sets {blocksets})")


def test_denovo_reparse_self_consistent():
    region = _open_region()
    if region is None:
        return
    _check_denovo_reparse_self_consistent(region, LEVEL, BLOCKSETS)


def test_denovo_reparse_self_consistent_level4():
    region = _open_region(LEVEL4, BLOCKSETS4)
    if region is None:
        return
    _check_denovo_reparse_self_consistent(region, LEVEL4, BLOCKSETS4)


def test_denovo_reparse_self_consistent_level2():
    region = _open_region(LEVEL2, BLOCKSETS2)
    if region is None:
        return
    _check_denovo_reparse_self_consistent(region, LEVEL2, BLOCKSETS2)


# ---------------------------------------------------------------------
# Negative controls: perturb one decoded/raw field and confirm the
# assembler correctly fails to reproduce the original / to re-parse
# identically.
# ---------------------------------------------------------------------

def test_negative_control_inplace_road_link_raw_bytes():
    """Flipping a byte inside a RoadLink.raw_bytes reachable from the
    whole-region load must break the in-place byte-identity check
    (confirms the region-scale assembler still actually writes
    `raw_bytes`, not that some vacuous code path always reports PASS)."""
    region = _open_region()
    if region is None:
        return
    with open(ALLDATA_PATH, "rb") as fh:
        real_bytes = fh.read()

    for block in region.blocks:
        for leaf in block.leaves:
            if leaf.parcel.road is not None and leaf.parcel.road.links:
                region_bad = copy.deepcopy(region)
                bad_block = next(b for b in region_bad.blocks
                                  if b.entry_index == block.entry_index
                                  and b.original_offset == block.original_offset)
                bad_leaf = next(l for l in bad_block.leaves
                                 if l.original_offset == leaf.original_offset)
                link = bad_leaf.parcel.road.links[0]
                link.raw_bytes = bytes([link.raw_bytes[0] ^ 0xFF]) + link.raw_bytes[1:]

                checks = aw.assemble_inplace(region_bad)
                target = next(c for c in checks if c.offset == leaf.original_offset)
                expected = real_bytes[target.offset : target.offset + len(target.rebuilt)]
                assert expected != target.rebuilt, (
                    "perturbed RoadLink.raw_bytes should NOT round-trip identically")
                print("PASS: negative control -- perturbed RoadLink.raw_bytes "
                      "correctly breaks the in-place round-trip")
                return
    print("SKIP: no leaf parcel in the loaded region had a road frame with links to perturb")


def test_negative_control_denovo_tail_raw():
    """Truncating a block's ParcelMgmtRecord.tail_raw must make the de
    novo buffer re-parse to *different* tail_raw than the original decode
    (confirms tail_raw is actually written at the relocated offset, not
    silently dropped)."""
    region = _open_region()
    if region is None:
        return

    block = next((b for b in region.blocks if b.root.tail_raw), None)
    assert block is not None, "expected at least one loaded block with a non-empty tail_raw"

    region_bad = copy.deepcopy(region)
    bad_block = next(b for b in region_bad.blocks
                      if b.entry_index == block.entry_index
                      and b.original_offset == block.original_offset)
    bad_block.root.tail_raw = (bytes([bad_block.root.tail_raw[0] ^ 0xFF])
                                + bad_block.root.tail_raw[1:])

    result = aw.assemble_denovo(region_bad)
    buf = io.BytesIO(result.buf)
    raw_hdr = buf.read(volume.DATAVOL_SIZE)
    hdr2 = volume.parse_volume_header(raw_hdr)
    raw_mht = buf.read(volume.MHT_SIZE)
    mht2 = volume.parse_management_header_table(raw_mht)
    prdm2 = mht2.entries[0]
    off2 = volume.getsector(prdm2.dsa, hdr2.sector_size, hdr2.logical_sector_size)
    buf.seek(off2)
    raw_pdmdh = buf.read(prdm2.size * hdr2.logical_sector_size)
    pdmdh2 = volume.parse_pdmdh_full(raw_pdmdh)
    lmr = next(l for l in pdmdh2.levels if l.level == region_bad.level)

    table = pdmdh2.bmt_tables[bad_block.bmt_table_ordinal]
    bmt_entry = table.entries[bad_block.entry_index]
    new_off = result.block_offsets[id(bad_block)]
    boff = volume.getsector(bmt_entry.dsa, hdr2.sector_size, hdr2.logical_sector_size)
    assert boff == new_off
    buf.seek(boff)
    bbuf = buf.read(bmt_entry.size * hdr2.logical_sector_size)
    root2 = parcel_mgmt.parse_parcel_mgmt_record(bbuf, lmr)
    assert root2.tail_raw != block.root.tail_raw, (
        "perturbed tail_raw should NOT re-parse identically to the original decode")
    print("PASS: negative control -- perturbed ParcelMgmtRecord.tail_raw "
          "correctly breaks de novo re-parse consistency")


if __name__ == "__main__":
    test_inplace_byte_identical()
    test_inplace_byte_identical_level4()
    test_inplace_byte_identical_level2()
    test_denovo_reparse_self_consistent()
    test_denovo_reparse_self_consistent_level4()
    test_denovo_reparse_self_consistent_level2()
    test_negative_control_inplace_road_link_raw_bytes()
    test_negative_control_denovo_tail_raw()
