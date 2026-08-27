#!/usr/bin/env python3
"""Round-trip harness for the `IDX/*.IDX` search-index writer
(`kiwiw/index_writer.py`), the Phase 2 write-direction counterpart to
`kiwiw/search_frame.py`.

    python3 parser/roundtrip_idx.py [DISC_ROOT]

Per docs/phases/02-roundtrip.md, this validates each *structural piece* of
the index format against real bytes at that piece's own byte range --
`DCTF` definition frames, individual Matching Data Records (street name,
address range, and POI), `DFSR` headers, Detailed Search Info Records, and
the SWS-halved additional-address indirection entries -- rather than
reassembling a whole file from scratch (see index_writer.py's module
docstring for why that's explicitly out of scope here).

Prints PASS/FAIL per structural piece, plus:
  - anchor-record checks (GADEN ROAD / GINGIN BROOK ROAD / GINGIN ROAD
    streets, BURSWOOD CAR RENTALS POI) called out by name
  - a broad sample: every street record, every address-range record
    reachable from the sampled streets, and a sample of POI records
  - negative controls: perturbing one decoded field must make the
    byte-diff fail, proving PASS isn't a harness artifact
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kiwiw.search_frame import (  # noqa: E402
    FieldDef,
    parse_definition_frame,
    parse_matching_record,
    parse_search_frame,
    iter_matching_records,
    sws32,
    _u32,
)
from kiwiw.index_writer import (  # noqa: E402
    DetailedSearchInfoRaw,
    parse_detailed_search_info_raw,
    write_definition_frame,
    write_detailed_search_info_raw,
    write_dfsr_header,
    write_frame_ref_entry,
    write_matching_record,
)

DEFAULT_DISC = "/run/media/codyh/464210-8480"

results: list[tuple[str, bool, str]] = []


def check(name: str, expected: bytes, actual: bytes) -> bool:
    ok = expected == actual
    if ok:
        results.append((name, True, f"{len(expected)} bytes"))
    else:
        n = min(len(expected), len(actual))
        first_diff = next((i for i in range(n) if expected[i] != actual[i]), n)
        detail = (
            f"len expected={len(expected)} actual={len(actual)}, "
            f"first diff @{first_diff}: "
            f"expected={expected[max(0,first_diff-4):first_diff+8].hex()} "
            f"actual={actual[max(0,first_diff-4):first_diff+8].hex()}"
        )
        results.append((name, False, detail))
    return ok


def check_dfsr_header(buf: bytes, base: int) -> None:
    decl = buf[base : base + 4].decode("ascii")
    count = _u32(buf, base + 4)
    rec_size = sws32(_u32(buf, base + 8))
    first = sws32(_u32(buf, base + 12))
    rebuilt = write_dfsr_header(decl, count, rec_size, first)
    check(f"DFSR header @{base} ({decl})", buf[base : base + 16], rebuilt)


def check_dsir(buf: bytes, base: int, label: str) -> None:
    raw = parse_detailed_search_info_raw(buf, base)
    rebuilt = write_detailed_search_info_raw(raw)
    check(f"DSIR @{base} ({label})", buf[base : base + 92], rebuilt)


def check_frame_ref(buf: bytes, record_base: int, field_off: int, label: str) -> None:
    raw_field = _u32(buf, record_base + field_off)
    entry_off = record_base + sws32(raw_field)
    import struct

    file_offset = _u32(buf, entry_off) * 2
    name_len = struct.unpack_from(">H", buf, entry_off + 4)[0] * 2
    name = buf[entry_off + 6 : entry_off + 6 + name_len].rstrip(b"\x00").decode("ascii")
    entry_size = 6 + name_len
    rebuilt = write_frame_ref_entry(file_offset, name)
    check(f"FrameRef entry @{entry_off} ({label} -> {name!r})", buf[entry_off : entry_off + entry_size], rebuilt)


def check_definition_frame(buf: bytes, off: int, label: str) -> list[FieldDef]:
    fields = parse_definition_frame(buf, off)
    rebuilt = write_definition_frame(fields)
    check(f"DCTF definition frame @{off} ({label}, {len(fields)} fields)", buf[off : off + len(rebuilt)], rebuilt)
    return fields


def check_records(
    buf: bytes, base: int, fields: list[FieldDef], label: str, max_records: int | None
) -> tuple[int, int]:
    """Round-trip every record in the chain (or up to max_records). Returns
    (n_checked, n_failed)."""
    n = 0
    n_fail = 0
    off = base
    while off is not None and 0 <= off < len(buf) and (max_records is None or n < max_records):
        rec = parse_matching_record(buf, off, fields)
        rebuilt = write_matching_record(rec, fields)
        total_len = rec["_nfrl"] if rec["_nfrl"] else (rec["_consumed"] + rec["_consumed"] % 2)
        expected = buf[off : off + len(rebuilt)]
        ok = expected == rebuilt
        n += 1
        if not ok:
            n_fail += 1
            if n_fail <= 5:
                first_diff = next(
                    (i for i in range(min(len(expected), len(rebuilt))) if expected[i] != rebuilt[i]),
                    min(len(expected), len(rebuilt)),
                )
                print(
                    f"    FAIL record @{off}: len expected={len(expected)} actual={len(rebuilt)} "
                    f"first diff @{first_diff} expected={expected.hex()} actual={rebuilt.hex()}"
                )
        if rec["_nfrl"] == 0:
            break
        off += rec["_nfrl"]
    results.append((f"{label}: {n} records sampled", n_fail == 0, f"{n_fail} failed"))
    return n, n_fail


def negative_controls(buf: bytes, street_base: int, street_fields: list[FieldDef]) -> None:
    """Perturb one decoded field and confirm the byte-diff now fails --
    proves the PASS results above aren't the harness comparing bytes to
    themselves."""
    rec = next(iter_matching_records(buf, street_base, street_fields, max_records=1))
    good = write_matching_record(rec, street_fields)
    original = buf[rec["_offset"] : rec["_offset"] + len(good)]
    assert good == original, "sanity: unperturbed record must still match before running negative controls"

    perturbed = dict(rec)
    perturbed["STID"] = rec["STID"] ^ 1
    bad = write_matching_record(perturbed, street_fields)
    ok = bad != original
    results.append(("negative control: perturbed STID must differ", ok, "OK" if ok else "BUG: perturbation had no effect"))

    perturbed2 = dict(rec)
    perturbed2["KYCH"] = rec["KYCH"] + "X"
    bad2 = write_matching_record(perturbed2, street_fields)
    ok2 = bad2 != original
    results.append(("negative control: perturbed KYCH must differ", ok2, "OK" if ok2 else "BUG: perturbation had no effect"))

    # Definition-frame negative control: change one field's count.
    fields_copy = list(street_fields)
    import dataclasses

    fields_copy[4] = dataclasses.replace(fields_copy[4], count=fields_copy[4].count + 1)
    from kiwiw.index_writer import write_definition_frame

    def_off = None  # not needed; we compare against the good rebuild directly
    good_def = write_definition_frame(street_fields)
    bad_def = write_definition_frame(fields_copy)
    ok3 = bad_def != good_def
    results.append(("negative control: perturbed FieldDef.count must differ", ok3, "OK" if ok3 else "BUG"))


def main() -> int:
    disc = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DISC
    sadsr_path = os.path.join(disc, "IDX", "SADSR201.IDX")
    poisr_path = os.path.join(disc, "IDX", "POISR201.IDX")

    print("=" * 78)
    print("SADSR201.IDX (Street Address Search)")
    print("=" * 78)
    with open(sadsr_path, "rb") as fh:
        buf = fh.read()

    check_dfsr_header(buf, 0)
    recs = parse_search_frame(buf, 0)
    si = next(r for r in recs if r.declaration == "SRMX")
    sha = next(r for r in recs if r.declaration == "SRHA")

    for r in (si, sha):
        check_dsir(buf, r.record_base, r.declaration)
        check_frame_ref(buf, r.record_base, 60, f"{r.declaration}.matching_data_definition")
        check_frame_ref(buf, r.record_base, 68, f"{r.declaration}.matching_data_frame")
        if r is si:
            check_frame_ref(buf, r.record_base, 88, f"{r.declaration}.next_level")

    street_fields = check_definition_frame(buf, si.matching_data_definition.file_offset, "SRMX street records")
    street_base = si.matching_data_frame.file_offset

    # Nested address-range (SRT1) frame.
    range_dfsr_base = si.next_level.file_offset
    check_dfsr_header(buf, range_dfsr_base)
    rf = parse_search_frame(buf, range_dfsr_base)[0]
    check_dsir(buf, rf.record_base, rf.declaration)
    check_frame_ref(buf, rf.record_base, 60, f"{rf.declaration}.matching_data_definition")
    check_frame_ref(buf, rf.record_base, 68, f"{rf.declaration}.matching_data_frame")
    range_fields = check_definition_frame(buf, rf.matching_data_definition.file_offset, "SRT1 address-range records")
    range_base = rf.matching_data_frame.file_offset

    print()
    print("-- broad sample: every street record (38,120 expected) --")
    n_streets, n_street_fail = check_records(buf, street_base, street_fields, "street records (full scan)", None)
    print(f"   {n_streets} street records checked, {n_street_fail} failed")

    print()
    print("-- broad sample: address-range records for the first 200 streets' ranges + anchors --")
    anchor_names = {"GADEN ROAD", "GINGIN BROOK ROAD", "GINGIN ROAD"}
    found_anchors = set()
    n_range_total = 0
    n_range_fail_total = 0
    sample_count = 0
    for rec in iter_matching_records(buf, street_base, street_fields, max_records=None):
        name = rec.get("KYCH", "")
        is_anchor = name in anchor_names
        if is_anchor:
            found_anchors.add(name)
        if is_anchor or sample_count < 200:
            nxst = sws32(rec.get("NXST", 0))
            nxct = rec.get("NXCT", 0)
            n, nf = check_records(buf, range_base + nxst, range_fields, f"address ranges for {name!r}", nxct)
            n_range_total += n
            n_range_fail_total += nf
            if not is_anchor:
                sample_count += 1
    print(f"   {n_range_total} address-range records checked across sampled streets, {n_range_fail_total} failed")
    missing = anchor_names - found_anchors
    results.append(("anchor streets found: GADEN/GINGIN BROOK/GINGIN ROAD", not missing, f"missing: {missing}" if missing else "all 3 found"))

    negative_controls(buf, street_base, street_fields)

    if os.path.exists(poisr_path):
        print()
        print("=" * 78)
        print("POISR201.IDX (POI Search)")
        print("=" * 78)
        with open(poisr_path, "rb") as fh:
            pbuf = fh.read()
        check_dfsr_header(pbuf, 0)
        precs = parse_search_frame(pbuf, 0)
        pinfo = precs[0]
        check_dsir(pbuf, pinfo.record_base, pinfo.declaration)
        check_frame_ref(pbuf, pinfo.record_base, 60, f"{pinfo.declaration}.matching_data_definition")
        check_frame_ref(pbuf, pinfo.record_base, 68, f"{pinfo.declaration}.matching_data_frame")
        poi_fields = check_definition_frame(pbuf, pinfo.matching_data_definition.file_offset, "POI records")
        poi_base = pinfo.matching_data_frame.file_offset

        print()
        print("-- broad sample: first 2000 POI records + BURSWOOD CAR RENTALS anchor --")
        n, nf = check_records(pbuf, poi_base, poi_fields, "POI records (sample of 2000)", 2000)
        print(f"   {n} POI records checked, {nf} failed")

        found_burswood = False
        checked_burswood = 0
        for rec in iter_matching_records(pbuf, poi_base, poi_fields, max_records=None):
            if "BURSWOOD CAR RENTALS" in rec.get("NAME", ""):
                found_burswood = True
                rebuilt = write_matching_record(rec, poi_fields)
                off = rec["_offset"]
                expected = pbuf[off : off + len(rebuilt)]
                check(f"POI anchor BURSWOOD CAR RENTALS @{off}", expected, rebuilt)
                checked_burswood += 1
        results.append(("anchor POI BURSWOOD CAR RENTALS found", found_burswood, f"{checked_burswood} matching records"))

    print()
    print("=" * 78)
    print("RESULTS")
    print("=" * 78)
    n_pass = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    print()
    print(f"{n_pass}/{len(results)} checks passed")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
