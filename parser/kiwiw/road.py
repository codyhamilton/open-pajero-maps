"""7.2 Road Data Frame decoder. Ported field-for-field from
`dumproad()` in kiwiread.c (which renders to SVG); this version keeps
every decoded field instead of only feeding a renderer.
"""
from __future__ import annotations

from .bitutils import extract, i8, sws, u16, u32
from .coordconv import decode_region_coord, xy_to_latlon
from .model import BoundingBox, RoadFrame, RoadLink, RoadNode
from .roadtypes import road_type_label


def decode_road_frame(buf: bytes, bounds: BoundingBox) -> RoadFrame:
    ninter = u16(buf, 2)
    ndc = buf[4]
    nad = buf[5]
    lvl_field = u16(buf, 6)
    route_planning_level = extract(lvl_field, 10, 15)

    frame = RoadFrame(
        n_intersections=ninter,
        n_display_classes=ndc,
        n_additional_data=nad,
        route_planning_level=route_planning_level,
        header_size_raw=u16(buf, 0),
        lvl_field_raw=lvl_field,
        frame_size=len(buf),
    )

    off = 8
    for _dc in range(ndc):
        raw_offset_word = u16(buf, off)
        raw_count_word = u16(buf, off + 2)
        frame.display_class_table.append((raw_offset_word, raw_count_word))
        xoff = sws(raw_offset_word)
        npoly = extract(raw_count_word, 0, 11)
        if xoff != 0xFFFF:
            frame.display_class_flags[_dc] = bytes(buf[xoff : xoff + 2])
            xoff += 2
            for _j in range(npoly):
                link_start = xoff
                hdr = u32(buf, xoff)
                nnodes = extract(u16(buf, xoff + 4), 0, 10)
                shape_len = sws(extract(u16(buf, xoff + 6), 0, 11))
                lattr = u16(buf, xoff + 14)
                road_type = extract(lattr, 12, 15)

                link = RoadLink(
                    display_class=_dc,
                    road_type=road_type,
                    altitude_flag=bool(extract(lattr, 0, 0)),
                    route_type_guidance_flag=bool(extract(lattr, 1, 1)),
                    pseudo3d_updown=extract(lattr, 2, 3),
                    route_planning_tag=bool(extract(lattr, 4, 4)),
                    link_id_flag=bool(extract(lattr, 6, 6)),
                    selected_link_flag=bool(extract(lattr, 7, 7)),
                    toll_flag=bool(extract(lattr, 8, 8)),
                    route_number_flag=bool(extract(lattr, 9, 9)),
                    infra_link_flag=bool(extract(lattr, 10, 10)),
                    link_id_number_flag=bool(extract(lattr, 11, 11)),
                    n_nodes=nnodes,
                    nodes=[],
                    points=[],
                )

                noff = sws(extract(hdr, 0, 7))
                for _k in range(nnodes):
                    nodeattr = u16(buf, xoff + noff)
                    nip = extract(nodeattr, 0, 9)
                    oneway = extract(nodeattr, 15, 15)
                    planned = extract(nodeattr, 13, 14)
                    tunnel = bool(extract(nodeattr, 12, 12))
                    bridge = bool(extract(nodeattr, 11, 11))

                    sx = u16(buf, xoff + noff + 2)
                    sy = u16(buf, xoff + noff + 4)
                    xc = decode_region_coord(sx)
                    yc = decode_region_coord(sy)
                    lat, lon = xy_to_latlon(xc, yc, bounds)
                    link.nodes.append(RoadNode(
                        x=xc, y=yc, lat=lat, lon=lon,
                        oneway=oneway, planned=planned, tunnel=tunnel, bridge=bridge,
                    ))
                    link.points.append((lat, lon))
                    noff += 6
                    for _l in range(nip):
                        xc += i8(buf, xoff + noff)
                        yc += i8(buf, xoff + noff + 1)
                        lat, lon = xy_to_latlon(xc, yc, bounds)
                        link.points.append((lat, lon))
                        noff += 2

                xoff += sws(extract(hdr, 16, 27))
                link.raw_offset = link_start
                link.raw_bytes = buf[link_start:xoff]
                frame.links.append(link)
        off += 4

    # Additional Data Management Records (7.2.1, [m] entries) -- kiwiread.c
    # never decodes their content's meaning either, and the Ch. 7.2
    # sub-tables for "additional data" weren't cross-referenced in this
    # pass, but real disc data does have non-empty content at the offsets
    # these entries declare (observed trailing the last polyline, right up
    # to the frame's own end), so it's captured raw for round-tripping.
    for _i in range(nad):
        raw_offset_word = u16(buf, off)
        raw_size_word = u16(buf, off + 2)
        frame.additional_data_table.append((raw_offset_word, raw_size_word))
        off += 4
        aoff = sws(raw_offset_word)
        asize = sws(raw_size_word)
        if aoff != 0xFFFF and asize:
            frame.additional_data_raw[_i] = bytes(buf[aoff : aoff + asize])

    return frame
