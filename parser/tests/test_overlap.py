"""Plan 03, 3-09: a background shape is written by every existing cell (and
divided sub-parcel) whose rectangle it overlaps, as R does -- not only by the
cell holding its centroid. Each cell clips it to its own rectangle (3-07), so
the two sides of a boundary meet at identical global raw coordinates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata
from harness import walk
from kiwiw import overlap
from kiwiw.model import BackgroundShape, NameRecord
from kiwiw.spool import SpoolWriter
from osm_to_parcel_geometry import TileGrid, parcel_bounds

LEVEL = 6


def _bg(ring, type_code=288, cls=2):
    return BackgroundShape(shape_class=cls, type_code=type_code, type_label="",
                           n_coords=len(ring) - 1, mult_const=1, underground=False,
                           pen_up=False, coords=list(ring))


def _name(lat, lon):
    return NameRecord(string_type=6, type_code=0, type_label="", priority=0,
                      vertical=False, display_scale_flag=0, text="x", lat=lat, lon=lon)


def _box(lat0, lon0, lat1, lon1):
    return [(lat0, lon0), (lat0, lon1), (lat1, lon1), (lat1, lon0), (lat0, lon0)]


def _global_raw(path):
    """{(ix, iy): [[(X, Y), ...] per shape]} in the level's global raw lattice."""
    g = TileGrid.from_reference(LEVEL)
    out = {}
    for wp in walk.iter_parcels(str(path)):
        if wp.level != LEVEL or wp.parcel is None or wp.parcel.background is None:
            continue
        fb, rng = wp.frame_bounds, wp.frame_range
        ix = round((wp.bounds.lon_lo - g.disc_lon_lo) / g.cell_lon)
        iy = round((wp.bounds.lat_lo - g.disc_lat_lo) / g.cell_lat)
        fx0 = round((fb.lon_lo - g.disc_lon_lo) / g.cell_lon) * rng
        fy0 = round((fb.lat_lo - g.disc_lat_lo) / g.cell_lat) * rng
        shapes = []
        for sh in wp.parcel.background.shapes:
            shapes.append([(fx0 + round((lon - fb.lon_lo) / (fb.lon_hi - fb.lon_lo) * rng),
                            fy0 + round((lat - fb.lat_lo) / (fb.lat_hi - fb.lat_lo) * rng))
                           for lat, lon in sh.coords])
        if shapes:
            out.setdefault((ix, iy), []).extend(shapes)
    return out


def _build(tmp_path, adds, workers=1, fixture=None, tag="b"):
    spool = tmp_path / f"spool_{tag}"
    if not spool.exists():
        with SpoolWriter(str(spool)) as w:
            for ix, iy, kw in adds:
                w.add(LEVEL, ix, iy, **kw)
    out = tmp_path / f"{tag}_j{workers}" / "ALLDATA.KWI"
    rc = build_alldata.run(spool_dir=str(spool), out_path=str(out), levels=[LEVEL],
                           fixture=fixture, disk_title="TEST", fill_mask=False,
                           workers=workers)
    assert rc == 0
    return out


def _cell(ix, iy):
    return parcel_bounds(ix, iy, TileGrid.from_reference(LEVEL))


def test_straddling_shape_is_written_by_both_cells(tmp_path):
    a, b = _cell(20, 20), _cell(21, 20)
    # Centroid in cell 20 (lon 130.5..132.5 around the 132 boundary).
    ring = _box(a.lat_lo + 0.3, a.lon_lo + 0.5, a.lat_lo + 0.8, b.lon_lo + 0.5)
    out = _build(tmp_path, [(20, 20, {"backgrounds": [_bg(ring)]}),
                            (21, 20, {"names": [_name(b.lat_lo + 0.1, b.lon_lo + 0.1)]})])
    got = _global_raw(out)
    assert (20, 20) in got and (21, 20) in got, got.keys()
    xb = 21 * 4096
    left = {p for s in got[(20, 20)] for p in s if p[0] == xb}
    right = {p for s in got[(21, 20)] for p in s if p[0] == xb}
    assert len(left) >= 2 and left == right  # densified along the boundary


def test_cell_inside_large_polygon_gets_frame_rectangle(tmp_path):
    a = _cell(20, 20)
    c = _cell(23, 23)
    ring = _box(a.lat_lo + 0.2, a.lon_lo + 0.2, c.lat_hi - 0.2, c.lon_hi - 0.2)
    adds = [(21, 21, {"backgrounds": [_bg(ring)]})]
    for ix in range(20, 24):
        for iy in range(20, 24):
            if (ix, iy) != (21, 21):
                cb = _cell(ix, iy)
                adds.append((ix, iy, {"names": [_name(cb.lat_lo + 0.1, cb.lon_lo + 0.1)]}))
    adds.append((25, 25, {"names": [_name(_cell(25, 25).lat_lo + 0.1,
                                          _cell(25, 25).lon_lo + 0.1)]}))
    out = _build(tmp_path, adds)
    got = _global_raw(out)
    assert set(got) == {(ix, iy) for ix in range(20, 24) for iy in range(20, 24)}
    x0, y0 = 22 * 4096, 22 * 4096
    rect = {(x0, y0), (x0 + 4096, y0), (x0 + 4096, y0 + 4096), (x0, y0 + 4096)}
    pts = set(got[(22, 22)][0])
    assert len(got[(22, 22)]) == 1 and rect <= pts  # densified along its edges
    assert all(x in (x0, x0 + 4096) or y in (y0, y0 + 4096) for x, y in pts)


def test_line_goes_to_every_crossed_cell_only(tmp_path):
    a, d = _cell(20, 20), _cell(22, 20)
    line = [(a.lat_lo + 0.5, a.lon_lo + 0.5), (a.lat_lo + 0.5, d.lon_lo + 0.5)]
    adds = [(21, 20, {"backgrounds": [_bg(line, type_code=5, cls=1)]})]
    for ix, iy in ((20, 20), (22, 20), (21, 21)):
        cb = _cell(ix, iy)
        adds.append((ix, iy, {"names": [_name(cb.lat_lo + 0.1, cb.lon_lo + 0.1)]}))
    got = _global_raw(_build(tmp_path, adds))
    assert set(got) == {(20, 20), (21, 20), (22, 20)}


def test_order_and_worker_independence(tmp_path):
    """Own shapes first in spool order, then borrowed ones by source (iy, ix)
    and spool index; identical bytes at any worker count."""
    t = _cell(21, 21)
    adds = [(21, 21, {"backgrounds": [_bg(_box(t.lat_lo + .1, t.lon_lo + .1,
                                                  t.lat_lo + .2, t.lon_lo + .2), 11)]})]
    # Neighbours whose shapes reach into (21, 21), added out of key order.
    for (ix, iy), code in (((22, 21), 13), ((20, 21), 12), ((21, 22), 14), ((21, 20), 10)):
        b = _cell(ix, iy)
        cx, cy = (b.lon_lo + b.lon_hi) / 2, (b.lat_lo + b.lat_hi) / 2
        tx, ty = (t.lon_lo + t.lon_hi) / 2, (t.lat_lo + t.lat_hi) / 2
        ring = _box(min(cy, ty) - .1, min(cx, tx) - .1, max(cy, ty) + .1, max(cx, tx) + .1)
        adds.append((ix, iy, {"backgrounds": [_bg(ring, code)]}))
    outs = [_build(tmp_path, adds, workers=j, tag="o") for j in (1, 3)]
    assert outs[0].read_bytes() == outs[1].read_bytes()
    types = []
    for wp in walk.iter_parcels(str(outs[0])):
        if wp.level == LEVEL and wp.parcel and abs(wp.bounds.lon_lo - t.lon_lo) < 1e-9 \
                and abs(wp.bounds.lat_lo - t.lat_lo) < 1e-9:
            types = [s.type_code for s in wp.parcel.background.shapes]
    # own (11), then sources by (iy, ix): (21,20)=10, (20,21)=12, (22,21)=13, (21,22)=14
    assert types == [11, 10, 12, 13, 14]


def test_shape_cells_supercover_and_interior():
    # A diagonal segment through cell space, and a big square polygon.
    edge, inner = overlap.shape_cells([0.5, 3.5], [0.5, 2.5], closed=False)
    assert (0, 0) in edge and (3, 2) in edge and not inner
    edge, inner = overlap.shape_cells([0.5, 5.5, 5.5, 0.5, 0.5],
                                      [0.5, 0.5, 5.5, 5.5, 0.5], closed=True)
    assert set(inner) == {(x, y) for x in range(1, 5) for y in range(1, 5)}
    assert (0, 0) in edge and (5, 5) in edge and (3, 0) in edge


def _order_adds():
    t = _cell(21, 21)
    adds = [(21, 21, {"backgrounds": [_bg(_box(t.lat_lo + .1, t.lon_lo + .1,
                                                  t.lat_lo + .2, t.lon_lo + .2), 11)]})]
    for (ix, iy), code in (((22, 21), 13), ((20, 21), 12), ((21, 22), 14), ((21, 20), 10)):
        b = _cell(ix, iy)
        ring = _box(b.lat_lo + .2, b.lon_lo + .2, t.lat_hi - .2, t.lon_hi - .2) \
            if (ix, iy) < (21, 21) else _box(t.lat_lo + .3, t.lon_lo + .3, b.lat_hi - .2,
                                              b.lon_hi - .2)
        adds.append((ix, iy, {"backgrounds": [_bg(ring, code)]}))
    return adds


def test_python_path_matches_c_path(tmp_path, monkeypatch):
    """The object/Python encoders give the same bytes as the C kernel with
    borrowed shapes merged in."""
    from kiwiw import cenc
    adds = _order_adds()
    c_out = _build(tmp_path, adds, tag="p").read_bytes()
    monkeypatch.setattr(cenc, "make_encoder", lambda *a, **k: None)
    monkeypatch.setattr(cenc, "bg_shape_records", lambda *a: None)
    monkeypatch.setattr(cenc, "measure_content", lambda *a, **k: None)
    py_out = _build(tmp_path, adds, workers=2, tag="p").read_bytes()
    assert c_out == py_out


def test_divided_sub_parcels_get_every_overlapping_shape():
    """`divide._retile_content`: a shape crossing the 2x2 midline goes to both
    halves, a shape inside one quadrant only to it."""
    from kiwiw import divide
    from osm_to_parcel_geometry import frame_bounds
    g = TileGrid.from_reference(LEVEL)
    fb = frame_bounds(20, 20, g)
    mlat, mlon = (fb.lat_lo + fb.lat_hi) / 2, (fb.lon_lo + fb.lon_hi) / 2
    cross = _bg(_box(fb.lat_lo + .1, mlon - .2, fb.lat_lo + .3, mlon + .2), 1)
    inside = _bg(_box(fb.lat_lo + .1, fb.lon_lo + .1, fb.lat_lo + .2, fb.lon_lo + .2), 2)
    big = _bg(_box(fb.lat_lo - 1, fb.lon_lo - 1, fb.lat_hi + 1, fb.lon_hi + 1), 3)
    sub = divide._sub_tile_grid(LEVEL, fb, 2, 2)
    out = divide._retile_content({"backgrounds": [cross, inside, big]}, sub, fb)
    types = {c: [s.type_code for s in v["backgrounds"]] for c, v in out.items()}
    assert types == {(0, 0): [1, 2, 3], (1, 0): [1, 3], (0, 1): [3], (1, 1): [3]}
