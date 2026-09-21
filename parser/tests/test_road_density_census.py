import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import road_density_census as rdc  # noqa: E402

B = NS(lat_lo=-28.0, lat_hi=-27.0, lon_lo=153.0, lon_hi=154.0)


def _pt(x, y):
    # decoder convention: range 32768
    return (B.lat_hi - y / 32768 * 1.0, B.lon_lo + x / 32768 * 1.0)


def _wp(level, chains):
    links = [NS(points=[_pt(x, y) for x, y in ch], nodes=[]) for ch in chains]
    return NS(level=level, bounds=B, parcel=NS(road=NS(links=links)))


def test_counts_and_length():
    c = rdc.Census()
    # raw 0..4096 on x == one full cell width (1 deg lon) at coord_max 4096
    c.add(_wp(8, [[(0, 0), (2048, 0), (4096, 0)], [(0, 0), (0, 4096)]]))
    lv = c.to_dict()["levels"]["8"]
    assert lv["links"] == 2 and lv["vertices"] == 5
    assert lv["vertices_per_link"]["p50"] == 2.5
    import math
    exp = 111.32 * math.cos(math.radians(-27.5)) + 111.32
    assert abs(lv["length_km"] - exp) < 0.01


def test_sparse_l0_uses_16384():
    c = rdc.Census()
    c.add(_wp(0, [[(0, 0), (10000, 0)]]))
    assert c.to_dict()["levels"]["0"]["parcels_by_coord_max"] == {"16384": 1}


def test_skips_empty_and_deterministic():
    c = rdc.Census()
    c.add(NS(level=2, bounds=B, parcel=None))
    c.add(_wp(2, [[(0, 0), (100, 100)]]))
    a = json.dumps(c.to_dict(), sort_keys=True)
    assert a == json.dumps(c.to_dict(), sort_keys=True)
    assert list(c.to_dict()["levels"]) == ["2"]


def test_shared_frames_counted_once():
    c = rdc.Census()
    for _ in range(3):
        w = _wp(0, [[(0, 0), (100, 0)]])
        w.file_offset, w.length = 4096, 64
        c.add(w)
    assert c.to_dict()["levels"]["0"]["links"] == 1
