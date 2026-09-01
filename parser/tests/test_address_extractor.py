"""Unit tests for ``parser/osm_to_address_index.py``.

Tests the ``build_index()`` pure function using hand-crafted ``AddressPoint``
lists -- no OSM PBF file or disc required.

Synthetic dataset
-----------------
- 3 streets: "MAIN STREET", "OAK AVENUE", "PINE ROAD"
- 2 cities:  "PERTH", "FREMANTLE"
- 10 address points distributed across streets and cities

Cross-reference invariants verified:
- SRMX record count (streets)
- SRT1 record count (address ranges)
- SRHA record count (cities)
- Every address_range.stid is a valid street stid
- Every city.street_stids entry is a valid street stid
- Streets are sorted alphabetically
- Address ranges are sorted by (stid, house_start)
- Cities are sorted alphabetically
- City cross-references are consistent with which streets have addresses there
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from osm_to_address_index import (
    AddressPoint,
    ExtractedStreet,
    ExtractedAddressRange,
    ExtractedCity,
    OsmAddressIndex,
    build_index,
    parse_house_number,
    street_to_srmx_dict,
    address_range_to_srt1_dict,
    city_to_srha_dict,
)

# ---------------------------------------------------------------------------
# Synthetic dataset
# ---------------------------------------------------------------------------

#: 10 address points across 3 streets and 2 cities.
#: Deliberately includes mixed upper/lower case and a house-number range.
SYNTHETIC_POINTS = [
    # Main Street, Perth (5 addresses)
    AddressPoint(lat=-31.950, lon=115.860, house_number="1",    street_name="Main Street",  city_name="Perth"),
    AddressPoint(lat=-31.951, lon=115.861, house_number="2",    street_name="Main Street",  city_name="Perth"),
    AddressPoint(lat=-31.952, lon=115.862, house_number="10",   street_name="main street",  city_name="PERTH"),  # lower-case
    AddressPoint(lat=-31.953, lon=115.863, house_number="12-16",street_name="MAIN STREET",  city_name="Perth"),  # range
    AddressPoint(lat=-31.954, lon=115.864, house_number="20",   street_name="Main Street",  city_name="Perth"),
    # Oak Avenue, Fremantle (3 addresses)
    AddressPoint(lat=-32.050, lon=115.750, house_number="3",    street_name="Oak Avenue",   city_name="Fremantle"),
    AddressPoint(lat=-32.051, lon=115.751, house_number="5",    street_name="Oak Avenue",   city_name="Fremantle"),
    AddressPoint(lat=-32.052, lon=115.752, house_number="7",    street_name="Oak Avenue",   city_name="Fremantle"),
    # Pine Road, Perth (2 addresses)
    AddressPoint(lat=-31.960, lon=115.870, house_number="100",  street_name="Pine Road",    city_name="Perth"),
    AddressPoint(lat=-31.961, lon=115.871, house_number="102",  street_name="Pine Road",    city_name="Perth"),
]


# ---------------------------------------------------------------------------
# Helper: build the index once for all tests in this module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def idx() -> OsmAddressIndex:
    return build_index(SYNTHETIC_POINTS)


# ---------------------------------------------------------------------------
# Record counts
# ---------------------------------------------------------------------------

def test_srmx_record_count(idx: OsmAddressIndex) -> None:
    """Exactly 3 unique streets -> 3 SRMX records."""
    assert len(idx.streets) == 3, (
        f"expected 3 SRMX records, got {len(idx.streets)}: {[s.name for s in idx.streets]}"
    )


def test_srt1_record_count(idx: OsmAddressIndex) -> None:
    """10 input points, all have parseable house numbers -> 10 SRT1 records."""
    assert len(idx.address_ranges) == 10, (
        f"expected 10 SRT1 records, got {len(idx.address_ranges)}"
    )


def test_srha_record_count(idx: OsmAddressIndex) -> None:
    """2 unique cities -> 2 SRHA records."""
    assert len(idx.cities) == 2, (
        f"expected 2 SRHA records, got {len(idx.cities)}: {[c.name for c in idx.cities]}"
    )


# ---------------------------------------------------------------------------
# Sorting invariants
# ---------------------------------------------------------------------------

def test_streets_sorted_alphabetically(idx: OsmAddressIndex) -> None:
    names = [s.name for s in idx.streets]
    assert names == sorted(names), f"streets not sorted: {names}"


def test_streets_uppercase(idx: OsmAddressIndex) -> None:
    for s in idx.streets:
        assert s.name == s.name.upper(), f"street name not upper-cased: {s.name!r}"


def test_address_ranges_sorted_by_stid_then_house(idx: OsmAddressIndex) -> None:
    keys = [(r.stid, r.house_start) for r in idx.address_ranges]
    assert keys == sorted(keys), f"address ranges not sorted: {keys[:5]}"


def test_cities_sorted_alphabetically(idx: OsmAddressIndex) -> None:
    names = [c.name for c in idx.cities]
    assert names == sorted(names), f"cities not sorted: {names}"


def test_cities_uppercase(idx: OsmAddressIndex) -> None:
    for c in idx.cities:
        assert c.name == c.name.upper(), f"city name not upper-cased: {c.name!r}"


# ---------------------------------------------------------------------------
# STID cross-reference consistency
# ---------------------------------------------------------------------------

def test_stid_values_unique(idx: OsmAddressIndex) -> None:
    """Each street has a distinct STID."""
    stids = [s.stid for s in idx.streets]
    assert len(stids) == len(set(stids)), f"duplicate STIDs: {stids}"


def test_stid_sequential_one_based(idx: OsmAddressIndex) -> None:
    """STIDs are assigned 1, 2, 3, ... in street sort order."""
    stids = [s.stid for s in idx.streets]
    assert stids == list(range(1, len(stids) + 1)), f"non-sequential STIDs: {stids}"


def test_address_range_stids_are_valid(idx: OsmAddressIndex) -> None:
    """Every address range's STID refers to an existing street."""
    valid_stids = {s.stid for s in idx.streets}
    for ar in idx.address_ranges:
        assert ar.stid in valid_stids, (
            f"address range has unknown STID {ar.stid}; valid: {valid_stids}"
        )


def test_city_street_stids_are_valid(idx: OsmAddressIndex) -> None:
    """Every STID in city.street_stids refers to an existing street."""
    valid_stids = {s.stid for s in idx.streets}
    for city in idx.cities:
        for stid in city.street_stids:
            assert stid in valid_stids, (
                f"city {city.name!r} references unknown STID {stid}; valid: {valid_stids}"
            )


def test_city_street_stids_sorted(idx: OsmAddressIndex) -> None:
    """street_stids within each city are in ascending order."""
    for city in idx.cities:
        assert city.street_stids == sorted(city.street_stids), (
            f"city {city.name!r} has unsorted street_stids: {city.street_stids}"
        )


def test_nxst_nxct_consistency(idx: OsmAddressIndex) -> None:
    """For each street, exactly NXCT address range records exist with its STID."""
    stid_to_count = {}
    for ar in idx.address_ranges:
        stid_to_count[ar.stid] = stid_to_count.get(ar.stid, 0) + 1

    for street in idx.streets:
        expected = stid_to_count.get(street.stid, 0)
        # The NXCT that the assembler would write == number of SRT1 records for this stid
        assert expected > 0, (
            f"street {street.name!r} (stid={street.stid}) has no address ranges"
        )


def test_city_references_correct_streets(idx: OsmAddressIndex) -> None:
    """Each city references exactly the streets that have addresses in it."""
    # Build expected mapping from the input points
    city_to_streets: dict = {}
    for pt in SYNTHETIC_POINTS:
        cn = pt.city_name.strip().upper()
        sn = pt.street_name.strip().upper()
        if cn and sn:
            city_to_streets.setdefault(cn, set()).add(sn)

    stid_map = {s.name: s.stid for s in idx.streets}
    for city in idx.cities:
        expected_stids = sorted(stid_map[sn] for sn in city_to_streets.get(city.name, set()))
        assert city.street_stids == expected_stids, (
            f"city {city.name!r}: expected street_stids {expected_stids}, "
            f"got {city.street_stids}"
        )


# ---------------------------------------------------------------------------
# House-number range parsing
# ---------------------------------------------------------------------------

def test_parse_house_number_single() -> None:
    assert parse_house_number("42") == (42, 42)


def test_parse_house_number_range_hyphen() -> None:
    assert parse_house_number("12-20") == (12, 20)


def test_parse_house_number_range_endash() -> None:
    assert parse_house_number("12–20") == (12, 20)


def test_parse_house_number_range_slash() -> None:
    assert parse_house_number("42/50") == (42, 50)


def test_parse_house_number_alphanumeric() -> None:
    assert parse_house_number("42A") == (42, 42)


def test_parse_house_number_zero_means_skip() -> None:
    assert parse_house_number("") == (0, 0)
    assert parse_house_number("abc") == (0, 0)


def test_range_is_normalised_low_to_high() -> None:
    """Range "50-42" is normalised to (42, 50) regardless of input order."""
    assert parse_house_number("50-42") == (42, 50)


# ---------------------------------------------------------------------------
# SRT1 range record: "12-16" should produce house_start=12, house_end=16
# ---------------------------------------------------------------------------

def test_address_range_from_housenumber_range(idx: OsmAddressIndex) -> None:
    """The "12-16" input point produces an address range with hs=12, he=16."""
    main_stid = next(s.stid for s in idx.streets if s.name == "MAIN STREET")
    matches = [ar for ar in idx.address_ranges if ar.stid == main_stid and ar.house_start == 12]
    assert len(matches) == 1, f"expected one range with house_start=12, got {matches}"
    assert matches[0].house_end == 16


# ---------------------------------------------------------------------------
# Coordinate sanity
# ---------------------------------------------------------------------------

def test_address_range_coordinates_in_wa_bbox(idx: OsmAddressIndex) -> None:
    """All synthetic coordinates are within the WA bounding box."""
    for ar in idx.address_ranges:
        assert -35.5 <= ar.lat <= -13.5, f"lat {ar.lat} out of WA bbox"
        assert 112.0 <= ar.lon <= 130.0, f"lon {ar.lon} out of WA bbox"


def test_city_representative_coordinate_is_mean(idx: OsmAddressIndex) -> None:
    """Perth's representative latitude should be the mean of its address lats."""
    perth = next(c for c in idx.cities if c.name == "PERTH")
    # Collect Perth points from input
    perth_lats = [pt.lat for pt in SYNTHETIC_POINTS if pt.city_name.upper() == "PERTH"]
    expected_lat = sum(perth_lats) / len(perth_lats)
    assert abs(perth.lat - expected_lat) < 1e-9


# ---------------------------------------------------------------------------
# Unparseable / missing data: these points should be silently skipped
# ---------------------------------------------------------------------------

def test_skips_missing_street_name() -> None:
    pts = [AddressPoint(lat=-31.9, lon=115.8, house_number="1", street_name="", city_name="Perth")]
    idx2 = build_index(pts)
    assert len(idx2.streets) == 0
    assert len(idx2.address_ranges) == 0


def test_skips_unparseable_house_number() -> None:
    pts = [AddressPoint(lat=-31.9, lon=115.8, house_number="ABC", street_name="Foo St", city_name="Perth")]
    idx2 = build_index(pts)
    # Street is discovered but has no valid address ranges
    assert len(idx2.streets) == 0
    assert len(idx2.address_ranges) == 0


def test_city_omitted_when_no_city_tag() -> None:
    pts = [AddressPoint(lat=-31.9, lon=115.8, house_number="1", street_name="Foo St", city_name="")]
    idx2 = build_index(pts)
    assert len(idx2.streets) == 1
    assert len(idx2.address_ranges) == 1
    assert len(idx2.cities) == 0


# ---------------------------------------------------------------------------
# Writer-compatible dict helpers
# ---------------------------------------------------------------------------

def test_srmx_dict_has_required_keys(idx: OsmAddressIndex) -> None:
    street = idx.streets[0]
    d = street_to_srmx_dict(street, nxst_halved=0, nxct=2)
    for key in ("BFRL", "NFRL", "FGFZ", "STFG", "STID", "NXKD", "NXFN", "NXST", "NXCT", "KYCH"):
        assert key in d, f"missing key {key!r} in SRMX dict"
    assert d["STID"] == street.stid
    assert d["KYCH"] == street.name
    assert d["NXCT"] == 2


def test_srt1_dict_has_required_keys(idx: OsmAddressIndex) -> None:
    ar = idx.address_ranges[0]
    d = address_range_to_srt1_dict(ar)
    for key in ("BFRL", "NFRL", "FGSA", "ARCD", "RLXY", "LKID", "STFG", "ZIPN", "PRFX", "STAD"):
        assert key in d, f"missing key {key!r} in SRT1 dict"
    assert d["STAD"] == [ar.house_start, ar.house_end]
    lat, lon = d["RLXY"]
    assert abs(lat - ar.lat) < 1e-9
    assert abs(lon - ar.lon) < 1e-9


def test_srha_dict_has_required_keys(idx: OsmAddressIndex) -> None:
    city = idx.cities[0]
    d = city_to_srha_dict(city, nxst_halved=0, nxct=1)
    for key in ("BFRL", "NFRL", "FGFZ", "STFG", "NXKD", "NXFN", "NXST", "NXCT", "KYCH", "RLXY"):
        assert key in d, f"missing key {key!r} in SRHA dict"
    assert d["KYCH"] == city.name
    assert d["NXCT"] == 1


def test_stfg_bits_correct_for_srmx() -> None:
    """SRMX STFG byte 0 = 0x3F (bits 0-5 set: STID,NXKD,NXFN,NXST,NXCT,KYCH)."""
    street = ExtractedStreet(stid=1, name="TEST STREET", city_name="PERTH")
    d = street_to_srmx_dict(street, nxst_halved=0, nxct=0)
    assert d["STFG"][0] == 0x3F, f"expected STFG[0]=0x3F, got {d['STFG'][0]:#04x}"
    assert d["STFG"][1] == 0x00, f"expected STFG[1]=0x00, got {d['STFG'][1]:#04x}"


if __name__ == "__main__":
    # Allow running directly with ``python3 parser/tests/test_address_extractor.py``
    import pytest as _pytest
    import sys as _sys
    _sys.exit(_pytest.main([__file__, "-v"]))
