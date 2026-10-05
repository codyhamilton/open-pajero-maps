#!/usr/bin/env python3
"""Seven O04 presence witnesses. Only --disc opens discs; Execute guards it.

publish reads JSON/TSV only. Missing/failed evidence never proves absence.
The polygon contract matches plan 30: class 2, at least three coordinates,
and the demanded code anywhere in the indexed covering leaf frames. Zero
covering-frame count therefore proves cell-local absence conservatively.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import csv
from functools import lru_cache
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[4]
TRIAGE = ROOT / "docs/plans/04-c-core-orchestration/triage"
NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")
TARGETS = {138: (1695, 699, 288), 236: (913, 876, 578),
           282: (1915, 1030, 288), 284: (1411, 1044, 288),
           317: (1945, 1110, 578), 496: (1248, 1253, 288),
           563: (1505, 1315, 288)}
EMIT = {138, 284, 496}
PINS = {
    "g_successor": "2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae",
    "g_historical": "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72",
    "r": "8c2d20275227b9d2abb0f1802d4e0cbb6697f46545794d19e1a2024b6f169275",
}
SOURCE_NAMES = ("per_rule_phase2_discriminators.tsv", "per_rule_phase2_reconciliation.md",
                "per_rule_completeness_mechanism.tsv", "r_contribution_3-02.tsv")
CAP = 64 * 1024 * 1024
SCHEMA = "plan33-presence-probe-v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def rel(path):
    # Keep the repository's output symlink spelling in provenance.
    path = Path(os.path.abspath(path))
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def light_read(path):
    path = Path(path)
    require(path.suffix in {".json", ".tsv", ".md", ".py"}, "not a light evidence path")
    return path.read_bytes()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@lru_cache(maxsize=1)
def readers():
    old = ROOT / "docs/plans/29-k1-name-anchor-failure/witness_p1.py"
    hardened = old if old.exists() else TRIAGE / "name_anchor/witness_p1.py"
    return (module("o04_hardened_index", hardened),
            module("o04_g_fingerprint", ROOT / "docs/plans/30-2-01-source-data-parity/fingerprint.py"),
            module("o04_cell_local", TRIAGE / "cell_local_2-01.py"))


def reader_hashes():
    result = {rel(__file__): sha(light_read(__file__))}
    for reader in readers():
        result[rel(reader.__file__)] = sha(light_read(reader.__file__))
    return result


def source_rows():
    """Reaffirm committed identity and discriminators without opening a spool."""
    blobs = {name: light_read(TRIAGE / name) for name in SOURCE_NAMES}
    tables = {}
    for name, raw in blobs.items():
        if name.endswith(".tsv"):
            selected = [r for r in csv.DictReader(io.StringIO(raw.decode()), delimiter="\t")
                        if int(r["dump_row"]) in TARGETS]
            require(len(selected) == 7 and len({r["dump_row"] for r in selected}) == 7,
                    f"seven unique rows required: {name}")
            tables[name] = {int(r["dump_row"]): r for r in selected}
    hashes = {rel(TRIAGE / name): sha(raw) for name, raw in blobs.items()}
    citation = TRIAGE / "name_anchor/witnesses/r.json"
    raw = light_read(citation)
    require(json.loads(raw)["historical_disc_sha256"] == PINS["r"], "historical R pin citation differs")
    hashes[rel(citation)] = sha(raw)
    rows = []
    for dump, target in TARGETS.items():
        d = tables[SOURCE_NAMES[0]][dump]
        m = tables[SOURCE_NAMES[2]][dump]
        r = tables[SOURCE_NAMES[3]][dump]
        native = {name: int(d[name]) for name in NATIVE}
        require(tuple(native[n] for n in ("ix", "iy", "code")) == target and native["level"] == 0,
                f"target identity differs: {dump}")
        require(all(int(m[n]) == native[n] for n in NATIVE), f"mechanism key differs: {dump}")
        require(d["rule_id"] == m["matching_rules"] == "O04" and d["cause"] == "spool"
                and d["verdict"] == "conflict-proven" and d["spool_successor"] == "true",
                f"O04/spool identity differs: {dump}")
        require(json.loads(r["key"]) == [0, *target] and r["verdict"] == "proven"
                and r["R_polygon_count"] == d["R_polygon_count"] == "0"
                and d["R_presence"] == d["R_cell_local_presence"] == "false",
                f"retained R-zero assertion differs: {dump}")
        demanders = json.loads(m["demander_ids"])
        discriminators = json.loads(d["discriminator_inputs"])
        predicates = json.loads(m["predicate_inputs"])
        require(demanders and sorted(demanders) == sorted(p["demander_id"] for p in discriminators)
                == sorted(p["demander_id"] for p in predicates["demanders"]),
                f"demander identity differs: {dump}")
        for p in predicates["demanders"]:
            require(p["closing_edge_crossing"] and p["predicates"]["7"]
                    and p["c_original_probe"]["records"] == 0, f"O04 predicate differs: {dump}")
        expected = 1 if dump in EMIT else 0
        require(json.loads(d["repair_c_records"]) == [expected] * len(demanders)
                and json.loads(d["repair_required"]) == [bool(expected)] * len(demanders)
                and all(p["settled"] and p["penultimate_repair_probe"]["c_probe"]["records"] == expected
                        for p in discriminators), f"penultimate stratum differs: {dump}")
        proof_path = ROOT / predicates["proof"]
        if proof_path.exists():
            raw = light_read(proof_path)
            require(sha(raw) == predicates["proof_sha256"], f"O04 proof hash differs: {dump}")
            proof = json.loads(raw)
            require(proof["dump_row"] == dump and proof["disc_sha256"] == PINS["g_historical"],
                    f"O04 proof provenance differs: {dump}")
            hashes[rel(proof_path)] = sha(raw)
        rows.append({**native, "dump_row": dump, "demander_id": demanders,
                     "rule_id": "O04", "cause": "spool",
                     "stratum": "emit-piece" if expected else "demand-removed",
                     "O04_proof_refs": json.loads(d["proof_references"]),
                     "O04_proof_sha256": predicates["proof_sha256"],
                     "retained_R_polygon_count": 0,
                     "retained_R_cell_local_verdict": d["R_cell_local_verdict"]})
    return rows, hashes


def decode_frame(raw, context, leaf_row, cell, code):
    """Use the existing cell-local decoder with a synthetic one-leaf index."""
    w, _, local = readers()
    walk, mesh, _, volume, u16, u32, sws, *_ = w.libs()
    from kiwiw.model import MeshLocation
    from kiwiw.parcel import decode_parcel
    root, bb, lmr, _, ss, ls = context
    path, leaf, lb, ptype = leaf_row
    fb, fc = walk._leaf_frame(root, 0, ptype, path, lb, bb, lmr, {})
    rng = mesh.leaf_frame_range(0, ptype, path, fc)
    bounds = walk.with_range(fb, rng)
    off, length = volume.getsector(leaf.dsa, ss, ls), leaf.size * ls
    require(len(raw) == length and 54 <= length <= CAP, "invalid map frame length")
    directory = 36 + u16(raw, 34) * 4
    require(directory + 18 <= length, "truncated basic frame directory")
    for i in range(3):
        at = directory + i * 6
        start, size = u32(raw, at), u16(raw, at + 4)
        if start != 0xFFFFFFFF:
            start, size = sws(start), sws(size)
            require(size > 0 and directory + 18 <= start and start + size <= length,
                    "invalid basic subframe extent")
            if i == 1:
                bg = raw[start:start + size]
                hlen = sws(u16(bg, 0))
                require(2 <= hlen <= len(bg) and (hlen - 2) % 4 == 0,
                        "invalid background directory")
                for at_bg in range(2, hlen, 4):
                    poff, plen = sws(u16(bg, at_bg)), sws(u16(bg, at_bg + 2))
                    if poff != 0xFFFF:
                        require(hlen <= poff and plen >= 2 and poff + plen <= len(bg),
                                "invalid background element extent")
    loc = MeshLocation(level=0, parcel_type=ptype, blockset_index=0, block_index=0,
                       parcel_index=path[-1], bounds=bounds, sector_addr=leaf.dsa,
                       size_logical_sectors=leaf.size)
    parcel = decode_parcel(loc, raw, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
    counts = Counter()
    for shape in parcel.background.shapes if parcel.background else []:
        require(len(shape.raw_bytes) >= 12 and
                (shape.shape_class == 0 or len(shape.raw_bytes) >= 12 + 2 * shape.n_coords),
                "invalid background shape extent")
        if shape.shape_class == 2 and len(shape.coords) >= 3:
            counts[str(shape.type_code)] += 1
    # decode_slot_shapes keeps its existing reader/index contract. Only the
    # already bounded frame is supplied, with no disc/spool constructor.
    class FrameReader:
        def __init__(self):
            self.pos = None

        def seek(self, at):
            require(at == off, "unexpected decoder seek")
            self.pos = at

        def read(self, n):
            require(self.pos == off and n == length, "unexpected decoder read")
            return raw
    handle = (lmr, (0, 0, 0), (path, leaf, lb, ptype, bb, (fb, fc)))
    index = SimpleNamespace(get=lambda ix, iy: SimpleNamespace(status="resolved", handles=[handle]))
    reader = SimpleNamespace(volume=volume, ss=ss, ls=ls, fh=FrameReader())
    decoded = local.decode_slot_shapes(reader, index, 0, *cell, code)
    require(len(decoded["polys"]) == counts.get(str(code), 0), "shape decoders disagree")
    return {"leaf_path": list(path), "offset": off, "length": length, "sha256": sha(raw),
            "frame_class": fc, "frame_range": rng, "bounds": vars(fb),
            "decoded_shape_type_counts": dict(sorted(counts.items())),
            "matching_polygon_count": len(decoded["polys"]),
            "frame_bytes": w.byte_evidence(raw, off)}


def probe_cells(path, members):
    w, fingerprint, _ = readers()
    # Reuse plan 30's capped pread adapter; reuse plan 29's hardened lookup.
    fh = fingerprint.BoundedPread(os.open(path, os.O_RDONLY), max_read=CAP)
    def read(n, at):
        fh.seek(at)
        return fh.read(n)
    retained = 0
    try:
        for member in members:
            cell = [member["ix"], member["iy"]]
            row, context = w.index_lookup(read, cell)
            row.update({**{n: member[n] for n in NATIVE}, "dump_row": member["dump_row"],
                        "type_count": None})
            try:
                retained += sum(p["length"] for p in row["index_evidence"]["reads"])
                require(retained <= CAP, "aggregate retained evidence exceeds 64 MiB")
                if context is not None:
                    for leaf_row in context[3]:
                        leaf = leaf_row[1]
                        volume = w.libs()[3]
                        retained += leaf.size * context[5]
                        require(retained <= CAP, "aggregate retained evidence exceeds 64 MiB")
                        raw = read(leaf.size * context[5],
                                   volume.getsector(leaf.dsa, context[4], context[5]))
                        row["frames"].append(decode_frame(raw, context, leaf_row, cell, member["code"]))
                    row["type_count"] = sum(f["matching_polygon_count"] for f in row["frames"])
                elif row["status"] == "empty_slot":
                    row["type_count"] = 0
            except (ValueError, IndexError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
                row.update(status="lookup_failed", reason=f"{type(exc).__name__}: {exc}", type_count=None)
            yield row
    finally:
        fh.close()


def validate_row(row, member):
    """Replay retained index and frame bytes without opening a disc."""
    try:
        w, _, _ = readers()
        require(all(type(row[n]) is int and row[n] == member[n] for n in (*NATIVE, "dump_row")),
                "probe native key/dump_row differs")
        require(row["cell"] == [member["ix"], member["iy"]], "probe cell differs")
        require(row["status"] in {"resolved", "empty_slot"}, "unresolved slot cannot prove absence")
        by_extent = {}
        for proof in row["index_evidence"]["reads"]:
            raw = w.evidence_bytes(proof)
            require(len(raw) <= CAP, "oversized index proof")
            extent = (proof["length"], proof["offset"])
            require(extent not in by_extent or by_extent[extent] == raw, "conflicting index bytes")
            by_extent[extent] = raw
        replay, context = w.index_lookup(lambda n, at: by_extent[(n, at)], row["cell"])
        for name in ("status", "reason", "geometry", "blockset", "block", "slot", "block_cells", "index_evidence"):
            require(replay.get(name) == row.get(name), f"index replay differs: {name}")
        if context is None:
            require(not row["frames"] and row["type_count"] == 0, "empty slot contains shapes")
        else:
            require(len(row["frames"]) == len(context[3]) > 0, "indexed leaf frames missing")
            for frame, leaf in zip(row["frames"], context[3]):
                raw = w.evidence_bytes(frame["frame_bytes"])
                require(len(raw) <= CAP, "oversized frame proof")
                expected = decode_frame(raw, context, leaf, row["cell"], member["code"])
                require(frame == expected, "decoded frame proof differs")
            require(row["type_count"] == sum(f["matching_polygon_count"] for f in row["frames"]),
                    "type count differs from frames")
        require(type(row["type_count"]) is int and row["type_count"] >= 0, "invalid type count")
        return None
    except (ValueError, IndexError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
        return f"{type(exc).__name__}: {exc}"


def file_identity(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def disc(args):
    members, hashes = source_rows()
    w, fingerprint, _ = readers()
    path = Path(args.path)
    require(path.name == "ALLDATA.KWI", "disc path must name ALLDATA.KWI")
    require(Path(args.output).resolve().is_relative_to((ROOT / "output/scratch-33").resolve()),
            "probe JSON must be under output/scratch-33")
    before = path.stat()
    pin_mode = "historical-citation" if args.disc == "r" else "streamed-full-sha256"
    if args.disc != "r":
        require(fingerprint.digest(path) == PINS[args.disc], "full G disc pin mismatch")
    rows = list(probe_cells(path, members))
    # Reuse the actual plan-30 G probe logic as an independent count control.
    if args.disc != "r":
        try:
            control = list(fingerprint.disc_rows(path, members))
            require(len(control) == len(rows), "plan30 G count control omitted rows")
            for row, other in zip(rows, control):
                # LeafIndex calls a missing block outside_coverage, whereas
                # the hardened reader can positively prove its sentinel.
                # Only the hardened index evidence can establish absence.
                if row["type_count"] != other["type_count"]:
                    row.update(status="lookup_failed", reason="plan30 G count disagreement", type_count=None)
        except (ValueError, IndexError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
            for row in rows:
                row.update(status="lookup_failed", reason=f"plan30 control failed: {exc}", type_count=None)
    require(file_identity(before) == file_identity(path.stat()), "disc changed during probe")
    write_json(args.output, {"schema": SCHEMA, "disc": args.disc, "disc_path": str(path),
                            "disc_sha256": PINS[args.disc], "pin_verification": pin_mode,
                            "R_pin_source": rel(TRIAGE / "name_anchor/witnesses/r.json") if args.disc == "r" else None,
                            "source_sha256": hashes, "reader_sha256": reader_hashes(),
                            "read_cap_bytes": CAP, "rows": rows})
    return 2 if any(validate_row(row, member) for row, member in zip(rows, members)) else 0


def checked_probe(result, label, members, hashes):
    require(result["schema"] == SCHEMA and result["disc"] == label
            and result["disc_sha256"] == PINS[label], "wrong probe schema/disc/pin")
    require(result["pin_verification"] == ("historical-citation" if label == "r" else "streamed-full-sha256"),
            "wrong probe pin verification")
    require(result["source_sha256"] == hashes, "probe O04 source hashes differ")
    require(result["reader_sha256"] == reader_hashes(), "probe reader hashes differ; rerun probe")
    rows = result["rows"]
    require(len(rows) == 7 and {r["dump_row"] for r in rows} == set(TARGETS),
            "probe must contain all seven rows exactly once")
    return {r["dump_row"]: r for r in rows}


def publish(args):
    members, hashes = source_rows()
    probes, problems = {}, {}
    inputs = {}
    for label in PINS:
        path = getattr(args, label)
        if path is None:
            problems[label] = "missing guarded disc probe"
            continue
        try:
            raw = light_read(path)
            inputs[rel(path)] = sha(raw)
            probes[label] = checked_probe(json.loads(raw), label, members, hashes)
        except (ValueError, IndexError, KeyError, TypeError, OSError) as exc:
            problems[label] = f"invalid guarded disc probe: {exc}"
    rows, exceptions = [], []
    for member in members:
        row = copy.deepcopy(member)
        row["O04_source_sha256"] = hashes
        issues = []
        for label in PINS:
            evidence = probes.get(label, {}).get(member["dump_row"])
            error = problems.get(label)
            if evidence is not None:
                error = validate_row(evidence, member)
            prefix = {"g_successor": "G_successor", "g_historical": "G_historical", "r": "R"}[label]
            row[f"{prefix}_sha256"] = PINS[label]
            row[f"{prefix}_slot_status"] = evidence["status"] if evidence else "pending-probe"
            row[f"{prefix}_type_count"] = None if error else evidence["type_count"]
            row[f"{prefix}_evidence"] = evidence
            if error:
                issues.append(f"{label}: {error}")
            elif evidence["type_count"] != 0:
                issues.append(f"{label}: demanded type present ({evidence['type_count']})")
        row["presence_witness_status"] = "exception" if issues else "absence-proven"
        row["exceptions"] = issues
        if issues:
            exceptions.append({"dump_row": member["dump_row"], "reasons": issues})
        rows.append(row)
    result = {"schema": "plan33-presence-witness-v1", "rows": rows,
              "source_sha256": hashes, "probe_sha256": inputs, "exceptions": exceptions,
              "absence_proven_count": 7 - len(exceptions),
              "R_pin_verification": "historical citation; not rehashed",
              "presence_contract": "class-2 polygons with >=3 coordinates in indexed covering frames; zero count proves cell-local absence",
              "phase1_verified": not exceptions, "dispositions_assigned": False}
    write_json(args.json, result)
    columns = [*NATIVE, "dump_row", "demander_id", "rule_id", "cause", "O04_proof_refs",
               "O04_proof_sha256", "O04_source_sha256", "stratum", "retained_R_polygon_count",
               "retained_R_cell_local_verdict"]
    for prefix in ("G_successor", "G_historical", "R"):
        columns += [f"{prefix}_type_count", f"{prefix}_sha256", f"{prefix}_slot_status", f"{prefix}_evidence"]
    columns += ["presence_witness_status", "exceptions"]
    Path(args.tsv).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.tsv).open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: packed(row[name]) if isinstance(row[name], (dict, list))
                             else ("" if row[name] is None else row[name]) for name in columns})
    return 2 if exceptions else 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--disc":
        argv[0] = "disc"
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("disc")
    probe.add_argument("disc", choices=PINS)
    probe.add_argument("--path", required=True)
    probe.add_argument("--output", required=True)
    pub = sub.add_parser("publish")
    for label in PINS:
        pub.add_argument("--" + label.replace("_", "-"), type=Path)
    pub.add_argument("--tsv", type=Path, default=PLAN / "presence_witness.tsv")
    pub.add_argument("--json", type=Path, default=PLAN / "presence_witness.json")
    args = parser.parse_args(argv)
    return disc(args) if args.command == "disc" else publish(args)


if __name__ == "__main__":
    raise SystemExit(main())
