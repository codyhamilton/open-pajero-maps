"""Level descriptor (plan 03, 3C-06) and the build-side homes of the
extractor's grid rules in `kiwiw/mesh.py`.

The descriptor is data Python hands C once per level (Contract B, "The level
descriptor"). These tests check its layout against the documented header and
its contents against their sources (reference grid, `coord_scale.json` via
`mesh`, the spool index, the mask). The `osm_to_parcel_geometry` comparisons
are verification of the moved rules (allowed until 3C-08 removes the build's
old imports), never build logic."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import descriptor, mesh
from kiwiw.model import BackgroundShape
from kiwiw.spool import _COLUMNS, _COUNT_KEYS

import boundary

REPO = Path(__file__).resolve().parents[2]
LEVELS = (0, 2, 4, 6, 8, 10, 12)


# ------------------------------------------------------------ mesh homes

@pytest.mark.parametrize("level", LEVELS)
def test_cell_grid_matches_extractor_tile_grid(level):
    from osm_to_parcel_geometry import TileGrid
    t = TileGrid.from_reference(level)
    g = mesh.CellGrid.from_reference(level)
    assert (g.level, g.nx, g.ny) == (t.level, t.nx, t.ny)
    assert (g.disc_lat_lo, g.disc_lon_lo) == (t.disc_lat_lo, t.disc_lon_lo)
    assert (g.disc_lat_span, g.disc_lon_span) == (t.disc_lat_span, t.disc_lon_span)
    assert (g.cell_lat, g.cell_lon) == (t.cell_lat, t.cell_lon)


_POINTS = [(-31.95312, 115.86719), (-37.813629, 144.963058), (-50.0, 90.0),
           (-10.0, -150.0), (-60.0, 100.0), (35.34, 179.99), (-33.0, -179.5),
           (-12.46, 130.84), (-42.88, 147.33)]


@pytest.mark.parametrize("level", LEVELS)
def test_assign_bounds_and_frame_rules_match_extractor(level):
    import osm_to_parcel_geometry as ex
    t = ex.TileGrid.from_reference(level)
    g = mesh.CellGrid.from_reference(level)
    for lat, lon in _POINTS:
        assert mesh.assign_to_parcel(lat, lon, g) == ex.assign_to_parcel(lat, lon, t)
    for ix, iy in ((0, 0), (g.nx - 1, g.ny - 1), (g.nx // 3, g.ny // 2)):
        assert mesh.parcel_bounds(ix, iy, g) == ex.parcel_bounds(ix, iy, t)
        assert mesh.frame_bounds(ix, iy, g) == ex.frame_bounds(ix, iy, t)
    assert mesh.g_frame_class(level) == ex.g_frame_class(level)
    assert mesh.g_frame_range(level) == ex.g_frame_range(level)
    for pt in (1, 2, 3):
        for sub in (0, 3):
            try:
                want = ex.g_frame_range(level, pt, sub)
            except KeyError:
                with pytest.raises(KeyError):
                    mesh.g_frame_range(level, pt, sub)
            else:
                assert mesh.g_frame_range(level, pt, sub) == want


# Captured from `build_alldata._fixture_cell_range(L, "perth", TileGrid...)`
# at 9e9f3de (the Python cell-range code it came from is gone).
_PERTH_RANGES = {0: (816, 848, 839, 887), 2: (204, 212, 209, 221), 4: (51, 53, 52, 55),
                 6: (12, 13, 13, 13), 8: (3, 3, 3, 3), 10: (0, 0, 0, 0), 12: (0, 0, 0, 0)}


def test_fixture_bboxes_and_cell_range_match_build():
    import osm_to_parcel_geometry as ex
    assert mesh.FIXTURE_BBOXES == ex.FIXTURE_BBOXES
    for level in LEVELS:
        assert mesh.fixture_cell_range(level, "perth") == _PERTH_RANGES[level]


def test_build_side_modules_do_not_import_extractor():
    out = subprocess.run(["git", "grep", "-n", "osm_to_parcel_geometry",
                          "parser/kiwiw/descriptor.py", "parser/kiwiw/mesh.py"],
                         cwd=REPO, capture_output=True, text=True)
    assert out.stdout == "", out.stdout


# ------------------------------------------------------------ descriptor

def test_header_layout_is_the_documented_one():
    assert descriptor.HEADER_BYTES == 168
    assert descriptor.E1_ROW_DTYPE.itemsize == 32
    names = descriptor.E1_ROW_DTYPE.names
    assert names == ("tix", "tiy", "six", "siy", "cell_off", "shape", "kind")
    offs = [descriptor.E1_ROW_DTYPE.fields[n][1] for n in names]
    assert offs == [0, 4, 8, 12, 16, 24, 28]


@pytest.mark.parametrize("level", (0, 6, 12))
def test_descriptor_fields(level):
    g = mesh.CellGrid.from_reference(level)
    ix = np.array([0, 3, g.nx - 1], np.int32) % g.nx
    iy = np.array([0, 0, g.ny - 1], np.int32) % g.ny
    buf = descriptor.build(level, ix, iy, threshold=65534,
                           kind_limits={"road": 100, "name": 7})
    d = descriptor.parse(buf)
    assert d["magic"] == descriptor.MAGIC and d["version"] == descriptor.VERSION
    assert d["header_bytes"] == descriptor.HEADER_BYTES and d["total_bytes"] == len(buf)
    assert len(buf) % 8 == 0
    assert (d["level"], d["nx"], d["ny"]) == (level, g.nx, g.ny)
    assert (d["disc_lat_lo"], d["disc_lon_lo"], d["cell_lat"], d["cell_lon"]) == \
        (g.disc_lat_lo, g.disc_lon_lo, g.cell_lat, g.cell_lon)
    assert d["frame_class"] == descriptor.FRAME_CLASS_CODES[mesh.g_frame_class(level)]
    assert d["range"][0] == mesh.g_frame_range(level)
    for pt in (1, 2, 3):
        try:
            want = mesh.g_frame_range(level, pt, 0)
        except KeyError:
            want = -1
        assert d["range"][pt] == want
    assert d["window"] == (0, g.nx - 1, 0, g.ny - 1)
    assert d["max_frame"] == 131070 == boundary.MAX_FRAME_BYTES
    assert d["threshold"] == 65534
    assert d["kind_limits"] == (100, descriptor.NO_LIMIT, 7)
    assert d["mask"].shape == (g.ny, g.nx)
    assert sorted(zip(*np.nonzero(d["mask"].T))) == sorted(set(zip(ix.tolist(), iy.tolist())))


def test_descriptor_mask_rect_and_window():
    level = 6
    buf = descriptor.build(level, np.array([1], np.int32), np.array([2], np.int32),
                           mask_rect=(10, 11, 20, 22), window=(5, 30, 6, 40))
    d = descriptor.parse(buf)
    want = {(1, 2)} | {(x, y) for x in (10, 11) for y in (20, 21, 22)}
    assert set(zip(*[a.tolist() for a in np.nonzero(d["mask"].T)])) == want
    assert d["window"] == (5, 30, 6, 40)


def test_descriptor_spool_layout_table_mirrors_spool_columns():
    d = descriptor.parse(descriptor.build(12, np.zeros(0, np.int32), np.zeros(0, np.int32)))
    assert d["n_count_keys"] == len(_COUNT_KEYS)
    want = [(np.dtype(dt).itemsize, _COUNT_KEYS.index(k)) for _n, dt, k in _COLUMNS]
    assert d["columns"] == want
    names = [n for n, _dt, _k in _COLUMNS]
    assert d["roles"] == tuple(names.index(n) for n in
                               ("b_class", "b_nstored", "c_lat", "c_lon"))


def test_build_for_spool_reads_the_spool_index(tmp_path):
    level = 6
    g = mesh.CellGrid.from_reference(level)
    lat = g.disc_lat_lo + 4.5 * g.cell_lat
    lon = g.disc_lon_lo + 7.5 * g.cell_lon
    shp = BackgroundShape(shape_class=0, type_code=1, type_label="", n_coords=1,
                          mult_const=1, underground=False, pen_up=False,
                          coords=[(lat, lon)])
    boundary.write_fixture_spool(tmp_path, {(level, 7, 4): {"backgrounds": [shp]}})
    d = descriptor.parse(descriptor.build_for_spool(tmp_path, level))
    assert list(zip(*[a.tolist() for a in np.nonzero(d["mask"].T)])) == [(7, 4)]
