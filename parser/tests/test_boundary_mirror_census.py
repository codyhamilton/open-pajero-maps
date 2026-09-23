"""Synthetic-fixture tests for `parser/tools/boundary_mirror_census.py`
(Plan 03 unit 2-14, frame/global-lattice rewrite). No disc is read.

Two fixtures:

* Fixture 1 (`StubReader`, level 2, 1x6 leaf grid, n=1 everywhere) exercises
  ordinary edge matching/violation/exclusions per NODE, via
  `test_edge_fixture_tallies_every_bucket` and friends. A node one raw unit
  off the edge is included to show it never qualifies at all.
* Fixture 2 (`StubReader2c`, level 2, 2x2 leaf grid, n=1 everywhere) is a
  minimal corner fixture: only the SW and NE (diagonal) leaves exist, so a
  corner node at SW's NE corner is satisfied only by the diagonal frame
  (2-13's `corner_frames`, "any sharing frame"), never by a nominated edge
  neighbour (both of SW's own E/N edges resolve `empty_slot`).
* Fixture 3 (`StubReader3`, level 0, reusing `test_r_neighbours.py`'s
  sparse-tile/urban fixture shape) exercises frame-dedup (one frame per
  16-aliased-slot L0 sparse tile, not 16) and cross-class inclusion (an
  n=4 sparse tile's edge facing an n=1 urban frame is an ordinary
  crossing, not `scale_mismatch`).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boundary_mirror_census as bmc  # noqa: E402
import r_neighbours as rn  # noqa: E402
from kiwiw.model import BoundingBox  # noqa: E402

LEVEL = 2
RANGE = 4096
RANGES = {"2": {"full": {"normal": {"max": RANGE}}}}
CLASS_RULE = {}  # unused for level != 0 (_class_key never calls _urban)


def _fb(span=1.0):
    return BoundingBox(lat_lo=0.0, lat_hi=1.0, lon_lo=0.0, lon_hi=span)


def _row(*lpath, ptype=0, span=1.0):
    return (lpath, None, None, ptype, None, (_fb(span), "leaf"))


def _blk(ordn, bs_index, ei):
    return (ordn, bs_index, ei, None, None)


# --------------------------------------------------------------- fixture 1
# 1x6 global leaf grid, one blockset, one block. Leaf 1 absent (empty_slot
# target), leaf 3 divided (scale_mismatch target). Source leaves: 0 (plain
# outside_coverage + a non-qualifying near-edge node), 2 (empty_slot via
# absent leaf1), 4 (scale_mismatch via divided leaf3, plus a matched E->W
# pair with leaf 5), 5 (the matched partner, plus one violation).

LMR = SimpleNamespace(
    n_blocksets_lng=0, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[5], n_parcels_lat=[0],
    grid_nx=6, grid_ny=1,
    level=LEVEL,
)

BLK = _blk(0, 0, 0)

LEAVES = {
    (0, 0): [_row(0), _row(2), _row(3, ptype=1), _row(4), _row(5)],  # leaf 1 absent
}

ENDS = {
    (0, 0, (0,)): [(0, 10), (1, 500)],   # leaf0: W -> outside_coverage;
                                          #        (1,500) does not qualify at all
    (0, 0, (2,)): [(0, 50)],             # leaf2: W -> leaf1 (absent) -> empty_slot
    (0, 0, (4,)): [(0, 77), (4096, 88)], # leaf4: W -> leaf3 (divided) -> scale_mismatch
                                          #        E -> leaf5, matches (0, 88)
    (0, 0, (5,)): [(0, 88), (0, 99)],    # leaf5: W -> leaf4, (0,88) matches (4096,88);
                                          #        (0,99) has no counterpart -> violation
}


class StubReader:
    def blocks(self, level):
        assert level == LEVEL
        return LMR, [BLK]

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return LEAVES[(bs_index, ei)]

    def decode(self, lmr, blk, leaf_row):
        _, bs_index, ei, _, _ = blk
        lpath = leaf_row[0]
        ends = ENDS.get((bs_index, ei, lpath))
        if ends is None:
            return []
        return [{"ends": ends}]


def _idx():
    return rn.LeafIndex(StubReader(), LEVEL)


# --------------------------------------------------------------- helpers

def test_qualifying_edges_one_unit_off_does_not_qualify():
    assert bmc._qualifying_edges(1, 500, RANGE) == []
    assert bmc._qualifying_edges(RANGE - 1, 500, RANGE) == []
    assert bmc._qualifying_edges(500, 1, RANGE) == []


def test_qualifying_edges_exact_range_and_zero():
    assert bmc._qualifying_edges(RANGE, 500, RANGE) == ["E"]
    assert bmc._qualifying_edges(0, 500, RANGE) == ["W"]
    assert bmc._qualifying_edges(0, 0, RANGE) == ["W", "S"]  # corner


def test_mirror_tol_raw_is_zero():
    assert bmc.MIRROR_TOL_RAW == 0


# --------------------------------------------------------------- fixture 1
#
# By-hand tally:
#   n_candidate_nodes = 6 (leaf0's (0,10); leaf2's (0,50); leaf4's (0,77)
#              and (4096,88); leaf5's (0,88) and (0,99). leaf0's (1,500)
#              never qualifies at all and is not counted.)
#   corner_nodes = 0
#   denominator = matched(2) + violations(1) = 3
#   matched = 2 (leaf4's (4096,88) <-> leaf5's (0,88), both directions)
#   violations = 1 (leaf5's (0,99), nearest actual global is leaf4's
#              (4096,88) point, 11 raw units away on the along axis)
#   outside_coverage = 1 (leaf0's (0,10))
#   empty_slot = 1 (leaf2's (0,50) -> absent leaf1)
#   scale_mismatch = 1 (leaf4's (0,77) -> divided leaf3)
#   total_incidences = 6 = n_candidate_nodes

def test_edge_fixture_tallies_every_bucket():
    r = bmc.census_class(StubReader(), _idx(), CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    assert r["n_candidate_nodes"] == 6
    assert r["corner_nodes"] == 0
    assert r["denominator"] == 3
    assert r["matched"] == 2
    assert r["violations"] == 1
    assert r["outside_coverage"] == 1
    assert r["empty_slot"] == 1
    assert r["scale_mismatch"] == 1
    assert r["total_incidences"] == r["n_candidate_nodes"]


def test_violation_nearest_actual_global_not_loosened_to_match():
    r = bmc.census_class(StubReader(), _idx(), CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    assert r["violations"] == 1
    ex = r["violation_examples"][0]
    assert ex["source_raw"] == [0, 99]
    # global X of leaf5's W node == global X of leaf4's E node (both on the
    # shared boundary); nearest actual is leaf4's (4096, 88), 11 raw units
    # away on Y, not the (0, 77) point (a different global X entirely).
    assert ex["nearest_actual_global"][1] == 88


def test_exclusions_out_of_denominator():
    r = bmc.census_class(StubReader(), _idx(), CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    assert r["denominator"] == r["matched"] + r["violations"]


def test_verdict_pass_with_residual_when_fully_enumerated():
    r = bmc.census_class(StubReader(), _idx(), CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    assert r["verdict"] == "pass_with_residual"
    assert len(r["violation_examples"]) == r["violations"]


def test_verdict_is_fail_when_residual_exceeds_cap(monkeypatch):
    monkeypatch.setattr(bmc, "RESIDUAL_ENUM_CAP", 0)
    r = bmc.census_class(StubReader(), _idx(), CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    assert r["violations"] == 1
    assert len(r["violation_examples"]) == 0
    assert r["verdict"] == "fail"


# --------------------------------------------------------------- fixture 2
# 2x2 leaf grid (gn_lng=gn_lat=2), one block. Only SW (leaf 0) and NE
# (leaf 3, diagonal) exist; SE (leaf 1) and NW (leaf 2) are absent, so SW's
# own E and N edges each resolve empty_slot -- the corner can only be
# satisfied by the diagonal frame via corner_frames.

LMR_C = SimpleNamespace(
    n_blocksets_lng=0, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[1], n_parcels_lat=[1],
    grid_nx=2, grid_ny=2,
    level=LEVEL,
)
BLK_C = _blk(0, 0, 0)
LEAVES_C = {(0, 0): [_row(0), _row(3)]}  # SW=0, NE=3; SE=1, NW=2 absent
ENDS_C = {
    (0, 0, (0,)): [(4096, 4096)],  # SW's own NE corner -> matches NE's SW corner
    (0, 0, (3,)): [(0, 0)],        # NE's own SW corner
}


class StubReaderCorner:
    def blocks(self, level):
        assert level == LEVEL
        return LMR_C, [BLK_C]

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return LEAVES_C[(bs_index, ei)]

    def decode(self, lmr, blk, leaf_row):
        _, bs_index, ei, _, _ = blk
        ends = ENDS_C.get((bs_index, ei, leaf_row[0]))
        return [{"ends": ends}] if ends else []


def test_corner_satisfied_by_diagonal_only_frame_not_by_either_edge():
    idx = rn.LeafIndex(StubReaderCorner(), LEVEL)
    r = bmc.census_class(StubReaderCorner(), idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    # Both SW and NE hold a corner node at this one physical lattice point
    # (SW's own NE corner and NE's own SW corner), each a separate source
    # node tested from its own side -- "as nodes" (brief), not deduped to
    # one physical point, consistent with how an ordinary edge node is
    # counted from both sides elsewhere in this tool.
    assert r["corner_nodes"] == 2
    # any-sharing-frame (per-node) reading: both satisfied by the diagonal frame.
    assert r["corner_split_per_node"]["matched"] == 2
    assert r["corner_split_per_node"]["violations"] == 0
    # per-edge (2-11-comparable) reading: both E and N resolve empty_slot,
    # so neither edge alone ever matches or violates -- the divergence this
    # fixture exists to demonstrate.
    assert r["corner_split_per_edge_2_11_comparable"]["matched"] == 0
    assert r["corner_split_per_edge_2_11_comparable"]["violations"] == 0
    assert r["verdict"] == "pass"


# --------------------------------------------------------------- fixture 3
# L0 sparse tile (n=4) adjacent to an L0 urban leaf (n=1), same shape as
# `test_r_neighbours.py`'s frame-adjacency fixture -- reused here to test
# this tool's frame-dedup and cross-class inclusion end to end.

LMR3 = SimpleNamespace(
    n_blocksets_lng=1, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[3], n_parcels_lat=[3],
    grid_nx=8, grid_ny=4,
    level=0,
)
RANGES3 = {"0": {"sparse": {"normal": {"max": 16384}}, "urban": {"normal": {"max": 4096}}}}
CLASS_RULE3 = {"l0_grid_width": 2, "l0_tile": 4, "urban_tiles": [[1, 0, 0, 0]]}


def _frow(*lpath, frame_class="l0_sparse_tile", span=1.0):
    return (lpath, None, None, 0, None, (_fb(span), frame_class))


BLK_B3 = _blk(0, 0, 0)   # sparse tile, frame (gx0=0, gy0=0, n=4)
BLK_E3 = _blk(1, 1, 0)   # urban, one leaf, frame (gx0=4, gy0=0, n=1), east of B
LEAVES3 = {
    (0, 0): [_frow(i) for i in range(16)],
    (1, 0): [_frow(0, frame_class="leaf")],
}
# Real R aliases all 16 leaf slots of one sparse tile to the identical
# (dsa, size), so every slot decodes to the same content (r_neighbours.py's
# module docstring, "Denominator inflation" paragraph); this stub mirrors
# that by giving every slot index the tile's content, since a neighbour
# lookup can resolve to any of the 16 aliased slots depending on which one
# sits immediately across the queried edge, not only index 0.
ENDS3 = {(0, 0, (i,)): [(16384, 500)] for i in range(16)}
ENDS3[(1, 0, (0,))] = [(0, 500)]  # E3: W -> B, matches


class StubReader3:
    def blocks(self, level):
        assert level == 0
        return LMR3, [BLK_B3, BLK_E3]

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return LEAVES3[(bs_index, ei)]

    def decode(self, lmr, blk, leaf_row):
        _, bs_index, ei, _, _ = blk
        ends = ENDS3.get((bs_index, ei, leaf_row[0]))
        return [{"ends": ends}] if ends else []


def test_sixteen_aliased_slots_dedup_to_one_frame():
    idx = rn.LeafIndex(StubReader3(), 0)
    r = bmc.census_class(StubReader3(), idx, CLASS_RULE3, RANGES3, "L0_sparse", 0,
                          sample_blocks=2)
    # 16 leaf slots alias one frame -- n_frames counts frames, not slots.
    assert r["n_frames"] == 1


def test_cross_class_crossing_is_matched_not_scale_mismatch():
    idx = rn.LeafIndex(StubReader3(), 0)
    r_sparse = bmc.census_class(StubReader3(), idx, CLASS_RULE3, RANGES3, "L0_sparse", 0,
                                 sample_blocks=2)
    assert r_sparse["scale_mismatch"] == 0
    assert r_sparse["matched"] == 1
    assert r_sparse["cross_class_split"]["matched"] == 1

    r_urban = bmc.census_class(StubReader3(), idx, CLASS_RULE3, RANGES3, "L0_urban", 0,
                                sample_blocks=2)
    assert r_urban["scale_mismatch"] == 0
    assert r_urban["matched"] == 1
    assert r_urban["cross_class_split"]["matched"] == 1


# --------------------------------------------------------------- fixture 4
# One raw unit off: MIRROR_TOL_RAW == 0 means a candidate that is exactly
# one raw unit away from the source's global (X, Y) must violate, not
# match -- no tolerance band around the exact lattice point.

LMR4 = SimpleNamespace(
    n_blocksets_lng=0, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[1], n_parcels_lat=[0],
    grid_nx=2, grid_ny=1,
    level=LEVEL,
)
BLK4 = _blk(0, 0, 0)
LEAVES4 = {(0, 0): [_row(0), _row(1)]}
ENDS4 = {
    (0, 0, (0,)): [(4096, 500)],  # leaf0: E -> leaf1, off by one raw unit
    (0, 0, (1,)): [(0, 501)],     # leaf1's W node is one raw unit north of
                                   # leaf0's E node's mirrored global (X, Y)
}


class StubReader4:
    def blocks(self, level):
        assert level == LEVEL
        return LMR4, [BLK4]

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return LEAVES4[(bs_index, ei)]

    def decode(self, lmr, blk, leaf_row):
        _, bs_index, ei, _, _ = blk
        ends = ENDS4.get((bs_index, ei, leaf_row[0]))
        return [{"ends": ends}] if ends else []


def test_one_raw_unit_off_fails_not_matches():
    idx = rn.LeafIndex(StubReader4(), LEVEL)
    r = bmc.census_class(StubReader4(), idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    # leaf0's E node and leaf1's W node are candidates for each other but
    # differ by exactly one raw unit on the along-edge axis -- both must
    # violate at MIRROR_TOL_RAW == 0, not match.
    assert r["matched"] == 0
    assert r["violations"] == 2
    assert r["denominator"] == 2


# --------------------------------------------------------------- fixture 5
# Old verdict-logic regression: `elif len(violation_examples) >= min(
# violations, 20): verdict = "pass_with_residual"` (2-11) labels a class
# `pass_with_residual` whenever it can print up to 20 examples, whatever
# share of the denominator they cover. 30 one-off violating pairs, cap
# monkeypatched to 20 (2-11's old hardcoded print limit): the old formula
# would see len(examples)==20 >= min(30, 20)==20 and call it
# `pass_with_residual`; the corrected logic requires every violation
# enumerated (30 != 20) and must call it `fail`.

N_PAIRS_5 = 30
LMR5 = SimpleNamespace(
    n_blocksets_lng=0, n_blocksets_lat=0,
    n_blocks_lng=0, n_blocks_lat=0,
    n_parcels_lng=[2 * N_PAIRS_5 - 1], n_parcels_lat=[0],
    grid_nx=2 * N_PAIRS_5, grid_ny=1,
    level=LEVEL,
)
BLK5 = _blk(0, 0, 0)
LEAVES5 = {(0, 0): [_row(i) for i in range(2 * N_PAIRS_5)]}
ENDS5 = {}
for _i in range(N_PAIRS_5):
    ENDS5[(0, 0, (2 * _i,))] = [(4096, 500 + _i)]      # E node
    ENDS5[(0, 0, (2 * _i + 1,))] = [(0, 501 + _i)]      # its W partner, one off


class StubReader5:
    def blocks(self, level):
        assert level == LEVEL
        return LMR5, [BLK5]

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return LEAVES5[(bs_index, ei)]

    def decode(self, lmr, blk, leaf_row):
        _, bs_index, ei, _, _ = blk
        ends = ENDS5.get((bs_index, ei, leaf_row[0]))
        return [{"ends": ends}] if ends else []


def _old_verdict(violations, n_examples):
    """2-11's retired formula, reproduced only to show it disagrees."""
    if violations == 0:
        return "pass"
    if n_examples >= min(violations, 20):
        return "pass_with_residual"
    return "fail"


def test_corrected_verdict_fails_where_old_logic_passed_with_residual(monkeypatch):
    monkeypatch.setattr(bmc, "RESIDUAL_ENUM_CAP", 20)
    idx = rn.LeafIndex(StubReader5(), LEVEL)
    r = bmc.census_class(StubReader5(), idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=1)
    assert r["violations"] == 2 * N_PAIRS_5  # both sides of every off-by-one pair
    assert len(r["violation_examples"]) == 20  # capped, not fully enumerated
    assert _old_verdict(r["violations"], len(r["violation_examples"])) == "pass_with_residual"
    assert r["verdict"] == "fail"
