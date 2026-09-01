"""Phase 3 encoder tests: coordinate encoder and road-link encoder.

Two claims:

1. **Coordinate encoder round-trip**: `encode_region_coord(xc)` followed by
   `decode_region_coord()` returns the original xc exactly; and
   `latlon_to_xy(xy_to_latlon(x, y, bounds), bounds) == (x, y)` for real
   node coordinates.  Checked against 10 real road-link node positions
   taken from the Melbourne parcel at level 0.

2. **Road-link encoder round-trip**: `encode_road_link(link, bounds)` produces
   bytes that `decode_road_frame()` parses back to a RoadLink whose decoded
   fields are identical to the original (exact for all flag/attribute fields;
   exact for node pixel coordinates and therefore exact for node lat/lon).

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present, same convention as the other roundtrip tests.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import mesh
from kiwiw.coordconv import (
    decode_region_coord,
    encode_region_coord,
    latlon_to_xy,
    xy_to_latlon,
)
from kiwiw.disc import AllData
from kiwiw.parcel import decode_parcel
from kiwiw.road import decode_road_frame
from kiwiw.road_writer import encode_road_link
from kiwiw.volume import getsector

ROOT = "/run/media/codyh/464210-8480"
ALLDATA_PATH = os.path.join(ROOT, "ALLDATA.KWI")

# Level 0, Melbourne -- a parcel known to have road links (validated by the
# existing roundtrip tests); use the same coordinate as test_mesh.py.
LEVEL = 0
TEST_LAT, TEST_LON = -37.813629, 144.963058


def _open_disc():
    if not os.path.exists(ALLDATA_PATH):
        print(f"SKIP: {ALLDATA_PATH} not present (disc not mounted)")
        return None
    return AllData(ALLDATA_PATH)


def _load_parcel_with_road_links(disc):
    """Return (parcel, bounds) for a parcel that has at least one road link,
    searching TEST_POINTS at LEVEL until one is found."""
    import roundtrip_parcel_content as rtpc  # local to parser/
    for lat, lon in [(TEST_LAT, TEST_LON),
                     (-33.868820, 151.209290),
                     (-33.8148, 151.0011),
                     (-31.95312, 115.86719)]:
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
        if parcel.road is not None and parcel.road.links:
            return parcel, loc.bounds
    return None, None


# ---------------------------------------------------------------------------
# Coordinate encoder tests (no disc required for the pure math checks, but
# the real-data checks do require the disc).
# ---------------------------------------------------------------------------

def test_encode_region_coord_roundtrip_synthetic():
    """encode_region_coord is the right inverse of decode_region_coord for
    all representative pixel coordinates in 0..32767."""
    test_values = [0, 1, 100, 4095, 4096, 4097, 8191, 8192, 16384, 24576, 32767]
    for xc in test_values:
        raw = encode_region_coord(xc)
        recovered = decode_region_coord(raw)
        assert recovered == xc, (
            f"encode_region_coord({xc}) = {raw:#06x}, "
            f"decode_region_coord({raw:#06x}) = {recovered} (expected {xc})"
        )
    print(f"PASS: encode/decode roundtrip exact for {len(test_values)} synthetic values")


def test_latlon_to_xy_roundtrip_synthetic():
    """latlon_to_xy is the right inverse of xy_to_latlon for integer
    pixel coordinates within a realistic parcel bounding box."""
    from kiwiw.model import BoundingBox
    # A bounding box typical for a level-0 Melbourne parcel.
    bounds = BoundingBox(lat_lo=-37.85, lat_hi=-37.80,
                         lon_lo=144.95, lon_hi=145.00)
    test_pixels = [(0, 0), (100, 200), (16384, 16384), (32767, 0), (0, 32767)]
    for xc, yc in test_pixels:
        lat, lon = xy_to_latlon(xc, yc, bounds)
        xc2, yc2 = latlon_to_xy(lat, lon, bounds)
        assert (xc2, yc2) == (xc, yc), (
            f"xy_to_latlon({xc},{yc}) -> ({lat:.8f},{lon:.8f}) -> "
            f"latlon_to_xy -> ({xc2},{yc2}), expected ({xc},{yc})"
        )
    print(f"PASS: latlon_to_xy(xy_to_latlon(x,y)) == (x,y) for {len(test_pixels)} synthetic pixels")


def test_coordinate_encoder_roundtrip_real_nodes():
    """Take up to 10 real node positions from a disc parcel; for each:
    - Verify encode_region_coord(node.x) decodes back to node.x exactly.
    - Verify latlon_to_xy(node.lat, node.lon, bounds) == (node.x, node.y).
    """
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, bounds = _load_parcel_with_road_links(disc)
        if parcel is None:
            print("SKIP: no parcel with road links found")
            return

        nodes_checked = 0
        for link in parcel.road.links:
            for node in link.nodes:
                # Pixel-level round-trip for x
                sx_encoded = encode_region_coord(node.x)
                xc_recovered = decode_region_coord(sx_encoded)
                assert xc_recovered == node.x, (
                    f"encode_region_coord({node.x}) = {sx_encoded:#06x}, "
                    f"decode_region_coord -> {xc_recovered} (expected {node.x})"
                )

                # Pixel-level round-trip for y
                sy_encoded = encode_region_coord(node.y)
                yc_recovered = decode_region_coord(sy_encoded)
                assert yc_recovered == node.y, (
                    f"encode_region_coord({node.y}) = {sy_encoded:#06x}, "
                    f"decode_region_coord -> {yc_recovered} (expected {node.y})"
                )

                # latlon_to_xy must recover the exact pixel coords from
                # the lat/lon that xy_to_latlon produced.
                xc2, yc2 = latlon_to_xy(node.lat, node.lon, bounds)
                assert (xc2, yc2) == (node.x, node.y), (
                    f"latlon_to_xy({node.lat},{node.lon}) -> ({xc2},{yc2}), "
                    f"expected ({node.x},{node.y})"
                )

                nodes_checked += 1
                if nodes_checked >= 10:
                    break
            if nodes_checked >= 10:
                break

        assert nodes_checked > 0, "expected at least one node in the parcel"
        print(f"PASS: coordinate encoder exact round-trip for {nodes_checked} real nodes")
    finally:
        disc.close()


# ---------------------------------------------------------------------------
# Road-link encoder tests (require disc).
# ---------------------------------------------------------------------------

def test_road_link_encoder_roundtrip():
    """Decode a real parcel's road frame, re-encode each link via
    encode_road_link(), decode the result, and assert all fields match.

    Checks:
    - All boolean / integer attribute flags (exact)
    - n_nodes (exact)
    - display_class, road_type (exact)
    - RoadNode fields: x, y, lat, lon, oneway, planned, tunnel, bridge (exact)
    """
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, bounds = _load_parcel_with_road_links(disc)
        if parcel is None:
            print("SKIP: no parcel with road links found")
            return

        n_links = len(parcel.road.links)
        assert n_links > 0

        for orig_link in parcel.road.links:
            encoded = encode_road_link(orig_link, bounds)
            assert len(encoded) == len(orig_link.raw_bytes), (
                f"encoded length {len(encoded)} != original {len(orig_link.raw_bytes)}"
            )

            # Decode the re-encoded bytes (feed them as a complete road frame
            # buffer: we need the header context so decode_road_frame is
            # used; instead, re-decode the full frame after patching one link).

        # Re-encode the full road frame in encode mode and decode the result.
        from kiwiw.parcel_writer import write_road_frame
        road_bytes = write_road_frame(parcel.road, bounds=bounds, encode=True)

        # The re-encoded road frame must be the same size as the original.
        from kiwiw.parcel_writer import write_road_frame as wrf_orig
        orig_road_bytes = wrf_orig(parcel.road)  # replicate mode
        assert len(road_bytes) == len(orig_road_bytes), (
            f"encoded road frame length {len(road_bytes)} != "
            f"original {len(orig_road_bytes)}"
        )

        # Decode the re-encoded road frame and compare fields.
        reenc_frame = decode_road_frame(road_bytes, bounds)
        assert len(reenc_frame.links) == len(parcel.road.links)

        for i, (orig, reenc) in enumerate(
            zip(parcel.road.links, reenc_frame.links)
        ):
            ctx = f"link[{i}]"

            # Attribute flags and type fields (must be exact).
            assert reenc.display_class == orig.display_class, f"{ctx} display_class"
            assert reenc.road_type == orig.road_type, f"{ctx} road_type"
            assert reenc.altitude_flag == orig.altitude_flag, f"{ctx} altitude_flag"
            assert reenc.route_type_guidance_flag == orig.route_type_guidance_flag, \
                f"{ctx} route_type_guidance_flag"
            assert reenc.pseudo3d_updown == orig.pseudo3d_updown, f"{ctx} pseudo3d_updown"
            assert reenc.route_planning_tag == orig.route_planning_tag, \
                f"{ctx} route_planning_tag"
            assert reenc.link_id_flag == orig.link_id_flag, f"{ctx} link_id_flag"
            assert reenc.selected_link_flag == orig.selected_link_flag, \
                f"{ctx} selected_link_flag"
            assert reenc.toll_flag == orig.toll_flag, f"{ctx} toll_flag"
            assert reenc.route_number_flag == orig.route_number_flag, \
                f"{ctx} route_number_flag"
            assert reenc.infra_link_flag == orig.infra_link_flag, f"{ctx} infra_link_flag"
            assert reenc.link_id_number_flag == orig.link_id_number_flag, \
                f"{ctx} link_id_number_flag"

            # Node count (must be exact).
            assert reenc.n_nodes == orig.n_nodes, f"{ctx} n_nodes"
            assert len(reenc.nodes) == len(orig.nodes), f"{ctx} len(nodes)"

            # Node-level fields.
            for k, (on, rn) in enumerate(zip(orig.nodes, reenc.nodes)):
                nctx = f"{ctx} node[{k}]"
                assert rn.x == on.x, f"{nctx} x: {rn.x} != {on.x}"
                assert rn.y == on.y, f"{nctx} y: {rn.y} != {on.y}"
                assert rn.lat == on.lat, f"{nctx} lat: {rn.lat} != {on.lat}"
                assert rn.lon == on.lon, f"{nctx} lon: {rn.lon} != {on.lon}"
                assert rn.oneway == on.oneway, f"{nctx} oneway"
                assert rn.planned == on.planned, f"{nctx} planned"
                assert rn.tunnel == on.tunnel, f"{nctx} tunnel"
                assert rn.bridge == on.bridge, f"{nctx} bridge"

        print(f"PASS: road-link encoder round-trip for {n_links} links "
              f"(all fields exact, parcel bounds={bounds})")
    finally:
        disc.close()


def test_road_link_encoder_does_not_break_existing_replicate_mode():
    """Calling write_road_frame() WITHOUT encode=True still produces
    byte-identical output (replicate mode unchanged)."""
    disc = _open_disc()
    if disc is None:
        return
    try:
        parcel, bounds = _load_parcel_with_road_links(disc)
        if parcel is None:
            print("SKIP: no parcel with road links found")
            return

        import roundtrip_parcel_content as rtpc
        from kiwiw.parcel_writer import (
            write_background_frame,
            write_map_frame,
            write_name_frame,
            write_road_frame,
        )

        road_bytes = write_road_frame(parcel.road)  # replicate mode, no bounds
        bg_bytes = (write_background_frame(parcel.background)
                    if parcel.background is not None else None)
        name_bytes = (write_name_frame(parcel.name)
                      if parcel.name is not None else None)
        rebuilt = write_map_frame(parcel.frame, road_bytes, bg_bytes, name_bytes)

        # Read original bytes from disc.
        loc = parcel.location
        off = getsector(loc.sector_addr, disc.sector_sz, disc.logical_sz)
        disc._fh.seek(off)
        original = disc._fh.read(loc.size_logical_sectors * disc.logical_sz)

        assert rebuilt == original, (
            "replicate mode write_road_frame() produced non-identical bytes "
            "after road_writer.py was added to the codebase"
        )
        print("PASS: replicate mode write_road_frame() still byte-identical after encoder addition")
    finally:
        disc.close()


if __name__ == "__main__":
    test_encode_region_coord_roundtrip_synthetic()
    test_latlon_to_xy_roundtrip_synthetic()
    test_coordinate_encoder_roundtrip_real_nodes()
    test_road_link_encoder_roundtrip()
    test_road_link_encoder_does_not_break_existing_replicate_mode()
