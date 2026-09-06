"""`decode` and `pointers` checks: "Decodes clean" and "Pointers resolve"
from `docs/design/target-disc.md`'s check table."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness import walk
from harness.context import Check, CheckResult
from kiwiw.bitutils import sws, u16, u32
from kiwiw.parcel import decode_map_frame_header

NO_DATA_DSA = 0xFFFFFFFF
DEFAULT_MFDE_ABSENT = [0xFFFFFFFF, 0]
POISON_BYTE = 0xA5
POISON_RUN_MIN = 32
MAPFRAME_HEADER_SIZE = 36


# ---------------------------------------------------------------------
# decode: every structure in G is parsed with zero errors.
# ---------------------------------------------------------------------

def _run_decode(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})

    summary = ctx.walk_summary(ctx.generated)
    n_errors = summary.block_error_count + summary.leaf_error_count
    total_leaves = sum(summary.per_level_leaf_counts.values())
    details = {
        "per_level_parcel_counts": summary.per_level_leaf_counts,
        "per_level_type_counts": summary.per_level_type_counts,
        "block_error_count": summary.block_error_count,
        "leaf_error_count": summary.leaf_error_count,
        "first_errors": summary.errors,
    }
    if n_errors:
        return CheckResult(
            "FAIL",
            f"{n_errors} decode error(s) ({summary.block_error_count} block, "
            f"{summary.leaf_error_count} leaf) across {total_leaves} decoded leaves",
            details,
        )
    return CheckResult("PASS", f"{total_leaves} leaves decoded with zero errors", details)


# ---------------------------------------------------------------------
# pointers: every offset/sector/index pointer lands inside its target
# table or buffer, or (mfde >= 3) carries the censused absent-slot value
# or a valid in-file sector; no 0xA5 poison run inside a parcel buffer's
# declared extent that isn't inside a sub-frame.
# ---------------------------------------------------------------------

def _mfde_absent_value(ctx) -> list:
    profile = ctx.profile("map")
    if profile:
        absent = profile.get("mfde", {}).get("absent")
        if absent is not None:
            return list(absent)
    return list(DEFAULT_MFDE_ABSENT)


def _covered_ranges(de_off: int, mfde_raw: list, frame_size: int) -> list[tuple[int, int]]:
    """Byte ranges of a parcel buffer that belong to a known sub-frame
    (header, region list, mfde table itself, and every mfde entry whose
    offset resolves inside the buffer) -- mirrors exactly the coverage
    `kiwiw.parcel.decode_parcel()` computes for its own `tail_raw`."""
    header_end = MAPFRAME_HEADER_SIZE
    mfde_end = de_off + len(mfde_raw) * 6
    ranges = [(0, header_end), (header_end, de_off), (de_off, mfde_end)]
    for raw_off, raw_size in mfde_raw:
        if raw_off == NO_DATA_DSA:
            continue
        off = sws(raw_off)
        size = sws(raw_size)
        if size and off < frame_size:
            ranges.append((off, min(off + size, frame_size)))
    return ranges


def _raw_mfde_table(buf: bytes, n_basic_map: int, n_ext_map: int):
    """Parse a leaf Map Frame's mfde (offset, size) table directly from its
    raw buffer -- independent of `kiwiw.parcel.decode_parcel()`'s own
    sub-frame decode, which can itself raise when a pointer is corrupted
    (that is exactly the failure this check exists to catch, so it must
    not depend on that decode having succeeded). Mirrors `decode_parcel()`'s
    own table-length derivation exactly. Returns `(mfde_raw, de_off)`, or
    `None` if even the 36-byte header can't be read."""
    if len(buf) < MAPFRAME_HEADER_SIZE:
        return None
    try:
        header = decode_map_frame_header(buf)
    except Exception:
        return None
    de_off = MAPFRAME_HEADER_SIZE + header.nregion * 4

    def _read_entry(i: int) -> tuple[int, int]:
        eoff = de_off + i * 6
        if eoff + 6 > len(buf):
            return (NO_DATA_DSA, 0)
        return u32(buf, eoff), u16(buf, eoff + 4)

    basic_raw = [_read_entry(i) for i in range(3)]
    local_starts = []
    for raw_off, _raw_size in basic_raw:
        if raw_off != NO_DATA_DSA:
            off_v = sws(raw_off)
            if off_v < len(buf):
                local_starts.append(off_v)
    if local_starts:
        table_end = min(local_starts)
        total_entries = max((table_end - de_off) // 6, n_basic_map)
    else:
        total_entries = n_basic_map + n_ext_map
    mfde_raw = [_read_entry(i) for i in range(total_entries)]
    return mfde_raw, de_off


def _poison_run_found(buf: bytes, covered: list[tuple[int, int]]) -> int | None:
    """Return the start offset of the first run of >= POISON_RUN_MIN
    0xA5 bytes lying outside every covered range, or None."""
    covered_sorted = sorted(covered)
    n = len(buf)
    i = 0
    while i < n:
        if buf[i] != POISON_BYTE:
            i += 1
            continue
        run_start = i
        while i < n and buf[i] == POISON_BYTE:
            i += 1
        run_end = i  # exclusive
        if run_end - run_start < POISON_RUN_MIN:
            continue
        # does this run overlap any covered range? Only flag the
        # sub-range of the run that lies outside every covered range.
        pos = run_start
        while pos < run_end:
            in_cover = False
            for c_start, c_end in covered_sorted:
                if c_start <= pos < c_end:
                    in_cover = True
                    pos = c_end
                    break
            if in_cover:
                continue
            # find how far the free stretch extends before the next cover
            next_cover_start = run_end
            for c_start, c_end in covered_sorted:
                if pos < c_start < next_cover_start:
                    next_cover_start = c_start
            free_end = min(run_end, next_cover_start)
            if free_end - pos >= POISON_RUN_MIN:
                return pos
            pos = free_end if free_end > pos else pos + 1
    return None


def _check_mfde_entry(idx: int, raw_off: int, raw_size: int, frame_size: int,
                       file_size: int, sector_sz: int, logical_sz: int,
                       absent: list) -> str | None:
    """Return an error string, or None if the entry is fine."""
    from kiwiw.volume import getsector

    if idx < 3:
        if raw_off == NO_DATA_DSA:
            return None
        size_v = sws(raw_size)
        if size_v == 0:
            return None
        off_v = sws(raw_off)
        if off_v + size_v > frame_size:
            return f"mfde[{idx}] offset {off_v}+{size_v} exceeds frame size {frame_size}"
        return None

    # entries >= 3
    if [raw_off, raw_size] == list(absent) or (raw_off, raw_size) == tuple(absent):
        return None
    off_v = sws(raw_off) if raw_off != NO_DATA_DSA else raw_off
    size_v = sws(raw_size) if raw_size != NO_DATA_DSA else raw_size
    if raw_off != NO_DATA_DSA and off_v < frame_size:
        # in-buffer: must resolve inside the buffer
        if off_v + size_v > frame_size:
            return f"mfde[{idx}] in-buffer offset {off_v}+{size_v} exceeds frame size {frame_size}"
        return None
    # out-of-buffer: must decode to a sector inside the file
    sector_off = getsector(raw_off, sector_sz, logical_sz)
    if not (0 <= sector_off < file_size):
        return (f"mfde[{idx}] out-of-buffer sector {sector_off} outside file "
                f"(size {file_size})")
    return None


def _run_pointers(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})

    path = ctx.generated
    container = walk.read_container(path)
    hdr = container.hdr
    sector_sz, logical_sz = hdr.sector_size, hdr.logical_sector_size
    file_size = container.file_size
    absent = _mfde_absent_value(ctx)

    fails: list[dict] = []

    # --- BMT entries: offset+length inside the file --------------------
    for table in container.pdmdh.bmt_tables:
        for entry_index, bmt_entry in enumerate(table.entries):
            if bmt_entry.dsa == NO_DATA_DSA or not bmt_entry.size:
                continue
            off = walk.volume.getsector(bmt_entry.dsa, sector_sz, logical_sz)
            length = bmt_entry.size * logical_sz
            if off + length > file_size:
                fails.append({
                    "kind": "bmt", "table_ordinal": table.blockset_ordinal,
                    "entry_index": entry_index,
                    "detail": f"block at {off}+{length} exceeds file size {file_size}",
                })
                if len(fails) >= 20:
                    break
        if len(fails) >= 20:
            break

    lmr_by_level = {lmr.level: lmr for lmr in container.pdmdh.levels}

    # --- mapinfo leaf entries + mfde table + poison, via a full walk ---
    # The mfde table and buffer are re-parsed directly from raw bytes here
    # (not taken from `wp.parcel.frame`): `decode_parcel()` can itself
    # raise when a leaf's mfde offset is corrupted (it dereferences the
    # sub-frame the offset points at), and that is exactly the failure
    # this check exists to catch -- so it must not depend on that decode
    # having succeeded. Only a block-level parse failure (no leaf at all)
    # is left to the `decode` check.
    with open(path, "rb") as fh:
        for wp in walk.iter_parcels(path):
            if len(fails) >= 20:
                break
            if wp.leaf_path == ():
                continue  # block-level parse failure -- decode check's job
            if wp.file_offset + wp.length > file_size:
                fails.append({
                    "kind": "mapinfo", "level": wp.level,
                    "blockset_index": wp.blockset_index, "block_index": wp.block_index,
                    "leaf_path": list(wp.leaf_path),
                    "detail": f"leaf at {wp.file_offset}+{wp.length} exceeds file size {file_size}",
                })
                continue

            fh.seek(wp.file_offset)
            buf = fh.read(wp.length)
            lmr = lmr_by_level.get(wp.level)
            n_basic_map = lmr.n_basic_map if lmr is not None else 3
            n_ext_map = lmr.n_ext_map if lmr is not None else 0
            table = _raw_mfde_table(buf, n_basic_map, n_ext_map)
            if table is None:
                fails.append({
                    "kind": "mfde", "level": wp.level,
                    "blockset_index": wp.blockset_index, "block_index": wp.block_index,
                    "leaf_path": list(wp.leaf_path),
                    "detail": "could not parse Map Frame header/mfde table from raw buffer",
                })
                continue
            mfde_raw, de_off = table
            frame_size = len(buf)
            for idx, (raw_off, raw_size) in enumerate(mfde_raw):
                err = _check_mfde_entry(idx, raw_off, raw_size, frame_size,
                                         file_size, sector_sz, logical_sz, absent)
                if err:
                    fails.append({
                        "kind": "mfde", "level": wp.level,
                        "blockset_index": wp.blockset_index, "block_index": wp.block_index,
                        "leaf_path": list(wp.leaf_path), "detail": err,
                    })
                    break

            # poison scan against the same raw buffer.
            covered = _covered_ranges(de_off, mfde_raw, frame_size)
            poison_at = _poison_run_found(buf, covered)
            if poison_at is not None:
                fails.append({
                    "kind": "poison", "level": wp.level,
                    "blockset_index": wp.blockset_index, "block_index": wp.block_index,
                    "leaf_path": list(wp.leaf_path),
                    "detail": f"0xA5 poison run >= {POISON_RUN_MIN} bytes at buffer offset {poison_at}",
                })

    if fails:
        return CheckResult("FAIL", f"{len(fails)} pointer/poison failure(s) (showing up to 20)",
                            {"failures": fails})
    return CheckResult("PASS", "every BMT/mapinfo/mfde pointer resolves; no poison leaks", {})


CHECKS = [
    Check(id="decode", layer="map", description="Every structure in G is parsed with zero errors.",
          run=_run_decode),
    Check(id="pointers", layer="map",
          description="Every offset/sector/index pointer in G lands inside its target table or buffer.",
          run=_run_pointers),
]
