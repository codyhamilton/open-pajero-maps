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
ROOT = PLAN.parents[4]
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


def byte_evidence(data, offset):
    return {"offset": offset, "length": len(data), "hex": data.hex(), "sha256": sha(data)}


def evidence_bytes(proof):
    raw = bytes.fromhex(proof["hex"])
    if (proof["offset"] < 0 or len(raw) != proof["length"]
            or not raw or sha(raw) != proof["sha256"]):
        raise ValueError("invalid byte evidence")
    return raw


def index_lookup(read, cell):
    """Resolve one cell, retaining the exact bounded reads for offline replay.

    Only NO_DATA_DSA (FFFFFFFF) proves an absent block/parcel. A zero-size
    non-sentinel BMT entry is unresolved; a zero-size non-sentinel mapinfo
    entry is a subrecord pointer, never absence. An absent BMT requires the
    documented raw FFFFFFFF offset AND zero size (volume.py's full reader).
    """
    walk, _, _, volume, u16, u32, sws, _, _, Lattice, _ = libs()
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    result = {"cell": list(cell), "status": "lookup_failed", "frames": [],
              "index_evidence": {"reads": []}}
    evidence = result["index_evidence"]

    def capture(length, offset):
        raw = read(length, offset)
        if len(raw) != length:
            raise ValueError(f"short index read at {offset}")
        evidence["reads"].append(byte_evidence(raw, offset))
        return raw

    try:
        hdr = volume.parse_volume_header(capture(volume.DATAVOL_SIZE, 0))
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        if ss <= 0 or ls <= 0:
            raise ValueError("invalid sector sizes")
        mhr = capture(volume.MHR_SIZE, volume.DATAVOL_SIZE)
        prdm = volume.MhrEntry(0, u32(mhr, 0), u16(mhr, 4),
                               mhr[6:18].split(b"\0", 1)[0].decode("latin-1"))
        if prdm.name or prdm.dsa == 0xFFFFFFFF or not prdm.size:
            raise ValueError("missing/invalid embedded PDMDH lookup")
        pmoff, pmlen = volume.getsector(prdm.dsa, ss, ls), prdm.size * ls
        if pmlen < 30 or pmlen > MAX_READ:
            raise ValueError("invalid PDMDH buffer extent")
        head = capture(30, pmoff)
        lmr_size, n_lmr, n_bsmr = sws(u16(head, 20)), u16(head, 26), u16(head, 28)
        if (lmr_size < volume.LMR_BASE_SIZE or u16(head, 22) * 2 != volume.BSMR_SIZE
                or u16(head, 24) * 2 != volume.BMT_SIZE):
            raise ValueError("invalid LMR/BSMR/BMT record sizes")
        directory_size = 30 + lmr_size * n_lmr + volume.BSMR_SIZE * n_bsmr
        if directory_size > pmlen:
            raise ValueError("LMR/BSMR directory outside PDMDH buffer")
        directory = capture(directory_size, pmoff)
        pd = volume.parse_pdmdh(directory)
        levels = [(i, m) for i, m in enumerate(pd.levels) if m.level == 0]
        if len(levels) != 1:
            raise ValueError("missing/ambiguous L0 lookup")
        li, lmr = levels[0]
        lattice = Lattice(0)
        span = walk._lon_span(pd.coverage.lon_lo, pd.coverage.lon_hi)
        if ((lmr.grid_nx, lmr.grid_ny) != (lattice.nx, lattice.ny)
                or abs(pd.coverage.lon_lo - lattice.lon0) > 1e-9
                or abs(pd.coverage.lat_lo - lattice.lat0) > 1e-9
                or abs(span / lmr.grid_nx - lattice.cell_lon) > 1e-9
                or abs((pd.coverage.lat_hi - pd.coverage.lat_lo) / lmr.grid_ny - lattice.cell_lat) > 1e-9):
            raise ValueError("disc/reference coverage or grid mismatch")
        evidence["pdmdh"] = {"offset": pmoff, "length": pmlen, "dsa": prdm.dsa,
                               "size": prdm.size, "sector_size": ss, "logical_sector_size": ls}
        evidence["lmr"] = byte_evidence(directory[30 + li * lmr_size:30 + (li + 1) * lmr_size],
                                        pmoff + 30 + li * lmr_size)
        ix, iy = cell
        result["geometry"] = {"level": 0, "grid": [lmr.grid_nx, lmr.grid_ny],
                              "coverage": vars(pd.coverage),
                              "in_coverage": 0 <= ix < lmr.grid_nx and 0 <= iy < lmr.grid_ny}
        if not result["geometry"]["in_coverage"]:
            result.update(status="outside_coverage", reason="cell_outside_L0_grid")
            return result, None
        npc_x, npc_y = 1 + lmr.n_parcels_lng[0], 1 + lmr.n_parcels_lat[0]
        nbx, nby = 1 + lmr.n_blocks_lng, 1 + lmr.n_blocks_lat
        bx, lx = divmod(ix, npc_x)
        by, ly = divmod(iy, npc_y)
        bsx, blx = divmod(bx, nbx)
        bsy, bly = divmod(by, nby)
        bsi, bi = bsy * (1 + lmr.n_blocksets_lng) + bsx, bly * nbx + blx
        slot = ly * npc_x + lx
        result.update(blockset=bsi, block=bi, slot=slot,
                      block_cells=[bx * npc_x, (bx + 1) * npc_x - 1,
                                   by * npc_y, (by + 1) * npc_y - 1])
        selected = [(i, bs) for i, bs in enumerate(pd.blocksets)
                    if bs.level == 0 and bs.blockset_index == bsi]
        if len(selected) != 1:
            raise ValueError("missing/ambiguous blockset lookup")
        ordinal, bs = selected[0]
        bs_at = pd.bsmr_table_offset + ordinal * volume.BSMR_SIZE
        bsraw = directory[bs_at:bs_at + volume.BSMR_SIZE]
        evidence["blockset"] = {**byte_evidence(bsraw, pmoff + bs_at), "ordinal": ordinal,
                                  "level": bs.level, "blockset_index": bs.blockset_index,
                                  "bmt_offset": bs.bmt_offset, "bmt_size": bs.bmt_size}
        if u32(bsraw, 2) == 0xFFFFFFFF and bs.bmt_size == 0:
            result.update(status="empty_slot", reason="absent_BMT_sentinel")
            return result, None
        if (bs.bmt_offset < directory_size or bs.bmt_size != nbx * nby * volume.BMT_SIZE
                or bs.bmt_offset + bs.bmt_size > pmlen):
            raise ValueError("invalid BMT table offset/extent")
        eraw = capture(volume.BMT_SIZE, pmoff + bs.bmt_offset + bi * volume.BMT_SIZE)
        dsa, size = u32(eraw, 0), u16(eraw, 4)
        evidence["bmt_entry"] = {**byte_evidence(eraw, pmoff + bs.bmt_offset + bi * volume.BMT_SIZE),
                                 "dsa": dsa, "size": size}
        if dsa == 0xFFFFFFFF:
            result.update(status="empty_slot", reason="absent_block_DSA_sentinel")
            return result, None
        if not size:
            raise ValueError("non-sentinel block DSA has zero size")
        blockoff = volume.getsector(dsa, ss, ls)
        blockraw = capture(size * ls, blockoff)
        evidence["slot_table"] = byte_evidence(blockraw, blockoff)
        slot_at = 4 + slot * 6
        if slot_at + 6 <= len(blockraw):
            slotraw = blockraw[slot_at:slot_at + 6]
            evidence["requested_slot"] = {**byte_evidence(slotraw, blockoff + slot_at),
                                          "path": [slot], "dsa": u32(slotraw, 0),
                                          "size": u16(slotraw, 4)}
        root = parse_parcel_mgmt_record(blockraw, lmr)
        if root.parcel_type != 0:
            raise ValueError("top-level slot table is not normal parcel type")
        evidence["slots"] = []

        def retain(rec, indices, path):
            for i in indices:
                entry = rec.entries[i]
                at = rec.offset + 4 + i * 6
                evidence["slots"].append({**byte_evidence(blockraw[at:at + 6], blockoff + at),
                                          "path": list(path + (i,)), "dsa": entry.dsa,
                                          "size": entry.size, "record_offset": blockoff + rec.offset,
                                          "parcel_type": rec.parcel_type})
                if entry.subrecord is not None:
                    retain(entry.subrecord, range(len(entry.subrecord.entries)), path + (i,))
        retain(root, [slot], ())
        bb = walk._block_base_bounds(pd, lmr, bsx, bsy, blx, bly)
        leaves = [item for item in walk._iter_tree_leaves(root, bb, lmr, ()) if item[0][0] == slot]
        if not leaves:
            # Every terminal must positively carry NO_DATA_DSA, including
            # divided trees. A parser omission is not an absence proof.
            parents = {tuple(s["path"][:-1]) for s in evidence["slots"]}
            terminals = [s for s in evidence["slots"] if tuple(s["path"]) not in parents]
            if not terminals or any(s["dsa"] != 0xFFFFFFFF for s in terminals):
                raise ValueError("no leaf without terminal sentinel proof")
            result.update(status="empty_slot", reason="parcel_tree_DSA_sentinels")
            return result, None
        result.update(status="resolved", reason="indexed_leaf_frames")
        return result, (root, bb, lmr, leaves, ss, ls)
    except (ValueError, IndexError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
        result.update(status="lookup_failed", reason=f"{type(exc).__name__}: {exc}")
        return result, None


def validate_cell_evidence(row):
    """Replay a cell's index lookup using only its retained bytes, never a disc."""
    try:
        reads = row["index_evidence"]["reads"]
        by_extent = {}
        for proof in reads:
            key = (proof["length"], proof["offset"])
            raw = evidence_bytes(proof)
            if key in by_extent and by_extent[key] != raw:
                raise ValueError("conflicting index bytes")
            by_extent[key] = raw
        replay, context = index_lookup(lambda n, at: by_extent[(n, at)], row["cell"])
        if replay["status"] == "lookup_failed":
            raise ValueError(replay["reason"])
        for key in ("status", "reason", "geometry", "blockset", "block", "slot", "block_cells", "index_evidence"):
            if replay.get(key) != row.get(key):
                raise ValueError(f"index proof differs at {key}")
        if context is None:
            if row["frames"]:
                raise ValueError("absent/outside cell contains frames")
        else:
            root, bb, lmr, leaves, ss, ls = context
            walk, mesh, _, volume, u16, u32, sws, _, decode_names, *_ = libs()
            if len(row["frames"]) != len(leaves):
                raise ValueError("indexed leaves missing from resolved frames")
            cache = {}
            for frame, (path, leaf, lb, ptype) in zip(row["frames"], leaves):
                fb, fc = walk._leaf_frame(root, 0, ptype, path, lb, bb, lmr, cache)
                rng = mesh.leaf_frame_range(0, ptype, path, fc)
                off, length = volume.getsector(leaf.dsa, ss, ls), leaf.size * ls
                if (frame["leaf_path"] != list(path) or frame["offset"] != off
                        or frame["length"] != length or frame["bounds"] != vars(fb)
                        or frame["range"] != rng or frame["frame_class"] != fc
                        or len(bytes.fromhex(frame["sha256"])) != 32):
                    raise ValueError("resolved frame identity differs from index")
                directory = evidence_bytes(frame["name_directory"])
                if (not 54 <= len(directory) <= length or frame["name_directory"]["offset"] != off
                        or len(directory) != 54 + u16(directory, 34) * 4):
                    raise ValueError("invalid name directory proof")
                de = 36 + u16(directory, 34) * 4 + 12
                no, nl = u32(directory, de), u16(directory, de + 4)
                if no == 0xFFFFFFFF:
                    records = []
                elif not nl:
                    raise ValueError("non-sentinel name directory has zero size")
                else:
                    no, nl = sws(no), sws(nl)
                    sub = frame["name_subframe"]
                    if sub["offset"] != off + no or sub["length"] != nl or no < len(directory) or no + nl > length:
                        raise ValueError("invalid name subframe extent")
                    records = decode_proven_names(evidence_bytes(sub), walk.with_range(fb, rng)).records
                strings = [name_record_string(rec.raw_bytes, rec.string_type).hex() for rec in records]
                if strings != frame["name_string_hex"] or len(strings) != frame["name_count"]:
                    raise ValueError("decoded name census differs from byte proof")
        return None
    except (ValueError, IndexError, KeyError, TypeError, struct.error, AssertionError) as exc:
        return f"{type(exc).__name__}: {exc}"


def decode_proven_names(raw, bounds):
    """Reject truncated/invalid lists before trusting the permissive decoder."""
    _, _, _, _, u16, _, sws, _, decode_names, *_ = libs()
    header_size = sws(u16(raw, 0))
    if header_size < 2 or header_size > len(raw) or (header_size - 2) % 4:
        raise ValueError("invalid name list directory extent")
    for at in range(2, header_size, 4):
        start, count = sws(u16(raw, at)), u16(raw, at + 2)
        if start == 0xFFFF:
            continue
        if start < header_size or start > len(raw):
            raise ValueError("name list offset outside subframe")
        for _ in range(count):
            length = sws(u16(raw, start) & 0xFFF)
            if length < 6 or start + length > len(raw):
                raise ValueError("name record extent outside subframe")
            start += length
    decoded = decode_names(raw, bounds)
    for rec in decoded.records:
        name_record_string(rec.raw_bytes, rec.string_type)
    return decoded


def name_record_string(rb, st):
    u16 = libs()[4]
    if st in (1, 5, 6):
        tlen_at, text_at = (12, 14) if st == 1 else (14, 16)
    elif st == 4:
        tlen_at = 10 + (u16(rb, 6) & 15) * 2
        text_at = tlen_at + 2
    else:
        raise ValueError(f"unhandled string bytes for type {st}")
    end = text_at + u16(rb, tlen_at) * 2
    if end > len(rb):
        raise ValueError("name text extends past record")
    return rb[text_at:end].split(b"\0", 1)[0]


def disc_cells(path, cells):
    """Bounded index/frame reads; failed lookups are never absence."""
    walk, mesh, spool, volume, u16, u32, sws, decode_xy, decode_names, Lattice, PointSet = libs()
    lattice = Lattice(0)
    with Path(path).open("rb") as fh:
        @lru_cache(maxsize=16)
        def read(length, offset):
            return pread(fh, length, offset)

        for cell in cells:
            result, context = index_lookup(read, cell)
            if context is None:
                yield result
                continue
            root, bb, lmr, leaves, ss, ls = context
            try:
                cache = {}
                for leaf_path, leaf, lb, ptype in leaves:
                    fb, fc = walk._leaf_frame(root, 0, ptype, leaf_path, lb, bb, lmr, cache)
                    rng = mesh.leaf_frame_range(0, ptype, leaf_path, fc)
                    bounds = walk.with_range(fb, rng)
                    off, length = volume.getsector(leaf.dsa, ss, ls), leaf.size * ls
                    frame = pread(fh, length, off)
                    # Only name subframe is relevant; do not decode roads/backgrounds.
                    de = 36 + u16(frame, 34) * 4 + 12
                    no, nl = u32(frame, de), u16(frame, de + 4)
                    if de + 6 > len(frame):
                        raise ValueError("name directory extends past map frame")
                    directory_proof = byte_evidence(frame[:de + 6], off)
                    subframe_proof = None
                    names = []
                    if no != 0xFFFFFFFF and not nl:
                        raise ValueError("non-sentinel name directory has zero size")
                    if no != 0xFFFFFFFF and nl:
                        no, nl = sws(no), sws(nl)
                        if no < de + 6 or no + nl > len(frame):
                            raise ValueError("name subframe extends past map frame")
                        subframe_proof = byte_evidence(frame[no:no + nl], off + no)
                        for rec in decode_proven_names(frame[no:no + nl], bounds).records:
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
                                             "bounds": vars(fb), "names": names,
                                             "name_count": len(names),
                                             "name_string_hex": [n["string_hex"] for n in names],
                                             "name_directory": directory_proof,
                                             "name_subframe": subframe_proof})
            except (ValueError, IndexError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
                result.update(status="lookup_failed", reason=f"frame decode {type(exc).__name__}: {exc}")
            yield result


def g_witness(args):
    if args.successor:
        historical = load(args.historical_g)
        cell = next(disc_cells(args.disc, [CELL]))
        names = [n for f in cell["frames"] for n in f["names"]]
        target_hex = historical["target"]["name"]["string_hex"]
        o03_absent = not any(n["string_hex"] == target_hex for n in names)
        write_json(args.out, {"schema": 1, "disc": str(args.disc),
                              "disc_sha256": streamed_sha(args.disc),
                              "historical_g": str(args.historical_g), "cell": cell,
                              "o03_absent": o03_absent,
                              "residual_names": names,
                              "r_parity": "R has no covering frames: names equal" if not names
                              else "residual differences: every name in residual_names"})
        return 0 if o03_absent else 1
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
            if not args.keep_names:
                del f["names"]
        cells.append(row)
    failed = any(c["status"] == "lookup_failed" for c in cells)
    write_json(args.out, {"schema": 2, "disc": str(args.disc), "historical_disc_sha256": R_PIN,
                          "full_pin_remeasured": False, "string_hex": want, "cells": cells,
                          "matches": matches, "match_result": "unresolved" if failed else "matches" if matches else "none"})
    return 2 if failed else 0


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
    if len(r["cells"]) != 9 or {tuple(c["cell"]) for c in r["cells"]} != expected_cells:
        drift.append("R did not cover the nine required cells")
    if r.get("historical_disc_sha256") != R_PIN:
        drift.append("R historical pin differs from DESIGN")
    for cell in r["cells"]:
        error = validate_cell_evidence(cell)
        if error:
            drift.append(f"R cell {cell['cell']} unresolved index/frame proof: {error}")
    hits = []
    if not drift:
        n = g["target"]["name"]
        hits = [m for m in r["matches"] if m["name"]["string_hex"] == n["string_hex"]
                and m["name"]["global_raw"] is not None
                and max(abs(a - b) for a, b in zip(m["name"]["global_raw"], n["global_raw"])) <= 0.5]
    # A requires every decoded frame to exclude the searched name. A
    # string present without a proven matching position needs investigation.
    if not drift and not hits and any(
            r["string_hex"] in f.get("name_string_hex", [])
            for c in r["cells"] for f in c["frames"]):
        drift.append("R searched name present without a proven position match")
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
    lines += [f"R historical disc pin `{r['historical_disc_sha256']}`. Index offsets/hex/SHA-256, decoded DSA/size and outside-coverage geometry are retained in the R JSON and replayed by this verdict. Full disc pins are cited from prior evidence, not re-hashed by this bounded witness. All nine requested cells follow; ix=-1 is outside coverage.", "", "| Cell | Status / reason | Covering frames (offset / length / sha256) |", "| --- | --- | --- |"]
    for c in r["cells"]:
        frames = "; ".join(f"{f['leaf_path']}: {f['offset']} / {f['length']} / `{f['sha256']}`" for f in c["frames"]) or "none"
        lines.append(f"| {c['cell']} | {c['status']} / {c.get('reason', 'unproven')} | {frames} |")
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
    p.add_argument("--successor", action="store_true", help="check O03 absence and list all residual names")
    p.add_argument("--historical-g", type=Path, default=OUT / "g.json")
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
    p.add_argument("--keep-names", action="store_true", help="retain every R name for successor parity")
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
