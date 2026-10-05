"""Independent C/Python completeness at the wire representability boundary."""
import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1])]
import k1_fixtures as fx
from tools import quantisation_roundtrip as qr
from tools.k1_representable import decompose_eo_faces, wire_survives


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


def test_any_representable_demander_keeps_pair_failing(tmp_path):
    disc, spool = fx.build_representable_fixture(tmp_path, "tol_vertical", second_square=True)
    py = qr.roundtrip(str(disc), str(spool), workers=1)["totals"]["completeness"]
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool))
    c = acc.result()["kinds"]["completeness"]
    assert (c["checked"], c["failing"]) == (py["checked"], py["failing"]) == (1, 1)
