"""Plan 43 (R-G8-1-d): seeded stress and edge cases for the 3-14 even-odd
background clipper (`kw__bg_shape` via the test-only probe).

Replaces the lost scratch-only `review_stress.py` (3-14 review b2) and covers
review F7's gaps: termination, capacity bounds and degenerate rings. The probe
runs in a child process with a 600 s timeout (the "guard" is this external timeout,
not an iteration bound inside eo_connect's for(;;)), so a non-terminating case
fails the test instead of hanging the suite. eo_connect runs on every eo_clip;
the island_hole_island case relies on collinear connector edges cancelling by
parity to produce separate components (the connection branch v>=0 is not
separately asserted). This is a test, not a fix: a failing case is a finding
against the encoder.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE), str(HERE / 'fixtures/harness')]
SEED = 4314
N_RINGS = 1000
TIMEOUT_S = 600
# Plan 48 P3: face-walk declines fixed (T-junction split + total-order CW neighbor).
KNOWN_DECLINES = set()


def _proper_cross(p, q, r, s):
    def o(a, b, c):
        v = (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        return (v > 0) - (v < 0)
    return o(p, q, r)*o(p, q, s) < 0 and o(r, s, p)*o(r, s, q) < 0


def self_crossing(ring):
    e = list(zip(ring, ring[1:] + ring[:1]))
    return any(_proper_cross(*e[i], *e[j]) for i in range(len(e))
               for j in range(i+2, len(e)) if not (i == 0 and j == len(e)-1))


def seeded_rings():
    rng = random.Random(SEED)
    out = []
    while len(out) < N_RINGS:
        ring = [(rng.randrange(-16, 81)*64, rng.randrange(-16, 81)*64)
                for _ in range(rng.randrange(4, 15))]
        if self_crossing(ring):
            out.append(ring)
    return out


# Degenerate and edge cases (raw 0..4096 cell units; probe rect [0,0,4096,4096]).
EDGE = {
    'collinear': [(512, 512), (1024, 1024), (2048, 2048), (3072, 3072)],
    'zero_area_retrace': [(512, 512), (3584, 512), (512, 512), (3584, 512)],
    'repeated_vertices': [(512, 512), (512, 512), (3584, 512), (3584, 512),
                          (3584, 3584), (512, 3584), (512, 3584)],
    'touching_leaf_edge': [(0, 512), (2048, 0), (4096, 512), (4096, 3584),
                           (2048, 4096), (0, 3584)],
    'on_leaf_edge_only': [(0, 0), (4096, 0), (4096, 4096), (0, 4096)],
    'single_point': [(2048, 2048), (2048, 2048), (2048, 2048)],
    'spike': [(512, 512), (3584, 512), (2048, 2048), (2048, 6000), (2048, 2048),
              (512, 3584)],
    # eo_connect: components that never meet the rectangle edge (island, hole,
    # island-in-hole) must be connected or emitted without a non-terminating walk.
    'island_hole_island': [(512, 512), (3584, 512), (3584, 3584), (512, 3584), (512, 512),
                           (1024, 1024), (1024, 3072), (3072, 3072), (3072, 1024), (1024, 1024),
                           (1536, 1536), (2560, 1536), (2560, 2560), (1536, 2560), (1536, 1536)],
    'nested_bowties': [(256, 256), (3840, 3840), (256, 3840), (3840, 256), (256, 256),
                       (1024, 1024), (3072, 3072), (1024, 3072), (3072, 1024)],
    'many_coincident_retraces': [(512, 2048), (3584, 2048)] * 6 + [(2048, 512), (2048, 3584)] * 6,
}


def _child(so_path, cases_path, out_path):
    """Runs in a subprocess: probe every case, check output validity."""
    import ctypes
    from test_bg_eo_stitch import inside, distance, raw_polygons
    import numpy as np
    lib = ctypes.CDLL(so_path)
    fn = lib.probe_bg
    fn.restype = ctypes.c_int64
    fn.argtypes = [ctypes.c_void_p]*2 + [ctypes.c_int64] + [ctypes.c_void_p]*2 + [ctypes.c_int64, ctypes.c_void_p]

    def run(ring, rect, room):
        lat = np.array([y for x, y in ring], 'f8'); lon = np.array([x for x, y in ring], 'f8')
        r = np.array(rect, 'f8'); out = np.zeros(max(1, room), 'u1'); nr = ctypes.c_int64()
        size = fn(lat.ctypes.data, lon.ctypes.data, len(ring), r.ctypes.data, out.ctypes.data, room, ctypes.byref(nr))
        return size, nr.value, out[:max(0, size)].tobytes()

    cases = json.load(open(cases_path))
    rng = random.Random(SEED + 1)
    res = {'n': 0, 'queries': 0, 'failures': []}
    for name, ring in cases.items():
        res['n'] += 1
        rect = [0, 0, 4096, 4096]
        size, nr, blob = run(ring, rect, 1 << 20)
        try:
            assert size >= 0, f'size {size}'
            assert size <= 1 << 20
            polys = raw_polygons(blob)
            assert nr == len(polys), f'nrec {nr} vs {len(polys)}'
            for p in polys:
                assert all(rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3] for x, y in p)
            for _ in range(80):
                q = (rng.randrange(1, 4096), rng.randrange(1, 4096))
                if distance(q, ring) > 1:
                    res['queries'] += 1
                    assert any(inside(q, p) for p in polys) == inside(q, ring), f'parity at {q}'
            if size > 0:  # capacity: one byte short must report room exhaustion, then retry identically
                assert run(ring, rect, size - 1)[0] == -2, 'room-1 not -2'
                assert run(ring, rect, size) == (size, nr, blob), 'retry differs'
        except AssertionError as e:
            res['failures'].append({'case': name, 'error': str(e), 'size': size})
    json.dump(res, open(out_path, 'w'))


@pytest.fixture(scope='module')
def probe_so(tmp_path_factory):
    from kiwiw import cbuild
    out = tmp_path_factory.mktemp('eo_stress') / 'probe.so'
    subprocess.run([cbuild._find_cc(), *cbuild.CFLAGS, '-shared',
                    str(HERE / 'fixtures/bg_eo/probe.c'), '-lm', '-o', str(out)], check=True)
    return out


def _run_cases(probe_so, tmp_path, cases):
    cp, op = tmp_path / 'cases.json', tmp_path / 'out.json'
    cp.write_text(json.dumps(cases))
    subprocess.run([sys.executable, '-B', __file__, '--child', str(probe_so), str(cp), str(op)],
                   check=True, timeout=TIMEOUT_S, cwd=str(HERE.parent.parent))
    return json.loads(op.read_text())


def test_seeded_self_crossing_stress(probe_so, tmp_path):
    rings = seeded_rings()
    assert len(rings) == N_RINGS and all(self_crossing(r) for r in rings)
    res = _run_cases(probe_so, tmp_path, {f'r{i}': r for i, r in enumerate(rings)})
    assert res['n'] == N_RINGS and res['queries'] > 50_000
    assert {f['case'] for f in res['failures']} == KNOWN_DECLINES, res['failures']
    assert all(f['error'] == 'size -1' for f in res['failures'])


def test_known_decline_ring_359_now_passes(probe_so, tmp_path):
    """Plan 48 P3: former R-G8-1-d-a decline r359 now clips with valid parity."""
    res = _run_cases(probe_so, tmp_path, {'r359': seeded_rings()[359]})
    assert res['failures'] == []


@pytest.mark.parametrize('name', EDGE)
def test_degenerate_and_termination_cases(probe_so, tmp_path, name):
    res = _run_cases(probe_so, tmp_path, {name: EDGE[name]})
    assert res['failures'] == []


if __name__ == '__main__' and len(sys.argv) == 5 and sys.argv[1] == '--child':
    _child(*sys.argv[2:])
