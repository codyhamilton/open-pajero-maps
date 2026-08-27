"""Phase 2 round-trip regression tests for parcel content: the Ch. 6
Parcel Management Record a Block Management Table entry addresses, and the
Ch. 7 Map Frame (header + mfde table + road/background/name sub-frames) a
leaf entry of that record points at (see docs/phases/02-roundtrip.md).

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present, same convention as test_mesh.py / test_roundtrip_misc.py.
"""
import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import roundtrip_parcel_content as rtpc  # noqa: E402

ROOT = "/run/media/codyh/464210-8480"
ALLDATA_PATH = os.path.join(ROOT, "ALLDATA.KWI")

# Reuse the same known-good coordinates as the harness / test_mesh.py.
TEST_POINTS = rtpc.TEST_POINTS
LEVEL = 0


def _open_disc():
    if not os.path.exists(ALLDATA_PATH):
        print(f"SKIP: {ALLDATA_PATH} not present (disc not mounted)")
        return None
    return AllData(ALLDATA_PATH)


def _for_each_point(fn):
    """Run `fn(disc, label, lat, lon, pdat, lmr, loc)` for every test point
    that has both a data block and a leaf parcel at this level. Returns the
    list of results `fn` produced (skips points with no data, same as the
    harness script)."""
    disc = _open_disc()
    if disc is None:
        return []
    results = []
    try:
        for label, lat, lon in TEST_POINTS:
            found = rtpc._find_block(disc.pdmdh, disc._zdat0, disc._fh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if found is None:
                print(f"SKIP: {label}: no data block at this coordinate")
                continue
            pdat, lmr, bmt_dsa, bmt_size = found
            loc = mesh.locate_parcel(disc._fh, disc._zdat0, disc.pdmdh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if loc is None:
                print(f"SKIP: {label}: no leaf parcel at this coordinate")
                continue
            results.append(fn(disc, label, lat, lon, pdat, lmr, loc))
    finally:
        disc.close()
    return results


def _read_mapdata(disc, loc):
    off = getsector(loc.sector_addr, disc.sector_sz, disc.logical_sz)
    disc._fh.seek(off)
    return disc._fh.read(loc.size_logical_sectors * disc.logical_sz)


# ---------------------------------------------------------------------
# Positive: byte-identical round-trip, across all 4 real test points.
# ---------------------------------------------------------------------

def test_block_record_byte_identical():
    def check(disc, label, lat, lon, pdat, lmr, loc):
        result = rtpc.check_block_roundtrip(pdat, lmr)
        print(f"{label}: {result}")
        assert result.startswith("PASS"), result
        return result

    results = _for_each_point(check)
    if not results:
        return
    print(f"PASS: {len(results)}/{len(TEST_POINTS)} block records byte-identical")


def test_parcel_content_byte_identical():
    def check(disc, label, lat, lon, pdat, lmr, loc):
        result = rtpc.check_parcel_roundtrip(disc, loc, lmr)
        print(f"{label}: {result}")
        assert result.startswith("PASS"), result
        return result

    results = _for_each_point(check)
    if not results:
        return
    print(f"PASS: {len(results)}/{len(TEST_POINTS)} parcels byte-identical")


# ---------------------------------------------------------------------
# Negative controls: perturb one decoded/raw field and confirm the
# round-trip check correctly detects and fails on the perturbation.
# ---------------------------------------------------------------------

def test_negative_control_block_tail_raw():
    """Truncating ParcelMgmtRecord.tail_raw by one byte must break the
    block-record round-trip (confirms tail_raw is actually load-bearing,
    not dead weight the writer ignores)."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        found = rtpc._find_block(disc.pdmdh, disc._zdat0, disc._fh, LEVEL,
                                  TEST_POINTS[0][1], TEST_POINTS[0][2],
                                  disc.sector_sz, disc.logical_sz)
        assert found is not None, "expected a data block at test point 0"
        pdat, lmr, _, _ = found
        rec = parse_parcel_mgmt_record(pdat, lmr)
        assert rec.tail_raw, "expected a non-empty tail_raw to perturb"

        rec_bad = copy.deepcopy(rec)
        rec_bad.tail_raw = bytes([rec_bad.tail_raw[0] ^ 0xFF]) + rec_bad.tail_raw[1:]

        buf = bytearray([POISON]) * len(pdat)
        write_parcel_mgmt_record(rec_bad, buf)
        assert bytes(buf) != pdat, "perturbed tail_raw should NOT round-trip identically"
        print("PASS: negative control -- perturbed tail_raw correctly breaks round-trip")
    finally:
        disc.close()


def test_negative_control_road_link_raw_bytes():
    """Flipping a byte inside a RoadLink.raw_bytes must break the parcel
    round-trip (confirms raw_bytes is what's actually written, not just
    carried around unused)."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        for label, lat, lon in TEST_POINTS:
            loc = mesh.locate_parcel(disc._fh, disc._zdat0, disc.pdmdh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if loc is None:
                continue
            mapdata = _read_mapdata(disc, loc)
            found = rtpc._find_block(disc.pdmdh, disc._zdat0, disc._fh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if found is None:
                continue
            _, lmr, _, _ = found
            parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                    n_ext_map=lmr.n_ext_map)
            if parcel.road is None or not parcel.road.links:
                continue

            parcel_bad = copy.deepcopy(parcel)
            link = parcel_bad.road.links[0]
            link.raw_bytes = bytes([link.raw_bytes[0] ^ 0xFF]) + link.raw_bytes[1:]

            road_bytes = write_road_frame(parcel_bad.road)
            bg_bytes = (write_background_frame(parcel_bad.background)
                        if parcel_bad.background is not None else None)
            name_bytes = (write_name_frame(parcel_bad.name)
                          if parcel_bad.name is not None else None)
            rebuilt = write_map_frame(parcel_bad.frame, road_bytes, bg_bytes, name_bytes)
            assert rebuilt != mapdata, (
                f"{label}: perturbed RoadLink.raw_bytes should NOT round-trip identically")
            print(f"PASS: negative control ({label}) -- perturbed RoadLink.raw_bytes "
                  f"correctly breaks round-trip")
            return
        print("SKIP: no test point had a road frame with links to perturb")
    finally:
        disc.close()


def test_negative_control_name_record_raw_bytes():
    """Flipping a byte inside a NameRecord.raw_bytes must break the parcel
    round-trip."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        for label, lat, lon in TEST_POINTS:
            loc = mesh.locate_parcel(disc._fh, disc._zdat0, disc.pdmdh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if loc is None:
                continue
            mapdata = _read_mapdata(disc, loc)
            found = rtpc._find_block(disc.pdmdh, disc._zdat0, disc._fh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if found is None:
                continue
            _, lmr, _, _ = found
            parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                    n_ext_map=lmr.n_ext_map)
            if parcel.name is None or not parcel.name.records:
                continue

            parcel_bad = copy.deepcopy(parcel)
            rec = parcel_bad.name.records[0]
            rec.raw_bytes = bytes([rec.raw_bytes[0] ^ 0xFF]) + rec.raw_bytes[1:]

            road_bytes = (write_road_frame(parcel_bad.road)
                          if parcel_bad.road is not None else None)
            bg_bytes = (write_background_frame(parcel_bad.background)
                        if parcel_bad.background is not None else None)
            name_bytes = write_name_frame(parcel_bad.name)
            rebuilt = write_map_frame(parcel_bad.frame, road_bytes, bg_bytes, name_bytes)
            assert rebuilt != mapdata, (
                f"{label}: perturbed NameRecord.raw_bytes should NOT round-trip identically")
            print(f"PASS: negative control ({label}) -- perturbed NameRecord.raw_bytes "
                  f"correctly breaks round-trip")
            return
        print("SKIP: no test point had a name frame with records to perturb")
    finally:
        disc.close()


def test_negative_control_map_frame_tail_raw():
    """Truncating MapFrame.tail_raw by one byte must break the parcel
    round-trip."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        for label, lat, lon in TEST_POINTS:
            loc = mesh.locate_parcel(disc._fh, disc._zdat0, disc.pdmdh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if loc is None:
                continue
            mapdata = _read_mapdata(disc, loc)
            found = rtpc._find_block(disc.pdmdh, disc._zdat0, disc._fh, LEVEL,
                                      lat, lon, disc.sector_sz, disc.logical_sz)
            if found is None:
                continue
            _, lmr, _, _ = found
            parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                    n_ext_map=lmr.n_ext_map)
            if not parcel.frame.tail_raw:
                continue

            parcel_bad = copy.deepcopy(parcel)
            tail = parcel_bad.frame.tail_raw
            parcel_bad.frame.tail_raw = bytes([tail[0] ^ 0xFF]) + tail[1:]

            road_bytes = (write_road_frame(parcel_bad.road)
                          if parcel_bad.road is not None else None)
            bg_bytes = (write_background_frame(parcel_bad.background)
                        if parcel_bad.background is not None else None)
            name_bytes = (write_name_frame(parcel_bad.name)
                          if parcel_bad.name is not None else None)
            rebuilt = write_map_frame(parcel_bad.frame, road_bytes, bg_bytes, name_bytes)
            assert rebuilt != mapdata, (
                f"{label}: perturbed MapFrame.tail_raw should NOT round-trip identically")
            print(f"PASS: negative control ({label}) -- perturbed MapFrame.tail_raw "
                  f"correctly breaks round-trip")
            return
        print("SKIP: no test point had a non-empty MapFrame.tail_raw to perturb")
    finally:
        disc.close()


if __name__ == "__main__":
    test_block_record_byte_identical()
    test_parcel_content_byte_identical()
    test_negative_control_block_tail_raw()
    test_negative_control_road_link_raw_bytes()
    test_negative_control_name_record_raw_bytes()
    test_negative_control_map_frame_tail_raw()
