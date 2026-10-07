"""Plan 44 Phase 1: synthetic cases for bg_owner_exclusive (shared vertex, edge, different-type)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent/"tools"), str(HERE), str(HERE / "fixtures/harness")]

from kiwiw import cbuild  # noqa: E402
import bg_owner_exclusive as oe  # noqa: E402


@pytest.fixture(scope="module")
def probe():
    so = oe.compile_probe()
    return oe.load_probe(so)


RECT = (0.0, 0.0, 4096.0, 4096.0)


def test_compile_probe_is_stable(probe):
    assert probe is not None


def test_shared_vertex_not_owner_exclusive(probe):
    # Two rings share the edge (2048,1024)-(2048,3072). Interior verts of A are exclusive;
    # the shared edge verts are not.
    A = [(1024, 1024), (2048, 1024), (2048, 3072), (1024, 3072)]
    B = [(2048, 1024), (3072, 1024), (3072, 3072), (2048, 3072)]
    sa, _, ba = oe.clip_ring(probe, A, RECT)
    sb, _, bb = oe.clip_ring(probe, B, RECT)
    assert sa > 0 and sb > 0
    va, vb = oe.wire_vertices(ba), oe.wire_vertices(bb)
    excl = oe.owner_exclusive_vertices(va, [vb], RECT)
    shared = set(va) & set(vb)
    assert shared
    assert all(p not in shared for p in excl)
    assert all(not oe.on_rect_boundary(x, y, RECT) for x, y in excl)
    # At least one interior vertex of A survives as exclusive.
    assert excl


def test_leaf_edge_vertex_excluded(probe):
    # Ring sitting on the left edge of the leaf: every vertex on x=0 is on the boundary.
    ring = [(0, 1024), (1024, 1024), (1024, 3072), (0, 3072)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    assert size > 0
    verts = oe.wire_vertices(blob)
    excl = oe.owner_exclusive_vertices(verts, [], RECT)
    assert all(not oe.on_rect_boundary(x, y, RECT) for x, y in excl)
    # The two left-edge verts must not appear.
    assert (0, 1024) not in excl and (0, 3072) not in excl


def test_different_type_supplier_blocks_exclusivity(probe):
    # Same geometry, treated as two suppliers (type is irrelevant at the vertex layer:
    # the design's candidate set is "every source of any type whose bbox meets L").
    ring = [(512, 512), (3584, 512), (3584, 3584), (512, 3584)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    assert size > 0
    verts = oe.wire_vertices(blob)
    # A second "different-type" supplier with identical vertices → no exclusive verts.
    excl = oe.owner_exclusive_vertices(verts, [verts], RECT)
    assert excl == []


def test_find_producer_unique_and_ambiguous(probe):
    ring = [(512, 512), (3584, 512), (3584, 3584), (512, 3584)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    assert size > 0
    # Unique: only one candidate matches.
    status, pid = oe.find_producer(probe, blob, [("S0", ring), ("S1", [(100, 100), (200, 100), (200, 200)])])
    assert status == "unique" and pid == "S0"
    # Ambiguous: two identical candidates.
    status, pid = oe.find_producer(probe, blob, [("S0", ring), ("S1", ring)])
    assert status == "producer-ambiguous" and pid is None
    # None: no candidate matches.
    status, pid = oe.find_producer(probe, blob, [("S1", [(100, 100), (200, 100), (200, 200)])])
    assert status == "none" and pid is None


def test_failing_vertices_excluded(probe):
    ring = [(512, 512), (3584, 512), (3584, 3584), (512, 3584)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    verts = oe.wire_vertices(blob)
    # Pick an interior (not-on-boundary) vertex so the exclusion is visible.
    interior = next(p for p in verts if not oe.on_rect_boundary(p[0], p[1], RECT))
    fail = {interior}
    excl = oe.owner_exclusive_vertices(verts, [], RECT, failing=fail)
    base = set(oe.owner_exclusive_vertices(verts, [], RECT))
    assert interior not in excl
    assert set(excl) == base - fail


def test_bbox_meets_rect():
    assert oe.bbox_meets_rect([(100, 100), (200, 200)], (0, 0, 4096, 4096))
    assert not oe.bbox_meets_rect([(5000, 5000), (6000, 6000)], (0, 0, 4096, 4096))
    assert oe.bbox_meets_rect([(-10, 100), (10, 200)], (0, 0, 4096, 4096))  # crosses edge
