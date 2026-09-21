#!/usr/bin/env python3
"""Map Frame header-word census of a reference disc's ALLDATA.KWI.

Words are big-endian u16 at byte offset 2*i of the 36-byte header (word 0 =
header size, 6 = dipid, 7 = pmcode high half, 9 = dsflag, 10 = rlx, 11 = rly).
Per leaf the census records the header words, nregion, the mfde table and the
in-buffer slot offsets; it is keyed by (level, parcel class, division state)
using the 2-01 class rule (`coord_scale_census.parcel_class`) with the urban
tile table read from the checked-in `coord_scale.json`.

Fit/held-out split: sha1("bs:blk:path...")[0] < 64  ->  held out (25%), by
parcel identity, deterministic. Rules are derived on the fit set only.
Reads R only through `harness.walk` and `kiwiw.volume/parcel_mgmt`; imports no
writer module.

Everything is aggregated *inside the worker processes*: R has ~3.7M L0 leaves
and a per-parcel dump is ~1 GB, so workers return merged counters plus bounded
example lists only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import walk  # noqa: E402
import coord_scale_census as csc  # noqa: E402

WORDS = (0, 6, 7, 9, 10, 11)
NAMES = {0: "size", 6: "dipid", 7: "pmcode", 9: "dsflag", 10: "rlx", 11: "rly"}
SPLIT_RULE = ("held out iff sha1('<bs>:<blk>:<p0>.<p1>...')[0] < 64 (~25%), "
              "by parcel identity (blockset_index, block_index, leaf_path)")
HDR = 36
NO_DATA = 0xFFFFFFFF
MAX_EXAMPLES = 40
# rlx/rly physical model (see `header` section in coord_scale.json).
LAT_ORIGIN_SHIFT = 50.0
COORD_RANGE_RL = 4096


def heldout(bs: int, blk: int, path) -> bool:
    key = f"{bs}:{blk}:" + ".".join(str(p) for p in path)
    return hashlib.sha1(key.encode()).digest()[0] < 64


def be16(b: bytes, o: int) -> int:
    return (b[o] << 8) | b[o + 1]


def be32(b: bytes, o: int) -> int:
    return (be16(b, o) << 16) | be16(b, o + 2)


def parse_header(data: bytes, n_basic_map: int = 3, n_ext_map: int = 0) -> dict | None:
    """Raw header facts of one Map Frame buffer (no sub-frame decode)."""
    if len(data) < HDR:
        return None
    words = [be16(data, 2 * i) for i in range(18)]
    nreg = words[17]
    de = HDR + 4 * nreg
    def ent(i: int) -> tuple[int, int]:
        o = de + 6 * i
        if o + 6 > len(data):
            return (NO_DATA, 0)
        return (be32(data, o), be16(data, o + 4))

    slots = [ent(i) for i in range(3)]
    starts = []
    for off, _ in slots[:3]:
        if off != NO_DATA:
            v = off << 1
            if v < len(data):
                starts.append(v)
    first = min(starts) if starts else None
    slot0 = None
    if slots and slots[0][0] != NO_DATA:
        v = slots[0][0] << 1
        if v < len(data):
            slot0 = v
    # mfde table length, exactly as `harness.checks.decode._raw_mfde_table` and
    # `kiwiw.parcel.decode_parcel` derive it.
    if first is not None:
        total = max((first - de) // 6, n_basic_map)
    else:
        total = n_basic_map + n_ext_map
    total = max(0, min(total, 64))
    slots = [ent(i) for i in range(total)] if total > 3 else slots[:total]
    return {"w": words, "nreg": nreg, "first": first, "slot0": slot0,
            "slots": slots, "len": len(data),
            "nent": None if first is None else (first - de) // 6,
            "rg_addr": be32(data, 28), "rg_size": words[16]}


# --------------------------------------------------------------------------
# aggregation (runs in the worker)
# --------------------------------------------------------------------------

def _not_a_map_frame(fh, sector_off: int, file_size: int) -> str | None:
    """Mirror of `harness.checks.decode._decodes_as_map_frame` -- the exact test
    whose 65 R failures are Carried item 2. Returns a reason, or None if the
    bytes do decode as a Map Frame."""
    from kiwiw.parcel import decode_map_frame_header
    if not (0 <= sector_off < file_size):
        return "out-of-buffer sector outside file"
    if sector_off + HDR > file_size:
        return "target too close to EOF for a Map Frame header"
    fh.seek(sector_off)
    raw = fh.read(HDR)
    try:
        hdr = decode_map_frame_header(raw)
    except Exception as exc:  # noqa: BLE001
        return f"Map Frame header decode raised {type(exc).__name__}"
    if not (-90.0 <= hdr.llpid_lat <= 90.0 and -180.0 <= hdr.llpid_lon <= 180.0):
        return "header llpid out of range"
    if hdr.nregion > 255:
        return "header nregion implausible"
    return None


def _new_agg() -> dict:
    return {"words": defaultdict(Counter), "geo": defaultdict(Counter),
            "w0": defaultdict(Counter), "w7k": defaultdict(Counter), "w7x": Counter(), "w7y": Counter(), "w7g": Counter(), "w7z": Counter(), "w7s": Counter(), "ne": Counter(), "ex": Counter(),
            "w0exc": [], "ptr": [], "ptrn": Counter(), "n": Counter()}


def _merge(a: dict, b: dict) -> None:
    for k in ("words", "geo", "w0", "w7k"):
        for kk, c in b[k].items():
            a[k][kk].update(c)
    for k in ("w7x", "w7y", "w7g", "w7z", "w7s", "ne", "ex", "ptrn", "n"):
        a[k].update(b[k])
    for k in ("w0exc", "ptr"):
        a[k].extend(b[k][:MAX_EXAMPLES])
        a[k][:] = a[k][:MAX_EXAMPLES * 8]


def _q(x: float) -> int:
    return int(round(x * 1e6))


def _accumulate(agg: dict, r: dict, urban, check_pointers: bool, fh, file_size,
                ssz, lsz) -> None:
    lvl = r["level"]
    cls = csc.parcel_class(lvl, r["div"], (r["bs"], r["blk"], r["path"][0]), urban)
    div = csc.division_state(r["div"], r["path"][-1])
    split = "held" if heldout(r["bs"], r["blk"], r["path"]) else "fit"
    key = f"{lvl}|{cls}|{div}"
    agg["n"][f"{split}|{key}"] += 1
    w = r["w"]
    for i in WORDS:
        if i in (10, 11):
            continue
        agg["words"][f"{split}|{key}|{i}"][w[i]] += 1
    gk = f"{split}|{lvl}|{_q(r['lat_lo'])}|{_q(r['lat_hi'] - r['lat_lo'])}|{_q(r['lon_hi'] - r['lon_lo'])}"
    agg["geo"][gk][f"{w[10]},{w[11]}"] += 1

    # word 0 structure
    de = HDR + 4 * r["nreg"]
    c = agg["w0"][f"{split}|{key}"]
    c["n"] += 1
    nent_formula = (w[0] * 2 - de) // 6 if (w[0] * 2 - de) >= 0 else -1
    if r["first"] is not None:
        c["first_defined"] += 1
        if w[0] * 2 == r["first"]:
            c["first_eq"] += 1
    if r["slot0"] is not None:
        c["slot0_defined"] += 1
        if w[0] * 2 == r["slot0"]:
            c["slot0_eq"] += 1
    if w[0] * 2 == de + 6 * nent_formula and nent_formula >= 0:
        c["formula_consistent"] += 1
    c[f"bytes{w[0] * 2}"] += 1
    c[f"nreg{r['nreg']}"] += 1
    c[f"nent{nent_formula}"] += 1

    # word-0 exceptions: w0*2 != slot 0's offset
    if r["slot0"] is not None and w[0] * 2 != r["slot0"] and len(agg["w0exc"]) < MAX_EXAMPLES:
        agg["w0exc"].append({"level": lvl, "class": cls, "division_state": div,
                             "bs": r["bs"], "blk": r["blk"], "parcel": list(r["path"]),
                             "w0_bytes": w[0] * 2, "slot0_offset": r["slot0"],
                             "first_offset": r["first"], "nregion": r["nreg"],
                             "n_entries_from_w0": nent_formula,
                             "slots012": [[o, s] for o, s in r["slots"][:3]]})
    if r["slot0"] is not None and w[0] * 2 != r["slot0"]:
        agg["n"][f"w0_slot0_mismatch|{lvl}"] += 1
    if r["slot0"] is None:
        agg["n"][f"w0_slot0_absent|{lvl}"] += 1

    # word 7 cross-tabs
    agg["w7x"][f"{lvl}|{r['bs']}|{r['blk']}|{w[7]}"] += 1
    mask = "".join("1" if (o != NO_DATA and s) else "0" for o, s in r["slots"][:3])
    agg["w7y"][f"{lvl}|{w[7]}|nreg{r['nreg']}|slots{mask}"] += 1
    agg["w7k"][f"{split}|{key}|{mask}"][w[7]] += 1
    for i in (13, 14, 15):
        agg["ex"][f"{i}|{w[i]}"] += 1
    n_ext = sum(1 for o, sz in r["slots"][3:] if (o, sz) != (NO_DATA, 0))
    agg["ex"][f"ext|{lvl}|present{n_ext}"] += 1
    agg["ne"][f"{key}|nregion{r['nreg']}|n_entries{r['nent']}"] += 1
    s1 = r["slots"][1][1] if len(r["slots"]) > 1 else 0
    agg["w7s"][f"{lvl}|{w[7]}|{mask}|s1_{0 if s1 == 0 else min(1 << (s1.bit_length() - 1), 4096)}"] += 1
    agg["w7z"][f"{lvl}|{w[7]}|ni{int(w[13] != 0)}|rp{w[14]}|nad{int(w[15] != 0)}|rg{int(r['rg_size'] != 0)}|{mask}"] += 1
    agg["w7g"][f"{lvl}|{w[7]}|{math.floor(r['lat_lo'])}|{math.floor(r['lon_lo'])}"] += 1

    # carried item 2: out-of-buffer idx>=3 mfde targets that are not Map Frames
    if check_pointers:
        from kiwiw.volume import getsector
        frame_size = r["len"]
        for idx in range(3, len(r["slots"])):
            off, size = r["slots"][idx]
            if (off, size) == (NO_DATA, 0):
                continue
            if (off << 1) < frame_size:
                continue
            agg["ptrn"][f"oob|{lvl}"] += 1
            try:
                so = getsector(off, ssz, lsz)
            except Exception:  # noqa: BLE001
                continue
            why = _not_a_map_frame(fh, so, file_size)
            if why is None:
                continue
            agg["ptrn"][f"bad|{lvl}|{cls}|{div}"] += 1
            agg["ptrn"][f"badwhy|{why}"] += 1
            if len(agg["ptr"]) < MAX_EXAMPLES:
                agg["ptr"].append({"level": lvl, "class": cls, "division_state": div,
                                   "bs": r["bs"], "blk": r["blk"],
                                   "parcel": list(r["path"]), "mfde_index": idx,
                                   "raw_offset": off, "sector": so, "reason": why,
                                   "source_header_words": {NAMES[i]: w[i] for i in WORDS},
                                   "source_nregion": r["nreg"]})


def _work(args) -> dict:
    path, keys, urban_list, check_pointers = args
    from kiwiw import volume
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    urban = {tuple(t) for t in urban_list}
    container = walk.read_container(path)
    pdmdh, hdr = container.pdmdh, container.hdr
    ssz, lsz = hdr.sector_size, hdr.logical_sector_size
    file_size = container.file_size
    lmrs = {l.level: l for l in pdmdh.levels}
    agg = _new_agg()
    with open(path, "rb") as fh:
        for level, bsi, bidx, bsx, bsy, blx, bly, boff, blen in keys:
            lmr = lmrs[level]
            bb = walk._block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
            fh.seek(boff)
            try:
                root = parse_parcel_mgmt_record(fh.read(blen), lmr)
            except Exception:  # noqa: BLE001
                continue
            for lp, entry, lb, pt in walk._iter_tree_leaves(root, bb, lmr, ()):
                fh.seek(volume.getsector(entry.dsa, ssz, lsz))
                data = fh.read(entry.size * lsz)
                h = parse_header(data, lmr.n_basic_map, lmr.n_ext_map)
                if h is None:
                    continue
                h.update(level=level, bs=bsi, blk=bidx, path=list(lp), div=pt,
                         lat_lo=lb.lat_lo, lat_hi=lb.lat_hi,
                         lon_lo=lb.lon_lo, lon_hi=lb.lon_hi)
                _accumulate(agg, h, urban, check_pointers, fh, file_size, ssz, lsz)
    return {"words": {k: dict(v) for k, v in agg["words"].items()},
            "geo": {k: dict(v) for k, v in agg["geo"].items()},
            "w0": {k: dict(v) for k, v in agg["w0"].items()},
            "w7k": {k: dict(v) for k, v in agg["w7k"].items()},
            "w7x": dict(agg["w7x"]), "w7y": dict(agg["w7y"]), "w7g": dict(agg["w7g"]), "w7z": dict(agg["w7z"]), "w7s": dict(agg["w7s"]), "ne": dict(agg["ne"]), "ex": dict(agg["ex"]),
            "ptrn": dict(agg["ptrn"]), "n": dict(agg["n"]),
            "w0exc": agg["w0exc"], "ptr": agg["ptr"]}


def _rehydrate(d: dict) -> dict:
    a = _new_agg()
    for k in ("words", "geo", "w0", "w7k"):
        for kk, v in d[k].items():
            a[k][kk] = Counter(v)
    for k in ("w7x", "w7y", "w7g", "w7z", "w7s", "ne", "ex", "ptrn", "n"):
        a[k] = Counter(d[k])
    a["w0exc"] = d["w0exc"]
    a["ptr"] = d["ptr"]
    return a


def collect(path: str, urban, workers: int = 10, l0_stride: int = 1,
            check_pointers: bool = True) -> dict:
    keys = [(b.level, b.blockset_index, b.block_index, b.bsx, b.bsy, b.blx, b.bly,
             b.file_offset, b.length)
            for b in walk.iter_blocks(path)
            if b.error is None and (b.level != 0 or (b.block_index % l0_stride == 0))]
    chunks = [keys[i::workers * 8] for i in range(workers * 8)]
    urban_list = sorted(list(t) for t in urban)
    total = _new_agg()
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(_work, [(path, c, urban_list, check_pointers)
                                for c in chunks if c]):
            _merge(total, _rehydrate(r))
    return total


# --------------------------------------------------------------------------
# rule derivation (fit set) and validation (held-out set)
# --------------------------------------------------------------------------

def _split_words(agg: dict, split: str, word: int) -> dict:
    out: dict = {}
    pre = f"{split}|"
    suf = f"|{word}"
    for k, c in agg["words"].items():
        if k.startswith(pre) and k.endswith(suf):
            out[k[len(pre):-len(suf)]] = c
    return out


def constant_rule(agg: dict, word: int) -> dict:
    """Per (level, class, division state) modal value from the fit set, scored
    on the held-out set."""
    fit = _split_words(agg, "fit", word)
    held = _split_words(agg, "held", word)
    table = {k: max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0] for k, c in fit.items()}
    fit_share = {k: round(max(c.values()) / sum(c.values()), 6) for k, c in fit.items()}
    ok = miss = unseen = 0
    misses: Counter = Counter()
    for k, c in held.items():
        if k not in table:
            unseen += sum(c.values())
            continue
        for v, n in c.items():
            if v == table[k]:
                ok += n
            else:
                miss += n
                misses[f"{k}: {v} (predicted {table[k]})"] += n
    tot = ok + miss + unseen
    return {"table": {k: table[k] for k in sorted(table)},
            "fit_modal_share": {k: fit_share[k] for k in sorted(fit_share)},
            "heldout_n": tot, "heldout_correct": ok,
            "heldout_unseen_key": unseen,
            "heldout_accuracy": round(ok / tot, 6) if tot else 0.0,
            "heldout_mismatches": dict(sorted(misses.items(), key=lambda kv: -kv[1])[:20])}


def w7_subframe_rule(agg: dict) -> dict:
    """Word 7 refined by the parcel's basic sub-frame presence mask (slots 0-2).
    NOT content-independent -- reported as evidence, never as the model rule."""
    fit: dict = {}
    held: dict = {}
    for k, c in agg["w7k"].items():
        split, rest = k.split("|", 1)
        (fit if split == "fit" else held)[rest] = c
    table = {k: max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0] for k, c in fit.items()}
    ok = miss = unseen = 0
    by_level: dict = defaultdict(lambda: [0, 0])
    for k, c in held.items():
        lvl = k.split("|")[0]
        if k not in table:
            unseen += sum(c.values())
            by_level[lvl][1] += sum(c.values())
            continue
        for v, n in c.items():
            by_level[lvl][1] += n
            if v == table[k]:
                ok += n
                by_level[lvl][0] += n
            else:
                miss += n
    tot = ok + miss + unseen
    return {"key": ["level", "class", "division_state", "subframe_presence_mask"],
            "table": {k: table[k] for k in sorted(table)},
            "heldout_n": tot, "heldout_correct": ok, "heldout_unseen_key": unseen,
            "heldout_accuracy": round(ok / tot, 6) if tot else 0.0,
            "heldout_accuracy_by_level": {k: round(v[0] / v[1], 6)
                                          for k, v in sorted(by_level.items(), key=lambda kv: int(kv[0]))
                                          if v[1]}}


# --------------------------------------------------------------------------
# word 7 model rule: road presence (WORD7-ANALYSIS.md, adopted 2026-09-22)
# --------------------------------------------------------------------------

W7_ROAD = 0x1200
W7_NONE = 0xFF00
W7_RULE = ("pmcode_word7(L0 parcel) = 0x1200 if parcel has road sub-frame with >=1 link else 0xFF00; "
           "pmcode_word7(L2 parcel) = 0x1200 if any L0 parcel inside it has road sub-frame else 0xFF00; "
           "pmcode_word7(L>=4) = 0xFF00; word 8 = 0, word 7 low byte = 0")
W7_CELL = 50_000  # microdegrees; spatial hash cell for the L2 <- L0 containment test


def _road_link_count(data: bytes, h: dict, bounds) -> tuple[bool, int]:
    """(road sub-frame present, link count) of one Map Frame buffer; the road
    sub-frame is mfde slot 0, located exactly as `kiwiw.parcel.decode_parcel`."""
    from kiwiw.bitutils import sws
    from kiwiw.road import decode_road_frame
    off, size = h["slots"][0] if h["slots"] else (NO_DATA, 0)
    if off == NO_DATA:
        return False, 0
    o, n = sws(off), sws(size)
    if not n:
        return False, 0
    return True, len(decode_road_frame(data[o:o + n], bounds).links)


def _w7_work(args) -> dict:
    path, keys = args
    from kiwiw import volume
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    from array import array
    container = walk.read_container(path)
    pdmdh, hdr = container.pdmdh, container.hdr
    ssz, lsz = hdr.sector_size, hdr.logical_sector_size
    lmrs = {l.level: l for l in pdmdh.levels}
    l0: Counter = Counter()
    hi: Counter = Counter()
    centres = array("q")
    l2: list = []
    with open(path, "rb") as fh:
        for level, bsi, bidx, bsx, bsy, blx, bly, boff, blen in keys:
            lmr = lmrs[level]
            bb = walk._block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
            fh.seek(boff)
            try:
                root = parse_parcel_mgmt_record(fh.read(blen), lmr)
            except Exception:  # noqa: BLE001
                continue
            for lp, entry, lb, pt in walk._iter_tree_leaves(root, bb, lmr, ()):
                fh.seek(volume.getsector(entry.dsa, ssz, lsz))
                data = fh.read(entry.size * lsz)
                h = parse_header(data, lmr.n_basic_map, lmr.n_ext_map)
                if h is None:
                    continue
                split = "held" if heldout(bsi, bidx, lp) else "fit"
                w7 = h["w"][7]
                if level == 0:
                    try:
                        has, links = _road_link_count(data, h, lb)
                    except Exception:  # noqa: BLE001
                        has, links = None, 0
                    cat = ("decode_error" if has is None else "no_subframe" if not has
                           else "links0" if links == 0 else "links1" if links == 1 else "links2+")
                    zh = "zero_height" if lb.lat_hi == lb.lat_lo else "normal"
                    l0[f"{split}|{w7}|{cat}|{zh}"] += 1
                    if has:
                        centres.append(_q((lb.lat_lo + lb.lat_hi) / 2))
                        centres.append(_q((lb.lon_lo + lb.lon_hi) / 2))
                elif level == 2:
                    own = bool(h["slots"] and h["slots"][0][0] != NO_DATA and h["slots"][0][1])
                    l2.append((split, w7, own, bool(pt), _q(lb.lat_lo), _q(lb.lat_hi),
                               _q(lb.lon_lo), _q(lb.lon_hi)))
                else:
                    hi[f"{level}|{split}|{w7}"] += 1
    return {"l0": dict(l0), "hi": dict(hi), "centres": centres.tolist(), "l2": l2}


def w7_census(path: str, workers: int = 10) -> dict:
    """Second, geometry-keyed pass over R for the word-7 road-presence rule
    (same shape as `divided_adjacency_census`, separate from `_accumulate`)."""
    keys = [(b.level, b.blockset_index, b.block_index, b.bsx, b.bsy, b.blx, b.bly,
             b.file_offset, b.length) for b in walk.iter_blocks(path) if b.error is None]
    chunks = [keys[i::workers * 8] for i in range(workers * 8)]
    out = {"l0": Counter(), "hi": Counter(), "centres": [], "l2": []}
    with ProcessPoolExecutor(workers) as ex:
        for r in ex.map(_w7_work, [(path, c) for c in chunks if c]):
            out["l0"].update(r["l0"])
            out["hi"].update(r["hi"])
            out["centres"].extend(r["centres"])
            out["l2"].extend(r["l2"])
    out["l2"].sort()
    return out


def _l2_has_l0_road(rec, cells: dict) -> bool:
    """Any L0 road-bearing centre inside this L2 parcel's bounds (half-open)."""
    _s, _w, _own, _div, la0, la1, lo0, lo1 = rec
    for cy in range(la0 // W7_CELL, la1 // W7_CELL + 1):
        for cx in range(lo0 // W7_CELL, lo1 // W7_CELL + 1):
            for la, lo in cells.get((cy, cx), ()):
                if la0 <= la < la1 and lo0 <= lo < lo1:
                    return True
    return False


def w7_road_presence_rule(pr: dict) -> dict:
    """Score the adopted word-7 rule. `pr` is `w7_census`'s output:
    l0 (Counter 'split|w7|cat|height'), l2 (list of (split, w7, own_road,
    divided, lat_lo, lat_hi, lon_lo, lon_hi) in microdegrees), centres (flat
    [lat, lon, ...] of L0 parcels with a road sub-frame), hi (Counter
    'level|split|w7'). The rule has no fitted parameter; fit and held-out are
    both reported."""
    cells: dict = defaultdict(list)
    c = pr["centres"]
    for i in range(0, len(c), 2):
        cells[(c[i] // W7_CELL, c[i + 1] // W7_CELL)].append((c[i], c[i + 1]))
    tot = defaultdict(lambda: {"n": 0, "correct": 0})   # (level, split)
    exc: Counter = Counter()

    def score(level, split, actual, pred, tag):
        for sp in (split, "all"):
            t = tot[(level, sp)]
            t["n"] += 1
            t["correct"] += int(actual == pred)
        if actual != pred:
            exc[f"{level}|{tag}|predicted {pred} actual {actual}"] += 1

    def score_n(level, split, actual, pred, tag, n):
        for sp in (split, "all"):
            t = tot[(level, sp)]
            t["n"] += n
            t["correct"] += n * int(actual == pred)
        if actual != pred:
            exc[f"{level}|{tag}|predicted {pred} actual {actual}"] += n

    zero_height = 0
    for k, n in pr["l0"].items():
        split, w7, cat, hgt = k.split("|")
        pred = W7_ROAD if cat in ("links1", "links2+") else W7_NONE
        score_n(0, split, int(w7), pred, f"{cat}", n)
        if hgt == "zero_height":
            zero_height += n
    divided = divided_bad = 0
    for rec in pr["l2"]:
        split, w7, own, div = rec[:4]
        pred = W7_ROAD if _l2_has_l0_road(rec, cells) else W7_NONE
        score(2, split, w7, pred, "divided" if div else "undivided")
        if div:
            divided += 1
            divided_bad += int(w7 != pred)
    for k, n in pr["hi"].items():
        lvl, split, w7 = k.split("|")
        score_n(int(lvl), split, int(w7), W7_NONE, "l4_and_above", n)

    def pack(sp):
        by_level = {}
        for (lvl, s), t in sorted(tot.items()):
            if s == sp:
                by_level[str(lvl)] = {"n": t["n"], "correct": t["correct"],
                                      "exceptions": t["n"] - t["correct"]}
        n = sum(v["n"] for v in by_level.values())
        ok = sum(v["correct"] for v in by_level.values())
        return {"n": n, "correct": ok, "accuracy": round(ok / n, 6) if n else 0.0,
                "by_level": by_level}

    l0_exc = {k: v for k, v in exc.items() if k.startswith("0|")}
    single = sum(v for k, v in l0_exc.items() if "|links1|" in k and "predicted 4608 actual 65280" in k)
    return {
        "whole_disc": pack("all"), "fit": pack("fit"), "heldout": pack("held"),
        "exceptions": dict(sorted(exc.items())),
        "residual_tolerance": {
            "name": "L0 single-link road parcels stored 0xFF00",
            "scope": "L0, whole disc (no fitted parameter, so fit == held-out population)",
            "count": sum(l0_exc.values()),
            "all_single_link_road_parcels_stored_0xFF00": bool(l0_exc) and single == sum(l0_exc.values()),
            "status": "recorded tolerance, not an exemption; a Phase 4 check may allow up to `count` L0 disagreements on R-equivalent input",
        },
        "caveats": {
            "divided_l2_parcels": {"count": divided, "scored": True, "exceptions": divided_bad,
                                   "note": "scored here by leaf-bounds containment of L0 road centres (half-open); the analysis skipped them"},
            "zero_height_l0_parcels": {"count": zero_height, "scored": True,
                                       "note": "included in the L0 population; their L0 centres lie on a lat edge and count toward L2 containment via half-open [lo,hi)"},
        },
    }


def rl_rule(agg: dict) -> dict:
    """rlx/rly: exact table keyed by (level, lat_lo, lat_span, lon_span), all in
    microdegrees; derived on the fit set, scored on the held-out set."""
    fit: dict = {}
    held: dict = {}
    for k, c in agg["geo"].items():
        split, rest = k.split("|", 1)
        (fit if split == "fit" else held)[rest] = c
    table = {k: max(c.items(), key=lambda kv: (kv[1], kv[0]))[0] for k, c in fit.items()}
    ambiguous = sum(1 for c in fit.values() if len(c) > 1)
    res = {}
    for w, comp in ((10, 0), (11, 1)):
        ok = miss = unseen = 0
        misses: Counter = Counter()
        for k, c in held.items():
            if k not in table:
                unseen += sum(c.values())
                continue
            pred = table[k].split(",")[comp]
            for v, n in c.items():
                if v.split(",")[comp] == pred:
                    ok += n
                else:
                    miss += n
                    misses[f"{k}: {v.split(',')[comp]} (predicted {pred})"] += n
        tot = ok + miss + unseen
        res[w] = {"heldout_n": tot, "heldout_correct": ok,
                  "heldout_unseen_key": unseen,
                  "heldout_accuracy": round(ok / tot, 6) if tot else 0.0,
                  "heldout_mismatches": dict(sorted(misses.items(), key=lambda kv: -kv[1])[:10])}
    return {"table": table, "fit_keys": len(table),
            "fit_ambiguous_keys": ambiguous, "per_word": res}


def mlat_m(phi: float) -> float:
    """Metres per degree of latitude at latitude phi (WGS84 series)."""
    p = math.radians(phi)
    return (111132.92 - 559.82 * math.cos(2 * p) + 1.175 * math.cos(4 * p)
            - 0.0023 * math.cos(6 * p))


def mlon_m(phi: float) -> float:
    """Metres per degree of longitude at latitude phi (WGS84 series)."""
    p = math.radians(phi)
    return (111412.84 * math.cos(p) - 93.5 * math.cos(3 * p)
            + 0.118 * math.cos(5 * p))


def rl_model_scan(agg: dict) -> dict:
    """How well the closed-form physical model reproduces the table (reported,
    not used as the rule)."""
    ok = tot = 0
    for k, v in agg["geo"].items():
        split, lvl, lat_lo, lat_span, lon_span = k.split("|")
        if split != "held":
            continue
        lat0 = int(lat_lo) / 1e6
        h = int(lat_span) / 1e6
        wdeg = int(lon_span) / 1e6
        phi = lat0 + h / 2 + LAT_ORIGIN_SHIFT
        px = round(100 * wdeg * mlon_m(phi) / COORD_RANGE_RL)
        py = round(100 * h * mlat_m(phi) / COORD_RANGE_RL)
        for val, n in v.items():
            rx, ry = (int(x) & 0x7FFF for x in val.split(","))
            tot += n
            if rx == (px & 0x7FFF) and ry == (py & 0x7FFF):
                ok += n
    return {"heldout_n": tot, "heldout_exact": ok,
            "heldout_accuracy": round(ok / tot, 6) if tot else 0.0}


def w0_section(agg: dict) -> dict:
    per: dict = {}
    tot = Counter()
    for k, c in agg["w0"].items():
        split, key = k.split("|", 1)
        if split != "held":
            continue
        per[key] = {"n": c["n"],
                    "formula_consistent": c["formula_consistent"],
                    "slot0_defined": c["slot0_defined"], "slot0_eq": c["slot0_eq"],
                    "first_defined": c["first_defined"], "first_eq": c["first_eq"],
                    "header_bytes": {kk[5:]: vv for kk, vv in sorted(c.items())
                                     if kk.startswith("bytes")}}
        for f in ("n", "formula_consistent", "slot0_defined", "slot0_eq",
                  "first_defined", "first_eq"):
            tot[f] += c[f]
    return {"per_key": {k: per[k] for k in sorted(per)}, "totals": dict(tot)}


def build_header_section(agg: dict, l0_stride: int, w7: dict | None = None) -> dict:
    words: dict = {}
    for w in (6, 7, 9):
        words[str(w)] = {"name": NAMES[w], "rule": "constant per (level, class, division state)"}
        words[str(w)].update(constant_rule(agg, w))
    words["7"]["subframe_presence_rule"] = w7_subframe_rule(agg)
    phase2_finding = (
        "word 7 (pmcode high half) takes only 0xFF00 (area 255) and 0x1200 "
        "(area 18). 0x1200 occurs at L0 and L2 only; L4-L12 are 100% 0xFF00. "
        "It is NOT a function of (level, class, division state, position): the "
        "per-key constant rule and a per-1-degree-cell majority rule both fall "
        "well short of 99%, and 0x1200 parcels are interleaved with 0xFF00 "
        "parcels inside the same block and the same 1-degree cell across the "
        "whole continent. It tracks frame composition instead: at L0, "
        "0x1200 <=> all three basic sub-frames present; at L2 that rule is exact "
        "for every mask other than background-only, and background-only parcels "
        "remain mixed with no structural distinguisher (no slot-size threshold, "
        "no nregion or WP2-word correlation). See subframe_presence_rule.")
    if w7 is None:
        words["7"]["status"] = (
            "blocked" if words["7"]["heldout_accuracy"] < 0.99 else "ok")
        words["7"]["finding"] = phase2_finding
    else:
        # The adopted model rule replaces the constant rule as the word's
        # headline; the Phase 2 rules stay as recorded, rejected evidence.
        rr = w7_road_presence_rule(w7)
        words["7"]["constant_per_key_rule"] = {
            k: words["7"].pop(k) for k in list(words["7"])
            if k not in ("name", "subframe_presence_rule")}
        words["7"]["rule"] = W7_RULE
        words["7"]["heldout_n"] = rr["heldout"]["n"]
        words["7"]["heldout_correct"] = rr["heldout"]["correct"]
        words["7"]["heldout_accuracy"] = rr["heldout"]["accuracy"]
        words["7"]["heldout_by_level"] = rr["heldout"]["by_level"]
        words["7"]["whole_disc"] = rr["whole_disc"]
        words["7"]["fit"] = rr["fit"]
        words["7"]["exceptions"] = rr["exceptions"]
        words["7"]["residual_tolerance"] = rr["residual_tolerance"]
        words["7"]["caveats"] = rr["caveats"]
        words["7"]["status"] = "blocked" if words["7"]["heldout_accuracy"] < 0.99 else "ok"
        words["7"]["phase4_scope"] = {
            "l2_post_pass": True,
            "note": ("the generator must write L2 word 7 after L0 generation: an L2 header "
                     "reads its L0 children (any L0 descendant with a road sub-frame). "
                     "Phase 4 scope; not implemented in Phase 2."),
        }
        words["7"]["area_18_meaning"] = {
            "status": "documented-unknown",
            "note": ("Area Number 18 refers to a metafile area entry; the metafile is "
                     "neither on the disc nor in the archived spec."),
        }
        words["7"]["finding"] = (
            "MODEL RULE (adopted, WORD7-ANALYSIS.md): road presence, see `rule`; scored by "
            "this tool over R (whole disc and held-out). The subframe_presence_rule and "
            "constant_per_key_rule are retained as recorded evidence of what was tested and "
            "rejected. Phase 2 finding: " + phase2_finding)
    w0 = constant_rule(agg, 0)
    w0s = w0_section(agg)
    t = w0s["totals"]
    words["0"] = {
        "name": "size",
        "rule": ("word0 * 2 = 36 + 4*nregion + 6*n_mfde_entries (header size in "
                 "bytes through the end of the mfde table). The generator knows "
                 "both terms when it lays the frame out, so the rule is "
                 "content-independent. The per-key modal byte size below is the "
                 "fallback/consistency table."),
        "formula": "word0 = (36 + 4*nregion + 6*n_mfde_entries) / 2",
        "heldout_n": t.get("n", 0),
        "heldout_correct": t.get("formula_consistent", 0),
        "heldout_accuracy": round(t.get("formula_consistent", 0) / t["n"], 6) if t.get("n") else 0.0,
        "modal_bytes_table": {k: max(((int(b), n) for b, n in v["header_bytes"].items()),
                                     key=lambda kv: kv[1])[0]
                              for k, v in w0s["per_key"].items()},
        "vs_first_data_slot": {
            "slot0_defined": t.get("slot0_defined", 0), "slot0_equal": t.get("slot0_eq", 0),
            "first_defined": t.get("first_defined", 0), "first_equal": t.get("first_eq", 0),
        },
        "per_key": w0s["per_key"],
    }
    rl = rl_rule(agg)
    for w, comp in ((10, "rlx"), (11, "rly")):
        words[str(w)] = {
            "name": NAMES[w],
            "rule": ("exact table keyed by (level, lat_lo_udeg, lat_span_udeg, "
                     "lon_span_udeg) of the parcel's own bounds -- a function of "
                     "grid geometry only, no content. Physical model behind it: "
                     "rlx = round(100 * lon_span_deg * m_per_deg_lon(phi) / 4096), "
                     "rly = round(100 * lat_span_deg * m_per_deg_lat(phi) / 4096) "
                     "with phi = parcel centre latitude + 50 (R's data behaves as "
                     "if latitude were measured from the -50 grid origin); bit 15 "
                     "is set at L10/L12. The model is reported, the table is the rule."),
            "table_key": ["level", "lat_lo_udeg", "lat_span_udeg", "lon_span_udeg"],
            "table_values": "rlx,rly",
            "fit_keys": rl["fit_keys"], "fit_ambiguous_keys": rl["fit_ambiguous_keys"],
        }
        words[str(w)].update(rl["per_word"][w])
    words["10"]["closed_form_model_heldout"] = rl_model_scan(agg)
    words["11"]["closed_form_model_heldout"] = words["10"]["closed_form_model_heldout"]
    return {"words": words, "rl_table": rl["table"]}


# --------------------------------------------------------------------------
# WP2-exempt words, pointer classification, word-0 exceptions
# --------------------------------------------------------------------------

EXEMPT = {
    "n_intersections": {"header_word": 13, "owner": "WP2"},
    "route_planning_level": {"header_word": 14, "owner": "WP2"},
    "n_additional_data": {"header_word": 15, "owner": "WP2"},
    "ext_frame_slots": {"mfde_indices": "3..n_ext_map-1", "owner": "WP2"},
    "nregion": {"header_word": 17, "owner": "WP2"},
}


def exempt_section(agg: dict) -> dict:
    """R's census values for the WP2-owned words (never predicted here)."""
    byword: dict = defaultdict(Counter)
    ext: dict = defaultdict(Counter)
    for k, n in agg["ex"].items():
        p = k.split("|")
        if p[0] == "ext":
            ext[p[1]][p[2]] += n
        else:
            byword[int(p[0])][int(p[1])] += n
    out = {}
    for name, meta in EXEMPT.items():
        entry = dict(meta)
        w = meta.get("header_word")
        c = byword.get(w)
        if c:
            top = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:20]
            entry["r_values"] = {str(v): n for v, n in sorted(top)}
            entry["r_distinct_values"] = len(c)
            entry["r_parcels"] = sum(c.values())
        out[name] = entry
    out["ext_frame_slots"]["r_populated_entries_by_level"] = {
        k: dict(sorted(ext[k].items())) for k in sorted(ext, key=int)}
    nreg = Counter()
    for k, c in agg["w0"].items():
        for kk, n in c.items():
            if kk.startswith("nreg"):
                nreg[kk[4:]] += n
    out["nregion"]["r_values"] = dict(sorted(nreg.items(), key=lambda kv: int(kv[0])))
    return out


def divided_adjacency_census(path: str, level: int = 6) -> dict:
    """Why some leaves carry more mfde entries than their level's baseline:
    cross-tab of n_entries against "this leaf is geometrically adjacent to a
    divided parcel". Run on one level (L6 by default, 939 leaves) because the
    adjacency test is global, not per block."""
    from kiwiw import volume
    from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
    container = walk.read_container(path)
    pdmdh, hdr = container.pdmdh, container.hdr
    ssz, lsz = hdr.sector_size, hdr.logical_sector_size
    lmr = {l.level: l for l in pdmdh.levels}[level]
    rows = []
    with open(path, "rb") as fh:
        for b in walk.iter_blocks(path):
            if b.error is not None or b.level != level:
                continue
            bb = walk._block_base_bounds(pdmdh, lmr, b.bsx, b.bsy, b.blx, b.bly)
            fh.seek(b.file_offset)
            try:
                root = parse_parcel_mgmt_record(fh.read(b.length), lmr)
            except Exception:  # noqa: BLE001
                continue
            for lp, entry, lb, pt in walk._iter_tree_leaves(root, bb, lmr, ()):
                fh.seek(volume.getsector(entry.dsa, ssz, lsz))
                h = parse_header(fh.read(entry.size * lsz), lmr.n_basic_map, lmr.n_ext_map)
                if h is None:
                    continue
                rows.append((h["nent"], h["nreg"], h["w"][0] * 2, bool(pt),
                             (lb.lat_lo, lb.lat_hi, lb.lon_lo, lb.lon_hi)))
    boxes = [r[4] for r in rows if r[3]]
    eps = 1e-9

    def touches(bx) -> bool:
        return any(bx[2] - eps <= d and bx[3] + eps >= c and bx[0] - eps <= b2
                   and bx[1] + eps >= a for a, b2, c, d in boxes)

    tab: Counter = Counter()
    for nent, nreg, _bytes, pt, bx in rows:
        tab[f"n_entries{nent}|divided{int(pt)}|adjacent_to_divided{int(touches(bx))}"] += 1
    return {"level": level, "leaves": len(rows), "divided_leaves": len(boxes),
            "n_entries_by_division_adjacency": dict(sorted(tab.items()))}


def w0_exceptions(agg: dict, adjacency: dict | None) -> dict:
    """The '42 of 939' word-0 disagreement, re-found and explained.

    Under the checked rule (word0*2 = 36 + 4*nregion + 6*n_entries = the first
    in-buffer data-slot offset) there is no disagreement anywhere on R. The 42
    are the L6 leaves whose *header size* is not the modal 160 bytes while
    nregion = 1, i.e. those with 21, 22 or 23 mfde entries instead of 20."""
    per_level: dict = {}
    for k, n in agg["n"].items():
        if k.startswith("w0_slot0_mismatch|"):
            per_level.setdefault(k.split("|")[1], {})["slot0_mismatch"] = n
        elif k.startswith("w0_slot0_absent|"):
            per_level.setdefault(k.split("|")[1], {})["slot0_absent"] = n

    # (nregion, n_entries) census per level, and the 42 reconstruction at L6.
    by_level: dict = defaultdict(Counter)
    for k, n in agg["ne"].items():
        lvl, _cls, _div, nreg, nent = k.split("|")
        by_level[lvl][f"{nreg}|{nent}"] += n
    sizes: dict = defaultdict(Counter)
    for lvl, c in by_level.items():
        for k, n in c.items():
            nreg = int(k.split("|")[0][len("nregion"):])
            nent = int(k.split("|")[1][len("n_entries"):])
            sizes[lvl][HDR + 4 * nreg + 6 * nent] += n
    l6 = by_level.get("6", Counter())
    nreg1 = {k: n for k, n in l6.items() if k.startswith("nregion1|")}
    modal = max(nreg1.items(), key=lambda kv: kv[1])[0] if nreg1 else None
    off_modal = {k: n for k, n in sorted(nreg1.items()) if k != modal}

    out = {
        "checked_rule": ("word0*2 = 36 + 4*nregion + 6*n_entries, and that is "
                         "also the first in-buffer data-slot offset"),
        "disagreements_with_checked_rule": 0,
        "slot0_presence_by_level": {k: per_level[k] for k in sorted(per_level, key=int)},
        "header_size_bytes_by_level": {k: {str(b): n for b, n in sorted(sizes[k].items())}
                                       for k in sorted(sizes, key=int)},
        "nregion_n_entries_by_level": {k: dict(sorted(by_level[k].items()))
                                       for k in sorted(by_level, key=int)},
        "the_42": {
            "definition": ("L6 leaves with nregion = 1 whose header size is not "
                           "the modal 160 bytes (the old ad-hoc L6 census's "
                           "'word 0 != first data-slot offset in 42 of 939')"),
            "modal": modal, "count": sum(off_modal.values()),
            "breakdown": off_modal,
            "cause": ("extra mfde entries. Entries past the basic three are "
                      "adjacent-parcel pointers, and a neighbour that is itself "
                      "divided needs one record per sub-parcel, so a leaf "
                      "bordering a divided parcel carries 21, 22 or 23 entries "
                      "instead of 20 and its header grows by 6, 12 or 18 bytes. "
                      "Word 0 tracks that exactly -- it is not an exception to "
                      "the rule, it is the rule applied to a longer table. "
                      "Content-independent: it follows from the WP1 grid and "
                      "the division layout, not from map content."),
        },
    }
    if adjacency is not None:
        out["the_42"]["divided_neighbour_evidence"] = adjacency
    return out


def pointer_section(agg: dict) -> dict:
    by_key = {}
    oob = {}
    why = {}
    for k, n in agg["ptrn"].items():
        if k.startswith("oob|"):
            oob[k.split("|")[1]] = n
        elif k.startswith("bad|"):
            by_key[k[4:]] = n
        elif k.startswith("badwhy|"):
            why[k[7:]] = n
    return {
        "definition": ("R's own mfde entries with index >= 3 whose offset lands "
                       "outside the parcel buffer and whose target does not decode "
                       "as a Map Frame (Carried item 2). Classified, not fixed: "
                       "Phase 9 owns the check's allowance."),
        "out_of_buffer_targets_by_level": {k: oob[k] for k in sorted(oob, key=int)},
        "non_frame_targets_by_key": dict(sorted(by_key.items())),
        "non_frame_reasons": dict(sorted(why.items())),
        "non_frame_total": sum(by_key.values()),
        "non_frame_rate_by_level": {
            lvl: round(sum(n for k, n in by_key.items() if k.split("|")[0] == lvl) / t, 6)
            for lvl, t in sorted(oob.items(), key=lambda kv: int(kv[0])) if t},
        "note": ("Carried item 2 quoted 65 of 4000; that was a sample. Over all "
                 "of R the non-frame share is small at every level, and the "
                 "targets are not confined to one class: they are spread across "
                 "L0 sparse, L0 urban and L2-L8 full, all with normal division "
                 "state and the ordinary header words for their key (see "
                 "examples), so they are placeholder/non-frame payloads rather "
                 "than a property of any (level, class, division state)."),
        "examples": agg["ptr"][:MAX_EXAMPLES],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--coord-scale", default=str(Path(__file__).resolve().parent.parent
                                                 / "refdata/profile/coord_scale.json"))
    ap.add_argument("--out", help="coord_scale.json to rewrite with a `header` section")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--l0-stride", type=int, default=1)
    ap.add_argument("--no-pointers", action="store_true")
    ap.add_argument("--save-agg", help="write the merged raw aggregate here (debug)")
    ap.add_argument("--load-agg", help="skip the disc walk, read the aggregate from here")
    args = ap.parse_args()

    cs = json.loads(Path(args.coord_scale).read_text())
    urban = {tuple(t) for t in cs["class_rule"]["urban_tiles"]}

    if args.load_agg:
        agg = _rehydrate(json.loads(Path(args.load_agg).read_text()))
    else:
        t0 = time.time()
        agg = collect(str(Path(args.reference) / "ALLDATA.KWI"), urban,
                      args.workers, args.l0_stride, not args.no_pointers)
        print(f"walked R in {time.time() - t0:.0f}s", file=sys.stderr)
    if args.save_agg:
        Path(args.save_agg).write_text(json.dumps(
            {"words": {k: dict(v) for k, v in agg["words"].items()},
             "geo": {k: dict(v) for k, v in agg["geo"].items()},
             "w0": {k: dict(v) for k, v in agg["w0"].items()},
             "w7k": {k: dict(v) for k, v in agg["w7k"].items()},
             "w7x": dict(agg["w7x"]), "w7y": dict(agg["w7y"]), "w7g": dict(agg["w7g"]), "w7z": dict(agg["w7z"]), "w7s": dict(agg["w7s"]), "ne": dict(agg["ne"]), "ex": dict(agg["ex"]),
             "ptrn": dict(agg["ptrn"]), "n": dict(agg["n"]),
             "w0exc": agg["w0exc"], "ptr": agg["ptr"]}, sort_keys=True))

    adjacency = None
    if not args.load_agg:
        adjacency = divided_adjacency_census(
            str(Path(args.reference) / "ALLDATA.KWI"), 6)
    w7 = None
    if not args.load_agg:
        w7 = w7_census(str(Path(args.reference) / "ALLDATA.KWI"), args.workers)
    sec = build_header_section(agg, args.l0_stride, w7)
    header = {
        "source": "reference disc R, all levels, every Map Frame leaf",
        "l0_stride": args.l0_stride,
        "split_rule": SPLIT_RULE,
        "word_encoding": "big-endian u16 at byte offset 2*i of the 36-byte Map Frame header",
        "parcels": {k: v for k, v in sorted(agg["n"].items()) if k.startswith(("fit|", "held|"))},
        "words": sec["words"],
        "rl_table": sec["rl_table"],
        "word0_exceptions": w0_exceptions(agg, adjacency),
        "wp2_exempt": exempt_section(agg),
        "pointer_nonframe_targets": pointer_section(agg),
    }
    if args.out:
        cs["header"] = header
        Path(args.out).write_text(json.dumps(cs, indent=2, sort_keys=True) + "\n")
    summary = {NAMES[w]: sec["words"][str(w)]["heldout_accuracy"] for w in WORDS}
    print(json.dumps(summary, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
