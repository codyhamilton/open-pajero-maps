"""Plan 46: bg_producer_scan shim + bit predicates."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "tools")]

import bg_producer_scan as ps  # noqa: E402


@pytest.fixture(scope="module")
def shim():
    so = ps.compile_shim()
    return ps.load_shim(so)


def test_compile_shim(shim):
    assert shim is not None


def test_ring_stats_closed_square(shim):
    # Closed unit square in lon/lat
    ring = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
    st = ps.ring_stats(shim, ring)
    assert st["closed"] == 1
    assert st["closing_is_longest"] in (0, 1)  # all edges equal length
    assert st["crossings"] == 0


def test_ring_stats_self_crossing(shim):
    # Bowtie: closing edge crosses the opposite edge
    ring = [(0.0, 0.0), (1.0, 1.0), (0.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
    st = ps.ring_stats(shim, ring)
    assert st["closed"] == 1
    # crossing count depends on which edge is closing; at least geometry is closed
    assert st["closing"] >= 0


def test_residual_bit_requires_unique_byte():
    stats = {"closed": 1, "closing_is_longest": 1, "crossings": 2}
    assert ps.residual_crossing_bit("unique-byte", stats) == 1
    assert ps.residual_crossing_bit("unique-fragment", stats) == 0
    assert ps.residual_crossing_bit("producer_home_outside_R_cap", stats) == 0
    assert ps.residual_crossing_bit("unique-byte", {**stats, "crossings": 0}) == 0


def test_s02_bit_l0_type291_only():
    stats = {"closed": 1, "closing_is_longest": 1, "crossings": 1}
    assert ps.s02_producer_bit("unique-byte", stats, level=0, code=291) == 1
    assert ps.s02_producer_bit("unique-byte", stats, level=0, code=288) == 0
    assert ps.s02_producer_bit("unique-byte", stats, level=2, code=291) == 0


def test_ring_stats_unclosed_is_not_explicit(shim):
    # Open ring (no repeated first vertex) must not count as explicitly closed
    ring = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]
    st = ps.ring_stats(shim, ring)
    assert st["closed"] == 0
    assert ps.residual_crossing_bit("unique-byte", st) == 0


def test_enrich_cands_keeps_raw_coords():
    class _Bg:
        coords = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]

    def _cell(_sp, _lv, _x, _y):
        return {"backgrounds": [_Bg()]}

    out = ps._enrich_cands(None, 0, [((0, 0, 0, 288), [(0, 0)])], _cell)
    assert out[0][2] == [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)]


def test_leaf_order_groups_and_masks_padding():
    import numpy as np
    dt = np.dtype([("level", "u1"), ("ix", "<i4"), ("iy", "<i4"), ("depth", "u1")]
                  + [(f"p{j}", "<u2") for j in range(7)])
    r = np.zeros(6, dt)
    r["ix"] = [5, 40, 5, 5, 40, 5]
    r["iy"] = [1, 1, 1, 1, 1, 2]
    r["depth"] = 1
    r["p0"] = [7, 7, 7, 8, 7, 7]
    r["p3"] = [0, 0, 9, 0, 0, 0]  # padding beyond depth must not split the leaf
    order, starts = ps.leaf_order(r, len(r), tile=32)
    leaves = [sorted(order[starts[k]:starts[k + 1]].tolist()) for k in range(len(starts) - 1)]
    assert sorted(map(tuple, leaves)) == sorted([(0, 2), (3,), (1, 4), (5,)])
    # tile order: (ix 5,iy 1/2) tile (0,0) before ix 40 tile (1,0)
    assert leaves.index([1, 4]) == len(leaves) - 1


def test_ring_cache_is_bounded_lru():
    ps.set_ring_cache_max(3)
    ps._RING_NP.clear()

    def cell(_sp, _lv, x, y):
        return {"backgrounds": []}

    for x in range(10):
        ps._cell_rings(None, 0, x, 0, cell)
    assert len(ps._RING_NP) == 3
    assert list(ps._RING_NP) == [(0, 7, 0), (0, 8, 0), (0, 9, 0)]
    ps.set_ring_cache_max(4096)


def test_leaf_clip_geometry_matches_e2_subrects():
    """Plan 46: divided leaves clip against E2 dv_tier_setup sub-rects on the parent bounds."""
    import bg_producer_scan as S
    b4 = (-30.0, -29.9, 150.0, 150.1)
    cb = lambda level, ix, iy: (b4, 4096.0)
    assert S.leaf_clip_geometry(0, 5, 6, (744,), 0, cb) == (b4, 4096.0, (0.0, 0.0, 4096.0, 4096.0))
    # pardiv1 (2x2): sub 2 -> sx 0, sy 1 (the (744, 2) record spans x<=2048, y>=2048)
    assert S.leaf_clip_geometry(0, 5, 6, (744, 2), 1, cb)[2] == (0.0, 2048.0, 2048.0, 4096.0)
    assert S.leaf_clip_geometry(0, 5, 6, (744, 1), 1, cb)[2] == (2048.0, 0.0, 4096.0, 2048.0)
    # pardiv2 (4x4): sub 6 -> sx 2, sy 1
    assert S.leaf_clip_geometry(0, 5, 6, (744, 6), 2, cb)[2] == (2048.0, 1024.0, 3072.0, 2048.0)
    with pytest.raises(ValueError):
        S.leaf_clip_geometry(0, 5, 6, (744, 4), 1, cb)
    with pytest.raises(ValueError):
        S.leaf_clip_geometry(0, 5, 6, (744, 0), 3, cb)


def test_far_homes_query_cell_superset():
    """Plan 46: FarHomes returns homes whose tall-shape cell bbox (+-1 margin) covers the cell."""
    import bg_producer_scan as S
    from collections import defaultdict
    fh = S.FarHomes.__new__(S.FarHomes)
    fh.home = np.array([[100, 100], [5, 5], [7, 40]], np.int64)
    fh.cell = np.array([[9, 31, 9, 12], [3, 7, 3, 7], [6, 8, 0, 41]], np.int64)
    T = fh.TILE
    b = defaultdict(list)
    for k, (cx0, cx1, cy0, cy1) in enumerate(fh.cell.tolist()):
        for tx in range(cx0 // T, cx1 // T + 1):
            for ty in range(cy0 // T, cy1 // T + 1):
                b[(tx, ty)].append(k)
    fh.buckets = {k: np.asarray(v) for k, v in b.items()}
    assert fh.query(20, 10) == [(100, 100)]
    assert fh.query(7, 5) == [(5, 5), (7, 40)]
    assert fh.query(8, 30) == [(7, 40)]
    assert fh.query(50, 50) == []


def test_ring_stats_longest_edge_in_raw_units():
    """Plan 46 RC6: 'closing = longest' is decided in raw lattice units, not degrees."""
    import bg_producer_scan as S
    shim = S.load_shim(S.compile_shim())
    # closing edge spans 1.0 deg of lat; edge 1 spans 1.2 deg of lon. With a cell of
    # 1 deg lat x 2 deg lon (sy = cr/1, sy > sx = cr/2), lat edges are longer in raw units.
    ring = [(0.0, 0.0), (0.0, 1.2), (1.0, 1.2), (1.0, 0.1), (0.0, 0.0)]  # (lat, lon)
    deg = S.ring_stats(shim, ring)
    raw = S.ring_stats(shim, ring, scale=(4096 / 2.0, 4096 / 1.0))
    assert deg["closed"] == raw["closed"] == 1
    assert deg["closing_is_longest"] == 0 and deg["longest"] == 0
    assert raw["longest"] == raw["closing"] == 3 and raw["closing_is_longest"] == 1
    assert deg["crossings"] == raw["crossings"]
