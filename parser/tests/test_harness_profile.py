"""Tests for the reference profile (`parser/harness/profile.py`) and the
profile-based checks (`vocab`/`envelope`/`mfde`) it feeds -- unit 03 of
`docs/plans/01-eval-harness-and-map-layer/`.

All fixtures are synthetic, built in-test with
`kiwiw.alldata_writer.build_alldata_kwi` (per this unit's brief, "Tests"
section); judging the profile/checks against the real reference disc is
unit 03b's job, not this unit's.

- `test_build_profile_structure`: build a tiny profile from a synthetic
  disc and assert its shape (per-level road/background/name/mfde/nregion
  census, byte totals, source/commit metadata).
- `test_vocab_fails_on_unlisted_display_class`: hand-build a reference
  profile (by mutating a real census) that lacks a display class the
  generated disc actually has; assert FAIL with that value in `details`.
- `test_envelope_exempts_level0_link_count`: a reference profile whose
  level-0 link count is wildly different from the generated disc's; assert
  PASS (exempt) with the ratio still reported.
- `test_mfde_fails_on_entry_count_mismatch`: a reference profile claiming a
  20-entry mfde table when the generated disc's parcels have 3; assert FAIL.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi
from kiwiw.model import BackgroundShape, BoundingBox, NameRecord, RoadLink, RoadNode
from kiwiw.synth import (
    build_background_frame_bytes,
    build_map_frame_bytes,
    build_name_frame_bytes,
    build_road_frame_bytes,
)

from harness import profile as profile_mod
from harness.checks import envelope as envelope_checks
from harness.checks import mfde as mfde_checks
from harness.checks import vocab as vocab_checks
from harness.context import Context

_BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)
NX, NY = 2, 2
LEVEL = 0


def _cell_bounds(ix: int, iy: int) -> BoundingBox:
    cell_lat = (_BOUNDS.lat_hi - _BOUNDS.lat_lo) / NY
    cell_lon = (_BOUNDS.lon_hi - _BOUNDS.lon_lo) / NX
    return BoundingBox(
        lat_lo=_BOUNDS.lat_lo + iy * cell_lat,
        lat_hi=_BOUNDS.lat_lo + (iy + 1) * cell_lat,
        lon_lo=_BOUNDS.lon_lo + ix * cell_lon,
        lon_hi=_BOUNDS.lon_lo + (ix + 1) * cell_lon,
    )


def _make_link(bounds: BoundingBox, display_class: int = 0, road_type: int = 0) -> RoadLink:
    from kiwiw.coordconv import COORD_RANGE, xy_to_latlon

    n_nodes = 2
    step = int(COORD_RANGE) // (n_nodes + 1)
    nodes = []
    for k in range(n_nodes):
        xc = step * (k + 1)
        yc = step * (k + 1)
        lat, lon = xy_to_latlon(xc, yc, bounds)
        nodes.append(RoadNode(x=xc, y=yc, lat=lat, lon=lon,
                               oneway=k % 2, planned=0, tunnel=False, bridge=False))
    return RoadLink(
        display_class=display_class, road_type=road_type, altitude_flag=False,
        route_type_guidance_flag=False, pseudo3d_updown=0, route_planning_tag=False,
        link_id_flag=False, selected_link_flag=False, toll_flag=True,
        route_number_flag=False, infra_link_flag=False, link_id_number_flag=False,
        n_nodes=n_nodes, nodes=nodes, points=[(n.lat, n.lon) for n in nodes],
        raw_offset=0, raw_bytes=b"",
    )


def _make_background_shape(type_code: int = 5) -> BackgroundShape:
    # shape_class=0 (point): no coords needed, simplest encodable shape.
    return BackgroundShape(shape_class=0, type_code=type_code, type_label="",
                            n_coords=0, mult_const=1, underground=False, pen_up=False,
                            coords=[])


def _make_name_record(bounds: BoundingBox, text: str = "TEST ST") -> NameRecord:
    return NameRecord(
        string_type=1, type_code=3, type_label="", priority=2, vertical=False,
        display_scale_flag=0, text=text,
        lat=(bounds.lat_lo + bounds.lat_hi) / 2, lon=(bounds.lon_lo + bounds.lon_hi) / 2,
    )


def _build_fixture_bytes(display_classes=None) -> bytes:
    """A 2x2, single-level (0) ALLDATA.KWI: one road link + one background
    shape + one name record per parcel. `display_classes` (length NX*NY, in
    (iy, ix) nested-loop order) lets a test vary the road link's display
    class per parcel; defaults to all-zero."""
    if display_classes is None:
        display_classes = [0] * (NX * NY)
    synth_parcels = []
    idx = 0
    for iy in range(NY):
        for ix in range(NX):
            bounds = _cell_bounds(ix, iy)
            link = _make_link(bounds, display_class=display_classes[idx])
            idx += 1
            road_bytes = build_road_frame_bytes([link], bounds)
            bg_bytes = build_background_frame_bytes([_make_background_shape()], bounds)
            name_bytes = build_name_frame_bytes([_make_name_record(bounds)], bounds)
            frame_bytes = build_map_frame_bytes(road_bytes, bg_bytes, name_bytes, bounds)
            synth_parcels.append(SynthParcel(ix=ix, iy=iy, bounds=bounds,
                                              map_frame_bytes=frame_bytes))
    return build_alldata_kwi(parcels=synth_parcels, coverage=_BOUNDS, level=LEVEL,
                              grid_nx=NX, grid_ny=NY)


def _write_fixture(tmp_path, display_classes=None) -> str:
    p = tmp_path / "ALLDATA.KWI"
    p.write_bytes(_build_fixture_bytes(display_classes))
    return str(p)


def _ctx(generated_path: str, config: dict | None = None) -> Context:
    return Context(reference=None, generated=generated_path,
                   config=config or {"layers_present": ["map"]})


# ---------------------------------------------------------------------
# build_profile: structure
# ---------------------------------------------------------------------

def test_build_profile_structure(tmp_path):
    path = _write_fixture(tmp_path)
    profile = profile_mod.build_profile(path)

    assert "source" in profile and profile["source"]["disk_title"]
    assert "profiled_at_commit" in profile  # str (git present) or None
    assert profile["mfde"]["absent"] == [0xFFFFFFFF, 0]  # no absent slots in this fixture -> fallback

    assert "0" in profile["levels"]
    lvl0 = profile["levels"]["0"]

    n_parcels = NX * NY
    assert sum(lvl0["parcel_count_by_type"].values()) == n_parcels
    assert lvl0["block_count"] >= 1
    assert lvl0["occupied_block_count"] >= 1

    assert lvl0["mapframe_size"]["max"] > 0
    assert lvl0["mapframe_size"]["byte_total"] > 0

    assert lvl0["road"]["link_count"] == n_parcels
    assert lvl0["road"]["node_count"] == n_parcels * 2
    assert lvl0["road"]["road_type_hist"] == {"0": n_parcels}
    assert lvl0["road"]["display_class_hist"] == {"0": n_parcels}
    assert lvl0["road"]["link_flag_hists"]["toll_flag"] == {"True": n_parcels}
    assert set(lvl0["road"]["link_flag_hists"]["oneway"].keys()) == {"0", "1"}

    assert lvl0["background"]["shape_count"] == n_parcels
    assert lvl0["background"]["type_code_hist"] == {"5": n_parcels}
    assert lvl0["background"]["shape_class_hist"] == {"0": n_parcels}

    assert lvl0["name"]["record_count"] == n_parcels
    assert lvl0["name"]["string_type_hist"] == {"1": n_parcels}
    assert lvl0["name"]["max_text_length"] == len("TEST ST")

    assert lvl0["mfde"]["entry_count_hist"] == {"3": n_parcels}
    assert lvl0["nregion_hist"] == {"0": n_parcels}

    assert profile["byte_totals_by_layer"]["map"]["total_bytes"] > 0


# ---------------------------------------------------------------------
# vocab: FAIL on a display class not in the (hand-built) reference profile
# ---------------------------------------------------------------------

def test_vocab_fails_on_unlisted_display_class(tmp_path):
    # Parcel 3 (of 4) gets an "unlisted" display class (9); others stay 0.
    path = _write_fixture(tmp_path, display_classes=[0, 0, 0, 9])
    g_profile = profile_mod.build_profile(path)
    assert "9" in g_profile["levels"]["0"]["road"]["display_class_hist"]

    ref_profile = copy.deepcopy(g_profile)
    del ref_profile["levels"]["0"]["road"]["display_class_hist"]["9"]

    ctx = _ctx(path)
    ctx._profile_cache["map"] = ref_profile

    result = vocab_checks._run_vocab(ctx)
    assert result.status == "FAIL", result.message
    assert "9" in result.details["offenders"]["0"]["display_class"]


# ---------------------------------------------------------------------
# envelope: level-0 link count is exempt from the count envelope
# ---------------------------------------------------------------------

def test_envelope_exempts_level0_link_count(tmp_path):
    path = _write_fixture(tmp_path)
    g_profile = profile_mod.build_profile(path)

    ref_profile = copy.deepcopy(g_profile)
    real_link_count = ref_profile["levels"]["0"]["road"]["link_count"]
    ref_profile["levels"]["0"]["road"]["link_count"] = real_link_count * 1000  # far outside 0.5x-2x

    ctx = _ctx(path, config={
        "layers_present": ["map"],
        "envelopes": {"count_ratio": [0.5, 2.0]},
        "level0_count_exempt": True,
    })
    ctx._profile_cache["map"] = ref_profile

    result = envelope_checks._run_envelope(ctx)
    assert result.status == "PASS", result.message
    link_detail = result.details["counts"]["0"]["link_count"]
    assert link_detail["exempt"] is True
    assert "ratio" in link_detail


# ---------------------------------------------------------------------
# mfde: FAIL when the profile's entry count doesn't match G's
# ---------------------------------------------------------------------

def test_mfde_fails_on_entry_count_mismatch(tmp_path):
    path = _write_fixture(tmp_path)
    g_profile = profile_mod.build_profile(path)
    assert g_profile["levels"]["0"]["mfde"]["entry_count_hist"] == {"3": NX * NY}

    ref_profile = copy.deepcopy(g_profile)
    ref_profile["levels"]["0"]["mfde"]["entry_count_hist"] = {"20": NX * NY}

    ctx = _ctx(path)
    ctx._profile_cache["map"] = ref_profile

    result = mfde_checks._run_mfde(ctx)
    assert result.status == "FAIL", result.message
    assert any("3" in f and "20" in f for f in result.details["failures"])
