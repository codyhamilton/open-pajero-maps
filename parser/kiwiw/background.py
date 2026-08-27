"""7.3 Background Data Frame decoder. Ported from `dumpbkgd()` in
kiwiread.c.
"""
from __future__ import annotations

from .bitutils import extract, sws, i8, u16, u32
from .coordconv import decode_region_coord, xy_to_latlon
from .model import BackgroundElement, BackgroundFrame, BackgroundShape, BoundingBox
from .roadtypes import background_type_label


def decode_background_frame(buf: bytes, bounds: BoundingBox) -> BackgroundFrame:
    header_size_raw = u16(buf, 0)
    hlen = sws(header_size_raw)
    frame = BackgroundFrame(header_size_raw=header_size_raw, frame_size=len(buf))

    off = 2
    while off < hlen:
        raw_offset_word = u16(buf, off)
        raw_size_word = u16(buf, off + 2)
        poff = sws(raw_offset_word)
        plen = sws(raw_size_word)
        off += 4
        if poff == 0xFFFF:
            frame.elements.append(BackgroundElement(
                raw_offset_word=raw_offset_word, raw_size_word=raw_size_word))
            continue

        n_raw = u16(buf, poff)
        n = n_raw
        poff += 2
        counts = []
        shape_classes = []
        unit_table_raw = []
        for _i in range(n):
            boff_word = u16(buf, poff)
            val = u16(buf, poff + 2)
            unit_table_raw.append((boff_word, val))
            counts.append(extract(val, 0, 11))
            shape_classes.append(extract(val, 14, 15))
            poff += 4

        frame.elements.append(BackgroundElement(
            raw_offset_word=raw_offset_word, raw_size_word=raw_size_word,
            n_raw=n_raw, unit_table_raw=unit_table_raw,
        ))

        for i in range(n):
            for _j in range(counts[i]):
                shape_start = poff
                hdr = u16(buf, poff)
                flag = u16(buf, poff + 2)
                code = u16(buf, poff + 4)
                addl = u16(buf, poff + 6)
                sx = u16(buf, poff + 8)
                sy = u16(buf, poff + 10)

                rec_len = sws(extract(hdr, 0, 11))
                ncoord = extract(flag, 0, 10)
                mult_const = 1 << extract(addl, 0, 2)
                underground = bool(extract(addl, 9, 9))
                pen_up = bool(extract(addl, 10, 10))

                shape = BackgroundShape(
                    shape_class=shape_classes[i],
                    type_code=code,
                    type_label=background_type_label(code),
                    n_coords=ncoord,
                    mult_const=mult_const,
                    underground=underground,
                    pen_up=pen_up,
                    coords=[],
                )

                if shape_classes[i]:  # 0 = point (not rendered/geometric in kiwiread either)
                    xc = decode_region_coord(sx)
                    yc = decode_region_coord(sy)
                    coord_off = poff + 12
                    lat, lon = xy_to_latlon(xc, yc, bounds)
                    shape.coords.append((lat, lon))
                    for k in range(ncoord):
                        xo = i8(buf, coord_off + k * 2)
                        yo = i8(buf, coord_off + k * 2 + 1)
                        xc += xo * mult_const
                        yc += yo * mult_const
                        lat, lon = xy_to_latlon(xc, yc, bounds)
                        shape.coords.append((lat, lon))

                poff += rec_len
                shape.raw_offset = shape_start
                shape.raw_bytes = buf[shape_start:poff]
                frame.shapes.append(shape)

    return frame
