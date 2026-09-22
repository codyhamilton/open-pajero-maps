#!/usr/bin/env python3
"""Cross-parcel continuity (Plan 03 unit 2-10, criterion 2) and divided
sub-parcel quadrant containment (criterion 3), grounded and tolerance-fixed
per DESIGN Decisions, Amendment 2026-09-23 (user).

Criterion 2: a link end-node on a shared parcel edge is stored independently
on both sides; decoded under the frame hypothesis of record
(`overlay_test.model_frame`), the two copies land on the same place, and do
not under the named alternatives. Criterion 3: every shape point of divided
sub-parcel k falls inside quadrant k of the parent leaf's 4096 frame.

Anti-circularity (binding, per the amendment): node *selection*
(`EDGE_TOL_RAW`) and *pairing* (`PAIR_TOL_RAW`) run once, in raw units,
under the hypothesis of record. The resulting pair list is then re-scored
UNCHANGED under every alternative -- no alternative may add, drop or re-pair
a node. This is structurally true in the code: `collect_pairs()` builds the
pair list once; `score_pair()` scores one already-built pair under a named
frame/range choice and is the only function alternatives call.

Pre-stated, not tuned -- fixed at refine time (2-10 brief). If one of these
turns out to be wrong, that is a `needs context` report, not an edit:

  EDGE_TOL_RAW = 4        raw coordinate units from 0 or the class range on
                          the crossed axis -- a node counts as an edge node.
  PAIR_TOL_RAW = 16       raw coordinate units of along-edge agreement (after
                          mapping to the shared edge's own parameter) for two
                          edge nodes on opposite sides to be paired.
  PASS_RAW_UNITS = 1.0    pass means every matched pair's hypothesis
                          separation is at most this many raw units expressed
                          in metres: max(width_m, height_m) / range of the
                          pair's own (source-side) frame.
  MIN_PAIRS_PER_CLASS = 300  for the full-leaf classes; the divided class is
                          measured over its whole population (small: single
                          digits of parents), never sampled.

Reads R only, through `overlay_test.RReader` and `r_neighbours.LeafIndex`
(both reused unmodified); imports no writer module. No OSM input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import overlay_test as ot  # noqa: E402
import r_neighbours as rn  # noqa: E402

EDGE_TOL_RAW = 4
PAIR_TOL_RAW = 16
PASS_RAW_UNITS = 1.0
MIN_PAIRS_PER_CLASS = 300

# Sample rule knob (not one of the four pre-stated constants above): how many
# blocks `overlay_test.spread` puts first before the remainder follows in
# on-disc order (see `_class_pairs`'s docstring for the full rule).
SAMPLE_BLOCKS = 60

# Residual-enumeration cap: a criterion-2 residual is only reported
# `pass_with_residual` if every over-threshold pair fits in the JSON
# record-by-record; past this the amendment's "enumerated residual" promise
# cannot be honoured and the criterion is `fail`. Not a pre-stated constant
# (it gates *reporting*, not selection/pairing/pass-per-pair), stated here
# once, before any run, and not changed after seeing a result.
RESIDUAL_ENUM_CAP = 200

OPPOSITE = {"E": "W", "W": "E", "N": "S", "S": "N"}
HALF = 2048  # criterion 3: quadrant half-extent of the parent's 4096 frame
QUAD_OFFSET = {0: (0, 0), 1: (1, 0), 2: (0, 1), 3: (1, 1)}  # k -> (qx, qy)

COORD_SCALE = json.loads((ROOT / "refdata" / "profile" / "coord_scale.json").read_text())
RANGES = COORD_SCALE["ranges"]
CLASS_RULE = COORD_SCALE["class_rule"]


# --------------------------------------------------------------- utilities

def _median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _percentile(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p / 100.0
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (k - f) * (s[c] - s[f])


def _cell_dict(level, ptype, cls, lb, parent, fr, sub):
    tile = fr[0] if fr is not None and fr[1] == "l0_sparse_tile" else None
    return {"ptype": ptype, "level": level, "class": cls, "bounds": lb, "parent": parent,
            "sub": sub, "tile": tile}


def score_pair(pair, frame_s, rng_s, frame_t, rng_t):
    """Metre separation of one already-built pair, decoded on each side in
    its own (frame, range), scored via `overlay_test.decode_uv` against a
    shared local reference cell (`pair["ref_cell"]`, the source leaf's own
    bbox -- stable across every hypothesis, used only to fix a common local
    metre scale) and `overlay_test.extent_m`."""
    import numpy as np
    ref = pair["ref_cell"]
    uv_s = ot.decode_uv(np.array([pair["s_pt"]], float), frame_s, ref, rng_s, True)[0]
    uv_t = ot.decode_uv(np.array([pair["t_pt"]], float), frame_t, ref, rng_t, True)[0]
    w, h = ot.extent_m(ref)
    dx, dy = (uv_s[0] - uv_t[0]) * w, (uv_s[1] - uv_t[1]) * h
    return float((dx * dx + dy * dy) ** 0.5)


def _select_edge_nodes(pts, edge, rng, tol):
    axis = 0 if edge in ("E", "W") else 1
    lo = edge in ("W", "S")
    target = 0.0 if lo else float(rng)
    return [p for p in pts if abs(p[axis] - target) <= tol]


def _along(edge):
    return 1 if edge in ("E", "W") else 0


def _pair_nodes(src_nodes, tgt_nodes, edge, rng_s, rng_t, tol):
    """Pair source/target edge nodes by along-edge agreement. If the two
    ranges differ, mapping is only defined when one is an exact multiple of
    the other (`scale_mismatch` otherwise): the target's along-edge raw
    value is rescaled into the source's raw units before the tolerance
    check, which is equivalent to scaling the tolerance by the same exact
    ratio in the other direction. Greedy nearest-first, each target used at
    most once. Returns (pairs, unpaired_src_count, scale_mismatch_count)."""
    ax = _along(edge)
    if rng_s == rng_t:
        ratio = 1.0
    elif max(rng_s, rng_t) % min(rng_s, rng_t) == 0:
        ratio = rng_s / rng_t
    else:
        return [], len(src_nodes), len(src_nodes)

    cand = [(t, t[ax] * ratio) for t in tgt_nodes]
    used = [False] * len(cand)
    pairs, unpaired = [], 0
    for s in src_nodes:
        sv = s[ax]
        best_i, best_d = None, None
        for i, (t, tv) in enumerate(cand):
            if used[i]:
                continue
            d = abs(sv - tv)
            if d <= tol and (best_d is None or d < best_d):
                best_i, best_d = i, d
        if best_i is None:
            unpaired += 1
            continue
        used[best_i] = True
        pairs.append((s, cand[best_i][0]))
    return pairs, unpaired, 0


# ----------------------------------------------------------- criterion two

def _class_pairs(rdr, idx, key, level, ptype, urban):
    """Sample rule: `overlay_test.spread` over the level's leaf-index-ordered
    block list (`SAMPLE_BLOCKS` spread evenly first, then every remaining
    block in on-disc order -- `spread` already returns the full permutation,
    see its docstring), leaves visited in index order within each block,
    stopping once `MIN_PAIRS_PER_CLASS` raw pairs are collected or the
    population is exhausted. Returns (pairs, stats, n_leaves, population_note)."""
    keys = list(idx.blocks.keys())
    order = ot.spread(keys, min(SAMPLE_BLOCKS, len(keys)) or 1)
    stats = Counter()
    pairs = []
    n_leaves = 0
    exhausted = True
    for bkey in order:
        if len(pairs) >= MIN_PAIRS_PER_CLASS:
            exhausted = False
            break
        blk = idx.blocks[bkey]
        rows = idx.leaves(bkey)
        for row in rows:
            lpath, le, lb, lptype, parent, fr = row
            if lptype != ptype or len(lpath) != 1:
                continue
            if level == 0 and ptype == 0 and urban is not None:
                if ot._urban(CLASS_RULE, blk[1], blk[2], lpath[0]) != urban:
                    continue
            links = rdr.decode(idx.lmr, blk, row)
            if not links:
                continue
            n_leaves += 1
            c = _cell_dict(level, 0, key, lb, parent, fr, None)
            frame_s, rng_s = ot.model_frame(c, RANGES)
            ends = [pt for lk in links for pt in lk["ends"]]
            handle = (idx.lmr, blk, row)
            for edge in ("E", "N"):
                src_nodes = _select_edge_nodes(ends, edge, rng_s, EDGE_TOL_RAW)
                if not src_nodes:
                    continue
                nb = idx.neighbour(handle, edge)
                if nb.status in ("outside_coverage", "empty_slot"):
                    stats[nb.status] += 1
                    continue
                if nb.divided:
                    stats["neighbour_divided"] += 1
                    continue
                n_lmr, n_blk, n_row = nb.handles[0]
                n_lpath, n_le, n_lb, n_lptype, n_parent, n_fr = n_row
                n_links = rdr.decode(n_lmr, n_blk, n_row)
                if not n_links:
                    stats["neighbour_decode_failed"] += 1
                    continue
                n_key = ot._class_key(level, n_lptype, CLASS_RULE, n_blk, n_lpath)
                n_c = _cell_dict(level, 0, n_key, n_lb, n_parent, n_fr, None)
                frame_t, rng_t = ot.model_frame(n_c, RANGES)
                n_ends = [pt for lk in n_links for pt in lk["ends"]]
                tgt_nodes = _select_edge_nodes(n_ends, OPPOSITE[edge], rng_t, EDGE_TOL_RAW)
                matched, unpaired, mismatch = _pair_nodes(
                    src_nodes, tgt_nodes, edge, rng_s, rng_t, PAIR_TOL_RAW)
                stats["unpaired"] += unpaired
                stats["scale_mismatch"] += mismatch
                for s_pt, t_pt in matched:
                    pairs.append({
                        "s_pt": s_pt, "t_pt": t_pt, "edge": edge,
                        "frame_s": frame_s, "rng_s": rng_s,
                        "frame_t": frame_t, "rng_t": rng_t,
                        "ref_cell": lb,
                        "ids": {"level": level, "class": key,
                                "src": [blk[1], blk[2], list(lpath)],
                                "tgt": [n_blk[1], n_blk[2], list(n_lpath)]},
                    })
    else:
        exhausted = True
    return pairs, stats, n_leaves, exhausted, len(keys)


def _sibling_pairs(rdr, idx, level):
    """Divided class (pardiv1): pairs are sibling sub-parcels inside one
    parent -- sub0|sub1 and sub2|sub3 share a vertical internal edge at
    parent x = HALF; sub0|sub2 and sub1|sub3 share a horizontal one at
    parent y = HALF. Both siblings' raw end-nodes are selected the same way
    as a real boundary edge, but against the internal midline (HALF) instead
    of 0/range, since the shared edge here is inside the parent frame, not
    at its outer edge. Whole population, no sampling."""
    stats = Counter()
    pairs = []
    n_leaves = 0
    sibs = [("W", "E", 0, 1), ("W", "E", 2, 3), ("S", "N", 0, 2), ("S", "N", 1, 3)]
    for bkey, blk in idx.blocks.items():
        rows = idx.leaves(bkey)
        groups = {}
        for row in rows:
            lpath, le, lb, lptype, parent, fr = row
            if lptype != 1:
                continue
            groups.setdefault(lpath[0], {})[lpath[-1]] = row
        for top_idx, subs in groups.items():
            for edge_a, edge_b, ka, kb in sibs:
                if ka not in subs or kb not in subs:
                    continue
                row_a, row_b = subs[ka], subs[kb]
                links_a = rdr.decode(idx.lmr, blk, row_a)
                links_b = rdr.decode(idx.lmr, blk, row_b)
                if not links_a or not links_b:
                    continue
                n_leaves += 1
                parent_bounds = row_a[4]
                c = _cell_dict(level, 1, "divided_pardiv1", None, parent_bounds, None, ka)
                frame, rng = ot.model_frame(c, RANGES)  # same parent frame/range both sides
                ends_a = [pt for lk in links_a for pt in lk["ends"]]
                ends_b = [pt for lk in links_b for pt in lk["ends"]]
                a_nodes = _select_edge_nodes_mid(ends_a, edge_a, HALF, EDGE_TOL_RAW)
                b_nodes = _select_edge_nodes_mid(ends_b, edge_b, HALF, EDGE_TOL_RAW)
                if not a_nodes:
                    continue
                matched, unpaired, mismatch = _pair_nodes(
                    a_nodes, b_nodes, edge_a, rng, rng, PAIR_TOL_RAW)
                stats["unpaired"] += unpaired
                stats["scale_mismatch"] += mismatch
                for s_pt, t_pt in matched:
                    pairs.append({
                        "s_pt": s_pt, "t_pt": t_pt, "edge": edge_a,
                        "frame_s": frame, "rng_s": rng,
                        "frame_t": frame, "rng_t": rng,
                        "ref_cell": row_a[4],
                        "own_leaf_s": row_a[2], "own_leaf_t": row_b[2],
                        "own_rng_s": _sub_range(level, ka), "own_rng_t": _sub_range(level, kb),
                        "ids": {"level": level, "class": "divided_pardiv1",
                                "top": top_idx, "sub_a": ka, "sub_b": kb},
                    })
    return pairs, stats, n_leaves


def _select_edge_nodes_mid(pts, edge, mid, tol):
    axis = 0 if edge in ("E", "W") else 1
    return [p for p in pts if abs(p[axis] - mid) <= tol]


def _sub_range(level, sub):
    return ot.class_range(RANGES, level, "divided_pardiv1", sub)


def continuity_class(rdr, idx_cache, key, level, ptype, urban):
    if level not in idx_cache:
        idx_cache[level] = rn.LeafIndex(rdr, level)
    idx = idx_cache[level]
    if key == "divided_pardiv1":
        pairs, stats, n_leaves = _sibling_pairs(rdr, idx, level)
        sample_rule = f"whole population ({n_leaves} parent(s) with content-bearing siblings)"
        population = n_leaves
    else:
        pairs, stats, n_leaves, exhausted, n_blocks_total = _class_pairs(
            rdr, idx, key, level, ptype, urban)
        sample_rule = (f"spread({min(SAMPLE_BLOCKS, n_blocks_total)} of {n_blocks_total} "
                        f"blocks, on-disc order, overlay_test.spread), leaves in index order, "
                        f"until {MIN_PAIRS_PER_CLASS} pairs or population exhausted "
                        f"({'exhausted' if exhausted else 'quota reached'})")
        population = n_leaves

    hyp_seps, hyp_thresh = [], []
    alt_seps = {"half": [], "double": [], "decoder_range": []}
    own_leaf_seps = [] if key == "divided_pardiv1" else None
    for p in pairs:
        sep = score_pair(p, p["frame_s"], p["rng_s"], p["frame_t"], p["rng_t"])
        hyp_seps.append(sep)
        w, h = ot.extent_m(p["frame_s"])
        hyp_thresh.append(PASS_RAW_UNITS * max(w, h) / p["rng_s"])
        alt_seps["half"].append(score_pair(p, p["frame_s"], p["rng_s"] / 2,
                                            p["frame_t"], p["rng_t"] / 2))
        alt_seps["double"].append(score_pair(p, p["frame_s"], p["rng_s"] * 2,
                                              p["frame_t"], p["rng_t"] * 2))
        alt_seps["decoder_range"].append(score_pair(p, p["frame_s"], ot.DECODER_RANGE,
                                                      p["frame_t"], ot.DECODER_RANGE))
        if own_leaf_seps is not None:
            own_leaf_seps.append(score_pair(p, p["own_leaf_s"], p["own_rng_s"],
                                             p["own_leaf_t"], p["own_rng_t"]))

    over = [s for s, t in zip(hyp_seps, hyp_thresh) if s > t]
    residual = None
    if over:
        examples = [{"pair_ids": p["ids"], "sep_m": round(s, 4), "threshold_m": round(t, 4)}
                    for p, s, t in zip(pairs, hyp_seps, hyp_thresh) if s > t]
        residual = examples[:RESIDUAL_ENUM_CAP]

    alt_medians = {k: (round(_median(v), 4) if v else None) for k, v in alt_seps.items()}
    if own_leaf_seps is not None:
        alt_medians["own_leaf_bbox_own_range"] = (
            round(_median(own_leaf_seps), 4) if own_leaf_seps else None)

    return {
        "class": key, "level": level, "n_leaves": n_leaves, "n_pairs": len(pairs),
        "population": population, "sample_rule": sample_rule,
        "median_m": round(_median(hyp_seps), 4) if hyp_seps else None,
        "p90_m": round(_percentile(hyp_seps, 90), 4) if hyp_seps else None,
        "max_m": round(max(hyp_seps), 4) if hyp_seps else None,
        "over_threshold": len(over),
        "over_threshold_fully_enumerated": residual is not None and len(residual) == len(over),
        "residual_examples": residual,
        "outside_coverage": stats.get("outside_coverage", 0),
        "empty_slot": stats.get("empty_slot", 0),
        "neighbour_divided": stats.get("neighbour_divided", 0),
        "neighbour_decode_failed": stats.get("neighbour_decode_failed", 0),
        "scale_mismatch": stats.get("scale_mismatch", 0),
        "unpaired": stats.get("unpaired", 0),
        "alt_medians_m": alt_medians,
    }


def criterion2(rdr):
    idx_cache = {}
    results = []
    for key, level, ptype, urban in ot.POOL_CLASSES:
        results.append(continuity_class(rdr, idx_cache, key, level, ptype, urban))
    total_over = sum(r["over_threshold"] for r in results)
    fully_enumerated = all(r["over_threshold_fully_enumerated"] for r in results if r["over_threshold"])
    if total_over == 0:
        verdict = "pass"
    elif fully_enumerated:
        verdict = "pass_with_residual"
    else:
        verdict = "fail"
    return {"classes": results, "over_threshold_total": total_over, "verdict": verdict}


# --------------------------------------------------------------- criterion 3

def _decode_full(rdr, lmr, blk, leaf_row):
    """Raw (x, y) points from the three shape-point sources
    `coord_scale_census.parcel_measure` enumerates: road node x/y (all
    nodes, not just ends -- `RReader.decode`'s `_links` keeps only ends, so
    this duplicates its two-line read+parse rather than reusing it, to keep
    the rest of the road frame and the background shapes too), road
    intermediate points, and background vertices. `fb` (the leaf/sub's own
    frame_bounds) is used identically for decode_parcel's internal lat/lon
    conversion and for the `_raw()` inversion below, so the round trip
    recovers the exact raw stored coordinate regardless of whether `fb` is
    the "correct" hypothesis frame."""
    from kiwiw.model import MeshLocation
    from kiwiw.parcel import decode_parcel
    _, bs_index, ei, _, _ = blk
    lpath, le, lb, ptype, _, (fb, _fc) = leaf_row
    rdr.fh.seek(rdr.volume.getsector(le.dsa, rdr.ss, rdr.ls))
    buf = rdr.fh.read(le.size * rdr.ls)
    loc = MeshLocation(level=lmr.level, parcel_type=ptype, blockset_index=bs_index,
                        block_index=ei, parcel_index=lpath[-1], bounds=fb,
                        sector_addr=le.dsa, size_logical_sectors=le.size)
    try:
        p = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
    except Exception:  # noqa: BLE001
        return None
    pts = []
    road = getattr(p, "road", None)
    if road is not None:
        for link in road.links:
            for nd in link.nodes:
                pts.append((float(nd.x), float(nd.y)))
            for lat, lon in (link.points or []):
                pts.append(ot._raw(lat, lon, fb))
    bg = getattr(p, "background", None)
    if bg is not None:
        for sh in bg.shapes:
            for lat, lon in sh.coords:
                pts.append(ot._raw(lat, lon, fb))
    return pts


def criterion3(rdr, levels=(0, 2, 4, 6, 8)):
    n_parents = n_subparcels = n_points = 0
    violations_parent_local = violations_sub_local = 0
    examples = []
    per_level = Counter()
    other_division_type = []
    for level in levels:
        lmr, blks = rdr.blocks(level)
        for blk in blks:
            rows = rdr.leaves(lmr, blk)
            groups: dict = {}
            for row in rows:
                lpath, le, lb, ptype, parent, fr = row
                if ptype == 0:
                    continue
                if ptype != 1:
                    other_division_type.append({"level": level, "blk": [blk[1], blk[2]],
                                                 "leaf_path": list(lpath), "ptype": ptype})
                    continue
                groups.setdefault(lpath[0], {})[lpath[-1]] = row
            for top_idx, subs in groups.items():
                n_parents += 1
                per_level[level] += 1
                for k, row in subs.items():
                    if k not in QUAD_OFFSET:
                        continue
                    qx, qy = QUAD_OFFSET[k]
                    pts = _decode_full(rdr, lmr, blk, row)
                    if pts is None:
                        continue
                    n_subparcels += 1
                    for x, y in pts:
                        n_points += 1
                        ok_parent = (qx * HALF <= x <= (qx + 1) * HALF and
                                     qy * HALF <= y <= (qy + 1) * HALF)
                        ok_sub = (0 <= x <= HALF and 0 <= y <= HALF)
                        if not ok_parent:
                            violations_parent_local += 1
                            if len(examples) < 10:
                                examples.append({
                                    "level": level, "blk": [blk[1], blk[2]],
                                    "top": top_idx, "sub": k, "x": x, "y": y,
                                    "quadrant": [qx, qy],
                                })
                        if not ok_sub:
                            violations_sub_local += 1
    if other_division_type:
        return {"needs_context": True,
                "reason": "division type other than type 1 (2x2) found",
                "examples": other_division_type[:10]}
    verdict = "pass" if violations_parent_local == 0 else "fail"
    return {
        "n_parents": n_parents, "n_subparcels": n_subparcels, "n_points": n_points,
        "violations": violations_parent_local,
        "violations_examples": examples,
        "parents_per_level": {str(k): v for k, v in sorted(per_level.items())},
        "readings": {
            "parent_local": {
                "description": "raw (x, y) tested directly against quadrant k's "
                                "[qx*HALF,(qx+1)*HALF] x [qy*HALF,(qy+1)*HALF] of the "
                                "parent's 4096 frame -- coordinates absolute in the "
                                "parent frame, per docs/schema/map-frame.md and "
                                "test_overlay_test.py's PARENT fixture.",
                "violations": violations_parent_local,
            },
            "sub_local": {
                "description": "raw (x, y) tested against [0,HALF] x [0,HALF] "
                                "regardless of k -- coordinates relative to the sub's "
                                "own quadrant, offset not added back.",
                "violations": violations_sub_local,
            },
        },
        "reference_population": {"n_parents": 42, "by_level": {"0": 13, "2": 4, "4": 13,
                                                                 "6": 7, "8": 5},
                                  "n_content_subparcels": 52},
        "verdict": verdict,
    }


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    rdr = ot.RReader(args.reference)
    c2 = criterion2(rdr)
    c3 = criterion3(rdr)

    out = {
        "tool": "continuity_census",
        "reference": args.reference,
        "constants": {
            "EDGE_TOL_RAW": EDGE_TOL_RAW, "PAIR_TOL_RAW": PAIR_TOL_RAW,
            "PASS_RAW_UNITS": PASS_RAW_UNITS, "MIN_PAIRS_PER_CLASS": MIN_PAIRS_PER_CLASS,
            "note": "pre-stated, not tuned",
        },
        "sample_blocks": SAMPLE_BLOCKS,
        "residual_enum_cap": RESIDUAL_ENUM_CAP,
        "criterion_2_continuity": c2,
        "criterion_3_quadrant": c3,
    }
    text = json.dumps(out, indent=2, sort_keys=True, default=str) + "\n"
    Path(args.out).write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"wrote {args.out} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
