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

_SMALL_BOUNDS = BoundingBox(lat_lo=-1.0, lat_hi=1.0, lon_lo=-1.0, lon_hi=1.0, coord_range=4096)


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


# ---------------------------------------------------------------------------
# Streaming assembly (plan 02 phase 1): spill-backed frames + streamed output
# equal the bytes-returning path.
# ---------------------------------------------------------------------------

def test_streaming_matches_bytes_path(tmp_path):
    import hashlib

    from kiwiw.spill import FrameSpill

    grid = _grid()
    coords = [(512, 0), (513, 0), (520, 10), (600, 40)]
    ref = aw.build_alldata_kwi({12: _level_build(12, [(0, 0)]),
                                0: _level_build(0, coords)},
                               grid, disk_title="TEST")
    with FrameSpill(str(tmp_path)) as spill:
        def spilled(level, cs):
            return aw.LevelBuild(level=level, parcels=[
                (ix, iy, spill.add(_make_frame(level, ix, iy))) for ix, iy in cs])
        out = tmp_path / "streamed.kwi"
        res = aw.build_alldata_kwi({12: spilled(12, [(0, 0)]), 0: spilled(0, coords)},
                                   grid, disk_title="TEST", out_path=str(out),
                                   return_bytes=False)
    assert out.read_bytes() == ref
    assert res.size == len(ref)
    assert res.sha256 == hashlib.sha256(ref).hexdigest()


# ---------------------------------------------------------------------------
# Indexed (FrameTable) assembly path == object path, byte for byte
# (plan 02 step 3), including divided parents in shared blocks.
# ---------------------------------------------------------------------------

def _table_from(frames, tmp_path, name):
    """frames: [(ix, iy, ptype, sx, sy, bytes)] -> FrameTable over one spill file."""
    import numpy as np

    from kiwiw import frame_table as ft
    sp = ft.ChunkSpill(str(tmp_path))
    rec = np.zeros(len(frames), ft.FRAME_DTYPE)
    for i, (ix, iy, pt, sx, sy, fb) in enumerate(frames):
        rec[i] = (ix, iy, pt, sx, sy, 0, len(fb), sp.append(fb))
    sp.close()
    return ft.merge_tables([(sp.path, rec)])


def test_indexed_matches_object_path(tmp_path):
    import hashlib
    import random

    import pytest
    from kiwiw import cenc
    if cenc.lib() is None:
        pytest.skip("C helpers unavailable")
    rng = random.Random(7)
    grid = _grid()
    frame = lambda: bytes(rng.randrange(256) for _ in range(rng.choice([0, 1, 31, 32, 33, 700, 2100])))
    plain = [(ix, iy, 0, 0, 0, frame()) for ix, iy in
             [(512, 0), (513, 0), (520, 10), (600, 40), (514, 1)]]
    divided = []
    for (ix, iy, pt) in [(515, 0, 1), (516, 0, 2), (601, 40, 1)]:  # 515/516 share a block with 512..
        n = 4 if pt == 1 else 16
        side = 2 if pt == 1 else 4
        for k in range(n):
            if rng.random() < 0.8:
                divided.append((ix, iy, pt, k % side, k // side, frame()))
    rows = plain + divided
    rng.shuffle(rows)  # stream order must not matter except within a parent
    rows.sort(key=lambda r: (r[1], r[0]))  # canonical (iy, ix); stable keeps sub order
    ref_levels = {12: _level_build(12, [(0, 0)]),
                  0: aw.LevelBuild(level=0, parcels=[(a, b, f) for a, b, pt, _x, _y, f in rows if pt == 0])}
    ref_out = tmp_path / "ref.kwi"
    ref = aw.build_alldata_kwi(ref_levels, grid, disk_title="T", out_path=str(ref_out),
                               divided={0: [r for r in rows if r[2] != 0]}, return_bytes=False)
    lv12 = _table_from([(0, 0, 0, 0, 0, _make_frame(12, 0, 0))], tmp_path, "12")
    lv0 = _table_from(rows, tmp_path, "0")
    got_out = tmp_path / "idx.kwi"
    got = aw.build_alldata_kwi({12: aw.LevelBuild(level=12, table=lv12),
                                0: aw.LevelBuild(level=0, table=lv0)},
                               grid, disk_title="T", out_path=str(got_out), return_bytes=False)
    assert got_out.read_bytes() == ref_out.read_bytes()
    assert (got.size, got.sha256) == (ref.size, ref.sha256)
