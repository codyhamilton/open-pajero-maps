#!/usr/bin/env python3
"""Standalone bytes-per-address-search-entry measurement.

Companion to `estimate_density.py` (roads/names). That study found KIWI-W's
road+name storage is not the bottleneck; this one measures the remaining
unknown -- the address/POI *search index* -- with the same rigor: exact
counts (full census where cheap, explicit sampling where not), poison-fill
discipline where it applies, and honest reporting of what is and is not
measured.

Does NOT modify any parser code. Uses `kiwiw.search_frame.StreetAddressIndex`
/ `PoiSearchIndex` exactly as validated by `demo_address_search.py` -- this
script adds nothing to the decode logic, only census/aggregation around it.

Usage:
    python3 estimate_address_density.py [--root /run/media/codyh/464210-8480]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.search_frame import (  # noqa: E402
    PoiSearchIndex,
    StreetAddressIndex,
    iter_matching_records,
    parse_matching_record,
)

DEFAULT_ROOT = "/run/media/codyh/464210-8480"

# Filename-prefix groups present under IDX/, so the "total index bytes"
# figure can be broken down rather than reported as one opaque blob. Only
# SADSR*/POISR* are decoded by search_frame.py / this script; the rest are
# listed for completeness (freeway search, intersection search, POI-area
# search, POI detail *text*, city/area name search, emergency-number
# search, zone selection) -- real IDX/ content this disc spends bytes on,
# but NOT what "address search index" means in the narrow sense, and NOT
# walked for entry counts here.
PREFIX_GROUPS = [
    "SADSR", "POISR", "ARSNC", "FWYSR", "ITSSR", "POIAS", "POIDT",
    "AGMSR", "ARGSR", "EM2SR", "EM3SR", "EMGSR", "ZONEV", "ZONEZ", "ZSEL",
]


def fmt(n: int) -> str:
    return f"{n:,}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    args = ap.parse_args()
    root = args.root
    idx_dir = os.path.join(root, "IDX")

    print("=" * 78)
    print("PART 1: on-disk byte size of index/address-search-related files")
    print("=" * 78)

    indexdat_path = os.path.join(root, "INDEXDAT.KWI")
    indexdat_size = os.path.getsize(indexdat_path)
    print(f"\nINDEXDAT.KWI: {fmt(indexdat_size)} bytes "
          f"(Ch.11.2 Data Management Frame header -- directory of the IDX/\n"
          f"  files' signatures/versions, not itself address/POI record data)")

    all_idx_files = sorted(os.listdir(idx_dir))
    file_sizes = {f: os.path.getsize(os.path.join(idx_dir, f)) for f in all_idx_files}
    total_idx_bytes = sum(file_sizes.values())

    print(f"\n{len(all_idx_files)} files under IDX/, {fmt(total_idx_bytes)} bytes total.")
    print("\nBy filename-prefix group (7 zoom/region levels 201..207 where present):")
    accounted = 0
    group_totals = {}
    for pfx in PREFIX_GROUPS:
        members = [f for f in all_idx_files if f.startswith(pfx)]
        s = sum(file_sizes[f] for f in members)
        group_totals[pfx] = s
        accounted += s
        if members:
            print(f"  {pfx:8s} {len(members):2d} files  {fmt(s):>15s} bytes")
    leftover = [f for f in all_idx_files if not any(f.startswith(p) for p in PREFIX_GROUPS)]
    leftover_bytes = sum(file_sizes[f] for f in leftover)
    if leftover:
        print(f"  {'(other)':8s} {len(leftover):2d} files  {fmt(leftover_bytes):>15s} bytes  {leftover}")
    print(f"  {'CHECK':8s}    sum of groups = {fmt(accounted + leftover_bytes)} "
          f"(vs directory total {fmt(total_idx_bytes)})")

    total_index_related_bytes = indexdat_size + total_idx_bytes
    print(f"\nTOTAL (INDEXDAT.KWI + all of IDX/): {fmt(total_index_related_bytes)} bytes "
          f"({total_index_related_bytes/1e6:.1f} MB)")

    sadsr_files = sorted(f for f in all_idx_files if f.startswith("SADSR"))
    poisr_files = sorted(f for f in all_idx_files if f.startswith("POISR"))
    sadsr_bytes = sum(file_sizes[f] for f in sadsr_files)
    poisr_bytes = sum(file_sizes[f] for f in poisr_files)
    print(f"\nNarrow 'address search' scope actually walked below:")
    print(f"  SADSR*.IDX (street + address-range, {len(sadsr_files)} files): {fmt(sadsr_bytes)} bytes")
    print(f"  POISR*.IDX (POI search, {len(poisr_files)} files):             {fmt(poisr_bytes)} bytes")
    print(f"  combined: {fmt(sadsr_bytes + poisr_bytes)} bytes "
          f"({(sadsr_bytes+poisr_bytes)/total_index_related_bytes*100:.1f}% of the full IDX/+INDEXDAT total)")

    print()
    print("=" * 78)
    print("PART 2: full census of address-search entries (all 7 SADSR/POISR files)")
    print("=" * 78)
    print("\nFull decode, not sampled -- these files are small enough (< 500MB total)")
    print("to walk every record via the NFRL chain, same as demo_address_search.py's")
    print("'whole-file validation' pass, just repeated across all 7 levels each.\n")

    sadsr_results = []
    total_street_records = 0
    total_street_bytes_consumed = 0
    total_range_records = 0
    total_range_bytes_consumed = 0

    for fname in sadsr_files:
        path = os.path.join(idx_dir, fname)
        t0 = time.time()
        idx = StreetAddressIndex(path)

        n_street = 0
        street_bytes = 0
        for rec in iter_matching_records(idx.buf, idx.street_base, idx.street_fields):
            n_street += 1
            street_bytes += rec["_consumed"]

        n_range = 0
        range_bytes = 0
        for rec in iter_matching_records(idx.buf, idx.range_base, idx.range_fields):
            n_range += 1
            range_bytes += rec["_consumed"]

        elapsed = time.time() - t0
        declared_street = idx.street_info.matching_record_count
        declared_range = idx.range_frame.matching_record_count
        print(f"  {fname}: {file_sizes[fname]:>11,} B  "
              f"streets {n_street:>7,} (declared {declared_street:>7,})  "
              f"ranges {n_range:>7,} (declared {declared_range:>7,})  "
              f"[{elapsed:.1f}s]")
        if n_street != declared_street or n_range != declared_range:
            print(f"    ** WARNING: walked count != frame's own declared count for {fname} **")

        sadsr_results.append(dict(
            fname=fname, file_bytes=file_sizes[fname],
            n_street=n_street, street_bytes=street_bytes,
            n_range=n_range, range_bytes=range_bytes,
        ))
        total_street_records += n_street
        total_street_bytes_consumed += street_bytes
        total_range_records += n_range
        total_range_bytes_consumed += range_bytes

    print(f"\nSADSR totals across {len(sadsr_files)} files:")
    print(f"  street records:        {fmt(total_street_records)}  "
          f"(record-payload bytes actually consumed: {fmt(total_street_bytes_consumed)})")
    print(f"  address-range records: {fmt(total_range_records)}  "
          f"(record-payload bytes actually consumed: {fmt(total_range_bytes_consumed)})")
    sadsr_payload_bytes = total_street_bytes_consumed + total_range_bytes_consumed
    sadsr_overhead_bytes = sadsr_bytes - sadsr_payload_bytes
    print(f"  SADSR file bytes: {fmt(sadsr_bytes)}  |  record payload bytes: {fmt(sadsr_payload_bytes)}  "
          f"|  overhead (DFSR/DCTF/category tables/frame headers/padding): {fmt(sadsr_overhead_bytes)} "
          f"({sadsr_overhead_bytes/sadsr_bytes*100:.1f}%)")

    poisr_results = []
    total_poi_records = 0
    total_poi_bytes_consumed = 0
    for fname in poisr_files:
        path = os.path.join(idx_dir, fname)
        t0 = time.time()
        idx = PoiSearchIndex(path)
        n_poi = 0
        poi_bytes = 0
        for rec in iter_matching_records(idx.buf, idx.base, idx.fields):
            n_poi += 1
            poi_bytes += rec["_consumed"]
        elapsed = time.time() - t0
        declared = idx.info.matching_record_count
        print(f"  {fname}: {file_sizes[fname]:>11,} B  "
              f"POIs {n_poi:>8,} (declared {declared:>8,})  [{elapsed:.1f}s]")
        if n_poi != declared:
            print(f"    ** WARNING: walked count != declared count for {fname} **")
        poisr_results.append(dict(fname=fname, file_bytes=file_sizes[fname],
                                   n_poi=n_poi, poi_bytes=poi_bytes))
        total_poi_records += n_poi
        total_poi_bytes_consumed += poi_bytes

    poisr_payload_bytes = total_poi_bytes_consumed
    poisr_overhead_bytes = poisr_bytes - poisr_payload_bytes
    print(f"\nPOISR totals across {len(poisr_files)} files:")
    print(f"  POI records: {fmt(total_poi_records)}  "
          f"(record-payload bytes actually consumed: {fmt(total_poi_bytes_consumed)})")
    print(f"  POISR file bytes: {fmt(poisr_bytes)}  |  record payload bytes: {fmt(poisr_payload_bytes)}  "
          f"|  overhead: {fmt(poisr_overhead_bytes)} ({poisr_overhead_bytes/poisr_bytes*100:.1f}%)")

    print()
    print("=" * 78)
    print("PART 3: bytes per entry")
    print("=" * 78)

    total_addressish_entries = total_street_records + total_range_records + total_poi_records
    print(f"\nRaw record-payload ratios (bytes actually consumed by that record type / count):")
    if total_street_records:
        print(f"  street record:        {street_bytes_note(total_street_bytes_consumed, total_street_records)}")
    if total_range_records:
        print(f"  address-range record: {street_bytes_note(total_range_bytes_consumed, total_range_records)}")
    if total_poi_records:
        print(f"  POI record:           {street_bytes_note(total_poi_bytes_consumed, total_poi_records)}")

    print(f"\nFully-loaded ratios (whole file bytes, including that file's own DFSR/DCTF/")
    print(f"category-table overhead, / entry count -- this is the number that should be")
    print(f"multiplied by an OSM entry-count projection, NOT the raw payload number above,")
    print(f"since a regenerated disc would need to pay the same per-file overhead):")
    if total_range_records:
        # Address ranges are the closest KIWI-W analogue to one OSM
        # addr:housenumber-tagged feature (a single point/line with a
        # coordinate + house-number range). Streets are a coarser,
        # much-lower-cardinality index layered on top.
        combined_sadsr_entries = total_street_records + total_range_records
        print(f"  SADSR blended (streets+ranges) : {sadsr_bytes:,} / {combined_sadsr_entries:,} "
              f"= {sadsr_bytes/combined_sadsr_entries:.2f} bytes/entry")
        print(f"  SADSR address-range ONLY       : {sadsr_bytes:,} / {total_range_records:,} "
              f"= {sadsr_bytes/total_range_records:.2f} bytes/entry "
              f"(treats street records as fixed per-file overhead, not per-entry cost --")
        print(f"                                    more defensible since street count is ~{total_street_records/total_range_records*100:.1f}% of range count)")
    if total_poi_records:
        print(f"  POISR (POI) only                : {poisr_bytes:,} / {total_poi_records:,} "
              f"= {poisr_bytes/total_poi_records:.2f} bytes/entry")
    combined_bytes = sadsr_bytes + poisr_bytes
    if total_addressish_entries:
        print(f"  SADSR+POISR blended             : {combined_bytes:,} / {total_addressish_entries:,} "
              f"= {combined_bytes/total_addressish_entries:.2f} bytes/entry")

    print()
    print("=" * 78)
    print("PART 4: sanity check -- factory disc's own address coverage vs OSM AU scale")
    print("=" * 78)
    print(f"""
This disc's SADSR/POISR files are split into 7 files each (suffixes
201..207); demo_address_search.py's original single-file (SADSR201/
POISR201) validation showed those coordinates land inside Western
Australia's real bounding box with zero outliers, so 201 is (at least)
a WA-scale regional file, not a national one. The per-file counts above
show whether 201..207 are disjoint regions (state-by-state), zoom levels
of the same national coverage, or something else -- see the counts
printed in Part 2: if they are ~7 independent regions of comparable
order of magnitude, the total ({fmt(total_range_records)} address ranges,
{fmt(total_poi_records)} POIs) is a reasonable stand-in for the disc's
whole-of-Australia address+POI coverage; if instead they are 7 zoom
levels of the SAME underlying entries, the true distinct-entry count is
closer to just the {sadsr_files[0] if sadsr_files else '?'} figure alone
and the sum above over-counts by ~7x. This script deliberately does not
guess which -- that determination needs a cross-file coordinate/name
overlap check, out of scope here (flagged, not resolved).

Whatever the true distinct count, compare against OSM Australia's
4,230,000 addr:housenumber-tagged features (3.39M nodes + 0.85M ways):
""")
    if total_range_records:
        frac = total_range_records / 4_230_000 * 100
        print(f"  factory disc address-range records (sum of 7 files): {fmt(total_range_records)} "
              f"= {frac:.1f}% of OSM AU's 4.23M address features")
    if total_poi_records:
        frac_poi = total_poi_records / 4_230_000 * 100
        print(f"  factory disc POI records (sum of 7 files):            {fmt(total_poi_records)} "
              f"= {frac_poi:.1f}% of OSM AU's 4.23M address features")

    print(f"\n(elapsed since this script's Part 2 census began: see per-file timings above)")
    return 0


def street_bytes_note(total_bytes: int, count: int) -> str:
    return f"{total_bytes:,} / {count:,} = {total_bytes/count:.2f} bytes/record"


if __name__ == "__main__":
    raise SystemExit(main())
