"""K1 failure-dump triage (plan 04, Phase 3, brief 3-05).

`k1_triage.py summary` turns a dump into the cause table's input tables and
`k1_triage.py classify` proves a rules file assigns every dump row to exactly one
cause.  These tests build a small synthetic dump in the manifest layout (three kinds,
two levels, 3,000 rows) and check the summary, the partition engine, the hard errors
and byte-identical output; the real full-disc dump is exercised by the brief's run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import k1_triage  # noqa: E402

FIELDS = [
    ("lat", "f64"), ("lon", "f64"), ("err", "f64"),
    ("ix", "i32"), ("iy", "i32"), ("vx", "i32"), ("vy", "i32"),
    ("reason", "i32"), ("code", "i32"),
    ("p0", "u16"), ("p1", "u16"), ("p2", "u16"), ("p3", "u16"), ("p4", "u16"),
    ("p5", "u16"), ("p6", "u16"), ("depth", "u8"), ("kind", "u8"), ("level", "u8"),
    ("shape", "i32"), ("vert", "i32"), ("onb", "u8"), ("d_any", "f64"),
    ("any_type", "i32"), ("in_eo_same", "u8"), ("in_wn_same", "u8"),
    ("in_eo_any", "u8"), ("src_ix", "i32"), ("src_iy", "i32"), ("src_rec", "i32"),
    ("src_tall", "u8"), ("src_nv", "i32"), ("src_maxseg", "f64"), ("d_src", "f64"),
    ("dcls", "i32"), ("dnv", "i32"),
]
_NP = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
DTYPE = np.dtype([(n, _NP[t]) for n, t in FIELDS], align=True)
INT32_MIN = np.iinfo(np.int32).min
KIND_ROWS = {"background": 1200, "background_boundary": 1200, "interior_cover": 600}


def _rows_for(kind: str, n: int) -> np.ndarray:
    i = np.arange(n)
    r = np.zeros(n, DTYPE)
    r["lat"] = -38.0 + i * 1e-4
    r["lon"] = 145.0 + i * 1e-4
    r["err"] = i * 0.5
    r["ix"] = i % 7
    r["iy"] = i % 5
    r["vx"] = i % 4096
    r["vy"] = i % 4096
    r["reason"] = 4 + (i % 2)
    r["code"] = (i % 3) + 1
    r["p0"] = i % 4
    r["p1"] = (i // 4) % 3
    r["p2"] = (i // 12) % 2
    r["depth"] = i % 7
    r["kind"] = sorted(KIND_ROWS).index(kind)
    r["level"] = i % 2
    r["shape"] = i % 11
    r["vert"] = i % 6
    r["onb"] = i % 16
    r["d_any"] = np.where(i % 5 == 0, np.nan, (i % 10).astype(float))
    r["any_type"] = np.where(i % 5 == 0, -1, i % 3)
    r["in_eo_same"] = i % 2
    r["in_wn_same"] = (i + 1) % 2
    r["in_eo_any"] = i % 2
    r["src_ix"] = np.where(i % 4 == 0, INT32_MIN, i % 3)
    r["src_iy"] = np.where(i % 4 == 0, INT32_MIN, i % 2)
    r["src_rec"] = i % 5
    r["src_tall"] = i % 2
    r["src_nv"] = i % 6
    r["src_maxseg"] = np.where(i % 4 == 0, np.nan, (i % 13).astype(float))
    r["d_src"] = np.where(i % 4 == 0, np.nan, (i % 9).astype(float))
    r["dcls"] = i % 3
    r["dnv"] = i % 4
    return r


def _make_dump(tmp_path: Path):
    dump = tmp_path / "dump"
    dump.mkdir(parents=True, exist_ok=True)
    data = {}
    kinds = {}
    for kind, n in KIND_ROWS.items():
        arr = _rows_for(kind, n)
        data[kind] = arr
        (dump / f"{kind}.bin").write_bytes(arr.tobytes())
        kinds[kind] = {"rows": n, "row_size": DTYPE.itemsize, "file": f"{kind}.bin",
                       "fields": [{"name": n, "type": t} for n, t in FIELDS]}
    manifest = {"tool": "quantisation_roundtrip", "engine": "c",
                "row_size": DTYPE.itemsize,
                "fields": [{"name": n, "type": t} for n, t in FIELDS],
                "kinds": kinds}
    (dump / "dump_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return dump, data


def _rules(tmp_path: Path, name: str, rules: list) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps({"version": 1, "rules": rules}))
    return p


def _tsv(path: Path):
    lines = path.read_text().splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, ln.split("\t"))) for ln in lines[1:] if ln]


def _complete_rules():
    tags = {"background": "bg", "background_boundary": "bb", "interior_cover": "ic"}
    out = []
    for kind in sorted(KIND_ROWS):
        for lvl in (0, 1):
            out.append({"id": f"R_{tags[kind]}{lvl}", "cause": "spool", "kind": kind,
                        "where": [["level", "==", lvl]], "note": "test"})
    return out


def _expected_groups(data, kind, level=None, dropped=None):
    """Distinct group keys of `kind` (optionally one level) as tuples, from the arrays."""
    a = data[kind]
    if level is not None:
        a = a[a["level"] == level]
    keys = {(int(x["level"]), int(x["ix"]), int(x["iy"]), int(x["code"]),
             int(x["p0"]), int(x["p1"]), int(x["p2"]), int(x["p3"]), int(x["p4"]),
             int(x["p5"]), int(x["p6"]), int(x["shape"])) for x in a}
    return keys


# ------------------------------------------------------------------ evidence

def test_summary_totals_and_files(tmp_path):
    dump, data = _make_dump(tmp_path)
    out = tmp_path / "summary"
    assert k1_triage.main(["summary", "--dump", str(dump), "--out", str(out)]) == 0
    for kind in KIND_ROWS:
        assert (out / f"groups_{kind}.tsv").is_file()
    totals = {r["kind"]: r for r in _tsv(out / "totals.tsv")}
    for kind, n in KIND_ROWS.items():
        assert int(totals[kind]["rows_manifest"]) == n
        assert int(totals[kind]["rows_read"]) == n
        assert totals[kind]["equal"] == "1"
    groups = _tsv(out / "groups_background.tsv")
    assert sum(int(r["rows"]) for r in groups) == KIND_ROWS["background"]
    assert {tuple(int(r[c]) for c in ("level", "ix", "iy", "type", "p0", "p1", "p2",
                                      "p3", "p4", "p5", "p6", "shape")) for r in groups} \
        == _expected_groups(data, "background")
    assert (out / "by_level_type.tsv").is_file()
    assert (out / "by_src.tsv").is_file()


def test_classify_complete_partition(tmp_path):
    dump, _ = _make_dump(tmp_path)
    rules = _rules(tmp_path, "rules.json", _complete_rules())
    out = tmp_path / "cls"
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(out)]) == 0
    assert (out / "partition.txt").read_text().splitlines()[-1] == "PARTITION OK"
    counts = _tsv(out / "cause_counts.tsv")
    for kind, n in KIND_ROWS.items():
        assert sum(int(r["rows"]) for r in counts if r["kind"] == kind) == n
    for kind in KIND_ROWS:
        a = np.fromfile(out / f"assign_{kind}.u16", dtype="<u2")
        assert len(a) == KIND_ROWS[kind]
        assert np.all(a != k1_triage.NO_RULE)


def test_classify_dropped_rule_lists_its_groups(tmp_path):
    dump, data = _make_dump(tmp_path)
    rules = [r for r in _complete_rules() if r["id"] != "R_bg0"]
    rules = _rules(tmp_path, "dropped.json", rules)
    out = tmp_path / "cls"
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(out)]) == 1
    assert (out / "partition.txt").read_text().splitlines()[-1] == "PARTITION FAIL"
    un = _tsv(out / "unclassified_groups.tsv")
    got = {tuple(int(r[c]) for c in ("level", "ix", "iy", "type", "p0", "p1", "p2",
                                     "p3", "p4", "p5", "p6", "shape")) for r in un}
    assert got == _expected_groups(data, "background", level=0)
    assert sum(int(r["rows"]) for r in un) == int((data["background"]["level"] == 0).sum())


def test_classify_unknown_column_exits_2(tmp_path):
    dump, _ = _make_dump(tmp_path)
    rules = _rules(tmp_path, "bad.json",
                   [{"id": "X", "cause": "spool", "kind": "background",
                     "where": [["nope", "==", 1]]}])
    out = tmp_path / "cls"
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(out)]) == 2
    assert not (out / "assign_background.u16").exists()


def test_classify_unknown_cause_exits_2(tmp_path):
    dump, _ = _make_dump(tmp_path)
    rules = _rules(tmp_path, "bad2.json",
                   [{"id": "X", "cause": "oops", "kind": "background", "where": []}])
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(tmp_path / "cls")]) == 2


def test_overlapping_rules_first_wins(tmp_path):
    dump, data = _make_dump(tmp_path)
    rules = _rules(tmp_path, "overlap.json", [
        {"id": "A", "cause": "checker", "kind": "background",
         "where": [["level", "==", 0]]},
        {"id": "B", "cause": "spool", "kind": "background", "where": [["code", ">=", 1]]},
    ])
    out = tmp_path / "cls"
    k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                    "--out", str(out)])
    counts = {r["rule_id"]: int(r["rows"]) for r in _tsv(out / "cause_counts.tsv")}
    n0 = int((data["background"]["level"] == 0).sum())
    n1 = KIND_ROWS["background"] - n0
    assert counts["A"] == n0
    assert counts["B"] == n1
    a = np.fromfile(out / "assign_background.u16", dtype="<u2")
    idx0 = np.flatnonzero(data["background"]["level"] == 0)
    assert np.all(a[idx0] == 0)
    assert np.all(a[np.setdiff1d(np.arange(len(a)), idx0)] == 1)


def test_outputs_byte_identical(tmp_path):
    dump, _ = _make_dump(tmp_path)
    rules = _rules(tmp_path, "rules.json", _complete_rules())
    o1, o2 = tmp_path / "s1", tmp_path / "s2"
    assert k1_triage.main(["summary", "--dump", str(dump), "--out", str(o1)]) == 0
    assert k1_triage.main(["summary", "--dump", str(dump), "--out", str(o2)]) == 0
    assert _dir_bytes(o1) == _dir_bytes(o2)
    c1, c2 = tmp_path / "c1", tmp_path / "c2"
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(c1)]) == 0
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(c2)]) == 0
    assert _dir_bytes(c1) == _dir_bytes(c2)


def _dir_bytes(path: Path):
    return {p.name: p.read_bytes() for p in sorted(path.iterdir()) if p.is_file()}


def test_enumerate_row_sum_matches_rule(tmp_path):
    dump, _ = _make_dump(tmp_path)
    rules = _rules(tmp_path, "rules.json", _complete_rules())
    out = tmp_path / "cls"
    assert k1_triage.main(["classify", "--dump", str(dump), "--rules", str(rules),
                           "--out", str(out)]) == 0
    counts = {r["rule_id"]: int(r["rows"]) for r in _tsv(out / "cause_counts.tsv")}
    enum_out = tmp_path / "pinned.tsv"
    assert k1_triage.main(["enumerate", "--dump", str(dump), "--assign", str(out),
                           "--rule", "R_bg0", "--out", str(enum_out)]) == 0
    rows = _tsv(enum_out)
    assert sum(int(r["rows"]) for r in rows) == counts["R_bg0"]
    assert {int(r["level"]) for r in rows} == {0}
    assert {r["kind"] for r in rows} == {"background"}


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
