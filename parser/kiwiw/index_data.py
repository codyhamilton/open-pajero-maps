"""Chapter 11 "Management Pattern of Index Data" decoders: ``INDEXDAT.KWI``
and the ``IDX/*.IDX`` search/POI families (Street Address Search, POI
Search/Information, and friends).

Confidence levels (see docs/phases/01-format-analysis.md "Index/search
data frame decoding" for the full writeup) -- everything below is graded
one of:

- CONFIRMED: real bytes from this disc decoded and cross-checked against
  the archived spec's byte-offset tables, with plausible/verifiable
  content (a real signature string, a real date, real AU street/POI
  names, ...).
- STRUCTURAL: the byte layout matches the spec's table shape and produces
  self-consistent pointers, but the semantic meaning of some fields is
  not independently verified against real-world ground truth.
- UNCONFIRMED / GUESS: filename-prefix pattern-matching or a plausible
  read of the spec text only, not yet exercised against real bytes.

Key disc-wide finding (CONFIRMED): the 4-byte "SWS"/"D" (size/displacement)
fields used throughout Chapter 11's record tables are stored *halved*,
exactly like the 2-byte SWS/D convention `kiwiw.bitutils.sws()` already
documented for the Ch. 5-7 main map frame -- multiply by 2 to get the real
byte value, except the sentinel (here 0xFFFFFFFF, vs. 0xFFFF for the
16-bit version) which means "absent" and is left untouched. This was
independently re-derived here (via aligning offsets in SADSR201.IDX/
INDEXDAT.KWI against real found signatures/records) before noticing
`bitutils.sws()` already encodes the same halving trick for 16-bit fields
-- strong cross-confirmation that this is a real, disc-wide encoding
convention rather than a coincidence of one file.

Second disc-wide finding (CONFIRMED, added while investigating the
coordinate-decoding blocker): the same halving convention also applies to
the **1-byte** "D" relation fields ("Relation to the Top of the Previous/
Following Record") used in the Matching Data Record chains -- see
`AlphabeticalMatchingRecord`/`iter_alphabetical_matching_records` below.
Real byte value = stored value * 2, with no sentinel observed at this
width on this disc.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO, Iterator, Optional

SENTINEL32 = 0xFFFFFFFF


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from(">I", buf, off)[0]


def sws32(v: int) -> int:
    """The Chapter 11 32-bit analogue of `bitutils.sws()`: stored value is
    half the real size/offset, except the 0xFFFFFFFF "not present"
    sentinel which is left as-is. CONFIRMED (see module docstring)."""
    return v if v == SENTINEL32 else v * 2


def read_cstr(buf: bytes, off: int, maxlen: int) -> str:
    end = buf.find(b"\x00", off, off + maxlen)
    if end < 0:
        end = off + maxlen
    return buf[off:end].decode("ascii", errors="replace")


# ---------------------------------------------------------------------------
# INDEXDAT.KWI / per-directory Data Management Frame header (Ch. 11.2)
# ---------------------------------------------------------------------------


@dataclass
class DataManagementFrameHeader:
    """Ch. 11.2.1 Data Management Frame Header. CONFIRMED against
    INDEXDAT.KWI: signature 'DCTR', format version '2.64_AU', creation
    date 2007-12-12 01:12:03 (matches the real Dec 2007 file dates seen
    on this disc), copyright 'DENSO CORPORATION' (exact string match)."""

    declaration: str
    format_version: str
    created: str  # YYYYMMDDhhmmssss as decoded from BCD
    copyright: str
    user_field_size: int
    user_field_offset: int
    expansion_field_size: int
    expansion_field_offset: int
    n_volume_mgmt_records: int
    volume_mgmt_record_size: int
    volume_mgmt_record_offset: int
    n_poi_mgmt_records: int
    poi_mgmt_record_size: int
    poi_mgmt_record_offset: int


def _bcd_byte(b: int) -> str:
    return f"{(b >> 4) & 0xF}{b & 0xF}"


def parse_data_management_frame_header(buf: bytes) -> DataManagementFrameHeader:
    decl = buf[0:4].decode("ascii")
    assert decl == "DCTR", f"expected 'DCTR' data declaration, got {decl!r}"
    fmt = buf[4:12].rstrip(b"\x00").decode("ascii", errors="replace")
    date_bytes = buf[12:20]
    ymd = "".join(_bcd_byte(b) for b in date_bytes)
    created = (
        f"{ymd[0:4]}-{ymd[4:6]}-{ymd[6:8]} {ymd[8:10]}:{ymd[10:12]}:{ymd[12:14]}.{ymd[14:16]}"
    )
    copyright_ = buf[20:52].rstrip(b"\x00").decode("ascii", errors="replace")
    return DataManagementFrameHeader(
        declaration=decl,
        format_version=fmt,
        created=created,
        copyright=copyright_,
        user_field_size=u32(buf, 52),
        user_field_offset=u32(buf, 56),
        expansion_field_size=u32(buf, 60),
        expansion_field_offset=u32(buf, 64),
        n_volume_mgmt_records=u32(buf, 68),
        volume_mgmt_record_size=u32(buf, 72),
        volume_mgmt_record_offset=u32(buf, 76),
        n_poi_mgmt_records=u32(buf, 80),
        poi_mgmt_record_size=u32(buf, 84),
        poi_mgmt_record_offset=u32(buf, 88),
    )


def parse_indexdat(path: str) -> DataManagementFrameHeader:
    with open(path, "rb") as fh:
        buf = fh.read(256)
    return parse_data_management_frame_header(buf)


# ---------------------------------------------------------------------------
# Search Frame Management Frame + Detailed Search Info Record (Ch. 11.A.2.4.1
# "SRMX" pattern -- CONFIRMED structurally identical across SADSR*.IDX and
# POISR*.IDX; the Detailed Search Info Record table for street name search
# (11.A.2.4.1.2) and for POI hybrid search (11.A.2.8) share the same
# 'DFSR'/'SRMX' framing this module decodes.)
# ---------------------------------------------------------------------------


@dataclass
class AdditionalAddress:
    """A resolved '***Address' + 'Additional ***Address' pair (Ch. 11.2.2
    note 9): a small table entry consisting of an absolute file offset, a
    (same-file, so far as observed) filename, giving the true location of
    a target frame. CONFIRMED empirically: every address field below
    (category definition/data, matching-data definition/data, next-level)
    resolves through exactly this indirection -- `raw_field * 2 + 16`
    (record-relative, doubled per sws32) lands exactly on one of these
    little structs, whose own 4-byte `file_offset` is the real, directly
    usable absolute offset into `filename`."""

    file_offset: int
    filename: str


@dataclass
class DetailedSearchInfoRecord:
    """Ch. 11.A.2.4.1.2 / (structurally shared by 11.A.2.8 POI search).
    STRUCTURAL/CONFIRMED: field layout matches the spec table and all
    five address fields below resolve (via sws32 + the additional-address
    indirection) to distinct, self-consistent regions of the file."""

    default_keyboard: str
    category_definition: Optional[AdditionalAddress]
    category_data: Optional[AdditionalAddress]
    matching_data_definition: Optional[AdditionalAddress]
    matching_data_frame: Optional[AdditionalAddress]
    next_level: Optional[AdditionalAddress]
    matching_record_max_size: int
    matching_record_count: int


def _resolve_additional_address(
    buf: bytes, record_base: int, raw_field: int
) -> Optional[AdditionalAddress]:
    """`raw_field` is the value straight out of e.g. "Category Definition
    Frame Address": halve-encoded (sws32) and record-relative. Doubling
    it and adding it to `record_base` (the SRMX record's own start)
    lands on a little [4-byte absolute offset][2-byte sws32 name size]
    [name, NUL-padded to even] struct -- see `AdditionalAddress`.

    Returns None if the field is the 0xFFFFFFFF "not present" sentinel
    (e.g. POISR*.IDX's Detailed Search Info Record has no "next-level"
    frame -- POI hybrid search resolves through matching_data_frame
    instead)."""
    if raw_field == SENTINEL32:
        return None
    entry_off = record_base + sws32(raw_field)
    file_offset = u32(buf, entry_off)
    name_size_words = struct.unpack_from(">H", buf, entry_off + 4)[0]
    name_size = name_size_words * 2
    filename = buf[entry_off + 6 : entry_off + 6 + name_size].rstrip(b"\x00").decode("ascii", errors="replace")
    return AdditionalAddress(file_offset=file_offset, filename=filename)


def parse_detailed_search_info_record(buf: bytes, record_base: int) -> DetailedSearchInfoRecord:
    decl = buf[record_base : record_base + 4].decode("ascii", errors="replace")
    assert decl == "SRMX", f"expected 'SRMX' at {record_base}, got {decl!r}"
    kbd = buf[record_base + 28 : record_base + 32].decode("ascii", errors="replace")

    catdef_raw = u32(buf, record_base + 16)
    catdata_raw = u32(buf, record_base + 24)
    mddf_raw = u32(buf, record_base + 60)
    mdf_raw = u32(buf, record_base + 68)
    mdf_rec_size = sws32(u32(buf, record_base + 72))
    mdf_rec_count = u32(buf, record_base + 76)
    next_raw = u32(buf, record_base + 88)

    return DetailedSearchInfoRecord(
        default_keyboard=kbd,
        category_definition=_resolve_additional_address(buf, record_base, catdef_raw),
        category_data=_resolve_additional_address(buf, record_base, catdata_raw),
        matching_data_definition=_resolve_additional_address(buf, record_base, mddf_raw),
        matching_data_frame=_resolve_additional_address(buf, record_base, mdf_raw),
        next_level=_resolve_additional_address(buf, record_base, next_raw),
        matching_record_max_size=mdf_rec_size,
        matching_record_count=mdf_rec_count,
    )


def parse_search_frame_header(path: str, read_size: int = 8192) -> DetailedSearchInfoRecord:
    """Parse the Management Frame of Search Frame (Ch. 11.A.2.4.1.1) at
    the top of a SADSR*/POISR*.IDX file and return its first Detailed
    Search Info Record ('SRMX'), fully resolved."""
    with open(path, "rb") as fh:
        buf = fh.read(read_size)
    decl = buf[0:4].decode("ascii", errors="replace")
    assert decl == "DFSR", f"expected 'DFSR' management frame header, got {decl!r}"
    return parse_detailed_search_info_record(buf, 16)


# ---------------------------------------------------------------------------
# Heuristic name scanner: neither the exact Street-Name Matching Data
# Record (11.A.2.4.1.6) nor the POI hybrid-search matching data record's
# bitfield "Stored Data Flag" variants have been fully cracked (see the
# module docstring / phase doc for what remains unconfirmed). What *is*
# solidly confirmed is that both formats store names as a 1-byte length
# prefix followed by that many bytes of printable ASCII -- this scanner
# exploits exactly that, independent of the surrounding fixed-field
# semantics, and is good enough to pull out real street/POI names.
# ---------------------------------------------------------------------------


@dataclass
class NameEntry:
    file_offset: int
    length: int
    text: str


@dataclass
class AlphabeticalMatchingRecord:
    """Ch. 11.A.2.4.5.2.5.1 "Street Name Search (alphabetical order search)
    Matching Data Record" as it actually appears on this disc's SADSR*.IDX
    `next_level` frame -- CONFIRMED record framing/boundaries. Coordinate
    field content is still NOT decoded to a lat/lon, but the archived
    Ch.11.A.2.4.5.2.5.1 field table (re-read 2026-08-25, see
    docs/phases/01-format-analysis.md "Street ID -> Link ID indirection
    hypothesis" for the full writeup) let this pass go one level deeper
    than the previous "16 undecoded bytes" state.

    ``file_offset``/``relprev``/``relnext`` are CONFIRMED: this is a
    doubly-linked chain of variable-length records, and ``relprev``/
    ``relnext`` (each stored **1-byte SWS-halved**) give the exact byte
    displacement to the previous/next record. Walking the chain via
    ``relnext`` reproduces the same records (in the same order) as
    independently scanning for length-prefixed strings and inferring
    boundaries from inter-string spacing.

    ``raw_prefix`` (the 16 bytes between ``relnext`` and the search-key
    length byte, record bytes [2:18)) splits *exactly* into four 4-byte
    big-endian fields with no remainder -- this clean fit (vs. the
    previous pass's fuzzy "constant/monotonic/constant" byte-range
    description) is itself new evidence that Ch.11.A.2.4.5.2.5.1's
    conditional ('c') Fuzzy Search Flag (1B) and Latitude/Longitude (6B)
    fields really are omitted on this disc (1+6+4=11 bytes would leave
    5 leftover, unaccounted bytes; 4+4+4+4=16 leaves none):

    - ``area_code`` (bytes [0:4)): matches the spec's mandatory ('a')
      "Area Code" field. CONFIRMED-ish: near-constant across long runs of
      consecutive alphabetical records (e.g. `80 7f 00 46` for all
      sampled F-street names, ticking to `80 7f 00 47` at the G's) --
      consistent with a coarse geographic/administrative zone id, not a
      coordinate.
    - ``street_id`` (bytes [4:8)): STRUCTURAL guess. Increases
      quasi-monotonically as the alphabetical list progresses. Does
      *not* line up with the spec's literal field order (which places
      "Street ID" *after* the name, not before it) -- another instance
      of the disc's real field order not matching the spec table's
      declared order, already seen elsewhere in this module.
    - ``next_level_field`` (bytes [8:12)): UNCONFIRMED, still the open
      question. Leading candidate for the spec's mandatory "Offset to
      Next-level Data Frame" (which per the spec should point at this
      street's Address Range Search Matching Data Record --
      Ch.11.A.2.4.4.5 -- whose own "Offset to POI Information" field is
      what finally reaches a Street Address POI Information Record with
      real RLXY + Link ID, per Ch.11.A.2.14.1.4). Tried resolving it as
      an absolute file offset under the sws32 halving convention
      (doubled, no base added): this DOES land in-bounds and on
      byte patterns that structurally resemble *other* Street Name
      Search (alphabetical) records elsewhere in the same file (i.e.
      `area_code`/`street_id`/`next_level_field`/`tail`-shaped data
      again) rather than on an Address Range Search record's shape --
      so either this field isn't what the spec calls "Offset to
      Next-level Data Frame", or the correct base/transform for
      resolving it is still wrong. Tried bases: raw absolute (doubled
      and undoubled), relative to `next_level.file_offset`, relative to
      `matching_data_frame.file_offset` (each doubled and undoubled) --
      none produced an unambiguous Address-Range-Search-shaped record.
      NOT to be treated as working.
    - ``tail`` (bytes [12:16)): small integer (observed range 1-38 across
      ~2000 real records sampled), never a plausible byte offset in this
      15MB file. Consistent with the spec's "Next-level Data Frame Class"
      + "Next-level Data Frame Serial Number" (both small, packed
      sub-byte fields per the spec) rather than a pointer -- e.g.
      plausibly a per-street address-range-segment count. UNCONFIRMED.

    Bottom line: the Street ID -> Link ID -> ALLDATA.KWI indirection
    hypothesis from the previous pass is NOT confirmed end-to-end this
    pass either. What's new is a cleaner, better-motivated decomposition
    of the previously-opaque 16-byte prefix, and an empirical ruling-out
    of several most-likely offset/base combinations for the pointer field
    -- see docs/phases/01-format-analysis.md for the full log of what was
    tried and what to try next."""

    file_offset: int
    relprev: int
    relnext: int
    raw_prefix: bytes
    search_key: str

    @property
    def area_code(self) -> bytes:
        return self.raw_prefix[0:4]

    @property
    def street_id(self) -> int:
        return int.from_bytes(self.raw_prefix[4:8], "big")

    @property
    def next_level_field(self) -> int:
        return int.from_bytes(self.raw_prefix[8:12], "big")

    @property
    def tail(self) -> bytes:
        return self.raw_prefix[12:16]


def iter_alphabetical_matching_records(
    buf: bytes, start: int, max_records: Optional[int] = None
) -> Iterator[AlphabeticalMatchingRecord]:
    """Walk the `relnext` chain of Street Name Search (alphabetical order)
    Matching Data Records starting at record-relative buffer offset
    `start` (i.e. `start` must point at the `relprev` byte of a real
    record -- e.g. found via `scan_length_prefixed_names` and subtracting
    18, or by locating record 0 via a `relprev == 0` check). CONFIRMED
    (see `AlphabeticalMatchingRecord`) to walk real SADSR201.IDX records
    self-consistently: each record's `relprev` equals the previous
    record's `relnext`, checked against >20 consecutive real records.
    Stops when `relnext` is 0 (spec: "If ... following record does not
    exist, the appropriate field contains 0") or bounds are exceeded."""
    off = start
    n = 0
    while 0 <= off < len(buf) - 19 and (max_records is None or n < max_records):
        relprev = buf[off] * 2
        relnext = buf[off + 1] * 2
        raw_prefix = buf[off + 2 : off + 18]
        name_len = buf[off + 18]
        search_key = buf[off + 19 : off + 19 + name_len].decode("ascii", errors="replace")
        yield AlphabeticalMatchingRecord(
            file_offset=off,
            relprev=relprev,
            relnext=relnext,
            raw_prefix=raw_prefix,
            search_key=search_key,
        )
        n += 1
        if relnext == 0:
            break
        off += relnext


def scan_length_prefixed_names(
    buf: bytes, start: int = 0, end: Optional[int] = None, min_len: int = 3, max_len: int = 40
) -> Iterator[NameEntry]:
    """UNCONFIRMED at the bit-field level (see docstring), but CONFIRMED
    to work in practice: yields every `[1-byte length][ascii text]` run
    found in `buf[start:end]`, e.g. real street names in SADSR*.IDX
    ("DUCKPOND ROAD") or business names in POISR*/POIDT*.IDX
    ("PALMERS MOBILE HIRE")."""
    if end is None:
        end = len(buf)
    i = start
    while i < end - 1:
        length = buf[i]
        if min_len <= length <= max_len and i + 1 + length <= end:
            s = buf[i + 1 : i + 1 + length]
            if all(32 <= b < 127 for b in s):
                text = s.decode("ascii")
                if any(c.isalpha() for c in text):
                    yield NameEntry(file_offset=i, length=length, text=text)
                    i += 1 + length
                    continue
        i += 1


def iter_names_from_file(path: str, offset: int, size: Optional[int] = None, window: int = 2_000_000) -> Iterator[NameEntry]:
    """Scan for length-prefixed names starting at absolute file `offset`
    (typically a `DetailedSearchInfoRecord.next_level.file_offset` or
    `.matching_data_frame.file_offset`), reading at most `window` bytes
    (or `size` if given and smaller) at a time."""
    with open(path, "rb") as fh:
        fh.seek(offset)
        to_read = window if size is None else min(window, size)
        buf = fh.read(to_read)
    yield from scan_length_prefixed_names(buf)


if __name__ == "__main__":
    import sys

    disc = sys.argv[1] if len(sys.argv) > 1 else "/run/media/codyh/464210-8480"

    print("=== INDEXDAT.KWI (Data Management Frame, Ch. 11.2) ===")
    hdr = parse_indexdat(f"{disc}/INDEXDAT.KWI")
    print(hdr)

    print()
    print("=== SADSR201.IDX (Street Address Search, Ch. 11.A.2.4) ===")
    rec = parse_search_frame_header(f"{disc}/IDX/SADSR201.IDX")
    print(rec)
    names = list(
        iter_names_from_file(
            f"{disc}/IDX/SADSR201.IDX",
            rec.next_level.file_offset,
            window=200_000,
        )
    )
    print(f"-- sample of {len(names)} names found in next-level frame --")
    for n in names[:15]:
        print(f"  @{n.file_offset}: {n.text!r}")

    print()
    print("=== SADSR201.IDX Alphabetical Matching Data Record chain walk ===")
    print("(record framing CONFIRMED; coordinate/raw_prefix content NOT decoded --")
    print(" see AlphabeticalMatchingRecord docstring / docs/phases/01-format-analysis.md)")
    with open(f"{disc}/IDX/SADSR201.IDX", "rb") as fh:
        fh.seek(rec.next_level.file_offset)
        chain_buf = fh.read(400_000)
    chain_names = list(scan_length_prefixed_names(chain_buf))
    # Skip the first hit: it may start before our read window (mid-file cut).
    walk_start = chain_names[1].file_offset - 18
    walked = list(iter_alphabetical_matching_records(chain_buf, walk_start, max_records=15))
    for r in walked:
        print(f"  @{r.file_offset}: relprev={r.relprev:4d} relnext={r.relnext:4d} "
              f"raw_prefix={r.raw_prefix.hex()} search_key={r.search_key!r}")

    print()
    print("=== POISR201.IDX (POI Search, Ch. 11.A.2.8) ===")
    poi_rec = parse_search_frame_header(f"{disc}/IDX/POISR201.IDX")
    print(poi_rec)
    # POISR's Detailed Search Info Record has no next-level frame (it's
    # the sentinel/None) -- POI names live in the matching data frame.
    poi_target = poi_rec.next_level or poi_rec.matching_data_frame
    poi_names = list(
        iter_names_from_file(
            f"{disc}/IDX/POISR201.IDX",
            poi_target.file_offset,
            window=200_000,
        )
    )
    print(f"-- sample of {len(poi_names)} names found in next-level frame --")
    for n in poi_names[:15]:
        print(f"  @{n.file_offset}: {n.text!r}")
