"""K1 background kinds (plan 04, Phase 2, brief 2-04).

`k1_bg_kinds` must give the Python tool's `background`, `background_boundary` and
`interior_cover` verdicts exactly: `checked`, `failing` and `worst_error_raw` (6 decimals),
from the same local + tall spool shapes, on every fixture of `BG_FIXTURES`, plus the
clean `FIXTURES`. `INTENT` pins which kinds each fixture must fail (so a fixture can not
go vacuous); `bg_shift_04/_06` straddle the half-unit tolerance, `bg_diamond` puts cover
corners exactly on a cell row line (the point-in-polygon half-open edge rule)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import k1_fixtures as fx  # noqa: E402
from kiwiw import cenc  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")

BG_KINDS = ("background", "background_boundary", "interior_cover")
NAMES = ["clean", "vertex_moved", "piece_removed"] + list(fx.BG_FIXTURES)

# kinds that must have failing > 0 / == 0 per fixture (None: no pin, only equality)
INTENT = {
    "bg_boundary_displaced": ("background_boundary",),
    "bg_cover_displaced": ("interior_cover",),
    "bg_tall_displaced": ("background", "background_boundary"),
    "bg_outside": ("background",),
    "bg_wrong_type": ("background",),
    "bg_shift_06": ("background",),
    "bg_many_failures": ("background", "background_boundary"),
}
CLEAN = ("bg_coarse", "bg_tall", "bg_long_edge", "bg_diamond", "bg_shift_04", "clean")


def _py(res):
    k = res["levels"]["0"]["kinds"]
    return {n: (k[n]["checked"], k[n]["failing"], round(k[n]["worst_error_raw"], 6)) for n in BG_KINDS}


def _c(acc):
    k = acc.result()["kinds"]
    return {n: (k[n]["checked"], k[n]["failing"], round(k[n]["worst"], 6)) for n in BG_KINDS}


@pytest.fixture(scope="module", params=NAMES)
def fixture(request, tmp_path_factory):
    disc, spool = fx.build_fixture(tmp_path_factory.mktemp(request.param), request.param)
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    return request.param, disc, spool, res


def test_verdicts_equal_the_python_tool(fixture):
    name, disc, spool, res = fixture
    want = _py(res)
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "tasks"))
    got = _c(acc)
    print(f"\n{name}")
    for n in BG_KINDS:
        print(f"  {n:22s} python {want[n]}  k1 {got[n]}")
    assert got == want, name


def test_fixture_is_not_vacuous(fixture):
    name, _, _, res = fixture
    want = _py(res)
    if name in INTENT:
        for n in INTENT[name]:
            assert want[n][1] > 0, (name, n, want)
    if name in CLEAN:
        assert all(want[n][1] == 0 for n in BG_KINDS), (name, want)
    if name not in ("piece_removed",):
        assert want["background"][0] > 0 or name == "vertex_moved", (name, want)


def test_band_partition_and_order_do_not_matter(fixture):
    name, disc, spool, _ = fixture
    ref, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "whole"))
    blob = ref.to_bytes()
    for mode in ("tasks", "rows", "rows_rev"):
        acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, mode))
        assert acc.to_bytes() == blob, (name, mode)


def test_one_c_call_per_band(fixture):
    name, disc, spool, _ = fixture
    for mode in ("whole", "rows"):
        plan = fx.plan_bands(disc, spool, mode)
        _, calls = fx.k1_run(disc, spool, plan)
        assert calls == len(plan), (name, mode)


def test_first_n_samples(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "bg_many_failures")
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    kinds = res["levels"]["0"]["kinds"]
    whole, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "whole"))
    rows, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "rows"))
    for kind in ("background", "background_boundary"):
        assert kinds[kind]["failing"] > cenc.K1_SAMPLE, kind
        s = whole.result()["samples"][kind]
        assert len(s) == cenc.K1_SAMPLE
        assert s == sorted(s, key=cenc.k1_sample_key)
        assert s == rows.result()["samples"][kind]


# ------------------------------------------------------------------ inside-side tolerance (3-04)
#
# The `background_boundary` path can not observe the inside interval tolerance (a
# boundary vertex within K1_TOL of a same-type outline already passes the near gate,
# one beyond it is outside every interval), so these fixtures observe it through a
# leaf-filling `interior_cover`, which `inside_batch` tests without the near gate.


@pytest.fixture(scope="module", params=sorted(fx.INSIDE_FIXTURES))
def inside_fixture(request, tmp_path_factory):
    name = request.param
    disc, spool = fx.build_inside_fixture(tmp_path_factory.mktemp(name), name)
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    return name, disc, spool, res


def test_inside_out_verdicts_equal_the_python_tool(inside_fixture):
    name, disc, spool, res = inside_fixture
    want = _py(res)
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "tasks"))
    got = _c(acc)
    print(f"\n{name}")
    for n in BG_KINDS:
        print(f"  {n:22s} python {want[n]}  k1 {got[n]}")
    assert got == want, name


# Failing counts at HEAD. 03: both `K1_TOL` terms decide a cover centre that is 0.3
# raw outside, so it passes. 07: the centre is 0.7 raw out (outside every interval)
# and so are the 35 frame vertices the encoder shares into the left edge cells.
INSIDE_INTENT = {
    "bg_inside_out_03": {"background": 0, "background_boundary": 0, "interior_cover": 0},
    "bg_inside_out_07": {"background_boundary": 35, "interior_cover": 1},
}


def test_inside_out_exact_counts(inside_fixture):
    name, _, _, res = inside_fixture
    want = _py(res)
    for kind, n in INSIDE_INTENT[name].items():
        assert want[kind][1] == n, (name, kind, want)
