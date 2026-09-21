"""Unit tests for `parser/tools/header_word_census.py`.

Synthetic Map Frame buffers only -- no reference disc is read here.
"""
import io
import json
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import header_word_census as hwc  # noqa: E402

NO_DATA = 0xFFFFFFFF


def _frame(words, nregion, entries, total_len=512):
    """A synthetic Map Frame buffer: 18 big-endian header words, a region list
    of `nregion` u32 words, then 6-byte mfde entries."""
    w = list(words) + [0] * (18 - len(words))
    w[17] = nregion
    buf = bytearray(b"".join(struct.pack(">H", x & 0xFFFF) for x in w))
    buf += b"\x00\x00\x00\x01" * nregion
    for off, size in entries:
        buf += struct.pack(">IH", off, size)
    buf += b"\x00" * max(0, total_len - len(buf))
    return bytes(buf)


# --------------------------------------------------------------- parse_header

def test_parse_header_reads_big_endian_words_and_table():
    # word0 = 80 words = 160 bytes = 36 + 4*1 + 6*20 -> 20 mfde entries.
    entries = [(80, 10)] + [(NO_DATA, 0)] * 19
    buf = _frame([80, 0, 0, 0, 0, 0, 0xE000, 0xFF00, 0, 0x64, 337, 225], 1, entries)
    h = hwc.parse_header(buf, n_basic_map=3, n_ext_map=17)
    assert h["w"][0] == 80 and h["w"][6] == 0xE000 and h["w"][7] == 0xFF00
    assert h["w"][9] == 0x64 and h["w"][10] == 337 and h["w"][11] == 225
    assert h["nreg"] == 1
    assert h["slot0"] == 160 and h["first"] == 160
    assert h["nent"] == 20 and len(h["slots"]) == 20
    assert h["w"][0] * 2 == 36 + 4 * h["nreg"] + 6 * h["nent"]


def test_parse_header_table_length_falls_back_when_no_in_buffer_slot():
    entries = [(NO_DATA, 0)] * 6
    buf = _frame([80], 0, entries)
    h = hwc.parse_header(buf, n_basic_map=3, n_ext_map=3)
    assert h["first"] is None and h["slot0"] is None
    assert len(h["slots"]) == 6  # n_basic_map + n_ext_map


def test_parse_header_rejects_short_buffer():
    assert hwc.parse_header(b"\x00" * 12) is None


# ------------------------------------------------------------- split and misc

def test_heldout_split_is_deterministic_and_about_a_quarter():
    keys = [(0, b, (p,)) for b in range(40) for p in range(100)]
    first = [hwc.heldout(*k) for k in keys]
    assert first == [hwc.heldout(*k) for k in keys]
    share = sum(first) / len(first)
    assert 0.2 < share < 0.3


def test_metre_series_are_sane():
    assert 110_000 < hwc.mlat_m(-30.0) < 112_000
    assert hwc.mlon_m(0.0) > hwc.mlon_m(60.0)


def test_not_a_map_frame_flags_short_and_accepts_plausible():
    buf = _frame([80, 0, 0, 0, 0, 0, 0xE000, 0xFF00, 0, 0x64], 1, [(80, 10)])
    fh = io.BytesIO(buf)
    assert hwc._not_a_map_frame(fh, 0, len(buf)) is None
    assert hwc._not_a_map_frame(fh, len(buf) - 4, len(buf)) is not None
    assert hwc._not_a_map_frame(fh, -1, len(buf)) is not None


# ------------------------------------------------------------ rule derivation

def _agg_with(words=None, geo=None, w0=None, w7k=None):
    a = hwc._new_agg()
    for k, v in (words or {}).items():
        a["words"][k] = Counter(v)
    for k, v in (geo or {}).items():
        a["geo"][k] = Counter(v)
    for k, v in (w0 or {}).items():
        a["w0"][k] = Counter(v)
    for k, v in (w7k or {}).items():
        a["w7k"][k] = Counter(v)
    return a


def test_constant_rule_scores_on_heldout_only():
    agg = _agg_with(words={
        "fit|2|full|normal|6": {0xE000: 90, 0x1234: 10},
        "held|2|full|normal|6": {0xE000: 99, 0x1234: 1},
    })
    r = hwc.constant_rule(agg, 6)
    assert r["table"] == {"2|full|normal": 0xE000}
    assert r["heldout_n"] == 100 and r["heldout_correct"] == 99
    assert r["heldout_accuracy"] == 0.99
    assert r["heldout_unseen_key"] == 0
    assert list(r["heldout_mismatches"]) == ["2|full|normal: 4660 (predicted 57344)"]


def test_constant_rule_counts_unseen_key_as_a_miss():
    agg = _agg_with(words={"held|4|full|normal|9": {100: 7}})
    r = hwc.constant_rule(agg, 9)
    assert r["heldout_unseen_key"] == 7 and r["heldout_accuracy"] == 0.0


def test_rl_rule_table_and_accuracy():
    agg = _agg_with(geo={
        "fit|2|-27000000|250000|250000": {"337,225": 12},
        "held|2|-27000000|250000|250000": {"337,225": 9, "337,226": 1},
        "held|2|-99000000|250000|250000": {"1,2": 2},
    })
    r = hwc.rl_rule(agg)
    assert r["fit_keys"] == 1 and r["fit_ambiguous_keys"] == 0
    assert r["per_word"][10]["heldout_correct"] == 10  # rlx matches on both rows
    assert r["per_word"][10]["heldout_unseen_key"] == 2
    assert r["per_word"][11]["heldout_correct"] == 9
    assert r["per_word"][11]["heldout_n"] == 12


def test_w7_subframe_rule_reports_per_level_accuracy():
    agg = _agg_with(w7k={
        "fit|0|sparse|normal|111": {0x1200: 50},
        "fit|0|sparse|normal|011": {0xFF00: 50},
        "held|0|sparse|normal|111": {0x1200: 25},
        "held|0|sparse|normal|011": {0xFF00: 24, 0x1200: 1},
    })
    r = hwc.w7_subframe_rule(agg)
    assert r["heldout_correct"] == 49 and r["heldout_n"] == 50
    assert r["heldout_accuracy_by_level"] == {"0": 0.98}


def test_word0_rule_uses_the_structural_formula():
    agg = _agg_with(w0={
        "held|2|full|normal": {"n": 100, "formula_consistent": 100,
                               "slot0_defined": 100, "slot0_eq": 95,
                               "first_defined": 100, "first_eq": 100,
                               "bytes160": 100},
        "fit|2|full|normal": {"n": 10, "formula_consistent": 10, "bytes160": 10},
    })
    agg["words"]["fit|2|full|normal|0"] = Counter({80: 10})
    agg["words"]["held|2|full|normal|0"] = Counter({80: 100})
    sec = hwc.build_header_section(agg, 1)["words"]["0"]
    assert sec["heldout_accuracy"] == 1.0
    assert sec["vs_first_data_slot"]["slot0_equal"] == 95
    assert sec["modal_bytes_table"] == {"2|full|normal": 160}


# --------------------------------------------------- exceptions and pointers

def test_word0_exceptions_reconstruct_the_42_from_entry_counts():
    agg = hwc._new_agg()
    agg["n"]["w0_slot0_absent|6"] = 739
    for nent, n in ((20, 881), (21, 19), (22, 15), (23, 8)):
        agg["ne"][f"6|full|normal|nregion1|n_entries{nent}"] = n
    agg["ne"]["6|full|normal|nregion0|n_entries20"] = 14
    out = hwc.w0_exceptions(agg, {"level": 6, "leaves": 939})
    assert out["disagreements_with_checked_rule"] == 0
    assert out["the_42"]["modal"] == "nregion1|n_entries20"
    assert out["the_42"]["count"] == 42
    assert out["the_42"]["breakdown"] == {"nregion1|n_entries21": 19,
                                          "nregion1|n_entries22": 15,
                                          "nregion1|n_entries23": 8}
    # header size classes: 36 + 4*nregion + 6*n_entries
    assert out["header_size_bytes_by_level"]["6"] == {"156": 14, "160": 881,
                                                      "166": 19, "172": 15,
                                                      "178": 8}
    assert "divided" in out["the_42"]["cause"]
    assert out["the_42"]["divided_neighbour_evidence"]["leaves"] == 939


def test_divided_adjacency_census_is_exposed_for_reproduction():
    import inspect
    assert list(inspect.signature(hwc.divided_adjacency_census).parameters) == \
        ["path", "level"]


def test_exempt_section_lists_every_wp2_word_with_r_values():
    agg = _agg_with(w0={"held|2|full|normal": {"nreg1": 5, "nreg0": 2}})
    agg["ex"].update({"13|0": 100, "14|65535": 90, "14|632": 10,
                      "15|1": 100, "ext|2|present8": 100})
    out = hwc.exempt_section(agg)
    assert set(out) == {"n_intersections", "route_planning_level",
                        "n_additional_data", "ext_frame_slots", "nregion"}
    assert out["nregion"]["r_values"] == {"0": 2, "1": 5}
    assert out["n_intersections"]["r_values"] == {"0": 100}
    assert out["route_planning_level"]["r_values"] == {"632": 10, "65535": 90}
    assert out["route_planning_level"]["r_distinct_values"] == 2
    assert out["ext_frame_slots"]["r_populated_entries_by_level"] == {
        "2": {"present8": 100}}


def test_pointer_section_classifies_by_key():
    agg = hwc._new_agg()
    agg["ptrn"].update({"oob|6": 4000, "bad|6|full|normal": 60,
                        "bad|8|full|normal": 5,
                        "badwhy|header llpid out of range": 65})
    out = hwc.pointer_section(agg)
    assert out["non_frame_total"] == 65
    assert out["out_of_buffer_targets_by_level"] == {"6": 4000}
    assert out["non_frame_targets_by_key"]["6|full|normal"] == 60


# ------------------------------------------------------------- determinism

def _demo_agg():
    agg = hwc._new_agg()
    for split, n in (("fit", 30), ("held", 10)):
        for w, v in ((0, 80), (6, 0xE000), (7, 0xFF00), (9, 0x64)):
            agg["words"][f"{split}|2|full|normal|{w}"] = Counter({v: n})
        agg["geo"][f"{split}|2|-27000000|250000|250000"] = Counter({"337,225": n})
        agg["w0"][f"{split}|2|full|normal"] = Counter(
            {"n": n, "formula_consistent": n, "slot0_defined": n, "slot0_eq": n,
             "first_defined": n, "first_eq": n, "bytes160": n, "nreg1": n})
        agg["w7k"][f"{split}|2|full|normal|010"] = Counter({0xFF00: n})
        agg["n"][f"{split}|2|full|normal"] = n
    return agg


def test_build_header_section_is_deterministic():
    a = json.dumps(hwc.build_header_section(_demo_agg(), 1), sort_keys=True)
    b = json.dumps(hwc.build_header_section(_demo_agg(), 1), sort_keys=True)
    assert a == b


def test_every_required_word_is_reported_with_an_accuracy():
    sec = hwc.build_header_section(_demo_agg(), 1)["words"]
    assert set(sec) == {"0", "6", "7", "9", "10", "11"}
    for w in hwc.WORDS:
        entry = sec[str(w)]
        assert entry["name"] == hwc.NAMES[w]
        assert 0.0 <= entry["heldout_accuracy"] <= 1.0


def test_merge_is_order_independent():
    a, b = hwc._new_agg(), hwc._new_agg()
    a["words"]["fit|2|full|normal|6"] = Counter({1: 2})
    a["n"]["fit|2|full|normal"] = 2
    b["words"]["fit|2|full|normal|6"] = Counter({1: 3, 2: 1})
    b["n"]["fit|2|full|normal"] = 4
    x, y = hwc._new_agg(), hwc._new_agg()
    hwc._merge(x, a)
    hwc._merge(x, b)
    hwc._merge(y, b)
    hwc._merge(y, a)
    assert x["words"]["fit|2|full|normal|6"] == y["words"]["fit|2|full|normal|6"]
    assert x["n"] == y["n"]
