"""Tests for the `spotcheck` harness check (`parser/harness/checks/spotcheck.py`):
against an in-test synthetic disc with one parcel containing a name record
"Queen Street", a fixture-table row expecting it PASSes and a row expecting
"Nowhere Road" FAILs. Mirrors `test_harness_core.py`'s synthetic-disc
pattern."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.model import NameRecord

sys.path.insert(0, str(Path(__file__).resolve().parent / "fixtures" / "harness"))
import e2_fixture  # noqa: E402  (fixture frames through E2, 3C-10)

from harness.checks.spotcheck import _run_spotcheck
from harness.context import Context

LEVEL = 0
# One real level-0 grid cell in Perth: E2 encodes the fixture's frame against
# the real grid, and the 1x1 fixture's coverage is that cell.
_IX, _IY = 1780, 814
_BOUNDS = e2_fixture.cell_bounds(LEVEL, _IX, _IY)
# Centre of the single 1x1 grid cell -- well inside its bounds either way.
_CENTRE_LAT = (_BOUNDS.lat_lo + _BOUNDS.lat_hi) / 2
_CENTRE_LON = (_BOUNDS.lon_lo + _BOUNDS.lon_hi) / 2


def _fixture_bytes_with_name(text: str) -> bytes:
    """A 1x1 ALLDATA.KWI whose one parcel holds one name record `text`. The
    frame comes from E2 (a fixture spool with that record); E2 emits only the
    string types the reference has at level 0, so the record is type 5, a
    road name (the legacy synthetic encoder emitted type 1)."""
    name_record = NameRecord(
        string_type=5, type_code=0x210, type_label="", priority=0, vertical=False,
        display_scale_flag=0, text=text, lat=_CENTRE_LAT, lon=_CENTRE_LON,
        angle_deg=0, angle_flags=0,
    )
    with tempfile.TemporaryDirectory() as d:
        return e2_fixture.alldata_bytes(d, LEVEL, {(_IX, _IY): {"names": [name_record]}})


def _build_fixture_bytes() -> bytes:
    return _fixture_bytes_with_name("Queen Street")


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


def _run_expecting(tmp_path, text, expected):
    p = tmp_path / "ALLDATA.KWI"
    p.write_bytes(_fixture_bytes_with_name(text))
    table = _write_table(tmp_path, [{
        "city": "T", "lat": _CENTRE_LAT, "lon": _CENTRE_LON, "levels": [0],
        "expect_road_names": [expected], "expect_place_names": [],
    }])
    return _run_spotcheck(_ctx(str(p), table))


def test_spotcheck_rejects_substring_false_positive(tmp_path):
    result = _run_expecting(tmp_path, "Pulteney Pokies", "Pulteney")
    assert result.status == "FAIL", result.message


def test_spotcheck_normalises_prefix_case_and_whitespace(tmp_path):
    result = _run_expecting(tmp_path, "1=GRENFELL  STREET", "Grenfell Street")
    assert result.status == "PASS", result.message


def test_spotcheck_matches_semicolon_segment(tmp_path):
    result = _run_expecting(tmp_path, "1=WILLIAM STREET;1=53", "William Street")
    assert result.status == "PASS", result.message
