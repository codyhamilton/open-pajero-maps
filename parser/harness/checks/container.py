"""`container` check: "Container byte-diff" from
`docs/design/target-disc.md`'s check table -- a generated disc's Data
Volume header, Management Header Table, PDMDH (with every LMR, BSMR and
Block Management Table) and the record-29 copy-through frame may differ
from the reference only in a named, allowlisted set of fields (build
stamp / data version / disk title strings, sizes, sector addresses).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness import bytediff, walk
from harness.context import Check, CheckResult
from harness.checks.shape import bmt_key_diffs, bmt_keys
from kiwiw.volume import BMT_SIZE, DATAVOL_SIZE, MHT_SIZE

NO_DATA_DSA = 0xFFFFFFFF
RECORD29_FRAME_SIZE = 2048
MAX_VIOLATIONS_REPORTED = 50


def _allow_sets(config: dict) -> dict[str, set[str]]:
    allow: dict[str, set[str]] = {"volume_header": set(), "mht": set(), "pdmdh": set()}
    for entry in config.get("container_allowlist", []):
        region = entry.get("region")
        field = entry.get("field")
        if region in allow and field:
            allow[region].add(field)
    return allow


def _read_bytes(path: str, offset: int, length: int) -> bytes:
    with open(path, "rb") as fh:
        fh.seek(offset)
        return fh.read(length)


def _bmt_explains_length(r_pdmdh, g_pdmdh, allow_pdmdh: set[str]) -> bool:
    """True when a PDMDH length difference is *entirely* a consequence of
    allowlisted per-build fields: `record_size` and `bsmr_bmt_size` are
    both allowlisted, the fixed prefix (header + LMR table + BSMR table,
    i.e. everything before the first Block Management Table) is the same
    length in R and G, and the record-size difference equals the
    difference in total BMT bytes. Block Management Tables are emitted
    only for blocksets that hold content, so a build whose geographic
    content coverage differs from R's legitimately has a different number
    of them (unit 27)."""
    if not {"record_size", "bsmr_bmt_size"} <= allow_pdmdh:
        return False
    def prefix(p):
        return min((t.offset for t in p.bmt_tables), default=p.record_size)
    def bmt_total(p):
        return sum(len(t.entries) for t in p.bmt_tables) * BMT_SIZE
    if prefix(r_pdmdh) != prefix(g_pdmdh):
        return False
    return (r_pdmdh.record_size == prefix(r_pdmdh) + bmt_total(r_pdmdh)
            and g_pdmdh.record_size == prefix(g_pdmdh) + bmt_total(g_pdmdh))


def _pdmdh_common(r_raw: bytes, g_raw: bytes,
                   bmt_explained: bool = False) -> tuple[bytes, bytes, dict | None]:
    """Trim both PDMDH blobs to their common length for the field-level
    diff below, and separately report a length mismatch as a violation
    unless the longer blob's extra tail is entirely zero (i.e. the only
    difference is how much trailing sector padding got attached)."""
    if len(r_raw) == len(g_raw):
        return r_raw, g_raw, None
    common = min(len(r_raw), len(g_raw))
    longer = r_raw if len(r_raw) > len(g_raw) else g_raw
    extra = longer[common:]
    if bmt_explained or all(b == 0 for b in extra):
        return r_raw[:common], g_raw[:common], None
    return r_raw[:common], g_raw[:common], {
        "region": "pdmdh", "field": "pdmdh_length", "offset": common, "length": len(extra),
        "r_bytes": "", "g_bytes": "",
        "detail": (f"PDMDH blob length differs (reference={len(r_raw)} "
                   f"generated={len(g_raw)}) and the extra {len(extra)} byte(s) are not "
                   f"all zero"),
    }


def _summarize(region: str, diffs: list, allowed_counts: dict, violations: list) -> None:
    for d in diffs:
        if d.classification == "allowed":
            key = f"{region}.{d.field}"
            allowed_counts[key] = allowed_counts.get(key, 0) + 1
        else:
            violations.append({
                "region": region, "field": d.field, "offset": d.start,
                "length": d.end - d.start,
                "r_bytes": d.r_bytes.hex(), "g_bytes": d.g_bytes.hex(),
            })


def _run_container(ctx) -> CheckResult:
    if ctx.reference is None:
        return CheckResult("NA", "--reference was not given", {})

    r_container = walk.read_container(ctx.reference)
    g_container = walk.read_container(ctx.generated)
    allow = _allow_sets(ctx.config)

    allowed_counts: dict[str, int] = {}
    violations: list[dict] = []

    # --- Data Volume header (Ch. 5.1) ------------------------------------
    r_hdr_raw = _read_bytes(ctx.reference, 0, DATAVOL_SIZE)
    g_hdr_raw = _read_bytes(ctx.generated, 0, DATAVOL_SIZE)
    fields = bytediff.field_map("volume_header", r_container.extras)
    diffs = bytediff.diff_regions(r_hdr_raw, g_hdr_raw, fields, allow["volume_header"])
    _summarize("volume_header", diffs, allowed_counts, violations)

    # --- Management Header Table (Ch. 5.2) -------------------------------
    r_mht_raw = _read_bytes(ctx.reference, DATAVOL_SIZE, MHT_SIZE)
    g_mht_raw = _read_bytes(ctx.generated, DATAVOL_SIZE, MHT_SIZE)
    fields = bytediff.field_map("mht", r_container.mht)
    diffs = bytediff.diff_regions(r_mht_raw, g_mht_raw, fields, allow["mht"])
    _summarize("mht", diffs, allowed_counts, violations)

    # --- PDMDH, with every LMR / BSMR / Block Management Table -----------
    r_pdmdh_raw = _read_bytes(ctx.reference, r_container.prdm_offset,
                               r_container.pdmdh.total_size)
    g_pdmdh_raw = _read_bytes(ctx.generated, g_container.prdm_offset,
                               g_container.pdmdh.total_size)
    r_trim, g_trim, length_violation = _pdmdh_common(
        r_pdmdh_raw, g_pdmdh_raw,
        _bmt_explains_length(r_container.pdmdh, g_container.pdmdh, allow["pdmdh"]))
    if length_violation:
        violations.append(length_violation)
    # Length equality (or an allowlisted length difference) does not prove
    # the tables line up: compare BMT tables by (level, blockset) key.
    for d in bmt_key_diffs(bmt_keys(r_container.pdmdh), g_container.pdmdh, r_container.pdmdh):
        violations.append({"region": "pdmdh", "field": "bmt_table", "offset": 0,
                           "length": 0, "r_bytes": "", "g_bytes": "", "detail": d})
    fields = bytediff.field_map("pdmdh", r_container.pdmdh)
    diffs = bytediff.diff_regions(r_trim, g_trim, fields, allow["pdmdh"])
    _summarize("pdmdh", diffs, allowed_counts, violations)

    # --- record-29 copy-through frame (language/country code list) -------
    r_entry = r_container.mht.entries[29]
    g_entry = g_container.mht.entries[29]
    if r_entry.dsa != NO_DATA_DSA and g_entry.dsa != NO_DATA_DSA:
        r_off = walk.volume.getsector(r_entry.dsa, r_container.hdr.sector_size,
                                       r_container.hdr.logical_sector_size)
        g_off = walk.volume.getsector(g_entry.dsa, g_container.hdr.sector_size,
                                       g_container.hdr.logical_sector_size)
        r_frame = _read_bytes(ctx.reference, r_off, RECORD29_FRAME_SIZE)
        g_frame = _read_bytes(ctx.generated, g_off, RECORD29_FRAME_SIZE)
        if r_frame != g_frame:
            first_diff = next(
                (i for i in range(min(len(r_frame), len(g_frame))) if r_frame[i] != g_frame[i]),
                min(len(r_frame), len(g_frame)))
            violations.append({
                "region": "record29", "field": "record29_frame", "offset": first_diff,
                "length": RECORD29_FRAME_SIZE - first_diff,
                "r_bytes": r_frame[first_diff:].hex(), "g_bytes": g_frame[first_diff:].hex(),
            })

    details = {
        "allowed_counts": allowed_counts,
        "violation_count": len(violations),
        "violations": violations[:MAX_VIOLATIONS_REPORTED],
    }
    if violations:
        return CheckResult(
            "FAIL",
            f"{len(violations)} unallowlisted byte difference(s) "
            f"(showing up to {MAX_VIOLATIONS_REPORTED})",
            details,
        )
    return CheckResult(
        "PASS",
        f"every container-layer byte differs only in the allowlist "
        f"({sum(allowed_counts.values())} allowed diff(s))",
        details,
    )


CHECKS = [
    Check(id="container", layer="map",
          description="Header/MHT/PDMDH (LMR/BSMR/BMT)/record-29 frame differ from the "
                       "reference only in allowlisted fields.",
          run=_run_container),
]
