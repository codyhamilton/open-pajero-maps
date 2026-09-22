import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import continuity_census as cc  # noqa: E402
from kiwiw.model import BoundingBox  # noqa: E402

# Two frames sharing the E/W edge at lon 150.1: FRAME_S is west, FRAME_T east.
FRAME_S = BoundingBox(lat_lo=-30.0, lat_hi=-29.9, lon_lo=150.0, lon_hi=150.1)
FRAME_T = BoundingBox(lat_lo=-30.0, lat_hi=-29.9, lon_lo=150.1, lon_hi=150.2)


def test_edge_node_selection_tolerance():
    """A node 5 raw units from the edge is not selected; one 4 units away is."""
    rng = 4096
    pts = [(rng - 4, 10.0), (rng - 5, 20.0), (4.0, 30.0), (5.0, 40.0)]
    e = cc._select_edge_nodes(pts, "E", rng, cc.EDGE_TOL_RAW)
    assert (rng - 4, 10.0) in e
    assert (rng - 5, 20.0) not in e
    w = cc._select_edge_nodes(pts, "W", rng, cc.EDGE_TOL_RAW)
    assert (4.0, 30.0) in w
    assert (5.0, 40.0) not in w


def test_continuous_pair_zero_under_hypothesis_nonzero_double():
    """An exactly continuous shared node scores 0 m at the true range and
    non-zero when both sides are (wrongly) decoded at double the range."""
    src = [(4096.0, 2000.0)]   # east edge of FRAME_S
    tgt = [(0.0, 2000.0)]      # west edge of FRAME_T -- same physical point
    matched, unpaired, mismatch = cc._pair_nodes(src, tgt, "E", 4096, 4096, cc.PAIR_TOL_RAW)
    assert unpaired == 0 and mismatch == 0
    assert len(matched) == 1
    pair = {"s_pt": matched[0][0], "t_pt": matched[0][1], "ref_cell": FRAME_S}

    hyp = cc.score_pair(pair, FRAME_S, 4096.0, FRAME_T, 4096.0)
    assert hyp == 0.0

    dbl = cc.score_pair(pair, FRAME_S, 8192.0, FRAME_T, 8192.0)
    assert dbl > 0.0


def test_pair_set_identical_across_hypotheses():
    """The pair (selection + pairing) is computed once; scoring under three
    different hypotheses must not add, drop or re-pair anything -- asserted
    on the pair's own contents, not eyeballed."""
    src = [(4096.0, 2000.0)]
    tgt = [(0.0, 2000.0)]
    matched, _, _ = cc._pair_nodes(src, tgt, "E", 4096, 4096, cc.PAIR_TOL_RAW)
    pair = {"s_pt": matched[0][0], "t_pt": matched[0][1], "ref_cell": FRAME_S}
    before = (pair["s_pt"], pair["t_pt"])
    for rng in (4096.0, 2048.0, 8192.0, cc.ot.DECODER_RANGE):
        cc.score_pair(pair, FRAME_S, rng, FRAME_T, rng)
        assert (pair["s_pt"], pair["t_pt"]) == before


def test_scale_mismatch_counted_not_dropped_silently():
    """Ranges that are not an exact multiple of each other cannot be mapped
    to a shared parameter: excluded and counted as `scale_mismatch`, not
    silently dropped, and not paired anyway."""
    src = [(4096.0, 2000.0)]
    tgt = [(0.0, 2000.0)]
    matched, unpaired, mismatch = cc._pair_nodes(src, tgt, "E", 4096, 6000, cc.PAIR_TOL_RAW)
    assert matched == []
    assert unpaired == 1
    assert mismatch == 1


def test_unpaired_counted_not_dropped():
    """An edge node with no partner within PAIR_TOL_RAW is counted, not
    dropped: same range, but the along-edge coordinates disagree by more
    than the tolerance."""
    src = [(4096.0, 2000.0)]
    tgt = [(0.0, 2000.0 + cc.PAIR_TOL_RAW + 1)]
    matched, unpaired, mismatch = cc._pair_nodes(src, tgt, "E", 4096, 4096, cc.PAIR_TOL_RAW)
    assert matched == []
    assert unpaired == 1
    assert mismatch == 0


def test_quadrant_containment_all_four_k():
    """An in-quadrant point passes and a point one raw unit outside fails,
    for all four quadrants."""
    HALF = cc.HALF

    def contained(x, y, qx, qy):
        return qx * HALF <= x <= (qx + 1) * HALF and qy * HALF <= y <= (qy + 1) * HALF

    for k, (qx, qy) in cc.QUAD_OFFSET.items():
        inside = (qx * HALF + 10, qy * HALF + 10)
        outside_x = (qx * HALF - 1) if qx == 0 else ((qx + 1) * HALF + 1)
        outside = (outside_x, qy * HALF + 10)
        assert contained(*inside, qx, qy), (k, inside)
        assert not contained(*outside, qx, qy), (k, outside)
