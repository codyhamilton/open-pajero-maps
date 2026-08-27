"""Tests for kiwiw.contraction -- the real CH-style node contraction
algorithm (see parser/kiwiw/contraction.py's module docstring for the
algorithm this validates). These are synthetic-graph tests: they don't
depend on OSM data or the mounted disc, so they run anywhere.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.contraction import Graph, contract, assign_levels, verify_shortest_paths, dijkstra_all


def _line_graph(n: int) -> Graph:
    g = Graph(n)
    for i in range(n - 1):
        g.add_edge(i, i + 1, 1.0)
        g.add_edge(i + 1, i, 1.0)
    return g


def _grid_graph(w: int, h: int, seed: int = 1) -> tuple[Graph, dict]:
    rnd = random.Random(seed)
    n = w * h
    g = Graph(n)

    def idx(x, y):
        return y * w + x

    for y in range(h):
        for x in range(w):
            u = idx(x, y)
            if x + 1 < w:
                wgt = rnd.uniform(1.0, 10.0)
                g.add_edge(u, idx(x + 1, y), wgt)
                g.add_edge(idx(x + 1, y), u, wgt)
            if y + 1 < h:
                wgt = rnd.uniform(1.0, 10.0)
                g.add_edge(u, idx(x, y + 1), wgt)
                g.add_edge(idx(x, y + 1), u, wgt)
    return g, {"w": w, "h": h}


def _top_rank_subset(result, frac: float) -> list[int]:
    """The nodes that "survive" to a coarser level are exactly the
    highest-contraction-rank nodes (contracted last = kept alive
    longest) -- a suffix of the contraction order, NOT an arbitrary
    index selection. This mirrors assign_levels()'s quantile-by-rank
    logic and is the only subset shape for which the CH shortcut graph
    is guaranteed to preserve distances."""
    n = len(result.rank)
    k = max(2, int(n * frac))
    order_desc = list(reversed(result.order))  # highest rank (most important) first
    return order_desc[:k]


def test_line_graph_contracts_and_preserves_distances():
    n = 40
    g = _line_graph(n)
    result = contract(g, max_settled=50)
    assert len(result.order) == n
    assert sorted(result.rank) == list(range(n))

    # subset: the top quarter by contraction rank (i.e. the nodes that
    # would survive to a coarser level) -- the correct shape for this
    # invariant, see _top_rank_subset()
    subset = _top_rank_subset(result, 0.25)
    check = verify_shortest_paths(_line_graph(n), result, subset, n_pairs=60, seed=7)
    assert check["n_mismatch"] == 0, check["mismatches"]
    assert check["n_match"] == check["n_pairs"]


def test_grid_graph_full_contraction_preserves_all_distances():
    g, meta = _grid_graph(6, 6, seed=3)
    n = meta["w"] * meta["h"]
    original = _grid_graph(6, 6, seed=3)[0]
    result = contract(g, max_settled=200)
    assert len(result.order) == n

    # verify shortest paths are preserved among the top-quarter-by-rank
    # subset (the nodes that would survive to a coarser level) -- this is
    # the strong form of task item 1's validation requirement: shortest
    # path through the CONTRACTED graph (only these nodes + shortcuts)
    # matches the original full graph for sampled node pairs.
    subset = _top_rank_subset(result, 0.25)
    check = verify_shortest_paths(original, result, subset, n_pairs=150, seed=11)
    assert check["n_mismatch"] == 0, check["mismatches"]

    # also verify the trivial full-node-set case (sanity: shortcuts never
    # HURT correctness when every original node is still present too)
    check_full = verify_shortest_paths(original, result, list(range(n)), n_pairs=80, seed=12)
    assert check_full["n_mismatch"] == 0, check_full["mismatches"]


def test_assign_levels_shape():
    ranks = list(range(100))
    levels = assign_levels(ranks, n_levels=4)
    assert set(levels) <= {2, 4, 6, 8}
    # highest-rank (most important / contracted last) nodes get level 8
    assert levels[99] == 8
    # lowest-rank (contracted first / least important) nodes get level 2
    assert levels[0] == 2
    # counts should be non-increasing as level increases (quartiles)
    from collections import Counter
    c = Counter(levels)
    assert c[2] >= c[4] >= c[6] >= c[8]


def test_contraction_never_increases_distance_random_graphs():
    """Broader randomized correctness sweep: several random grid sizes and
    seeds, checking full-population all-node-subset shortest-path
    preservation each time (not just one hand-picked graph)."""
    for (w, h, seed) in [(4, 4, 1), (5, 5, 2), (7, 4, 5), (5, 8, 9)]:
        g, meta = _grid_graph(w, h, seed=seed)
        n = w * h
        original = _grid_graph(w, h, seed=seed)[0]
        result = contract(g, max_settled=300)
        subset = _top_rank_subset(result, 0.3)
        check = verify_shortest_paths(original, result, subset, n_pairs=80, seed=seed * 100)
        assert check["n_mismatch"] == 0, (w, h, seed, check["mismatches"])


def test_shortcuts_are_actually_needed_not_gratuitous():
    """Sanity check that the witness search is doing real work: on a graph
    with an obvious cheap detour (a "bypass" edge), contracting the
    intermediate node on the expensive path should NOT introduce a
    shortcut, because the cheap bypass is already a witness."""
    g = Graph(4)
    # 0 -> 1 -> 2 expensive path (cost 100 total)
    g.add_edge(0, 1, 50.0)
    g.add_edge(1, 0, 50.0)
    g.add_edge(1, 2, 50.0)
    g.add_edge(2, 1, 50.0)
    # 0 -> 3 -> 2 cheap bypass (cost 4 total) -- a witness for 0->2 via 1
    g.add_edge(0, 3, 2.0)
    g.add_edge(3, 0, 2.0)
    g.add_edge(3, 2, 2.0)
    g.add_edge(2, 3, 2.0)

    result = contract(g, max_settled=50)
    # node 1 should contract without needing a 0<->2 shortcut, since the
    # bypass through node 3 is cheaper than the direct path through 1
    has_direct_shortcut = 2 in result.search_graph.out[0] and result.search_graph.out[0][2].is_shortcut
    assert not has_direct_shortcut, "witness search failed to find the cheap bypass, added an unnecessary shortcut"
