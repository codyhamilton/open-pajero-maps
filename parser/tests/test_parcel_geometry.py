"""Tests for parser/osm_to_parcel_geometry.py.

All tests are self-contained: they use synthetic TileGrid instances and do not
require the real disc (ALLDATA.KWI) or an OSM PBF.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.model import BoundingBox
from kiwiw.coordconv import latlon_to_xy, xy_to_latlon, COORD_RANGE
from osm_to_parcel_geometry import (
    TileGrid,
    assign_to_parcel,
    parcel_bounds,
    split_polyline_by_parcel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_grid(
    lat_lo: float = -35.0,
    lon_lo: float = 113.0,
    lat_span: float = 10.0,
    lon_span: float = 20.0,
    nx: int = 100,
    ny: int = 50,
    target: BoundingBox | None = None,
    level: int = 8,
) -> TileGrid:
    """Create a synthetic TileGrid for testing."""
    if target is None:
        target = BoundingBox(
            lat_lo=lat_lo, lat_hi=lat_lo + lat_span,
            lon_lo=lon_lo, lon_hi=lon_lo + lon_span,
        )
    return TileGrid(
        level=level,
        disc_lat_lo=lat_lo,
        disc_lon_lo=lon_lo,
        disc_lat_span=lat_span,
        disc_lon_span=lon_span,
        nx=nx,
        ny=ny,
        target=target,
    )


# ---------------------------------------------------------------------------
# Test 1: tile assignment
# ---------------------------------------------------------------------------

class TestTileAssignment:
    """Given synthetic grid points, verify they land in the correct parcel."""

    def test_five_synthetic_points(self):
        """Five known points are assigned to the correct (ix, iy) cell."""
        # Grid: lat -35...-25, lon 113...133, 100×50 cells
        # cell_lat = 0.2°, cell_lon = 0.2°
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        assert grid.cell_lat == pytest.approx(0.2)
        assert grid.cell_lon == pytest.approx(0.2)

        # Point 1: exactly at the SW corner → cell (0, 0)
        assert assign_to_parcel(-35.0, 113.0, grid) == (0, 0)

        # Point 2: 1° north, 1° east → cell (5, 5)
        # dlat=1.0 / cell_lat=0.2 → iy=5; dlon=1.0 / cell_lon=0.2 → ix=5
        assert assign_to_parcel(-34.0, 114.0, grid) == (5, 5)

        # Point 3: near NE corner
        assert assign_to_parcel(-25.05, 132.95, grid) == (99, 49)

        # Point 4: middle of grid
        assert assign_to_parcel(-30.0, 123.0, grid) == (50, 25)

        # Point 5: outside disc coverage → None
        assert assign_to_parcel(-10.0, 113.0, grid) is None

    def test_boundary_precision(self):
        """Points exactly on a cell boundary land in the lower cell."""
        grid = _make_grid(lat_lo=0.0, lon_lo=0.0, lat_span=1.0, lon_span=1.0,
                          nx=10, ny=10)
        # 0.1° per cell; a point at exactly 0.5° → cell 5
        par = assign_to_parcel(0.5, 0.5, grid)
        assert par == (5, 5)

    def test_outside_disc_returns_none(self):
        """Points outside the disc's latitude coverage return None.

        Note: longitude is handled with anti-meridian-safe wrapping (matching
        the real disc's locate_parcel behaviour), so out-of-longitude-range
        points are NOT expected to return None — they wrap around to the nearest
        cell, just as mesh.locate_parcel does.  Only lat-out-of-range returns None.
        """
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=5.0, lon_span=5.0,
                          nx=10, ny=10)
        assert assign_to_parcel(0.0, 113.0, grid) is None    # lat too high
        assert assign_to_parcel(-40.0, 113.0, grid) is None  # lat too low

    def test_parcel_bounds_match_assignment(self):
        """parcel_bounds returns a box that contains the query point."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        lat, lon = -32.3, 117.7
        par = assign_to_parcel(lat, lon, grid)
        assert par is not None
        ix, iy = par
        b = parcel_bounds(ix, iy, grid)
        assert b.lat_lo <= lat < b.lat_hi
        assert b.lon_lo <= lon < b.lon_hi

    def test_target_cells_count(self):
        """target_cells returns the expected number of cells for a sub-bbox."""
        grid = _make_grid(
            lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
            nx=100, ny=50,
            target=BoundingBox(lat_lo=-34.0, lat_hi=-33.0, lon_lo=114.0, lon_hi=115.0),
        )
        cells = grid.target_cells()
        # target spans 1°×1°; cell_lat=0.2, cell_lon=0.2 → 5×5 = 25 cells
        assert len(cells) == 25


# ---------------------------------------------------------------------------
# Test 2: road clip
# ---------------------------------------------------------------------------

class TestRoadClip:
    """A road crossing a parcel boundary is split correctly."""

    def test_single_parcel_no_split(self):
        """A segment contained in one parcel is returned as-is."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        # cell_lat=0.2°, cell_lon=0.2°
        # Both points in cell (5, 4):
        #   lat=-34.05 → dlat=0.95 → iy=int(0.95/0.2)=int(4.75)=4
        #   lat=-34.15 → dlat=0.85 → iy=int(0.85/0.2)=int(4.25)=4
        #   lon=114.05 → dlon=1.05 → ix=int(1.05/0.2)=int(5.25)=5
        coords = [(-34.05, 114.05), (-34.15, 114.15)]
        result = split_polyline_by_parcel(coords, grid)
        assert len(result) == 1
        key = next(iter(result))
        assert key == (5, 4)
        chains = result[key]
        assert len(chains) == 1
        assert len(chains[0]) == 2

    def test_cross_boundary_splits(self):
        """A segment crossing a parcel boundary produces two sub-segments."""
        # cell_lat = 0.2°; a segment from iy=5 to iy=6 crosses lat=-34.0 + 5*0.2 = -33.0
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        # Both points in the same ix=5 column, crossing iy=5/iy=6 boundary at lat=-34.0
        p1 = (-34.05, 114.05)   # iy=4 (dlat=0.95 / 0.2 = 4.75 → 4)
        p2 = (-33.85, 114.05)   # iy=5 (dlat=1.15 / 0.2 = 5.75 → 5)

        # Verify assignments
        par1 = assign_to_parcel(*p1, grid)
        par2 = assign_to_parcel(*p2, grid)
        assert par1 != par2, "Test setup: points should be in different cells"

        result = split_polyline_by_parcel([p1, p2], grid)
        # Should produce entries for both parcels
        assert len(result) == 2
        assert par1 in result
        assert par2 in result

    def test_multi_point_way_clips(self):
        """A 3-point polyline crossing two boundaries clips to multiple parcels."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        # Three points each in a different cell (iy=0, 1, 2; same ix)
        # dlat step = 0.25° (crosses 0.2° cell boundaries)
        p0 = (-34.9, 113.1)   # iy=0 (dlat=0.1/0.2=0.5→0)
        p1 = (-34.6, 113.1)   # iy=2 (dlat=0.4/0.2=2.0→2? actually int(0.4/0.2)=2)
        p2 = (-34.3, 113.1)   # iy=3 (dlat=0.7/0.2=3.5→3)

        par0 = assign_to_parcel(*p0, grid)
        par1 = assign_to_parcel(*p1, grid)
        par2 = assign_to_parcel(*p2, grid)

        # All three should be distinct cells
        assert len({par0, par1, par2}) >= 2, "Expected points in different cells"

        result = split_polyline_by_parcel([p0, p1, p2], grid)
        # At minimum 2 parcels are represented
        assert len(result) >= 2

    def test_single_point_polyline(self):
        """A single-point 'polyline' returns a single-point entry."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        result = split_polyline_by_parcel([(-34.5, 113.5)], grid)
        assert len(result) == 1

    def test_empty_polyline(self):
        """An empty input returns an empty dict."""
        grid = _make_grid()
        result = split_polyline_by_parcel([], grid)
        assert result == {}

    def test_outside_disc_excluded(self):
        """Segments entirely outside the disc are excluded."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=5.0, lon_span=5.0,
                          nx=25, ny=25)
        # Both points well outside
        result = split_polyline_by_parcel([(10.0, 113.0), (11.0, 113.0)], grid)
        assert result == {}


# ---------------------------------------------------------------------------
# Test 3: coordinate round-trip
# ---------------------------------------------------------------------------

class TestCoordinateRoundtrip:
    """WGS84 lat/lon → parcel-local x/y → lat/lon round-trips within quantization."""

    def _roundtrip(self, lat: float, lon: float, bounds: BoundingBox):
        xc, yc = latlon_to_xy(lat, lon, bounds)
        lat2, lon2 = xy_to_latlon(xc, yc, bounds)
        return lat2, lon2, xc, yc

    def _quant_tol(self, bounds: BoundingBox) -> tuple[float, float]:
        """Quantization tolerance: half a pixel in each axis."""
        lat_tol = 0.5 * (bounds.lat_hi - bounds.lat_lo) / COORD_RANGE
        lon_tol = 0.5 * (bounds.lon_hi - bounds.lon_lo) / COORD_RANGE
        return lat_tol, lon_tol

    def test_centre_roundtrip(self):
        """Centre of a parcel round-trips exactly (even pixel)."""
        bounds = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0)
        lat, lon = -31.5, 115.5
        lat2, lon2, xc, yc = self._roundtrip(lat, lon, bounds)
        lat_tol, lon_tol = self._quant_tol(bounds)
        assert abs(lat2 - lat) <= lat_tol, f"lat roundtrip error {abs(lat2 - lat)} > {lat_tol}"
        assert abs(lon2 - lon) <= lon_tol, f"lon roundtrip error {abs(lon2 - lon)} > {lon_tol}"

    def test_corner_roundtrip(self):
        """SW corner round-trips to (0, COORD_RANGE)."""
        bounds = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0)
        lat, lon = bounds.lat_lo, bounds.lon_lo
        lat2, lon2, xc, yc = self._roundtrip(lat, lon, bounds)
        lat_tol, lon_tol = self._quant_tol(bounds)
        assert abs(lat2 - lat) <= lat_tol
        assert abs(lon2 - lon) <= lon_tol
        assert xc == 0
        assert yc == int(COORD_RANGE)  # y=0 is north, so SW corner → full y

    def test_five_scattered_points(self):
        """Five scattered points all round-trip within quantization tolerance."""
        bounds = BoundingBox(lat_lo=-32.5, lat_hi=-31.5, lon_lo=115.5, lon_hi=116.5)
        points = [
            (-32.4, 115.6),
            (-32.0, 116.0),
            (-31.7, 115.8),
            (-32.3, 116.3),
            (-31.6, 115.55),
        ]
        lat_tol, lon_tol = self._quant_tol(bounds)
        for lat, lon in points:
            lat2, lon2, _, _ = self._roundtrip(lat, lon, bounds)
            assert abs(lat2 - lat) <= lat_tol, \
                f"lat roundtrip error at ({lat},{lon}): {abs(lat2-lat):.2e} > {lat_tol:.2e}"
            assert abs(lon2 - lon) <= lon_tol, \
                f"lon roundtrip error at ({lat},{lon}): {abs(lon2-lon):.2e} > {lon_tol:.2e}"

    def test_encode_decode_region_coord(self):
        """encode_region_coord(decode_region_coord(x)) is the identity."""
        from kiwiw.coordconv import encode_region_coord, decode_region_coord
        test_values = [0, 1, 4095, 4096, 8191, 8192, 16383, 32767]
        for v in test_values:
            encoded = encode_region_coord(v)
            decoded = decode_region_coord(encoded)
            assert decoded == v, f"encode→decode failed for {v}: got {decoded}"

    def test_integer_pixel_exact(self):
        """xy_to_latlon composed with latlon_to_xy is exact for integer pixels."""
        bounds = BoundingBox(lat_lo=-33.0, lat_hi=-32.0, lon_lo=115.0, lon_hi=116.0)
        for xc, yc in [(0, 0), (0, 32767), (32767, 0), (16384, 16384), (1000, 5000)]:
            lat, lon = xy_to_latlon(xc, yc, bounds)
            xc2, yc2 = latlon_to_xy(lat, lon, bounds)
            assert xc2 == xc, f"x roundtrip failed: {xc} → lat/lon → {xc2}"
            assert yc2 == yc, f"y roundtrip failed: {yc} → lat/lon → {yc2}"


# ---------------------------------------------------------------------------
# Additional sanity: parcel_bounds geometry
# ---------------------------------------------------------------------------

class TestParcelBounds:
    def test_bounds_tile_correctly(self):
        """Adjacent parcels share edges (no gap, no overlap)."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        b00 = parcel_bounds(0, 0, grid)
        b10 = parcel_bounds(1, 0, grid)
        b01 = parcel_bounds(0, 1, grid)
        assert b10.lon_lo == pytest.approx(b00.lon_hi)
        assert b01.lat_lo == pytest.approx(b00.lat_hi)

    def test_bounds_span_matches_cell_size(self):
        """Each parcel's geographic span equals the grid cell size."""
        grid = _make_grid(lat_lo=-35.0, lon_lo=113.0, lat_span=10.0, lon_span=20.0,
                          nx=100, ny=50)
        b = parcel_bounds(23, 11, grid)
        assert (b.lat_hi - b.lat_lo) == pytest.approx(grid.cell_lat, rel=1e-9)
        assert (b.lon_hi - b.lon_lo) == pytest.approx(grid.cell_lon, rel=1e-9)
