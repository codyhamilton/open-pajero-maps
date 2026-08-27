#!/usr/bin/env python3
"""Ch.10.5/10.5.1 "ext" (Extended Route Planning Data Frame) census.

Decodes the raw bytes of every populated ext slot across all real regions
on the reference disc, per the confirmed Ch.10.5.1 layout:

    [12B MID  User Identification ID]
    [ 4B N    Data Identification Code]
    [ n B     vendor-defined payload, size = slot_size - 16]

(spec/format_english/pdf/1000122e.pdf, Ch.10.5/10.5.1 -- "used for the
extended data defined with META", i.e. genuinely vendor/meta-defined and
not specified further in the archived spec set.)

This is throwaway analysis code (per docs/phases/01-format-analysis.md
conventions, kept under parser/ since it's a useful, rerunnable script,
not a one-off scratch file). It does not modify the parser package.

Usage:
    python3 parser/analyze_ext_frames.py --alldata /path/to/ALLDATA.KWI
"""
from __future__ import annotations

import argparse
import collections
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from kiwiw.disc import AllData
from kiwiw.misc import DISC_STAMP_12B
from kiwiw.route_planning import (
    NO_DATA_DSA,
    d32,
    parse_region_frame,
    parse_rp_frame,
)
from kiwiw.volume import getsector


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--alldata", required=True)
    args = ap.parse_args()

    disc = AllData(args.alldata)
    rf = parse_region_frame(disc)

    real_regions = [r for r in rf.regions if not r.is_dummy]
    print(f"Real (non-dummy) region records: {len(real_regions)}")

    mids = collections.Counter()
    slot_count_hist = collections.Counter()
    ext_size_hist = collections.Counter()
    dataid_by_slotpos = collections.defaultdict(collections.Counter)
    dataid_sequences = collections.Counter()  # per-region tuple of data-id codes in slot order
    payload_len_hist = collections.Counter()
    payload_content = collections.Counter()  # hex of payload, to spot constants
    per_region_rows = []
    slots_per_level = collections.defaultdict(lambda: [0, 0])  # level -> [n_regions, n_populated_slots]
    n_regions_with_ext = 0
    n_total_ext_slots_possible = 0
    n_total_ext_slots_populated = 0
    mid_matches_disc_stamp = 0
    mid_all_ff = 0
    boundary_vs_ext = collections.Counter()  # has_children / is_leaf vs has_ext

    for rec in real_regions:
        lmr = next(l for l in rf.levels if l.level == rec.level)
        if rec.rp_dsa == NO_DATA_DSA or rec.rp_size_ls == 0:
            continue
        disc._fh.seek(getsector(rec.rp_dsa, disc.sector_sz, disc.logical_sz))
        buf = disc._fh.read(rec.rp_size_ls * disc.logical_sz)
        f = parse_rp_frame(buf, lmr.n_basic_rp_frames, lmr.n_ext_rp_frames)

        n_total_ext_slots_possible += len(f.ext)
        populated = [s for s in f.ext if s.size > 0]
        slot_count_hist[len(populated)] += 1
        slots_per_level[rec.level][0] += 1
        slots_per_level[rec.level][1] += len(populated)
        if populated:
            n_regions_with_ext += 1
        n_total_ext_slots_populated += len(populated)

        has_children = rec.n_child_regions > 0
        boundary_vs_ext[(has_children, bool(populated))] += 1

        dataid_seq = []
        for slot_i, s in enumerate(populated):
            if s.offset == 0xFFFFFFFF or s.offset + 16 > len(buf):
                continue
            mid = buf[s.offset : s.offset + 12]
            dataid = int.from_bytes(buf[s.offset + 12 : s.offset + 16], "big")
            payload = buf[s.offset + 16 : s.offset + s.size]

            mids[mid.hex()] += 1
            if mid == DISC_STAMP_12B:
                mid_matches_disc_stamp += 1
            if mid == b"\xff" * 12:
                mid_all_ff += 1
            ext_size_hist[s.size] += 1
            dataid_by_slotpos[slot_i][dataid] += 1
            payload_len_hist[len(payload)] += 1
            payload_content[payload.hex()] += 1
            dataid_seq.append(dataid)

            per_region_rows.append(dict(
                level=rec.level, region_no=rec.region_no, slot_i=slot_i,
                n_slots=len(populated), mid=mid.hex(), dataid=dataid,
                payload_len=len(payload), payload_hex=payload.hex(),
                n_nodes=f.node_header.n_nodes if f.node_header else None,
                n_links=f.node_header.n_links if f.node_header else None,
                has_children=has_children, n_child_regions=rec.n_child_regions,
                parent_region=rec.parent_region,
                lat_top=rec.lat_top, lat_bottom=rec.lat_bottom,
                lon_left=rec.lon_left, lon_right=rec.lon_right,
            ))
        dataid_sequences[tuple(dataid_seq)] += 1

    print(f"\nTotal ext slot-instances possible (n_ext summed over all real regions): {n_total_ext_slots_possible}")
    print(f"Total ext slot-instances populated (size>0): {n_total_ext_slots_populated}")
    print(f"Regions with >=1 populated ext slot: {n_regions_with_ext} / {len(real_regions)} "
          f"({100*n_regions_with_ext/len(real_regions):.1f}%)")

    print("\nPopulated-slot-count-per-region histogram:")
    for k in sorted(slot_count_hist):
        print(f"  {k} populated slots: {slot_count_hist[k]} regions")

    print("\nPopulated slots per level (n_regions, n_populated_slots):")
    for lvl in sorted(slots_per_level):
        nreg, nslot = slots_per_level[lvl]
        print(f"  level {lvl}: {nreg} regions, {nslot} populated slots "
              f"({nslot/nreg:.3f} avg/region)")

    print(f"\nDistinct MID (User Identification ID) values seen: {len(mids)}")
    for mid, cnt in mids.most_common(10):
        print(f"  {mid}: {cnt}")
    print(f"MID == known cross-file DISC_STAMP_12B: {mid_matches_disc_stamp} / {n_total_ext_slots_populated}")
    print(f"MID == all-0xFF sentinel: {mid_all_ff} / {n_total_ext_slots_populated}")

    print(f"\nExt slot total size (16B header + payload) histogram (top 10):")
    for sz, cnt in ext_size_hist.most_common(10):
        print(f"  size={sz}: {cnt}")

    print(f"\nPayload length (size-16) histogram (top 10):")
    for ln, cnt in payload_len_hist.most_common(10):
        print(f"  payload_len={ln}: {cnt}")

    print(f"\nDistinct payload byte-contents (top 10 by frequency):")
    for hexval, cnt in payload_content.most_common(10):
        shown = hexval if len(hexval) <= 64 else hexval[:64] + "..."
        print(f"  {cnt:5d}x  {shown}")
    print(f"Total distinct payload contents: {len(payload_content)}")

    print(f"\nData Identification Code, by slot position (0-indexed within a region's populated slots):")
    for slot_i in sorted(dataid_by_slotpos):
        c = dataid_by_slotpos[slot_i]
        print(f"  slot {slot_i}: {len(c)} distinct codes, top 5: {c.most_common(5)}")

    print(f"\nPer-region Data-ID-code sequences (top 10 patterns):")
    for seq, cnt in dataid_sequences.most_common(10):
        print(f"  {cnt:5d}x  {seq}")

    print(f"\nBoundary-node (has_children) vs has-ext-slot cross-tab:")
    for k, v in sorted(boundary_vs_ext.items()):
        print(f"  has_children={k[0]}, has_ext={k[1]}: {v}")

    # Dump full per-slot rows to CSV for further offline correlation.
    import csv
    out_path = "/tmp/claude-1000/-home-codyh-workspace-open-pajero-maps/ff6e712c-d0ef-45a6-b3a7-d1ab7fec5ea8/scratchpad/ext_frames.csv"
    if per_region_rows:
        with open(out_path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(per_region_rows[0].keys()))
            w.writeheader()
            w.writerows(per_region_rows)
        print(f"\nWrote {len(per_region_rows)} per-slot rows to {out_path}")


if __name__ == "__main__":
    main()
