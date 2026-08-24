"""7.4 Name Data Frame decoder. Ported from `dumpname()` in kiwiread.c.

Five "String Type" variants are defined by the spec (7.4.2.1.x); kiwiread.c
(and this port) only decode types 1 (Barycentric), 4 (Linear-B), 5
(Linear-C), and 6 (Symbol+String) -- the C tool `exit()`s on any other type
as unhandled. This port instead stops decoding the remaining records in
that one name-data-list (recording what was already decoded) and reports
the gap, rather than aborting the whole parcel.
"""
from __future__ import annotations

from .bitutils import extract, sws, u16
from .coordconv import decode_region_coord, xy_to_latlon
from .model import BoundingBox, NameFrame, NameRecord
from .roadtypes import background_type_label


def _cstr(buf: bytes, off: int, length: int) -> str:
    return buf[off : off + length].split(b"\x00", 1)[0].decode("latin-1", errors="replace")


def decode_name_frame(buf: bytes, bounds: BoundingBox) -> NameFrame:
    hlen = sws(u16(buf, 0))
    frame = NameFrame()

    off = 2
    while off < hlen:
        toff = sws(u16(buf, off))
        tnum = u16(buf, off + 2)
        off += 4
        if toff == 0xFFFF:
            continue

        for _k in range(tnum):
            attr1 = u16(buf, toff + 2)
            attr2 = u16(buf, toff + 4)
            ds = extract(attr1, 11, 15)
            st = extract(attr1, 8, 10)
            priority = extract(attr1, 0, 5)
            vertical = bool(extract(attr1, 6, 6))
            toff += 6

            lat = lon = None
            xc = yc = None
            if st != 4:
                sx = u16(buf, toff + 2)
                sy = u16(buf, toff + 4)
                xc = decode_region_coord(sx)
                yc = decode_region_coord(sy)
                lat, lon = xy_to_latlon(xc, yc, bounds)

            angle_deg = None
            text = ""

            if st == 1:
                # 7.4.2.1.2 Barycentric string
                slen = u16(buf, toff + 6) * 2
                text = _cstr(buf, toff + 8, slen)
                toff += slen + 8
            elif st == 4:
                # 7.4.2.1.5 Linear-B (placed along a road link; no single
                # anchor coordinate is decoded here)
                xc0 = u16(buf, toff)
                toff += 4
                for _i in range(extract(xc0, 0, 3)):
                    toff += 2  # orientation/distance placement record, not decoded further
                slen = u16(buf, toff) * 2
                text = _cstr(buf, toff + 2, slen)
                toff += slen + 2
            elif st == 5:
                # 7.4.2.1.6 Linear-C
                ang = u16(buf, toff + 6)
                slen = u16(buf, toff + 8) * 2
                text = _cstr(buf, toff + 10, slen)
                angle_deg = extract(ang, 0, 8) - 90
                toff += slen + 10
            elif st == 6:
                # 7.4.2.1.7 Symbol+String
                slen = u16(buf, toff + 8) * 2
                text = _cstr(buf, toff + 10, slen)
                toff += slen + 10
            else:
                frame.records.append(NameRecord(
                    string_type=st, type_code=attr2,
                    type_label=f"UNHANDLED string_type={st} (kiwiread.c aborts here)",
                    priority=priority, vertical=vertical, display_scale_flag=ds,
                    text="", lat=lat, lon=lon,
                ))
                break

            frame.records.append(NameRecord(
                string_type=st, type_code=attr2,
                type_label=background_type_label(attr2),
                priority=priority, vertical=vertical, display_scale_flag=ds,
                text=text, lat=lat, lon=lon, angle_deg=angle_deg,
            ))

    return frame
