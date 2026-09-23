"""Per-vertex quantisation round-trip tool (plan 03, unit 3-04). Synthetic
cells, no disc; one tiny spool for the end-to-end path."""
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


def _cell(frames, bs, blk, lx, ly):
    """Global (ix, iy) of leaf (lx, ly) in block `blk` of block set `bs`."""
    bsy, bsx = divmod(bs, frames.nbs_lng)
    bly, blx = divmod(blk, frames.nbl_lng)
    ix = (bsx * frames.nbl_lng + blx) * frames.npc_lng + lx
    iy = (bsy * frames.nbl_lat + bly) * frames.npc_lat + ly
    return ix, iy


def _urban_and_sparse(frames):
    bs, blk, ty, tx = sorted(frames.urban)[0]
    urban = _cell(frames, bs, blk, tx * 4 + 1, ty * 4 + 2)
    # A tile of the same block that is not urban.
    for sty in range(8):
        for stx in range(8):
            if (bs, blk, sty, stx) not in frames.urban:
                return urban, _cell(frames, bs, blk, stx * 4 + 3, sty * 4 + 1)
    raise AssertionError("no sparse tile")


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
    _, _, lat_lo, lon_lo, lat_sp, lon_sp = fr
    lon = lon_lo + fx * lon_sp
    return lat_lo + fy * lat_sp, (lon + 180.0) % 360.0 - 180.0


def test_l0_urban_4096_and_sparse_16384_tile_frame():
    f = qr.Frames(0)
    (uix, uiy), (six, siy) = _urban_and_sparse(f)
    u, s = f.frame(uix, uiy), f.frame(six, siy)
    assert (u[0], u[1]) == ("urban", 4096)
    assert (s[0], s[1]) == ("sparse", 16384)
    assert s[4] == pytest.approx(4 * f.cell_lat) and s[5] == pytest.approx(4 * f.cell_lon)
    # The sparse frame is the tile: its origin is the tile anchor, not the leaf.
    assert s[3] < f.lon0 + six * f.cell_lon


def test_higher_level_full():
    f = qr.Frames(2)
    assert f.frame(10, 10)[:2] == ("full", 4096)


def test_inside_passes_outside_is_clamped_and_fails():
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    lat, lon = _inside(fr, 1.0, 1.0)  # exactly on the NE corner: raw 4096, legal
    assert qr.measure([lat], [lon], fr)[1:3] == (0, 0)
    step = fr[5] / fr[1]
    n, fail, clamp, over, _ = qr.measure([lat], [lon + 3 * step], fr)
    assert (n, fail, clamp) == (1, 1, 1)
    assert over == pytest.approx(3.0, abs=1e-6)


def test_run_cells_counts_every_kind_and_reports_clamps():
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    a, b = _inside(fr, 0.1, 0.2), _inside(fr, 0.9, 0.8)
    out_lat, out_lon = _inside(fr, 1.01, 0.5)  # ~41 raw units east of the frame
    content = {"roads": [_link([a, (out_lat, out_lon), b])],
               "backgrounds": [_bg([a, b, a])],
               "names": [_name(*a), _name(None, None)]}
    per, no_pos = qr.run_cells(2, [(10, 10, content_to_columns(content))], f)
    st = per["full"]
    assert no_pos == 1
    assert {k: v["vertices"] for k, v in st["per_kind"].items()} == {"n": 2, "p": 1, "c": 3, "s": 1}
    assert st["failing"] == 1 and st["clamped"] == 1
    assert st["per_kind"]["p"]["failing"] == 1
    assert st["worst_overshoot_raw"] == pytest.approx(0.01 * 4096, rel=1e-3)
    assert st["half_pixel_deg"]["lon"] == pytest.approx(fr[5] / (2 * 4096))


@pytest.mark.parametrize("writer", [SpoolWriter, spool_legacy.SpoolWriter],
                         ids=["binary", "legacy_pickle"])
def test_end_to_end_spool(tmp_path, writer):
    f = qr.Frames(2)
    fr = f.frame(10, 10)
    a, b = _inside(fr, 0.25, 0.5), _inside(fr, 0.75, 0.5)
    with writer(tmp_path / "spool") as w:
        w.add(2, 10, 10, roads=[_link([a, b])], backgrounds=[_bg([a, b])])
    out = tmp_path / "rt.json"
    assert qr.main(["--spool", str(tmp_path / "spool"), "--out", str(out), "--workers", "1"]) == 0
    res = json.loads(out.read_text())
    assert res["pass"] is True
    assert res["totals"]["vertices"] == 4
    assert list(res["levels"]) == ["2"]
    text = out.read_text()
    assert str(tmp_path) not in text
    qr.main(["--spool", str(tmp_path / "spool"), "--out", str(tmp_path / "rt2.json"),
             "--workers", "1"])
    assert (tmp_path / "rt2.json").read_text() == text
