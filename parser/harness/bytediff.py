"""Byte-level diff engine for the `container` check: maps named fields (in
the same offset coordinate system `kiwiw/volume.py`'s decoders use) onto
byte ranges of the volume header / MHT / PDMDH regions, and classifies
every byte range that actually differs between a reference (`R`) and
generated (`G`) buffer as `allowed` (named in the harness config's
`container_allowlist`) or `violation`.

`kiwiw/volume.py` decodes these regions from inline literal offsets rather
than named constants (its docstring cites the spec's field table directly,
which is the right call for a decoder read against a fixed spec) -- so the
field boundaries below are re-derived here, read-only, rather than adding
constants to that module (this brief's owned paths do not include
`kiwiw/volume.py`).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.volume import (
    BSMR_SIZE,
    DATAVOL_SIZE,
    LMR_BASE_SIZE,
    MHR_SIZE,
    MHT_RECORD_COUNT,
    MHT_SIZE,
)

# ---------------------------------------------------------------------
# Ch. 5.1 Data Volume field boundaries -- every one of the 2048 bytes is
# named, following `volume.parse_volume_header`/`parse_volume_header_extras`
# offset-by-offset, so any violation there can be reported against a real
# field name rather than a bare offset.
# ---------------------------------------------------------------------
_VOLUME_HEADER_FIELDS: list[tuple[str, int, int]] = [
    ("system_specific_mid", 0, 12),
    ("system_specific_id", 12, 64),
    ("data_author_mid", 64, 76),
    ("data_author_id", 76, 128),
    ("system_mid", 128, 140),
    ("system_id", 140, 160),
    ("format_version", 160, 224),
    ("data_version", 224, 288),
    ("disk_title", 288, 416),
    ("contents_word0", 416, 418),
    ("contents_words_1_3", 418, 424),
    ("media_version", 424, 456),
    ("coverage_ll", 456, 464),
    ("coverage_ur", 464, 472),
    ("logical_sector_size", 472, 474),
    ("sector_size", 474, 476),
    ("background", 476, 478),
    ("reserved_478", 478, 492),
    ("level_mgmt_info", 492, 748),
    ("reserved_748", 748, DATAVOL_SIZE),
]

assert _VOLUME_HEADER_FIELDS[-1][2] == DATAVOL_SIZE


@dataclass
class Diff:
    field: str
    start: int
    end: int
    r_bytes: bytes
    g_bytes: bytes
    classification: str  # "allowed" | "violation"


def field_map(region: str, parsed) -> list[tuple[str, int, int]]:
    """`(name, start, end)` byte ranges for one region. `parsed` is the
    region's own decoded structure (`VolumeHeaderExtras` / `ManagementHeaderTable`
    / `Pdmdh` from `parse_pdmdh_full`) -- only `pdmdh` actually needs it, since
    the PDMDH's layout (LMR count/size, BSMR count, BMT entry counts) is
    data-dependent; the volume header and MHT are fixed layouts."""
    if region == "volume_header":
        return list(_VOLUME_HEADER_FIELDS)

    if region == "mht":
        fields: list[tuple[str, int, int]] = []
        for i in range(MHT_RECORD_COUNT):
            off = i * MHR_SIZE
            fields.append(("dsa", off, off + 4))
            fields.append(("size", off + 4, off + 6))
            fields.append(("name", off + 6, off + 18))
        tail_off = MHT_RECORD_COUNT * MHR_SIZE
        fields.append(("tail", tail_off, MHT_SIZE))
        return fields

    if region == "pdmdh":
        pdmdh = parsed
        fields = [
            ("record_size", 0, 2),
            ("header_gap", 2, 8),
            ("coverage", 8, 20),
            ("lmr_size", 20, 22),
            ("bsmr_size", 22, 24),
            ("bmr_size", 24, 26),
            ("n_lmr", 26, 28),
            ("n_bsmr", 28, 30),
        ]
        moff = 30
        for lmr in pdmdh.levels:
            lvl = lmr.level
            size = pdmdh.lmr_size
            fields.append((f"lmr[{lvl}].header", moff, moff + 2))
            fields.append((f"lmr[{lvl}].numbers", moff + 2, moff + 4))
            fields.append((f"lmr[{lvl}].dispflag", moff + 4, moff + 24))
            fields.append((f"lmr[{lvl}].block_counts", moff + 24, moff + 28))
            fields.append((f"lmr[{lvl}].parcel_counts", moff + 28, moff + 36))
            fields.append((f"lmr[{lvl}].bsmr_offset", moff + 36, moff + 38))
            fields.append((f"lmr[{lvl}].node_record_size", moff + 38, moff + 40))
            if size > LMR_BASE_SIZE:
                fields.append((f"lmr[{lvl}].tail", moff + LMR_BASE_SIZE, moff + size))
            moff += size

        for i, _bs in enumerate(pdmdh.blocksets):
            off = pdmdh.bsmr_table_offset + i * BSMR_SIZE
            fields.append((f"bsmr[{i}].header", off, off + 2))
            fields.append(("bsmr_bmt_offset", off + 2, off + 6))
            fields.append(("bsmr_bmt_size", off + 6, off + 10))

        entry_size = pdmdh.bmr_size * 2
        for table in pdmdh.bmt_tables or []:
            for i in range(len(table.entries)):
                off = table.offset + i * entry_size
                fields.append(("bmt_dsa", off, off + 4))
                fields.append(("bmt_size", off + 4, off + entry_size))

        fields.append(("trailing_padding", pdmdh.record_size, pdmdh.total_size))
        return fields

    raise ValueError(f"unknown region: {region!r}")


def nearest_field(offset: int, fields: list[tuple[str, int, int]]) -> str:
    """Best-effort field name for an `offset` not covered by any field range
    in `fields` (a gap between declared fields) -- the name of whichever
    field's range is closest to it."""
    best_name = "?"
    best_dist = None
    for name, start, end in fields:
        if start <= offset < end:
            return name
        dist = min(abs(offset - start), abs(offset - end))
        if best_dist is None or dist < best_dist:
            best_name, best_dist = name, dist
    return best_name


def diff_regions(r_bytes: bytes, g_bytes: bytes,
                  fields: list[tuple[str, int, int]], allow: set[str]) -> list[Diff]:
    """Compare `r_bytes` and `g_bytes` over every `fields` range plus any gap
    between them, and return one `Diff` per range that actually differs,
    classified `allowed` (its field name is in `allow`) or `violation`
    (gaps -- bytes no declared field covers -- are always `violation`,
    named via `nearest_field`)."""
    diffs: list[Diff] = []

    for name, start, end in sorted(fields, key=lambda f: (f[1], f[2])):
        rseg = r_bytes[start:end]
        gseg = g_bytes[start:end]
        if rseg == gseg:
            continue
        classification = "allowed" if name in allow else "violation"
        diffs.append(Diff(field=name, start=start, end=end,
                           r_bytes=rseg, g_bytes=gseg, classification=classification))

    length = max(len(r_bytes), len(g_bytes))
    covered = sorted((start, end) for _, start, end in fields)
    pos = 0
    gaps: list[tuple[int, int]] = []
    for start, end in covered:
        if start > pos:
            gaps.append((pos, start))
        pos = max(pos, end)
    if pos < length:
        gaps.append((pos, length))

    for gstart, gend in gaps:
        rseg = r_bytes[gstart:gend]
        gseg = g_bytes[gstart:gend]
        if rseg == gseg:
            continue
        diffs.append(Diff(field=f"gap~{nearest_field(gstart, fields)}", start=gstart, end=gend,
                           r_bytes=rseg, g_bytes=gseg, classification="violation"))

    return diffs
