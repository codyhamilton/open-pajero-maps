#!/usr/bin/env python3
"""Plan 29 byte witnesses. Disc/spool subcommands require Execute's heavy guard.

No implicit run. Input discs/data are opened rb and accessed by bounded pread.
Spool indexes are streamed too: SpoolReader's whole-index loads are avoided.
Full disc hashes below are historical pins, not re-measured by this local probe.
"""
from __future__ import annotations

import argparse
import csv
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[2]
OUT = PLAN / "witnesses"
G_DISC = ROOT / "output/scratch-14/G_new/ALLDATA.KWI"
R_DISC = Path("/run/media/codyh/464210-8480/ALLDATA.KWI")
SPOOL = ROOT / "output/extract_timing/spool"
LIVE = ROOT / "output/scratch-14/p3/indep/rem01/k1_live.json"
G_PIN = "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72"
R_PIN = "8c2d20275227b9d2abb0f1802d4e0cbb6697f46545794d19e1a2024b6f169275"
MAX_READ = 64 * 1024 * 1024
CELL = [0, 541]
LAT, LON = -38.727284749, 77.51903576666666
# LAT is G's decoded anchor latitude as quoted in DESIGN; the spool stores the
# unquantised source latitude (-38.727285888405795), which lies in the same L0
# raw row. Spool identity therefore compares latitude by the shared raw row
# (|gy(lat) - G_RAW_Y| <= 0.5), not by float equality (Execute fix, Phase 1).
G_RAW_Y = 2216306


def same_raw_row(la):
    from quantisation_roundtrip import Lattice
    return abs(float(Lattice(0).gy(la)) - G_RAW_Y) <= 0.5


@lru_cache(maxsize=1)
def libs():
    sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
    from harness import walk
    from kiwiw import mesh, spool, volume
    from kiwiw.bitutils import u16, u32, sws
    from kiwiw.coordconv import decode_region_coord
    from kiwiw.name import decode_name_frame
    from quantisation_roundtrip import Lattice, PointSet
    return walk, mesh, spool, volume, u16, u32, sws, decode_region_coord, decode_name_frame, Lattice, PointSet


def sha(data):
    return hashlib.sha256(data).hexdigest()


def streamed_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load(path):
    return json.loads(Path(path).read_text())


def pread(fh, length, offset):
    if length < 0 or length > MAX_READ or offset < 0:
        raise ValueError(f"unbounded/invalid pread: offset={offset}, length={length}")
    buf = os.pread(fh.fileno(), length, offset)
    if len(buf) != length:
        raise ValueError(f"short pread at {offset}: {len(buf)} != {length}")
    return buf


def disc_cells(path, cells):
    """Read only requested blocks/leaves, keeping at most one block in memory.

    Reuses walk's divided/sparse frame geometry, including every divided leaf
    in a requested top-level slot. Aliased R frames retain each covering slot.
    """
    walk, mesh, spool, volume, u16, u32, sws, decode_xy, decode_names, Lattice, PointSet = libs()
    lattice = Lattice(0)
    with Path(path).open("rb") as fh:
        raw = pread(fh, volume.DATAVOL_SIZE, 0)
        hdr = volume.parse_volume_header(raw)
        mht = volume.parse_management_header_table(pread(fh, volume.MHT_SIZE, volume.DATAVOL_SIZE))
        prdm = mht.entries[0]
        if prdm.name:
            raise ValueError("file-based PDMDH unsupported")
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        pmoff = volume.getsector(prdm.dsa, ss, ls)
        pmraw = pread(fh, prdm.size * ls, pmoff)
        pd = volume.parse_pdmdh_full(pmraw)
        lmr = next(m for m in pd.levels if m.level == 0)
        if (lmr.grid_nx, lmr.grid_ny) != (lattice.nx, lattice.ny):
            raise ValueError("disc/reference grid mismatch")
        span = walk._lon_span(pd.coverage.lon_lo, pd.coverage.lon_hi)
        if (abs(pd.coverage.lon_lo - lattice.lon0) > 1e-9
                or abs(pd.coverage.lat_lo - lattice.lat0) > 1e-9
                or abs(span / lmr.grid_nx - lattice.cell_lon) > 1e-9
                or abs((pd.coverage.lat_hi - pd.coverage.lat_lo) / lmr.grid_ny - lattice.cell_lat) > 1e-9):
            raise ValueError("disc/reference coverage mismatch")
        npc_x, npc_y = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]
        nbx, nby = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
        nbsx = 1 + lmr.n_blocksets_lng
        cached = None
        for ix, iy in cells:
            result = {"cell": [ix, iy], "status": "outside_coverage", "frames": []}
            if not (0 <= ix < lmr.grid_nx and 0 <= iy < lmr.grid_ny):
                yield result
                continue
            bx, lx = divmod(ix, npc_x)
            by, ly = divmod(iy, npc_y)
            bsx, blx = divmod(bx, nbx)
            bsy, bly = divmod(by, nby)
            bsi, bi = bsy * nbsx + bsx, bly * nbx + blx
            slot = ly * npc_x + lx
            result.update(status="empty_slot", blockset=bsi, block=bi,
                          block_cells=[bx * npc_x, (bx + 1) * npc_x - 1,
                                       by * npc_y, (by + 1) * npc_y - 1])
            ordinal = next((i for i, bs in enumerate(pd.blocksets)
                            if bs.level == 0 and bs.blockset_index == bsi), None)
            table = next((t for t in pd.bmt_tables if t.blockset_ordinal == ordinal), None)
            if table is None:
                yield result
                continue
            entry = table.entries[bi]
            if entry.dsa == 0xFFFFFFFF or not entry.size:
                yield result
                continue
            if cached != (bsi, bi):
                from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
                root = parse_parcel_mgmt_record(pread(fh, entry.size * ls,
                                                     volume.getsector(entry.dsa, ss, ls)), lmr)
                bb = walk._block_base_bounds(pd, lmr, bsx, bsy, blx, bly)
                cached = (bsi, bi)
            cache = {}
            for leaf_path, leaf, lb, ptype in walk._iter_tree_leaves(root, bb, lmr, ()):
                if leaf_path[0] != slot:
                    continue
                fb, fc = walk._leaf_frame(root, 0, ptype, leaf_path, lb, bb, lmr, cache)
                rng = mesh.leaf_frame_range(0, ptype, leaf_path, fc)
                bounds = walk.with_range(fb, rng)
                off, length = volume.getsector(leaf.dsa, ss, ls), leaf.size * ls
                frame = pread(fh, length, off)
                # Only name subframe is relevant; do not decode roads/backgrounds.
                de = 36 + u16(frame, 34) * 4 + 12
                no, nl = u32(frame, de), u16(frame, de + 4)
                names = []
                if no != 0xFFFFFFFF and nl:
                    no, nl = sws(no), sws(nl)
                    if no + nl > len(frame):
                        raise ValueError("name subframe extends past map frame")
                    for rec in decode_names(frame[no:no + nl], bounds).records:
                        rb = rec.raw_bytes
                        st = rec.string_type
                        if st in (1, 5, 6):
                            tlen_at, text_at = (12, 14) if st == 1 else (14, 16)
                        elif st == 4:
                            tlen_at = 10 + (u16(rb, 6) & 15) * 2
                            text_at = tlen_at + 2
                        else:
                            raise ValueError(f"unhandled string bytes for type {st}")
                        text = rb[text_at:text_at + u16(rb, tlen_at) * 2]
                        if text_at + u16(rb, tlen_at) * 2 > len(rb):
                            raise ValueError("name text extends past record")
                        rawxy = None if st == 4 else [decode_xy(u16(rb, 8)), decode_xy(u16(rb, 10))]
                        globalxy = None if rec.lat is None else [float(lattice.gx(rec.lon)), float(lattice.gy(rec.lat))]
                        names.append({"string_type": st, "class": rec.type_code,
                                      "type_code": rec.type_code, "text": rec.text,
                                      "string_hex": text.split(b"\0", 1)[0].hex(),
                                      "stored_string_hex": text.hex(), "string_encoding": "latin-1",
                                      "raw": rawxy, "global_raw": globalxy,
                                      "lat": rec.lat, "lon": rec.lon,
                                      "record_offset": off + no + rec.raw_offset,
                                      "record_length": len(rb), "record_hex": rb.hex(), "record_sha256": sha(rb)})
                result["frames"].append({"leaf_path": list(leaf_path), "offset": off,
                                         "length": length, "sha256": sha(frame),
                                         "frame_class": fc, "range": rng,
                                         "bounds": vars(fb), "names": names})
            result["status"] = "resolved" if result["frames"] else "empty_slot"
            yield result


def g_witness(args):
    live = load(args.live)
    failures = [r for v in live["levels"].values() for r in v["failures"] if r["kind"] == "name_anchor"]
    cell = next(disc_cells(args.disc, [CELL]))
    candidates = [{"frame": f, "name": n} for f in cell["frames"] for n in f["names"]
                  if n["raw"] == [0, 370]]
    target = candidates[0] if len(candidates) == 1 else None
    drift = []
    if live["totals"]["name_anchor"]["failing"] != 1 or len(failures) != 1:
        drift.append("live name_anchor failure count/sample differs from one")
    elif (failures[0]["cell"] != CELL or failures[0]["leaf_path"] != [928]
          or failures[0]["vertex"]["raw"] != [0, 370]
          or failures[0]["reason"] != "no spool record within half a raw unit"
          or abs(failures[0]["vertex"]["lat"] - LAT) > 1e-9
          or failures[0]["vertex"]["lon"] != 90):
        drift.append("saved live failing item differs from Decision 4")
    if target is None:
        drift.append("G does not have exactly one name at raw (0,370)")
    elif (target["frame"]["leaf_path"] != [928]
          or target["name"]["string_type"] != 6 or target["name"]["class"] != 288
          or abs(target["name"]["lat"] - LAT) > 1e-9 or target["name"]["lon"] != 90):
        drift.append("decoded G item differs from Decision 4")
    write_json(args.out, {"schema": 1, "disc": str(args.disc), "historical_disc_sha256": G_PIN,
                          "full_pin_remeasured": False, "live_report": str(args.live),
                          "live_report_sha256": sha(Path(args.live).read_bytes()),
                          "live_total": live["totals"]["name_anchor"], "failures": failures,
                          "cell": cell, "target": target, "drift": drift})


def index_rows(path):
    """The spool index is four parallel arrays after its 48-byte header."""
    with Path(path).open("rb") as fh:
        head = pread(fh, 48, 0)
        if head[:8] != b"KWSPIDX1":
            raise ValueError("not a binary spool index")
        n = struct.unpack_from("<Q", head, 8)[0]
        if os.fstat(fh.fileno()).st_size != 48 + n * 24:
            raise ValueError("spool index size mismatch")
        for start in range(0, n, 4096):
            size = min(4096, n - start)
            arrays = [struct.unpack(f"<{size}{fmt}", pread(fh, size * width, 48 + base * n + width * start))
                      for base, width, fmt in ((0, 4, "i"), (4, 4, "i"), (8, 8, "Q"), (16, 8, "Q"))]
            yield from zip(*arrays)


def name_columns(fh, off, length):
    """Skip non-name columns; read one cell's name columns, bounded by MAX_READ."""
    _, _, spool, *_ = libs()
    import numpy as np
    counts = dict(zip(spool._COUNT_KEYS, struct.unpack("<9Q", pread(fh, 72, off))))
    pos, cols, offsets = off + 72, {}, {}
    for key, dt, countkey in spool._COLUMNS:
        size = counts[countkey] * np.dtype(dt).itemsize
        if pos + size > off + length:
            raise ValueError("spool column outside cell record")
        if key.startswith("s_") or key.startswith("blob_name_"):
            offsets[key] = pos
            cols[key] = np.frombuffer(pread(fh, size, pos), dtype=dt)
        pos += size + spool._pad8(size)
    if pos != off + length:
        raise ValueError("spool cell layout/length mismatch")
    return cols, offsets


def name_identity(cols, offsets, i):
    """A columnar name has disjoint on-file segments, never a synthetic record."""
    segments, values = [], {}
    for key, col in cols.items():
        if not key.startswith("s_"):
            continue
        raw = col[i:i + 1].tobytes()
        segments.append({"column": key, "offset": offsets[key] + i * col.dtype.itemsize,
                         "length": len(raw), "hex": raw.hex()})
        values[key] = col[i].item()
    for kind in ("label", "text"):
        lengths = cols[f"s_{kind}_len"]
        start = int(lengths[:i].sum())
        size = int(lengths[i])
        key = f"blob_name_{kind}"
        raw = cols[key][start:start + size].tobytes()
        if len(raw) != size or start < 0 or size < 0:
            raise ValueError("invalid spool name blob extent")
        segments.append({"column": key, "offset": offsets[key] + start, "length": size, "hex": raw.hex()})
        values[kind] = raw.decode("utf-8")
        values[f"{kind}_hex"] = raw.hex()
    joined = b"".join(bytes.fromhex(s["hex"]) for s in segments)
    return {"record": i, "lat": values["s_lat"] if values["s_present"] & 1 else None,
            "lon": values["s_lon"] if values["s_present"] & 2 else None,
            "string_type": values["s_type"], "type_code": values["s_code"],
            "text": values["text"], "string_hex": values["text_hex"],
            "string_encoding": "utf-8", "encoder_string_hex": values["text"].encode("latin-1", errors="replace").split(b"\0", 1)[0].hex(),
            "columns": values, "segments": segments, "record_hex": joined.hex(),
            "record_length": len(joined), "record_sha256": sha(joined),
            "byte_layout": "concatenated on-file scalar columns then label/text; offsets in segments"}


def spool_witness(args):
    _, mesh, _, _, _, _, _, _, _, Lattice, PointSet = libs()
    g = load(args.g)
    if g["target"] is None:
        raise ValueError("G target unresolved; inspect drift before spool witness")
    lat = Lattice(0)
    anchor = g["target"]["name"]
    query = [round(x) for x in anchor["global_raw"]]
    c0, c1, r0, r1 = g["cell"]["block_cells"]
    target, nearest, bucket = None, math.inf, math.inf
    cells_read = names_checked = 0
    with (Path(args.spool) / "level_0.data").open("rb") as fh:
        for ix, iy, off, length in index_rows(Path(args.spool) / "level_0.idx"):
            if not (c0 - 1 <= ix <= c1 + 1 and r0 - 1 <= iy <= r1 + 1):
                continue
            cols, offsets = name_columns(fh, off, length)
            cells_read += 1
            present = (cols["s_present"] & 3) == 3
            xs, ys = lat.gx(cols["s_lon"][present]), lat.gy(cols["s_lat"][present])
            names_checked += len(xs)
            for x, y in zip(xs, ys):
                nearest = min(nearest, max(abs(float(x) - query[0]), abs(float(y) - query[1])))
            bucket = min(bucket, float(PointSet(xs, ys).nearest([query[0]], [query[1]])[0]))
            if [ix, iy] == CELL and len(cols["s_type"]):
                target = name_identity(cols, offsets, 0)
                target.update(level=0, cell=CELL, cell_offset=off, cell_length=length,
                              cell_sha256=sha(pread(fh, length, off)))
    drift = []
    if target is None:
        drift.append("spool name record 0 missing")
    else:
        target["source_distance_raw"] = (None if target["lat"] is None or target["lon"] is None else
                                          max(abs(float(lat.gx(target["lon"])) - query[0]),
                                              abs(float(lat.gy(target["lat"])) - query[1])))
        if (not same_raw_row(target["lat"]) or target["lon"] != LON or target["type_code"] != 288
                or target["string_type"] != 6 or target["encoder_string_hex"] != anchor["string_hex"]):
            drift.append("spool identity differs from Decision 4/G string")
    from osm_to_parcel_geometry import TileGrid, assign_to_parcel
    assigned = assign_to_parcel(LAT, LON, TileGrid.from_reference(0))
    twin = mesh.assign_to_parcel(LAT, LON, mesh.CellGrid.from_reference(0))
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", "34a04cc", "16e2931"], cwd=ROOT).returncode
    write_json(args.out, {"schema": 1, "spool": str(args.spool), "target": target, "drift": drift,
                          "spool_extractor_tree": "34a04cc", "provenance_source": "docs/plans/14-completeness-root-cause.md and docs/provenance.md spool recovery",
                          "ancestor_exit": ancestor, "tip_assignment": assigned, "mesh_assignment": twin,
                          "region_block_cells": [c0, c1, r0, r1], "region_cells_read": cells_read,
                          "region_names_checked": names_checked, "k1_query_global_raw": query,
                          "nearest_distance_raw": nearest if math.isfinite(nearest) else None,
                          "k1_bucket_distance_raw": bucket if math.isfinite(bucket) else None,
                          "k1_bucket_result": "finite" if math.isfinite(bucket) else "inf (saved K1 error_raw null)",
                          "tolerance_raw": 0.5, "halo_eligible": g["target"]["frame"]["range"] < 4096})


def r_witness(args):
    g = load(args.g)
    if g["target"] is None:
        raise ValueError("G target unresolved; inspect drift")
    want = g["target"]["name"]["string_hex"]
    cells, matches = [], []
    for row in disc_cells(args.disc, [(x, y) for y in range(540, 543) for x in (-1, 0, 1)]):
        for f in row["frames"]:
            f["name_count"] = len(f["names"])
            for n in f["names"]:
                if n["string_hex"] == want:
                    matches.append({"cell": row["cell"], "leaf_path": f["leaf_path"],
                                    "frame_offset": f["offset"], "name": n})
            del f["names"]
        cells.append(row)
    write_json(args.out, {"schema": 1, "disc": str(args.disc), "historical_disc_sha256": R_PIN,
                          "full_pin_remeasured": False, "string_hex": want, "cells": cells,
                          "matches": matches, "match_result": "matches" if matches else "none"})


def spool_scan(args):
    _, mesh, *_ = libs()
    total = rejected = absent = expected_count = 0
    per_level = {}
    extras = Path(args.extras)
    extras.parent.mkdir(parents=True, exist_ok=True)
    with extras.open("w", newline="") as out:
        writer = csv.writer(out, delimiter="\t")
        writer.writerow(["level", "ix", "iy", "record", "lat", "lon", "type_code", "string_type", "string_hex", "text", "record_sha256", "expected_O03"])
        for idxpath in sorted(Path(args.spool).glob("level_*.idx"), key=lambda p: int(p.stem.split("_")[1])):
            level = int(idxpath.stem.split("_")[1])
            grid = mesh.CellGrid.from_reference(level)
            counts = {"checked": 0, "rejected": 0, "without_anchor": 0}
            with idxpath.with_suffix(".data").open("rb") as fh:
                for ix, iy, off, length in index_rows(idxpath):
                    cols, offsets = name_columns(fh, off, length)
                    for i in range(len(cols["s_type"])):
                        if cols["s_present"][i] & 3 != 3:
                            counts["without_anchor"] += 1
                            continue
                        counts["checked"] += 1
                        la, lo = float(cols["s_lat"][i]), float(cols["s_lon"][i])
                        if mesh.assign_to_parcel(la, lo, grid) is None:
                            counts["rejected"] += 1
                            n = name_identity(cols, offsets, i)
                            expected = level == 0 and [ix, iy] == CELL and i == 0 and same_raw_row(la) and lo == LON and n["type_code"] == 288 and n["string_type"] == 6
                            expected_count += int(expected)
                            writer.writerow([level, ix, iy, i, la, lo, n["type_code"], n["string_type"], n["string_hex"], n["text"], n["record_sha256"], int(expected)])
            per_level[str(level)] = counts
            total += counts["checked"]
            rejected += counts["rejected"]
            absent += counts["without_anchor"]
    if not per_level:
        raise ValueError("no spool index levels found")
    write_json(args.out, {"schema": 1, "spool": str(args.spool), "checked": total,
                          "rejected": rejected, "without_anchor": absent, "per_level": per_level,
                          "expected_O03_rejected": expected_count, "extra_rejected": rejected - expected_count,
                          "rejects_tsv": str(extras), "rejects_tsv_sha256": streamed_sha(extras)})


def verdict(args):
    g, s, r, scan = [load(p) for p in (args.g, args.spool_json, args.r, args.scan)]
    drift = g["drift"] + s["drift"]
    if g["target"] is None or s["target"] is None:
        drift.append("missing target; A/B cannot be established")
    if r["string_hex"] != (g["target"]["name"]["string_hex"] if g["target"] else None):
        drift.append("R search string differs from G")
    expected_cells = {(x, y) for y in range(540, 543) for x in (-1, 0, 1)}
    if {tuple(c["cell"]) for c in r["cells"]} != expected_cells:
        drift.append("R did not cover the nine required cells")
    if any(c["status"] not in ("resolved", "empty_slot", "outside_coverage")
           or (c["status"] == "outside_coverage" and c["cell"][0] != -1) for c in r["cells"]):
        drift.append("R coverage status unresolved")
    hits = []
    if not drift:
        n = g["target"]["name"]
        hits = [m for m in r["matches"] if m["name"]["string_hex"] == n["string_hex"]
                and m["name"]["global_raw"] is not None
                and max(abs(a - b) for a, b in zip(m["name"]["global_raw"], n["global_raw"])) <= 0.5]
    result = "drift" if drift else "B" if hits else "A"
    concerns = []
    if scan["rejected"] != 1:
        concerns.append(f"whole-spool rejected count {scan['rejected']} differs from expected 1; inspect rejects TSV")
    if scan["expected_O03_rejected"] != 1 or scan["extra_rejected"]:
        concerns.append("whole-spool rejects do not consist of the single pinned O03 identity")
    if s["ancestor_exit"] != 0 or s["tip_assignment"] is not None or s["mesh_assignment"] is not None:
        concerns.append("plan-18 assignment/provenance check differs from DESIGN")
    if s["k1_bucket_distance_raw"] is not None and s["k1_bucket_distance_raw"] <= 0.500001:
        concerns.append("bounded K1 name query passes; saved failure requires investigation")
    full_record_equal = any(m["name"].get("record_hex") == g["target"]["name"].get("record_hex")
                            and m["name"].get("record_hex") is not None for m in hits)
    if result == "B" and not full_record_equal:
        concerns.append("B proves string/position parity, but full name-record bytes differ; inspect R/G records before Phase 2's byte-equality claim")
    record = {"schema": 1, "verdict": result, "criterion": "byte-equal string at Chebyshev distance <= 0.5 in the shared L0 raw lattice",
              "position_matches": hits, "drift": drift, "concerns": concerns,
              "full_name_record_byte_equal": full_record_equal,
              "scan_rejected": scan["rejected"], "phase1_ready": not drift and not concerns}
    write_json(args.out, record)
    lines = ["# Phase 1 name_anchor byte witness", "", f"Verdict: **{result}**.", ""]
    if result == "A":
        lines += ["R lacks the byte-equal G string at G's position within ±0.5 raw per axis. G≠R for this item; the pinned O03 stale-spool clamp is the root cause.", ""]
    elif result == "B":
        lines += ["R carries the byte-equal string at G's position within ±0.5 raw per axis. G==R for this name and anchor. Plan 18 would drop an R-present name on a future extract: a conflict finding for Design.", ""]
    else:
        lines += ["The Decision 4 premise drifted; no A/B verdict is forced.", ""]
    if g["target"] and s["target"]:
        f, n, sn = g["target"]["frame"], g["target"]["name"], s["target"]
        lines += [f"G historical disc pin `{g['historical_disc_sha256']}`; frame leaf `{f['leaf_path']}`, offset {f['offset']}, length {f['length']}, sha256 `{f['sha256']}`.", "",
                  f"G name `{n['text']}`; string hex `{n['string_hex']}` (latin-1), stored hex `{n['stored_string_hex']}`; string_type {n['string_type']}, class {n['class']}, raw {n['raw']}, lat/lon {n['lat']}/{n['lon']}. Record offset {n['record_offset']}, length {n['record_length']}, sha256 `{n['record_sha256']}`.", "",
                  f"Spool L0 {sn['cell']} record {sn['record']}: lat/lon {sn['lat']}/{sn['lon']}, UTF-8 string hex `{sn['string_hex']}`. Record-column bytes sha256 `{sn['record_sha256']}`; exact offsets/hex are in spool.json. Its columnar layout has no single contiguous name-record extent. Cell offset {sn['cell_offset']}, length {sn['cell_length']}, sha256 `{sn['cell_sha256']}`.", "",
                  f"Source-anchor distance {sn['source_distance_raw']} raw. Region nearest distance {s['nearest_distance_raw']}; K1 bucket result {s['k1_bucket_result']}, tolerance 0.5 raw; halo eligible {s['halo_eligible']}. The saved live report has name_anchor totals {g['live_total']} and failure samples {g['failures']}.", ""]
    lines += [f"R historical disc pin `{r['historical_disc_sha256']}`. Full disc pins are cited from prior evidence, not re-hashed by this bounded witness. All nine requested cells follow; ix=-1 is outside coverage.", "", "| Cell | Status | Covering frames (offset / length / sha256) |", "| --- | --- | --- |"]
    for c in r["cells"]:
        frames = "; ".join(f"{f['leaf_path']}: {f['offset']} / {f['length']} / `{f['sha256']}`" for f in c["frames"]) or "none"
        lines.append(f"| {c['cell']} | {c['status']} | {frames} |")
    lines += ["", f"R byte-equal names: {r['match_result']} ({len(r['matches'])} covering-slot observations, including aliases). Full name-record byte equality at the matching position: {full_record_equal}."]
    for m in r["matches"]:
        lines.append(f"- Cell {m['cell']} leaf {m['leaf_path']}: frame raw {m['name']['raw']}, global raw {m['name']['global_raw']}; record sha256 `{m['name']['record_sha256']}`.")
    lines += ["", f"Tip extractor assignment → {s['tip_assignment']}; mesh twin → {s['mesh_assignment']}. Existing controls: parser/tests/test_name_anchor_o03_extractor.py, test_parcel_geometry.py:119, test_descriptor.py:47.", "",
              f"Spool extractor provenance `{s['spool_extractor_tree']}` is recorded in plan 14's recovery and docs/provenance.md, not stored intrinsically in the spool. `git merge-base --is-ancestor 34a04cc 16e2931` exit {s['ancestor_exit']}.", "",
              f"Whole-spool anchored names checked {scan['checked']}; plan-18-rejectable {scan['rejected']}; without anchors {scan['without_anchor']}. Per-level counts: `{json.dumps(scan['per_level'], sort_keys=True)}`. Every reject, including any extras, is listed in `{scan['rejects_tsv']}`.", "",
              "Heavy runs use parser/tools/run_heavy_python.py and its output/.heavy.lock. No disc/spool/encoder/checker/rule change or K1 re-run is part of Phase 1."]
    lines += ["", "Drift: " + ("; ".join(drift) or "none"), "", "Concerns: " + ("; ".join(concerns) or "none"), ""]
    Path(args.note).parent.mkdir(parents=True, exist_ok=True)
    Path(args.note).write_text("\n".join(lines))
    print(json.dumps(record, sort_keys=True))
    return 2 if drift else 1 if concerns else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("g-witness", help="bounded G frame/name witness")
    p.add_argument("--disc", type=Path, default=G_DISC)
    p.add_argument("--live", type=Path, default=LIVE)
    p.add_argument("--out", type=Path, default=OUT / "g.json")
    p.set_defaults(run=g_witness)
    p = sub.add_parser("spool-witness", help="record 0 bytes and bounded K1 block-region nearest query")
    p.add_argument("--spool", type=Path, default=SPOOL)
    p.add_argument("--g", type=Path, default=OUT / "g.json")
    p.add_argument("--out", type=Path, default=OUT / "spool.json")
    p.set_defaults(run=spool_witness)
    p = sub.add_parser("r-witness", help="bounded R covering leaves in nine-cell neighbourhood")
    p.add_argument("--disc", type=Path, default=R_DISC)
    p.add_argument("--g", type=Path, default=OUT / "g.json")
    p.add_argument("--out", type=Path, default=OUT / "r.json")
    p.set_defaults(run=r_witness)
    p = sub.add_parser("spool-scan", help="stream all levels; count coverage-rejected names and list each")
    p.add_argument("--spool", type=Path, default=SPOOL)
    p.add_argument("--out", type=Path, default=OUT / "scan.json")
    p.add_argument("--extras", type=Path, default=OUT / "scan_rejects.tsv")
    p.set_defaults(run=spool_scan)
    p = sub.add_parser("verdict", help="light JSON-only A/B verdict and generated note")
    p.add_argument("--g", type=Path, default=OUT / "g.json")
    p.add_argument("--spool-json", type=Path, default=OUT / "spool.json")
    p.add_argument("--r", type=Path, default=OUT / "r.json")
    p.add_argument("--scan", type=Path, default=OUT / "scan.json")
    p.add_argument("--out", type=Path, default=OUT / "verdict.json")
    p.add_argument("--note", type=Path, default=PLAN / "phase1_witness.md")
    p.set_defaults(run=verdict)
    args = parser.parse_args(argv)
    return args.run(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
