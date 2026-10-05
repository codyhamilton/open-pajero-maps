#!/usr/bin/env python3
"""CLI: offline reference-vs-generated comparison harness for `ALLDATA.KWI`,
per `docs/design/target-disc.md`'s "Evaluation: the offline oracle".

Usage::

    python3 parser/compare_disc.py --reference <disc root or ALLDATA.KWI> \\
        --generated <dir or ALLDATA.KWI> [--checks a,b,c] [--config file.json] \\
        [--report output/compare_report.json]

Exit code 0 when no check is FAIL (PASS and NA both OK).

Default config has layers_present=["map"] only. A green exit under that
map-only scope is **not** full-disc parity: WP2–WP4 appear as NA negative
controls; copy_through_graphics (layer meta) is also NA under map-only.
The JSON report sets full_disc_parity=false. See docs/OVERVIEW.md WP table
and the Assessor functional-e2e warning.

This module is a thin CLI over `parser/harness/`; all check logic lives
there. See `parser/harness/__init__.py` for the reading-paths-only import
constraint.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import registry, report
from harness.context import Context
from harness.profile import build_profile

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "refdata" / "harness.json"
DEFAULT_PROFILE_OUT = Path(__file__).resolve().parent / "refdata" / "profile" / "map.json"


def _resolve_alldata_path(p: str) -> str:
    """Accept either a disc root directory or a direct path to
    `ALLDATA.KWI`. Prefer `_resolve_disc_paths` when sibling roots matter."""
    alldata, _root = _resolve_disc_paths(p)
    return alldata


def _resolve_disc_paths(p: str) -> tuple[str, str | None]:
    """Return `(alldata_path, disc_root)`.

    A directory argument is the disc root (`…/ALLDATA.KWI` beside siblings).
    A path whose basename is `ALLDATA.KWI` uses its parent as the root.
    Any other bare file has no sibling meaning → root is None.
    """
    path = Path(p)
    if path.is_dir():
        return str(path / "ALLDATA.KWI"), str(path)
    alldata = str(path)
    if path.name.upper() == "ALLDATA.KWI":
        return alldata, str(path.parent)
    return alldata, None


def _load_config(path: str | None) -> dict:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(cfg_path, "r") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", help="Reference disc root or ALLDATA.KWI path")
    ap.add_argument("--generated", help="Generated disc dir or ALLDATA.KWI path")
    ap.add_argument("--checks", help="Comma-separated list of check ids to run "
                                       "(default: all discovered checks)")
    ap.add_argument("--config", help="Path to a harness config JSON "
                                       "(default: parser/refdata/harness.json)")
    ap.add_argument("--report", default="output/compare_report.json",
                     help="Path to write the JSON report")
    ap.add_argument("--profile", action="store_true",
                     help="Census --reference into the checked-in reference profile "
                          "(parser/refdata/profile/map.json by default) instead of "
                          "running checks")
    ap.add_argument("--profile-out", help="Path to write the profile JSON "
                                            "(default: parser/refdata/profile/map.json)")
    ap.add_argument("--manifest", help="Build manifest to bind the generated "
                                         "ALLDATA.KWI to (default: manifest.json "
                                         "beside it)")
    ap.add_argument("--no-manifest", action="store_true",
                     help="Skip manifest binding (report records manifest_bound=false)")
    ap.add_argument("--workers", type=int, default=1,
                     help="Worker-pool width for checks that support a "
                          "parallel-over-blocks decode (default: 1, today's "
                          "single-process behaviour; only coord_scale uses it)")
    args = ap.parse_args()

    if args.profile:
        if not args.reference:
            ap.error("--reference is required with --profile")
        reference_path = _resolve_alldata_path(args.reference)
        profile = build_profile(reference_path)
        out_path = Path(args.profile_out) if args.profile_out else DEFAULT_PROFILE_OUT
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(profile, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"wrote reference profile to {out_path}", file=sys.stderr)
        return 0

    if not args.generated:
        ap.error("--generated is required unless --profile")

    config = _load_config(args.config)
    generated_path, generated_root = _resolve_disc_paths(args.generated)
    if args.reference:
        reference_path, reference_root = _resolve_disc_paths(args.reference)
    else:
        reference_path, reference_root = None, None

    binding, err = report.bind_generated(generated_path, args.manifest,
                                         args.no_manifest)
    if err:
        print(err, file=sys.stderr)
        return 2

    ctx = Context(reference=reference_path, generated=generated_path, config=config,
                  workers=args.workers,
                  reference_root=reference_root, generated_root=generated_root)

    all_checks = registry.discover()
    if args.checks:
        wanted = set(c.strip() for c in args.checks.split(","))
        unknown = wanted - {c.id for c in all_checks}
        if unknown:
            ap.error(f"unknown check id(s): {', '.join(sorted(unknown))}")
        selected = [c for c in all_checks if c.id in wanted]
    else:
        selected = all_checks

    from harness.context import CheckResult

    results = []
    for check in selected:
        if not ctx.layer_present(check.layer):
            result = CheckResult("NA", f"layer '{check.layer}' not present per config", {})
        else:
            result = check.run(ctx)
        results.append({
            "id": check.id,
            "layer": check.layer,
            "status": result.status,
            "message": result.message,
            "details": result.details,
        })

    layers_present = list(config.get("layers_present") or [])
    report.print_table(results, layers_present=layers_present)
    report.write_report(args.report, reference_path, generated_path, results, binding,
                        layers_present=layers_present)

    exit_code = 0 if all(r["status"] != "FAIL" for r in results) else 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
