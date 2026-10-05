"""Plan 34 synthetic inputs only. No ALLDATA.KWI, R disc or live spool reads."""
import copy
import importlib.util
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "l0_frame_witness", ROOT / "docs/plans/34-l0-empty-slot-frame-parity/frame_witness.py")
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


@pytest.fixture(scope="module", autouse=True)
def isolated_routing_product(tmp_path_factory):
    # All synthetic C build products belong under the requested --basetemp.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(w, "ROUTING_SO", tmp_path_factory.mktemp("e1_routing") / "routing.so")
        w.routing_lib.cache_clear()
        yield
        w.routing_lib.cache_clear()


def bounds():
    w.reader().libs()
    from kiwiw.model import BoundingBox
    return BoundingBox(lat_lo=-39, lat_hi=-38, lon_lo=90, lon_hi=91, coord_range=4096)


def name_section():
    raw = bytearray(24)
    struct.pack_into(">HHH", raw, 0, 3, 3, 1)
    struct.pack_into(">HHH", raw, 6, 9, 6 << 8, 288)
    struct.pack_into(">H", raw, 20, 1)
    raw[22:24] = b"X\0"
    return bytes(raw)


def background_section():
    raw = bytearray(24)
    struct.pack_into(">HHH", raw, 0, 3, 3, 9)
    struct.pack_into(">HHH", raw, 6, 1, 0, 1)
    struct.pack_into(">H", raw, 12, 6)
    return bytes(raw)


def road_section():
    raw = bytearray(30)
    struct.pack_into(">H", raw, 0, 6)
    raw[4] = 1
    struct.pack_into(">HH", raw, 8, 6, 1)
    struct.pack_into(">I", raw, 14, 8 << 16)
    return bytes(raw)


def frame(section=None, kind=1, length=320):
    # G L0's 20 MFDEs. Empty BG's two-byte directory is header only.
    raw = bytearray(length)
    struct.pack_into(">H", raw, 0, min(length, 158 + len(section or b"")) // 2)
    for i in range(20):
        struct.pack_into(">IH", raw, 36 + i * 6, 0xFFFFFFFF, 0)
    if section is not None:
        struct.pack_into(">IH", raw, 36 + kind * 6, 78, len(section) // 2)
        raw[156:156 + len(section)] = section
    return bytes(raw)


def synthetic_index(path, state="g", historical=False):
    w.reader().libs()
    from kiwiw.bitutils import geo_secs_bytes
    from kiwiw.grid import ReferenceGrid
    grid = ReferenceGrid.load()
    lmr = grid._level_dict(0)
    pmoff, blockoff, frameoff = 4096, 8192, 24576
    nblocks = (1 + lmr["n_blocks_lng"]) * (1 + lmr["n_blocks_lat"])
    pmlen = (80 + nblocks * 6 + 31) // 32 * 32
    cells = [*w.TARGETS, (1, 564)]
    data = bytearray(frameoff + len(cells) * 320)
    struct.pack_into(">HH", data, 472, 32, 2048)
    struct.pack_into(">IH", data, 2048, 2 << 8, pmlen // 32)
    struct.pack_into(">HHHHH", data, pmoff + 20, 20, 5, 3, 1, 1)
    for at, key in ((8, "lat_hi"), (11, "lat_lo"), (14, "lon_lo"), (17, "lon_hi")):
        data[pmoff + at:pmoff + at + 3] = geo_secs_bytes(grid.coverage[key])
    struct.pack_into(">H", data, pmoff + 32, (3 << 12) | (9 << 8))
    for at, key in ((24, "n_blocksets_lat"), (25, "n_blocksets_lng"),
                    (26, "n_blocks_lat"), (27, "n_blocks_lng")):
        data[pmoff + 30 + at] = lmr[key]
    for i in range(4):
        data[pmoff + 58 + i * 2] = lmr["n_parcels_lat"][i]
        data[pmoff + 59 + i * 2] = lmr["n_parcels_lng"][i]
    struct.pack_into(">HII", data, pmoff + 70, 32, 40, nblocks * 3)
    for i in range(nblocks):
        struct.pack_into(">IH", data, pmoff + 80 + i * 6, 0xFFFFFFFF, 0)
    struct.pack_into(">IH", data, pmoff + 80, 4 << 8, 385)
    for i in range(2048):
        struct.pack_into(">IH", data, blockoff + 4 + i * 6, 0xFFFFFFFF, 0)
    if state == "absent":
        struct.pack_into(">II", data, pmoff + 72, 0xFFFFFFFF, 0)
    elif state == "zero_size":
        struct.pack_into(">IH", data, pmoff + 80, 4 << 8, 0)
    else:
        for i, (x, y) in enumerate(cells):
            off = frameoff + i * 320
            sector = (off // 2048) << 8 | (off % 2048) // 32
            slot = (y % 64) * 32 + x
            struct.pack_into(">IH", data, blockoff + 4 + slot * 6, sector, 10)
            payload = name_section() if historical and i == 0 else b"\0\1"
            kind = 2 if historical and i == 0 else 1
            data[off:off + 320] = frame(payload, kind)
    path.write_bytes(data)
    return path


@pytest.mark.parametrize("raw,expected", [
    (frame(length=156), "empty_shell"),
    (frame(b"\0\1", length=158), "empty_shell"),
    (frame(b"\0\1"), "padded_shell"),
    (frame(name_section(), 2), "content"),
    (frame(background_section(), 1), "content"),
    (frame(road_section(), 0), "content"),
])
def test_payload_classes_and_exact_byte_partition(raw, expected):
    result = w.frame_payload(raw, 100, bounds(), 3, 9, True)
    assert result["payload_class"] == expected
    cursor = 100
    parts = []
    for span in result["byte_spans"]:
        p = span["bytes"]
        assert p["offset"] == cursor
        chunk = w.proof_bytes(p)
        if span["kind"] == "zero_padding":
            assert not any(chunk)
        parts.append(chunk)
        cursor += len(chunk)
    assert b"".join(parts) == raw
    assert sum(result[k] for k in ("name_count", "background_count", "road_count")) == (1 if expected == "content" else 0)


def test_unreferenced_nonzero_tail_is_content():
    raw = bytearray(frame(b"\0\1"))
    raw[-1] = 7
    assert w.frame_payload(bytes(raw), 0, bounds(), 3, 9, True)["payload_class"] == "content"


@pytest.mark.parametrize("mutation", ["short", "non_sentinel_zero", "overlap", "bad_extent", "bad_name", "bad_bg", "bad_road"])
def test_malformed_payload_is_unresolved(mutation):
    raw = bytearray(frame(name_section(), 2))
    if mutation == "short":
        raw = raw[:50]
    elif mutation == "non_sentinel_zero":
        struct.pack_into(">IH", raw, 48, 78, 0)
    elif mutation == "overlap":
        struct.pack_into(">IH", raw, 42, 78, 12)
    elif mutation == "bad_extent":
        struct.pack_into(">H", raw, 52, 500)
    elif mutation == "bad_name":
        struct.pack_into(">H", raw, 162, 0)
    elif mutation == "bad_bg":
        raw = bytearray(frame(background_section(), 1))
        struct.pack_into(">H", raw, 168, 0)
    else:
        raw = bytearray(frame(road_section(), 0))
        struct.pack_into(">I", raw, 170, 100 << 16)
    with pytest.raises((ValueError, struct.error)):
        w.frame_payload(bytes(raw), 0, bounds(), 3, 9, True)


def test_failed_lookup_never_becomes_absence(tmp_path):
    path = synthetic_index(tmp_path / "synthetic.index", "zero_size")
    with path.open("rb") as fh:
        row = next(w.disc_rows(fh, [(0, 541)], True))
    assert row["status"] == "lookup_failed"
    assert w.reader().validate_cell_evidence(row)


def test_pin_verification_precedes_index_reads(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.index"
    path.write_bytes(b"synthetic bytes")
    monkeypatch.setattr(w, "disc_rows", lambda *a: pytest.fail("index read before pin check"))
    with path.open("rb") as fh, pytest.raises(ValueError, match="full pin mismatch"):
        w.disc_document(fh, "g_successor", path)


def test_probe_denies_unguarded_inputs_before_open(monkeypatch):
    def reject():
        raise ValueError("guard denied")
    monkeypatch.setattr(w, "require_heavy_guard", reject)
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("unguarded input opened"))
    assert w.main(["probe", "--disc", "g_successor"]) == 2
    assert w.main(["probe", "--spool", "output/extract_timing/spool"]) == 2


def test_guard_requires_wrapper_ancestry_and_a_held_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(w, "ROOT", tmp_path)
    monkeypatch.setattr(w.os, "getppid", lambda: 10)
    lock = tmp_path / "output/.heavy.lock"
    lock.parent.mkdir()
    lock.write_bytes(b"")
    argv = {10: ["python", str(tmp_path / "parser/tools/run_heavy_python.py"), "--inner"],
            20: ["flock", str(lock)]}
    monkeypatch.setattr(Path, "read_bytes", lambda p: b"\0".join(v.encode() for v in argv[int(p.parent.name)]))
    monkeypatch.setattr(Path, "read_text", lambda p: "10 (python) S 20" if p.parent.name == "10" else "20 (flock) S 1")
    def held(*args):
        raise BlockingIOError
    monkeypatch.setattr(w.fcntl, "flock", held)
    w.require_heavy_guard()
    monkeypatch.setattr(w.fcntl, "flock", lambda *args: None)
    with pytest.raises(ValueError, match="not held"):
        w.require_heavy_guard()
    argv[10].remove("--inner")
    with pytest.raises(ValueError, match="requires"):
        w.require_heavy_guard()


def test_pread_is_bounded_and_exact(tmp_path):
    path = tmp_path / "synthetic.bytes"
    path.write_bytes(b"0123")
    with path.open("rb") as fh:
        assert w.pread(fh, 2, 1) == b"12"
        for length, offset in ((w.MAX_READ + 1, 0), (1, -1), (5, 0)):
            with pytest.raises(ValueError):
                w.pread(fh, length, offset)


@pytest.fixture(scope="module")
def documents(tmp_path_factory):
    path = tmp_path_factory.mktemp("frame_documents")
    docs, pins = {}, {}
    for label, state, historical in (("g_successor", "g", False), ("g_historical", "g", True), ("r", "absent", False)):
        fixture = synthetic_index(path / f"{label}.index", state, historical)
        with fixture.open("rb") as fh:
            pins[label] = w.full_hash(fh)
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(w, "PINS", pins)
                docs[label] = w.disc_document(fh, label, fixture)
    return path, docs, pins


def empty_spool(tmp_path, targets):
    directory = tmp_path / "synthetic_spool"
    directory.mkdir()
    cells = sorted(targets, key=lambda c: (c[1], c[0]))
    n = len(cells)
    idx = b"KWSPIDX1" + struct.pack("<5Q", n, n, 0, 0, 0)
    idx += struct.pack(f"<{n}i", *(c[0] for c in cells))
    idx += struct.pack(f"<{n}i", *(c[1] for c in cells))
    idx += struct.pack(f"<{n}Q", *(i * 72 for i in range(n)))
    idx += struct.pack(f"<{n}Q", *([72] * n))
    (directory / "level_0.idx").write_bytes(idx)
    (directory / "level_0.data").write_bytes(b"\0" * (n * 72))
    return w.spool_document(directory, targets)


def test_full_census_sentinel_replay_and_extra_cells(documents, tmp_path, monkeypatch):
    _, docs, pins = documents
    monkeypatch.setattr(w, "PINS", pins)
    rows = {label: w.validate_disc(doc, label) for label, doc in docs.items()}
    assert docs["r"]["census"]["status_counts"] == {"empty_slot": 2048}
    for cell in w.TARGETS:
        assert rows["r"][cell]["index_evidence"]["blockset"]["hex"] == "0020ffffffff00000000"
        assert rows["g_successor"][cell]["frames"][0]["payload_class"] == "padded_shell"
    assert rows["g_historical"][(0, 541)]["frames"][0]["name_count"] == 1
    assert docs["g_successor"]["census"]["frame_count"] == 4
    assert len(docs["g_successor"]["byte_pool"]) < 100
    targets = set(w.TARGETS) | {(1, 564)}
    spool = empty_spool(tmp_path, targets)
    out = tmp_path / "witnesses"
    out.mkdir()
    for label, doc in docs.items():
        w.write(out / f"{label}.json", doc)
    w.write(out / "spool.json", spool)
    monkeypatch.setattr(w, "OUT", out)
    assert w.publish(SimpleNamespace(out=out / "summary.json", note=tmp_path / "note.md")) == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["extra_cells"] == {"g_successor": [[1, 564]], "g_historical": [[1, 564]]}
    assert len(summary["cells"]) == 4
    assert len(summary["residuals"]) == 2
    assert all(c["spool_sources"] for c in summary["cells"])


@pytest.mark.parametrize("mutation", ["missing_cell", "duplicate_cell", "forged_absence", "bad_hash", "bad_census"])
def test_publish_validation_rejects_unproven_census(documents, monkeypatch, mutation):
    _, docs, pins = documents
    monkeypatch.setattr(w, "PINS", pins)
    doc = copy.deepcopy(docs["r"])
    if mutation == "missing_cell":
        doc["cells"].pop()
    elif mutation == "duplicate_cell":
        doc["cells"].append(doc["cells"][0])
    elif mutation == "forged_absence":
        doc["cells"][0]["reason"] = "lookup failed means absent"
    elif mutation == "bad_hash":
        next(iter(doc["byte_pool"].values()))["sha256"] = "0" * 64
    else:
        doc["census"]["frame_count"] = 1
    with pytest.raises(ValueError):
        w.validate_disc(doc, "r")


@pytest.mark.parametrize("mutation", ["classification", "name_count", "frame_sha", "subframe_hash"])
def test_frame_publication_requires_recomputed_payload(documents, monkeypatch, mutation):
    _, docs, pins = documents
    monkeypatch.setattr(w, "PINS", pins)
    doc = copy.deepcopy(docs["g_successor"])
    frame_row = next(r for r in doc["cells"] if r["frames"])["frames"][0]
    if mutation == "classification":
        frame_row["payload_class"] = "content"
    elif mutation == "name_count":
        frame_row["name_count"] = 1
    elif mutation == "frame_sha":
        frame_row["sha256"] = "0" * 64
    else:
        ref = frame_row["sections"][0]["bytes"]["byte_ref"]
        doc["byte_pool"][ref]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        w.validate_disc(doc, "g_successor")


def test_spool_byte_offsets_and_layout_are_replayed(tmp_path):
    targets = set(w.TARGETS)
    doc = empty_spool(tmp_path, targets)
    sources = w.validate_spool(doc, targets)
    assert [s["cell_offset"] for s in sources] == [0, 72, 144]
    assert [s["source_row"] for s in sources] == [0, 1, 2]
    assert all(s["level"] == 0 and s["counts"]["n_names"] == 0 for s in sources)
    bad = copy.deepcopy(doc)
    bad["sources"][0]["source_row"] = 1
    with pytest.raises(ValueError):
        w.validate_spool(bad, targets)
    bad = copy.deepcopy(doc)
    bad["sources"][0]["counts"]["n_roads"] = 1
    with pytest.raises(ValueError):
        w.validate_spool(bad, targets)


def test_bounded_e1_replays_a_distant_source_geometry(tmp_path):
    w.reader().libs()
    from kiwiw import descriptor, mesh, spool
    from kiwiw.model import BackgroundShape
    grid = mesh.CellGrid.from_reference(0)
    cell = (0, 562)
    bbox = mesh.parcel_bounds(*cell, grid)
    shape = BackgroundShape(shape_class=1, type_code=1, type_label="synthetic", n_coords=1,
                            mult_const=1, underground=False, pen_up=False,
                            coords=[(bbox.lat_lo + grid.cell_lat * .2, bbox.lon_lo + grid.cell_lon * .2),
                                    (bbox.lat_lo + grid.cell_lat * .8, bbox.lon_lo + grid.cell_lon * .8)])
    raw = spool.encode_columns(spool.content_to_columns({"roads": [], "backgrounds": [shape], "names": []}))
    desc = descriptor.build(0, [0], [562], window=(0, 31, 512, 575))
    routed = w.route_record(desc, raw, (9, 900))
    assert routed == [{"target": [0, 562], "shape": 0, "kind": "edge"}]
    assert w.route_record(desc, raw, cell) == []  # Own records are not borrowed.


def test_streamed_spool_retains_names_and_nonlocal_background_sources(tmp_path):
    w.reader().libs()
    from kiwiw import mesh, spool
    import numpy as np
    directory = tmp_path / "synthetic_spool_sources"
    directory.mkdir()
    cols = {k: np.zeros(1 if key == "n_names" else 0, dtype=dt) for k, dt, key in spool._COLUMNS}
    cols["s_type"][0], cols["s_code"][0], cols["s_present"][0] = 6, 288, 3
    cols["s_lat"][0], cols["s_lon"][0] = -38.72, 77.5
    cols["s_text_len"][0] = 1
    cols["blob_name_text"] = np.frombuffer(b"X", "u1")
    own = spool.encode_columns(cols)
    grid = mesh.CellGrid.from_reference(0)
    bbox = mesh.parcel_bounds(0, 562, grid)
    bgcols = {k: np.zeros(1 if key == "n_bgs" else 2 if key == "n_coords" else 0, dtype=dt)
              for k, dt, key in spool._COLUMNS}
    bgcols["b_class"][0], bgcols["b_type"][0], bgcols["b_nstored"][0] = 1, 1, 2
    bgcols["b_ncoords"][0], bgcols["b_mult"][0] = 1, 1
    bgcols["c_lat"][:] = [bbox.lat_lo + grid.cell_lat * .2, bbox.lat_lo + grid.cell_lat * .8]
    bgcols["c_lon"][:] = [bbox.lon_lo + grid.cell_lon * .2, bbox.lon_lo + grid.cell_lon * .8]
    borrowed = spool.encode_columns(bgcols)
    idx = b"KWSPIDX1" + struct.pack("<5Q", 2, 2, 0, 1, 1)
    idx += struct.pack("<2i2i2Q2Q", 0, 9, 541, 900, 0, len(own), len(own), len(borrowed))
    (directory / "level_0.idx").write_bytes(idx)
    (directory / "level_0.data").write_bytes(own + borrowed)
    doc = w.spool_document(directory, set(w.TARGETS))
    sources = w.validate_spool(doc, set(w.TARGETS))
    assert len(sources) == 2
    assert sources[0]["names_before_guard"][0]["string_hex"] == "58"
    assert sources[0]["names_before_guard"][0]["lon"] == 77.5
    assert sources[1]["cell"] == [9, 900]
    assert sources[1]["cell_offset"] == len(own)
    assert sources[1]["routed_backgrounds"] == [{"target": [0, 562], "shape": 0, "kind": "edge"}]
    bad = copy.deepcopy(doc)
    bad["sources"][1]["routed_backgrounds"][0]["kind"] = "interior_cover"
    with pytest.raises(ValueError, match="E1 byte replay"):
        w.validate_spool(bad, set(w.TARGETS))
