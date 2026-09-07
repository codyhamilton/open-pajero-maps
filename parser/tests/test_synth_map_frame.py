"""Tests for `kiwiw.synth.build_map_frame_bytes` -- the synthetic Map
Frame shape per `docs/plans/01-eval-harness-and-map-layer/DESIGN.md`
sections 2-4 (header fields, region list, mfde table).

Covers, for each level in ``12 10 8 6 4 2 0``:
  - mfde table length matches `DESIGN.md` section 4 (12 at level 12, 20
    elsewhere).
  - `nregion` and the header's Header-Size/dsflag/rg_addr/rg_size fields
    decode to the WP1-emission values `DESIGN.md` section 2/3 specifies.
  - per-index presence: indices 0-2 reflect whether road/background/name
    content was supplied; every other index is the absent sentinel
    `(0xFFFFFFFF, 0)`.
  - `ext_frames={4: b"..."}` produces an in-buffer entry at index 4 that
    round-trips through `decode_parcel()`'s `ext_frame_raw`.
  - determinism: two builds from identical inputs are byte-equal.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.bitutils import sws
from kiwiw.model import BoundingBox, MeshLocation, RoadLink, RoadNode
from kiwiw.parcel import decode_parcel
from kiwiw.synth import (
    build_background_frame_bytes,
    build_map_frame_bytes,
    build_name_frame_bytes,
    build_road_frame_bytes,
    mfde_table_len,
)

_BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)
_LLPID = (_BOUNDS.lat_lo, _BOUNDS.lon_lo)
_LLCODE = (3, 7)
_LEVELS = [12, 10, 8, 6, 4, 2, 0]
_ABSENT = (0xFFFFFFFF, 0)


def _fixture_road_bytes() -> bytes:
    node = RoadNode(x=100, y=200, lat=_BOUNDS.lat_lo, lon=_BOUNDS.lon_lo,
                     oneway=0, planned=0, tunnel=False, bridge=False)
    link = RoadLink(
        display_class=0, road_type=0, altitude_flag=False,
        route_type_guidance_flag=False, pseudo3d_updown=0, route_planning_tag=False,
        link_id_flag=False, selected_link_flag=False, toll_flag=False,
        route_number_flag=False, infra_link_flag=False, link_id_number_flag=False,
        n_nodes=1, nodes=[node], points=[(node.lat, node.lon)],
        raw_offset=0, raw_bytes=b"",
    )
    return build_road_frame_bytes([link], _BOUNDS)


def _fixture_bg_bytes() -> bytes:
    return build_background_frame_bytes([], _BOUNDS)   # always generated (DESIGN.md idx 1)


def _fixture_name_bytes() -> bytes:
    from kiwiw.model import NameRecord
    rec = NameRecord(
        string_type=1, type_code=0, type_label="", priority=0, vertical=False,
        display_scale_flag=0, text="Test St",
        lat=_BOUNDS.lat_lo, lon=_BOUNDS.lon_lo,
    )
    return build_name_frame_bytes([rec], _BOUNDS)


def _decode(frame_bytes: bytes):
    loc = MeshLocation(level=0, parcel_type=0, blockset_index=0, block_index=0,
                        parcel_index=0, bounds=_BOUNDS, sector_addr=0,
                        size_logical_sectors=1)
    return decode_parcel(loc, frame_bytes, n_basic_map=3, n_ext_map=0)


@pytest.mark.parametrize("level", _LEVELS)
def test_mfde_table_shape_per_level(level):
    road_bytes = _fixture_road_bytes()
    bg_bytes = _fixture_bg_bytes()
    name_bytes = _fixture_name_bytes()

    frame_bytes = build_map_frame_bytes(
        level, _LLPID, _LLCODE, road_bytes, bg_bytes, name_bytes)
    parcel = _decode(frame_bytes)

    expected_len = mfde_table_len(level)
    assert expected_len == (12 if level == 12 else 20)
    assert len(parcel.frame.mfde_raw) == expected_len

    # nregion: WP1 emits 0 (no region-list bytes) at every level (DESIGN.md
    # section 3).
    assert parcel.frame.header.nregion == 0
    assert parcel.frame.region_list_raw == b""

    # Indices 0-2: road/background/name all supplied -> in_buffer.
    for idx in (0, 1, 2):
        raw_off, raw_size = parcel.frame.mfde_raw[idx]
        assert raw_off != 0xFFFFFFFF and raw_size != 0, (
            f"level {level} index {idx}: expected in_buffer, got absent")

    # Every remaining index (3..expected_len-1) is absent -- WP1 does not
    # populate ext frames or the 12-19 group by default.
    for idx in range(3, expected_len):
        assert parcel.frame.mfde_raw[idx] == _ABSENT, (
            f"level {level} index {idx}: expected absent {_ABSENT}, "
            f"got {parcel.frame.mfde_raw[idx]}")

    # Road/background/name content round-trips byte-identically.
    assert parcel.road is not None and len(parcel.road.links) == 1
    assert parcel.background is not None
    assert parcel.name is not None and len(parcel.name.records) == 1


@pytest.mark.parametrize("level", _LEVELS)
def test_absent_slot_sentinel_when_no_content(level):
    """A parcel with no road/name content still has the profile-confirmed
    absent sentinel (never zero-fill) at indices 0 and 2."""
    bg_bytes = _fixture_bg_bytes()
    frame_bytes = build_map_frame_bytes(
        level, _LLPID, _LLCODE, None, bg_bytes, None)
    parcel = _decode(frame_bytes)

    assert parcel.frame.mfde_raw[0] == _ABSENT   # road absent
    assert parcel.frame.mfde_raw[1] != _ABSENT   # background always present
    assert parcel.frame.mfde_raw[2] == _ABSENT   # name absent
    assert parcel.road is None
    assert parcel.background is not None
    assert parcel.name is None


def test_header_fields_per_design():
    road_bytes = _fixture_road_bytes()
    bg_bytes = _fixture_bg_bytes()
    frame_bytes = build_map_frame_bytes(
        0, _LLPID, _LLCODE, road_bytes, bg_bytes, None)

    # Header Size (SWS, offset 0) matches the buffer's total size.
    assert sws(frame_bytes[0] << 8 | frame_bytes[1]) == len(frame_bytes)

    # dsflag (offset 18-19) = 0x0064 per DESIGN.md's WP1 emission.
    assert frame_bytes[18:20] == b"\x00\x64"

    # rg_addr (offset 28-31) absent = 0xFFFFFFFF; rg_size (32-33) = 0.
    assert frame_bytes[28:32] == b"\xff\xff\xff\xff"
    assert frame_bytes[32:34] == b"\x00\x00"

    # llpid/llcode decode back through the established decoder.
    parcel = _decode(frame_bytes)
    header = parcel.frame.header
    assert header.llpid_lat == pytest.approx(_LLPID[0], abs=1e-4)
    assert header.llpid_lon == pytest.approx(_LLPID[1], abs=1e-4)
    assert header.llcode_cx == _LLCODE[0]
    assert header.llcode_cy == _LLCODE[1]


def test_ext_frames_in_buffer_entry_round_trips():
    road_bytes = _fixture_road_bytes()
    bg_bytes = _fixture_bg_bytes()
    ext_payload = b"hello ext frame!"   # odd length -> exercises even-padding too

    frame_bytes = build_map_frame_bytes(
        0, _LLPID, _LLCODE, road_bytes, bg_bytes, None,
        ext_frames={4: ext_payload})
    parcel = _decode(frame_bytes)

    raw_off, raw_size = parcel.frame.mfde_raw[4]
    assert raw_off != 0xFFFFFFFF and raw_size != 0, "index 4 must be in_buffer"
    assert 4 in parcel.frame.ext_frame_raw
    padded = ext_payload + b"\x00" if len(ext_payload) % 2 else ext_payload
    assert parcel.frame.ext_frame_raw[4] == padded

    # Every other index besides 0/1/4 remains absent.
    for idx in range(2, 20):
        if idx == 4:
            continue
        assert parcel.frame.mfde_raw[idx] == _ABSENT, f"index {idx} should be absent"


def test_ext_frames_out_of_range_index_rejected():
    road_bytes = _fixture_road_bytes()
    bg_bytes = _fixture_bg_bytes()
    with pytest.raises(ValueError):
        build_map_frame_bytes(
            12, _LLPID, _LLCODE, road_bytes, bg_bytes, None,
            ext_frames={15: b"xx"})   # level 12's table only has indices 0-11


def test_determinism():
    road_bytes = _fixture_road_bytes()
    bg_bytes = _fixture_bg_bytes()
    name_bytes = _fixture_name_bytes()

    a = build_map_frame_bytes(0, _LLPID, _LLCODE, road_bytes, bg_bytes, name_bytes)
    b = build_map_frame_bytes(0, _LLPID, _LLCODE, road_bytes, bg_bytes, name_bytes)
    assert a == b

    c = build_map_frame_bytes(
        0, _LLPID, _LLCODE, road_bytes, bg_bytes, name_bytes,
        ext_frames={4: b"stable payload"})
    d = build_map_frame_bytes(
        0, _LLPID, _LLCODE, road_bytes, bg_bytes, name_bytes,
        ext_frames={4: b"stable payload"})
    assert c == d
