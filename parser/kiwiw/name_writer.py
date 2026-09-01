"""Name-record encoder: inverse of name.decode_name_frame() at the
individual-NameRecord level for string_type == 4 (Linear-B).

Uses a 'copy-and-patch' strategy mirroring road_writer.py: starts with
raw_bytes (the verbatim on-disc bytes captured by
name.decode_name_frame()), then overwrites only the fields that name.py
decoded semantically for string_type == 4:

  - attr1 word (bytes 2-3 of the record): rebuilt from priority (bits
    0:5), vertical (bit 6), string_type (bits 8:10), and
    display_scale_flag (bits 11:15); bit 7 is preserved verbatim from
    raw_bytes (name.py never decoded it).
  - attr2 word (bytes 4-5): re-encoded from NameRecord.type_code.

For string_type != 4, raw_bytes is returned unchanged -- name.py does not
decode the string content or coordinates for those types in a way this
encoder could safely reconstruct, and the record boundary (from na) is
still reliable so raw_bytes is complete and correct.

The record content beyond attr1/attr2 (the `na` header word at bytes 0-1,
the `xc0` placement word and undecoded follower word at body offsets 0-3,
the orientation/distance placement records, the string length word, and the
raw string bytes) are all preserved verbatim from raw_bytes.  Because the
string is stored already encoded on disc and _cstr() decodes it by slicing
then null-stripping, the round-trip is: decode → store text → preserve
raw_bytes string region → re-decode same text.  No re-encoding of the
string bytes is needed.
"""
from __future__ import annotations

from .model import NameRecord


def encode_name_record(record: NameRecord) -> bytes:
    """Re-encode a decoded NameRecord to bytes that
    name.decode_name_frame() would parse back to an equivalent NameRecord.

    For string_type == 4 (Linear-B), attr1 and attr2 are re-assembled from
    the decoded semantic fields; all other bytes come verbatim from
    raw_bytes.  For all other string_types, raw_bytes is returned unchanged.

    Parameters
    ----------
    record:
        A NameRecord decoded by name.decode_name_frame().  Must have
        ``raw_bytes`` set (always the case for records decoded from real
        disc data when name.py could determine the record length via `na`).

    Returns
    -------
    bytes
        A byte string the same length as record.raw_bytes that decodes to a
        NameRecord with the same semantic fields as the input.
    """
    raw = record.raw_bytes
    if not raw:
        raise ValueError(
            "NameRecord.raw_bytes is empty -- encode_name_record() requires "
            "raw_bytes captured by name.decode_name_frame()"
        )

    if record.string_type != 4:
        # For unhandled types the full record content is opaque; raw_bytes
        # is the authoritative source.
        return bytes(raw)

    buf = bytearray(raw)

    # attr1 at record-relative bytes 2-3.
    # Decoded fields:
    #   bits  0: 5  = priority
    #   bit   6     = vertical
    #   bit   7     = undecoded; preserved verbatim
    #   bits  8:10  = string_type
    #   bits 11:15  = display_scale_flag
    attr1_raw = (raw[2] << 8) | raw[3]
    bit7 = (attr1_raw >> 7) & 1  # undecoded; carry verbatim

    attr1_new = (
        (record.priority & 0x3F)
        | (int(record.vertical) << 6)
        | (bit7 << 7)
        | ((record.string_type & 0x7) << 8)
        | ((record.display_scale_flag & 0x1F) << 11)
    )
    buf[2] = (attr1_new >> 8) & 0xFF
    buf[3] = attr1_new & 0xFF

    # attr2 at record-relative bytes 4-5: directly the type_code word.
    buf[4] = (record.type_code >> 8) & 0xFF
    buf[5] = record.type_code & 0xFF

    return bytes(buf)
