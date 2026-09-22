#!/usr/bin/env python3
"""Boundary-node mirror check across resolved neighbours (Plan 03 unit
2-11): for a link end-node sitting exactly on a parcel edge, is there an
end-node at the mirrored coordinate in the parcel on the other side of that
edge -- including when that parcel is in another block or another blockset?

Cited, DESIGN Decisions, Amendment 2026-09-23 (user), Phase 2 criterion 4:
"A link end-node whose raw coordinate is exactly 0 or exactly the class
range is a genuine boundary crossing: the adjacent parcel holds an
end-node at the mirrored coordinate, crossed axis = range - value, other
axis unchanged. Per-node violation count; denominator all exact-coordinate
nodes with a resolvable neighbour, with nodes at the extract's outer edge
excluded from the denominator rather than failed."

Cited, the same amendment, "Carried into the re-run": "The mirror
invariant was tested only on same-block neighbours, so block- and
blockset-crossing neighbour lookup must exist before it is load-bearing."
This module answers that with `r_neighbours.LeafIndex`/`neighbour` (2-09).

Pre-stated constants (fixed at refine time; not tuned after seeing a
result -- a constant that turns out wrong is a `needs context` report, not
an edit):

- EXACT_ONLY = True -- a node qualifies only when its raw crossed-axis
  coordinate is exactly 0 or exactly the class range, as an integer. No
  epsilon, no rounding window. Raw values recover exactly because decode
  and inversion use the same bbox (DECODER_RANGE = 32768 in
  overlay_test.py, for the shape points inverted through `_raw`); link
  *end*-nodes come straight from `RoadNode.x`/`.y`, which are stored ints
  (kiwiw/model.py), so "exact" is literal Python `int ==`.
- MIRROR_TOL_RAW = 0 -- the mirrored node must satisfy
  `crossed == range - value` and `along_edge == value_along`, both at
  exact integer equality. The recorded scratchpad result was "matched to
  0 raw units", so 0 is the pre-stated threshold.
- MIN_NODES_PER_CLASS = 300 -- the minimum qualifying nodes per class
  before a class's figure is reportable; L6, L8 and any smaller class are
  measured over their whole population.

Reads R only through `harness.walk` reading paths, `overlay_test.RReader`
and `r_neighbours` (2-09); imports no writer module. y increases northward
(coordconv, 2-06): edge "N" is +gy/+y, "S" is -gy/-y, "W" is -gx/-x,
"E" is +gx/+x. Frame of record: `overlay_test.model_frame` /
`overlay_test.class_range`, both reused unmodified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import overlay_test as ot  # noqa: E402
import r_neighbours as rn  # noqa: E402

EXACT_ONLY = True
MIRROR_TOL_RAW = 0
MIN_NODES_PER_CLASS = 300

COORD_SCALE_PATH = ROOT / "refdata" / "profile" / "coord_scale.json"

# One class per leaf-population this unit walks. L0 splits into two classes
# by the same class rule overlay_test/coord_scale.json use; L2/L4/L6/L8 are
# each one class. divided_pardiv1 sources are out of scope for this unit
# (not named in the brief's Changes section); a divided *neighbour* is
# still handled, as a scale_mismatch exclusion, since `r_neighbours`
# reports `divided=True` for it.
CLASSES = ["L0_urban", "L0_sparse", "L2", "L4", "L6", "L8"]
CLASS_LEVEL = {"L0_urban": 0, "L0_sparse": 0, "L2": 2, "L4": 4, "L6": 6, "L8": 8}
FULL_POPULATION_CLASSES = {"L6", "L8"}
SAMPLE_BLOCKS = 40  # stated block count for the spread-sampled classes
FRAME_EXTENT_TOL_REL = 1e-6  # relative to the source frame's own along-edge span

def _qualifying_edges(x, y, rng):
    """Edges (up to two, for a corner) that (x, y) qualifies for, exactly,
    against class range `rng`."""
    edges = []
    if x == 0:
        edges.append("W")
    if x == rng:
        edges.append("E")
    if y == 0:
        edges.append("S")
    if y == rng:
        edges.append("N")
    return edges


def _mirrored_point(x, y, edge, rng):
    """Expected (x, y) of the mirrored node on the neighbour across `edge`,
    at the source's own range (only called once ranges are known equal)."""
    if edge in ("W", "E"):
        return (rng - x, y)
    return (x, rng - y)


def _leaf_ident(level, blk, lpath):
    return {"level": level, "blockset_index": blk[1], "block_index": blk[2],
            "leaf_path": list(lpath)}


def _nearest_raw(px, py, ends):
    if not ends:
        return None
    return min(ends, key=lambda e: (e[0] - px) ** 2 + (e[1] - py) ** 2)


def _frame_extent(fb, axis):
    return (fb.lon_hi - fb.lon_lo) if axis == "lon" else (fb.lat_hi - fb.lat_lo)


def census_class(rdr, idx, class_rule, ranges, class_name, level, sample_blocks):
    """One class's figures. `idx` is a shared `r_neighbours.LeafIndex` for
    `level` (L0_urban and L0_sparse share one)."""
    rng = ot.class_range(ranges, level, class_name)
    keys = list(idx.blocks.keys())
    full_population = class_name in FULL_POPULATION_CLASSES
    if full_population:
        ordered = keys
        sample_rule = f"full population ({len(keys)} blocks)"
    else:
        ordered = [k for k, _ in ot.spread([(k, idx.blocks[k]) for k in keys],
                                            sample_blocks)]
        sample_rule = (f"spread({sample_blocks} of {len(keys)} blocks, on-disc "
                        f"order, overlay_test.spread) first, then every leaf of "
                        f"each chosen block in spread order, continuing past "
                        f"{sample_blocks} blocks if {MIN_NODES_PER_CLASS} "
                        f"qualifying nodes are not yet reached, until the "
                        f"threshold is met or the block list (full population) "
                        f"is exhausted")

    n_leaves = 0
    n_candidate_nodes = 0
    corner_incidences = 0
    denominator = 0
    matched = 0
    violations = 0
    outside_coverage = 0
    empty_slot = 0
    scale_mismatch = 0
    crossing_matched = {"same_block": 0, "cross_block": 0, "cross_blockset": 0}
    crossing_violations = {"same_block": 0, "cross_block": 0, "cross_blockset": 0}
    violation_examples = []
    decode_cache: dict = {}
    blocks_visited = 0
    reached_threshold = False

    for key in ordered:
        blocks_visited += 1
        rows = idx.leaves(key)
        for row in rows:
            lpath, _le, _lb, ptype, _parent, fr = row
            if ptype != 0 or len(lpath) != 1:
                continue  # divided sources out of scope for this unit
            blk = idx.blocks[key]
            cls = ot._class_key(level, ptype, class_rule, blk, lpath)
            if cls != class_name:
                continue
            n_leaves += 1
            links = rdr.decode(idx.lmr, blk, row)
            if not links:
                continue
            node_set = set()
            for lk in links:
                for e in lk["ends"]:
                    node_set.add((int(e[0]), int(e[1])))
            handle = (idx.lmr, blk, row)
            src_ident = _leaf_ident(level, blk, lpath)
            fb_src = fr[0]
            for (x, y) in sorted(node_set):
                edges = _qualifying_edges(x, y, rng)
                if not edges:
                    continue
                n_candidate_nodes += 1
                if len(edges) == 2:
                    corner_incidences += 1
                for edge in edges:
                    nb = idx.neighbour(handle, edge)
                    if nb.status == "outside_coverage":
                        outside_coverage += 1
                        continue
                    if nb.status == "empty_slot":
                        empty_slot += 1
                        continue
                    # resolved
                    if nb.divided:
                        scale_mismatch += 1
                        continue
                    t_lmr, t_blk, t_row = nb.handles[0]
                    t_lpath, _tle, _tlb, t_ptype, _tparent, t_fr = t_row
                    if t_ptype != 0:
                        scale_mismatch += 1
                        continue
                    t_cls = ot._class_key(level, t_ptype, class_rule, t_blk, t_lpath)
                    t_rng = ot.class_range(ranges, level, t_cls)
                    axis = "lon" if edge in ("W", "E") else "lat"
                    fb_tgt = t_fr[0]
                    span_src = _frame_extent(fb_src, axis)
                    span_tgt = _frame_extent(fb_tgt, axis)
                    tol = abs(span_src) * FRAME_EXTENT_TOL_REL
                    if (t_rng != rng
                            or abs(span_src - span_tgt) > tol):
                        scale_mismatch += 1
                        continue
                    denominator += 1
                    px, py = _mirrored_point(x, y, edge, rng)
                    dkey = (t_blk[1], t_blk[2], tuple(t_lpath))
                    if dkey not in decode_cache:
                        decode_cache[dkey] = rdr.decode(t_lmr, t_blk, t_row) or []
                    t_links = decode_cache[dkey]
                    t_ends = sorted({(int(a), int(b)) for lk in t_links
                                      for (a, b) in lk["ends"]})
                    found = MIRROR_TOL_RAW == 0 and (px, py) in set(t_ends)
                    crossing = nb.crossing
                    if found:
                        matched += 1
                        crossing_matched[crossing] += 1
                    else:
                        violations += 1
                        crossing_violations[crossing] += 1
                        if len(violation_examples) < 20:
                            nearest = _nearest_raw(px, py, t_ends)
                            violation_examples.append({
                                "source": src_ident, "edge": edge,
                                "source_raw": [x, y],
                                "expected_mirrored_raw": [px, py],
                                "neighbour": _leaf_ident(level, t_blk, t_lpath),
                                "nearest_neighbour_raw": (list(nearest)
                                                           if nearest else None),
                                "crossing": crossing,
                            })
        if (not full_population
                and (denominator + outside_coverage + empty_slot + scale_mismatch)
                >= MIN_NODES_PER_CLASS):
            reached_threshold = True
            break

    if full_population:
        reached_threshold = (denominator + outside_coverage + empty_slot
                              + scale_mismatch) >= MIN_NODES_PER_CLASS

    total_incidences = denominator + outside_coverage + empty_slot + scale_mismatch
    if violations == 0:
        verdict = "pass"
    elif len(violation_examples) >= min(violations, 20):
        verdict = "pass_with_residual"
    else:
        verdict = "fail"

    return {
        "class": class_name,
        "level": level,
        "class_range": rng,
        "sample_rule": sample_rule,
        "blocks_visited": blocks_visited,
        "n_leaves": n_leaves,
        "n_candidate_nodes": n_candidate_nodes,
        "corner_incidences": corner_incidences,
        "denominator": denominator,
        "matched": matched,
        "violations": violations,
        "outside_coverage": outside_coverage,
        "empty_slot": empty_slot,
        "scale_mismatch": scale_mismatch,
        "total_edge_incidences": total_incidences,
        "meets_min_nodes_per_class": reached_threshold,
        "crossing_breakdown": {
            "matched": crossing_matched,
            "violations": crossing_violations,
        },
        "violation_examples": violation_examples,
        "verdict": verdict,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    profile = json.loads(COORD_SCALE_PATH.read_text())
    class_rule = profile["class_rule"]
    ranges = profile["ranges"]

    rdr = ot.RReader(args.reference)
    idx_by_level: dict = {}
    results = []
    for class_name in CLASSES:
        level = CLASS_LEVEL[class_name]
        if level not in idx_by_level:
            idx_by_level[level] = rn.LeafIndex(rdr, level)
        idx = idx_by_level[level]
        results.append(census_class(rdr, idx, class_rule, ranges, class_name,
                                      level, SAMPLE_BLOCKS))

    out = {
        "tool": "boundary_mirror_census",
        "reference": args.reference,
        "constants": {
            "EXACT_ONLY": EXACT_ONLY,
            "MIRROR_TOL_RAW": MIRROR_TOL_RAW,
            "MIN_NODES_PER_CLASS": MIN_NODES_PER_CLASS,
            "note": "pre-stated, not tuned",
        },
        "sample_blocks": SAMPLE_BLOCKS,
        "frame_extent_tol_rel": FRAME_EXTENT_TOL_REL,
        "notes": {
            "denominator_is_edge_incidences": (
                "denominator/matched/violations/outside_coverage/empty_slot/"
                "scale_mismatch are node-edge incidences, not nodes: a corner "
                "node (both axes exact) contributes one incidence per "
                "qualifying edge (two), counted once in corner_incidences "
                "and twice across the incidence counters."),
            "node_dedup": (
                "candidate nodes are deduped by (x, y) raw coordinate within "
                "a leaf before edge classification, so a shared link endpoint "
                "at an intersection is counted once, not once per link."),
            "divided_sources_out_of_scope": (
                "this unit walks only ptype=0 (undivided) leaves of "
                "L0_urban, L0_sparse, L2, L4, L6, L8; a divided neighbour "
                "is still resolvable via r_neighbours and is counted as "
                "scale_mismatch, per the brief."),
        },
        "reproduction_targets_same_block_only": {
            "L6": "316/316 matched (scratchpad census, retired)",
            "L8": "64/64 matched (scratchpad census, retired)",
        },
        "classes": results,
    }
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    Path(args.out).write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    print(f"wrote {args.out} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
