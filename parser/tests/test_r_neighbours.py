"""Synthetic-fixture tests for `parser/tools/r_neighbours.py` (Plan 03 unit
2-09). No disc is read.

A real R block is a parsed `ParcelMgmtRecord` decoded from raw sector bytes
via `harness.walk`/`kiwiw.volume`; assembling one from scratch is out of
proportion to this unit (it needs a full synthetic PDMDH + LMR + sector
layout, which `test_overlay_test.py` avoids too, building synthetic *links*
instead of synthetic *disc bytes*). So these tests use a stub `rdr` that
implements just the two methods `LeafIndex` calls -- `blocks(level)` and
`leaves(lmr, blk)` -- with the same shapes `overlay_test.RReader` returns,
over a small synthetic leaf grid whose geometry is hand-computed below.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import r_neighbours as rn  # noqa: E402

# ---------------------------------------------------------------------
# Synthetic grid: n_blocksets_lng=1 (2 blocksets wide), n_blocks_lng=1 (2
# blocks per blockset wide), n_parcels_lng=[1] (2 leaves per block wide);
# lat dims collapsed to 1 row throughout (n_blocksets_lat=n_blocks_lat=0,
# n_parcels_lat=[0]) since these tests only exercise the lon (W/E) axis.
# Global leaf grid: nx = 2*2*2 = 8, ny = 1*1*1 = 1.
# ---------------------------------------------------------------------

LMR = SimpleNamespace(
    n_blocksets_lng=1, n_blocksets_lat=0,
    n_blocks_lng=1, n_blocks_lat=0,
    n_parcels_lng=[1], n_parcels_lat=[0],
    grid_nx=8, grid_ny=1,
    level=0,
)


def _row(*lpath):
    """A leaf row shaped like `RReader.leaves()`'s tuples
    (lpath, entry, bounds, ptype, parent_bounds, frame); only `lpath` is
    read by `r_neighbours` (bounds/frame are exercised by the disc-backed
    `main()` run, not these unit tests)."""
    return (lpath, None, None, 0, None, None)


def _blk(ordn, bs_index, ei):
    return (ordn, bs_index, ei, None, None)


# Block A: bsx=0, blx=0 -> bs_index=0, ei=0. Leaves 0 and 1, both normal.
BLK_A = _blk(0, 0, 0)
# Block B: bsx=0, blx=1 -> bs_index=0, ei=1. Leaves 0 and 1, both normal.
BLK_B = _blk(1, 0, 1)
# Block C: bsx=1, blx=0 -> bs_index=1, ei=0. Leaf 0 normal, leaf 1 divided
# into 4 sub-leaves (pardiv1 quadrants 0..3).
BLK_C = _blk(2, 1, 0)
# Block D: bsx=1, blx=1 -> bs_index=1, ei=1. Leaf 0 normal, leaf 1 NO_DATA
# (absent from its leaf list): the block is on disc but that slot is not.
BLK_D = _blk(3, 1, 1)

LEAVES = {
    (0, 0): [_row(0), _row(1)],
    (0, 1): [_row(0), _row(1)],
    (1, 0): [_row(0), _row(1, 0), _row(1, 1), _row(1, 2), _row(1, 3)],
    (1, 1): [_row(0)],
}


class StubReader:
    def blocks(self, level):
        assert level == 0
        return LMR, [BLK_A, BLK_B, BLK_C, BLK_D]

    def leaves(self, lmr, blk):
        _, bs_index, ei, _, _ = blk
        return LEAVES[(bs_index, ei)]


def _idx():
    return rn.LeafIndex(StubReader(), 0)


# --------------------------------------------------------------- global_leaf_xy

def test_global_leaf_xy_hand_computed():
    # bsx=1, blx=1 both non-zero; leaf_index=1 -> leaf_x=1, leaf_y=0.
    # base_ix = (1*2 + 1) * 2 = 6; gx = 6 + 1 = 7. base_iy = 0; gy = 0.
    assert rn.global_leaf_xy(LMR, bsx=1, bsy=0, blx=1, bly=0, leaf_index=1) == (7, 0)


def test_grid_dims():
    assert rn.grid_dims(LMR) == (8, 1)


# --------------------------------------------------------------- neighbour()

def test_w_edge_crosses_into_previous_block():
    idx = _idx()
    # Block B leaf 0 sits at gx=2 (colidx=1, base_ix=2, leaf_x=0). Its W
    # neighbour is gx=1, which is block A's leaf 1 (colidx=0, leaf_x=1).
    handle = (LMR, BLK_B, LEAVES[(0, 1)][0])
    nb = idx.neighbour(handle, "W")
    assert (nb.gx, nb.gy) == (1, 0)
    assert nb.status == "resolved"
    assert nb.crossing == "cross_block"
    assert nb.handles == [(LMR, BLK_A, LEAVES[(0, 0)][1])]


def test_w_edge_of_grid_first_column_is_outside_coverage():
    idx = _idx()
    # Block A leaf 0 sits at gx=0 (colidx=0, base_ix=0, leaf_x=0): the
    # grid's first column. Its W neighbour is gx=-1, off the grid.
    handle = (LMR, BLK_A, LEAVES[(0, 0)][0])
    nb = idx.neighbour(handle, "W")
    assert nb.status == "outside_coverage"
    assert nb.gx == -1
    assert nb.handles == []


def test_cross_blockset_when_target_blockset_differs():
    idx = _idx()
    # Block C leaf 0 sits at gx=4 (colidx=2 -> bsx=1, blx=0; base_ix=4).
    # Its W neighbour is gx=3, which is block B's leaf 1 (colidx=1 ->
    # bsx=0, blx=1): a different bsx, so a different blockset.
    handle = (LMR, BLK_C, LEAVES[(1, 0)][0])
    nb = idx.neighbour(handle, "W")
    assert (nb.gx, nb.gy) == (3, 0)
    assert nb.status == "resolved"
    assert nb.crossing == "cross_blockset"


def test_divided_parent_returns_four_handles():
    idx = _idx()
    # Block C leaf 1 (gx=5) is divided into 4 sub-leaves.
    nb = idx.get(5, 0)
    assert nb.status == "resolved"
    assert nb.divided is True
    assert len(nb.handles) == 4
    assert [h[2][0] for h in nb.handles] == [(1, 0), (1, 1), (1, 2), (1, 3)]


def test_empty_slot_distinct_from_outside_coverage():
    idx = _idx()
    # gx=7, gy=0 is block D's leaf 1 (colidx=3 -> bsx=1, blx=1; leaf_x=1):
    # the block exists but that leaf slot is NO_DATA.
    nb = idx.get(7, 0)
    assert nb.status == "empty_slot"
    assert nb.handles == []
