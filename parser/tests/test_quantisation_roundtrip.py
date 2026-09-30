"""Quantisation round-trip tool (plan 03, units 3-04, 3-07, 3C-04).

The tool decodes a built `ALLDATA.KWI` and checks it against the spool, so
these tests build tiny real discs (`build_alldata.run`, level 0 only) from
synthetic spools (`kiwiw.spool.SpoolWriter`) and then check them against the
same spool or a deliberately mismatched one."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata  # noqa: E402
from kiwiw.model import BackgroundShape, NameRecord, RoadLink, RoadNode  # noqa: E402
from kiwiw.spool import SpoolWriter  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402

# Level-0 cell (512, 0) is lat -50..-49.97917, lon 106..106.03125.
CELL_LAT, CELL_LON = 1 / 48, 1 / 32
LAT0, LON0 = -49.99, 106.01
D = 0.002
RAW_LON = CELL_LON / 4096     # one raw unit of longitude at level 0


def _node(lat, lon):
    return RoadNode(x=0, y=0, lat=lat, lon=lon, oneway=0, planned=0, tunnel=False, bridge=False)


def _link(pts):
    nodes = [_node(*pts[0]), _node(*pts[-1])]
    return RoadLink(display_class=1, road_type=1, altitude_flag=False,
                    route_type_guidance_flag=False, pseudo3d_updown=0,
                    route_planning_tag=False, link_id_flag=False, selected_link_flag=False,
                    toll_flag=False, route_number_flag=False, infra_link_flag=False,
                    link_id_number_flag=False, n_nodes=2, nodes=nodes, points=list(pts))


def _square(lat0, lon0, d=D, dlon=None):
    e = d if dlon is None else dlon
    return [(lat0 - d, lon0 - e), (lat0 + d, lon0 - e), (lat0 + d, lon0 + e),
            (lat0 - d, lon0 + e), (lat0 - d, lon0 - e)]


def _bg(coords, type_code=1):
    return BackgroundShape(shape_class=2, type_code=type_code, type_label="x",
                           n_coords=len(coords), mult_const=1, underground=False,
                           pen_up=False, coords=coords)


def _name(lat, lon):
    # string_type 6 / type_code 0: other codes are dropped by the name encoder
    return NameRecord(string_type=6, type_code=0, type_label="", priority=0, vertical=False,
                      display_scale_flag=0, text="n", lat=lat, lon=lon)


def _centre(ix, iy):
    return -50 + (iy + 0.5) * CELL_LAT, 90 + (ix + 0.5) * CELL_LON


def _write_spool(path: Path, cells: dict) -> Path:
    with SpoolWriter(str(path)) as w:
        for (ix, iy), content in sorted(cells.items()):
            w.add(0, ix, iy, **content)
    return path


def _base_cells(bg=True, bg_shift_lon=0.0):
    a, m, b = (LAT0, LON0), (LAT0 + 0.0003, LON0 + 0.0001), (LAT0 + 0.0005, LON0 + 0.0005)
    bgs = [_bg(_square(LAT0, LON0 + bg_shift_lon))] if bg else []
    return {(512, 0): {"roads": [_link([a, m, b])], "backgrounds": bgs, "names": [_name(*a)]}}


def _big_cells(shift_lon=0.0):
    """A polygon 2.5 cells square homed in cell (514, 3), so it crosses cell
    edges (boundary vertices) and covers the centre cell (interior cover);
    every cell it touches is emitted through a name of its own."""
    clat, clon = _centre(514, 3)
    cells = {}
    for ix in range(513, 516):
        for iy in range(2, 5):
            cells[(ix, iy)] = {"roads": [], "backgrounds": [], "names": [_name(*_centre(ix, iy))]}
    cells[(514, 3)]["backgrounds"] = [_bg(_square(clat, clon + shift_lon, 1.25 * CELL_LAT,
                                                  1.25 * CELL_LON), type_code=2)]
    return cells


def _build(tmp_path: Path, name: str, cells: dict):
    spool = _write_spool(tmp_path / f"spool_{name}", cells)
    disc = tmp_path / name / "ALLDATA.KWI"
    rc = build_alldata.run(spool_dir=str(spool), out_path=str(disc), levels=[0],
                           fixture=None, disk_title="TEST")
    assert rc == 0
    return disc, spool


def _failing(res):
    return {k: v["failing"] for k, v in res["totals"].items() if v["failing"]}


# ------------------------------------------------------------------ geometry units

def test_point_set_is_chebyshev_within_half_unit():
    ps = qr.PointSet(np.array([10.4, 20.0]), np.array([5.2, 7.6]))
    d = ps.nearest(np.array([10, 20, 30]), np.array([5, 8, 0]))
    assert d[0] == pytest.approx(0.4) and d[1] == pytest.approx(0.4) and np.isinf(d[2])


def test_cheb_seg_distance():
    d = qr._cheb_seg(np.array([5.0, 0.0]), np.array([3.0, 0.0]),
                     np.array([0.0, 10.0]), np.array([0.0, 10.0]),
                     np.array([10.0, 20.0]), np.array([0.0, 10.0]))
    assert d[0] == pytest.approx(3.0)
    # diagonal segment (10,10)-(20,10)... distance from origin is 10
    assert d[1] == pytest.approx(10.0)


# ------------------------------------------------------------------ end to end

def test_passes_against_its_own_spool(tmp_path):
    cells = {**_base_cells(), **_big_cells()}
    disc, spool = _build(tmp_path, "full", cells)
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    assert res["pass"] is True, (_failing(res), res["levels"]["0"]["failures"])
    t = res["totals"]
    for kind in ("road_node", "name_anchor", "background", "background_boundary",
                 "completeness", "interior_cover", "range", "step"):
        assert t[kind]["checked"] > 0, kind
    text = json.dumps(res, sort_keys=True)
    assert str(tmp_path) not in text
    res2 = qr.roundtrip(str(disc), str(spool), workers=1)
    res.pop("wall_s")
    res2.pop("wall_s")
    assert res2 == res


def test_cli_exit_code_and_report(tmp_path):
    disc, spool = _build(tmp_path, "full", _base_cells())
    out = tmp_path / "rt.json"
    assert qr.main(["--disc", str(disc), "--spool", str(spool), "--out", str(out),
                    "--workers", "1"]) == 0
    assert json.loads(out.read_text())["pass"] is True
    _, other = _build(tmp_path, "nobg", _base_cells(bg=False))
    assert qr.main(["--disc", str(disc), "--spool", str(other), "--out", str(out),
                    "--workers", "1"]) == 1


def test_vertex_outside_every_source_polygon_is_caught(tmp_path):
    """Check a disc against a spool whose same-type polygon sits 8 raw units
    east: every decoded vertex is then outside every source polygon's
    half-unit neighbourhood."""
    disc, _ = _build(tmp_path, "full", _base_cells())
    _, moved = _build(tmp_path, "moved", _base_cells(bg_shift_lon=8 * RAW_LON))
    res = qr.roundtrip(str(disc), str(moved), workers=1)
    assert res["pass"] is False
    assert _failing(res) == {"background": res["totals"]["background"]["failing"]}
    fails = [f for f in res["levels"]["0"]["failures"] if f["kind"] == "background"]
    assert fails and all(f["error_raw"] is None or f["error_raw"] > 0.5 for f in fails)
    assert all(f["cell"] == [512, 0] for f in fails)


def test_boundary_vertex_outside_every_source_polygon_is_caught(tmp_path):
    """The large polygon moved 8 raw units east: boundary vertices on its
    west side then lie outside it, and interior vertices off its outline."""
    disc, _ = _build(tmp_path, "full", _big_cells())
    _, moved = _build(tmp_path, "moved", _big_cells(shift_lon=8 * RAW_LON))
    res = qr.roundtrip(str(disc), str(moved), workers=1)
    assert res["pass"] is False
    assert res["totals"]["background_boundary"]["failing"] > 0


def test_removed_piece_is_caught(tmp_path):
    """A disc built without the polygon, checked against the spool that has
    it: the (cell, type) has no decoded piece."""
    disc, _ = _build(tmp_path, "nobg", _base_cells(bg=False))
    _, spool = _build(tmp_path, "full", _base_cells())
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    assert res["pass"] is False
    assert _failing(res) == {"completeness": 1}
    (f,) = [f for f in res["levels"]["0"]["failures"] if f["kind"] == "completeness"]
    assert f["cell"] == [512, 0] and f["type"] == 1


def test_removed_cover_piece_is_caught(tmp_path):
    """Removing the large polygon loses its pieces in all nine cells."""
    cells = _big_cells()
    disc, _ = _build(tmp_path, "full", cells)
    stripped = {k: {**v, "backgrounds": []} for k, v in cells.items()}
    disc2, _ = _build(tmp_path, "stripped", stripped)
    _, spool = _build(tmp_path, "spool", cells)
    res = qr.roundtrip(str(disc2), str(spool), workers=1)
    assert _failing(res) == {"completeness": 9}


def test_moved_road_node_and_name_are_caught(tmp_path):
    disc, _ = _build(tmp_path, "full", _base_cells(bg=False))
    a, b = (LAT0, LON0 + 3 * RAW_LON), (LAT0 + 0.0005, LON0 + 0.0005)
    moved = {(512, 0): {"roads": [_link([a, b])], "backgrounds": [], "names": [_name(*a)]}}
    _, spool = _build(tmp_path, "moved", moved)
    res = qr.roundtrip(str(disc), str(spool), workers=1)
    assert _failing(res) == {"road_node": 1, "name_anchor": 1}
