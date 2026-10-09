"""Plan 68 (p10_bg_dedup) geometry and scoring unit tests (Codex review 1 regressions)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p10_bg_dedup"))

import r_corr  # noqa: E402
import dclass  # noqa: E402
import rules  # noqa: E402


def rect(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float)


def test_near_crossing_perpendicular_rectangles():
    # vertices of each lie far (> 1 raw) from the other's edges, but the rings cross (16 raw^2 shared)
    a = rect(0, 48, 100, 52); b = rect(48, 0, 52, 100)
    assert r_corr.rings_cross(a, b)
    assert r_corr.near(a, b)


def test_near_far_apart_and_touching():
    assert not r_corr.near(rect(0, 0, 10, 10), rect(20, 20, 30, 30))
    assert r_corr.near(rect(0, 0, 10, 10), rect(10.5, 0, 20, 10))


def test_near_nested():
    assert r_corr.near(rect(0, 0, 100, 100), rect(40, 40, 60, 60))


def _pairs(rings):
    recs = [(s, 2, 288, bytes([s]), np.asarray(R, float)) for s, R in enumerate(rings)]
    res, _ex = dclass.leaf_pairs(recs)
    return dict(res)


def test_dclass_contain_simple_both_orders():
    big, small = rect(0, 0, 100, 100), rect(10, 10, 20, 20)
    assert _pairs([big, small]) == {"D-contain/288": 1}
    assert _pairs([small, big]) == {"D-contain/288": 1}


def test_dclass_bowtie_contains_triangle():
    # even-odd bowtie: shoelace area cancels to 0, so the area order picks the wrong direction
    bowtie = np.array([[0, 0], [100, 100], [100, 0], [0, 100]], float)
    tri = np.array([[70, 45], [90, 50], [70, 55]], float)
    assert _pairs([bowtie, tri]) == {"D-contain/288": 1}


def test_dclass_rot_and_overlap():
    a = rect(0, 0, 10, 10)
    assert _pairs([a, np.roll(a, 1, 0)]) == {"D-rot/288": 1}
    assert _pairs([rect(0, 0, 10, 10), rect(5, 5, 15, 15)]) == {"D-overlap/288": 1}


def test_rules_correct():
    assert rules.correct("drop-all", {"class": "R-absent"})
    assert not rules.correct("drop-all", {"class": "R-other"})
    assert rules.correct("keep-first", {"class": "R-one-byte", "position": {"label": "first"}})
    assert not rules.correct("keep-last", {"class": "R-one-byte", "position": {"label": "first"}})
    assert rules.correct("merge-sources", {"class": "R-merged"})
