"""`shape` and `mht29` checks: the LMR/BSMR/BMT-shape half of "Profile
envelope", and the record-29 copy-through frame, from
`docs/design/target-disc.md`'s check table / `docs/plans/.../PLAN.md`'s
acceptance criteria.

Shape means *dimensions and coverage* from `grid.json` -- block-set/block/
parcel counts, cell sizes, coverage box -- not which blocks are actually
occupied on `G` (that is a `pointers`/`decode` question, not a shape one).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness import walk
from harness.context import Check, CheckResult
from kiwiw.grid import ReferenceGrid

COORD_TOL = 1e-9
NO_DATA_DSA = 0xFFFFFFFF


def _coverage_close(a: dict, b: dict) -> list[str]:
    diffs = []
    for k in ("lat_lo", "lat_hi", "lon_lo", "lon_hi"):
        av, bv = a[k], b[k]
        if abs(av - bv) > COORD_TOL:
            diffs.append(f"coverage.{k}: generated={av!r} reference={bv!r}")
    return diffs


def _lmr_field_diffs(g_lmr, ref_lmr: dict) -> list[str]:
    diffs = []
    level = g_lmr.level
    simple_fields = [
        "n_blocksets_lat", "n_blocksets_lng", "n_blocks_lat", "n_blocks_lng",
        "n_basic_map", "n_ext_map", "n_basic_route", "n_ext_route",
        "node_record_size",
    ]
    for f in simple_fields:
        gv, rv = getattr(g_lmr, f), ref_lmr[f]
        if gv != rv:
            diffs.append(f"level {level}: {f} generated={gv!r} reference={rv!r}")
    for f in ("n_parcels_lat", "n_parcels_lng"):
        gv, rv = getattr(g_lmr, f), ref_lmr[f]
        if list(gv) != list(rv):
            diffs.append(f"level {level}: {f} generated={gv!r} reference={rv!r}")
    for f in ("road_frame_table", "background_frame_table", "name_frame_table"):
        gv, rv = getattr(g_lmr, f) or [], ref_lmr.get(f) or []
        if len(gv) != len(rv):
            diffs.append(f"level {level}: len({f}) generated={len(gv)} reference={len(rv)}")
    return diffs


def _run_shape(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})

    container = walk.read_container(ctx.generated)
    pdmdh = container.pdmdh
    grid = ReferenceGrid.load()
    ref = grid.data

    diffs: list[str] = []

    diffs += [f"pdmdh.{d}" for d in _coverage_close(
        {"lat_lo": pdmdh.coverage.lat_lo, "lat_hi": pdmdh.coverage.lat_hi,
         "lon_lo": pdmdh.coverage.lon_lo, "lon_hi": pdmdh.coverage.lon_hi}, ref["coverage"])]
    diffs += [f"volume_header.{d}" for d in _coverage_close(
        {"lat_lo": container.hdr.coverage.lat_lo, "lat_hi": container.hdr.coverage.lat_hi,
         "lon_lo": container.hdr.coverage.lon_lo, "lon_hi": container.hdr.coverage.lon_hi},
        ref["coverage"])]

    if pdmdh.lmr_size != ref["pdmdh"]["lmr_size"]:
        diffs.append(f"pdmdh.lmr_size generated={pdmdh.lmr_size} reference={ref['pdmdh']['lmr_size']}")
    if pdmdh.n_bsmr != ref["pdmdh"]["n_bsmr"]:
        diffs.append(f"pdmdh.n_bsmr generated={pdmdh.n_bsmr} reference={ref['pdmdh']['n_bsmr']}")

    g_levels = [lmr.level for lmr in pdmdh.levels]
    ref_levels = [lvl["level"] for lvl in ref["levels"]]
    if g_levels != ref_levels:
        diffs.append(f"level list/order generated={g_levels} reference={ref_levels}")
    else:
        ref_by_level = {lvl["level"]: lvl for lvl in ref["levels"]}
        for g_lmr in pdmdh.levels:
            ref_lmr = ref_by_level.get(g_lmr.level)
            if ref_lmr is None:
                diffs.append(f"level {g_lmr.level}: no reference LMR")
                continue
            diffs += _lmr_field_diffs(g_lmr, ref_lmr)

            g_bs_count = sum(1 for b in pdmdh.blocksets if b.level == g_lmr.level)
            ref_bs_count = sum(1 for b in ref["blocksets"] if b["level"] == g_lmr.level)
            if g_bs_count != ref_bs_count:
                diffs.append(f"level {g_lmr.level}: blockset count generated={g_bs_count} "
                             f"reference={ref_bs_count}")

    details = {"diffs": diffs}
    if diffs:
        return CheckResult("FAIL", f"{len(diffs)} shape difference(s) (showing up to 20)",
                            {"diffs": diffs[:20]})
    return CheckResult("PASS", "LMR/BSMR/BMT shape matches the reference grid", details)


def _run_mht29(ctx) -> CheckResult:
    container = walk.read_container(ctx.generated)
    entry = container.mht.entries[29]
    if entry.dsa == NO_DATA_DSA:
        if not ctx.layer_present("map"):
            return CheckResult("NA", "map layer not present and MHT entry 29 is the sentinel", {})
        return CheckResult("FAIL", "MHT entry 29 is the sentinel but the map layer is present", {})

    off = walk.volume.getsector(entry.dsa, container.hdr.sector_size, container.hdr.logical_sector_size)
    with open(ctx.generated, "rb") as fh:
        fh.seek(off)
        actual = fh.read(2048)

    grid = ReferenceGrid.load()
    expected = grid.mht29_frame_bytes()
    if actual != expected:
        first_diff = next((i for i in range(min(len(actual), len(expected)))
                            if actual[i] != expected[i]), min(len(actual), len(expected)))
        return CheckResult("FAIL", f"MHT entry 29 frame differs from reference at byte {first_diff}",
                            {"first_diff_offset": first_diff})
    return CheckResult("PASS", "MHT entry 29 frame is byte-identical to the reference", {})


CHECKS = [
    Check(id="mht29", layer="map",
          description="MHT entry 29's 2048-byte frame is byte-identical to the reference.",
          run=_run_mht29),
    Check(id="shape", layer="map",
          description="Per-level LMR/BSMR/BMT shape equals the reference's.",
          run=_run_shape),
]
