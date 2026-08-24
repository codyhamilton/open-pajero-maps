"""Ch. 5 (Data Volume) and Ch. 6 (Parcel-related Data Management Frame)
header parsing for ALLDATA.KWI.

Ported from `showalldata()` in kiwiread.c, which this file's struct offsets
were validated against (builds, decodes this exact disc's header/LMR/BSMR
tables without assertion failures -- see docs/phases/00-inventory.md).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .bitutils import extract, sws, geo_secs, u16, u32
from .model import BoundingBox, LevelMgmtRecord, BlockSetMgmtRecord, VolumeHeader

SECTOR_SZ_DEFAULT = 2048
LOGICAL_SZ_DEFAULT = 32

# sizeof(struct mid_t) = pid_t(8) + floor(1) + reserved(1) + date(2) = 12
MID_SIZE = 12
# sizeof(struct pid_t) = geonum(3) + exp(1) + geonum(3) + exp(1) = 8
PID_SIZE = 8
# sizeof(struct datavol_t), padded to 2048 per spec 5. table (record 1)
DATAVOL_SIZE = 2048
# sizeof(struct mhr_t) = sectoraddress_t(4) + size(2) + name(12)
MHR_SIZE = 18
MHR_COUNT = 34
# sizeof(struct lmr_t): header(2)+numbers(2)+dispflag(4*5=20)
#   +nblocksets(2)+nblocks(2)+nparcels(4*2=8)+bsmr_off(2)+nrsize(2) = 40
LMR_BASE_SIZE = 40
# sizeof(struct bsmr_t) = header(2)+bmt_offset(4)+bmt_size(4)
BSMR_SIZE = 10
# sizeof(struct bmt_t) = sectoraddress_t(4)+size(2)
BMT_SIZE = 6


def getsector(sector_addr: int, sector_sz: int, logical_sz: int) -> int:
    """1.2.7 Sector Address -> byte offset. Mirrors kiwiread.c's
    `getsector()`. Top 24 bits are a sector index (relative to some base),
    low 6 bits (of the low byte) are a "logical sector" sub-index within
    that sector; bits 6/7 of the low byte are flags not used for the
    offset math (booklet A/B, S/D) here."""
    return (sector_addr >> 8) * sector_sz + (sector_addr & 0x3F) * logical_sz


def _cstr(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("latin-1", errors="replace")


def parse_volume_header(buf: bytes) -> VolumeHeader:
    """Decode the 2048-byte Data Volume (Ch. 5.1) at the start of
    ALLDATA.KWI."""
    assert len(buf) >= DATAVOL_SIZE

    def mid_ssi(off: int, ssi_len: int):
        # mid_t.date is the last u16 of the 12-byte mid_t
        date = u16(buf, off + 10)
        ssi = _cstr(buf[off + MID_SIZE : off + MID_SIZE + ssi_len])
        return date, ssi

    _spec_date, spec_ssi = mid_ssi(0, 52)
    _data_date, data_ssi = mid_ssi(64, 52)
    _sys_date, sys_ssi = mid_ssi(128, 20)

    format_ver = _cstr(buf[160:224])
    data_ver = _cstr(buf[224:288])
    disk_title = _cstr(buf[288:416])
    contents0 = u16(buf, 416)
    media_version = _cstr(buf[424:456])

    box_ll_off = 456
    box_ur_off = 456 + PID_SIZE
    ll_lat = geo_secs(buf[box_ll_off : box_ll_off + 3])
    ll_lng = geo_secs(buf[box_ll_off + 4 : box_ll_off + 7])
    ur_lat = geo_secs(buf[box_ur_off : box_ur_off + 3])
    ur_lng = geo_secs(buf[box_ur_off + 4 : box_ur_off + 7])

    log_size = u16(buf, 472)
    sector_size = u16(buf, 474)
    background = u16(buf, 476)

    return VolumeHeader(
        format_version=format_ver,
        data_version=data_ver,
        disk_title=disk_title,
        media_version=media_version,
        system_specific_id=spec_ssi,
        data_author_id=data_ssi,
        system_id=sys_ssi,
        contents_main_map=bool(contents0 & (1 << 15)),
        contents_route_planning=bool(contents0 & (1 << 14)),
        contents_index_data=bool(contents0 & (1 << 13)),
        coverage=BoundingBox(lat_lo=ll_lat, lat_hi=ur_lat, lon_lo=ll_lng, lon_hi=ur_lng),
        logical_sector_size=log_size,
        sector_size=sector_size,
        background_in_map_is_sea=bool(background & (1 << 15)),
        background_out_of_map_is_sea=bool(background & (1 << 14)),
    )


@dataclass
class MhrEntry:
    index: int  # 0-based (spec numbers these 1..34)
    dsa: int
    size: int
    name: str


def parse_mhr_table(buf: bytes) -> list[MhrEntry]:
    """Decode the 34-entry Management Header Record table that
    immediately follows the Data Volume."""
    entries = []
    for i in range(MHR_COUNT):
        off = i * MHR_SIZE
        dsa = u32(buf, off)
        size = u16(buf, off + 4)
        name = _cstr(buf[off + 6 : off + 18])
        entries.append(MhrEntry(index=i, dsa=dsa, size=size, name=name))
    return entries


@dataclass
class Pdmdh:
    """6.1 Parcel Data Management Distribution Header, plus the LMR/BSMR
    tables it introduces."""
    coverage: BoundingBox
    lmr_size: int
    bsmr_size: int
    bmr_size: int
    n_lmr: int
    n_bsmr: int
    levels: list[LevelMgmtRecord]
    blocksets: list[BlockSetMgmtRecord]
    bsmr_table_offset: int  # byte offset (within the PDMDH buffer) of the BSMR array
    bmt_table_base: int  # byte offset (within the PDMDH buffer) that bmt_offset fields are relative to


def parse_pdmdh(buf: bytes) -> Pdmdh:
    header_size = sws(u16(buf, 0))
    lower_lat = geo_secs(buf[11:14])
    upper_lat = geo_secs(buf[8:11])
    left_lng = geo_secs(buf[14:17])
    right_lng = geo_secs(buf[17:20])
    lmr_sz = sws(u16(buf, 20))
    bsmr_sz = u16(buf, 22)
    bmr_sz = u16(buf, 24)
    n_lmr = u16(buf, 26)
    n_bsmr = u16(buf, 28)

    coverage = BoundingBox(lat_lo=lower_lat, lat_hi=upper_lat, lon_lo=left_lng, lon_hi=right_lng)

    moff = 30  # sizeof(pdmdh_t) per struct layout (matches header_size when present)
    levels: list[LevelMgmtRecord] = []
    raw_lmrs = []
    for _ in range(n_lmr):
        lmr_off = moff
        lmr_header = u16(buf, lmr_off)
        numbers = u16(buf, lmr_off + 2)
        dispflag = [u32(buf, lmr_off + 4 + 4 * i) for i in range(5)]
        # struct nblocksets/nblocks are {lat; lng;} (lat byte first) --
        # see kiwiread.c lmr_t definition.
        nbs_lat = buf[lmr_off + 24]
        nbs_lng = buf[lmr_off + 25]
        nbl_lat = buf[lmr_off + 26]
        nbl_lng = buf[lmr_off + 27]
        nparcels_lat = []
        nparcels_lng = []
        for i in range(4):
            base = lmr_off + 28 + 2 * i
            nparcels_lat.append(buf[base])
            nparcels_lng.append(buf[base + 1])
        bsmr_off = u16(buf, lmr_off + 36)
        nrsize = u16(buf, lmr_off + 38)

        level = extract(lmr_header, 10, 15)
        nx = (1 + nbs_lng) * (1 + nbl_lng) * (1 + nparcels_lng[0])
        ny = (1 + nbs_lat) * (1 + nbl_lat) * (1 + nparcels_lat[0])

        lmr = LevelMgmtRecord(
            level=level,
            upper_level=extract(lmr_header, 4, 7),
            lower_level=extract(lmr_header, 0, 3),
            n_basic_map=extract(numbers, 12, 15),
            n_ext_map=extract(numbers, 8, 11),
            n_basic_route=extract(numbers, 4, 7),
            n_ext_route=extract(numbers, 0, 3),
            display_flags=dispflag,
            n_blocksets_lat=nbs_lat,
            n_blocksets_lng=nbs_lng,
            n_blocks_lat=nbl_lat,
            n_blocks_lng=nbl_lng,
            n_parcels_lat=nparcels_lat,
            n_parcels_lng=nparcels_lng,
            bsmr_offset=bsmr_off * 2,
            node_record_size=nrsize * 2,
            grid_nx=nx,
            grid_ny=ny,
        )

        # Extended info directly follows the base 40-byte LMR when
        # lmr_size >= 42 (see kiwiread.c ~line 1779).
        if lmr_sz >= LMR_BASE_SIZE + 2:
            xt = u16(buf, lmr_off + LMR_BASE_SIZE)
            lmr.n_road_frames = extract(xt, 10, 13) + 1
            lmr.n_background_frames = extract(xt, 5, 9) + 1
            lmr.n_name_frames = extract(xt, 0, 4) + 1

        levels.append(lmr)
        raw_lmrs.append((lmr_off, lmr))
        moff += lmr_sz

    bsmr_table_offset = moff
    blocksets: list[BlockSetMgmtRecord] = []
    for i in range(n_bsmr):
        off = moff + i * BSMR_SIZE
        b_header = u16(buf, off)
        bmt_offset_raw = u32(buf, off + 2)
        bmt_size_raw = u32(buf, off + 6)
        # struct bsmr_t: bmt_offset is [D] (doubled unless the 0xFFFF
        # sentinel), bmt_size is [SWS] (same encoding) -- kiwiread.c calls
        # D()/SWS() on these (they're the same function) before using them.
        blocksets.append(
            BlockSetMgmtRecord(
                level=extract(b_header, 10, 15),
                blockset_index=extract(b_header, 0, 7),
                bmt_offset=sws(bmt_offset_raw),
                bmt_size=sws(bmt_size_raw),
            )
        )

    return Pdmdh(
        coverage=coverage,
        lmr_size=lmr_sz,
        bsmr_size=bsmr_sz,
        bmr_size=bmr_sz,
        n_lmr=n_lmr,
        n_bsmr=n_bsmr,
        levels=levels,
        blocksets=blocksets,
        bsmr_table_offset=bsmr_table_offset,
        bmt_table_base=0,
    )
