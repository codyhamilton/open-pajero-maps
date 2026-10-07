"""Plan 50 — supply-path assembler unit tests (no heavy PBF / spool I/O)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from supply_path_assembler import (  # noqa: E402
    SUPPLY_RELATION_IDS, clip_rect, join_rings, make_bg, stitch_rings,
)


def test_clip_rect_unit_square():
    poly = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    out = clip_rect(poly, 0.5, 0.5, 1.5, 1.5)
    assert len(out) >= 3
    xs, ys = zip(*out)
    assert min(xs) >= 0.5 - 1e-9 and max(xs) <= 1.5 + 1e-9
    assert min(ys) >= 0.5 - 1e-9 and max(ys) <= 1.5 + 1e-9


def test_join_and_stitch_simple_outer():
    nodes = [1, 2, 3, 4, 1]
    coords = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]
    ways = {10: (nodes, coords)}
    members = [{"type": "w", "ref": 10, "role": "outer"}]
    rings = join_rings(members, ways)
    assert len(rings) == 1 and rings[0][0] == "outer"
    stitched = stitch_rings(rings)
    assert len(stitched) >= 4
    bg = make_bg(stitched)
    assert bg.type_code == 288 and bg.shape_class == 2 and bg.n_coords == len(stitched)


def test_supply_relation_ids_count():
    assert len(SUPPLY_RELATION_IDS) == 10
    assert 2647638 in SUPPLY_RELATION_IDS


def test_targets_341_fixture_present():
    p = Path("docs/plans/04-c-core-orchestration/triage/source_parity/implement/targets_341.json")
    if not p.exists():
        pytest.skip("implement targets not checked out")
    rows = json.loads(p.read_text())
    assert len(rows) == 341
    assert {r["relation_id"] for r in rows} == set(SUPPLY_RELATION_IDS)
