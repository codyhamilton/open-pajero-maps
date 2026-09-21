"""Coverage direction for `vocab` and `mfde` (brief 1-04): synthetic profiles."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.checks import mfde as mfde_module, vocab as vocab_module
from harness.context import Context


def _ctx(ref):
    ctx = Context(reference=None, generated="unused", config={"layers_present": ["map"]})
    ctx._profile_cache["map"] = ref
    return ctx


def _vocab_profile(road_hist):
    return {"levels": {"0": {"road": {"road_type_hist": road_hist}}}}


def _run_vocab(monkeypatch, ref, g):
    monkeypatch.setattr(vocab_module, "generated_profile", lambda p: g)
    return vocab_module._run_vocab(_ctx(ref))


def test_vocab_subset_but_poor_fails(monkeypatch):
    ref = _vocab_profile({"1": 500, "2": 300, "3": 200})
    r = _run_vocab(monkeypatch, ref, _vocab_profile({"1": 5}))
    assert r.status == "FAIL"
    assert r.details["coverage_failures"]["0"]["road_type"]["missing_top"][0][0] == "2"
    assert "offenders" not in r.details


def test_vocab_covering_passes(monkeypatch):
    ref = _vocab_profile({"1": 500, "2": 300, "3": 200})
    assert _run_vocab(monkeypatch, ref, _vocab_profile({"1": 1, "2": 1, "3": 1})).status == "PASS"


def test_vocab_rare_tail_within_tol_passes(monkeypatch):
    ref = _vocab_profile({"1": 990, "2": 7, "3": 3})  # 3 is 0.3% < 1% min share
    assert _run_vocab(monkeypatch, ref, _vocab_profile({"1": 1, "2": 1})).status == "PASS"


def test_vocab_low_count_is_advisory(monkeypatch):
    ref = _vocab_profile({"1": 5, "2": 5})
    r = _run_vocab(monkeypatch, ref, _vocab_profile({"1": 1}))
    assert r.status == "PASS"
    assert r.details["advisory_levels"] == ["0"]


def test_vocab_subset_message_not_masked(monkeypatch):
    ref = _vocab_profile({"1": 500, "2": 500})
    r = _run_vocab(monkeypatch, ref, _vocab_profile({"9": 1}))
    assert r.status == "FAIL"
    assert r.details["offenders"] and r.details["coverage_failures"]


def _mfde_profile(entry, nregion):
    return {"mfde": {"absent": [4294967295, 0]},
            "levels": {"0": {"mfde": {"entry_count_hist": entry,
                                      "absent_values_observed": {"4294967295,0": 1},
                                      "per_entry_index_class_hist": {}},
                             "nregion_hist": nregion}}}


def _run_mfde(monkeypatch, ref, g):
    monkeypatch.setattr(mfde_module, "generated_profile", lambda p: g)
    return mfde_module._run_mfde(_ctx(ref))


def test_mfde_subset_but_poor_fails(monkeypatch):
    ref = _mfde_profile({"20": 500, "21": 500}, {"1": 1000})
    r = _run_mfde(monkeypatch, ref, _mfde_profile({"20": 1}, {"1": 1}))
    assert r.status == "FAIL" and r.details["coverage_failures"]
    assert r.details["levels"]["0"]["coverage"]["entry_count"]["missing_top"] == [["21", 500]]


def test_mfde_covering_passes(monkeypatch):
    ref = _mfde_profile({"20": 500, "21": 500}, {"1": 1000})
    assert _run_mfde(monkeypatch, ref, _mfde_profile({"20": 1, "21": 1}, {"1": 1})).status == "PASS"


def test_mfde_low_count_advisory(monkeypatch):
    ref = _mfde_profile({"20": 5, "21": 5}, {"1": 10})
    assert _run_mfde(monkeypatch, ref, _mfde_profile({"20": 1}, {"1": 1})).status == "PASS"
