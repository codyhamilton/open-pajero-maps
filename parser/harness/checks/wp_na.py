"""WP2–WP5 negative-control checks: absent layers report NA under map-only
config so a green harness run cannot omit that route / address / index /
metadata packages were not evaluated.

Real parity science for those packages lives in future WP designs. Until a
layer is present *and* a real check body replaces these sentinels, run()
returns NA (not started) if somehow invoked with the layer marked present.
"""
from __future__ import annotations

from harness.context import Check, CheckResult

_WP = (
    ("wp2_route", "route", "WP2", "route planning frames / ext frames"),
    ("wp3_address", "address", "WP3", "address and POI search"),
    ("wp4_index", "index", "WP4", "remaining IDX / HWMAP / INDEXDAT"),
    ("wp5_meta", "meta", "WP5", "disc stamp / coverage / image / burn"),
)


def _make_run(wp_label: str, package: str):
    def _run(ctx) -> CheckResult:
        return CheckResult(
            "NA",
            f"{wp_label} ({package}) not started — negative control; "
            "not full-disc parity",
            {"work_package": wp_label, "not_started": True},
        )
    return _run


CHECKS = [
    Check(
        id=cid,
        layer=layer,
        description=(
            f"{wp} negative control: layer '{layer}' absent under map-only "
            f"config reports NA ({package} not started)."
        ),
        run=_make_run(wp, package),
    )
    for cid, layer, wp, package in _WP
]
