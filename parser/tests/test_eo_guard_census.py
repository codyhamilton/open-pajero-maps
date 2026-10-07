"""Plan 48 Phase 2: eo_stats census on seeded decline vs clean ring."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
import eo_guard_census as eg  # noqa: E402

DECLINE = (
    ROOT / "docs/plans/04-c-core-orchestration/triage/independent_reviews"
    / "3-14/conditions/eo_decline/decline_rings.json"
)


@pytest.fixture(scope="module")
def census_lib(tmp_path_factory):
    so = tmp_path_factory.mktemp("census") / "probe.so"
    eg.build_probe(so)
    return eg.load_stats_api(so)


def test_former_declines_now_pass(census_lib):
    """Plan 48 P3: all five seeded declines clip without walk_used."""
    lib, fn = census_lib
    rings = json.loads(DECLINE.read_text())
    for name, ring in rings.items():
        lib.kw__eo_stats_reset()
        size, _ = eg.run_ring(fn, ring)
        st = eg.read_stats(lib)
        assert size > 0, (name, size, st)
        assert st["decline_walk_used"] == 0, (name, st)
        assert st["declines_total"] == 0, (name, st)


def test_clean_square_zero_declines(census_lib):
    lib, fn = census_lib
    lib.kw__eo_stats_reset()
    size, _ = eg.run_ring(fn, [(512, 512), (3584, 512), (3584, 3584), (512, 3584)])
    st = eg.read_stats(lib)
    assert size > 0
    assert st["decline_walk_used"] == 0
    assert st["declines_total"] == 0
