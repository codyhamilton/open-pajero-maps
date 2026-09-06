#!/usr/bin/env python3
"""CLI: offline reference-vs-generated comparison harness for `ALLDATA.KWI`,
per `docs/design/target-disc.md`'s "Evaluation: the offline oracle".

Usage::

    python3 parser/compare_disc.py --reference <disc root or ALLDATA.KWI> \\
        --generated <dir or ALLDATA.KWI> [--checks a,b,c] [--config file.json] \\
        [--report output/compare_report.json]

Exit code 0 only when every applicable (non-NA) check is PASS.

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
    `ALLDATA.KWI`."""
    path = Path(p)
    if path.is_dir():
        return str(path / "ALLDATA.KWI")
    return str(path)


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
    generated_path = _resolve_alldata_path(args.generated)
    reference_path = _resolve_alldata_path(args.reference) if args.reference else None

    ctx = Context(reference=reference_path, generated=generated_path, config=config)

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

    report.print_table(results)
    report.write_report(args.report, reference_path, generated_path, results)

    exit_code = 0 if all(r["status"] != "FAIL" for r in results) else 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
