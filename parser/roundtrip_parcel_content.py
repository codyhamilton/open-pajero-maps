#!/usr/bin/env python3
"""Round-trip harness for `ALLDATA.KWI` parcel content: the Ch. 6 Parcel
Management Record a Block Management Table entry addresses, and the Ch. 7
Map Frame (header + mfde table + road/background/name sub-frames) a leaf
entry of that record points at.

For each of several real, known-good coordinates (reused from
`parser/tests/test_mesh.py` -- Melbourne, Sydney Harbour, regional NSW,
Perth CBD -- spanning multiple Australian cities/regions per the disc's
coverage), this:

1. Locates the coordinate's containing Block, fetches that block's own
   data buffer (what a BMT entry's `dsa`/`size` addresses), parses it as a
   `ParcelMgmtRecord` tree (`kiwiw/parcel_mgmt.py`), re-serializes it
   (`kiwiw/parcel_writer.write_parcel_mgmt_record`), and byte-diffs the
   result against the original block buffer.
2. Locates the coordinate's leaf Map Frame, decodes it
   (`kiwiw/parcel.decode_parcel`), re-serializes the Map Frame header/mfde
   table + road/background/name sub-frames
   (`kiwiw/parcel_writer.write_map_frame` and friends), and byte-diffs the
   result against the original Map Frame buffer.

Run against the real mounted disc (override `--root`):
    python3 roundtrip_parcel_content.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw import mesh
from kiwiw.disc import AllData
from kiwiw.parcel import decode_parcel
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
from kiwiw.parcel_writer import (
    POISON,
    write_background_frame,
    write_map_frame,
    write_name_frame,
    write_parcel_mgmt_record,
    write_road_frame,
)
from kiwiw.volume import getsector

# (label, lat, lon) -- known-good coordinates cross-checked in test_mesh.py
# (Melbourne, two Sydney-area points) plus the Perth CBD coordinate named
# in mesh.py's own module docstring as a validated query -- four points
# across three different Australian cities/regions.
TEST_POINTS = [
    ("Melbourne (Docklands)", -37.813629, 144.963058),
    ("Sydney Harbour", -33.868820, 151.209290),
    ("Sydney (Camellia/Granville)", -33.8148, 151.0011),
    ("Perth CBD", -31.95312, 115.86719),
]


def _diff(expected: bytes, actual: bytes) -> str | None:
    if expected == actual:
        return None
    if len(expected) != len(actual):
        return f"length mismatch: expected {len(expected)}, actual {len(actual)}"
    for i, (a, b) in enumerate(zip(expected, actual)):
        if a != b:
            lo, hi = max(0, i - 4), i + 12
            return (f"first diff at offset {i}: expected "
                     f"{expected[lo:hi].hex()} actual {actual[lo:hi].hex()}")
    return "unreachable"


def _find_block(pdmdh, zdat0, fh, level: int, lat: float, lon: float, sector_sz: int, logical_sz: int):
    """Reuse mesh.py's own block-resolution math (grid cell -> blockset ->
    block -> BMT entry) up to fetching that block's raw data buffer,
    without re-deriving the formulas independently. Returns
    (pdat_bytes, lmr, bmt_dsa, bmt_size) or None if there's no data there."""
    lmr = next((l for l in pdmdh.levels if l.level == level), None)
    if lmr is None:
        raise ValueError(f"no LMR for level {level}")

    lon_span = mesh._lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    nx, ny = lmr.grid_nx, lmr.grid_ny
    mx = lon_span / nx
    my = lat_span / ny
    dlon = mesh._lon_delta(pdmdh.coverage.lon_lo, lon, lon_span)
    dlat = lat - pdmdh.coverage.lat_lo
    ix = mesh._clamp(int(dlon / mx), 0, nx - 1)
    iy = mesh._clamp(int(dlat / my), 0, ny - 1)

    nbs_lng, nbs_lat = 1 + lmr.n_blocksets_lng, 1 + lmr.n_blocksets_lat
    nbl_lng, nbl_lat = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
    npc_lng, npc_lat = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]

    px = ix % npc_lng
    tmp = ix // npc_lng
    blx = tmp % nbl_lng
    bsx = tmp // nbl_lng
    py = iy % npc_lat
    tmp = iy // npc_lat
    bly = tmp % nbl_lat
    bsy = tmp // nbl_lat

    bset_flat = bsy * nbs_lng + bsx
    bs_rec = next((b for b in pdmdh.blocksets
                   if b.level == level and b.blockset_index == bset_flat), None)
    if bs_rec is None or bs_rec.bmt_size == 0:
        return None

    n_blocks = nbl_lat * nbl_lng
    bmt_entries = mesh._read_bmt_array(zdat0, bs_rec.bmt_offset, n_blocks)
    block_flat = bly * nbl_lng + blx
    bmt = bmt_entries[block_flat]
    if bmt.dsa == mesh.NO_DATA_DSA or bmt.size == 0:
        return None

    poff = getsector(bmt.dsa, sector_sz, logical_sz)
    fh.seek(poff)
    pdat = fh.read(bmt.size * logical_sz)
    return pdat, lmr, bmt.dsa, bmt.size


def check_block_roundtrip(pdat: bytes, lmr) -> str:
    rec = parse_parcel_mgmt_record(pdat, lmr)
    buf = bytearray([POISON]) * len(pdat)
    write_parcel_mgmt_record(rec, buf)
    diff = _diff(pdat, bytes(buf))
    if diff is None:
        return f"PASS  block record: byte-identical ({len(pdat)} bytes)"
    return f"FAIL  block record: {diff}"


def check_parcel_roundtrip(disc: AllData, loc, lmr) -> str:
    off = getsector(loc.sector_addr, disc.sector_sz, disc.logical_sz)
    disc._fh.seek(off)
    mapdata = disc._fh.read(loc.size_logical_sectors * disc.logical_sz)

    parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)

    road_bytes = write_road_frame(parcel.road) if parcel.road is not None else None
    bg_bytes = write_background_frame(parcel.background) if parcel.background is not None else None
    try:
        name_bytes = write_name_frame(parcel.name) if parcel.name is not None else None
    except ValueError as e:
        return f"FAIL  parcel {loc.sector_addr}: name frame: {e}"

    rebuilt = write_map_frame(parcel.frame, road_bytes, bg_bytes, name_bytes)
    diff = _diff(mapdata, rebuilt)
    n_links = len(parcel.road.links) if parcel.road else 0
    n_shapes = len(parcel.background.shapes) if parcel.background else 0
    n_names = len(parcel.name.records) if parcel.name else 0
    detail = f"{len(mapdata)} bytes, {n_links} road links, {n_shapes} bg shapes, {n_names} names"
    if diff is None:
        return f"PASS  parcel @ sector {loc.sector_addr}: byte-identical ({detail})"
    return f"FAIL  parcel @ sector {loc.sector_addr}: {diff} ({detail})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="/run/media/codyh/464210-8480",
                     help="Mounted disc root (default: %(default)s)")
    ap.add_argument("--level", type=int, default=0)
    args = ap.parse_args()

    alldata_path = str(Path(args.root) / "ALLDATA.KWI")
    if not Path(alldata_path).exists():
        print(f"SKIP: {alldata_path} not found (disc not mounted?)")
        return 0

    results = []
    with AllData(alldata_path) as disc:
        for label, lat, lon in TEST_POINTS:
            found = _find_block(disc.pdmdh, disc._zdat0, disc._fh, args.level,
                                 lat, lon, disc.sector_sz, disc.logical_sz)
            if found is None:
                results.append(f"SKIP  {label}: no data block at this coordinate")
                continue
            pdat, lmr, bmt_dsa, bmt_size = found
            print(f"-- {label} ({lat}, {lon}), block dsa={bmt_dsa} size={bmt_size} --")
            r1 = check_block_roundtrip(pdat, lmr)
            print(f"  {r1}")
            results.append(r1)

            loc = mesh.locate_parcel(disc._fh, disc._zdat0, disc.pdmdh, args.level,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if loc is None:
                results.append(f"SKIP  {label}: no leaf parcel at this coordinate")
                continue
            r2 = check_parcel_roundtrip(disc, loc, lmr)
            print(f"  {r2}")
            results.append(r2)

    n_pass = sum(1 for r in results if r.startswith("PASS"))
    n_fail = sum(1 for r in results if r.startswith("FAIL"))
    n_total = n_pass + n_fail
    print()
    print(f"{n_pass}/{n_total} parcel-content round-trip checks byte-identical "
          f"({len(results) - n_total} skipped)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
