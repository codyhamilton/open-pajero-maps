"""`mfde` check: the plan's acceptance bullet -- "the mfde entry count and
absent-slot encoding match the profile on every parcel" -- plus the
`nregion` half of the same census (`docs/plans/.../PLAN.md`'s "Refinement
findings": "`nregion` is 1 at levels 0-8 ... 0 at levels 10 and 12").

Per-parcel mfde detail is not retained anywhere (the census in
`harness/profile.py` is already an aggregate, streamed one leaf at a time),
so this check works off `harness.profile.build_profile()`'s per-level
aggregates for both `R` and `G`: every parcel having the same entry count as
the profile's shows up as `G`'s `entry_count_hist` containing exactly one
key (the profile's dominant/only value); likewise for `nregion`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness.context import Check, CheckResult
from harness.profile import generated_profile


def _dominant_key(hist: dict) -> str | None:
    if not hist:
        return None
    return max(hist.items(), key=lambda kv: kv[1])[0]


def _run_mfde(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})

    ref_profile = ctx.profile("map")
    if not ref_profile:
        return CheckResult("NA", "no reference profile available (unit 03b not landed yet)", {})

    g_profile = generated_profile(ctx.generated)

    ref_levels = ref_profile.get("levels", {})
    g_levels = g_profile.get("levels", {})
    ref_absent = ref_profile.get("mfde", {}).get("absent")

    fails: list = []
    details_by_level: dict = {}

    for level_str, g_level_data in g_levels.items():
        ref_level_data = ref_levels.get(level_str)
        if ref_level_data is None:
            fails.append(f"level {level_str}: no reference profile data for this level")
            continue

        level_detail: dict = {}

        # --- entry count: every parcel's count must equal R's for this level ---
        ref_entry_hist = ref_level_data.get("mfde", {}).get("entry_count_hist", {})
        g_entry_hist = g_level_data.get("mfde", {}).get("entry_count_hist", {})
        ref_dominant_count = _dominant_key(ref_entry_hist)
        g_entry_counts = set(g_entry_hist.keys())
        level_detail["entry_count"] = {
            "reference_dominant": ref_dominant_count, "generated_observed": sorted(g_entry_counts),
        }
        if ref_dominant_count is not None and g_entry_counts - {ref_dominant_count}:
            fails.append(
                f"level {level_str}: mfde entry count(s) {sorted(g_entry_counts - {ref_dominant_count})} "
                f"!= profile's {ref_dominant_count}")

        # --- absent-slot encoding: G's observed absent pairs must match R's ---
        g_absent_observed = set(g_level_data.get("mfde", {}).get("absent_values_observed", {}).keys())
        expected_absent_key = f"{ref_absent[0]},{ref_absent[1]}" if ref_absent else None
        level_detail["absent_value"] = {
            "reference": ref_absent, "generated_observed": sorted(g_absent_observed),
        }
        if expected_absent_key is not None:
            unexpected = g_absent_observed - {expected_absent_key}
            if unexpected:
                fails.append(
                    f"level {level_str}: absent-slot encoding(s) {sorted(unexpected)} "
                    f"!= profile's {expected_absent_key}")

        # --- per-entry-index presence classes: G's subset of R's ---
        ref_idx_hist = ref_level_data.get("mfde", {}).get("per_entry_index_class_hist", {})
        g_idx_hist = g_level_data.get("mfde", {}).get("per_entry_index_class_hist", {})
        idx_offenders = {}
        for idx, g_classes in g_idx_hist.items():
            g_present = {c for c, n in g_classes.items() if n}
            ref_present = {c for c, n in ref_idx_hist.get(idx, {}).items() if n}
            extra = g_present - ref_present
            if extra:
                idx_offenders[idx] = sorted(extra)
        level_detail["entry_index_class_offenders"] = idx_offenders
        if idx_offenders:
            fails.append(f"level {level_str}: mfde entry-index presence classes not in R: {idx_offenders}")

        # --- nregion: every parcel's value must equal R's dominant value ---
        ref_nregion_hist = ref_level_data.get("nregion_hist", {})
        g_nregion_hist = g_level_data.get("nregion_hist", {})
        ref_dominant_nregion = _dominant_key(ref_nregion_hist)
        g_nregion_values = set(g_nregion_hist.keys())
        level_detail["nregion"] = {
            "reference_dominant": ref_dominant_nregion, "generated_observed": sorted(g_nregion_values),
        }
        if ref_dominant_nregion is not None and g_nregion_values - {ref_dominant_nregion}:
            fails.append(
                f"level {level_str}: nregion value(s) {sorted(g_nregion_values - {ref_dominant_nregion})} "
                f"!= profile's dominant {ref_dominant_nregion}")

        details_by_level[level_str] = level_detail

    if fails:
        return CheckResult("FAIL", f"{len(fails)} mfde/nregion failure(s) (showing up to 20)",
                            {"levels": details_by_level, "failures": fails[:20]})
    return CheckResult(
        "PASS",
        "every parcel's mfde entry count/absent-slot encoding and nregion match the profile",
        {"levels": details_by_level},
    )


CHECKS = [
    Check(
        id="mfde", layer="map",
        description=(
            "Every parcel's mfde entry count and absent-slot encoding match the "
            "profile; per-entry-index presence classes in G are a subset of R's; "
            "nregion per level equals R's dominant value."
        ),
        run=_run_mfde,
    ),
]
