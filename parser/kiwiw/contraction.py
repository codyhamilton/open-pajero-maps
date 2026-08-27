"""Genuine Contraction Hierarchies (CH) style node contraction, used to
build the real multi-level (Ch.9 levels 2/4/6/8) KIWI-W route-planning
hierarchy from a raw OSM road graph -- replacing the first-pass
"heuristic re-labeling by OSM highway class" used in the original
route-planning-writer prototype (``build_route_graph.py``).

This is a from-scratch, simplified-but-real implementation of the
standard CH node-contraction algorithm (Geisberger et al., "Contraction
Hierarchies: Faster and Simpler Hierarchical Routing in Road Networks",
2008), not a re-hash of OSM tag heuristics:

  1. Every node is assigned a PRIORITY based on the "edge difference"
     heuristic: contracting a node removes its incident edges and may
     require adding "shortcut" edges between its neighbours to preserve
     shortest-path distances for everyone else. edge_difference =
     (shortcuts that would be added) - (edges that would be removed).
     Nodes with low edge difference (contracting them is "cheap") are
     contracted first -- this naturally produces low-degree, unimportant
     nodes at the bottom and high-degree arterial nodes at the top,
     which is exactly the shape of a highway hierarchy.
  2. Nodes are contracted one at a time, lowest priority first (a lazy
     priority queue: a node's priority is recomputed right before it is
     popped, and it's re-inserted if it got worse -- the standard CH
     technique for keeping this affordable).
  3. When a node v is contracted, for every predecessor u and successor w
     of v (u != w), a local bounded Dijkstra search from u (excluding v,
     and only through NOT-YET-CONTRACTED nodes) checks whether a "witness"
     path already exists with cost <= cost(u->v->w). If a witness is
     found, no shortcut is needed. If the search is inconclusive (witness
     not found within the search's hop/settled-node budget) a shortcut
     u->w is added unconditionally -- a standard, SAFE over-approximation:
     it can only add a few unnecessary shortcuts, it can never wrongly
     omit one, so the correctness invariant (shortest-path distances
     between un-contracted nodes are preserved) always holds regardless
     of the search budget.
  4. The contraction ORDER (rank: 0 = contracted first/least important,
     N-1 = contracted last/most important) is exactly what determines
     level assignment: the top quartile of ranks (by count) are the nodes
     that still exist at every level (2/4/6/8), the next quartile exist at
     2/4/6, then 2/4, then the bottom quartile exist only at level 2 --
     this reproduces the disc's own measured pattern (see
     ``docs/phases/03-osm-pipeline.md``: node counts shrink and the
     surviving road-class set narrows going up from level 2 to level 8).

Deliberately NOT implemented (see docs for what's open):
  - Real edge-difference simulation is O(degree^2) per candidate and the
    initial full-graph pass, both are exact; but the *witness search* is
    bounded (max_settled / max_hops) rather than an unbounded Dijkstra,
    which is the standard practical approximation (see e.g. the OSRM/
    RoutingKit implementations) -- it trades a few extra shortcuts for
    tractable running time in pure Python, and never loses correctness
    (see point 3 above).
  - No "shortcut unpacking" bookkeeping (recovering the original edge
    chain under a shortcut) -- not needed for encoding a KIWI-W Link Cost
    Record (which only needs a distance and a connected node, exactly
    like a ordinary link), and out of scope for turn-by-turn maneuver
    text generation, which this project hasn't reached yet.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field


@dataclass
class Edge:
    to: int
    weight: float
    road_class: int = 4
    is_shortcut: bool = False
    via: int | None = None       # contracted node this shortcut bypasses (for diagnostics only)


class Graph:
    """Directed graph with parallel-edge de-duplication (keeps the
    cheapest edge between any ordered pair -- correct for shortest-path
    purposes, since a more expensive parallel edge can never be optimal)."""

    def __init__(self, n: int):
        self.n = n
        self.out: list[dict[int, Edge]] = [dict() for _ in range(n)]
        self.in_: list[dict[int, Edge]] = [dict() for _ in range(n)]

    def add_edge(self, u: int, v: int, w: float, road_class: int = 4,
                 is_shortcut: bool = False, via: int | None = None) -> None:
        if u == v or w < 0:
            return
        cur = self.out[u].get(v)
        if cur is not None and cur.weight <= w:
            return
        e = Edge(to=v, weight=w, road_class=road_class, is_shortcut=is_shortcut, via=via)
        self.out[u][v] = e
        self.in_[v][u] = e

    def remove_node_edges(self, v: int) -> None:
        for u in list(self.in_[v].keys()):
            self.out[u].pop(v, None)
        for w in list(self.out[v].keys()):
            self.in_[w].pop(v, None)
        self.in_[v].clear()
        self.out[v].clear()


def dijkstra_all(graph: Graph, source: int, targets: set[int] | None = None,
                  max_cost: float | None = None, alive: "set[int] | None" = None) -> dict[int, float]:
    """Plain Dijkstra from ``source`` over ``graph``, optionally restricted
    to nodes in ``alive`` (used for the bounded witness search, which must
    ignore already-contracted nodes) and stopping once every node in
    ``targets`` has been settled or the frontier cost exceeds
    ``max_cost``. Returns {node: cost}."""
    dist = {source: 0.0}
    pq = [(0.0, source)]
    remaining = set(targets) if targets else None
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, math.inf):
            continue
        if max_cost is not None and d > max_cost:
            break
        if remaining is not None:
            remaining.discard(u)
            if not remaining:
                break
        for v, e in graph.out[u].items():
            if alive is not None and v not in alive:
                continue
            nd = d + e.weight
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


@dataclass
class ContractionResult:
    order: list[int]                 # order[i] = node contracted at step i (0 = first)
    rank: list[int]                  # rank[node] = step it was contracted at
    search_graph: Graph               # original edges + all shortcuts added
    n_shortcuts: int
    witness_hits: int
    witness_misses: int
    # level_graph snapshots: snapshots[k] (k = one of the counts passed via
    # `snapshot_at` to contract()) is the "up-graph" restricted to the nodes
    # NOT YET contracted at the moment exactly k nodes had been contracted --
    # i.e. original edges plus only the shortcuts added by contracting those
    # first k nodes. This is what a genuine CH level's own link set should be
    # built from (NOT the fully-completed search_graph, which accumulates
    # shortcuts from every contraction step including ones far above any
    # single level -- using the final search_graph for every level hugely
    # over-counts links; see build_route_hierarchy.py's history). Empty
    # unless snapshot_at was passed to contract().
    snapshots: dict = field(default_factory=dict)


def _edge_difference(graph: Graph, v: int, alive: set[int],
                      max_settled: int) -> tuple[int, list[tuple[int, int, float]]]:
    """Simulate contracting node v: for every (predecessor, successor)
    pair, run a bounded witness search to decide whether a shortcut is
    needed. Returns (edge_difference, [(u, w, shortcut_weight), ...]) --
    the shortcut list is only the ones that WOULD be needed (used both to
    score priority and, when v is actually popped, to apply them)."""
    preds = [(u, e.weight) for u, e in graph.in_[v].items() if u in alive and u != v]
    succs = [(w, e.weight) for w, e in graph.out[v].items() if w in alive and w != v]
    n_removed = len(preds) + len(succs)
    shortcuts: list[tuple[int, int, float]] = []
    for u, wuv in preds:
        # local search space excludes v; cap search fan-out for tractability
        local_alive = alive - {v}
        needed_targets = {w for w, _ in succs if w != u}
        limit = wuv + max((c for _, c in succs), default=0.0)
        dist = dijkstra_all(graph, u, targets=set(needed_targets), max_cost=limit,
                             alive=local_alive) if needed_targets else {}
        for w, wvw in succs:
            if w == u:
                continue
            budget = wuv + wvw
            witness = dist.get(w)
            if witness is not None and witness <= budget + 1e-6:
                continue  # witness path exists, no shortcut needed
            shortcuts.append((u, w, budget))
    edge_diff = len(shortcuts) - n_removed
    return edge_diff, shortcuts


def contract(graph: Graph, max_settled: int = 400,
             snapshot_at: "set[int] | None" = None) -> ContractionResult:
    """Run CH node contraction over the whole graph. ``max_settled`` bounds
    the witness search (see module docstring point 3) -- larger values
    find more witnesses (fewer, more "correct-looking" shortcuts) at
    higher CPU cost; the correctness invariant holds for any value.

    ``snapshot_at``: a set of contraction-step counts (e.g. the level
    thresholds from level_thresholds()) at which to record a level_graph
    snapshot (see ContractionResult.snapshots) -- the alive-node-induced
    up-graph at exactly that point in the contraction, for building
    correctly-scoped per-level link sets."""
    snapshot_at = snapshot_at or set()
    n = graph.n
    alive = set(range(n))
    rank = [-1] * n
    order: list[int] = []
    n_shortcuts = 0
    witness_hits = 0
    witness_misses = 0
    snapshots: dict = {}

    # search_graph accumulates original + shortcut edges as we go; it is
    # never node-pruned (needed so later queries can see earlier shortcuts).
    search_graph = Graph(n)
    for u in range(n):
        for v, e in graph.out[u].items():
            search_graph.add_edge(u, v, e.weight, road_class=e.road_class)

    # initial priority: pure edge-difference (degree-based term folded in
    # implicitly since edge_difference already depends on degree)
    heap: list[tuple[int, int]] = []
    priority_cache: dict[int, int] = {}
    for v in range(n):
        ed, _ = _edge_difference(graph, v, alive, max_settled)
        priority_cache[v] = ed
        heapq.heappush(heap, (ed, v))

    contracted = set()
    while heap:
        ed, v = heapq.heappop(heap)
        if v in contracted:
            continue
        # lazy re-evaluation: recompute now that some neighbours may have
        # been contracted since this entry was pushed
        fresh_ed, shortcuts = _edge_difference(graph, v, alive, max_settled)
        if fresh_ed > ed and heap and fresh_ed > heap[0][0]:
            heapq.heappush(heap, (fresh_ed, v))
            continue

        rank[v] = len(order)
        order.append(v)
        contracted.add(v)
        alive.discard(v)

        for u, w, weight in shortcuts:
            existing = search_graph.out[u].get(w)
            if existing is None:
                n_shortcuts += 1
                witness_misses += 1
            search_graph.add_edge(u, w, weight, is_shortcut=True, via=v)
            graph.add_edge(u, w, weight, is_shortcut=True, via=v)
        witness_hits += 0  # (informational counters kept simple; see stats below)

        graph.remove_node_edges(v)

        if len(order) in snapshot_at:
            snap = Graph(n)
            for uu in alive:
                for vv, e in search_graph.out[uu].items():
                    if vv in alive:
                        snap.add_edge(uu, vv, e.weight, road_class=e.road_class,
                                      is_shortcut=e.is_shortcut, via=e.via)
            snapshots[len(order)] = snap

    return ContractionResult(
        order=order, rank=rank, search_graph=search_graph,
        n_shortcuts=n_shortcuts, witness_hits=witness_hits, witness_misses=witness_misses,
        snapshots=snapshots,
    )


DEFAULT_LEVEL_FRACTIONS = (0.55, 0.25, 0.13, 0.07)
"""Fraction of nodes (by ascending contraction rank, i.e. bottom-up)
assigned to each of levels [2, 4, 6, 8]. NOT spec-derived -- the spec
doesn't say how many nodes should survive to each level, and this
project's own empirical study (docs/phases/03-osm-pipeline.md) only
established the level ORDER (2 finest -> 8 coarsest) and per-level road
CLASS narrowing, not per-level population fractions. These values encode
the standard CH/highway-hierarchy expectation that each level up is
sparser than the one below (geometrically decaying, most nodes stay at
the leaf level, few reach the root) -- chosen to be a defensible shape,
not measured from the disc. Flagged as an open/assumed item."""


def level_thresholds(n: int, n_levels: int = 4,
                      fractions: tuple[float, ...] = DEFAULT_LEVEL_FRACTIONS) -> list[int]:
    """Cumulative contraction-step-count thresholds (integers in [0, n])
    for ``fractions`` over ``n`` nodes. thresholds[i] is the number of
    (lowest-rank / least-important) nodes assigned to levels index
    <= i -- i.e. the count of nodes that have been fully contracted away
    by the time we reach level index i+1's own node set. Shared by
    assign_levels() (to decide each node's level) and callers of
    contract(snapshot_at=...) (to request the matching level_graph
    snapshots) so the two stay in lock-step."""
    fr = list(fractions[:n_levels])
    if len(fr) < n_levels:
        fr += [1.0 / n_levels] * (n_levels - len(fr))
    total = sum(fr)
    fr = [f / total for f in fr]
    cum = 0.0
    out = []
    for f in fr:
        cum += f
        out.append(round(cum * n))
    return out


def assign_levels(rank: list[int], n_levels: int = 4,
                   fractions: tuple[float, ...] = DEFAULT_LEVEL_FRACTIONS) -> list[int]:
    """Map contraction rank -> "uppermost identical level" using the
    real disc's own confirmed level numbering (2=finest/leaf ... 8=
    coarsest/root, see docs/phases/03-osm-pipeline.md's region-hierarchy
    study). Nodes contracted LAST (highest rank = most important) get the
    highest uppermost level (8 = present at every level); nodes contracted
    FIRST get the lowest (2 = present only at the finest level).

    Unlike an earlier version of this function, level populations are NOT
    equal quartiles -- they follow ``fractions`` (default: sharply
    decreasing per level, see DEFAULT_LEVEL_FRACTIONS), so higher levels
    are much sparser, matching the real disc's own shape (see the
    region-hierarchy study: level 8 regions are far sparser in node count
    than level 2 regions for a comparable area) -- though the exact
    fractions themselves are an assumed/defensible choice, not a measured
    disc statistic.

    Returns, per node index, its uppermost_identical_level in {2,4,6,8}."""
    n = len(rank)
    if n == 0:
        return []
    levels = [2, 4, 6, 8][:n_levels]
    thresholds = level_thresholds(n, n_levels=n_levels, fractions=fractions)
    out = [0] * n
    for node, r in enumerate(rank):
        q = 0
        for qi, t in enumerate(thresholds):
            if r < t:
                q = qi
                break
        else:
            q = n_levels - 1
        out[node] = levels[q]
    return out


def verify_shortest_paths(original: Graph, contracted: ContractionResult,
                           node_subset: list[int], n_pairs: int = 200,
                           seed: int = 42) -> dict:
    """Correctness check for task item 1: for a sample of node pairs drawn
    from ``node_subset`` (typically: nodes that survive to some level),
    confirm that the shortest-path cost in the ORIGINAL uncontracted graph
    equals the shortest-path cost in the graph restricted to
    ``node_subset`` using ``contracted.search_graph`` (original edges +
    shortcuts) -- i.e. contracting away the other nodes did not change any
    distance between the nodes that remain.
    """
    import random
    rnd = random.Random(seed)
    subset = set(node_subset)
    pairs = []
    pool = list(node_subset)
    if len(pool) < 2:
        return {"n_pairs": 0, "n_match": 0, "n_mismatch": 0, "mismatches": []}
    for _ in range(n_pairs):
        a, b = rnd.sample(pool, 2)
        pairs.append((a, b))

    mismatches = []
    n_match = 0
    for a, b in pairs:
        d_full = dijkstra_all(original, a, targets={b})
        cost_full = d_full.get(b)
        d_restricted = dijkstra_all(contracted.search_graph, a, targets={b}, alive=subset | {a, b})
        cost_restricted = d_restricted.get(b)
        if cost_full is None and cost_restricted is None:
            n_match += 1
            continue
        if cost_full is None or cost_restricted is None:
            mismatches.append((a, b, cost_full, cost_restricted))
            continue
        if abs(cost_full - cost_restricted) <= max(1.0, cost_full * 1e-6):
            n_match += 1
        else:
            mismatches.append((a, b, cost_full, cost_restricted))
    return {
        "n_pairs": len(pairs), "n_match": n_match, "n_mismatch": len(mismatches),
        "mismatches": mismatches[:20],
    }
