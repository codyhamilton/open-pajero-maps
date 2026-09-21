import inspect
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import coord_scale_census as csc  # noqa: E402

B = NS(lat_lo=-28.0, lat_hi=-27.0, lon_lo=153.0, lon_hi=154.0)


def _pt(x, y):
    return (B.lat_hi - y / 32768.0, B.lon_lo + x / 32768.0)


def _wp(level, nodes, points=(), bg=()):
    link = NS(nodes=[NS(x=x, y=y) for x, y in nodes], points=[_pt(x, y) for x, y in points])
    parcel = NS(road=NS(links=[link]),
                background=NS(shapes=[NS(coords=[_pt(x, y) for x, y in bg])]))
    return NS(level=level, bounds=B, parcel=parcel)


def test_measure_covers_nodes_points_background():
    m = csc.parcel_measure(_wp(2, [(0, 10), (4096, 20)], points=[(100, 3000)], bg=[(50, 4000)]))
    assert m["max_x"] == 4096 and m["max_y"] == 4000
    assert m["max"] == 4096 and m["end_max"] == 4096 and m["road_max"] == 4096


def test_measure_empty_parcel_is_none():
    assert csc.parcel_measure(NS(level=2, bounds=B, parcel=None)) is None


def test_class_rule_takes_no_content():
    params = list(inspect.signature(csc.parcel_class).parameters)
    assert params == ["level", "division", "grid", "urban_tiles"]
    tiles = {(1, 2, 0, 1)}
    assert csc.parcel_class(4, 0, (1, 2, 5), tiles) == "full"
    assert csc.parcel_class(0, 1, (1, 2, 5), tiles) == "divided"
    # leaf 4 -> x=4,y=0 -> tile (0,1): urban; leaf 0 -> tile (0,0): sparse
    assert csc.parcel_class(0, 0, (1, 2, 4), tiles) == "urban"
    assert csc.parcel_class(0, 0, (1, 2, 0), tiles) == "sparse"


def _rec(level, bs, blk, path, div, mx):
    return {"level": level, "bs": bs, "blk": blk, "path": path, "div": div, "max": mx,
            "hdr": [0] * 18}


def test_urban_tile_derivation_and_aggregate_deterministic():
    recs = [_rec(0, 1, 1, [0], 0, 16384), _rec(0, 1, 1, [1], 0, 16384),  # tile (0,0) off-anchor
            _rec(0, 1, 1, [4], 0, 16384),                                # anchor only: sparse
            _rec(2, 1, 1, [0], 0, 4096), _rec(2, 1, 1, [1], 0, 4000),
            _rec(2, 1, 1, [0, 0], 1, 2048)]
    tiles = csc.derive_urban_tiles(recs)
    assert tiles == {(1, 1, 0, 0)}
    a = csc.aggregate(recs, tiles)
    assert a == csc.aggregate(list(recs), set(tiles))
    assert a["2"]["full"]["normal"]["max"] == 4096 and a["2"]["full"]["normal"]["n"] == 2
    assert a["2"]["divided"]["pardiv1_sub0"]["max"] == 2048
    assert a["0"]["urban"]["normal"]["n"] == 2 and a["0"]["sparse"]["normal"]["n"] == 1


def test_bucket_and_exceptions():
    recs = [_rec(4, 0, 0, [i], 0, 4096) for i in range(3)] + [_rec(4, 0, 0, [9], 0, 900)]
    e = csc.aggregate(recs, set())["4"]["full"]["normal"]
    assert e["max"] == 4096 and e["share_at_max"] == 0.75
    assert e["exceptions"]["count"] == 1 and e["exceptions"]["examples"][0]["max"] == 900
