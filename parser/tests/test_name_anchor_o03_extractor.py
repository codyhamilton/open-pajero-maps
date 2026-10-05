"""Synthetic PBF proof for plan 18: an out-of-span place node (O03) is not
admitted to the level-0 spool, while an in-span control name still lands in
exactly one cell.

Mirrors the osmium.SimpleWriter pattern in test_extractor_scale.py. The AU
reference L0 grid (``TileGrid.from_reference(0)``) has ``lon_lo=90``; the O03
source name sits at lon 77.51903576666666 (Ile Saint-Paul), west of coverage.
Before the plan-18 fix ``assign_to_parcel`` clamped it into edge cell (0,541).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.spool import SpoolReader, SpoolWriter
from osm_to_parcel_geometry import (
    TileGrid,
    _default_level_filter,
    assign_to_parcel,
    extract_parcel_geometry,
)

O03_LAT = -38.727284749
O03_LON = 77.51903576666666
O03_NAME = "Ile Saint-Paul O03"

CONTROL_LAT = -27.0
CONTROL_LON = 133.0
CONTROL_NAME = "Control Inland Town"


def _build_pbf(path: str) -> None:
    import osmium
    from osmium.osm.mutable import Node

    writer = osmium.SimpleWriter(path)
    try:
        writer.add_node(Node(
            id=1, location=(O03_LON, O03_LAT),
            tags={"place": "suburb", "name": O03_NAME},
        ))
        writer.add_node(Node(
            id=2, location=(CONTROL_LON, CONTROL_LAT),
            tags={"place": "suburb", "name": CONTROL_NAME},
        ))
    finally:
        writer.close()


@pytest.fixture(scope="module")
def pbf_path(tmp_path_factory):
    d = tmp_path_factory.mktemp("name_anchor_o03")
    p = d / "o03.osm.pbf"
    _build_pbf(str(p))
    return str(p)


def test_control_assigns_in_span():
    grid = TileGrid.from_reference(0)
    assert grid.disc_lon_lo == pytest.approx(90.0)
    assert assign_to_parcel(O03_LAT, O03_LON, grid) is None
    control = assign_to_parcel(CONTROL_LAT, CONTROL_LON, grid)
    assert control is not None


def test_out_of_span_name_not_spooled(pbf_path, tmp_path):
    grid = TileGrid.from_reference(0)
    control_cell = assign_to_parcel(CONTROL_LAT, CONTROL_LON, grid)
    assert control_cell is not None

    spool_dir = tmp_path / "spool"
    extract_parcel_geometry(
        pbf_path, {0: grid}, SpoolWriter(spool_dir, flush_threshold=1),
        verbose=False, level_filter=_default_level_filter,
    )
    reader = SpoolReader(spool_dir)

    by_cell = {}
    for ix, iy, content in reader.iter_level(0):
        by_cell[(ix, iy)] = content

    names = [(ix, iy, rec) for (ix, iy), c in by_cell.items()
             for rec in c["names"]]

    # out-of-span name is absent from every cell, including edge (0, 541)
    assert all(rec.text != O03_NAME for _ix, _iy, rec in names)
    assert all((0, 541) != (ix, iy) or not c["names"]
               for (ix, iy), c in by_cell.items())
    # no record at all carries the O03 source coordinate
    for _ix, _iy, rec in names:
        assert not (abs(rec.lat - O03_LAT) < 1e-6 and abs(rec.lon - O03_LON) < 1e-6)

    # control name present exactly once, in its in-span cell
    control = [(ix, iy, rec) for ix, iy, rec in names if rec.text == CONTROL_NAME]
    assert len(control) == 1
    cix, ciy, crec = control[0]
    assert (cix, ciy) == control_cell
    assert crec.lat == pytest.approx(CONTROL_LAT)
    assert crec.lon == pytest.approx(CONTROL_LON)
