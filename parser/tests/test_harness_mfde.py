"""Tests for `harness/checks/mfde.py`'s entry-count and `nregion` checks
(brief 17): both must judge G's *set* of observed values as a subset of R's
observed set for that level, per `DESIGN.md` sections 3-4 -- not require
every generated parcel to match only the profile's dominant value. Uses
small synthetic profile dicts (not a real disc), monkeypatching
`generated_profile` so `_run_mfde` never touches a real ALLDATA.KWI file."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.checks import mfde as mfde_module
from harness.checks.mfde import _run_mfde
from harness.context import Context

_REF_PROFILE = {
    "mfde": {"absent": [4294967295, 0]},
    "levels": {
        "0": {
            "mfde": {
                # Dominant 20, real minority tail at 21/35 per DESIGN.md sec.4.
                "entry_count_hist": {"20": 3600000, "21": 5000, "35": 12},
                "absent_values_observed": {"4294967295,0": 3700000},
                "per_entry_index_class_hist": {
                    "1": {"in_buffer": 3700000},
                },
            },
            # Dominant 1, real minority at 0 per DESIGN.md sec.3.
            "nregion_hist": {"0": 65536, "1": 3639335},
        },
    },
}


def _ctx_with_ref_profile() -> Context:
    ctx = Context(reference=None, generated="unused.KWI", config={"layers_present": ["map"]})
    ctx._profile_cache["map"] = _REF_PROFILE
    return ctx


def _run_with_generated(monkeypatch, g_profile: dict):
    ctx = _ctx_with_ref_profile()
    monkeypatch.setattr(mfde_module, "generated_profile", lambda path: g_profile)
    return _run_mfde(ctx)


def _g_profile(entry_counts: dict, nregion: dict) -> dict:
    return {
        "levels": {
            "0": {
                "mfde": {
                    "entry_count_hist": entry_counts,
                    "absent_values_observed": {"4294967295,0": 1},
                    "per_entry_index_class_hist": {"1": {"in_buffer": 1}},
                },
                "nregion_hist": nregion,
            },
        },
    }


def test_entry_count_passes_for_nondominant_profiled_value(monkeypatch):
    g_profile = _g_profile({"21": 1}, {"1": 1})
    result = _run_with_generated(monkeypatch, g_profile)
    assert result.status == "PASS", result.message


def test_entry_count_fails_for_value_absent_from_profile(monkeypatch):
    g_profile = _g_profile({"99": 1}, {"1": 1})
    result = _run_with_generated(monkeypatch, g_profile)
    assert result.status == "FAIL"
    assert any("99" in f and "entry count" in f for f in result.details["failures"])


def test_nregion_passes_for_nondominant_profiled_value(monkeypatch):
    g_profile = _g_profile({"20": 1}, {"0": 1})
    result = _run_with_generated(monkeypatch, g_profile)
    assert result.status == "PASS", result.message


def test_nregion_fails_for_value_absent_from_profile(monkeypatch):
    g_profile = _g_profile({"20": 1}, {"2": 1})
    result = _run_with_generated(monkeypatch, g_profile)
    assert result.status == "FAIL"
    assert any("2" in f and "nregion" in f for f in result.details["failures"])


def test_dominant_only_case_still_passes(monkeypatch):
    """WP1 today only emits the dominant entry count and nregion=0; this
    must still PASS after the widening (contract: "must not turn any
    currently-passing check into a FAIL")."""
    g_profile = _g_profile({"20": 1}, {"0": 1})
    result = _run_with_generated(monkeypatch, g_profile)
    assert result.status == "PASS", result.message
