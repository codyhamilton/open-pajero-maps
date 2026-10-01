"""K1 `completeness` (plan 04, Phase 2, brief 2-05) and the whole-tool equality.

`k1_cmp_kinds` must give the Python tool's `completeness` verdict exactly: `checked` and
`failing`, the first-N `(cell, type)` samples, from the same decoded pieces and spool
shapes, on every fixture. `test_k1_all_kinds_match_python` runs K1 against `roundtrip` on
every fixture disc and compares EVERY kind and every explained counter."""
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

ALL = {**fx.FIXTURES, **fx.BG_FIXTURES, **fx.CMP_FIXTURES}
NAMES = list(ALL)
ALL_KINDS = tuple(cenc.K1Acc().names) if cenc._load_lib() is not None else ()

# fixtures whose completeness must fail / must stay clean (None: equality only)
FAILS = {"piece_removed": 1, "cmp_tall_removed": 5, "cmp_cover_removed": 1,
         "cmp_tall_small": 5, "cmp_sliver_removed": 1, "cmp_other_type": 1}


def _py(res):
    k = res["levels"]["0"]
    c = k["kinds"]["completeness"]
    smp = [(f["cell"][0], f["cell"][1], f["type"]) for f in k["failures"] if f["kind"] == "completeness"]
    return (c["checked"], c["failing"]), smp


@pytest.fixture(scope="module", params=NAMES)
def fixture(request, tmp_path_factory):
    disc, spool = fx.build_fixture(tmp_path_factory.mktemp(request.param), request.param)
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    return request.param, disc, spool, res


def test_verdict_equals_the_python_tool(fixture):
    name, disc, spool, res = fixture
    want, py_smp = _py(res)
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "tasks"))
    r = acc.result()
    got = (r["kinds"]["completeness"]["checked"], r["kinds"]["completeness"]["failing"])
    smp = [(s["ix"], s["iy"], s["code"]) for s in r["samples"]["completeness"]]
    print(f"\n{name}: python {want} k1 {got} samples {smp}")
    assert got == want, name
    assert smp == py_smp[:cenc.K1_SAMPLE] or got[1] > cenc.K1_SAMPLE, name
    assert smp == sorted(smp, key=lambda t: (t[1], t[0], t[2])), name


def test_fixture_is_not_vacuous(fixture):
    name, _, _, res = fixture
    (checked, failing), _ = _py(res)
    if name in FAILS:
        assert failing >= FAILS[name] if name != "cmp_sliver_removed" else failing == 1, (name, checked, failing)
    if name == "clean":
        assert checked > 0 and failing == 0


def test_band_partition_and_order_do_not_matter(fixture):
    name, disc, spool, _ = fixture
    ref, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "whole"))
    blob = ref.to_bytes()
    # the completeness verdict of a row band is the Python tool's per-band verdict; the
    # byte-identity gate is order and merge invariance of the same bands
    rows = fx.plan_bands(disc, spool, "rows")
    a, _ = fx.k1_run(disc, spool, rows)
    b, _ = fx.k1_run(disc, spool, rows[::-1])
    assert a.to_bytes() == b.to_bytes(), name
    parts = [fx.k1_run(disc, spool, [p])[0] for p in rows]
    merged = cenc.K1Acc()
    for p in parts[::-1]:
        merged.merge(p)
    assert merged.to_bytes() == a.to_bytes(), name
    for mode in ("tasks", "whole"):
        x, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, mode))
        y, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, mode)[::-1])
        assert x.to_bytes() == y.to_bytes(), (name, mode)
    assert blob == fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "whole"))[0].to_bytes()


def test_one_c_call_per_band(fixture):
    name, disc, spool, _ = fixture
    for mode in ("whole", "rows"):
        plan = fx.plan_bands(disc, spool, mode)
        _, calls = fx.k1_run(disc, spool, plan)
        assert calls == len(plan), (name, mode)


def test_k1_all_kinds_match_python(fixture):
    name, disc, spool, res = fixture
    lv = res["levels"]["0"]
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "tasks"))
    r = acc.result()
    rows = []
    for k in ALL_KINDS:
        py = lv["kinds"][k]
        c = r["kinds"][k]
        rows.append((k, (py["checked"], py["failing"]), (c["checked"], c["failing"])))
        assert (c["checked"], c["failing"]) == (py["checked"], py["failing"]), (name, k)
        if "worst_error_raw" in py:
            assert c["worst"] == pytest.approx(py["worst_error_raw"], abs=1e-6), (name, k)
    assert dict(r["explained"]) == dict(lv["explained"]), name
    print(f"\n{name}: " + " ".join(f"{k}={a[0]}/{a[1]}" for k, a, _ in rows)
          + " | explained " + " ".join(f"{k}={v}" for k, v in r["explained"].items() if v))
