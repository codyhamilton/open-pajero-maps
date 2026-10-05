"""Synthetic TSV/JSON census and merge checks; never open a real disc or spool."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "docs/plans/30-2-01-source-data-parity/fingerprint.py"
SPEC = importlib.util.spec_from_file_location("parity_fingerprint", SCRIPT)
fp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fp)

# A subdivided rectangle, including its repeated closing coordinate.
T1 = [(1, 0), (170 / 256, 0), (85 / 256, 0), (0, 0), (0, 85 / 256),
      (0, 170 / 256), (0, 1), (85 / 256, 1), (170 / 256, 1), (1, 1),
      (1, 170 / 256), (1, 85 / 256), (1, 0)]
T2 = T1[3:-1] + T1[:4]


def write_table(path, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def read_table(path):
    with path.open() as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


@pytest.fixture
def dataset(tmp_path):
    members, membership, joined = [], [], []
    t1_count = 0
    for dump in range(342):
        native = {name: 0 for name in fp.NATIVE}
        native.update(ix=dump, iy=100, code=321 if dump == 246 else 288, shape=-1, vert=-1)
        if dump == 246:
            coords = [[-32, 116], [-31.99, 116], [-32, 116.01], [-32, 116]]
        else:
            template = T1 if t1_count < 191 else T2
            t1_count += 1
            coords = [[-36 + a / 12, 116 + dump / 10000 + b / 8] for a, b in template]
        mechanism = {
            "clipped_ring_area2": 0, "clipped_ring_q": 2, "encoder_emits": False,
            "mechanism": "encoder_drops_clipped_source_sliver", "spool_source_branch": "b",
            "spool_source_cell": [0, dump, 99], "spool_source_ncoord": 4,
            "spool_source_bbox_raw": [1, 1, 2, 3],
        }
        proof_path = tmp_path / f"proof-{dump}.json"
        witness_path = tmp_path / f"witness-{dump}.json"
        branches = ["a"] if dump == 246 else ["c"]
        fp.write_json(proof_path, {
            "native_key": native, "dump_row": dump, "g_cell_type_count": 0,
            "r_slot_status": "resolved", "r_matching_polygons": [{"coords": coords, "n_coords": len(coords)}],
            "r_cell_local_meets": [{"branches": branches}], "mechanism": mechanism,
            "spool_requirement_witness": str(witness_path),
        })
        fp.write_json(witness_path, {"native_key": native, "dump_row": dump, "source": {
            "source_cell": [0, dump, 99], "n_coords": 4, "branch": "b",
            "background_ordinal": 0, "source_cell_sha256": "synthetic", "offset": dump * 100,
        }})
        member = {**native, "dump_row": dump, "membership": "2-01-member", "R_polygon_count": 1,
                  "r_slot_status": "resolved", "r_meeting_polygons": 1, "r_meet_branches": branches[0],
                  "r_proof_path": str(proof_path), "g_cell_type_count": 0,
                  **{k: fp.packed(v) if isinstance(v, list) else str(v) for k, v in mechanism.items()}}
        members.append(member)
        membership.append({**native, "dump_row": dump, "phase3_group": "g-omits-cell-local-dvd-type"})
        joined.append({**native, "dump_row": dump, "plan14_group": "g-omits-cell-local-dvd-type",
                       "rule_id": "O05" if dump in (246, 300) else "O01"})
    paths = {"members": tmp_path / "members.tsv", "membership": tmp_path / "membership.tsv",
             "join": tmp_path / "join.tsv", "output": tmp_path / "fingerprint.tsv",
             "summary": tmp_path / "summary.json"}
    for name, rows in (("members", members), ("membership", membership), ("join", joined)):
        write_table(paths[name], rows)
    return argparse.Namespace(**paths)


def probes(args):
    members = read_table(args.members)
    for pin in fp.PINS:
        path = args.output.parent / f"{pin}.json"
        fp.write_json(path, {
            "schema": "plan30-disc-counts-v1", "pin": pin, "disc_sha256": fp.PINS[pin],
            "inputs_sha256": {fp.relpath(args.members): fp.digest(args.members)},
            "rows": [{**{k: int(m[k]) for k in fp.NATIVE}, "dump_row": int(m["dump_row"]),
                      "type_count": 3 if pin == "successor" and int(m["dump_row"]) == 246 else 0,
                      "slot_status": "resolved"} for m in members],
        })
        setattr(args, f"{pin}_json", path)
    return args


def test_signature_preserves_start_and_winding_but_ignores_translation_scale():
    assert fp.signature(T1) == fp.signature([(10 + a / 12, 100 + b / 8) for a, b in T1])
    assert fp.signature(T1) != fp.signature(T2)
    assert fp.signature(T1) != fp.signature(list(reversed(T1)))
    assert fp.signed_area2_lon_lat(T1) == fp.signed_area2_lon_lat(T2) == 2


def test_census_exhaustive_join_hashes_and_pending_successor(dataset):
    summary = fp.census(dataset)
    rows = read_table(dataset.output)
    assert len(rows) == 342 and len({fp.key(r) for r in rows}) == 342
    assert summary["type_counts"] == {"288": 341, "321": 1}
    assert summary["non_288_dump_rows"] == [246]
    assert summary["rule_counts"] == {"O01": 340, "O05": 2}
    assert {k: v["count"] for k, v in summary["templates"].items()} == {"T1": 191, "T2": 150}
    assert summary["template_exception_dump_rows"] == []
    assert len(summary["inputs_sha256"]) == 3 + 342 * 2 + 1
    assert all(fp.digest(path) == sha for path, sha in summary["inputs_sha256"].items()
               if Path(path).is_absolute())
    assert all(r["G_successor_type_count"] == r["G_successor_sha256"] == "" for r in rows)
    assert rows[246]["R_shape_signature_id"] == "not-288"
    assert json.loads(rows[246]["spool_demander_identity"])["background_ordinal"] == 0
    before = dataset.output.read_bytes(), dataset.summary.read_bytes()
    fp.census(dataset)
    assert before == (dataset.output.read_bytes(), dataset.summary.read_bytes())


def test_wrong_span_is_listed_not_assigned_a_template(dataset):
    path = dataset.output.parent / "proof-341.json"
    data = json.loads(path.read_text())
    for coord in data["r_matching_polygons"][0]["coords"]:
        coord[1] = 116 + (coord[1] - 116) * 2
    fp.write_json(path, data)
    summary = fp.census(dataset)
    assert summary["template_exception_dump_rows"] == [341]
    assert read_table(dataset.output)[341]["R_shape_signature_id"] == "other"


def test_same_span_and_vertex_count_do_not_hide_a_third_signature(dataset):
    path = dataset.output.parent / "proof-341.json"
    data = json.loads(path.read_text())
    data["r_matching_polygons"][0]["coords"][1][1] += 0.001
    fp.write_json(path, data)
    summary = fp.census(dataset)
    assert summary["type288_span_pass_count"] == 341
    assert summary["measured_288_signature_count"] == 3
    assert summary["template_exception_dump_rows"] == [341]


@pytest.mark.parametrize("corruption", ["duplicate-native", "wrong-dump", "missing-member", "wrong-witness"])
def test_census_rejects_broken_joins_or_proof_identity(dataset, corruption):
    if corruption == "wrong-witness":
        path = dataset.output.parent / "witness-0.json"
        data = json.loads(path.read_text())
        data["native_key"]["p6"] = 1
        fp.write_json(path, data)
    else:
        rows = read_table(dataset.join)
        if corruption == "duplicate-native":
            rows.append(rows[0])
        elif corruption == "wrong-dump":
            rows[0]["dump_row"] = "1000"
        else:
            rows.pop()
        write_table(dataset.join, rows)
    with pytest.raises(ValueError):
        fp.census(dataset)
    assert not dataset.output.exists()


def test_merge_populates_from_pinned_counts_and_validates_historical_control(dataset):
    fp.census(dataset)
    fp.merge(probes(dataset))
    rows = read_table(dataset.output)
    assert rows[246]["G_successor_type_count"] == "3"
    assert all(r["G_historical_type_count"] == "0" for r in rows)
    assert all(r["G_successor_sha256"] == fp.PINS["successor"] for r in rows)
    summary = json.loads(dataset.summary.read_text())
    assert summary["G_type_count_totals"] == {"successor": 3, "historical": 0}
    assert fp.relpath(dataset.successor_json) in summary["merge_inputs_sha256"]


@pytest.mark.parametrize("corruption", ["pin", "member-hash", "missing-key", "duplicate-key", "dump", "control", "negative-count"])
def test_merge_rejects_corrupt_probes_without_changing_census(dataset, corruption):
    fp.census(dataset)
    probes(dataset)
    before = dataset.output.read_bytes(), dataset.summary.read_bytes()
    path = dataset.historical_json
    data = json.loads(path.read_text())
    if corruption == "pin":
        data["disc_sha256"] = fp.PINS["successor"]
    elif corruption == "member-hash":
        data["inputs_sha256"][fp.relpath(dataset.members)] = "wrong"
    elif corruption == "missing-key":
        data["rows"].pop()
    elif corruption == "duplicate-key":
        data["rows"].append(data["rows"][0])
    elif corruption == "dump":
        data["rows"][0]["dump_row"] = 1000
    elif corruption == "control":
        data["rows"][0]["type_count"] = 1
    else:
        data["rows"][0]["type_count"] = -1
    fp.write_json(path, data)
    with pytest.raises(ValueError):
        fp.merge(dataset)
    assert before == (dataset.output.read_bytes(), dataset.summary.read_bytes())


def test_pread_refuses_unbounded_oversized_and_out_of_file_reads(tmp_path):
    path = tmp_path / "synthetic-buffer.bin"
    path.write_bytes(b"0123456789")
    reader = fp.BoundedPread(os.open(path, os.O_RDONLY), max_read=4)
    try:
        reader.seek(3)
        assert reader.read(4) == b"3456"
        for length in (-1, 5):
            with pytest.raises(ValueError):
                reader.read(length)
        reader.seek(9)
        with pytest.raises(ValueError):
            reader.read(2)
    finally:
        reader.close()


def test_disc_alias_routes_to_guarded_probe_without_reading_a_disc(monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(fp, "disc", lambda args: seen.append(args) or {"synthetic": True})
    assert fp.main(["--disc", "unused-path", "--pin", "successor", "--output", "unused.json"]) == 0
    assert seen[0].pin == "successor" and seen[0].path == Path("unused-path")
    assert json.loads(capsys.readouterr().out) == {"synthetic": True}


@pytest.mark.parametrize("box,expected", [
    ([-36, -35.9, 112, 112.1], "west"), ([-36, -35.9, 154, 154.1], "east"),
    ([-36, -35.9, 116, 116.1], "south_offshore"), ([-32, -31.9, 116, 116.1], "other"),
])
def test_geographic_band_rule_and_precedence(box, expected):
    assert fp.geographic_band(box) == expected
