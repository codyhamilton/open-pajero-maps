"""Plan 44 Phase 1: synthetic cases for bg_owner_exclusive (shared vertex, edge, fragment)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent / "tools"), str(HERE), str(HERE / "fixtures/harness")]

import bg_owner_exclusive as oe  # noqa: E402


@pytest.fixture(scope="module")
def probe():
    so = oe.compile_probe()
    return oe.load_probe(so)


RECT = (0.0, 0.0, 4096.0, 4096.0)


def test_compile_probe_is_stable(probe):
    assert probe is not None


def test_shared_vertex_not_owner_exclusive(probe):
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
    assert excl


def test_leaf_edge_vertex_excluded(probe):
    ring = [(0, 1024), (1024, 1024), (1024, 3072), (0, 3072)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    assert size > 0
    verts = oe.wire_vertices(blob)
    excl = oe.owner_exclusive_vertices(verts, [], RECT)
    assert all(not oe.on_rect_boundary(x, y, RECT) for x, y in excl)
    assert (0, 1024) not in excl and (0, 3072) not in excl


def test_different_type_supplier_blocks_exclusivity(probe):
    ring = [(512, 512), (3584, 512), (3584, 3584), (512, 3584)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    assert size > 0
    verts = oe.wire_vertices(blob)
    excl = oe.owner_exclusive_vertices(verts, [verts], RECT)
    assert excl == []


def test_find_producer_unique_byte_and_ambiguous(probe):
    ring = [(512, 512), (3584, 512), (3584, 3584), (512, 3584)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    assert size > 0
    status, pid = oe.find_producer(probe, blob, [("S0", ring), ("S1", [(100, 100), (200, 100), (200, 200)])])
    assert status == "unique-byte" and pid == "S0"
    status, pid = oe.find_producer(probe, blob, [("S0", ring), ("S1", ring)])
    assert status == "producer-ambiguous" and pid is None
    status, pid = oe.find_producer(probe, blob, [("S1", [(100, 100), (200, 100), (200, 200)])])
    assert status == "producer_none" and pid is None


def test_failing_vertices_excluded(probe):
    ring = [(512, 512), (3584, 512), (3584, 3584), (512, 3584)]
    size, _, blob = oe.clip_ring(probe, ring, RECT)
    verts = oe.wire_vertices(blob)
    interior = next(p for p in verts if not oe.on_rect_boundary(p[0], p[1], RECT))
    fail = {interior}
    excl = oe.owner_exclusive_vertices(verts, [], RECT, failing=fail)
    base = set(oe.owner_exclusive_vertices(verts, [], RECT))
    assert interior not in excl
    assert set(excl) == base - fail


def test_bbox_meets_rect():
    assert oe.bbox_meets_rect([(100, 100), (200, 200)], (0, 0, 4096, 4096))
    assert not oe.bbox_meets_rect([(5000, 5000), (6000, 6000)], (0, 0, 4096, 4096))
    assert oe.bbox_meets_rect([(-10, 100), (10, 200)], (0, 0, 4096, 4096))


def test_identity_bearing_excludes_boundary_and_failing():
    rect = RECT
    verts = [(512, 512), (0, 1024), (3584, 3584)]
    fail = {(3584, 3584)}
    ib = oe.identity_bearing_vertices(verts, rect, failing=fail)
    assert (512, 512) in ib
    assert (0, 1024) not in ib
    assert (3584, 3584) not in ib


def test_unique_fragment_vs_full_leaf_and_ambiguous(probe):
    """EO fragment: disc record verts are a proper subset of one source's clip."""
    full = [(400, 400), (3700, 400), (3700, 3700), (400, 3700)]
    other = [(2000, 2000), (3800, 2000), (3800, 3800), (2000, 3800)]
    size_f, _, blob_full = oe.clip_ring(probe, full, RECT)
    assert size_f > 0
    full_verts = oe.wire_vertices(blob_full)
    ib = [p for p in full_verts if not oe.on_rect_boundary(p[0], p[1], RECT)]
    assert len(ib) >= 2
    frag_verts = ib[: max(2, len(ib) // 2)]
    fake_bytes = b"\x00fragment-not-a-real-wire\x00"
    status, pid = oe.find_producer(
        probe, fake_bytes, [("S0", full), ("S1", other)], RECT, record_verts=frag_verts,
    )
    assert status == "unique-fragment", (status, pid, frag_verts[:3])
    assert pid == "S0"
    status, pid = oe.find_producer(
        probe, fake_bytes, [("S0", full), ("S1", full)], RECT, record_verts=frag_verts,
    )
    assert status == "producer-ambiguous" and pid is None
    status, pid = oe.find_producer(
        probe, fake_bytes, [("S1", other)], RECT, record_verts=frag_verts,
    )
    assert status == "producer_none" and pid is None
    status, pid = oe.find_producer(
        probe, blob_full, [("S0", full), ("S1", other)], RECT, record_verts=frag_verts,
    )
    assert status == "unique-byte" and pid == "S0"


def test_find_producer_clip_cache_is_transparent(probe):
    """Plan 46: leaf-scoped clip_cache gives the same verdict as uncached, and is reused."""
    full = [(400, 400), (3700, 400), (3700, 3700), (400, 3700)]
    other = [(2000, 2000), (3800, 2000), (3800, 3800), (2000, 3800)]
    _s, _, blob_full = oe.clip_ring(probe, full, RECT)
    cands = [("S0", full), ("S1", other), ("S2", [(100, 100), (200, 100), (200, 200)])]
    cache = {}
    for rec in (blob_full, b"\x00none\x00"):
        a = oe.find_producer(probe, rec, cands, RECT)
        b = oe.find_producer(probe, rec, cands, RECT, clip_cache=cache)
        c = oe.find_producer(probe, rec, cands, RECT, clip_cache=cache)  # warm
        assert a == b == c
    assert len(cache) == 3


def test_find_producer_piecewise_matches_one_clip_piece(probe):
    """Plan 46: a clip emitting two pieces byte-matches each piece only when piecewise."""
    u = [(1000, 3000), (1000, 5000), (3000, 5000), (3000, 3000),
         (2500, 3000), (2500, 4500), (1500, 4500), (1500, 3000)]
    size, nrec, blob = oe.clip_ring(probe, u, RECT)
    pieces = oe.wire_records(blob)
    assert nrec == 2 and len(pieces) == 2 and b"".join(pieces) == blob
    cands = [("U", u), ("far", [(100, 100), (200, 100), (200, 200), (100, 200)])]
    for piece in pieces:
        assert oe.find_producer(probe, piece, cands, RECT) == ("producer_none", None)
        assert oe.find_producer(probe, piece, cands, RECT, piecewise=True) == ("unique-byte", "U")
    # whole blob still matches in both modes; duplicate producer is ambiguous
    assert oe.find_producer(probe, blob, cands, RECT, piecewise=True) == ("unique-byte", "U")
    assert oe.find_producer(probe, pieces[0], cands + [("U2", u)], RECT,
                            piecewise=True) == ("producer-ambiguous", None)
