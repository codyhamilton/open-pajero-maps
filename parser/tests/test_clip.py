"""Plan 03 3-07: background geometry is clipped to its parcel, never clamped."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw import clip, synth
from kiwiw.model import BackgroundShape, BoundingBox

R = 4096
RECT = (0, 0, R, R)
B = BoundingBox(lat_lo=-32.0, lat_hi=-31.0, lon_lo=115.0, lon_hi=116.0, coord_range=R)


def _pieces(pts, closed=True, rect=RECT):
    fx = [p[0] for p in pts]
    fy = [p[1] for p in pts]
    return clip.shape_pieces(fx, fy, closed, rect)


def _key(piece):
    """Vertex set without densified points (long steps are split for i8)."""
    return {v[:2] for v in piece if v[4] != clip.DENSE}


def _area2(piece):
    return sum(piece[i][0] * piece[i + 1][1] - piece[i + 1][0] * piece[i][1]
               for i in range(len(piece) - 1))


def _check_piece(piece, closed, rect=RECT):
    x0, y0, x1, y1 = rect
    for x, y, fx, fy, kind in piece:
        assert x0 <= x <= x1 and y0 <= y <= y1, (x, y)
        assert abs(x - fx) <= 0.5 and abs(y - fy) <= 0.5
        if kind == clip.CROSS_X:
            assert fx in (x0, x1)
        if kind == clip.CROSS_Y:
            assert fy in (y0, y1)
        if kind == clip.CORNER:
            assert (fx, fy) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for a, b in zip(piece, piece[1:]):
        assert (a[0], a[1]) != (b[0], b[1])
        assert abs(b[0] - a[0]) <= 127 and abs(b[1] - a[1]) <= 127
    if closed:
        assert piece[0][:2] == piece[-1][:2]
        assert _area2(piece) > 0  # counter-clockwise


def test_fully_inside_unchanged_ccw():
    sq = [(100, 100), (100, 200), (200, 200), (200, 100), (100, 100)]  # clockwise
    (p,) = _pieces(sq)
    _check_piece(p, True)
    assert {v[:2] for v in p} == {(100, 100), (100, 200), (200, 200), (200, 100)}
    assert all(v[4] == clip.ORIG for v in p)


def test_fully_outside_writes_nothing():
    assert _pieces([(5000, 5000), (5100, 5000), (5100, 5100), (5000, 5100)]) == []
    assert _pieces([(-10, -10), (-10, 5000)], closed=False) == []


def test_whole_frame_is_rectangle():
    (p,) = _pieces([(-50, -50), (5000, -50), (5000, 5000), (-50, 5000)])
    _check_piece(p, True)
    assert _key(p) == {(0, 0), (R, 0), (R, R), (0, R)}
    assert all(v[4] in (clip.CORNER, clip.DENSE) for v in p)
    assert all(v[0] in (0, R) or v[1] in (0, R) for v in p)


def test_corner_covering_inserts_corner():
    (p,) = _pieces([(4000, 4000), (4500, 4000), (4500, 4500), (4000, 4500)])
    _check_piece(p, True)
    assert (R, R) in {v[:2] for v in p}
    assert {v[:2] for v in p} == {(4000, 4000), (R, 4000), (R, R), (4000, R)}


def test_leave_and_reenter_splits_pieces_no_bridge():
    # a U open to the right edge: dips outside x > R between two prongs
    u = [(3000, 100), (5000, 100), (5000, 900), (3000, 900), (3000, 700),
         (4500, 700), (4500, 300), (3000, 300)]
    ps = _pieces(u)
    # clipping to x <= R leaves two separate prongs, never a bridge along x = R
    assert len(ps) == 2
    for p in ps:
        _check_piece(p, True)
    xs = sorted(tuple(sorted({v[1] for v in p if v[4] != clip.DENSE})) for p in ps)
    assert xs == [(100, 300), (700, 900)]


def test_line_one_record_per_inside_run():
    line = [(100, 100), (5000, 100), (5000, 200), (100, 200), (-100, 200), (-100, 300), (100, 300)]
    ps = _pieces(line, closed=False)
    assert len(ps) == 3
    for p in ps:
        _check_piece(p, False)
    assert ps[0][-1][2] == R and ps[1][0][2] == R and ps[1][-1][2] == 0 and ps[2][0][2] == 0


def test_crossing_exact_on_edge_and_mirrored():
    # the same segment clipped in two adjacent frames yields the same point
    a, b = (4000.3, 17.7), (4200.9, 1001.2)
    (left,) = _pieces([a, b], closed=False)
    (right,) = _pieces([(a[0] - R, a[1]), (b[0] - R, b[1])], closed=False)
    assert left[-1][2] == R and right[0][2] == 0
    assert left[-1][3] == right[0][3]


def test_sub_parcel_quadrant():
    rect = clip.sub_rect(R, 2, 2, 1, 0)
    assert rect == (2048, 0, R, 2048)
    (p,) = _pieces([(1000, 1000), (3000, 1000), (3000, 3000), (1000, 3000)], rect=rect)
    _check_piece(p, True, rect)
    assert _key(p) == {(2048, 1000), (3000, 1000), (3000, 2048), (2048, 2048)}


def test_fuzz_invariants():
    rng = random.Random(3)
    for _ in range(3000):
        n = rng.choice([3, 4, 7, 20])
        cx, cy = rng.uniform(-2000, 6000), rng.uniform(-2000, 6000)
        sc = rng.choice([50, 500, 3000])
        closed = rng.random() < 0.7
        if closed:  # simple (star-shaped) rings, as area data must be
            angs = sorted(rng.uniform(0, 6.283) for _ in range(n))
            pts = [(cx + math.cos(a) * rng.uniform(0.2, 1) * sc,
                    cy + math.sin(a) * rng.uniform(0.2, 1) * sc) for a in angs]
        else:
            pts = [(cx + rng.uniform(-sc, sc), cy + rng.uniform(-sc, sc)) for _ in range(n)]
        for p in _pieces(pts, closed):
            _check_piece(p, closed)


def _raw_records(recs):
    """(start x, y, deltas) decoded from each 12+2n record (mult 1)."""
    out = []
    for r in recs:
        n = ((r[2] << 8) | r[3]) & 0x7FF
        assert len(r) == 12 + 2 * n
        sx, sy = (r[8] << 8) | r[9], (r[10] << 8) | r[11]
        x = (sx & 0x1FFF) + (sx >> 13) * 4096
        y = (sy & 0x1FFF) + (sy >> 13) * 4096
        pts = [(x, y)]
        for k in range(n):
            dx, dy = r[12 + 2 * k], r[13 + 2 * k]
            x += dx - 256 if dx > 127 else dx
            y += dy - 256 if dy > 127 else dy
            pts.append((x, y))
        out.append(pts)
    return out


def _bg(coords, cls=2):
    return BackgroundShape(shape_class=cls, type_code=7, type_label="t", n_coords=len(coords),
                           mult_const=1, underground=False, pen_up=False, coords=coords)


def _ll(x, y):
    return (-32.0 + y / R, 115.0 + x / R)


def test_encoder_clips_not_clamps():
    """An overhanging polygon is written as its clipped piece: every vertex in
    [0, range], no clamped copy of outside vertices, the covered corner present."""
    s = _bg([_ll(x, y) for x, y in [(4000, 4000), (4600, 4000), (4600, 4600), (4000, 4600)]])
    recs = synth.encode_background_shape_records_scalar(s, B)
    (pts,) = _raw_records(recs)
    assert all(0 <= x <= R and 0 <= y <= R for x, y in pts)
    assert set(pts) == {(4000, 4000), (R, 4000), (R, R), (4000, R)}
    assert synth.encode_background_shape_records(s, B) == recs


def test_encoder_outside_and_split():
    out = _bg([_ll(x, y) for x, y in [(5000, 5000), (5100, 5000), (5100, 5100)]])
    assert synth.encode_background_shape_records_scalar(out, B) == []
    frame = synth.build_background_frame_bytes([out], B)
    assert frame == bytes([0, 1])
    line = _bg([_ll(x, y) for x, y in [(100, 100), (5000, 100), (5000, 200), (100, 200)]], cls=1)
    recs = synth.encode_background_shape_records_scalar(line, B)
    assert len(recs) == 2
    assert synth.encode_background_shape_records(line, B) == recs
