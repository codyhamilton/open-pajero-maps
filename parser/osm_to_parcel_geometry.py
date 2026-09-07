#!/usr/bin/env python3
"""OSM PBF → ALLDATA.KWI parcel geometry extractor.

Extracts road polylines, background polygons, and place names from an OSM PBF
file and tiles them into the reference disc's own parcel grid (via
``kiwiw.grid.ReferenceGrid`` -- see docs/design/target-disc.md, "Grid
contract": grid parameters are checked-in data derived once from the
reference disc; a build never reads the mounted reference). One pass over
the PBF feeds every requested level at once, streaming output to an
on-disk spool (``kiwiw.spool``) so memory stays bounded regardless of file
size; per-level content is read back with ``SpoolReader.iter_level``.

Usage::

    # Dry-run: print tile grid stats for every level, no extraction
    python3 parser/osm_to_parcel_geometry.py --dry-run

    # Full-Australia extraction, all seven levels, no bbox (full coverage)
    python3 parser/osm_to_parcel_geometry.py \\
        --pbf australia-260824.osm.pbf --spool output/spool

    # Perth-only fixture, for fast iteration
    python3 parser/osm_to_parcel_geometry.py --fixture perth --spool /tmp/spool

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
- Every level receives the same feature set; per-level *selection* (which
  ways appear at which level) is unit 14's -- the ``level_filter`` hook on
  ``extract_parcel_geometry`` is the seam it fills.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kiwiw.coordconv import latlon_to_xy, COORD_RANGE
from kiwiw.grid import ReferenceGrid
from kiwiw.model import (
    BackgroundShape,
    BoundingBox,
    NameRecord,
    RoadFrame,
    RoadLink,
    RoadNode,
)
from kiwiw.roadtypes import background_type_label
from kiwiw.spool import SpoolReader, SpoolWriter
from kiwiw import vocab

DEFAULT_PBF = str(
    Path(__file__).resolve().parent.parent / "australia-260824.osm.pbf"
)
DEFAULT_SPOOL_DIR = str(
    Path(__file__).resolve().parent.parent / "output" / "spool"
)
DEFAULT_LEVELS = [12, 10, 8, 6, 4, 2, 0]
PROGRESS_EVERY = 1_000_000

# Perth metro fixture bbox (lon_left, lat_bottom, lon_right, lat_top).
# Used only behind --fixture perth; never a default (docs/design/target-disc.md
# decision 2: regional subsets are fixtures behind explicit flags).
FIXTURE_BBOXES = {
    "perth": (115.5, -32.5, 116.5, -31.5),
}
# Alias kept for import compatibility with parser/build_alldata.py (unit
# 09/12's, not touched here); that script's own pipeline call still needs
# updating for the new extract_parcel_geometry signature regardless -- see
# this unit's report for the contradiction this surfaces.
DEFAULT_BBOX = FIXTURE_BBOXES["perth"]

# ---------------------------------------------------------------------------
# Road-type mappings (mirrors build_route_graph.py)
# ---------------------------------------------------------------------------

ROADS = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
    "unclassified", "residential", "living_street", "service", "track", "road", "busway",
}

# OSM highway=* → 4-bit road_type for RoadLink.road_type, and
# OSM highway=* → display_class, both per-level and data-driven
# (docs/design/target-disc.md, "Vocabulary is data, not code"; tables +
# rationale in parser/refdata/vocab/{road_type,display_class}.json and
# parser/refdata/vocab/README.md; loader in kiwiw/vocab.py). Coverage
# against the reference census is enforced by parser/tests/test_vocab.py.
_ROAD_TYPE_VOCAB = vocab.load("road_type")
_DISPLAY_CLASS_VOCAB = vocab.load("display_class")

# ---------------------------------------------------------------------------
# Background type-code mapping (OSM tags → disc type codes from roadtypes.py)
# ---------------------------------------------------------------------------

_BG_TYPE_VOCAB = vocab.load("bg_type")


def _osm_tags_to_bg_type(tags: dict, level: int = 0) -> Optional[int]:
    """Map an OSM tag dict to a background type_code for `level`, data-driven
    (parser/refdata/vocab/bg_type.json + README.md), or None if not mapped
    at this level. `level` defaults to 0 for callers that are not yet
    level-aware (docs/design/target-disc.md, "Vocabulary is data, not
    code")."""
    return _BG_TYPE_VOCAB.lookup(level, tags)


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

    @classmethod
    def from_reference(cls, level: int, target: Optional[BoundingBox] = None) -> "TileGrid":
        """Build the TileGrid for `level` from the checked-in reference grid
        (`kiwiw.grid.ReferenceGrid`; see docs/design/target-disc.md, "Grid
        contract" -- a build never reads the mounted reference disc).

        `target=None` means the full reference coverage box (E90..W142,
        crossing the antimeridian): the only grid a non-fixture run uses.
        """
        rg = ReferenceGrid.load()
        c = rg.coverage
        lg = rg.level(level)
        lat_lo = c["lat_lo"]
        lon_lo = c["lon_lo"]
        lat_span = c["lat_hi"] - c["lat_lo"]
        lon_span = _lon_span(c["lon_lo"], c["lon_hi"])
        if target is None:
            target = BoundingBox(
                lat_lo=lat_lo, lat_hi=lat_lo + lat_span,
                lon_lo=lon_lo, lon_hi=lon_lo + lon_span,
            )
        return cls(
            level=level,
            disc_lat_lo=lat_lo,
            disc_lon_lo=lon_lo,
            disc_lat_span=lat_span,
            disc_lon_span=lon_span,
            nx=lg.nx,
            ny=lg.ny,
            target=target,
        )


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


class _Chain(list):
    """A per-parcel sub-polyline chain: behaves exactly like a plain
    ``list[tuple[float, float]]`` of (lat, lon) points (same construction,
    indexing, ``len()``, iteration -- existing callers that treat a chain as
    a plain list are unaffected), plus one extra attribute: ``ordinal``, the
    0-based index of this chain in the order it was produced along the way's
    node sequence (see docs/design/target-disc.md, "Link identity": a link's
    on-disc identity is ``(osm_way_id, ordinal)``).
    """
    ordinal: int = 0


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
    disc coverage (None key) are not included.  Each returned chain is a
    ``_Chain`` (a `list` subclass) whose ``.ordinal`` attribute is the
    0-based index of that chain in the order it was produced along the
    way's node sequence -- the same chain order the on-disc link identity
    `(osm_way_id, ordinal)` (docs/design/target-disc.md, "Link identity")
    is keyed on. Chains dropped for lying outside disc coverage do not
    consume an ordinal.
    """
    if len(coords) < 2:
        if len(coords) == 1:
            par = assign_to_parcel(coords[0][0], coords[0][1], grid)
            if par is not None:
                chain = _Chain(coords)
                chain.ordinal = 0
                return {par: [chain]}
        return {}

    # Build the full split list
    all_segs: list[tuple] = []
    for i in range(len(coords) - 1):
        all_segs.extend(_split_segment(coords[i], coords[i + 1], grid))

    # Merge consecutive segments in the same parcel into polylines
    result: dict[tuple[int, int], list[list]] = defaultdict(list)
    if not all_segs:
        return {}

    next_ordinal = 0

    def _emit(par, chain_points: list) -> None:
        nonlocal next_ordinal
        if par is not None and len(chain_points) >= 2:
            chain = _Chain(chain_points)
            chain.ordinal = next_ordinal
            next_ordinal += 1
            result[par].append(chain)

    cur_par = all_segs[0][2]
    cur_chain: list[tuple] = [all_segs[0][0], all_segs[0][1]]

    for seg in all_segs[1:]:
        p_a, p_b, par = seg
        if par == cur_par:
            cur_chain.append(p_b)
        else:
            _emit(cur_par, cur_chain)
            cur_par = par
            cur_chain = [p_a, p_b]

    _emit(cur_par, cur_chain)

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
                    level: int,
                    tags: dict,
                    bounds: BoundingBox,
                    osm_way_id: Optional[int] = None,
                    ordinal: int = 0) -> Optional[RoadLink]:
    """Build a synthetic RoadLink for one parcel-clipped road sub-polyline, or
    None if `tags` has no road_type/display_class mapping at `level`
    (per-level vocab lookup; docs/design/target-disc.md, "Vocabulary is
    data, not code" -- a null vocab entry means "omit this feature at this
    level", not "guess a default").

    The chain is a list of (lat, lon) pairs already clipped to the parcel.
    Coordinate values outside [0, COORD_RANGE) are clamped.

    ``osm_way_id`` is the OSM way ID this polyline was derived from; it is
    stored as IR-only metadata (not encoded into KWI bytes) so that the RP
    layer can later look up the corresponding link's positional index in the
    parcel's RoadFrame via a ``LinkIdRegistry``.

    ``ordinal`` is this chain's 0-based position in the order
    ``split_polyline_by_parcel`` produced it along the way's node sequence
    (its ``_Chain.ordinal``); together with ``osm_way_id`` it is the link's
    on-disc identity (docs/design/target-disc.md, "Link identity").
    """
    road_type = _ROAD_TYPE_VOCAB.lookup(level, tags)
    display_class = _DISPLAY_CLASS_VOCAB.lookup(level, tags)
    if road_type is None or display_class is None:
        return None
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
        osm_way_id=osm_way_id,
        ordinal=ordinal,
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


# Default no-op level_filter: every level receives the same feature set.
# `level_filter(level, tags) -> bool` is the seam unit 14 fills with
# per-level selection matched to the reference census; do not invent a
# selection rule here.
LevelFilter = Callable[[int, dict], bool]


def _default_level_filter(level: int, tags: dict) -> bool:
    return True


class _GeomHandler:
    """pyosmium handler that tiles roads, background features, and names into
    every requested level's grid *as each way/node is read* and spools the
    result -- nothing is retained across the whole file, so memory stays
    bounded regardless of PBF size.
    """

    def __init__(self, grids: dict[int, "TileGrid"], spool: SpoolWriter,
                 level_filter: LevelFilter, progress_every: int = PROGRESS_EVERY):
        self.grids = grids
        self.spool = spool
        self.level_filter = level_filter
        self.progress_every = progress_every
        self.target_cells: dict[int, set] = {
            level: set(grid.target_cells()) for level, grid in grids.items()
        }
        self.n_ways = 0
        self.n_nodes = 0

    def apply(self, pbf_path: str) -> None:
        import osmium

        outer = self

        class Handler(osmium.SimpleHandler):
            def way(h_self, w):
                outer._handle_way(w)

            def node(h_self, n):
                outer._handle_node(n)

        h = Handler()
        h.apply_file(pbf_path, locations=True, idx="flex_mem")

    def _handle_node(self, n) -> None:
        self.n_nodes += 1
        if not n.location.valid():
            return
        tags = n.tags
        name = tags.get("name")
        if not name:
            return
        place = tags.get("place")
        if place not in ("suburb", "city", "town", "village", "locality"):
            return
        tags_dict = dict(tags)
        lat, lon = n.location.lat, n.location.lon
        type_code = 0x134 if place == "suburb" else 0x132
        for level, grid in self.grids.items():
            if not self.level_filter(level, tags_dict):
                continue
            par = assign_to_parcel(lat, lon, grid)
            if par is None or par not in self.target_cells[level]:
                continue
            ix, iy = par
            rec = _make_name_record(name, lat, lon, type_code=type_code)
            self.spool.add(level, ix, iy, names=[rec])

    def _handle_way(self, w) -> None:
        self.n_ways += 1
        if self.n_ways % self.progress_every == 0:
            print(f"  ... {self.n_ways} ways, {self.n_nodes} nodes processed",
                  flush=True)
        try:
            coords = [(nd.lat, nd.lon) for nd in w.nodes if nd.location.valid()]
        except Exception:
            return
        if len(coords) < 2:
            return

        tags = dict(w.tags)
        hw = tags.get("highway")
        is_road = hw in ROADS
        way_id = w.id
        name = tags.get("name")

        ring = None
        if not is_road and len(coords) >= 3:
            ring = list(coords)
            if ring[0] != ring[-1]:
                ring.append(ring[0])
        if not is_road and ring is None:
            # Not a road and not enough coords for a background ring: cannot
            # be emitted at any level.
            return

        for level, grid in self.grids.items():
            if not self.level_filter(level, tags):
                continue
            tcells = self.target_cells[level]

            if is_road:
                per_parcel = split_polyline_by_parcel(coords, grid)
                any_link = False
                for (ix, iy), chains in per_parcel.items():
                    if (ix, iy) not in tcells:
                        continue
                    bounds = parcel_bounds(ix, iy, grid)
                    links = [
                        link for link in (
                            _make_road_link(
                                chain, level, tags, bounds, osm_way_id=way_id,
                                ordinal=getattr(chain, "ordinal", 0),
                            )
                            for chain in chains if len(chain) >= 2
                        ) if link is not None
                    ]
                    if links:
                        self.spool.add(level, ix, iy, roads=links)
                        any_link = True
                if name and any_link:
                    clat, clon = _centroid(coords)
                    par = assign_to_parcel(clat, clon, grid)
                    if par is not None and par in tcells:
                        nix, niy = par
                        rec = _make_name_record(name, clat, clon, type_code=0x134)
                        self.spool.add(level, nix, niy, names=[rec])
                continue

            # Background way (ring is not None: checked above for every
            # non-road way, before the per-level loop).
            bg_type = _osm_tags_to_bg_type(tags, level)
            if bg_type is None:
                continue
            clat, clon = _centroid(ring)
            par = assign_to_parcel(clat, clon, grid)
            if par is None or par not in tcells:
                continue
            ix, iy = par
            bounds = parcel_bounds(ix, iy, grid)
            shape = _make_background_shape(ring, bg_type, bounds)
            self.spool.add(level, ix, iy, backgrounds=[shape])
            if name:
                rec = _make_name_record(name, clat, clon, type_code=bg_type)
                self.spool.add(level, ix, iy, names=[rec])


# ---------------------------------------------------------------------------
# Main extraction pipeline
# ---------------------------------------------------------------------------

ParcelKey = tuple[int, int, int]  # (level, ix, iy)
ParcelContent = dict  # {'roads': [...], 'backgrounds': [...], 'names': [...]}


def extract_parcel_geometry(
    pbf_path: str,
    grids: dict[int, "TileGrid"],
    spool: SpoolWriter,
    level_filter: Optional[LevelFilter] = None,
    verbose: bool = True,
    progress_every: int = PROGRESS_EVERY,
) -> SpoolWriter:
    """One streaming pass over `pbf_path` that tiles every way/node into
    every level in `grids` as it is read, spooling per-parcel content to
    `spool` (see `kiwiw.spool`).  Nothing from the PBF is retained beyond
    the current record and the small per-parcel flush buffers inside
    `spool`, so memory stays bounded regardless of file size.

    `level_filter(level, tags) -> bool` (default: every level, always True)
    is the seam unit 14 fills with per-level feature selection; here every
    level receives the same feature set.

    Returns `spool`, closed (its index files are finalized) so callers can
    immediately construct a `SpoolReader` over it.
    """
    if level_filter is None:
        level_filter = _default_level_filter

    handler = _GeomHandler(grids, spool, level_filter, progress_every=progress_every)
    if verbose:
        print(f"Streaming {pbf_path} ...", flush=True)
    handler.apply(pbf_path)
    if verbose:
        print(f"Done: {handler.n_ways} ways, {handler.n_nodes} nodes processed",
              flush=True)
    spool.close()
    return spool


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pbf", default=DEFAULT_PBF,
                    help="OSM PBF input file (default: %(default)s)")
    ap.add_argument("--levels", nargs="+", type=int, default=DEFAULT_LEVELS,
                    help="Map levels to extract (default: %(default)s)")
    ap.add_argument("--fixture", choices=sorted(FIXTURE_BBOXES), default=None,
                    help="Restrict extraction to a named dev fixture bbox "
                         "(e.g. 'perth'); omit for the full reference coverage box")
    ap.add_argument("--spool", default=DEFAULT_SPOOL_DIR,
                    help="Output spool directory (default: %(default)s)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print per-level grid stats and exit without extracting")
    args = ap.parse_args()

    target = None
    if args.fixture is not None:
        lon_l, lat_b, lon_r, lat_t = FIXTURE_BBOXES[args.fixture]
        target = BoundingBox(lat_lo=lat_b, lat_hi=lat_t, lon_lo=lon_l, lon_hi=lon_r)

    grids: dict[int, TileGrid] = {}
    for level in args.levels:
        grid = TileGrid.from_reference(level, target=target)
        grids[level] = grid
        cells = grid.target_cells()
        print(f"Level {level:>2}: grid {grid.nx}x{grid.ny} cells, "
              f"cell {grid.cell_lat:.6f}° lat x {grid.cell_lon:.6f}° lon, "
              f"{len(cells)} parcels in target", flush=True)

    if args.dry_run:
        print("\n(--dry-run: no extraction performed, no spool written)")
        return

    if not os.path.exists(args.pbf):
        print(f"ERROR: PBF not found: {args.pbf}", file=sys.stderr)
        sys.exit(1)

    print(f"\nExtracting geometry from {args.pbf} into spool {args.spool} ...",
          flush=True)
    writer = SpoolWriter(args.spool)
    extract_parcel_geometry(args.pbf, grids, writer, verbose=True)

    reader = SpoolReader(args.spool)
    print("\nExtraction complete:")
    for level in args.levels:
        st = reader.stats(level)
        print(f"  level {level:>2}: parcels={st['parcels']} roads={st['roads']} "
              f"backgrounds={st['backgrounds']} names={st['names']}")


if __name__ == "__main__":
    main()
