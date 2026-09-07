"""Tests for the `container` byte-diff check (`parser/harness/checks/container.py`,
`parser/harness/bytediff.py`): reference-independent, built entirely from two
synthetic `ALLDATA.KWI` buffers assembled in-test with
`kiwiw.alldata_writer.build_alldata_kwi` -- no mounted reference disc needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PARSER_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARSER_DIR))

from kiwiw import volume as _volume
from kiwiw.alldata_writer import SynthParcel, build_alldata_kwi
from kiwiw.model import BoundingBox

from harness.checks import container as container_checks
from harness.context import Context

_BOUNDS = BoundingBox(lat_lo=-32.0, lat_hi=-31.5, lon_lo=115.75, lon_hi=116.25)
_OTHER_BOUNDS = BoundingBox(lat_lo=-33.0, lat_hi=-30.0, lon_lo=115.0, lon_hi=117.0)
NX, NY = 2, 2
LEVEL = 0


def _build(coverage: BoundingBox = _BOUNDS, disk_title: str | None = None,
           media_version: str | None = None) -> bytes:
    """A tiny 2x2, single-level, parcel-free `ALLDATA.KWI` (no map frames
    needed for this check -- it never reads leaf content, only the
    container skeleton)."""
    raw = build_alldata_kwi(parcels=[], coverage=coverage, level=LEVEL,
                             grid_nx=NX, grid_ny=NY)
    if disk_title is None and media_version is None:
        return raw
    buf = bytearray(raw)
    hdr = _volume.parse_volume_header(bytes(buf[:_volume.DATAVOL_SIZE]))
    extras = _volume.parse_volume_header_extras(bytes(buf[:_volume.DATAVOL_SIZE]))
    if disk_title is not None:
        hdr.disk_title = disk_title
    if media_version is not None:
        hdr.media_version = media_version
    from kiwiw import volume_writer as _vw
    buf[0:_volume.DATAVOL_SIZE] = _vw.write_volume_header(hdr, extras)
    return bytes(buf)


def _ctx(reference_path: str, generated_path: str) -> Context:
    return Context(reference=reference_path, generated=generated_path,
                   config={"layers_present": ["map"], "container_allowlist": [
                       {"region": "volume_header", "field": "disk_title", "reason": "test"},
                       {"region": "volume_header", "field": "media_version", "reason": "test"},
                   ]})


def test_container_classifies_allowed_title_and_violation_coverage(tmp_path):
    r_path = tmp_path / "R.KWI"
    g_path = tmp_path / "G.KWI"
    r_path.write_bytes(_build(coverage=_BOUNDS, disk_title="REFERENCE TITLE"))
    g_path.write_bytes(_build(coverage=_OTHER_BOUNDS, disk_title="GENERATED TITLE"))

    ctx = _ctx(str(r_path), str(g_path))
    result = container_checks._run_container(ctx)

    assert result.status == "FAIL", result.message
    # disk_title differs but is allowlisted -> counted, not a violation.
    assert result.details["allowed_counts"].get("volume_header.disk_title") == 1
    # coverage (a PDMDH field, not allowlisted) differs -> a violation naming
    # the pdmdh coverage field, not a raw offset.
    violation_fields = {v["field"] for v in result.details["violations"]}
    assert "coverage" in violation_fields
    coverage_violations = [v for v in result.details["violations"] if v["field"] == "coverage"]
    assert all(v["region"] == "pdmdh" for v in coverage_violations)


def test_container_classifies_media_version_as_allowed(tmp_path):
    """Brief 18 ambiguity (a): `media_version` (Ch. 5.1 Data Volume, offset
    424..456) is a spec field distinct from `format_version`/`data_version`,
    confirmed legitimately variable between R and G on the real reference
    disc (R='V 05.07.20' vs the synthetic writer's '001') -- it belongs on
    the allowlist, same as the other version/title strings."""
    r_path = tmp_path / "R.KWI"
    g_path = tmp_path / "G.KWI"
    r_path.write_bytes(_build(coverage=_BOUNDS, media_version="V 05.07.20"))
    g_path.write_bytes(_build(coverage=_BOUNDS, media_version="001"))

    ctx = _ctx(str(r_path), str(g_path))
    result = container_checks._run_container(ctx)

    assert result.details["allowed_counts"].get("volume_header.media_version") == 1
    violation_fields = {v["field"] for v in result.details["violations"]}
    assert "media_version" not in violation_fields


def test_container_passes_when_identical(tmp_path):
    r_path = tmp_path / "R.KWI"
    g_path = tmp_path / "G.KWI"
    data = _build(coverage=_BOUNDS, disk_title="SAME TITLE")
    r_path.write_bytes(data)
    g_path.write_bytes(data)

    ctx = _ctx(str(r_path), str(g_path))
    result = container_checks._run_container(ctx)
    assert result.status == "PASS", result.message
    assert result.details["violation_count"] == 0


def test_container_na_without_reference(tmp_path):
    g_path = tmp_path / "G.KWI"
    g_path.write_bytes(_build())
    ctx = Context(reference=None, generated=str(g_path), config={"layers_present": ["map"]})
    result = container_checks._run_container(ctx)
    assert result.status == "NA"


def test_container_flags_one_byte_lmr_change_by_field_name(tmp_path):
    r_path = tmp_path / "R.KWI"
    g_path = tmp_path / "G.KWI"
    data = _build(coverage=_BOUNDS, disk_title="SAME TITLE")
    r_path.write_bytes(data)

    # Corrupt one byte inside level 0's LMR display-flags region in the
    # generated copy: PDMDH offset 30 is the LMR base (see
    # `build_alldata_kwi`'s "PDMDH layout" comment); display_flags occupies
    # bytes [4, 24) of the LMR (`volume.parse_pdmdh`).
    hdr = _volume.parse_volume_header(data[:_volume.DATAVOL_SIZE])
    mht = _volume.parse_management_header_table(
        data[_volume.DATAVOL_SIZE:_volume.DATAVOL_SIZE + _volume.MHT_SIZE])
    prdm = mht.entries[0]
    pdmdh_off = _volume.getsector(prdm.dsa, hdr.sector_size, hdr.logical_sector_size)
    lmr_off = pdmdh_off + 30  # PDMDH header is 30 bytes; the one LMR follows.
    dispflag_off = lmr_off + 4

    buf = bytearray(data)
    buf[dispflag_off] ^= 0xFF
    g_path.write_bytes(bytes(buf))

    ctx = _ctx(str(r_path), str(g_path))
    result = container_checks._run_container(ctx)

    assert result.status == "FAIL", result.message
    violation_fields = {v["field"] for v in result.details["violations"]}
    assert f"lmr[{LEVEL}].dispflag" in violation_fields
