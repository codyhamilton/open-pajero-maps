"""D1 block walker equivalence (plan 04, Phase 2, brief 2-02): `kw_d1_blocks`
(tree walk, bounds arithmetic, sparse-tile / divided-parent frame rules, row-band
filter, then the 2-01 frame decode, all in one C call per block band) equals
`harness.walk` + `parcel.decode_parcel` on the reference discs G and R.

Python is the oracle (the second of the two permitted Python-oracle uses,
DESIGN.md Phase 2). The sample of leaves is deterministic: the rule, its seed and
the resulting list are committed in `fixtures/d1_sample.json`
(`test_sample_rule_reproduces` re-derives the list from the rule; regenerate with
`D1_SAMPLE_WRITE=1`). A disc that is absent skips (reported `blocked` by the
brief's evidence rule, never a pass). Goldens: they hold frames only (no block
level), so test_d1_frames.py covers them.
"""
from __future__ import annotations

import json
import math
import os
import random
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness import walk
from kiwiw import cenc
from kiwiw.model import BoundingBox, MeshLocation
from kiwiw.parcel import decode_parcel
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
from test_d1_frames import assert_same, build_parcel
from tools import quantisation_roundtrip as qr

pytestmark = pytest.mark.skipif(cenc._load_lib() is None, reason="no C compiler")

REPO = Path(__file__).resolve().parents[2]
SAMPLE = Path(__file__).resolve().parent / "fixtures" / "d1_sample.json"
DISCS = {"G": REPO / "output" / "scratch-3-11" / "G" / "ALLDATA.KWI",
         "R": Path("/run/media/codyh/464210-8480/ALLDATA.KWI")}

# ---- the sample rule (recorded verbatim in d1_sample.json) -----------------
SEED = 20260930
QUOTA = 6              # leaves per (level, frame class)
PER_BLOCK = 3          # at most this many per class from one block
MAX_SCAN = 60          # shuffled blocks scanned per level
WHOLE = 2              # complete blocks compared per level
CLASSES = ("leaf", "l0_sparse_tile", "divided_parent")
RULE = (
    "Per disc, per level: take that level's non-error blocks in table order, shuffle with "
    "random.Random(f'{seed}:{disc}:{level}'), scan at most MAX_SCAN of them; from each block "
    "take, for each frame class (leaf, l0_sparse_tile, divided_parent), min(PER_BLOCK, QUOTA - "
    "taken) leaves via rng.sample over that block's leaves of the class (harness.walk order), "
    "until every class holds QUOTA leaves. Then, if no sampled leaf has a road link / a "
    "background polygon (shape_class 2) / a name record, scan every level's shuffled blocks "
    "(at most 3000 leaves) and add the first leaf that has it. whole_blocks: the first WHOLE "
    "blocks of each level's shuffled order that have a leaf; they are compared in full "
    "(every leaf, field for field), unbanded and banded.")
CONSTANTS = {"QUOTA": QUOTA, "PER_BLOCK": PER_BLOCK, "MAX_SCAN": MAX_SCAN, "WHOLE": WHOLE}


def _hex(x: float) -> str:
    return struct.pack("<d", x).hex()


# ------------------------------------------------------------ python oracle

class Disc:
    """One reference disc: container, blocks, and the Python oracle on them."""

    def __init__(self, name: str, path: Path):
        self.name, self.path = name, path
        self.container = walk.read_container(str(path))
        self.blocks = list(walk.iter_blocks(str(path)))
        self.lmrs = {m.level: m for m in self.container.pdmdh.levels}
        self.region = np.memmap(path, dtype=np.uint8, mode="r")
        self.by_key = {(b.level, b.blockset_index, b.block_index): b for b in self.blocks}
        self.lattice = {}
        self.fh = open(path, "rb")

    def key(self, b):
        return (b.level, b.blockset_index, b.block_index, b.bsx, b.bsy, b.blx, b.bly,
                b.file_offset, b.length)

    def lat(self, level):
        if level not in self.lattice:
            self.lattice[level] = qr.Lattice(level)
        return self.lattice[level]

    def py_items(self, wb):
        """Leaves of one block as walk yields them, no decode: dicts."""
        lmr = self.lmrs[wb.level]
        bb = walk._block_base_bounds(self.container.pdmdh, lmr, wb.bsx, wb.bsy, wb.blx, wb.bly)
        cache: dict = {}
        out = []
        for path, entry, lb, ptype in walk._iter_tree_leaves(wb.root, bb, lmr, ()):
            fb, cls = walk._leaf_frame(wb.root, wb.level, ptype, path, lb, bb, lmr, cache)
            out.append(dict(path=path, entry=entry, bounds=lb, ptype=ptype, fb=fb, cls=cls,
                            rng=walk.leaf_frame_range(wb.level, ptype, path, cls)))
        return out

    def py_decode(self, wb, it):
        """(Parcel | None, MeshLocation) exactly as the walk loop decodes a leaf."""
        hdr = self.container.hdr
        lmr = self.lmrs[wb.level]
        moff = walk.volume.getsector(it["entry"].dsa, hdr.sector_size, hdr.logical_sector_size)
        mlen = it["entry"].size * hdr.logical_sector_size
        self.fh.seek(moff)
        data = self.fh.read(mlen)
        loc = MeshLocation(level=wb.level, parcel_type=it["ptype"],
                           blockset_index=wb.blockset_index, block_index=wb.block_index,
                           parcel_index=it["path"][-1],
                           bounds=walk.with_range(it["fb"], it["rng"]),
                           sector_addr=it["entry"].dsa, size_logical_sectors=it["entry"].size)
        try:
            return decode_parcel(loc, data, n_basic_map=lmr.n_basic_map,
                                 n_ext_map=lmr.n_ext_map), loc
        except Exception:  # noqa: BLE001 -- the oracle's failure, D1 must fail too
            return None, loc


def _features(p) -> dict:
    return dict(road=bool(p and p.road and p.road.links),
                bg_poly=bool(p and p.background and any(s.shape_class == 2
                                                        for s in p.background.shapes)),
                name=bool(p and p.name and p.name.records),
                bg=bool(p and p.background and p.background.shapes))


def make_sample(d: Disc) -> dict:
    """The committed sample, derived from the rule (see RULE)."""
    levels = sorted({b.level for b in d.blocks})
    orders = {}
    leaves, whole, seen = [], [], set()
    for level in levels:
        rng = random.Random(f"{SEED}:{d.name}:{level}")
        order = [b for b in d.blocks if b.level == level and b.error is None]
        rng.shuffle(order)
        orders[level] = order
        have = dict.fromkeys(CLASSES, 0)
        for wb in order[:MAX_SCAN]:
            items = d.py_items(wb)
            if len(whole) < 0 or sum(1 for w in whole if w[0] == level) < WHOLE and items:
                whole.append([level, wb.blockset_index, wb.block_index])
            for cls in CLASSES:
                avail = [it for it in items if it["cls"] == cls]
                k = min(PER_BLOCK, QUOTA - have[cls], len(avail))
                for it in rng.sample(avail, k):
                    leaves.append([level, wb.blockset_index, wb.block_index, list(it["path"]), cls])
                    seen.add((wb.level, wb.blockset_index, wb.block_index, it["path"]))
                have[cls] += k
            if all(v >= QUOTA for v in have.values()) and \
                    sum(1 for w in whole if w[0] == level) >= WHOLE:
                break
    feats = dict.fromkeys(("road", "bg_poly", "name"), False)
    for lv, bs, bi, path, cls in leaves:
        wb = d.by_key[(lv, bs, bi)]
        it = next(i for i in d.py_items(wb) if list(i["path"]) == path)
        for k, v in _features(d.py_decode(wb, it)[0]).items():
            if k in feats:
                feats[k] = feats[k] or v
    budget = 3000
    for level in levels:
        for wb in orders[level]:
            if all(feats.values()) or budget <= 0:
                break
            for it in d.py_items(wb):
                if all(feats.values()) or budget <= 0:
                    break
                budget -= 1
                f = _features(d.py_decode(wb, it)[0])
                if any(f[k] and not feats[k] for k in feats):
                    leaves.append([level, wb.blockset_index, wb.block_index, list(it["path"]),
                                   it["cls"]])
                    for k in feats:
                        feats[k] = feats[k] or f[k]
    return {"disc_size": d.path.stat().st_size, "n_blocks": {
                str(lv): sum(1 for b in d.blocks if b.level == lv) for lv in levels},
            "whole_blocks": whole, "leaves": leaves}


_DISCS: dict = {}


def disc(name: str) -> Disc:
    if not DISCS[name].exists():
        pytest.skip(f"{name} disc absent ({DISCS[name]})")
    if name not in _DISCS:
        _DISCS[name] = Disc(name, DISCS[name])
    return _DISCS[name]


def committed(name: str) -> dict:
    return json.loads(SAMPLE.read_text())["discs"][name]


# ---------------------------------------------------------------- comparison

def _row_loc(row, wrow) -> MeshLocation:
    rng = int(wrow["frame_range"]) or None
    fb = BoundingBox(float(wrow["flat_lo"]), float(wrow["flat_hi"]), float(wrow["flon_lo"]),
                     float(wrow["flon_hi"]), coord_range=rng)
    depth = int(wrow["depth"])
    return MeshLocation(level=int(wrow["level"]), parcel_type=int(wrow["parcel_type"]),
                        blockset_index=int(wrow["blockset_index"]),
                        block_index=int(wrow["block_index"]),
                        parcel_index=int(wrow[f"p{depth - 1}"]), bounds=fb,
                        sector_addr=int(wrow["dsa"]), size_logical_sectors=int(wrow["size"]))


def _path(w) -> tuple:
    return tuple(int(w[f"p{i}"]) for i in range(int(w["depth"])))


def _compare_leaf(d: Disc, cols, w, wb, it, what, parcel=None, loc=None):
    """One D1 walk row vs the Python leaf `it` of block `wb`, every field."""
    assert _path(w) == tuple(it["path"]), f"{what}: path"
    assert int(w["parcel_type"]) == it["ptype"], f"{what}: parcel_type"
    for a, b in (("lat_lo", it["bounds"].lat_lo), ("lat_hi", it["bounds"].lat_hi),
                 ("lon_lo", it["bounds"].lon_lo), ("lon_hi", it["bounds"].lon_hi),
                 ("flat_lo", it["fb"].lat_lo), ("flat_hi", it["fb"].lat_hi),
                 ("flon_lo", it["fb"].lon_lo), ("flon_hi", it["fb"].lon_hi)):
        assert _hex(float(w[a])) == _hex(b), f"{what}: {a} {float(w[a])!r} != {b!r}"
    assert ("leaf", "l0_sparse_tile", "divided_parent")[int(w["frame_class"])] == it["cls"], \
        f"{what}: frame_class"
    assert int(w["frame_range"]) == (it["rng"] or 0), f"{what}: frame_range"
    hdr = d.container.hdr
    assert int(w["off"]) == walk.volume.getsector(it["entry"].dsa, hdr.sector_size,
                                                  hdr.logical_sector_size), f"{what}: off"
    assert int(w["len"]) == it["entry"].size * hdr.logical_sector_size, f"{what}: len"
    lat = d.lat(wb.level)
    mid_lat = (it["bounds"].lat_lo + it["bounds"].lat_hi) / 2
    mid_lon = (it["bounds"].lon_lo + it["bounds"].lon_hi) / 2
    assert int(w["iy"]) == math.floor(float(lat.gy(mid_lat)) / qr.RAW), f"{what}: iy"
    assert int(w["ix"]) == math.floor(float(lat.gx(mid_lon)) / qr.RAW), f"{what}: ix"
    if parcel is None and loc is None:
        parcel, loc = d.py_decode(wb, it)
    fr = cols.t["frame"][int(w["frame"])]
    if parcel is None:
        assert int(w["status"]) == 2 and int(fr["status"]) != 0, \
            f"{what}: python failed to decode but D1 status {int(w['status'])}/{int(fr['status'])}"
        return None
    assert int(w["status"]) == 0 and int(fr["status"]) == 0, \
        f"{what}: D1 failed (frame status {int(fr['status'])}) where python decoded"
    got = build_parcel(cols, int(w["frame"]), d.region, _row_loc(None, w))
    assert_same(parcel, got, what)
    return parcel


def _walk_rows(cols, bidx):
    w = cols.t["walk"]
    return w[w["block"] == bidx]


def _planned():
    """Counter: `ranges` (block-band calls) must equal the calls the test plans."""
    return cenc.d1_stats()


# ----------------------------------------------------------------------- tests

@pytest.mark.parametrize("name", ["G", "R"])
def test_sample_rule_reproduces(name):
    d = disc(name)
    got = make_sample(d)
    if os.environ.get("D1_SAMPLE_WRITE"):
        data = json.loads(SAMPLE.read_text()) if SAMPLE.exists() else {}
        data.update(rule=RULE, seed=SEED, constants=CONSTANTS)
        data.setdefault("discs", {})[name] = got
        SAMPLE.write_text(json.dumps(data, indent=0, sort_keys=True) + "\n")
    want = committed(name)
    assert got["disc_size"] == want["disc_size"], "disc differs from the one the sample came from"
    assert got == want, "sample rule no longer reproduces the committed list"


@pytest.mark.parametrize("name", ["G", "R"])
def test_d1_walker_equals_python(name, capsys):
    d = disc(name)
    spec = committed(name)
    assert json.loads(SAMPLE.read_text())["rule"] == RULE
    levels = sorted({s[0] for s in spec["leaves"]} | {w[0] for w in spec["whole_blocks"]})
    s0 = cenc.d1_stats()
    planned = 0
    counts = {"sampled": {}, "whole": {}, "banded": {}, "classes": {}, "layers": {}}
    sampled_by_block: dict = {}
    for lv, bs, bi, path, cls in spec["leaves"]:
        sampled_by_block.setdefault((lv, bs, bi), []).append((tuple(path), cls))
    whole_by_level: dict = {}
    for lv, bs, bi in spec["whole_blocks"]:
        whole_by_level.setdefault(lv, []).append((lv, bs, bi))
    layers = dict.fromkeys(("frame", "road", "background", "name"), 0)

    for level in levels:
        keys = list(whole_by_level.get(level, []))
        keys += [k for k in sampled_by_block if k[0] == level and k not in keys]
        wbs = [d.by_key[k] for k in keys]
        rows = cenc.d1_block_rows([d.key(b) for b in wbs], d.container)
        cols = cenc.d1_blocks(d.region, rows)
        planned += 1
        for bidx, (k, wb) in enumerate(zip(keys, wbs)):
            wrows = _walk_rows(cols, bidx)
            items = d.py_items(wb)
            by_path = {tuple(i["path"]): i for i in items}
            assert len(wrows) == len(items), f"{name} {k}: leaf count {len(wrows)} != {len(items)}"
            if k in whole_by_level.get(level, []):
                # the checker's own walk: every leaf, in order, decoded
                key = d.key(wb)
                py = list(qr._iter_leaves(str(d.path), d.container, key, d.lat(level),
                                          -(10 ** 9), 10 ** 9))
                assert len(py) == len(wrows), f"{name} {k}: checker walk leaf count"
                for n, (wp, w) in enumerate(zip(py, wrows)):
                    assert _path(w) == wp.leaf_path, f"{name} {k} leaf #{n}: order/path"
                    it = by_path[wp.leaf_path]
                    _compare_leaf(d, cols, w, wb, it, f"{name} L{level} {k} {wp.leaf_path}",
                                  parcel=wp.parcel, loc=None) if wp.parcel is not None else \
                        _compare_leaf(d, cols, w, wb, it, f"{name} L{level} {k} {wp.leaf_path}")
                    assert (int(w["status"]) == 2) == (wp.error is not None), \
                        f"{name} {k} {wp.leaf_path}: error marker"
                    if wp.parcel is not None:
                        fr = cols.t["frame"][int(w["frame"])]
                        layers["frame"] += 1
                        layers["road"] += int(fr["has_road"])
                        layers["background"] += int(fr["has_bg"])
                        layers["name"] += int(fr["has_name"])
                counts["whole"][f"{name} L{level}"] = counts["whole"].get(f"{name} L{level}", 0) \
                    + len(wrows)
            for path, cls in sampled_by_block.get(k, []):
                w = next(r for r in wrows if _path(r) == path)
                _compare_leaf(d, cols, w, wb, by_path[path], f"{name} L{level} {k} {path}")
                counts["sampled"][f"{name} L{level}"] = \
                    counts["sampled"].get(f"{name} L{level}", 0) + 1
                counts["classes"][cls] = counts["classes"].get(cls, 0) + 1

        # one banded call over the whole-compare blocks: a band starting at the median iy
        wkeys = whole_by_level.get(level, [])
        if not wkeys:
            continue
        wwbs = [d.by_key[k] for k in wkeys]
        wrows_in = cenc.d1_block_rows([d.key(b) for b in wwbs], d.container)
        full = cenc.d1_blocks(d.region, wrows_in)
        planned += 1
        iys = full.t["walk"]["iy"]
        lo, hi = int(iys.min()), int(iys.max())
        rlo = int(np.sort(iys)[len(iys) * 3 // 8])
        rhi = rlo + max(1, (hi - lo) // 8)
        band = cenc.d1_blocks(d.region, wrows_in, rlo, rhi)
        planned += 1
        want_paths = []
        for wb in wwbs:
            want_paths += [(wb.block_index, wp.leaf_path) for wp in qr._iter_leaves(
                str(d.path), d.container, d.key(wb), d.lat(level), rlo, rhi)]
        got_paths = [(int(w["block_index"]), _path(w)) for w in band.t["walk"]]
        assert got_paths == want_paths, f"{name} L{level}: band [{rlo},{rhi}] leaves differ"
        assert len(got_paths) < len(full.t["walk"]) or hi == lo
        counts["banded"][f"{name} L{level}"] = len(got_paths)

    s1 = cenc.d1_stats()
    assert s1["ranges"] - s0["ranges"] == planned, "ranges != block bands planned"
    assert s1["calls"] - s0["calls"] - (s1["retries"] - s0["retries"]) == planned, \
        "ctypes calls (net of buffer-growth retries) != block bands planned"
    cls_seen = counts["classes"]
    with capsys.disabled():
        print(f"\n[d1 equivalence {name}] planned block-band calls={planned} "
              f"(ranges={s1['ranges'] - s0['ranges']}, calls={s1['calls'] - s0['calls']}, "
              f"retries={s1['retries'] - s0['retries']})")
        print(f"[d1 equivalence {name}] whole-block leaves compared per level: {counts['whole']}")
        print(f"[d1 equivalence {name}] sampled leaves per level: {counts['sampled']}")
        print(f"[d1 equivalence {name}] sampled classes: {cls_seen}; "
              f"whole-block decoded frames / with road / bg / name: {layers}")
        print(f"[d1 equivalence {name}] banded leaves per level: {counts['banded']}")
    # G is a dense L0 disc (no sparse tiles at all, measured over all 1858 L0 blocks);
    # R's L0 is sparse tiles. Together the two discs exercise all three classes.
    for c in CLASSES:
        if name == "G" and c == "l0_sparse_tile":
            assert cls_seen.get(c, 0) == 0
        else:
            assert cls_seen.get(c, 0) > 0, f"{name}: no sampled leaf of class {c}"
    sampled = [(k, p) for k, ps in sampled_by_block.items() for p, _ in ps]
    assert len(sampled) <= 400
    # all four sub-layers (parcel frame header, road, background, name) non-empty in the sample
    feats = dict.fromkeys(("road", "bg_poly", "name", "bg"), False)
    for (lv, bs, bi), ps in sampled_by_block.items():
        wb = d.by_key[(lv, bs, bi)]
        its = {tuple(i["path"]): i for i in d.py_items(wb)}
        for p, _ in ps:
            for k, v in _features(d.py_decode(wb, its[p])[0]).items():
                feats[k] = feats[k] or v
    assert all(feats.values()), f"{name}: sample lacks {[k for k, v in feats.items() if not v]}"


def test_every_level_in_sample():
    for name in ("G", "R"):
        d = disc(name)
        have = {s[0] for s in committed(name)["leaves"]}
        assert have == {m.level for m in d.container.pdmdh.levels} - {
            lv for lv in {m.level for m in d.container.pdmdh.levels}
            if not any(b.level == lv for b in d.blocks)}, f"{name}: levels missing from sample"


# ------------------------------------------------- unparsable blocks (markers)

def _synthetic():
    """Blocks the discs do not contain: a record parse must fail on exactly the
    inputs `parse_parcel_mgmt_record` raises on, and yield a marker row."""
    npl = [1, 1, 1, 1]
    lmr = SimpleNamespace(n_parcels_lat=npl, n_parcels_lng=npl)

    def rec(type_word, entries):
        b = struct.pack(">HH", type_word, 0)
        for dsa, size in entries:
            b += struct.pack(">IH", dsa, size)
        return b

    nd = 0xFFFFFFFF
    good = rec(0, [(nd, 0)] * 4)
    cases = {
        "empty-grid": good,
        "list_type": rec(1, [(nd, 0)] * 4),
        "short-header": b"\x00",
        "short-entries": good[:9],
        "self-recursion": rec(0, [(0, 0), (nd, 0), (nd, 0), (nd, 0)]),      # sws(0) = 0: itself
        "subrecord-ok": rec(0, [(4 + 4 * 6 + 0, 0)] * 0 or [(14, 0), (nd, 0), (nd, 0), (nd, 0)])
        + good,                      # slot 0 -> offset 28: a valid empty record
        "bad-leaf-frame": rec(0, [(0x100, 3), (nd, 0), (nd, 0), (nd, 0)]) + b"\x00" * 64,
    }
    return lmr, cases


def test_unparsable_blocks_yield_markers():
    lmr, cases = _synthetic()
    region = b""
    keys = []
    for name, buf in cases.items():
        keys.append((name, len(region), len(buf)))
        region += buf
    region += b"\x00" * 4096
    rows = np.zeros(len(keys), cenc.D1_BLOCK_DTYPE)
    for i, (name, off, n) in enumerate(keys):
        r = rows[i]
        r["off"], r["len"] = off, n
        r["sector_sz"] = r["logical_sz"] = 1
        r["grid_nx"] = r["grid_ny"] = 1
        r["cov_lat_hi"], r["cov_lon_hi"], r["cell_lat"], r["cell_lon"] = 1.0, 1.0, 1.0, 1.0
        r["npl0"] = r["npl1"] = r["npl2"] = r["npl3"] = 1
        r["npg0"] = r["npg1"] = r["npg2"] = r["npg3"] = 1
        r["rng_normal"] = 4096
    s0 = cenc.d1_stats()["ranges"]
    cols = cenc.d1_blocks(np.frombuffer(region, np.uint8), rows)
    assert cenc.d1_stats()["ranges"] - s0 == 1
    for i, (name, off, n) in enumerate(keys):
        buf = region[off:off + n]
        try:
            root = parse_parcel_mgmt_record(buf, lmr)
            err = None
        except Exception as exc:  # noqa: BLE001
            root, err = None, exc
        w = _walk_rows(cols, i)
        if err is not None:
            assert len(w) == 1 and int(w[0]["status"]) == 1 and int(w[0]["depth"]) == 0 \
                and int(w[0]["frame"]) == -1, f"{name}: python raised {err!r}, D1 gave {w}"
            code = {1: "list_type", 2: "recursion", 3: "index"}[int(w[0]["err"])]
            assert {"list_type": "list_type", "recursion": "recursion",
                    "index": "index"}[code] in (
                "list_type" if "list_type" in str(err) else
                "recursion" if "recursion" in str(err) else "index"), f"{name}: {code} vs {err!r}"
        else:
            n_py = sum(1 for _ in walk._iter_tree_leaves(
                root, BoundingBox(0, 1, 0, 1), lmr, ()))
            assert all(int(x["status"]) != 1 for x in w) and len(w) == n_py, \
                f"{name}: python parsed ({n_py} leaves), D1 rows {w}"
