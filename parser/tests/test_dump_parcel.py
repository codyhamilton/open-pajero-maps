"""`to_jsonable` on a `Parcel` carrying non-empty `bytes` fields (`raw_bytes`
on a `RoadLink`, `ext_frame_raw` on a `MapFrame`) must produce
`json.dumps`-able output with those fields as lowercase hex strings -- the
2026-09-02 IR additions regression fixed by unit 05 (see
`docs/plans/01-eval-harness-and-map-layer/PLAN.md` "Why This Plan Exists"
gap (7))."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from kiwiw.model import (
    BoundingBox,
    MapFrame,
    MapFrameHeader,
    MeshLocation,
    Parcel,
    RoadFrame,
    RoadLink,
    to_jsonable,
)


def _make_parcel() -> Parcel:
    bounds = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)
    location = MeshLocation(
        level=0, parcel_type=0, blockset_index=0, block_index=0, parcel_index=0,
        bounds=bounds, sector_addr=0, size_logical_sectors=1,
    )
    link = RoadLink(
        display_class=0, road_type=0, altitude_flag=False,
        route_type_guidance_flag=False, pseudo3d_updown=0, route_planning_tag=False,
        link_id_flag=False, selected_link_flag=False, toll_flag=False,
        route_number_flag=False, infra_link_flag=False, link_id_number_flag=False,
        n_nodes=0, nodes=[], points=[],
        raw_offset=0, raw_bytes=b"\xde\xad\xbe\xef",
    )
    road = RoadFrame(
        n_intersections=0, n_display_classes=0, n_additional_data=0,
        route_planning_level=0, links=[link],
    )
    frame = MapFrame(
        header=MapFrameHeader(raw_bytes=b"\x00" * 36),
        ext_frame_raw={3: b"\x01\x02\x03"},
    )
    return Parcel(location=location, road=road, frame=frame)


def test_to_jsonable_hexifies_bytes_fields():
    parcel = _make_parcel()
    out = to_jsonable(parcel)
    dumped = json.dumps(out)  # must not raise
    redecoded = json.loads(dumped)

    assert redecoded["road"]["links"][0]["raw_bytes"] == "deadbeef"
    assert redecoded["frame"]["header"]["raw_bytes"] == "00" * 36
    assert redecoded["frame"]["ext_frame_raw"]["3"] == "010203"
