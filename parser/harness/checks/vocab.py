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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness.context import Check, CheckResult
from harness.profile import generated_profile

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
    string_type_1_at_level_0 = False

    for level_str, g_level_data in g_levels.items():
        ref_level_data = ref_levels.get(level_str)
        level_offenders: dict = {}
        for field_name, path in _VOCAB_FIELDS:
            g_set = _hist_keys(g_level_data, path)
            ref_set = _hist_keys(ref_level_data, path)
            extra = sorted(g_set - ref_set)
            if extra:
                level_offenders[field_name] = extra

        if level_str == "0":
            name_types_at_l0 = _hist_keys(g_level_data, ("name", "string_type_hist"))
            if "1" in name_types_at_l0:
                string_type_1_at_level_0 = True
                level_offenders.setdefault("name_string_type_forbidden", []).append("1")

        if level_offenders:
            offenders[level_str] = level_offenders

    if offenders:
        msg = f"vocabulary offenders at {len(offenders)} level(s)"
        if string_type_1_at_level_0:
            msg += "; string_type=1 present at level 0 (forbidden)"
        return CheckResult("FAIL", msg, {"offenders": offenders})
    return CheckResult(
        "PASS", "every enumerated value in G is a subset of R's per-level vocabulary", {})


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
