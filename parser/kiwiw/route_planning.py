"""KIWI-W Chapter 9 (Region Data Management Frame) and Chapter 10
(Route Planning Data Frame) decoders.

This is the ~151 MB of ALLDATA.KWI that the main-map mesh walk never
reaches (see ``parser/estimate_overhead_scaling.py``'s census, tag 0 run
starting at the Region Management Table address).  It is the *route
planning* database: a multi-level, region-partitioned road graph
(nodes + links + link costs + turn regulations + node coordinates),
entirely separate from the main-map road geometry used for drawing.

Entry point: ``parse_region_frame(disc)`` -> ``RegionFrame``, which
enumerates every level and every region, with each region's bounding box
and the DSA/size of its Route Planning Data Frame.  ``parse_rp_frame()``
then decodes one region's Chapter 10 payload down to the per-sub-frame
offset/size table plus the node distribution header (which carries the
node/link/rank census for that region).

Spec references are given as ``Ch. 9.x`` / ``Ch. 10.x`` throughout and
match ``spec/format_english/pdf/0900122e.pdf`` and ``1000122e.pdf``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .bitutils import extract, sws, u8, u16, u24, u32
from .volume import getsector

NO_DATA_DSA = 0xFFFFFFFF
NULL_OFFSET = 0xFFFFFFFF
SENTINEL32 = 0xFFFFFFFF
NULL_REGION = 0xFFFF

# Ch. 9.1 item 14: level management records are 16 B on this disc, but the
# header carries the real size in item 13, so we never hardcode it.
REGION_MGMT_HEADER_FIXED = 50


def d32(v: int) -> int:
    """The 4-byte ``D`` offset encoding.  Confirmed empirically on the real
    disc: like the 16-bit SWS/D fields, these are stored halved (i.e. in
    2-byte word units), with 0xFFFFFFFF as the "no entity" sentinel.  The
    first basic sub-frame (the node data frame) of every region resolves to
    exactly the route planning distribution header size only under this
    reading."""
    return v if v == SENTINEL32 else v << 1


def geo(buf: bytes, off: int) -> float:
    """Ch. 9.2.1 (1): 3-byte value, bit 23 = S/W sign, low 23 bits in
    units of 1/8 arc-second.  Returns signed degrees."""
    v = u24(buf, off)
    deg = (v & 0x7FFFFF) / 8.0 / 3600.0
    return -deg if (v & 0x800000) else deg


# --------------------------------------------------------------------------
# Chapter 9 -- Region Data Management Frame
# --------------------------------------------------------------------------

@dataclass
class LevelMgmtRecord:
    """Ch. 9.1.1 Level Management Record."""
    index: int
    level: int                  # signed, -31..+31; -32 == dummy record
    n_basic_rp_frames: int      # level code bits 7..4
    n_ext_rp_frames: int        # level code bits 3..0
    n_regions: int
    region_rec_size: int        # SWS-decoded bytes
    node_rec_size: int
    link_rec_size: int
    link_cost_rec_size: int
    between_links_restriction_rec_size: int
    between_links_cost_rec_size: int
    raw_level_code: int


@dataclass
class RegionMgmtRecord:
    """Ch. 9.2.1 Region Management Record (+ Ch. 9.2.1.1 Data Storage
    Location Record for region management record type code 0)."""
    index: int          # index within the whole region management table
    level: int          # level this record belongs to (from its level record)
    region_no: int      # index within its level
    lat_top: float
    lat_bottom: float
    lon_left: float
    lon_right: float
    parent_region: int          # 0xFFFF == null (root)
    first_child_region: int     # 0xFFFF == null (no lower level)
    n_child_regions: int
    rp_dsa: int                 # DSA of this region's Route Planning Data Frame
    rp_size_ls: int             # its size, in logical sectors (BS)
    is_dummy: bool

    @property
    def rp_bytes(self) -> int:
        return 0 if self.rp_dsa == NO_DATA_DSA else self.rp_size_ls * 32


@dataclass
class RegionFrame:
    """Ch. 9.1 Region Data Management Distribution Header + Ch. 9.2 table."""
    header_size: int
    region_rec_type_code: int
    n_region_records: int
    rmt_dsa: int
    rmt_size_ls: int
    rmt_file: str
    ctc_dsa: int
    ctc_size_ls: int
    ctc_file: str
    ctc_rec_size: int
    n_levels: int
    level_rec_size: int
    levels: list[LevelMgmtRecord] = field(default_factory=list)
    regions: list[RegionMgmtRecord] = field(default_factory=list)


def _cstr(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("latin-1", errors="replace")


def parse_region_header(buf: bytes) -> RegionFrame:
    """Ch. 9.1 Region Data Management Distribution Header."""
    rf = RegionFrame(
        header_size=sws(u16(buf, 0)),
        region_rec_type_code=u16(buf, 2) & 0xFF,
        n_region_records=u32(buf, 4),
        rmt_dsa=u32(buf, 8),
        rmt_size_ls=u16(buf, 12),
        rmt_file=_cstr(buf[14:26]),
        ctc_dsa=u32(buf, 26),
        ctc_size_ls=u16(buf, 30),
        ctc_file=_cstr(buf[32:44]),
        ctc_rec_size=sws(u16(buf, 44)),
        n_levels=u8(buf, 46),
        level_rec_size=sws(u16(buf, 48)),
    )
    off = REGION_MGMT_HEADER_FIXED
    for i in range(rf.n_levels):
        b = buf[off : off + rf.level_rec_size]
        code = u16(b, 0)
        lvl = extract(code, 10, 15)
        if lvl >= 32:
            lvl -= 64          # 6-bit signed; -32 == dummy
        rf.levels.append(LevelMgmtRecord(
            index=i,
            level=lvl,
            n_basic_rp_frames=extract(code, 4, 7),
            n_ext_rp_frames=extract(code, 0, 3),
            n_regions=u16(b, 2),
            region_rec_size=sws(u16(b, 4)),
            node_rec_size=sws(u16(b, 6)),
            link_rec_size=sws(u16(b, 8)),
            link_cost_rec_size=sws(u16(b, 10)),
            between_links_restriction_rec_size=sws(u16(b, 12)),
            between_links_cost_rec_size=sws(u16(b, 14)),
            raw_level_code=code,
        ))
        off += rf.level_rec_size
    return rf


def parse_region_table(rf: RegionFrame, buf: bytes) -> None:
    """Ch. 9.2 Region Management Table.  Records are stored level by level
    in the same order as the level management records (higher level first);
    each level supplies its own record size and record count."""
    off = 0
    idx = 0
    for lmr in rf.levels:
        for rno in range(lmr.n_regions):
            b = buf[off : off + lmr.region_rec_size]
            dummy = b[0:12] == b"\xff" * 12
            rec = RegionMgmtRecord(
                index=idx,
                level=lmr.level,
                region_no=rno,
                lat_top=geo(b, 0),
                lat_bottom=geo(b, 3),
                lon_left=geo(b, 6),
                lon_right=geo(b, 9),
                parent_region=u16(b, 12),
                first_child_region=u16(b, 14),
                n_child_regions=u16(b, 16),
                rp_dsa=u32(b, 18),
                rp_size_ls=u16(b, 22),
                is_dummy=dummy,
            )
            rf.regions.append(rec)
            off += lmr.region_rec_size
            idx += 1


def parse_region_frame(disc) -> RegionFrame:
    """Read + decode mhr[1] (Ch. 9) and its Region Management Table from an
    open ``kiwiw.disc.AllData``."""
    fh = disc._fh
    e = disc.mhr[1]
    if e.dsa == NO_DATA_DSA or not e.size:
        raise ValueError("no Region Data Management record on this disc")
    fh.seek(getsector(e.dsa, disc.sector_sz, disc.logical_sz))
    rf = parse_region_header(fh.read(e.size * disc.logical_sz))
    fh.seek(getsector(rf.rmt_dsa, disc.sector_sz, disc.logical_sz))
    parse_region_table(rf, fh.read(rf.rmt_size_ls * disc.logical_sz))
    return rf


# --------------------------------------------------------------------------
# Chapter 10 -- Route Planning Data Frame
# --------------------------------------------------------------------------

# Ch. 10.2: the basic route planning data frame management "record" is
# really a sequence of n 6-byte (4-byte D offset + 2-byte SWS size) entries,
# where n is the level management record's "number of sequences of basic
# route planning data frame management records" (9 on this disc -- one per
# sub-frame listed in Ch. 10.4).  Likewise the m extended entries.
BASIC_MGMT_ENTRY_SIZE = 6
BASIC_MGMT_FIELDS = [
    "node", "link", "link_cost", "upper_node", "upper_link",
    "passage_code", "statistical_cost", "node_coord", "road_ref",
]


@dataclass
class RankInfo:
    """Ch. 10.6.1.1 Rank Management Information."""
    rank: int
    n_nodes: int
    n_boundary_nodes: int
    n_links: int
    road_class_mask: int     # bit15 == road class 0, bit0 == road class 15
    rp_level: int
    avg_travel_time: bool

    @property
    def road_classes(self) -> list[int]:
        return [c for c in range(16) if self.road_class_mask & (1 << (15 - c))]


@dataclass
class NodeFrameHeader:
    """Ch. 10.6.1 Node Distribution Header."""
    header_size: int
    n_nodes: int
    n_links: int
    n_ranks: int
    ranks: list[RankInfo] = field(default_factory=list)


@dataclass
class RpSubFrame:
    name: str
    offset: int      # from the top of the route planning distribution header
    size: int        # bytes


@dataclass
class RpFrame:
    """Ch. 10.1 Route Planning Distribution Header, for one region."""
    header_size: int
    region_no: int
    practical_mgmt_code: int
    n_basic: int
    n_ext: int
    basic: list[RpSubFrame] = field(default_factory=list)
    ext: list[RpSubFrame] = field(default_factory=list)
    node_header: NodeFrameHeader | None = None

    def sub(self, name: str) -> RpSubFrame | None:
        for s in self.basic:
            if s.name == name:
                return s
        return None


def parse_node_frame_header(buf: bytes, off: int) -> NodeFrameHeader:
    h = NodeFrameHeader(
        header_size=sws(u16(buf, off)),
        n_nodes=u16(buf, off + 2),
        n_links=u16(buf, off + 4),
        n_ranks=u16(buf, off + 6),
    )
    for i in range(h.n_ranks):
        o = off + 8 + i * 10
        lvl = u16(buf, o + 8)
        h.ranks.append(RankInfo(
            rank=i,
            n_nodes=u16(buf, o),
            n_boundary_nodes=u16(buf, o + 2),
            n_links=u16(buf, o + 4),
            road_class_mask=u16(buf, o + 6),
            rp_level=extract(lvl, 1, 3),
            avg_travel_time=bool(lvl & 1),
        ))
    return h


def parse_rp_frame(buf: bytes, n_basic: int, n_ext: int) -> RpFrame:
    """Decode one region's Route Planning Data Frame (Ch. 10.1-10.3).

    ``buf`` must start at the route planning distribution header (i.e. at
    the byte offset the region management record's DSA resolves to), and
    ``n_basic``/``n_ext`` come from that level's level management record.
    """
    f = RpFrame(
        header_size=sws(u16(buf, 0)),
        region_no=u16(buf, 2),
        practical_mgmt_code=u32(buf, 4),
        n_basic=n_basic,
        n_ext=n_ext,
    )
    off = 8
    subs = []
    for j in range(n_basic):
        o = d32(u32(buf, off))
        s = sws(u16(buf, off + 4))
        nm = BASIC_MGMT_FIELDS[j] if j < len(BASIC_MGMT_FIELDS) else f"basic{j}"
        subs.append(RpSubFrame(nm, o, 0 if o == NULL_OFFSET else s))
        off += 6
    f.basic = subs
    for _ in range(n_ext):
        o = d32(u32(buf, off))
        s = sws(u16(buf, off + 4))
        f.ext.append(RpSubFrame("ext", o, 0 if o == NULL_OFFSET else s))
        off += 6

    nd = f.basic[0] if f.basic else None
    if nd and nd.offset != NULL_OFFSET and nd.size and nd.offset + 8 <= len(buf):
        f.node_header = parse_node_frame_header(buf, nd.offset)
    return f


def read_rp_frame(disc, rec: RegionMgmtRecord, rf: RegionFrame) -> RpFrame | None:
    """Read + decode the Route Planning Data Frame for one region record."""
    if rec.rp_dsa == NO_DATA_DSA or rec.rp_size_ls == 0:
        return None
    lmr = next(l for l in rf.levels if l.level == rec.level)
    disc._fh.seek(getsector(rec.rp_dsa, disc.sector_sz, disc.logical_sz))
    buf = disc._fh.read(rec.rp_size_ls * disc.logical_sz)
    return parse_rp_frame(buf, lmr.n_basic_rp_frames, lmr.n_ext_rp_frames)
