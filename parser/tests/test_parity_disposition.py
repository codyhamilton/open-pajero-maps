"""Synthetic plan-30 probes/publication. No retained spool, PBF or discs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import struct

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "docs/plans/30-2-01-source-data-parity/disposition.py"
SPEC = importlib.util.spec_from_file_location("parity_disposition", SCRIPT)
dp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dp)

T1 = [[1., 0.], [.6640625, 0.], [.33203125, 0.], [0., 0.], [0., .33203125],
      [0., .6640625], [0., 1.], [.33203125, 1.], [.6640625, 1.], [1., 1.],
      [1., .6640625], [1., .33203125], [1., 0.]]
T2 = T1[3:-1] + T1[:4]


def table(path, rows):
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def read_table(path):
    with path.open() as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


@pytest.fixture
def dataset(tmp_path):
    grid = dp.lattice()
    rows, members = [], []
    template_index = 0
    for dump in range(342):
        k = {n: 0 for n in dp.NATIVE}
        k.update(ix=400 + dump, iy=600, code=321 if dump == 246 else 288, shape=-1, vert=-1)
        member = {**k, "dump_row": dump}
        members.append(member)
        r = {**member, "rule_id": "O05" if dump in (246, 300) else "O01", "geographic_band": "other"}
        if dump == 246:
            sig, coords, box = "not-288", [], dp.b4(grid, k["ix"], k["iy"])
        else:
            sig = "T1" if template_index < 191 else "T2"
            template_index += 1
            coords = [T1 if sig == "T1" else T2]
            box = dp.b4(grid, k["ix"] // 4 * 4, k["iy"] // 4 * 4)
            box[1] = box[0] + 4 * grid.cell_lat
            box[3] = box[2] + 4 * grid.cell_lon
        r.update(R_shape_signature_id=sig, R_template_span_ok="true" if dump != 246 else "false",
                 R_polygon_count=1 if dump != 246 else 11, R_cell_local_polygon_count=1,
                 R_vertex_counts="[13]" if dump != 246 else "[28]", R_meet_branches="c" if dump != 246 else "a",
                 R_bbox_lat_lon=dp.packed(box), R_local_signatures=dp.packed(coords),
                 clipped_ring_area2=0, encoder_emits="False", mechanism="encoder_drops_clipped_source_sliver",
                 spool_demander_identity=dp.packed({"source_cell": [0, k["ix"], k["iy"]], "background_ordinal": 0,
                                                   "offset": 0, "length": 0, "n_coords": 4, "source_cell_sha256": "0" * 64}),
                 R_proof_path=f"synthetic/proof-{dump}.json", spool_requirement_witness=f"synthetic/witness-{dump}.json")
        for pin, sha in dp.PINS.items():
            r.update({f"G_{pin}_sha256": sha, f"G_{pin}_type_count": 0, f"G_{pin}_status": "disc-verified:resolved"})
        rows.append(r)
    args = argparse.Namespace(fingerprint=tmp_path / "fingerprint.tsv", fingerprint_summary=tmp_path / "fingerprint_summary.json",
                              members=tmp_path / "members.tsv", output=tmp_path / "inventory.json")
    table(args.members, members)
    table(args.fingerprint, rows)
    summary = {"schema": "plan30-fingerprint-v1", "rows": 342,
               "inputs_sha256": {dp.label(args.members): dp.digest(args.members)},
               "templates": {n: {"normalised_vertices_lat_lon": seq,
                                  "sha256": hashlib.sha256(dp.packed(seq).encode()).hexdigest()}
                             for n, seq in (("T1", T1), ("T2", T2))}}
    dp.write_json(args.fingerprint_summary, summary)
    return args


def publish_args(args):
    return argparse.Namespace(**{**vars(args), "inventory": args.output, "output": args.output.parent / "disposition.tsv",
                                 "summary": args.output.parent / "disposition_summary.json", "spool_json": None,
                                 "pbf_json": None, "spool_run": None, "pbf_run": None})


@pytest.fixture(scope="module")
def production_probe(tmp_path_factory):
    return dp.c_probe(tmp_path_factory.mktemp("production_C"))


def square(box, start=.25, stop=.75):
    a, b, c, d = box
    return [(a + y * (b-a), c + x * (d-c)) for y, x in
            ((start, start), (start, stop), (stop, stop), (stop, start), (start, start))]


def c_event(row, code=None, records=1, kind="spool"):
    code = int(row["code"]) if code is None else code
    tags = {"natural": "wood"} if code == 321 else {"natural": "sea"} if code == 289 else {"building": "yes"}
    return {**dp.native(row), "source": {"kind": kind, "id": 123, "code": code, "mult": 1, "flags": 0, "tags": tags},
            "result": {"variants": {v: {"bytes": 20 if records else 0, "records": records, "mult": 1}
                                    for v in ("original", "clipped", "unit-mult")},
                       "mirror": {"q": 4, "area2": 200, "emits": True},
                       "source_bbox_lat_lon": dp.b4(dp.lattice(), int(row["ix"]), int(row["iy"])),
                       "coords_sha256": "e" * 64}}


def fake_probe(args, kind, events=(), gaps=()):
    rows, _, grid, inputs = dp.context(args)
    acc = dp.Accumulator(rows)
    path = args.output.parent / f"{kind}.json"
    proof = path.with_suffix(".proofs.jsonl")
    with proof.open("w") as fh:
        for event in events:
            acc.accept(event)
            fh.write(dp.packed(event) + "\n")
        for gap in gaps:
            fh.write(dp.packed(gap) + "\n")
    heavy = args.output.parent / ("synthetic.pbf" if kind == "pbf" else "level_0.data")
    inputs.hashes[dp.label(heavy)] = "a" * 64  # Never open these nonexistent synthetic inputs at publication.
    heavy_inputs = [dp.label(heavy)]
    if kind == "spool":
        idx = heavy.with_suffix(".idx")
        inputs.hashes[dp.label(idx)] = "b" * 64
        heavy_inputs.append(dp.label(idx))
    doc = dp.base_document(kind, rows, inputs, grid)
    doc.update(rows=list(acc.rows.values()), scan_complete=True, memory={"max_rss_kib": 1},
               proof_log=dp.label(proof), proof_log_sha256=dp.digest(proof),
               gap_counts=dict(dp.Counter(g["gap"] for g in gaps)), heavy_inputs=heavy_inputs)
    dp.write_json(path, doc)
    run = path.with_suffix(".run.json")
    dp.write_json(run, {"exit": 0, "memory_peak": 1024, "max_rss_kib": 1,
                       "argv": ["python", "-B", str(SCRIPT), kind, "--output", str(path)]})
    return path, run


def test_inventory_and_pending_publish_never_guess_negative(dataset):
    doc = dp.inventory(dataset)
    assert sum(r["lattice"]["template"] for r in doc["rows"]) == 341
    assert not doc["rows"][246]["lattice"]["template"]
    result = dp.publish(publish_args(dataset))
    assert result["counts"] == {"supply-path": 0, "unfixable-proven": 0, "conflict-open": 342}
    assert result["type288_disposition"] == "uniform"
    assert len(result["open_rows"]) == 342
    assert all(r["discriminators_tried"]["unresolved"] == ["pending-spool", "pending-pbf"] for r in result["open_rows"])


@pytest.mark.parametrize("field,value", [("G_successor_type_count", 1), ("G_historical_sha256", "bad"),
                                         ("G_successor_status", "pending-disc-probe")])
def test_inventory_requires_completed_phase1(dataset, field, value):
    rows = read_table(dataset.fingerprint)
    rows[0][field] = value
    table(dataset.fingerprint, rows)
    with pytest.raises(ValueError, match="Phase-1"):
        dp.inventory(dataset)


def test_grid_exception_not_folded_into_lattice(dataset):
    rows = read_table(dataset.fingerprint)
    box = json.loads(rows[0]["R_bbox_lat_lon"])
    box[2] += .000001
    rows[0]["R_bbox_lat_lon"] = dp.packed(box)
    table(dataset.fingerprint, rows)
    assert not dp.inventory(dataset)["rows"][0]["lattice"]["template"]


def test_c_square_line_clip_and_mult(production_probe):
    grid = dp.lattice()
    row = {"ix": 400, "iy": 600}
    box = dp.b4(grid, 400, 600)
    result = dp.evaluate(square(box), 288, 1, 0, row, grid, production_probe)
    assert result["variants"]["original"]["records"] > 0
    assert result["mirror"]["emits"]
    a, b, c, d = box
    line = [(a, c), (b, c), (b, c), (a, c)]
    result = dp.evaluate(line, 288, 1, 0, row, grid, production_probe)
    assert all(v["records"] == 0 for v in result["variants"].values())
    assert not result["mirror"]["emits"]
    # Counterfactual mult=1 may rescue a footprint without moving coordinates.
    result = dp.evaluate(square(box, .499, .501), 288, 4096, 0, row, grid, production_probe)
    assert result["variants"]["unit-mult"]["records"] > 0


def test_relation_node_join_reverse_member_and_hole_C(production_probe):
    grid = dp.lattice()
    box = dp.b4(grid, 400, 600)
    outer, hole = square(box, -.5, 1.5), square(box, -.01, 1.01)
    ways = {10: ([1, 2, 3], outer[:3]), 11: ([1, 4, 3], [outer[0], outer[3], outer[2]]),
            12: ([5, 6, 7, 8, 5], hole)}
    members = [{"type": "w", "ref": i, "role": "inner" if i == 12 else "outer"} for i in ways]
    rings = dp.join_rings(members, ways)
    dp.validate_rings(rings)
    joined = dp.stitch_rings(rings)
    assert set(joined) <= set(outer + hole)  # bridge endpoints are existing source coordinates.
    result = dp.evaluate(joined, 321, 1, 0, {"ix": 400, "iy": 600}, grid, production_probe)
    assert all(v["records"] == 0 for v in result["variants"].values())  # target entirely in the hole.


@pytest.mark.parametrize("problem", ["missing", "open", "nested", "branch", "outside-hole"])
def test_relation_gaps_not_fake_polygons(problem):
    coords = [(0., 0.), (0., 2.), (2., 2.), (2., 0.), (0., 0.)]
    ways = {10: ([1, 2, 3, 4, 1], coords)}
    members = [{"type": "w", "ref": 10, "role": "outer"}]
    if problem == "missing":
        members[0]["ref"] = 999
    elif problem == "open":
        ways[10] = ([1, 2, 3, 4], coords[:-1])
    elif problem == "nested":
        members[0]["type"] = "r"
    elif problem == "branch":
        ways = {10: ([1, 2], coords[:2]), 11: ([2, 3], coords[1:3]), 12: ([2, 4], [coords[1], coords[3]])}
        members = [{"type": "w", "ref": i, "role": "outer"} for i in ways]
    else:
        ways[11] = ([5, 6, 7, 8, 5], [(y+10, x+10) for y, x in coords])
        members.append({"type": "w", "ref": 11, "role": "inner"})
    with pytest.raises(ValueError):
        dp.validate_rings(dp.join_rings(members, ways))


def test_bounded_index_and_column_corruption(tmp_path):
    path = tmp_path / "level_0.idx"
    path.write_bytes(b"KWSPIDX1" + struct.pack("<5Q", 2, 2, 0, 0, 0) + struct.pack("<2i2i2Q2Q", 7, 8, 4, 4, 0, 72, 72, 72))
    assert list(dp.index_entries(path)) == [(7, 4, 0, 72), (8, 4, 72, 72)]
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(ValueError, match="length"):
        list(dp.index_entries(path))
    with pytest.raises(ValueError, match="malformed"):
        dp.checked_columns(struct.pack("<9Q", *([0] * 9)) + b"x")


def test_production_error_and_vertex_limit_stay_gap(production_probe, tmp_path):
    class FailedProbe:
        def run(self, *args):
            return -2, 0
    grid = dp.lattice()
    r = {n: 0 for n in dp.NATIVE} | {"ix": 400, "iy": 600, "code": 288, "dump_row": 0}
    writer = dp.ProbeWriter(tmp_path / "proofs.jsonl", [r], grid, FailedProbe())
    writer.geometry(square(dp.b4(grid, 400, 600)), {"kind": "way", "id": 1, "code": 288, "mult": 1, "flags": 0})
    doc = writer.finish()
    assert sum(doc["gap_counts"].values()) == 1 and doc["rows"][0]["supply"] is None
    ring = square(dp.b4(grid, 400, 600))
    with pytest.raises(ValueError, match="native-C vertex limit"):
        dp.evaluate([ring[0]] * (dp.MAX_C_VERTICES + 1), 288, 1, 0, r, grid, FailedProbe())


def test_wrong_code_is_alternate_not_supply_and_outlier_independent(dataset):
    dp.inventory(dataset)
    rows = read_table(dataset.fingerprint)
    args = publish_args(dataset)
    args.spool_json, args.spool_run = fake_probe(dataset, "spool", [c_event(rows[0], code=289)])
    args.pbf_json, args.pbf_run = fake_probe(dataset, "pbf", [c_event(rows[246], kind="way")])
    summary = dp.publish(args)
    assert summary["counts"] == {"supply-path": 1, "unfixable-proven": 341, "conflict-open": 0}
    table_rows = read_table(args.output)
    assert table_rows[0]["cause_class"] == "type-semantic mismatch" and table_rows[0]["verdict"] == "unfixable-proven"
    assert summary["type321_row246"]["verdict"] == "supply-path"
    assert summary["type321_row246"]["successor_implement_path"]
    assert summary["type288_disposition"] == "split"


def test_gap_does_not_hide_positive_but_blocks_negative(dataset):
    dp.inventory(dataset)
    rows = read_table(dataset.fingerprint)
    args = publish_args(dataset)
    args.spool_json, args.spool_run = fake_probe(dataset, "spool", [c_event(rows[246])])
    args.pbf_json, args.pbf_run = fake_probe(dataset, "pbf", gaps=[{"gap": "missing-member", "source": {"id": 999},
                                                                  "affected_dump_rows": [0, 246]}])
    result = dp.publish(args)
    assert result["counts"] == {"supply-path": 1, "unfixable-proven": 340, "conflict-open": 1}
    assert result["open_rows"][0]["dump_row"] == 0


def test_unproven_321_negative_remains_open(dataset):
    dp.inventory(dataset)
    args = publish_args(dataset)
    args.spool_json, args.spool_run = fake_probe(dataset, "spool")
    args.pbf_json, args.pbf_run = fake_probe(dataset, "pbf")
    result = dp.publish(args)
    assert result["counts"] == {"supply-path": 0, "unfixable-proven": 341, "conflict-open": 1}
    assert result["open_rows"][0]["dump_row"] == 246


def test_degenerate_321_ceiling_needs_own_geometry_evidence(dataset):
    dp.inventory(dataset)
    args = publish_args(dataset)
    rows = read_table(dataset.fingerprint)
    event = c_event(rows[246], records=0)
    event["result"]["source_bbox_lat_lon"][1] = event["result"]["source_bbox_lat_lon"][0]
    args.spool_json, args.spool_run = fake_probe(dataset, "spool", [event])
    args.pbf_json, args.pbf_run = fake_probe(dataset, "pbf")
    result = dp.publish(args)
    assert result["type321_row246"]["cause_class"] == "representability ceiling"
    assert result["counts"]["conflict-open"] == 0


@pytest.mark.parametrize("corruption", ["pin", "native", "dump", "fingerprint", "script-hash", "window", "log-hash",
                                        "summary-count", "partial-scan", "wrapper-exit", "wrapper-peak", "wrapper-output", "vocab"])
def test_publish_rejects_bad_evidence_without_changing_outputs(dataset, corruption):
    dp.inventory(dataset)
    args = publish_args(dataset)
    dp.publish(args)
    before = (args.output.read_bytes(), args.summary.read_bytes())
    rows = read_table(dataset.fingerprint)
    args.spool_json, args.spool_run = fake_probe(dataset, "spool")
    args.pbf_json, args.pbf_run = fake_probe(dataset, "pbf", [c_event(rows[0], kind="way")])
    doc = json.loads(args.pbf_json.read_text())
    if corruption == "pin":
        rows[0]["G_successor_sha256"] = "bad"
        table(dataset.fingerprint, rows)
    elif corruption == "native":
        doc["rows"][0]["ix"] += 10000
    elif corruption == "dump":
        doc["rows"][0]["dump_row"] = 123456
    elif corruption == "fingerprint":
        doc["inputs_sha256"][dp.label(dataset.fingerprint)] = "0" * 64
    elif corruption == "script-hash":
        doc["inputs_sha256"][dp.label(SCRIPT)] = "0" * 64
    elif corruption == "window":
        doc["windows"][0]["bbox_lat_lon"][0] += .001
    elif corruption == "log-hash":
        doc["proof_log_sha256"] = "0" * 64
    elif corruption == "summary-count":
        doc["rows"][0]["emitters_by_code"]["288"] += 1
    elif corruption == "partial-scan":
        doc["scan_complete"] = False
    elif corruption.startswith("wrapper"):
        log = json.loads(args.pbf_run.read_text())
        if corruption == "wrapper-exit":
            log["exit"] = 2
        elif corruption == "wrapper-peak":
            log["memory_peak"] = None
        else:
            log["argv"][-1] = str(args.pbf_json.with_name("wrong.json"))
        dp.write_json(args.pbf_run, log)
    else:
        path = dp.resolve(doc["proof_log"])
        event = json.loads(path.read_text())
        event["source"]["tags"] = {"natural": "sea"}
        path.write_text(dp.packed(event) + "\n")
        doc["proof_log_sha256"] = dp.digest(path)
    dp.write_json(args.pbf_json, doc)
    with pytest.raises(ValueError):
        dp.publish(args)
    assert before == (args.output.read_bytes(), args.summary.read_bytes())


def test_publish_revalidates_light_dependencies_without_opening_heavy(dataset, monkeypatch):
    dp.inventory(dataset)
    args = publish_args(dataset)
    args.spool_json, args.spool_run = fake_probe(dataset, "spool")
    args.pbf_json, args.pbf_run = fake_probe(dataset, "pbf")
    digest = dp.digest
    def safe_digest(path):
        assert Path(path).suffix not in (".pbf", ".data", ".idx", ".KWI")
        return digest(path)
    monkeypatch.setattr(dp, "digest", safe_digest)
    assert dp.publish(args)["counts"]["unfixable-proven"] == 341


def test_synthetic_pbf_stream_relation_tags_and_missing_members(dataset, production_probe, monkeypatch):
    import osmium
    rows = read_table(dataset.fingerprint)
    grid = dp.lattice()
    path = dataset.output.parent / "tiny.osm.pbf"
    nodes = square(dp.b4(grid, int(rows[246]["ix"]), 600))
    writer = osmium.SimpleWriter(str(path))
    for i, (lat, lon) in enumerate(nodes[:-1], 1):
        writer.add_node(osmium.osm.mutable.Node(id=i, location=(lon, lat)))
    for i, (lat, lon) in enumerate(square([50., 51., 10., 11.])[:-1], 20):
        writer.add_node(osmium.osm.mutable.Node(id=i, location=(lon, lat)))
    # Tags only on the relation; each member is a road so the way path cannot provide 321.
    writer.add_way(osmium.osm.mutable.Way(id=10, nodes=[1, 2, 3], tags={"highway": "service"}))
    writer.add_way(osmium.osm.mutable.Way(id=11, nodes=[3, 4, 1], tags={"highway": "service"}))
    writer.add_way(osmium.osm.mutable.Way(id=12, nodes=[20, 22, 21, 23, 20], tags={"highway": "service"}))
    writer.add_relation(osmium.osm.mutable.Relation(id=20, members=[("w", 10, "outer"), ("w", 11, "outer"), ("n", 1, "admin_centre")],
                                                   tags={"type": "multipolygon", "natural": "wood"}))
    writer.add_relation(osmium.osm.mutable.Relation(id=21, members=[("w", 999, "outer")],
                                                   tags={"type": "multipolygon", "natural": "wood"}))
    writer.add_relation(osmium.osm.mutable.Relation(id=22, members=[("w", 12, "outer")],
                                                   tags={"type": "multipolygon", "natural": "wood"}))
    writer.close()
    args = argparse.Namespace(**{**vars(dataset), "pbf": path, "cache": path.parent / "cache", "output": path.parent / "pbf.json"})
    monkeypatch.setattr(dp, "c_probe", lambda _: production_probe)
    # c_probe normally creates this compile directory; this test reuses a compiled synthetic probe.
    (args.output.parent / "pbf_c_probe").mkdir()
    result = dp.pbf(args)
    assert result["scan_counts"]["nodes"] == 8 and result["scan_counts"]["relations_assembled"] == 1
    assert result["scan_counts"]["relations_outside_windows"] == 1
    measured = dp.keyed(result["rows"])[dp.key(rows[246])]
    assert measured["supply"]["source"]["kind"] == "relation"
    assert measured["supply"]["source"]["id"] == 20 and measured["supply"]["production_C"]["records"] > 0
    # Unit 2-02: a node member (admin_centre/label) carries no area geometry and
    # is recorded as ignored; only the genuinely absent way 999 is a gap.
    assert result["gap_counts"] == {"missing relation member way": 1}
    assert result["ignored_member_counts"] == {"n:admin_centre": 1}
    assert result["memory"]["max_rss_kib"] > 0
    with pytest.raises(ValueError, match="cache already exists"):
        dp.disk_db(args.cache / "geometry.sqlite")


@pytest.mark.parametrize("corrupt_pin", [False, True])
def test_synthetic_spool_scan_includes_distant_source_cell_and_pins(dataset, production_probe, monkeypatch, corrupt_pin):
    import numpy as np
    from kiwiw.spool import content_to_columns, encode_columns
    grid = dp.lattice()
    rows = read_table(dataset.fingerprint)
    spool = dataset.output.parent / "synthetic_spool"
    spool.mkdir()
    entries, chunks, offset = [], [], 0

    def record(ix, iy, coords, code):
        nonlocal offset
        cols = content_to_columns({})
        for name in ("b_class", "b_type", "b_ncoords", "b_mult", "b_flags", "b_nstored", "b_label_len"):
            cols[name] = np.array([0], dtype=cols[name].dtype)
        for name, value in (("b_class", 2), ("b_type", code), ("b_ncoords", len(coords)), ("b_mult", 1), ("b_nstored", len(coords))):
            cols[name][0] = value
        cols["c_lat"] = np.array([p[0] for p in coords], dtype="<f8")
        cols["c_lon"] = np.array([p[1] for p in coords], dtype="<f8")
        raw = encode_columns(cols)
        entries.append((ix, iy, offset, len(raw)))
        chunks.append(raw)
        source = {"source_cell": [0, ix, iy], "background_ordinal": 0, "offset": offset, "length": len(raw),
                  "n_coords": len(coords), "source_cell_sha256": hashlib.sha256(raw).hexdigest()}
        offset += len(raw)
        return source

    # Stored far outside every requested cell/halo; its geometry supplies row 0.
    record(100, 100, square(dp.b4(grid, int(rows[0]["ix"]), 600)), 288)
    for row in rows:
        ix, iy = int(row["ix"]), int(row["iy"])
        a, b, c, d = dp.b4(grid, ix, iy)
        line = [(a, (c+d)/2), (b, (c+d)/2), (b, (c+d)/2), (a, (c+d)/2)]
        row["spool_demander_identity"] = dp.packed(record(ix, iy, line, int(row["code"])))
    if corrupt_pin:
        source = json.loads(rows[0]["spool_demander_identity"])
        source["source_cell_sha256"] = "0" * 64
        rows[0]["spool_demander_identity"] = dp.packed(source)
    table(dataset.fingerprint, rows)
    (spool / "level_0.data").write_bytes(b"".join(chunks))
    n = len(entries)
    index = b"KWSPIDX1" + struct.pack("<5Q", n, n, 0, n, 0)
    for col, fmt in enumerate(("i", "i", "Q", "Q")):
        index += struct.pack("<" + fmt * n, *(r[col] for r in entries))
    (spool / "level_0.idx").write_bytes(index)
    args = argparse.Namespace(**{**vars(dataset), "spool": spool, "output": spool.parent / "spool.json"})
    monkeypatch.setattr(dp, "c_probe", lambda _: production_probe)
    (args.output.parent / "spool_c_probe").mkdir()
    if corrupt_pin:
        with pytest.raises(ValueError, match="demander cell pin"):
            dp.spool(args)
        assert not args.output.exists()
    else:
        result = dp.spool(args)
        assert result["cells_scanned"] == 343 and result["demander_cells_verified"] == 342
        supply = dp.keyed(result["rows"])[dp.key(rows[0])]["supply"]
        assert supply["source"]["source_cell"] == [0, 100, 100] and supply["production_C"]["records"] > 0


def test_cli_paths_and_explicit_heavy_inputs():
    with pytest.raises(ValueError, match="scratch-30"):
        dp.cli(["spool", "--spool", "/never-open", "--output", "/tmp/out.json"])
    with pytest.raises(SystemExit):
        dp.cli(["pbf", "--output", "output/scratch-30/pbf.json", "--cache", "output/scratch-30/cache"])


def test_area_members_ignore_nodes_and_non_area_roles():
    members = [{"type": "w", "ref": 1, "role": "outer"}, {"type": "w", "ref": 2, "role": ""},
               {"type": "w", "ref": 3, "role": "inner"}, {"type": "n", "ref": 4, "role": "label"},
               {"type": "n", "ref": 5, "role": "admin_centre"}, {"type": "r", "ref": 6, "role": "subarea"},
               {"type": "r", "ref": 7, "role": "outer"}]
    area, ignored, nested = dp.area_members(members)
    assert [m["ref"] for m in area] == [1, 2, 3]
    assert [m["ref"] for m in ignored] == [4, 5, 6]
    assert [m["ref"] for m in nested] == [7]


def test_readonly_cache_refuses_missing_or_journaled(tmp_path):
    import sqlite3
    with pytest.raises(ValueError, match="missing retained cache"):
        dp.readonly_cache(tmp_path / "absent.sqlite")
    db_path = tmp_path / "geometry.sqlite"
    sqlite3.connect(db_path).execute("CREATE TABLE t(x)").connection.commit()
    (tmp_path / "geometry.sqlite-journal").write_bytes(b"")
    with pytest.raises(ValueError, match="pending journal"):
        dp.readonly_cache(db_path)


def test_cache_provenance_refuses_mismatched_pin(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "geometry.sqlite").write_bytes(b"x")
    pin_path = tmp_path / "pin.json"
    pin_path.write_text(json.dumps({"schema": "wrong"}))
    args = argparse.Namespace(cache_provenance=pin_path, cache=cache_dir,
                              source_json=pin_path, source_run=pin_path)
    with pytest.raises(ValueError, match="cache provenance schema mismatch"):
        dp.verify_cache_provenance(args, dp.Inputs(), {"heavy_inputs": [], "inputs_sha256": {}})


# --- Unit 2-03: date-matched relation snapshot (DESIGN Amendment 1) ---------

ADMIN = {"type": "boundary", "boundary": "administrative", "admin_level": "4"}


def _snap_fixture(tmp_path, *, cache_ways=(10, 11), snap_ways=(11,), snap_members=None, extra=None,
                  conflict=False, requested=(500,), cache_rel=True):
    from kiwiw.vocab import load as load_vocab
    grid = dp.lattice()
    row = {n: 0 for n in dp.NATIVE} | {"ix": 400, "iy": 600, "code": 288, "dump_row": 0}
    outer = square(dp.b4(grid, 400, 600), -.5, 1.5)
    geo = {10: ([1, 2, 3], outer[:3]), 11: ([3, 4, 1], [outer[2], outer[3], outer[0]])}
    members = [{"ref": 10, "role": "outer", "type": "w"}, {"ref": 11, "role": "outer", "type": "w"}]
    db = dp.disk_db(tmp_path / "geometry.sqlite")
    if cache_rel:
        db.execute("INSERT INTO relations VALUES(?,?,?)", (500, dp.packed(ADMIN), dp.packed(members)))
    for wid in cache_ways:
        ids, coords = geo[wid]
        db.execute("INSERT INTO ways VALUES(?,?,?)", (wid, dp.packed(ids), dp.packed(coords)))
        for n, (lat, lon) in zip(ids, coords):
            db.execute("INSERT OR IGNORE INTO nodes VALUES(?,?,?)", (n, lat, lon))
    sw = {}
    for wid in snap_ways:
        ids, coords = geo[wid]
        coords = [list(c) for c in coords]
        if conflict:
            coords[0] = [coords[0][0] + 1e-7, coords[0][1]]
        sw[str(wid)] = {"nodes": ids, "coords": coords}
    rels = {"500": {"tags": ADMIN, "members": snap_members if snap_members is not None else members,
                    "version": 1, "timestamp": "2026-08-01T00:00:00Z"}}
    rels.update(extra or {})
    doc = {"schema": dp.SNAPSHOT_SCHEMA, "requested_relation_ids": list(requested), "relations": rels, "ways": sw,
           "nodes": {}}
    for k, v in (extra or {}).items():
        for m in v["members"]:
            if m["type"] == "w" and str(m["ref"]) not in sw and m["ref"] in geo:
                sw[str(m["ref"])] = {"nodes": geo[m["ref"]][0], "coords": [list(c) for c in geo[m["ref"]][1]]}
    path = tmp_path / "snapshot.json"
    path.write_text(dp.packed(doc))
    return grid, row, db, path, load_vocab("bg_type")


def _assemble(tmp_path, grid, row, db, snap, probe, name="proofs.jsonl"):
    from kiwiw.selection import level_filter
    from kiwiw.vocab import load as load_vocab
    writer = dp.ProbeWriter(tmp_path / name, [row], grid, probe)
    counts = dp.Counter()
    dp.assemble_relations(db, writer, load_vocab("bg_type"), level_filter, "synthetic.pbf", counts, {}, snap)
    doc = writer.finish()
    events = [json.loads(l) for l in (tmp_path / name).read_text().splitlines()]
    return doc, events, counts


def test_snapshot_sha_and_schema_refused(tmp_path):
    _, _, _, path, _ = _snap_fixture(tmp_path)
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        dp.load_snapshot(path, "0" * 64, [500])
    with pytest.raises(ValueError, match="request-set"):
        dp.load_snapshot(path, dp.digest(path), [500, 501])
    assert dp.load_snapshot(path, dp.digest(path), [500])["relations"]["500"]["tags"] == ADMIN


def test_snapshot_supplies_missing_way_and_completes_ring(tmp_path, production_probe):
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(10,), snap_ways=(11,))
    legacy, legacy_events, _ = _assemble(tmp_path, grid, row, db, None, production_probe, "legacy.jsonl")
    assert legacy["gap_counts"] == {"missing relation member way": 1} and legacy["rows"][0]["supply"] is None
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    doc, events, counts = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert doc["gap_counts"] == {} and counts["snapshot_relations_assembled"] == 1
    supply = doc["rows"][0]["supply"]
    assert supply and supply["source"]["geometry_ways"] == {"cache": 1, "snapshot": 1}
    assert supply["source"]["tags_members"] == "pbf-cache"


def test_snapshot_member_mismatch_is_gap_and_unused(tmp_path, production_probe):
    other = [{"ref": 10, "role": "outer", "type": "w"}, {"ref": 12, "role": "outer", "type": "w"}]
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(10,), snap_ways=(11,), snap_members=other)
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    doc, events, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert doc["gap_counts"] == {"snapshot-member-mismatch": 1, "missing relation member way": 1}
    assert doc["rows"][0]["supply"] is None  # snapshot way 11 was not used


def test_snapshot_shared_node_conflict_refused(tmp_path, production_probe):
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(10,), snap_ways=(11,), conflict=True)
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    doc, _, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert doc["gap_counts"] == {"snapshot shared-node coordinate conflict": 1}
    assert doc["rows"][0]["supply"] is None


def test_snapshot_non_requested_relation_ignored(tmp_path, production_probe):
    extra = {"777": {"tags": ADMIN, "members": [{"ref": 10, "role": "outer", "type": "w"},
                                                {"ref": 11, "role": "outer", "type": "w"}]}}
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(), snap_ways=(10, 11), extra=extra, cache_rel=False,
                                           requested=())
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), []), [], db)
    assert snap.eligible == set()
    doc, events, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert events == [] and doc["rows"][0]["events"] == 0


def test_snapshot_not_retained_relation_tags_from_snapshot_are_noted(tmp_path, production_probe):
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(), snap_ways=(10, 11), cache_rel=False)
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    doc, events, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert doc["note_counts"] == {"snapshot-tags-members": 1}
    assert doc["rows"][0]["supply"]["source"]["tags_members"] == "snapshot"


@pytest.mark.parametrize("complete", [True, False])
def test_snapshot_nested_parent_bounded_only_when_all_descendants_present(tmp_path, production_probe, complete):
    far = [[10., 10.], [10., 11.], [11., 11.], [10., 10.]]
    child = {"tags": {"type": "multipolygon"}, "members": [{"ref": 20, "role": "outer", "type": "w"}]}
    parent_members = [{"ref": 900, "role": "outer", "type": "r"}]
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(), snap_ways=(), snap_members=parent_members,
                                           extra={"900": child}, cache_rel=False)
    doc_json = json.loads(path.read_text())
    if complete:
        doc_json["ways"]["20"] = {"nodes": [1, 2, 3, 1], "coords": far}
    path.write_text(dp.packed(doc_json))
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    assert snap.eligible == {500, 900}
    doc, events, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    if complete:
        assert doc["gap_counts"] == {} and doc["note_counts"]["nested-outside-windows"] == 1
    else:
        assert doc["gap_counts"]["nested area relation member"] == 1
        gap = next(e for e in events if e.get("gap") == "nested area relation member")
        assert gap["affected_dump_rows"] == [0]  # unknown bound blocks every row


def test_snapshot_no_area_geometry_is_note_not_gap(tmp_path, production_probe):
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(), snap_ways=(),
                                           snap_members=[{"ref": 1, "role": "", "type": "n"}], cache_rel=False)
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    doc, _, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert doc["gap_counts"] == {} and doc["note_counts"]["no-area-geometry"] == 1


def test_snapshot_vertex_limit_uses_boundary_clip_without_blanket_gap(tmp_path, production_probe):
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(), snap_ways=(), cache_rel=False)
    a, b, c, d = dp.b4(grid, 400, 600)
    n = dp.MAX_C_VERTICES + 10   # a dense ring that wholly contains the target cell
    lat0, lat1, lon0, lon1 = a - (b - a), b + (b - a), c - (d - c), d + (d - c)
    ring = ([[lat0, lon0 + (lon1 - lon0) * i / n] for i in range(n)] + [[lat0, lon1], [lat1, lon1], [lat1, lon0]])
    ring.append(ring[0])
    doc_json = json.loads(path.read_text())
    doc_json["relations"]["500"]["members"] = [{"ref": 30, "role": "outer", "type": "w"}]
    doc_json["ways"] = {"30": {"nodes": list(range(1, len(ring))) + [1], "coords": ring}}
    path.write_text(dp.packed(doc_json))
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), [500]), [500], db)
    doc, events, _ = _assemble(tmp_path, grid, row, db, snap, production_probe)
    assert "native-C vertex limit" not in doc["gap_counts"]
    assert doc["rows"][0]["supply"]["source"]["boundary_clip_target"]["dump_row"] == 0


def test_snapshot_inert_without_eligible_relations_and_flag_guard(tmp_path, production_probe):
    grid, row, db, path, _ = _snap_fixture(tmp_path, cache_ways=(10,), snap_ways=(11,), requested=())
    legacy, _, _ = _assemble(tmp_path, grid, row, db, None, production_probe, "legacy.jsonl")
    snap = dp.Snapshot(dp.load_snapshot(path, dp.digest(path), []), [], db)
    inert, _, _ = _assemble(tmp_path, grid, row, db, snap, production_probe, "inert.jsonl")
    assert (tmp_path / "legacy.jsonl").read_bytes() == (tmp_path / "inert.jsonl").read_bytes()
    assert "note_counts" not in legacy and "note_counts" not in inert
    args = argparse.Namespace(relation_snapshot=None, relation_snapshot_sha256="a" * 64)
    with pytest.raises(ValueError):
        dp.pbf_cache(args)


def test_publish_rejects_unknown_note(dataset):
    with pytest.raises(ValueError, match="unknown proof note"):
        dp.ProbeWriter(dataset.output.parent / "n.jsonl", [], dp.lattice(), None).note("made-up", {}, {})
