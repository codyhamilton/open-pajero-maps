"""Phase 2 writer for `ALLDATA.KWI` parcel content: the Ch. 7 Map Frame
(header + region list + Main Map Data Frame Entry table) and its road/
background/name sub-frames, plus the Ch. 6 Parcel Management Record that
a Block Management Table entry addresses.

Exact inverse of the read side in `kiwiw/parcel.py` / `kiwiw/road.py` /
`kiwiw/background.py` / `kiwiw/name.py` / `kiwiw/parcel_mgmt.py`. Follows
the same two conventions as `volume_writer.py` (itself following the
`COUNTRY.KWI` round-trip lesson):

- Every buffer starts filled with a poison byte (`POISON`), not zeros, so
  a region the model forgets shows up as a diff instead of silently
  matching a zero-filled original.
- Content this pass doesn't have an established semantic decode for
  (the Map Frame Header's undecoded fields, the multilink
  additional/altitude/passage-regulation info, background's optional
  name/auxdata trailer, the name-record header word) is carried through
  the IR as raw bytes (see each dataclass's docstring in `model.py`) and
  written back verbatim here -- never regenerated from a partial
  interpretation.
"""
from __future__ import annotations

from .bitutils import sws
from .model import (
    BackgroundFrame,
    BoundingBox,
    MapFrame,
    NameFrame,
    ParcelMgmtRecord,
    RoadFrame,
)
from .parcel import MAPFRAME_HEADER_SIZE

POISON = 0xA5


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"{v} does not fit in a u16")
    return bytes((v >> 8, v & 0xFF))


def _u32(v: int) -> bytes:
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"{v} does not fit in a u32")
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _put(buf: bytearray, off: int, data: bytes) -> None:
    end = off + len(data)
    if end > len(buf):
        raise ValueError(f"write of {len(data)} bytes at {off} overruns "
                          f"buffer of size {len(buf)}")
    buf[off:end] = data


def write_road_frame(
    frame: RoadFrame,
    bounds: BoundingBox | None = None,
    encode: bool = False,
) -> bytes:
    """Inverse of `road.decode_road_frame()`. Table words are rebuilt from
    their raw captured form (exact by construction); each multilink record
    is placed at its original `raw_offset`.

    Two modes, selected by the `encode` flag:

    * ``encode=False`` (default, **replicate mode**): re-emits each
      RoadLink verbatim from ``RoadLink.raw_bytes``.  The output is
      byte-identical to the original disc data.  Existing callers --
      including the round-trip regression tests -- use this mode and
      pass no ``bounds`` argument.

    * ``encode=True`` (**encode mode**): re-serialises each RoadLink from
      its decoded semantic fields via ``road_writer.encode_road_link()``.
      The output is functionally equivalent (decodes to the same fields)
      but not necessarily byte-identical (the coordinate raw words use a
      normalised encoding that may differ from the original).
      ``bounds`` must be supplied in this mode.
    """
    if frame.frame_size <= 0:
        raise ValueError("RoadFrame.frame_size is unset -- cannot size the output buffer")
    if encode and bounds is None:
        raise ValueError("bounds must be provided when encode=True")

    buf = bytearray([POISON]) * frame.frame_size

    _put(buf, 0, _u16(frame.header_size_raw))
    _put(buf, 2, _u16(frame.n_intersections))
    buf[4] = frame.n_display_classes
    buf[5] = frame.n_additional_data
    _put(buf, 6, _u16(frame.lvl_field_raw))

    if len(frame.display_class_table) != frame.n_display_classes:
        raise ValueError(
            f"road frame: n_display_classes={frame.n_display_classes} but "
            f"display_class_table has {len(frame.display_class_table)} entries")
    off = 8
    for idx, (raw_offset_word, raw_count_word) in enumerate(frame.display_class_table):
        _put(buf, off, _u16(raw_offset_word))
        _put(buf, off + 2, _u16(raw_count_word))
        off += 4
        flag = frame.display_class_flags.get(idx)
        if flag is not None:
            _put(buf, sws(raw_offset_word), flag)

    if len(frame.additional_data_table) != frame.n_additional_data:
        raise ValueError(
            f"road frame: n_additional_data={frame.n_additional_data} but "
            f"additional_data_table has {len(frame.additional_data_table)} entries")
    for idx, (raw_offset_word, raw_size_word) in enumerate(frame.additional_data_table):
        _put(buf, off, _u16(raw_offset_word))
        _put(buf, off + 2, _u16(raw_size_word))
        off += 4
        content = frame.additional_data_raw.get(idx)
        if content is not None:
            _put(buf, sws(raw_offset_word), content)

    if encode:
        from .road_writer import encode_road_link
        for link in frame.links:
            _put(buf, link.raw_offset, encode_road_link(link, bounds))
    else:
        for link in frame.links:
            if not link.raw_bytes:
                raise ValueError("RoadLink has no raw_bytes captured -- cannot round-trip")
            _put(buf, link.raw_offset, link.raw_bytes)

    return bytes(buf)


def write_background_frame(
    frame: BackgroundFrame,
    bounds: BoundingBox | None = None,
    encode: bool = False,
) -> bytes:
    """Inverse of `background.decode_background_frame()`. Element/type-unit
    table words are rebuilt from their raw captured form; each Minimum
    Graphics Data Record is placed at its original `raw_offset`.

    Two modes, selected by the `encode` flag:

    * ``encode=False`` (default, **replicate mode**): re-emits each
      BackgroundShape verbatim from ``BackgroundShape.raw_bytes``.  The
      output is byte-identical to the original disc data.  Existing
      callers pass no ``bounds`` argument and use this mode.

    * ``encode=True`` (**encode mode**): re-serialises each BackgroundShape
      from its decoded semantic fields via
      ``background_writer.encode_background_shape()``.  The output is
      functionally equivalent (decodes to the same fields) but may not be
      byte-identical when the disc used a non-canonical coordinate encoding.
      ``bounds`` must be supplied in this mode.
    """
    if frame.frame_size <= 0:
        raise ValueError("BackgroundFrame.frame_size is unset -- cannot size the output buffer")
    if encode and bounds is None:
        raise ValueError("bounds must be provided when encode=True")
    buf = bytearray([POISON]) * frame.frame_size

    _put(buf, 0, _u16(frame.header_size_raw))

    off = 2
    for elem in frame.elements:
        _put(buf, off, _u16(elem.raw_offset_word))
        _put(buf, off + 2, _u16(elem.raw_size_word))
        off += 4
        if elem.raw_offset_word == 0xFFFF:
            continue
        poff = sws(elem.raw_offset_word)
        _put(buf, poff, _u16(elem.n_raw))
        p = poff + 2
        for boff_word, val_word in elem.unit_table_raw:
            _put(buf, p, _u16(boff_word))
            _put(buf, p + 2, _u16(val_word))
            p += 4

    if encode:
        from .background_writer import encode_background_shape
        for shape in frame.shapes:
            _put(buf, shape.raw_offset, encode_background_shape(shape, bounds))
    else:
        for shape in frame.shapes:
            if not shape.raw_bytes:
                raise ValueError("BackgroundShape has no raw_bytes captured -- cannot round-trip")
            _put(buf, shape.raw_offset, shape.raw_bytes)

    return bytes(buf)


def write_name_frame(frame: NameFrame, encode: bool = False) -> bytes:
    """Inverse of `name.decode_name_frame()`. Name-list table words are
    rebuilt from their raw captured form; each Name Data Record is placed
    at its original `raw_offset`.

    Two modes, selected by the `encode` flag:

    * ``encode=False`` (default, **replicate mode**): re-emits each
      NameRecord verbatim from ``NameRecord.raw_bytes``.  The output is
      byte-identical to the original disc data.

    * ``encode=True`` (**encode mode**): re-serialises each NameRecord from
      its decoded semantic fields via
      ``name_writer.encode_name_record()``.  For ``string_type == 4``
      (Linear-B, the only fully-decoded type) this patches attr1/attr2
      from the decoded fields; for all other types it falls back to
      raw_bytes verbatim.  The output is functionally equivalent (decodes
      to the same fields).

    Raises if any decoded record has no ``raw_bytes`` (which name.py
    captures via the `na`-derived length for every record type, even
    unhandled ones -- so this should never trigger on well-formed disc
    data).
    """
    if frame.frame_size <= 0:
        raise ValueError("NameFrame.frame_size is unset -- cannot size the output buffer")
    buf = bytearray([POISON]) * frame.frame_size

    _put(buf, 0, _u16(frame.header_size_raw))

    off = 2
    for lst in frame.lists:
        _put(buf, off, _u16(lst.raw_offset_word))
        _put(buf, off + 2, _u16(lst.raw_count_word))
        off += 4

    if encode:
        from .name_writer import encode_name_record
        for rec in frame.records:
            if not rec.raw_bytes:
                raise ValueError(
                    f"NameRecord with string_type={rec.string_type} has no raw_bytes "
                    "-- cannot encode")
            _put(buf, rec.raw_offset, encode_name_record(rec))
    else:
        for rec in frame.records:
            if not rec.raw_bytes:
                raise ValueError(
                    f"NameRecord with string_type={rec.string_type} has no raw_bytes "
                    "-- name.py cannot determine the length of an unhandled string "
                    "type, so this name frame cannot be round-tripped byte-identically "
                    "(see docs/phases/02-roundtrip.md)")
            _put(buf, rec.raw_offset, rec.raw_bytes)

    return bytes(buf)


def write_map_frame_header(header) -> bytes:
    """Inverse of `parcel.decode_map_frame_header()`: the 36-byte header
    is carried verbatim in `MapFrameHeader.raw_bytes` (see that
    dataclass's docstring for why -- most of its fields have no
    established semantic decode in this codebase), so this is simply
    that blob, length-checked."""
    if len(header.raw_bytes) != MAPFRAME_HEADER_SIZE:
        raise ValueError(
            f"MapFrameHeader.raw_bytes is {len(header.raw_bytes)} bytes, "
            f"expected {MAPFRAME_HEADER_SIZE}")
    return bytes(header.raw_bytes)


def write_map_frame(
    frame: MapFrame,
    road_bytes: bytes | None,
    background_bytes: bytes | None,
    name_bytes: bytes | None,
) -> bytes:
    """Inverse of `parcel.decode_parcel()`'s Map Frame structure: header +
    region list + mfde table, with the road/background/name sub-frame
    bytes (already re-serialized by `write_road_frame()` /
    `write_background_frame()` / `write_name_frame()`) placed at the
    offsets the mfde table itself declares.

    `road_bytes`/`background_bytes`/`name_bytes` are the exact bytes to
    place at mfde slots 0/1/2 -- pass `None` for a slot whose entry has
    size 0 (no sub-frame present)."""
    if frame.frame_size <= 0:
        raise ValueError("MapFrame.frame_size is unset -- cannot size the output buffer")
    buf = bytearray([POISON]) * frame.frame_size

    _put(buf, 0, write_map_frame_header(frame.header))

    region_off = MAPFRAME_HEADER_SIZE
    _put(buf, region_off, frame.region_list_raw)

    de_off = region_off + len(frame.region_list_raw)
    if len(frame.region_list_raw) != frame.header.nregion * 4:
        raise ValueError(
            f"region_list_raw is {len(frame.region_list_raw)} bytes, "
            f"nregion={frame.header.nregion} implies {frame.header.nregion * 4}")

    for i, (raw_off, raw_size) in enumerate(frame.mfde_raw):
        eoff = de_off + i * 6
        _put(buf, eoff, _u32(raw_off))
        _put(buf, eoff + 4, _u16(raw_size))

    slots = ((0, road_bytes), (1, background_bytes), (2, name_bytes))
    for idx, content in slots:
        if idx >= len(frame.mfde_raw):
            if content is not None:
                raise ValueError(f"mfde slot {idx} has no table entry but content was given")
            continue
        raw_off, raw_size = frame.mfde_raw[idx]
        if raw_size == 0 or raw_off == 0xFFFFFFFF:
            if content is not None:
                raise ValueError(f"mfde slot {idx} declares no sub-frame but content was given")
            continue
        if content is None:
            raise ValueError(f"mfde slot {idx} declares a sub-frame but no content was given")
        sub_off = sws(raw_off)
        sub_size = sws(raw_size)
        if len(content) != sub_size:
            raise ValueError(
                f"mfde slot {idx}: declared size {sub_size}, content is {len(content)} bytes")
        _put(buf, sub_off, content)

    # Extended-index slots (index 3..) -- content this layer doesn't
    # decode, written back verbatim from what decode_parcel() captured
    # for entries whose offset lies inside this buffer. Entries whose
    # offset is far outside this buffer (observed to look like absolute
    # disc sector addresses -- content belonging to a different layer
    # entirely, e.g. route guidance) are left as table-entry-only: there
    # is nothing of theirs in *this* buffer to write.
    for idx in range(3, len(frame.mfde_raw)):
        raw_off, raw_size = frame.mfde_raw[idx]
        if raw_size == 0 or raw_off == 0xFFFFFFFF:
            continue
        sub_off = sws(raw_off)
        sub_size = sws(raw_size)
        if sub_off >= len(buf):
            continue  # external content -- out of scope for this buffer
        content = frame.ext_frame_raw.get(idx)
        if content is None:
            raise ValueError(
                f"mfde slot {idx} declares an in-buffer extended data frame but no "
                "raw content was captured for it")
        if len(content) != sub_size:
            raise ValueError(
                f"mfde slot {idx}: declared size {sub_size}, content is {len(content)} bytes")
        _put(buf, sub_off, content)

    if frame.tail_raw:
        _put(buf, len(buf) - len(frame.tail_raw), frame.tail_raw)

    return bytes(buf)


def write_parcel_mgmt_record(rec: ParcelMgmtRecord, buf: bytearray) -> None:
    """Inverse of `parcel_mgmt.parse_parcel_mgmt_record()`. Writes `rec`
    (and, recursively, every subrecord it references) into `buf` in
    place, at the exact offsets the parse captured -- `buf` must already
    be allocated to the owning block's full size (poison-filled by the
    caller) before this is invoked.

    Also writes `rec.tail_raw` (non-empty only on the root record --
    see its docstring) verbatim at the end of `buf`, reproducing the
    real trailing bytes a Block's declared size leaves beyond the
    record structure addressed within it."""
    p_type_raw = (rec.parcel_type << 8) | rec.list_type
    _put(buf, rec.offset, _u16(p_type_raw))
    _put(buf, rec.offset + 2, rec.header_gap_raw)
    mapinfo_off = rec.offset + 4
    for idx, entry in enumerate(rec.entries):
        eoff = mapinfo_off + idx * 6
        _put(buf, eoff, _u32(entry.dsa) + _u16(entry.size))
        if entry.subrecord is not None:
            write_parcel_mgmt_record(entry.subrecord, buf)
    if rec.tail_raw:
        _put(buf, len(buf) - len(rec.tail_raw), rec.tail_raw)
