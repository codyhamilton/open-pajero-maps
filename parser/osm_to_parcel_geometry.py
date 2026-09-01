#!/usr/bin/env python3
"""OSM PBF → ALLDATA.KWI parcel geometry extractor.

Extracts road polylines, background polygons, and place names from an OSM PBF
file and tiles them into the same parcel grid used by the real ALLDATA.KWI
disc (grid parameters taken from the disc's LMR records).  The output is a
dict keyed by (level, cell_ix, cell_iy) → {roads, backgrounds, names} that
the parcel writer can consume.

Usage::

    # Dry-run: print tile grid stats, no output file
    python3 parser/osm_to_parcel_geometry.py --dry-run

    # Full extraction (requires OSM PBF)
    python3 parser/osm_to_parcel_geometry.py \\
        --pbf ~/workspace/open-pajero-maps/australia-260824.osm.pbf \\
        --level 8 \\
        --out /tmp/perth_parcel_geometry.pkl

Grid tiling strategy
--------------------
The real disc's LMR defines a world-spanning tile grid at each map level.
This script reads those LMR parameters (n_blocksets_lat/lng × n_blocks_lat/lng
× n_parcels_lat/lng) from the real ALLDATA.KWI to reproduce the *same* cell
size and layout, then restricts extraction to parcels that intersect a target
bounding box (default: Perth metro, roughly −32.5 to −31.5 lat, 115.5 to
116.5 lon).  All cell indices are global (relative to the full disc grid), not
local to the target bbox.

RoadLink / BackgroundShape / NameRecord construction
----------------------------------------------------
Objects built here have ``raw_bytes=b""`` (no disc data to copy verbatim).
The parcel writer's existing "replicate" mode requires ``raw_bytes``; a
future "encode-from-semantic" mode will feed these objects instead.  That
round-trip gap is tracked in docs/phases/03-osm-pipeline.md.

Coordinate representation
-------------------------
Parcel-local pixel coordinates are computed via
``coordconv.latlon_to_xy(lat, lon, bounds)`` which maps the parcel's
geographic bounding box onto a 0..32767 pixel grid (COORD_RANGE = 2^15).
RoadNode.x/y and BackgroundShape.coords store these pixel values; the
geographic lat/lon is also stored for readability.

KNOWN SIMPLIFICATIONS (deliberately flagged, not silently assumed away)
-----------------------------------------------------------------------
- Road connectivity flags (oneway, planned, tunnel, bridge) are set to safe
  zero defaults; a join against the routing graph is needed to populate them.
- lattr fields (altitude_flag, toll_flag, etc.) are all False/0 defaults.
- BackgroundShape road-type codes (0x210..0x218) are not populated; only
  natural/landuse/boundary features are extracted here.
- NameRecord.raw_bytes is b""; writing these into a real frame requires the
  new name-frame encoder (future).
- Multi-polygon OSM relations are handled as individual outer-ring ways only;
  holes are ignored (inner rings).
- Node/point features (natural=peak, amenity=*, etc.) are out of scope.
"""
from __future__ import annotations

import argparse
import math
import os
import pickle
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.coordconv import latlon_to_xy, COORD_RANGE
from kiwiw.model import (
    BackgroundShape,
    BoundingBox,
    NameRecord,
    RoadFrame,
    RoadLink,
    RoadNode,
)
from kiwiw.roadtypes import background_type_label

DEFAULT_ALLDATA = "/run/media/codyh/464210-8480/ALLDATA.KWI"
DEFAULT_PBF = str(
    Path.home() / "workspace" / "open-pajero-maps" / "australia-260824.osm.pbf"
)

# Perth metro target bbox (lon_left, lat_bottom, lon_right, lat_top)
DEFAULT_BBOX = (115.5, -32.5, 116.5, -31.5)
DEFAULT_LEVEL = 8

# ---------------------------------------------------------------------------
# Road-type mappings (mirrors build_route_graph.py)
# ---------------------------------------------------------------------------

ROADS = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
    "unclassified", "residential", "living_street", "service", "track", "road", "busway",
}

# OSM highway=* → 4-bit road_type for RoadLink.road_type
# (mirrors ROAD_CLASS from build_route_graph.py / Ch. 32.2 codes)
HIGHWAY_TO_ROAD_TYPE: dict[str, int] = {
    "motorway": 0, "motorway_link": 0,
    "trunk": 1, "trunk_link": 1,
    "primary": 2, "primary_link": 2,
    "secondary": 3, "secondary_link": 3,
    "tertiary": 3, "tertiary_link": 3,
    "unclassified": 4, "road": 4,
    "residential": 5,
    "living_street": 6,
    "service": 7, "track": 7, "busway": 7,
}

# OSM highway=* → display_class (0 = most prominent, higher = less)
HIGHWAY_TO_DISPLAY_CLASS: dict[str, int] = {
    "motorway": 0, "motorway_link": 0,
    "trunk": 0, "trunk_link": 0,
    "primary": 1, "primary_link": 1,
    "secondary": 1, "secondary_link": 1,
    "tertiary": 2, "tertiary_link": 2,
    "unclassified": 2, "road": 2,
    "residential": 2, "living_street": 2,
    "service": 3, "track": 3, "busway": 3,
}

# ---------------------------------------------------------------------------
# Background type-code mapping (OSM tags → disc type codes from roadtypes.py)
# ---------------------------------------------------------------------------

def _osm_tags_to_bg_type(tags: dict) -> Optional[int]:
    """Map an OSM tag dict to a background type_code, or None if not mapped."""
    natural = tags.get("natural")
    landuse = tags.get("landuse")
    boundary = tags.get("boundary")
    admin_level = tags.get("admin_level")
    leisure = tags.get("leisure")
    aeroway = tags.get("aeroway")

    if natural == "coastline":
        return 0x121  # water system (shore line, ocean, bay, sea, creek)
    if natural == "water":
        return 0x122  # water system (lake, marsh, pond)
    if natural in ("bay", "sea", "ocean"):
        return 0x121
    if natural in ("wetland",):
        return 0x122
    if natural in ("river", "stream"):
        return 0x123  # water system (river)
    if natural in ("wood", "scrub", "heath"):
        return 0x141  # green belt, park
    if landuse in ("reservoir",):
        return 0x122
    if landuse in ("grass", "meadow", "farmland", "forest"):
        return 0x141
    if leisure == "park":
        return 0x141
    if landuse == "industrial":
        return 0x142  # factory, factory site
    if landuse == "cemetery" or tags.get("amenity") == "grave_yard":
        return 0x408  # cemetery
    if aeroway == "aerodrome":
        return 0x280  # airport
    if landuse == "university" or tags.get("amenity") == "university":
        return 0x464  # university
    if tags.get("amenity") == "hospital":
        return 0x480  # hospital
    if tags.get("leisure") == "golf_course":
        return 0x6180  # golf course
    if boundary == "administrative":
        level = admin_level
        if level == "2":
            return 0x131  # country
        if level == "4":
            return 0x132  # state
        if level in ("6", "8"):
            return 0x134  # municipality
    return None


# ---------------------------------------------------------------------------
# TileGrid: wraps the disc LMR parameters for one map level
# ---------------------------------------------------------------------------

@dataclass
class TileGrid:
    """Tile grid matching the real disc's LMR at one map level.

    Cell (ix, iy) covers:
      lon: disc_lon_lo + ix * cell_lon  ..  disc_lon_lo + (ix+1) * cell_lon  (modulo anti-meridian)
      lat: disc_lat_lo + iy * cell_lat  ..  disc_lat_lo + (iy+1) * cell_lat

    Cell indices are global (relative to the full disc, not the target bbox).
    ``target`` is the subset bbox for extraction; only cells that intersect it
    are populated in the output dict.
    """
    level: int
    disc_lat_lo: float
    disc_lon_lo: float
    disc_lat_span: float   # always > 0
    disc_lon_span: float   # always > 0, may exceed 180 (anti-meridian crossing)
    nx: int                # total cell columns (longitude)
    ny: int                # total cell rows (latitude)
    target: BoundingBox    # subset bbox to extract

    @property
    def cell_lat(self) -> float:
        return self.disc_lat_span / self.ny

    @property
    def cell_lon(self) -> float:
        return self.disc_lon_span / self.nx

    def parcel_count_in_target(self) -> int:
        """Number of cells that intersect the target bbox."""
        cells = self._target_cell_range()
        if cells is None:
            return 0
        ix0, ix1, iy0, iy1 = cells
        return (ix1 - ix0 + 1) * (iy1 - iy0 + 1)

    def _target_cell_range(self):
        """Return (ix_lo, ix_hi, iy_lo, iy_hi) for cells intersecting target bbox.
        Returns None if target bbox doesn't overlap the disc coverage."""
        t = self.target
        # Latitude range.  Cell iy covers [iy*c, (iy+1)*c).  All cells that
        # intersect [dlat_lo, dlat_hi] are iy_lo..iy_hi where:
        #   iy_lo = floor(dlat_lo / c)
        #   iy_hi = ceil(dlat_hi / c) - 1   (largest iy where iy*c < dlat_hi)
        c = self.cell_lat
        dlat_lo = t.lat_lo - self.disc_lat_lo
        dlat_hi = t.lat_hi - self.disc_lat_lo
        iy_lo = max(0, int(dlat_lo / c))
        iy_hi = min(self.ny - 1, math.ceil(dlat_hi / c) - 1)
        if iy_lo > iy_hi:
            return None
        # Longitude range (anti-meridian safe).
        cl = self.cell_lon
        dlon_lo = _lon_delta(self.disc_lon_lo, t.lon_lo, self.disc_lon_span)
        dlon_hi = _lon_delta(self.disc_lon_lo, t.lon_hi, self.disc_lon_span)
        if dlon_hi < dlon_lo:
            # Target bbox crosses the 0-reference meridian of the disc; extend hi
            dlon_hi = dlon_lo + (t.lon_hi - t.lon_lo)
        ix_lo = max(0, int(dlon_lo / cl))
        ix_hi = min(self.nx - 1, math.ceil(dlon_hi / cl) - 1)
        if ix_lo > ix_hi:
            return None
        return ix_lo, ix_hi, iy_lo, iy_hi

    def target_cells(self) -> list[tuple[int, int]]:
        """List of (ix, iy) cell indices that intersect the target bbox."""
        r = self._target_cell_range()
        if r is None:
            return []
        ix0, ix1, iy0, iy1 = r
        return [(ix, iy) for iy in range(iy0, iy1 + 1) for ix in range(ix0, ix1 + 1)]


def _lon_span(lo: float, hi: float) -> float:
    span = hi - lo
    return span + 360.0 if span < 0 else span


def _lon_delta(disc_lon_lo: float, lon: float, lon_span: float) -> float:
    delta = lon - disc_lon_lo
    while delta < 0:
        delta += 360.0
    while delta > lon_span:
        delta -= 360.0
    return delta


def assign_to_parcel(lat: float, lon: float, grid: TileGrid) -> Optional[tuple[int, int]]:
    """Return the (ix, iy) cell index for (lat, lon), or None if outside disc coverage."""
    dlat = lat - grid.disc_lat_lo
    if dlat < 0 or dlat >= grid.disc_lat_span:
        return None
    dlon = _lon_delta(grid.disc_lon_lo, lon, grid.disc_lon_span)
    ix = int(dlon / grid.cell_lon)
    iy = int(dlat / grid.cell_lat)
    ix = max(0, min(grid.nx - 1, ix))
    iy = max(0, min(grid.ny - 1, iy))
    return ix, iy


def parcel_bounds(ix: int, iy: int, grid: TileGrid) -> BoundingBox:
    """Return the geographic bounding box for cell (ix, iy)."""
    lat_lo = grid.disc_lat_lo + iy * grid.cell_lat
    lat_hi = lat_lo + grid.cell_lat
    # Longitude: reconstruct from disc_lon_lo + ix * cell_lon (may wrap)
    lon_lo_raw = grid.disc_lon_lo + ix * grid.cell_lon
    lon_hi_raw = lon_lo_raw + grid.cell_lon
    # Normalise to [-180, 360) range for well-behaved callers
    def norm(v):
        while v > 360:
            v -= 360
        while v < -180:
            v += 360
        return v
    return BoundingBox(lat_lo=lat_lo, lat_hi=lat_hi,
                       lon_lo=norm(lon_lo_raw), lon_hi=norm(lon_hi_raw))


# ---------------------------------------------------------------------------
# Build TileGrid from real disc LMR
# ---------------------------------------------------------------------------

def build_tile_grid_from_lmr(alldata_path: str, level: int,
                              target_bbox: tuple) -> TileGrid:
    """Read ALLDATA.KWI, decode its PDMDH/LMR for `level`, and return a
    TileGrid matching the real disc's grid parameters.

    Parameters
    ----------
    alldata_path : path to ALLDATA.KWI
    level : map level (0, 2, 4, 6, 8)
    target_bbox : (lon_left, lat_bottom, lon_right, lat_top) tuple
    """
    from kiwiw import volume
    with open(alldata_path, "rb") as fh:
        raw_hdr = fh.read(volume.DATAVOL_SIZE)
        hdr = volume.parse_volume_header(raw_hdr)
        raw_mht = fh.read(volume.MHT_SIZE)
        mht = volume.parse_management_header_table(raw_mht)
        prdm = mht.entries[0]
        off = volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
        fh.seek(off)
        raw_pdmdh = fh.read(prdm.size * hdr.logical_sector_size)
    pdmdh = volume.parse_pdmdh(raw_pdmdh)

    lmr = next((l for l in pdmdh.levels if l.level == level), None)
    if lmr is None:
        raise ValueError(f"No LMR for level {level}; available: "
                         f"{[l.level for l in pdmdh.levels]}")

    lon_lo = pdmdh.coverage.lon_lo
    lat_lo = pdmdh.coverage.lat_lo
    lat_span = pdmdh.coverage.lat_hi - pdmdh.coverage.lat_lo
    lon_span = _lon_span(pdmdh.coverage.lon_lo, pdmdh.coverage.lon_hi)

    target = BoundingBox(lat_lo=target_bbox[1], lat_hi=target_bbox[3],
                         lon_lo=target_bbox[0], lon_hi=target_bbox[2])
    return TileGrid(
        level=level,
        disc_lat_lo=lat_lo,
        disc_lon_lo=lon_lo,
        disc_lat_span=lat_span,
        disc_lon_span=lon_span,
        nx=lmr.grid_nx,
        ny=lmr.grid_ny,
        target=target,
    )


# ---------------------------------------------------------------------------
# Road polyline clipping
# ---------------------------------------------------------------------------

def _split_segment(p1: tuple, p2: tuple, grid: TileGrid,
                   depth: int = 0) -> list[tuple]:
    """Recursively split a segment at parcel boundaries using binary search.

    Returns a list of (point_a, point_b, parcel_ix, parcel_iy) tuples where
    each sub-segment lies entirely within one parcel.  Parcels outside the
    disc coverage are represented as (None, None).
    """
    MAX_DEPTH = 18
    par1 = assign_to_parcel(p1[0], p1[1], grid)
    par2 = assign_to_parcel(p2[0], p2[1], grid)
    if par1 == par2 or depth >= MAX_DEPTH:
        # Both in same parcel (or max recursion): emit as one sub-segment
        return [(p1, p2, par1)]
    # Binary search: split at midpoint
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    return (_split_segment(p1, mid, grid, depth + 1)
            + _split_segment(mid, p2, grid, depth + 1))


def split_polyline_by_parcel(
    coords: list[tuple[float, float]],
    grid: TileGrid,
) -> dict[tuple[int, int], list[list[tuple[float, float]]]]:
    """Split a polyline into per-parcel sub-polylines.

    Parameters
    ----------
    coords : list of (lat, lon) points
    grid   : TileGrid defining parcel boundaries

    Returns
    -------
    dict mapping (ix, iy) → list of sub-polyline coord lists.  Each
    sub-polyline is contiguous within that parcel.  Segments outside the
    disc coverage (None key) are not included.
    """
    if len(coords) < 2:
        if len(coords) == 1:
            par = assign_to_parcel(coords[0][0], coords[0][1], grid)
            if par is not None:
                return {par: [list(coords)]}
        return {}

    # Build the full split list
    all_segs: list[tuple] = []
    for i in range(len(coords) - 1):
        all_segs.extend(_split_segment(coords[i], coords[i + 1], grid))

    # Merge consecutive segments in the same parcel into polylines
    result: dict[tuple[int, int], list[list]] = defaultdict(list)
    if not all_segs:
        return {}

    cur_par = all_segs[0][2]
    cur_chain: list[tuple] = [all_segs[0][0], all_segs[0][1]]

    for seg in all_segs[1:]:
        p_a, p_b, par = seg
        if par == cur_par:
            cur_chain.append(p_b)
        else:
            if cur_par is not None and len(cur_chain) >= 2:
                result[cur_par].append(cur_chain)
            cur_par = par
            cur_chain = [p_a, p_b]

    if cur_par is not None and len(cur_chain) >= 2:
        result[cur_par].append(cur_chain)

    return dict(result)


# ---------------------------------------------------------------------------
# Centroid / polygon utilities
# ---------------------------------------------------------------------------

def _centroid(coords: list[tuple[float, float]]) -> tuple[float, float]:
    """Compute arithmetic centroid of a coordinate list."""
    if not coords:
        return (0.0, 0.0)
    lat = sum(c[0] for c in coords) / len(coords)
    lon = sum(c[1] for c in coords) / len(coords)
    return lat, lon


def _latlon_in_bounds(lat: float, lon: float, bounds: BoundingBox) -> bool:
    return (bounds.lat_lo <= lat <= bounds.lat_hi
            and bounds.lon_lo <= lon <= bounds.lon_hi)


# ---------------------------------------------------------------------------
# RoadLink / BackgroundShape / NameRecord constructors
# ---------------------------------------------------------------------------

def _make_road_link(chain: list[tuple[float, float]],
                    highway: str,
                    bounds: BoundingBox) -> RoadLink:
    """Build a synthetic RoadLink for one parcel-clipped road sub-polyline.

    The chain is a list of (lat, lon) pairs already clipped to the parcel.
    Coordinate values outside [0, COORD_RANGE) are clamped.
    """
    road_type = HIGHWAY_TO_ROAD_TYPE.get(highway, 4)
    display_class = HIGHWAY_TO_DISPLAY_CLASS.get(highway, 2)
    limit = int(COORD_RANGE) - 1

    nodes = []
    for lat, lon in chain:
        xc, yc = latlon_to_xy(lat, lon, bounds)
        xc = max(0, min(limit, xc))
        yc = max(0, min(limit, yc))
        nodes.append(RoadNode(
            x=xc, y=yc, lat=lat, lon=lon,
            oneway=0, planned=0, tunnel=False, bridge=False,
        ))

    return RoadLink(
        display_class=display_class,
        road_type=road_type,
        altitude_flag=False,
        route_type_guidance_flag=False,
        pseudo3d_updown=0,
        route_planning_tag=False,
        link_id_flag=False,
        selected_link_flag=False,
        toll_flag=False,
        route_number_flag=False,
        infra_link_flag=False,
        link_id_number_flag=False,
        n_nodes=len(nodes),
        nodes=nodes,
        points=[(n.lat, n.lon) for n in nodes],
        raw_offset=0,
        raw_bytes=b"",   # no disc data -- synthetic link
    )


def _make_background_shape(ring: list[tuple[float, float]],
                            type_code: int,
                            bounds: BoundingBox) -> BackgroundShape:
    """Build a synthetic BackgroundShape for one polygon ring."""
    limit = int(COORD_RANGE) - 1
    px_coords = []
    for lat, lon in ring:
        xc, yc = latlon_to_xy(lat, lon, bounds)
        xc = max(0, min(limit, xc))
        yc = max(0, min(limit, yc))
        px_coords.append((lat, lon))  # keep as latlon; writer converts

    # shape_class: 2=polygon, 1=line
    shape_class = 2 if len(ring) >= 3 else 1
    return BackgroundShape(
        shape_class=shape_class,
        type_code=type_code,
        type_label=background_type_label(type_code),
        n_coords=max(0, len(ring) - 1),   # delta-coded points after first
        mult_const=1,
        underground=False,
        pen_up=False,
        coords=ring,
        raw_offset=0,
        raw_bytes=b"",   # synthetic
    )


def _make_name_record(text: str, lat: float, lon: float,
                      type_code: int = 0x134) -> NameRecord:
    """Build a synthetic NameRecord (string_type=1, Barycentric point label)."""
    return NameRecord(
        string_type=1,
        type_code=type_code,
        type_label=background_type_label(type_code),
        priority=5,
        vertical=False,
        display_scale_flag=0,
        text=text,
        lat=lat,
        lon=lon,
        angle_deg=None,
        raw_offset=0,
        raw_bytes=b"",   # synthetic
    )


# ---------------------------------------------------------------------------
# OSM extraction (pyosmium handler)
# ---------------------------------------------------------------------------

def _is_background_way(tags) -> bool:
    """Return True if this way/relation should be extracted as a background shape."""
    return (_osm_tags_to_bg_type(dict(tags)) is not None)


def _is_name_feature(tags) -> bool:
    place = tags.get("place")
    name = tags.get("name")
    return bool(name) and (place in ("suburb", "city", "town", "village", "locality")
                            or tags.get("highway") in ROADS)


class _GeomHandler:
    """pyosmium handler that collects roads, background features, and names.

    Call `apply(pbf_path)` to run the streaming parse.  Results are in:
      self.road_ways      list of {coords, highway}
      self.bg_ways        list of {ring, type_code}
      self.name_points    list of {text, lat, lon, type_code}
      self.name_ways      list of {text, coords, type_code}  (centroid used)
    """

    def __init__(self, target_bbox):
        self.target_bbox = target_bbox  # (lon_left, lat_bottom, lon_right, lat_top)
        self.road_ways: list[dict] = []
        self.bg_ways: list[dict] = []
        self.name_points: list[dict] = []
        self.name_ways: list[dict] = []

    def _in_bbox(self, lats, lons) -> bool:
        lon_l, lat_b, lon_r, lat_t = self.target_bbox
        return (max(lons) >= lon_l and min(lons) <= lon_r
                and max(lats) >= lat_b and min(lats) <= lat_t)

    def apply(self, pbf_path: str) -> None:
        import osmium

        class Handler(osmium.SimpleHandler):
            def __init__(h_self):
                osmium.SimpleHandler.__init__(h_self)

            def way(h_self, w):
                self._handle_way(w)

            def node(h_self, n):
                self._handle_node(n)

        h = Handler()
        h.apply_file(pbf_path, locations=True, idx="flex_mem")

    def _handle_node(self, n) -> None:
        if not n.location.valid():
            return
        lat, lon = n.location.lat, n.location.lon
        lon_l, lat_b, lon_r, lat_t = self.target_bbox
        if not (lat_b <= lat <= lat_t and lon_l <= lon <= lon_r):
            return
        tags = n.tags
        name = tags.get("name")
        if not name:
            return
        place = tags.get("place")
        if place in ("suburb", "city", "town", "village", "locality"):
            type_code = 0x134 if place in ("suburb",) else 0x132
            self.name_points.append({"text": name, "lat": lat, "lon": lon,
                                     "type_code": type_code})

    def _handle_way(self, w) -> None:
        try:
            coords = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        except Exception:
            return
        if len(coords) < 2:
            return
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        if not self._in_bbox(lats, lons):
            return

        tags = w.tags
        hw = tags.get("highway")
        if hw in ROADS:
            self.road_ways.append({"coords": coords, "highway": hw})
            name = tags.get("name")
            if name:
                clat, clon = _centroid(coords)
                self.name_ways.append({"text": name, "lat": clat, "lon": clon,
                                       "type_code": 0x134})
            return

        type_code = _osm_tags_to_bg_type(dict(tags))
        if type_code is not None and len(coords) >= 3:
            # Close the ring if not already closed
            ring = list(coords)
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            self.bg_ways.append({"ring": ring, "type_code": type_code})
            name = tags.get("name")
            if name:
                clat, clon = _centroid(ring)
                self.name_ways.append({"text": name, "lat": clat, "lon": clon,
                                       "type_code": type_code})


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

ParcelKey = tuple[int, int, int]  # (level, ix, iy)
ParcelContent = dict  # {'roads': [...], 'backgrounds': [...], 'names': [...]}


def extract_parcel_geometry(
    pbf_path: str,
    grid: TileGrid,
    verbose: bool = False,
) -> dict[ParcelKey, ParcelContent]:
    """Extract OSM geometry and tile it into parcels.

    Returns
    -------
    dict mapping (level, cell_ix, cell_iy) → {
        'roads':       list[RoadLink],
        'backgrounds': list[BackgroundShape],
        'names':       list[NameRecord],
    }
    Only parcels that intersect ``grid.target`` and have at least one feature
    are included.
    """
    target_cells = set(grid.target_cells())

    handler = _GeomHandler(target_bbox=(
        grid.target.lon_lo, grid.target.lat_lo,
        grid.target.lon_hi, grid.target.lat_hi,
    ))
    if verbose:
        print(f"  Streaming {pbf_path} ...", flush=True)
    handler.apply(pbf_path)
    if verbose:
        print(f"  Collected {len(handler.road_ways)} road ways, "
              f"{len(handler.bg_ways)} background ways, "
              f"{len(handler.name_points) + len(handler.name_ways)} name features",
              flush=True)

    result: dict[ParcelKey, ParcelContent] = defaultdict(
        lambda: {"roads": [], "backgrounds": [], "names": []}
    )

    # --- Roads ---
    for way in handler.road_ways:
        coords = way["coords"]
        hw = way["highway"]
        per_parcel = split_polyline_by_parcel(coords, grid)
        for (ix, iy), chains in per_parcel.items():
            if (ix, iy) not in target_cells:
                continue
            bounds = parcel_bounds(ix, iy, grid)
            for chain in chains:
                if len(chain) >= 2:
                    link = _make_road_link(chain, hw, bounds)
                    result[(grid.level, ix, iy)]["roads"].append(link)

    # --- Backgrounds ---
    for bg in handler.bg_ways:
        ring = bg["ring"]
        type_code = bg["type_code"]
        # Assign background to parcel of its centroid (no clipping for polygons)
        clat, clon = _centroid(ring)
        par = assign_to_parcel(clat, clon, grid)
        if par is None or par not in target_cells:
            continue
        ix, iy = par
        bounds = parcel_bounds(ix, iy, grid)
        shape = _make_background_shape(ring, type_code, bounds)
        result[(grid.level, ix, iy)]["backgrounds"].append(shape)

    # --- Names (point nodes) ---
    for np_ in handler.name_points:
        par = assign_to_parcel(np_["lat"], np_["lon"], grid)
        if par is None or par not in target_cells:
            continue
        ix, iy = par
        rec = _make_name_record(np_["text"], np_["lat"], np_["lon"],
                                 type_code=np_["type_code"])
        result[(grid.level, ix, iy)]["names"].append(rec)

    # --- Names (from road/bg way centroids) ---
    for nw in handler.name_ways:
        par = assign_to_parcel(nw["lat"], nw["lon"], grid)
        if par is None or par not in target_cells:
            continue
        ix, iy = par
        rec = _make_name_record(nw["text"], nw["lat"], nw["lon"],
                                 type_code=nw["type_code"])
        result[(grid.level, ix, iy)]["names"].append(rec)

    return dict(result)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alldata", default=DEFAULT_ALLDATA,
                    help="Path to ALLDATA.KWI (disc file, default: %(default)s)")
    ap.add_argument("--pbf", default=DEFAULT_PBF,
                    help="OSM PBF input file (default: %(default)s)")
    ap.add_argument("--level", type=int, default=DEFAULT_LEVEL,
                    help="Map level to extract (default: %(default)s)")
    ap.add_argument("--bbox", nargs=4, type=float,
                    metavar=("LON_LEFT", "LAT_BOTTOM", "LON_RIGHT", "LAT_TOP"),
                    default=list(DEFAULT_BBOX),
                    help="Target bbox (default: Perth metro)")
    ap.add_argument("--out", default=None,
                    help="Output pickle path (omit for dry-run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print stats and exit without writing output")
    args = ap.parse_args()

    bbox = tuple(args.bbox)

    # --- Build tile grid ---
    if not os.path.exists(args.alldata):
        print(f"SKIP: {args.alldata} not found (disc not mounted?)", file=sys.stderr)
        sys.exit(1)

    print(f"Loading LMR from {args.alldata} for level {args.level} …")
    grid = build_tile_grid_from_lmr(args.alldata, args.level, bbox)

    print(f"\nTile grid (level {grid.level}):")
    print(f"  Disc coverage:  lat [{grid.disc_lat_lo:.4f}, "
          f"{grid.disc_lat_lo + grid.disc_lat_span:.4f}], "
          f"lon_lo={grid.disc_lon_lo:.4f}, lon_span={grid.disc_lon_span:.4f}")
    print(f"  Grid:           {grid.nx} × {grid.ny} cells globally")
    print(f"  Cell size:      {grid.cell_lat:.6f}° lat × {grid.cell_lon:.6f}° lon")
    print(f"  Target bbox:    lat [{grid.target.lat_lo}, {grid.target.lat_hi}], "
          f"lon [{grid.target.lon_lo}, {grid.target.lon_hi}]")
    cells = grid.target_cells()
    print(f"  Parcels in target: {len(cells)}")

    # Sample parcel info
    if cells:
        ix0, iy0 = cells[0]
        b0 = parcel_bounds(ix0, iy0, grid)
        print(f"\n  Sample parcel ({ix0}, {iy0}): "
              f"lat [{b0.lat_lo:.5f}, {b0.lat_hi:.5f}], "
              f"lon [{b0.lon_lo:.5f}, {b0.lon_hi:.5f}]")

    if args.dry_run:
        print("\n(--dry-run: no extraction performed, no output written)")
        return

    # --- Full extraction ---
    if not os.path.exists(args.pbf):
        print(f"ERROR: PBF not found: {args.pbf}", file=sys.stderr)
        sys.exit(1)

    print(f"\nExtracting geometry from {args.pbf} …")
    geometry = extract_parcel_geometry(args.pbf, grid, verbose=True)

    # Summary
    n_parcels = len(geometry)
    n_roads = sum(len(v["roads"]) for v in geometry.values())
    n_bgs = sum(len(v["backgrounds"]) for v in geometry.values())
    n_names = sum(len(v["names"]) for v in geometry.values())
    print(f"\nExtraction complete:")
    print(f"  Non-empty parcels: {n_parcels}")
    print(f"  Road links:        {n_roads}")
    print(f"  Background shapes: {n_bgs}")
    print(f"  Name records:      {n_names}")

    # Sample parcel detail
    if geometry:
        sample_key = next(iter(geometry))
        v = geometry[sample_key]
        print(f"\nSample parcel {sample_key}:")
        print(f"  roads={len(v['roads'])}, backgrounds={len(v['backgrounds'])}, "
              f"names={len(v['names'])}")

    if args.out:
        with open(args.out, "wb") as fh:
            pickle.dump(geometry, fh, protocol=4)
        print(f"\nOutput written to {args.out}")


if __name__ == "__main__":
    main()
