"""C background-shape encoder (plan 03): byte-identical to the Python oracle
(`synth`, which 3C-12 retires with it). The build-path encoders are covered by
`test_e2.py`'s goldens."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import cenc, spool, synth
from kiwiw.model import BackgroundShape, BoundingBox

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")



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
    b = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0,
                    coord_range=16384)
    for k in (1, 2, 3, 5, 50, 700):
        for mult in (0, 1, 3):
            s = BackgroundShape(
                shape_class=1, type_code=5, type_label="", n_coords=k, mult_const=mult,
                underground=bool(k & 1), pen_up=bool(k & 2),
                coords=[(rng.uniform(-32.1, -30.9), rng.uniform(114.9, 116.1)) for _ in range(k)])
            got = cenc.bg_shape_records(s, b, b.coord_range)
            if got is not None:
                assert got == synth.encode_background_shape_records_scalar(s, b), (k, mult)


# ---------------------------------------------------------------- 3-02: the
# coordinate range is a parameter of both encoders, not a constant either owns.

RANGES = (16384, 4096)  # every real frame range (range_for); 32768 is not one


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
            want = synth.encode_background_shape_records_scalar(s, b)
            got = cenc.bg_shape_records(s, b, coord_range)
            if got is not None:
                got_any = True
                assert got == want, (k, mult)
            assert synth.encode_background_shape_records(s, b) == want, (k, mult)
    assert got_any


# ---------------------------------------------------------------- 3-07: the
# clip-to-frame background encoder, C == Python on every clip case.

_CB = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0, coord_range=4096)


def _raw_shape(cls, pts, mult=1):
    r = 4096.0
    return BackgroundShape(shape_class=cls, type_code=9, type_label="", n_coords=len(pts),
                           mult_const=mult, underground=False, pen_up=False,
                           coords=[(-32.0 + y / r, 115.0 + x / r) for x, y in pts])


_CLIP_CASES = {
    "leave_reenter": (2, [(3000, 100), (5000, 100), (5000, 900), (3000, 900), (3000, 700),
                          (4500, 700), (4500, 300), (3000, 300)]),
    "corner_covering": (2, [(4000, 4000), (4500, 4000), (4500, 4500), (4000, 4500)]),
    "fully_inside": (2, [(100, 100), (100, 200), (200, 200), (200, 100), (100, 100)]),
    "fully_outside": (2, [(5000, 5000), (5100, 5000), (5100, 5100), (5000, 5100)]),
    "whole_frame": (2, [(-50, -50), (5000, -50), (5000, 5000), (-50, 5000)]),
    "line_runs": (1, [(100, 100), (5000, 100), (5000, 200), (100, 200), (-100, 200),
                      (-100, 300), (100, 300)]),
    "line_outside": (1, [(-10, -10), (-10, 5000)]),
    "two_corners": (2, [(-300, 1000), (4400, 1000), (4400, 4400), (-300, 4400)]),
}


@pytest.mark.parametrize("case", sorted(_CLIP_CASES))
@pytest.mark.parametrize("rect", [None, (2048, 0, 4096, 2048), (1024, 3072, 2048, 4096)])
def test_bg_clip_cases_c_equals_python(case, rect):
    from kiwiw import clip
    cls, pts = _CLIP_CASES[case]
    b = _CB if rect is None else clip.SubParcelBounds(**vars(_CB), clip_rect=rect)
    s = _raw_shape(cls, pts)
    want = synth.encode_background_shape_records_scalar(s, b)
    got = cenc.bg_shape_records(s, b, 4096)
    assert got == want, case
    if rect is None and case in ("fully_outside", "line_outside"):
        assert want == []
    if rect is None and case in ("leave_reenter", "line_runs"):
        assert len(want) == (2 if case == "leave_reenter" else 3)


@pytest.mark.parametrize("coord_range", [4096, 65536])
def test_bg_whole_cell_rect_coarse_mult_c_equals_python(coord_range):
    """3-11: a shape covering the whole frame clips to exactly the frame
    rectangle -- C and Python must pick the same coarse mult_const and emit
    byte-identical records, including the multi-step case (coord_range=65536,
    mult_const=128 needs several exact-multiple steps per edge)."""
    r = float(coord_range)
    pts = [(-50, -50), (r + 50, -50), (r + 50, r + 50), (-50, r + 50)]
    s = BackgroundShape(shape_class=2, type_code=9, type_label="", n_coords=len(pts),
                        mult_const=1, underground=False, pen_up=False,
                        coords=[(-32.0 + y / r, 115.0 + x / r) for x, y in pts])
    b = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0, coord_range=coord_range)
    want = synth.encode_background_shape_records_scalar(s, b)
    got = cenc.bg_shape_records(s, b, r)
    assert got == want
    (rec,) = want
    addl = (rec[6] << 8) | rec[7]
    assert (1 << (addl & 0x7)) > 1  # coarser than mult_const=1


def test_bg_clip_fuzz_c_equals_python():
    from kiwiw import clip
    rng = random.Random(307)
    checked = 0
    for i in range(3000):
        n = rng.choice([2, 3, 4, 7, 20, 90])
        cx, cy = rng.uniform(-3000, 7000), rng.uniform(-3000, 7000)
        sc = rng.choice([30, 400, 3000, 9000])
        cls = rng.choice([1, 2, 2, 3])
        if cls == 2:
            import math
            angs = sorted(rng.uniform(0, 6.283) for _ in range(n))
            pts = [(cx + math.cos(a) * rng.uniform(0.2, 1) * sc,
                    cy + math.sin(a) * rng.uniform(0.2, 1) * sc) for a in angs]
            if rng.random() < 0.5:
                pts.append(pts[0])
        else:
            pts = [(cx + rng.uniform(-sc, sc), cy + rng.uniform(-sc, sc)) for _ in range(n)]
        rect = rng.choice([None, None, clip.sub_rect(4096, 2, 2, rng.randrange(2), rng.randrange(2)),
                           clip.sub_rect(4096, 4, 4, rng.randrange(4), rng.randrange(4))])
        b = _CB if rect is None else clip.SubParcelBounds(**vars(_CB), clip_rect=rect)
        s = _raw_shape(cls, pts, mult=rng.choice([0, 1, 1, 2]))
        want = synth.encode_background_shape_records_scalar(s, b)
        got = cenc.bg_shape_records(s, b, 4096)
        assert got == want, i
        checked += bool(want)
    assert checked > 500
