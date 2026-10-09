"""Plan 67: the census's leaf-rect convention against the encoder's own `dv_assign` (E2, `_e2.c`).

The probe compiles `_e2.c` (with `_cenc.c` / `_e1.c`) and calls the static `dv_assign` with the same
sub-grid setup as `dv_tier_setup`. Boundaries at tip: lat half-open (south edge in, north edge -> -1),
lon closed (east edge in, epsilon past east -> -1, no wrap to sx=0: plan 53). Cell c = sy*nx + sx with sy
from the south edge, matching `bg_producer_scan.leaf_clip_geometry`."""
from __future__ import annotations

import ctypes
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
KW = HERE.parent / "kiwiw"
B4 = (-28.0, -27.5, 153.0, 153.5)  # lat_lo, lat_hi, lon_lo, lon_hi (dv_state.b4 order)
EPS = 1e-9


@pytest.fixture(scope="module")
def assign(tmp_path_factory):
    from kiwiw import cbuild
    out = tmp_path_factory.mktemp("dv_probe") / "probe_dv.so"
    subprocess.run([cbuild._find_cc(), *cbuild.CFLAGS, "-shared", str(HERE / "fixtures/l0_edge/probe_dv.c"),
                    str(KW / "_cenc.c"), str(KW / "_e1.c"), "-lm", "-o", str(out)], check=True)
    fn = ctypes.CDLL(str(out)).probe_dv_assign
    fn.restype = ctypes.c_int
    fn.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double, ctypes.c_double]
    b4 = (ctypes.c_double * 4)(*B4)
    return lambda ptype, fx, fy: fn(b4, ptype, B4[0] + fy * (B4[1] - B4[0]), B4[2] + fx * (B4[3] - B4[2]))


def rect_cell(nx, fx, fy):
    """cells whose committed `leaf_clip_geometry` rect (closed) holds the parent fraction (fx, fy), y-up."""
    import sys
    sys.path.insert(0, str(HERE.parent / "tools"))
    from bg_producer_scan import leaf_clip_geometry
    out = set()
    for c in range(nx * nx):
        _b4, crs, (x0, y0, x1, y1) = leaf_clip_geometry(0, 0, 0, (0, c), 1 if nx == 2 else 2,
                                                        lambda lv, x, y: (B4, None))
        if x0 <= fx * crs <= x1 and y0 <= fy * crs <= y1:
            out.add(c)
    return out


@pytest.mark.parametrize("ptype,nx", [(1, 2), (2, 4)])
def test_interior_cells_match_rects(assign, ptype, nx):
    for c in range(nx * nx):
        sx, sy = c % nx, c // nx
        fx, fy = (sx + .5) / nx, (sy + .5) / nx
        assert assign(ptype, fx, fy) == c
        assert rect_cell(nx, fx, fy) == {c}


@pytest.mark.parametrize("ptype,nx", [(1, 2), (2, 4)])
def test_parent_edges(assign, ptype, nx):
    mid = .5 / nx  # inside column/row 0
    # south edge (lat = lat_lo): in, row 0
    assert assign(ptype, mid, 0.0) == 0
    # north edge (lat = lat_hi): half-open -> outside the parent
    assert assign(ptype, mid, 1.0) == -1
    # west edge: in, column 0
    assert assign(ptype, 0.0, mid) == 0
    # east edge (lon = lon_hi): closed -> clamped to the last column
    assert assign(ptype, 1.0, mid) == nx - 1
    # epsilon past east: outside, not wrapped to column 0 (plan 53)
    assert assign(ptype, 1.0 + EPS, mid) == -1
    # epsilon past west and south: outside
    assert assign(ptype, -EPS, mid) == -1
    assert assign(ptype, mid, -EPS) == -1


@pytest.mark.parametrize("ptype,nx", [(1, 2), (2, 4)])
def test_corners(assign, ptype, nx):
    assert assign(ptype, 0.0, 0.0) == 0                      # SW
    assert assign(ptype, 1.0, 0.0) == nx - 1                 # SE
    assert assign(ptype, 0.0, 1.0) == -1                     # NW (north open)
    assert assign(ptype, 1.0, 1.0) == -1                     # NE (north open)


@pytest.mark.parametrize("ptype,nx", [(1, 2), (2, 4)])
def test_interior_cell_boundaries_go_to_upper_cell(assign, ptype, nx):
    """a vertex on an internal cell boundary assigns to the east / north cell, while closed rects hold it in both."""
    for k in range(1, nx):
        f = k / nx
        assert assign(ptype, f, .5 / nx) == k                # vertical boundary -> column k
        assert rect_cell(nx, f, .5 / nx) == {k - 1, k}
        assert assign(ptype, .5 / nx, f) == k * nx           # horizontal boundary -> row k
        assert rect_cell(nx, .5 / nx, f) == {(k - 1) * nx, k * nx}
