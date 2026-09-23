#!/usr/bin/env python3
"""Boundary-node mirror check across resolved neighbours (Plan 03 unit
2-14, criterion 4), rerun against 2-13's frame-level adjacency and the
level's global raw lattice, per DESIGN Decisions, "Amendment 2026-09-23
(design agent) -- the adjacency unit is the frame, not the leaf slot", and
the 2-14 brief that cites it.

Criterion 4 (restated by the brief): "A link end node exactly on a frame
edge is answered by an end node at the identical global (X, Y) in a frame
sharing that point. Per node, at exact integer equality, zero tolerance.
Denominator: all exact-coordinate nodes with at least one resolvable
sharing frame, nodes at the extract's outer edge excluded from the
denominator rather than failed, and counted-and-reported exclusions
retained. A node at a frame corner is satisfied by any of the frames
sharing that point (2-13's `corner_frames`), not by one nominated edge
neighbour; report corner nodes separately, as nodes, and state the
per-edge figure too so the 2-11 comparison is possible. `scale_mismatch` is
no longer an exclusion for an ordinary cross-class crossing (a 4096 frame
facing a 16384 frame is now folded into the denominator as an ordinary
crossing, since the lattice places both correctly); it remains an
exclusion only for a neighbour that resolves to a genuinely divided leaf
(a different coordinate scale)."

Root cause fixed here (GATE-2.md carried item 7, DESIGN.md's design-agent
amendment): the 2-11 run used the leaf-slot `LeafIndex.neighbour` (one-slot
step) for L0_sparse, self-neighbouring 12 of the tile's 16 aliased slots,
and excluded every cross-class (4096-vs-16384) crossing as `scale_mismatch`
even though the lattice places it correctly -- both together manufactured
most of the 8652/11536 L0_sparse violations. This version walks one frame
per distinct `FrameId`, matches per NODE (not per edge incidence) via
`r_neighbours.frame_neighbour`/`corner_frames`/`to_global`, and folds
cross-class crossings into the ordinary denominator.

Verdict-logic defect fixed here (GATE-2.md criterion 4 discussion): the
2-11 tool's `elif len(violation_examples) >= min(violations, 20): verdict =
"pass_with_residual"` labelled a class `pass_with_residual` whenever it
could print up to 20 examples, regardless of what share of the violations
those 20 covered -- so L0_sparse's 8652/11536 (75%) failure was labelled
`pass_with_residual`. Fixed per the brief's binding instruction: `pass` at
zero violations; `pass_with_residual` ONLY when every violation is
enumerated in the output (`violation_examples` cap tied to
`RESIDUAL_ENUM_CAP`, not a fixed 20); `fail` otherwise.

Pre-stated constants (fixed before this unit's first run; not tuned after
seeing a result -- a constant that turns out wrong is a `needs context`
report, not an edit):

- EXACT_ONLY = True -- a node qualifies only when its raw crossed-axis
  coordinate is exactly 0 or exactly the frame range, as an integer.
- MIRROR_TOL_RAW = 0 -- a match is exact integer equality of the global
  raw lattice coordinate (`r_neighbours.to_global`), zero tolerance.
- MIN_NODES_PER_CLASS = 300 -- the minimum qualifying nodes per class
  before a class's figure is reportable; L6, L8 and any smaller class are
  measured over their whole population.
- RESIDUAL_ENUM_CAP = 400 -- see `continuity_census.py`'s module docstring
  for the brief-vs-DESIGN.md discrepancy (400 here, 200 there); this run
  follows the brief and reports the discrepancy rather than resolving it
  silently.

Reads R only through `harness.walk` reading paths, `overlay_test.RReader`
and `r_neighbours`'s frame-adjacency API (2-13, reused unmodified); imports
no writer module. y increases northward (coordconv, 2-06): edge "N" is
+gy/+y, "S" is -gy/-y, "W" is -gx/-x, "E" is +gx/+x.
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
RESIDUAL_ENUM_CAP = 400

COORD_SCALE_PATH = ROOT / "refdata" / "profile" / "coord_scale.json"

# One class per leaf-population this unit walks. L0 splits into two classes
# by the same class rule overlay_test/coord_scale.json use; L2/L4/L6/L8 are
# each one class. divided_pardiv1 sources are out of scope for this unit
# (not named in the brief's Changes section); a divided *neighbour* is
# still handled, as a scale_mismatch exclusion, since a divided leaf is a
# genuinely different coordinate scale (quadrant-relative), not an ordinary
# cross-class crossing.
CLASSES = ["L0_urban", "L0_sparse", "L2", "L4", "L6", "L8"]
CLASS_LEVEL = {"L0_urban": 0, "L0_sparse": 0, "L2": 2, "L4": 4, "L6": 6, "L8": 8}
FULL_POPULATION_CLASSES = {"L6", "L8"}
SAMPLE_BLOCKS = 40  # stated block count for the spread-sampled classes
CORNERS = {("W", "S"): "SW", ("W", "N"): "NW", ("E", "S"): "SE", ("E", "N"): "NE"}


def _qualifying_edges(x, y, rng):
    """Edges (up to two, for a corner) that (x, y) qualifies for, exactly,
    against frame range `rng`."""
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


def _leaf_ident(level, blk, lpath):
    return {"level": level, "blockset_index": blk[1], "block_index": blk[2],
            "leaf_path": list(lpath)}


def _nearest_raw(g, points):
    if not points:
        return None
    return min(points, key=lambda e: (e[0] - g[0]) ** 2 + (e[1] - g[1]) ** 2)


def _resolve_targets(idx, fid, edge_or_corner_frames, class_rule, ranges, rdr, cache):
    """`edge_or_corner_frames` is a `rn.FrameNeighbour`. Returns a list of
    candidate dicts (fid, ident, global set of end-node coords, is_divided),
    decoding/caching each target frame's representative leaf at most once."""
    out = []
    for tgt_fid, handles, crossing in zip(edge_or_corner_frames.frames,
                                           edge_or_corner_frames.handles,
                                           edge_or_corner_frames.crossings):
        if tgt_fid in cache:
            out.append(cache[tgt_fid])
            continue
        t_lmr, t_blk, t_row = handles[0]
        t_lpath, _tle, _tlb, t_ptype, _tparent, t_fr = t_row
        is_divided = t_ptype != 0
        entry = {"fid": tgt_fid, "crossing": crossing, "divided": is_divided,
                 "rng": tgt_fid.n * rn.RAW_PER_SLOT,
                 "ident": _leaf_ident(t_lmr.level, t_blk, t_lpath), "global": []}
        if not is_divided:
            t_links = rdr.decode(t_lmr, t_blk, t_row)
            if t_links:
                t_ends = {(int(a), int(b)) for lk in t_links for (a, b) in lk["ends"]}
                entry["global"] = [rn.to_global(tgt_fid, x, y) for (x, y) in t_ends]
        cache[tgt_fid] = entry
        out.append(entry)
    return out


def census_class(rdr, idx, class_rule, ranges, class_name, level, sample_blocks):
    """One class's figures. `idx` is a shared `r_neighbours.LeafIndex` for
    `level` (L0_urban and L0_sparse share one). Walks one FRAME per
    distinct `FrameId` (an L0 sparse tile's 16 aliased leaf slots
    contribute one frame), matches per NODE via the global raw lattice."""
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
                        f"each chosen block in spread order, one frame per "
                        f"distinct FrameId, continuing past {sample_blocks} "
                        f"blocks if {MIN_NODES_PER_CLASS} qualifying nodes are "
                        f"not yet reached, until the threshold is met or the "
                        f"block list (full population) is exhausted")

    n_frames = 0
    n_candidate_nodes = 0
    corner_nodes = 0
    denominator = 0
    matched = 0
    violations = 0
    outside_coverage = 0
    empty_slot = 0
    scale_mismatch = 0
    cross_class_matched = cross_class_violations = 0
    corner_matched = corner_violations = 0
    # per-edge reading of corner nodes (each of a corner's two edges tested
    # independently, as 2-11 did), reported alongside the per-node reading
    # for comparability.
    corner_per_edge_matched = corner_per_edge_violations = 0
    crossing_matched = {"same_block": 0, "cross_block": 0, "cross_blockset": 0}
    crossing_violations = {"same_block": 0, "cross_block": 0, "cross_blockset": 0}
    violation_examples = []
    seen_frames: set = set()
    target_cache: dict = {}
    blocks_visited = 0
    reached_threshold = False

    def _test_against(candidates, g):
        """True if global point g is present in any candidate's node set
        (excluding divided candidates, which are scale_mismatch)."""
        for c in candidates:
            if not c["divided"] and g in c["global"]:
                return True, c
        return False, None

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
            handle = (idx.lmr, blk, row)
            fid, agrees = rn.frame_of(idx, handle, class_rule, ranges)
            if fid in seen_frames:
                continue
            seen_frames.add(fid)
            n_frames += 1
            links = rdr.decode(idx.lmr, blk, row)
            if not links:
                continue
            node_set = sorted({(int(e[0]), int(e[1])) for lk in links for e in lk["ends"]})
            src_ident = _leaf_ident(level, blk, lpath)
            edge_nb_cache: dict = {}
            for (x, y) in node_set:
                edges = _qualifying_edges(x, y, rng)
                if not edges:
                    continue
                n_candidate_nodes += 1
                g = rn.to_global(fid, x, y)
                is_corner = len(edges) == 2

                if is_corner:
                    corner_nodes += 1
                    corner = CORNERS[(edges[0], edges[1])]
                    cnb = rn.corner_frames(idx, fid, corner, class_rule, ranges)
                    if cnb.status == "outside_coverage":
                        outside_coverage += 1
                    elif cnb.status == "empty_slot":
                        empty_slot += 1
                    else:
                        candidates = _resolve_targets(idx, fid, cnb, class_rule, ranges,
                                                        rdr, target_cache)
                        if all(c["divided"] for c in candidates):
                            scale_mismatch += 1
                        else:
                            found, hit = _test_against(candidates, g)
                            denominator += 1
                            crossing = hit["crossing"] if hit else candidates[0]["crossing"]
                            cross_class = any((not c["divided"]) and c["rng"] != rng for c in candidates)
                            if found:
                                matched += 1
                                corner_matched += 1
                                crossing_matched[crossing] += 1
                                if cross_class:
                                    cross_class_matched += 1
                            else:
                                violations += 1
                                corner_violations += 1
                                crossing_violations[crossing] += 1
                                if cross_class:
                                    cross_class_violations += 1
                                if len(violation_examples) < RESIDUAL_ENUM_CAP:
                                    all_global = [p for c in candidates for p in c["global"]]
                                    nearest = _nearest_raw(g, all_global)
                                    violation_examples.append({
                                        "source": src_ident, "edge": "corner:" + corner,
                                        "source_raw": [x, y], "source_global": list(g),
                                        "candidate_frames": [c["ident"] for c in candidates],
                                        "nearest_actual_global": (list(nearest)
                                                                   if nearest else None),
                                        "crossing": crossing, "corner": True,
                                    })

                # per-edge reading (always computed, for corner AND
                # non-corner nodes; feeds corner_per_edge_* for corners and
                # the ordinary per-node result for a single-edge node).
                for edge in edges:
                    if edge not in edge_nb_cache:
                        edge_nb_cache[edge] = rn.frame_neighbour(idx, fid, edge, class_rule,
                                                                   ranges)
                    fnb = edge_nb_cache[edge]
                    if fnb.status == "outside_coverage":
                        if not is_corner:
                            outside_coverage += 1
                        continue
                    if fnb.status == "empty_slot":
                        if not is_corner:
                            empty_slot += 1
                        continue
                    candidates = _resolve_targets(idx, fid, fnb, class_rule, ranges,
                                                    rdr, target_cache)
                    if all(c["divided"] for c in candidates):
                        if not is_corner:
                            scale_mismatch += 1
                        continue
                    found, hit = _test_against(candidates, g)
                    crossing = hit["crossing"] if hit else candidates[0]["crossing"]
                    cross_class = any((not c["divided"]) and c["rng"] != rng for c in candidates)
                    if is_corner:
                        if found:
                            corner_per_edge_matched += 1
                        else:
                            corner_per_edge_violations += 1
                        continue
                    denominator += 1
                    if found:
                        matched += 1
                        crossing_matched[crossing] += 1
                        if cross_class:
                            cross_class_matched += 1
                    else:
                        violations += 1
                        crossing_violations[crossing] += 1
                        if cross_class:
                            cross_class_violations += 1
                        if len(violation_examples) < RESIDUAL_ENUM_CAP:
                            all_global = [p for c in candidates for p in c["global"]]
                            nearest = _nearest_raw(g, all_global)
                            violation_examples.append({
                                "source": src_ident, "edge": edge,
                                "source_raw": [x, y], "source_global": list(g),
                                "candidate_frames": [c["ident"] for c in candidates],
                                "nearest_actual_global": (list(nearest) if nearest else None),
                                "crossing": crossing, "corner": False,
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
    fully_enumerated = len(violation_examples) == violations
    if violations == 0:
        verdict = "pass"
    elif fully_enumerated:
        verdict = "pass_with_residual"
    else:
        verdict = "fail"

    return {
        "class": class_name,
        "level": level,
        "class_range": rng,
        "sample_rule": sample_rule,
        "blocks_visited": blocks_visited,
        "n_frames": n_frames,
        "n_candidate_nodes": n_candidate_nodes,
        "corner_nodes": corner_nodes,
        "denominator": denominator,
        "matched": matched,
        "violations": violations,
        "outside_coverage": outside_coverage,
        "empty_slot": empty_slot,
        "scale_mismatch": scale_mismatch,
        "total_incidences": total_incidences,
        "meets_min_nodes_per_class": reached_threshold,
        "crossing_breakdown": {
            "matched": crossing_matched,
            "violations": crossing_violations,
        },
        "cross_class_split": {"matched": cross_class_matched,
                               "violations": cross_class_violations},
        "corner_split_per_node": {"matched": corner_matched, "violations": corner_violations},
        "corner_split_per_edge_2_11_comparable": {
            "matched": corner_per_edge_matched, "violations": corner_per_edge_violations},
        "violation_examples_fully_enumerated": fully_enumerated,
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
            "RAW_PER_SLOT": rn.RAW_PER_SLOT,
            "note": "pre-stated, not tuned; FRAME_EXTENT_TOL_REL retired 2-14 "
                    "(the global raw lattice replaces frame-bbox-span "
                    "comparison for detecting a genuine scale mismatch)",
        },
        "sample_blocks": SAMPLE_BLOCKS,
        "residual_enum_cap": RESIDUAL_ENUM_CAP,
        "residual_enum_cap_note": "brief (2-14-continuity-and-mirror-rerun.md) states 400; "
                                   "DESIGN.md's design-agent amendment states 200 for this "
                                   "same cap -- both exceed the measured residual with "
                                   "margin; this run follows the brief and reports the "
                                   "discrepancy rather than resolving it silently.",
        "notes": {
            "denominator_is_nodes": (
                "denominator/matched/violations/outside_coverage/empty_slot/"
                "scale_mismatch are per NODE (2-14), not per edge incidence "
                "(2-11's reading): a corner node (both axes exact) is tested "
                "once via corner_frames' any-sharing-frame rule, counted once "
                "in corner_nodes and once across the incidence counters. The "
                "corner's per-edge reading (2-11-comparable, each of the two "
                "edges tested independently) is reported separately in "
                "corner_split_per_edge_2_11_comparable and is NOT part of "
                "denominator/matched/violations."),
            "node_dedup": (
                "candidate nodes are deduped by (x, y) raw coordinate within "
                "a leaf before edge classification, so a shared link endpoint "
                "at an intersection is counted once, not once per link."),
            "cross_class_no_longer_excluded": (
                "a neighbour of a different frame size (e.g. an L0_urban "
                "n=1 frame facing an L0_sparse n=4 tile) is an ordinary "
                "crossing, included in denominator/matched/violations and "
                "reported separately in cross_class_split. scale_mismatch "
                "now means only: every candidate frame at that edge/corner "
                "resolves to a genuinely divided leaf (a different "
                "coordinate scale, quadrant-relative)."),
            "divided_sources_out_of_scope": (
                "this unit walks only ptype=0 (undivided) leaves of "
                "L0_urban, L0_sparse, L2, L4, L6, L8; a divided neighbour "
                "is still resolvable via r_neighbours and is counted as "
                "scale_mismatch."),
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
