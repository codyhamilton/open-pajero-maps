"""Whole-file `IDX/SADSR201.IDX` assembly tests (Phase 2, see
`roundtrip_idx_full.py` and docs/phases/02-roundtrip.md "Whole-file
IDX/*.IDX assembly"). This is materially different from
`test_roundtrip_idx.py`: that file validates individual structural pieces
against real bytes *at their own original byte range*; this file validates
a **from-scratch reassembly** -- every DFSR header, DSIR record slot, DCTF
definition frame, matching-record chain, and "Additional ***Address"
indirection entry is placed at a brand-new, freshly-computed offset, not
its original one.

Requires the real disc mounted at /run/media/codyh/464210-8480/ -- skips if
not present. Runs standalone with plain `python3` (no pytest dependency
required), and also under pytest.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiwiw.search_frame import parse_search_frame, sws32, _u32
from roundtrip_idx_full import (
    assemble,
    compare_decoded_trees,
    _verified_offsets,
)

ROOT = "/run/media/codyh/464210-8480"
SADSR = os.path.join(ROOT, "IDX", "SADSR201.IDX")


def _skip():
    if not os.path.exists(SADSR):
        print(f"SKIP: {SADSR} not present (disc not mounted)")
        return True
    return False


def _load():
    with open(SADSR, "rb") as fh:
        return fh.read()


def test_replicate_mode_whole_file_byte_identical():
    """The core deliverable: an allocator CONSTRAINED to reproduce the
    real disc's own layout choices (same order/offsets, derived from a
    zero-gap sequential-packing rule -- see roundtrip_idx_full.py's module
    docstring) produces a byte-identical whole file, proving we understand
    the disc's real allocation rule -- not just that individual pieces
    round-trip in place."""
    if _skip():
        return
    real = _load()
    report = []
    rebuilt = assemble(real, mode="replicate", include_trailing_tail=True, report=report)
    assert len(rebuilt) == len(real)
    assert rebuilt == real, "whole-file replicate-mode reassembly must be byte-identical to the real file"
    # At least the 3 large, fully-decoded-and-verified record populations
    # (street name search, nested city-selection search, address range)
    # must have round-tripped via genuine record-by-record reconstruction,
    # not a verbatim copy -- otherwise "byte-identical" would trivially
    # follow from copying bytes we never actually reassembled.
    verified = [orig for orig, status, _ in report if status == "verified"]
    assert len(verified) >= 3, f"expected >=3 verified (record-reconstructed) populations, got {report}"
    print(f"PASS: whole-file SADSR201.IDX replicate-mode reassembly byte-identical to real disc ({len(real)} bytes)")
    print(f"      {len(verified)} matching-record populations verified record-by-record: {verified}")


def test_fromscratch_mode_layout_genuinely_differs():
    """Guards against the from-scratch allocator secretly being the same
    as the replicate allocator (which would make the self-consistency
    proof below meaningless)."""
    if _skip():
        return
    real = _load()
    fromscratch = assemble(real, mode="fromscratch", include_trailing_tail=False)
    assert len(fromscratch) != len(real) or fromscratch != real[: len(fromscratch)]
    print("PASS: fromscratch-mode buffer's layout is provably different from the real file's")


def test_fromscratch_mode_decode_equivalent_to_original():
    """The other required proof: a from-scratch allocation (offsets that do
    NOT match the real disc) re-parsed by the existing read-side parser
    decodes to the SAME intermediate representation as the original file
    -- self-consistency via re-parse, not byte-identity."""
    if _skip():
        return
    real = _load()
    report = []
    assemble(real, mode="replicate", report=report)  # to learn which populations are decode-verifiable
    verified = _verified_offsets(report)
    fromscratch = assemble(real, mode="fromscratch", report=[])
    mismatches = compare_decoded_trees(real, fromscratch, 0, 0, verified)
    assert not mismatches, f"decode mismatches: {mismatches[:10]}"
    print("PASS: fromscratch-mode buffer re-parses to a decode-equivalent tree (self-consistency via re-parse)")


def test_negative_control_perturbed_source_field_is_detected():
    """Perturbing one real field before reassembly must make the
    from-scratch reassembly of the perturbed source decode DIFFERENTLY
    from the (unperturbed) original -- proves compare_decoded_trees() is
    actually discriminating, not vacuously passing everything."""
    if _skip():
        return
    real = _load()
    top = parse_search_frame(real, 0)[0]  # SRMX, street records
    base = top.matching_data_frame.file_offset
    # STID is one of the fixed-width fields decoded near the start of every
    # street record (same field the sibling test_roundtrip_idx.py negative
    # control perturbs) -- flip a bit a few bytes into the first record.
    corrupted = bytearray(real)
    flip_at = base + 4
    corrupted[flip_at] ^= 0x01
    corrupted = bytes(corrupted)

    report = []
    assemble(real, mode="replicate", report=report)
    verified = _verified_offsets(report)

    fromscratch_bad = assemble(corrupted, mode="fromscratch", report=[])
    mismatches = compare_decoded_trees(real, fromscratch_bad, 0, 0, verified)
    assert mismatches, "perturbed source field must produce a detectable decode mismatch"
    print(f"PASS: perturbed source field correctly detected as a decode mismatch ({mismatches[0]})")


def test_negative_control_corrupted_replicate_output_fails_byte_compare():
    """A trivial but important guard: the byte-identical assertion in
    test_replicate_mode_whole_file_byte_identical is not vacuous -- a
    corrupted rebuild must actually fail the comparison."""
    if _skip():
        return
    real = _load()
    rebuilt = bytearray(assemble(real, mode="replicate", include_trailing_tail=True))
    rebuilt[1000] ^= 0xFF
    assert bytes(rebuilt) != real, "corrupting one byte of the rebuild must break byte-identity"
    print("PASS: negative control -- corrupted replicate-mode output correctly fails byte comparison")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} tests run.")
