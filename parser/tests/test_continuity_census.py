"""Synthetic-fixture tests for `parser/tools/continuity_census.py` (Plan 03
unit 2-14, frame/global-lattice rewrite). No disc is read.

Covers: the pure selection/pairing/scoring helpers directly, plus
`_class_pairs` end to end via small `LeafIndex`-backed stub readers (the
same pattern `test_boundary_mirror_census.py` uses) for the scenarios the
brief's done-evidence names that are specific to criterion 2 -- exact
lattice pairing across a shared frame edge, the n=4-vs-n=4 and n=1-vs-n=4
(cross-class) cases, a one-raw-unit-off pair failing to pair, a residual
over the cap producing `fail`, and the corrected verdict logic.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import continuity_census as cc  # noqa: E402
import overlay_test as ot  # noqa: E402
import r_neighbours as rn  # noqa: E402
from kiwiw.model import BoundingBox  # noqa: E402

LEVEL = 2
RANGE = 4096
RANGES = {"2": {"full": {"normal": {"max": RANGE}}},
          "0": {"sparse": {"normal": {"max": 16384}}, "urban": {"normal": {"max": 4096}}}}
CLASS_RULE = {"l0_grid_width": 2, "l0_tile": 4, "urban_tiles": [[1, 0, 0, 0]]}

FRAME_S = BoundingBox(lat_lo=-30.0, lat_hi=-29.9, lon_lo=150.0, lon_hi=150.1)
FRAME_T = BoundingBox(lat_lo=-30.0, lat_hi=-29.9, lon_lo=150.1, lon_hi=150.2)


# --------------------------------------------------------------- pure helpers

def test_edge_node_selection_is_exact_no_tolerance():
    """A node one raw unit inside the edge does not qualify at all --
    EDGE_TOL_RAW is retired (module docstring, retirement rule)."""
    rng = 4096
    pts = [(rng, 10.0), (rng - 1, 20.0), (0.0, 30.0), (1.0, 40.0)]
    e = cc._select_edge_nodes(pts, "E", rng)
    assert (rng, 10.0) in e
    assert (rng - 1, 20.0) not in e
    w = cc._select_edge_nodes(pts, "W", rng)
    assert (0.0, 30.0) in w
    assert (1.0, 40.0) not in w


def test_midline_selection_is_exact():
    mid = 2048
    pts = [(mid, 5.0), (mid - 1, 6.0), (mid + 1, 7.0)]
    sel = cc._select_edge_nodes_mid(pts, "E", mid)
    assert sel == [(mid, 5.0)]


def test_greedy_exact_pair_matches_and_reports_unmatched():
    src = [(500,), (501,)]
    tgt = [(500,), (502,)]
    pairs, unmatched = cc._greedy_exact_pair(src, tgt, lambda p: p[0])
    assert pairs == [((500,), (500,))]
    assert unmatched == [(501,)]


def test_score_pair_zero_under_true_range_nonzero_under_double():
    pair = {"s_pt": (4096.0, 2000.0), "t_pt": (0.0, 2000.0), "ref_cell": FRAME_S}
    hyp = cc.score_pair(pair, FRAME_S, 4096.0, FRAME_T, 4096.0)
    assert hyp == 0.0
    dbl = cc.score_pair(pair, FRAME_S, 8192.0, FRAME_T, 8192.0)
    assert dbl > 0.0


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


# ----------------------------------------------------------- stub helpers

def _fb(span=1.0):
    return BoundingBox(lat_lo=0.0, lat_hi=1.0, lon_lo=0.0, lon_hi=span)


def _row(*lpath, ptype=0, span=1.0, frame_class="leaf"):
    # `lb` (3rd element) is the leaf's own local bbox, used by `score_pair`
    # as a stable reference cell for metre scaling -- must be a real
    # BoundingBox, not None.
    return (lpath, None, _fb(span), ptype, None, (_fb(span), frame_class))


def _blk(ordn, bs_index, ei):
    return (ordn, bs_index, ei, None, None)


class DictStubReader:
    """Generic stub: `leaves_by_key[block_key] -> [row, ...]`,
    `ends_by_key[(bs_index, ei, lpath)] -> [(x, y), ...]`."""

    def __init__(self, lmr, blocks, leaves_by_key, ends_by_key):
        self.lmr = lmr
        self._blocks = blocks
        self._leaves = leaves_by_key
        self._ends = ends_by_key

    def blocks(self, level):
        assert level == self.lmr.level
        return self.lmr, self._blocks

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return self._leaves[(bs_index, ei)]

    def decode(self, lmr, blk, leaf_row):
        _, bs_index, ei, _, _ = blk
        ends = self._ends.get((bs_index, ei, leaf_row[0]))
        return [{"ends": ends}] if ends else []


# --------------------------------------------------------------- ordinary n=1

LMR1 = SimpleNamespace(
    n_blocksets_lng=0, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[1], n_parcels_lat=[0],
    grid_nx=2, grid_ny=1,
    level=LEVEL,
)
BLK1 = _blk(0, 0, 0)


def _reader1(ends):
    return DictStubReader(LMR1, [BLK1], {(0, 0): [_row(0), _row(1)]}, ends)


def test_matched_pair_at_shared_frame_edge_same_class():
    """Two adjacent n=1 frames, exact same global (X, Y): one matched pair,
    zero violations."""
    ends = {(0, 0, (0,)): [(4096, 500)], (0, 0, (1,)): [(0, 500)]}
    idx = rn.LeafIndex(_reader1(ends), LEVEL)
    r = cc.continuity_class(_reader1(ends), {LEVEL: idx}, "L2", LEVEL, 0, None)
    assert r["matched"] == 1
    assert r["violations"] == 0
    assert r["denominator"] == 1
    assert r["verdict"] == "pass"


def test_one_raw_unit_off_does_not_pair():
    """Pairing is exact lattice equality (retirement rule): a candidate one
    raw unit off must not pair, and is counted as a violation, not
    silently dropped or loosened to match."""
    ends = {(0, 0, (0,)): [(4096, 500)], (0, 0, (1,)): [(0, 501)]}
    idx = rn.LeafIndex(_reader1(ends), LEVEL)
    r = cc.continuity_class(_reader1(ends), {LEVEL: idx}, "L2", LEVEL, 0, None)
    assert r["matched"] == 0
    assert r["violations"] == 1
    assert r["denominator"] == 1
    assert r["residual_examples"][0]["source_raw"] == [4096, 500]


# ----------------------------------------------------- n=4 <-> n=4, n=1 <-> n=4

LMR0 = SimpleNamespace(
    n_blocksets_lng=1, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[3], n_parcels_lat=[3],
    grid_nx=8, grid_ny=4,
    level=0,
)
RANGES0 = RANGES
BLK_B = _blk(0, 0, 0)   # sparse tile, frame (gx0=0, gy0=0, n=4)
BLK_D = _blk(1, 1, 0)   # sparse tile, frame (gx0=4, gy0=0, n=4), east of B
BLK_E = _blk(2, 1, 0)   # urban leaf, frame (gx0=4, gy0=0, n=1) -- alt. east of B


def _tile_rows(frame_class="l0_sparse_tile"):
    return [_row(i, frame_class=frame_class) for i in range(16)]


def test_n4_frame_matches_n4_frame_at_shared_edge():
    """A node at the range of one n=4 tile matches a node at 0 in the
    adjacent n=4 tile at the identical global (X, Y)."""
    leaves = {(0, 0): _tile_rows(), (1, 0): _tile_rows()}
    ends = {**{(0, 0, (i,)): [(16384, 500)] for i in range(16)},
            **{(1, 0, (i,)): [(0, 500)] for i in range(16)}}
    reader = DictStubReader(LMR0, [BLK_B, BLK_D], leaves, ends)
    idx = rn.LeafIndex(reader, 0)
    r = cc.continuity_class(reader, {0: idx}, "L0_sparse", 0, 0, None)
    assert r["matched"] == 1
    assert r["violations"] == 0
    assert r["verdict"] == "pass"


def test_n1_frame_matches_n4_frame_cross_class():
    """An n=1 urban frame's node matches an n=4 sparse tile's node across
    their shared edge (the cross-class case), counted in cross_class_split."""
    leaves = {(0, 0): _tile_rows(), (1, 0): [_row(0, frame_class="leaf")]}
    ends = {**{(0, 0, (i,)): [(16384, 500)] for i in range(16)},
            (1, 0, (0,)): [(0, 500)]}
    reader = DictStubReader(LMR0, [BLK_B, BLK_E], leaves, ends)
    idx = rn.LeafIndex(reader, 0)
    r_sparse = cc.continuity_class(reader, {0: idx}, "L0_sparse", 0, 0, None)
    assert r_sparse["matched"] == 1
    assert r_sparse["violations"] == 0
    assert r_sparse["cross_class_split"]["matched"] == 1


def test_sixteen_aliased_slots_contribute_one_frame_not_sixteen():
    """The denominator-inflation regression: all 16 aliased leaf slots of
    one L0_sparse tile must contribute one candidate frame, not sixteen."""
    leaves = {(0, 0): _tile_rows(), (1, 0): _tile_rows()}
    ends = {**{(0, 0, (i,)): [(16384, 500)] for i in range(16)},
            **{(1, 0, (i,)): [(0, 500)] for i in range(16)}}
    reader = DictStubReader(LMR0, [BLK_B, BLK_D], leaves, ends)
    idx = rn.LeafIndex(reader, 0)
    r = cc.continuity_class(reader, {0: idx}, "L0_sparse", 0, 0, None)
    assert r["n_frames"] == 2  # B and D, not 32 (16 slots x 2 tiles)


# --------------------------------------------------------------- verdict logic

def test_residual_over_cap_is_fail_not_truncated(monkeypatch):
    monkeypatch.setattr(cc, "RESIDUAL_ENUM_CAP", 0)
    ends = {(0, 0, (0,)): [(4096, 500)], (0, 0, (1,)): [(0, 501)]}
    idx = rn.LeafIndex(_reader1(ends), LEVEL)
    r = cc.continuity_class(_reader1(ends), {LEVEL: idx}, "L2", LEVEL, 0, None)
    assert r["violations"] == 1
    assert len(r["residual_examples"]) == 0
    assert r["verdict"] == "fail"


def _old_verdict(violations, n_examples):
    """2-11's retired formula (ported to this tool's shape), reproduced
    only to show it disagrees with the corrected logic."""
    if violations == 0:
        return "pass"
    if n_examples >= min(violations, 20):
        return "pass_with_residual"
    return "fail"


def test_corrected_verdict_fails_where_old_logic_passed_with_residual(monkeypatch):
    """30 one-off-not-pairing pairs with the cap monkeypatched to 20 (2-11's
    old hardcoded print limit): the old formula would see
    len(examples) == 20 >= min(30, 20) == 20 and call it
    `pass_with_residual`; the corrected logic requires every violation
    enumerated and must call it `fail`."""
    monkeypatch.setattr(cc, "RESIDUAL_ENUM_CAP", 20)
    n = 30
    lmr = SimpleNamespace(
        n_blocksets_lng=0, n_blocksets_lat=0, n_blocks_lng=0, n_blocks_lat=0,
        n_parcels_lng=[2 * n - 1], n_parcels_lat=[0],
        grid_nx=2 * n, grid_ny=1, level=LEVEL,
    )
    blk = _blk(0, 0, 0)
    leaves = {(0, 0): [_row(i) for i in range(2 * n)]}
    ends = {}
    for i in range(n):
        ends[(0, 0, (2 * i,))] = [(4096, 500 + i)]
        ends[(0, 0, (2 * i + 1,))] = [(0, 501 + i)]  # one off, never pairs
    reader = DictStubReader(lmr, [blk], leaves, ends)
    idx = rn.LeafIndex(reader, LEVEL)
    r = cc.continuity_class(reader, {LEVEL: idx}, "L2", LEVEL, 0, None)
    assert r["violations"] == n
    assert len(r["residual_examples"]) == 20
    assert _old_verdict(r["violations"], len(r["residual_examples"])) == "pass_with_residual"
    assert r["verdict"] == "fail"
