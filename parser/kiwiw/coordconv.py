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

Plan 03 settled the real model (`range_for` below): the combined value's
range is not one fixed constant but a function of (level, parcel class,
division state), read from `refdata/profile/coord_scale.json`. The
per-call `coord_range` parameters below replace the old fixed-2**15
assumption; `_LEGACY_RANGE` is a temporary shim -- see its docstring.

Orientation (settled): y increases northward, so y=0 is the parcel's
south edge (lat_lo) and y=coord_range its north edge (lat_hi); x increases
eastward. Basis: Plan 03's 2-03 overlay test, pooled over 12 cells x 7
classes, matched road fraction / p50 error with y up vs y down -- L0_urban
0.836/4.73 m vs 0.094/50.33 m; L2 0.843/8.07 vs 0.190/210.78; L4
0.894/10.68 vs 0.138/1340.50; L6 0.875/25.43 vs 0.234/4412.48; L8
0.863/119.92 vs 0.145/58783.46; divided 0.773/3.62 vs 0.291/22.87;
L0_sparse 0.717/26.51 vs 0.042/487.49.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .model import BoundingBox

# TEMPORARY -- deleted by unit 3-03; no caller may rely on it.
# Default of the three conversions' keyword-only `coord_range`, so the
# unmigrated encoders (3-02/3-03's) keep their exact present behaviour.
_LEGACY_RANGE = 32768

# TEMPORARY -- deleted by unit 3-03 with `_LEGACY_RANGE`. 3-01's brief says
# to delete this public name, but synth.py and osm_to_parcel_geometry.py
# (out of 3-01's owned paths) still import it; an alias, not a second copy.
COORD_RANGE = float(_LEGACY_RANGE)

# Design rule "one global raw lattice per level": 4096 raw units per leaf
# slot; a divided parent's frame is one slot.
_SLOT_RANGE = 4096

_COORD_SCALE_PATH = (
    Path(__file__).resolve().parent.parent / "refdata" / "profile" / "coord_scale.json"
)
_RANGE_TABLE: Optional[dict] = None


def _ranges() -> dict:
    """`coord_scale.json`'s `ranges`, loaded once and memoised."""
    global _RANGE_TABLE
    if _RANGE_TABLE is None:
        _RANGE_TABLE = json.loads(_COORD_SCALE_PATH.read_text())["ranges"]
    return _RANGE_TABLE


def range_for(level: int, parcel_class: str, division_state: str = "normal") -> int:
    """The coordinate range (divisor) of one (level, parcel_class,
    division_state) frame, from `coord_scale.json`'s `ranges`.

    This is the frame's divisor, not an observed maximum. For any divided
    sub-parcel (`division_state != "normal"`, e.g. "pardiv1_sub0") this
    always returns **4096** -- the parent frame's range -- never the
    smaller value `coord_scale.json` records as that sub's *observed*
    maximum (2048 for `pardiv1_sub0`, because a sub-parcel's coordinates
    live in the parent's 4096 frame and the SW quadrant only occupies its
    lower half). Dividing a coordinate by an observed maximum instead of
    the frame's actual range is the defect this function exists to
    prevent. Every other division state (L0 urban/sparse normal, every
    other level's full normal) returns `coord_scale.json`'s recorded max,
    which already equals the frame's true range for those classes.

    Raises `KeyError` if the (level, parcel_class, division_state) triple
    is absent from `coord_scale.json` -- never falls back to a default.
    """
    table = _ranges()
    try:
        entry = table[str(level)][parcel_class][division_state]
    except KeyError as exc:
        raise KeyError(
            f"no coord_scale.json range for (level={level}, "
            f"parcel_class={parcel_class!r}, division_state={division_state!r})"
        ) from exc
    if division_state != "normal":
        return _SLOT_RANGE
    return int(entry["max"])


def xy_to_latlon(xc: int, yc: int, bounds: BoundingBox, *,
                  coord_range: int = _LEGACY_RANGE) -> tuple[float, float]:
    lon = bounds.lon_lo + (xc / coord_range) * (bounds.lon_hi - bounds.lon_lo)
    lat = bounds.lat_lo + (yc / coord_range) * (bounds.lat_hi - bounds.lat_lo)
    return lat, lon


def decode_region_coord(raw: int) -> int:
    """Combine the 13-bit value + 3-bit region field used throughout the
    road/background/name shape encodings (`extract(v,0,12) + region*4096`).
    Not range-dependent: the 4096-per-region packing is unchanged by
    `range_for` (only the *validity bound* of the combined value is)."""
    from .bitutils import extract

    region = extract(raw, 13, 15)
    value = extract(raw, 0, 12)
    return value + region * 4096


def encode_region_coord(xc: int, *, coord_range: int = _LEGACY_RANGE) -> int:
    """Inverse of decode_region_coord: encode a parcel-local pixel coordinate
    to the raw 16-bit word form used throughout the road/background/name
    shape encodings.

    Uses region = xc // 4096, value = xc % 4096 (value always in 0..4095,
    12 bits) -- this packing is unchanged by `coord_range`. What
    `coord_range` changes is the validity bound: the admissible interval
    is `0 <= xc <= coord_range` **inclusive** (not `coord_range - 1`) --
    R's own census shows `share_at_max = 1.0` and `observed_peak == max`
    in nearly every class, and a boundary node sits exactly on the frame
    edge. `encode_region_coord(4096, coord_range=4096)` is region 1, value
    0, and is legal.

    Note: the real disc may use different (but equally valid) raw values
    for some coordinates -- this encoder will produce different bytes than
    the original but decodes to the same pixel coordinate.
    """
    if not 0 <= xc <= coord_range:
        raise ValueError(f"pixel coordinate {xc} out of range 0..{coord_range}")
    region = xc // 4096
    value = xc % 4096
    return value | (region << 13)


def latlon_to_xy(lat: float, lon: float, bounds: BoundingBox, *,
                  coord_range: int = _LEGACY_RANGE) -> tuple[int, int]:
    """Inverse of xy_to_latlon: convert geographic coordinates to
    parcel-local pixel coordinates.

    The result is rounded to the nearest integer pixel.  When called with
    a (lat, lon) that xy_to_latlon() produced from integer (xc, yc), the
    round-trip is exact (the floating-point cancellation is clean and
    round() absorbs any residual epsilon).
    """
    xc = int(round(
        (lon - bounds.lon_lo) / (bounds.lon_hi - bounds.lon_lo) * coord_range
    ))
    yc = int(round(
        (lat - bounds.lat_lo) / (bounds.lat_hi - bounds.lat_lo) * coord_range
    ))
    return xc, yc
