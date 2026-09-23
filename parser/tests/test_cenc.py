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
            got = cenc.bg_shape_bytes(s, b, 32768)
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


# ---------------------------------------------------------------- 3-02: the
# coordinate range is a parameter of both encoders, not a constant either owns.

RANGES = (32768, 16384, 4096)
_C_BG = cenc.bg_shape_bytes


@pytest.fixture()
def pure_py(monkeypatch):
    """The Python encoders alone (no C probe, no C background shapes)."""
    monkeypatch.setattr(cenc, "bg_shape_bytes", lambda *a: None)
    monkeypatch.setattr(cenc, "measure_content", lambda *a, **k: None)


def _encodable(c):
    """`_content` draws oneway=2, which overflows the node word and makes
    both encoders decline the cell; keep these cells encodable."""
    for lk in c["roads"]:
        for nd in lk.nodes:
            nd.oneway &= 1
    return c


def _ranged(b, r):
    import dataclasses
    return dataclasses.replace(b, coord_range=r)


@pytest.mark.parametrize("coord_range", RANGES)
@pytest.mark.parametrize("level", (8, 0))
def test_kernel_matches_python_at_range(level, coord_range, tmp_path, pure_py):
    """Road links, background shapes and names: C kernel == Python oracle at
    each supplied range (Python reads the range from `bounds.coord_range`)."""
    g = TileGrid.from_reference(level)
    enc = cenc.make_encoder(level, g, 131070, KL)
    cells = []
    for n, (nr, nb, nn) in enumerate([(1, 0, 0), (5, 2, 3), (30, 10, 10), (200, 20, 40)]):
        ix, iy = 4 + n, 6 + 2 * n
        cells.append((ix, iy, _encodable(_content(random.Random(n * 7 + level),
                                                  parcel_bounds(ix, iy, g), nr, nb, nn))))
    w = spool.SpoolWriter(tmp_path / "sp")
    for ix, iy, c in cells:
        w.add(level, ix, iy, roads=c["roads"], backgrounds=c["backgrounds"], names=c["names"])
    w.close()
    raws = {(ix, iy): raw for ix, iy, raw in spool.SpoolReader(tmp_path / "sp").iter_cell_raw(level)}
    checked = 0
    for ix, iy, _c in cells:
        rc = spool.columns_to_content(spool.decode_columns(raws[(ix, iy)]))
        b = _ranged(parcel_bounds(ix, iy, g), coord_range)
        try:
            fr, sz = B._measure_one(level, ix, iy, b, rc)
        except ValueError:
            fr = None
        want = None if fr is None or len(fr) > 131070 or divide._kind_breach(sz, KL) else fr
        got = enc.encode(raws[(ix, iy)], ix, iy, coord_range=coord_range)
        assert got == want, (level, coord_range, ix, iy)
        checked += want is not None
    assert checked


@pytest.mark.parametrize("coord_range", RANGES)
def test_bg_shape_matches_scalar_at_range(coord_range, monkeypatch):
    rng = random.Random(coord_range)
    b = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0,
                    coord_range=coord_range)
    got_any = False
    for k in (2, 3, 50, 700):
        for mult in (0, 1, 3):
            s = BackgroundShape(
                shape_class=1, type_code=5, type_label="", n_coords=k, mult_const=mult,
                underground=False, pen_up=False,
                coords=[(rng.uniform(-32.1, -30.9), rng.uniform(114.9, 116.1)) for _ in range(k)])
            want = synth.encode_background_shape_bytes_scalar(s, b)
            got = cenc.bg_shape_bytes(s, b, coord_range)
            if got is not None:
                got_any = True
                assert got == want, (k, mult)
            assert synth._bg_fast(s, b, coord_range) == want, (k, mult)  # via C
            with monkeypatch.context() as m:  # the numpy path
                m.setattr(cenc, "bg_shape_bytes", lambda *a: None)
                assert synth._bg_fast(s, b, coord_range) == want, (k, mult)
    assert got_any


@pytest.mark.parametrize("coord_range", RANGES)
def test_measure_content_matches_python_at_range(coord_range, no_c_bg, monkeypatch):
    g = TileGrid.from_reference(0)
    checked = 0
    for n, (nr, nb, nn) in enumerate([(3, 2, 4), (12, 8, 9)]):
        ix, iy = 5 + n, 9 + n
        b = _ranged(parcel_bounds(ix, iy, g), coord_range)
        c = _encodable(_content(random.Random(n), b, nr, nb, nn))
        got = cenc.measure_content(0, ix, iy, b, c)
        if got is None:
            continue
        with monkeypatch.context() as m:
            m.setattr(cenc, "measure_content", lambda *a, **k: None)
            assert got == B._measure_one(0, ix, iy, b, c)
        checked += 1
    assert checked


def _nd(x, y, lat, lon):
    return RoadNode(x=x, y=y, lat=lat, lon=lon, oneway=0, planned=0, tunnel=False, bridge=False)


def _one_link(nodes):
    return RoadLink(
        display_class=0, road_type=1, altitude_flag=False, route_type_guidance_flag=False,
        pseudo3d_updown=0, route_planning_tag=False, link_id_flag=False,
        selected_link_flag=False, toll_flag=False, route_number_flag=False,
        infra_link_flag=False, link_id_number_flag=False, n_nodes=len(nodes), nodes=nodes,
        points=[(nd.lat, nd.lon) for nd in nodes], link_id=0, osm_way_id=None, ordinal=0)


def _node_words(link_bytes):
    """(sx, sy) raw words of each node record of a single encoded link."""
    return [((link_bytes[16 + 6 * j + 2] << 8) | link_bytes[16 + 6 * j + 3],
             (link_bytes[16 + 6 * j + 4] << 8) | link_bytes[16 + 6 * j + 5])
            for j in range((len(link_bytes) - 16) // 6)]


def _c_cell(level, ix, iy, content, coord_range, tmp_path):
    w = spool.SpoolWriter(tmp_path / "sp1")
    w.add(level, ix, iy, **content)
    w.close()
    (_, _, raw), = spool.SpoolReader(tmp_path / "sp1").iter_cell_raw(level)
    enc = cenc.make_encoder(level, TileGrid.from_reference(level), 131070, KL)
    return raw, enc.encode(raw, ix, iy, coord_range=coord_range)


@pytest.mark.parametrize("coord_range", RANGES)
def test_stored_pixels_ignored_latlon_wins(coord_range, tmp_path, pure_py):
    """A node whose stored x/y disagree with its lat/lon encodes from the
    lat/lon, in both encoders (the spool's n_x/n_y were written at 32768)."""
    level = 8
    g = TileGrid.from_reference(level)
    ix, iy = 5, 5
    b = _ranged(parcel_bounds(ix, iy, g), coord_range)
    lat = b.lat_lo + 0.25 * (b.lat_hi - b.lat_lo)
    lon = b.lon_lo + 0.75 * (b.lon_hi - b.lon_lo)
    lied = [_nd(1234, 4321, lat, lon), _nd(7, 9, lat, lon)]
    honest = [_nd(0, 0, lat, lon), _nd(0, 0, lat, lon)]
    py = synth.encode_road_link_bytes(_one_link(lied), b)
    assert py == synth.encode_road_link_bytes(_one_link(honest), b)
    q = coord_range // 4
    want = ((3 * q) % 4096) | ((3 * q // 4096) << 13), (q % 4096) | ((q // 4096) << 13)
    assert _node_words(py) == [want, want]
    content = {"roads": [_one_link(lied)], "backgrounds": [], "names": []}
    raw, got = _c_cell(level, ix, iy, content, coord_range, tmp_path)
    rc = spool.columns_to_content(spool.decode_columns(raw))
    assert rc["roads"][0].nodes[0].x == 1234  # the spool really carries the lie
    assert got is not None and got == B._measure_one(level, ix, iy, b, rc)[0]
    assert py in got


@pytest.mark.parametrize("coord_range", RANGES)
def test_frame_edge_is_inclusive(coord_range, tmp_path, pure_py):
    """A coordinate of exactly `coord_range` survives the clamp and encodes as
    the next region's value 0; beyond it clamps to `coord_range`. The one
    exception is the legacy 32768 frame, whose edge (region 8) does not fit the
    3-bit region field: it clamps to 32767, the word's largest value."""
    level = 8
    g = TileGrid.from_reference(level)
    ix, iy = 5, 5
    b = _ranged(parcel_bounds(ix, iy, g), coord_range)
    if coord_range == 32768:
        edge = 0xEFFF  # region 7, value 4095 = 32767
    else:
        edge = (coord_range % 4096) | ((coord_range // 4096) << 13)
        assert edge & 0x1FFF == 0 and edge >> 13 == coord_range // 4096
    ne = _nd(0, 0, b.lat_hi, b.lon_hi)
    beyond = _nd(0, 0, b.lat_hi + 1.0, b.lon_hi + 1.0)
    py = synth.encode_road_link_bytes(_one_link([ne, beyond]), b)
    assert _node_words(py) == [(edge, edge), (edge, edge)]
    s = BackgroundShape(shape_class=1, type_code=5, type_label="", n_coords=2, mult_const=1,
                        underground=False, pen_up=False,
                        coords=[(b.lat_hi, b.lon_hi), (b.lat_hi + 1.0, b.lon_hi + 1.0)])
    bg = synth.encode_background_shape_bytes_scalar(s, b)
    assert (bg[8] << 8 | bg[9], bg[10] << 8 | bg[11]) == (edge, edge)
    assert bg[12:14] == b"\x00\x00"  # clamped at the edge: zero delta
    assert _C_BG(s, b, coord_range) == bg
    nm = NameRecord(string_type=1, type_code=1, type_label="", priority=0, vertical=False,
                    display_scale_flag=0, text="Edge", lat=b.lat_hi, lon=b.lon_hi)
    nb = synth.encode_name_record_bytes(nm, b)
    assert (nb[8] << 8 | nb[9], nb[10] << 8 | nb[11]) == (edge, edge)
    content = {"roads": [_one_link([ne, beyond])], "backgrounds": [s], "names": [nm]}
    raw, got = _c_cell(level, ix, iy, content, coord_range, tmp_path)
    rc = spool.columns_to_content(spool.decode_columns(raw))
    assert got is not None and got == B._measure_one(level, ix, iy, b, rc)[0]
    assert py in got and bg in got and nb in got
