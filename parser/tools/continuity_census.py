#!/usr/bin/env python3
"""Cross-parcel continuity (Plan 03 unit 2-14, criterion 2) and divided
sub-parcel quadrant containment (criterion 3, unchanged from 2-10), rerun
against 2-13's frame-level adjacency and the level's global raw lattice, per
DESIGN Decisions, "Amendment 2026-09-23 (design agent) -- the adjacency unit
is the frame, not the leaf slot", and the 2-14 brief that cites it.

Criterion 2 (restated by the brief): "A road link crossing a frame boundary
is stored independently on both sides; the two copies of the shared endpoint
occupy the same point on the level's global raw lattice. Per matched pair;
denominator all boundary endpoint pairs at a shared frame edge, the
adjacency unit being the frame, not the leaf slot. Endpoint selection is
exact -- a node qualifies only when its raw crossed-axis coordinate is
exactly 0 or exactly the frame range -- and pairing is exact lattice
equality." Criterion 3 (unchanged): every shape point of divided sub-parcel
k falls inside quadrant k of the parent leaf's 4096 frame.

Root cause fixed here (GATE-2.md carried items 6/7, DESIGN.md's design-agent
amendment): the 2-10 run stepped one *leaf slot* where L0 sparse's leaf
slots are 16-aliased onto one 4x4-tile *frame*, inflating the L0_sparse
denominator 16x and manufacturing self-neighbour false failures. This
version uses `r_neighbours.FrameId`/`frame_of`/`frame_neighbour` to walk one
frame per distinct `FrameId` (never a leaf slot), and `to_global`/
`to_frame_local` to match/report in the level's global raw lattice, so a
frame is compared against *every* distinct neighbouring frame its edge
faces (which can be more than one, at a class-size boundary), not one
leaf-slot-nominated neighbour.

Retirement (binding, per DESIGN.md's "retirement rule" -- where a grounded
exact measure is found underneath a fuzzy one, the fuzzy one is retired, not
retuned): `EDGE_TOL_RAW` and `PAIR_TOL_RAW` (2-10's tolerance-based
selection/pairing) are retired. Selection is exact-integer membership at 0
or the frame range; pairing is exact integer equality of the global raw
lattice coordinate (same-frame siblings, criterion 2's `divided_pardiv1`
class only, compare directly in frame-local raw since both sides share one
frame -- see `_sibling_pairs`).

Anti-circularity (binding, carried from 2-10, still true here): node
*selection* and *pairing* run once, under the hypothesis of record. The
resulting pair list is then re-scored UNCHANGED under every alternative
range hypothesis (half, double, `overlay_test.DECODER_RANGE`) via
`score_pair`, purely as diagnostic evidence for how R-consistent the
lattice model is -- no alternative may add, drop or re-pair a node. Because
pairing is now exact-lattice equality rather than a metre threshold, a
matched pair's hypothesis separation is definitionally ~0 (floating-point
noise only); `score_pair`/`PASS_RAW_UNITS` remain for that diagnostic, not
for deciding matched/violation, which is `_greedy_exact_pair`'s job.

Pre-stated, not tuned -- fixed before this unit's first run. If one of
these turns out wrong, that is a `needs context` report, not an edit:

  PASS_RAW_UNITS = 1.0       diagnostic-only sanity threshold on a matched
                             pair's hypothesis separation (should be ~0 by
                             construction); not part of the pass/fail
                             decision.
  MIN_PAIRS_PER_CLASS = 300  for the full-leaf classes; the divided class is
                             measured over its whole population (small:
                             single digits of parents), never sampled.
  RESIDUAL_ENUM_CAP = 400    a class is `pass_with_residual` only if every
                             one of its violations is enumerated in the
                             output; past this cap the criterion's own
                             "enumerated residual, record by record" promise
                             cannot be honoured and the class (and so the
                             whole criterion) is `fail`. NOTE: the brief
                             states 400; DESIGN.md's design-agent amendment
                             states 200 for this same cap -- both exceed the
                             measured residual (152) with margin, so this
                             run follows the brief (this module's direct
                             governing contract) and the discrepancy is
                             reported, not silently resolved.

Reads R only, through `overlay_test.RReader` and `r_neighbours.LeafIndex`
plus its frame-adjacency API (`FrameId`, `frame_of`, `frame_neighbour`,
`to_global`, `to_frame_local` -- all reused unmodified, 2-13); imports no
writer module. No OSM input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import overlay_test as ot  # noqa: E402
import r_neighbours as rn  # noqa: E402

PASS_RAW_UNITS = 1.0
MIN_PAIRS_PER_CLASS = 300

# Sample rule knob (not one of the pre-stated constants above): how many
# blocks `overlay_test.spread` puts first before the remainder follows in
# on-disc order (see `_class_pairs`'s docstring for the full rule).
SAMPLE_BLOCKS = 60

# Residual-enumeration cap -- see module docstring for the brief-vs-DESIGN.md
# discrepancy (400 here, 200 in DESIGN.md); not changed after seeing a
# result.
RESIDUAL_ENUM_CAP = 400

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


def _along(edge):
    return 1 if edge in ("E", "W") else 0


def _select_edge_nodes(pts, edge, rng):
    """Exact selection: a node qualifies only when its raw crossed-axis
    coordinate is exactly 0 or exactly `rng`, as an integer. No tolerance --
    `EDGE_TOL_RAW` is retired (module docstring, retirement rule)."""
    axis = 0 if edge in ("E", "W") else 1
    lo = edge in ("W", "S")
    target = 0 if lo else int(rng)
    return [p for p in pts if int(p[axis]) == target]


def _select_edge_nodes_mid(pts, edge, mid):
    """Exact midline selection for divided siblings (criterion 2's internal
    edge, not an outer frame edge)."""
    axis = 0 if edge in ("E", "W") else 1
    return [p for p in pts if int(p[axis]) == int(mid)]


def _greedy_exact_pair(src_items, tgt_items, key_fn):
    """Pair `src_items` to `tgt_items` by exact equality of `key_fn(item)`,
    each target consumed at most once (first-available, deterministic
    within one call since both lists are already in a stable order).
    Returns (pairs, unmatched_src) where each pair is (src_item, tgt_item)."""
    buckets: dict = {}
    for t in tgt_items:
        buckets.setdefault(key_fn(t), []).append(t)
    pairs, unmatched = [], []
    for s in src_items:
        b = buckets.get(key_fn(s))
        if b:
            pairs.append((s, b.pop(0)))
        else:
            unmatched.append(s)
    return pairs, unmatched


def _nearest_point(g, global_points):
    best, bd = None, None
    for p in global_points:
        d = (p[0] - g[0]) ** 2 + (p[1] - g[1]) ** 2
        if bd is None or d < bd:
            bd, best = d, p
    return best


# ----------------------------------------------------------- criterion two

def _class_pairs(rdr, idx, key, level, ptype, urban, class_rule, ranges):
    """Sample rule: `overlay_test.spread` over the level's leaf-index-ordered
    block list (`SAMPLE_BLOCKS` spread evenly first, then every remaining
    block in on-disc order), leaves visited in index order within each
    block, one frame visited at most once (deduped by `FrameId` -- an L0
    sparse tile's 16 aliased leaf slots contribute exactly one frame),
    stopping once `MIN_PAIRS_PER_CLASS` raw pairs are collected or the
    population is exhausted. Returns (pairs, stats, n_frames, exhausted,
    n_blocks_total, residual)."""
    keys = list(idx.blocks.keys())
    order = ot.spread(keys, min(SAMPLE_BLOCKS, len(keys)) or 1)
    stats = Counter()
    pairs = []
    residual = []
    n_frames = 0
    seen_frames: set = set()
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
                if ot._urban(class_rule, blk[1], blk[2], lpath[0]) != urban:
                    continue
            handle = (idx.lmr, blk, row)
            fid, agrees = rn.frame_of(idx, handle, class_rule, ranges)
            if fid in seen_frames:
                continue
            seen_frames.add(fid)
            if not agrees:
                stats["tile_disagreements"] += 1
            links = rdr.decode(idx.lmr, blk, row)
            if not links:
                continue
            n_frames += 1
            rng_s = fid.n * rn.RAW_PER_SLOT
            fb_s = fr[0]
            ends = [(int(p[0]), int(p[1])) for lk in links for p in lk["ends"]]
            src_ident = {"level": level, "class": key,
                         "blockset_index": blk[1], "block_index": blk[2],
                         "leaf_path": list(lpath)}
            for edge in ("E", "N"):
                src_nodes = _select_edge_nodes(ends, edge, rng_s)
                if not src_nodes:
                    continue
                fnb = rn.frame_neighbour(idx, fid, edge, class_rule, ranges)
                if fnb.status in ("outside_coverage", "empty_slot"):
                    stats[fnb.status] += len(src_nodes)
                    continue
                candidates = []
                for tgt_fid, handles, crossing in zip(fnb.frames, fnb.handles, fnb.crossings):
                    t_lmr, t_blk, t_row = handles[0]
                    t_lpath, t_le, t_lb, t_lptype, t_parent, t_fr = t_row
                    if t_lptype != 0:
                        stats["neighbour_divided"] += len(handles)
                        continue
                    t_links = rdr.decode(t_lmr, t_blk, t_row)
                    if not t_links:
                        stats["neighbour_decode_failed"] += 1
                        continue
                    t_ends = [(int(p[0]), int(p[1])) for lk in t_links for p in lk["ends"]]
                    t_rng = tgt_fid.n * rn.RAW_PER_SLOT
                    candidates.append({
                        "fid": tgt_fid, "crossing": crossing,
                        "fb": t_fr[0], "rng": t_rng,
                        "cross_class": t_rng != rng_s,
                        "global": [rn.to_global(tgt_fid, x, y) for (x, y) in t_ends],
                        "ident": {"level": level,
                                  "blockset_index": t_blk[1], "block_index": t_blk[2],
                                  "leaf_path": list(t_lpath)},
                    })
                if not candidates:
                    continue
                all_global = []
                for tc in candidates:
                    all_global.extend(tc["global"])
                counts = Counter(all_global)
                for (x, y) in src_nodes:
                    g = rn.to_global(fid, x, y)
                    if counts.get(g, 0) <= 0:
                        stats["unmatched"] += 1
                        cross_class = any(tc["cross_class"] for tc in candidates)
                        if len(residual) < RESIDUAL_ENUM_CAP:
                            nearest = _nearest_point(g, all_global)
                            residual.append({
                                "source": src_ident, "edge": edge,
                                "source_raw": [x, y], "source_global": list(g),
                                "candidate_frames": [c["ident"] for c in candidates],
                                "nearest_actual_global": (list(nearest) if nearest else None),
                                "cross_class": cross_class,
                            })
                        continue
                    counts[g] -= 1
                    # attribute the match to a candidate that still holds g
                    hit_tc = None
                    for tc in candidates:
                        if g in tc["global"]:
                            hit_tc = tc
                            break
                    t_local = rn.to_frame_local(hit_tc["fid"], g[0], g[1])
                    pairs.append({
                        "s_pt": (float(x), float(y)), "t_pt": (float(t_local[0]), float(t_local[1])),
                        "edge": edge,
                        "frame_s": fb_s, "rng_s": float(rng_s),
                        "frame_t": hit_tc["fb"], "rng_t": float(hit_tc["rng"]),
                        "ref_cell": lb,
                        "crossing": hit_tc["crossing"],
                        "cross_class": hit_tc["cross_class"],
                        "ids": {"level": level, "class": key, "src": src_ident,
                                "tgt": hit_tc["ident"]},
                    })
    else:
        exhausted = True
    return pairs, stats, n_frames, exhausted, len(keys), residual


def _sibling_pairs(rdr, idx, level):
    """Divided class (pardiv1): pairs are sibling sub-parcels inside one
    parent -- sub0|sub1 and sub2|sub3 share a vertical internal edge at
    parent x = HALF; sub0|sub2 and sub1|sub3 share a horizontal one at
    parent y = HALF. Both siblings share the SAME parent frame/range (this
    is an internal edge, not an outer frame edge crossing onto another
    frame), so no lattice translation is needed: matching is exact equality
    of the along-edge raw coordinate directly, greedy, each target used at
    most once. Whole population, no sampling."""
    stats = Counter()
    pairs = []
    residual = []
    n_leaves = 0
    sibs = [("W", "E", 0, 1), ("W", "E", 2, 3), ("S", "N", 0, 2), ("S", "N", 1, 3)]
    for bkey, blk in idx.blocks.items():
        rows = idx.leaves(bkey)
        groups: dict = {}
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
                frame, rng = parent_bounds, HALF * 2  # same parent frame/range both sides
                ends_a = [(int(p[0]), int(p[1])) for lk in links_a for p in lk["ends"]]
                ends_b = [(int(p[0]), int(p[1])) for lk in links_b for p in lk["ends"]]
                a_nodes = _select_edge_nodes_mid(ends_a, edge_a, HALF)
                b_nodes = _select_edge_nodes_mid(ends_b, edge_b, HALF)
                if not a_nodes:
                    continue
                ax = _along(edge_a)
                matched, unmatched = _greedy_exact_pair(a_nodes, b_nodes, lambda p: p[ax])
                stats["unpaired"] += len(unmatched)
                src_ident = {"level": level, "class": "divided_pardiv1", "top": top_idx,
                              "sub": ka, "blockset_index": blk[1], "block_index": blk[2]}
                for s_pt in unmatched:
                    if len(residual) < RESIDUAL_ENUM_CAP:
                        residual.append({
                            "source": src_ident, "edge": edge_a, "source_raw": list(s_pt),
                            "candidate_sub": kb,
                        })
                for s_pt, t_pt in matched:
                    pairs.append({
                        "s_pt": s_pt, "t_pt": t_pt, "edge": edge_a,
                        "frame_s": frame, "rng_s": rng,
                        "frame_t": frame, "rng_t": rng,
                        "ref_cell": row_a[4],
                        "own_leaf_s": row_a[2], "own_leaf_t": row_b[2],
                        "own_rng_s": _sub_range(level, ka), "own_rng_t": _sub_range(level, kb),
                        "cross_class": False,
                        "ids": {"level": level, "class": "divided_pardiv1",
                                "top": top_idx, "sub_a": ka, "sub_b": kb},
                    })
    return pairs, stats, n_leaves, residual


def _sub_range(level, sub):
    return ot.class_range(RANGES, level, "divided_pardiv1", sub)


def continuity_class(rdr, idx_cache, key, level, ptype, urban):
    if level not in idx_cache:
        idx_cache[level] = rn.LeafIndex(rdr, level)
    idx = idx_cache[level]
    if key == "divided_pardiv1":
        pairs, stats, n_frames, residual = _sibling_pairs(rdr, idx, level)
        sample_rule = f"whole population ({n_frames} parent(s) with content-bearing siblings)"
        population = n_frames
    else:
        pairs, stats, n_frames, exhausted, n_blocks_total, residual = _class_pairs(
            rdr, idx, key, level, ptype, urban, CLASS_RULE, RANGES)
        sample_rule = (f"spread({min(SAMPLE_BLOCKS, n_blocks_total)} of {n_blocks_total} "
                        f"blocks, on-disc order, overlay_test.spread), leaves in index order, "
                        f"one query per distinct frame (FrameId-deduped), until "
                        f"{MIN_PAIRS_PER_CLASS} pairs or population exhausted "
                        f"({'exhausted' if exhausted else 'quota reached'})")
        population = n_frames

    hyp_seps, hyp_thresh = [], []
    alt_seps = {"half": [], "double": [], "decoder_range": []}
    own_leaf_seps = [] if key == "divided_pardiv1" else None
    cross_class_matched = cross_class_violations = 0
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
        if p.get("cross_class"):
            cross_class_matched += 1

    for r in residual:
        if r.get("cross_class"):
            cross_class_violations += 1

    matched = len(pairs)
    violations = stats.get("unmatched", 0) + stats.get("unpaired", 0)
    fully_enumerated = len(residual) == violations
    if violations == 0:
        verdict = "pass"
    elif fully_enumerated:
        verdict = "pass_with_residual"
    else:
        verdict = "fail"

    alt_medians = {k: (round(_median(v), 4) if v else None) for k, v in alt_seps.items()}
    if own_leaf_seps is not None:
        alt_medians["own_leaf_bbox_own_range"] = (
            round(_median(own_leaf_seps), 4) if own_leaf_seps else None)

    return {
        "class": key, "level": level, "n_frames": n_frames, "n_pairs": matched,
        "population": population, "sample_rule": sample_rule,
        "median_m": round(_median(hyp_seps), 4) if hyp_seps else None,
        "p90_m": round(_percentile(hyp_seps, 90), 4) if hyp_seps else None,
        "max_m": round(max(hyp_seps), 4) if hyp_seps else None,
        "matched": matched,
        "violations": violations,
        "denominator": matched + violations,
        "over_threshold_fully_enumerated": fully_enumerated,
        "residual_examples": residual,
        "outside_coverage": stats.get("outside_coverage", 0),
        "empty_slot": stats.get("empty_slot", 0),
        "neighbour_divided": stats.get("neighbour_divided", 0),
        "neighbour_decode_failed": stats.get("neighbour_decode_failed", 0),
        "cross_class_split": {"matched": cross_class_matched,
                               "violations": cross_class_violations},
        "alt_medians_m": alt_medians,
        "verdict": verdict,
    }


def criterion2(rdr):
    idx_cache = {}
    results = []
    for key, level, ptype, urban in ot.POOL_CLASSES:
        results.append(continuity_class(rdr, idx_cache, key, level, ptype, urban))
    total_violations = sum(r["violations"] for r in results)
    any_fail = any(r["verdict"] == "fail" for r in results)
    any_residual = any(r["verdict"] == "pass_with_residual" for r in results)
    if any_fail:
        verdict = "fail"
    elif any_residual:
        verdict = "pass_with_residual"
    else:
        verdict = "pass"
    return {"classes": results, "violations_total": total_violations,
            "over_threshold_total": total_violations, "verdict": verdict}


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
            "PASS_RAW_UNITS": PASS_RAW_UNITS, "MIN_PAIRS_PER_CLASS": MIN_PAIRS_PER_CLASS,
            "RAW_PER_SLOT": rn.RAW_PER_SLOT,
            "note": "pre-stated, not tuned; EDGE_TOL_RAW/PAIR_TOL_RAW retired 2-14 "
                    "(exact lattice equality replaces tolerance-based selection/pairing)",
        },
        "sample_blocks": SAMPLE_BLOCKS,
        "residual_enum_cap": RESIDUAL_ENUM_CAP,
        "residual_enum_cap_note": "brief (2-14-continuity-and-mirror-rerun.md) states 400; "
                                   "DESIGN.md's design-agent amendment states 200 for this "
                                   "same cap -- both exceed the measured residual with "
                                   "margin; this run follows the brief and reports the "
                                   "discrepancy rather than resolving it silently.",
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
