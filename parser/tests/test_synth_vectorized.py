"""Plan 02 phase 3: fast (C) encoders are byte-identical to the scalar oracle."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import synth
from kiwiw.model import BackgroundShape, BoundingBox

B = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0, coord_range=4096)


def _shape(rng, cls, n, step, mult, bounds_margin=0.0):
    lat, lon = rng.uniform(-32 - bounds_margin, -31 + bounds_margin), \
        rng.uniform(115 - bounds_margin, 116 + bounds_margin)
    coords = []
    for _ in range(n):
        lat += rng.uniform(-step, step)
        lon += rng.uniform(-step, step)
        coords.append((lat, lon))
    return BackgroundShape(shape_class=cls, type_code=rng.randrange(0, 65536),
                           type_label="t", n_coords=n, mult_const=mult,
                           underground=bool(rng.getrandbits(1)), pen_up=bool(rng.getrandbits(1)),
                           coords=coords)


def test_background_fast_equals_scalar_fuzz():
    rng = random.Random(1234)
    fast = 0
    from kiwiw import cenc
    for i in range(4000):
        cls = rng.choice([1, 2, 2, 3])
        n = rng.choice([1, 2, 3, 10, 60, 300])
        step = rng.choice([1e-5, 1e-4, 5e-4, 5e-3, 0.3])  # small steps and saturating ones
        mult = rng.choice([0, 1, 1, 1, 2, 4, 8])
        s = _shape(rng, cls, n, step, mult, bounds_margin=rng.choice([0.0, 0.5]))
        want = synth.encode_background_shape_records_scalar(s, B)
        got = synth.encode_background_shape_records(s, B)
        assert got == want, (i, cls, n, step, mult)
        fast += cls != 0 and cenc.bg_shape_records(s, B, 4096) is not None
    assert fast > 3000  # nearly every line/polygon takes the C path


def test_background_point_and_grid_snap():
    rng = random.Random(7)
    pt = _shape(rng, 0, 1, 1e-4, 1)
    assert synth.encode_background_shape_bytes(pt, B) == \
        synth.encode_background_shape_bytes_scalar(pt, B)
    # exact half-pixel ties must round half-to-even like `round()`
    coords = [(-31.0 - (k + 0.5) / 32768.0, 115.0 + (k + 0.5) / 32768.0) for k in range(40)]
    s = BackgroundShape(shape_class=2, type_code=5, type_label="t", n_coords=40,
                        mult_const=1, underground=False, pen_up=False, coords=coords)
    assert synth.encode_background_shape_bytes(s, B) == \
        synth.encode_background_shape_bytes_scalar(s, B)
