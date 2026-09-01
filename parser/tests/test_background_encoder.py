"""Phase 3 encoder tests: background-shape encoder.

Verifies that `write_background_frame(encode=True)` re-serialises a decoded
BackgroundFrame such that:

1. The output has the same byte length as the original (copy-and-patch
   preserves shape record sizes).
2. Decoding the re-encoded frame produces BackgroundShapes whose decoded
   fields are identical to the originals:
   - shape_class, type_code, n_coords, mult_const, underground, pen_up
   - coords[0] (starting coordinate lat/lon) -- exact round-trip via
     latlon_to_xy → encode_region_coord → decode_region_coord → xy_to_latlon

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
from kiwiw.background import decode_background_frame
from kiwiw.disc import AllData
from kiwiw.parcel import decode_parcel
from kiwiw.parcel_writer import write_background_frame
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


def _load_parcel_with_background(disc):
    """Return (parcel, lmr) for the first test point that has a non-empty
    background frame with at least one non-point shape."""
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
        if (parcel.background is not None and parcel.background.shapes
                and any(s.shape_class != 0 for s in parcel.background.shapes)):
            return parcel, loc
    return None, None


def test_background_encoder_roundtrip():
    """Decode a real parcel's background frame, re-encode each shape via
    write_background_frame(encode=True), decode the result, and assert all
    decoded fields match.

    Checks per shape:
    - shape_class, n_coords, mult_const, underground, pen_up, type_code (exact)
    - coords[0] lat/lon (exact round-trip through latlon_to_xy /
      encode_region_coord / decode_region_coord / xy_to_latlon)
    """
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, loc = _load_parcel_with_background(disc)
        if parcel is None:
            print("SKIP: no parcel with non-point background shapes found")
            return

        bounds = loc.bounds
        orig_frame = parcel.background

        # Re-encode in encode mode and check length.
        encoded_bytes = write_background_frame(orig_frame, bounds=bounds, encode=True)
        orig_bytes = write_background_frame(orig_frame)  # replicate mode

        assert len(encoded_bytes) == len(orig_bytes), (
            f"encoded background frame length {len(encoded_bytes)} != "
            f"original {len(orig_bytes)}"
        )

        # Decode the re-encoded frame and compare fields shape by shape.
        reenc_frame = decode_background_frame(encoded_bytes, bounds)

        assert len(reenc_frame.shapes) == len(orig_frame.shapes), (
            f"shape count mismatch: {len(reenc_frame.shapes)} vs "
            f"{len(orig_frame.shapes)}"
        )

        n_shapes_checked = 0
        for i, (orig, reenc) in enumerate(
            zip(orig_frame.shapes, reenc_frame.shapes)
        ):
            ctx = f"shape[{i}]"
            assert reenc.shape_class == orig.shape_class, f"{ctx} shape_class"
            assert reenc.type_code == orig.type_code, f"{ctx} type_code"
            assert reenc.n_coords == orig.n_coords, f"{ctx} n_coords"
            assert reenc.mult_const == orig.mult_const, f"{ctx} mult_const"
            assert reenc.underground == orig.underground, f"{ctx} underground"
            assert reenc.pen_up == orig.pen_up, f"{ctx} pen_up"

            # For non-point shapes, check the starting coordinate.
            if orig.shape_class != 0 and orig.coords:
                assert reenc.coords, f"{ctx} expected coords in re-encoded shape"
                orig_lat, orig_lon = orig.coords[0]
                reenc_lat, reenc_lon = reenc.coords[0]
                assert reenc_lat == orig_lat, (
                    f"{ctx} coords[0] lat: {reenc_lat} != {orig_lat}"
                )
                assert reenc_lon == orig_lon, (
                    f"{ctx} coords[0] lon: {reenc_lon} != {orig_lon}"
                )

                # All subsequent coords (derived from delta bytes unchanged
                # in raw_bytes) must also match.
                assert len(reenc.coords) == len(orig.coords), (
                    f"{ctx} coord count: {len(reenc.coords)} vs {len(orig.coords)}"
                )
                for k, ((olat, olon), (rlat, rlon)) in enumerate(
                    zip(orig.coords, reenc.coords)
                ):
                    assert rlat == olat, f"{ctx} coords[{k}] lat mismatch"
                    assert rlon == olon, f"{ctx} coords[{k}] lon mismatch"

            n_shapes_checked += 1

        assert n_shapes_checked > 0, "expected at least one background shape"
        print(f"PASS: background encoder round-trip: {n_shapes_checked} shapes "
              f"all fields exact (bounds={bounds})")
    finally:
        disc.close()


def test_background_encoder_does_not_break_replicate_mode():
    """Calling write_background_frame() WITHOUT encode=True still produces
    byte-identical output (replicate mode unchanged after encoder addition)."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, loc = _load_parcel_with_background(disc)
        if parcel is None:
            print("SKIP: no parcel with non-point background shapes found")
            return

        import roundtrip_parcel_content as rtpc
        from kiwiw.parcel_writer import (
            write_map_frame,
            write_name_frame,
            write_road_frame,
        )

        road_bytes = (write_road_frame(parcel.road)
                      if parcel.road is not None else None)
        bg_bytes = write_background_frame(parcel.background)  # replicate mode
        name_bytes = (write_name_frame(parcel.name)
                      if parcel.name is not None else None)
        rebuilt = write_map_frame(parcel.frame, road_bytes, bg_bytes, name_bytes)

        # Read original bytes from disc.
        off = getsector(loc.sector_addr, disc.sector_sz, disc.logical_sz)
        disc._fh.seek(off)
        original = disc._fh.read(loc.size_logical_sectors * disc.logical_sz)

        assert rebuilt == original, (
            "replicate mode write_background_frame() produced non-identical "
            "bytes after background_writer.py was added to the codebase"
        )
        print("PASS: replicate mode write_background_frame() still byte-identical "
              "after encoder addition")
    finally:
        disc.close()


if __name__ == "__main__":
    test_background_encoder_roundtrip()
    test_background_encoder_does_not_break_replicate_mode()
