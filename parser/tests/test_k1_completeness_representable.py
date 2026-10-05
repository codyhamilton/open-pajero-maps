"""Independent C/Python completeness at the wire representability boundary."""
import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import k1_fixtures as fx
from tools import quantisation_roundtrip as qr
from tools.k1_representable import decompose_eo_faces, representable, wire_survives
from test_bg_eo_stitch import RINGS, distance, inside, probe, probe_output, raw_polygons


@pytest.mark.parametrize("name", list(fx.REPRESENTABLE_CASES))
@pytest.mark.parametrize("tall_home", [False, True])
def test_missing_piece_requires_representable_demander(tmp_path, name, tall_home):
    pts, mc, emits = fx.REPRESENTABLE_CASES[name]
    if name.startswith("densify_"):
        assert wire_survives(pts, mc, densify=False)
        assert wire_survives(pts, mc) == emits
    if name == "bowtie":
        assert sum(wire_survives(face) for face in decompose_eo_faces(pts)) == 1
    disc, spool = fx.build_representable_fixture(tmp_path, name, tall_home)
    py = qr.roundtrip(str(disc), str(spool), workers=1)["totals"]["completeness"]
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool))
    c = acc.result()["kinds"]["completeness"]
    assert (c["checked"], c["failing"]) == (py["checked"], py["failing"])
    assert py["checked"] > 0
    assert c["failing"] == int(fx.REPRESENTABLE_CASES[name][2]), (name, py, c)


@pytest.mark.parametrize("name", ["tol_vertical", "twice_square", "twice_crossing"])
@pytest.mark.parametrize("tall_home", [False, True])
def test_any_representable_demander_keeps_pair_failing(tmp_path, name, tall_home):
    disc, spool = fx.build_representable_fixture(tmp_path, name, tall_home, second_square=True)
    py = qr.roundtrip(str(disc), str(spool), workers=1)["totals"]["completeness"]
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool))
    c = acc.result()["kinds"]["completeness"]
    assert (c["checked"], c["failing"]) == (py["checked"], py["failing"]) == (1, 1)


@pytest.fixture(scope="module")
def checker_probe(tmp_path_factory):
    """Test the C footprint directly without exporting a production symbol."""
    import ctypes
    import subprocess
    import numpy as np
    from kiwiw import cbuild
    directory = tmp_path_factory.mktemp("k1_eo_probe")
    source = Path(__file__).resolve().parents[1] / "kiwiw/_k1_cmp.c"
    wrapper = directory / "probe.c"
    wrapper.write_text(f'''#include "{source}"
__attribute__((visibility("default")))
int probe_represent(const double *x, const double *y, int64_t n, int32_t ix, int32_t iy) {{
    int64_t off[2] = {{0,n}}; int32_t mult[1] = {{1}};
    k1_shapes h = {{0}}; h.x = (double *)x; h.y = (double *)y; h.off = off; h.mult = mult;
    return rrepresent(&h,0,(trip){{iy,ix,288,0}});
}}
''')
    output = directory / "probe.so"
    subprocess.run([cbuild._find_cc(), *cbuild.CFLAGS, "-shared", "-ffunction-sections",
                    "-fdata-sections", "-fvisibility=hidden", "-Wl,--gc-sections",
                    str(wrapper), "-lm", "-o", str(output)], check=True)
    lib = ctypes.CDLL(str(output))
    fn = lib.probe_represent
    fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64, ctypes.c_int32, ctypes.c_int32]
    fn.restype = ctypes.c_int

    def run(ring, ix=0, iy=0):
        x, y = np.array(ring, "f8").T.copy()
        x, y = np.ascontiguousarray(x), np.ascontiguousarray(y)
        return fn(x.ctypes.data, y.ctypes.data, len(ring), ix, iy)
    return run


@pytest.mark.parametrize("name", ["endpoint_lobes", "twice_square", "twice_crossing"])
def test_review_reproductions_have_independent_eo_results(name, checker_probe, probe):
    ring, _, emits = fx.REPRESENTABLE_CASES[name]
    expected = (40, 2) if emits else (0, 0)
    assert probe_output(probe, ring, [0, 0, 4096, 4096])[:2] == expected
    assert representable(ring, 0, 0) == emits
    assert checker_probe(ring) == int(emits)
    faces = decompose_eo_faces(ring)
    assert len(faces) == (2 if emits else 0)
    if emits:
        assert all(abs(sum(a[0]*b[1]-b[0]*a[1] for a, b in
                           zip(face, face[1:]+face[:1]))) == 20000 for face in faces)


@pytest.mark.parametrize("name", ["duplicate_square", "partial_overlap", "touching",
                                  "hole", "short_fragment_retrace", "frame_overlap"])
@pytest.mark.parametrize("reverse", [False, True])
def test_contact_faces_preserve_source_parity(name, reverse, checker_probe, probe):
    ring = RINGS[name][::-1] if reverse else RINGS[name]
    emits = name != "duplicate_square"
    size, records, blob = probe_output(probe, ring, [0, 0, 4096, 4096])
    assert size >= 0 and (records > 0) == emits
    assert representable(ring, 0, 0) == emits
    assert checker_probe(ring) == int(emits)
    faces, production = decompose_eo_faces(ring), raw_polygons(blob)
    for x in range(43, 4096, 139):
        for y in range(61, 4096, 137):
            if distance((x, y), ring) > 1:
                expected = inside((x, y), ring)
                assert any(inside((x, y), face) for face in faces) == expected, (name, x, y)
                assert any(inside((x, y), face) for face in production) == expected, (name, x, y)


def test_cell_wholly_in_retraced_hole_is_empty(checker_probe, probe):
    ring = [((x-1536)*4, (y-1536)*4) for x, y in RINGS["hole"]]
    assert not inside((2048, 2048), ring)
    assert probe_output(probe, ring, [0, 0, 4096, 4096])[:2] == (0, 0)
    assert not representable(ring, 0, 0)
    assert checker_probe(ring) == 0


def test_unsupported_c_grid_is_an_explicit_error(checker_probe):
    assert checker_probe([(0, 0), (1, 1), (1, 2**-100)]) == -3
