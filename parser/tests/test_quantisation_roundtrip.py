"""Per-vertex quantisation round-trip tool (plan 03, units 3-04 and 3-07).
Synthetic cells, no disc; one tiny spool for the end-to-end path."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from kiwiw.model import BackgroundShape, NameRecord, RoadLink, RoadNode  # noqa: E402
from kiwiw import spool_legacy  # noqa: E402
from kiwiw.spool import SpoolWriter, content_to_columns  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402


def _node(lat, lon):
    return RoadNode(x=0, y=0, lat=lat, lon=lon, oneway=0, planned=0, tunnel=False, bridge=False)


def _link(pts):
    nodes = [_node(*pts[0]), _node(*pts[-1])]
    return RoadLink(display_class=1, road_type=1, altitude_flag=False,
                    route_type_guidance_flag=False, pseudo3d_updown=0,
                    route_planning_tag=False, link_id_flag=False, selected_link_flag=False,
                    toll_flag=False, route_number_flag=False, infra_link_flag=False,
                    link_id_number_flag=False, n_nodes=2, nodes=nodes, points=list(pts[1:-1]))


def _bg(coords):
    return BackgroundShape(shape_class=2, type_code=1, type_label="x", n_coords=len(coords),
                           mult_const=1, underground=False, pen_up=False, coords=coords)


def _name(lat, lon):
    return NameRecord(string_type=1, type_code=1, type_label="x", priority=0, vertical=False,
                      display_scale_flag=0, text="n", lat=lat, lon=lon)


def _inside(fr, fx, fy):
    """lat/lon at fractional frame position (fx, fy) in 0..1."""
    _, _, lat_lo, lon_lo, lat_sp, lon_sp = fr[:6]
    return lat_lo + fy * lat_sp, lon_lo + fx * lon_sp


def test_frames_are_the_frames_g_writes():
    """G writes every cell as its own 4096 frame, L0 included (no sparse tile)."""
    assert qr.Frames(0).frame(700, 300)[:2] == ("urban", 4096)
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    assert fr[:2] == ("full", 4096)
    assert fr[4] == pytest.approx(f.grid.cell_lat) and fr[5] == pytest.approx(f.grid.cell_lon)


def test_inside_passes_outside_is_clamped_and_fails():
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    lat, lon = _inside(fr, 1.0, 1.0)  # exactly on the NE corner: raw 4096, legal
    assert qr.measure([lat], [lon], fr)[:2] == (1, 0)
    step = fr[5] / fr[1]
    n, fail, err = qr.measure([lat], [lon + 3 * step], fr)
    assert (n, fail) == (1, 1)
    assert err == pytest.approx(3.0, abs=1e-6)


def test_overhanging_background_is_clipped_and_passes():
    """An overhanging polygon is measured as written: clipped, with crossing
    and corner vertices, none outside the frame, none failing."""
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    ring = [_inside(fr, x, y) for x, y in [(0.99, 0.99), (1.01, 0.99), (1.01, 1.02), (0.99, 1.02)]]
    content = {"roads": [], "backgrounds": [_bg(ring + ring[:1])], "names": []}
    per, _ = qr.run_cells(2, [(10, 10, content_to_columns(content))], f)
    st = per["full"]
    bg = st["background"]
    assert st["per_kind"]["c"]["failing"] == 0 and st["failing"] == 0
    assert bg["input_vertices"] == 5 and bg["records"] == 1
    assert bg["outside_rect"] == bg["crossing_off_edge"] == bg["step_overflow"] == 0
    assert bg["written_by_provenance"]["crossing"] == 3  # 2 + the closing repeat
    assert bg["written_by_provenance"]["corner"] == 1
    assert st["worst_error_raw"] <= 0.5


def test_background_outside_writes_nothing():
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    ring = [_inside(fr, x, y) for x, y in [(1.1, 0.2), (1.3, 0.2), (1.3, 0.4)]]
    content = {"roads": [], "backgrounds": [_bg(ring)], "names": []}
    per, _ = qr.run_cells(2, [(10, 10, content_to_columns(content))], f)
    bg = per["full"]["background"]
    assert per["full"]["per_kind"]["c"]["vertices"] == 0
    assert bg["shapes"] == bg["shapes_dropped"] == 1 and bg["records"] == 0


def test_run_cells_counts_every_kind_and_fails_clamped_roads():
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    a, b = _inside(fr, 0.1, 0.2), _inside(fr, 0.9, 0.8)
    out_lat, out_lon = _inside(fr, 1.01, 0.5)  # ~41 raw units east of the frame
    content = {"roads": [_link([a, (out_lat, out_lon), b])],
               "backgrounds": [_bg([a, _inside(fr, 0.12, 0.2), _inside(fr, 0.12, 0.22), a])],
               "names": [_name(*a), _name(None, None)]}
    per, no_pos = qr.run_cells(2, [(10, 10, content_to_columns(content))], f)
    st = per["full"]
    assert no_pos == 1
    assert {k: v["vertices"] for k, v in st["per_kind"].items()} == {"n": 2, "p": 1, "c": 4, "s": 1}
    assert st["failing"] == 1
    assert st["per_kind"]["p"]["failing"] == 1
    assert st["worst_error_raw"] == pytest.approx(0.01 * 4096, rel=1e-3)
    assert st["half_pixel_deg"]["lon"] == pytest.approx(fr[5] / (2 * 4096))


@pytest.mark.parametrize("writer", [SpoolWriter, spool_legacy.SpoolWriter],
                         ids=["binary", "legacy_pickle"])
def test_end_to_end_spool(tmp_path, writer):
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    a, b, c = _inside(fr, 0.25, 0.5), _inside(fr, 0.27, 0.5), _inside(fr, 0.26, 0.52)
    with writer(tmp_path / "spool") as w:
        w.add(2, 10, 10, roads=[_link([a, b])], backgrounds=[_bg([a, b, c, a])])
    out = tmp_path / "rt.json"
    assert qr.main(["--spool", str(tmp_path / "spool"), "--out", str(out), "--workers", "1"]) == 0
    res = json.loads(out.read_text())
    assert res["pass"] is True
    assert res["totals"]["vertices"] == 6
    assert list(res["levels"]) == ["2"]
    text = out.read_text()
    assert str(tmp_path) not in text
    qr.main(["--spool", str(tmp_path / "spool"), "--out", str(tmp_path / "rt2.json"),
             "--workers", "1"])
    assert (tmp_path / "rt2.json").read_text() == text
