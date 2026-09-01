"""Generic KIWI-W Chapter 11 *search frame* decoder -- the piece that turns
a typed street name or POI name into a real lat/lon on the map.

This module supersedes the hand-rolled, per-file byte-offset guessing in
``index_data.py``.  The key realisation (2026-08-25) is that **the index
files are self-describing**: every Matching Data Frame is preceded by a
*Matching Data Definition Frame* (a ``DCTF`` block, Ch.11.5) that lists,
in order, the exact fields of every record in that frame together with
their data type and repeat count.  Combined with each record's own
"Stored Data Flag" (``STFG``) presence bitmap, that is enough to parse
any record in any of the disc's search files *without* guessing offsets.

Confidence summary (see docs/phases/01-format-analysis.md for the log):

- CONFIRMED: the ``DCTF`` definition-frame entry layout, the STFG presence
  bitmap convention, the ``P6`` coordinate type, the address-range record
  content, and the whole street-name -> coordinate chain.  Validated by
  decoding all 344,207 Address Range Search records in ``SADSR201.IDX``:
  every single one lands inside lat -35.125..-14.29, lon 113.44..128.94,
  which is Western Australia's real bounding box to within a parcel
  (including the exact 129 deg E WA/NT state border), with zero outliers.
  Spot-checked street names resolve to their real-world locations
  (ST GEORGES TERRACE -> Perth CBD, STIRLING HIGHWAY -> Claremont,
  WANNEROO ROAD -> Balcatta, ALBANY HIGHWAY -> Albany, GINGIN BROOK ROAD
  -> Gingin).
- CONFIRMED: ``AdditionalAddress.file_offset`` is stored **halved**, like
  every other address/offset field in Chapter 11 (this was the bug that
  blocked the previous three investigation passes -- see
  ``index_data._resolve_additional_address``).

Chain implemented here (Ch.11.A.2.4 "Street Address Search"), all of it
verified against real bytes on this disc:

    SADSR201.IDX
      DFSR management frame header
        -> SRMX Detailed Search Info Record #1 ("STREET ADDRESS")
             .matching_data_frame  -> 38,120 alphabetically sorted
                                      Street Name Search matching records
                                      (BFRL/NFRL/FGFZ/STFG/STID/NXKD/NXFN/
                                       NXST/NXCT/KYCH)
             .next_level           -> a nested DFSR + SRT1 record
                                      ("ADDRESS RANGE", Ch.11.A.2.4.4)
                  .matching_data_frame -> 344,207 Address Range Search
                                          matching records, each carrying
                                          FGSA/ARCD/**RLXY**/**LKID**/
                                          STFG/ZIPN/PRFX/STAD

    street record .NXST (halved!) * 2  ==  byte offset of that street's
    first Address Range record inside the address-range matching data
    frame; .NXCT is how many consecutive records belong to it.

``RLXY`` is the "P6" type: two 3-byte ``geo_secs`` angles (bit 23 = sign,
low 23 bits = 1/8 arc-second), i.e. a Ch.1.2.13 Parcel ID with the two
exponent bytes dropped -- exactly ``bitutils.geo_secs`` already used for
the main map frame.  Per Ch.11.A.2.14 footnote 4 this is "the coordinates
of the link start point", so it is a coarse link-locating coordinate, not
a house-accurate one; ``STAD`` (house number range) plus the main map's
link geometry is what the head unit interpolates against for a precise
house position.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import BinaryIO, Iterator, List, Optional, Sequence

from .bitutils import geo_secs

SENTINEL32 = 0xFFFFFFFF


def _u16(buf: bytes, off: int) -> int:
    return struct.unpack_from(">H", buf, off)[0]


def _u32(buf: bytes, off: int) -> int:
    return struct.unpack_from(">I", buf, off)[0]


def sws32(v: int) -> int:
    """Chapter 11's 32-bit "stored halved" convention (sibling of
    ``bitutils.sws``).  CONFIRMED."""
    return v if v == SENTINEL32 else v * 2


# ---------------------------------------------------------------------------
# Definition frames ('DCTF') -- Ch. 11.5
# ---------------------------------------------------------------------------

# Byte width of each scalar description type.  Fractional widths are
# nibble-packed fields (the spec writes them as "1/2" in its byte tables).
# CONFIRMED for every type actually used by this disc's index files
# (UB/UW/UL/LG/UH/P6/BF/CH); the rest are read straight off the spec's
# type table and are STRUCTURAL only.
_TYPE_WIDTH = {
    "UB": 1.0, "SB": 1.0,
    "UW": 2.0, "SW": 2.0,
    "UL": 4.0, "SL": 4.0,
    "LG": 4.0,
    "UH": 0.5,
    "P6": 6.0,
    "CH": 1.0,
    "SG": 4.0,
    "C": 4.0,
}


@dataclass
class FieldDef:
    """One 16-byte entry of a ``DCTF`` definition frame.

    Layout (CONFIRMED against SADSR201/POISR201):
    ``[4B usage][4B description type][2B element type][2B count-or-count-type]
    [4B additional information]``.

    - ``description_type`` is ``NORM`` (plain scalar), ``VRBL``
      (length-prefixed vector), ``FDRL`` (record-relative displacement),
      ``OFST`` (frame-relative offset), ``ACTN``, or ``REAL`` (the
      declaration entry itself).
    - For ``VRBL`` fields, ``element_type`` is the element's scalar type
      and ``count_type`` is the scalar type of the leading length field.
    - For everything else, ``count`` is the repeat count (a ``BF``
      bitfield's count is in *bits*, not elements).
    """

    usage: str
    description_type: str
    element_type: str
    count: int
    count_type: str
    additional: str

    @property
    def is_variable(self) -> bool:
        return self.description_type == "VRBL"


def parse_definition_frame(buf: bytes, off: int) -> List[FieldDef]:
    """Parse a ``DCTF`` definition frame at ``off``.

    CORRECTED 2026-08-28 (whole-file `IDX` assembly pass, see
    docs/phases/02-roundtrip.md "Whole-file IDX/*.IDX assembly"): the
    declaration entry's last 2 bytes (``n_items``) give the number of
    field entries *following* the header, **not** "including itself" as
    previously documented/implemented (``range(1, n_items)``, one short).
    This under-parsed every definition frame on this disc by exactly one
    trailing field -- e.g. the street-record matching-data-definition
    frame really has 16 fields (``...RPNS, RPNC``), not 15; the
    address-range frame really has 14 (``...STYP, GDXY``), not 13; every
    category-definition frame really has 8 (``...NEXT, NTSZ``), not 7.

    This was invisible to every previous round-trip check because they
    all compared ``buf[off:off+len(rebuilt)]`` -- a byte *prefix* -- never
    the frame's full span out to the next known structure, and because
    the missing trailing field happens to be STFG-gated and never
    actually asserted present in any record on this disc (so omitting it
    from the field list did not change a single decoded record value).
    Confirmed by recomputing, for all 7 real `DCTF` definition frames in
    SADSR201.IDX (2 top-level catdef, 2 top-level mdef, the nested
    address-range frame's catdef/mdef, and its own SRT1 mdef), that
    ``off + 16 * (n_items + 1)`` lands exactly on the next frame's known
    anchor offset (its neighbour's already-resolved FrameRef file_offset)
    with zero exceptions -- i.e. this is what makes whole-file byte
    accounting close with no unexplained gap.  Fixing it does not change
    ``parse_matching_record``'s output for any record already validated
    (the extra field's presence bit is always 0), so the previously-
    reported 232/232 structural-piece and 38,120-street full-scan results
    are unaffected -- confirmed by re-running the full existing suite
    after this change (see roundtrip_idx.py's own output)."""
    decl = buf[off : off + 4].decode("ascii", errors="replace")
    if decl != "DCTF":
        raise ValueError(f"expected 'DCTF' definition frame at {off}, got {decl!r}")
    n_items = _u16(buf, off + 14)
    fields: List[FieldDef] = []
    for i in range(1, n_items + 1):
        e = off + 16 * i
        usage = buf[e : e + 4].decode("ascii", errors="replace")
        dtype = buf[e + 4 : e + 8].decode("ascii", errors="replace")
        # CORRECTED 2026-08-28 (whole-file assembly pass): right-strip only,
        # not `.strip()`. `write_field_def` always right-pads with NUL, so a
        # genuine ASCII tag (e.g. "CMCH") never has leading NULs to worry
        # about -- but a field like a category-definition frame's `DCSF`
        # entry's "additional" slot is really a raw big-endian integer
        # (0x00000003), which happens to *decode* as ASCII '\x00\x00\x00\x03'.
        # The old `.strip("\x00 ")` silently dropped its leading NUL bytes,
        # so `write_field_def` re-padded on the wrong side (right instead of
        # left) and produced 0x03000000 instead of 0x00000003 -- invisible
        # under the old prefix-only round-trip checks, caught only by this
        # pass's full-frame byte comparison of a category_definition frame
        # (offset 896 in SADSR201.IDX) that no earlier test exercised.
        etype = buf[e + 8 : e + 10].decode("ascii", errors="replace").rstrip("\x00 ")
        raw_count = buf[e + 10 : e + 12]
        addl = buf[e + 12 : e + 16].decode("ascii", errors="replace").rstrip("\x00 ")
        if dtype == "VRBL":
            count_type = raw_count.decode("ascii", errors="replace").strip("\x00 ")
            count = 1
        else:
            count_type = ""
            count = _u16(buf, e + 10)
        fields.append(
            FieldDef(
                usage=usage,
                description_type=dtype,
                element_type=etype,
                count=count,
                count_type=count_type,
                additional=addl,
            )
        )
    return fields


# ---------------------------------------------------------------------------
# Generic matching-data record decoding
# ---------------------------------------------------------------------------


class _BitReader:
    """Byte cursor that can also hand out nibbles, for the spec's "1/2"
    (``UH``) fields.  ``NXKD``/``NXFN`` are a nibble each and share one
    byte -- CONFIRMED: on every real street record that byte reads 0x51,
    i.e. NXKD=5 ("next-level matching data") and NXFN=1 ("detailed search
    information record serial number"), exactly the values Ch.11.A.2.4.1.5
    footnote 4 says a street-address record must carry."""

    def __init__(self, buf: bytes, off: int) -> None:
        self.buf = buf
        self.off = off
        self._nibble: Optional[int] = None

    def bytes(self, n: int) -> bytes:
        self._flush_nibble()
        b = self.buf[self.off : self.off + n]
        self.off += n
        return b

    def nibble(self) -> int:
        if self._nibble is None:
            byte = self.buf[self.off]
            self.off += 1
            self._nibble = byte & 0x0F
            return (byte >> 4) & 0x0F
        v = self._nibble
        self._nibble = None
        return v

    def _flush_nibble(self) -> None:
        self._nibble = None


def _read_scalar(r: _BitReader, type_: str, count: int):
    if type_ in ("UH", "HB"):
        # CORRECTED 2026-08-28 (SRHA decode-overrun fix, see
        # parse_matching_record's docstring): 'HB' ("Half Byte") is the
        # same nibble-packed type as 'UH', just spelled differently in the
        # archived spec's field tables (Ch.11.A.2.4.2.4 declares SRHA's
        # own NXKD/NXFN as 'HB', where the top-level street frame declares
        # the identical-purpose fields as 'UH' -- same "1/2" byte width in
        # both tables). Previously only 'UH' was special-cased here, so
        # 'HB' silently fell through to the generic 1-byte-per-element
        # branch below -- reading a whole byte per nibble field and
        # permanently shifting every subsequent field read in the record
        # by however many extra bytes that stole.
        vals = [r.nibble() for _ in range(count)]
        return vals[0] if count == 1 else vals
    if type_ == "BF":
        nbytes = (count + 7) // 8
        return r.bytes(nbytes)
    if type_ == "P6":
        out = []
        for _ in range(count):
            raw = r.bytes(6)
            out.append((geo_secs(raw[0:3]), geo_secs(raw[3:6])))
        return out[0] if count == 1 else out
    width = int(_TYPE_WIDTH.get(type_, 1.0))
    raw = r.bytes(width * count)
    if type_ in ("C", "SG"):
        return raw.decode("ascii", errors="replace")
    vals = [int.from_bytes(raw[i * width : (i + 1) * width], "big") for i in range(count)]
    return vals[0] if count == 1 else vals


def _read_variable(r: _BitReader, fd: FieldDef):
    n = _read_scalar(r, fd.count_type or "UB", 1)
    if fd.element_type == "CH":
        return r.bytes(n).decode("ascii", errors="replace")
    if fd.element_type == "BT" and fd.additional == "CMP6" and n == 6:
        # RLXY as declared on the SRHA ("City Selection") matching-data
        # frame (both SADSR*.IDX and POISR*.IDX): a VRBL field
        # (element 'BT', count type 'UH', additional 'CMP6' -- literally
        # "comprises a P6") rather than the fixed NORM/P6 field used by
        # street/address-range/POI records. Ch.11.A.2.4.2.4 note 6) says
        # this holds "the representative coordinates of the appropriate
        # area" -- i.e. it is semantically the same lat/lon P6 pair, just
        # encoded through the generic VRBL-of-raw-bytes machinery with a
        # length prefix that is always observed to be 6 (one geo_secs pair)
        # rather than a bare fixed-width field. Decoding it as
        # (lat, lon) via the same geo_secs() used everywhere else keeps
        # this consistent with AddressRange/Poi's RLXY representation
        # instead of leaving it as an opaque 6-int list.
        raw = r.bytes(6)
        return (geo_secs(raw[0:3]), geo_secs(raw[3:6]))
    return [_read_scalar(r, fd.element_type, 1) for _ in range(n)]


def parse_matching_record(buf: bytes, off: int, fields: Sequence[FieldDef]) -> dict:
    """Decode one Matching Data Record at ``off`` using its frame's field
    definitions.

    CONFIRMED rules:

    - The first two fields are always ``BFRL``/``NFRL``, 1 byte each,
      **SWS-halved** (real displacement = stored * 2).  ``NFRL == 0``
      marks the last record of the frame.
    - Every field up to and including ``STFG`` is unconditionally present.
    - ``STFG`` ("Stored Data Flag") is a presence bitmap over the fields
      that *follow* it, in definition order, LSB-first within each byte
      and byte 0 first.  This was derived empirically and then verified
      three independent ways: it reproduces the exact observed byte
      content of the SADSR alphabetical record (``STFG=7f 00`` -> the 7
      fields STID..NAME present, rest absent), the SADSR address-range
      record (``STFG=07`` -> ZIPN/PRFX/STAD present), and the POISR
      hybrid-search record (``STFG=fc 07`` -> RLXY..RPAT present, while a
      degenerate representative record's ``STFG=81 2f`` -> CTGY/KYCH/NAME/
      RPLV/RPAT/RPCN/RPST present).  Each of those parses ends exactly on
      the record boundary announced by ``NFRL``.
    - Any bytes left between the end of the last field and ``NFRL`` are
      the spec's trailing Padding Field.

    FIXED 2026-08-28 (SRHA "city name" decode-overrun bug, see
    docs/phases/02-roundtrip.md's dated entry for the full writeup): the
    root cause of SRHA's own City Selection Matching Data Records (1,285 in
    SADSR201.IDX, an analogous population in POISR201.IDX) overrunning
    their own record length was a single mis-typed field width, not a new
    unknown structure. SRHA's ``NXKD``/``NXFN`` fields are declared with
    element type ``'HB'`` (Ch.11.A.2.4.2.4's own spelling for the same
    nibble-packed "1/2 byte" field the top-level street frame calls
    ``'UH'``); ``_read_scalar`` only special-cased ``'UH'``, so ``'HB'``
    silently fell through to the generic 1-byte-per-element path -- reading
    a whole byte for what is really half a byte, and permanently shifting
    every subsequent field's read position in the record by the stolen
    byte. That shift corrupted the following ``NXST`` offset, the ``NAME``
    length prefix, and above all the ``RLXY`` field's own ``UH`` length
    prefix -- which is why ``NAME``/``RLXY`` appeared to "overrun into
    subsequent records' bytes" (the reader was, in effect, reading a
    respectably-sized city name's length byte from what was actually the
    *next* record's own data, several bytes further into the frame than it
    should have been). Fixed by treating ``'HB'`` as an alias of ``'UH'``
    in ``_read_scalar`` (see there) plus a matching fix in ``_read_variable``
    for RLXY's own VRBL-encoded P6 coordinate (also there). Proven: all
    1,285 real SRHA records in SADSR201.IDX now decode with ``_consumed``
    exactly equal to ``_nfrl`` (zero overrun) and round-trip byte-identical
    through ``index_writer.write_matching_record`` -- see
    `parser/roundtrip_idx_full.py`'s report and
    `parser/tests/test_roundtrip_idx_full.py`.
    """
    r = _BitReader(buf, off)
    out: dict = {}
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
        if fd.is_variable:
            out[fd.usage] = _read_variable(r, fd)
        else:
            out[fd.usage] = _read_scalar(r, fd.element_type, fd.count)
        if fd.usage == "STFG":
            raw = out["STFG"]
            stfg_bits = bytes(raw) if isinstance(raw, list) else bytes([raw])
            gated = True
    out["_offset"] = off
    out["_bfrl"] = (out.get("BFRL") or 0) * 2
    out["_nfrl"] = (out.get("NFRL") or 0) * 2
    out["_consumed"] = r.off - off
    return out


def iter_matching_records(
    buf: bytes,
    start: int,
    fields: Sequence[FieldDef],
    max_records: Optional[int] = None,
    end_offset: Optional[int] = None,
) -> Iterator[dict]:
    """Walk a Matching Data Frame from ``start``.

    Default (``end_offset=None``): walk the ``NFRL`` chain, stopping at
    ``NFRL == 0``. This is what every population exercised before
    2026-08-28 actually does (the top-level street frame, address-range
    frames, and POISR201.IDX's own top two flat-list frames): NFRL happens
    to equal each record's own physical byte length there, so chaining by
    NFRL reproduces the real physical sequence exactly, and ``NFRL == 0``
    does land on the frame's true last record.

    ADDED 2026-08-28 (see docs/phases/02-roundtrip.md's dated entry, and
    `roundtrip_idx_full._matching_frame_bytes`): when ``end_offset`` is
    given, walk PHYSICALLY instead -- advance by each record's own actual
    decoded length (``_consumed``) and stop once ``off >= end_offset``,
    ignoring ``NFRL``/``NFRL == 0`` for termination entirely. This is
    required for POISR201.IDX's deeper (``next_level``-nested)
    matching_data_frame populations: CONFIRMED by direct inspection that
    NFRL there is a search/alphabetical-chain pointer, not a
    physical-adjacency pointer -- it can be 0 (or a value that is off by a
    byte or two from the record's own decoded length, apparently
    record-end alignment padding) on a record that is NOT the frame's last
    physical record, with more genuinely different records' bytes sitting
    immediately after in the file. Using NFRL to decide when the frame
    ends silently truncated these populations far short of their declared
    ``matching_data_frame_size`` (proven: all 4 of POISR201.IDX's
    previously-"unverified verbatim" populations decode 100%
    byte-identical, record by record, when walked this way all the way to
    their declared frame size -- 108511, 7250, 204319, and 204319 records
    respectively, zero decode exceptions, zero byte mismatches)."""
    off = start
    n = 0
    if end_offset is not None:
        while off < end_offset and (max_records is None or n < max_records):
            rec = parse_matching_record(buf, off, fields)
            consumed = rec["_consumed"]
            if off + consumed > end_offset:
                # Record starts within the frame but its decoded content extends
                # past end_offset -- this is trailing-padding territory (bytes
                # beyond the true last record that look vaguely record-shaped but
                # are actually an adjacent structure's header or opaque padding).
                # Yielding it would read bytes from whatever follows the frame in
                # the containing buffer, producing layout-dependent values that
                # differ between the real file and a from-scratch reassembly even
                # though the frame's own bytes are byte-identical. Stop here.
                break
            yield rec
            n += 1
            off += consumed
        return
    while 0 <= off < len(buf) and (max_records is None or n < max_records):
        rec = parse_matching_record(buf, off, fields)
        yield rec
        n += 1
        if rec["_nfrl"] == 0:
            break
        off += rec["_nfrl"]


# ---------------------------------------------------------------------------
# Search frame management frame ('DFSR' + detailed search info records)
# ---------------------------------------------------------------------------


@dataclass
class FrameRef:
    """A resolved "***Frame Address" -- a pointer into the little
    ``[4B halved absolute file offset][2B size in words][filename]``
    additional-address table (Ch.11.A.2.1.2 note 7).

    **The 4-byte offset is stored halved**, like every other address on
    this disc.  Getting that wrong is what made three previous passes
    resolve every frame pointer to garbage; with the doubling applied,
    all five of SADSR201's frame addresses land exactly on their expected
    signatures (``DCTF`` definition frames, the category table, the
    alphabetical matching records, and a nested ``DFSR``/``SRT1``
    management frame whose representation name literally reads
    "ADDRESS RANGE")."""

    file_offset: int
    filename: str


@dataclass
class DetailedSearchInfo:
    """Ch.11.A.2.4.1.2 / 11.A.2.4.4.2 / 11.A.2.8.x -- all instances share
    one fixed 92-byte field table, only the declaration differs
    (``SRMX`` all-city street name, ``SRHA`` city selection, ``SRT1``
    address range, ...).  CONFIRMED byte-for-byte."""

    declaration: str
    record_base: int
    category_definition: Optional[FrameRef]
    category_data: Optional[FrameRef]
    category_data_size: int
    category_parent_record_size: int
    category_option_record_size: int
    first_level_category_size: int
    first_level_category_options: int
    matching_data_definition: Optional[FrameRef]
    matching_data_frame: Optional[FrameRef]
    matching_data_frame_size: int
    matching_record_max_size: int
    matching_record_count: int
    default_poi_serial: int
    next_level: Optional[FrameRef]
    next_level_size: int
    default_keyboard: str


def _resolve_frame_ref(buf: bytes, record_base: int, raw: int) -> Optional[FrameRef]:
    if raw == SENTINEL32:
        return None
    entry = record_base + sws32(raw)
    file_offset = _u32(buf, entry) * 2  # <-- halved, see FrameRef docstring
    name_len = _u16(buf, entry + 4) * 2
    name = buf[entry + 6 : entry + 6 + name_len].rstrip(b"\x00").decode("ascii", "replace")
    return FrameRef(file_offset=file_offset, filename=name)


def parse_detailed_search_info(buf: bytes, base: int) -> DetailedSearchInfo:
    return DetailedSearchInfo(
        declaration=buf[base : base + 4].decode("ascii", errors="replace"),
        record_base=base,
        category_definition=_resolve_frame_ref(buf, base, _u32(buf, base + 16)),
        category_data=_resolve_frame_ref(buf, base, _u32(buf, base + 24)),
        category_data_size=sws32(_u32(buf, base + 20)),
        category_parent_record_size=sws32(_u32(buf, base + 32)),
        category_option_record_size=sws32(_u32(buf, base + 36)),
        first_level_category_size=sws32(_u32(buf, base + 40)),
        first_level_category_options=_u32(buf, base + 44),
        matching_data_definition=_resolve_frame_ref(buf, base, _u32(buf, base + 60)),
        matching_data_frame=_resolve_frame_ref(buf, base, _u32(buf, base + 68)),
        matching_data_frame_size=sws32(_u32(buf, base + 64)),
        matching_record_max_size=sws32(_u32(buf, base + 72)),
        matching_record_count=_u32(buf, base + 76),
        default_poi_serial=_u32(buf, base + 80),
        next_level=_resolve_frame_ref(buf, base, _u32(buf, base + 88)),
        next_level_size=sws32(_u32(buf, base + 84)),
        default_keyboard=buf[base + 28 : base + 32].decode("ascii", errors="replace"),
    )


def parse_search_frame(buf: bytes, base: int = 0) -> List[DetailedSearchInfo]:
    """Parse a ``DFSR``-style Management Frame of Search Frame at ``base``
    and return its Detailed Search Information Records.

    CONFIRMED: header is ``[4B 'DFSR'][4B record count][4B SWS record
    size][4B D offset to first record]``.  SADSR201.IDX declares 2 records
    of 440 bytes at offset 16 (``SRMX`` street name search + ``SRHA`` city
    selection); the nested address-range frame declares 1 record of 376
    bytes (``SRT1``)."""
    decl = buf[base : base + 4].decode("ascii", errors="replace")
    if decl not in ("DFSR", "DFSA", "DFSM", "DFM2", "DSRC"):
        raise ValueError(f"unexpected search-frame declaration {decl!r} at {base}")
    count = _u32(buf, base + 4)
    rec_size = sws32(_u32(buf, base + 8))
    first = base + sws32(_u32(buf, base + 12))
    return [parse_detailed_search_info(buf, first + i * rec_size) for i in range(count)]


# ---------------------------------------------------------------------------
# High-level: street address search
# ---------------------------------------------------------------------------


@dataclass
class AddressRange:
    """One Address Range Search Matching Data Record (Ch.11.A.2.4.4.5), as
    this disc actually stores it.

    Note the disc's Matching Data Definition Frame for this frame declares
    ``RLXY`` (P6 coordinate) and ``LKID`` (main-map Link ID) *inline*,
    where the spec's worked example instead used ``POIO``/``POIC``
    pointers into a separate Street Address POI Information frame.  That
    is a legal variation -- the definition frame is authoritative -- and
    it is good news: the coordinate is one indirection closer than the
    spec example implied."""

    file_offset: int
    lat: float
    lon: float
    link_id: int
    #: ``STAD`` house numbers at the two ends of the link, in link
    #: direction -- so ``house_start`` is frequently *greater* than
    #: ``house_end``.  ``None`` where the disc stores the 0xFFFFFFFF null
    #: (always the case on ``is_center_link`` records).
    house_start: Optional[int]
    house_end: Optional[int]
    area_codes: List[int]
    street_address_flag: int
    zip_code: str
    prefix: str
    raw: dict

    @property
    def is_center_link(self) -> bool:
        """bit 7 of ``FGSA``: this record is the street's map-display
        centre link rather than a real house-number range (its ``STAD``
        values are the 0xFFFFFFFF null)."""
        return bool(self.street_address_flag & 0x80)


@dataclass
class Street:
    """One Street Name Search (alphabetical order) Matching Data Record."""

    file_offset: int
    name: str
    street_id: int
    next_level_offset: int  # already doubled: byte offset into the AR frame
    next_level_count: int
    next_level_class: int
    next_level_serial: int
    fuzzy_flag: int
    raw: dict


class StreetAddressIndex:
    """Street Address Search index (``IDX/SADSR2xx.IDX``, Ch.11.A.2.4).

    Usage::

        idx = StreetAddressIndex("/mnt/disc/IDX/SADSR201.IDX")
        for street in idx.find("GINGIN ROAD"):
            for rng in idx.address_ranges(street):
                print(rng.lat, rng.lon, rng.house_start, rng.house_end)

    Everything is read into memory once (SADSR201.IDX is ~15 MB).
    """

    def __init__(self, path: str) -> None:
        self.path = path
        with open(path, "rb") as fh:
            self.buf = fh.read()
        self.records = parse_search_frame(self.buf, 0)
        self.street_info = next(r for r in self.records if r.declaration == "SRMX")
        self.street_fields = parse_definition_frame(
            self.buf, self.street_info.matching_data_definition.file_offset
        )
        # The street records' "next-level data frame" is a *nested* search
        # frame (DFSR + 'SRT1' Address Range Search); its own matching
        # data frame is what NXST offsets are relative to.
        self.range_frame = parse_search_frame(self.buf, self.street_info.next_level.file_offset)[0]
        self.range_fields = parse_definition_frame(
            self.buf, self.range_frame.matching_data_definition.file_offset
        )
        self.street_base = self.street_info.matching_data_frame.file_offset
        self.range_base = self.range_frame.matching_data_frame.file_offset

    # -- streets -----------------------------------------------------------

    def iter_streets(self, max_records: Optional[int] = None) -> Iterator[Street]:
        for rec in iter_matching_records(
            self.buf, self.street_base, self.street_fields, max_records
        ):
            nxkd = rec.get("NXKD", 0)
            yield Street(
                file_offset=rec["_offset"],
                name=rec.get("KYCH", ""),
                street_id=rec.get("STID", 0),
                next_level_offset=sws32(rec.get("NXST", 0)),
                next_level_count=rec.get("NXCT", 0),
                next_level_class=nxkd if isinstance(nxkd, int) else 0,
                next_level_serial=rec.get("NXFN", 0),
                fuzzy_flag=rec.get("FGFZ", 0),
                raw=rec,
            )

    def find(self, name: str) -> List[Street]:
        """Exact (case-sensitive) search-key match.  Records are stored in
        alphabetical order, so this is a linear scan that stops as soon as
        it walks past the target -- fast enough (~0.2 s worst case on the
        38,120-record SADSR201.IDX) and avoids assuming anything about the
        category jump table."""
        out: List[Street] = []
        for s in self.iter_streets():
            if s.name == name:
                out.append(s)
            elif out:
                break
            elif s.name > name:
                break
        return out

    # -- address ranges ----------------------------------------------------

    def address_ranges(self, street: Street) -> List[AddressRange]:
        base = self.range_base + street.next_level_offset
        out: List[AddressRange] = []
        for rec in iter_matching_records(
            self.buf, base, self.range_fields, street.next_level_count
        ):
            out.append(self._to_range(rec))
        return out

    @staticmethod
    def _to_range(rec: dict) -> AddressRange:
        lat, lon = rec.get("RLXY", (0.0, 0.0))
        stad = rec.get("STAD")
        if isinstance(stad, list) and len(stad) == 2:
            hf, ht = stad
        else:
            hf = ht = None
        if hf == SENTINEL32:
            hf = None
        if ht == SENTINEL32:
            ht = None
        arcd = rec.get("ARCD", [])
        return AddressRange(
            file_offset=rec["_offset"],
            lat=lat,
            lon=lon,
            link_id=rec.get("LKID", 0),
            house_start=hf,
            house_end=ht,
            area_codes=arcd if isinstance(arcd, list) else [arcd],
            street_address_flag=rec.get("FGSA", 0),
            zip_code=rec.get("ZIPN", ""),
            prefix=rec.get("PRFX", ""),
            raw=rec,
        )

    def lookup(self, name: str) -> List[AddressRange]:
        """Convenience: street name -> every address range on that street."""
        out: List[AddressRange] = []
        for s in self.find(name):
            out.extend(self.address_ranges(s))
        return out


# ---------------------------------------------------------------------------
# High-level: POI search
# ---------------------------------------------------------------------------


@dataclass
class Poi:
    """One POI Search (hybrid search) Matching Data Record, Ch.11.A.2.8.

    ``lat``/``lon`` come from the same ``RLXY`` P6 field as street address
    ranges.  CONFIRMED against real data: the record whose ``NAME`` reads
    ``POLE A A\\48 FARRINGTON ROAD, PERTH, WESTERN AUSTRALIA`` decodes to
    (-32.0619, 115.8404), which is Farrington Road, Leeming/Murdoch WA.

    Records with no ``RLXY`` are *degenerate representative* records (the
    grouping rows the head unit shows when many POIs share a name); their
    ``RPCN``/``RPST`` fields point at the constituent records instead."""

    file_offset: int
    search_key: str
    name: str
    lat: Optional[float]
    lon: Optional[float]
    category: Optional[int]
    area_codes: List[int]
    raw: dict

    @property
    def is_degenerate(self) -> bool:
        return self.lat is None


class PoiSearchIndex:
    """POI Search index (``IDX/POISR2xx.IDX``, Ch.11.A.2.8).  Same generic
    machinery as ``StreetAddressIndex`` -- which is the point: the
    definition frame drives everything, so no per-file byte offsets."""

    def __init__(self, path: str, info_index: int = 0) -> None:
        self.path = path
        with open(path, "rb") as fh:
            self.buf = fh.read()
        self.records = parse_search_frame(self.buf, 0)
        self.info = self.records[info_index]
        self.fields = parse_definition_frame(
            self.buf, self.info.matching_data_definition.file_offset
        )
        self.base = self.info.matching_data_frame.file_offset

    def iter_pois(self, max_records: Optional[int] = None) -> Iterator[Poi]:
        for rec in iter_matching_records(self.buf, self.base, self.fields, max_records):
            rlxy = rec.get("RLXY")
            arcd = rec.get("ARCD", [])
            yield Poi(
                file_offset=rec["_offset"],
                search_key=rec.get("KYCH", ""),
                name=rec.get("NAME", ""),
                lat=rlxy[0] if rlxy else None,
                lon=rlxy[1] if rlxy else None,
                category=rec.get("CTGY"),
                area_codes=arcd if isinstance(arcd, list) else [arcd],
                raw=rec,
            )

    def find(self, needle: str, limit: int = 20) -> List[Poi]:
        """Substring match over the POI name (the disc stores POI names as
        ``<facility name>\\<street address>``, so this matches either)."""
        out: List[Poi] = []
        for poi in self.iter_pois():
            if needle in poi.name or needle in poi.search_key:
                out.append(poi)
                if len(out) >= limit:
                    break
        return out
