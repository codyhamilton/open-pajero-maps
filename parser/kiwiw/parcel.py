"""Ties together one located main-map parcel's Map Frame header (7.1) with
its road/background/name sub-frames. Ported from `showmap()` in
kiwiread.c.
"""
from __future__ import annotations

from .background import decode_background_frame
from .bitutils import parcel_id_bounds, sws, u16, u32
from .model import BoundingBox, MapFrame, MapFrameHeader, MeshLocation, Parcel
from .name import decode_name_frame
from .road import decode_road_frame

MAPFRAME_HEADER_SIZE = 36  # size+llpid+llcode+dipid+pmcode+dsflag+rlx+rly+geo_str+geo_dec+rg_addr+rg_size+nregion


def decode_map_frame_header(mapdata: bytes) -> MapFrameHeader:
    """7.1 Map Frame Header (36 bytes). Only `llpid` (Ch. 1.2.13 `pid_t`)
    and `llcode` have an established decode anywhere in this codebase
    (kiwiread.c's `showmap()`); the rest are carried verbatim in
    `raw_bytes` -- see `MapFrameHeader`'s docstring for why."""
    raw = mapdata[0:MAPFRAME_HEADER_SIZE]
    llpid_lat, llpid_lon = parcel_id_bounds(mapdata, 2)
    llcode = u16(mapdata, 10)
    return MapFrameHeader(
        raw_bytes=bytes(raw),
        llpid_lat=llpid_lat,
        llpid_lon=llpid_lon,
        llcode_cx=llcode & 0xFF,
        llcode_cy=(llcode >> 8) & 0xFF,
        nregion=u16(mapdata, 34),
    )


def decode_parcel(loc: MeshLocation, mapdata: bytes, n_basic_map: int = 3,
                   n_ext_map: int = 0) -> Parcel:
    """`mapdata` is the full parcel block as read from disk at
    `loc.sector_addr`/`loc.size_logical_sectors` (a Map Frame: header +
    region list + Main Map Data Frame Entry (mfde) table + the
    road/background/name sub-frames it points into).

    The mfde table's real length is *not* `n_basic_map` (always 3 on this
    disc) or even `n_basic_map + n_ext_map` (3+9=12): direct inspection of
    every tested real parcel (Melbourne, both Sydney points, Perth CBD)
    showed the table consistently runs to exactly 20 entries -- ending
    right where the road sub-frame's own content begins, with no gap --
    while `n_basic_map`+`n_ext_map`+`n_basic_route`+`n_ext_route` (the
    LMR's only other three "frame count" fields) only account for 14.
    kiwiread.c's `showmap()` never reads past index `n_basic_map`, so it
    has no opinion on the true table length either; entries at index >= 3
    beyond road/background/name are never dereferenced anywhere in this
    codebase regardless of *why* they exist (Main Map Extended Data Frame,
    or -- for the higher indices, whose `dsa` values are far larger than
    this buffer, i.e. absolute disc sector addresses rather than in-buffer
    [D] offsets -- what looks like route-guidance-related content that is
    a different layer's territory entirely).

    So the table length is derived directly from the data itself: it ends
    exactly where the lowest in-buffer offset among the road/background/
    name entries (indices 0-2, always decoded) begins -- this held exactly
    on every real parcel tested. `n_basic_map`/`n_ext_map` are kept as a
    fallback lower bound only (used if none of road/background/name are
    present with an in-buffer offset, which hasn't been observed on real
    data) so existing callers that don't pass them keep working.

    Every entry from index 3 up to the table's true length is preserved
    as a raw (offset, size) pair in `mfde_raw`; those whose offset lies
    *within* this buffer (Extended Data Frame content, at least for the
    entries actually observed) additionally get their raw content bytes
    captured verbatim in `ext_frame_raw` (no semantic decode -- no other
    sub-frame kind is understood anywhere in this codebase). Entries whose
    offset is far outside this buffer are left as table-only: they are
    real, but point at content elsewhere on disc that isn't part of this
    parcel's own Map Frame buffer, so there is nothing here to round-trip
    beyond the pointer itself."""
    header = decode_map_frame_header(mapdata)
    nregion = header.nregion
    region_list_off = MAPFRAME_HEADER_SIZE
    de_off = region_list_off + nregion * 4

    def _read_entry(i: int) -> tuple[int, int]:
        eoff = de_off + i * 6
        if eoff + 6 > len(mapdata):
            return (0xFFFFFFFF, 0)
        return u32(mapdata, eoff), u16(mapdata, eoff + 4)

    basic_raw = [_read_entry(i) for i in range(3)]
    local_starts = []
    for raw_off, raw_size in basic_raw:
        if raw_off != 0xFFFFFFFF:
            off_v = sws(raw_off)
            if off_v < len(mapdata):
                local_starts.append(off_v)
    if local_starts:
        table_end = min(local_starts)
        total_entries = max((table_end - de_off) // 6, n_basic_map)
    else:
        total_entries = n_basic_map + n_ext_map

    # mfde_t entries: offset(u32,[D]) + size(u16,[SWS]). Index 0=road,
    # 1=background, 2=name (showmap()); any further entries are preserved
    # as raw (offset, size) pairs plus -- for in-buffer ones -- verbatim
    # raw content bytes (`ext_frame_raw`).
    mfde_raw = []
    entries = []
    for i in range(total_entries):
        raw_off, raw_size = _read_entry(i)
        mfde_raw.append((raw_off, raw_size))
        if raw_off != 0xFFFFFFFF:
            entries.append((sws(raw_off), sws(raw_size)))
        else:
            entries.append((0xFFFFFFFF, 0))

    ext_frame_raw: dict[int, bytes] = {}
    max_end = de_off + total_entries * 6
    for i, (off_i, size_i) in enumerate(entries):
        if size_i and off_i != 0xFFFFFFFF and off_i < len(mapdata):
            max_end = max(max_end, off_i + size_i)
            if i >= 3:
                ext_frame_raw[i] = bytes(mapdata[off_i : off_i + size_i])

    # As with the Ch. 6 Parcel Management Record (`parcel_mgmt.py`), the
    # buffer a BMT/mapinfo entry declares is consistently a little larger
    # than everything this Map Frame's own structure actually reaches
    # (observed on every tested real parcel: 6-16 leftover bytes that look
    # like fragments of readable ASCII text, e.g. "...REET"/"...RANT" --
    # plausibly stray leftovers from however the disc was mastered, not a
    # structure this decoder is missing). Preserved verbatim rather than
    # guessed at.
    tail_raw = bytes(mapdata[max_end:])

    parcel = Parcel(location=loc)
    parcel.frame = MapFrame(
        header=header,
        region_list_raw=bytes(mapdata[region_list_off:de_off]),
        mfde_raw=mfde_raw,
        ext_frame_raw=ext_frame_raw,
        tail_raw=tail_raw,
        frame_size=len(mapdata),
    )

    road_off, road_size = entries[0] if len(entries) > 0 else (0xFFFFFFFF, 0)
    bg_off, bg_size = entries[1] if len(entries) > 1 else (0xFFFFFFFF, 0)
    name_off, name_size = entries[2] if len(entries) > 2 else (0xFFFFFFFF, 0)

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
