"""Plan 48 Phase 1: decline mechanism naming from EO_DIAG dumps + xfail fixtures."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
DECLINE = (
    ROOT / "docs/plans/04-c-core-orchestration/triage/independent_reviews"
    / "3-14/conditions/eo_decline"
)
CASES = ("r359", "r8475", "r11892", "r14503", "r19650")
H2 = ("r359", "r8475", "r19650")
H1 = ("r11892", "r14503")


def test_mechanisms_json_names_all_five():
    m = json.loads((DECLINE / "mechanisms.json").read_text())
    assert set(m) == set(CASES)
    for c in CASES:
        assert m[c]["status"] == "named"
        assert m[c]["primary"] in {
            "H1_rounding_non_planarity",
            "H2_equal_angle_ties",
            "H2_atan2_order_mismatch",
            "H3_zero_length_edge",
            "successor_non_injective",
        }
        names = {x["name"] for x in m[c]["mechanisms"]}
        assert "successor_non_injective" in names
        assert m[c]["decline_site"]["used"] == 1


def test_dumps_parse_and_match_decline_site():
    for c in CASES:
        d = json.loads((DECLINE / "dumps" / f"{c}.json").read_text())
        assert "vertices" in d and "edges" in d and "half_edges" in d
        assert d["decline"]["used"] == 1
        assert d["decline"]["bound"] == 0


def test_primary_partition_h1_h2():
    m = json.loads((DECLINE / "mechanisms.json").read_text())
    for c in H2:
        assert m[c]["primary"] == "H2_equal_angle_ties"
    for c in H1:
        assert m[c]["primary"] == "H1_rounding_non_planarity"


@pytest.fixture(scope="module")
def decline_rings():
    return json.loads((DECLINE / "decline_rings.json").read_text())


@pytest.mark.parametrize("case", H2)
@pytest.mark.xfail(strict=True, reason="plan 48 P3: H2 equal-angle ties still declines at :885")
def test_xfail_h2_ring_passes_after_robust_walk(probe, decline_rings, case):
    from test_bg_eo_stitch import probe_output
    size, _nr, _blob = probe_output(probe, decline_rings[case], [0, 0, 4096, 4096])
    assert size >= 0, f"{case} still declines size={size}"


@pytest.mark.parametrize("case", H1)
@pytest.mark.xfail(strict=True, reason="plan 48 P3: H1 rounding non-planarity still declines at :885")
def test_xfail_h1_ring_passes_after_robust_walk(probe, decline_rings, case):
    from test_bg_eo_stitch import probe_output
    size, _nr, _blob = probe_output(probe, decline_rings[case], [0, 0, 4096, 4096])
    assert size >= 0, f"{case} still declines size={size}"
