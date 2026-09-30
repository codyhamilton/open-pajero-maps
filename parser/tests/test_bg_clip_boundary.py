"""Background geometry is clipped to its frame, never clamped (Contract T,
boundary test on R-measured invariants; replaces the retired Python clipper's
`test_clip.py` and the C-vs-Python `test_cenc.py` cases, 3C-12).

Shapes go through the real boundary (fixture spool -> E1 -> E2) and the frame
is read back with the Python decoder; nothing here computes an expected byte.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "harness"))

import boundary  # noqa: E402
import e2_fixture  # noqa: E402
from kiwiw.model import BackgroundShape  # noqa: E402

LEVEL = 0
IX, IY = 1780, 814
B = e2_fixture.cell_bounds(LEVEL, IX, IY)
DLAT = B.lat_hi - B.lat_lo
DLON = B.lon_hi - B.lon_lo
TOL = max(DLAT, DLON) / B.require_range()  # one raw unit


def _shapes(cls: int, pts, type_code: int = 5):
    s = BackgroundShape(shape_class=cls, type_code=type_code, type_label="", n_coords=len(pts),
                        mult_const=1, underground=False, pen_up=False, coords=list(pts))
    with tempfile.TemporaryDirectory() as d:
        fb = e2_fixture.e2_frames(d, LEVEL, {(IX, IY): {"backgrounds": [s]}})[(IX, IY)]
    frame = boundary.decode_frame(fb, B).background
    return [] if frame is None else list(frame.shapes)


def _pt(fx: float, fy: float):
    """(lat, lon) at fractions of the cell (may lie outside 0..1)."""
    return (B.lat_lo + fy * DLAT, B.lon_lo + fx * DLON)


def _on_edge(p) -> bool:
    lat, lon = p
    return (min(abs(lat - B.lat_lo), abs(lat - B.lat_hi)) <= TOL
            or min(abs(lon - B.lon_lo), abs(lon - B.lon_hi)) <= TOL)


def test_overhanging_polygon_is_clipped_not_clamped():
    ring = [_pt(0.25, 0.25), _pt(1.5, 0.25), _pt(1.5, 0.75), _pt(0.25, 0.75)]
    out = _shapes(2, ring)
    assert out, "the inside part of an overhanging polygon must be written"
    pts = [p for s in out for p in s.coords]
    boundary.assert_latlon_in_bounds(pts, B, tol=TOL)
    # clipped: the cut runs along the frame edge at the crossing, with the
    # inside corners kept where they were (a clamp would move them)
    assert sum(_on_edge(p) for p in pts) >= 2
    assert any(abs(p[0] - (B.lat_lo + 0.25 * DLAT)) <= TOL
               and abs(p[1] - (B.lon_lo + 0.25 * DLON)) <= TOL for p in pts)


def test_fully_outside_polygon_writes_nothing():
    ring = [_pt(1.25, 0.25), _pt(1.75, 0.25), _pt(1.75, 0.75), _pt(1.25, 0.75)]
    assert _shapes(2, ring) == []


def test_frame_covering_polygon_becomes_the_frame_rectangle():
    ring = [_pt(-1, -1), _pt(2, -1), _pt(2, 2), _pt(-1, 2)]
    out = _shapes(2, ring)
    pts = [p for s in out for p in s.coords]
    assert pts, "a covering polygon must keep the whole frame"
    boundary.assert_latlon_in_bounds(pts, B, tol=TOL)
    for lat in (B.lat_lo, B.lat_hi):
        for lon in (B.lon_lo, B.lon_hi):
            assert any(abs(p[0] - lat) <= TOL and abs(p[1] - lon) <= TOL for p in pts), (lat, lon)


def test_line_leaving_and_reentering_splits_without_a_bridge():
    line = [_pt(0.2, 0.5), _pt(1.5, 0.5), _pt(1.5, 0.7), _pt(0.2, 0.7)]
    out = _shapes(1, line)
    assert len(out) >= 2, "a line that leaves and re-enters is written as separate runs"
    boundary.assert_latlon_in_bounds([p for s in out for p in s.coords], B, tol=TOL)
