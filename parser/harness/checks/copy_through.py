"""`copy_through_graphics` check: byte-identical R↔G contracts for the
ten target-disc content-independent copy files (LOADING / DICVCE / GRA /
PCT / …), per `docs/design/target-disc.md` WP5 copy row and the Assessor
UI `cmp` recipe.

Layer is `meta` (aligned with plan 22). Under default
`layers_present=["map"]` the CLI gates this check to NA — missing G
siblings must not FAIL map-only runs, and must not PASS as if copy
succeeded. When the layer is in scope, every listed basename must exist
on both disc roots and be byte-identical; missing or mismatched files
are FAIL (missing verification is not successful copying).

This check subsumes the plan-22 `wp5_meta` NA-only sentinel. It does
**not** implement WP5 copy writers and does not promote `meta` into
default `layers_present`.
"""
from __future__ import annotations

from pathlib import Path

from harness.context import Check, CheckResult

# Canonical list = docs/design/target-disc.md copy row (ten basenames).
COPY_THROUGH_BASENAMES: tuple[str, ...] = (
    "LOADING.KWI",
    "DICVCE56.KWI",
    "GRA256D.KWI",
    "KGRA256.KWI",
    "PCT256D.KWI",
    "KPCT256.KWI",
    "PCT2DAT.KWI",
    "KPCT2DT.KWI",
    "KGRPDAT.KWI",
    "VAR256D.KWI",
)


def _first_diff_offset(a: bytes, b: bytes) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def _run_copy_through_graphics(ctx) -> CheckResult:
    if ctx.reference is None or ctx.reference_root is None:
        return CheckResult(
            "NA",
            "--reference disc root required for copy-through cmp "
            "(directory or ALLDATA.KWI path)",
            {"basenames": list(COPY_THROUGH_BASENAMES)},
        )
    if ctx.generated_root is None:
        return CheckResult(
            "NA",
            "generated disc root required for copy-through cmp "
            "(directory or ALLDATA.KWI path)",
            {"basenames": list(COPY_THROUGH_BASENAMES)},
        )

    r_root = Path(ctx.reference_root)
    g_root = Path(ctx.generated_root)
    failures: list[dict] = []

    for name in COPY_THROUGH_BASENAMES:
        r_path = r_root / name
        g_path = g_root / name
        if not r_path.is_file():
            failures.append({
                "basename": name,
                "kind": "missing_reference",
                "reference": str(r_path),
                "generated": str(g_path),
            })
            continue
        if not g_path.is_file():
            failures.append({
                "basename": name,
                "kind": "missing_generated",
                "reference": str(r_path),
                "generated": str(g_path),
            })
            continue
        r_bytes = r_path.read_bytes()
        g_bytes = g_path.read_bytes()
        if len(r_bytes) != len(g_bytes):
            failures.append({
                "basename": name,
                "kind": "size_mismatch",
                "reference_size": len(r_bytes),
                "generated_size": len(g_bytes),
            })
            continue
        if r_bytes != g_bytes:
            failures.append({
                "basename": name,
                "kind": "content_mismatch",
                "first_diff_offset": _first_diff_offset(r_bytes, g_bytes),
                "size": len(r_bytes),
            })

    if failures:
        names = ", ".join(f["basename"] for f in failures)
        return CheckResult(
            "FAIL",
            f"copy-through graphics mismatch or missing: {names}",
            {
                "failures": failures,
                "checked": list(COPY_THROUGH_BASENAMES),
                "reference_root": str(r_root),
                "generated_root": str(g_root),
            },
        )

    return CheckResult(
        "PASS",
        f"all {len(COPY_THROUGH_BASENAMES)} copy-through files "
        "byte-identical on disc roots",
        {
            "checked": list(COPY_THROUGH_BASENAMES),
            "reference_root": str(r_root),
            "generated_root": str(g_root),
        },
    )


CHECKS = [
    Check(
        id="copy_through_graphics",
        layer="meta",
        description=(
            "Target-disc copy-through siblings (LOADING/DICVCE/GRA/PCT/…) "
            "are byte-identical on R and G disc roots; missing files FAIL "
            "when layer 'meta' is in scope."
        ),
        run=_run_copy_through_graphics,
    ),
]
