"""Tests for the `spotcheck` harness check (`parser/harness/checks/spotcheck.py`):
against an in-test synthetic disc with one parcel containing a name record
"Queen Street", a fixture-table row expecting it PASSes and a row expecting
"Nowhere Road" FAILs. Mirrors `test_harness_core.py`'s synthetic-disc
pattern."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi
from kiwiw.model import BoundingBox, NameRecord
from kiwiw.synth import build_map_frame_bytes, build_name_frame_bytes

from harness.checks.spotcheck import _run_spotcheck
from harness.context import Context

_BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)
LEVEL = 0
# Centre of the single 1x1 grid cell -- well inside its bounds either way.
_CENTRE_LAT = (_BOUNDS.lat_lo + _BOUNDS.lat_hi) / 2
_CENTRE_LON = (_BOUNDS.lon_lo + _BOUNDS.lon_hi) / 2


def _build_fixture_bytes() -> bytes:
    name_record = NameRecord(
        string_type=1, type_code=0, type_label="", priority=0, vertical=False,
        display_scale_flag=0, text="Queen Street",
        lat=_CENTRE_LAT, lon=_CENTRE_LON,
    )
    name_bytes = build_name_frame_bytes([name_record], _BOUNDS)
    frame_bytes = build_map_frame_bytes(None, None, name_bytes, _BOUNDS)
    parcel = SynthParcel(ix=0, iy=0, bounds=_BOUNDS, map_frame_bytes=frame_bytes)
    return build_alldata_kwi(parcels=[parcel], coverage=_BOUNDS, level=LEVEL,
                              grid_nx=1, grid_ny=1)


def _write_table(tmp_path, rows) -> str:
    p = tmp_path / "spot_checks.json"
    p.write_text(json.dumps(rows))
    return str(p)


def _ctx(generated_path: str, table_path: str) -> Context:
    return Context(reference=None, generated=generated_path,
                   config={"layers_present": ["map"], "spot_checks": table_path})


def test_spotcheck_passes_when_expected_name_present(tmp_path):
    alldata_path = tmp_path / "ALLDATA.KWI"
    alldata_path.write_bytes(_build_fixture_bytes())
    table_path = _write_table(tmp_path, [{
        "city": "Test City", "lat": _CENTRE_LAT, "lon": _CENTRE_LON,
        "levels": [0], "expect_road_names": ["Queen Street"],
        "expect_place_names": [],
    }])

    ctx = _ctx(str(alldata_path), table_path)
    result = _run_spotcheck(ctx)
    assert result.status == "PASS", result.message
    assert result.details["rows"][0]["matched"] == ["Queen Street"]


def test_spotcheck_fails_when_expected_name_missing(tmp_path):
    alldata_path = tmp_path / "ALLDATA.KWI"
    alldata_path.write_bytes(_build_fixture_bytes())
    table_path = _write_table(tmp_path, [{
        "city": "Test City", "lat": _CENTRE_LAT, "lon": _CENTRE_LON,
        "levels": [0], "expect_road_names": ["Nowhere Road"],
        "expect_place_names": [],
    }])

    ctx = _ctx(str(alldata_path), table_path)
    result = _run_spotcheck(ctx)
    assert result.status == "FAIL", result.message
    assert result.details["rows"][0]["missing"] == ["Nowhere Road"]


def test_spotcheck_na_when_table_absent(tmp_path):
    alldata_path = tmp_path / "ALLDATA.KWI"
    alldata_path.write_bytes(_build_fixture_bytes())
    ctx = _ctx(str(alldata_path), str(tmp_path / "does_not_exist.json"))
    result = _run_spotcheck(ctx)
    assert result.status == "NA"
