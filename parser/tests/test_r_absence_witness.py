"""Synthetic index bytes only; never open a live disc, ALLDATA.KWI or spool."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

PLAN = Path(__file__).resolve().parents[2] / "docs/plans/04-c-core-orchestration/triage/name_anchor"
spec = importlib.util.spec_from_file_location("r_absence_witness", PLAN / "witness_p1.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def synthetic_index(tmp_path, state):
    w.libs()
    from kiwiw.bitutils import geo_secs_bytes
    from kiwiw.grid import ReferenceGrid
    grid = ReferenceGrid.load()
    lmr = grid._level_dict(0)
    pmoff, blockoff, frameoff = 4096, 8192, 24576
    bmt_at = 80
    nblocks = (1 + lmr["n_blocks_lng"]) * (1 + lmr["n_blocks_lat"])
    pmlen = (bmt_at + 6 * nblocks + 31) // 32 * 32
    data = bytearray(frameoff + 96)
    struct.pack_into(">HH", data, 472, 32, 2048)
    struct.pack_into(">IH", data, 2048, 2 << 8, pmlen // 32)
    struct.pack_into(">HHHHH", data, pmoff + 20, 20, 5, 3, 1, 1)
    cov = grid.coverage
    for at, key in ((8, "lat_hi"), (11, "lat_lo"), (14, "lon_lo"), (17, "lon_hi")):
        data[pmoff + at:pmoff + at + 3] = geo_secs_bytes(cov[key])
    for at, key in ((24, "n_blocksets_lat"), (25, "n_blocksets_lng"),
                    (26, "n_blocks_lat"), (27, "n_blocks_lng")):
        data[pmoff + 30 + at] = lmr[key]
    for i in range(4):
        data[pmoff + 58 + 2 * i] = lmr["n_parcels_lat"][i]
        data[pmoff + 59 + 2 * i] = lmr["n_parcels_lng"][i]
    npc_x, npc_y = 1 + lmr["n_parcels_lng"][0], 1 + lmr["n_parcels_lat"][0]
    bsi = (541 // npc_y // (1 + lmr["n_blocks_lat"])) * (1 + lmr["n_blocksets_lng"])
    struct.pack_into(">HII", data, pmoff + 70, bsi, bmt_at // 2, 6 * nblocks // 2)
    for i in range(nblocks):
        struct.pack_into(">IH", data, pmoff + bmt_at + 6 * i, 0xFFFFFFFF, 0)
    blocklen = (4 + 6 * npc_x * npc_y + 31) // 32 * 32
    struct.pack_into(">IH", data, pmoff + bmt_at, 4 << 8, blocklen // 32)
    for i in range(npc_x * npc_y):
        struct.pack_into(">IH", data, blockoff + 4 + 6 * i, 0xFFFFFFFF, 0)
    target_slot = (541 % npc_y) * npc_x
    slot_at = blockoff + 4 + 6 * target_slot
    if state in ("populated", "nameless", "decode_error"):
        struct.pack_into(">IH", data, slot_at, 12 << 8, 3)
        if state == "nameless":
            struct.pack_into(">IH", data, frameoff + 48, 0xFFFFFFFF, 0)
        else:
            struct.pack_into(">IH", data, frameoff + 48, 32, 12)
            # Name frame: 6-byte directory, one type-6 record spelling X.
            struct.pack_into(">HHH", data, frameoff + 64, 3, 3, 1)
            struct.pack_into(">HHH", data, frameoff + 70, 9, 6 << 8, 288)
            struct.pack_into(">H", data, frameoff + 84, 1)
            data[frameoff + 86:frameoff + 88] = b"X\0"
            if state == "decode_error":
                struct.pack_into(">H", data, frameoff + 70, 0)
    elif state == "missing":
        struct.pack_into(">H", data, pmoff + 28, 0)
    elif state == "invalid_offset":
        struct.pack_into(">I", data, pmoff + 72, 1000000)
    elif state == "malformed_slot":
        struct.pack_into(">IH", data, slot_at, 0xFFFFFE, 0)
    elif state == "absent_table":
        struct.pack_into(">II", data, pmoff + 72, 0xFFFFFFFF, 0)
    elif state == "absent_block":
        struct.pack_into(">IH", data, pmoff + bmt_at, 0xFFFFFFFF, 0)
    elif state == "zero_size_block":
        struct.pack_into(">IH", data, pmoff + bmt_at, 4 << 8, 0)
    elif state == "truncated_table":
        struct.pack_into(">I", data, pmoff + 76, (pmlen + 2) // 2)
    path = tmp_path / "synthetic.index"
    path.write_bytes(data)
    return path


def verdict_inputs(tmp_path, rows):
    name = {"string_hex": "58", "global_raw": [0, 0], "record_hex": "00",
            "text": "X", "stored_string_hex": "5800", "string_type": 6, "class": 288,
            "raw": [0, 0], "lat": 0, "lon": 0, "record_offset": 0,
            "record_length": 1, "record_sha256": w.sha(b"\0")}
    frame = {"leaf_path": [928], "offset": 0, "length": 1, "sha256": w.sha(b"\0")}
    g = {"drift": [], "target": {"name": name, "frame": frame},
         "historical_disc_sha256": w.G_PIN, "live_total": {}, "failures": []}
    target = {"cell": [0, 541], "record": 0, "lat": 0, "lon": 0, "string_hex": "58",
              "record_sha256": "synthetic", "cell_offset": 0, "cell_length": 1,
              "cell_sha256": "synthetic", "source_distance_raw": 10}
    s = {"drift": [], "target": target, "ancestor_exit": 0,
         "tip_assignment": None, "mesh_assignment": None, "k1_bucket_distance_raw": None,
         "nearest_distance_raw": 10, "k1_bucket_result": "inf", "halo_eligible": False,
         "spool_extractor_tree": "synthetic"}
    r = {"string_hex": "58", "historical_disc_sha256": w.R_PIN,
         "cells": rows, "matches": [], "match_result": "none"}
    scan = {"checked": 1, "rejected": 1, "expected_O03_rejected": 1, "extra_rejected": 0,
            "without_anchor": 0, "per_level": {}, "rejects_tsv": "synthetic"}
    paths = []
    for tag, value in (("g", g), ("s", s), ("r", r), ("scan", scan)):
        path = tmp_path / f"{tag}.json"
        w.write_json(path, value)
        paths.append(path)
    return SimpleNamespace(g=paths[0], spool_json=paths[1], r=paths[2], scan=paths[3],
                           out=tmp_path / "verdict.json", note=tmp_path / "note.md")


def rows_for(path):
    return list(w.disc_cells(path, [(x, y) for y in range(540, 543) for x in (-1, 0, 1)]))


@pytest.mark.parametrize("state,status", [
    ("empty", "empty_slot"), ("populated", "resolved"),
    ("missing", "lookup_failed"), ("invalid_offset", "lookup_failed"),
    ("malformed_slot", "lookup_failed"), ("decode_error", "lookup_failed"),
    ("zero_size_block", "lookup_failed"), ("truncated_table", "lookup_failed")])
def test_absence_requires_real_sentinel(tmp_path, state, status):
    rows = rows_for(synthetic_index(tmp_path, state))
    target = next(r for r in rows if r["cell"] == [0, 541])
    assert target["status"] == status
    assert target["reason"]
    if status != "lookup_failed":
        assert w.validate_cell_evidence(target) is None
        assert target["index_evidence"]["bmt_entry"]["dsa"] == 4 << 8
        slot = target["index_evidence"]["slots"][0]
        assert slot["hex"] == ("ffffffff0000" if state == "empty" else "00000c000003")
        assert slot["sha256"] == w.sha(bytes.fromhex(slot["hex"]))
    else:
        assert w.validate_cell_evidence(target)
    args = verdict_inputs(tmp_path, rows)
    assert w.verdict(args) == (0 if state == "empty" else 2)
    assert json.loads(args.out.read_text())["verdict"] == ("A" if state == "empty" else "drift")


@pytest.mark.parametrize("state,reason", [("absent_table", "absent_BMT_sentinel"),
                                         ("absent_block", "absent_block_DSA_sentinel")])
def test_format_absence_branches(tmp_path, state, reason):
    rows = rows_for(synthetic_index(tmp_path, state))
    assert all(r["reason"] == reason for r in rows if r["cell"][0] >= 0)
    assert all(w.validate_cell_evidence(r) is None for r in rows)
    args = verdict_inputs(tmp_path, rows)
    assert w.verdict(args) == 0


def test_resolved_nameless_frame_supports_a(tmp_path):
    rows = rows_for(synthetic_index(tmp_path, "nameless"))
    target = next(r for r in rows if r["cell"] == [0, 541])
    assert target["status"] == "resolved"
    assert target["frames"][0]["name_string_hex"] == []
    assert w.validate_cell_evidence(target) is None
    assert w.verdict(verdict_inputs(tmp_path, rows)) == 0


@pytest.mark.parametrize("mutation", ["drop_index", "bad_hash", "forged_dsa", "drop_geometry",
                                      "forge_outside", "drop_slot_proof", "duplicate_cell"])
def test_verdict_rejects_unproven_labels(tmp_path, mutation):
    rows = copy.deepcopy(rows_for(synthetic_index(tmp_path, "empty")))
    target = next(r for r in rows if r["cell"] == [0, 541])
    if mutation == "drop_index":
        del target["index_evidence"]
    elif mutation == "bad_hash":
        target["index_evidence"]["reads"][-1]["sha256"] = "0" * 64
    elif mutation == "forged_dsa":
        target["index_evidence"]["bmt_entry"]["dsa"] = 0xFFFFFFFF
    elif mutation == "drop_geometry":
        del rows[0]["geometry"]
    elif mutation == "forge_outside":
        target["status"] = "outside_coverage"
    elif mutation == "drop_slot_proof":
        target["index_evidence"]["slots"] = []
    else:
        rows.append(copy.deepcopy(rows[0]))
    args = verdict_inputs(tmp_path, rows)
    assert w.verdict(args) == 2
    assert json.loads(args.out.read_text())["verdict"] == "drift"


@pytest.mark.parametrize("corruption", ["directory_hash", "subframe_hash", "name_census"])
def test_resolved_frame_requires_decoded_byte_proof(tmp_path, corruption):
    rows = rows_for(synthetic_index(tmp_path, "populated"))
    frame = next(r for r in rows if r["cell"] == [0, 541])["frames"][0]
    if corruption == "directory_hash":
        frame["name_directory"]["sha256"] = "0" * 64
    elif corruption == "subframe_hash":
        frame["name_subframe"]["sha256"] = "0" * 64
    else:
        frame["name_string_hex"] = []
        frame["name_count"] = 0
    assert w.verdict(verdict_inputs(tmp_path, rows)) == 2


def test_r_reader_control_requires_explicit_output(tmp_path):
    spec = importlib.util.spec_from_file_location("r_reader_control", PLAN / "r_reader_control.py")
    control = importlib.util.module_from_spec(spec)
    # Import must not open a disc or run the census.
    spec.loader.exec_module(control)
    with pytest.raises(SystemExit) as exc:
        control.main([])
    assert exc.value.code == 2
