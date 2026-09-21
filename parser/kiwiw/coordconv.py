"""Local parcel-internal pixel coordinates -> lat/lon.

**Confidence: medium, not spec-confirmed.** Road/background/name shape
coordinates are stored as a 13-bit value (0..8191) plus a 3-bit "relative
position" field (bits 13:15 of the raw 16-bit word) which the spec labels
differently in different places ("Relative position within integrated
parcel" in the Linear-B/Linear-C name records, 7.4.2.1.2/.1.6). kiwiread.c
combines them as `extract(v,0,12) + region*4096` and feeds the result
directly into an SVG canvas nominally sized 4096x4096 -- Phase 0 observed
some background polygon coordinates landing far outside that canvas
(thousands of pixels negative/over), which is consistent with the combined
value actually ranging up to ~2^15 (0..32767ish) rather than 0..4095.

We treat the combined value's *full* range as spanning the single small
leaf-parcel bounding box that `mesh.locate_parcel()` resolves (not a larger
"integrated parcel" -- we could not confirm which interpretation is right).
`COORD_RANGE` is chosen as 2**15 accordingly. If real-disc output looks
wrong (e.g. road points landing wildly outside the parcel bbox), this
constant is the first thing to revisit.

Orientation (settled): y increases northward, so y=0 is the parcel's
south edge (lat_lo) and y=COORD_RANGE its north edge (lat_hi); x increases
eastward. Basis: Plan 03's 2-03 overlay test, pooled over 12 cells x 7
classes, matched road fraction / p50 error with y up vs y down -- L0_urban
0.836/4.73 m vs 0.094/50.33 m; L2 0.843/8.07 vs 0.190/210.78; L4
0.894/10.68 vs 0.138/1340.50; L6 0.875/25.43 vs 0.234/4412.48; L8
0.863/119.92 vs 0.145/58783.46; divided 0.773/3.62 vs 0.291/22.87;
L0_sparse 0.717/26.51 vs 0.042/487.49.
"""
from __future__ import annotations

from .model import BoundingBox

COORD_RANGE = float(1 << 15)


def xy_to_latlon(xc: int, yc: int, bounds: BoundingBox) -> tuple[float, float]:
    lon = bounds.lon_lo + (xc / COORD_RANGE) * (bounds.lon_hi - bounds.lon_lo)
    lat = bounds.lat_lo + (yc / COORD_RANGE) * (bounds.lat_hi - bounds.lat_lo)
    return lat, lon


def decode_region_coord(raw: int) -> int:
    """Combine the 13-bit value + 3-bit region field used throughout the
    road/background/name shape encodings (`extract(v,0,12) + region*4096`)."""
    from .bitutils import extract

    region = extract(raw, 13, 15)
    value = extract(raw, 0, 12)
    return value + region * 4096


def encode_region_coord(xc: int) -> int:
    """Inverse of decode_region_coord: encode a parcel-local pixel coordinate
    to the raw 16-bit word form used throughout the road/background/name
    shape encodings.

    Uses region = xc // 4096, value = xc % 4096 (value always in 0..4095,
    12 bits).  This is a valid inverse -- decode_region_coord(
    encode_region_coord(xc)) == xc for any xc in 0..32767.

    Note: the real disc may use different (but equally valid) raw values
    for some coordinates -- this encoder will produce different bytes than
    the original but decodes to the same pixel coordinate.
    """
    if not 0 <= xc <= int(COORD_RANGE) - 1:
        raise ValueError(
            f"pixel coordinate {xc} out of range 0..{int(COORD_RANGE) - 1}"
        )
    region = xc // 4096
    value = xc % 4096
    return value | (region << 13)


def latlon_to_xy(lat: float, lon: float, bounds: BoundingBox) -> tuple[int, int]:
    """Inverse of xy_to_latlon: convert geographic coordinates to
    parcel-local pixel coordinates.

    The result is rounded to the nearest integer pixel.  When called with
    a (lat, lon) that xy_to_latlon() produced from integer (xc, yc), the
    round-trip is exact (the floating-point cancellation is clean and
    round() absorbs any residual epsilon).
    """
    xc = int(round(
        (lon - bounds.lon_lo) / (bounds.lon_hi - bounds.lon_lo) * COORD_RANGE
    ))
    yc = int(round(
        (lat - bounds.lat_lo) / (bounds.lat_hi - bounds.lat_lo) * COORD_RANGE
    ))
    return xc, yc
