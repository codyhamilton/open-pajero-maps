"""K1 core and the point kinds (plan 04, Phase 2, brief 2-03).

`kw_k1_band` -- one C call per (block, row band): D1 decode, then the checks of
`range` (incl. background vertices), `step`, `road_node`, `road_point`,
`name_anchor` and the explained counters -- must give the same `checked`,
`failing` and `explained` numbers as `tools/quantisation_roundtrip.py`
(`roundtrip(..., workers=1)`) on a clean disc and on every injected fault."""
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


def _expected(res):
    lv = res["levels"]["0"]
    return ({k: (lv["kinds"][k]["checked"], lv["kinds"][k]["failing"]) for k in fx.POINT_KINDS},
            dict(lv["explained"]))


def _got(acc):
    r = acc.result()
    return ({k: (r["kinds"][k]["checked"], r["kinds"][k]["failing"]) for k in fx.POINT_KINDS},
            dict(r["explained"]))


@pytest.fixture(scope="module", params=list(fx.FIXTURES))
def fixture(request, tmp_path_factory):
    disc, spool = fx.build_fixture(tmp_path_factory.mktemp(request.param), request.param)
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    return request.param, disc, spool, res


def test_counts_equal_the_python_tool(fixture):
    name, disc, spool, res = fixture
    acc, calls = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "tasks"))
    want, got = _expected(res), _got(acc)
    assert got == want, name
    if name == "clean":
        assert all(c > 0 for k, (c, _) in want[0].items() if k != "road_point"), want
    else:
        assert any(f for _, f in want[0].values()) or any(want[1].values()) or name in (
            "vertex_moved", "piece_removed"), name
    print(name, got)


def test_worst_error_equals_the_python_tool(fixture):
    name, disc, spool, res = fixture
    acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "tasks"))
    r = acc.result()["kinds"]
    for k in fx.POINT_KINDS:
        assert r[k]["worst"] == pytest.approx(res["levels"]["0"]["kinds"][k]["worst_error_raw"],
                                              abs=1e-6), (name, k)


def test_band_partition_and_order_do_not_matter(fixture):
    name, disc, spool, _ = fixture
    ref, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "whole"))
    blob = ref.to_bytes()
    for mode in ("tasks", "rows", "rows_rev"):
        acc, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, mode))
        assert acc.to_bytes() == blob, (name, mode)
    plan = fx.plan_bands(disc, spool, "rows")
    acc, _ = fx.k1_run(disc, spool, plan[::-1])
    assert acc.to_bytes() == blob, name
    # merging per-band accumulators equals one accumulator over all bands
    parts = [fx.k1_run(disc, spool, [p])[0] for p in plan]
    merged = cenc.K1Acc()
    for p in parts[::-1]:
        merged.merge(p)
    assert merged.to_bytes() == blob, name


def test_one_c_call_per_band(fixture):
    name, disc, spool, _ = fixture
    for mode in ("whole", "tasks", "rows"):
        plan = fx.plan_bands(disc, spool, mode)
        _, calls = fx.k1_run(disc, spool, plan)
        assert calls == len(plan), (name, mode)


def test_sample_is_the_first_n_in_order(tmp_path):
    disc, spool = fx.build_fixture(tmp_path, "many_failures")
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    kinds = res["levels"]["0"]["kinds"]
    assert kinds["name_anchor"]["failing"] > cenc.K1_SAMPLE
    assert kinds["road_node"]["failing"] > cenc.K1_SAMPLE
    whole, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "whole"))
    rows, _ = fx.k1_run(disc, spool, fx.plan_bands(disc, spool, "rows"))
    for kind in ("name_anchor", "road_node"):
        s = whole.result()["samples"][kind]
        assert len(s) == cenc.K1_SAMPLE
        assert s == sorted(s, key=cenc.k1_sample_key)
        assert s == rows.result()["samples"][kind]
        # the python tool's reported cells are a subset of the failing cells
        py_cells = {tuple(f["cell"]) for f in res["levels"]["0"]["failures"] if f["kind"] == kind}
        assert py_cells <= {(r["ix"], r["iy"]) for r in s}
    # the first N of the union of per-band first-N lists
    parts = [fx.k1_run(disc, spool, [p])[0].result()["samples"]["name_anchor"]
             for p in fx.plan_bands(disc, spool, "rows")]
    union = sorted((r for p in parts for r in p), key=cenc.k1_sample_key)[:cenc.K1_SAMPLE]
    assert union == whole.result()["samples"]["name_anchor"]
