"""Checks for `parser/refdata/grid.json` / `mht29_frame.bin` and the
`kiwiw.grid.ReferenceGrid` loader built on them.

Most of these need no disc (they check the checked-in data itself); one
cross-checks against the mounted reference disc's own LMR decode and
skips if the disc isn't mounted.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.grid import ReferenceGrid  # noqa: E402

DISC = "/run/media/codyh/464210-8480/ALLDATA.KWI"

LEVEL_ORDER = [12, 10, 8, 6, 4, 2, 0]


def test_levels_present_in_order():
    g = ReferenceGrid.load()
    levels = [lvl["level"] for lvl in g.data["levels"]]
    assert levels == LEVEL_ORDER


def test_level_0_grid_is_4096_square():
    g = ReferenceGrid.load()
    lg = g.level(0)
    assert lg.nx == 4096
    assert lg.ny == 4096


def test_level_12_grid_is_1_by_1():
    g = ReferenceGrid.load()
    lg = g.level(12)
    assert lg.nx == 1
    assert lg.ny == 1


def test_coverage_and_lon_span():
    g = ReferenceGrid.load()
    c = g.coverage
    assert c["lon_lo"] == 90.0
    assert c["lon_hi"] == -142.0
    assert g.lon_span == 128.0


def test_mht29_frame_bytes():
    g = ReferenceGrid.load()
    frame = g.mht29_frame_bytes()
    assert len(frame) == 2048
    assert b"au" in frame


def test_n_basic_route_by_level():
    g = ReferenceGrid.load()
    assert g.to_level_mgmt_record(0).n_basic_route == 2
    assert g.to_level_mgmt_record(4).n_basic_route == 0


def _decode_disc_level_grid(disc_path: str, level: int):
    """Read `disc_path`'s PDMDH/LMR for `level` and return an object with
    `.nx`, `.ny`, `.cell_lat`, `.cell_lon` -- the same fields
    `osm_to_parcel_geometry.TileGrid.from_reference()` derives from the
    checked-in `ReferenceGrid`.

    This duplicates (deliberately -- it is a live cross-check, not part of
    any build path) the small decode that
    `osm_to_parcel_geometry.build_tile_grid_from_lmr` used to perform before
    unit 07 removed it: a build never reads the mounted reference disc
    (docs/design/target-disc.md, "Grid contract"), but this *test* still may,
    to prove the checked-in `grid.json` matches `R`'s own LMR.
    """
    from collections import namedtuple
    from kiwiw import volume

    with open(disc_path, "rb") as fh:
        raw_hdr = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_hdr)
        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        prdm = mht.entries[0]
        off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        fh.seek(off)
        raw_pdmdh = fh.read(prdm.size * hdr.logical_sector_size)
    pdmdh = volume.parse_pdmdh(raw_pdmdh)

    lmr = next((l for l in pdmdh.levels if l.level == level), None)
    if lmr is None:
        raise ValueError(f"No LMR for level {level}; available: "
                         f"{[l.level for l in pdmdh.levels]}")

    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    lon_span_raw = pdmdh.coverage.lon_hi - pdmdh.coverage.lon_lo
    lon_span = lon_span_raw + 360.0 if lon_span_raw < 0 else lon_span_raw

    Dims = namedtuple("Dims", "nx ny cell_lat cell_lon")
    return Dims(
        nx=lmr.grid_nx, ny=lmr.grid_ny,
        cell_lat=lat_span / lmr.grid_ny, cell_lon=lon_span / lmr.grid_nx,
    )


def test_matches_disc_lmr_decode():
    if not os.path.exists(DISC):
        print("SKIP: disc not mounted")
        return

    from kiwiw import volume

    g = ReferenceGrid.load()

    for level in LEVEL_ORDER:
        want = g.level(level)
        got = _decode_disc_level_grid(DISC, level)
        assert got.nx == want.nx, level
        assert got.ny == want.ny, level
        assert got.cell_lat == want.cell_lat, level
        assert got.cell_lon == want.cell_lon, level

    with open(DISC, "rb") as fh:
        raw_hdr = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_hdr)
        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        mht29 = mht.entries[29]
        off = volume.getsector(mht29.dsa, hdr.sector_size, hdr.logical_sector_size)
        fh.seek(off)
        disc_frame = fh.read(mht29.size * hdr.logical_sector_size)

    assert g.mht29_frame_bytes() == disc_frame
    print("PASS: ReferenceGrid matches live disc LMR decode and record-29 frame")
