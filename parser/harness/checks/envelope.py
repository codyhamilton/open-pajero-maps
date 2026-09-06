"""`envelope` check: "Profile envelope" from `docs/design/target-disc.md`'s
check table -- "`G`'s size and count distributions fall inside a stated
envelope around `R`'s (default 0.5x-2x on counts, <= `R`'s observed maximum
on any per-parcel or per-record size). Level 0 road counts are exempt from
the count envelope and bounded by size and capacity instead." Also reports
the map-layer byte total and the capacity projection against the 4.7 GB
budget ("Capacity" in the same table)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness.context import Check, CheckResult
from harness.profile import generated_profile

CAPACITY_BUDGET_BYTES = 4_700_000_000

# (label, path-to-count-within-one-level's-profile-entry)
_COUNT_FIELDS = [
    ("parcel_count", None),  # special-cased: sum of parcel_count_by_type
    ("link_count", ("road", "link_count")),
    ("background_count", ("background", "shape_count")),
    ("name_count", ("name", "record_count")),
]

_SUBFRAME_MAX_FIELDS = ["road", "background", "name"]


def _get(d: dict, path) -> int:
    node = d
    for p in path:
        node = node.get(p, {}) if isinstance(node, dict) else {}
    return node if isinstance(node, (int, float)) else 0


def _parcel_count(level_data: dict) -> int:
    return sum(level_data.get("parcel_count_by_type", {}).values())


def _run_envelope(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})

    ref_profile = ctx.profile("map")
    if not ref_profile:
        return CheckResult("NA", "no reference profile available (unit 03b not landed yet)", {})

    g_profile = generated_profile(ctx.generated)

    lo, hi = ctx.config.get("envelopes", {}).get("count_ratio", [0.5, 2.0])
    level0_exempt = bool(ctx.config.get("level0_count_exempt", False))

    ref_levels = ref_profile.get("levels", {})
    g_levels = g_profile.get("levels", {})

    count_report: dict = {}
    fails: list = []

    for level_str, g_level_data in g_levels.items():
        ref_level_data = ref_levels.get(level_str)
        if ref_level_data is None:
            fails.append(f"level {level_str}: no reference profile data for this level")
            continue

        level_report: dict = {}
        for field_name, path in _COUNT_FIELDS:
            g_count = _parcel_count(g_level_data) if path is None else _get(g_level_data, path)
            ref_count = _parcel_count(ref_level_data) if path is None else _get(ref_level_data, path)
            ratio = (g_count / ref_count) if ref_count else (0.0 if g_count == 0 else float("inf"))
            exempt = level0_exempt and level_str == "0" and field_name == "link_count"
            in_range = (lo * ref_count <= g_count <= hi * ref_count) if ref_count else (g_count == 0)
            level_report[field_name] = {
                "generated": g_count, "reference": ref_count, "ratio": ratio,
                "exempt": exempt, "in_range": in_range,
            }
            if not exempt and not in_range:
                fails.append(
                    f"level {level_str}: {field_name} generated={g_count} reference={ref_count} "
                    f"ratio={ratio:.3f} outside [{lo}, {hi}]")

        # Map Frame size <= reference's per-level max.
        g_max = g_level_data.get("mapframe_size", {}).get("max", 0)
        ref_max = ref_level_data.get("mapframe_size", {}).get("max", 0)
        level_report["mapframe_max"] = {"generated": g_max, "reference": ref_max}
        if g_max > ref_max:
            fails.append(
                f"level {level_str}: Map Frame max size generated={g_max} exceeds "
                f"reference max={ref_max}")

        # Every road/background/name sub-frame <= reference's per-level max.
        g_kind_max = g_level_data.get("frame_kind_max_bytes", {})
        ref_kind_max = ref_level_data.get("frame_kind_max_bytes", {})
        for kind in _SUBFRAME_MAX_FIELDS:
            g_v = g_kind_max.get(kind, 0)
            ref_v = ref_kind_max.get(kind, 0)
            level_report[f"{kind}_subframe_max"] = {"generated": g_v, "reference": ref_v}
            if g_v > ref_v:
                fails.append(
                    f"level {level_str}: {kind} sub-frame max size generated={g_v} exceeds "
                    f"reference max={ref_v}")

        count_report[level_str] = level_report

    # --- capacity projection ---
    g_map_bytes = g_profile.get("byte_totals_by_layer", {}).get("map", {}).get("total_bytes", 0)
    ref_other = ref_profile.get("byte_totals_by_layer", {}).get("other_mht_entries", {})
    non_map_bytes = sum(v for v in ref_other.values() if isinstance(v, (int, float)))
    projected_total = g_map_bytes + non_map_bytes
    over_budget = projected_total > CAPACITY_BUDGET_BYTES

    details = {
        "counts": count_report,
        "capacity_projection": {
            "generated_map_bytes": g_map_bytes,
            "reference_non_map_bytes": non_map_bytes,
            "projected_total_bytes": projected_total,
            "budget_bytes": CAPACITY_BUDGET_BYTES,
            "over_budget": over_budget,
        },
    }

    if over_budget:
        fails.append(
            f"capacity projection {projected_total} exceeds the {CAPACITY_BUDGET_BYTES} budget "
            f"-- the level-0 trade-off (drop minor ways vs exceed budget) must be made explicitly, "
            f"not silently"
        )

    if fails:
        return CheckResult("FAIL", f"{len(fails)} envelope failure(s) (showing up to 20)",
                            {**details, "failures": fails[:20]})
    return CheckResult(
        "PASS",
        f"counts within [{lo}, {hi}]x of R; sizes <= R's per-level max; "
        f"capacity projection {projected_total} <= {CAPACITY_BUDGET_BYTES}",
        details,
    )


CHECKS = [
    Check(
        id="envelope", layer="map",
        description=(
            "G's per-level parcel/link/background/name counts fall within the "
            "configured ratio of R's (level 0 link count exempt); every Map Frame "
            "and road/background/name sub-frame is <= R's per-level max; reports "
            "the capacity projection against the 4.7 GB budget."
        ),
        run=_run_envelope,
    ),
]
