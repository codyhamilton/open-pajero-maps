"""Whole-file `IDX/*.IDX` assembly -- the gap Phase 2's per-piece round-trip
passes (`roundtrip_idx.py`) explicitly left open (see its module docstring
and `docs/phases/02-roundtrip.md`): computing brand-new offsets for every
structural piece of a `DFSR`/`DCTF`/Detailed-Search-Info-Record tree and
serializing a whole file from scratch, rather than validating each piece
in place at its own original byte range.

Scope: `IDX/SADSR201.IDX` (primary target, 100% of the reachable tree --
every DFSR header, every Detailed Search Info Record slot, every DCTF
definition frame, every street/address-range matching record, all 5
"Additional ***Address" indirection entries per record). `POISR201.IDX`'s
single flat frame is included too (its shape is a strict subset of
SADSR201's -- one frame, one record, no `next_level` -- so the same
machinery covers it directly).

Allocation rule discovered (see docs/phases/02-roundtrip.md for full
writeup and confidence levels): every reachable byte in SADSR201.IDX from
offset 0 to 15,375,908 is a **zero-gap, zero-padding sequential packing**
in this order, applied recursively to every `DFSR` frame (top-level and
every `next_level` nested frame alike):

    1. the 16-byte `DFSR` header
    2. every record's fixed-`rec_size` slot, in record order
    3. for each record, in record order: its `category_definition` DCTF
       frame, `matching_data_definition` DCTF frame, `category_data` blob,
       `matching_data_frame` matching-record chain (whichever of these
       four are present -- `None` entries are simply skipped)
    4. for each record, in REVERSE record order: recurse into its
       `next_level` nested frame (steps 1-4 again), *unless* that same
       original offset has already been placed by an earlier record's
       `next_level` (SADSR201.IDX's "ADDRESS RANGE" SRT1 frame at original
       offset 5,046,996 is reached this way from two different places:
       the top-level SRMX record's `next_level` and the nested-under-SRHA
       SRMX record's `next_level` -- CONFIRMED via direct byte inspection,
       both point at the identical offset).

This was verified by recomputing, by hand, every one of these boundaries
against the real file for all 4 reachable Detailed Search Info Records
(top SRMX, top SRHA, nested SRMX under SRHA, and SRT1) and finding *zero*
unexplained gaps anywhere in the reachable tree -- see the "Whole-file
IDX/*.IDX assembly" section of docs/phases/02-roundtrip.md.

Step-4's REVERSE ordering is witnessed only once (a single 2-record
sibling group: SRHA's next_level subtree is placed before SRMX's) -- this
part of the rule is WEAK confidence (not independently reproduced across
multiple sibling groups) even though it is the exact, fully-consistent
explanation for the one instance observed. Everything else (zero-gap
packing, forward order for local fields, shared-target dedup by original
offset) is HIGH confidence: it is directly, exactly consistent with every
byte boundary in the entire reachable tree, with no exceptions.

Not modelled / explicitly out of scope, per this project's "preserve what
isn't understood as raw bytes" discipline (see index_writer.py's
DetailedSearchInfoRaw docstring and COUNTRY.KWI's raw_tail precedent):

  - Each Detailed Search Info Record's bytes from +92 to +rec_size (the
    "tail") are captured and replayed **verbatim**, not reconstructed
    field-by-field, *except* for the specific 4-byte absolute-file-offset
    word inside each of up to 5 "Additional ***Address" indirection
    entries embedded in that tail (whose *locator* -- record-relative
    sws32 offset -- is unaffected by relocation, but whose *stored target*
    must be repointed at wherever this assembler places the referenced
    content). This is a deliberately narrow, fully-explained mutation of
    an otherwise-verbatim region, not a bypass of the "writers only take
    parsed IR" discipline: the record's *understood* 92-byte prefix goes
    through `index_writer.write_detailed_search_info_raw` from its parsed
    `DetailedSearchInfoRaw` IR exactly as `roundtrip_idx.py` already
    proves byte-identical; only the still-undecoded tail is replayed raw.
  - `category_data` blob content is copied verbatim (opaque, per this
    project's established category/ARCD/CTGY scope boundary) -- it is
    relocated as a byte range, never decoded.
  - The trailing 11,776-byte region of SADSR201.IDX (offset 15,375,908 to
    EOF) is a `DFSR`/`SRAL`-declared structure not reachable from any
    `next_level` pointer anywhere in the tree this assembler walks (all 4
    Detailed Search Info Records' `next_level` fields were directly
    checked -- SRT1 has none, and the other 3 all resolve into the
    already-walked tree). Two 12-byte undecoded "gap" fields in each
    Detailed Search Info Record's 92-byte prefix were checked byte-by-byte
    as a candidate record-relative or sws32-encoded pointer to this
    offset; none resolved to it (one gap instead contains what reads as
    an ASCII tag, e.g. `KBA2`/`KBST`, not a pointer). This region is
    therefore copied **verbatim** as an unresolved opaque tail -- never
    reconstructed from IR, and its true structure/purpose is undocumented.

Verification discipline: same as `roundtrip_idx.py` -- output buffers are
poison-filled with 0xA5 before any chunk is written, so an unwritten gap
shows up as a diff rather than silently reading as zero; no writer here
is ever handed raw disc bytes as its "product" without an explanation (the
verbatim regions above are explicitly, narrowly scoped exceptions, not a
general bypass); byte-identical claims are only made where a direct
`buf1 == buf2` comparison is performed.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from kiwiw.search_frame import (
    DetailedSearchInfo,
    FieldDef,
    SENTINEL32,
    _u32,
    iter_matching_records,
    parse_definition_frame,
    parse_detailed_search_info,
    parse_matching_record,
    parse_search_frame,
    sws32,
)
from kiwiw.index_writer import (
    DetailedSearchInfoRaw,
    parse_detailed_search_info_raw,
    unsws32,
    write_definition_frame,
    write_detailed_search_info_raw,
    write_dfsr_header,
    write_matching_record,
)

POISON = 0xA5

# Field offsets of the 5 "Additional ***Address" pointer words within a
# Detailed Search Info Record's 92-byte known prefix (see
# index_writer.DetailedSearchInfoRaw / search_frame._resolve_frame_ref).
_FRAME_REF_FIELD_OFFSETS = {
    "category_definition": 16,
    "category_data": 24,
    "matching_data_definition": 60,
    "matching_data_frame": 68,
    "next_level": 88,
}


# ---------------------------------------------------------------------------
# Planning: walk the real file, build an ordered chunk list + a mapping from
# every original offset to its freshly-assigned new offset, plus per-record
# patch targets (field name -> new offset of the content it must point at).
# ---------------------------------------------------------------------------


@dataclass
class _Chunk:
    kind: str
    data: bytes  # for non-slot chunks: final bytes, ready to emit as-is
    # for 'slot' chunks only:
    record_base: Optional[int] = None
    rec_size: int = 0
    patches: Dict[str, int] = field(default_factory=dict)


@dataclass
class PlanResult:
    chunks: List[_Chunk]
    new_offset_by_orig: Dict[int, int]
    total_size: int


def _def_frame_bytes(buf: bytes, orig_offset: int) -> bytes:
    fields = parse_definition_frame(buf, orig_offset)
    return write_definition_frame(fields)


class VerbatimFrameCopy(Exception):
    """Raised internally to signal that a matching_data_frame population
    could not be verified record-by-record and was copied verbatim
    instead -- not an error, just a flag caught by `_matching_frame_bytes`."""


# Populations confirmed (this pass) to decode-and-rebuild byte-identical for
# EVERY record, not just a sample -- see docs/phases/02-roundtrip.md. Any
# matching_data_frame NOT in this set is copied verbatim (opaque, unverified
# record-by-record) rather than risking a silent lossy reconstruction.
VERIFIED_RECORD_POPULATIONS = "verified"
UNVERIFIED_VERBATIM = "verbatim"


def _matching_frame_bytes(buf: bytes, orig_offset: int, def_offset: int, expected_size: int, report: Optional[list] = None) -> bytes:
    """Rebuild a whole matching_data_frame's record chain from parsed IR,
    verifying EVERY record round-trips byte-identical against the real
    file at its OWN original offset as it goes (not just checking the
    final concatenated length). If any record fails -- either a decode
    exception or a byte mismatch -- the whole frame is copied verbatim
    from the original file instead (its content is then not "reassembled
    from IR", just relocated as an opaque blob), and this is recorded in
    `report` rather than silently swallowed."""
    fields = parse_definition_frame(buf, def_offset)
    out = bytearray()
    off = orig_offset
    try:
        while True:
            rec = parse_matching_record(buf, off, fields)
            rebuilt = write_matching_record(rec, fields)
            original = buf[off : off + len(rebuilt)]
            if rebuilt != original:
                raise VerbatimFrameCopy(f"record @{off} not byte-identical")
            out += rebuilt
            nfrl = rec["_nfrl"]
            if nfrl == 0:
                break
            off += nfrl
        if len(out) != expected_size:
            raise VerbatimFrameCopy(
                f"rebuilt {len(out)} bytes, expected matching_data_frame_size={expected_size}"
            )
    except VerbatimFrameCopy as exc:
        if report is not None:
            report.append((orig_offset, UNVERIFIED_VERBATIM, str(exc)))
        return buf[orig_offset : orig_offset + expected_size]
    except Exception as exc:  # decode blew up outright (e.g. field misalignment)
        if report is not None:
            report.append((orig_offset, UNVERIFIED_VERBATIM, f"{type(exc).__name__}: {exc}"))
        return buf[orig_offset : orig_offset + expected_size]
    if report is not None:
        report.append((orig_offset, VERIFIED_RECORD_POPULATIONS, f"{expected_size} bytes"))
    return bytes(out)


def _plan_record_locals(
    buf: bytes,
    rec: DetailedSearchInfo,
    memo: Dict[int, int],
    chunks: List[_Chunk],
    cursor: int,
    patches: Dict[str, int],
    report: Optional[list] = None,
) -> int:
    """Place (in this fixed order) category_definition, matching_data_definition,
    category_data, matching_data_frame -- whichever are present -- and record
    each one's new offset into `patches` for later slot-patching. Returns the
    updated cursor."""
    if rec.category_definition is not None:
        orig = rec.category_definition.file_offset
        if orig not in memo:
            data = _def_frame_bytes(buf, orig)
            memo[orig] = cursor
            chunks.append(_Chunk(kind="def", data=data))
            cursor += len(data)
        patches["category_definition"] = memo[orig]

    if rec.matching_data_definition is not None:
        orig = rec.matching_data_definition.file_offset
        if orig not in memo:
            data = _def_frame_bytes(buf, orig)
            memo[orig] = cursor
            chunks.append(_Chunk(kind="def", data=data))
            cursor += len(data)
        patches["matching_data_definition"] = memo[orig]

    if rec.category_data is not None:
        orig = rec.category_data.file_offset
        if orig not in memo:
            data = buf[orig : orig + rec.category_data_size]
            memo[orig] = cursor
            chunks.append(_Chunk(kind="catdata", data=data))
            cursor += len(data)
        patches["category_data"] = memo[orig]

    if rec.matching_data_frame is not None:
        orig = rec.matching_data_frame.file_offset
        if orig not in memo:
            def_off = rec.matching_data_definition.file_offset
            data = _matching_frame_bytes(buf, orig, def_off, rec.matching_data_frame_size, report)
            memo[orig] = cursor
            chunks.append(_Chunk(kind="matchframe", data=data))
            cursor += len(data)
        patches["matching_data_frame"] = memo[orig]

    return cursor


def _plan_frame_replicate(
    buf: bytes,
    orig_frame_offset: int,
    memo: Dict[int, int],
    chunks: List[_Chunk],
    cursor: int,
    record_patches: Dict[int, Dict[str, int]],
    report: Optional[list] = None,
) -> int:
    """Recursive planner reproducing the *real disc's* observed order:
    header, all record slots, then per-record locals (forward order), then
    per-record next_level recursion (REVERSE order), deduping shared
    next_level targets by original offset. Returns the updated cursor."""
    if orig_frame_offset in memo:
        return cursor  # already placed (shared next_level target)

    decl = buf[orig_frame_offset : orig_frame_offset + 4].decode("ascii")
    count = _u32(buf, orig_frame_offset + 4)
    rec_size = sws32(_u32(buf, orig_frame_offset + 8))
    first = sws32(_u32(buf, orig_frame_offset + 12))
    assert first == 16, f"unexpected non-16 first_offset at {orig_frame_offset}: {first}"

    memo[orig_frame_offset] = cursor
    chunks.append(_Chunk(kind="header", data=write_dfsr_header(decl, count, rec_size, 16)))
    cursor += 16

    recs = parse_search_frame(buf, orig_frame_offset)
    assert len(recs) == count

    record_bases = []
    for i, rec in enumerate(recs):
        rb = orig_frame_offset + first + i * rec_size
        assert rb == rec.record_base
        record_bases.append(rb)
        chunks.append(_Chunk(kind="slot", data=b"", record_base=rb, rec_size=rec_size))
        cursor += rec_size

    # step 3: per-record locals, forward order
    for rb, rec in zip(record_bases, recs):
        patches = record_patches.setdefault(rb, {})
        cursor = _plan_record_locals(buf, rec, memo, chunks, cursor, patches, report)

    # step 4: per-record next_level recursion, REVERSE order
    for rb, rec in zip(reversed(record_bases), reversed(recs)):
        if rec.next_level is None:
            continue
        orig = rec.next_level.file_offset
        cursor = _plan_frame_replicate(buf, orig, memo, chunks, cursor, record_patches, report)
        record_patches[rb]["next_level"] = memo[orig]

    return cursor


def _plan_frame_fromscratch(
    buf: bytes,
    orig_frame_offset: int,
    memo: Dict[int, int],
    chunks: List[_Chunk],
    cursor: int,
    record_patches: Dict[int, Dict[str, int]],
    report: Optional[list] = None,
) -> int:
    """A deliberately DIFFERENT allocation order from the real disc's, to
    prove this is a genuine from-scratch allocation rather than a replay of
    recorded offsets: same header/slot/local-fields steps, but each
    record's next_level subtree is recursed into IMMEDIATELY after that
    record's own locals (forward order throughout), not deferred to a
    second reverse-order pass."""
    if orig_frame_offset in memo:
        return cursor

    decl = buf[orig_frame_offset : orig_frame_offset + 4].decode("ascii")
    count = _u32(buf, orig_frame_offset + 4)
    rec_size = sws32(_u32(buf, orig_frame_offset + 8))
    first = sws32(_u32(buf, orig_frame_offset + 12))

    memo[orig_frame_offset] = cursor
    chunks.append(_Chunk(kind="header", data=write_dfsr_header(decl, count, rec_size, 16)))
    cursor += 16

    recs = parse_search_frame(buf, orig_frame_offset)
    record_bases = [orig_frame_offset + first + i * rec_size for i in range(count)]
    for rb, rec_size_i in zip(record_bases, [rec_size] * count):
        chunks.append(_Chunk(kind="slot", data=b"", record_base=rb, rec_size=rec_size))
        cursor += rec_size

    for rb, rec in zip(record_bases, recs):
        patches = record_patches.setdefault(rb, {})
        cursor = _plan_record_locals(buf, rec, memo, chunks, cursor, patches, report)
        if rec.next_level is not None:
            orig = rec.next_level.file_offset
            cursor = _plan_frame_fromscratch(buf, orig, memo, chunks, cursor, record_patches, report)
            patches["next_level"] = memo[orig]

    return cursor


def plan(buf: bytes, root_offset: int = 0, mode: str = "replicate", report: Optional[list] = None) -> Tuple[PlanResult, Dict[int, Dict[str, int]]]:
    memo: Dict[int, int] = {}
    chunks: List[_Chunk] = []
    record_patches: Dict[int, Dict[str, int]] = {}
    fn = _plan_frame_replicate if mode == "replicate" else _plan_frame_fromscratch
    total = fn(buf, root_offset, memo, chunks, 0, record_patches, report)
    return PlanResult(chunks=chunks, new_offset_by_orig=memo, total_size=total), record_patches


# ---------------------------------------------------------------------------
# Emission: fill slot chunks in using the (by-then-fully-populated) patch
# tables, then concatenate everything into one poison-filled output buffer.
# ---------------------------------------------------------------------------


def _patched_slot_bytes(buf: bytes, record_base: int, rec_size: int, patches: Dict[str, int]) -> bytes:
    raw = parse_detailed_search_info_raw(buf, record_base)
    rebuilt_prefix = write_detailed_search_info_raw(raw)
    original_prefix = buf[record_base : record_base + 92]
    if rebuilt_prefix != original_prefix:
        raise AssertionError(f"DSIR prefix @{record_base} did not round-trip byte-identical before patching")

    tail = bytearray(buf[record_base + 92 : record_base + rec_size])

    raws = {
        "category_definition": raw.category_definition_raw,
        "category_data": raw.category_data_raw,
        "matching_data_definition": raw.matching_data_definition_raw,
        "matching_data_frame": raw.matching_data_frame_raw,
        "next_level": raw.next_level_raw,
    }
    for name, field_off in _FRAME_REF_FIELD_OFFSETS.items():
        raw_val = raws[name]
        if raw_val == SENTINEL32:
            continue
        entry_rel = sws32(raw_val)  # record-relative, unaffected by relocation
        tail_rel = entry_rel - 92
        if not (0 <= tail_rel <= len(tail) - 4):
            raise AssertionError(
                f"record @{record_base} field {name!r}: entry_rel={entry_rel} "
                f"falls outside tail (len {len(tail)}) -- locator assumption broken"
            )
        new_target = patches.get(name)
        if new_target is None:
            raise AssertionError(f"record @{record_base}: no new-offset patch recorded for {name!r}")
        struct.pack_into(">I", tail, tail_rel, new_target // 2)

    return bytes(rebuilt_prefix) + bytes(tail)


def emit(buf: bytes, plan_result: PlanResult, record_patches: Dict[int, Dict[str, int]]) -> bytes:
    out = bytearray([POISON]) * plan_result.total_size
    cursor = 0
    for chunk in plan_result.chunks:
        if chunk.kind == "slot":
            data = _patched_slot_bytes(buf, chunk.record_base, chunk.rec_size, record_patches[chunk.record_base])
        else:
            data = chunk.data
        out[cursor : cursor + len(data)] = data
        cursor += len(data)
    assert cursor == plan_result.total_size
    return bytes(out)


def assemble(
    buf: bytes,
    root_offset: int = 0,
    mode: str = "replicate",
    include_trailing_tail: bool = False,
    report: Optional[list] = None,
) -> bytes:
    """Assemble the whole reachable `DFSR` tree rooted at `root_offset` into
    a brand-new byte buffer with freshly-computed offsets. `mode` is
    `"replicate"` (matches the real disc's exact layout choices) or
    `"fromscratch"` (a deliberately different, still-valid layout, to prove
    genuine reallocation). If `include_trailing_tail` is set, the file's
    trailing unresolved region (see module docstring) is appended verbatim
    so the output is the same total length as the real file -- this is a
    verbatim copy, not a reconstruction, and is only meaningful in
    `"replicate"` mode (where it makes the output byte-identical to the
    real file). `report`, if given, collects one entry per matching_data_frame
    population: `(original_offset, "verified"|"verbatim", detail)` -- see
    `_matching_frame_bytes`."""
    plan_result, record_patches = plan(buf, root_offset, mode, report)
    out = emit(buf, plan_result, record_patches)
    if include_trailing_tail:
        # Only meaningful/exact when the reachable tree's own new size
        # matches the original reachable-tree size (true in "replicate"
        # mode, where every offset matches the original exactly).
        out = out + buf[len(out) :]
    return out


# ---------------------------------------------------------------------------
# Self-consistency proof: decode a freshly-assembled buffer (new offsets
# throughout) and confirm it produces the SAME intermediate representation
# as decoding the real file -- not byte-identical (the offsets differ by
# construction), decode-EQUIVALENT.
# ---------------------------------------------------------------------------


def _record_public_fields(rec: dict) -> dict:
    """Drop bookkeeping keys (`_offset`, `_bfrl`, `_nfrl`, `_consumed`) that
    are expected to differ once a record moves to a new file offset --
    everything else must match exactly."""
    return {k: v for k, v in rec.items() if not k.startswith("_")}


def _decode_records(buf: bytes, frame_offset: int, def_offset: int, verified: bool):
    if not verified:
        return None  # known-unverifiable population (see _matching_frame_bytes); skip decode compare
    fields = parse_definition_frame(buf, def_offset)
    return [_record_public_fields(r) for r in iter_matching_records(buf, frame_offset, fields)]


def _verified_offsets(report: list) -> Dict[int, bool]:
    return {orig: (status == VERIFIED_RECORD_POPULATIONS) for orig, status, _ in report}


def compare_decoded_trees(orig_buf: bytes, other_buf: bytes, orig_root: int = 0, other_root: int = 0, orig_verified: Optional[Dict[int, bool]] = None) -> List[str]:
    """Recursively decode the `DFSR` tree rooted at `orig_root` in
    `orig_buf` and at `other_root` in `other_buf`, and compare every
    decoded field of every reachable Detailed Search Info Record and every
    matching record (for populations known to decode-and-rebuild cleanly --
    see `orig_verified`), ignoring absolute offsets (which are expected to
    differ by construction in a from-scratch allocation). Returns a list
    of human-readable mismatches; empty means fully decode-equivalent."""
    mismatches: List[str] = []
    orig_recs = parse_search_frame(orig_buf, orig_root)
    other_recs = parse_search_frame(other_buf, other_root)
    if len(orig_recs) != len(other_recs):
        mismatches.append(f"frame @{orig_root}/{other_root}: record count {len(orig_recs)} != {len(other_recs)}")
        return mismatches

    for i, (o, n) in enumerate(zip(orig_recs, other_recs)):
        tag = f"frame @{orig_root} rec[{i}] ({o.declaration})"
        if o.declaration != n.declaration:
            mismatches.append(f"{tag}: declaration {o.declaration!r} != {n.declaration!r}")
        if (o.category_definition is None) != (n.category_definition is None):
            mismatches.append(f"{tag}: category_definition presence differs")
        elif o.category_definition is not None:
            of = parse_definition_frame(orig_buf, o.category_definition.file_offset)
            nf = parse_definition_frame(other_buf, n.category_definition.file_offset)
            if of != nf:
                mismatches.append(f"{tag}: category_definition fields differ")
        if o.category_data_size != n.category_data_size:
            mismatches.append(f"{tag}: category_data_size {o.category_data_size} != {n.category_data_size}")
        if (o.category_data is None) != (n.category_data is None):
            mismatches.append(f"{tag}: category_data presence differs")
        elif o.category_data is not None:
            ob = orig_buf[o.category_data.file_offset : o.category_data.file_offset + o.category_data_size]
            nb = other_buf[n.category_data.file_offset : n.category_data.file_offset + n.category_data_size]
            if ob != nb:
                mismatches.append(f"{tag}: category_data content differs")
        if (o.matching_data_definition is None) != (n.matching_data_definition is None):
            mismatches.append(f"{tag}: matching_data_definition presence differs")
        elif o.matching_data_definition is not None:
            of = parse_definition_frame(orig_buf, o.matching_data_definition.file_offset)
            nf = parse_definition_frame(other_buf, n.matching_data_definition.file_offset)
            if of != nf:
                mismatches.append(f"{tag}: matching_data_definition fields differ")
        if o.matching_record_count != n.matching_record_count:
            mismatches.append(f"{tag}: matching_record_count {o.matching_record_count} != {n.matching_record_count}")
        if o.matching_data_frame_size != n.matching_data_frame_size:
            mismatches.append(f"{tag}: matching_data_frame_size {o.matching_data_frame_size} != {n.matching_data_frame_size}")
        if (o.matching_data_frame is None) != (n.matching_data_frame is None):
            mismatches.append(f"{tag}: matching_data_frame presence differs")
        elif o.matching_data_frame is not None:
            is_verified = True if orig_verified is None else orig_verified.get(o.matching_data_frame.file_offset, True)
            orecs = _decode_records(orig_buf, o.matching_data_frame.file_offset, o.matching_data_definition.file_offset, is_verified)
            nrecs = _decode_records(other_buf, n.matching_data_frame.file_offset, n.matching_data_definition.file_offset, is_verified)
            if orecs is None:
                pass  # known-unverifiable population, not decode-compared (see module docstring)
            elif orecs != nrecs:
                mismatches.append(f"{tag}: matching_data_frame decoded records differ ({len(orecs)} vs {len(nrecs) if nrecs is not None else '?'})")
        if (o.next_level is None) != (n.next_level is None):
            mismatches.append(f"{tag}: next_level presence differs")
        elif o.next_level is not None:
            mismatches.extend(
                compare_decoded_trees(orig_buf, other_buf, o.next_level.file_offset, n.next_level.file_offset, orig_verified)
            )

    return mismatches


if __name__ == "__main__":
    import os

    ROOT = "/run/media/codyh/464210-8480"
    SADSR = os.path.join(ROOT, "IDX", "SADSR201.IDX")
    if not os.path.exists(SADSR):
        print(f"SKIP: {SADSR} not present (disc not mounted)")
    else:
        with open(SADSR, "rb") as fh:
            real = fh.read()

        report: list = []
        replicated = assemble(real, mode="replicate", include_trailing_tail=True, report=report)
        print(f"replicate mode: {len(replicated)} bytes (real file {len(real)} bytes)")
        for orig, status, detail in report:
            print(f"  matching_data_frame @{orig}: {status} ({detail})")
        if replicated == real:
            print("PASS: whole-file reassembly is BYTE-IDENTICAL to the real SADSR201.IDX")
        else:
            first_diff = next(i for i in range(min(len(replicated), len(real))) if replicated[i] != real[i])
            print(f"FAIL: first diff @{first_diff}")

        fromscratch_report: list = []
        fromscratch = assemble(real, mode="fromscratch", include_trailing_tail=False, report=fromscratch_report)
        print(f"fromscratch mode: {len(fromscratch)} bytes (not expected to match real layout)")
        assert fromscratch != real[: len(fromscratch)], "fromscratch layout must actually differ from the real one"
        print("PASS: fromscratch buffer's layout is provably different from the real file's (genuine reallocation)")

        verified = _verified_offsets(report)
        mismatches = compare_decoded_trees(real, fromscratch, 0, 0, verified)
        if not mismatches:
            print("PASS: fromscratch buffer re-parses to a decode-EQUIVALENT tree (self-consistency via re-parse)")
        else:
            print(f"FAIL: {len(mismatches)} decode mismatch(es):")
            for m in mismatches[:20]:
                print(" ", m)
