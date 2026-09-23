"""`coord_scale` check (plan 03, unit 3-04): zero parcels exceeding their
class range. Synthetic `WalkedParcel`s, no disc."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from harness import walk  # noqa: E402
from harness.checks import coord_scale  # noqa: E402
from kiwiw.model import BoundingBox  # noqa: E402

_BOX = BoundingBox(lat_lo=-30.0, lat_hi=-29.0, lon_lo=150.0, lon_hi=151.0)
_OFF = [0]


def _node(x, y):
    return SimpleNamespace(x=x, y=y)


def _wp(level, x, *, ptype=0, leaf_path=(0,), frame_class="leaf", bg=None, offset=None):
    rng = walk.leaf_frame_range(level, ptype, leaf_path, frame_class)
    road = SimpleNamespace(links=[SimpleNamespace(nodes=[_node(0, 0), _node(x, 10)], points=[])])
    parcel = SimpleNamespace(road=road, background=bg)
    if offset is None:
        _OFF[0] += 1
        offset = _OFF[0]
    return walk.WalkedParcel(level=level, blockset_index=1, block_index=2, parcel_type=ptype,
                             leaf_path=leaf_path, bounds=_BOX, file_offset=offset, length=64,
                             parcel=parcel, error=None, frame_bounds=_BOX, frame_range=rng,
                             frame_class=frame_class)


def _status(*wps):
    return coord_scale.judge(list(wps))


def test_one_raw_unit_over_range_fails():
    r = _status(_wp(2, 4097))
    assert r.status == "FAIL"
    assert r.details["parcels_exceeding"] == 1
    assert r.details["per_class"]["2/full/normal"]["observed_max"] == 4097


def test_exactly_at_range_passes():
    r = _status(_wp(2, 4096))
    assert r.status == "PASS", r.message
    assert r.details["per_class"]["2/full/normal"] == {
        "range": 4096, "parcels": 1, "observed_max": 4096, "observed_min": 0, "exceeding": 0}


def test_negative_vertex_fails():
    wp = _wp(2, 10)
    wp.parcel.road.links[0].nodes[0].x = -1
    assert _status(wp).status == "FAIL"


def test_l0_sparse_judged_at_16384():
    assert _status(_wp(0, 16384, frame_class="l0_sparse_tile")).status == "PASS"
    r = _status(_wp(0, 16385, frame_class="l0_sparse_tile"))
    assert r.status == "FAIL"
    assert r.details["per_class"]["0/sparse/normal"]["range"] == 16384


def test_l0_urban_judged_at_4096():
    assert _status(_wp(0, 4096)).status == "PASS"
    r = _status(_wp(0, 4097))
    assert r.status == "FAIL"
    assert r.details["per_class"]["0/urban/normal"]["range"] == 4096


def test_divided_sub_parcel_judged_at_4096_not_2048():
    kw = dict(ptype=1, leaf_path=(5, 0), frame_class="divided_parent")
    r = _status(_wp(0, 4096, **kw))
    assert r.status == "PASS", r.message  # 2048 would fail this
    assert r.details["per_class"]["0/divided/pardiv1_sub0"]["range"] == 4096
    assert _status(_wp(0, 4097, **kw)).status == "FAIL"


def test_background_vertex_inverted_at_frame_range():
    # lon one full frame-width east of the frame's lo edge = raw 4096 (legal);
    # beyond it, one raw unit over.
    step = (_BOX.lon_hi - _BOX.lon_lo) / 4096
    ok = SimpleNamespace(shapes=[SimpleNamespace(coords=[(-29.5, _BOX.lon_hi)])])
    bad = SimpleNamespace(shapes=[SimpleNamespace(coords=[(-29.5, _BOX.lon_hi + step)])])
    assert _status(_wp(2, 1, bg=ok)).status == "PASS"
    assert _status(_wp(2, 1, bg=bad)).status == "FAIL"


def test_aliased_frame_judged_once_and_mixed_verdict_counts():
    a = _wp(0, 20000, frame_class="l0_sparse_tile", offset=999)
    b = _wp(0, 20000, frame_class="l0_sparse_tile", offset=999)
    r = _status(a, b, _wp(2, 100))
    assert r.details["parcels_judged"] == 2
    assert r.details["parcels_exceeding"] == 1
    assert r.status == "FAIL"


def test_pardiv2_is_ranged_at_parent_4096():
    # 3-03 amendment: any pardiv<t>_sub<i> is the parent slot's 4096 frame.
    wp = _wp(2, 10, ptype=2, leaf_path=(0, 0), frame_class="divided_parent")
    assert wp.frame_range == 4096


def test_unranged_class_fails():
    # Genuinely unranged frames: a level coord_scale.json does not know, and
    # a divided sub-parcel at a level with no divided class (L10).
    for wp in (_wp(5, 10), _wp(10, 10, ptype=1, leaf_path=(0, 0),
                                frame_class="divided_parent")):
        assert wp.frame_range is None
        r = _status(wp)
        assert r.status == "FAIL" and r.details["parcels_unranged"] == 1


def test_registered():
    assert [c.id for c in coord_scale.CHECKS] == ["coord_scale"]
    assert coord_scale.CHECKS[0].layer == "map"
