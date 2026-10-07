#!/usr/bin/env python3
"""Plan 50 Phase 1 — stratified presence proof (≥1 cell/relation incl. 396/397/775)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from supply_path_assembler import SupplyAssembler, production_c_probe  # noqa: E402

IMPL = Path(__file__).resolve().parent
SCRATCH = ROOT / "output/scratch-50"
PIN = json.loads((IMPL / "snapshot_ways_pin.json").read_text())


def main() -> int:
    asm = SupplyAssembler(
        members_path=IMPL / "relation_members_10.json",
        pbf_ways_path=SCRATCH / "way_geometry_pbf.json",
        snapshot_ways_path=ROOT / PIN["snapshot"]["path"],
        snapshot_sha=PIN["snapshot"]["sha256"],
        targets_path=IMPL / "targets_341.json",
    )
    sample = asm.stratified_sample()
    results = []
    probe_scratch = SCRATCH / "phase1" / "cprobe"
    probe_scratch.mkdir(parents=True, exist_ok=True)
    for row in sample:
        rid = int(row["relation_id"])
        ix, iy = int(row["ix"]), int(row["iy"])
        bg = asm.emit_for_cell(rid, ix, iy)
        entry = {
            "dump_row": int(row["dump_row"]),
            "relation_id": rid,
            "ix": ix,
            "iy": iy,
            "clip_present": bg is not None,
            "n_coords": 0 if bg is None else bg.n_coords,
        }
        if bg is not None:
            c = production_c_probe(bg.coords, ix, iy, probe_scratch)
            entry["production_C"] = c
            entry["presence"] = bool(c["emits"])
        else:
            entry["production_C"] = None
            entry["presence"] = False
        results.append(entry)
        print(json.dumps(entry, sort_keys=True), flush=True)
    ok = all(r["presence"] for r in results)
    out = {
        "schema": "plan50-phase1-stratified-proof-v1",
        "n_sample": len(results),
        "all_present": ok,
        "relations_covered": sorted({r["relation_id"] for r in results}),
        "snapshot_rows_covered": sorted(
            r["dump_row"] for r in results if r["dump_row"] in (396, 397, 775)),
        "path_choice": "overlay",
        "provenance": asm.provenance,
        "results": results,
    }
    path = SCRATCH / "phase1" / "stratified_proof.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print("wrote", path, "all_present", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
