"""Tests for the comparison harness core (`parser/harness/`):

- `decode`/`pointers`/`shape` against a small synthetic `ALLDATA.KWI` built
  in-test with `kiwiw.alldata_writer.build_alldata_kwi` (tests may import
  encoders; the harness package itself must not -- see
  `test_no_forbidden_imports`).
- `decode` PASS, `shape` FAIL against that single-level flat fixture (an
  expected negative control: it does not match the reference LMR shape
  until unit 12's all-levels assembler lands).
- `pointers` FAIL after corrupting one mfde offset in a copy.
- a static grep-based guard that `parser/harness/` never imports any
  content-generation / assembler / OSM-extraction module.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import pytest

# Make ``kiwiw``/``harness`` importable without installing.
_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from kiwiw import volume as _volume
from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi
from kiwiw.bitutils import sws, u16, u32
from kiwiw.model import BoundingBox, MeshLocation, RoadLink, RoadNode
from kiwiw.parcel import decode_parcel
from kiwiw.synth import build_map_frame_bytes, build_road_frame_bytes

from harness.checks import decode as decode_checks
from harness.checks import shape as shape_checks
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


def _make_link(bounds: BoundingBox) -> RoadLink:
    from kiwiw.coordconv import COORD_RANGE, xy_to_latlon

    n_nodes = 2
    step = int(COORD_RANGE) // (n_nodes + 1)
    nodes = []
    for k in range(n_nodes):
        xc = step * (k + 1)
        yc = step * (k + 1)
        lat, lon = xy_to_latlon(xc, yc, bounds)
        nodes.append(RoadNode(x=xc, y=yc, lat=lat, lon=lon,
                               oneway=0, planned=0, tunnel=False, bridge=False))
    return RoadLink(
        display_class=0, road_type=0, altitude_flag=False,
        route_type_guidance_flag=False, pseudo3d_updown=0, route_planning_tag=False,
        link_id_flag=False, selected_link_flag=False, toll_flag=False,
        route_number_flag=False, infra_link_flag=False, link_id_number_flag=False,
        n_nodes=n_nodes, nodes=nodes, points=[(n.lat, n.lon) for n in nodes],
        raw_offset=0, raw_bytes=b"",
    )


def _build_fixture_bytes() -> bytes:
    """A tiny 2x2, single-level (0) ALLDATA.KWI: one road link per parcel."""
    synth_parcels = []
    for iy in range(NY):
        for ix in range(NX):
            bounds = _cell_bounds(ix, iy)
            links = [_make_link(bounds)]
            road_bytes = build_road_frame_bytes(links, bounds)
            frame_bytes = build_map_frame_bytes(road_bytes, None, None, bounds)
            synth_parcels.append(SynthParcel(ix=ix, iy=iy, bounds=bounds,
                                              map_frame_bytes=frame_bytes))
    return build_alldata_kwi(parcels=synth_parcels, coverage=_BOUNDS, level=LEVEL,
                              grid_nx=NX, grid_ny=NY)


@pytest.fixture()
def fixture_path(tmp_path):
    p = tmp_path / "ALLDATA.KWI"
    p.write_bytes(_build_fixture_bytes())
    return str(p)


def _ctx(generated_path: str) -> Context:
    return Context(reference=None, generated=generated_path,
                   config={"layers_present": ["map"]})


# ---------------------------------------------------------------------
# decode
# ---------------------------------------------------------------------

def test_decode_passes_on_synthetic_fixture(fixture_path):
    ctx = _ctx(fixture_path)
    result = decode_checks._run_decode(ctx)
    assert result.status == "PASS", result.message
    # 4 parcels (2x2 grid), each with one leaf.
    assert result.details["per_level_parcel_counts"].get(LEVEL) == NX * NY


# ---------------------------------------------------------------------
# shape: single-level flat fixture does not match the reference LMR/BSMR/
# BMT shape -- an expected negative control until unit 12's all-levels
# assembler lands (see this module's docstring and the brief for unit 02).
# ---------------------------------------------------------------------

def test_shape_fails_on_synthetic_fixture(fixture_path):
    ctx = _ctx(fixture_path)
    result = shape_checks._run_shape(ctx)
    assert result.status == "FAIL", "single-level flat fixture is expected to fail shape"
    assert result.details["diffs"]


# ---------------------------------------------------------------------
# pointers: corrupt one mfde offset in a copy -> FAIL
# ---------------------------------------------------------------------

def _find_first_leaf_mfde_offset(buf: bytearray) -> int:
    """Locate the byte offset of mfde entry 0's [D]-offset field (a u32) in
    the first leaf Map Frame this fixture places, by re-parsing the same
    structures the harness itself reads."""
    hdr = _volume.parse_volume_header(bytes(buf[:_volume.DATAVOL_SIZE]))
    mht = _volume.parse_management_header_table(
        bytes(buf[_volume.DATAVOL_SIZE:_volume.DATAVOL_SIZE + _volume.MHT_SIZE]))
    prdm = mht.entries[0]
    pdmdh_off = _volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
    raw_pdmdh = bytes(buf[pdmdh_off:pdmdh_off + prdm.size * hdr.logical_sector_size])
    pdmdh = _volume.parse_pdmdh_full(raw_pdmdh)
    table = pdmdh.bmt_tables[0]
    first_entry = next(e for e in table.entries if e.dsa != 0xFFFFFFFF and e.size)
    block_off = _volume.getsector(first_entry.dsa, hdr.sector_size, hdr.logical_sector_size)
    block_len = first_entry.size * hdr.logical_sector_size
    block_buf = bytes(buf[block_off:block_off + block_len])
    # Root Parcel Management Record: [type word(2)][gap(2)][mapinfo entries]
    mapinfo_off = 4
    leaf_dsa = u32(block_buf, mapinfo_off)
    leaf_size = u16(block_buf, mapinfo_off + 4)
    assert leaf_size, "expected the first mapinfo slot to be a real leaf"
    leaf_off = _volume.getsector(leaf_dsa, hdr.sector_size, hdr.logical_sector_size)
    # Map Frame header is 36 bytes, nregion at offset 34; mfde table starts
    # right after the region list.
    nregion = u16(bytes(buf[leaf_off:leaf_off + 36]), 34)
    de_off = leaf_off + 36 + nregion * 4
    return de_off  # offset of mfde entry 0's raw u32 [D] offset field


def test_pointers_fails_on_corrupted_mfde_offset(fixture_path):
    ctx = _ctx(fixture_path)
    baseline = decode_checks._run_pointers(ctx)
    assert baseline.status == "PASS", baseline.message

    buf = bytearray(Path(fixture_path).read_bytes())
    off = _find_first_leaf_mfde_offset(buf)
    # Corrupt mfde entry 0's [D] offset to something wildly out of range
    # (not the 0xFFFFFFFF sentinel, not in-buffer, not a valid in-file
    # sector either).
    buf[off:off + 4] = (0x7FFFFFF0).to_bytes(4, "big")

    corrupted_path = str(Path(fixture_path).with_name("ALLDATA_corrupt.KWI"))
    Path(corrupted_path).write_bytes(bytes(buf))

    ctx2 = _ctx(corrupted_path)
    result = decode_checks._run_pointers(ctx2)
    assert result.status == "FAIL", "corrupted mfde offset should fail the pointers check"


# ---------------------------------------------------------------------
# Forbidden imports guard
# ---------------------------------------------------------------------

FORBIDDEN_PATTERNS = [
    re.compile(r"\bsynth\b"),
    re.compile(r"alldata_writer"),
    re.compile(r"_writer\b"),
    re.compile(r"osm_to_"),
]


def test_no_forbidden_imports():
    harness_dir = _PARSER_DIR / "harness"
    offenders = []
    for py_file in harness_dir.rglob("*.py"):
        text = py_file.read_text()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{py_file}: matched {pattern.pattern!r}")
    assert not offenders, "\n".join(offenders)
