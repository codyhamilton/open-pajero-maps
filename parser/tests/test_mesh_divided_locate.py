"""Brief 28: locate_parcel divided-parcel descent (synthetic fixtures).

Hand-laid pdat: a type-0 root record (1x1, size==0 -> subparcel) descending
into a type-1 (2x2) record, whose entries are leaves or, for one quadrant,
a further type-2 (4x4) record.
"""
import io
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import mesh
from kiwiw.model import BoundingBox, BlockSetMgmtRecord, LevelMgmtRecord
from kiwiw.volume import Pdmdh

SECTOR, LOGICAL = 4096, 512
LAT_LO, LON_LO, SPAN = -34.0, 151.0, 0.25
# The level grid is 2x2 (type-0 records are 2x2); the divided cell under
# test is the NE one (px=py=1), whose bounds are the top-right quarter.
CELL = SPAN / 2
CLAT, CLON = LAT_LO + CELL, LON_LO + CELL


def _lmr():
    return LevelMgmtRecord(
        level=0, upper_level=0, lower_level=0, n_basic_map=0, n_ext_map=0,
        n_basic_route=0, n_ext_route=0, display_flags=[],
        n_blocksets_lat=0, n_blocksets_lng=0, n_blocks_lat=0, n_blocks_lng=0,
        n_parcels_lat=[1, 1, 3, 0], n_parcels_lng=[1, 1, 3, 0],
        bsmr_offset=0, node_record_size=0, grid_nx=2, grid_ny=2)


def _pdmdh():
    return Pdmdh(coverage=BoundingBox(lat_lo=LAT_LO, lat_hi=LAT_LO + SPAN,
                                      lon_lo=LON_LO, lon_hi=LON_LO + SPAN),
                 lmr_size=0, bsmr_size=0, bmr_size=0, n_lmr=1, n_bsmr=1,
                 levels=[_lmr()],
                 blocksets=[BlockSetMgmtRecord(level=0, blockset_index=0,
                                               bmt_offset=0, bmt_size=6)],
                 bsmr_table_offset=0, bmt_table_base=0)


def _rec(off, pt, entries, buf):
    struct.pack_into(">H", buf, off, pt << 8)
    for i, (dsa, size) in enumerate(entries):
        struct.pack_into(">IH", buf, off + 4 + i * 6, dsa, size)


def _fixture(deep):
    buf = bytearray(512)
    # root type-0 record at 0 (2x2); NE entry (idx 3) -> subparcel at byte 64
    _rec(0, 0, [(0x800, 1), (0x840, 1), (0x880, 1), (64 // 2, 0)], buf)
    # type-1 (2x2) at 64: idx = lpy*2+lpx; leaves 0x100+idx*0x40, size 1
    ents = [(0x100 + i * 0x40, 1) for i in range(4)]
    if deep:
        ents[3] = (192 // 2, 0)  # NE quadrant -> type-2 record at 192
    _rec(64, 1, ents, buf)
    if deep:
        _rec(192, 2, [(0x1000 + i * 0x40, 1) for i in range(16)], buf)
    zdat0 = struct.pack(">IH", 0, 1)  # BMT entry: dsa 0 (offset 0), size 1
    return io.BytesIO(bytes(buf)), zdat0


def _locate(fh, zdat0, lat, lon):
    return mesh.locate_parcel(fh, zdat0, _pdmdh(), 0, lat, lon, SECTOR, LOGICAL)


def _contains(b, lat, lon):
    return b.lat_lo <= lat <= b.lat_hi and b.lon_lo <= lon <= b.lon_hi


def test_type1_quadrants():
    fh, z = _fixture(False)
    for qy in (0, 1):
        for qx in (0, 1):
            lat = CLAT + CELL * (qy + 0.5) / 2
            lon = CLON + CELL * (qx + 0.5) / 2
            loc = _locate(fh, z, lat, lon)
            assert loc.parcel_type == 1
            assert loc.parcel_index == qy * 2 + qx
            assert _contains(loc.bounds, lat, lon)
            assert abs((loc.bounds.lat_hi - loc.bounds.lat_lo) - CELL / 2) < 1e-9


def test_type2_divided_root():
    fh, z = _fixture(True)
    # NE quadrant (index 3) descends into a 4x4 type-2 record
    for qy in range(4):
        for qx in range(4):
            lat = CLAT + (CELL / 2) + (CELL / 2) * (qy + 0.5) / 4
            lon = CLON + (CELL / 2) + (CELL / 2) * (qx + 0.5) / 4
            loc = _locate(fh, z, lat, lon)
            assert loc.parcel_type == 2
            assert loc.parcel_index == qy * 4 + qx
            assert _contains(loc.bounds, lat, lon)
            assert abs((loc.bounds.lat_hi - loc.bounds.lat_lo) - CELL / 8) < 1e-9


def test_depth3_sibling_unaffected():
    fh, z = _fixture(True)
    lat, lon = CLAT + CELL * 0.25, CLON + CELL * 0.25  # SW leaf of type-1
    loc = _locate(fh, z, lat, lon)
    assert loc.parcel_type == 1 and loc.parcel_index == 0
    assert _contains(loc.bounds, lat, lon)


def test_undivided_unchanged():
    fh, z = _fixture(False)
    lat, lon = LAT_LO + 0.01, LON_LO + 0.01  # SW cell: plain type-0 leaf
    loc = _locate(fh, z, lat, lon)
    assert loc.parcel_type == 0 and loc.parcel_index == 0
    assert (loc.bounds.lat_lo, loc.bounds.lat_hi) == (LAT_LO, LAT_LO + CELL)
