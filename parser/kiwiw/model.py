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


@dataclass
class RoadFrame:
    n_intersections: int
    n_display_classes: int
    n_additional_data: int
    route_planning_level: int
    links: list[RoadLink] = field(default_factory=list)


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


@dataclass
class BackgroundFrame:
    shapes: list[BackgroundShape] = field(default_factory=list)


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


@dataclass
class NameFrame:
    records: list[NameRecord] = field(default_factory=list)


@dataclass
class Parcel:
    location: MeshLocation
    road: Optional[RoadFrame] = None
    background: Optional[BackgroundFrame] = None
    name: Optional[NameFrame] = None
