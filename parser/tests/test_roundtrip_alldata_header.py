"""Phase 2 round-trip regression tests for ALLDATA.KWI's container/mesh
layer: the Ch. 5 All Data Management Frame and the Ch. 6 Parcel-related
Data Management Record (PDMDH + LMR + BSMR + BMT tables).

Scope note: parcel *content* (road/background/name frames) is deliberately
not covered here -- see docs/phases/02-roundtrip.md.

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present, same convention as test_mesh.py.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import volume, volume_writer

ROOT = "/run/media/codyh/464210-8480"
ALLDATA = os.path.join(ROOT, "ALLDATA.KWI")


def _open():
    if not os.path.exists(ALLDATA):
        print("SKIP: ALLDATA.KWI not present (disc not mounted)")
        return None
    return open(ALLDATA, "rb")


def test_data_volume_byte_identical():
    fh = _open()
    if fh is None:
        return
    with fh:
        raw = fh.read(volume.DATAVOL_SIZE)
    hdr = volume.parse_volume_header(raw)
    extras = volume.parse_volume_header_extras(raw)
    assert volume_writer.write_volume_header(hdr, extras) == raw
    print("PASS: Data Volume (Ch. 5.1) round-trips byte-identical")


def test_management_header_table_byte_identical():
    fh = _open()
    if fh is None:
        return
    with fh:
        fh.seek(volume.DATAVOL_SIZE)
        raw = fh.read(volume.MHT_SIZE)
    table = volume.parse_management_header_table(raw)
    assert volume_writer.write_management_header_table(table) == raw
    # The maker-original area of this disc's table is used as a plain
    # continuation of the 18-byte record grid (record 34 = COUNTRY.KWI),
    # which is why the whole 2048 bytes is modelled as 113 records.
    assert table.entries[34].name == "COUNTRY.KWI"
    print("PASS: Management Header Table (Ch. 5.2) round-trips byte-identical")


def test_pdmdh_record_byte_identical():
    fh = _open()
    if fh is None:
        return
    with fh:
        raw_hdr = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_hdr)
        table = volume.parse_management_header_table(fh.read(volume.MHT_SIZE))
        prdm = table.entries[0]
        assert not prdm.name, "expected an inline (not file-based) PDMDH"
        off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        fh.seek(off)
        raw = fh.read(prdm.size * hdr.logical_sector_size)
    pdmdh = volume.parse_pdmdh_full(raw)
    assert volume_writer.write_pdmdh(pdmdh) == raw
    # Sanity-check the structure the round-trip is asserting about, so a
    # trivially-empty parse could not pass this test.
    assert pdmdh.n_lmr == 7 and pdmdh.n_bsmr == 601
    assert sum(len(t.entries) for t in pdmdh.bmt_tables) == 2307
    print("PASS: PDMDH + LMR + BSMR + BMT (Ch. 6) round-trips byte-identical")


def test_lmr_size_is_fully_explained_by_frame_index_tables():
    """The LMR's 170-byte size is exactly 42 bytes of decoded fields plus
    three u16 sub-frame index tables sized by the extended-info word's
    road/background/name frame counts (16/32/16 here). Nothing is left
    over, which is what identified those tables in the first place."""
    fh = _open()
    if fh is None:
        return
    with fh:
        raw_hdr = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_hdr)
        table = volume.parse_management_header_table(fh.read(volume.MHT_SIZE))
        prdm = table.entries[0]
        fh.seek(volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size))
        raw = fh.read(prdm.size * hdr.logical_sector_size)
    pdmdh = volume.parse_pdmdh_full(raw)
    for lmr in pdmdh.levels:
        assert lmr.raw_tail_hex == "", f"level {lmr.level} has undecoded LMR bytes"
        assert (42 + 2 * (len(lmr.road_frame_table)
                          + len(lmr.background_frame_table)
                          + len(lmr.name_frame_table))) == pdmdh.lmr_size
    print("PASS: every LMR byte is accounted for by decoded fields")


if __name__ == "__main__":
    test_data_volume_byte_identical()
    test_management_header_table_byte_identical()
    test_pdmdh_record_byte_identical()
    test_lmr_size_is_fully_explained_by_frame_index_tables()
