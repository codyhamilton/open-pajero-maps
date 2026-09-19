"""C whole-cell encoder (plan 03): byte-identical to the Python oracle."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata as B
from kiwiw import cenc, divide, spool, synth
from kiwiw.model import BackgroundShape, BoundingBox, NameRecord, RoadLink, RoadNode
from osm_to_parcel_geometry import TileGrid, parcel_bounds

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")

KL = {"road": 131070, "background": 131070, "name": 131070}
LEVELS = (12, 8, 6, 4, 0)


def _cell_latlon(level, ix, iy, g):
    b = parcel_bounds(ix, iy, g)
    return b, random.Random(level * 1000 + ix * 31 + iy)


def _content(rng, b, n_roads, n_bgs, n_names):
    def pt():
        return (rng.uniform(b.lat_lo, b.lat_hi), rng.uniform(b.lon_lo, b.lon_hi))
    roads = []
    for i in range(n_roads):
        nodes = [RoadNode(x=rng.choice([0, 0, 5, 300, 1000]), y=rng.choice([0, 7, 900]),
                          lat=pt()[0], lon=pt()[1], oneway=rng.randint(0, 2),
                          planned=rng.randint(0, 1), tunnel=bool(rng.getrandbits(1)),
                          bridge=bool(rng.getrandbits(1)))
                 for _ in range(rng.randint(2, 6))]
        roads.append(RoadLink(
            display_class=rng.randint(0, 4), road_type=rng.randint(0, 8),
            altitude_flag=False, route_type_guidance_flag=bool(rng.getrandbits(1)),
            pseudo3d_updown=rng.randint(0, 2), route_planning_tag=False,
            link_id_flag=False, selected_link_flag=False, toll_flag=bool(rng.getrandbits(1)),
            route_number_flag=False, infra_link_flag=False, link_id_number_flag=False,
            n_nodes=len(nodes), nodes=nodes, points=[pt() for _ in range(rng.randint(0, 3))],
            link_id=i, osm_way_id=None, ordinal=i))
    bgs = []
    for i in range(n_bgs):
        k = rng.choice([1, 2, 3, 6, 40])
        bgs.append(BackgroundShape(
            shape_class=rng.randint(0, 2), type_code=rng.randint(0, 30),
            type_label="bg", n_coords=k, mult_const=rng.choice([0, 1, 2]),
            underground=bool(rng.getrandbits(1)), pen_up=bool(rng.getrandbits(1)),
            coords=[pt() for _ in range(k)]))
    names = []
    for i in range(n_names):
        names.append(NameRecord(
            string_type=rng.choice([1, 2, 5, 6]), type_code=rng.randint(0, 20),
            type_label="l", priority=rng.randint(0, 8), vertical=bool(rng.getrandbits(1)),
            display_scale_flag=rng.randint(0, 2),
            text=rng.choice(["Main St", "Émile Rd", "東京", "a", "ab", "x" * 33]),
            lat=pt()[0], lon=pt()[1],
            angle_deg=rng.choice([None, 12.5, 359.9]), angle_flags=rng.randint(0, 3)))
    return {"roads": roads, "backgrounds": bgs, "names": names}


def _oracle(level, ix, iy, g, content):
    try:
        fr, sz = B._measure_one(level, ix, iy, parcel_bounds(ix, iy, g), content)
    except ValueError:
        return None
    if len(fr) > 131070 or divide._kind_breach(sz, KL):
        return None
    return fr


@pytest.fixture()
def no_c_bg(monkeypatch):
    monkeypatch.setattr(cenc, "bg_shape_bytes", lambda *a: None)


@pytest.mark.parametrize("level", LEVELS)
def test_kernel_matches_python(level, tmp_path, no_c_bg):
    g = TileGrid.from_reference(level)
    enc = cenc.make_encoder(level, g, 131070, KL)
    cells = []
    for n, (nr, nb, nn) in enumerate([(0, 0, 0), (1, 0, 0), (5, 2, 3), (0, 3, 0),
                                      (0, 0, 4), (30, 10, 10), (400, 20, 50), (2000, 5, 5)]):
        ix, iy = 3 + n, 7 + 2 * n
        b = parcel_bounds(ix, iy, g)
        cells.append((ix, iy, _content(random.Random(n + level), b, nr, nb, nn)))
    w = spool.SpoolWriter(tmp_path / "sp")
    for ix, iy, c in cells:
        w.add(level, ix, iy, roads=c["roads"], backgrounds=c["backgrounds"], names=c["names"])
    w.close()
    raws = {(ix, iy): raw for ix, iy, raw in spool.SpoolReader(tmp_path / "sp").iter_cell_raw(level)}
    assert raws
    for ix, iy, c in cells:
        # the reader returns the round-tripped content, which is what the oracle sees
        rc = spool.columns_to_content(spool.decode_columns(raws[(ix, iy)])) \
            if (ix, iy) in raws else spool._empty_content()
        want = _oracle(level, ix, iy, g, rc)
        got = enc.encode(raws.get((ix, iy)), ix, iy)
        assert got == want, (level, ix, iy)


def test_empty_cell(no_c_bg):
    g = TileGrid.from_reference(0)
    enc = cenc.make_encoder(0, g, 131070, KL)
    assert enc.encode(None, 5, 5) == _oracle(0, 5, 5, g, spool._empty_content())


def test_column_table_matches_spool():
    lib = cenc._load_lib()
    import ctypes
    lib.kw_ncols.restype = lib.kw_col_size.restype = lib.kw_col_key.restype = ctypes.c_int
    lib.kw_col_size.argtypes = lib.kw_col_key.argtypes = [ctypes.c_int]
    assert lib.kw_ncols() == len(spool._COLUMNS)
    for i, (name, dt, key) in enumerate(spool._COLUMNS):
        assert lib.kw_col_size(i) == spool.np.dtype(dt).itemsize, name
        assert lib.kw_col_key(i) == spool._COUNT_KEYS.index(key), name


def test_bg_shape_matches_scalar():
    rng = random.Random(7)
    b = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0)
    for k in (1, 2, 3, 5, 50, 700):
        for mult in (0, 1, 3):
            s = BackgroundShape(
                shape_class=1, type_code=5, type_label="", n_coords=k, mult_const=mult,
                underground=bool(k & 1), pen_up=bool(k & 2),
                coords=[(rng.uniform(-32.1, -30.9), rng.uniform(114.9, 116.1)) for _ in range(k)])
            got = cenc.bg_shape_bytes(s, b)
            if got is not None:
                assert got == synth.encode_background_shape_bytes_scalar(s, b), (k, mult)


def test_measure_content_matches_python(no_c_bg, monkeypatch):
    """The C probe (used on the divide path) equals the Python encoders, incl. sizes."""
    g = TileGrid.from_reference(0)
    checked = 0
    for n, (nr, nb, nn) in enumerate([(0, 0, 0), (3, 2, 4), (12, 8, 9)]):
        ix, iy = 5 + n, 9 + n
        b = parcel_bounds(ix, iy, g)
        c = _content(random.Random(n), b, nr, nb, nn)
        got = cenc.measure_content(0, ix, iy, b, c)
        if got is None:  # ceiling / unmodelled input: caller uses the Python path
            continue
        with monkeypatch.context() as m:
            m.setattr(cenc, "measure_content", lambda *a: None)
            assert got == B._measure_one(0, ix, iy, b, c)
        checked += 1
    assert checked
