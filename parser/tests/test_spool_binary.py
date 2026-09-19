"""Binary columnar spool (plan 02 phase 2): lossless vs the legacy pickle spool."""
from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from kiwiw import spool as new
from kiwiw import spool_legacy as old
from kiwiw.model import BackgroundShape, NameRecord, RoadLink, RoadNode

import convert_spool


def _road(i, way=None):
    nodes = [RoadNode(x=i + k, y=2 * k, lat=-31.5 + k * 1e-5, lon=115.5 + i * 1e-5,
                      oneway=k % 3, planned=k % 2, tunnel=bool(k & 1), bridge=bool(k & 2))
             for k in range(3 + i % 3)]
    return RoadLink(display_class=i % 5, road_type=i % 7, altitude_flag=bool(i & 1),
                    route_type_guidance_flag=bool(i & 2), pseudo3d_updown=i % 3,
                    route_planning_tag=bool(i & 4), link_id_flag=bool(i & 1),
                    selected_link_flag=bool(i & 2), toll_flag=bool(i & 4),
                    route_number_flag=bool(i & 1), infra_link_flag=bool(i & 2),
                    link_id_number_flag=bool(i & 4), n_nodes=len(nodes), nodes=nodes,
                    points=[(-31.0 - k * .001, 115.0 + k * .002) for k in range(i % 4)],
                    link_id=100 + i, osm_way_id=way, ordinal=i)


def _bg(i):
    return BackgroundShape(shape_class=i % 3, type_code=i, type_label=f"lab{i}é",
                           n_coords=4, mult_const=i % 2, underground=bool(i & 1),
                           pen_up=bool(i & 2),
                           coords=[(-31 + k * .01, 115 + k * .01) for k in range(4)])


def _name(i):
    return NameRecord(string_type=i % 4, type_code=i, type_label="x" * (i % 5),
                      priority=i % 9, vertical=bool(i & 1), display_scale_flag=i % 3,
                      text=f"Street {i} ünï", lat=None if i % 3 == 0 else -31.1,
                      lon=None if i % 4 == 0 else 115.2,
                      angle_deg=None if i % 2 else 45.5, angle_flags=i % 4)


def _same(a, b):
    for cls_a, cls_b in zip(a, b):
        assert type(cls_a) is type(cls_b)
        for f in fields(cls_a):
            if f.name in ("raw_bytes", "raw_offset"):
                continue
            assert getattr(cls_a, f.name) == getattr(cls_b, f.name), f.name


def _fill(w):
    for i in range(12):
        ix, iy = (i * 7) % 5, (i * 3) % 4
        w.add(2, ix, iy, roads=[_road(i, way=None if i % 2 else 10 ** 12 + i)],
              backgrounds=[_bg(i)] if i % 2 else None, names=[_name(i)])
    w.add(0, 1, 1)  # empty add is a no-op
    w.add(2, 0, 0, roads=[_road(99)])  # repeated key merges


def test_roundtrip_matches_legacy(tmp_path):
    for flush in (1, 10 ** 9):
        o = old.SpoolWriter(tmp_path / f"o{flush}", flush_threshold=flush)
        n = new.SpoolWriter(tmp_path / f"n{flush}", flush_threshold=flush)
        _fill(o), _fill(n)
        o.close(), n.close()
        ro, rn = old.SpoolReader(tmp_path / f"o{flush}"), new.SpoolReader(tmp_path / f"n{flush}")
        assert rn.levels() == ro.levels() == [2]
        assert rn.stats(2) == ro.stats(2)
        assert rn.stats(7) == {"parcels": 0, "roads": 0, "backgrounds": 0, "names": 0}
        lo, ln = list(ro.iter_level(2)), list(rn.iter_level(2))
        assert [(a, b) for a, b, _ in ln] == [(a, b) for a, b, _ in lo]
        for (_, _, co), (_, _, cn) in zip(lo, ln):
            for k in ("roads", "backgrounds", "names"):
                assert len(co[k]) == len(cn[k])
                _same(co[k], cn[k])
        assert not list((tmp_path / f"n{flush}").glob("*.seg"))


def test_iter_cells_range_and_determinism(tmp_path):
    for d in ("a", "b"):
        w = new.SpoolWriter(tmp_path / d, flush_threshold=3)
        _fill(w)
        w.close()
    assert (tmp_path / "a/level_2.data").read_bytes() == (tmp_path / "b/level_2.data").read_bytes()
    r = new.SpoolReader(tmp_path / "a")
    allc = list(r.iter_level(2))
    assert [(a, b) for a, b, _ in r.iter_cells(2, 2, 5)] == [(a, b) for a, b, _ in allc[2:5]]
    assert r.cell_keys(2) == [(a, b) for a, b, _ in allc]


def test_converter(tmp_path):
    o = old.SpoolWriter(tmp_path / "old")
    _fill(o)
    o.close()
    convert_spool.convert(str(tmp_path / "old"), str(tmp_path / "bin"), verbose=False)
    a, b = old.SpoolReader(tmp_path / "old"), new.SpoolReader(tmp_path / "bin")
    for (_, _, ca), (_, _, cb) in zip(a.iter_level(2), b.iter_level(2)):
        for k in ("roads", "backgrounds", "names"):
            _same(ca[k], cb[k])
