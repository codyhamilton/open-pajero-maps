"""Synthetic disposition tests. No production disc, R disc, spool or K1 run."""
import builtins
import csv
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


d = module("test_o04_disposition_module", ROOT / "docs/plans/33-o04-spool-successor-seven/disposition.py")
fixtures = module("o04_disposition_synthetic_fixtures", Path(__file__).with_name("test_o04_presence_witness.py"))
w = fixtures.w


@pytest.fixture
def args(tmp_path):
    members = w.source_rows()[0]
    phase1 = fixtures.publish_args(tmp_path, members)
    assert w.publish(phase1) == 0
    counts = {"checked": 1800514, "failing": 0, "worst_error_raw": 0.0}
    k1 = tmp_path / "synthetic_k1.json"
    w.write_json(k1, {"pass": True, "errors": [], "expected_k1_exit": 0,
                      "comparisons": {level: {"completeness": {
                          "equal": True, "new": counts, "expected": counts}}
                          for level in ("0", "totals")}})
    return SimpleNamespace(
        presence_json=phase1.json, presence_tsv=phase1.tsv,
        presence_sha256=w.sha(phase1.json.read_bytes()),
        g_successor=phase1.g_successor, g_historical=phase1.g_historical, r=phase1.r,
        k1=k1, k1_sha256=w.sha(k1.read_bytes()),
        json=tmp_path / "disposition.json", tsv=tmp_path / "disposition.tsv")


def update_witness(args, mutate):
    witness = json.loads(args.presence_json.read_bytes())
    mutate(witness)
    w.write_json(args.presence_json, witness)
    args.presence_sha256 = w.sha(args.presence_json.read_bytes())
    with args.presence_tsv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(witness["rows"][0]), delimiter="\t")
        writer.writeheader()
        for row in witness["rows"]:
            writer.writerow({name: w.packed(value) if isinstance(value, (dict, list))
                             else ("" if value is None else value) for name, value in row.items()})


def result(args):
    return json.loads(args.json.read_bytes())


def test_all_seven_closed_with_native_keys_provenance_and_residuals(args, monkeypatch):
    # Guard the actual publisher's I/O, not only its advertised entry point.
    original_path_open, original_open, original_os_open = Path.open, builtins.open, os.open

    def check(path):
        if isinstance(path, int):
            return
        path = Path(path)
        assert path.name != "ALLDATA.KWI"
        assert "spool" not in path.parts and not str(path).startswith("/run/media/")

    def path_open(path, *a, **kw):
        check(path)
        return original_path_open(path, *a, **kw)

    def builtin_open(path, *a, **kw):
        check(path)
        return original_open(path, *a, **kw)

    def os_open(path, *a, **kw):
        check(path)
        return original_os_open(path, *a, **kw)

    monkeypatch.setattr(Path, "open", path_open)
    monkeypatch.setattr(builtins, "open", builtin_open)
    monkeypatch.setattr(os, "open", os_open)
    assert d.publish(args) == 0
    published = result(args)
    assert published["phase2_verified"]
    assert published["verdict_counts"] == {
        "proven-non-deviation": 7, "fix-landed": 0, "conflict-open": 0}
    assert published["K1"]["checked"] == 1800514 and published["K1"]["failing"] == 0
    assert not any(published[n] for n in ("spool_edited", "encode_run", "K1_rerun", "plan04_phase3_closed"))
    assert published["spool_hygiene_residual_rows"] == list(w.TARGETS)
    with args.tsv.open() as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert [int(r["dump_row"]) for r in rows] == list(w.TARGETS)
    for row, member in zip(published["rows"], w.source_rows()[0]):
        assert all(row[n] == member[n] for n in w.NATIVE)
        assert row["cause"] == "spool" and row["rule_id"] == "O04"
        assert row["fix_artifact_paths"] == [] and row["fix_disc_sha256"] is None
        assert row["presence_json_sha256"] == args.presence_sha256
        assert row["K1_sha256"] == args.k1_sha256
        assert len(row["probe_sha256"]) == 3
        assert row["presence_witness_ref"].endswith(f"#dump_row={row['dump_row']}")
        if row["dump_row"] in w.EMIT:
            assert "evidence only" in row["penultimate_counterfactual"]


@pytest.mark.parametrize("label", d.PREFIXES)
@pytest.mark.parametrize("failure", ["lookup_failed", "positive", "missing_evidence", "missing_row",
                                      "empty_without_sentinel", "exceptions", "pending", "bool_zero"])
def test_bad_per_row_witness_never_gets_default_verdict(args, label, failure):
    prefix = d.PREFIXES[label]

    def mutate(witness):
        row = witness["rows"][0]
        if failure == "lookup_failed":
            row[f"{prefix}_slot_status"] = "lookup_failed"
        elif failure == "positive":
            row[f"{prefix}_type_count"] = 1
        elif failure == "missing_evidence":
            row[f"{prefix}_evidence"] = None
        elif failure == "missing_row":
            witness["rows"].pop(0)
        elif failure == "empty_without_sentinel":
            row[f"{prefix}_slot_status"] = "empty_slot"
            row[f"{prefix}_evidence"].update(status="empty_slot", frames=[], type_count=0,
                                             index_evidence={"reads": []})
        elif failure == "exceptions":
            row["exceptions"] = ["unresolved proof"]
        elif failure == "pending":
            row["presence_witness_status"] = "exception"
        else:
            row[f"{prefix}_type_count"] = False

    update_witness(args, mutate)
    assert d.publish(args) == 2
    published = result(args)
    assert published["verdict_counts"] == {
        "proven-non-deviation": 6, "fix-landed": 0, "conflict-open": 1}
    assert published["rows"][0]["dump_row"] == 138
    assert published["rows"][0]["exceptions"]
    assert not published["phase2_verified"]


@pytest.mark.parametrize("label", d.PREFIXES)
def test_replayed_nonzero_probe_cannot_be_hidden_by_zero_summaries(args, label, tmp_path):
    member = w.source_rows()[0][0]
    evidence = fixtures.cell_row(tmp_path, member, "resolved_present")
    evidence["type_count"] = 0  # Lie about the decoded triangle; replay must catch it.
    probe_path = getattr(args, label)
    probe = json.loads(probe_path.read_bytes())
    probe["rows"][0] = evidence
    w.write_json(probe_path, probe)

    def mutate(witness):
        witness["probe_sha256"][w.rel(probe_path)] = w.sha(probe_path.read_bytes())
        witness["rows"][0][f"{d.PREFIXES[label]}_evidence"] = evidence

    update_witness(args, mutate)
    assert d.publish(args) == 2
    assert result(args)["verdict_counts"]["conflict-open"] == 1
    assert any("replay failed" in e for e in result(args)["rows"][0]["exceptions"])


@pytest.mark.parametrize("source", ["presence_json", "presence_tsv", "g_successor", "g_historical", "r", "k1"])
@pytest.mark.parametrize("failure", ["missing", "hash_mismatch"])
def test_missing_inputs_or_hash_mismatch_fail_closed(args, source, failure):
    path = getattr(args, source)
    if failure == "missing":
        path.unlink()
    elif source == "presence_tsv":
        path.write_text(path.read_text().replace("absence-proven", "exception"))
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    assert d.publish(args) == 2
    published = result(args)
    assert not published["phase2_verified"]
    assert published["verdict_counts"]["conflict-open"] == 7
    assert all(row["exceptions"] for row in published["rows"])


@pytest.mark.parametrize("state", ["empty", "absent_bmt", "absent_block"])
def test_empty_slot_requires_replayed_index_sentinel(args, tmp_path, state):
    member = w.source_rows()[0][0]
    evidence = fixtures.cell_row(tmp_path, member, state)
    path = args.r
    probe = json.loads(path.read_bytes())
    probe["rows"][0] = evidence
    w.write_json(path, probe)

    def mutate(witness):
        witness["probe_sha256"][w.rel(path)] = w.sha(path.read_bytes())
        row = witness["rows"][0]
        row["R_evidence"] = evidence
        row["R_slot_status"] = "empty_slot"

    update_witness(args, mutate)
    assert d.publish(args) == 0
    assert result(args)["verdict_counts"]["proven-non-deviation"] == 7


@pytest.mark.parametrize("failure", ["nonzero", "wrong_checked", "kind_changed", "not_passed",
                                     "inconsistent_totals"])
def test_k1_retention_requires_valid_cited_comparison(args, failure):
    k1 = json.loads(args.k1.read_bytes())
    if failure == "nonzero":
        k1["comparisons"]["0"]["completeness"]["new"]["failing"] = 1
    elif failure == "wrong_checked":
        k1["comparisons"]["0"]["completeness"]["new"]["checked"] -= 1
    elif failure == "kind_changed":
        k1["comparisons"]["0"]["completeness"]["equal"] = False
    elif failure == "inconsistent_totals":
        k1["comparisons"]["totals"]["completeness"]["new"]["checked"] -= 1
        k1["comparisons"]["totals"]["completeness"]["expected"]["checked"] -= 1
    else:
        k1["pass"] = False
    w.write_json(args.k1, k1)
    args.k1_sha256 = w.sha(args.k1.read_bytes())
    assert d.publish(args) == 2
    assert result(args)["verdict_counts"]["conflict-open"] == 7
    assert result(args)["K1"]["failing"] is None


def test_cli_requires_publish():
    with pytest.raises(SystemExit):
        d.main([])


def test_retained_tsv_fields_can_exceed_default_csv_limit(args):
    # Frame and index hex in real witnesses may exceed 128 KiB per field.
    previous = csv.field_size_limit()
    update_witness(args, lambda witness: witness["rows"][0].update(retained_note="x" * 140000))
    assert d.publish(args) == 0
    assert result(args)["verdict_counts"]["proven-non-deviation"] == 7
    assert csv.field_size_limit() == previous
