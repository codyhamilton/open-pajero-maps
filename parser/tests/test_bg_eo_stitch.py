"""3-14: original per-ring EO regions survive clipping through E1 -> E2.

Geometry expectations come from ray parity and outline distance on the source,
not another encoder. Ordinary-ring hashes were captured at 8b9a65e.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE), str(HERE / 'fixtures/harness')]
import boundary
import e2_fixture
from kiwiw.model import BackgroundShape

LEVEL, IX, IY = 0, 1780, 814
B = e2_fixture.cell_bounds(LEVEL, IX, IY)
RANGE = B.require_range()

# Integer raw coordinates; both lobes, clipping corners, coincident traversals,
# an attached inner hole, and the original implicit closing chord are exercised.
RINGS = {
    'bowtie_inside': [(512, 512), (3584, 3584), (512, 3584), (3584, 512)],
    'bowtie_clipped': [(-1024, 512), (5120, 3584), (-1024, 3584), (5120, 512)],
    'reversed_lobe': [(-2048, -1024), (2048, 3072), (5120, 512), (5120, 5120)],
    'multi_lobe': [(-1024, 1024), (3072, 3072), (1024, 3072), (5120, 1024),
                   (3072, 5120), (1024, -1024)],
    'chord_closed': [(-1024, 512), (3072, 512), (3072, 3072), (512, 3072),
                     (512, -1024), (3584, 3584)],
    'duplicate_square': [(512, 512), (3584, 512), (3584, 3584), (512, 3584),
                         (512, 512), (3584, 512), (3584, 3584), (512, 3584)],
    'partial_overlap': [(-1024, 512), (3072, 512), (3072, 3072), (512, 3072),
                        (512, 512), (5120, 512), (5120, 3584), (-1024, 3584)],
    'hole': [(512, 512), (3584, 512), (3584, 3584), (512, 3584), (512, 512),
             (1024, 1024), (1024, 3072), (3072, 3072), (3072, 1024), (1024, 1024)],
    'touching': [(512, 512), (2048, 2048), (512, 3584), (3584, 3584),
                 (2048, 2048), (3584, 512)],
    'short_fragment_retrace': [(2944, 928), (-320, 2112), (2560, 1088),
        (512, 416), (-832, 3072), (2688, 1760), (576, 2624), (-896, 1120),
        (3008, 1952), (2048, -1024), (2944, 928), (-320, 2112)],
    'frame_overlap': [(-1024, 0), (2048, 0), (2048, 3072), (0, 3072),
                       (0, 0), (4096, 0), (4096, 4096), (-1024, 4096)],
}
SIMPLE = {
    'triangle': [(512, 512), (3584, 512), (2048, 3584)],
    'rectangle': [(512, 512), (3584, 512), (3584, 3584), (512, 3584)],
    'clip_right': [(512, 512), (5120, 512), (5120, 3584), (512, 3584)],
    'cover': [(-1024, -1024), (5120, -1024), (5120, 5120), (-1024, 5120)],
    'outside': [(5120, 512), (6144, 512), (6144, 3584), (5120, 3584)],
    'concave': [(-1024, 512), (3072, 512), (3072, 1024), (512, 1024),
                (512, 3072), (3072, 3072), (3072, 3584), (-1024, 3584)],
}


def inside(p, ring):
    x, y = p
    odd = False
    for (ax, ay), (bx, by) in zip(ring, ring[1:] + ring[:1]):
        if (ay > y) != (by > y) and x < ax + (y-ay)/(by-ay)*(bx-ax):
            odd = not odd
    return odd


def distance(p, ring):
    """Chebyshev segment distance, including diagonal equal-error minima."""
    x, y = p
    best = math.inf
    for a, b in zip(ring, ring[1:] + ring[:1]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        ux, uy = x-a[0], y-a[1]
        candidates = [0., 1.]
        for num, den in [(ux, dx), (uy, dy), (ux-uy, dx-dy), (ux+uy, dx+dy)]:
            if den:
                candidates.append(max(0., min(1., num/den)))
        best = min(best, *(max(abs(ux-t*dx), abs(uy-t*dy)) for t in candidates))
    return best


def frame(tmp_path, rings):
    shapes = []
    for ring in rings:
        coords = [(B.lat_lo+y/RANGE*(B.lat_hi-B.lat_lo),
                   B.lon_lo+x/RANGE*(B.lon_hi-B.lon_lo)) for x, y in ring]
        shapes.append(BackgroundShape(shape_class=2, type_code=288, type_label='',
            n_coords=len(coords), mult_const=1, underground=False, pen_up=False, coords=coords))
    return e2_fixture.e2_frames(tmp_path, LEVEL, {(IX, IY): {'backgrounds': shapes}})[IX, IY]


def polygons(blob):
    bg = boundary.decode_frame(blob, B).background
    return [[((lon-B.lon_lo)/(B.lon_hi-B.lon_lo)*RANGE,
              (lat-B.lat_lo)/(B.lat_hi-B.lat_lo)*RANGE) for lat, lon in s.coords]
            for s in ([] if bg is None else bg.shapes)]


@pytest.mark.parametrize('name', RINGS)
@pytest.mark.parametrize('reverse', [False, True])
def test_original_even_odd_region(tmp_path, name, reverse):
    ring = RINGS[name][::-1] if reverse else RINGS[name]
    out = polygons(frame(tmp_path, [ring]))
    for x in range(43, 4096, 139):
        for y in range(61, 4096, 137):
            if distance((x, y), ring) > 1:
                assert any(inside((x, y), poly) for poly in out) == inside((x, y), ring), (name, x, y)
    for poly in out:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            for t in [0., .25, .5, .75]:
                p = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
                assert -.000001 <= p[0] <= 4096.000001 and -.000001 <= p[1] <= 4096.000001
                assert inside(p, ring) or distance(p, ring) <= .500001, (name, p)


def test_separate_rings_are_or_not_xor(tmp_path):
    ring = RINGS['bowtie_clipped']
    a = frame(tmp_path/'one', [ring])
    b = frame(tmp_path/'two', [ring, ring])
    for p in [(1024, 1024), (1024, 3072), (2048, 512), (2048, 3584)]:
        assert any(inside(p, q) for q in polygons(a)) == any(inside(p, q) for q in polygons(b))


@pytest.mark.parametrize('name', SIMPLE)
def test_ordinary_ring_bytes(tmp_path, name):
    expected = json.loads((HERE/'fixtures/bg_eo/simple_sha256.json').read_text())
    assert hashlib.sha256(frame(tmp_path, [SIMPLE[name]])).hexdigest() == expected[name]


@pytest.fixture(scope='module')
def probe(tmp_path_factory):
    import ctypes
    import subprocess
    from kiwiw import cbuild
    output = tmp_path_factory.mktemp('eo_probe')/'probe.so'
    subprocess.run([cbuild._find_cc(), *cbuild.CFLAGS, '-shared',
                    str(HERE/'fixtures/bg_eo/probe.c'), '-lm', '-o', str(output)], check=True)
    lib = ctypes.CDLL(str(output))
    fn = lib.probe_bg
    fn.restype = ctypes.c_int64
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
    return fn


def probe_output(probe, ring, rect, room=65536):
    import ctypes
    import numpy as np
    lat = np.array([y for x,y in ring], 'f8')
    lon = np.array([x for x,y in ring], 'f8')
    rect = np.array(rect, 'f8')
    out = np.zeros(max(1,room), 'u1')
    nr = ctypes.c_int64()
    size = probe(lat.ctypes.data,lon.ctypes.data,len(ring),rect.ctypes.data,
                 out.ctypes.data,room,ctypes.byref(nr))
    return size, nr.value, out[:max(0,size)].tobytes()


def raw_polygons(blob):
    import struct
    from kiwiw.coordconv import decode_region_coord
    out = []
    pos = 0
    while pos < len(blob):
        size, ndl, tc, flags, x, y = struct.unpack_from('>6H',blob,pos)
        size = (size & 4095)*2
        step = 1 << (flags & 7)
        x, y = decode_region_coord(x), decode_region_coord(y)
        p = [(x,y)]
        for k in range(ndl & 2047):
            dx,dy = struct.unpack_from('bb',blob,pos+12+2*k)
            x += step*dx; y += step*dy; p.append((x,y))
        out.append(p)
        pos += size
    assert pos == len(blob)
    return out


def test_probe_subrectangle_and_room_retry(probe):
    ring = RINGS['bowtie_clipped']
    rect = [1024, 512, 3072, 3072]
    assert probe_output(probe,ring,rect,1)[0] == -2
    size,nr,blob = probe_output(probe,ring,rect)
    assert size > 0 and nr == 2
    out = raw_polygons(blob)
    for x in range(1043,3072,97):
        for y in range(537,3072,103):
            if distance((x,y),ring) > 1:
                assert any(inside((x,y),p) for p in out) == inside((x,y),ring)
    for p in out:
        assert all(rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3] for x,y in p)
    assert probe_output(probe,ring,rect) == (size,nr,blob)


def test_seeded_crossing_arrangements(probe):
    import random
    rng = random.Random(314)
    for _ in range(100):
        ring = [(rng.randrange(-16,81)*64,rng.randrange(-16,81)*64)
                for k in range(rng.randrange(4,12))]
        size,nr,blob = probe_output(probe,ring,[0,0,4096,4096])
        assert size >= 0
        out = raw_polygons(blob)
        for _ in range(80):
            p = (rng.randrange(1,4096),rng.randrange(1,4096))
            if distance(p,ring) > 1:
                assert any(inside(p,q) for q in out) == inside(p,ring), (ring,p)


def test_short_fragment_side_classification(probe):
    ring = RINGS['short_fragment_retrace']
    size,nr,blob = probe_output(probe,ring,[512,1024,3072,3584])
    assert size > 0
    assert any(inside((2030,2024),p) for p in raw_polygons(blob))
