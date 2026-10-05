"""Synthetic index/frame bytes only. No ALLDATA.KWI, R disc or spool opens."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "o04_presence_witness", ROOT / "docs/plans/04-c-core-orchestration/triage/o04_seven/presence_witness.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def synthetic_index(tmp_path, member, state="resolved_zero"):
    hardened, _, _ = w.readers()
    hardened.libs()
    from kiwiw.bitutils import geo_secs_bytes
    from kiwiw.grid import ReferenceGrid
    grid = ReferenceGrid.load()
    lmr = grid._level_dict(0)
    pmoff, blockoff, frameoff = 4096, 32768, 65536
    bmt_at = 80
    nbx, nby = 1 + lmr["n_blocks_lng"], 1 + lmr["n_blocks_lat"]
    nblocks = nbx * nby
    pmlen = (bmt_at + 6 * nblocks + 31) // 32 * 32
    data = bytearray(frameoff + 96)
    struct.pack_into(">HH", data, 472, 32, 2048)
    struct.pack_into(">IH", data, 2048, 2 << 8, pmlen // 32)
    struct.pack_into(">HHHHH", data, pmoff + 20, 20, 5, 3, 1, 1)
    for at, key in ((8, "lat_hi"), (11, "lat_lo"), (14, "lon_lo"), (17, "lon_hi")):
        data[pmoff + at:pmoff + at + 3] = geo_secs_bytes(grid.coverage[key])
    for at, key in ((24, "n_blocksets_lat"), (25, "n_blocksets_lng"),
                    (26, "n_blocks_lat"), (27, "n_blocks_lng")):
        data[pmoff + 30 + at] = lmr[key]
    for i in range(4):
        data[pmoff + 58 + 2 * i] = lmr["n_parcels_lat"][i]
        data[pmoff + 59 + 2 * i] = lmr["n_parcels_lng"][i]
    npc_x, npc_y = 1 + lmr["n_parcels_lng"][0], 1 + lmr["n_parcels_lat"][0]
    bx, lx = divmod(member["ix"], npc_x)
    by, ly = divmod(member["iy"], npc_y)
    bsx, blx = divmod(bx, nbx)
    bsy, bly = divmod(by, nby)
    bsi, bi = bsy * (1 + lmr["n_blocksets_lng"]) + bsx, bly * nbx + blx
    struct.pack_into(">HII", data, pmoff + 70, bsi, bmt_at // 2, 6 * nblocks // 2)
    for i in range(nblocks):
        struct.pack_into(">IH", data, pmoff + bmt_at + 6 * i, 0xFFFFFFFF, 0)
    blocklen = (4 + 6 * npc_x * npc_y + 31) // 32 * 32
    bmt_entry = pmoff + bmt_at + bi * 6
    struct.pack_into(">IH", data, bmt_entry, 16 << 8, blocklen // 32)
    for i in range(npc_x * npc_y):
        struct.pack_into(">IH", data, blockoff + 4 + 6 * i, 0xFFFFFFFF, 0)
    slot_at = blockoff + 4 + 6 * (ly * npc_x + lx)
    if state.startswith("resolved") or state in {"bad_background", "bad_directory", "bad_record"}:
        struct.pack_into(">IH", data, slot_at, 32 << 8, 3)
        for at in (36, 42, 48):
            struct.pack_into(">IH", data, frameoff + at, 0xFFFFFFFF, 0)
        if state == "resolved_present" or state in {"bad_background", "bad_record"}:
            struct.pack_into(">IH", data, frameoff + 42, 32, 14)
            # 28-byte background: one class-2 triangle of the demanded code.
            struct.pack_into(">HHHHHH", data, frameoff + 64, 3, 3, 11, 1, 6, (2 << 14) | 1)
            struct.pack_into(">HHHHHH", data, frameoff + 76, 8, 2, member["code"], 0, 2048, 2048)
            data[frameoff + 88:frameoff + 92] = bytes((1, 0, 0, 1))
            if state == "bad_background":
                struct.pack_into(">H", data, frameoff + 64, 0)
            if state == "bad_record":
                struct.pack_into(">H", data, frameoff + 76, 0)
        if state == "bad_directory":
            struct.pack_into(">H", data, frameoff + 34, 1000)
    elif state == "absent_bmt":
        struct.pack_into(">II", data, pmoff + 72, 0xFFFFFFFF, 0)
    elif state == "absent_block":
        struct.pack_into(">IH", data, bmt_entry, 0xFFFFFFFF, 0)
    elif state == "zero_block":
        struct.pack_into(">IH", data, bmt_entry, 16 << 8, 0)
    elif state == "missing_bsmr":
        struct.pack_into(">H", data, pmoff + 28, 0)
    elif state == "zero_slot":
        struct.pack_into(">IH", data, slot_at, 0xFFFFFE, 0)
    elif state == "truncated_bmt":
        struct.pack_into(">I", data, pmoff + 76, (pmlen + 2) // 2)
    path = tmp_path / f"synthetic-{member['dump_row']}-{state}.index"
    path.write_bytes(data)
    return path


@pytest.fixture
def members():
    return w.source_rows()[0]


def cell_row(tmp_path, member, state="resolved_zero"):
    return next(w.probe_cells(synthetic_index(tmp_path, member, state), [member]))


@pytest.mark.parametrize("state,status,count", [
    ("resolved_zero", "resolved", 0), ("resolved_present", "resolved", 1),
    ("empty", "empty_slot", 0), ("absent_bmt", "empty_slot", 0),
    ("absent_block", "empty_slot", 0), ("missing_bsmr", "lookup_failed", None),
    ("zero_block", "lookup_failed", None), ("zero_slot", "lookup_failed", None),
    ("truncated_bmt", "lookup_failed", None), ("bad_directory", "lookup_failed", None),
    ("bad_background", "lookup_failed", None), ("bad_record", "lookup_failed", None),
])
def test_count_requires_positive_index_and_decode_evidence(tmp_path, members, state, status, count):
    row = cell_row(tmp_path, members[0], state)
    assert row["status"] == status
    assert row["type_count"] == count
    assert (w.validate_row(row, members[0]) is None) == (status != "lookup_failed")
    if status == "empty_slot":
        assert row["index_evidence"]["reads"]
    if status == "resolved":
        assert row["frames"][0]["sha256"] == w.sha(bytes.fromhex(row["frames"][0]["frame_bytes"]["hex"]))


@pytest.mark.parametrize("mutation", ["index_hash", "frame_hash", "drop_frame", "counts",
                                      "native_key", "fake_empty", "drop_slots", "outside"])
def test_replay_rejects_forged_absence(tmp_path, members, mutation):
    row = cell_row(tmp_path, members[0], "resolved_present")
    if mutation == "index_hash":
        row["index_evidence"]["reads"][-1]["sha256"] = "0" * 64
    elif mutation == "frame_hash":
        row["frames"][0]["frame_bytes"]["sha256"] = "0" * 64
    elif mutation == "drop_frame":
        row["frames"] = []
    elif mutation == "counts":
        row["frames"][0]["decoded_shape_type_counts"] = {}
        row["frames"][0]["matching_polygon_count"] = row["type_count"] = 0
    elif mutation == "native_key":
        row["p6"] += 1
    elif mutation == "fake_empty":
        row.update(status="empty_slot", frames=[], type_count=0)
    elif mutation == "drop_slots":
        row["index_evidence"]["slots"] = []
    else:
        row["status"] = "outside_coverage"
    assert w.validate_row(row, members[0])


def probe_fixture(tmp_path, members, label, states=None):
    rows = [cell_row(tmp_path, m, (states or {}).get(m["dump_row"], "resolved_zero")) for m in members]
    result = {"schema": w.SCHEMA, "disc": label, "disc_sha256": w.PINS[label],
              "source_sha256": w.source_rows()[1], "reader_sha256": w.reader_hashes(), "rows": rows,
              "pin_verification": "historical-citation" if label == "r" else "streamed-full-sha256"}
    path = tmp_path / f"{label}.json"
    w.write_json(path, result)
    return path


def publish_args(tmp_path, members, states=None):
    return SimpleNamespace(**{label: probe_fixture(tmp_path, members, label, states) for label in w.PINS},
                           tsv=tmp_path / "presence.tsv", json=tmp_path / "presence.json")


def test_all_seven_absence_publish(tmp_path, members):
    args = publish_args(tmp_path, members)
    assert w.publish(args) == 0
    result = json.loads(args.json.read_text())
    assert result["phase1_verified"] and result["absence_proven_count"] == 7
    assert not result["dispositions_assigned"]
    with args.tsv.open() as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert [int(r["dump_row"]) for r in rows] == list(w.TARGETS)
    assert [int(r["dump_row"]) for r in rows if r["stratum"] == "emit-piece"] == [138, 284, 496]
    assert all(r["R_type_count"] == r["G_successor_type_count"] == r["G_historical_type_count"] == "0" for r in rows)


@pytest.mark.parametrize("failure", ["missing", "lookup", "present", "wrong_pin", "source_hash", "reader_hash", "duplicate"])
def test_publish_names_exceptions_and_never_assumes_absence(tmp_path, members, failure):
    args = publish_args(tmp_path, members)
    if failure == "missing":
        args.g_successor = None
    else:
        result = json.loads(args.g_successor.read_text())
        if failure == "lookup":
            result["rows"][0] = cell_row(tmp_path, members[0], "missing_bsmr")
        elif failure == "present":
            result["rows"][0] = cell_row(tmp_path, members[0], "resolved_present")
        elif failure == "wrong_pin":
            result["disc_sha256"] = w.PINS["g_historical"]
        elif failure == "source_hash":
            result["source_sha256"] = {}
        elif failure == "reader_hash":
            result["reader_sha256"] = {}
        else:
            result["rows"][-1] = copy.deepcopy(result["rows"][0])
        w.write_json(args.g_successor, result)
    assert w.publish(args) == 2
    result = json.loads(args.json.read_text())
    assert not result["phase1_verified"] and result["exceptions"]
    if failure in {"present", "lookup"}:
        assert result["absence_proven_count"] == 6
        assert result["exceptions"][0]["dump_row"] == 138
    else:
        assert result["absence_proven_count"] == 0
    if failure != "present":
        assert result["rows"][0]["G_successor_type_count"] is None


def test_unbounded_pread_is_refused(tmp_path):
    import os
    _, fingerprint, _ = w.readers()
    path = tmp_path / "tiny.synthetic"
    path.write_bytes(b"abcd")
    reader = fingerprint.BoundedPread(os.open(path, os.O_RDONLY), max_read=4)
    try:
        for length in (-1, 5):
            with pytest.raises(ValueError):
                reader.read(length)
    finally:
        reader.close()


def test_publish_without_probes_is_light(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "readers", lambda: pytest.fail("light publish imported disc readers"))
    assert w.main(["publish", "--tsv", str(tmp_path / "pending.tsv"),
                   "--json", str(tmp_path / "pending.json")]) == 2
    result = json.loads((tmp_path / "pending.json").read_text())
    assert len(result["rows"]) == len(result["exceptions"]) == 7


def test_cli_requires_explicit_command_and_paths():
    with pytest.raises(SystemExit):
        w.main([])
    with pytest.raises(SystemExit):
        w.main(["--disc", "g_successor"])
