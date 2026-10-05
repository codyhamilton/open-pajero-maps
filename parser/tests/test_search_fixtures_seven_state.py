"""Offline seven-state search fixtures (plan 26).

Proves the search-index test surface covers IDX suffixes 201–207
(WA, NT, SA, QLD, NSW, VIC, TAS). Synthetic AddressPoint fixtures +
build_index + SRMX matching-record round-trip. POISR coverage is
filename/partition stubs only (no POISR decoder bugfix).

Offline seven-state fixtures ≠ WP3 complete ≠ Australia-wide MMCS proof.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.index_writer import write_matching_record
from kiwiw.search_frame import FieldDef, parse_matching_record
from kiwiw.state_partitions import (
    EXPECTED_ROWS,
    StatePartition,
    all_suffixes,
    code_to_suffix,
    load_partitions,
    resolve_suffix,
    suffix_to_code,
)
from osm_to_address_index import (
    AddressPoint,
    build_index,
    street_to_srmx_dict,
)

_REFDATA = Path(__file__).resolve().parent.parent / "refdata" / "state_partitions.json"

# One synthetic address per state. Coordinates are illustrative city
# centroids (explicit state_code on each row — not bbox-as-state product law).
SYNTHETIC_BY_SUFFIX: dict[int, dict] = {
    201: {
        "code": "WA",
        "city": "Perth",
        "street": "Hay Street",
        "lat": -31.9505,
        "lon": 115.8605,
    },
    202: {
        "code": "NT",
        "city": "Darwin",
        "street": "Mitchell Street",
        "lat": -12.4634,
        "lon": 130.8456,
    },
    203: {
        "code": "SA",
        "city": "Adelaide",
        "street": "King William Street",
        "lat": -34.9285,
        "lon": 138.6007,
    },
    204: {
        "code": "QLD",
        "city": "Brisbane",
        "street": "Queen Street",
        "lat": -27.4698,
        "lon": 153.0251,
    },
    205: {
        "code": "NSW",
        "city": "Sydney",
        "street": "George Street",
        "lat": -33.8688,
        "lon": 151.2093,
    },
    206: {
        "code": "VIC",
        "city": "Melbourne",
        "street": "Collins Street",
        "lat": -37.8136,
        "lon": 144.9631,
    },
    207: {
        "code": "TAS",
        "city": "Hobart",
        "street": "Elizabeth Street",
        "lat": -42.8821,
        "lon": 147.3272,
    },
}

# Australia-wide soft box for synthetic sanity only (not state assignment).
_AU_LAT = (-44.0, -10.0)
_AU_LON = (112.0, 154.0)


def _points_for_suffix(suffix: int) -> list[AddressPoint]:
    row = SYNTHETIC_BY_SUFFIX[suffix]
    return [
        AddressPoint(
            lat=row["lat"],
            lon=row["lon"],
            house_number="1",
            street_name=row["street"],
            city_name=row["city"],
        )
    ]


def _srmx_field_defs() -> list:
    def fd(usage, dtype, etype, count, count_type="", addl=""):
        return FieldDef(
            usage=usage,
            description_type=dtype,
            element_type=etype,
            count=count,
            count_type=count_type,
            additional=addl,
        )

    return [
        fd("BFRL", "FDRL", "UB", 1),
        fd("NFRL", "FDRL", "UB", 1),
        fd("FGFZ", "NORM", "UB", 1),
        fd("STFG", "NORM", "UB", 2),
        fd("STID", "NORM", "UL", 1),
        fd("NXKD", "NORM", "UH", 1),
        fd("NXFN", "NORM", "UH", 1),
        fd("NXST", "OFST", "LG", 1),
        fd("NXCT", "NORM", "LG", 1),
        fd("KYCH", "VRBL", "CH", 1, "UB", "CMCH"),
        fd("NAME", "VRBL", "CH", 1, "UB", "CMCH"),
        fd("RPAT", "NORM", "BF", 8),
        fd("RPNK", "NORM", "UH", 1),
        fd("RPNF", "NORM", "UH", 1),
        fd("RPNS", "OFST", "LG", 1),
        fd("RPNC", "NORM", "UL", 1),
    ]


# ---------------------------------------------------------------------------
# Partition table completeness
# ---------------------------------------------------------------------------


def test_partition_table_length_is_seven() -> None:
    parts = load_partitions()
    assert len(parts) == 7
    assert len(EXPECTED_ROWS) == 7


def test_partition_table_matches_schema_row() -> None:
    parts = load_partitions()
    got = [(p.suffix, p.code) for p in parts]
    assert got == list(EXPECTED_ROWS)


def test_partition_table_no_extra_suffixes() -> None:
    suffixes = all_suffixes()
    assert suffixes == [201, 202, 203, 204, 205, 206, 207]
    assert set(suffixes) == set(range(201, 208))


def test_partition_json_agrees_with_loader() -> None:
    raw = json.loads(_REFDATA.read_text(encoding="utf-8"))
    assert len(raw["partitions"]) == 7
    for row, expected in zip(raw["partitions"], EXPECTED_ROWS):
        assert int(row["suffix"]) == expected[0]
        assert row["code"] == expected[1]


def test_inverse_maps_roundtrip() -> None:
    s2c = suffix_to_code()
    c2s = code_to_suffix()
    assert len(s2c) == 7 and len(c2s) == 7
    for suffix, code in EXPECTED_ROWS:
        assert s2c[suffix] == code
        assert c2s[code] == suffix


@pytest.mark.parametrize("code,suffix", [("WA", 201), ("TAS", 207), ("NSW", 205)])
def test_resolve_suffix_accepts_code_and_int(code: str, suffix: int) -> None:
    assert resolve_suffix(code) == suffix
    assert resolve_suffix(suffix) == suffix
    assert resolve_suffix(str(suffix)) == suffix


def test_resolve_suffix_default_wa() -> None:
    assert resolve_suffix(None) == 201
    assert resolve_suffix("") == 201


def test_resolve_suffix_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        resolve_suffix("ZZ")
    with pytest.raises(ValueError):
        resolve_suffix(199)


# ---------------------------------------------------------------------------
# Per-state synthetic fixtures + search-index behaviour
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("partition", load_partitions(), ids=lambda p: f"{p.suffix}-{p.code}")
def test_synthetic_fixture_covers_every_suffix(partition: StatePartition) -> None:
    assert partition.suffix in SYNTHETIC_BY_SUFFIX
    row = SYNTHETIC_BY_SUFFIX[partition.suffix]
    assert row["code"] == partition.code
    pts = _points_for_suffix(partition.suffix)
    assert len(pts) >= 1
    assert _AU_LAT[0] <= pts[0].lat <= _AU_LAT[1]
    assert _AU_LON[0] <= pts[0].lon <= _AU_LON[1]


@pytest.mark.parametrize("partition", load_partitions(), ids=lambda p: f"{p.suffix}-{p.code}")
def test_build_index_and_srmx_roundtrip_per_state(partition: StatePartition) -> None:
    """Address-index path exercised for every suffix (write/read SRMX)."""
    row = SYNTHETIC_BY_SUFFIX[partition.suffix]
    idx = build_index(_points_for_suffix(partition.suffix))
    assert len(idx.streets) == 1
    assert len(idx.address_ranges) == 1
    assert len(idx.cities) == 1

    street = idx.streets[0]
    assert street.name == row["street"].upper()
    city = idx.cities[0]
    assert city.name == row["city"].upper()

    ar = idx.address_ranges[0]
    assert abs(ar.lat - row["lat"]) < 1e-9
    assert abs(ar.lon - row["lon"]) < 1e-9

    fields = _srmx_field_defs()
    d = street_to_srmx_dict(street, nxst_halved=0, nxct=0)
    rec = write_matching_record(d, fields)
    parsed = parse_matching_record(rec, 0, fields)
    assert parsed["KYCH"] == street.name
    assert parsed["STID"] == street.stid
    assert parsed["NAME"] == ""
    assert isinstance(rec, (bytes, bytearray))
    assert len(rec) > 0


@pytest.mark.parametrize("partition", load_partitions(), ids=lambda p: f"{p.suffix}-{p.code}")
def test_sadsr_poisr_basenames_per_state(partition: StatePartition) -> None:
    """Basename/partition contract for SADSR + best-effort POISR stubs."""
    assert partition.sadsr_basename == f"SADSR{partition.suffix}.IDX"
    assert partition.poisr_basename == f"POISR{partition.suffix}.IDX"
    assert str(partition.suffix) in partition.sadsr_basename
    assert str(partition.suffix) in partition.poisr_basename
    # Path-shaped fixture name used by demo / tests (no real-disc blob).
    rel = f"IDX/{partition.sadsr_basename}"
    assert rel.endswith(f"{partition.suffix}.IDX")
    assert partition.code in suffix_to_code().values()


def test_fixture_set_missing_suffix_would_fail() -> None:
    """Oracle: every table suffix must have a synthetic fixture row."""
    missing = [s for s in all_suffixes() if s not in SYNTHETIC_BY_SUFFIX]
    assert missing == [], f"missing synthetic fixtures for suffixes {missing}"


def test_wa_retained_in_fixture_set() -> None:
    assert 201 in SYNTHETIC_BY_SUFFIX
    assert SYNTHETIC_BY_SUFFIX[201]["code"] == "WA"
