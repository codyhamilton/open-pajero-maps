"""`mfde` check: the plan's acceptance bullet -- "the mfde entry count and
absent-slot encoding match the profile on every parcel" -- plus the
`nregion` half of the same census (`docs/plans/.../PLAN.md`'s "Refinement
findings": "`nregion` is 1 at levels 0-8 ... 0 at levels 10 and 12").

Per-parcel mfde detail is not retained anywhere (the census in
`harness/profile.py` is already an aggregate, streamed one leaf at a time),
so this check works off `harness.profile.build_profile()`'s per-level
aggregates for both `R` and `G`: `R` itself carries a real distribution of
entry counts and `nregion` values per level, not a single constant (see
`DESIGN.md` sections 3-4), so `G`'s observed set of values must be a subset
of `R`'s observed set for that level -- the same presence-class subset
logic already used below for `per_entry_index_class_hist`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness.context import Check, CheckResult
from harness.profile import generated_profile


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

        # --- entry count: G's observed counts must be a subset of R's observed set ---
        ref_entry_hist = ref_level_data.get("mfde", {}).get("entry_count_hist", {})
        g_entry_hist = g_level_data.get("mfde", {}).get("entry_count_hist", {})
        ref_entry_counts = set(ref_entry_hist.keys())
        g_entry_counts = set(g_entry_hist.keys())
        level_detail["entry_count"] = {
            "reference_observed": sorted(ref_entry_counts), "generated_observed": sorted(g_entry_counts),
        }
        entry_count_offenders = g_entry_counts - ref_entry_counts
        if entry_count_offenders:
            fails.append(
                f"level {level_str}: mfde entry count(s) {sorted(entry_count_offenders)} "
                f"not in profile's observed set {sorted(ref_entry_counts)}")

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

        # --- nregion: G's observed values must be a subset of R's observed set ---
        ref_nregion_hist = ref_level_data.get("nregion_hist", {})
        g_nregion_hist = g_level_data.get("nregion_hist", {})
        ref_nregion_values = set(ref_nregion_hist.keys())
        g_nregion_values = set(g_nregion_hist.keys())
        level_detail["nregion"] = {
            "reference_observed": sorted(ref_nregion_values), "generated_observed": sorted(g_nregion_values),
        }
        nregion_offenders = g_nregion_values - ref_nregion_values
        if nregion_offenders:
            fails.append(
                f"level {level_str}: nregion value(s) {sorted(nregion_offenders)} "
                f"not in profile's observed set {sorted(ref_nregion_values)}")

        details_by_level[level_str] = level_detail

    if fails:
        return CheckResult("FAIL", f"{len(fails)} mfde/nregion failure(s) (showing up to 20)",
                            {"levels": details_by_level, "failures": fails[:20]})
    return CheckResult(
        "PASS",
        "every parcel's mfde entry count/absent-slot encoding and nregion are within the profile's observed sets",
        {"levels": details_by_level},
    )


CHECKS = [
    Check(
        id="mfde", layer="map",
        description=(
            "Every parcel's mfde entry count and absent-slot encoding match the "
            "profile; per-entry-index presence classes in G are a subset of R's; "
            "mfde entry counts and nregion per level are each a subset of R's "
            "observed set of values."
        ),
        run=_run_mfde,
    ),
]
