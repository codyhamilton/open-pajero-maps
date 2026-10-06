#!/usr/bin/env python3
"""Plan 30 disposition evidence. Only spool/pbf subcommands open heavy inputs.

inventory reads Phase 1 TSV/JSON; publish joins evidence, never infers a
negative from a missing probe. Execute must wrap spool/pbf in run_heavy_python.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import resource
import sqlite3
import struct
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
PLAN = Path(__file__).resolve().parent
TRIAGE = ROOT / "docs/plans/04-c-core-orchestration/triage"
MEMBERS = TRIAGE / "2-01_g-omits-cell-local-dvd-type_members.tsv"
NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")
PINS = {
    "historical": "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72",
    "successor": "2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae",
}
MAX_CELL_BYTES = 64 << 20
MAX_VERTICES = 20000
MAX_C_VERTICES = 2048
MAX_MEMBERS = 2000
MAX_DENSIFIED = 200000
MAX_TOPOLOGY_EDGES = 2048
# Replay may hold one larger relation; native C remains capped at 2048 vertices.
MAX_RELATION_VERTICES = 250000
MAX_RELATION_MEMBERS = 12000
MAX_TOPOLOGY_CHECKS = 5000000
MAX_JSON_BYTES = 64 << 20
LEGACY_SCRIPT_SHA256 = "e54ea773c826874abad8c7d8a81ea940296a177d4edf9cc7b937ee812cdcf3bb"
AREA_ROLES = ("", "outer", "inner")
# Unit 2-03 (DESIGN Amendment 1): date-matched relation snapshot, opt-in only.
SNAPSHOT_SCHEMA = "plan30-relation-snapshot-v1"
SNAPSHOT_PIN_SCHEMA = "plan30-relation-snapshot-pin-v1"
REQUESTS = PLAN / "relation_requests.json"
SNAPSHOT_PIN = PLAN / "phase2_snapshot_pin.json"
NOTE_KINDS = ("no-area-geometry", "boundary-clip-empty", "nested-outside-windows", "snapshot-tags-members")
MAX_NESTED_DEPTH = 4
HALO = 1
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def label(path):
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def key(row):
    return tuple(int(row[n]) for n in NATIVE)


def native(row):
    return {n: int(row[n]) for n in NATIVE} | {"dump_row": int(row["dump_row"])}


def keyed(rows):
    result = {}
    dumps = set()
    for row in rows:
        k, d = key(row), int(row["dump_row"])
        require(k not in result and d not in dumps, "duplicate key/dump row")
        result[k] = row
        dumps.add(d)
    return result


class Inputs:
    def __init__(self):
        self.hashes = {label(__file__): digest(__file__)}

    def read(self, path, kind="json"):
        path = resolve(path)
        require(path.suffix == (".tsv" if kind == "tsv" else ".json"), "light inputs must be TSV/JSON")
        require(path.stat().st_size <= 8 << 20, f"oversized light input: {path}")
        data = path.read_bytes()
        self.hashes[label(path)] = hashlib.sha256(data).hexdigest()
        if kind == "tsv":
            return list(csv.DictReader(io.StringIO(data.decode()), delimiter="\t"))
        return json.loads(data)

    def add_file(self, path):
        self.hashes[label(path)] = digest(path)


def memory():
    result = {"max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    try:
        cg = next(l[3:] for l in Path("/proc/self/cgroup").read_text().splitlines() if l.startswith("0::"))
        result["cgroup_memory_peak_bytes"] = int((Path("/sys/fs/cgroup") / cg.lstrip("/") / "memory.peak").read_text())
    except (OSError, StopIteration, ValueError):
        result["cgroup_memory_peak_bytes"] = None
    return result


def lattice():
    from kiwiw.mesh import CellGrid
    return CellGrid.from_reference(0)


def b4(grid, ix, iy):
    a, c = grid.disc_lat_lo + iy * grid.cell_lat, grid.disc_lon_lo + ix * grid.cell_lon
    return [a, a + grid.cell_lat, c, c + grid.cell_lon]


def window(row, grid):
    a, b, c, d = b4(grid, int(row["ix"]), int(row["iy"]))
    return [a - HALO * grid.cell_lat, b + HALO * grid.cell_lat,
            c - HALO * grid.cell_lon, d + HALO * grid.cell_lon]


def bbox(coords):
    require(coords and all(len(p) == 2 and all(math.isfinite(v) for v in p) for p in coords),
            "invalid/nonfinite geometry")
    return [min(p[0] for p in coords), max(p[0] for p in coords),
            min(p[1] for p in coords), max(p[1] for p in coords)]


def intersects(a, b):
    # All plan-30 cells are in the Australian, non-wrapping longitude window.
    return a[0] <= b[1] + 1e-9 and a[1] >= b[0] - 1e-9 and a[2] <= b[3] + 1e-9 and a[3] >= b[2] - 1e-9


def lattice_evidence(row, summary, grid):
    if int(row["code"]) != 288:
        return {"template": False, "reason": "type-321 outlier; independent evidence required"}
    sig = row["R_shape_signature_id"]
    template = summary["templates"].get(sig)
    ix, iy = int(row["ix"]), int(row["iy"])
    expected = b4(grid, ix // 4 * 4, iy // 4 * 4)
    expected[1] = expected[0] + 4 * grid.cell_lat
    expected[3] = expected[2] + 4 * grid.cell_lon
    box = json.loads(row["R_bbox_lat_lon"])
    local = json.loads(row["R_local_signatures"])
    ok = (template is not None and row["R_template_span_ok"] == "true" and
          int(row["R_polygon_count"]) == int(row["R_cell_local_polygon_count"]) == 1 and
          json.loads(row["R_vertex_counts"]) == [13] and row["R_meet_branches"] == "c" and
          local == [template["normalised_vertices_lat_lon"]] and
          all(abs(a - b) <= 1e-9 for a, b in zip(box, expected)) and
          abs(box[1] - box[0] - 1 / 12) <= 1e-9 and abs(box[3] - box[2] - 1 / 8) <= 1e-9)
    return {"template": ok, "signature": sig, "grid_bbox_lat_lon": expected,
            "reason": "Phase-1 sequence plus aligned 4x4 L0 grid" if ok else "template/grid exception"}


def context(args):
    inputs = Inputs()
    rows = inputs.read(args.fingerprint, "tsv")
    summary = inputs.read(args.fingerprint_summary)
    members = inputs.read(args.members, "tsv")
    kr, km = keyed(rows), keyed(members)
    require(len(rows) == summary["rows"] == len(members) == 342, "expected 342 members")
    require(set(kr) == set(km), "fingerprint membership mismatch")
    require(Counter(int(r["code"]) for r in rows) == Counter({288: 341, 321: 1}), "census mismatch")
    require([int(r["dump_row"]) for r in rows if int(r["code"]) == 321] == [246], "outlier mismatch")
    require(summary["schema"] == "plan30-fingerprint-v1", "fingerprint schema mismatch")
    require(summary["inputs_sha256"][label(args.members)] == inputs.hashes[label(args.members)], "membership hash mismatch")
    for k, row in kr.items():
        require(int(row["dump_row"]) == int(km[k]["dump_row"]) and int(row["level"]) == 0, "native join mismatch")
        for pin in PINS:
            require(row[f"G_{pin}_sha256"] == PINS[pin] and int(row[f"G_{pin}_type_count"]) == 0 and
                    row[f"G_{pin}_status"].startswith("disc-verified:"), "Phase-1 disc verification missing/changed")
    for template in summary["templates"].values():
        require(hashlib.sha256(packed(template["normalised_vertices_lat_lon"]).encode()).hexdigest() == template["sha256"],
                "template sequence hash mismatch")
    inputs.add_file(ROOT / "parser/refdata/grid.json")
    grid = lattice()
    return sorted(rows, key=lambda r: int(r["dump_row"])), summary, grid, inputs


def base_document(kind, rows, inputs, grid):
    return {"schema": "plan30-discriminator-v1", "kind": kind, "inputs_sha256": inputs.hashes,
            "window_definition": "target L0 cell plus one-cell halo; source bbox intersection, including enclosing polygons",
            "limits": {"cell_bytes": MAX_CELL_BYTES, "vertices": MAX_VERTICES, "relation_members": MAX_MEMBERS,
                       "c_probe_vertices": MAX_C_VERTICES, "densified_vertices": MAX_DENSIFIED,
                       "topology_edges": MAX_TOPOLOGY_EDGES, "sqlite_cache_kib": 4096},
            "windows": [{**native(r), "bbox_lat_lon": window(r, grid)} for r in rows]}


def inventory(args):
    rows, summary, grid, inputs = context(args)
    doc = base_document("inventory", rows, inputs, grid)
    doc["rows"] = [{**native(r), "lattice": lattice_evidence(r, summary, grid),
                    "retained_demander": {"mechanism": r["mechanism"], "area2": int(r["clipped_ring_area2"]),
                                          "emits": r["encoder_emits"], "identity": json.loads(r["spool_demander_identity"]),
                                          "proof": r["R_proof_path"], "witness": r["spool_requirement_witness"]}}
                   for r in rows]
    doc["memory"] = memory()
    write_json(args.output, doc)
    return doc


_MIRROR = None


def mirror():
    global _MIRROR
    if _MIRROR is None:
        path = TRIAGE / "complete_repair_2-02.py"
        spec = importlib.util.spec_from_file_location("plan30_complete_repair", path)
        _MIRROR = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_MIRROR)
    return _MIRROR


def c_probe(scratch):
    probe = mirror().CProbe(scratch)
    box = [0., 1., 0., 1.]
    size, records = probe.run([.25, .25, .75, .75, .25], [.25, .75, .75, .25, .25], 1, 288, 0, box)
    require(size > 0 and records > 0, "production-C positive control failed")
    return probe


def evaluate(coords, code, mult, flags, row, grid, probe):
    """Original/clip and unit-mult repair; no R coordinates, no arbitrary densify."""
    require(3 <= len(coords) <= MAX_VERTICES, "geometry vertex bound exceeded")
    # The native EO arrangement can have quadratic intersection storage/work.
    # Bound its input separately from the streamed source-coordinate limit.
    require(len(coords) <= MAX_C_VERTICES, "native-C vertex limit")
    require(1 <= mult <= 4096 and 0 <= code <= 65535 and 0 <= flags <= 255, "invalid shape attributes")
    box = b4(grid, int(row["ix"]), int(row["iy"]))
    a, b, c, d = box
    poly = [((lon - c) / (d - c) * 4096, (lat - a) / (b - a) * 4096) for lat, lon in coords]
    clipped = mirror().clip_rect(poly, 0., 0., 4096., 4096.)
    require(len(clipped) <= MAX_VERTICES, "clipped vertex bound exceeded")
    require(len(clipped) <= MAX_C_VERTICES, "native-C clipped vertex limit")
    nc = sum(max(1, math.ceil(max(abs(q[0] - p[0]), abs(q[1] - p[1])) / 126))
             for p, q in zip(clipped, clipped[1:] + clipped[:1]))
    require(nc <= MAX_DENSIFIED, "densification bound exceeded")
    q, area2, emits = mirror().encoder_piece_densified(clipped, mult)
    clip_coords = [(a + y / 4096 * (b - a), c + x / 4096 * (d - c)) for x, y in clipped]
    variants = {}
    for name, ring, mc in (("original", coords, mult), ("clipped", clip_coords, mult), ("unit-mult", coords, 1)):
        if len(ring) < 3:
            size, records = 0, 0
        else:
            size, records = probe.run([p[0] for p in ring], [p[1] for p in ring], mc, code, flags, box)
        require(size >= 0 and records >= 0, f"production C error/overflow in {name}: {size}")
        require((size > 0) == (records > 0), "C size/record inconsistency")
        variants[name] = {"bytes": size, "records": records, "mult": mc}
    tile = b4(grid, int(row["ix"]) // 4 * 4, int(row["iy"]) // 4 * 4)
    tile[1], tile[3] = tile[0] + 4 * grid.cell_lat, tile[2] + 4 * grid.cell_lon
    shape_box = bbox(coords)
    on_grid_boundary = all(any(abs(p[axis] - boundary) <= 1e-9 and abs(q0[axis] - boundary) <= 1e-9
                               for axis, boundaries in ((0, tile[:2]), (1, tile[2:])) for boundary in boundaries)
                           for p, q0 in zip(coords, coords[1:] + coords[:1]))
    coincident = all(abs(v - w) <= 1e-9 for v, w in zip(shape_box, tile)) and on_grid_boundary
    return {"mirror": {"q": q, "area2": area2, "emits": bool(emits)}, "variants": variants,
            "grid_boundary_coincident": coincident,
            "source_bbox_lat_lon": shape_box, "coords_sha256": hashlib.sha256(packed(coords).encode()).hexdigest()}


def successor(source, variant):
    if source["kind"] == "spool":
        action = "retain the identified OSM-derived spool ring and route it to the target cell through E2 retile"
    elif source["kind"] == "way":
        action = "admit the identified OSM way with its existing background tags and retile into the target cell"
    else:
        action = "assemble the identified OSM relation from member node IDs, inherit relation tags, preserve even-odd holes, and retile"
    if source.get("boundary_clip_target"):
        action += "; clip the original boundary at the target cell before encoding"
    if variant == "clipped":
        action += "; clip the original source boundary at the target cell before encoding"
    if variant == "unit-mult":
        action += "; use wire-valid mult=1 on this source"
    return action + "; presence match only; validate successor G and re-oracle under a separate implement unit"


class Accumulator:
    """Bounded summary, with an exhaustive on-disk event log for the probes."""
    def __init__(self, rows):
        self.rows = {key(r): {**native(r), "candidates_by_code": {}, "emitters_by_code": {},
                             "grid_coincident_by_code": {}, "same_code_nondegenerate": 0, "supply": None, "events": 0} for r in rows}

    def accept(self, event):
        k = key(event)
        require(k in self.rows and int(event["dump_row"]) == self.rows[k]["dump_row"], "event key/dump mismatch")
        r, code = self.rows[k], int(event["source"]["code"])
        require(set(event["result"]["variants"]) == {"original", "clipped", "unit-mult"}, "missing repair variants")
        variants = event["result"]["variants"]
        for variant in variants.values():
            require(type(variant["bytes"]) is int and type(variant["records"]) is int and
                    variant["bytes"] >= 0 and variant["records"] >= 0 and
                    (variant["bytes"] > 0) == (variant["records"] > 0), "invalid C result")
        c = str(code)
        r["candidates_by_code"][c] = r["candidates_by_code"].get(c, 0) + 1
        if event["result"].get("grid_boundary_coincident", False):
            r["grid_coincident_by_code"][c] = r["grid_coincident_by_code"].get(c, 0) + 1
        emitting = [n for n in ("original", "clipped", "unit-mult") if variants[n]["records"] > 0]
        if emitting:
            r["emitters_by_code"][c] = r["emitters_by_code"].get(c, 0) + 1
        if code == int(r["code"]):
            a, b, c0, d = event["result"]["source_bbox_lat_lon"]
            if b > a and d > c0:
                r["same_code_nondegenerate"] += 1
            if emitting and r["supply"] is None:
                variant = emitting[0]
                r["supply"] = {"source": event["source"], "variant": variant, "production_C": variants[variant],
                               "coords_sha256": event["result"]["coords_sha256"],
                               "successor_implement_path": successor(event["source"], variant)}
        r["events"] += 1


class ProbeWriter:
    def __init__(self, path, rows, grid, probe):
        self.path, self.acc, self.grid, self.probe = path, Accumulator(rows), grid, probe
        self.rows = rows
        self.windows = [(r, window(r, grid)) for r in rows]
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = path.open("w")
        self.gaps = Counter()
        self.ignored = Counter()
        self.gap_samples = []
        self.notes = Counter()

    def note(self, kind, source, details):
        """Snapshot-mode proof record that is neither a C event nor a gap."""
        require(kind in NOTE_KINDS, "unknown proof note")
        self.notes[kind] += 1
        self.fh.write(packed({"note": kind, "source": source, "details": details}) + "\n")

    def gap(self, reason, source, box=None, details=None):
        # An unknown bbox can hide an enclosing polygon: it affects all negatives.
        affected = [int(r["dump_row"]) for r, w in self.windows if box is None or intersects(box, w)]
        if affected:
            self.gaps[reason] += 1
            if len(self.gap_samples) < 20:
                self.gap_samples.append({"reason": reason, "source": source, "affected_dump_rows": affected})
            self.fh.write(packed({"gap": reason, "source": source, "affected_dump_rows": affected,
                                  **({"details": details} if details else {})}) + "\n")

    def geometry(self, coords, source):
        if len(coords) < 3:
            return
        box = bbox(coords)
        hits = [r for r, w in self.windows if intersects(box, w)]
        if not hits:
            return
        if source["kind"] != "spool" and any(abs(a[1]-b[1]) > 180 for a,b in zip(coords, coords[1:] + coords[:1])):
            self.gap("ambiguous-antimeridian-source", source, box)
            return
        if len(coords) > MAX_VERTICES:
            self.gap("geometry-vertex-limit", source, box)
            return
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        for row in hits:
            try:
                result = evaluate(coords, source["code"], source["mult"], source["flags"], row, self.grid, self.probe)
            except ValueError as e:
                # Bound/encode errors are a discriminator gap, never absence.
                self.gap(str(e), source, b4(self.grid, int(row["ix"]), int(row["iy"])))
                continue
            event = {**native(row), "source": source, "result": result}
            self.acc.accept(event)
            self.fh.write(packed(event) + "\n")

    def finish(self):
        self.fh.close()
        result = {"rows": list(self.acc.rows.values()), "proof_log": label(self.path), "proof_log_sha256": digest(self.path),
                  "gap_counts": dict(self.gaps), "gap_samples": self.gap_samples, "ignored_member_counts": dict(self.ignored)}
        if self.notes:  # absent without a snapshot, so no-flag output is unchanged
            result["note_counts"] = dict(self.notes)
        return result


def stamp(path):
    s = Path(path).stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def pread(fd, size, offset):
    require(0 <= size <= MAX_CELL_BYTES and offset >= 0 and offset + size <= os.fstat(fd).st_size, "out-of-bounds spool read")
    data = os.pread(fd, size, offset)
    require(len(data) == size, "short spool read")
    return data


def index_entries(path):
    """48-byte header and 4-column pread batches; never load the index whole."""
    fd = os.open(path, os.O_RDONLY)
    try:
        header = pread(fd, 48, 0)
        require(header[:8] == b"KWSPIDX1", "bad spool index magic")
        n = struct.unpack_from("<Q", header, 8)[0]
        require(os.fstat(fd).st_size == 48 + 24 * n, "spool index length mismatch")
        previous = None
        for start in range(0, n, 4096):
            count = min(4096, n - start)
            arrays = [struct.unpack("<" + fmt * count, pread(fd, width * count, base + width * start))
                      for base, width, fmt in ((48, 4, "i"), (48 + 4*n, 4, "i"),
                                               (48 + 8*n, 8, "Q"), (48 + 16*n, 8, "Q"))]
            for ix, iy, offset, length in zip(*arrays):
                require(previous is None or (iy, ix) > previous, "unsorted/duplicate spool cells")
                previous = (iy, ix)
                yield ix, iy, offset, length
    finally:
        os.close(fd)


def checked_columns(raw):
    from kiwiw.spool import _HDR, _COUNT_KEYS, _COLUMNS, decode_columns
    import numpy as np
    require(len(raw) >= _HDR.size, "short spool cell")
    counts = dict(zip(_COUNT_KEYS, _HDR.unpack_from(raw)))
    size = _HDR.size
    for _, dt, k in _COLUMNS:
        n = counts[k] * np.dtype(dt).itemsize
        size += n + (-n % 8)
    require(size == len(raw), "malformed/trailing spool cell bytes")
    cols = decode_columns(raw)
    require(all(int(n) >= 0 for n in cols["b_nstored"]) and
            sum(int(n) for n in cols["b_nstored"]) == len(cols["c_lat"]), "background coordinate counts mismatch")
    require(np.isfinite(cols["c_lat"]).all() and np.isfinite(cols["c_lon"]).all(), "nonfinite spool geometry")
    return cols


def add_runtime_inputs(inputs):
    # Hash all loaded repo code and checked-in profiles used by these imports.
    for mod in list(sys.modules.values()):
        p = getattr(mod, "__file__", None)
        if p and Path(p).is_file() and Path(p).suffix in (".py", ".so") and (
                Path(p).resolve().is_relative_to(ROOT) or "site-packages" in str(p)):
            inputs.add_file(p)
    for p in (ROOT / "parser/refdata").rglob("*.json"):
        inputs.add_file(p)
    inputs.add_file(ROOT / "parser/kiwiw/_cenc.c")
    inputs.add_file(TRIAGE / "cell_local_2-01.py")
    inputs.add_file(TRIAGE / "complete_repair_2-02.py")


def spool(args):
    rows, _, grid, inputs = context(args)
    source_dir = resolve(args.spool)
    paths = [source_dir / "level_0.idx", source_dir / "level_0.data"]
    stamps = {p: stamp(p) for p in paths}
    for p in paths:
        inputs.add_file(p)  # streamed, full-file provenance
    probe = c_probe(Path(args.output).parent / "spool_c_probe")
    writer = ProbeWriter(Path(args.output).with_suffix(".proofs.jsonl"), rows, grid, probe)
    expected_cells = {}
    for row in rows:
        src = json.loads(row["spool_demander_identity"])
        cell = tuple(src["source_cell"][1:])
        expected_cells.setdefault(cell, []).append(src)
    witnessed = set()
    fd = os.open(paths[1], os.O_RDONLY)
    end, cells, backgrounds = 0, 0, 0
    try:
        for ix, iy, offset, length in index_entries(paths[0]):
            require(offset == end and 72 <= length <= MAX_CELL_BYTES, "spool data coverage/bound mismatch")
            raw = pread(fd, length, offset)
            end += length
            cells += 1
            cols = checked_columns(raw)
            sha = hashlib.sha256(raw).hexdigest()
            for src in expected_cells.get((ix, iy), []):
                require(src["source_cell_sha256"] == sha and src["offset"] == offset and src["length"] == length,
                        "Phase-1 demander cell pin mismatch")
                ordinal = src["background_ordinal"]
                require(0 <= ordinal < len(cols["b_class"]) and int(cols["b_nstored"][ordinal]) == src["n_coords"],
                        "Phase-1 demander ordinal/count mismatch")
                witnessed.add((ix, iy))
            start = 0
            for ordinal, nc in enumerate(cols["b_nstored"]):
                stop = start + int(nc)
                if int(cols["b_class"][ordinal]) == 2 and int(nc) >= 3:
                    backgrounds += 1
                    # No shape list across records/cells; conversion only after bbox filter.
                    lat, lon = cols["c_lat"][start:stop], cols["c_lon"][start:stop]
                    box = [float(lat.min()), float(lat.max()), float(lon.min()), float(lon.max())]
                    if any(intersects(box, w) for _, w in writer.windows):
                        source = {"kind": "spool", "source_cell": [0, ix, iy], "background_ordinal": ordinal,
                                  "offset": offset, "length": length, "source_cell_sha256": sha,
                                  "code": int(cols["b_type"][ordinal]), "mult": int(cols["b_mult"][ordinal]),
                                  "flags": int(cols["b_flags"][ordinal]), "input": label(paths[1])}
                        if int(nc) > MAX_VERTICES:
                            writer.gap("geometry-vertex-limit", source, box)
                        else:
                            writer.geometry(list(zip(lat.tolist(), lon.tolist())), source)
                start = stop
        require(end == os.fstat(fd).st_size, "unindexed spool data")
        require(witnessed == set(expected_cells), "missing Phase-1 demander cell")
    finally:
        os.close(fd)
        writer.fh.close()
    require(all(stamp(p) == s for p, s in stamps.items()), "spool changed during probe")
    add_runtime_inputs(inputs)
    for p in (Path(args.output).parent / "spool_c_probe").iterdir():
        inputs.add_file(p)
    doc = base_document("spool", rows, inputs, grid) | writer.finish()
    doc.update(scan_complete=True, scope="all indexed L0 class-2 spool rings; source bbox window, not centroid window",
               cells_scanned=cells, backgrounds_scanned=backgrounds, demander_cells_verified=len(witnessed), memory=memory(),
               compile_argv=probe.cmd, heavy_inputs=[label(p) for p in paths])
    write_json(args.output, doc)
    return doc


def disk_db(path):
    """Small fixed SQLite cache, disk temp tables; unique fresh scratch database."""
    require(not path.exists(), f"cache already exists: {path}; use a fresh --cache directory")
    db = sqlite3.connect(path)
    db.executescript("PRAGMA cache_size=-4096; PRAGMA temp_store=FILE; PRAGMA journal_mode=OFF;"
                     "CREATE TABLE nodes(id INTEGER PRIMARY KEY, lat REAL, lon REAL) WITHOUT ROWID;"
                     "CREATE TABLE relations(id INTEGER PRIMARY KEY, tags TEXT, members TEXT) WITHOUT ROWID;"
                     "CREATE TABLE needed(id INTEGER PRIMARY KEY) WITHOUT ROWID;"
                     "CREATE TABLE ways(id INTEGER PRIMARY KEY, nodes TEXT, coords TEXT) WITHOUT ROWID;")
    return db


def area_members(members):
    """Only area-role ways form rings. Nested area relations stay unresolved."""
    area, ignored, nested = [], [], []
    for member in members:
        if member["type"] == "w" and member["role"] in AREA_ROLES:
            area.append(member)
        elif member["type"] == "r" and member["role"] in AREA_ROLES:
            nested.append(member)
        else:
            ignored.append(member)
    return area, ignored, nested


def join_rings(members, ways, vertex_limit=MAX_VERTICES):
    """Join by OSM node IDs only. Reject branches, missing members and open rings."""
    members, _, nested = area_members(members)
    require(not nested, "nested area relation member")
    rings = []
    for role in ("outer", "inner"):
        remaining = []
        for member in members:
            require(member["type"] == "w" and member["role"] in ("", "outer", "inner"), "unsupported relation member/role")
            if (member["role"] or "outer") != role:
                continue
            require(member["ref"] in ways, "missing relation member way")
            ids, coords = ways[member["ref"]]
            require(len(ids) == len(coords) >= 2, "invalid relation member geometry")
            remaining.append((list(ids), list(coords)))
        while remaining:
            ids, coords = remaining.pop(0)
            while ids[-1] != ids[0]:
                matches = [(i, part) for i, part in enumerate(remaining) if ids[-1] in (part[0][0], part[0][-1])]
                require(len(matches) == 1, "open/branched relation ring")
                i, (more_ids, more_coords) = matches[0]
                remaining.pop(i)
                if more_ids[-1] == ids[-1]:
                    more_ids, more_coords = more_ids[::-1], more_coords[::-1]
                require(coords[-1] == more_coords[0], "inconsistent shared-node coordinates")
                ids.extend(more_ids[1:])
                coords.extend(more_coords[1:])
                require(len(ids) <= vertex_limit, "relation vertex limit")
            require(len(set(ids)) >= 3, "degenerate relation ring")
            rings.append((role, coords))
    require(any(role == "outer" for role, _ in rings), "relation has no outer ring")
    return rings


def stitch_rings(rings, vertex_limit=MAX_VERTICES):
    """Even-odd compound ring with doubled bridges between existing vertices.

    Bridges cancel as even-odd edges. Neither bridge changes polygon area;
    production C's EO arrangement is the authority (including hole clipping).
    """
    outer = next(coords for role, coords in rings if role == "outer")
    anchor, result = outer[0], list(outer)
    skipped = False
    for role, ring in rings:
        if not skipped and role == "outer" and ring is outer:
            skipped = True
            continue
        result.extend([ring[0], *ring[1:], anchor])
    require(len(result) <= vertex_limit, "compound relation vertex limit")
    return result


def validate_rings(rings, edge_limit=MAX_TOPOLOGY_EDGES):
    """OSM relation roles must describe a valid polygon, before EO stitching."""
    from fractions import Fraction

    def orient(a, b, c):
        l = (b[0]-a[0]) * (c[1]-a[1])
        r = (b[1]-a[1]) * (c[0]-a[0])
        if abs(l-r) > (abs(l)+abs(r)) * 8 * sys.float_info.epsilon:
            return 1 if l > r else -1
        # Exact fallback for collinear/near-collinear binary-float inputs.
        a, b, c = [tuple(Fraction(v) for v in p) for p in (a, b, c)]
        v = (b[0]-a[0]) * (c[1]-a[1]) - (b[1]-a[1]) * (c[0]-a[0])
        return (v > 0) - (v < 0)

    def on(a, b, p):
        return orient(a, b, p) == 0 and all(min(a[i], b[i]) <= p[i] <= max(a[i], b[i]) for i in (0, 1))

    def touch(a, b, c, d):
        o1, o2, o3, o4 = orient(a,b,c), orient(a,b,d), orient(c,d,a), orient(c,d,b)
        return (o1*o2 < 0 and o3*o4 < 0) or any((on(a,b,c), on(a,b,d), on(c,d,a), on(c,d,b)))

    def inside(p, ring):
        y, x = p
        yes = False
        for a, b in zip(ring, ring[1:]):
            if (a[0] > y) != (b[0] > y) and x < (b[1]-a[1]) * (y-a[0]) / (b[0]-a[0]) + a[1]:
                yes = not yes
        return yes

    require(sum(len(r)-1 for _, r in rings) <= edge_limit, "relation topology edge limit")
    segments = []
    for rid, (_, ring) in enumerate(rings):
        require(ring[0] == ring[-1] and len(set(tuple(p) for p in ring[:-1])) == len(ring)-1,
                "repeated relation ring vertex")
        for i, (a,b) in enumerate(zip(ring, ring[1:])):
            segments.append((min(a[0],b[0]), max(a[0],b[0]), min(a[1],b[1]), max(a[1],b[1]), rid, i, a, b))
    active, checks = [], 0
    for s in sorted(segments, key=lambda s: (s[0], s[4], s[5])):
        active = [p for p in active if p[1] >= s[0]]
        for p in active:
            checks += 1
            require(checks <= MAX_TOPOLOGY_CHECKS, "relation topology work limit")
            if p[3] < s[2] or s[3] < p[2]:
                continue
            adjacent = p[4] == s[4] and ((p[5]-s[5]) % (len(rings[s[4]][1])-1) in (1, len(rings[s[4]][1])-2))
            if adjacent:
                shared = set(tuple(q) for q in p[6:]) & set(tuple(q) for q in s[6:])
                require(len(shared) == 1, "overlapping adjacent relation edges")
                other_p = next(tuple(q) for q in p[6:] if tuple(q) not in shared)
                other_s = next(tuple(q) for q in s[6:] if tuple(q) not in shared)
                endpoint = next(iter(shared))
                require(not on(endpoint, other_p, other_s) and not on(endpoint, other_s, other_p), "overlapping adjacent relation edges")
            else:
                require(not touch(p[6],p[7],s[6],s[7]), "crossing/touching relation boundaries")
        active.append(s)
    outers = [r for role, r in rings if role == "outer"]
    for i, outer in enumerate(outers):
        require(not any(inside(outer[0], r) or inside(r[0], outer) for r in outers[i+1:]), "nested relation outer rings")
    holes = [r for role, r in rings if role == "inner"]
    for i, hole in enumerate(holes):
        require(sum(inside(hole[0], r) for r in outers) == 1, "relation hole outside outer ring")
        require(not any(inside(hole[0], r) or inside(r[0], hole) for r in holes[i+1:]), "nested relation inner rings")


def relation_rows(db):
    """Keyset pages keep queries and Python residency bounded."""
    last = -1
    while True:
        page = db.execute("SELECT id,length(tags),length(members) FROM relations WHERE id>? ORDER BY id LIMIT 64", (last,)).fetchall()
        if not page:
            return
        for rid, nt, nm in page:
            require(max(nt, nm) <= MAX_JSON_BYTES, "relation JSON byte limit")
            yield (rid, *db.execute("SELECT tags,members FROM relations WHERE id=?", (rid,)).fetchone())
        last = page[-1][0]


def assemble_relations(db, writer, vocab, level_filter, input_name, counts, full=None, snap=None):
    """Complete-area-member bounds only; missing parts always have unknown bounds."""
    seen = set()
    for rid, raw_tags, raw_members in relation_rows(db):
        seen.add(rid)
        if snap is not None and rid in snap.eligible:
            assemble_snapshot(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts, snap)
            continue
        replacement = full.get(rid) if full else None
        if replacement:
            raw_tags, raw_members, ways = replacement
        else:
            ways = None
        assemble_relation(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts, ways)
    for rid, (raw_tags, raw_members, ways) in (full or {}).items():
        if rid not in seen:
            assemble_relation(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts, ways)
    if snap is not None:
        for rid in sorted(snap.eligible - seen):
            assemble_snapshot(rid, None, None, db, writer, vocab, level_filter, input_name, counts, snap)
    return seen


def load_snapshot(path, expected_sha, requested):
    """Verify the pinned snapshot digest and schema before any use."""
    path = resolve(path)
    require(isinstance(expected_sha, str) and len(expected_sha) == 64, "relation snapshot SHA256 required")
    require(digest(path) == expected_sha, "relation snapshot SHA256 mismatch")
    snap = json.loads(path.read_bytes())
    require(isinstance(snap, dict) and snap.get("schema") == SNAPSHOT_SCHEMA, "relation snapshot schema mismatch")
    require(sorted(snap.get("requested_relation_ids", [])) == sorted(requested), "relation snapshot request-set mismatch")
    rels, ways = snap.get("relations"), snap.get("ways")
    require(isinstance(rels, dict) and isinstance(ways, dict), "relation snapshot schema mismatch")
    require(all(str(rid) in rels for rid in requested), "requested relation missing from snapshot")
    for r in rels.values():
        require(isinstance(r.get("tags"), dict) and isinstance(r.get("members"), list), "relation snapshot schema mismatch")
        require(all(isinstance(m, dict) and set(m) == {"type", "ref", "role"} and m["type"] in ("n", "w", "r")
                    for m in r["members"]), "relation snapshot member schema mismatch")
    for w in ways.values():
        require(isinstance(w.get("nodes"), list) and isinstance(w.get("coords"), list) and
                len(w["nodes"]) == len(w["coords"]) >= 2 and all(len(p) == 2 for p in w["coords"]),
                "relation snapshot way schema mismatch")
    return snap


class Snapshot:
    """Date-matched member geometry for the requested relations only.

    Eligible: the requested ids, plus area-role child relations of a requested
    parent (assembled as their own sources). Nothing else is ever added.
    """
    def __init__(self, doc, requested, db):
        self.rels, self.ways, self.db = doc["relations"], doc["ways"], db
        self.requested = set(int(r) for r in requested)
        self.eligible = set(self.requested)
        self.children = {}
        for rid in sorted(self.requested):
            _, _, nested = area_members(self.rels[str(rid)]["members"])
            for m in nested:
                if str(m["ref"]) in self.rels:
                    self.eligible.add(int(m["ref"]))
                    self.children.setdefault(int(m["ref"]), rid)

    def members(self, rid):
        rel = self.rels.get(str(rid))
        return None if rel is None else [{"ref": m["ref"], "role": m["role"], "type": m["type"]} for m in rel["members"]]

    def cache_way(self, wid):
        sizes = self.db.execute("SELECT length(nodes),length(coords) FROM ways WHERE id=?", (wid,)).fetchone()
        if not sizes:
            return None
        require(max(sizes) <= MAX_JSON_BYTES, "member JSON byte limit")
        return tuple(json.loads(v) for v in self.db.execute("SELECT nodes,coords FROM ways WHERE id=?", (wid,)).fetchone())

    def member_ways(self, area):
        """Cache geometry first (pinned PBF); the snapshot only for absent ways.

        A node shared with a cache way or present in the cache node table
        must carry identical coordinates, else the relation is refused.
        """
        ways, origin, known, supplied = {}, Counter(), {}, []
        for m in area:
            if m["ref"] in ways:
                continue
            item = self.cache_way(m["ref"])
            if item is not None:
                ids, coords = item
                require(len(ids) == len(coords) >= 2, "invalid relation member geometry")
                known.update((n, tuple(c)) for n, c in zip(ids, coords))
                ways[m["ref"]] = (ids, coords)
                origin["cache"] += 1
                continue
            w = self.ways.get(str(m["ref"]))
            if w is None:
                continue
            ways[m["ref"]] = (list(w["nodes"]), [list(c) for c in w["coords"]])
            supplied.append(m["ref"])
            origin["snapshot"] += 1
        pending = {}
        for wid in supplied:
            for n, c in zip(*ways[wid]):
                c = tuple(c)
                if n in known:
                    require(known[n] == c, "snapshot shared-node coordinate conflict")
                require(pending.setdefault(n, c) == c, "snapshot shared-node coordinate conflict")
        ids = sorted(n for n in pending if n not in known)
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            for n, lat, lon in self.db.execute(f"SELECT id,lat,lon FROM nodes WHERE id IN ({','.join('?' * len(chunk))})", chunk):
                require((lat, lon) == pending[n], "snapshot shared-node coordinate conflict")
        return ways, dict(origin)

    def nested_bound(self, rid, depth=0, stack=()):
        """Union bbox of every descendant area way, or None if any is absent."""
        if depth > MAX_NESTED_DEPTH or rid in stack:
            return None, []
        members = self.members(rid)
        if members is None:
            return None, []
        area, _, nested = area_members(members)
        ways, _ = self.member_ways(area)
        if any(m["ref"] not in ways for m in area):
            return None, []
        boxes = [bbox(c) for _, c in ways.values()]
        seen = [rid]
        for m in nested:
            box, ids = self.nested_bound(int(m["ref"]), depth + 1, (*stack, rid))
            if box is None:
                return None, []
            boxes.append(box)
            seen.extend(ids)
        if not boxes:
            return None, []
        return [min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes)], seen


def assemble_snapshot(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts, snap):
    """Snapshot-mode assembly for one eligible relation (DESIGN Amendment 1 §2)."""
    ref = {"kind": "relation", "id": rid}
    snap_members = snap.members(rid)
    if snap_members is None:
        return assemble_relation(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts) if raw_members else None
    origin_tm = "pbf-cache"
    if raw_members is None:
        rel = snap.rels[str(rid)]
        raw_tags, raw_members, origin_tm = packed(rel["tags"]), packed(snap_members), "snapshot"
    else:
        cache_members = [(m["type"], m["ref"], m["role"]) for m in json.loads(raw_members)]
        if cache_members != [(m["type"], m["ref"], m["role"]) for m in snap_members]:
            writer.gap("snapshot-member-mismatch", ref, None,
                       {"resolution": "snapshot member list differs from the pinned PBF; the snapshot is not used for this relation"})
            return assemble_relation(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts)
    tags, members = json.loads(raw_tags), json.loads(raw_members)
    source = {"kind": "relation", "id": rid, "tags": tags, "input": input_name, "mult": 1, "flags": 0,
              "code": vocab.lookup(0, tags), "members_sha256": hashlib.sha256(raw_members.encode()).hexdigest(),
              "members_count": len(members), "selected": bool(level_filter(0, tags))}
    if source["code"] is None:
        return
    if origin_tm == "snapshot":
        rel = snap.rels[str(rid)]
        why = ("area-role child of requested relation %d, absent from the legacy cache" % snap.children[rid]
               if rid in snap.children and rid not in snap.requested else
               "legacy cache never retained this relation (member limit)")
        writer.note("snapshot-tags-members", ref, {"reason": why + "; tags and members from the date-matched snapshot",
                                                   "version": rel.get("version"), "timestamp": rel.get("timestamp")})
    area, ignored, nested = area_members(members)
    if ignored:
        writer.fh.write(packed({"source": ref, "ignored_members": ignored}) + "\n")
        writer.ignored.update(m["type"] + ":" + m["role"] for m in ignored)
    details = {"resolution": "date-matched snapshot geometry (plan 30 unit 2-03)", "tags_members": origin_tm}
    shape_box, complete = None, False
    try:
        if not area and not nested:
            writer.note("no-area-geometry", ref, {"members": len(members), "tags_members": origin_tm,
                        "reason": "no area-role way or relation member in the date-matched member list: no polygon anywhere"})
            return
        require(len(area) <= MAX_RELATION_MEMBERS, "relation-member-limit")
        ways, origin = snap.member_ways(area)
        missing = sorted({m["ref"] for m in area if m["ref"] not in ways})
        if missing:
            details["missing_way_ids"] = missing
            raise ValueError("missing relation member way")
        if nested:
            details["nested_relation_ids"] = sorted({m["ref"] for m in nested})
            box, descendants = snap.nested_bound(rid)
            if box is not None and not any(intersects(box, w) for _, w in writer.windows):
                writer.note("nested-outside-windows", ref, {"union_bbox_lat_lon": box, "descendants": descendants})
                counts["relations_outside_windows"] += 1
                return
            details["union_bbox_lat_lon"] = box
            shape_box, complete = box, box is not None
            raise ValueError("nested area relation member")
        boxes = [bbox(c) for _, c in ways.values()]
        shape_box = [min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes)]
        complete = True
        if not any(intersects(shape_box, w) for _, w in writer.windows):
            counts["relations_outside_windows"] += 1
            return
        total = sum(len(c) for _, c in ways.values())
        require(total <= MAX_RELATION_VERTICES, "relation vertex limit")
        rings = join_rings(area, ways, MAX_RELATION_VERTICES)
        validate_rings(rings, MAX_RELATION_VERTICES)
        coords = stitch_rings(rings, MAX_RELATION_VERTICES)
        source["geometry_ways"] = origin
        source["tags_members"] = origin_tm
        if len(coords) <= MAX_C_VERTICES:
            writer.geometry(coords, source)
        else:
            boundary_clip(coords, shape_box, source, writer, details)
        counts["relations_assembled"] += 1
        counts["snapshot_relations_assembled"] += 1
    except ValueError as e:
        writer.gap(str(e), ref, shape_box if complete else None, details)


def boundary_clip(coords, shape_box, source, writer, details):
    """Validated complete geometry above the native-C cap: the in-cell piece.

    Topology is validated, so the polygon's restriction to the target cell is
    its boundary clip. An empty clip is recorded as a note; a non-empty clip
    is a production-C event; a C error stays a gap at that cell.
    """
    ref = {"kind": "relation", "id": source["id"]}
    source_sha = hashlib.sha256(packed(coords).encode()).hexdigest()
    for row, w in writer.windows:
        if not intersects(shape_box, w):
            continue
        box = b4(writer.grid, int(row["ix"]), int(row["iy"]))
        a, b, c, d = box
        local = mirror().clip_rect([(p[1], p[0]) for p in coords], c, a, d, b)
        if len(local) < 3:
            writer.note("boundary-clip-empty", ref, {"dump_row": int(row["dump_row"]), "vertices": len(coords),
                                                     "original_coords_sha256": source_sha})
            continue
        clipped = [(lat, lon) for lon, lat in local]
        repaired = source | {"boundary_clip_target": native(row), "original_coords_sha256": source_sha}
        try:
            result = evaluate(clipped, source["code"], 1, 0, row, writer.grid, writer.probe)
        except ValueError as e:
            writer.gap(str(e), ref, box, details)
            continue
        event = {**native(row), "source": repaired, "result": result}
        writer.acc.accept(event)
        writer.fh.write(packed(event) + "\n")


def assemble_relation(rid, raw_tags, raw_members, db, writer, vocab, level_filter, input_name, counts, supplied_ways=None):
    tags, members = json.loads(raw_tags), json.loads(raw_members)
    source = {"kind": "relation", "id": rid, "tags": tags, "input": input_name, "mult": 1, "flags": 0,
              "code": vocab.lookup(0, tags), "members_sha256": hashlib.sha256(raw_members.encode()).hexdigest(),
              "members_count": len(members), "selected": bool(level_filter(0, tags))}
    if source["code"] is None:
        return
    area, ignored, nested = area_members(members)
    if ignored:
        writer.fh.write(packed({"source": {"kind": "relation", "id": rid}, "ignored_members": ignored}) + "\n")
        writer.ignored.update(m["type"] + ":" + m["role"] for m in ignored)
    details = {"resolution": "complete pinned-snapshot relation geometry, or a higher bounded cap with validated topology"}
    ways, total, shape_box, complete = {}, 0, None, False
    try:
        require(len(area) <= MAX_RELATION_MEMBERS, "relation-member-limit")
        if nested:
            details["nested_relation_ids"] = sorted({m["ref"] for m in nested})
            raise ValueError("nested area relation member")
        missing = []
        for m in area:
            if supplied_ways is not None:
                item = supplied_ways.get(m["ref"])
            else:
                sizes = db.execute("SELECT length(nodes),length(coords) FROM ways WHERE id=?", (m["ref"],)).fetchone()
                if sizes:
                    require(max(sizes) <= MAX_JSON_BYTES, "member JSON byte limit")
                    item = tuple(json.loads(v) for v in db.execute("SELECT nodes,coords FROM ways WHERE id=?", (m["ref"],)).fetchone())
                else:
                    item = None
            if item is None:
                missing.append(m["ref"])
                continue
            ids, coords = item
            require(len(ids) == len(coords) >= 2, "invalid relation member geometry")
            total += len(coords)
            member_box = bbox(coords)
            shape_box = member_box if shape_box is None else [min(shape_box[0], member_box[0]), max(shape_box[1], member_box[1]),
                                                            min(shape_box[2], member_box[2]), max(shape_box[3], member_box[3])]
            if total <= MAX_RELATION_VERTICES:
                ways[m["ref"]] = (ids, coords)
        if missing:
            details["missing_way_ids"] = sorted(set(missing))
            details["resolution"] = "fetch the complete relation at the pinned PBF replication timestamp; present-member bounds are insufficient"
            raise ValueError("missing relation member way")
        complete = True
        if shape_box is not None and not any(intersects(shape_box, w) for _, w in writer.windows):
            counts["relations_outside_windows"] += 1
            return
        require(total <= MAX_RELATION_VERTICES, "relation vertex limit")
        rings = join_rings(area, ways, MAX_RELATION_VERTICES)
        validate_rings(rings, MAX_RELATION_VERTICES)
        coords = stitch_rings(rings, MAX_RELATION_VERTICES)
        if len(coords) <= MAX_C_VERTICES:
            writer.geometry(coords, source)
        else:
            # Boundary clipping is an allowed supply repair. Keep the unprobed
            # original's cap gap, so a failed local repair cannot prove absence.
            writer.gap("native-C vertex limit", {"kind": "relation", "id": rid}, shape_box,
                       {"resolution": "a positive boundary-clipped C witness overrides; otherwise a bounded original-source probe is still required"})
            source_sha = hashlib.sha256(packed(coords).encode()).hexdigest()
            for row, w in writer.windows:
                if not intersects(shape_box, w):
                    continue
                box = b4(writer.grid, int(row["ix"]), int(row["iy"]))
                a, b, c, d = box
                local = mirror().clip_rect([(p[1], p[0]) for p in coords], c, a, d, b)
                if len(local) < 3:
                    continue
                clipped = [(lat, lon) for lon, lat in local]
                repaired = source | {"boundary_clip_target": native(row), "original_coords_sha256": source_sha}
                try:
                    result = evaluate(clipped, source["code"], 1, 0, row, writer.grid, writer.probe)
                    event = {**native(row), "source": repaired, "result": result}
                    writer.acc.accept(event)
                    writer.fh.write(packed(event) + "\n")
                except ValueError as e:
                    writer.gap(str(e), {"kind": "relation", "id": rid}, box, details)
        counts["relations_assembled"] += 1
    except ValueError as e:
        writer.gap(str(e), {"kind": "relation", "id": rid}, shape_box if complete else None, details)


def proof_events(path):
    with resolve(path).open("rb") as fh:
        while line := fh.readline(4 << 20):
            require(line.endswith(b"\n"), "oversized/truncated proof-log event")
            yield json.loads(line)


def readonly_cache(path):
    path = resolve(path).resolve()
    require(path.is_file(), "missing retained cache")
    require(not any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal")), "cache has pending journal/WAL")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA cache_size=-4096")
    db.execute("PRAGMA temp_store=FILE")
    return db


def legacy_probe(args, kind, inputs, rows, grid):
    return read_probe(args.source_json, kind, rows, inputs, grid, args, args.source_run, historical=True)[0]


def inherited_inputs(inputs, doc, args):
    # Historical script is reviewed explicitly. Other dependencies must match.
    inputs.hashes.update({p: sha for p, sha in doc["inputs_sha256"].items() if p != label(__file__)})
    inputs.add_file(args.source_json)
    inputs.add_file(args.source_run)
    inputs.hashes[label(__file__)] = digest(__file__)


def reuse(args):
    """Refresh already measured spool evidence; never open the retained spool."""
    rows, _, grid, inputs = context(args)
    doc = legacy_probe(args, "spool", inputs, rows, grid)
    proof = Path(args.output).with_suffix(".proofs.jsonl")
    require(not proof.exists() and not Path(args.output).exists(), "reuse requires fresh outputs")
    with proof.open("w") as fh:
        for event in proof_events(doc["proof_log"]):
            fh.write(packed(event) + "\n")
    inherited_inputs(inputs, doc, args)
    result = {k: v for k, v in doc.items() if not k.startswith("_")}
    result.update(base_document("spool", rows, inputs, grid))
    result.update(command="reuse", proof_log=label(proof), proof_log_sha256=digest(proof), memory=memory(),
                  replay_source=label(args.source_json), replay_script_sha256=doc["inputs_sha256"][label(__file__)])
    write_json(args.output, result)
    return result


def cache_pin(args):
    """Execute only: pin legacy cache to its successful source run and PBF."""
    import osmium
    rows, _, grid, inputs = context(args)
    doc = legacy_probe(args, "pbf", inputs, rows, grid)
    run = inputs.read(args.source_run)
    require("--cache" in run["argv"] and "--pbf" in run["argv"], "source wrapper lacks cache/PBF provenance")
    cache = resolve(args.cache).resolve() / "geometry.sqlite"
    require(resolve(run["argv"][run["argv"].index("--cache") + 1]).resolve() == cache.parent, "cache provenance path mismatch")
    pbf_path = resolve(args.pbf).resolve()
    require(resolve(run["argv"][run["argv"].index("--pbf") + 1]).resolve() == pbf_path, "PBF provenance path mismatch")
    require(doc["heavy_inputs"] == [label(pbf_path)], "PBF provenance manifest mismatch")
    pbf_stamp, cache_stamp = stamp(pbf_path), stamp(cache)
    require(cache_stamp[3] <= resolve(args.source_run).stat().st_mtime_ns, "cache newer than source run")
    require(digest(pbf_path) == doc["inputs_sha256"][label(pbf_path)], "PBF provenance SHA256 mismatch")
    with osmium.io.Reader(str(pbf_path), osmium.osm.osm_entity_bits.NOTHING) as reader:
        timestamp = reader.header().get("osmosis_replication_timestamp") or None
    with readonly_cache(cache) as db:
        require(db.execute("SELECT count(*) FROM nodes").fetchone()[0] == doc["scan_counts"]["nodes"], "cache node census mismatch")
        require(db.execute("SELECT count(*) FROM relations").fetchone()[0] == doc["scan_counts"]["polygon_relations"], "cache relation census mismatch")
    cache_sha = digest(cache)
    require(stamp(pbf_path) == pbf_stamp and stamp(cache) == cache_stamp, "provenance inputs changed during pin")
    if "cache_sha256" in doc:
        require(doc["cache_sha256"] == cache_sha and doc["cache_stamp"] == list(cache_stamp), "cache provenance SHA256/stamp mismatch")
    result = {"schema": "plan30-cache-provenance-v1", "rows": len(rows), "source_json": label(args.source_json),
              "source_json_sha256": digest(args.source_json), "source_run": label(args.source_run),
              "source_run_sha256": digest(args.source_run), "cache_path": label(cache), "cache_sha256": cache_sha,
              "cache_stamp": list(cache_stamp), "pbf_path": label(pbf_path), "pbf_sha256": doc["inputs_sha256"][label(pbf_path)],
              "pbf_stamp": list(pbf_stamp), "replication_timestamp": timestamp,
              "legacy_binding": "successful wrapper cache path and census; first content pin (legacy probe recorded no cache digest)",
              "memory": memory()}
    require(not Path(args.output).exists(), "cache pin requires a fresh output")
    write_json(args.output, result)
    return result


def verify_cache_provenance(args, inputs, doc):
    pin = inputs.read(args.cache_provenance)
    cache = resolve(args.cache).resolve() / "geometry.sqlite"
    require(pin["schema"] == "plan30-cache-provenance-v1", "cache provenance schema mismatch")
    for field, path in (("source_json", args.source_json), ("source_run", args.source_run)):
        require(resolve(pin[field]).resolve() == resolve(path).resolve() and pin[field + "_sha256"] == digest(path), "cache source provenance mismatch")
    require(resolve(pin["cache_path"]).resolve() == cache and pin["cache_stamp"] == list(stamp(cache)), "cache provenance stamp/path mismatch")
    require(doc["heavy_inputs"] == [pin["pbf_path"]] and doc["inputs_sha256"][pin["pbf_path"]] == pin["pbf_sha256"], "cache PBF provenance mismatch")
    # Stat only: the replay never opens the PBF. Original pin did the hash.
    require(pin["pbf_stamp"] == list(stamp(resolve(pin["pbf_path"]))), "PBF provenance stamp mismatch")
    require(digest(cache) == pin["cache_sha256"], "cache provenance SHA256 mismatch")
    require(pin["cache_stamp"] == list(stamp(cache)), "cache changed during provenance check")
    return pin


def pbf_cache(args):
    """Read-only disk-cache replay: retain ways, replace all relation evidence."""
    require(bool(getattr(args, "relation_snapshot", None)) == bool(getattr(args, "relation_snapshot_sha256", None)),
            "--relation-snapshot and --relation-snapshot-sha256 go together")
    from kiwiw.vocab import load as load_vocab
    from kiwiw.selection import level_filter
    rows, _, grid, inputs = context(args)
    doc = legacy_probe(args, "pbf", inputs, rows, grid)
    pin = verify_cache_provenance(args, inputs, doc)
    cache = resolve(args.cache).resolve() / "geometry.sqlite"
    cache_stamp = stamp(cache)
    output = Path(args.output)
    require(not output.exists() and not output.with_suffix(".proofs.jsonl").exists(), "cache replay requires fresh outputs")
    snapshot_doc = snapshot_meta = None
    if getattr(args, "relation_snapshot", None):
        requested = inputs.read(args.relation_requests)["relation_ids"]
        pin_doc = inputs.read(args.relation_snapshot_pin)
        require(pin_doc.get("schema") == SNAPSHOT_PIN_SCHEMA and pin_doc["snapshot"]["sha256"] == args.relation_snapshot_sha256
                and resolve(pin_doc["snapshot"]["path"]).resolve() == resolve(args.relation_snapshot).resolve(),
                "relation snapshot pin mismatch")
        snapshot_doc = load_snapshot(args.relation_snapshot, args.relation_snapshot_sha256, requested)
        inputs.hashes[label(resolve(args.relation_snapshot))] = args.relation_snapshot_sha256
        snapshot_meta = {"path": label(resolve(args.relation_snapshot)), "sha256": args.relation_snapshot_sha256,
                         "pin": label(args.relation_snapshot_pin), "requests": label(args.relation_requests),
                         "attic_date": snapshot_doc.get("attic_date"), "requested_relations": len(requested),
                         "role": "member geometry for the requested relations only (DESIGN Amendment 1)"}
    probe = c_probe(output.parent / (output.stem + "_c_probe"))
    writer = ProbeWriter(output.with_suffix(".proofs.jsonl"), rows, grid, probe)
    counts, omitted = Counter(), {}
    try:
        for event in proof_events(doc["proof_log"]):
            if event["source"]["kind"] == "relation":
                if event.get("gap") == "relation-member-limit":
                    omitted[event["source"]["id"]] = event
                continue
            if "gap" in event:
                writer.gaps[event["gap"]] += 1
            else:
                writer.acc.accept(event)
            writer.fh.write(packed(event) + "\n")
        # No pinned complete-relation snapshot exists yet (see the .requests.json
        # output); `full` stays empty until one is supplied and pinned.
        full = {}
        with readonly_cache(cache) as db:
            snap = Snapshot(snapshot_doc, requested, db) if snapshot_doc is not None else None
            seen = assemble_relations(db, writer, load_vocab("bg_type"), level_filter, pin["pbf_path"], counts, full, snap)
            if snap is not None:
                snapshot_meta["eligible_relations"] = len(snap.eligible)
        snapshot_doc = None
        for rid, event in omitted.items():
            if rid not in seen and rid not in full and not (snap is not None and rid in snap.eligible):
                writer.gap("relation-not-retained-member-limit", {"kind": "relation", "id": rid},
                           details={"resolution": "fetch this complete relation at the pinned PBF replication timestamp; the legacy cache omitted its member list"})
        require(stamp(cache) == cache_stamp, "cache changed during replay")
    finally:
        writer.fh.close()
    inherited_inputs(inputs, doc, args)
    add_runtime_inputs(inputs)
    for p in (output.parent / (output.stem + "_c_probe")).iterdir():
        inputs.add_file(p)
    result = base_document("pbf", rows, inputs, grid) | writer.finish()
    result.update(command="pbf-cache", scan_complete=True, memory=memory(), compile_argv=probe.cmd,
                  scan_counts=dict(counts), heavy_inputs=doc["heavy_inputs"], scope=doc["scope"],
                  cache_provenance=label(args.cache_provenance), cache_sha256=pin["cache_sha256"],
                  replay_source=label(args.source_json), replay_script_sha256=doc["inputs_sha256"][label(__file__)],
                  relation_limits={"vertices": MAX_RELATION_VERTICES, "members": MAX_RELATION_MEMBERS,
                                   "topology_checks": MAX_TOPOLOGY_CHECKS, "json_bytes": MAX_JSON_BYTES})
    if snapshot_meta is not None:
        result["relation_snapshot"] = snapshot_meta
    write_json(output, result)
    requests = sorted({e["source"]["id"] for e in proof_events(result["proof_log"])
                       if "gap" in e and e["source"]["kind"] == "relation"})
    write_json(output.with_suffix(".requests.json"), {"schema": "plan30-relation-requests-v1", "relation_ids": requests,
               "cache_provenance": label(args.cache_provenance), "cache_provenance_sha256": digest(args.cache_provenance),
               "replication_timestamp": pin["replication_timestamp"]})
    return result


def pbf(args):
    import osmium
    from kiwiw.vocab import load as load_vocab
    from kiwiw.selection import level_filter
    from osm_to_parcel_geometry import ROADS
    rows, _, grid, inputs = context(args)
    pbf_path, cache = resolve(args.pbf), Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    original_stamp = stamp(pbf_path)
    inputs.add_file(pbf_path)
    vocab = load_vocab("bg_type")
    probe = c_probe(Path(args.output).parent / "pbf_c_probe")
    writer = ProbeWriter(Path(args.output).with_suffix(".proofs.jsonl"), rows, grid, probe)
    db = disk_db(cache / "geometry.sqlite")
    counts = Counter()

    class Relations(osmium.SimpleHandler):
        def relation(self, rel):
            tags = dict(rel.tags)
            if tags.get("type") not in ("multipolygon", "boundary"):
                return
            if len(rel.members) > MAX_RELATION_MEMBERS:
                writer.gap("relation-member-limit", {"kind": "relation", "id": rel.id})
                return
            members = [{"type": m.type, "ref": m.ref, "role": m.role} for m in rel.members]
            db.execute("INSERT INTO relations VALUES(?,?,?)", (rel.id, packed(tags), packed(members)))
            db.executemany("INSERT OR IGNORE INTO needed VALUES(?)", ((m["ref"],) for m in members if m["type"] == "w"))
            counts["polygon_relations"] += 1

    class Geometry(osmium.SimpleHandler):
        def node(self, node):
            counts["nodes"] += 1
            if node.location.valid():
                db.execute("INSERT INTO nodes VALUES(?,?,?)", (node.id, node.location.lat, node.location.lon))
            else:
                writer.gap("invalid-node-location", {"kind": "node", "id": node.id})
            if counts["nodes"] % 10000 == 0:
                db.commit()

        def way(self, way):
            counts["ways"] += 1
            tags = dict(way.tags)
            needed = db.execute("SELECT 1 FROM needed WHERE id=?", (way.id,)).fetchone() is not None
            if tags.get("highway") in ROADS and not needed:
                return
            if len(way.nodes) > MAX_VERTICES:
                writer.gap("way-vertex-limit", {"kind": "way", "id": way.id})
                return
            ids = [nd.ref for nd in way.nodes]
            if len(ids) < 2:
                return
            locations = {}
            for start in range(0, len(ids), 800):
                part = ids[start:start+800]
                locations.update((i, (lat, lon)) for i, lat, lon in db.execute(
                    "SELECT id,lat,lon FROM nodes WHERE id IN (" + ",".join("?" for _ in part) + ")", part))
            if any(i not in locations for i in ids):
                writer.gap("missing-way-node", {"kind": "way", "id": way.id})
                return
            coords = [locations[i] for i in ids]
            if needed:
                db.execute("INSERT INTO ways VALUES(?,?,?)", (way.id, packed(ids), packed(coords)))
            if tags.get("highway") in ROADS or len(coords) < 3:
                return
            code = vocab.lookup(0, tags)
            if code is not None:
                # Production closes every non-road >=3-coordinate way, including open ways.
                writer.geometry(coords, {"kind": "way", "id": way.id, "tags": tags, "code": code, "mult": 1,
                                         "flags": 0, "selected": bool(level_filter(0, tags)), "input": label(pbf_path)})
            if counts["ways"] % 10000 == 0:
                db.commit()

    try:
        Relations().apply_file(str(pbf_path))
        db.commit()
        Geometry().apply_file(str(pbf_path))  # streaming; all coordinates are on disk, no flex_mem/mmap index
        db.commit()
        assemble_relations(db, writer, vocab, level_filter, label(pbf_path), counts)
        require(stamp(pbf_path) == original_stamp, "PBF changed during probe")
    finally:
        db.close()
        writer.fh.close()
    add_runtime_inputs(inputs)
    for p in (Path(args.output).parent / "pbf_c_probe").iterdir():
        inputs.add_file(p)
    # Pin the parser binary and all loaded pyosmium modules as well as repo inputs.
    for mod in list(sys.modules.values()):
        p = getattr(mod, "__file__", None)
        if p and Path(p).is_file() and getattr(mod, "__name__", "").startswith("osmium"):
            inputs.add_file(p)
    doc = base_document("pbf", rows, inputs, grid) | writer.finish()
    doc.update(scan_complete=True, scope="all production non-road >=3-node ways (production closure), plus tagged multipolygon/boundary relations with EO holes",
               scan_counts=dict(counts), cache="disk SQLite; fixed 4 MiB cache; no node-coordinate RAM index", memory=memory(),
               compile_argv=probe.cmd, heavy_inputs=[label(pbf_path)], pbf_stamp=list(original_stamp),
               cache_path=label(cache / "geometry.sqlite"), cache_stamp=list(stamp(cache / "geometry.sqlite")),
               cache_sha256=digest(cache / "geometry.sqlite"))
    write_json(args.output, doc)
    return doc


def read_probe(path, kind, rows, inputs, grid, args, run_log=None, historical=False):
    doc = inputs.read(path)
    require(doc["schema"] == "plan30-discriminator-v1" and doc["kind"] == kind, "probe schema/kind mismatch")
    script_sha = doc["inputs_sha256"].get(label(__file__))
    require(script_sha == inputs.hashes[label(__file__)] or
            (historical and script_sha == LEGACY_SCRIPT_SHA256), "stale probe input hash")
    for p in (args.fingerprint, args.fingerprint_summary, args.members):
        require(doc["inputs_sha256"].get(label(p)) == inputs.hashes[label(p)], "stale probe input hash")
    expected = keyed(rows)
    actual = keyed(doc["rows"])
    require(set(actual) == set(expected), "probe native-key set mismatch")
    require(all(int(actual[k]["dump_row"]) == int(expected[k]["dump_row"]) for k in actual), "probe dump-row mismatch")
    require(doc["windows"] == base_document(kind, rows, inputs, grid)["windows"], "probe window mismatch")
    if kind == "inventory":
        return doc, set()
    require(doc["scan_complete"] is True and doc["memory"]["max_rss_kib"] > 0, "incomplete/unaccounted probe")
    heavy = set(doc["heavy_inputs"])
    require(len(heavy) == (2 if kind == "spool" else 1), "heavy input manifest mismatch")
    for p, sha in doc["inputs_sha256"].items():
        require(len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), "invalid input SHA256")
        if p in heavy:
            require(Path(p).suffix in ((".data", ".idx") if kind == "spool" else (".pbf",)), "unexpected heavy input")
        elif historical and p == label(__file__) and sha == LEGACY_SCRIPT_SHA256:
            pass  # Only explicit replay admits this one reviewed predecessor.
        else:
            # Revalidate light/code dependencies only. Never reopen heavy inputs in publish.
            require(Path(p).suffix not in (".data", ".idx", ".pbf", ".KWI"), "undeclared heavy input")
            require(digest(resolve(p)) == sha, f"stale probe dependency: {p}")
    require(run_log is not None, "heavy probe requires successful wrapper run log")
    log = inputs.read(run_log)
    require(log["exit"] == 0 and isinstance(log["memory_peak"], int) and log["memory_peak"] > 0 and
            log["max_rss_kib"] > 0, "heavy wrapper failed/missing memory.peak")
    require("--output" in log["argv"] and resolve(log["argv"][log["argv"].index("--output") + 1]) == resolve(path), "wrapper output mismatch")
    command = doc.get("command", kind)
    require(command in log["argv"] and any(resolve(a) == Path(__file__) for a in log["argv"] if a.endswith("disposition.py")), "wrapper command mismatch")
    acc, gaps, gap_counts = Accumulator(rows), set(), Counter()
    note_counts = Counter()
    gap_details = {}
    ignored_counts = Counter()
    proof_path = resolve(doc["proof_log"])
    h = hashlib.sha256()
    from kiwiw.vocab import load as load_vocab
    vocab = load_vocab("bg_type")
    with proof_path.open("rb") as fh:
        while True:
            line = fh.readline(4 << 20)
            if not line:
                break
            require(line.endswith(b"\n"), "oversized/truncated proof-log event")
            h.update(line)
            event = json.loads(line)
            if "ignored_members" in event:
                require(kind == "pbf" and event["source"]["kind"] == "relation", "invalid ignored-member event")
                area, ignored, nested = area_members(event["ignored_members"])
                require(not area and not nested and len(ignored) == len(event["ignored_members"]), "area member ignored")
                ignored_counts.update(m["type"] + ":" + m["role"] for m in ignored)
                continue
            if "note" in event:
                require(kind == "pbf" and event["note"] in NOTE_KINDS and event["source"]["kind"] == "relation",
                        "invalid proof note")
                note_counts[event["note"]] += 1
                continue
            if "gap" in event:
                affected = set(event["affected_dump_rows"])
                require(affected <= {int(r["dump_row"]) for r in rows}, "gap member mismatch")
                gaps.update(affected)
                gap_counts[event["gap"]] += 1
                detail = {"gap": event["gap"], "source": event["source"], **event.get("details", {})}
                for dump in affected:
                    gap_details.setdefault(dump, []).append(detail)
            else:
                require(event["source"]["kind"] in (("spool",) if kind == "spool" else ("way", "relation")), "source-kind mismatch")
                if kind == "pbf":
                    require(vocab.lookup(0, event["source"]["tags"]) == event["source"]["code"], "wrong-code/false vocab supply")
                acc.accept(event)
    require(h.hexdigest() == doc["proof_log_sha256"], "proof-log hash mismatch")
    inputs.hashes[label(proof_path)] = h.hexdigest()
    require(keyed(acc.rows.values()) == actual and dict(gap_counts) == doc["gap_counts"], "probe summary/log mismatch")
    require(dict(ignored_counts) == doc.get("ignored_member_counts", {}), "ignored member summary/log mismatch")
    require(dict(note_counts) == doc.get("note_counts", {}), "proof note summary/log mismatch")
    # Transient only; publication retains exact IDs/classes for every affected row.
    doc["_gaps_by_dump"] = gap_details
    return doc, gaps


def decide(row, inv, probes):
    """Positive C witnesses override gaps; negatives require both exhaustive probes."""
    for kind in ("spool", "pbf"):
        if kind in probes:
            candidate, _ = probes[kind]
            if candidate["supply"]:
                return "supply-path", "OSM-derived demanded-code supply", candidate["supply"], []
    missing = [kind for kind in ("spool", "pbf") if kind not in probes]
    gaps = [kind for kind, (_, gap) in probes.items() if gap]
    if missing or gaps:
        return "conflict-open", "supply discriminator incomplete", None, [*(f"pending-{k}" for k in missing), *(f"{k}-coverage-gap" for k in gaps)]
    correct = sum(p["candidates_by_code"].get(str(row["code"]), 0) for p, _ in probes.values())
    nondegenerate = sum(p["same_code_nondegenerate"] for p, _ in probes.values())
    alternates = sorted({int(c) for p, _ in probes.values() for c in p["emitters_by_code"] if int(c) != int(row["code"])})
    if inv["lattice"]["template"]:
        cause = "type-semantic mismatch" if alternates else "WhereIS-only lattice"
        return "unfixable-proven", cause, {"alternate_emitting_codes": alternates,
                "correct_code_sources_tested": correct, "scope": "pinned spool/PBF; stated window; production vocab; original/clip/unit-mult C probes"}, []
    # A line has zero area under any boundary-preserving clip/densify/round.
    # Do not extrapolate that ceiling to a non-degenerate sub-raw sliver.
    if int(row["code"]) == 321 and correct > 0 and nondegenerate == 0:
        return "unfixable-proven", "representability ceiling", {"proof": "every correct-code source has identically zero latitude or longitude span; repairs preserve a line", "alternate_emitting_codes": alternates}, []
    return "conflict-open", "outlier/stratum evidence insufficient", None, ["original/clip/unit-mult negative; no proof of all honest repairs or semantic mismatch"]


def publish(args):
    rows, summary, grid, inputs = context(args)
    inv, _ = read_probe(args.inventory, "inventory", rows, inputs, grid, args)
    inv_rows = keyed(inv["rows"])
    for row in rows:
        require(inv_rows[key(row)]["lattice"] == lattice_evidence(row, summary, grid), "inventory lattice mismatch")
    probes = {}
    for kind in ("spool", "pbf"):
        path = getattr(args, f"{kind}_json", None)
        if path:
            doc, gaps = read_probe(path, kind, rows, inputs, grid, args, getattr(args, f"{kind}_run", None))
            probes[kind] = (keyed(doc["rows"]), gaps, doc)
    result = []
    for row in rows:
        k, dump = key(row), int(row["dump_row"])
        verdict, cause, proof, unresolved = decide(row, inv_rows[k], {kind: (p[k], dump in gaps) for kind, (p, gaps, _) in probes.items()})
        discriminators = {"retained-demander": inv_rows[k]["retained_demander"], "lattice-identity": inv_rows[k]["lattice"],
                          **{kind: {"result": p[k], "coverage_gap": dump in gaps,
                                    "gap_counts": dict(Counter(d["gap"] for d in doc["_gaps_by_dump"].get(dump, []))),
                                    "blocking_gaps": doc["_gaps_by_dump"].get(dump, [])}
                             for kind, (p, gaps, doc) in probes.items()}, "unresolved": unresolved}
        paths = [label(args.fingerprint), label(args.inventory), row["R_proof_path"], row["spool_requirement_witness"],
                 *(doc["proof_log"] for _, _, doc in probes.values())]
        result.append({**native(row), "rule_id": row["rule_id"], "geographic_band": row["geographic_band"],
                       "stratum": "288-template" if inv_rows[k]["lattice"]["template"] else "321-outlier" if int(row["code"]) == 321 else "288-template-exception",
                       "verdict": verdict, "cause_class": cause, "discriminator_records": packed(discriminators),
                       "proof_paths": packed(paths), "production_C_counterfactual": packed(proof) if proof else "",
                       "successor_implement_path": proof["successor_implement_path"] if verdict == "supply-path" else ""})
    counts = Counter(r["verdict"] for r in result)
    cohort = [r for r in result if int(r["code"]) == 288]
    grouped = {}
    for r in cohort:
        grouped.setdefault(r["verdict"] + ":" + r["cause_class"], []).append(r["dump_row"])
    report = {"schema": "plan30-disposition-v1", "rows": len(result), "inputs_sha256": inputs.hashes,
              "status": "settled" if counts["conflict-open"] == 0 else "incomplete",
              "counts": {v: counts[v] for v in ("supply-path", "unfixable-proven", "conflict-open")},
              "type288_disposition": "uniform" if len(grouped) == 1 else "split", "type288_members_by_verdict_and_cause": grouped,
              "type321_row246": next(r for r in result if r["dump_row"] == 246),
              "open_rows": [{"dump_row": r["dump_row"], "native_key": {n: r[n] for n in NATIVE},
                             "discriminators_tried": json.loads(r["discriminator_records"]), "cause_class": r["cause_class"]}
                            for r in result if r["verdict"] == "conflict-open"],
              "scope": "DVD demanded-code presence; no R geometry copied; no disc/encoder/vocab/extractor change",
              "overview_handoff": f"2-01 source-data parity (342): {counts['supply-path']} supply-path successor implement rows; {counts['unfixable-proven']} unfixable-proven; {counts['conflict-open']} conflict-open. See plan-30 disposition.tsv. O04 spool successors and plan-04 Phase 3 gates remain separate."}
    # All validation completes before either output is changed.
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(result[0]), delimiter="\t")
    writer.writeheader()
    writer.writerows(result)
    Path(args.output).write_text(out.getvalue())
    write_json(args.summary, report)
    return report


def scratch_path(value):
    path = resolve(value).resolve()
    require(path.is_relative_to((ROOT / "output/scratch-30").resolve()), "probe output/cache must be under output/scratch-30")
    return path


def cli(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for kind in ("inventory", "spool", "pbf", "publish"):
        p = commands.add_parser(kind)
        p.add_argument("--fingerprint", type=Path, default=PLAN / "fingerprint.tsv")
        p.add_argument("--fingerprint-summary", type=Path, default=PLAN / "fingerprint_summary.json")
        p.add_argument("--members", type=Path, default=MEMBERS)
        p.add_argument("--output", type=Path, default=PLAN / "disposition.tsv" if kind == "publish" else None, required=kind != "publish")
        if kind == "publish":
            p.add_argument("--inventory", type=Path, required=True)
            p.add_argument("--spool-json", type=Path)
            p.add_argument("--pbf-json", type=Path)
            p.add_argument("--spool-run", type=Path)
            p.add_argument("--pbf-run", type=Path)
            p.add_argument("--summary", type=Path, default=PLAN / "disposition_summary.json")
        elif kind == "spool":
            p.add_argument("--spool", type=Path, required=True)
        elif kind == "pbf":
            p.add_argument("--pbf", type=Path, required=True)
            p.add_argument("--cache", type=Path, required=True)
    # Unit 2-02: replay subcommands. They never reopen the spool; cache-pin
    # reads the PBF header and hashes it once; pbf-cache reads the retained
    # SQLite cache read-only and never opens the PBF.
    for kind in ("reuse", "cache-pin", "pbf-cache"):
        p = commands.add_parser(kind)
        p.add_argument("--fingerprint", type=Path, default=PLAN / "fingerprint.tsv")
        p.add_argument("--fingerprint-summary", type=Path, default=PLAN / "fingerprint_summary.json")
        p.add_argument("--members", type=Path, default=MEMBERS)
        p.add_argument("--source-json", type=Path, required=True)
        p.add_argument("--source-run", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
        if kind in ("cache-pin", "pbf-cache"):
            p.add_argument("--cache", type=Path, required=True)
        if kind == "cache-pin":
            p.add_argument("--pbf", type=Path, required=True)
        if kind == "pbf-cache":
            p.add_argument("--cache-provenance", type=Path, required=True)
            p.add_argument("--relation-snapshot", type=Path)
            p.add_argument("--relation-snapshot-sha256")
            p.add_argument("--relation-snapshot-pin", type=Path, default=SNAPSHOT_PIN)
            p.add_argument("--relation-requests", type=Path, default=REQUESTS)
    args = parser.parse_args(argv)
    if args.command != "publish":
        args.output = scratch_path(args.output)
    else:
        for p in (args.output, args.summary):
            require(resolve(p).resolve().is_relative_to(PLAN), "publish outputs must be under plan-30")
    if args.command == "pbf":
        args.cache = scratch_path(args.cache)
    doc = globals()[args.command.replace("-", "_")](args)
    rows_out = doc.get("rows")
    print(packed({"command": args.command, "rows": len(rows_out) if isinstance(rows_out, list) else rows_out,
                  "counts": doc.get("counts"), "output": label(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
