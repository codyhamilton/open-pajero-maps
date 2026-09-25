"""Exercises the layer (a) boundary-test helpers (`parser/tests/boundary.py`,
Contract T, plan 03 3C-02) -- not the C pipeline itself, which has nothing to
port yet in this unit. On a hand-built fixture spool, and on real frames
from `output/scratch-3-11/perth_j1` (skipped if that scratch build is
absent -- it is a large, regenerable, gitignored build product, not a
committed fixture)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boundary
from harness import walk
from kiwiw.model import BoundingBox, RoadLink, RoadNode

PERTH_ALLDATA = Path(__file__).resolve().parent.parent.parent / \
    "output/scratch-3-11/perth_j1/ALLDATA.KWI"


def _road_link(nodes, points):
    return RoadLink(
        display_class=0, road_type=0, altitude_flag=False, route_planning_tag=False,
        route_type_guidance_flag=False, pseudo3d_updown=0, link_id_flag=False,
        selected_link_flag=False, toll_flag=False, route_number_flag=False,
        infra_link_flag=False, link_id_number_flag=False, n_nodes=len(nodes),
        nodes=nodes, points=points, link_id=0, osm_way_id=None, ordinal=0)


def test_write_and_read_fixture_spool(tmp_path):
    nodes = [
        RoadNode(x=0, y=0, lat=-31.95, lon=115.86, oneway=0, planned=0,
                 tunnel=False, bridge=False),
        RoadNode(x=100, y=200, lat=-31.94, lon=115.87, oneway=0, planned=0,
                 tunnel=False, bridge=False),
    ]
    link = _road_link(nodes, points=[(-31.95, 115.86), (-31.94, 115.87)])
    spool_dir = tmp_path / "spool"
    boundary.write_fixture_spool(spool_dir, {(0, 3, 4): {"roads": [link]}})

    reader = boundary.open_spool(spool_dir)
    try:
        cells = list(reader.iter_level(0))
    finally:
        reader.close()
    assert len(cells) == 1
    ix, iy, content = cells[0]
    assert (ix, iy) == (3, 4)
    assert len(content["roads"]) == 1
    got = content["roads"][0]
    assert got.link_id == 0 and got.n_nodes == 2
    assert [(n.x, n.y) for n in got.nodes] == [(0, 0), (100, 200)]


def test_road_node_range_invariant():
    nodes = [RoadNode(x=0, y=0, lat=0, lon=0, oneway=0, planned=0,
                       tunnel=False, bridge=False),
             RoadNode(x=4096, y=4096, lat=0, lon=0, oneway=0, planned=0,
                       tunnel=False, bridge=False)]
    boundary.assert_road_nodes_in_range(nodes, coord_range=4096)
    bad = [RoadNode(x=4097, y=0, lat=0, lon=0, oneway=0, planned=0,
                     tunnel=False, bridge=False)]
    with pytest.raises(AssertionError):
        boundary.assert_road_nodes_in_range(bad, coord_range=4096)


def test_latlon_bounds_invariant():
    bounds = BoundingBox(lat_lo=-32.0, lat_hi=-31.9, lon_lo=115.8, lon_hi=115.9,
                          coord_range=4096)
    boundary.assert_latlon_in_bounds([(-31.95, 115.85)], bounds)
    with pytest.raises(AssertionError):
        boundary.assert_latlon_in_bounds([(-32.5, 115.85)], bounds)


def test_delta_representable_invariant():
    boundary.assert_delta_representable([0, 128 * 100, 128 * 4], mult_const=128)
    with pytest.raises(AssertionError):
        boundary.assert_delta_representable([0, 128 * 200], mult_const=128)  # 200 > 127
    with pytest.raises(AssertionError):
        boundary.assert_delta_representable([0, 130], mult_const=128)  # not a multiple


def test_frame_size_ceiling_invariant():
    boundary.assert_frame_size_ceiling(b"x" * 100, limit=1000)
    with pytest.raises(AssertionError):
        boundary.assert_frame_size_ceiling(b"x" * 1001, limit=1000)


@pytest.mark.skipif(not PERTH_ALLDATA.exists(), reason="output/scratch-3-11/perth_j1 absent")
def test_invariants_on_real_perth_frames():
    checked = 0
    for wp in walk.iter_parcels(str(PERTH_ALLDATA)):
        if wp.parcel is None or wp.frame_range is None:
            continue
        rng = wp.frame_range
        if wp.parcel.road is not None:
            nodes = [n for link in wp.parcel.road.links for n in link.nodes]
            boundary.assert_road_nodes_in_range(nodes, rng)
        if wp.parcel.background is not None:
            for shape in wp.parcel.background.shapes:
                boundary.assert_latlon_in_bounds(shape.coords, wp.frame_bounds)
        for frame in (wp.parcel.road, wp.parcel.background, wp.parcel.name):
            if frame is not None:
                boundary.assert_frame_size_ceiling(b"x" * frame.frame_size)
        checked += 1
        if checked >= 25:
            break
    assert checked > 0, "no decodable leaf parcels found in perth_j1"
