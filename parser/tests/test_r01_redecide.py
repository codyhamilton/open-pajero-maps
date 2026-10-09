"""Plan 62: r01_redecide pure helpers (ablation configs, attribution, decide limb, G-c3/G-c4 geometry)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "tools")]

import r01_redecide as rd  # noqa: E402


def test_configs_are_single_fix_ablations():
    full = rd.CONFIGS["FULL"]
    assert (full.piecewise, full.far, full.divided, full.same_type) == (True, True, True, True)
    flags = {"-RC2": "piecewise", "-RC3": "far", "-RC4": "divided", "-RC5": "same_type"}
    for name, off in flags.items():
        c = rd.CONFIGS[name]
        for f in ("piecewise", "far", "divided", "same_type"):
            assert getattr(c, f) == (f != off), (name, f)
    p44 = rd.CONFIGS["PLAN44"]
    assert not any((p44.piecewise, p44.far, p44.divided, p44.same_type)) and p44.p44_neigh


def test_old_class_and_radius():
    assert rd.old_class("producer_home_outside_R_cap@16(p45)") == "outside"
    assert rd.old_class("skip_divided_leaf") == "skip"
    with pytest.raises(ValueError):
        rd.old_class("waived")
    assert rd.p44_radius("outside", "8") == 16
    assert rd.p44_radius("build", "11") == 11
    assert rd.p44_radius("ambiguous", "") == 8
    assert rd.radius(rd.CONFIGS["FULL"], "outside", 16) == 8
    assert rd.radius(rd.CONFIGS["-RC3"], "outside", 8) == 16


def test_filter_type():
    cands = [((1, 2, 0, 288), "r0", None), ((1, 2, 1, 321), "r1", None)]
    assert rd.filter_type(cands, 288, True) == [((1, 2, 0, 288), "r0")]
    assert len(rd.filter_type(cands, 288, False)) == 2


def test_decide_class_limb():
    kw = dict(leaf_on_new=True, clip_size=10, byte_hit=False, vert_hit=False)
    assert rd.decide_class(producer_status="producer_none", **kw) == "outside"
    assert rd.decide_class(producer_status="producer-ambiguous", **kw) == "ambiguous"
    assert rd.decide_class(producer_status="unique-byte", **kw) == "no_oe"
    assert rd.decide_class(producer_status="unique-byte", **{**kw, "vert_hit": True}) == "build"
    assert rd.decide_class(producer_status="unique-fragment", **{**kw, "clip_size": 0}) == "source-removed"
    assert rd.decide_class(producer_status="unique-byte", **{**kw, "leaf_on_new": False}) == "removed"


def test_byte_hit_piecewise_vs_whole():
    wires = {b"B"}
    assert rd.byte_hit([b"A", b"B"], b"AB", wires, piecewise=True)
    assert not rd.byte_hit([b"A", b"B"], b"AB", wires, piecewise=False)
    assert rd.byte_hit([b"B"], b"B", wires, piecewise=False)


def test_attribute():
    assert rd.attribute("build", "build", {}) == []
    assert rd.attribute("skip", "build", {"RC4": "build"}) == ["RC4"]
    assert rd.attribute("outside", "build", {"RC2": "build", "RC3": "outside", "RC4": "build",
                                             "RC5": "build"}) == ["RC3"]
    assert rd.attribute("ambiguous", "build", {"RC2": "ambiguous", "RC5": "ambiguous"}) == ["RC2", "RC5"]
    assert rd.attribute("no_oe", "build", {f: "build" for f in rd.FIXES}) == ["joint"]


def test_geometry_helpers():
    assert rd.rect_intersection((0, 0, 2048, 2048), (2048, 0, 4096, 2048)) is None
    assert rd.rect_intersection((0, 0, 2048, 2048), (1024, 1024, 3072, 3072)) == (1024, 1024, 2048, 2048)
    assert rd.strictly_inside((5, 5), (0, 0, 10, 10)) and not rd.strictly_inside((0, 5), (0, 0, 10, 10))
    # old quadrant (2048-4096, 0-2048) of a pardiv1 leaf vs a pardiv2 4x4 new tiling
    new = {(768, c): ((c % 4) * 1024, (c // 4) * 1024, (c % 4 + 1) * 1024, (c // 4 + 1) * 1024)
           for c in range(16)}
    assert rd.covering_leaves((2048, 0, 4096, 2048), new) == [(768, 2), (768, 3), (768, 6), (768, 7)]
    assert rd.covering_leaves((0, 0, 4096, 4096), {(1285,): (0, 0, 4096, 4096)}) == [(1285,)]


def test_src_known_answer():
    assert rd.src_known_answer((rd.SENTINEL, rd.SENTINEL, -1), (1, 2, 3)) == "src_sentinel"
    assert rd.src_known_answer((1, 2, 3), (1, 2, 3, 288)) == "match"
    assert rd.src_known_answer((1, 2, 4), (1, 2, 3)) == "mismatch"
    assert rd.src_known_answer((1, 2, 4), None) == "no_producer"
