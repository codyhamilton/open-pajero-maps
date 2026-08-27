"""Ch. 6 Parcel Management Record: the small `[type][mapinfo array]`
record that a Block Management Table entry's `dsa` addresses, and which
recurses into itself for divided/integrated-parcel (`pardiv1..3`)
subdivision.

This is a from-scratch, *whole-record* generalization of the read path
already proven in `mesh.py`'s `locate_parcel()` -- that function only
walks the single slot chain leading to one queried coordinate. Here we
decode every slot at every level so a writer (`parcel_writer.py`) can
regenerate the entire per-block buffer, not just reproduce one query's
answer.

No raw/verbatim fallback is needed for this layer: a mapinfo slot is
exactly two plain integers (`dsa`, `size`) with no undecoded bits, and the
recursive structure itself is exactly what `mesh.py` already established
(and cross-validated at 99.9% against real disc data -- see the
2026-08-25 "Parcel-index bug" decision-log entry) for locating one leaf.
"""
from __future__ import annotations

from .bitutils import extract, sws, u16, u32
from .model import ParcelMapInfoEntry, ParcelMgmtRecord
from .volume import LevelMgmtRecord

NO_DATA_DSA = 0xFFFFFFFF
MAX_SUBPARCEL_DEPTH = 6


def _own_footprint_end(rec: ParcelMgmtRecord) -> int:
    """Byte offset just past `rec`'s own `[type][mapinfo array]`, not
    counting any subrecord's footprint."""
    return rec.offset + 4 + len(rec.entries) * 6


def _max_covered_end(rec: ParcelMgmtRecord) -> int:
    """Deepest byte offset reached anywhere in `rec`'s subrecord tree."""
    end = _own_footprint_end(rec)
    for entry in rec.entries:
        if entry.subrecord is not None:
            end = max(end, _max_covered_end(entry.subrecord))
    return end


def parse_parcel_mgmt_record(
    buf: bytes, lmr: LevelMgmtRecord, offset: int = 0, _depth: int = 0
) -> ParcelMgmtRecord:
    """Decode one Parcel Management Record at `offset` within `buf` (a
    Block's data, i.e. what a BMT entry's `dsa`/`size` addresses), and
    recursively decode every subparcel it references within the same
    buffer.

    Raises if the list-type field is ever nonzero (matches kiwiread.c's
    own assumption, `mesh.py`'s `locate_parcel()` treats this the same
    way) or if recursion exceeds `MAX_SUBPARCEL_DEPTH`.

    At the root call (`_depth == 0`), also captures whatever trailing
    bytes of `buf` lie past the deepest point this record's subrecord
    chain ever reaches, into `tail_raw` (see `ParcelMgmtRecord`'s
    docstring) -- confirmed, by directly porting kiwiread.c's own
    `showbmt()` loop condition (`if (!size) recurse; else leaf; if
    (add==NO_DATA_DSA) skip`), that the reference tool itself never reads
    past that same point either: this isn't a gap in this parser, real
    disc blocks are simply larger than the record structure addressed
    within them.
    """
    if _depth > MAX_SUBPARCEL_DEPTH:
        raise ValueError(
            f"Parcel Management Record recursion exceeded {MAX_SUBPARCEL_DEPTH} "
            f"levels at buffer offset {offset} -- likely a decode bug, not real data")

    p_type_raw = u16(buf, offset)
    lt = extract(p_type_raw, 0, 7)
    pt = extract(p_type_raw, 8, 9)
    if lt != 0:
        raise ValueError(
            f"Parcel Management Record at offset {offset}: list_type={lt}, "
            "expected 0 for every real record on this disc (per mesh.py/kiwiread.c)")

    gn_lat = 1 + lmr.n_parcels_lat[pt]
    gn_lng = 1 + lmr.n_parcels_lng[pt]
    k = gn_lat * gn_lng

    mapinfo_off = offset + 4
    entries: list[ParcelMapInfoEntry] = []
    for idx in range(k):
        eoff = mapinfo_off + idx * 6
        dsa = u32(buf, eoff)
        size = u16(buf, eoff + 4)
        subrecord = None
        if size == 0 and dsa != NO_DATA_DSA:
            sub_off = sws(dsa)
            subrecord = parse_parcel_mgmt_record(buf, lmr, sub_off, _depth + 1)
        entries.append(ParcelMapInfoEntry(dsa=dsa, size=size, subrecord=subrecord))

    header_gap_raw = bytes(buf[offset + 2 : offset + 4])
    rec = ParcelMgmtRecord(offset=offset, list_type=lt, parcel_type=pt,
                            header_gap_raw=header_gap_raw, entries=entries)
    if _depth == 0:
        tail_start = _max_covered_end(rec)
        rec.tail_raw = bytes(buf[tail_start:])
    return rec
