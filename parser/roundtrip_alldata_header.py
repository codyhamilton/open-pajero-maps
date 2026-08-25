#!/usr/bin/env python3
"""Phase 2 round-trip harness for `ALLDATA.KWI`'s top structural layer.

Reads the real disc (mounted, or pass --root to point at an extracted copy
/ ISO mount point), parses only the container/mesh layer -- the Ch. 5 All
Data Management Frame (Data Volume + Management Header Table) and the
Ch. 6 Parcel-related Data Management Record (PDMDH + LMR + BSMR + BMT
tables) -- re-serializes it with `kiwiw.volume_writer`, and byte-diffs each
region against the original bytes at that exact file offset.

Deliberately *not* covered: parcel content (roads, background geometry,
names). That is a separate, much less well-understood layer; see
docs/phases/02-roundtrip.md.

Reporting follows parser/roundtrip_misc.py: PASS only on an exact match,
otherwise FAIL with the first differing file offset and a hex window. A
coverage summary additionally splits each region's bytes into "rebuilt
from decoded fields" vs "carried through verbatim", so a pass is not
mistaken for a stronger claim than it is.

Usage:
    python3 parser/roundtrip_alldata_header.py [--root /run/media/codyh/464210-8480]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from kiwiw import volume, volume_writer

DATAVOL_SIZE = volume.DATAVOL_SIZE
MHT_SIZE = volume.MHT_SIZE


def diff_report(name: str, original: bytes, rebuilt: bytes, base_offset: int) -> bool:
    """Byte-diff `rebuilt` against `original`; offsets are reported as
    absolute file offsets (`base_offset` + index)."""
    if original == rebuilt:
        print(f"PASS  {name}: byte-identical ({len(original)} bytes "
              f"at file offset {base_offset})")
        return True

    print(f"FAIL  {name}: original {len(original)} bytes, "
          f"rebuilt {len(rebuilt)} bytes (file offset {base_offset})")
    n = min(len(original), len(rebuilt))
    diffs = [i for i in range(n) if original[i] != rebuilt[i]]
    if not diffs:
        print(f"      bytes match up to the shorter length ({n}); the "
              f"{'original' if len(original) > n else 'rebuilt'} has extra "
              f"trailing bytes")
        return False
    first = diffs[0]
    lo, hi = max(0, first - 4), min(n, first + 12)
    print(f"      {len(diffs)} differing byte(s); first at file offset "
          f"{base_offset + first} (region offset {first})")
    print(f"      expected: {original[lo:hi].hex(' ')}")
    print(f"      actual:   {rebuilt[lo:hi].hex(' ')}")
    if len(diffs) > 1:
        tail = ", ".join(str(base_offset + d) for d in diffs[1:9])
        print(f"      further differing file offsets: {tail}"
              f"{' ...' if len(diffs) > 9 else ''}")
    return False


def coverage(total: int, verbatim_hex: list[str], note: str = "") -> None:
    """Report how much of a region was rebuilt from decoded, typed fields
    versus copied through as not-understood raw bytes -- and how much of
    that raw remainder is actually non-zero (zero-filled RESERVED areas are
    a much weaker caveat than live bytes nobody has decoded)."""
    verbatim = sum(len(h) // 2 for h in verbatim_hex)
    nonzero = sum(sum(1 for b in bytes.fromhex(h) if b) for h in verbatim_hex)
    decoded = total - verbatim
    pct = 100.0 * decoded / total if total else 0.0
    print(f"      coverage: {decoded}/{total} bytes ({pct:.1f}%) rebuilt from "
          f"decoded fields, {verbatim} carried verbatim "
          f"({nonzero} of those non-zero)"
          f"{(' -- ' + note) if note else ''}")


def check_all(root: str) -> int:
    path = os.path.join(root, "ALLDATA.KWI")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found -- is the disc mounted? "
              f"(pass --root to point elsewhere)")
        return 2

    results = []
    with open(path, "rb") as fh:
        # --- Ch. 5.1 Data Volume ---------------------------------------
        raw_header = fh.read(DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_header)
        extras = volume.parse_volume_header_extras(raw_header)
        rebuilt = volume_writer.write_volume_header(hdr, extras)
        results.append(diff_report("Data Volume (Ch. 5.1)", raw_header, rebuilt, 0))
        coverage(DATAVOL_SIZE,
                 extras.maker_defined_hex + [extras.reserved_478_hex,
                                              extras.level_mgmt_info_hex,
                                              extras.reserved_748_hex],
                 "maker-defined MID:C halves + the spec's RESERVED / Level "
                 "Management Information areas")

        # --- Ch. 5.2 Management Header Table ---------------------------
        raw_mht = fh.read(MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        rebuilt = volume_writer.write_management_header_table(mht)
        results.append(diff_report("Management Header Table (Ch. 5.2)",
                                    raw_mht, rebuilt, DATAVOL_SIZE))
        coverage(MHT_SIZE, [mht.tail_hex],
                 "14-byte remainder the 18-byte record grid cannot cover")
        used = [i for i, e in enumerate(mht.entries)
                if e.name or (e.dsa not in (0, 0xFFFFFFFF)) or e.size]
        print(f"      {len(used)} of {len(mht.entries)} management header "
              f"records point at real data (highest index {max(used)}; "
              f"Ch. 5.2 defines only records 0..32 plus a maker-original "
              f"area, so anything above index 32 is this disc's own use of "
              f"that area)")

        # --- Ch. 6 Parcel-related Data Management Record ---------------
        prdm = mht.entries[0]
        if prdm.name:
            print("SKIP  PDMDH: management record 1 names a file "
                  f"({prdm.name!r}); file-based parcel management is not "
                  "implemented on the read side either")
            return 0 if all(results) else 1
        prdm_off = volume.getsector(prdm.dsa, hdr.sector_size,
                                     hdr.logical_sector_size)
        prdm_size = prdm.size * hdr.logical_sector_size
        fh.seek(prdm_off)
        raw_prdm = fh.read(prdm_size)
        pdmdh = volume.parse_pdmdh_full(raw_prdm)
        rebuilt = volume_writer.write_pdmdh(pdmdh)
        results.append(diff_report(
            "Parcel-related Data Management Record: PDMDH + LMR + BSMR + BMT "
            "(Ch. 6)", raw_prdm, rebuilt, prdm_off))
        coverage(prdm_size,
                 [pdmdh.header_gap_hex, pdmdh.trailing_padding_hex]
                 + [l.raw_tail_hex for l in pdmdh.levels],
                 "6 undecoded PDMDH header bytes + trailing sector padding")
        n_bmt = sum(len(t.entries) for t in pdmdh.bmt_tables)
        print(f"      {pdmdh.n_lmr} levels, {pdmdh.n_bsmr} block sets, "
              f"{len(pdmdh.bmt_tables)} block management tables / "
              f"{n_bmt} block entries")

    # Region between the management header table and the PDMDH record is
    # not part of this layer; say so rather than quietly ignoring it.
    gap_lo, gap_hi = DATAVOL_SIZE + MHT_SIZE, prdm_off
    if gap_hi > gap_lo:
        owners = []
        for i, e in enumerate(mht.entries):
            if e.name or e.dsa in (0, 0xFFFFFFFF) or not e.size:
                continue
            eoff = volume.getsector(e.dsa, hdr.sector_size, hdr.logical_sector_size)
            if gap_lo <= eoff < gap_hi:
                owners.append(f"record {i} (offset {eoff}, "
                              f"{e.size * hdr.logical_sector_size} bytes)")
        owned = ("; ".join(owners) if owners
                 else "not referenced by any management header record")
        print(f"\nNOT ATTEMPTED: file offsets {gap_lo}..{gap_hi} "
              f"({gap_hi - gap_lo} bytes) sit between the Management Header "
              f"Table and the parcel management record. This is another "
              f"management frame, not part of this layer: {owned}.")
    print("NOT ATTEMPTED: parcel content (road / background / name frames) -- "
          "out of scope for this pass.")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} ALLDATA.KWI header/table regions byte-identical")
    return 0 if passed == len(results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/run/media/codyh/464210-8480",
                     help="path to the mounted/extracted disc root")
    args = ap.parse_args()
    return check_all(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
