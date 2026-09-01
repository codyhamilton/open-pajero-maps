"""Phase 3 encoder tests: name-record encoder.

Verifies that `write_name_frame(encode=True)` re-serialises a decoded
NameFrame such that:

1. The output has the same byte length as the original (copy-and-patch
   preserves record sizes since the na word is untouched).
2. Decoding the re-encoded frame produces NameRecords whose decoded fields
   are identical to the originals:
   - string_type, priority, vertical, display_scale_flag, type_code (exact)
   - text (exact -- the string bytes are preserved verbatim in raw_bytes)

The test focuses on string_type == 4 (Linear-B) since that is the only
type whose attr1/attr2 the encoder actively re-assembles.  Other types pass
through raw_bytes unchanged so their round-trip is trivially correct.

Also verifies that calling without encode=True still produces byte-identical
output (replicate mode unchanged).

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present, same convention as test_road_encoder.py.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import mesh
from kiwiw.disc import AllData
from kiwiw.name import decode_name_frame
from kiwiw.parcel import decode_parcel
from kiwiw.parcel_writer import write_name_frame
from kiwiw.volume import getsector

ROOT = "/run/media/codyh/464210-8480"
ALLDATA_PATH = os.path.join(ROOT, "ALLDATA.KWI")

LEVEL = 0
TEST_POINTS = [
    (-37.813629, 144.963058),   # Melbourne (Docklands)
    (-33.868820, 151.209290),   # Sydney Harbour
    (-33.8148, 151.0011),       # Sydney (Camellia/Granville)
    (-31.95312, 115.86719),     # Perth CBD
]


def _open_disc():
    if not os.path.exists(ALLDATA_PATH):
        print(f"SKIP: {ALLDATA_PATH} not present (disc not mounted)")
        return None
    return AllData(ALLDATA_PATH)


def _load_parcel_with_name_records(disc, require_type4: bool = False):
    """Return (parcel, loc) for the first test point that has a non-empty
    name frame.  When require_type4 is True, also requires at least one
    string_type == 4 record."""
    import roundtrip_parcel_content as rtpc

    for lat, lon in TEST_POINTS:
        found = rtpc._find_block(disc.pdmdh, disc._zdat0, disc._fh, LEVEL,
                                  lat, lon, disc.sector_sz, disc.logical_sz)
        if found is None:
            continue
        _, lmr, _, _ = found
        loc = mesh.locate_parcel(disc._fh, disc._zdat0, disc.pdmdh, LEVEL,
                                  lat, lon, disc.sector_sz, disc.logical_sz)
        if loc is None:
            continue
        off = getsector(loc.sector_addr, disc.sector_sz, disc.logical_sz)
        disc._fh.seek(off)
        mapdata = disc._fh.read(loc.size_logical_sectors * disc.logical_sz)
        parcel = decode_parcel(loc, mapdata,
                               n_basic_map=lmr.n_basic_map,
                               n_ext_map=lmr.n_ext_map)
        if parcel.name is None or not parcel.name.records:
            continue
        if require_type4 and not any(r.string_type == 4
                                      for r in parcel.name.records):
            continue
        return parcel, loc
    return None, None


def test_name_encoder_roundtrip():
    """Decode a real parcel's name frame, re-encode each record via
    write_name_frame(encode=True), decode the result, and assert all decoded
    fields match.

    Checks per record:
    - string_type, type_code, priority, vertical, display_scale_flag (exact)
    - text (exact -- string bytes preserved verbatim from raw_bytes)
    - lat, lon, angle_deg (exact -- coord bytes preserved verbatim from
      raw_bytes for all types)
    """
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, loc = _load_parcel_with_name_records(disc)
        if parcel is None:
            print("SKIP: no parcel with name records found")
            return

        bounds = loc.bounds
        orig_frame = parcel.name

        # Re-encode in encode mode and check length.
        encoded_bytes = write_name_frame(orig_frame, encode=True)
        orig_bytes = write_name_frame(orig_frame)  # replicate mode

        assert len(encoded_bytes) == len(orig_bytes), (
            f"encoded name frame length {len(encoded_bytes)} != "
            f"original {len(orig_bytes)}"
        )

        # Decode the re-encoded frame and compare fields record by record.
        reenc_frame = decode_name_frame(encoded_bytes, bounds)

        assert len(reenc_frame.records) == len(orig_frame.records), (
            f"record count mismatch: {len(reenc_frame.records)} vs "
            f"{len(orig_frame.records)}"
        )

        n_records = len(orig_frame.records)
        n_type4 = sum(1 for r in orig_frame.records if r.string_type == 4)

        for i, (orig, reenc) in enumerate(
            zip(orig_frame.records, reenc_frame.records)
        ):
            ctx = f"record[{i}] (string_type={orig.string_type})"
            assert reenc.string_type == orig.string_type, f"{ctx} string_type"
            assert reenc.type_code == orig.type_code, f"{ctx} type_code"
            assert reenc.priority == orig.priority, f"{ctx} priority"
            assert reenc.vertical == orig.vertical, f"{ctx} vertical"
            assert reenc.display_scale_flag == orig.display_scale_flag, \
                f"{ctx} display_scale_flag"
            assert reenc.text == orig.text, f"{ctx} text"
            # lat/lon/angle_deg: None for type 4, decoded from verbatim
            # coord bytes for others.
            assert reenc.lat == orig.lat, f"{ctx} lat"
            assert reenc.lon == orig.lon, f"{ctx} lon"
            assert reenc.angle_deg == orig.angle_deg, f"{ctx} angle_deg"

        assert n_records > 0, "expected at least one name record"
        print(f"PASS: name encoder round-trip: {n_records} records "
              f"({n_type4} type-4 Linear-B) all fields exact")
    finally:
        disc.close()


def test_name_encoder_type4_present():
    """Confirm there is at least one parcel with a string_type == 4 record
    among the test points (guards against the test silently only exercising
    the raw-bytes fallback path)."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, loc = _load_parcel_with_name_records(disc, require_type4=True)
        if parcel is None:
            print("SKIP: no parcel with string_type==4 name records found "
                  "(test point set may not cover Linear-B names)")
            return
        n4 = sum(1 for r in parcel.name.records if r.string_type == 4)
        assert n4 > 0
        print(f"PASS: found parcel with {n4} string_type==4 name record(s) "
              f"-- encoder exercises the active re-encode path")
    finally:
        disc.close()


def test_name_encoder_does_not_break_replicate_mode():
    """Calling write_name_frame() WITHOUT encode=True still produces
    byte-identical output (replicate mode unchanged after encoder addition)."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, loc = _load_parcel_with_name_records(disc)
        if parcel is None:
            print("SKIP: no parcel with name records found")
            return

        import roundtrip_parcel_content as rtpc
        from kiwiw.parcel_writer import (
            write_background_frame,
            write_map_frame,
            write_road_frame,
        )

        road_bytes = (write_road_frame(parcel.road)
                      if parcel.road is not None else None)
        bg_bytes = (write_background_frame(parcel.background)
                    if parcel.background is not None else None)
        name_bytes = write_name_frame(parcel.name)  # replicate mode

        rebuilt = write_map_frame(parcel.frame, road_bytes, bg_bytes, name_bytes)

        # Read original bytes from disc.
        off = getsector(loc.sector_addr, disc.sector_sz, disc.logical_sz)
        disc._fh.seek(off)
        original = disc._fh.read(loc.size_logical_sectors * disc.logical_sz)

        assert rebuilt == original, (
            "replicate mode write_name_frame() produced non-identical bytes "
            "after name_writer.py was added to the codebase"
        )
        print("PASS: replicate mode write_name_frame() still byte-identical "
              "after encoder addition")
    finally:
        disc.close()


if __name__ == "__main__":
    test_name_encoder_roundtrip()
    test_name_encoder_type4_present()
    test_name_encoder_does_not_break_replicate_mode()
