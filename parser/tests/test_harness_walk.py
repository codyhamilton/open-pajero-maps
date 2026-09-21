"""L0 sparse coordinate frame in harness.walk (brief 2-05).

`alldata_writer.build_alldata_kwi` only supports a flat parcel_type-0 grid
with distinct leaf ranges, so it cannot build an L0 *sparse* tile (16 slots
aliasing one Map Frame). These tests drive the frame helpers `iter_parcels`
uses (`_leaf_frame`) with a synthetic parcel-management record instead."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk
from kiwiw.model import BoundingBox

W, H = 32, 64


def _lmr():
    return SimpleNamespace(n_parcels_lat=[H - 1, 0, 0, 0], n_parcels_lng=[W - 1, 0, 0, 0])


def _rec(sparse_tile=(1, 2)):
    ents = []
    for i in range(W * H):
        y, x = divmod(i, W)
        if (y // 4, x // 4) == sparse_tile:
            ents.append(SimpleNamespace(dsa=1000, size=4, subrecord=None))  # aliased
        else:
            ents.append(SimpleNamespace(dsa=2000 + i, size=4, subrecord=None))  # urban
    return SimpleNamespace(entries=ents, parcel_type=0)


BLOCK = BoundingBox(lat_lo=-30.0, lat_hi=-28.0, lon_lo=140.0, lon_hi=142.0)


def _frames(rec, tile):
    cache, out = {}, []
    for i in range(W * H):
        y, x = divmod(i, W)
        if (y // 4, x // 4) != tile:
            continue
        leaf = walk._narrow_bounds(BLOCK, H, W, i)
        out.append((leaf, *walk._leaf_frame(rec, 0, 0, (i,), leaf, BLOCK, _lmr(), cache)))
    return out


def test_l0_sparse_tile_leaves_distinct_and_frame_is_4x_tile():
    rows = _frames(_rec(), (1, 2))
    assert len(rows) == 16
    leaves = {(l.lat_lo, l.lon_lo) for l, _, _ in rows}
    assert len(leaves) == 16
    frames = {(f.lat_lo, f.lat_hi, f.lon_lo, f.lon_hi) for _, f, _ in rows}
    assert len(frames) == 1
    f = rows[0][1]
    leaf = rows[0][0]
    assert all(c == "l0_sparse_tile" for *_, c in rows)
    assert abs((f.lat_hi - f.lat_lo) - 4 * (leaf.lat_hi - leaf.lat_lo)) < 1e-12
    assert abs((f.lon_hi - f.lon_lo) - 4 * (leaf.lon_hi - leaf.lon_lo)) < 1e-12
    # the frame tiles exactly from the 16 leaf bboxes
    assert abs(f.lat_lo - min(l.lat_lo for l, _, _ in rows)) < 1e-12
    assert abs(f.lon_hi - max(l.lon_hi for l, _, _ in rows)) < 1e-12


def test_l0_urban_tile_frame_is_leaf():
    for leaf, f, cls in _frames(_rec(), (0, 0)):
        assert f is leaf and cls == "leaf"


def test_walkedparcel_frame_defaults_to_leaf_bounds():
    wp = walk.WalkedParcel(level=2, blockset_index=0, block_index=0, parcel_type=0,
                           leaf_path=(0,), bounds=BLOCK, file_offset=0, length=0,
                           parcel=None, error=None)
    assert wp.frame_bounds is BLOCK and wp.frame_class == "leaf"
