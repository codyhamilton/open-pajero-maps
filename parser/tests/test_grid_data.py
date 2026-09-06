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


def test_matches_disc_lmr_decode():
    if not os.path.exists(DISC):
        print("SKIP: disc not mounted")
        return

    from osm_to_parcel_geometry import build_tile_grid_from_lmr
    from kiwiw import volume

    g = ReferenceGrid.load()
    # Any bbox works for this check -- build_tile_grid_from_lmr only uses
    # it to populate TileGrid.target, not the disc-derived grid fields.
    dummy_bbox = (110.0, -40.0, 150.0, -10.0)

    for level in LEVEL_ORDER:
        want = g.level(level)
        got = build_tile_grid_from_lmr(DISC, level, dummy_bbox)
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
