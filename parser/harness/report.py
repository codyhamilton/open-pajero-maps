"""Prints the per-check PASS/FAIL/N-A table and writes the JSON report."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_REPORT_PATH = "output/compare_report.json"


def print_table(results: list[dict]) -> None:
    id_width = max([len("id")] + [len(r["id"]) for r in results])
    status_width = max([len("status")] + [len(r["status"]) for r in results])
    header = f"{'id':<{id_width}}  {'status':<{status_width}}  message"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['id']:<{id_width}}  {r['status']:<{status_width}}  {r['message']}")


def write_report(path: str, reference, generated: str, results: list[dict]) -> None:
    out = {
        "generated": generated,
        "reference": reference,
        "checks": results,
    }
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
