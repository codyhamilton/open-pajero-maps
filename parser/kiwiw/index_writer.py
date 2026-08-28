"""Writer functions (the inverse of `kiwiw.search_frame`'s read side) for the
self-describing `IDX/*.IDX` search/POI index chain: `DCTF` Matching Data
Definition Frames, per-record `STFG`-gated Matching Data Records (street
name, address range, and POI records alike -- they all share this one
generic machinery), `DFSR` search-frame headers, Detailed Search Info
Records (`SRMX`/`SRHA`/`SRT1`/...), and the SWS-halved "Additional
***Address" indirection-table entries those records point through.

Same discipline as `kiwiw.misc_writer` / `kiwiw.volume_writer`:

- Buffers that have a fixed known size are poison-filled with `0xA5`, not
  zeros, so a region the model forgets shows up as a diff rather than
  silently matching a zero-filled original.
- Nothing here is handed raw disc bytes to copy through wholesale -- each
  function takes only the parsed intermediate representation (the dict
  `search_frame.parse_matching_record` produces, a list of `FieldDef`s,
  etc.) and re-derives the bytes from typed fields.
- Where a region genuinely isn't understood (gaps in the Detailed Search
  Info Record layout that `search_frame.parse_detailed_search_info` never
  decodes), it is captured and replayed as verbatim hex, per the
  `COUNTRY.KWI` lesson from the metadata-file round-trip pass -- never
  forced through a lossy reinterpretation.

Scope note (see docs/phases/02-roundtrip.md for the full writeup): this
module reproduces each *structural piece* of the index-file format
byte-for-byte from its own parsed IR -- definition frames, individual
matching records, DFSR headers, Detailed Search Info Records, and
additional-address entries -- each validated against real bytes at that
piece's own byte range on the real disc. It does **not** attempt full-file
reassembly of a whole `SADSR*.IDX`/`POISR*.IDX` (i.e. it does not re-derive
*where in the file* each definition frame / matching-data frame /
additional-address entry should itself be placed) -- that is a materially
bigger, separate problem (the disc's file-layout allocation strategy), left
open here the same way `ALLDATA.KWI`'s parcel content was left open in the
container/mesh-layer pass.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional, Sequence

from .bitutils import geo_secs_bytes
from .search_frame import SENTINEL32, FieldDef, _TYPE_WIDTH

POISON = 0xA5


def unsws32(v: int) -> int:
    """Inverse of `search_frame.sws32`: halve a decoded value back to its
    stored form, leaving the 0xFFFFFFFF "not present" sentinel untouched.
    Raises on an odd value rather than silently writing the wrong bytes
    (mirrors `bitutils.unsws`'s discipline for the 16-bit case)."""
    if v == SENTINEL32:
        return v
    if v & 1:
        raise ValueError(f"{v} is odd -- cannot be an sws32-decoded value")
    return v >> 1


# ---------------------------------------------------------------------------
# 1. Generic self-describing frame machinery: DCTF definition frame + STFG-
#    gated Matching Data Records. This is the highest-leverage piece: street,
#    address-range and POI frames all reuse it unchanged.
# ---------------------------------------------------------------------------


def _ascii_field(s: str, size: int) -> bytes:
    raw = s.encode("ascii")
    if len(raw) > size:
        raise ValueError(f"{s!r} does not fit in {size} bytes")
    return raw + b"\x00" * (size - len(raw))


def write_field_def(fd: FieldDef) -> bytes:
    """Inverse of one 16-byte entry parsed by
    `search_frame.parse_definition_frame`: `[4B usage][4B description type]
    [2B element type][2B count-or-count-type][4B additional]`. For `VRBL`
    fields the "count" slot holds the count-field's own scalar type as
    ASCII text (e.g. `"UB"`) rather than a numeric count -- CONFIRMED
    against real `KYCH`/`NAME` entries in SADSR201.IDX's definition frame."""
    usage = _ascii_field(fd.usage, 4)
    dtype = _ascii_field(fd.description_type, 4)
    etype = _ascii_field(fd.element_type, 2)
    if fd.is_variable:
        count_field = _ascii_field(fd.count_type, 2)
    else:
        count_field = struct.pack(">H", fd.count)
    addl = _ascii_field(fd.additional, 4)
    return usage + dtype + etype + count_field + addl


def write_definition_frame(fields: Sequence[FieldDef]) -> bytes:
    """Inverse of `search_frame.parse_definition_frame`: the 16-byte
    'DCTF'/'REAL' declaration entry (layout: `[4B 'DCTF'][4B 'REAL']
    [2B zero][2B zero][2B zero][2B entry count]`) followed by one 16-byte
    entry per field, in order.

    CORRECTED 2026-08-28 (whole-file assembly pass): the declaration's
    entry-count field is the number of field entries *only* -- it does
    NOT include the header itself, despite this function's (and
    `search_frame.parse_definition_frame`'s pre-fix) docstrings previously
    claiming otherwise. See `search_frame.parse_definition_frame`'s
    docstring for the byte-level evidence (recomputing every real
    definition frame's end-of-frame offset against its neighbour's already
    -resolved anchor position, with zero exceptions once this is applied).
    The previous `len(fields) + 1` was silently "consistent" with the
    matching pre-fix over-subtraction on the read side, so the bug was
    invisible until this pass needed the frame's *total byte length* (not
    just a re-derived prefix) to place the next structure after it."""
    n_items = len(fields)
    header = (
        b"DCTF" + b"REAL" + b"\x00\x00" + b"\x00\x00" + b"\x00\x00"
        + struct.pack(">H", n_items)
    )
    out = bytearray(header)
    for fd in fields:
        out += write_field_def(fd)
    return bytes(out)


class _BitWriter:
    """Byte cursor that can also accept nibbles, mirroring
    `search_frame._BitReader`. Nibble fields (`NXKD`/`NXFN`, `RPNK`/`RPNF`,
    ...) must come in adjacent pairs on this disc -- CONFIRMED, every real
    record's nibble-typed fields appear back-to-back in the definition
    frame -- so an odd nibble left over when a byte-aligned field or the
    end of the record is reached raises loudly rather than silently
    dropping it."""

    def __init__(self) -> None:
        self.data = bytearray()
        self._pending_nibble: Optional[int] = None

    def bytes(self, b: bytes) -> None:
        if self._pending_nibble is not None:
            raise ValueError(
                "odd number of nibble fields written before a byte-aligned field"
            )
        self.data += b

    def nibble(self, v: int) -> None:
        if not 0 <= v <= 0xF:
            raise ValueError(f"{v} does not fit in a nibble")
        if self._pending_nibble is None:
            self._pending_nibble = v
        else:
            self.data.append((self._pending_nibble << 4) | v)
            self._pending_nibble = None

    def finish(self) -> bytes:
        if self._pending_nibble is not None:
            raise ValueError("unflushed nibble at end of record")
        return bytes(self.data)


def _write_scalar(bw: _BitWriter, type_: str, count: int, val) -> None:
    if type_ == "UH":
        vals = val if count > 1 else [val]
        for v in vals:
            bw.nibble(v)
        return
    if type_ == "BF":
        nbytes = (count + 7) // 8
        raw = bytes(val)
        if len(raw) != nbytes:
            raise ValueError(f"BF field expected {nbytes} bytes, got {len(raw)}")
        bw.bytes(raw)
        return
    if type_ == "P6":
        vals = val if count > 1 else [val]
        for lat, lon in vals:
            bw.bytes(geo_secs_bytes(lat) + geo_secs_bytes(lon))
        return
    width = int(_TYPE_WIDTH.get(type_, 1.0))
    if type_ in ("C", "SG"):
        bw.bytes(val.encode("ascii"))
        return
    vals = val if count > 1 else [val]
    for v in vals:
        bw.bytes(int(v).to_bytes(width, "big"))


def _write_field(bw: _BitWriter, fd: FieldDef, val) -> None:
    if fd.is_variable:
        count_type = fd.count_type or "UB"
        if fd.element_type == "CH":
            content = val.encode("ascii")
            n = len(content)
        else:
            vals = val if isinstance(val, list) else [val]
            n = len(vals)
        _write_scalar(bw, count_type, 1, n)
        if fd.element_type == "CH":
            bw.bytes(content)
        else:
            for v in vals:
                _write_scalar(bw, fd.element_type, 1, v)
        return
    _write_scalar(bw, fd.element_type, fd.count, val)


def write_matching_record(rec: dict, fields: Sequence[FieldDef]) -> bytes:
    """Inverse of `search_frame.parse_matching_record`: given the dict that
    function produced (raw halved `BFRL`/`NFRL`, the raw `STFG` presence
    bitmap, and every field the bitmap marked present) and the frame's own
    field definitions, re-emit the exact record bytes -- including the
    trailing zero pad-to-even-length byte the disc uses (CONFIRMED: on
    every real record sampled on this disc, from both the street name frame
    and the address range frame, the gap between the last decoded field and
    the record's real length is either 0 or exactly one zero byte -- see
    docs/phases/02-roundtrip.md for the sampled evidence).

    Works identically for street, address-range, and POI records: nothing
    here is specific to any one frame kind, only the `fields` list passed
    in differs.
    """
    bw = _BitWriter()
    gated = False
    stfg_bits: bytes = b""
    bit_index = 0
    for fd in fields:
        if gated:
            byte_i, bit_i = divmod(bit_index, 8)
            bit_index += 1
            present = byte_i < len(stfg_bits) and bool((stfg_bits[byte_i] >> bit_i) & 1)
            if not present:
                continue
        if fd.usage not in rec:
            raise ValueError(f"field {fd.usage!r} required but absent from record dict")
        val = rec[fd.usage]
        _write_field(bw, fd, val)
        if fd.usage == "STFG":
            stfg_bits = bytes(val) if isinstance(val, list) else bytes([val])
            gated = True
    data = bytearray(bw.finish())
    if len(data) % 2 == 1:
        data += b"\x00"
    return bytes(data)


# ---------------------------------------------------------------------------
# 2 & 4. DFSR search-frame header + Detailed Search Info Record (shared by
#    SRMX street name search, SRT1 address range, and POI hybrid search --
#    Ch.11.A.2.4.1.2 / 11.A.2.4.4.2 / 11.A.2.8.x all use the same 92-byte
#    layout, only the 4-byte declaration differs).
# ---------------------------------------------------------------------------


def write_dfsr_header(declaration: str, count: int, record_size: int, first_offset: int) -> bytes:
    """Inverse of the 16-byte header `search_frame.parse_search_frame`
    reads: `[4B declaration]['DFSR' etc][4B record count][4B SWS record
    size][4B D offset to first record]`."""
    if declaration not in ("DFSR", "DFSA", "DFSM", "DFM2", "DSRC"):
        raise ValueError(f"unexpected search-frame declaration {declaration!r}")
    return (
        declaration.encode("ascii")
        + struct.pack(">I", count)
        + struct.pack(">I", unsws32(record_size))
        + struct.pack(">I", unsws32(first_offset))
    )


@dataclass
class DetailedSearchInfoRaw:
    """The 92-byte Detailed Search Info Record, captured as *raw* stored
    field values (record-relative sws32-encoded pointers, not resolved
    through the additional-address indirection) plus the two undecoded gaps
    kept verbatim -- same "preserve what isn't understood" discipline as
    `CountryFile.raw_tail`. Every field here is a literal 4-byte offset into
    this struct; `parse_detailed_search_info_raw`/`write_detailed_search_info_raw`
    are exact inverses of each other by construction, and the round-trip
    test compares the rebuilt bytes against the real record bytes to
    confirm the offset map itself is right (a wrong offset would silently
    shift a field into the "gap" and fail the byte-diff instead of being
    hidden by re-deriving the same wrong value back).
    """

    declaration: str
    gap_4_16_hex: str
    category_definition_raw: int
    category_data_size_raw: int
    category_data_raw: int
    default_keyboard: str
    category_parent_record_size_raw: int
    category_option_record_size_raw: int
    first_level_category_size_raw: int
    first_level_category_options: int
    gap_48_60_hex: str
    matching_data_definition_raw: int
    matching_data_frame_size_raw: int
    matching_data_frame_raw: int
    matching_record_max_size_raw: int
    matching_record_count: int
    default_poi_serial: int
    next_level_size_raw: int
    next_level_raw: int


DSIR_SIZE = 92


def parse_detailed_search_info_raw(buf: bytes, base: int) -> DetailedSearchInfoRaw:
    def u32_(off: int) -> int:
        return struct.unpack_from(">I", buf, base + off)[0]

    return DetailedSearchInfoRaw(
        declaration=buf[base : base + 4].decode("ascii", errors="replace"),
        gap_4_16_hex=buf[base + 4 : base + 16].hex(),
        category_definition_raw=u32_(16),
        category_data_size_raw=u32_(20),
        category_data_raw=u32_(24),
        default_keyboard=buf[base + 28 : base + 32].decode("ascii", errors="replace"),
        category_parent_record_size_raw=u32_(32),
        category_option_record_size_raw=u32_(36),
        first_level_category_size_raw=u32_(40),
        first_level_category_options=u32_(44),
        gap_48_60_hex=buf[base + 48 : base + 60].hex(),
        matching_data_definition_raw=u32_(60),
        matching_data_frame_size_raw=u32_(64),
        matching_data_frame_raw=u32_(68),
        matching_record_max_size_raw=u32_(72),
        matching_record_count=u32_(76),
        default_poi_serial=u32_(80),
        next_level_size_raw=u32_(84),
        next_level_raw=u32_(88),
    )


def write_detailed_search_info_raw(d: DetailedSearchInfoRaw) -> bytes:
    buf = bytearray([POISON]) * DSIR_SIZE

    def put32(off: int, v: int) -> None:
        buf[off : off + 4] = struct.pack(">I", v)

    buf[0:4] = _ascii_field(d.declaration, 4)
    buf[4:16] = bytes.fromhex(d.gap_4_16_hex)
    put32(16, d.category_definition_raw)
    put32(20, d.category_data_size_raw)
    put32(24, d.category_data_raw)
    buf[28:32] = _ascii_field(d.default_keyboard, 4)
    put32(32, d.category_parent_record_size_raw)
    put32(36, d.category_option_record_size_raw)
    put32(40, d.first_level_category_size_raw)
    put32(44, d.first_level_category_options)
    buf[48:60] = bytes.fromhex(d.gap_48_60_hex)
    put32(60, d.matching_data_definition_raw)
    put32(64, d.matching_data_frame_size_raw)
    put32(68, d.matching_data_frame_raw)
    put32(72, d.matching_record_max_size_raw)
    put32(76, d.matching_record_count)
    put32(80, d.default_poi_serial)
    put32(84, d.next_level_size_raw)
    put32(88, d.next_level_raw)
    return bytes(buf)


# ---------------------------------------------------------------------------
# 3. "Additional ***Address" indirection-table entry -- the piece that bit
#    the read side badly (see index_data.py / search_frame.py module
#    docstrings): the entry's own 4-byte absolute file offset is itself
#    SWS-halved, on top of the record-relative pointer that reaches the
#    entry in the first place.
# ---------------------------------------------------------------------------


def write_frame_ref_entry(file_offset: int, filename: str) -> bytes:
    """Inverse of `search_frame._resolve_frame_ref` /
    `index_data._resolve_additional_address`: the little
    `[4B halved absolute file offset][2B halved name length][name]` struct.

    Both halved fields use the plain "stored = real / 2" convention (no
    0xFFFFFFFF/0xFFFF sentinel checked here, matching the read side, which
    doesn't check one either -- these entries are always resolved, never
    absent, on this disc).

    CONFIRMED against real bytes: on this disc every observed filename
    (`IDX/SADSR201.IDX`, `IDX/POISR201.IDX`, ...) is already even-length
    ASCII with no padding, so the "pad the name to even length" branch
    below is UNVALIDATED -- flagged rather than silently assumed correct.
    """
    if file_offset % 2 != 0:
        raise ValueError(f"file_offset {file_offset} must be even to SWS-halve")
    name_bytes = filename.encode("ascii")
    if len(name_bytes) % 2 == 1:
        name_bytes += b"\x00"  # UNVALIDATED: no real example of this on this disc
    return (
        struct.pack(">I", file_offset // 2)
        + struct.pack(">H", len(name_bytes) // 2)
        + name_bytes
    )
