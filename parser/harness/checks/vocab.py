"""`vocab` check: "Same vocabulary" from `docs/design/target-disc.md`'s
check table -- "Every enumerated value in `G` (road type, display class,
background type code, name string type, name type code) is drawn from the
set observed in `R`", plus the plan's explicit `string_type=1` criterion:
"the generated disc's ... name string-type value sets are subsets of the
reference profile's sets; `string_type=1` does not appear" (that bullet is
the reference disc's own level-0 rule -- level 0 is where `string_type=1` is
absent on `R`; see this brief's "Refinement findings" epigraph and the
contradiction called out in profile.py / this unit's report-back)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness.context import Check, CheckResult
from harness.profile import generated_profile

HARNESS_JSON = Path(__file__).resolve().parent.parent.parent / "refdata" / "harness.json"
# A vocabulary/histogram where R has fewer observations than this is reported
# advisory (never FAIL) for the coverage direction.
MIN_R_OBSERVATIONS = 100


def coverage_band() -> tuple:
    """(tol, min_class_share) from harness.json bands.vocab_coverage / amendments."""
    with open(HARNESS_JSON) as f:
        bands = json.load(f)["bands"]
    return (bands["vocab_coverage"]["tol"],
            bands.get("amendments", {}).get("coverage_min_class_share", 0.0))


def coverage(r_hist: dict, g_keys, tol: float, min_share: float, top: int = 5) -> dict:
    """R-frequency-weighted share of R's values that G uses. `status` is
    ok | fail | advisory (R total < MIN_R_OBSERVATIONS)."""
    total = sum(r_hist.values())
    if total <= 0:
        return {"status": "advisory", "r_total": total, "share": None, "missing_top": []}
    g_keys = set(g_keys)
    missing = sorted(((k, n) for k, n in r_hist.items() if k not in g_keys), key=lambda kv: -kv[1])
    share = 1 - sum(n for _, n in missing) / total
    rare_missing = [k for k, n in missing if n / total >= min_share]
    if total < MIN_R_OBSERVATIONS:
        status = "advisory"
    elif share < 1 - tol or rare_missing:
        status = "fail"
    else:
        status = "ok"
    return {"status": status, "r_total": total, "share": round(share, 6),
            "missing_top": [[k, n] for k, n in missing[:top]], "missing_over_min_share": rare_missing}


# field label -> (sub-dict path within one level's profile entry) to the
# histogram whose *keys* are the censused vocabulary for that field.
_VOCAB_FIELDS = [
    ("road_type", ("road", "road_type_hist")),
    ("display_class", ("road", "display_class_hist")),
    ("background_type_code", ("background", "type_code_hist")),
    ("name_string_type", ("name", "string_type_hist")),
    ("name_type_code", ("name", "type_code_hist")),
]


def _hist_keys(level_data: dict, path: tuple) -> set:
    node = level_data
    for p in path:
        node = node.get(p, {}) if node is not None else {}
    return set((node or {}).keys())


def _hist(level_data, path):
    node = level_data
    for p in path:
        node = (node or {}).get(p, {})
    return node or {}


def _run_vocab(ctx) -> CheckResult:
    if not ctx.layer_present("map"):
        return CheckResult("NA", "map layer not present per config", {})

    ref_profile = ctx.profile("map")
    if not ref_profile:
        return CheckResult("NA", "no reference profile available (unit 03b not landed yet)", {})

    g_profile = generated_profile(ctx.generated)

    ref_levels = ref_profile.get("levels", {})
    g_levels = g_profile.get("levels", {})

    offenders: dict = {}
    tol, min_share = coverage_band()
    cov_fail: dict = {}
    cov_advisory: dict = {}
    cov_all: dict = {}
    string_type_1_at_level_0 = False

    # Iterate the union of R's and G's levels, not just G's -- see
    # envelope.py's identical fix and docs/design/target-disc.md's map
    # layer row ("harness level-iteration gap").
    all_level_strs = sorted(set(ref_levels) | set(g_levels), key=int)
    for level_str in all_level_strs:
        g_level_data = g_levels.get(level_str, {})
        ref_level_data = ref_levels.get(level_str)
        level_offenders: dict = {}
        for field_name, path in _VOCAB_FIELDS:
            g_set = _hist_keys(g_level_data, path)
            ref_set = _hist_keys(ref_level_data, path)
            extra = sorted(g_set - ref_set)
            if extra:
                level_offenders[field_name] = extra

        if ref_level_data is not None:
            for field_name, path in _VOCAB_FIELDS:
                c = coverage(_hist(ref_level_data, path), _hist_keys(g_level_data, path), tol, min_share)
                cov_all.setdefault(level_str, {})[field_name] = c
                if c["status"] == "fail":
                    cov_fail.setdefault(level_str, {})[field_name] = c
                elif c["status"] == "advisory":
                    cov_advisory.setdefault(level_str, {})[field_name] = c

        if level_str == "0":
            name_types_at_l0 = _hist_keys(g_level_data, ("name", "string_type_hist"))
            if "1" in name_types_at_l0:
                string_type_1_at_level_0 = True
                level_offenders.setdefault("name_string_type_forbidden", []).append("1")

        if level_offenders:
            offenders[level_str] = level_offenders

    details = {"coverage": cov_all, "coverage_tol": tol, "coverage_min_class_share": min_share,
               "min_r_observations": MIN_R_OBSERVATIONS,
               "advisory_levels": sorted(cov_advisory, key=int)}
    if offenders or cov_fail:
        parts = []
        if offenders:
            msg = f"vocabulary offenders at {len(offenders)} level(s)"
            if string_type_1_at_level_0:
                msg += "; string_type=1 present at level 0 (forbidden)"
            parts.append(msg)
            details["offenders"] = offenders
        if cov_fail:
            parts.append(f"coverage below {1 - tol:.2f} at {len(cov_fail)} level(s)")
            details["coverage_failures"] = cov_fail
        return CheckResult("FAIL", "; ".join(parts), details)
    return CheckResult(
        "PASS", "every enumerated value in G is a subset of R's per-level vocabulary and covers R by frequency",
        details)


CHECKS = [
    Check(
        id="vocab", layer="map",
        description=(
            "Road type, display class, background type code, and name "
            "string-type/type-code sets in G are subsets of R's per level; "
            "string_type=1 must not appear at level 0."
        ),
        run=_run_vocab,
    ),
]
