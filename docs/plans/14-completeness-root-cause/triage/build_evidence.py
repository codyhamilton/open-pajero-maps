#!/usr/bin/env python3
"""Plan 14 Phase 1 evidence, without synthesising mechanism assignments.

Run from the repository root under flock output/.heavy.lock after fresh K1.
Only plan-14 documentation and scratch-14 artifacts are written. The classifier
is invoked with unchanged rules; missing mechanism evidence stays missing.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
from harness import walk
from kiwiw.model import MeshLocation
from kiwiw.parcel import decode_parcel
from kiwiw.spool import SpoolReader, decode_columns
from overlay_test import RReader
from r_neighbours import LeafIndex
from quantisation_roundtrip import Lattice, RAW

SCRATCH = ROOT / "output/scratch-14"
TRIAGE = Path(__file__).resolve().parent
OLD = ROOT / "docs/plans/04-c-core-orchestration/triage"
NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape", "vert")
TS = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
G_SHA = "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72"


def digest(path):
    with Path(path).open("rb") as fh:
        h = hashlib.file_digest(fh, "sha256")
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def relative(path):
    return str(path.relative_to(ROOT))


class StrictReader(RReader):
    """Same leaf/frame enumeration as RReader, with PM errors propagated."""

    def leaves(self, lmr, blk):
        _, _, _, ent, bb = blk
        self.fh.seek(self.volume.getsector(ent.dsa, self.ss, self.ls))
        raw = self.fh.read(ent.size * self.ls)
        assert len(raw) == ent.size * self.ls
        root = walk.parse_parcel_mgmt_record(raw, lmr)
        out, cache = [], {}
        for lpath, le, lb, ptype in walk._iter_tree_leaves(root, bb, lmr, ()):
            parent = walk._narrow_bounds(bb, 1 + lmr.n_parcels_lat[0],
                                         1 + lmr.n_parcels_lng[0], lpath[0])
            fr = walk._leaf_frame(root, lmr.level, ptype, lpath, lb, bb, lmr, cache)
            out.append((lpath, le, lb, ptype, parent, fr))
        return out


def disc_witness(reader, indexes, key):
    level, ix, iy, code = key[:4]
    result = {"disc": reader.path, "cell": [level, ix, iy], "code": code,
              "contract": "decoded shape_class=2 and len(coords)>=3 in covering leaf slots",
              "frames": []}
    try:
        index = indexes.setdefault(level, None)
        if index is None:
            index = indexes[level] = LeafIndex(reader, level)
        slot = index.get(ix, iy)
        result["slot_status"] = slot.status
        addr, _ = index._addr(ix, iy)
        if addr in index.blocks:
            ent = index.blocks[addr][3]
            off = reader.volume.getsector(ent.dsa, reader.ss, reader.ls)
            reader.fh.seek(off)
            raw = reader.fh.read(ent.size * reader.ls)
            result["parcel_management"] = {"offset": off, "length": len(raw),
                                             "sha256": hashlib.sha256(raw).hexdigest()}
        count = 0
        for lmr, blk, leaf in slot.handles:
            lpath, le, lb, ptype, _, (fb, fc) = leaf
            frame_range = walk.leaf_frame_range(level, ptype, lpath, fc)
            fb = walk.with_range(fb, frame_range)
            off = reader.volume.getsector(le.dsa, reader.ss, reader.ls)
            length = le.size * reader.ls
            reader.fh.seek(off)
            buf = reader.fh.read(length)
            assert len(buf) == length
            loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=blk[1],
                               block_index=blk[2], parcel_index=lpath[-1], bounds=fb,
                               sector_addr=le.dsa, size_logical_sectors=le.size)
            parcel = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
            shapes = parcel.background.shapes if parcel.background else []
            polygons = [s for s in shapes if s.shape_class == 2 and len(s.coords) >= 3]
            matching = [s for s in polygons if s.type_code == code]
            count += len(matching)
            result["frames"].append({"leaf_path": list(lpath), "frame_class": fc,
                "frame_range": frame_range, "offset": off, "length": length,
                "sha256": hashlib.sha256(buf).hexdigest(),
                "polygon_types": dict(sorted(Counter(s.type_code for s in polygons).items())),
                "matching_polygon_count": len(matching)})
        result["polygon_count"] = count
    except Exception as exc:
        result["evidence-gap"] = f"covering leaf enumeration/decode: {type(exc).__name__}: {exc}"
        result["polygon_count"] = None
    return result


def spool_witnesses(keys):
    """Find one exact (a)/(b) K1 requirement trigger per cell/type.

    Scan source bytes, applying _k1_cmp.c's bbox and deep-vertex arithmetic.
    This is a requirement witness only; it does not compute rule mechanisms.
    A remaining (c) centre trigger is explicitly left as a source evidence gap.
    """
    found = {}
    reader = SpoolReader(ROOT / "output/extract_timing/spool")
    for level in sorted({k[0] for k in keys}):
        wanted = {(k[1], k[2], k[3]) for k in keys if k[0] == level}
        wanted_types = np.array(sorted({k[2] for k in wanted}))
        lat = Lattice(level)
        idx = reader._load_idx(level)
        for cell_ordinal, (sx, sy, raw) in enumerate(reader.iter_cell_raw(level)):
            cols = decode_columns(raw)
            ns = cols["b_nstored"].astype(np.int64)
            offsets = np.r_[0, np.cumsum(ns)]
            selected = np.flatnonzero((cols["b_class"] == 2) & (ns >= 3)
                                      & np.isin(cols["b_type"], wanted_types))
            for rec in selected:
                code = int(cols["b_type"][rec])
                a, b = offsets[rec:rec + 2]
                x, y = lat.gx(cols["c_lon"][a:b]), lat.gy(cols["c_lat"][a:b])
                cx = int(np.floor((x.min() + x.max()) / (2 * RAW)))
                cy = int(np.floor((y.min() + y.max()) / (2 * RAW)))
                one = (x.min() >= cx * RAW and x.max() <= (cx + 1) * RAW
                       and y.min() >= cy * RAW and y.max() <= (cy + 1) * RAW)
                hits = []
                if one:
                    rx, ry = np.rint(x), np.rint(y)
                    area = float(np.sum(rx * np.roll(ry, -1) - np.roll(rx, -1) * ry))
                    if area != 0 and (cx, cy, code) in wanted:
                        hits = [(cx, cy, "a", {"rounded_area2": area})]
                else:
                    vx, vy = np.floor(x / RAW).astype(np.int64), np.floor(y / RAW).astype(np.int64)
                    fx, fy = x - vx * RAW, y - vy * RAW
                    deep = np.flatnonzero((fx >= 1) & (fx <= RAW - 1) & (fy >= 1) & (fy <= RAW - 1))
                    for v in deep:
                        target = (int(vx[v]), int(vy[v]), code)
                        if target in wanted:
                            hits.append((target[0], target[1], "b", {"vertex": int(v),
                                "global_raw": [float(x[v]), float(y[v])],
                                "cell_raw": [float(fx[v]), float(fy[v])],
                                "lat_lon": [float(cols["c_lat"][a + v]), float(cols["c_lon"][a + v])]}))
                for ix, iy, branch, trigger in hits:
                    k = (level, ix, iy, code)
                    if k not in found:
                        found[k] = {"branch": branch, "trigger": trigger,
                            "source_cell": [level, sx, sy], "background_ordinal": int(rec),
                            "spool_data": f"output/extract_timing/spool/level_{level}.data",
                            "offset": int(idx.offset[cell_ordinal]), "length": len(raw),
                            "source_cell_sha256": hashlib.sha256(raw).hexdigest(),
                            "n_coords": int(ns[rec]),
                            "bbox_global_raw": [float(x.min()), float(x.max()), float(y.min()), float(y.max())]}
                        wanted.discard((ix, iy, code))
            if not wanted:
                break
        print(f"spool level {level}: {len(wanted)} without (a)/(b) source witness", flush=True)
    reader.close()
    return found


def main():
    gdisc = SCRATCH / "G_new/ALLDATA.KWI"
    rdisc = Path("/run/media/codyh/464210-8480/ALLDATA.KWI")
    assert digest(gdisc) == G_SHA
    rawdir = SCRATCH / "dump_raw"
    manifest = json.loads((rawdir / "dump_manifest.json").read_text())
    dtype = np.dtype([(f["name"], TS[f["type"]]) for f in manifest["fields"]], align=True)
    info = manifest["kinds"]["completeness"]
    assert set(manifest["kinds"]) == {"completeness"}
    rows = np.fromfile(rawdir / info["file"], dtype=dtype)
    keys = [tuple(int(row[n]) for n in NATIVE) for row in rows]
    assert len(keys) == len(set(keys)) == info["rows"]
    k1 = json.loads((SCRATCH / "k1_full.json").read_text())
    assert len(keys) == k1["totals"]["completeness"]["failing"]
    # Missing side values are metadata, never zero/sentinel mechanism bytes.
    ext = SCRATCH / "dump_ext"
    ext.mkdir(exist_ok=True)
    shutil.copyfile(rawdir / info["file"], ext / info["file"])
    manifest["evidence_gaps"] = {"other_mechanism": "producer side tables not retained; no mechanism values fabricated"}
    save(ext / "dump_manifest.json", manifest)
    cmd = [sys.executable, "-B", "parser/tools/k1_triage.py", "classify", "--dump",
           relative(ext), "--rules", relative(OLD / "rules_other.json"), "--out",
           "output/scratch-14/classify_completeness"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (SCRATCH / "classify.stdout").write_text(proc.stdout)
    (SCRATCH / "classify.stderr").write_text(proc.stderr)
    save(SCRATCH / "classify_invocation.json", {"argv": cmd, "exit_code": proc.returncode})
    assert proc.returncode == 2 and "unknown column 'other_mechanism'" in proc.stderr, proc.stderr
    historic_text = (OLD / "rebaseline_3-17_9064.md").read_text().split("## Preserved live completeness identities", 1)[1]
    historic = {(0, int(ix), int(iy), int(code), *([0] * 7), -1, -1)
                for ix, iy, code in re.findall(r"^\| (\d+) \| (\d+) \| (\d+) \| \d+ \| \d+ \|$", historic_text, re.M)}
    with (OLD / "completeness_3-16_outcomes.tsv").open() as fh:
        added = {tuple(int(row[n]) if n != "vert" else -1 for n in NATIVE)
                 for row in csv.DictReader(fh, delimiter="\t")}
    assert len(historic) == 188 and len(added) == 89 and not historic & added
    assert historic <= set(keys) and added <= set(keys)
    sources = spool_witnesses(keys)
    readers = {"R": StrictReader(str(rdisc.parent)), "G": StrictReader(str(gdisc.parent))}
    indexes = {label: {} for label in readers}
    table = []
    for ordinal, key in enumerate(keys):
        paths, counts = {}, {}
        for label, reader in readers.items():
            witness = disc_witness(reader, indexes[label], key)
            path = SCRATCH / f"witnesses/{ordinal:04d}_{label}.json"
            save(path, witness)
            paths[label] = relative(path)
            counts[label] = witness["polygon_count"] if witness["polygon_count"] is not None else "evidence-gap"
        source = sources.get(key[:4])
        req = {"native_key": dict(zip(NATIVE, key)), "dump": relative(rawdir / info["file"]),
               "dump_row": ordinal, "byte_offset": ordinal * dtype.itemsize,
               "row_size": dtype.itemsize, "reason": int(rows[ordinal]["reason"]),
               "K1_requirement": "required cell/type; no decoded G polygon of class 2 with >=3 coordinates",
               "checker": "parser/kiwiw/_k1_cmp.c:k1_cmp_kinds", "source": source}
        if source is None:
            req["evidence-gap"] = "which source establishes the K1 requirement (centre branch not enumerated)"
        path = SCRATCH / f"witnesses/{ordinal:04d}_requirement.json"
        save(path, req)
        table.append([*key, ordinal, "evidence-gap:other_mechanism", "output/scratch-14/classify.stderr",
                      int(key in historic), int(key in added), paths["R"], counts["R"],
                      paths["G"], counts["G"], relative(path)])
    for reader in readers.values():
        reader.fh.close()
    header = [*NATIVE, "dump_row", "classify_assignment", "classify_witness", "in_historic_188", "in_added_89",
              "R_witness", "R_polygon_count", "G_witness", "G_polygon_count", "spool_K1_requirement_witness"]
    with (TRIAGE / "completeness_evidence.tsv").open("w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(table)
    totals = {"failing": len(keys), "attributed_by_rule": {r: 0 for r in ("O01", "O04", "O05", "O06", "other")},
              "unattributed_in_this_evidence_table": len(keys), "assignment_evidence_gaps": len(keys),
              "classifier_partition": "not produced: missing other_mechanism", "classify_exit": proc.returncode,
              "historic_188_present": len(historic), "added_89_present": len(added),
              "neither_historic_nor_added": len(set(keys) - historic - added),
              "source_requirement_witnesses": len(sources),
              "R_polygon_count_distribution": dict(Counter(str(r[-4]) for r in table)),
              "G_polygon_count_distribution": dict(Counter(str(r[-2]) for r in table)),
              "R_decode_gaps": sum(r[-4] == "evidence-gap" for r in table),
              "G_decode_gaps": sum(r[-2] == "evidence-gap" for r in table),
              "drift_vs_3_17_failing": len(keys) - 776,
              "unattributed_numeric_difference_vs_3_17": len(keys) - 308,
              "unattributed_numeric_difference_vs_3_15": len(keys) - 274}
    pins = {"G_disc_sha256": G_SHA, "R_disc_sha256": digest(rdisc),
            "protected_disc_sha256": digest(ROOT / "output/scratch-3-11/G_new/ALLDATA.KWI"),
            "inputs": {relative(p): digest(p) for p in (rawdir / "dump_manifest.json", rawdir / info["file"],
                OLD / "rules_other.json", OLD / "rules_bg.json", OLD / "rebaseline_3-17_9064.md",
                OLD / "completeness_3-16_outcomes.tsv", ROOT / "parser/kiwiw/_k1_cmp.c", TRIAGE / "build_evidence.py")}}
    assert digest(gdisc) == G_SHA
    save(SCRATCH / "evidence_summary.json", totals)
    save(SCRATCH / "evidence_inputs.json", pins)
    print(json.dumps(totals, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
