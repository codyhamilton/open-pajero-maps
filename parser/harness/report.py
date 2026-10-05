"""Prints the per-check PASS/FAIL/N-A table and writes the JSON report."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPORT_PATH = "output/compare_report.json"


def print_table(results: list[dict], *, layers_present: list | None = None) -> None:
    id_width = max([len("id")] + [len(r["id"]) for r in results] or [2])
    status_width = max([len("status")] + [len(r["status"]) for r in results] or [6])
    header = f"{'id':<{id_width}}  {'status':<{status_width}}  message"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['id']:<{id_width}}  {r['status']:<{status_width}}  {r['message']}")
    layers = list(layers_present) if layers_present is not None else []
    map_only = layers == ["map"]
    if map_only:
        print()
        print(
            "scope: map-only (layers_present=['map']); "
            "full_disc_parity=false — exit 0 is not full-disc parity"
        )


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def bind_generated(generated: str, manifest_path: str | None, no_manifest: bool):
    """Hash the evaluated ALLDATA.KWI and check it against the build manifest.

    Returns (binding_fields, error). `error` is a refusal message or None.
    """
    p = Path(generated)
    binding = {
        "generated_sha256": sha256_file(generated),
        "generated_mtime": datetime.fromtimestamp(
            p.stat().st_mtime, timezone.utc).isoformat(),
    }
    if no_manifest:
        binding["manifest_bound"] = False
        return binding, None
    mpath = Path(manifest_path) if manifest_path else p.parent / "manifest.json"
    if not mpath.is_file():
        return binding, (f"refusing to compare: manifest {mpath} not found "
                         "(pass --manifest or --no-manifest)")
    try:
        want = json.loads(mpath.read_text()).get("sha256")
    except (OSError, ValueError) as e:
        return binding, f"refusing to compare: cannot read manifest {mpath}: {e}"
    if want != binding["generated_sha256"]:
        return binding, (
            f"refusing to compare: {generated} sha256 {binding['generated_sha256']} "
            f"!= manifest {mpath} sha256 {want} (stale manifest/report or a "
            "different build)")
    binding["manifest_bound"] = True
    binding["manifest_path"] = str(mpath)
    return binding, None


def write_report(path: str, reference, generated: str, results: list[dict],
                 binding: dict | None = None,
                 layers_present: list | None = None) -> None:
    layers = list(layers_present) if layers_present is not None else []
    map_only = layers == ["map"]
    out = {
        "generated": generated,
        "reference": reference,
        **(binding or {}),
        "layers_present": layers,
        "scope": "map-only" if map_only else ("full-disc" if layers else "unspecified"),
        "full_disc_parity": False if map_only or not layers else None,
        "checks": results,
    }
    if out["full_disc_parity"] is None:
        # Non-map-only configs: do not claim full-disc parity here either
        # until WP2–WP5 real checks exist; honesty default is false.
        out["full_disc_parity"] = False
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
