"""Phase 2 round-trip regression tests for the `IDX/*.IDX` search-index
writer (`kiwiw/index_writer.py`, see docs/phases/02-roundtrip.md).

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present, same convention as test_mesh.py / test_roundtrip_misc.py. Runs
standalone with plain `python3` (no pytest dependency required), and also
under pytest.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.search_frame import (
    parse_definition_frame,
    parse_matching_record,
    parse_search_frame,
    iter_matching_records,
    sws32,
    _u32,
)
from kiwiw.index_writer import (
    parse_detailed_search_info_raw,
    write_definition_frame,
    write_detailed_search_info_raw,
    write_dfsr_header,
    write_frame_ref_entry,
    write_matching_record,
)

ROOT = "/run/media/codyh/464210-8480"
SADSR = os.path.join(ROOT, "IDX", "SADSR201.IDX")
POISR = os.path.join(ROOT, "IDX", "POISR201.IDX")


def _skip(path):
    if not os.path.exists(path):
        print(f"SKIP: {path} not present (disc not mounted)")
        return True
    return False


def _load(path):
    with open(path, "rb") as fh:
        return fh.read()


def _frame_ref_bytes(buf, record_base, field_off):
    """Re-derive the resolved (file_offset, name) pair and the entry's own
    real byte range, exactly as roundtrip_idx.py's harness does."""
    raw_field = _u32(buf, record_base + field_off)
    entry_off = record_base + sws32(raw_field)
    import struct

    file_offset = _u32(buf, entry_off) * 2
    name_len = struct.unpack_from(">H", buf, entry_off + 4)[0] * 2
    name = buf[entry_off + 6 : entry_off + 6 + name_len].rstrip(b"\x00").decode("ascii")
    entry_size = 6 + name_len
    return entry_off, entry_size, file_offset, name


def test_dfsr_header_byte_identical():
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    decl = buf[0:4].decode("ascii")
    count = _u32(buf, 4)
    rec_size = sws32(_u32(buf, 8))
    first = sws32(_u32(buf, 12))
    rebuilt = write_dfsr_header(decl, count, rec_size, first)
    assert buf[0:16] == rebuilt
    print("PASS: SADSR201.IDX DFSR header round-trips byte-identical")


def test_detailed_search_info_record_byte_identical():
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    for r in parse_search_frame(buf, 0):
        raw = parse_detailed_search_info_raw(buf, r.record_base)
        rebuilt = write_detailed_search_info_raw(raw)
        assert buf[r.record_base : r.record_base + 92] == rebuilt, r.declaration
    print("PASS: SADSR201.IDX SRMX/SRHA Detailed Search Info Records round-trip byte-identical")


def test_frame_ref_entries_byte_identical():
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    si = next(r for r in parse_search_frame(buf, 0) if r.declaration == "SRMX")
    for field_off in (60, 68, 88):  # matching_data_definition, matching_data_frame, next_level
        entry_off, entry_size, file_offset, name = _frame_ref_bytes(buf, si.record_base, field_off)
        rebuilt = write_frame_ref_entry(file_offset, name)
        assert buf[entry_off : entry_off + entry_size] == rebuilt
    print("PASS: SADSR201.IDX additional-address (FrameRef) entries round-trip byte-identical")


def test_street_definition_frame_byte_identical():
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    si = next(r for r in parse_search_frame(buf, 0) if r.declaration == "SRMX")
    off = si.matching_data_definition.file_offset
    fields = parse_definition_frame(buf, off)
    rebuilt = write_definition_frame(fields)
    assert buf[off : off + len(rebuilt)] == rebuilt
    print(f"PASS: SADSR201.IDX street DCTF definition frame ({len(fields)} fields) round-trips byte-identical")


def test_all_street_records_byte_identical():
    """Full scan: every one of the 38,120 Street Name Search matching
    records round-trips byte-identical, not just a sample."""
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    si = next(r for r in parse_search_frame(buf, 0) if r.declaration == "SRMX")
    fields = parse_definition_frame(buf, si.matching_data_definition.file_offset)
    base = si.matching_data_frame.file_offset
    n = 0
    off = base
    while True:
        rec = parse_matching_record(buf, off, fields)
        rebuilt = write_matching_record(rec, fields)
        assert buf[off : off + len(rebuilt)] == rebuilt, f"street record @{off} mismatch"
        n += 1
        if rec["_nfrl"] == 0:
            break
        off += rec["_nfrl"]
    assert n == si.matching_record_count, f"expected {si.matching_record_count} records, walked {n}"
    print(f"PASS: all {n} street records round-trip byte-identical (full scan)")


def test_anchor_address_ranges_byte_identical():
    """The three anchor streets used to validate the read side
    (GADEN ROAD / GINGIN BROOK ROAD / GINGIN ROAD)."""
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    si = next(r for r in parse_search_frame(buf, 0) if r.declaration == "SRMX")
    street_fields = parse_definition_frame(buf, si.matching_data_definition.file_offset)
    street_base = si.matching_data_frame.file_offset
    rf = parse_search_frame(buf, si.next_level.file_offset)[0]
    range_fields = parse_definition_frame(buf, rf.matching_data_definition.file_offset)
    range_base = rf.matching_data_frame.file_offset

    anchors = {"GADEN ROAD", "GINGIN BROOK ROAD", "GINGIN ROAD"}
    found = set()
    for rec in iter_matching_records(buf, street_base, street_fields):
        name = rec.get("KYCH", "")
        if name not in anchors:
            continue
        found.add(name)
        nxst = sws32(rec.get("NXST", 0))
        nxct = rec.get("NXCT", 0)
        for rr in iter_matching_records(buf, range_base + nxst, range_fields, max_records=nxct):
            rebuilt = write_matching_record(rr, range_fields)
            off = rr["_offset"]
            assert buf[off : off + len(rebuilt)] == rebuilt, f"{name} address-range @{off} mismatch"
    assert found == anchors, f"missing anchor streets: {anchors - found}"
    print("PASS: GADEN ROAD / GINGIN BROOK ROAD / GINGIN ROAD address-range records round-trip byte-identical")


def test_poi_records_byte_identical_sample():
    if _skip(POISR):
        return
    buf = _load(POISR)
    info = parse_search_frame(buf, 0)[0]
    fields = parse_definition_frame(buf, info.matching_data_definition.file_offset)
    base = info.matching_data_frame.file_offset
    n = 0
    for rec in iter_matching_records(buf, base, fields, max_records=2000):
        rebuilt = write_matching_record(rec, fields)
        off = rec["_offset"]
        assert buf[off : off + len(rebuilt)] == rebuilt, f"POI record @{off} mismatch"
        n += 1
    print(f"PASS: {n} sampled POI records round-trip byte-identical")


def test_anchor_poi_burswood_car_rentals_byte_identical():
    if _skip(POISR):
        return
    buf = _load(POISR)
    info = parse_search_frame(buf, 0)[0]
    fields = parse_definition_frame(buf, info.matching_data_definition.file_offset)
    base = info.matching_data_frame.file_offset
    found = 0
    for rec in iter_matching_records(buf, base, fields):
        if "BURSWOOD CAR RENTALS" not in rec.get("NAME", ""):
            continue
        rebuilt = write_matching_record(rec, fields)
        off = rec["_offset"]
        assert buf[off : off + len(rebuilt)] == rebuilt
        found += 1
    assert found > 0, "BURSWOOD CAR RENTALS not found in POISR201.IDX"
    print(f"PASS: {found} BURSWOOD CAR RENTALS POI record(s) round-trip byte-identical")


def test_negative_control_perturbed_field_fails():
    """Perturbing one decoded field must change the rebuilt bytes -- proves
    the PASS results above aren't the harness comparing something to
    itself."""
    if _skip(SADSR):
        return
    buf = _load(SADSR)
    si = next(r for r in parse_search_frame(buf, 0) if r.declaration == "SRMX")
    fields = parse_definition_frame(buf, si.matching_data_definition.file_offset)
    base = si.matching_data_frame.file_offset
    rec = next(iter_matching_records(buf, base, fields, max_records=1))
    good = write_matching_record(rec, fields)
    original = buf[rec["_offset"] : rec["_offset"] + len(good)]
    assert good == original

    perturbed = dict(rec)
    perturbed["STID"] = rec["STID"] ^ 1
    bad = write_matching_record(perturbed, fields)
    assert bad != original, "perturbed STID must produce different bytes"
    print("PASS: perturbed STID field correctly produces a non-matching rebuild")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} tests run.")
