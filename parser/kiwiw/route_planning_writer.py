"""Writer (encoder) for the KIWI-W Chapter 9 (Region Data Management Frame)
and Chapter 10 (Route Planning Data Frame), the exact inverse of the
decoders in ``route_planning.py``.

Scope (2026-08-25 prototype, OSM -> Ch9/Ch10 writer):

- Every field/frame/table the spec defines for a "type-code 0" (DSA+BS)
  region is written, including the vendor "ext" frames (10.5/10.5.1) and
  the Road Reference Table (10.13) -- per the project owner's explicit
  instruction to match the vendor structure for safety rather than omit
  anything we don't fully understand. Where semantics are genuinely
  unknown (the ext frame payload, the Common Traffic Condition Table),
  a documented, spec-legal placeholder/absent value is written -- never
  silently skipped.
- This module only encodes bytes from an in-memory graph model
  (``RpGraph`` / ``RpNode`` / ``RpLink`` below, built by
  ``parser/build_route_graph.py``). It does not know how to place the
  result inside a real ``ALLDATA.KWI`` (sector allocation, DSA
  resolution) -- ``parse_rp_frame()``/``parse_region_header()`` in the
  sibling decoder module already work directly off in-memory buffers, so
  round-tripping through them doesn't require that either.

Known simplifications relative to the real disc (see
``docs/phases/01-format-analysis.md`` / the Phase-3 prototype report for
the full list): no multi-region hierarchy (a single, standalone region is
encoded, not embedded in a country-wide level-2/4/6/8 tree of regions);
no boundary-node/cross-region link bookkeeping (the graph is a single
self-contained bbox, so no node is marked a boundary node and no link
record carries a region number); no "aggregated intersection" clustering
(the Road Reference Table is written with zero aggregated nodes, a
spec-legal empty case); "Corresponding Route Planning Data Level" per
rank is a heuristic derived from OSM highway class, not a real
multi-region contraction; link-cost "Link ID Number" fields are
synthetic (no main-map road writer exists yet to cross-reference); the
Upper Level Node/Link, Statistical Cost and Passage Code frames are left
absent (matching the empirically observed real-disc population: these
are 0% or near-0% populated across all 1,864 real regions -- see the
Ch.9/Ch.10 phase-doc entry).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .bitutils import geo_secs_bytes, unsws
from .route_planning import (
    BASIC_MGMT_FIELDS,
    NO_DATA_DSA,
    NULL_OFFSET,
    SENTINEL32,
)

POISON = 0xA5


# --------------------------------------------------------------------------
# Small helpers (mirrors of volume_writer.py's conventions)
# --------------------------------------------------------------------------

def _u8(v: int) -> bytes:
    if not 0 <= v <= 0xFF:
        raise ValueError(f"{v} does not fit in a u8")
    return bytes((v,))


def _u16(v: int) -> bytes:
    if not 0 <= v <= 0xFFFF:
        raise ValueError(f"{v} does not fit in a u16")
    return bytes((v >> 8, v & 0xFF))


def _u24(v: int) -> bytes:
    if not 0 <= v <= 0xFFFFFF:
        raise ValueError(f"{v} does not fit in a u24")
    return bytes(((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _u32(v: int) -> bytes:
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"{v} does not fit in a u32")
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _text(s: str, size: int) -> bytes:
    raw = s.encode("latin-1")
    if len(raw) > size:
        raise ValueError(f"text {s!r} is {len(raw)} bytes, field is {size}")
    return raw + b"\x00" * (size - len(raw))


def _put(buf: bytearray, off: int, data: bytes) -> None:
    if off + len(data) > len(buf):
        raise ValueError(f"write of {len(data)} B at {off} overruns buffer of {len(buf)} B")
    buf[off : off + len(data)] = data


def sws_enc(v: int) -> int:
    """Inverse of ``route_planning`` decoding's ``sws()`` (== bitutils.sws):
    halve, leaving the 0xFFFF sentinel untouched."""
    return unsws(v)


def d32_enc(v: int) -> int:
    """Inverse of ``route_planning.d32()``: halve, leaving the 0xFFFFFFFF
    sentinel untouched."""
    if v == SENTINEL32:
        return v
    if v & 1:
        raise ValueError(f"{v} is odd -- cannot be a D-encoded (halved) offset")
    return v >> 1


def geo_enc(deg: float) -> bytes:
    """Inverse of ``route_planning.geo()`` -- identical bit layout to
    ``bitutils.geo_secs_bytes`` (3-byte, bit23 sign, 1/8 arc-second)."""
    return geo_secs_bytes(deg)


# ==========================================================================
# In-memory graph model consumed by this writer. Built by
# parser/build_route_graph.py from OSM data; independent of the KIWI-W
# on-disc dataclasses in route_planning.py, which round-trip these through
# their own dataclasses (RegionMgmtRecord, RpFrame, ...) instead.
# ==========================================================================

@dataclass
class RpLink:
    """One directed link record, stored inside its origin node's adjacency
    list. ``adjacent_node`` is the node-table index (0-based) of the other
    end. ``link_cost_index`` indexes into the region's shared link-cost
    table (10.10.2) -- forward and reverse directions of an undirected OSM
    way share one link-cost record, matching the spec's stated size-saving
    convention (10.10.2, paragraph before Condition 1)."""
    adjacent_node: int
    link_cost_index: int
    forward_direction: bool          # link is in the *reverse* direction of the underlying entity when False
    angle_deg: int                   # 0..359, Ch.10.7.1.1 item (7)
    following_same_road: int | None  # 0..14 link-record-number, or None ("no entity", 0xF)
    road_class: int                  # 0..15, Ch.32.2
    # Between-links regulations that apply for this link as the entry side,
    # keyed by exit-side link-record-number local to the same node (None
    # key == "all exit links", per spec bit pattern 0xF).
    regulations: list[tuple[int | None, int]] = field(default_factory=list)  # (exit_link_no, passage_code)


@dataclass
class RpNode:
    lat: float
    lon: float
    is_boundary: bool
    rank: int
    links: list[RpLink] = field(default_factory=list)


@dataclass
class RpLinkCost:
    """One shared Link Cost Record (10.10.2). ``link_id_origin``/
    ``link_id_dest_delta`` are the synthetic Link ID Number fields (see
    module docstring: no real main-map link exists to cross-reference in
    this prototype)."""
    link_id_origin: int
    link_id_dest_delta: int
    length_m: float
    connected_node: int         # node-table index of one end (10.10.2 item 16)
    road_class: int
    forward_passable: bool = True
    reverse_passable: bool = True
    has_avg_travel_time: bool = False


@dataclass
class RpGraph:
    """A single, standalone routing-graph region: everything needed to
    encode one Ch.9 Region Management Record + its Ch.10 Route Planning
    Data Frame."""
    lat_top: float
    lat_bottom: float
    lon_left: float
    lon_right: float
    nodes: list[RpNode] = field(default_factory=list)
    link_costs: list[RpLinkCost] = field(default_factory=list)
    region_no: int = 0


# ==========================================================================
# Chapter 9 -- Region Data Management Frame
# ==========================================================================

def write_level_mgmt_record(
    level: int, n_basic_rp_frames: int, n_ext_rp_frames: int, n_regions: int,
    region_rec_size: int, node_rec_size: int, link_rec_size: int,
    link_cost_rec_size: int, between_links_restriction_rec_size: int,
    between_links_cost_rec_size: int,
) -> bytes:
    """One 16-byte Ch.9.1.1 Level Management Record (no expansion field)."""
    lvl6 = level & 0x3F if level >= 0 else (level + 64) & 0x3F
    code = (lvl6 << 10) | ((n_basic_rp_frames & 0xF) << 4) | (n_ext_rp_frames & 0xF)
    out = bytearray()
    out += _u16(code)
    out += _u16(n_regions)
    out += _u16(sws_enc(region_rec_size))
    out += _u16(sws_enc(node_rec_size))
    out += _u16(sws_enc(link_rec_size))
    out += _u16(sws_enc(link_cost_rec_size))
    out += _u16(sws_enc(between_links_restriction_rec_size))
    out += _u16(sws_enc(between_links_cost_rec_size))
    assert len(out) == 16
    return bytes(out)


def write_region_mgmt_record(
    lat_top: float, lat_bottom: float, lon_left: float, lon_right: float,
    parent_region: int, first_child_region: int, n_child_regions: int,
    rp_dsa: int, rp_size_ls: int,
) -> bytes:
    """One 24-byte Ch.9.2.1 Region Management Record, type code 0 (DSA+BS)."""
    out = bytearray()
    out += geo_enc(lat_top)
    out += geo_enc(lat_bottom)
    out += geo_enc(lon_left)
    out += geo_enc(lon_right)
    out += _u16(parent_region)
    out += _u16(first_child_region)
    out += _u16(n_child_regions)
    out += _u32(rp_dsa)
    out += _u16(rp_size_ls)
    assert len(out) == 24
    return bytes(out)


def write_dummy_region_record() -> bytes:
    """A 24-byte dummy region record (all-0xFF, per the decoder's own
    ``dummy = b[0:12] == b'\\xff'*12`` recognition rule)."""
    return b"\xff" * 24


def write_region_frame_header(
    n_region_records: int, n_levels: int, level_rec_size: int,
    levels_bytes: bytes, rmt_size_ls: int,
) -> bytes:
    """The Ch.9.1 Region Data Management Distribution Header (50 fixed
    bytes) followed by the level management records. The Region
    Management Table itself (the region records) is a separate buffer in
    this prototype (this writer never resolves real DSAs), so
    ``rmt_dsa``/``ctc_*`` are written as spec-legal "no entity" values --
    honest here since this module doesn't place data on a real medium.
    """
    header = bytearray([POISON]) * 50
    _put(header, 0, _u16(sws_enc(50 + len(levels_bytes))))
    _put(header, 2, _u16(0))                       # region rec type code 0 (DSA+BS)
    _put(header, 4, _u32(n_region_records))
    _put(header, 8, _u32(NO_DATA_DSA))              # RMT address: not on a real medium here
    _put(header, 12, _u16(rmt_size_ls))
    _put(header, 14, _text("", 12))
    _put(header, 26, _u32(NO_DATA_DSA))             # Common Traffic Condition Table: absent
    _put(header, 30, _u16(0))
    _put(header, 32, _text("", 12))
    _put(header, 44, _u16(sws_enc(0)))
    _put(header, 46, _u8(n_levels))
    _put(header, 47, _u8(0))
    _put(header, 48, _u16(sws_enc(level_rec_size)))
    return bytes(header) + levels_bytes


def write_region_frame(graph: RpGraph, rp_size_ls: int, level: int = 2) -> tuple[bytes, bytes]:
    """Build the full Ch.9 header+level-table buffer and the Ch.9 Region
    Management Table buffer for a single standalone test region, preceded
    by one dummy root record (matching the real disc's own convention of
    always placing the dummy level first -- see 9.1's introductory note).

    Returns ``(header_and_levels, region_table)``.
    """
    dummy_level = write_level_mgmt_record(
        level=-32, n_basic_rp_frames=0, n_ext_rp_frames=0, n_regions=1,
        region_rec_size=24, node_rec_size=0, link_rec_size=0,
        link_cost_rec_size=0, between_links_restriction_rec_size=0,
        between_links_cost_rec_size=0,
    )
    real_level = write_level_mgmt_record(
        level=level, n_basic_rp_frames=9, n_ext_rp_frames=6, n_regions=1,
        region_rec_size=24, node_rec_size=6, link_rec_size=6,
        link_cost_rec_size=14, between_links_restriction_rec_size=2,
        between_links_cost_rec_size=4,
    )
    levels_bytes = dummy_level + real_level

    region_table = write_dummy_region_record() + write_region_mgmt_record(
        lat_top=graph.lat_top, lat_bottom=graph.lat_bottom,
        lon_left=graph.lon_left, lon_right=graph.lon_right,
        parent_region=0xFFFF, first_child_region=0xFFFF, n_child_regions=0,
        rp_dsa=NO_DATA_DSA, rp_size_ls=rp_size_ls,
    )
    header = write_region_frame_header(
        n_region_records=2, n_levels=2, level_rec_size=16,
        levels_bytes=levels_bytes, rmt_size_ls=len(region_table) // 32 or 1,
    )
    return header, region_table


# ==========================================================================
# Chapter 10 -- Route Planning Data Frame
# ==========================================================================

def write_node_record(
    is_boundary: bool, uppermost_identical_level: int, is_aggregated: bool,
    n_link_records: int, is_parcel_boundary: bool, has_traffic_light: bool,
    is_rotary: bool, link_record_offset: int, n_regulations: int,
    n_between_links_cost: int,
) -> bytes:
    """One 6-byte Ch.10.6.2.1 Node Record (no expansion field)."""
    if n_link_records > 14:
        raise ValueError("at most 14 link records can be represented (15 == undecided)")
    attr = 0
    attr |= (uppermost_identical_level & 0x7) << 27
    if is_aggregated:
        attr |= 1 << 26
    if is_boundary:
        attr |= 1 << 25
    attr |= (n_link_records & 0xF) << 21
    if is_parcel_boundary:
        attr |= 1 << 20
    if has_traffic_light:
        attr |= 1 << 19
    if is_rotary:
        attr |= 1 << 18
    attr |= link_record_offset & 0x3FFFF
    out = _u32(attr)
    out += _u16(((n_regulations & 0xFF) << 8) | (n_between_links_cost & 0xFF))
    assert len(out) == 6
    return out


def write_link_record(
    adjacent_node: int, link_cost_index: int, is_suburb: bool,
    is_semi_urban_highway: bool, is_reverse_direction: bool,
    following_same_road: int | None, angle_deg: int,
    region_number: int | None = None,
) -> bytes:
    """One Ch.10.7.1.1 Link Record: 6 bytes, +2 more if ``region_number``
    is given (i.e. the owning node is a boundary node -- item (8))."""
    if adjacent_node > 0x1FFF:
        raise ValueError("adjacent node id must fit in 13 bits (0..8191)")
    if link_cost_index > 0x7FFF:
        raise ValueError("link cost record number must fit in 15 bits")
    if not 0 <= angle_deg <= 359:
        raise ValueError("angle must be 0..359")
    out = _u16(adjacent_node & 0x1FFF)
    out += _u16(link_cost_index & 0x7FFF)
    fsr = (1 if is_suburb else 0) << 15
    fsr |= (1 if is_semi_urban_highway else 0) << 14
    fsr |= (1 if is_reverse_direction else 0) << 13
    fsr |= (0xF if following_same_road is None else following_same_road & 0xF) << 9
    fsr |= angle_deg & 0x1FF
    out += _u16(fsr)
    if region_number is not None:
        out += _u16(region_number)
    return out


def write_regulation_record(entry_link_no: int | None, exit_link_no: int | None,
                              is_between_links: bool, passage_code: int) -> bytes:
    """One 2-byte Ch.10.7.1.2 Regulation Record. ``None`` == the reserved
    "all entry/exit links" code 0xF."""
    if not 0 <= passage_code <= 0x7F:
        raise ValueError("passage code must fit in 7 bits")
    b0 = ((0xF if entry_link_no is None else entry_link_no & 0xF) << 4) | \
         (0xF if exit_link_no is None else exit_link_no & 0xF)
    b1 = ((1 if is_between_links else 0) << 7) | passage_code
    return bytes((b0, b1))


def write_between_links_cost_record(
    entry_link_no: int | None, exit_link_no: int | None,
    n_non_following_nodes: int, is_aggregated_intersection: bool,
    length_m: float, avg_travel_time_s: float | None,
) -> bytes:
    """One 4-byte Ch.10.7.1.3 Between-links Cost Record (no expansion
    field)."""
    b0 = ((0xF if entry_link_no is None else entry_link_no & 0xF) << 4) | \
         (0xF if exit_link_no is None else exit_link_no & 0xF)
    len_units, len_mult = _quantize_length(length_m, max_units=0xFE)
    t_units, t_mult = _quantize_time(avg_travel_time_s, max_units=0xFD) \
        if avg_travel_time_s is not None else (0xFE, 0)
    b1 = ((n_non_following_nodes & 0x3) << 5) | \
         ((1 if is_aggregated_intersection else 0) << 4) | \
         ((len_mult & 0x3) << 2) | (t_mult & 0x3)
    return bytes((b0, b1, len_units, t_units))


def _quantize_length(length_m: float, max_units: int) -> tuple[int, int]:
    """4^n metres/unit encoding shared by 10.7.1.3 and 10.10.2: pick the
    smallest multiplication constant n such that the rounded length fits
    in ``max_units`` (0xFF/0xFFF sentinels are reserved, so callers pass
    one less)."""
    n = 0
    while True:
        unit = 4 ** n
        units = int(round(length_m / unit))
        if units <= max_units:
            return units, n
        n += 1
        if n > 3:
            return max_units, 3  # clamp; should not happen for realistic road lengths


def _quantize_time(seconds: float, max_units: int) -> tuple[int, int]:
    n = 0
    while True:
        unit = (4 ** n) * 0.1
        units = int(round(seconds / unit))
        if units <= max_units:
            return units, n
        n += 1
        if n > 3:
            return max_units, 3


def write_link_cost_header(n_with_avg_time: int, n_without_avg_time: int) -> bytes:
    out = _u16(sws_enc(6))
    out += _u16(n_with_avg_time)
    out += _u16(n_without_avg_time)
    assert len(out) == 6
    return out


def write_link_cost_record(
    link_id_origin: int, link_id_dest_delta: int,
    uppermost_identical_link_level: int, link_passage_status: int,
    is_toll: bool, is_bypass: bool, n_traffic_lights: int,
    forward_passable: bool, reverse_passable: bool, has_center_line: bool,
    crossable_oncoming_lane: bool, same_cost_both_directions: bool,
    has_statistics_cost: bool, n_lanes_width_code: int, link_class_code: int,
    road_class_code: int, length_m: float, connected_node: int,
    avg_travel_time_s: float | None,
) -> bytes:
    """One Ch.10.10.2 Link Cost Record: a 14-byte fixed part (Link ID
    Number, the two flag/status words, Link Length, Connected Node ID)
    PLUS a 2-byte Average Travelling Time word that is only present when
    ``avg_travel_time_s`` is not None -- confirmed empirically against
    the real disc: region 178's own rank has ``avg_travel_time=False``
    and its link_cost subframe size (2162 B) divides EXACTLY into a
    6-byte header + 154 * 14-byte records with no remainder, only under
    a 14-byte (no avg-time-word) record size, whereas the spec's own
    Link Cost Record field table (10.10.2) lists all 6 items (including
    Average Travelling Time) as classification "a" (mandatory) summing
    to 16 bytes -- so despite that classification, the avg-time word must
    in practice be governed by the rank's ``avg_travel_time`` flag,
    consistent with Condition 1 of 10.10.2's ordering rules ("The link
    cost record which contains the average travelling time must come
    earlier in the storing order" -- which only makes sense as a
    variable-length distinction, not a constant-size field). This is a
    genuine spec-vs-disc discrepancy this prototype had to resolve
    empirically; flagged in the final report."""
    out = _u32(link_id_origin)
    out += _u16(link_id_dest_delta)
    w = ((uppermost_identical_link_level & 0x7) << 13) | \
        ((link_passage_status & 0x3) << 11) | \
        ((1 if is_toll else 0) << 10) | ((1 if is_bypass else 0) << 9) | \
        (n_traffic_lights & 0x1FF)
    out += _u16(w)
    attr = ((1 if forward_passable else 0) << 15) | \
           ((1 if reverse_passable else 0) << 14) | \
           ((1 if has_center_line else 0) << 13) | \
           ((1 if crossable_oncoming_lane else 0) << 12) | \
           ((1 if same_cost_both_directions else 0) << 11) | \
           ((1 if has_statistics_cost else 0) << 10) | \
           ((n_lanes_width_code & 0x7) << 7) | \
           ((link_class_code & 0x7) << 4) | (road_class_code & 0xF)
    out += _u16(attr)
    len_units, len_mult = _quantize_length(length_m, max_units=0xFFD)
    out += _u16((len_mult & 0x7) << 12 | (len_units & 0xFFF))
    out += _u16(connected_node)
    assert len(out) == 14
    if avg_travel_time_s is not None:
        t_units, t_mult = _quantize_time(avg_travel_time_s, max_units=0xFFD)
        out += _u16((t_mult & 0x7) << 12 | (t_units & 0xFFF))
    return out


def write_link_cost_record_ext(road_status: int, speed_limit_code: int,
                                 sublink_type_code: int) -> bytes:
    """The 4-byte Ch.10.10.2.1 Link Cost Record Extended Area."""
    b0 = (road_status & 0x3) << 6
    b1 = (speed_limit_code & 0xF) << 4
    w = (sublink_type_code & 0x1F) << 11
    return bytes((b0, b1)) + _u16(w)


def write_node_coord_header(
    lat_width_deg: float, lon_width_deg: float, n_lat_grids: int, n_lon_grids: int,
    ref_grid_table_offset: int, ref_grid_table_size: int,
    node_coord_table_offset: int, node_coord_table_size: int,
) -> bytes:
    """The 18-byte Ch.10.12.1 Node Coordinate Distribution Header."""
    out = _u16(sws_enc(18))
    out += _u24(int(round(lat_width_deg * 3600 * 8)))
    out += _u24(int(round(lon_width_deg * 3600 * 8)))
    out += _u8(n_lat_grids) + _u8(n_lon_grids)
    out += _u16(d32_enc(ref_grid_table_offset))
    out += _u16(sws_enc(ref_grid_table_size))
    out += _u16(d32_enc(node_coord_table_offset))
    out += _u16(sws_enc(node_coord_table_size))
    assert len(out) == 18
    return out


def write_reference_grid_record(lowest_lat: float, leftmost_lon: float) -> bytes:
    """6-byte Ch.10.12.2.1 record."""
    return geo_enc(lowest_lat) + geo_enc(leftmost_lon)


def write_node_coord_record(grid_record_number: int, x: int, y: int) -> bytes:
    """4-byte Ch.10.12.3.1 record."""
    if not 0 <= x <= 4095 or not 0 <= y <= 4095:
        raise ValueError("normalized X/Y must be 0..4095")
    v = ((grid_record_number & 0xFF) << 24) | ((x & 0xFFF) << 12) | (y & 0xFFF)
    return _u32(v)


def write_road_reference_table(n_aggregated_nodes: int = 0) -> bytes:
    """Ch.10.13 Road Reference Table. This prototype does not implement
    "aggregated intersection" clustering (see module docstring), so this
    always writes the spec-legal empty case: a 2-byte count of 0 and no
    Aggregated Node Information records."""
    if n_aggregated_nodes:
        raise NotImplementedError(
            "aggregated-intersection encoding is not implemented in this "
            "prototype; pass n_aggregated_nodes=0"
        )
    return _u16(0)


def write_ext_frame_management_record(offset: int, size: int) -> bytes:
    return _u32(d32_enc(offset) if offset != NULL_OFFSET else NULL_OFFSET) + \
        _u16(sws_enc(size) if size else 0)


def write_ext_frame(user_id_12b: bytes, data_id_code: int, payload: bytes = b"") -> bytes:
    """One Ch.10.5.1 Extended Route Planning Data Frame. The payload's
    real semantics are vendor-proprietary and unknown (see module
    docstring) -- this writer emits the frame structurally (so nothing is
    silently omitted, per the project owner's instruction) with an empty,
    explicitly-placeholder payload by default."""
    if len(user_id_12b) != 12:
        raise ValueError("user id must be 12 bytes")
    return user_id_12b + _u32(data_id_code) + payload
