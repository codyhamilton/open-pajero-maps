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

from .bitutils import extract, i8, sws, u8, u16, u24, u32
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


def read_rp_buf(disc, rec: RegionMgmtRecord) -> bytes | None:
    """Like ``read_rp_frame`` but returns the raw region buffer itself
    (needed by callers, e.g. the road-reference-table decoder below, that
    must read subframe payload bytes rather than just the header table)."""
    if rec.rp_dsa == NO_DATA_DSA or rec.rp_size_ls == 0:
        return None
    disc._fh.seek(getsector(rec.rp_dsa, disc.sector_sz, disc.logical_sz))
    return disc._fh.read(rec.rp_size_ls * disc.logical_sz)


# --------------------------------------------------------------------------
# Chapter 10.6/10.7 -- Node and Link records
# --------------------------------------------------------------------------

@dataclass
class NodeRecord:
    """Ch. 10.6.2.1 Node Record (6 B, no expansion field observed)."""
    index: int
    uppermost_identical_level: int
    is_aggregated: bool
    is_boundary: bool
    n_link_records: int    # 0..14; 15 == "undecided" (no link records stored)
    is_parcel_boundary: bool
    has_traffic_light: bool
    is_rotary: bool
    link_record_offset: int
    n_regulations: int
    n_between_links_cost: int


@dataclass
class LinkRecord:
    """Ch. 10.7.1.1 Link Record (6 B, +2 B region number if the owning
    node is a boundary node)."""
    adjacent_node: int
    link_cost_index: int
    is_suburb: bool
    is_semi_urban_highway: bool
    is_reverse_direction: bool
    following_same_road: int | None   # None == 0xF "no entity"
    angle_deg: int
    region_number: int | None = None


@dataclass
class RegulationRecord:
    """Ch. 10.7.1.2 Regulation Record (2 B)."""
    entry_link_no: int | None
    exit_link_no: int | None
    is_between_links: bool
    passage_code: int


@dataclass
class BetweenLinksCostRecord:
    """Ch. 10.7.1.3 Between-links Cost Record (4 B)."""
    entry_link_no: int | None
    exit_link_no: int | None
    n_non_following_nodes: int
    is_aggregated_intersection: bool
    length_m: float
    avg_travel_time_s: float | None


def _decode_quantized(units: int, mult: int, unit_scale: float = 1.0) -> float:
    return units * (4 ** mult) * unit_scale


def parse_node_record(buf: bytes, off: int, index: int = 0) -> NodeRecord:
    attr = u32(buf, off)
    w2 = u16(buf, off + 4)
    return NodeRecord(
        index=index,
        uppermost_identical_level=extract(attr, 27, 29),
        is_aggregated=bool(attr & (1 << 26)),
        is_boundary=bool(attr & (1 << 25)),
        n_link_records=extract(attr, 21, 24),
        is_parcel_boundary=bool(attr & (1 << 20)),
        has_traffic_light=bool(attr & (1 << 19)),
        is_rotary=bool(attr & (1 << 18)),
        link_record_offset=extract(attr, 0, 17),
        n_regulations=extract(w2, 8, 15),
        n_between_links_cost=extract(w2, 0, 7),
    )


def parse_node_table(buf: bytes, node_sub: RpSubFrame, header: NodeFrameHeader) -> list[NodeRecord]:
    """Ch.10.6.2: the Node Record array, one entry per node in
    ``header.n_nodes``, immediately following the Node Distribution
    Header (``header.header_size`` bytes, including the rank array)."""
    base = node_sub.offset + header.header_size
    return [parse_node_record(buf, base + i * 6, i) for i in range(header.n_nodes)]


def parse_link_record(buf: bytes, off: int, is_boundary: bool) -> LinkRecord:
    adj = u16(buf, off) & 0x1FFF
    cost_idx = u16(buf, off + 2) & 0x7FFF
    fsr = u16(buf, off + 4)
    fsr_val = extract(fsr, 9, 12)
    rec = LinkRecord(
        adjacent_node=adj,
        link_cost_index=cost_idx,
        is_suburb=bool(fsr & (1 << 15)),
        is_semi_urban_highway=bool(fsr & (1 << 14)),
        is_reverse_direction=bool(fsr & (1 << 13)),
        following_same_road=None if fsr_val == 0xF else fsr_val,
        angle_deg=extract(fsr, 0, 8),
    )
    if is_boundary:
        rec.region_number = u16(buf, off + 6)
    return rec


def link_record_size(is_boundary: bool) -> int:
    return 8 if is_boundary else 6


def parse_node_links(buf: bytes, link_sub: RpSubFrame, node: NodeRecord) -> list[LinkRecord]:
    """The Link/Regulation/Between-links-cost records belonging to one
    node, found at ``link_sub.offset + node.link_record_offset`` (Ch.
    10.7: the three record kinds are stored contiguously per node, in
    that order)."""
    if node.n_link_records >= 15:
        return []  # 15 == "undecided": no link records were created
    size = link_record_size(node.is_boundary)
    base = link_sub.offset + node.link_record_offset
    return [parse_link_record(buf, base + i * size, node.is_boundary)
            for i in range(node.n_link_records)]


def parse_node_regulations(buf: bytes, link_sub: RpSubFrame, node: NodeRecord) -> list[RegulationRecord]:
    size = link_record_size(node.is_boundary)
    base = link_sub.offset + node.link_record_offset + node.n_link_records * size
    out = []
    for i in range(node.n_regulations):
        b0, b1 = buf[base + i * 2], buf[base + i * 2 + 1]
        out.append(RegulationRecord(
            entry_link_no=None if (b0 >> 4) == 0xF else (b0 >> 4),
            exit_link_no=None if (b0 & 0xF) == 0xF else (b0 & 0xF),
            is_between_links=bool(b1 & 0x80),
            passage_code=b1 & 0x7F,
        ))
    return out


def parse_node_between_links_cost(buf: bytes, link_sub: RpSubFrame, node: NodeRecord) -> list[BetweenLinksCostRecord]:
    size = link_record_size(node.is_boundary)
    base = (link_sub.offset + node.link_record_offset + node.n_link_records * size
            + node.n_regulations * 2)
    out = []
    for i in range(node.n_between_links_cost):
        o = base + i * 4
        b0, b1, b2, b3 = buf[o], buf[o + 1], buf[o + 2], buf[o + 3]
        len_mult = extract(b1, 2, 3)
        t_mult = extract(b1, 0, 1)
        t_units = b3
        out.append(BetweenLinksCostRecord(
            entry_link_no=None if (b0 >> 4) == 0xF else (b0 >> 4),
            exit_link_no=None if (b0 & 0xF) == 0xF else (b0 & 0xF),
            n_non_following_nodes=extract(b1, 5, 6),
            is_aggregated_intersection=bool(b1 & (1 << 4)),
            length_m=_decode_quantized(b2, len_mult),
            avg_travel_time_s=None if t_units == 0xFE else _decode_quantized(t_units, t_mult, 0.1),
        ))
    return out


# --------------------------------------------------------------------------
# Chapter 10.10 -- Link Cost Table
# --------------------------------------------------------------------------

@dataclass
class LinkCostRecord:
    link_id_origin: int
    link_id_dest_delta: int
    uppermost_identical_link_level: int
    link_passage_status: int
    is_toll: bool
    is_bypass: bool
    n_traffic_lights: int
    forward_passable: bool
    reverse_passable: bool
    has_center_line: bool
    crossable_oncoming_lane: bool
    same_cost_both_directions: bool
    has_statistics_cost: bool
    n_lanes_width_code: int
    link_class_code: int
    road_class_code: int
    length_m: float
    connected_node: int
    avg_travel_time_s: float | None


def parse_link_cost_table(buf: bytes, sub: RpSubFrame) -> tuple[int, int, list[LinkCostRecord]]:
    """Ch.10.10.1/10.10.2. Returns ``(n_with_avg_time, n_without_avg_time,
    records)``. The disc stores the ``n_with_avg_time`` 16-byte records
    first, then the ``n_without_avg_time`` 14-byte records (see
    ``route_planning_writer.write_link_cost_record``'s docstring for the
    empirical resolution of this spec-vs-disc size discrepancy)."""
    n_with = u16(buf, sub.offset + 2)
    n_without = u16(buf, sub.offset + 4)
    off = sub.offset + 6
    out = []
    for i in range(n_with + n_without):
        has_time = i < n_with
        rec_size = 16 if has_time else 14
        out.append(_parse_link_cost_record(buf, off, has_time))
        off += rec_size
    return n_with, n_without, out


def _parse_link_cost_record(buf: bytes, off: int, has_time: bool) -> LinkCostRecord:
    """Field offsets within one record (see
    ``route_planning_writer.write_link_cost_record`` for the exact
    inverse): 0:4 link_id_origin(u32), 4:6 link_id_dest_delta(u16),
    6:8 status word, 8:10 attr word, 10:12 length word, 12:14
    connected_node, 14:16 optional avg-travel-time word."""
    w = u16(buf, off + 6)
    attr = u16(buf, off + 8)
    lw = u16(buf, off + 10)
    rec = LinkCostRecord(
        link_id_origin=u32(buf, off),
        link_id_dest_delta=u16(buf, off + 4),
        uppermost_identical_link_level=extract(w, 13, 15),
        link_passage_status=extract(w, 11, 12),
        is_toll=bool(w & (1 << 10)),
        is_bypass=bool(w & (1 << 9)),
        n_traffic_lights=extract(w, 0, 8),
        forward_passable=bool(attr & (1 << 15)),
        reverse_passable=bool(attr & (1 << 14)),
        has_center_line=bool(attr & (1 << 13)),
        crossable_oncoming_lane=bool(attr & (1 << 12)),
        same_cost_both_directions=bool(attr & (1 << 11)),
        has_statistics_cost=bool(attr & (1 << 10)),
        n_lanes_width_code=extract(attr, 7, 9),
        link_class_code=extract(attr, 4, 6),
        road_class_code=attr & 0xF,
        length_m=_decode_quantized(extract(lw, 0, 11), extract(lw, 12, 14)),
        connected_node=u16(buf, off + 12),
        avg_travel_time_s=None,
    )
    if has_time:
        tw = u16(buf, off + 14)
        rec.avg_travel_time_s = _decode_quantized(extract(tw, 0, 11), extract(tw, 12, 14), 0.1)
    return rec


# --------------------------------------------------------------------------
# Chapter 10.13 -- Road Reference Table (aggregated-intersection clustering)
# --------------------------------------------------------------------------

@dataclass
class AggregatedNodeInfo:
    """Ch.10.13.1 Aggregated Node Information.

    Confidence, per field (see docs/phases/01-format-analysis.md for the
    empirical validation this is based on):
    - ``size``, ``node_number``, ``n_composition_links``,
      ``n_route_info``, ``n_subordinate_nodes``: HIGH -- fixed offsets,
      and ``size`` is checked against the real disc by confirming
      consecutive records consume the Road Reference Table exactly.
    - ``composition_link_cost_numbers``, ``subordinate_node_offsets``:
      MEDIUM-HIGH -- fixed-width arrays whose *count* is spec-given,
      decoded at the offsets implied by the preceding variable-length
      bit-packed field's declared size. Validated indirectly: with the
      padding rule below, byte-accounting a full record (header + nibble
      array + these two arrays + route-info array) against the record's
      own declared ``size`` lands exactly on zero leftover bytes for
      208,766/218,440 (95.6%) of every real Aggregated Node Information
      record on the disc (see ``survey_road_reference_table.py``); the
      remaining 4.4% are off by a small, non-random amount (+4 bytes:
      2.8%; +2 bytes: 0.2%; +6 bytes: <0.1%; a handful of other residuals)
      whose cause was not identified (candidates: rare extra field or a
      parity case in the padding rule not covered by the disc sample
      examined). Field VALUES were not independently cross-checked
      against a second oracle -- only the record's total byte length.
    - ``subordinate_node_order_by_link``: MEDIUM -- decoded as a 4-bit-
      per-entry nibble array, count = the representative node's own
      ``n_link_records``, followed by 0 or 1 padding bytes such that the
      *record-relative* byte offset immediately after the array (i.e.
      ``7 + nibble_bytes``, since the fixed header is 7 bytes) is even --
      i.e. this field is padded so the following field starts on a
      word (2-byte) boundary measured from the start of the record, not
      from the start of the sub-frame. This word-alignment rule is what
      drives the 95.6% exact byte-accounting figure above; the naive
      "round the nibble array itself up to an even byte count"
      alternative was tried first and fits substantially worse (see
      docs/phases/01-format-analysis.md). Still best-effort: the
      underlying spec text for this item and its padding was garbled in
      the archived PDF extraction, so this is inferred from the byte
      arithmetic, not read off unambiguous spec prose.
    - ``route_info``: MEDIUM -- decoded per the literal field table.
      Each entry is additionally assumed to be word-padded the same way
      (padded to keep the running record-relative offset even after each
      entry) -- this is part of what the 95.6% figure above validates,
      but individual field values are not independently cross-checked.
    """
    size: int
    node_number: int
    n_composition_links: int
    n_route_info: int
    n_subordinate_nodes: int
    n_connected_links: int    # from the representative node's own Node Record
    subordinate_node_order_by_link: list[int] = field(default_factory=list)
    composition_link_cost_numbers: list[int] = field(default_factory=list)
    subordinate_node_offsets: list[tuple[int, int]] = field(default_factory=list)  # (dx, dy), signed
    route_info: list[dict] = field(default_factory=list)


def parse_road_reference_table(
    buf: bytes, sub: RpSubFrame, node_records: list[NodeRecord] | None = None,
) -> list[AggregatedNodeInfo]:
    """Ch.10.13. ``node_records`` (from ``parse_node_table``) is optional
    but required to decode the bit-packed "external link connection
    subordinate node numbers" field (10.13.1 item 6), whose length
    depends on the representative node's own connected-link count; when
    omitted, that one field is left empty but every other field (and,
    critically, the record-to-record walk via each record's own declared
    ``size``) still works, since ``size`` alone is enough to advance to
    the next record regardless of whether the bit-packed field was
    understood."""
    if sub.size < 2:
        return []
    n_aggregated = u16(buf, sub.offset)
    out = []
    pos = sub.offset + 2
    end = sub.offset + sub.size
    for _ in range(n_aggregated):
        if pos + 2 > end:
            break
        size = sws(u16(buf, pos))
        node_number = u16(buf, pos + 2)
        ncl = buf[pos + 4] & 0x0F
        nri = buf[pos + 5]
        nsni = buf[pos + 6]
        n_connected_links = 0
        if node_records is not None and 0 <= node_number < len(node_records):
            n_connected_links = node_records[node_number].n_link_records
            if n_connected_links >= 15:
                n_connected_links = 0
        rec = AggregatedNodeInfo(
            size=size, node_number=node_number, n_composition_links=ncl,
            n_route_info=nri, n_subordinate_nodes=nsni,
            n_connected_links=n_connected_links,
        )
        nibble_bytes = (n_connected_links + 1) // 2
        # Word-align the *following* field to an even record-relative
        # offset (record header is 7 bytes, so pad by 1 iff
        # 7 + nibble_bytes is odd) -- see AggregatedNodeInfo docstring.
        # Applies even when n_connected_links == 0 (a lone 1-byte pad).
        padded = nibble_bytes + ((7 + nibble_bytes) % 2)
        o = pos + 7
        if n_connected_links:
            orders = []
            for k in range(n_connected_links):
                byte = buf[o + k // 2]
                nib = (byte >> 4) if k % 2 == 0 else (byte & 0xF)
                orders.append(nib)
            rec.subordinate_node_order_by_link = orders
        o2 = o + padded
        if ncl:
            for k in range(ncl):
                rec.composition_link_cost_numbers.append(u16(buf, o2 + k * 2))
            o3 = o2 + ncl * 2
        else:
            o3 = o2
        if nsni:
            for k in range(nsni):
                dx = i8(buf, o3 + k * 2)
                dy = i8(buf, o3 + k * 2 + 1)
                rec.subordinate_node_offsets.append((dx, dy))
            o4 = o3 + nsni * 2
        else:
            o4 = o3
        oo = o4
        for _ in range(nri):
            if oo + 2 > pos + size:
                break
            b0 = buf[oo]
            b1 = buf[oo + 1]
            n_passing = (b1 >> 4) & 0xF
            links = list(buf[oo + 2: oo + 2 + n_passing])
            rec.route_info.append({
                "entry_link_no": b0 >> 4, "exit_link_no": b0 & 0xF,
                "n_passing_links": n_passing,
                "composition_link_relative_numbers": links,
            })
            step = 2 + n_passing
            # Word-align each route-info entry the same way as the nibble
            # array above (record-relative offset kept even).
            if (oo - pos + step) % 2:
                step += 1
            oo += step
        out.append(rec)
        pos += size
    return out
