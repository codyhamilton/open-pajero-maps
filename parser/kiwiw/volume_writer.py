"""Phase 2 writer for `ALLDATA.KWI`'s top structural layer: the Ch. 5 All
Data Management Frame (Data Volume + Management Header Table) and the
Ch. 6 Parcel-related Data Management Record (PDMDH + LMR + BSMR + BMT
tables).

This is the exact inverse of the read side in `kiwiw/volume.py`. Scope is
deliberately limited to that container/mesh layer -- nothing here touches
parcel content (roads, background, names), which is a separate and much
harder problem (see docs/phases/02-roundtrip.md).

Two conventions, both learned from the `COUNTRY.KWI` round-trip:

- Every byte is written explicitly. Buffers start filled with a poison
  byte (`POISON`) rather than zeros, so any region the model forgets shows
  up as a diff instead of silently matching a zero-filled original.
- Regions that are genuinely not understood (the spec's RESERVED areas,
  the maker-defined halves of the MID:C fields, anything past the modelled
  LMR fields) are carried through the IR verbatim as hex and written back
  unchanged, never regenerated from a partial interpretation.
"""
from __future__ import annotations

from .bitutils import geo_secs_bytes, unsws
from .model import BlockSetMgmtRecord, LevelMgmtRecord, VolumeHeader
from .volume import (
    BSMR_SIZE,
    DATAVOL_SIZE,
    LMR_BASE_SIZE,
    MHR_SIZE,
    MHT_RECORD_COUNT,
    MHT_SIZE,
    ManagementHeaderTable,
    Mid,
    Pdmdh,
    VolumeHeaderExtras,
)

POISON = 0xA5


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"{v} does not fit in a u16")
    return bytes((v >> 8, v & 0xFF))


def _u32(v: int) -> bytes:
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"{v} does not fit in a u32")
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _i8(v: int) -> bytes:
    if not -128 <= v <= 127:
        raise ValueError(f"{v} does not fit in an i8")
    return bytes((v & 0xFF,))


def _text(s: str, size: int) -> bytes:
    """Fixed-width latin-1 text field, zero-padded (Ch. 5.1: 'the remaining
    blanks are padded with 0(16)')."""
    raw = s.encode("latin-1")
    if len(raw) > size:
        raise ValueError(f"text {s!r} is {len(raw)} bytes, field is {size}")
    return raw + b"\x00" * (size - len(raw))


def _hexfield(hexstr: str, size: int, what: str) -> bytes:
    raw = bytes.fromhex(hexstr)
    if len(raw) != size:
        raise ValueError(f"{what}: expected {size} verbatim bytes, got {len(raw)}")
    return raw


def _put(buf: bytearray, off: int, data: bytes) -> None:
    buf[off : off + len(data)] = data


def write_mid(mid: Mid) -> bytes:
    """Inverse of `volume._parse_mid` -- 12-byte Maker Identification."""
    return (
        geo_secs_bytes(mid.lat)
        + bytes((mid.lat_exponent,))
        + geo_secs_bytes(mid.lon)
        + bytes((mid.lon_exponent,))
        + _i8(mid.floor)
        + bytes((mid.reserved,))
        + _u16(mid.date)
    )


def write_volume_header(hdr: VolumeHeader, extras: VolumeHeaderExtras) -> bytes:
    """Re-emit the 2048-byte Ch. 5.1 Data Volume from
    `parse_volume_header()` + `parse_volume_header_extras()`."""
    buf = bytearray([POISON]) * DATAVOL_SIZE

    # 1-3: MID:C system-specific / data-author / system identification.
    for i, (mid_off, c_off, c_len) in enumerate(
        ((0, 12, 52), (64, 76, 52), (128, 140, 20))
    ):
        _put(buf, mid_off, write_mid(extras.mids[i]))
        _put(buf, c_off, _hexfield(extras.maker_defined_hex[i], c_len,
                                   f"maker-defined field {i}"))

    # 4-6, 8: fixed-width text fields.
    _put(buf, 160, _text(hdr.format_version, 64))
    _put(buf, 224, _text(hdr.data_version, 64))
    _put(buf, 288, _text(hdr.disk_title, 128))
    _put(buf, 424, _text(hdr.media_version, 32))

    # 7: Data Contents (4 words; only word 0 bits 15..13 are defined).
    word0 = extras.contents_word0_low
    if hdr.contents_main_map:
        word0 |= 1 << 15
    if hdr.contents_route_planning:
        word0 |= 1 << 14
    if hdr.contents_index_data:
        word0 |= 1 << 13
    _put(buf, 416, _u16(word0))
    for i, w in enumerate(extras.contents_words_1_3):
        _put(buf, 418 + 2 * i, _u16(w))

    # 9: Data Coverage -- two PIDs (lat, exponent, lon, exponent).
    cov = hdr.coverage
    exps = extras.coverage_exponents
    _put(buf, 456, geo_secs_bytes(cov.lat_lo) + bytes((exps[0],))
                    + geo_secs_bytes(cov.lon_lo) + bytes((exps[1],)))
    _put(buf, 464, geo_secs_bytes(cov.lat_hi) + bytes((exps[2],))
                    + geo_secs_bytes(cov.lon_hi) + bytes((exps[3],)))

    # 10-12: sector sizes and background default info.
    _put(buf, 472, _u16(hdr.logical_sector_size))
    _put(buf, 474, _u16(hdr.sector_size))
    background = extras.background_low
    if hdr.background_in_map_is_sea:
        background |= 1 << 15
    if hdr.background_out_of_map_is_sea:
        background |= 1 << 14
    _put(buf, 476, _u16(background))

    # 13-15: RESERVED / Level Management Information, carried verbatim.
    _put(buf, 478, _hexfield(extras.reserved_478_hex, 14, "RESERVED@478"))
    _put(buf, 492, _hexfield(extras.level_mgmt_info_hex, 256, "level mgmt info"))
    _put(buf, 748, _hexfield(extras.reserved_748_hex, 1300, "RESERVED@748"))

    return bytes(buf)


def write_mhr_entry(dsa: int, size: int, name: str) -> bytes:
    """One 18-byte Ch. 5.2 Management Header Record."""
    return _u32(dsa) + _u16(size) + _text(name, 12)


def write_management_header_table(table: ManagementHeaderTable) -> bytes:
    """Re-emit one 2048-byte Ch. 5.2 Management Header Table."""
    if len(table.entries) != MHT_RECORD_COUNT:
        raise ValueError(
            f"expected {MHT_RECORD_COUNT} management header records, "
            f"got {len(table.entries)}"
        )
    buf = bytearray([POISON]) * MHT_SIZE
    for i, e in enumerate(table.entries):
        _put(buf, i * MHR_SIZE, write_mhr_entry(e.dsa, e.size, e.name))
    _put(buf, MHT_RECORD_COUNT * MHR_SIZE,
         _hexfield(table.tail_hex, MHT_SIZE - MHT_RECORD_COUNT * MHR_SIZE,
                   "management header table tail"))
    return bytes(buf)


def write_lmr(lmr: LevelMgmtRecord, lmr_size: int) -> bytes:
    """One Ch. 6.1.1 Level Management Record (`lmr_size` bytes)."""
    header = (lmr.level << 10) | (lmr.upper_level << 4) | lmr.lower_level
    numbers = (
        (lmr.n_basic_map << 12)
        | (lmr.n_ext_map << 8)
        | (lmr.n_basic_route << 4)
        | lmr.n_ext_route
    )
    out = bytearray()
    out += _u16(header)
    out += _u16(numbers)
    if len(lmr.display_flags) != 5:
        raise ValueError("expected 5 display-flag words")
    for f in lmr.display_flags:
        out += _u32(f)
    out += bytes((lmr.n_blocksets_lat, lmr.n_blocksets_lng,
                  lmr.n_blocks_lat, lmr.n_blocks_lng))
    for i in range(4):
        out += bytes((lmr.n_parcels_lat[i], lmr.n_parcels_lng[i]))
    out += _u16(unsws(lmr.bsmr_offset))
    out += _u16(unsws(lmr.node_record_size))
    assert len(out) == LMR_BASE_SIZE, len(out)

    if lmr.n_road_frames is not None:
        out += _u16(
            ((lmr.n_road_frames - 1) << 10)
            | ((lmr.n_background_frames - 1) << 5)
            | (lmr.n_name_frames - 1)
        )
        for table, count, what in (
            (lmr.road_frame_table, lmr.n_road_frames, "road"),
            (lmr.background_frame_table, lmr.n_background_frames, "background"),
            (lmr.name_frame_table, lmr.n_name_frames, "name"),
        ):
            if table and len(table) != count:
                raise ValueError(
                    f"level {lmr.level}: {what} frame table has {len(table)} "
                    f"entries, header declares {count}")
            for v in table:
                out += _u16(v)
    out += bytes.fromhex(lmr.raw_tail_hex)

    if len(out) != lmr_size:
        raise ValueError(
            f"level {lmr.level}: rebuilt LMR is {len(out)} bytes, "
            f"the PDMDH declares {lmr_size}")
    return bytes(out)


def write_bsmr(bs: BlockSetMgmtRecord) -> bytes:
    """One Ch. 6.1.2 Block Set Management Record (10 bytes)."""
    header = (bs.level << 10) | bs.blockset_index
    out = _u16(header) + _u32(unsws(bs.bmt_offset)) + _u32(unsws(bs.bmt_size))
    assert len(out) == BSMR_SIZE
    return out


def write_pdmdh(pdmdh: Pdmdh) -> bytes:
    """Re-emit the whole Parcel-related Data Management Record blob (the
    PDMDH header, the LMR table, the BSMR table, every Block Management
    Table and the trailing sector padding) from `parse_pdmdh_full()`.

    Records are placed at exactly the offsets the parsed structure itself
    declares (LMRs after the 30-byte header, BSMRs at `bsmr_table_offset`,
    each BMT at its own block set's `bmt_offset`), so a byte-identical
    result also proves those offsets are self-consistent.
    """
    if pdmdh.bmt_tables is None:
        raise ValueError("write_pdmdh() needs parse_pdmdh_full() output "
                         "(bmt_tables is unset)")
    buf = bytearray([POISON]) * pdmdh.total_size

    _put(buf, 0, _u16(unsws(pdmdh.record_size)))
    _put(buf, 2, _hexfield(pdmdh.header_gap_hex, 6, "PDMDH bytes 2..8"))
    cov = pdmdh.coverage
    _put(buf, 8, geo_secs_bytes(cov.lat_hi) + geo_secs_bytes(cov.lat_lo)
                  + geo_secs_bytes(cov.lon_lo) + geo_secs_bytes(cov.lon_hi))
    _put(buf, 20, _u16(unsws(pdmdh.lmr_size)))
    _put(buf, 22, _u16(pdmdh.bsmr_size))
    _put(buf, 24, _u16(pdmdh.bmr_size))
    _put(buf, 26, _u16(pdmdh.n_lmr))
    _put(buf, 28, _u16(pdmdh.n_bsmr))

    off = 30
    if len(pdmdh.levels) != pdmdh.n_lmr:
        raise ValueError("LMR count does not match the PDMDH header")
    for lmr in pdmdh.levels:
        _put(buf, off, write_lmr(lmr, pdmdh.lmr_size))
        off += pdmdh.lmr_size

    if off != pdmdh.bsmr_table_offset:
        raise ValueError(
            f"LMR table ends at {off} but the BSMR table is at "
            f"{pdmdh.bsmr_table_offset}")
    if len(pdmdh.blocksets) != pdmdh.n_bsmr:
        raise ValueError("BSMR count does not match the PDMDH header")
    for i, bs in enumerate(pdmdh.blocksets):
        _put(buf, pdmdh.bsmr_table_offset + i * BSMR_SIZE, write_bsmr(bs))

    entry_size = pdmdh.bmr_size * 2
    for table in pdmdh.bmt_tables:
        for i, e in enumerate(table.entries):
            _put(buf, table.offset + i * entry_size, _u32(e.dsa) + _u16(e.size))

    _put(buf, pdmdh.record_size,
         _hexfield(pdmdh.trailing_padding_hex,
                   pdmdh.total_size - pdmdh.record_size, "PDMDH padding"))
    return bytes(buf)
