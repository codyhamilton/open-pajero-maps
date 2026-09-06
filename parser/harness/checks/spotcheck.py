"""`spotcheck`: the content-level spot-check fixture table from
`docs/design/target-disc.md`'s paragraph after the check table -- named
coordinates in each state capital resolving to the expected OSM
street/place names, driven by the data table at
`parser/refdata/spot_checks.json` (referenced by `harness.json`'s
`spot_checks` key) rather than ad-hoc.

Each fixture row is checked at each of its `levels`: at level 0 every name
in `expect_road_names` must appear (case-insensitive substring match) in
some decoded `NameRecord.text` of the located parcel; at level 2 every name
in `expect_place_names` must appear the same way (level 2 rows expect place
names only, per the brief's contract -- `expect_road_names` is not checked
at level 2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from harness.context import Check, CheckResult
from kiwiw.disc import AllData

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _resolve_table_path(ctx) -> Path | None:
    raw = ctx.config.get("spot_checks")
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        p = _REPO_ROOT / p
    return p


def _record_texts(parcel) -> list[str]:
    texts: list[str] = []
    if parcel.name is not None:
        texts.extend(r.text for r in parcel.name.records)
    return texts


def _missing(expected: list[str], texts: list[str]) -> tuple[list[str], list[str]]:
    """Returns (matched, missing) for `expected` names against `texts`,
    case-insensitive substring match."""
    lowered = [t.lower() for t in texts]
    matched, missing = [], []
    for name in expected:
        if any(name.lower() in t for t in lowered):
            matched.append(name)
        else:
            missing.append(name)
    return matched, missing


def _run_spotcheck(ctx) -> CheckResult:
    table_path = _resolve_table_path(ctx)
    if table_path is None or not table_path.exists():
        return CheckResult("NA", "spot-check fixture table not present", {})

    with open(table_path, "r") as f:
        rows = json.load(f)

    row_details = []
    any_fail = False
    with AllData(ctx.generated) as disc:
        for row in rows:
            city = row["city"]
            lat = row["lat"]
            lon = row["lon"]
            for level in row["levels"]:
                expected = (
                    row.get("expect_road_names", [])
                    if level == 0
                    else row.get("expect_place_names", [])
                )
                parcel = disc.find_parcel(lat, lon, level=level)
                if parcel is None:
                    row_details.append({
                        "city": city, "level": level, "found": False,
                        "matched": [], "missing": expected,
                    })
                    any_fail = True
                    continue
                texts = _record_texts(parcel)
                matched, missing = _missing(expected, texts)
                if missing:
                    any_fail = True
                row_details.append({
                    "city": city, "level": level, "found": True,
                    "matched": matched, "missing": missing,
                })

    if any_fail:
        n_fail = sum(1 for d in row_details if d["missing"] or not d["found"])
        return CheckResult(
            "FAIL",
            f"{n_fail} row/level(s) missing an expected name or parcel",
            {"rows": row_details},
        )
    return CheckResult(
        "PASS",
        f"all {len(row_details)} row/level checks matched their expected names",
        {"rows": row_details},
    )


CHECKS = [
    Check(id="spotcheck", layer="map",
          description="Named coordinates in each state capital resolve to the expected "
                       "OSM road/place names (fixture table at parser/refdata/spot_checks.json).",
          run=_run_spotcheck),
]
