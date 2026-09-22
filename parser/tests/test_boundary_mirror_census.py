"""Synthetic-fixture tests for `parser/tools/boundary_mirror_census.py`
(Plan 03 unit 2-11). No disc is read.

One small 1x8 global leaf grid (2 blocksets x 2 blocks x 2 leaves wide,
lat collapsed to one row -- the same shape `test_r_neighbours.py` uses for
its W/E fixtures), levelled at L2 (class range 4096, `ranges["2"]["full"]
["normal"]["max"]`), with hand-chosen link end-nodes so one `census_class`
call exercises every bucket at once: two matched incidences (one
`cross_block`), one violation (`cross_blockset`, the mirrored candidate one
raw unit off), one `outside_coverage`-only corner (two incidences from one
node), one plain `outside_coverage`, one `empty_slot`, one `scale_mismatch`,
and one node that misses the edge entirely (one raw unit off, not a
boundary node at all). The by-hand tally is transcribed as a comment above
`test_full_fixture_tallies_every_bucket`.
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

LMR = SimpleNamespace(
    n_blocksets_lng=1, n_blocksets_lat=0,
    n_blocks_lng=1, n_blocks_lat=0,
    n_parcels_lng=[1], n_parcels_lat=[0],
    grid_nx=8, grid_ny=1,
    level=LEVEL,
)


def _fb(span=1.0):
    return BoundingBox(lat_lo=0.0, lat_hi=1.0, lon_lo=0.0, lon_hi=span)


def _row(*lpath, span=1.0):
    return (lpath, None, None, 0, None, (_fb(span), "leaf"))


def _blk(ordn, bs_index, ei):
    return (ordn, bs_index, ei, None, None)


BLK_A = _blk(0, 0, 0)  # bsx=0, blx=0
BLK_B = _blk(1, 0, 1)  # bsx=0, blx=1 (same blockset as A, different block)
BLK_C = _blk(2, 1, 0)  # bsx=1, blx=0 (different blockset from A/B)
BLK_D = _blk(3, 1, 1)  # bsx=1, blx=1 (same blockset as C, different block)

LEAVES = {
    (0, 0): [_row(0), _row(1)],
    (0, 1): [_row(0), _row(1)],
    (1, 0): [_row(0), _row(1)],
    (1, 1): [_row(0, span=2.0)],  # D1 absent -> empty_slot when addressed
}

ENDS = {
    (0, 0, (0,)): [(0, 50), (0, 0)],     # A0: plain W (-> outside_coverage)
                                          #     + corner W+S (-> outside_coverage x2)
    (0, 0, (1,)): [(4096, 60)],          # A1: E -> B0, cross_block, matches
    (0, 1, (0,)): [(0, 60)],             # B0: W -> A1, cross_block, matches
    (0, 1, (1,)): [(4096, 800)],         # B1: E -> C0, cross_blockset, violation
    (1, 0, (0,)): [(1, 800)],            # C0: not a boundary node at all
    (1, 0, (1,)): [(4096, 300)],         # C1: E -> D0, scale_mismatch (span 1 vs 2)
    (1, 1, (0,)): [(4096, 200)],         # D0: E -> D1, empty_slot
}


class StubReader:
    def blocks(self, level):
        assert level == LEVEL
        return LMR, [BLK_A, BLK_B, BLK_C, BLK_D]

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


def test_mirrored_point():
    assert bmc._mirrored_point(0, 60, "W", RANGE) == (RANGE, 60)
    assert bmc._mirrored_point(RANGE, 60, "E", RANGE) == (0, 60)


def test_mirror_tol_raw_is_zero():
    assert bmc.MIRROR_TOL_RAW == 0


# --------------------------------------------------------------- the fixture
#
# By-hand tally (see ENDS above for the per-leaf reasoning):
#   n_leaves = 7 (A0, A1, B0, B1, C0, C1, D0; D1 is absent, never walked
#              as a source)
#   n_candidate_nodes = 7 (A0 x2, A1, B0, B1, C1, D0; C0's (1, 800) does not
#              qualify at all and is not counted)
#   corner_incidences = 1 (A0's (0, 0))
#   denominator = 3 (A1-E, B0-W, B1-E)
#   matched = 2 (A1-E -> B0 cross_block, B0-W -> A1 cross_block)
#   violations = 1 (B1-E -> C0 cross_blockset, mirrored candidate (0, 800)
#              missing; C0 has (1, 800), one raw unit off)
#   outside_coverage = 3 (A0's plain W, A0's corner W, A0's corner S)
#   empty_slot = 1 (D0-E -> D1, absent)
#   scale_mismatch = 1 (C1-E -> D0, lon span 1.0 vs 2.0)
#   total_edge_incidences = 8 = n_candidate_nodes(7) + corner_incidences(1)
#                              = denominator(3) + outside_coverage(3)
#                                + empty_slot(1) + scale_mismatch(1)


def test_full_fixture_tallies_every_bucket():
    reader = StubReader()
    idx = _idx()
    r = bmc.census_class(reader, idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=4)

    assert r["n_leaves"] == 7
    assert r["n_candidate_nodes"] == 7
    assert r["corner_incidences"] == 1
    assert r["denominator"] == 3
    assert r["matched"] == 2
    assert r["violations"] == 1
    assert r["outside_coverage"] == 3
    assert r["empty_slot"] == 1
    assert r["scale_mismatch"] == 1
    assert r["total_edge_incidences"] == 8
    assert (r["n_candidate_nodes"] + r["corner_incidences"]
            == r["total_edge_incidences"])


def test_basic_match_along_edge_unchanged():
    reader = StubReader()
    idx = _idx()
    r = bmc.census_class(reader, idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=4)
    # A1-E -> B0 and B0-W -> A1 are the two directions of one boundary,
    # both matched at (0, 60) <-> (4096, 60): along-edge value 60 unchanged,
    # crossed axis 0 <-> 4096 = range - 0.
    assert r["crossing_breakdown"]["matched"]["cross_block"] == 2


def test_violation_is_not_loosened_to_match():
    reader = StubReader()
    idx = _idx()
    r = bmc.census_class(reader, idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=4)
    assert r["crossing_breakdown"]["violations"]["cross_blockset"] == 1
    ex = r["violation_examples"][0]
    assert ex["expected_mirrored_raw"] == [0, 800]
    assert ex["nearest_neighbour_raw"] == [1, 800]


def test_exclusions_land_in_their_own_counters_out_of_denominator():
    reader = StubReader()
    idx = _idx()
    r = bmc.census_class(reader, idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=4)
    assert r["outside_coverage"] == 3
    assert r["empty_slot"] == 1
    assert r["scale_mismatch"] == 1
    # None of the exclusions inflate matched/violations/denominator.
    assert r["denominator"] == r["matched"] + r["violations"]


def test_crossing_breakdown_sums_to_matched_plus_violations():
    reader = StubReader()
    idx = _idx()
    r = bmc.census_class(reader, idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=4)
    cb = r["crossing_breakdown"]
    total = sum(cb["matched"].values()) + sum(cb["violations"].values())
    assert total == r["matched"] + r["violations"]


def test_verdict_is_pass_with_residual_when_violations_are_enumerated():
    reader = StubReader()
    idx = _idx()
    r = bmc.census_class(reader, idx, CLASS_RULE, RANGES, "L2", LEVEL,
                          sample_blocks=4)
    assert r["verdict"] == "pass_with_residual"
    assert len(r["violation_examples"]) == r["violations"]
