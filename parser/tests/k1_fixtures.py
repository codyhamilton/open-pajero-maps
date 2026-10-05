"""Shared K1 fixtures (plan 04, Phase 2, brief 2-03; reused by 2-04 and 2-05).

Tiny level-0 discs built by `build_alldata.run` from synthetic spools
(`kiwiw.spool.SpoolWriter`), the way `test_quantisation_roundtrip.py` does (its
`_base_cells` / `_big_cells` / `_build` helpers are copied here, not imported, so
that file stays untouched), plus the injected-fault builders and the K1 driver
(`plan_bands`, `k1_run`) the K1 tests share.

`FIXTURES` maps a name to `(disc_cells, spool_cells)`: the disc is built from the
first, checked against the spool built from the second. Faults:

- `vertex_moved`      the spool's polygon sits 8 raw units east of the disc's
                      (every decoded vertex is outside every source polygon)
- `piece_removed`     the disc has no polygon, the spool has one
- `name_node_moved`   a road node and a name anchor moved 1 raw unit
- `many_failures`     more than K1_SAMPLE names and road nodes moved far away
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_alldata  # noqa: E402
from harness import walk  # noqa: E402
from harness.checks.coord_scale import _block_keys  # noqa: E402
from kiwiw import cenc  # noqa: E402
from kiwiw.model import BackgroundShape, NameRecord, RoadLink, RoadNode  # noqa: E402
from kiwiw.spool import SpoolReader, SpoolWriter  # noqa: E402
from tools import quantisation_roundtrip as qr  # noqa: E402

# Level-0 cell (512, 0) is lat -50..-49.97917, lon 106..106.03125.
CELL_LAT, CELL_LON = 1 / 48, 1 / 32
LAT0, LON0 = -49.99, 106.01
D = 0.002
RAW_LON = CELL_LON / 4096     # one raw unit of longitude at level 0
POINT_KINDS = ("range", "step", "road_node", "road_point", "name_anchor")
EXPLAINED = qr.EXPLAINED


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


# ------------------------------------------------------------------ fault builders

def _many(shift_lat=0.0, shift_lon=0.0, n=14):
    """`n` short roads and `n` names in cell (512, 0), optionally moved."""
    roads, names = [], []
    for i in range(n):
        lat, lon = LAT0 + 0.0001 * i + shift_lat, LON0 + 0.0002 * i + shift_lon
        roads.append(_link([(lat, lon), (lat + 0.0002, lon + 0.0001)]))
        names.append(_name(lat + 0.0001, lon))
    return {(512, 0): {"roads": roads, "backgrounds": [], "names": names}}


def vertex_moved():
    return _base_cells(), _base_cells(bg_shift_lon=8 * RAW_LON)


def piece_removed():
    return _base_cells(bg=False), _base_cells()


def name_node_moved():
    a, b = (LAT0, LON0 + 1 * RAW_LON), (LAT0 + 0.0005, LON0 + 0.0005)
    moved = {(512, 0): {"roads": [_link([a, b])], "backgrounds": [], "names": [_name(*a)]}}
    return _base_cells(bg=False), moved


def many_failures():
    return _many(), _many(shift_lat=0.0004, shift_lon=0.0004)


def _dense(n=7000, pts=6, names=300):
    """One cell holding enough road geometry to exceed the Map Frame byte ceiling, so
    E2 divides it: sub-cell leaves, retiled roads (road_*_subcell_on_polyline,
    road_*_on_leaf_edge) and halo names. Roads are long diagonals with interior points."""
    roads, nm = [], []
    for i in range(n):
        f = (i % 70) / 70.0
        g = (i // 70) / (n / 70.0)
        lat = -49.9999 + f * CELL_LAT * 0.9
        lon = 106.0005 + g * CELL_LON * 0.9
        line = [(lat + 0.00002 * k * ((i % 3) - 1) + 0.00001 * k, lon + 0.00003 * k) for k in range(pts)]
        roads.append(_link(line))
    for i in range(names):
        nm.append(_name(-49.9999 + (i % 20) * CELL_LAT * 0.045, 106.0005 + (i // 20) * CELL_LON * 0.06))
    return {(512, 0): {"roads": roads, "backgrounds": [], "names": nm}}


def dense():
    return _dense(), _dense()


def dense_moved():
    return _dense(), {(512, 0): {**_dense()[(512, 0)], "names": []}}


FIXTURES = {
    "clean": lambda: ({**_base_cells(), **_big_cells()}, {**_base_cells(), **_big_cells()}),
    "vertex_moved": vertex_moved,
    "piece_removed": piece_removed,
    "name_node_moved": name_node_moved,
    "many_failures": many_failures,
    "dense": dense,
    "dense_moved": dense_moved,
}
FAULTS = tuple(k for k in FIXTURES if k != "clean")


def build_fixture(tmp_path: Path, name: str):
    """(disc path, spool path) of fixture `name` (`FIXTURES` or `BG_FIXTURES`)."""
    disc_cells, spool_cells = {**FIXTURES, **BG_FIXTURES, **CMP_FIXTURES}[name]()
    disc, _ = _build(tmp_path, f"{name}_d", disc_cells)
    _, spool = _build(tmp_path, f"{name}_s", spool_cells)
    return disc, spool


# ------------------------------------------------------------------ background fixtures (2-04)
# Kept apart from FIXTURES: test_k1_points.py parametrises over FIXTURES and expects a
# point-kind failure from every fault in it. The background kinds read the same
# (disc_cells, spool_cells) pairs.
#
#   bg_coarse            a 12-vertex ring 0.9 cell wide (coarse steps in the disc)
#   bg_tall              a polygon 4.5 cells wide homed in one cell: its bbox leaves the home
#                        cell grown by one cell, so it is found only by the tall pass
#   bg_long_edge         an unclosed triangle 2.5 cells across: the closing edge is long
#                        and carries disc vertices that are near no spool vertex (65623)
#   bg_diamond           a diamond whose left/right vertices sit exactly on a cell row line
#                        (the point-in-polygon half-open edge rule decides its covers)
#   bg_boundary_displaced  the spool polygon 8 raw east of the disc's (boundary vertices fail)
#   bg_cover_displaced   the spool polygon 2 cells east (the cover centre is outside it)
#   bg_tall_displaced    the tall polygon moved 8 raw
#   bg_outside           one disc vertex 30 raw outside the spool polygon
#   bg_wrong_type        the disc polygon has type 1, the spool's type 2
#   bg_shift_04 / _06    the spool polygon 0.4 / 0.6 raw east (the half-unit tolerance)


def _poly_cells(coords, home, ixs, iys, type_code=2, shapes=None):
    """Spool/disc cells: a name in every cell of `ixs` x `iys` (so each is emitted) and
    the polygon `coords` in cell `home`."""
    cells = {(ix, iy): {"roads": [], "backgrounds": [], "names": [_name(*_centre(ix, iy))]}
             for ix in ixs for iy in iys}
    cells[home]["backgrounds"] = shapes if shapes is not None else [_bg(coords, type_code)]
    return cells


def _ring(clat, clon, n, ry, rx):
    """A closed n-gon around (clat, clon), `ry` / `rx` in degrees."""
    import math
    pts = [(clat + ry * math.sin(2 * math.pi * k / n), clon + rx * math.cos(2 * math.pi * k / n))
           for k in range(n)]
    return pts + [pts[0]]


def _coarse(shift_lon=0.0):
    lat, lon = _centre(512, 0)
    return _poly_cells(_ring(lat, lon + shift_lon, 12, 0.45 * CELL_LAT, 0.45 * CELL_LON),
                       (512, 0), [512], [0])


def _tall(shift_lon=0.0, type_code=2):
    clat, clon = _centre(514, 3)
    return _poly_cells(_square(clat, clon + shift_lon, 2.25 * CELL_LAT, 2.25 * CELL_LON),
                       (514, 3), range(512, 517), range(1, 6), type_code)


def _long_edge(shift_lon=0.0):
    clat, clon = _centre(514, 3)
    a = (clat - 1.2 * CELL_LAT, clon + shift_lon - 1.2 * CELL_LON)
    b = (clat - 1.2 * CELL_LAT, clon + shift_lon + 1.3 * CELL_LON)
    c = (clat + 1.3 * CELL_LAT, clon + shift_lon + 1.3 * CELL_LON + 0.0001)
    return _poly_cells([a, b, c], (514, 3), range(513, 517), range(1, 6))


def _diamond(shift_lon=0.0):
    """A diamond astride the level's bottom edge (raw row 0 is exactly latitude -50.0, the
    one row that is exactly representable) with its left/right tips ON that row. The disc
    side is clipped at the row, so its base vertices are boundary vertices at Y == 0 that lie
    far from every spool vertex and segment: the verdict comes from `inside()`, where the
    tips make the half-open edge rule decide (each tip has one edge ending, one starting)."""
    assert float(qr.Lattice(0).gy(-50.0)) == 0.0
    clon = 90 + 513 * CELL_LON + shift_lon
    r = 1.2
    pts = [(-50.0, clon - r * CELL_LON), (-50.0 + r * CELL_LAT, clon), (-50.0, clon + r * CELL_LON),
           (-50.0 - r * CELL_LAT, clon), (-50.0, clon - r * CELL_LON)]
    return _poly_cells(pts, (513, 0), range(511, 515), range(0, 2))


def _outside_vertex():
    sq = _square(LAT0, LON0)
    moved = list(sq)
    moved[1] = (sq[1][0] + 30 * CELL_LAT / 4096, sq[1][1])
    moved[-1] = moved[0]
    return ({(512, 0): {"roads": [], "backgrounds": [_bg(moved)], "names": [_name(LAT0, LON0)]}},
            {(512, 0): {"roads": [], "backgrounds": [_bg(sq)], "names": [_name(LAT0, LON0)]}})


def _wrong_type():
    sq = _square(LAT0, LON0)
    return ({(512, 0): {"roads": [], "backgrounds": [_bg(sq, 1)], "names": [_name(LAT0, LON0)]}},
            {(512, 0): {"roads": [], "backgrounds": [_bg(sq, 2)], "names": [_name(LAT0, LON0)]}})


def _shift(raw):
    return ({**_base_cells(), **_big_cells()},
            {**_base_cells(bg_shift_lon=raw * RAW_LON), **_big_cells(shift_lon=raw * RAW_LON)})


BG_FIXTURES = {
    "bg_coarse": lambda: (_coarse(), _coarse()),
    "bg_tall": lambda: (_tall(), _tall()),
    "bg_long_edge": lambda: (_long_edge(), _long_edge()),
    "bg_diamond": lambda: (_diamond(), _diamond()),
    "bg_boundary_displaced": lambda: (_big_cells(), _big_cells(shift_lon=8 * RAW_LON)),
    "bg_cover_displaced": lambda: (_big_cells(), _big_cells(shift_lon=2 * CELL_LON)),
    "bg_tall_displaced": lambda: (_tall(), _tall(shift_lon=8 * RAW_LON)),
    "bg_outside": _outside_vertex,
    "bg_wrong_type": _wrong_type,
    "bg_shift_04": lambda: _shift(0.4),
    "bg_shift_06": lambda: _shift(0.6),
    "bg_many_failures": lambda: (_tall(), _tall(shift_lon=40 * RAW_LON)),
}


# ------------------------------------------------------------------ completeness fixtures (2-05)
#
#   cmp_tall_removed     the tall polygon is in the spool only: its interior meets cells that
#                        hold no vertex of it (the cell-centre rule), every one is missing
#   cmp_cover_removed    the 2.5-cell polygon is in the spool only: the centre cell is wholly
#                        covered (a cell with no vertex), the ring cells hold vertices
#   cmp_tall_small       the disc keeps only a one-cell polygon of the spool's tall one
#   cmp_sliver_removed   a spool polygon about a third of a raw unit wide: rounds to zero area,
#                        so it is not required (negative case) next to a removed real one
#   cmp_other_type       two spool polygon types over the same cells, the disc has one of them


def _two_types(drop_type=None):
    clat, clon = _centre(514, 3)
    shapes = [_bg(_square(clat, clon, 1.25 * CELL_LAT, 1.25 * CELL_LON), t) for t in (1, 2)
              if t != drop_type]
    return _poly_cells(None, (514, 3), range(513, 516), range(2, 5), shapes=shapes)


def _sliver():
    d = 0.3 * CELL_LAT / 4096
    lat, lon = _centre(512, 0)       # away from the cell centre, which a polygon holds by TOL
    lat, lon = lat - 600 * CELL_LAT / 4096, lon - 600 * RAW_LON
    return [(lat, lon), (lat + d, lon), (lat, lon + d), (lat, lon)]


def _sliver_cells(with_sliver=True, with_square=True):
    lat, lon = _centre(512, 0)
    shapes = []
    if with_sliver:
        shapes.append(_bg(_sliver(), 1))
    if with_square:
        shapes.append(_bg(_square(lat + 0.0005, lon + 0.0005, 0.0003), 2))
    return _poly_cells(None, (512, 0), [512], [0], shapes=shapes)


def _tall_removed(disc_poly=False):
    clat, clon = _centre(514, 3)
    spool = _tall()
    shapes = [_bg(_square(clat, clon, 0.4 * CELL_LAT, 0.4 * CELL_LON), 2)] if disc_poly else []
    return _poly_cells(None, (514, 3), range(512, 517), range(1, 6), shapes=shapes), spool


def _cover_removed():
    disc = _big_cells()
    disc[(514, 3)]["backgrounds"] = []
    return disc, _big_cells()


CMP_FIXTURES = {
    "cmp_tall_removed": lambda: _tall_removed(False),
    "cmp_cover_removed": _cover_removed,
    "cmp_tall_small": lambda: _tall_removed(True),
    "cmp_sliver_removed": lambda: (_sliver_cells(False, False), _sliver_cells(True, True)),
    "cmp_other_type": lambda: (_two_types(drop_type=2), _two_types()),
}


# ------------------------------------------------------------------ the K1 driver

def plan_bands(disc, spool, mode: str = "tasks"):
    """`[(key, rlo, rhi)]` band plans over every block of `disc`: `whole` (one
    band per block), `tasks` (the Python tool's own `_block_tasks`, workers=1),
    `rows` (one band per cell row of each block), `rows_rev` (the same, reversed)."""
    container = walk.read_container(str(disc))
    keys = _block_keys(str(disc))
    lats = {lv: qr.Lattice(lv) for lv in {k[0] for k in keys}}
    reader = SpoolReader(str(spool))
    if mode == "whole":
        out = []
        for k in keys:
            _c0, _c1, r0, r1 = qr.key_cells(container, k, lats[k[0]])
            out.append((k, r0, r1))
        return out
    if mode == "tasks":
        return qr._block_tasks(reader, container, keys, lats, 1)
    rows = []
    for k in keys:
        _c0, _c1, r0, r1 = qr.key_cells(container, k, lats[k[0]])
        rows += [(k, r, r) for r in range(r0, r1 + 1)]
    return rows[::-1] if mode == "rows_rev" else rows


def k1_run(disc, spool, plan, acc=None):
    """Run K1 over `plan` (`plan_bands` output) against `disc` / `spool`;
    returns `(K1Acc, calls)` with `calls` the number of K1 band calls made."""
    container = walk.read_container(str(disc))
    region = np.memmap(str(disc), dtype=np.uint8, mode="r")
    cache: dict = {}
    spools: dict = {}
    acc = acc if acc is not None else cenc.K1Acc()
    before = cenc.k1_stats()["calls"]
    for key, rlo, rhi in plan:
        row = cenc.d1_block_rows([key], container, cache)[0:1]
        if key[0] not in spools:
            spools[key[0]] = cenc.E1Spool(str(spool), key[0])
        cenc.k1_check_band(region, row, rlo, rhi, spools[key[0]], acc)
    return acc, cenc.k1_stats()["calls"] - before


# ------------------------------------------------------------------ inside-side tolerance (3-04)
#
# `background_boundary` can not observe the inside interval tolerance: a boundary
# vertex within K1_TOL of a same-type outline is already `near` (NEAR = K1_TOL +
# K1_EPS) and passes before `inside_batch` runs, and one beyond it is outside every
# interval by more than K1_TOL, so both `+ K1_TOL` and `- K1_TOL` are equivalent
# there. The tolerance is observable only for a leaf-filling `interior_cover`, whose
# centre `inside_batch` tests without the near gate. `bg_inside_out_03` pins both
# comparisons: a full-cell disc ring in two cells against a cell-sized C-shaped spool
# ring whose narrow mouth reaches past the centre, leaving that centre 0.3 raw to the
# left of one mouth wall (in cell 512) and 0.3 raw to the right of the other (cell
# 513); either `K1_TOL` term decides its interval. `bg_inside_out_07` repeats the
# first geometry at 0.7 raw (outside every interval) and shifts the outer ring 0.7
# raw east, so the left frame vertices are 0.7 raw outside too: the cover fails and
# 35 frame vertices fail (the vertices the encoder shares into the eight edge cells).

_RAW_LAT = CELL_LAT / 4096


def _cell_rect(clat, clon):
    return _square(clat, clon, 0.5 * CELL_LAT, 0.5 * CELL_LON)


def _cshaped_ring(clat, clon, d_lo, d_hi, outer=0.0):
    """A cell-sized ring with a mouth from the top edge past the centre: the mouth
    walls sit `d_lo` / `d_hi` raw from the centre, the outer rectangle `outer` raw east."""
    lat0, lat1 = clat - 0.5 * CELL_LAT, clat + 0.5 * CELL_LAT
    lon0 = clon + outer * RAW_LON - 0.5 * CELL_LON
    lon1 = clon + outer * RAW_LON + 0.5 * CELL_LON
    mlo, mhi = clon + d_lo * RAW_LON, clon + d_hi * RAW_LON
    mb = clat - 5 * _RAW_LAT
    return [(lat0, lon0), (lat0, lon1), (lat1, lon1), (lat1, mhi),
            (mb, mhi), (mb, mlo), (lat1, mlo), (lat1, lon0), (lat0, lon0)]


def _cover_cells(ixs, spool=None):
    """A full-cell disc ring in each cell of `ixs`; `spool` maps a cell to its
    `(d_lo, d_hi, outer)` ring. With no `spool`, the disc rings are the spool."""
    disc = {}
    for ix in ixs:
        clat, clon = _centre(ix, 0)
        disc[(ix, 0)] = {"roads": [], "backgrounds": [_bg(_cell_rect(clat, clon), 2)],
                         "names": [_name(clat, clon)]}
    if spool is None:
        return disc, disc
    s = {}
    for ix, (d_lo, d_hi, outer) in spool.items():
        clat, clon = _centre(ix, 0)
        s[(ix, 0)] = {"roads": [],
                      "backgrounds": [_bg(_cshaped_ring(clat, clon, d_lo, d_hi, outer), 2)],
                      "names": [_name(clat, clon)]}
    return disc, s


def bg_inside_out_03():
    return _cover_cells([512, 513], {512: (-5.0, 0.3, 0.0), 513: (-0.3, 5.0, 0.0)})


def bg_inside_out_07():
    return _cover_cells([512], {512: (-5.0, 0.7, 0.7)})


# Kept out of `BG_FIXTURES`: those parametrise the shared tests (point kinds among
# them) and their vacuity check wants a non-boundary `background` vertex, which a
# leaf-filling cover has none of. The inside fixtures get their own tests.
INSIDE_FIXTURES = {
    "bg_inside_out_03": bg_inside_out_03,
    "bg_inside_out_07": bg_inside_out_07,
}


def build_inside_fixture(tmp_path: Path, name: str):
    """(disc path, spool path) of an `INSIDE_FIXTURES` fixture."""
    disc_cells, spool_cells = INSIDE_FIXTURES[name]()
    disc, _ = _build(tmp_path, f"{name}_d", disc_cells)
    _, spool = _build(tmp_path, f"{name}_s", spool_cells)
    return disc, spool


# Plan 14 3-03: absent G against demanders at the representability boundary.
# Raw points are cell-local; conversion exercises the spool and both tall paths.
REPRESENTABLE_CASES = {
    "endpoint_lobes": ([(2000, 2000), (2100, 2000), (2100, 2100), (2000, 2100),
                         (2000, 2000), (2000, 1900), (1900, 1900), (1900, 2000)], 1, True),
    "twice_square": ([(1800, 1800), (2300, 1800), (2300, 2300), (1800, 2300)] * 2, 1, False),
    "twice_crossing": ([(1000, 1000), (2500, 2000), (1000, 2000), (2300, 1000)] * 2, 1, False),
    "tol_vertical": ([(2048.3, -500), (2048.3, 9000), (2048.3, -500)], 1, False),
    "vertex_poke": ([(-50, 1000), (1.2, 1000.02), (-50, 1000.04)], 1, False),
    "square": ([(512, 512), (1024, 512), (1024, 1024), (512, 1024)], 1, True),
    "surviving_sliver": ([(-50, 1000), (2.4, 1000), (2.4, 1100), (-50, 1100)], 1, True),
    "bowtie": ([(1024, 1024), (3072, 3072), (1024, 3072), (1024.2, 1024)], 1, True),
    # Attribution row 656, translated by whole cells: vertex rounding has
    # nonzero area, but densification adds a spike that collapses the ring.
    "densify_collapse": ([(6991823.608217601 - 1706 * 4096, 6197222.001868799 - 1512 * 4096),
                           (6991818.234265599 - 1706 * 4096, 6197109.699379199 - 1512 * 4096),
                           (6991812.912742399 - 1706 * 4096, 6196998.733823999 - 1512 * 4096)],
                          1, False),
    "densify_mult2": ([(6991823.608217601 - 1706 * 4096, 6197222.001868799 - 1512 * 4096),
                        (6991818.234265599 - 1706 * 4096, 6197109.699379199 - 1512 * 4096),
                        (6991812.912742399 - 1706 * 4096, 6196998.733823999 - 1512 * 4096)],
                       2, True),
}


def build_representable_fixture(tmp_path, name, tall_home=False, second_square=False):
    pts, mc, _ = REPRESENTABLE_CASES[name]
    coords = [(-50 + y * CELL_LAT / 4096, 90 + (512 * 4096 + x) * RAW_LON)
              for x, y in pts]
    shape = _bg(coords + [coords[0]], 288)
    shape.mult_const = mc
    target = {"roads": [], "backgrounds": [], "names": [_name(*_centre(512, 0))]}
    disc, _ = _build(tmp_path, f"{name}_absent", {(512, 0): target})
    home = (512, 5) if tall_home else (512, 0)
    cells = {(512, 0): target, home: {**target, "backgrounds": [shape]}}
    if second_square:
        lat, lon = _centre(512, 0)
        cells[home]["backgrounds"].append(_bg(_square(lat, lon, 0.001), 288))
    return disc, _write_spool(tmp_path / f"{name}_demand", cells)
