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

Also unconfirmed: which raw axis direction maps to increasing latitude.
We assume "y increases toward the northern edge of the bbox" (screen-down
convention flipped to geographic-up); this only affects north/south
mirroring within a single small parcel (order-of-magnitude sanity checks
are unaffected either way).
"""
from __future__ import annotations

from .model import BoundingBox

COORD_RANGE = float(1 << 15)


def xy_to_latlon(xc: int, yc: int, bounds: BoundingBox) -> tuple[float, float]:
    lon = bounds.lon_lo + (xc / COORD_RANGE) * (bounds.lon_hi - bounds.lon_lo)
    lat = bounds.lat_hi - (yc / COORD_RANGE) * (bounds.lat_hi - bounds.lat_lo)
    return lat, lon


def decode_region_coord(raw: int) -> int:
    """Combine the 13-bit value + 3-bit region field used throughout the
    road/background/name shape encodings (`extract(v,0,12) + region*4096`)."""
    from .bitutils import extract

    region = extract(raw, 13, 15)
    value = extract(raw, 0, 12)
    return value + region * 4096
