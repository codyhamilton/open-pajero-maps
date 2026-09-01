"""JSON-serializable dataclasses forming the parser's intermediate
representation (IR).

Every dataclass here is meant to be passed through `dataclasses.asdict()`
(see `to_jsonable` below) and dumped with `json.dumps`. Coordinates are
always decimal degrees (WGS84, per METADATA.KWI) unless noted otherwise.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Optional


def to_jsonable(obj):
    """Recursively convert dataclasses (and plain containers) to
    JSON-safe structures."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    return obj


@dataclass
class BoundingBox:
    lat_lo: float
    lat_hi: float
    lon_lo: float
    lon_hi: float


@dataclass
class VolumeHeader:
    """Ch. 5.1 Data Volume, decoded fields only (system-dependent
    manufacturer areas / reserved bytes are not further decoded)."""
    format_version: str
    data_version: str
    disk_title: str
    media_version: str
    system_specific_id: str
    data_author_id: str
    system_id: str
    contents_main_map: bool
    contents_route_planning: bool
    contents_index_data: bool
    coverage: BoundingBox
    logical_sector_size: int
    sector_size: int
    background_in_map_is_sea: bool
    background_out_of_map_is_sea: bool


@dataclass
class LevelMgmtRecord:
    """Ch. 6.1.1 Level Management Record, one per zoom level."""
    level: int
    upper_level: int
    lower_level: int
    n_basic_map: int
    n_ext_map: int
    n_basic_route: int
    n_ext_route: int
    display_flags: list[int]
    n_blocksets_lat: int
    n_blocksets_lng: int
    n_blocks_lat: int
    n_blocks_lng: int
    # index 0 = normal parcels, 1..3 = pardiv1..3 (divided/integrated parcels)
    n_parcels_lat: list[int]
    n_parcels_lng: list[int]
    bsmr_offset: int
    node_record_size: int
    # Extended info (present when the LMR is large enough) -- number of
    # road/background/name sub-frames used at this level.
    n_road_frames: Optional[int] = None
    n_background_frames: Optional[int] = None
    n_name_frames: Optional[int] = None
    grid_nx: int = 0
    grid_ny: int = 0
    # The bytes after the 2-byte extended-info word are three u16 index
    # tables, one entry per road / background / name sub-frame declared by
    # the n_*_frames counts above (see docs/phases/02-roundtrip.md --
    # 42 + 2*(n_road+n_background+n_name) accounts for the LMR size
    # exactly on this disc). Empty when the LMR is too short to hold them.
    road_frame_table: list[int] = field(default_factory=list)
    background_frame_table: list[int] = field(default_factory=list)
    name_frame_table: list[int] = field(default_factory=list)
    # Any LMR bytes past what the fields above model, kept verbatim (hex)
    # so a writer can reproduce them without pretending to understand them.
    raw_tail_hex: str = ""


@dataclass
class BlockSetMgmtRecord:
    """Ch. 6.1.2 Block Set Management Record."""
    level: int
    blockset_index: int
    bmt_offset: int
    bmt_size: int


@dataclass
class MeshLocation:
    """Result of locating a coordinate in the block-set/block/parcel/
    subparcel mesh hierarchy for one level."""
    level: int
    parcel_type: int  # 0=normal,1..3=pardiv1..3 (divided/integrated parcel)
    blockset_index: int
    block_index: int
    parcel_index: int
    bounds: BoundingBox
    sector_addr: int
    size_logical_sectors: int


@dataclass
class RoadNode:
    x: int
    y: int
    lat: float
    lon: float
    oneway: int
    planned: int
    tunnel: bool
    bridge: bool


@dataclass
class RoadLink:
    """One 'multilink' record (7.2.2.1.1 MultiLink Header + shape data):
    a polyline of one or more links sharing the same attributes."""
    display_class: int
    road_type: int
    altitude_flag: bool
    route_type_guidance_flag: bool
    pseudo3d_updown: int
    route_planning_tag: bool
    link_id_flag: bool
    selected_link_flag: bool
    toll_flag: bool
    route_number_flag: bool
    infra_link_flag: bool
    link_id_number_flag: bool
    n_nodes: int
    nodes: list[RoadNode]
    # Full decoded shape polyline (every vertex, including the
    # intermediate delta-coded points between nodes), as (lat, lon) pairs
    # in the same order as encoded on disc.
    points: list[tuple[float, float]] = field(default_factory=list)
    # Round-trip support: the record's absolute byte offset within the road
    # sub-frame buffer, and its exact bytes verbatim (multilink management
    # header + node/shape data + the additional/altitude/passage-regulation
    # info that `road.py` computes the size of but never decodes -- see
    # docs/phases/02-roundtrip.md). The writer emits `raw_bytes` at
    # `raw_offset` unchanged; the decoded fields above are for
    # readability/cross-validation only, not used to reconstruct bytes.
    raw_offset: int = 0
    raw_bytes: bytes = b""
    # IR-only metadata (NOT encoded into KWI bytes): positional index of this
    # link within its parcel's RoadFrame link list (0-based), and the OSM way
    # ID that this link was derived from (join key to the RP layer).  Both
    # default to safe non-values so existing round-trip tests (which build
    # RoadLinks from real disc data that carries no OSM provenance) are
    # unaffected.
    link_id: int = 0
    osm_way_id: Optional[int] = None


@dataclass
class RoadFrame:
    n_intersections: int
    n_display_classes: int
    n_additional_data: int
    route_planning_level: int
    links: list[RoadLink] = field(default_factory=list)
    frame_size: int = 0  # total bytes of this Road Data Frame (== len(buf) at decode time)
    # Round-trip support (all verbatim/raw, written back unchanged):
    header_size_raw: int = 0   # u16 @0 -- unused by any known reader, incl. kiwiread.c
    lvl_field_raw: int = 0     # u16 @6 -- route_planning_level occupies bits 10:15 only
    # Display Class Management Records (7.2.1.1), one per display class, in
    # order: (raw offset word [D], raw count word [B:N]) exactly as stored.
    display_class_table: list[tuple[int, int]] = field(default_factory=list)
    # 2-byte "Display Flag" word that sits immediately before a display
    # class's first polyline (kiwiread.c's dumproad() reads and prints it
    # as `dispflag` but road.py never modeled it semantically); keyed by
    # display class index, only present when that class's offset isn't
    # the 0xFFFF sentinel. Captured verbatim so the writer can place it
    # back at the same (recomputed) offset.
    display_class_flags: dict[int, bytes] = field(default_factory=dict)
    # Additional Data Management Records (7.2.1, [m] entries): (raw offset
    # word [D], raw size word [SWS]). Their content's *semantics* aren't
    # decoded by road.py (see module docstring), but its raw bytes are
    # still captured verbatim here (keyed by table index) so the frame
    # round-trips byte-identically.
    additional_data_table: list[tuple[int, int]] = field(default_factory=list)
    additional_data_raw: dict[int, bytes] = field(default_factory=dict)


@dataclass
class BackgroundShape:
    """One Minimum Graphics Data Record (7.3.2.2.1)."""
    shape_class: int  # 0=point,1=line,2=polygon (kiwiread's `t[i]`)
    type_code: int
    type_label: str
    n_coords: int
    mult_const: int
    underground: bool
    pen_up: bool
    coords: list[tuple[float, float]]  # (lat, lon)
    # Round-trip support: absolute offset + verbatim bytes of the whole
    # Minimum Graphics Data Record, including the point-shape starting
    # coordinate (never decoded for shape_class 0) and the optional
    # trailing "name"/"auxdata" 2-byte fields background.py's rec_len
    # already strides past without reading. See RoadLink.raw_bytes for
    # the same rationale.
    raw_offset: int = 0
    raw_bytes: bytes = b""


@dataclass
class BackgroundElement:
    """One entry of the 7.3.1 Background Distribution Header: (raw [D]
    offset word, raw [SWS] size word) verbatim, plus -- when the offset is
    not the 0xFFFF "no element" sentinel -- the 7.3.2 Background Type Unit
    table found at that offset (raw `n` count word, and (boff, val) raw
    word pairs, one per background type)."""
    raw_offset_word: int
    raw_size_word: int
    n_raw: int = 0
    unit_table_raw: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class BackgroundFrame:
    shapes: list[BackgroundShape] = field(default_factory=list)
    header_size_raw: int = 0  # u16 @0 -- SWS-encoded distribution header size
    elements: list[BackgroundElement] = field(default_factory=list)
    frame_size: int = 0  # total bytes of this Background Data Frame (== len(buf) at decode time)


@dataclass
class NameRecord:
    """One Name Data Record (7.4.2.1), string_type-dependent."""
    string_type: int
    type_code: int
    type_label: str
    priority: int
    vertical: bool
    display_scale_flag: int
    text: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    angle_deg: Optional[float] = None
    # Round-trip support: absolute offset + verbatim bytes of the whole
    # Name Data Record, including the "Name Data Header" (`na`) word never
    # decoded by name.py (7.4.2.1.1, size-of-minimum-graphics-record +
    # extended-data-flag -- unused by kiwiread.c's traversal, so its
    # meaning was never modelled).
    raw_offset: int = 0
    raw_bytes: bytes = b""


@dataclass
class NameList:
    """One entry of the 7.4.1 Name Data Management Information table: (raw
    [D] offset word, raw count word) verbatim."""
    raw_offset_word: int
    raw_count_word: int


@dataclass
class NameFrame:
    records: list[NameRecord] = field(default_factory=list)
    header_size_raw: int = 0  # u16 @0 -- SWS-encoded distribution header size
    lists: list[NameList] = field(default_factory=list)
    frame_size: int = 0  # total bytes of this Name Data Frame (== len(buf) at decode time)


@dataclass
class MapFrameHeader:
    """7.1 Map Frame Header, 36 bytes. Only `llpid`/`llcode` have an
    established decode in this codebase (kiwiread.c's `showmap()` only
    ever uses those two fields plus `nregion`); `dipid`/`pmcode`/`dsflag`/
    `rlx`/`rly`/`geo_str`/`geo_dec`/`rg_addr`/`rg_size` have no
    spec-confirmed semantic model here. Per the COUNTRY.KWI round-trip
    lesson, the header is carried as `raw_bytes` (the writer's actual
    source of truth) with a few fields also decoded for readability /
    cross-validation."""
    raw_bytes: bytes  # 36 bytes, verbatim
    llpid_lat: float = 0.0
    llpid_lon: float = 0.0
    llcode_cx: int = 0
    llcode_cy: int = 0
    nregion: int = 0


@dataclass
class MapFrame:
    """7.1 Map Frame: header + region list + Main Map Data Frame Entry
    (mfde) table -- the structural directory pointing at the road/
    background/name sub-frames. `mfde_raw` entries are in on-disc order;
    by convention (kiwiread.c `showmap()`) index 0 is road, 1 is
    background, 2 is name.

    The table's real length is neither `n_basic_map` (always 3 on this
    disc, and kiwiread.c's `showmap()` never byte-swaps/reads past it) nor
    `n_basic_map + n_ext_map`: cross-checked on every real parcel tested
    (Melbourne, both Sydney points, Perth CBD), it consistently runs to
    exactly 20 entries, ending precisely where the road sub-frame's own
    content begins. `parcel.decode_parcel()` derives this length directly
    from the data (see its docstring) rather than trusting any LMR count.

    Since no sub-frame kind beyond road/background/name is decoded
    anywhere in this codebase, every entry at index >= 3 is preserved as a
    raw (offset, size) pair in `mfde_raw`; those whose offset lies inside
    this Map Frame's own buffer additionally get their raw content bytes
    captured verbatim in `ext_frame_raw[index]`, so a writer can reproduce
    them without understanding what they mean. Entries whose offset points
    far outside this buffer (observed to look like absolute disc sector
    addresses, plausibly route-guidance-related content -- a different
    layer's territory) are left as table-entry-only: there is nothing of
    theirs inside *this* buffer to capture."""
    header: MapFrameHeader
    region_list_raw: bytes = b""
    mfde_raw: list[tuple[int, int]] = field(default_factory=list)
    ext_frame_raw: dict[int, bytes] = field(default_factory=dict)
    # Trailing bytes beyond everything this Map Frame's own structure
    # reaches (see `decode_parcel()`'s docstring) -- observed on every
    # tested real parcel, plausibly mastering-artifact leftovers rather
    # than a structure this decoder is missing. Preserved verbatim.
    tail_raw: bytes = b""
    frame_size: int = 0  # total bytes of this parcel's Map Frame (== len(mapdata))


@dataclass
class Parcel:
    location: MeshLocation
    road: Optional[RoadFrame] = None
    background: Optional[BackgroundFrame] = None
    name: Optional[NameFrame] = None
    frame: Optional[MapFrame] = None


@dataclass
class ParcelMapInfoEntry:
    """One `mapinfo` slot (Ch. 6 Parcel Management Record, [DSA]+[BS]):
    either NO_DATA_DSA (empty), a leaf pointing at a real Map Frame
    elsewhere on disc (`size != 0`), or -- when `size == 0` and `dsa` is
    not the sentinel -- a [D]-encoded offset to a nested `ParcelMgmtRecord`
    (divided/integrated-parcel subdivision) within the *same* block buffer,
    captured recursively in `subrecord`."""
    dsa: int
    size: int
    subrecord: Optional["ParcelMgmtRecord"] = None


@dataclass
class ParcelMgmtRecord:
    """One Parcel Management Record within a Block's data (what a Block
    Management Table entry's `dsa` addresses, and what a subparcel slot's
    `dsa` recursively addresses within the same buffer): a `[type]` word
    (list-type + parcel-type) followed by a `gn_lat*gn_lng`-entry mapinfo
    array. `offset` is the byte offset within the owning block's buffer.

    `header_gap_raw` is the 2 bytes between the type word (offset+0..1)
    and the mapinfo array (offset+4..): neither `mesh.py`'s locate_parcel()
    nor kiwiread.c's own `showbmt()` ever reads them, but real disc data
    has non-zero content there, so it's carried verbatim rather than
    assumed to be padding.

    `tail_raw` is only ever set on the *root* record returned for a Block's
    buffer (every nested subrecord leaves it as `b""`): on real disc data a
    Block Management Table entry's declared `size` is consistently larger
    than the root record's own footprint plus everything its subrecord
    chain reaches (observed across every tested real block -- Melbourne,
    both Sydney points, and Perth -- the gap ranges from roughly 8.3 KB to
    12.5 KB). Nothing in `mesh.py`'s validated traversal, nor kiwiread.c,
    ever reads past that footprint, so this trailing region is genuinely
    unreachable through the documented addressing scheme -- almost
    certainly reserved/stale space from however the disc was mastered,
    not a further structure this decoder is missing. It's carried
    verbatim here (from the end of the deepest-covered byte onward to the
    end of the block buffer) rather than guessed at, per the COUNTRY.KWI
    lesson."""
    offset: int
    list_type: int   # bits 0:7 of the type word; kiwiread.c asserts this is always 0
    parcel_type: int  # bits 8:9: 0=normal, 1..3=pardiv1..3 (divided/integrated)
    header_gap_raw: bytes = b"\x00\x00"
    entries: list[ParcelMapInfoEntry] = field(default_factory=list)
    tail_raw: bytes = b""
