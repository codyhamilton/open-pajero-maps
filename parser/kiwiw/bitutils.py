"""Low-level byte/bitfield helpers, ported from kiwiread.c.

KIWI-W is big-endian throughout and uses two recurring integer encodings
that aren't plain fixed-width ints:

- ``SWS`` ("size-word-stored"?) / ``D`` ("delta"/offset): a 16-bit field
  that stores half the real value, except the sentinel 0xFFFF which means
  "no entity" and is left untouched. kiwiread.c defines both `D()` and
  `SWS()` identically -- we keep both names (as `sws`/`d`) for
  spec-traceability, since the spec's own field-type column uses both
  labels for what turns out to be the same encoding.
- geonum: a 3-byte big-endian value where bit 23 is a N/S or E/W sign flag
  and the low 23 bits are an angle in units of 1/8 arc-second.
"""
from __future__ import annotations

SENTINEL16 = 0xFFFF


def u8(buf: bytes, off: int) -> int:
    return buf[off]


def u16(buf: bytes, off: int) -> int:
    return (buf[off] << 8) | buf[off + 1]


def u24(buf: bytes, off: int) -> int:
    return (buf[off] << 16) | (buf[off + 1] << 8) | buf[off + 2]


def u32(buf: bytes, off: int) -> int:
    return (
        (buf[off] << 24)
        | (buf[off + 1] << 16)
        | (buf[off + 2] << 8)
        | buf[off + 3]
    )


def i8(buf: bytes, off: int) -> int:
    v = buf[off]
    return v - 256 if v >= 128 else v


def sws(v: int) -> int:
    """The `SWS`/`D` "stored-halved" 16-bit encoding: doubled unless it's
    the 0xFFFF "not present" sentinel."""
    if v != SENTINEL16:
        v <<= 1
    return v


# kiwiread.c names this the same operation twice (`D()` and `SWS()`); keep
# an alias so callers can match whichever name the spec table used for a
# given field.
d = sws


def extract(val: int, start: int, end: int) -> int:
    """Extract inclusive bitfield [start, end] (LSB = bit 0)."""
    mask = (1 << (end - start + 1)) - 1
    return (val >> start) & mask


def signex(val: int, start: int, end: int) -> int:
    """Like extract(), but sign-extends the result treating bit `end` as
    the sign bit."""
    mask = (1 << (end - start + 1)) - 1
    bits = (val >> start) & mask
    if bits & (1 << (end - start)):
        bits -= mask + 1
    return bits


def geo_secs(raw3: bytes) -> float:
    """Decode a 3-byte geonum field (1.2.7-ish "B:N" lat/lon angle) into
    signed decimal degrees. Bit 23 = sign flag (1 = negative /
    south-or-west), low 23 bits = angle in 1/8 arc-second units."""
    v = u24(raw3, 0)
    negative = bool(v & (1 << 23))
    secs = v & ~(1 << 23)
    degrees = secs / (3600.0 * 8)
    return -degrees if negative else degrees


def parcel_id_bounds(buf: bytes, off: int) -> tuple[float, float]:
    """Decode a `pid_t` (1.2.13 Parcel ID: 3-byte lat, 1-byte exp, 3-byte
    lng, 1-byte exp) at `off`, returning (lat_deg, lon_deg). The exponent
    bytes are not decoded here (kiwiread.c doesn't use them for the main
    map frame; flagged as unconfirmed in docs)."""
    lat = geo_secs(buf[off : off + 3])
    lng = geo_secs(buf[off + 4 : off + 7])
    return lat, lng
