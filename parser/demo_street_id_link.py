"""Demo/exploration script for the "Street ID -> Link ID -> ALLDATA.KWI"
indirection hypothesis (see docs/phases/01-format-analysis.md, section
"Street ID -> Link ID indirection hypothesis, 2026-08-25").

Status: NOT CONFIRMED. This script demonstrates:

1. The new, cleaner 4x4-byte decomposition of the SADSR201.IDX
   alphabetical matching record's 16-byte raw_prefix (area_code /
   street_id / next_level_field / tail) -- see
   `kiwiw.index_data.AlphabeticalMatchingRecord`.
2. The candidate resolutions tried for `next_level_field` as a pointer,
   and why each was rejected (doesn't land on an Address-Range-Search-
   shaped record).

Run: python3 parser/demo_street_id_link.py [disc_root]
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from kiwiw.index_data import (
    iter_alphabetical_matching_records,
    parse_search_frame_header,
    scan_length_prefixed_names,
)


def main() -> None:
    disc = sys.argv[1] if len(sys.argv) > 1 else "/run/media/codyh/464210-8480"
    path = f"{disc}/IDX/SADSR201.IDX"

    rec = parse_search_frame_header(path)
    print("SADSR201.IDX Detailed Search Info Record:")
    print(f"  matching_data_frame = {rec.matching_data_frame}")
    print(f"  next_level          = {rec.next_level}")
    print()

    with open(path, "rb") as fh:
        fh.seek(rec.next_level.file_offset)
        buf = fh.read(2_500_000)

    names = list(scan_length_prefixed_names(buf))
    # Skip record 0: our read window may start mid-record.
    walk_start = names[1].file_offset - 18
    walked = list(iter_alphabetical_matching_records(buf, walk_start, max_records=8000))

    target_names = {"GADEN ROAD", "GINGIN BROOK ROAD", "GINGIN ROAD"}
    targets = [r for r in walked if r.search_key in target_names]

    print("Real records, decomposed 16-byte raw_prefix into 4x4-byte fields:")
    for r in targets:
        print(
            f"  {r.search_key!r:20s} area_code={r.area_code.hex()} "
            f"street_id={r.street_id:#x} ({r.street_id}) "
            f"next_level_field={r.next_level_field:#x} ({r.next_level_field}) "
            f"tail={r.tail.hex()}"
        )
    print()

    # Distribution of `tail` across many real records: small integers,
    # never plausible as a byte offset into this multi-MB file --
    # evidence *against* `tail` being the pointer field.
    tails = sorted({r.tail.hex() for r in walked[:2000]})
    print(f"`tail` distribution over first 2000 records: {len(tails)} distinct values, "
          f"range {int(tails[0], 16)}..{int(tails[-1], 16)} -- consistent with a small "
          f"class/serial-number field, NOT a pointer.")
    print()

    # Candidate resolutions of `next_level_field` as a pointer, for the
    # GINGIN ROAD record specifically. All produce in-bounds offsets that
    # decode to *some* structured bytes, but none look like the expected
    # Address Range Search Matching Data Record shape (Ch.11.A.2.4.4.5:
    # 1B relprev, 1B relnext, 4B offset-to-POI-info, 2B POI-info-count,
    # 1B street-address-flag, variable street address...).
    gingin = next(r for r in targets if r.search_key == "GINGIN ROAD")
    file_size = _file_size(path)
    with open(path, "rb") as fh:
        full = fh.read()

    print("Candidate resolutions of GINGIN ROAD's next_level_field "
          f"({gingin.next_level_field:#x}) as a pointer (file size {file_size}):")
    candidates = {
        "raw absolute": gingin.next_level_field,
        "raw absolute x2 (sws32)": gingin.next_level_field * 2,
        "relative to next_level base": rec.next_level.file_offset + gingin.next_level_field,
        "relative to next_level base, x2": rec.next_level.file_offset + gingin.next_level_field * 2,
        "relative to matching_data_frame base": rec.matching_data_frame.file_offset + gingin.next_level_field,
        "relative to matching_data_frame base, x2": rec.matching_data_frame.file_offset + gingin.next_level_field * 2,
    }
    for label, off in candidates.items():
        if 0 <= off < file_size - 16:
            print(f"  {label:45s} -> offset {off:>9d}: {full[off:off+16].hex()}")
        else:
            print(f"  {label:45s} -> offset {off} OUT OF BOUNDS")

    print()
    print("None of the above land on a plausible Address Range Search")
    print("Matching Data Record. CONCLUSION: the Street ID -> Link ID ->")
    print("main-map indirection hypothesis is NOT confirmed end-to-end.")
    print("See docs/phases/01-format-analysis.md for the full writeup and")
    print("recommended next steps.")


def _file_size(path: str) -> int:
    import os

    return os.path.getsize(path)


if __name__ == "__main__":
    main()
