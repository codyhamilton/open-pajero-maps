"""Synthetic-only proof of plan 32's census/discharge gates."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "other_kind_census", REPO / "docs/plans/32-other-kind-classify-joins/census.py")
assert SPEC and SPEC.loader
census = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(census)


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def inputs(tmp_path):
    dump = tmp_path / "dump"
    dump.mkdir()
    manifest = dict(tool="quantisation_roundtrip", engine="c", row_size=8, kinds={})
    for kind in census.KINDS:
        (dump / f"{kind}.bin").write_bytes(b"")
        manifest["kinds"][kind] = dict(file=f"{kind}.bin", row_size=8, rows=0)
    write(dump / "dump_manifest.json", manifest)
    report_path, guard_path, control_path = [tmp_path / f"{k}.json" for k in ("report", "guard", "control")]
    totals = {k: dict(failing=0) for k in (*census.KINDS, *census.POINT_KINDS, "completeness")}
    write(report_path, dict(totals=totals, dump={k: 0 for k in census.KINDS},
                            timing=dict(workers=6, pss_peak_kb=1024)))
    write(guard_path, dict(exit=0, memory_peak=2048, cgroup_error=None, cwd=str(tmp_path), argv=[
        ".venv-rp/bin/python", "-B", "parser/tools/quantisation_roundtrip.py",
        "--disc", "output/scratch-29/G_new/ALLDATA.KWI", "--spool", "/nonexistent/spool",
        "--out", str(report_path), "-j", "6", "--engine", "c",
        "--dump-failures", str(dump), "--dump-kinds", ",".join(census.KINDS)]))
    write(control_path, dict(pass_=True, comparisons=dict(totals={
        k: dict(new=dict(failing=0)) for k in census.KINDS})))
    control = census.load(control_path)
    control["pass"] = control.pop("pass_")
    write(control_path, control)
    header = tmp_path / "header.tsv"
    header.write_text("\t".join(census.ASSIGNMENT_COLUMNS) + "\n", encoding="utf-8")
    return dict(dump=dump, report=report_path, guard=guard_path, control=control_path,
                out=tmp_path / "result", header=header)


def scan(inputs):
    return census.main(["census", "--dump-dir", str(inputs["dump"]),
                        "--report", str(inputs["report"]), "--guard", str(inputs["guard"]),
                        "--control", str(inputs["control"]), "--out-dir", str(inputs["out"])])


def publish(inputs):
    return census.main(["publish", "--census", str(inputs["out"] / "census.json"),
                        "--assignment-header", str(inputs["header"]), "--out-dir", str(inputs["out"])])


def mutate(path, edit):
    data = census.load(path)
    edit(data)
    write(path, data)


def test_empty_census_and_header_only_publication(inputs):
    assert scan(inputs) == 0
    record = census.load(inputs["out"] / "census.json")
    assert record["branch_flag"] == "all_live_empty"
    assert record["disc_pin"] == census.DISC_PIN
    assert record["control"] == dict(pass_failing_counts=True, plan29_pass=True)
    assert record["excluded"]["completeness"]["status"] == "excluded"
    assert [p["kind"] for p in record["point_kinds"]] == list(census.POINT_KINDS)
    assert all(p["status"] == "out_of_scope" and p["k1_failing"] == 0 for p in record["point_kinds"])
    assert all(r["failing_rows"] == r["k1_failing"] == 0 and r["native_key_set"] == []
               for r in record["kinds"])
    assert all(r["dump_sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
               and r["workers"] == 6 and r["memory_peak_bytes"] == 2048 for r in record["kinds"])
    assert len((inputs["out"] / "census.tsv").read_text().splitlines()) == 5
    assert publish(inputs) == 0
    for kind in census.KINDS:
        assert (inputs["out"] / f"assignments/{kind}_assignment.tsv").read_bytes() == inputs["header"].read_bytes()


@pytest.mark.parametrize("defect", ["fractional", "manifest", "k1", "missing", "zero_size", "wrong_file"])
def test_dump_inconsistencies_fail_before_writes(inputs, defect):
    manifest = inputs["dump"] / "dump_manifest.json"
    if defect == "fractional":
        (inputs["dump"] / "name_anchor.bin").write_bytes(b"x")
    elif defect == "manifest":
        mutate(manifest, lambda d: d["kinds"]["name_anchor"].update(rows=1))
    elif defect == "k1":
        mutate(inputs["report"], lambda d: d["totals"]["name_anchor"].update(failing=1))
    elif defect == "missing":
        (inputs["dump"] / "name_anchor.bin").unlink()
    elif defect == "zero_size":
        mutate(manifest, lambda d: d["kinds"]["name_anchor"].update(row_size=0))
    else:
        mutate(manifest, lambda d: d["kinds"]["name_anchor"].update(file="ALLDATA.KWI"))
    assert scan(inputs) == 2
    assert not inputs["out"].exists()


@pytest.mark.parametrize("defect", ["workers", "peak", "exit", "disc", "report_path"])
def test_guard_provenance_required(inputs, defect):
    if defect == "workers":
        mutate(inputs["report"], lambda d: d["timing"].update(workers=7))
    elif defect == "peak":
        mutate(inputs["guard"], lambda d: d.update(memory_peak=None))
    elif defect == "exit":
        mutate(inputs["guard"], lambda d: d.update(exit=1))
    else:
        flag = "--disc" if defect == "disc" else "--out"
        mutate(inputs["guard"], lambda d: d["argv"].__setitem__(d["argv"].index(flag) + 1, "wrong"))
    assert scan(inputs) == 2
    assert not inputs["out"].exists()


def test_nonempty_records_exact_row_interval_and_refuses_publish(inputs):
    (inputs["dump"] / "name_anchor.bin").write_bytes(b"x" * 16)
    mutate(inputs["dump"] / "dump_manifest.json", lambda d: d["kinds"]["name_anchor"].update(rows=2))
    mutate(inputs["report"], lambda d: (d["totals"]["name_anchor"].update(failing=2), d["dump"].update(name_anchor=2)))
    mutate(inputs["control"], lambda d: d["comparisons"]["totals"]["name_anchor"]["new"].update(failing=2))
    assert scan(inputs) == 0
    record = census.load(inputs["out"] / "census.json")
    assert record["branch_flag"] == 'nonempty_kinds=["name_anchor"]'
    assert record["nonempty_kinds"] == ["name_anchor"]
    row = next(r for r in record["kinds"] if r["kind"] == "name_anchor")
    assert row["failing_rows"] == 2 and row["dump_row_ids"] == dict(start=0, stop=2, step=1)
    assert row["native_key_set"] is None
    assert publish(inputs) == 2
    assert not (inputs["out"] / "assignments").exists()


@pytest.mark.parametrize("defect", ["count", "verdict"])
def test_control_failure_recorded_and_publication_refused(inputs, defect):
    if defect == "count":
        mutate(inputs["control"], lambda d: d["comparisons"]["totals"]["name_anchor"]["new"].update(failing=1))
    else:
        mutate(inputs["control"], lambda d: d.update({"pass": False}))
    assert scan(inputs) == 1
    assert publish(inputs) == 2
    assert not (inputs["out"] / "assignments").exists()


def test_stale_evidence_and_edited_census_refused(inputs):
    assert scan(inputs) == 0
    mutate(inputs["out"] / "census.json", lambda d: d.update(disc_pin="wrong"))
    assert publish(inputs) == 2
    assert scan(inputs) == 0
    # A metadata-only evidence change also invalidates the recorded provenance.
    mutate(inputs["report"], lambda d: d.update(extra="changed"))
    assert publish(inputs) == 2
    assert not (inputs["out"] / "assignments").exists()


def test_changed_assignment_schema_refused(inputs):
    assert scan(inputs) == 0
    inputs["header"].write_text("changed\n")
    assert publish(inputs) == 2
    assert not (inputs["out"] / "assignments").exists()


def test_point_kind_failure_is_named_as_carry(inputs):
    mutate(inputs["report"], lambda d: d["totals"]["road_point"].update(failing=3))
    assert scan(inputs) == 0
    assert census.load(inputs["out"] / "census.json")["carried_point_kinds"] == ["road_point"]


def test_symlink_dump_and_hardlinked_output_refused(inputs):
    bin_path = inputs["dump"] / "name_anchor.bin"
    bin_path.unlink()
    bin_path.symlink_to(inputs["report"])
    assert scan(inputs) == 2
    bin_path.unlink()
    bin_path.write_bytes(b"")
    inputs["out"].mkdir()
    (inputs["out"] / "census.json").hardlink_to(inputs["report"])
    before = inputs["report"].read_bytes()
    assert scan(inputs) == 2
    assert inputs["report"].read_bytes() == before
