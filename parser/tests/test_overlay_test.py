import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import overlay_test as ot  # noqa: E402
from kiwiw.model import BoundingBox  # noqa: E402

TOL = 0.005
CELL = BoundingBox(lat_lo=-30.09, lat_hi=-30.0, lon_lo=150.0, lon_hi=150.104)
# The 2x2 parent of CELL when CELL is the south-west (sub 0) quadrant.
PARENT = BoundingBox(lat_lo=-30.09, lat_hi=-29.91, lon_lo=150.0, lon_hi=150.208)


def _fixture(range_=4096.0, y_up=True, frame=CELL, cell=CELL):
    """A street grid over `cell`, plus the same streets as R links whose raw
    coordinates are expressed in `frame` at `range_`."""
    ways, links = [], []
    for t in np.linspace(0.05, 0.95, 10):
        ways.append(np.array([[t, 0.0], [t, 1.0]]))
        ways.append(np.array([[0.0, t], [1.0, t]]))
    for w in ways:
        lon = cell.lon_lo + w[:, 0] * (cell.lon_hi - cell.lon_lo)
        lat = cell.lat_hi - w[:, 1] * (cell.lat_hi - cell.lat_lo)
        x = (lon - frame.lon_lo) / (frame.lon_hi - frame.lon_lo) * range_
        y = ((lat - frame.lat_lo) if y_up else (frame.lat_hi - lat)) / \
            (frame.lat_hi - frame.lat_lo) * range_
        pts = [(float(a), float(b)) for a, b in zip(x, y)]
        links.append({"pts": pts, "ends": [pts[0], pts[-1]]})
    return links, ways


def test_correct_range_passes():
    links, ways = _fixture()
    r = ot.analyze(links, ways, CELL, TOL, 4096.0)
    assert r["pass"], r
    assert r["matched_fraction"] == 1.0
    assert r["clip_exact_share"] == 1.0
    assert r["occupied_ratio"] >= 0.9


def test_wrong_scale_fails_clustering():
    links, _ = _fixture()
    _, ways = _fixture()
    r = ot.analyze(links, ways, CELL, TOL, ot.DECODER_RANGE)
    assert not r["criteria"]["no_clustering"]
    assert not r["criteria"]["coord_max"]
    assert not r["pass"]


def test_unclipped_ends_fail_edge_criterion():
    links, ways = _fixture()
    for l in links:
        l["ends"] = [(x, min(y, 4090.0)) for x, y in l["ends"]]
    r = ot.analyze(links, ways, CELL, TOL, 4096.0)
    assert not r["criteria"]["clipped_at_edge"]


def test_orientation_is_discriminated():
    """A y-up encoding read as y-down mirrors the cell north/south."""
    links, ways = _fixture(y_up=True)
    # asymmetric street set so the mirror is detectable
    ways = [w for w in ways if w[0][1] < 0.5 and w[-1][1] < 0.5] or ways
    links = [l for l in links if max(p[1] for p in l["pts"]) > 4096 * 0.5]
    up = ot.analyze(links, ways, CELL, TOL, 4096.0, y_up=True)
    dn = ot.analyze(links, ways, CELL, TOL, 4096.0, y_up=False)
    assert up["matched_fraction"] > dn["matched_fraction"]


def test_divided_parent_frame_beats_own_bounds():
    """Sub-parcel coordinates absolute in the parent frame at 4096: read in the
    sub's own bbox at 4096 they land in the wrong place."""
    links, ways = _fixture(range_=4096.0, frame=PARENT, cell=CELL)
    good = ot.analyze(links, ways, CELL, TOL, 4096.0, frame=PARENT)
    bad = ot.analyze(links, ways, CELL, TOL, 4096.0, frame=CELL)
    assert good["matched_fraction"] == 1.0
    assert bad["matched_fraction"] < 0.5
    assert good["inside_cell_fraction"] == 1.0


def test_pool_weights_every_link_once():
    links, ways = _fixture()
    a = ot.analyze(links, ways, CELL, TOL, 4096.0)
    p = ot.pool([a, a], TOL, [max(ot.extent_m(CELL))] * 2)
    assert p["cells"] == 2
    assert p["links"] == 2 * len(links)
    assert p["matched_fraction"] == 1.0
