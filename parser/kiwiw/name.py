"""7.4 Name Data Frame decoder. Ported from `dumpname()` in kiwiread.c.

Five "String Type" variants are defined by the spec (7.4.2.1.x); kiwiread.c
only decodes the *content* of types 1 (Barycentric), 4 (Linear-B), 5
(Linear-C), and 6 (Symbol+String) -- it `exit()`s on any other type because
*it* has no other way to know how many bytes to skip.

This port doesn't need that escape hatch: the Name Attribute Header's `na`
word (7.4.2.1.1, bits 0:11, [SWS]-encoded) gives the record's total byte
length directly, independent of `string_type`. Round-tripping was
previously observed to fail on real disc data with an apparent
"string_type=0" record with a bogus zero-length na -- direct inspection
(walking a whole real name-data-list purely by na-derived lengths, cross-
checked against every record's `attr1`/`attr2` looking sane) showed this
was actually a *decode misalignment*: the preceding Linear-B (type 4)
record's manually-computed content length was 2 bytes short of its real
`na`-declared length, throwing off every offset after it in the list.
Trusting `na` for the record boundary (and only using the per-type content
parse for the human-readable `text`/`lat`/`lon`/`angle_deg` fields, best
effort) fixed the misalignment and means a genuinely-unrecognized
`string_type` no longer forecloses reading the rest of the list -- its
raw bytes are still captured, just without semantic fields.
"""
from __future__ import annotations

from .bitutils import extract, sws, u16
from .coordconv import decode_region_coord, xy_to_latlon
from .model import BoundingBox, NameFrame, NameList, NameRecord
from .roadtypes import background_type_label


def _cstr(buf: bytes, off: int, length: int) -> str:
    return buf[off : off + length].split(b"\x00", 1)[0].decode("latin-1", errors="replace")


def decode_name_frame(buf: bytes, bounds: BoundingBox) -> NameFrame:
    header_size_raw = u16(buf, 0)
    hlen = sws(header_size_raw)
    frame = NameFrame(header_size_raw=header_size_raw, frame_size=len(buf))

    off = 2
    while off < hlen:
        raw_offset_word = u16(buf, off)
        raw_count_word = u16(buf, off + 2)
        frame.lists.append(NameList(raw_offset_word=raw_offset_word,
                                     raw_count_word=raw_count_word))
        toff = sws(raw_offset_word)
        tnum = raw_count_word
        off += 4
        if toff == 0xFFFF:
            continue

        for _k in range(tnum):
            rec_start = toff
            na = u16(buf, rec_start)
            attr1 = u16(buf, rec_start + 2)
            attr2 = u16(buf, rec_start + 4)
            reclen = sws(extract(na, 0, 11))
            if reclen <= 0:
                raise ValueError(
                    f"Name Data Record at offset {rec_start}: na-derived "
                    f"length is {reclen} -- cannot be a real record")
            ds = extract(attr1, 11, 15)
            st = extract(attr1, 8, 10)
            priority = extract(attr1, 0, 5)
            vertical = bool(extract(attr1, 6, 6))
            body = rec_start + 6

            lat = lon = None
            angle_deg = None
            text = ""
            type_label = f"UNHANDLED string_type={st} (kiwiread.c aborts here)"

            # Best-effort content decode for the human-readable fields,
            # bounded by `reclen` (the authoritative record extent) rather
            # than trusted to derive it -- see module docstring. A type
            # this parser doesn't (yet) recognize just skips this block:
            # `raw_bytes` below is still captured correctly either way.
            if st != 4:
                sx = u16(buf, body + 2)
                sy = u16(buf, body + 4)
                xc = decode_region_coord(sx)
                yc = decode_region_coord(sy)
                lat, lon = xy_to_latlon(xc, yc, bounds)

            if st == 1:
                # 7.4.2.1.2 Barycentric string
                slen = u16(buf, body + 6) * 2
                text = _cstr(buf, body + 8, slen)
                type_label = background_type_label(attr2)
            elif st == 4:
                # 7.4.2.1.5 Linear-B (placed along a road link; no single
                # anchor coordinate is decoded here)
                xc0 = u16(buf, body)
                p = body + 4
                for _i in range(extract(xc0, 0, 3)):
                    p += 2  # orientation/distance placement record, not decoded further
                slen = u16(buf, p) * 2
                text = _cstr(buf, p + 2, slen)
                type_label = background_type_label(attr2)
            elif st == 5:
                # 7.4.2.1.6 Linear-C
                ang = u16(buf, body + 6)
                slen = u16(buf, body + 8) * 2
                text = _cstr(buf, body + 10, slen)
                angle_deg = extract(ang, 0, 8) - 90
                type_label = background_type_label(attr2)
            elif st == 6:
                # 7.4.2.1.7 Symbol+String
                slen = u16(buf, body + 8) * 2
                text = _cstr(buf, body + 10, slen)
                type_label = background_type_label(attr2)

            toff = rec_start + reclen
            frame.records.append(NameRecord(
                string_type=st, type_code=attr2, type_label=type_label,
                priority=priority, vertical=vertical, display_scale_flag=ds,
                raw_offset=rec_start, raw_bytes=buf[rec_start:toff],
                text=text, lat=lat, lon=lon, angle_deg=angle_deg,
            ))

    return frame
