"""Background-shape encoder: inverse of background.decode_background_frame()
at the individual-BackgroundShape level.

Uses a 'copy-and-patch' strategy mirroring road_writer.py: starts with
raw_bytes (the verbatim on-disc bytes captured by
background.decode_background_frame()), then overwrites only the fields that
background.py decoded semantically:

  - sx/sy (bytes 8-9 and 10-11 within the shape record): the starting
    parcel-local pixel coordinate, re-encoded from the first entry of
    shape.coords via latlon_to_xy() + encode_region_coord().  Only
    patched when shape_class != 0 (point shapes have no coords decoded).

All other bytes are preserved verbatim from raw_bytes:
  - hdr word (bytes 0-1): rec_len + undecoded header bits
  - flag word (bytes 2-3): ncoord + undecoded bits
  - code word (bytes 4-5): type_code (already verbatim -- we could
    reconstruct it from BackgroundShape.type_code, but preserving is
    simpler and equally correct)
  - addl word (bytes 6-7): mult_const exponent + underground + pen_up +
    undecoded bits
  - delta coordinate pairs (bytes 12..): signed i8 deltas applied
    cumulatively to the starting coordinate; because
    decode_region_coord(encode_region_coord(xc)) == xc exactly, the
    decoded starting xc/yc is identical to the original, so the stored
    deltas continue to decode correctly without modification.
  - any trailing name/auxdata bytes: rec_len accounts for them; they are
    inside raw_bytes and pass through unchanged.
"""
from __future__ import annotations

from .coordconv import encode_region_coord, latlon_to_xy
from .model import BackgroundShape, BoundingBox


def encode_background_shape(shape: BackgroundShape, bounds: BoundingBox) -> bytes:
    """Re-encode a decoded BackgroundShape to bytes that
    background.decode_background_frame() would parse back to an equivalent
    BackgroundShape.

    Parameters
    ----------
    shape:
        A BackgroundShape decoded by background.decode_background_frame().
        Must have ``raw_bytes`` set (always the case for shapes decoded from
        real disc data).
    bounds:
        The parcel's bounding box, required to convert shape.coords[0] from
        (lat, lon) back to parcel-local pixel coordinates for the sx/sy
        re-encoding.

    Returns
    -------
    bytes
        A byte string the same length as shape.raw_bytes that decodes to a
        BackgroundShape with the same semantic fields as the input.
        For shape_class == 0 (point) the bytes are byte-identical to the
        original (no coords were decoded to re-encode).  For shape_class
        != 0, sx/sy may differ from the original when the disc used an
        alternative (non-canonical) raw encoding; all decoded fields are
        still exact.
    """
    raw = shape.raw_bytes
    if not raw:
        raise ValueError(
            "BackgroundShape.raw_bytes is empty -- encode_background_shape() "
            "requires raw_bytes captured by background.decode_background_frame()"
        )

    buf = bytearray(raw)

    # For shape_class != 0, the decoder decoded sx/sy (bytes 8-9, 10-11)
    # as the starting parcel-local pixel coordinate and appended the
    # corresponding (lat, lon) as shape.coords[0].  Re-encode from there.
    if shape.shape_class != 0 and shape.coords:
        lat0, lon0 = shape.coords[0]
        xc, yc = latlon_to_xy(lat0, lon0, bounds)
        sx = encode_region_coord(xc)
        sy = encode_region_coord(yc)
        buf[8]  = (sx >> 8) & 0xFF
        buf[9]  = sx & 0xFF
        buf[10] = (sy >> 8) & 0xFF
        buf[11] = sy & 0xFF

    return bytes(buf)
