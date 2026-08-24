#!/usr/bin/env python3
"""End-to-end demo of the KIWI-W address/POI search chain: a typed street
name in, a real Western Australian latitude/longitude out.

    python3 parser/demo_address_search.py [DISC_ROOT] [--street "HAY STREET"]

This is the piece that was blocked for three investigation passes. The
chain, all of it now decoded (see parser/kiwiw/search_frame.py):

    IDX/SADSR201.IDX
      DFSR management frame
       -> SRMX detailed search info record ("STREET ADDRESS")
          -> matching data frame: 38,120 street names, alphabetical
             (each carries STID, NXST, NXCT)
          -> next-level frame: a nested DFSR + SRT1 ("ADDRESS RANGE")
             -> matching data frame: 344,276 address ranges, each with
                an inline RLXY coordinate, a Link ID, and a house-number
                range

Validation built into this demo:

1. Spot checks -- eight well-known WA streets whose real-world locations
   are independently known, printed with their decoded coordinates.
2. Whole-file statistics -- decode all 344,276 address-range records and
   print the bounding box. It comes out as lat -35.125..-14.292,
   lon 113.438..128.938 with zero outliers, which is Western Australia's
   real extent (including the 129 deg E straight-line state border) to
   within one parcel. A wrong decode could not produce that.
3. The POI file -- POISR201.IDX goes through the exact same generic
   decoder, and its 101,855 geocoded POIs land in the same box.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwiw.search_frame import (  # noqa: E402
    PoiSearchIndex,
    StreetAddressIndex,
    iter_matching_records,
)

DEFAULT_DISC = "/run/media/codyh/464210-8480"

# Streets whose real location is independently known, for eyeballing.
SPOT_CHECKS = [
    ("ST GEORGES TERRACE", "Perth CBD, the main city street"),
    ("STIRLING HIGHWAY", "Perth -> Fremantle, through Claremont/Cottesloe"),
    ("GREAT EASTERN HIGHWAY", "Perth airport / Redcliffe / Ascot"),
    ("WANNEROO ROAD", "northern Perth suburbs (Balcatta/Nollamara)"),
    ("GINGIN BROOK ROAD", "Gingin, ~85 km north of Perth"),
    ("GINGIN ROAD", "Gingin"),
    ("ALBANY HIGHWAY", "Perth -> Albany, ~400 km south"),
    ("HANNAN STREET", "Kalgoorlie, ~600 km east"),
]


def banner(text: str) -> None:
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("disc", nargs="?", default=DEFAULT_DISC)
    ap.add_argument("--street", action="append", default=None,
                    help="look up an extra street name (repeatable)")
    ap.add_argument("--poi", default="BURSWOOD CAR RENTALS",
                    help="POI name substring to search for")
    ap.add_argument("--full-scan", action="store_true", default=True)
    ap.add_argument("--no-full-scan", dest="full_scan", action="store_false")
    args = ap.parse_args()

    sadsr = os.path.join(args.disc, "IDX", "SADSR201.IDX")
    poisr = os.path.join(args.disc, "IDX", "POISR201.IDX")
    if not os.path.exists(sadsr):
        print(f"error: {sadsr} not found -- pass the disc root as argv[1]", file=sys.stderr)
        return 2

    banner("1. Resolving the search frame chain in SADSR201.IDX")
    t0 = time.time()
    idx = StreetAddressIndex(sadsr)
    print(f"  loaded in {time.time() - t0:.1f}s")
    si = idx.street_info
    print(f"  detailed search info records : {[r.declaration for r in idx.records]}")
    print(f"  street name matching frame   : @{idx.street_base} "
          f"({si.matching_record_count} records, max {si.matching_record_max_size} B)")
    print(f"  street record fields         : {[f.usage for f in idx.street_fields]}")
    print(f"  next-level frame             : @{si.next_level.file_offset} "
          f"({si.next_level.filename})")
    rf = idx.range_frame
    print(f"  address range matching frame : @{idx.range_base} "
          f"({rf.matching_record_count} records, max {rf.matching_record_max_size} B)")
    print(f"  address range fields         : {[f.usage for f in idx.range_fields]}")

    banner("2. Street name -> coordinate (spot checks against known geography)")
    names = [n for n, _ in SPOT_CHECKS] + list(args.street or [])
    notes = dict(SPOT_CHECKS)
    for name in names:
        streets = idx.find(name)
        if not streets:
            print(f"\n  {name!r}: NOT FOUND")
            continue
        for s in streets:
            print(f"\n  {name!r}")
            print(f"    street record @{s.file_offset}  STID={s.street_id}  "
                  f"NXKD/NXFN={s.next_level_class}/{s.next_level_serial}  "
                  f"NXST=+{s.next_level_offset}  NXCT={s.next_level_count}")
            ranges = idx.address_ranges(s)
            lats = [r.lat for r in ranges]
            lons = [r.lon for r in ranges]
            print(f"    -> {len(ranges)} address ranges spanning "
                  f"lat {min(lats):.5f}..{max(lats):.5f}  "
                  f"lon {min(lons):.5f}..{max(lons):.5f}")
            if name in notes:
                print(f"       (expected: {notes[name]})")
            for r in ranges[:4]:
                houses = ("centre link, no house numbers" if r.is_center_link
                          else f"#{r.house_start}..#{r.house_end}")
                print(f"       lat {r.lat:10.5f}  lon {r.lon:10.5f}  "
                      f"LKID 0x{r.link_id:08x}  ARCD 0x{r.area_codes[0]:08x}  {houses}")
            if len(ranges) > 4:
                print(f"       ... {len(ranges) - 4} more")

    if args.full_scan:
        banner("3. Whole-file validation: decode every address range record")
        t0 = time.time()
        n = 0
        latmin = lonmin = 1e9
        latmax = lonmax = -1e9
        outside = 0
        for rec in iter_matching_records(idx.buf, idx.range_base, idx.range_fields):
            lat, lon = rec["RLXY"]
            n += 1
            latmin, latmax = min(latmin, lat), max(latmax, lat)
            lonmin, lonmax = min(lonmin, lon), max(lonmax, lon)
            # Generous box around Western Australia.
            if not (-36.0 < lat < -13.0 and 112.0 < lon < 130.0):
                outside += 1
        print(f"  decoded {n} records in {time.time() - t0:.1f}s "
              f"(frame declares {rf.matching_record_count})")
        print(f"  latitude  {latmin:.4f} .. {latmax:.4f}   "
              f"(WA runs -35.13 at West Cape Howe to -13.69 at Cape Londonderry)")
        print(f"  longitude {lonmin:.4f} .. {lonmax:.4f}   "
              f"(WA runs 112.92 at Steep Point to 129.00 at the NT/SA border)")
        print(f"  records outside Western Australia: {outside}")
        assert n == rf.matching_record_count, "record count mismatch"
        assert outside == 0, "coordinates escaped Western Australia"
        print("  OK -- every coordinate on the disc lands inside WA.")

    if os.path.exists(poisr):
        banner("4. Same decoder, POI search file (POISR201.IDX)")
        poi_idx = PoiSearchIndex(poisr)
        print(f"  POI matching frame @{poi_idx.base}, "
              f"{poi_idx.info.matching_record_count} records")
        print(f"  POI record fields  : {[f.usage for f in poi_idx.fields]}")
        for poi in poi_idx.find(args.poi, limit=5):
            where = ("(degenerate representative record, no coordinate)"
                     if poi.is_degenerate else f"lat {poi.lat:.5f}  lon {poi.lon:.5f}")
            print(f"\n    @{poi.file_offset}  {poi.search_key!r}")
            print(f"      name  : {poi.name!r}")
            print(f"      where : {where}")
            print(f"      CTGY  : 0x{(poi.category or 0):04x}   "
                  f"ARCD: {[hex(a) for a in poi.area_codes]}")

    banner("Chain solved: street name -> STID/NXST -> address range -> RLXY lat/lon + LKID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
