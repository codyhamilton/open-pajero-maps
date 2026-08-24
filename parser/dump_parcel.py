#!/usr/bin/env python3
"""CLI: locate and dump the KIWI-W main-map parcel containing a coordinate.

Usage:
    python3 dump_parcel.py --alldata /path/to/ALLDATA.KWI --lat -37.813629 --lon 144.963058 [--level 0]

Prints the fully decoded parcel (mesh location + road/background/name
frames) as JSON to stdout. Exits non-zero (with a message on stderr) if no
parcel is found at that coordinate/level -- e.g. the disc doesn't cover
that area, or that block/blockset has no data (a real gap, matching the AU
disc's sparse coverage noted in Phase 0).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.disc import AllData
from kiwiw.model import to_jsonable


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alldata", required=True, help="Path to ALLDATA.KWI")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--level", type=int, default=0, help="Map level (default 0 = finest)")
    ap.add_argument("--header-only", action="store_true",
                     help="Just print the volume header + level table, don't locate a parcel")
    args = ap.parse_args()

    with AllData(args.alldata) as disc:
        if args.header_only:
            out = {
                "header": to_jsonable(disc.header),
                "levels": [to_jsonable(l) for l in disc.levels],
            }
            print(json.dumps(out, indent=2))
            return 0

        if args.lat is None or args.lon is None:
            ap.error("--lat/--lon are required unless --header-only is given")
        parcel = disc.find_parcel(args.lat, args.lon, level=args.level)
        if parcel is None:
            print(
                f"No parcel found at ({args.lat}, {args.lon}) level {args.level} "
                "-- either outside disc coverage or a real data gap.",
                file=sys.stderr,
            )
            return 1

        print(json.dumps(to_jsonable(parcel), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
