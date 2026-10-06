#!/usr/bin/env python3
"""Plan 34 bounded frame witnesses. Real inputs are opened only by guarded probe.

Import and publish are offline. Evidence deduplicates byte extents, retaining
the hardened plan-29 reader's exact index proof for every census cell.
"""
from __future__ import annotations

import argparse
from collections import Counter
import ctypes
import fcntl
from functools import lru_cache
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys

PLAN = Path(__file__).resolve().parent
ROOT = PLAN.parents[4]
OUT = PLAN / "witnesses"
TARGETS = ((0, 541), (0, 562), (0, 563))
BLOCK_CELLS = tuple((x, y) for y in range(512, 576) for x in range(32))
PINS = {
    "g_successor": "2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae",
    "g_historical": "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72",
    "r": "8c2d20275227b9d2abb0f1802d4e0cbb6697f46545794d19e1a2024b6f169275",
}
DISCS = {
    "g_successor": ROOT / "output/scratch-29/G_new/ALLDATA.KWI",
    "g_historical": ROOT / "output/scratch-14/G_new/ALLDATA.KWI",
    "r": Path("/run/media/codyh/464210-8480/ALLDATA.KWI"),
}
SPOOL = ROOT / "output/extract_timing/spool"
ROUTING_SO = ROOT / "output/scratch-34/e1_routing.so"
MAX_READ = 64 * 1024 * 1024
SOURCE_CONTRACT = {
    "level": 0,
    "own": "parser/kiwiw/_e2.c: own record is looked up at the target (ix, iy)",
    "borrowed": "parser/kiwiw/_e1.c: same-level background edge/interior routing",
    "halo": "parser/kiwiw/_e2.c: dv_halo uses the parent cell's names, not another level",
    "other_levels": "No cross-level source routing in E1/E2; other spool levels do not feed L0",
    "meaning": "Source inputs before admission, division and trimming; not proof of emitted record identity",
}


@lru_cache(maxsize=1)
def reader():
    paths = [ROOT / "docs/plans/04-c-core-orchestration/triage/name_anchor/witness_p1.py",
             ROOT / "docs/plans/29-k1-name-anchor-failure/witness_p1.py"]
    path = next((p for p in paths if p.is_file()), None)
    if path is None:
        raise ValueError("hardened plan-29 reader not found")
    spec = importlib.util.spec_from_file_location("plan34_name_anchor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pread(fh, length, offset):
    if offset < 0 or not 0 <= length <= MAX_READ:
        raise ValueError(f"invalid bounded pread: {offset}/{length}")
    raw = os.pread(fh.fileno(), length, offset)
    if len(raw) != length:
        raise ValueError(f"short pread: {offset}/{length}")
    return raw


def full_hash(fh):
    digest = hashlib.sha256()
    size = os.fstat(fh.fileno()).st_size
    for off in range(0, size, 1024 * 1024):
        digest.update(pread(fh, min(1024 * 1024, size - off), off))
    return digest.hexdigest()


def stamp(fh):
    st = os.fstat(fh.fileno())
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def require_heavy_guard():
    """Require wrapper and flock ancestors, then check that the lock is held."""
    wrapper = ROOT / "parser/tools/run_heavy_python.py"
    lock = (ROOT / "output/.heavy.lock").resolve()
    pid, have_wrapper, have_flock = os.getppid(), False, False
    for _ in range(32):
        if pid <= 1:
            break
        proc = Path(f"/proc/{pid}")
        argv = [v.decode() for v in (proc / "cmdline").read_bytes().split(b"\0") if v]
        have_wrapper |= "--inner" in argv and any(
            Path(v).name == wrapper.name and Path(v).resolve() == wrapper.resolve()
            for v in argv if v.endswith("run_heavy_python.py"))
        have_flock |= bool(argv and Path(argv[0]).name == "flock" and any(
            Path(v).resolve() == lock for v in argv[1:] if v.endswith(".heavy.lock")))
        stat = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        pid = int(stat[1])
    if not (have_wrapper and have_flock):
        raise ValueError("probe requires run_heavy_python.py and flock output/.heavy.lock")
    with lock.open("rb") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        fcntl.flock(fh, fcntl.LOCK_UN)
    raise ValueError("heavy lock is not held")


def proof(raw, off):
    return {"offset": off, "length": len(raw), "hex": raw.hex(), "sha256": sha(raw)}


def proof_bytes(value):
    raw = bytes.fromhex(value["hex"])
    if value["offset"] < 0 or len(raw) != value["length"] or sha(raw) != value["sha256"]:
        raise ValueError("byte proof mismatch")
    return raw


def pack_evidence(value, pool):
    if isinstance(value, dict):
        if set(value) == {"offset", "length", "hex", "sha256"}:
            key = f"{value['offset']}:{value['length']}:{value['sha256']}"
            if key in pool and pool[key] != value:
                raise ValueError("conflicting byte extent")
            pool[key] = value
            return {"byte_ref": key}
        return {k: pack_evidence(v, pool) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [pack_evidence(v, pool) for v in value]
    return value


def unpack_evidence(value, pool):
    if isinstance(value, dict):
        if set(value) == {"byte_ref"}:
            return pool[value["byte_ref"]]
        return {k: unpack_evidence(v, pool) for k, v in value.items()}
    if isinstance(value, list):
        return [unpack_evidence(v, pool) for v in value]
    return value


def checked(raw, at, length):
    if at < 0 or length < 0 or at + length > len(raw):
        raise ValueError("record extent outside payload")
    return raw[at:at + length]


def section_counts(kind, raw, bounds):
    """Validate record extents before using the existing permissive decoders."""
    w = reader()
    _, _, _, _, u16, u32, sws, *_ = w.libs()
    if kind == "name":
        records = w.decode_proven_names(raw, bounds).records
        return len(records), [w.name_record_string(r.raw_bytes, r.string_type).hex() for r in records]
    if kind == "background":
        from kiwiw.background import decode_background_frame
        hlen = sws(u16(checked(raw, 0, 2), 0))
        if hlen < 2 or (hlen - 2) % 4:
            raise ValueError("invalid background directory")
        checked(raw, 0, hlen)
        for at in range(2, hlen, 4):
            off, size = sws(u16(raw, at)), sws(u16(raw, at + 2))
            if off == 0xFFFF:
                continue
            if off < hlen or size < 2:
                raise ValueError("invalid background element")
            element = checked(raw, off, size)
            n = u16(element, 0)
            checked(element, 2, n * 4)
            cursor = 2 + n * 4
            for i in range(n):
                val = u16(element, 4 + i * 4)
                for _ in range(val & 0xFFF):
                    checked(element, cursor, 12)
                    length = sws(u16(element, cursor) & 0xFFF)
                    coords = u16(element, cursor + 2) & 0x7FF
                    if length < 12 or (val >> 14 and 12 + coords * 2 > length):
                        raise ValueError("invalid background shape")
                    checked(element, cursor, length)
                    cursor += length
        return len(decode_background_frame(raw, bounds).shapes), None
    from kiwiw.road import decode_road_frame
    checked(raw, 0, 8)
    ndc, nad = raw[4], raw[5]
    hlen = 8 + (ndc + nad) * 4
    checked(raw, 0, hlen)
    for at in range(8, 8 + ndc * 4, 4):
        off, count = sws(u16(raw, at)), u16(raw, at + 2) & 0xFFF
        if off == 0xFFFF:
            continue
        if off < hlen:
            raise ValueError("invalid road display class")
        checked(raw, off, 2)
        cursor = off + 2
        for _ in range(count):
            checked(raw, cursor, 16)
            hdr = u32(raw, cursor)
            length = sws((hdr >> 16) & 0xFFF)
            link = checked(raw, cursor, length)
            if length < 16:
                raise ValueError("invalid road link length")
            nodeoff = sws(hdr & 0xFF)
            for _ in range(u16(raw, cursor + 4) & 0x7FF):
                checked(link, nodeoff, 6)
                nip = u16(link, nodeoff) & 0x3FF
                checked(link, nodeoff + 6, nip * 2)
                nodeoff += 6 + nip * 2
            cursor += length
    for at in range(8 + ndc * 4, hlen, 4):
        off, size = sws(u16(raw, at)), sws(u16(raw, at + 2))
        if off != 0xFFFF and size:
            if off < hlen:
                raise ValueError("invalid road additional data")
            checked(raw, off, size)
    return len(decode_road_frame(raw, bounds).links), None


def frame_payload(raw, offset, bounds, n_basic=3, n_ext=0, g_layout=False):
    """Classify every byte. Unreferenced nonzero bytes remain content."""
    _, _, _, _, u16, u32, sws, *_ = reader().libs()
    checked(raw, 0, 36)
    de = 36 + u16(raw, 34) * 4
    checked(raw, 0, de + 18)
    basic = [(u32(raw, de + i * 6), u16(raw, de + i * 6 + 4)) for i in range(3)]
    starts = [sws(off) for off, _ in basic if off != 0xFFFFFFFF and sws(off) < len(raw)]
    # G's encoder writes exactly 20 L0 MFDE entries even for empty frames
    # (_cenc.c, kw__encode_rec). The wire reader's fallback of 3+9 is only
    # a lower bound and would misclassify the other 8 sentinels as content.
    n = 20 if g_layout else max((min(starts) - de) // 6, n_basic) if starts else n_basic + n_ext
    if g_layout and (de != 36 or starts and min(starts) != de + 20 * 6):
        raise ValueError("G L0 directory differs from the encoder's 20-entry layout")
    if n < 3:
        raise ValueError("missing basic map directory")
    header_end = de + n * 6
    checked(raw, 0, header_end)
    counts = {"name": 0, "background": 0, "road": 0}
    strings, sections = [], []
    mask = bytearray(len(raw))
    mask[:header_end] = b"H" * header_end
    semantic_content = False
    for i in range(n):
        off, size = u32(raw, de + i * 6), u16(raw, de + i * 6 + 4)
        if off == 0xFFFFFFFF:
            if size:
                raise ValueError("absent subframe has nonzero size")
            continue
        off, size = sws(off), sws(size)
        kind = ("road", "background", "name")[i] if i < 3 else f"extended_{i}"
        if i >= 3 and off >= len(raw):
            sections.append({"kind": kind, "external_pointer": True, "offset": off, "length": size})
            semantic_content = True
            continue
        if not size or off < header_end or any(mask[off:off + size]):
            raise ValueError("invalid/overlapping subframe")
        sub = checked(raw, off, size)
        mask[off:off + size] = b"C" * size
        section = {"kind": kind, "bytes": proof(sub, offset + off)}
        if i < 3:
            count, texts = section_counts(kind, sub, bounds)
            counts[kind] = count
            section["count"] = count
            if texts is not None:
                strings = texts
            subheader_end = 8 + (sub[4] + sub[5]) * 4 if kind == "road" else sws(u16(sub, 0))
            checked(sub, 0, subheader_end)
            mask[off:off + subheader_end] = b"H" * subheader_end
            section["header_bytes"] = proof(sub[:subheader_end], offset + off)
            # A two-byte empty BG/name list is a header, not geometry.
            # Road intersection metadata remains content even without links.
            semantic_content |= bool(count or kind == "road" and u16(sub, 2))
        else:
            semantic_content = True
        sections.append(section)
    spans = []
    start = 0
    def role(at):
        return "header" if mask[at] == ord("H") else "content" if mask[at] or raw[at] else "zero_padding"
    while start < len(raw):
        kind = role(start)
        end = start + 1
        while end < len(raw) and role(end) == kind:
            end += 1
        spans.append({"kind": kind, "bytes": proof(raw[start:end], offset + start)})
        start = end
    semantic_content |= any(s["kind"] == "content" for s in spans)
    payload_class = "content" if semantic_content else "padded_shell" if any(s["kind"] == "zero_padding" for s in spans) else "empty_shell"
    name_section = next((s["bytes"] for s in sections if s["kind"] == "name"), None)
    return {"frame_bytes": proof(raw, offset), "header_bytes": proof(raw[:header_end], offset),
            "sections": sections, "byte_spans": spans, "payload_class": payload_class,
            "name_count": counts["name"], "background_count": counts["background"],
            "road_count": counts["road"], "name_string_hex": strings,
            "name_directory": proof(raw[:de + 18], offset), "name_subframe": name_section,
            "n_basic_map": n_basic, "n_ext_map": n_ext,
            "directory_contract": "G L0: parser/kiwiw/_cenc.c, 20 entries" if g_layout else "wire-inferred with LMR fallback"}


def disc_rows(fh, cells, g_layout=False):
    w = reader()
    walk, mesh, _, volume, *_ = w.libs()
    @lru_cache(maxsize=16)
    def read(length, offset):
        return pread(fh, length, offset)
    for cell in cells:
        row, context = w.index_lookup(read, cell)
        if context is not None:
            root, bb, lmr, leaves, ss, ls = context
            try:
                cache = {}
                for path, leaf, lb, ptype in leaves:
                    fb, fc = walk._leaf_frame(root, 0, ptype, path, lb, bb, lmr, cache)
                    rng = mesh.leaf_frame_range(0, ptype, path, fc)
                    off, length = volume.getsector(leaf.dsa, ss, ls), leaf.size * ls
                    raw = pread(fh, length, off)
                    row["frames"].append({"leaf_path": list(path), "offset": off, "length": length,
                                          "sha256": sha(raw), "frame_class": fc, "range": rng,
                                          "bounds": vars(fb), **frame_payload(raw, off, walk.with_range(fb, rng),
                                                                                   lmr.n_basic_map, lmr.n_ext_map, g_layout)})
            except (ValueError, IndexError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
                row.update(status="lookup_failed", reason=f"frame decode {type(exc).__name__}: {exc}")
        yield row


def census(rows):
    return {"cells_requested": len(rows), "status_counts": dict(Counter(r["status"] for r in rows)),
            "cells_with_frames": [r["cell"] for r in rows if r["frames"]],
            "frame_count": sum(len(r["frames"]) for r in rows),
            "lookup_failures": [{"cell": r["cell"], "reason": r["reason"]} for r in rows if r["status"] == "lookup_failed"],
            "blockset": 32, "block": 0, "bounds": [0, 31, 512, 575]}


def disc_document(fh, label, path, expected_sha256=None):
    if expected_sha256 is not None:
        if label != "g_successor" or len(expected_sha256) != 64 or any(
                c not in "0123456789abcdef" for c in expected_sha256):
            raise ValueError("candidate pin requires g_successor and a lowercase SHA-256")
    expected = expected_sha256 or PINS[label]
    before = stamp(fh)
    measured = full_hash(fh) if label != "r" else None
    if measured is not None and measured != expected:
        raise ValueError(f"{label} full pin mismatch: {measured}")
    rows, pool = [], {}
    for row in disc_rows(fh, BLOCK_CELLS, label != "r"):
        rows.append(pack_evidence(row, pool))
    if stamp(fh) != before:
        raise ValueError("disc changed while probing")
    return {"schema": 1, "kind": "disc", "label": label, "disc": str(path),
            "disc_sha256": expected, "measured_sha256": measured,
            **({"predecessor_sha256": PINS[label]} if expected_sha256 else {}),
            "full_pin_remeasured": label != "r", "r_pin_source": "plan-29 historical pin; not remeasured" if label == "r" else None,
            "hardened_reader": str(Path(reader().__file__).relative_to(ROOT)),
            "byte_pool": pool, "cells": rows, "census": census(rows)}


def validate_disc(doc, label, expected_sha256=None):
    expected = expected_sha256 or PINS[label]
    if (doc["schema"] != 1 or doc["kind"] != "disc" or doc["label"] != label
            or doc["disc_sha256"] != expected):
        raise ValueError("disc document identity mismatch")
    if label != "r" and (not doc["full_pin_remeasured"] or doc["measured_sha256"] != expected):
        raise ValueError("G pin was not fully verified")
    if [tuple(r["cell"]) for r in doc["cells"]] != list(BLOCK_CELLS):
        raise ValueError("census must cover all 2048 cells exactly once in order")
    if doc["census"] != census(doc["cells"]):
        raise ValueError("census counters disagree")
    w = reader()
    walk = w.libs()[0]
    for value in doc["byte_pool"].values():
        proof_bytes(value)
    rows = {}
    for packed in doc["cells"]:
        row = unpack_evidence(packed, doc["byte_pool"])
        error = w.validate_cell_evidence(row)
        if error:
            raise ValueError(f"{label} {row['cell']}: {error}")
        if row.get("blockset") != 32 or row.get("block") != 0 or row.get("block_cells") != [0, 31, 512, 575]:
            raise ValueError("unexpected block geometry")
        # Replay LMR identity rather than trusting stored basic/extended counts.
        context = None
        if row["frames"]:
            reads = {(p["length"], p["offset"]): proof_bytes(p) for p in row["index_evidence"]["reads"]}
            _, context = w.index_lookup(lambda n, at: reads[(n, at)], row["cell"])
        for frame in row["frames"]:
            raw = proof_bytes(frame["frame_bytes"])
            if (frame["frame_bytes"]["offset"] != frame["offset"] or len(raw) != frame["length"]
                    or sha(raw) != frame["sha256"]):
                raise ValueError("frame bytes disagree with indexed identity")
            from kiwiw.model import BoundingBox
            bounds = BoundingBox(**frame["bounds"])
            payload = frame_payload(raw, frame["offset"], walk.with_range(bounds, frame["range"]),
                                    context[2].n_basic_map, context[2].n_ext_map, label != "r")
            if any(frame.get(k) != v for k, v in payload.items()):
                raise ValueError("payload classification/counts disagree with bytes")
        rows[tuple(row["cell"])] = row
    return rows


def spool_layout(raw, offset):
    """Validate the complete column layout without loading a whole spool."""
    reader().libs()
    from kiwiw import spool
    import numpy as np
    checked(raw, 0, 72)
    counts = dict(zip(spool._COUNT_KEYS, struct.unpack_from("<9Q", raw)))
    cursor, columns = 72, []
    for name, dtype, countkey in spool._COLUMNS:
        length = counts[countkey] * np.dtype(dtype).itemsize
        checked(raw, cursor, length + spool._pad8(length))
        columns.append({"column": name, "offset": offset + cursor, "length": length})
        cursor += length + spool._pad8(length)
    if cursor != len(raw):
        raise ValueError("spool cell length/layout mismatch")
    return counts, columns


@lru_cache(maxsize=1)
def routing_lib():
    """Build only the existing E1 reader into owned scratch, never parser/."""
    reader().libs()
    from kiwiw import cbuild
    source = ROOT / "parser/kiwiw/_e1.c"
    path = cbuild.build_ext(sources=(source,), headers=(), out=ROUTING_SO)
    lib = ctypes.CDLL(str(path))
    lib.kw_e1.restype = ctypes.c_int64
    lib.kw_e1.argtypes = [ctypes.c_void_p, ctypes.c_int64] * 3 + [ctypes.c_int64, ctypes.c_int64,
                        ctypes.c_void_p, ctypes.c_int64, ctypes.c_void_p]
    return lib


def route_record(desc, raw, cell):
    """Replay E1 on one bounded source record, using a one-row synthetic index."""
    import numpy as np
    from kiwiw.descriptor import E1_ROW_DTYPE
    ix, iy = cell
    idx = b"KWSPIDX1" + struct.pack("<5Q", 1, 1, 0, 0, 0) + struct.pack("<iiQQ", ix, iy, 0, len(raw))
    inputs = [np.frombuffer(v, np.uint8) for v in (desc, idx, raw)]
    cap = 32
    while True:
        out, cnt = np.zeros(cap, E1_ROW_DTYPE), np.zeros(8, np.int64)
        n = routing_lib().kw_e1(*[v for a in inputs for v in (a.ctypes.data, len(a))],
                               iy, iy + 1, out.ctypes.data, cap, cnt.ctypes.data)
        if n < 0:
            raise ValueError(f"bounded E1 source routing failed: {n}")
        if n <= cap:
            return [{"target": [int(r["tix"]), int(r["tiy"])], "shape": int(r["shape"]),
                     "kind": "interior_cover" if r["kind"] else "edge"} for r in out[:n]]
        if n > MAX_READ // E1_ROW_DTYPE.itemsize:
            raise ValueError("unbounded source routing output")
        cap = int(n)


def spool_document(directory, targets):
    """Stream the entire L0 index and one bounded record at a time.

    E1 sees only the census's frame-bearing receivers. Missing receivers
    cannot alter routing to these cells; their mask bits are explicitly set.
    """
    w = reader()
    w.libs()
    from kiwiw import descriptor, spool
    targets = sorted(set(targets), key=lambda c: (c[1], c[0]))
    desc = descriptor.build(0, [c[0] for c in targets], [c[1] for c in targets], window=(0, 31, 512, 575))
    sources, pool, scanned, counts_total = [], {}, 0, Counter()
    idxpath, datapath = directory / "level_0.idx", directory / "level_0.data"
    with idxpath.open("rb") as idxfh, datapath.open("rb") as datafh:
        before = (stamp(idxfh), stamp(datafh))
        head = pread(idxfh, 48, 0)
        if head[:8] != b"KWSPIDX1":
            raise ValueError("not a binary spool index")
        n = struct.unpack_from("<Q", head, 8)[0]
        if before[0][2] != 48 + n * 24:
            raise ValueError("spool index size mismatch")
        previous = None
        for start in range(0, n, 4096):
            batch = min(4096, n - start)
            chunks = [pread(idxfh, batch * width, 48 + base * n + start * width)
                      for base, width in ((0, 4), (4, 4), (8, 8), (16, 8))]
            arrays = [struct.unpack(f"<{batch}{fmt}", chunk) for chunk, fmt in zip(chunks, "iiQQ")]
            for j, (ix, iy, off, length) in enumerate(zip(*arrays)):
                if previous is not None and (iy, ix) <= previous:
                    raise ValueError("spool cells are not strictly ordered")
                previous = (iy, ix)
                if length < 72 or off + length > before[1][2]:
                    raise ValueError("invalid spool cell extent")
                count_bytes = pread(datafh, 72, off)
                counts = dict(zip(spool._COUNT_KEYS, struct.unpack("<9Q", count_bytes)))
                counts_total.update(counts)
                scanned += 1
                own = (ix, iy) in targets
                if not own and not counts["n_bgs"]:
                    continue
                raw = pread(datafh, length, off)
                counts, columns = spool_layout(raw, off)
                routed = route_record(desc, raw, (ix, iy)) if counts["n_bgs"] else []
                if not own and not routed:
                    continue
                identities = []
                if own and counts["n_names"]:
                    cols, offsets = w.name_columns(datafh, off, length)
                    identities = [w.name_identity(cols, offsets, k) for k in range(counts["n_names"])]
                index_proofs = [proof(chunks[k][j * width:(j + 1) * width],
                                      48 + base * n + (start + j) * width)
                                for k, (base, width) in enumerate(((0, 4), (4, 4), (8, 8), (16, 8)))]
                source = {"level": 0, "cell": [ix, iy], "source_row": start + j,
                          "cell_offset": off, "cell_length": length, "cell_sha256": sha(raw),
                          "counts": counts, "column_extents": columns,
                          "cell_bytes": proof(raw, off), "index_entries": index_proofs,
                          "own_targets": [[ix, iy]] if own else [], "routed_backgrounds": routed,
                          "names_before_guard": identities}
                sources.append(pack_evidence(source, pool))
        hashes = {"index": full_hash(idxfh), "data": full_hash(datafh)}
        totals = (scanned, counts_total["n_roads"], counts_total["n_bgs"], counts_total["n_names"])
        if struct.unpack_from("<4Q", head, 16) != totals:
            raise ValueError("spool index totals differ from streamed source counts")
        if before != (stamp(idxfh), stamp(datafh)):
            raise ValueError("spool changed while probing")
    return {"schema": 1, "kind": "spool", "spool": str(directory), "level": 0,
            "targets": [list(c) for c in targets], "source_contract": SOURCE_CONTRACT,
            "index_header": proof(head, 0), "source_rows_scanned": scanned,
            "counts_total": dict(counts_total), "sha256": hashes,
            "e1_source_sha256": sha((ROOT / "parser/kiwiw/_e1.c").read_bytes()),
            "byte_pool": pool, "sources": sources}


def validate_spool(doc, targets):
    if doc["schema"] != 1 or doc["kind"] != "spool" or doc["level"] != 0 or doc["source_contract"] != SOURCE_CONTRACT:
        raise ValueError("spool contract mismatch")
    if {tuple(c) for c in doc["targets"]} != set(targets):
        raise ValueError("spool targets differ from complete G-frame census")
    if len(doc["targets"]) != len(targets):
        raise ValueError("duplicate spool targets")
    if doc["e1_source_sha256"] != sha((ROOT / "parser/kiwiw/_e1.c").read_bytes()):
        raise ValueError("E1 routing source drift; re-probe under the guard")
    from kiwiw import descriptor, spool
    desc = descriptor.build(0, [c[0] for c in targets], [c[1] for c in targets], window=(0, 31, 512, 575))
    head = proof_bytes(doc["index_header"])
    if head[:8] != b"KWSPIDX1" or len(head) != 48 or struct.unpack_from("<Q", head, 8)[0] != doc["source_rows_scanned"]:
        raise ValueError("spool source scan incomplete")
    for value in doc["byte_pool"].values():
        proof_bytes(value)
    for digest in doc["sha256"].values():
        if len(bytes.fromhex(digest)) != 32:
            raise ValueError("invalid spool digest")
    sources = []
    seen = set()
    for packed in doc["sources"]:
        source = unpack_evidence(packed, doc["byte_pool"])
        if source["level"] != 0 or source["source_row"] in seen:
            raise ValueError("duplicate/non-L0 source row")
        seen.add(source["source_row"])
        raw = proof_bytes(source["cell_bytes"])
        if (source["cell_bytes"]["offset"] != source["cell_offset"] or len(raw) != source["cell_length"]
                or sha(raw) != source["cell_sha256"]):
            raise ValueError("spool source extent mismatch")
        counts, columns = spool_layout(raw, source["cell_offset"])
        if counts != source["counts"] or columns != source["column_extents"]:
            raise ValueError("spool counts/columns disagree with bytes")
        n = doc["source_rows_scanned"]
        row = source["source_row"]
        if not 0 <= row < n:
            raise ValueError("spool row outside index")
        values = (*source["cell"], source["cell_offset"], source["cell_length"])
        for entry, value, (base, width, fmt) in zip(source["index_entries"], values,
                                                 ((0, 4, "i"), (4, 4, "i"), (8, 8, "Q"), (16, 8, "Q"))):
            if entry["offset"] != 48 + base * n + row * width or proof_bytes(entry) != struct.pack("<" + fmt, value):
                raise ValueError("spool source index identity mismatch")
        if len(source["index_entries"]) != 4:
            raise ValueError("missing spool index fields")
        if source["own_targets"] != ([source["cell"]] if tuple(source["cell"]) in targets else []):
            raise ValueError("spool own-source relationship mismatch")
        if any(tuple(r["target"]) not in targets or r["kind"] not in ("edge", "interior_cover")
               or not 0 <= r["shape"] < counts["n_bgs"] for r in source["routed_backgrounds"]):
            raise ValueError("invalid spool routing relationship")
        routed = route_record(desc, raw, source["cell"]) if counts["n_bgs"] else []
        if routed != source["routed_backgrounds"]:
            raise ValueError("spool routing differs from E1 byte replay")
        cols = spool.decode_columns(raw)
        offsets = {c["column"]: c["offset"] for c in columns}
        namecols = {k: v for k, v in cols.items() if k.startswith("s_") or k.startswith("blob_name_")}
        names = [reader().name_identity(namecols, offsets, k) for k in range(counts["n_names"])] if source["own_targets"] else []
        if names != source["names_before_guard"]:
            raise ValueError("spool names differ from cell-byte replay")
        sources.append(source)
    return sources


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def probe(args):
    require_heavy_guard()  # Before any protected input is opened.
    if args.disc:
        path = args.path or DISCS[args.disc]
        with path.open("rb") as fh:
            doc = disc_document(fh, args.disc, path, getattr(args, "expected_sha256", None))
        write(args.out or OUT / f"{args.disc}.json", doc)
        return 2 if doc["census"]["lookup_failures"] else 0
    docs = [load(OUT / f"{label}.json") for label in ("g_successor", "g_historical")]
    rows = [validate_disc(doc, label) for doc, label in zip(docs, ("g_successor", "g_historical"))]
    targets = set(TARGETS) | {cell for disc in rows for cell, row in disc.items() if row["frames"]}
    doc = spool_document(args.spool, targets)
    write(args.out or OUT / "spool.json", doc)
    return 0


def publish(args):
    docs = {label: load(OUT / f"{label}.json") for label in PINS}
    rows = {label: validate_disc(doc, label) for label, doc in docs.items()}
    targets = set(TARGETS) | {cell for label in ("g_successor", "g_historical")
                            for cell, row in rows[label].items() if row["frames"]}
    spool = load(OUT / "spool.json")
    sources = validate_spool(spool, targets)
    mismatches = {}
    for label in ("g_successor", "g_historical"):
        mismatches[label] = [list(cell) for cell in BLOCK_CELLS
                             if rows[label][cell]["frames"] and rows["r"][cell]["status"] == "empty_slot"]
    for cell in TARGETS:
        if rows["r"][cell]["status"] != "empty_slot":
            raise ValueError(f"R target {cell} unexpectedly has a frame; inspect its decoded evidence")
        if any(not rows[label][cell]["frames"] for label in ("g_successor", "g_historical")):
            raise ValueError(f"G target {cell} frame missing; inspect drift")
    cells = []
    for cell in sorted(targets, key=lambda c: (c[1], c[0])):
        source_rows = [{"source_row": s["source_row"], "level": s["level"], "cell": s["cell"],
                        "cell_offset": s["cell_offset"], "cell_length": s["cell_length"],
                        "own": list(cell) in s["own_targets"],
                        "backgrounds": [r for r in s["routed_backgrounds"] if r["target"] == list(cell)]}
                       for s in sources if list(cell) in s["own_targets"] or any(
                           r["target"] == list(cell) for r in s["routed_backgrounds"])]
        discs = {}
        for label in PINS:
            row = rows[label][cell]
            discs[label] = {"status": row["status"], "reason": row["reason"],
                            "frames": [{k: f[k] for k in ("leaf_path", "offset", "length", "sha256", "frame_class",
                                        "name_count", "background_count", "road_count", "payload_class")}
                                       for f in row["frames"]]}
        cells.append({"cell": list(cell), "discs": discs, "spool_sources": source_rows})
    extras = {label: [c for c in values if tuple(c) not in TARGETS] for label, values in mismatches.items()}
    result = {"schema": 1, "status": "witnessed", "pins": PINS, "cells": cells,
              "census": {label: doc["census"] for label, doc in docs.items()},
              "G_frame_R_empty_cells": mismatches, "extra_cells": extras,
              "residuals": [f"Extra {label} cell {c} needs Phase 2 disposition" for label, values in extras.items() for c in values],
              "fix": "not attempted", "phase3_closed": False,
              "spool_source_meaning": SOURCE_CONTRACT["meaning"]}
    write(args.out, result)
    lines = ["# Phase 1 frame witnesses", "", "Status: byte-witnessed; no fix or root-cause verdict. Plan 04 Phase 3 remains open.", "",
             "G pins were fully streamed and verified before bounded census reads. R's historical pin is cited, not remeasured.", "",
             "All 2,048 cells of L0 blockset 32 / block 0 were replayed through the hardened reader. Lookup failures forbid publication.", "",
             "Full frame bytes, index reads, sections and zero-padding spans are in the deduplicated byte pools. Source rows are assembly inputs before filtering and trimming.", "",
             "| Disc | Cells with frames | Frames | G frame / R empty cells |", "| --- | ---: | ---: | --- |"]
    for label, doc in docs.items():
        c = doc["census"]
        lines.append(f"| {label} | {len(c['cells_with_frames'])} | {c['frame_count']} | {mismatches.get(label, [])} |")
    lines += ["", "Per-cell evidence and spool source offsets:", "", "```json", json.dumps(cells, indent=2), "```", "",
              f"Extra cells requiring Phase 2 disposition: {json.dumps(extras, sort_keys=True)}", "",
              "No O03 reseat, frame suppression, K1 run, protected-disc mutation, or Phase 3 close was performed.", ""]
    Path(args.note).write_text("\n".join(lines))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe")
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--disc", choices=tuple(PINS))
    inputs.add_argument("--spool", type=Path)
    p.add_argument("--path", type=Path, help="disc path override; fixed pin required unless --expected-sha256 is supplied")
    p.add_argument("--expected-sha256", help="Execute-measured candidate pin; g_successor only; cannot replace Phase 1 evidence")
    p.add_argument("--out", type=Path)
    p.set_defaults(run=probe)
    p = sub.add_parser("publish", help="offline evidence replay and Phase 1 summary; opens no disc or spool")
    p.add_argument("--out", type=Path, default=OUT / "summary.json")
    p.add_argument("--note", type=Path, default=PLAN / "phase1_note.md")
    p.set_defaults(run=publish)
    args = parser.parse_args(argv)
    for key in ("path", "spool", "out", "note"):
        value = getattr(args, key, None)
        if value is not None and not value.is_absolute():
            setattr(args, key, ROOT / value)
    if args.command == "probe" and args.spool and args.path:
        parser.error("--path applies only to --disc")
    if args.command == "probe" and args.expected_sha256:
        if args.disc != "g_successor" or not args.path or not args.out:
            parser.error("candidate pin requires --disc g_successor, --path and --out")
        if args.out.resolve() in {(OUT / f"{label}.json").resolve() for label in (*PINS, "spool", "summary")}:
            parser.error("candidate probe cannot replace Phase 1 witnesses")
    try:
        return args.run(args)
    except (ValueError, KeyError, TypeError, OSError, struct.error, AssertionError) as exc:
        print(f"frame_witness: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
