#!/usr/bin/env python3
"""Light proof census, guarded G-disc probe, and checked census merge for plan 30.

Only ``disc`` (also spelled ``--disc``) opens a disc. Execute must run that
command through run_heavy_python.py. Census and merge read TSV/JSON only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PLAN = Path(__file__).resolve().parent
TRIAGE = ROOT / "docs/plans/04-c-core-orchestration/triage"
MEMBERS = TRIAGE / "2-01_g-omits-cell-local-dvd-type_members.tsv"
MEMBERSHIP = TRIAGE / "phase3_membership.tsv"
JOIN = TRIAGE / "per_rule_phase2_join.tsv"
NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")
PINS = {
    "historical": "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72",
    "successor": "2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae",
}
SPAN_TOL_DEG = 1e-9
SIGNATURE_DECIMALS = 9
MAX_READ_BYTES = 64 * 1024 * 1024
EXTRA_COLUMNS = [
    "dump_row", "rule_id", "R_polygon_count", "R_cell_local_polygon_count",
    "R_vertex_counts", "R_polygon_bboxes_lat_lon", "R_bbox_lat_lon",
    "R_meet_branches", "R_cell_local_meets", "R_shape_signature_id",
    "R_local_signatures", "R_template_span_ok", "R_proof_path",
    "G_historical_type_count", "G_historical_sha256", "G_historical_status",
    "G_successor_type_count", "G_successor_sha256", "G_successor_status",
    "spool_requirement_witness", "spool_demander_identity", "spool_source_branch",
    "spool_source_cell", "spool_source_ncoord", "spool_source_bbox_raw",
    "clipped_ring_q", "clipped_ring_area2", "encoder_emits", "mechanism",
    "geographic_band",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relpath(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def digest(path):
    # Stream hashing, including the Execute-only disc pin check; never read().
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def packed(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True, allow_nan=False)


class Inputs:
    def __init__(self):
        self.hashes = {relpath(__file__): digest(__file__)}

    def read(self, path, kind):
        path = resolve(path)
        require(path.suffix == (".json" if kind == "json" else ".tsv"),
                f"light input must be {kind}: {path}")
        # Hash exactly the bytes parsed, so the manifest cannot name a later version.
        data = path.read_bytes()
        self.hashes[relpath(path)] = hashlib.sha256(data).hexdigest()
        if kind == "json":
            return json.loads(data)
        return list(csv.DictReader(io.StringIO(data.decode()), delimiter="\t"))


def key(row):
    return tuple(int(row[k]) for k in NATIVE)


def keyed(rows, label):
    result = {}
    for row in rows:
        k = key(row)
        require(k not in result, f"duplicate native key in {label}: {k}")
        result[k] = row
    return result


def load_members(inputs, path):
    rows = inputs.read(path, "tsv")
    keyed(rows, "members")
    require(len(rows) == 342, f"expected 342 members, got {len(rows)}")
    require(len({int(r["dump_row"]) for r in rows}) == 342, "duplicate dump_row")
    require(all(r["membership"] == "2-01-member" for r in rows), "non-2-01 member")
    return sorted(rows, key=lambda r: int(r["dump_row"]))


def bbox(coords):
    require(len(coords) >= 3 and all(len(c) == 2 for c in coords), "invalid polygon coords")
    require(all(math.isfinite(v) for c in coords for v in c), "non-finite coordinate")
    return [min(c[0] for c in coords), max(c[0] for c in coords),
            min(c[1] for c in coords), max(c[1] for c in coords)]


def signature(coords):
    """Translation/scale normalisation, preserving every vertex, start and winding."""
    a, b, c, d = bbox(coords)
    require(b > a and d > c, "degenerate bbox")
    return tuple((round((lat - a) / (b - a), SIGNATURE_DECIMALS),
                  round((lon - c) / (d - c), SIGNATURE_DECIMALS)) for lat, lon in coords)


def template_span(box):
    a, b, c, d = box
    return abs((b - a) - 1 / 12) <= SPAN_TOL_DEG and abs((d - c) - 1 / 8) <= SPAN_TOL_DEG


def signed_area2_lon_lat(sig):
    return sum(sig[i][1] * sig[(i + 1) % len(sig)][0] -
               sig[(i + 1) % len(sig)][1] * sig[i][0] for i in range(len(sig)))


def geographic_band(box):
    a, b, c, d = box
    lat, lon = (a + b) / 2, (c + d) / 2
    if lon < 113:
        return "west"
    if lon > 153.5:
        return "east"
    # A conservative south-of-WA window, descriptive only (no coastline test).
    if lat < -35.5 and 113 <= lon < 130:
        return "south_offshore"
    return "other"


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_tsv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[*NATIVE, *EXTRA_COLUMNS], delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def census(args):
    inputs = Inputs()
    members = load_members(inputs, args.members)
    membership = keyed(inputs.read(args.membership, "tsv"), "phase3 membership")
    joined = keyed(inputs.read(args.join, "tsv"), "plan28 join")
    member_keys = set(key(r) for r in members)
    require({k for k, r in membership.items() if r["phase3_group"] ==
             "g-omits-cell-local-dvd-type"} == member_keys, "phase3 group set mismatch")
    require({k for k, r in joined.items() if r["plan14_group"] ==
             "g-omits-cell-local-dvd-type"} == member_keys, "plan28 group set mismatch")
    rows, signatures = [], Counter()
    for member in members:
        k, dump = key(member), int(member["dump_row"])
        require(int(membership[k]["dump_row"]) == dump == int(joined[k]["dump_row"]),
                f"dump_row join mismatch: {dump}")
        proof = inputs.read(member["r_proof_path"], "json")
        witness_path = proof["spool_requirement_witness"]
        witness = inputs.read(witness_path, "json")
        require(key(proof["native_key"]) == k == key(witness["native_key"]),
                f"proof/witness key mismatch: {dump}")
        require(proof["dump_row"] == dump == witness["dump_row"], f"proof dump mismatch: {dump}")
        require(proof["g_cell_type_count"] == int(member["g_cell_type_count"]),
                f"retained G mismatch: {dump}")
        require(proof["r_slot_status"] == member["r_slot_status"] == "resolved",
                f"unresolved R: {dump}")
        polys, meets, mechanism = (proof["r_matching_polygons"], proof["r_cell_local_meets"],
                                   proof["mechanism"])
        require(len(polys) == int(member["R_polygon_count"]), f"R count mismatch: {dump}")
        require(len(meets) == int(member["r_meeting_polygons"]) > 0, f"meet count mismatch: {dump}")
        branches = sorted({b for meet in meets for b in meet["branches"]})
        require(",".join(branches) == member["r_meet_branches"], f"branch mismatch: {dump}")
        boxes, sigs, counts = [], [], []
        for poly in polys:
            coords = poly["coords"]
            require(len(coords) == poly["n_coords"], f"vertex count mismatch: {dump}")
            boxes.append(bbox(coords))
            sigs.append(signature(coords))
            counts.append(len(coords))
        combined = [min(b[0] for b in boxes), max(b[1] for b in boxes),
                    min(b[2] for b in boxes), max(b[3] for b in boxes)]
        span_ok = len(polys) == 1 and counts == [13] and template_span(boxes[0])
        if int(member["code"]) == 288 and span_ok:
            signatures[sigs[0]] += 1
        row = {name: member[name] for name in NATIVE}
        row.update({
            "dump_row": dump, "rule_id": joined[k]["rule_id"], "R_polygon_count": len(polys),
            "R_cell_local_polygon_count": len(meets), "R_vertex_counts": packed(counts),
            "R_polygon_bboxes_lat_lon": packed(boxes), "R_bbox_lat_lon": packed(combined),
            "R_meet_branches": ",".join(branches), "R_cell_local_meets": packed(meets),
            "R_shape_signature_id": "other" if int(member["code"]) == 288 else "not-288",
            "R_local_signatures": packed(sigs), "R_template_span_ok": str(span_ok).lower(),
            "R_proof_path": member["r_proof_path"],
            "G_historical_type_count": int(member["g_cell_type_count"]),
            "G_historical_sha256": PINS["historical"],
            "G_historical_status": "retained-proof;pending-disc-control",
            "G_successor_type_count": "", "G_successor_sha256": "",
            "G_successor_status": "pending-disc-probe", "spool_requirement_witness": witness_path,
            "spool_demander_identity": packed(witness["source"]),
            "geographic_band": geographic_band(combined),
        })
        for name, value in mechanism.items():
            encoded = packed(value) if isinstance(value, (list, dict)) else str(value)
            require(member[name] == encoded or (name == "spool_source_cell" and
                    json.loads(member[name]) == value) or (name == "spool_source_bbox_raw" and
                    json.loads(member[name]) == value), f"mechanism mismatch: {dump}/{name}")
            row[name] = encoded
        source = witness["source"]
        require(source["source_cell"] == mechanism["spool_source_cell"] and
                source["n_coords"] == mechanism["spool_source_ncoord"] and
                source["branch"] == mechanism["spool_source_branch"],
                f"demander mismatch: {dump}")
        rows.append(row)
    # The two most frequent measured sequences are recorded in full, never
    # inferred from spans/counts. Additional or wrong-span sequences stay other.
    templates = {sig: f"T{i + 1}" for i, (sig, _) in enumerate(
        sorted(signatures.items(), key=lambda item: (-item[1], item[0]))[:2])}
    for row in rows:
        if int(row["code"]) == 288 and row["R_template_span_ok"] == "true":
            sig = tuple(tuple(v) for v in json.loads(row["R_local_signatures"])[0])
            row["R_shape_signature_id"] = templates.get(sig, "other")
    exceptions = [int(r["dump_row"]) for r in rows if int(r["code"]) == 288 and
                  r["R_shape_signature_id"] == "other"]
    summary = {
        "schema": "plan30-fingerprint-v1", "rows": len(rows), "inputs_sha256": inputs.hashes,
        "type_counts": dict(Counter(r["code"] for r in rows)),
        "non_288_dump_rows": [r["dump_row"] for r in rows if int(r["code"]) != 288],
        "rule_counts": dict(Counter(r["rule_id"] for r in rows)),
        "signature_definition": "[(lat-lat_min)/lat_span,(lon-lon_min)/lon_span] in original vertex order; round to 9 decimals; retain closure/start/winding",
        "span_degrees": {"lat": 1 / 12, "lon": 1 / 8, "absolute_tolerance": SPAN_TOL_DEG},
        "templates": {name: {"count": signatures[sig], "normalised_vertices_lat_lon": sig,
                               "signed_area2_lon_lat": signed_area2_lon_lat(sig),
                               "sha256": hashlib.sha256(packed(sig).encode()).hexdigest()}
                      for sig, name in templates.items()},
        "template_exception_dump_rows": exceptions,
        "measured_288_signature_count": len(signatures),
        "type288_span_pass_count": sum(r["R_template_span_ok"] == "true" for r in rows
                                       if int(r["code"]) == 288),
        "R_cell_local_branch_counts": dict(Counter(r["R_meet_branches"] for r in rows)),
        "geographic_band_rule": "bbox midpoint; west lon<113; east lon>153.5; then south_offshore lat<-35.5 and 113<=lon<130; otherwise other (descriptive window, no coastline test)",
        "geographic_band_counts": dict(Counter(r["geographic_band"] for r in rows)),
        "G_disc_verification": "pending-successor-and-historical-probes",
        "R_provenance": "retained scratch-14 decoded-coordinate proofs; no R-disc read or fresh pin validation in this census",
    }
    write_tsv(args.output, rows)
    write_json(args.summary, summary)
    return summary


class BoundedPread:
    """File-like cursor for existing readers; every read is a capped os.pread."""
    def __init__(self, fd, max_read=MAX_READ_BYTES):
        self.fd, self.pos, self.max_read = fd, 0, max_read
        self.size = os.fstat(fd).st_size

    def seek(self, offset, whence=0):
        base = {0: 0, 1: self.pos, 2: self.size}[whence]
        require(base + offset >= 0, "negative disc offset")
        self.pos = base + offset
        return self.pos

    def read(self, length=-1):
        require(0 <= length <= self.max_read, f"refuse unbounded/oversized disc read: {length}")
        require(self.pos + length <= self.size, "disc read exceeds file")
        data = os.pread(self.fd, length, self.pos)
        require(len(data) == length, "short disc read")
        self.pos += length
        return data

    def close(self):
        os.close(self.fd)


def disc_rows(path, members):
    """Existing frame/shape decoders and bounded LeafIndex, with strict PMR reads."""
    sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
    from harness import walk
    from kiwiw import volume
    from kiwiw.model import MeshLocation
    from kiwiw.parcel import decode_parcel
    from overlay_test import RReader
    from r_neighbours import LeafIndex

    class Reader(RReader):
        def __init__(self):
            self.walk, self.volume = walk, volume
            self.path = str(path)
            self.fh = BoundedPread(os.open(path, os.O_RDONLY))
            try:
                hdr = volume.parse_volume_header(self.fh.read(volume.DATAVOL_SIZE))
                mht = volume.parse_management_header_table(self.fh.read(volume.MHT_SIZE))
                prdm = mht.entries[0]
                require(not prdm.name, "file-based PDMDH unsupported")
                self.ss, self.ls = hdr.sector_size, hdr.logical_sector_size
                self.fh.seek(volume.getsector(prdm.dsa, self.ss, self.ls))
                self.pdmdh = volume.parse_pdmdh_full(self.fh.read(prdm.size * self.ls))
            except BaseException:
                self.fh.close()
                raise

        def leaves(self, lmr, blk):
            # RReader.leaves catches PMR parse errors and returns []: that would
            # falsely certify G absence, so propagate errors for this probe.
            _, _, _, ent, bb = blk
            self.fh.seek(volume.getsector(ent.dsa, self.ss, self.ls))
            tree = walk.parse_parcel_mgmt_record(self.fh.read(ent.size * self.ls), lmr)
            gn_lat, gn_lng = 1 + lmr.n_parcels_lat[0], 1 + lmr.n_parcels_lng[0]
            cache, out = {}, []
            for lpath, le, lb, ptype in walk._iter_tree_leaves(tree, bb, lmr, ()):
                parent = walk._narrow_bounds(bb, gn_lat, gn_lng, lpath[0])
                frame = walk._leaf_frame(tree, lmr.level, ptype, lpath, lb, bb, lmr, cache)
                out.append((lpath, le, lb, ptype, parent, frame))
            return out

    reader = Reader()
    try:
        indices = {level: LeafIndex(reader, level) for level in {int(r["level"]) for r in members}}
        for member in members:
            level, ix, iy, code = (int(member[k]) for k in ("level", "ix", "iy", "code"))
            slot = indices[level].get(ix, iy)
            count = 0
            for lmr, blk, leaf in slot.handles:
                lpath, le, _, ptype, _, (fb, fc) = leaf
                frame = walk.with_range(fb, walk.leaf_frame_range(level, ptype, lpath, fc))
                reader.fh.seek(volume.getsector(le.dsa, reader.ss, reader.ls))
                buf = reader.fh.read(le.size * reader.ls)
                loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=blk[1],
                                   block_index=blk[2], parcel_index=lpath[-1], bounds=frame,
                                   sector_addr=le.dsa, size_logical_sectors=le.size)
                parcel = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
                if parcel.background:
                    count += sum(s.shape_class == 2 and len(s.coords) >= 3 and s.type_code == code
                                 for s in parcel.background.shapes)
                del parcel, buf
            yield {**{k: int(member[k]) for k in NATIVE}, "dump_row": int(member["dump_row"]),
                   "type_count": count, "slot_status": slot.status}
    finally:
        reader.fh.close()


def disc(args):
    inputs = Inputs()
    members = load_members(inputs, args.members)
    path = resolve(args.path)
    require(path.name == "ALLDATA.KWI", "disc must name ALLDATA.KWI")
    require(resolve(args.output).resolve().is_relative_to((ROOT / "output/scratch-30").resolve()),
            "disc JSON must be under output/scratch-30")
    before = path.stat()
    disc_sha = digest(path)
    require(disc_sha == PINS[args.pin], f"{args.pin} disc pin mismatch: {disc_sha}")
    inputs.hashes[relpath(path)] = disc_sha
    rows = list(disc_rows(path, members))  # Only small counts/keys retained.
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
            "disc changed during pin check/probe")
    if args.pin == "historical":
        require(all(r["type_count"] == int(m["g_cell_type_count"]) for r, m in zip(rows, members)),
                "historical disc disagrees with members g_cell_type_count")
    # Capture loaded repo decoder/reference dependencies without reading any
    # extra disc/spool. Each reference JSON used by imports is also hashed.
    for module in list(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).resolve().is_relative_to(ROOT / "parser"):
            inputs.hashes[relpath(filename)] = digest(filename)
    for ref in (ROOT / "parser/refdata/profile").glob("*.json"):
        inputs.hashes[relpath(ref)] = digest(ref)
    result = {"schema": "plan30-disc-counts-v1", "pin": args.pin, "disc_sha256": disc_sha,
              "inputs_sha256": inputs.hashes, "rows": rows, "read_cap_bytes": MAX_READ_BYTES,
              "read_contract": "streamed SHA256; bounded pread metadata/block/leaf decode; LeafIndex LRU=64"}
    write_json(args.output, result)
    return {"rows": len(rows), "pin": args.pin, "type_count_total": sum(r["type_count"] for r in rows)}


def checked_disc_result(result, members, pin, members_sha):
    require(result["schema"] == "plan30-disc-counts-v1" and result["pin"] == pin and
            result["disc_sha256"] == PINS[pin], f"wrong {pin} disc provenance")
    require(result["inputs_sha256"].get(relpath(members)) == members_sha,
            f"{pin} members hash mismatch")
    rows = keyed(result["rows"], f"{pin} counts")
    for row in rows.values():
        require(type(row["type_count"]) is int and row["type_count"] >= 0,
                f"invalid {pin} type count")
        require(row["slot_status"] in {"resolved", "empty_slot", "outside_coverage"},
                f"invalid {pin} slot status")
        require(row["slot_status"] == "resolved" or row["type_count"] == 0,
                f"unresolved {pin} slot with polygons")
    return rows


def merge(args):
    inputs = Inputs()
    members = load_members(inputs, args.members)
    rows = inputs.read(args.output, "tsv")
    summary = inputs.read(args.summary, "json")
    require(summary["schema"] == "plan30-fingerprint-v1", "wrong census schema")
    member_sha = inputs.hashes[relpath(args.members)]
    require(summary["inputs_sha256"].get(relpath(args.members)) == member_sha,
            "census members hash mismatch")
    mapped = keyed(rows, "fingerprint")
    require(set(mapped) == {key(r) for r in members}, "fingerprint member set mismatch")
    probes = {}
    for pin, filename in (("successor", args.successor_json), ("historical", args.historical_json)):
        result = inputs.read(filename, "json")
        probes[pin] = checked_disc_result(result, args.members, pin, member_sha)
        require(set(probes[pin]) == set(mapped), f"{pin} key set mismatch")
    for member in members:
        k, dump = key(member), int(member["dump_row"])
        require(int(mapped[k]["dump_row"]) == dump, f"fingerprint dump_row mismatch: {dump}")
        for pin in probes:
            require(probes[pin][k]["dump_row"] == dump, f"{pin} dump_row mismatch: {dump}")
        historical = probes["historical"][k]["type_count"]
        require(historical == int(member["g_cell_type_count"]) ==
                int(mapped[k]["G_historical_type_count"]), f"historical control mismatch: {dump}")
        for pin in probes:
            mapped[k][f"G_{pin}_type_count"] = probes[pin][k]["type_count"]
            mapped[k][f"G_{pin}_sha256"] = PINS[pin]
            mapped[k][f"G_{pin}_status"] = "disc-verified:" + probes[pin][k]["slot_status"]
    summary["merge_inputs_sha256"] = inputs.hashes
    summary["G_disc_verification"] = "successor-and-historical-verified;historical-control-matched"
    summary["G_type_count_totals"] = {pin: sum(r["type_count"] for r in data.values())
                                      for pin, data in probes.items()}
    write_tsv(args.output, [mapped[key(m)] for m in members])
    write_json(args.summary, summary)
    return {"rows": len(rows), "G_disc_verification": summary["G_disc_verification"],
            "G_type_count_totals": summary["G_type_count_totals"]}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--disc":
        argv[0] = "disc"
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    light = commands.add_parser("census", help="read only retained TSV/JSON inputs")
    light.add_argument("--membership", type=Path, default=MEMBERSHIP)
    light.add_argument("--join", type=Path, default=JOIN)
    heavy = commands.add_parser("disc", help="Execute-only; alias --disc; bounded G counts")
    heavy.add_argument("path", type=Path)
    heavy.add_argument("--pin", choices=PINS, required=True)
    heavy.add_argument("--output", type=Path, required=True)
    combine = commands.add_parser("merge", help="validate pins/key sets/control, then fill G columns")
    combine.add_argument("--successor-json", type=Path, required=True)
    combine.add_argument("--historical-json", type=Path, required=True)
    for command in (light, heavy, combine):
        command.add_argument("--members", type=Path, default=MEMBERS)
    for command in (light, combine):
        command.add_argument("--output", type=Path, default=PLAN / "fingerprint.tsv")
        command.add_argument("--summary", type=Path, default=PLAN / "fingerprint_summary.json")
    args = parser.parse_args(argv)
    try:
        result = {"census": census, "disc": disc, "merge": merge}[args.command](args)
    except (ValueError, KeyError) as exc:
        parser.exit(1, f"fingerprint: {exc}\n")
    if args.command == "census":
        result = {k: result[k] for k in ("rows", "type_counts", "rule_counts", "templates",
                                        "template_exception_dump_rows", "geographic_band_counts")}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
