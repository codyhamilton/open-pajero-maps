#!/usr/bin/env python3
"""OSM PBF → address search index extractor.

Reads an OSM PBF file (addr:housenumber / addr:street / addr:city tagged
nodes and ways) and produces an ``OsmAddressIndex`` intermediate
representation (IR) that the existing ``kiwiw/index_writer.py`` machinery
can encode into ``IDX/SADSR201.IDX``.

Usage::

    python3 parser/osm_to_address_index.py [PBF_FILE] [--dry-run] \\
        [--out OUTPUT.pkl]

    # quick smoke-test (no disc needed):
    python3 parser/osm_to_address_index.py --dry-run

Default PBF path matches ``build_route_graph.py``'s convention
(``~/workspace/open-pajero-maps/australia-260824.osm.pbf``).

Output
------
A Python ``pickle`` file containing an ``OsmAddressIndex`` object whose
three record lists map directly onto the three SADSR matching-data frames:

=================  ===========  ================================================
IR list            Frame type   Writer consumer
=================  ===========  ================================================
``streets``        SRMX         one SRMX matching record per street name
``address_ranges`` SRT1         one SRT1 matching record per addressed point
``cities``         SRHA         one SRHA matching record per city/suburb name
=================  ===========  ================================================

Cross-reference design
----------------------
- ``ExtractedStreet.stid`` is a synthetic sequential integer (1-based,
  assigned in alphabetical name order) that populates the ``STID`` field
  of both the SRMX record and every SRT1 record for that street.
- ``ExtractedCity.street_stids`` carries, in STID order, every street
  that has at least one address in that city; the assembler turns this
  into the ``NXST``/``NXCT`` pair in each SRHA record.
- ``address_ranges`` is sorted by ``(stid, house_start)``; consecutive
  records sharing the same ``stid`` form the contiguous block that the
  SRMX record's ``NXST``/``NXCT`` points at. The byte offset (``NXST``)
  and count (``NXCT``) are *not* stored here -- they depend on the
  serialized byte size of each SRT1 record, which is only known during
  final assembly.

Scope
-----
POISR (POI index) records are intentionally out of scope -- this module
covers only SADSR (street address / city) records.
"""
from __future__ import annotations

import argparse
import pickle
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_PBF = str(
    Path.home() / "workspace" / "open-pajero-maps" / "australia-260824.osm.pbf"
)

# ---------------------------------------------------------------------------
# Intermediate representation
# ---------------------------------------------------------------------------


@dataclass
class AddressPoint:
    """One geocoded address entry harvested from OSM (node or way centroid).

    This is the raw per-point data before deduplication and index assembly.
    """

    lat: float
    lon: float
    house_number: str   # raw OSM ``addr:housenumber`` value
    street_name: str    # OSM ``addr:street`` (will be upper-cased by builder)
    city_name: str      # ``addr:city`` or ``addr:suburb``; may be empty string


@dataclass
class ExtractedStreet:
    """SRMX matching record data: one unique street name.

    Fields map to SRMX matching-record slots:

    ========  ========  =====================================================
    IR field  MR field  Notes
    ========  ========  =====================================================
    stid      STID      synthetic sequential integer, 1-based
    name      KYCH      upper-cased ASCII search key
    city_name --        primary city for NXST/NXCT linkage to SRHA frame;
                        assembly step uses ExtractedCity.street_stids instead
    ========  ========  =====================================================

    NXKD / NXFN are always 5 / 1 (Ch.11.A.2.4.1.5 footnote 4: "next-level
    matching data" kind 5 + DSIR serial 1) -- the assembler fills these in.

    NXST / NXCT are computed by the assembler from the sorted
    ``address_ranges`` list (contiguous block of same-STID records).
    """

    stid: int
    name: str
    city_name: str  # primary city name (for informational cross-ref only)


@dataclass
class ExtractedAddressRange:
    """SRT1 matching record data: one address point on a named street.

    Fields map to SRT1 matching-record slots:

    ============  ========  =====================================================
    IR field      MR field  Notes
    ============  ========  =====================================================
    stid          --        not a direct MR field; used by the assembler to
                            sort records and to compute SRMX NXST/NXCT
    house_start   STAD[0]   low end of house-number range (= house_end for
                            a single house number)
    house_end     STAD[1]   high end of house-number range
    lat, lon      RLXY      WGS84 decimal degrees, encoded as ``geo_secs``
                            (3-byte signed 1/8 arc-second) during assembly
    ============  ========  =====================================================

    LKID is synthetic (sequential, matching ``build_route_graph.py``'s
    convention for a not-yet-linked main-map writer) -- filled in by the
    assembler.  ARCD (area codes) is left empty; FGSA is 0 (not a
    centre-link record).
    """

    stid: int
    house_start: int    # STAD[0] -- low end of range
    house_end: int      # STAD[1] -- high end of range
    lat: float          # RLXY latitude (WGS84 degrees)
    lon: float          # RLXY longitude (WGS84 degrees)


@dataclass
class ExtractedCity:
    """SRHA matching record data: one unique city or suburb.

    Fields map to SRHA matching-record slots:

    ============  ========  =====================================================
    IR field      MR field  Notes
    ============  ========  =====================================================
    name          KYCH      upper-cased ASCII search key / display name
    street_stids  NXST/NXCT sorted list of STIDs of streets with addresses in
                            this city; the assembler maps these to SRHA's own
                            NXST byte-offset / NXCT count (pointing into the
                            SRMX matching-data frame, NOT the SRT1 frame)
    lat, lon      RLXY      representative centroid (mean of address coords)
    ============  ========  =====================================================
    """

    name: str
    street_stids: List[int]     # sorted ascending list of STIDs
    lat: float                  # representative latitude
    lon: float                  # representative longitude


@dataclass
class OsmAddressIndex:
    """Complete address search IR built from OSM data.

    Invariants (verified by ``tests/test_address_extractor.py``):

    1. ``streets`` is sorted alphabetically by ``name``.
    2. ``address_ranges`` is sorted by ``(stid, house_start)``.
    3. ``cities`` is sorted alphabetically by ``name``.
    4. Every ``address_range.stid`` is a valid ``street.stid``.
    5. Every value in every ``city.street_stids`` is a valid ``street.stid``.
    6. If a city references street S, then at least one address range with
       ``stid == S.stid`` exists.
    """

    streets: List[ExtractedStreet]
    address_ranges: List[ExtractedAddressRange]
    cities: List[ExtractedCity]


# ---------------------------------------------------------------------------
# House-number parsing
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^(\d+)\s*[-–/]\s*(\d+)$")
_LEADING_DIGITS_RE = re.compile(r"^(\d+)")


def parse_house_number(raw: str) -> Tuple[int, int]:
    """Parse an OSM ``addr:housenumber`` value into ``(house_start, house_end)``.

    Handles the common cases:

    ========================  ===========================  =================
    Input                     Result                       Notes
    ========================  ===========================  =================
    ``"42"``                  ``(42, 42)``                 single number
    ``"42-50"``               ``(42, 50)``                 ASCII hyphen range
    ``"42\\u201350"``         ``(42, 50)``                 en-dash range
    ``"42/50"``               ``(42, 50)``                 slash range
    ``"42A"``                 ``(42, 42)``                 alphanumeric suffix
    ``"0"`` / ``""``          ``(0, 0)``                   caller should skip
    ========================  ===========================  =================

    Returns ``(0, 0)`` when no digits can be extracted.
    """
    raw = raw.strip()
    m = _RANGE_RE.match(raw)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return (min(a, b), max(a, b))
    m = _LEADING_DIGITS_RE.match(raw)
    if m:
        v = int(m.group(1))
        return (v, v)
    return (0, 0)


# ---------------------------------------------------------------------------
# Index builder -- pure function, testable without PBF I/O
# ---------------------------------------------------------------------------


def build_index(points: List[AddressPoint]) -> OsmAddressIndex:
    """Build an ``OsmAddressIndex`` from a flat list of geocoded address points.

    This is the core, PBF-independent logic:

    1. Upper-case and deduplicate street names; assign sequential STIDs in
       alphabetical order.
    2. Parse each point's house number; skip unparseable / zero entries.
    3. Sort address ranges by ``(stid, house_start)``.
    4. Collect unique city names; for each city accumulate the set of STIDs
       and a representative centroid (mean of all address coordinates).
    5. Sort cities alphabetically.

    Street and city names are normalised to upper-case ASCII strip -- matching
    the real disc's KYCH convention (all 38,120 street records in
    ``SADSR201.IDX`` use upper-case ASCII).
    """
    # ---- 1. Unique street names, alphabetical STID assignment ---------------
    name_to_stid: Dict[str, int] = {}   # upper-cased name → stid
    name_to_city: Dict[str, str] = {}   # name → first city seen (informational)

    valid_points: List[Tuple[AddressPoint, int, int]] = []  # (pt, hs, he)
    for pt in points:
        if not pt.street_name:
            continue
        hs, he = parse_house_number(pt.house_number)
        if hs == 0 and he == 0:
            continue
        name = pt.street_name.strip().upper()
        if not name:
            continue
        if name not in name_to_stid:
            name_to_stid[name] = 0          # placeholder; filled below
            name_to_city[name] = (pt.city_name.strip().upper() if pt.city_name else "")
        valid_points.append((pt, hs, he))

    sorted_names = sorted(name_to_stid.keys())
    for i, name in enumerate(sorted_names, start=1):
        name_to_stid[name] = i

    streets: List[ExtractedStreet] = [
        ExtractedStreet(stid=name_to_stid[name], name=name, city_name=name_to_city[name])
        for name in sorted_names
    ]

    # ---- 2. Address range records (SRT1) ------------------------------------
    address_ranges: List[ExtractedAddressRange] = []
    for pt, hs, he in valid_points:
        name = pt.street_name.strip().upper()
        stid = name_to_stid.get(name, 0)
        if stid == 0:
            continue
        address_ranges.append(ExtractedAddressRange(
            stid=stid,
            house_start=hs,
            house_end=he,
            lat=pt.lat,
            lon=pt.lon,
        ))
    address_ranges.sort(key=lambda r: (r.stid, r.house_start))

    # ---- 3. City records (SRHA) ---------------------------------------------
    city_stids: Dict[str, List[int]] = {}    # city_name → unique stid list
    city_lats: Dict[str, List[float]] = {}
    city_lons: Dict[str, List[float]] = {}

    for pt, hs, he in valid_points:
        cn = pt.city_name.strip().upper() if pt.city_name else ""
        if not cn:
            continue
        name = pt.street_name.strip().upper()
        stid = name_to_stid.get(name, 0)
        if stid == 0:
            continue
        if cn not in city_stids:
            city_stids[cn] = []
            city_lats[cn] = []
            city_lons[cn] = []
        if stid not in city_stids[cn]:
            city_stids[cn].append(stid)
        city_lats[cn].append(pt.lat)
        city_lons[cn].append(pt.lon)

    cities: List[ExtractedCity] = []
    for cn in sorted(city_stids.keys()):
        stids = sorted(set(city_stids[cn]))
        lats = city_lats[cn]
        lons = city_lons[cn]
        cities.append(ExtractedCity(
            name=cn,
            street_stids=stids,
            lat=sum(lats) / len(lats),
            lon=sum(lons) / len(lons),
        ))

    return OsmAddressIndex(streets=streets, address_ranges=address_ranges, cities=cities)


# ---------------------------------------------------------------------------
# OSM PBF reader (pyosmium)
# ---------------------------------------------------------------------------


class _AddressHandler:
    """pyosmium handler that collects AddressPoints from tagged OSM elements.

    Handles both nodes (direct lat/lon) and ways (centroid of member node
    coordinates, available when apply_file is called with ``locations=True``).
    """

    def __init__(self) -> None:
        self.points: List[AddressPoint] = []

    def node(self, n) -> None:
        tags = n.tags
        hn = tags.get("addr:housenumber", "")
        st = tags.get("addr:street", "")
        if not hn or not st:
            return
        if not n.location.valid():
            return
        city = tags.get("addr:city") or tags.get("addr:suburb") or ""
        self.points.append(AddressPoint(
            lat=n.location.lat,
            lon=n.location.lon,
            house_number=hn,
            street_name=st,
            city_name=city,
        ))

    def way(self, w) -> None:
        tags = w.tags
        hn = tags.get("addr:housenumber", "")
        st = tags.get("addr:street", "")
        if not hn or not st:
            return
        lats: List[float] = []
        lons: List[float] = []
        try:
            for nd in w.nodes:
                if nd.location.valid():
                    lats.append(nd.location.lat)
                    lons.append(nd.location.lon)
        except Exception:
            return
        if not lats:
            return
        city = tags.get("addr:city") or tags.get("addr:suburb") or ""
        self.points.append(AddressPoint(
            lat=sum(lats) / len(lats),
            lon=sum(lons) / len(lons),
            house_number=hn,
            street_name=st,
            city_name=city,
        ))


def extract_from_pbf(pbf_path: str) -> OsmAddressIndex:
    """Read *pbf_path* (OSM PBF) and return an ``OsmAddressIndex``.

    Requires ``pyosmium`` (already installed; used by ``build_route_graph.py``).
    Uses a single-pass ``SimpleHandler`` with ``locations=True`` so way nodes'
    coordinates are available to the ``way()`` callback.
    """
    try:
        import osmium
    except ImportError as exc:
        raise ImportError(
            "pyosmium is required (pip install osmium) -- it is already "
            "available in this project's environment (build_route_graph.py uses it)"
        ) from exc

    class _Handler(osmium.SimpleHandler, _AddressHandler):
        def __init__(self) -> None:
            osmium.SimpleHandler.__init__(self)
            _AddressHandler.__init__(self)

    h = _Handler()
    h.apply_file(pbf_path, locations=True, idx="flex_mem")
    return build_index(h.points)


# ---------------------------------------------------------------------------
# Writer-compatible record dict helpers
# ---------------------------------------------------------------------------
#
# These functions produce the field-value dicts that
# ``kiwiw.index_writer.write_matching_record`` consumes.  They require the
# FieldDef lists for each frame type, which the caller must supply (typically
# read from the real disc via ``kiwiw.search_frame.parse_definition_frame``
# on the existing SADSR201.IDX, or reconstructed from the hardcoded schema
# in ``make_srmx_fields`` / ``make_srt1_fields`` / ``make_srha_fields``).
#
# BFRL / NFRL (chain pointers) are set to 0 here -- the final assembler
# must patch them after serializing each record, because they depend on the
# encoded byte length of adjacent records.  The real disc's chain uses
# NFRL == physical_byte_length and BFRL == previous_record_byte_length
# (both SWS-halved).  A value of 0 is safe as a placeholder: the writer
# stores (value // 2), and 0 // 2 == 0 which is unambiguous as the
# "last record" sentinel on the real disc -- so the assembler must overwrite
# these before the file is valid.


def _stfg_bytes(bits: List[bool]) -> bytes:
    """Pack a list of boolean presence flags into a STFG byte string (LSB-first
    within each byte, byte 0 first) matching the real disc's encoding."""
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j, b in enumerate(bits[i : i + 8]):
            if b:
                byte |= 1 << j
        out.append(byte)
    return bytes(out)


def street_to_srmx_dict(
    street: ExtractedStreet,
    nxst_halved: int,
    nxct: int,
    *,
    nxkd: int = 5,
    nxfn: int = 1,
    fgfz: int = 0,
) -> dict:
    """Return a matching-record dict for one SRMX (street name) record.

    ``nxst_halved`` is the SWS-halved byte offset into the SRT1
    matching-data frame of the first address-range record for this street.
    ``nxct`` is the number of consecutive SRT1 records belonging to it.

    The six gated fields (STID, NXKD, NXFN, NXST, NXCT, KYCH) correspond
    to STFG bits 0-5; bits 6-11 (NAME, RPNK, RPNF, RPNS, RPNC, and one
    reserved) are absent.  This matches the real disc's ``STFG = 0x3F 0x00``
    pattern for streets that carry only the primary search fields.

    BFRL / NFRL are set to 0 -- the assembler must patch them.
    """
    # 12 gated fields in the real SRMX definition frame (16 total - 4 pre-STFG)
    # bits 0-5: STID, NXKD, NXFN, NXST, NXCT, KYCH present
    # bits 6-11: NAME, RPNK, RPNF, RPNS, RPNC, (reserved) absent
    stfg = _stfg_bytes([True, True, True, True, True, True, False, False,
                        False, False, False, False])
    return {
        "BFRL": 0,
        "NFRL": 0,
        "FGFZ": fgfz,
        "STFG": list(stfg),
        "STID": street.stid,
        "NXKD": nxkd,
        "NXFN": nxfn,
        "NXST": nxst_halved,
        "NXCT": nxct,
        "KYCH": street.name,
    }


def address_range_to_srt1_dict(
    ar: ExtractedAddressRange,
    *,
    lkid: int = 0,
    fgsa: int = 0,
    arcd: Optional[List[int]] = None,
) -> dict:
    """Return a matching-record dict for one SRT1 (address range) record.

    The three gated fields (ZIPN, PRFX, STAD) correspond to STFG bits 0-2.
    ZIPN (zip code) and PRFX (address prefix) are set to empty strings since
    OSM data does not carry separate postcode/prefix fields at the point
    level; callers can override by editing the returned dict.

    LKID is synthetic (set to ``lkid``, default 0); the final assembler
    must supply real link IDs once a main-map writer is available.
    ARCD (area codes) defaults to an empty list.
    BFRL / NFRL are set to 0 -- the assembler must patch them.
    """
    if arcd is None:
        arcd = []
    # 9 gated fields in the real SRT1 definition frame
    # bits 0-2: ZIPN, PRFX, STAD present; bits 3-8 absent
    stfg = _stfg_bytes([True, True, True, False, False, False, False, False, False])
    return {
        "BFRL": 0,
        "NFRL": 0,
        "FGSA": fgsa,
        "ARCD": arcd,
        "RLXY": (ar.lat, ar.lon),
        "LKID": lkid,
        "STFG": list(stfg),
        "ZIPN": "",
        "PRFX": "",
        "STAD": [ar.house_start, ar.house_end],
    }


def city_to_srha_dict(
    city: ExtractedCity,
    nxst_halved: int,
    nxct: int,
    *,
    nxkd: int = 5,
    nxfn: int = 1,
    fgfz: int = 0,
) -> dict:
    """Return a matching-record dict for one SRHA (city selection) record.

    ``nxst_halved`` / ``nxct`` point at the contiguous block of SRMX
    matching records for the streets in this city (i.e. into the SRMX
    matching-data frame, not the SRT1 frame).

    RLXY uses the CMP6 VRBL encoding declared on SRHA's own definition
    frame -- a (lat, lon) tuple, exactly as ``_read_variable`` and
    ``_write_field`` expect for ``element_type='BT', additional='CMP6'``.
    NXKD / NXFN use element type ``'HB'`` (nibble, same as SRMX's ``'UH'``).

    BFRL / NFRL are set to 0 -- the assembler must patch them.
    """
    # SRHA gated fields (from Ch.11.A.2.4.2.4):
    # STID, NXKD, NXFN, NXST, NXCT, KYCH, NAME, RLXY -- 8 gated fields
    # bits 0-7: STID, NXKD, NXFN, NXST, NXCT, KYCH, NAME, RLXY all present
    # For OSM data we omit STID (SRHA records don't carry a per-city STID),
    # and include NXKD, NXFN, NXST, NXCT, KYCH, RLXY (6 fields, bits 1-5,7).
    stfg = _stfg_bytes([False, True, True, True, True, True, False, True])
    return {
        "BFRL": 0,
        "NFRL": 0,
        "FGFZ": fgfz,
        "STFG": list(stfg),
        "NXKD": nxkd,
        "NXFN": nxfn,
        "NXST": nxst_halved,
        "NXCT": nxct,
        "KYCH": city.name,
        "RLXY": (city.lat, city.lon),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_sample(label: str, records: list, n: int = 3) -> None:
    print(f"  {label}: {len(records)} records")
    for r in records[:n]:
        print(f"    {r}")
    if len(records) > n:
        print(f"    ... ({len(records) - n} more)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="OSM PBF → SADSR address search index extractor"
    )
    parser.add_argument(
        "pbf",
        nargs="?",
        default=DEFAULT_PBF,
        metavar="PBF_FILE",
        help=f"path to OSM PBF extract (default: {DEFAULT_PBF})",
    )
    parser.add_argument(
        "--out",
        default="address_index.pkl",
        metavar="OUTPUT",
        help="output pickle file path (default: address_index.pkl)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print record counts and samples without writing the output file",
    )
    args = parser.parse_args(argv)

    pbf_path = args.pbf
    if not Path(pbf_path).exists():
        print(f"ERROR: PBF file not found: {pbf_path}", file=sys.stderr)
        if args.dry_run:
            print("(--dry-run: nothing to do without input file)", file=sys.stderr)
            return 1
        return 1

    print(f"Reading {pbf_path} ...")
    idx = extract_from_pbf(pbf_path)

    print(f"Extracted:")
    _print_sample("streets (SRMX)", idx.streets)
    _print_sample("address ranges (SRT1)", idx.address_ranges)
    _print_sample("cities (SRHA)", idx.cities)

    if args.dry_run:
        print("(--dry-run: output file not written)")
        return 0

    out_path = args.out
    with open(out_path, "wb") as fh:
        pickle.dump(idx, fh, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"Written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
