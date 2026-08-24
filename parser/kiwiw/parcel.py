"""Ties together one located main-map parcel's Map Frame header (7.1) with
its road/background/name sub-frames. Ported from `showmap()` in
kiwiread.c.
"""
from __future__ import annotations

from .background import decode_background_frame
from .bitutils import sws, u16, u32
from .model import BoundingBox, MeshLocation, Parcel
from .name import decode_name_frame
from .road import decode_road_frame

MAPFRAME_HEADER_SIZE = 36  # size+llpid+llcode+dipid+pmcode+dsflag+rlx+rly+geo_str+geo_dec+rg_addr+rg_size+nregion


def decode_parcel(loc: MeshLocation, mapdata: bytes) -> Parcel:
    """`mapdata` is the full parcel block as read from disk at
    `loc.sector_addr`/`loc.size_logical_sectors` (a Map Frame: header +
    region list + Main Map Data Frame Entry (mfde) table + the
    road/background/name sub-frames it points into)."""
    nregion = u16(mapdata, 34)
    de_off = MAPFRAME_HEADER_SIZE + nregion * 4

    # mfde_t entries: offset(u32,[D]) + size(u16,[SWS]). We always read
    # (at least) the 3 fixed slots showmap() relies on: [0]=road,
    # [1]=background, [2]=name. kiwiread.c derives the "real" count from
    # the level's n_basic_map field; we don't have the LMR here, so we
    # defensively read up to 3 entries bounds-checked against the buffer.
    entries = []
    for i in range(3):
        eoff = de_off + i * 6
        if eoff + 6 > len(mapdata):
            entries.append((0xFFFFFFFF, 0))
            continue
        raw_off = u32(mapdata, eoff)
        raw_size = u16(mapdata, eoff + 4)
        entries.append((sws(raw_off), sws(raw_size)))

    parcel = Parcel(location=loc)

    road_off, road_size = entries[0]
    bg_off, bg_size = entries[1]
    name_off, name_size = entries[2]

    if bg_size and bg_off != 0xFFFFFFFF:
        parcel.background = decode_background_frame(
            mapdata[bg_off : bg_off + bg_size], loc.bounds)
    if road_size and road_off != 0xFFFFFFFF:
        parcel.road = decode_road_frame(
            mapdata[road_off : road_off + road_size], loc.bounds)
    if name_size and name_off != 0xFFFFFFFF:
        parcel.name = decode_name_frame(
            mapdata[name_off : name_off + name_size], loc.bounds)

    return parcel
