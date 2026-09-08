"""Tests for the whole-Australia, all-seven-level `build_alldata_kwi()`
(unit 12): reference LMR/BSMR/BMT shape, record-29 copy-through, wrap-safe
coverage, determinism.

Covers exactly the brief's ("12-assembler-all-levels.md") required cases:
  - a two-level build (12, 0) decodes with `AllData.find_parcel()` at both
    levels;
  - a full seven-level build has 7 LMRs, each of size 170;
  - MHT entry 29 bytes equal `grid.mht29_frame_bytes()` at byte offset 4096;
  - a parcel at lon 179.9 and one at lon -179.9 (antimeridian wrap) both
    resolve;
  - two builds from identical input are byte-equal (determinism).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import alldata_writer as aw
from kiwiw import synth
from kiwiw.disc import AllData
from kiwiw.grid import ReferenceGrid
from kiwiw.model import BoundingBox

_SMALL_BOUNDS = BoundingBox(lat_lo=-1.0, lat_hi=1.0, lon_lo=-1.0, lon_hi=1.0)


def _make_frame(level: int, ix: int, iy: int) -> bytes:
    """A minimal (no roads/backgrounds/names) Map Frame for cell (ix, iy)."""
    road = synth.build_road_frame_bytes([], _SMALL_BOUNDS)
    bg = synth.build_background_frame_bytes([], _SMALL_BOUNDS)
    name = synth.build_name_frame_bytes([], _SMALL_BOUNDS, level=level)
    return synth.build_map_frame_bytes(level, (0, 0), (ix % 256, iy % 256),
                                        road, bg, name)


def _level_build(level: int, coords: list[tuple[int, int]]) -> aw.LevelBuild:
    return aw.LevelBuild(
        level=level,
        parcels=[(ix, iy, _make_frame(level, ix, iy)) for ix, iy in coords],
    )


def _grid() -> ReferenceGrid:
    return ReferenceGrid.load()


# ---------------------------------------------------------------------------
# Two-level build: decode round-trip at both levels
# ---------------------------------------------------------------------------

def test_two_level_roundtrip(tmp_path):
    grid = _grid()
    # Level 12's grid is exactly 1x1 (a single top-level parcel covering all
    # of Australia), so it can only ever hold one distinct cell position.
    levels = {
        12: _level_build(12, [(0, 0)]),
        0: _level_build(0, [(512, 0), (513, 0), (520, 10)]),
    }
    out_path = tmp_path / "test.kwi"
    data = aw.build_alldata_kwi(levels, grid, disk_title="TEST", out_path=str(out_path))
    assert out_path.read_bytes() == data

    cov = grid.coverage
    lg0 = grid.level(0)
    with AllData(str(out_path)) as ad:
        lat0 = cov["lat_lo"] + 0 * lg0.cell_lat + lg0.cell_lat * 0.5
        lon0 = cov["lon_lo"] + 513 * lg0.cell_lon + lg0.cell_lon * 0.5
        p0 = ad.find_parcel(lat0, lon0, level=0)
        assert p0 is not None

        lg12 = grid.level(12)
        lat12 = cov["lat_lo"] + lg12.cell_lat * 0.5
        lon12 = cov["lon_lo"] + lg12.cell_lon * 0.5
        p12 = ad.find_parcel(lat12, lon12, level=12)
        assert p12 is not None


# ---------------------------------------------------------------------------
# Full seven-level build: LMR count and size
# ---------------------------------------------------------------------------

def test_seven_levels_lmr_shape(tmp_path):
    grid = _grid()
    levels = {lvl: _level_build(lvl, [(0, 0)]) for lvl in (12, 10, 8, 6, 4, 2, 0)}
    out_path = tmp_path / "test.kwi"
    aw.build_alldata_kwi(levels, grid, disk_title="TEST", out_path=str(out_path))

    with AllData(str(out_path)) as ad:
        assert len(ad.pdmdh.levels) == 7
        for lmr in ad.pdmdh.levels:
            assert ad.pdmdh.lmr_size == 170


# ---------------------------------------------------------------------------
# MHT entry 29 copy-through
# ---------------------------------------------------------------------------

def test_mht29_copy_through(tmp_path):
    grid = _grid()
    levels = {0: _level_build(0, [(0, 0)])}
    out_path = tmp_path / "test.kwi"
    data = aw.build_alldata_kwi(levels, grid, disk_title="TEST", out_path=str(out_path))

    frame = data[4096:4096 + 2048]
    assert frame == grid.mht29_frame_bytes()


# ---------------------------------------------------------------------------
# Antimeridian wrap
# ---------------------------------------------------------------------------

def test_antimeridian_wrap(tmp_path):
    grid = _grid()
    tile_grid_nx = grid.level(0).nx
    tile_grid_ny = grid.level(0).ny
    cov = grid.coverage
    lg0 = grid.level(0)

    # lon 179.9 and -179.9 both lie within the reference's coverage box
    # (90.0 -> -142.0 the long way around, lon_span 128), on either side of
    # the +/-180 seam. Compute the matching global cell indices the same
    # wrap-safe way the extractor does.
    def _ix_for_lon(lon: float) -> int:
        span = cov["lon_hi"] - cov["lon_lo"]
        if span < 0:
            span += 360.0
        delta = lon - cov["lon_lo"]
        if delta < 0:
            delta += 360.0
        return min(int(delta / lg0.cell_lon), tile_grid_nx - 1)

    def _iy_for_lat(lat: float) -> int:
        delta = lat - cov["lat_lo"]
        return min(int(delta / lg0.cell_lat), tile_grid_ny - 1)

    iy = _iy_for_lat(0.0)
    ix_e = _ix_for_lon(179.9)
    ix_w = _ix_for_lon(-179.9)

    levels = {0: _level_build(0, [(ix_e, iy), (ix_w, iy)])}
    out_path = tmp_path / "test.kwi"
    aw.build_alldata_kwi(levels, grid, disk_title="TEST", out_path=str(out_path))

    with AllData(str(out_path)) as ad:
        p_e = ad.find_parcel(0.0, 179.9, level=0)
        p_w = ad.find_parcel(0.0, -179.9, level=0)
        assert p_e is not None
        assert p_w is not None


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic():
    grid = _grid()
    levels = {
        12: _level_build(12, [(0, 0)]),
        0: _level_build(0, [(512, 0), (513, 0), (520, 10)]),
    }
    data1 = aw.build_alldata_kwi(levels, grid, disk_title="TEST")
    data2 = aw.build_alldata_kwi(levels, grid, disk_title="TEST")
    assert data1 == data2
